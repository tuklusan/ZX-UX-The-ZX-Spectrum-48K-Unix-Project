; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Proprietary rights reserved except as expressly licensed herein.
;
; ZX-UX Sinclair ZX Spectrum Unix
; This file is governed by the SANYALnet Labs Non-Commercial License in the
; root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
; for AI/ML model training are prohibited unless separately authorized.
;
; Attribution is required: "Based on original work by Supratim Sanyal of
; SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
; patent, trademark, and governing-law provisions.
;
; Native ZX-UX linker. Phase 10 grows this file monotonically.

; P10.21 linker OBJ1 input loader.
    MACRO EMIT_P10_LD_INPUT_LOADER
LD_P1021_HEADER_SIZE EQU 24
LD_P1021_SYMBOL_SIZE EQU 20
LD_P1021_RELOC_SIZE  EQU 6
LD_P1021_MAX_STORED  EQU $8000
LD_P1021_REL_ABS16   EQU 1

; C=input count. One or more inputs are mandatory.
ld_p1021_require_inputs:
    ld a,c
    or a
    jr z,ld_p1021_format
    xor a
    ret

; HL=path, DE=destination buffer, BC=capacity.
; Success HL=exact stored length, candidate fully validated.
ld_p1021_load_file:
    ld (ld_p1021_path),hl
    ld (ld_p1021_buffer),de
    ld (ld_p1021_capacity),bc
    xor a
    ld (ld_p1021_open),a
    ld (ld_p1021_used),a
    ld (ld_p1021_used+1),a

    ; Kernel type metadata is authoritative; suffix spelling is irrelevant.
    ld (ld_p1021_stat_req),hl
    ld hl,ld_p1021_stat_out
    ld (ld_p1021_stat_req+2),hl
    ld hl,ld_p1021_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    ret c
    ld a,(ld_p1021_stat_out)
    cp OBJ_OBJ
    jp nz,ld_p1021_format

    ld hl,(ld_p1021_path)
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jp nz,ld_p1021_bad_handle
    ld a,l
    ld (ld_p1021_handle),a
    ld a,1
    ld (ld_p1021_open),a

ld_p1021_read_loop:
    ld hl,(ld_p1021_capacity)
    ld de,(ld_p1021_used)
    or a
    sbc hl,de
    jr z,ld_p1021_probe_eof
    ld b,h
    ld c,l
    ld hl,(ld_p1021_buffer)
    ld de,(ld_p1021_used)
    add hl,de
    ld a,(ld_p1021_handle)
    ld e,a
    ld d,0
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jr c,ld_p1021_stream_error
    ld a,h
    or l
    jr z,ld_p1021_read_eof
    ex de,hl
    ld hl,(ld_p1021_used)
    add hl,de
    jr c,ld_p1021_nospc_stream
    ld de,(ld_p1021_capacity)
    push hl
    or a
    sbc hl,de
    pop hl
    jr c,ld_p1021_read_store
    jr z,ld_p1021_read_store
    jr ld_p1021_nospc_stream
ld_p1021_read_store:
    ld (ld_p1021_used),hl
    jr ld_p1021_read_loop

; Exact-capacity candidate: probe one byte without writing beyond caller buffer.
ld_p1021_probe_eof:
    ld a,(ld_p1021_handle)
    ld e,a
    ld d,0
    ld hl,ld_p1021_probe
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jr c,ld_p1021_stream_error
    ld a,h
    or l
    jr z,ld_p1021_read_eof
    jr ld_p1021_nospc_stream

ld_p1021_read_eof:
    call ld_p1021_close
    jr c,ld_p1021_stream_error_closed
    ld hl,(ld_p1021_buffer)
    ld bc,(ld_p1021_used)
    call ld_p1021_validate_memory
    ret c
    ld hl,(ld_p1021_used)
    ret

ld_p1021_nospc_stream:
    ld a,E_NOSPC
    jr ld_p1021_stream_error
ld_p1021_stream_error:
    ld (ld_p1021_errno),a
    call ld_p1021_close
    ld a,(ld_p1021_errno)
    scf
    ret
ld_p1021_stream_error_closed:
    scf
    ret
ld_p1021_bad_handle:
    ld a,E_FORMAT
    jr ld_p1021_stream_error
ld_p1021_close:
    ld a,(ld_p1021_open)
    or a
    ret z
    ld a,(ld_p1021_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret c
    xor a
    ld (ld_p1021_open),a
    ret

; HL=memory OBJ1 pointer, BC=exact stored length.
; Used for both file-loaded inputs and selected built-in archive members.
ld_p1021_validate_memory:
    ld (ld_p1021_obj),hl
    ld (ld_p1021_length),bc
    ld hl,(ld_p1021_length)
    ld de,LD_P1021_HEADER_SIZE
    or a
    sbc hl,de
    jp c,ld_p1021_val_bad

    ld ix,(ld_p1021_obj)
    ld a,(ix+0)
    cp 'O'
    jp nz,ld_p1021_val_bad
    ld a,(ix+1)
    cp 'B'
    jp nz,ld_p1021_val_bad
    ld a,(ix+2)
    cp 'J'
    jp nz,ld_p1021_val_bad
    ld a,(ix+3)
    cp '1'
    jp nz,ld_p1021_val_bad
    ld a,(ix+4)
    cp 1
    jp nz,ld_p1021_val_bad
    ld a,(ix+5)
    or a
    jp nz,ld_p1021_val_bad
    ld a,(ix+6)
    cp LD_P1021_HEADER_SIZE
    jp nz,ld_p1021_val_bad
    ld a,(ix+7)
    or a
    jp nz,ld_p1021_val_bad

    ld l,(ix+8)
    ld h,(ix+9)
    ld (ld_p1021_text),hl
    ld l,(ix+10)
    ld h,(ix+11)
    ld (ld_p1021_bss),hl
    ld l,(ix+12)
    ld h,(ix+13)
    ld (ld_p1021_sc),hl
    ld l,(ix+14)
    ld h,(ix+15)
    ld (ld_p1021_rc),hl
    ld l,(ix+16)
    ld h,(ix+17)
    ld (ld_p1021_so),hl
    ld l,(ix+18)
    ld h,(ix+19)
    ld (ld_p1021_ro),hl

    ld hl,(ld_p1021_text)
    ld de,(ld_p1021_bss)
    add hl,de
    jp c,ld_p1021_val_bad
    call ld_p1021_bound
    jp c,ld_p1021_val_bad

    ld hl,(ld_p1021_text)
    ld de,LD_P1021_HEADER_SIZE
    add hl,de
    jp c,ld_p1021_val_bad
    ld de,(ld_p1021_so)
    or a
    sbc hl,de
    jp nz,ld_p1021_val_bad

    ld de,(ld_p1021_sc)
    ld a,LD_P1021_SYMBOL_SIZE
    call ld_p1021_mul_small
    jp c,ld_p1021_val_bad
    ld (ld_p1021_sym_bytes),hl
    ld de,(ld_p1021_so)
    add hl,de
    jp c,ld_p1021_val_bad
    ld de,(ld_p1021_ro)
    or a
    sbc hl,de
    jp nz,ld_p1021_val_bad

    ld de,(ld_p1021_rc)
    ld a,LD_P1021_RELOC_SIZE
    call ld_p1021_mul_small
    jp c,ld_p1021_val_bad
    ld (ld_p1021_rel_bytes),hl
    ld de,(ld_p1021_ro)
    add hl,de
    jp c,ld_p1021_val_bad
    call ld_p1021_bound
    jp c,ld_p1021_val_bad
    ld de,(ld_p1021_length)
    or a
    sbc hl,de
    jp nz,ld_p1021_val_bad

    ld hl,(ld_p1021_rc)
    ld a,h
    or l
    jr z,ld_p1021_crc_body
    ld hl,(ld_p1021_text)
    ld a,h
    or a
    jr nz,ld_p1021_crc_body
    ld a,l
    cp 2
    jp c,ld_p1021_val_bad

ld_p1021_crc_body:
    ld hl,(ld_p1021_length)
    ld de,LD_P1021_HEADER_SIZE
    or a
    sbc hl,de
    ld b,h
    ld c,l
    ld hl,(ld_p1021_obj)
    ld de,LD_P1021_HEADER_SIZE
    add hl,de
    call ld_p1021_crc16
    ld ix,(ld_p1021_obj)
    ld a,(ix+20)
    cp e
    jp nz,ld_p1021_val_bad
    ld a,(ix+21)
    cp d
    jp nz,ld_p1021_val_bad

    ld hl,(ld_p1021_obj)
    ld de,ld_p1021_header_copy
    ld bc,LD_P1021_HEADER_SIZE
    ldir
    xor a
    ld (ld_p1021_header_copy+22),a
    ld (ld_p1021_header_copy+23),a
    ld hl,ld_p1021_header_copy
    ld bc,LD_P1021_HEADER_SIZE
    call ld_p1021_crc16
    ld ix,(ld_p1021_obj)
    ld a,(ix+22)
    cp e
    jp nz,ld_p1021_val_bad
    ld a,(ix+23)
    cp d
    jp nz,ld_p1021_val_bad

    call ld_p1021_validate_symbols
    jp c,ld_p1021_val_bad
    call ld_p1021_validate_relocs
    jp c,ld_p1021_val_bad
    xor a
    ret

ld_p1021_validate_symbols:
    ld hl,(ld_p1021_obj)
    ld de,(ld_p1021_so)
    add hl,de
    ld (ld_p1021_sym_start),hl
    ld (ld_p1021_sym_cur),hl
    ld hl,(ld_p1021_sc)
    ld (ld_p1021_left),hl
ld_p1021_sym_loop:
    ld hl,(ld_p1021_left)
    ld a,h
    or l
    jr z,ld_p1021_sym_ok
    ld hl,(ld_p1021_sym_cur)
    call ld_p1021_validate_symbol
    ret c

    ld hl,(ld_p1021_sym_start)
    ld (ld_p1021_scan),hl
ld_p1021_dup_loop:
    ld hl,(ld_p1021_scan)
    ld de,(ld_p1021_sym_cur)
    or a
    sbc hl,de
    jr z,ld_p1021_sym_advance
    ld hl,(ld_p1021_scan)
    ld de,(ld_p1021_sym_cur)
    ld b,16
ld_p1021_dup_cmp:
    ld a,(de)
    cp (hl)
    jr nz,ld_p1021_dup_next
    inc hl
    inc de
    djnz ld_p1021_dup_cmp
    scf
    ret
ld_p1021_dup_next:
    ld hl,(ld_p1021_scan)
    ld de,LD_P1021_SYMBOL_SIZE
    add hl,de
    ld (ld_p1021_scan),hl
    jr ld_p1021_dup_loop
ld_p1021_sym_advance:
    ld hl,(ld_p1021_sym_cur)
    ld de,LD_P1021_SYMBOL_SIZE
    add hl,de
    ld (ld_p1021_sym_cur),hl
    ld hl,(ld_p1021_left)
    dec hl
    ld (ld_p1021_left),hl
    jr ld_p1021_sym_loop
ld_p1021_sym_ok:
    xor a
    ret

; HL=one 20-byte symbol record.
ld_p1021_validate_symbol:
    ld (ld_p1021_record),hl
    ld b,16
    ld c,0
ld_p1021_name_loop:
    ld a,(hl)
    or a
    jr z,ld_p1021_name_zero
    ld a,c
    cp 15
    jr nc,ld_p1021_sym_bad
    ld a,c
    or a
    ld a,(hl)
    jr nz,ld_p1021_name_tail
    call ld_p1021_name_first
    jr c,ld_p1021_sym_bad
    jr ld_p1021_name_accept
ld_p1021_name_tail:
    call ld_p1021_name_next
    jr c,ld_p1021_sym_bad
ld_p1021_name_accept:
    inc c
    inc hl
    djnz ld_p1021_name_loop
    jr ld_p1021_sym_bad
ld_p1021_name_zero:
    ld a,c
    or a
    jr z,ld_p1021_sym_bad
ld_p1021_zero_tail:
    ld a,(hl)
    or a
    jr nz,ld_p1021_sym_bad
    inc hl
    djnz ld_p1021_zero_tail

    ld hl,(ld_p1021_record)
    ld de,18
    add hl,de
    ld a,(hl)
    cp 4
    jr nc,ld_p1021_sym_bad
    ld (ld_p1021_section),a
    inc hl
    ld a,(hl)
    and $FE
    jr nz,ld_p1021_sym_bad
    ld a,(hl)
    ld (ld_p1021_flags),a

    ld hl,(ld_p1021_record)
    ld de,16
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (ld_p1021_value),de

    ld a,(ld_p1021_section)
    or a
    jr z,ld_p1021_sym_undef
    cp 1
    jr z,ld_p1021_sym_text
    cp 2
    jr z,ld_p1021_sym_bss
    xor a
    ret
ld_p1021_sym_undef:
    ld hl,(ld_p1021_value)
    ld a,h
    or l
    jr nz,ld_p1021_sym_bad
    ld a,(ld_p1021_flags)
    cp 1
    jr nz,ld_p1021_sym_bad
    xor a
    ret
ld_p1021_sym_text:
    ld hl,(ld_p1021_value)
    ld de,(ld_p1021_text)
    or a
    sbc hl,de
    jr c,ld_p1021_sym_good
    jr z,ld_p1021_sym_good
    jr ld_p1021_sym_bad
ld_p1021_sym_bss:
    ld hl,(ld_p1021_value)
    ld de,(ld_p1021_bss)
    or a
    sbc hl,de
    jr c,ld_p1021_sym_good
    jr z,ld_p1021_sym_good
ld_p1021_sym_bad:
    scf
    ret
ld_p1021_sym_good:
    xor a
    ret

ld_p1021_name_first:
    cp 'A'
    jr c,ld_p1021_name_punct
    cp 'Z'+1
    jr c,ld_p1021_name_good
    cp 'a'
    jr c,ld_p1021_name_punct
    cp 'z'+1
    jr c,ld_p1021_name_good
ld_p1021_name_punct:
    cp '_'
    jr z,ld_p1021_name_good
    cp '.'
    jr z,ld_p1021_name_good
    cp '$'
    jr z,ld_p1021_name_good
    scf
    ret
ld_p1021_name_next:
    cp '0'
    jr c,ld_p1021_name_first
    cp '9'+1
    jr c,ld_p1021_name_good
    jp ld_p1021_name_first
ld_p1021_name_good:
    or a
    ret

ld_p1021_validate_relocs:
    ld hl,(ld_p1021_obj)
    ld de,(ld_p1021_ro)
    add hl,de
    ld (ld_p1021_rel_cur),hl
    ld hl,(ld_p1021_rc)
    ld (ld_p1021_left),hl
    xor a
    ld (ld_p1021_have_prev),a
ld_p1021_rel_loop:
    ld hl,(ld_p1021_left)
    ld a,h
    or l
    jr z,ld_p1021_rel_ok
    ld hl,(ld_p1021_rel_cur)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (ld_p1021_cur_off),de

    ld hl,(ld_p1021_text)
    dec hl
    dec hl
    or a
    sbc hl,de
    jr c,ld_p1021_rel_bad

    ld hl,(ld_p1021_rel_cur)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(ld_p1021_sc)
    or a
    sbc hl,de
    jr z,ld_p1021_rel_bad
    jr c,ld_p1021_rel_bad

    ld hl,(ld_p1021_rel_cur)
    ld de,4
    add hl,de
    ld a,(hl)
    cp LD_P1021_REL_ABS16
    jr nz,ld_p1021_rel_bad
    inc hl
    ld a,(hl)
    or a
    jr nz,ld_p1021_rel_bad

    ld a,(ld_p1021_have_prev)
    or a
    jr z,ld_p1021_rel_store
    ld hl,(ld_p1021_prev)
    inc hl
    inc hl
    ld de,(ld_p1021_cur_off)
    or a
    sbc hl,de
    jr c,ld_p1021_rel_store
    jr z,ld_p1021_rel_store
    jr ld_p1021_rel_bad
ld_p1021_rel_store:
    ld hl,(ld_p1021_cur_off)
    ld (ld_p1021_prev),hl
    ld a,1
    ld (ld_p1021_have_prev),a
    ld hl,(ld_p1021_rel_cur)
    ld de,LD_P1021_RELOC_SIZE
    add hl,de
    ld (ld_p1021_rel_cur),hl
    ld hl,(ld_p1021_left)
    dec hl
    ld (ld_p1021_left),hl
    jr ld_p1021_rel_loop
ld_p1021_rel_bad:
    scf
    ret
ld_p1021_rel_ok:
    xor a
    ret

ld_p1021_mul_small:
    ld hl,0
    ld b,a
ld_p1021_mul_loop:
    ld a,b
    or a
    ret z
    add hl,de
    ret c
    djnz ld_p1021_mul_loop
    xor a
    ret

ld_p1021_bound:
    push hl
    push de
    ld de,$8001
    or a
    sbc hl,de
    pop de
    pop hl
    ccf
    ret

ld_p1021_crc16:
    ld de,$FFFF
ld_p1021_crc_byte:
    ld a,b
    or c
    ret z
    ld a,(hl)
    xor d
    ld d,a
    inc hl
    push bc
    ld b,8
ld_p1021_crc_bit:
    sla e
    rl d
    jr nc,ld_p1021_crc_no_poly
    ld a,d
    xor $10
    ld d,a
    ld a,e
    xor $21
    ld e,a
ld_p1021_crc_no_poly:
    djnz ld_p1021_crc_bit
    pop bc
    dec bc
    jr ld_p1021_crc_byte

ld_p1021_val_bad:
ld_p1021_format:
    ld a,E_FORMAT
    scf
    ret

ld_p1021_path:       dw 0
ld_p1021_buffer:     dw 0
ld_p1021_capacity:   dw 0
ld_p1021_used:       dw 0
ld_p1021_handle:     db 0
ld_p1021_open:       db 0
ld_p1021_errno:      db 0
ld_p1021_probe:      db 0
ld_p1021_stat_req:   defs 4,0
ld_p1021_stat_out:   defs 10,0
ld_p1021_obj:        dw 0
ld_p1021_length:     dw 0
ld_p1021_text:       dw 0
ld_p1021_bss:        dw 0
ld_p1021_sc:         dw 0
ld_p1021_rc:         dw 0
ld_p1021_so:         dw 0
ld_p1021_ro:         dw 0
ld_p1021_sym_bytes:  dw 0
ld_p1021_rel_bytes:  dw 0
ld_p1021_sym_start:  dw 0
ld_p1021_sym_cur:    dw 0
ld_p1021_rel_cur:    dw 0
ld_p1021_scan:       dw 0
ld_p1021_left:       dw 0
ld_p1021_record:     dw 0
ld_p1021_value:      dw 0
ld_p1021_section:    db 0
ld_p1021_flags:      db 0
ld_p1021_prev:       dw 0
ld_p1021_cur_off:    dw 0
ld_p1021_have_prev:  db 0
ld_p1021_header_copy: defs LD_P1021_HEADER_SIZE,0
    ENDM
