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
    jp z,ld_p1021_format
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
    jp z,ld_p1021_probe_eof
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
    jp c,ld_p1021_stream_error
    ld a,h
    or l
    jp z,ld_p1021_read_eof
    ex de,hl
    ld hl,(ld_p1021_used)
    add hl,de
    jp c,ld_p1021_nospc_stream
    ld de,(ld_p1021_capacity)
    push hl
    or a
    sbc hl,de
    pop hl
    jp c,ld_p1021_read_store
    jp z,ld_p1021_read_store
    jp ld_p1021_nospc_stream
ld_p1021_read_store:
    ld (ld_p1021_used),hl
    jp ld_p1021_read_loop

; Exact-capacity candidate: probe one byte without writing beyond caller buffer.
ld_p1021_probe_eof:
    ld a,(ld_p1021_handle)
    ld e,a
    ld d,0
    ld hl,ld_p1021_probe
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,ld_p1021_stream_error
    ld a,h
    or l
    jp z,ld_p1021_read_eof
    jp ld_p1021_nospc_stream

ld_p1021_read_eof:
    call ld_p1021_close
    jp c,ld_p1021_stream_error_closed
    ld hl,(ld_p1021_buffer)
    ld bc,(ld_p1021_used)
    call ld_p1021_validate_memory
    ret c
    ld hl,(ld_p1021_used)
    ret

ld_p1021_nospc_stream:
    ld a,E_NOSPC
    jp ld_p1021_stream_error
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
    jp ld_p1021_stream_error
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
    jp z,ld_p1021_crc_body
    ld hl,(ld_p1021_text)
    ld a,h
    or a
    jp nz,ld_p1021_crc_body
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
    jp z,ld_p1021_sym_ok
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
    jp z,ld_p1021_sym_advance
    ld hl,(ld_p1021_scan)
    ld de,(ld_p1021_sym_cur)
    ld b,16
ld_p1021_dup_cmp:
    ld a,(de)
    cp (hl)
    jp nz,ld_p1021_dup_next
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
    jp ld_p1021_dup_loop
ld_p1021_sym_advance:
    ld hl,(ld_p1021_sym_cur)
    ld de,LD_P1021_SYMBOL_SIZE
    add hl,de
    ld (ld_p1021_sym_cur),hl
    ld hl,(ld_p1021_left)
    dec hl
    ld (ld_p1021_left),hl
    jp ld_p1021_sym_loop
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
    jp z,ld_p1021_name_zero
    ld a,c
    cp 15
    jp nc,ld_p1021_sym_bad
    ld a,c
    or a
    ld a,(hl)
    jp nz,ld_p1021_name_tail
    call ld_p1021_name_first
    jp c,ld_p1021_sym_bad
    jp ld_p1021_name_accept
ld_p1021_name_tail:
    call ld_p1021_name_next
    jp c,ld_p1021_sym_bad
ld_p1021_name_accept:
    inc c
    inc hl
    djnz ld_p1021_name_loop
    jp ld_p1021_sym_bad
ld_p1021_name_zero:
    ld a,c
    or a
    jp z,ld_p1021_sym_bad
ld_p1021_zero_tail:
    ld a,(hl)
    or a
    jp nz,ld_p1021_sym_bad
    inc hl
    djnz ld_p1021_zero_tail

    ld hl,(ld_p1021_record)
    ld de,18
    add hl,de
    ld a,(hl)
    cp 4
    jp nc,ld_p1021_sym_bad
    ld (ld_p1021_section),a
    inc hl
    ld a,(hl)
    and $FE
    jp nz,ld_p1021_sym_bad
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
    jp z,ld_p1021_sym_undef
    cp 1
    jp z,ld_p1021_sym_text
    cp 2
    jp z,ld_p1021_sym_bss
    xor a
    ret
ld_p1021_sym_undef:
    ld hl,(ld_p1021_value)
    ld a,h
    or l
    jp nz,ld_p1021_sym_bad
    ld a,(ld_p1021_flags)
    cp 1
    jp nz,ld_p1021_sym_bad
    xor a
    ret
ld_p1021_sym_text:
    ld hl,(ld_p1021_value)
    ld de,(ld_p1021_text)
    or a
    sbc hl,de
    jp c,ld_p1021_sym_good
    jp z,ld_p1021_sym_good
    jp ld_p1021_sym_bad
ld_p1021_sym_bss:
    ld hl,(ld_p1021_value)
    ld de,(ld_p1021_bss)
    or a
    sbc hl,de
    jp c,ld_p1021_sym_good
    jp z,ld_p1021_sym_good
ld_p1021_sym_bad:
    scf
    ret
ld_p1021_sym_good:
    xor a
    ret

ld_p1021_name_first:
    cp 'A'
    jp c,ld_p1021_name_punct
    cp 'Z'+1
    jp c,ld_p1021_name_good
    cp 'a'
    jp c,ld_p1021_name_punct
    cp 'z'+1
    jp c,ld_p1021_name_good
ld_p1021_name_punct:
    cp '_'
    jp z,ld_p1021_name_good
    cp '.'
    jp z,ld_p1021_name_good
    cp '$'
    jp z,ld_p1021_name_good
    scf
    ret
ld_p1021_name_next:
    cp '0'
    jp c,ld_p1021_name_first
    cp '9'+1
    jp c,ld_p1021_name_good
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
    jp z,ld_p1021_rel_ok
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
    jp c,ld_p1021_rel_bad

    ld hl,(ld_p1021_rel_cur)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(ld_p1021_sc)
    or a
    sbc hl,de
    jp z,ld_p1021_rel_bad
    jp c,ld_p1021_rel_bad

    ld hl,(ld_p1021_rel_cur)
    ld de,4
    add hl,de
    ld a,(hl)
    cp LD_P1021_REL_ABS16
    jp nz,ld_p1021_rel_bad
    inc hl
    ld a,(hl)
    or a
    jp nz,ld_p1021_rel_bad

    ld a,(ld_p1021_have_prev)
    or a
    jp z,ld_p1021_rel_store
    ld hl,(ld_p1021_prev)
    inc hl
    inc hl
    ld de,(ld_p1021_cur_off)
    or a
    sbc hl,de
    jp c,ld_p1021_rel_store
    jp z,ld_p1021_rel_store
    jp ld_p1021_rel_bad
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
    jp ld_p1021_rel_loop
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
    jp nc,ld_p1021_crc_no_poly
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
    jp ld_p1021_crc_byte

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

; P10.23 built-in archive fixed-point selection.
; Runtime member order is frozen as write(1), puts(2), exit(3). This compact
; selector state is the native linker's unresolved-set engine for that archive:
; selecting puts introduces write after write's slot has already been scanned,
; forcing another fixed-order pass. Reserved heap globals are satisfiable
; without selecting an archive member.
    MACRO EMIT_P10_LD_ARCHIVE_SELECT_ROUTINES
LD_P1023_NEED_WRITE      EQU 1
LD_P1023_NEED_PUTS       EQU 2
LD_P1023_NEED_EXIT       EQU 4
LD_P1023_NEED_HEAP_START EQU 8
LD_P1023_NEED_HEAP_END   EQU 16
LD_P1023_NEED_OTHER      EQU 32

ld_p1023_select:
    ld (ld_p1023_need),a
    xor a
    ld (ld_p1023_selected_mask),a
    ld (ld_p1023_selected_count),a
    call ld_p1023_validate_order
    ret c
ld_p1023_fixed_point:
    xor a
    ld (ld_p1023_changed),a
    call ld_p1023_scan_write
    call ld_p1023_scan_puts
    call ld_p1023_scan_exit
    ld a,(ld_p1023_changed)
    or a
    jp nz,ld_p1023_fixed_point

    ; Only the two linker-defined heap globals are satisfiable without a member.
    ld a,(ld_p1023_need)
    and ~(LD_P1023_NEED_HEAP_START|LD_P1023_NEED_HEAP_END)
    ld (ld_p1023_need),a
    or a
    jp nz,ld_p1023_unresolved
    xor a
    ret

; One frozen-order scan, exposed only for the negative qualification oracle.
ld_p1023_select_one_pass:
    ld (ld_p1023_need),a
    xor a
    ld (ld_p1023_selected_mask),a
    ld (ld_p1023_selected_count),a
    call ld_p1023_validate_order
    ret c
    xor a
    ld (ld_p1023_changed),a
    call ld_p1023_scan_write
    call ld_p1023_scan_puts
    call ld_p1023_scan_exit
    xor a
    ret

ld_p1023_validate_order:
    ld a,(ld_p1023_member_order+0)
    cp 1
    jp nz,ld_p1023_format
    ld a,(ld_p1023_member_order+1)
    cp 2
    jp nz,ld_p1023_format
    ld a,(ld_p1023_member_order+2)
    cp 3
    jp nz,ld_p1023_format
    xor a
    ret

ld_p1023_scan_write:
    ld a,(ld_p1023_selected_mask)
    bit 0,a
    ret nz
    ld a,(ld_p1023_need)
    bit 0,a
    ret z
    res 0,a
    ld (ld_p1023_need),a
    ld a,1
    call ld_p1023_append
    ld a,(ld_p1023_selected_mask)
    set 0,a
    ld (ld_p1023_selected_mask),a
    ld a,1
    ld (ld_p1023_changed),a
    ret

ld_p1023_scan_puts:
    ld a,(ld_p1023_selected_mask)
    bit 1,a
    ret nz
    ld a,(ld_p1023_need)
    bit 1,a
    ret z
    res 1,a
    set 0,a                  ; puts imports write
    ld (ld_p1023_need),a
    ld a,2
    call ld_p1023_append
    ld a,(ld_p1023_selected_mask)
    set 1,a
    ld (ld_p1023_selected_mask),a
    ld a,1
    ld (ld_p1023_changed),a
    ret

ld_p1023_scan_exit:
    ld a,(ld_p1023_selected_mask)
    bit 2,a
    ret nz
    ld a,(ld_p1023_need)
    bit 2,a
    ret z
    res 2,a
    ld (ld_p1023_need),a
    ld a,3
    call ld_p1023_append
    ld a,(ld_p1023_selected_mask)
    set 2,a
    ld (ld_p1023_selected_mask),a
    ld a,1
    ld (ld_p1023_changed),a
    ret

ld_p1023_append:
    push af
    ld a,(ld_p1023_selected_count)
    cp 3
    jp nc,ld_p1023_append_overflow
    ld e,a
    ld d,0
    ld hl,ld_p1023_selected_order
    add hl,de
    pop af
    ld (hl),a
    ld a,(ld_p1023_selected_count)
    inc a
    ld (ld_p1023_selected_count),a
    xor a
    ret
ld_p1023_append_overflow:
    pop af
    jp ld_p1023_format

ld_p1023_unresolved:
    ld a,E_NOENT
    scf
    ret
ld_p1023_format:
    ld a,E_FORMAT
    scf
    ret

ld_p1023_member_order:   db 1,2,3
ld_p1023_need:           db 0
ld_p1023_selected_mask:  db 0
ld_p1023_selected_count: db 0
ld_p1023_selected_order: defs 3,0
ld_p1023_changed:        db 0
    ENDM

; P10.24 deterministic final module order, even layout, and zero-padding gates.
    MACRO EMIT_P10_LD_LAYOUT_ROUTINES
LD_P1024_MAX_MODULES EQU 8

; A=nostart (0 normal, nonzero development-only), HL=user ID bytes, B=user count,
; DE=selected archive ID bytes, C=selected count. Output frozen order/count.
ld_p1024_build_order:
    ld (ld_p1024_user_ids),hl
    ld (ld_p1024_archive_ids),de
    ld a,b
    ld (ld_p1024_user_count),a
    ld a,c
    ld (ld_p1024_archive_count),a
    xor a
    ld (ld_p1024_order_count),a
    ; nostart flag is recovered from caller through the saved byte below.
    ; Caller stores it before entry using ld_p1024_nostart.
    ld a,(ld_p1024_nostart)
    or a
    jp nz,ld_p1024_order_users
    xor a                       ; crt0 ID is always zero and first
    call ld_p1024_order_append
    ret c
ld_p1024_order_users:
    xor a
    ld (ld_p1024_index),a
ld_p1024_order_user_loop:
    ld a,(ld_p1024_index)
    ld b,a
    ld a,(ld_p1024_user_count)
    cp b
    jp z,ld_p1024_order_archive_start
    ld hl,(ld_p1024_user_ids)
    ld e,b
    ld d,0
    add hl,de
    ld a,(hl)
    call ld_p1024_order_append
    ret c
    ld a,(ld_p1024_index)
    inc a
    ld (ld_p1024_index),a
    jp ld_p1024_order_user_loop
ld_p1024_order_archive_start:
    xor a
    ld (ld_p1024_index),a
ld_p1024_order_archive_loop:
    ld a,(ld_p1024_index)
    ld b,a
    ld a,(ld_p1024_archive_count)
    cp b
    jp z,ld_p1024_order_ok
    ld hl,(ld_p1024_archive_ids)
    ld e,b
    ld d,0
    add hl,de
    ld a,(hl)
    call ld_p1024_order_append
    ret c
    ld a,(ld_p1024_index)
    inc a
    ld (ld_p1024_index),a
    jp ld_p1024_order_archive_loop
ld_p1024_order_ok:
    xor a
    ret
ld_p1024_order_append:
    push af
    ld a,(ld_p1024_order_count)
    cp LD_P1024_MAX_MODULES
    jp nc,ld_p1024_order_overflow
    ld e,a
    ld d,0
    ld hl,ld_p1024_order
    add hl,de
    pop af
    ld (hl),a
    ld a,(ld_p1024_order_count)
    inc a
    ld (ld_p1024_order_count),a
    xor a
    ret
ld_p1024_order_overflow:
    pop af
    jp ld_p1024_format

; HL=table of count records {text_size dw,bss_size dw}, B=count, DE=heap bytes.
; Output TEXT/BSS bases, even image_size, even heap base, exact final_bss_size.
ld_p1024_layout:
    ld (ld_p1024_table),hl
    ld (ld_p1024_heap_size),de
    ld a,b
    cp LD_P1024_MAX_MODULES+1
    jp nc,ld_p1024_format
    ld (ld_p1024_count),a
    xor a
    ld (ld_p1024_index),a
    ld hl,0
    ld (ld_p1024_cursor),hl
ld_p1024_text_loop:
    ld a,(ld_p1024_index)
    ld b,a
    ld a,(ld_p1024_count)
    cp b
    jp z,ld_p1024_text_done
    ld hl,(ld_p1024_cursor)
    bit 0,l
    jp z,ld_p1024_text_aligned
    inc hl
    jp z,ld_p1024_nospc
ld_p1024_text_aligned:
    ld (ld_p1024_cursor),hl
    ld a,(ld_p1024_index)
    ld de,ld_p1024_text_bases
    call ld_p1024_store_indexed_word
    call ld_p1024_record_ptr
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(ld_p1024_cursor)
    add hl,de
    jp c,ld_p1024_nospc
    ld (ld_p1024_cursor),hl
    ld a,(ld_p1024_index)
    inc a
    ld (ld_p1024_index),a
    jp ld_p1024_text_loop
ld_p1024_text_done:
    ld hl,(ld_p1024_cursor)
    bit 0,l
    jp z,ld_p1024_text_final_even
    inc hl
    jp z,ld_p1024_nospc
ld_p1024_text_final_even:
    ld (ld_p1024_image_size),hl
    xor a
    ld (ld_p1024_index),a
    ld hl,0
    ld (ld_p1024_cursor),hl
ld_p1024_bss_loop:
    ld a,(ld_p1024_index)
    ld b,a
    ld a,(ld_p1024_count)
    cp b
    jp z,ld_p1024_bss_done
    ld hl,(ld_p1024_cursor)
    bit 0,l
    jp z,ld_p1024_bss_aligned
    inc hl
    jp z,ld_p1024_nospc
ld_p1024_bss_aligned:
    ld (ld_p1024_cursor),hl
    ld a,(ld_p1024_index)
    ld de,ld_p1024_bss_bases
    call ld_p1024_store_indexed_word
    call ld_p1024_record_ptr
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(ld_p1024_cursor)
    add hl,de
    jp c,ld_p1024_nospc
    ld (ld_p1024_cursor),hl
    ld a,(ld_p1024_index)
    inc a
    ld (ld_p1024_index),a
    jp ld_p1024_bss_loop
ld_p1024_bss_done:
    ld hl,(ld_p1024_cursor)
    bit 0,l
    jp z,ld_p1024_heap_even
    inc hl
    jp z,ld_p1024_nospc
ld_p1024_heap_even:
    ld (ld_p1024_heap_base),hl
    ld de,(ld_p1024_heap_size)
    add hl,de
    jp c,ld_p1024_nospc
    ld (ld_p1024_final_bss),hl

    ld de,(ld_p1024_image_size)
    add hl,de
    jp c,ld_p1024_nospc
    ld de,$8001
    or a
    sbc hl,de
    jp nc,ld_p1024_nospc
    xor a
    ret

ld_p1024_record_ptr:
    ld a,(ld_p1024_index)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld de,(ld_p1024_table)
    add hl,de
    ret

; A=index, HL=value, DE=word-array base. Restores HL=value.
ld_p1024_store_indexed_word:
    push hl
    ld l,a
    ld h,0
    add hl,hl
    add hl,de
    pop de
    ld (hl),e
    inc hl
    ld (hl),d
    ex de,hl
    ret

; HL=image, DE=list of u16 padding offsets, B=count. Every named pad byte is zero.
ld_p1024_check_zero_offsets:
    ld (ld_p1024_pad_image),hl
    ld (ld_p1024_pad_list),de
    ld a,b
    ld (ld_p1024_pad_count),a
    xor a
    ld (ld_p1024_index),a
ld_p1024_pad_loop:
    ld a,(ld_p1024_index)
    ld b,a
    ld a,(ld_p1024_pad_count)
    cp b
    jp z,ld_p1024_pad_ok
    ld hl,(ld_p1024_pad_list)
    ld a,(ld_p1024_index)
    add a,a
    ld e,a
    ld d,0
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(ld_p1024_pad_image)
    add hl,de
    ld a,(hl)
    or a
    jp nz,ld_p1024_format
    ld a,(ld_p1024_index)
    inc a
    ld (ld_p1024_index),a
    jp ld_p1024_pad_loop
ld_p1024_pad_ok:
    xor a
    ret

ld_p1024_nospc:
    ld a,E_NOSPC
    scf
    ret
ld_p1024_format:
    ld a,E_FORMAT
    scf
    ret

ld_p1024_nostart:       db 0
ld_p1024_user_ids:      dw 0
ld_p1024_user_count:    db 0
ld_p1024_archive_ids:   dw 0
ld_p1024_archive_count: db 0
ld_p1024_order_count:   db 0
ld_p1024_order:         defs LD_P1024_MAX_MODULES,0
ld_p1024_table:         dw 0
ld_p1024_count:         db 0
ld_p1024_index:         db 0
ld_p1024_cursor:        dw 0
ld_p1024_heap_size:     dw 0
ld_p1024_image_size:    dw 0
ld_p1024_heap_base:     dw 0
ld_p1024_final_bss:     dw 0
ld_p1024_text_bases:    defs LD_P1024_MAX_MODULES*2,0
ld_p1024_bss_bases:     defs LD_P1024_MAX_MODULES*2,0
ld_p1024_pad_image:     dw 0
ld_p1024_pad_list:      dw 0
ld_p1024_pad_count:     db 0
    ENDM


; P10.25 case-sensitive global resolution and exact final symbol formulas.
; Defined-global records used by this resolver are 23 bytes:
; name[16], OBJ1 value u16, section u8, module TEXT base u16, module BSS base u16.
    MACRO EMIT_P10_LD_SYMBOL_RESOLVE_ROUTINES
LD_P1025_DEF_SIZE EQU 23

; HL=query name[16], DE=defined-global table, B=count.
; ld_p1025_image_size must contain the final even image size.
; Success publishes exact section/value. Unresolved and duplicate globals are hard errors.
ld_p1025_resolve:
    ld (ld_p1025_query),hl
    ld (ld_p1025_defs),de
    ld a,b
    ld (ld_p1025_count),a
    call ld_p1025_validate_unique
    ret c
    xor a
    ld (ld_p1025_index),a
    ld (ld_p1025_matched),a
ld_p1025_resolve_loop:
    ld a,(ld_p1025_index)
    ld c,a
    ld a,(ld_p1025_count)
    cp c
    jp z,ld_p1025_resolve_done
    ld a,c
    call ld_p1025_record_ptr
    ld (ld_p1025_record),hl
    ex de,hl
    ld hl,(ld_p1025_query)
    call ld_p1025_name_equal
    jp nz,ld_p1025_resolve_next
    ld a,(ld_p1025_matched)
    or a
    jp nz,ld_p1025_duplicate
    ld a,1
    ld (ld_p1025_matched),a
    call ld_p1025_compute_record_value
    ret c
ld_p1025_resolve_next:
    ld a,(ld_p1025_index)
    inc a
    ld (ld_p1025_index),a
    jp ld_p1025_resolve_loop
ld_p1025_resolve_done:
    ld a,(ld_p1025_matched)
    or a
    jp z,ld_p1025_unresolved
    xor a
    ret

; Reject any duplicate defined global, even when it is not the queried symbol.
ld_p1025_validate_unique:
    xor a
    ld (ld_p1025_i),a
ld_p1025_unique_i:
    ld a,(ld_p1025_i)
    ld c,a
    ld a,(ld_p1025_count)
    cp c
    jp z,ld_p1025_unique_ok
    ld a,c
    inc a
    ld (ld_p1025_j),a
ld_p1025_unique_j:
    ld a,(ld_p1025_j)
    ld c,a
    ld a,(ld_p1025_count)
    cp c
    jp z,ld_p1025_unique_next_i
    ld a,(ld_p1025_i)
    call ld_p1025_record_ptr
    push hl
    ld a,(ld_p1025_j)
    call ld_p1025_record_ptr
    ex de,hl
    pop hl
    call ld_p1025_name_equal
    jp z,ld_p1025_duplicate
    ld a,(ld_p1025_j)
    inc a
    ld (ld_p1025_j),a
    jp ld_p1025_unique_j
ld_p1025_unique_next_i:
    ld a,(ld_p1025_i)
    inc a
    ld (ld_p1025_i),a
    jp ld_p1025_unique_i
ld_p1025_unique_ok:
    xor a
    ret

; HL/DE each point at one exact 16-byte OBJ1 name field. Case is significant.
ld_p1025_name_equal:
    ld b,16
ld_p1025_name_loop:
    ld a,(de)
    cp (hl)
    jp nz,ld_p1025_name_not_equal
    inc hl
    inc de
    djnz ld_p1025_name_loop
    xor a
    ret
ld_p1025_name_not_equal:
    ld a,1
    or a
    ret

; A=index -> HL=record pointer.
ld_p1025_record_ptr:
    ld b,a
    ld hl,0
    ld de,LD_P1025_DEF_SIZE
ld_p1025_record_mul:
    ld a,b
    or a
    jp z,ld_p1025_record_add
    add hl,de
    djnz ld_p1025_record_mul
ld_p1025_record_add:
    ld de,(ld_p1025_defs)
    add hl,de
    ret

; Compute the frozen final formula for ld_p1025_record.
ld_p1025_compute_record_value:
    ld hl,(ld_p1025_record)
    ld de,16
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (ld_p1025_obj_value),de
    inc hl
    ld a,(hl)
    ld (ld_p1025_resolved_section),a
    cp 1
    jp z,ld_p1025_value_text
    cp 2
    jp z,ld_p1025_value_bss
    cp 3
    jp z,ld_p1025_value_abs
    jp ld_p1025_format

; TEXT = module_text_base + OBJ1 value.
ld_p1025_value_text:
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(ld_p1025_obj_value)
    add hl,de
    jp c,ld_p1025_range
    ld (ld_p1025_resolved_value),hl
    xor a
    ret

; BSS = image_size + module_bss_base + OBJ1 value.
ld_p1025_value_bss:
    inc hl
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(ld_p1025_obj_value)
    add hl,de
    jp c,ld_p1025_range
    ld de,(ld_p1025_image_size)
    add hl,de
    jp c,ld_p1025_range
    ld (ld_p1025_resolved_value),hl
    xor a
    ret

; ABS = OBJ1 value.
ld_p1025_value_abs:
    ld hl,(ld_p1025_obj_value)
    ld (ld_p1025_resolved_value),hl
    xor a
    ret

ld_p1025_unresolved:
    ld a,E_NOENT
    scf
    ret
ld_p1025_duplicate:
ld_p1025_format:
    ld a,E_FORMAT
    scf
    ret
ld_p1025_range:
    ld a,E_NOSPC
    scf
    ret

ld_p1025_query:            dw 0
ld_p1025_defs:             dw 0
ld_p1025_count:            db 0
ld_p1025_index:            db 0
ld_p1025_i:                db 0
ld_p1025_j:                db 0
ld_p1025_matched:          db 0
ld_p1025_record:           dw 0
ld_p1025_obj_value:        dw 0
ld_p1025_image_size:       dw 0
ld_p1025_resolved_value:   dw 0
ld_p1025_resolved_section: db 0
    ENDM


; P10.26 final OBJ1 relocation patching and deterministic MEX1 runtime table.
    MACRO EMIT_P10_LD_RELOCATION_ROUTINES
LD_P1026_MAX_RELOCS EQU 8

ld_p1026_reset:
    xor a
    ld (ld_p1026_rel_count),a
    ret

; State inputs: image/image_size, patch_loc, symbol_value, signed addend,
; symbol_section. Applies one ABS16 relocation in widened arithmetic.
ld_p1026_apply:
    call ld_p1026_validate_patch
    ret c
    ld hl,(ld_p1026_symbol_value)
    ld de,(ld_p1026_addend)
    bit 7,d
    jp nz,ld_p1026_add_negative
    add hl,de
    jp c,ld_p1026_arith
    jp ld_p1026_value_ready
ld_p1026_add_negative:
    ; magnitude = -signed(addend), then require symbol >= magnitude.
    ld a,e
    cpl
    ld e,a
    ld a,d
    cpl
    ld d,a
    inc de
    or a
    sbc hl,de
    jp c,ld_p1026_arith
ld_p1026_value_ready:
    ld (ld_p1026_value),hl
    ld de,(ld_p1026_patch_loc)
    ld hl,(ld_p1026_image)
    add hl,de
    ld de,(ld_p1026_value)
    ld (hl),e
    inc hl
    ld (hl),d

    ld a,(ld_p1026_symbol_section)
    cp 3
    jp z,ld_p1026_apply_ok       ; ABS: fixed absolute, no runtime relocation.
    cp 1
    jp z,ld_p1026_emit_runtime
    cp 2
    jp z,ld_p1026_emit_runtime
    jp ld_p1026_format

ld_p1026_emit_runtime:
    ld a,(ld_p1026_rel_count)
    cp LD_P1026_MAX_RELOCS
    jp nc,ld_p1026_format
    ld c,a
    add a,a
    ld e,a
    ld d,0
    ld hl,ld_p1026_rel_locs
    add hl,de
    ld de,(ld_p1026_patch_loc)
    ld (hl),e
    inc hl
    ld (hl),d
    ld a,c
    ld e,a
    ld d,0
    ld hl,ld_p1026_rel_sections
    add hl,de
    ld a,(ld_p1026_symbol_section)
    ld (hl),a
    ld a,(ld_p1026_rel_count)
    inc a
    ld (ld_p1026_rel_count),a
ld_p1026_apply_ok:
    xor a
    ret

ld_p1026_validate_patch:
    ld hl,(ld_p1026_patch_loc)
    inc hl
    ld a,h
    or l
    jp z,ld_p1026_format
    ld de,(ld_p1026_image_size)
    or a
    sbc hl,de
    jp nc,ld_p1026_format
    xor a
    ret

; Sort runtime relocation locations ascending with source-section metadata.
; Then require unique, non-overlapping, in-image locations and TEXT/BSS only.
ld_p1026_finalize:
    xor a
    ld (ld_p1026_i),a
ld_p1026_sort_i:
    ld a,(ld_p1026_i)
    ld c,a
    ld a,(ld_p1026_rel_count)
    cp c
    jp z,ld_p1026_validate_sorted
    ld a,c
    inc a
    ld (ld_p1026_j),a
ld_p1026_sort_j:
    ld a,(ld_p1026_j)
    ld c,a
    ld a,(ld_p1026_rel_count)
    cp c
    jp z,ld_p1026_sort_next_i
    ld a,(ld_p1026_i)
    call ld_p1026_get_loc
    ld (ld_p1026_left),hl
    ld a,(ld_p1026_j)
    call ld_p1026_get_loc
    ex de,hl
    ld hl,(ld_p1026_left)
    or a
    sbc hl,de
    jp c,ld_p1026_sort_j_next
    jp z,ld_p1026_sort_j_next
    call ld_p1026_swap_ij
ld_p1026_sort_j_next:
    ld a,(ld_p1026_j)
    inc a
    ld (ld_p1026_j),a
    jp ld_p1026_sort_j
ld_p1026_sort_next_i:
    ld a,(ld_p1026_i)
    inc a
    ld (ld_p1026_i),a
    jp ld_p1026_sort_i

ld_p1026_validate_sorted:
    xor a
    ld (ld_p1026_i),a
ld_p1026_validate_loop:
    ld a,(ld_p1026_i)
    ld c,a
    ld a,(ld_p1026_rel_count)
    cp c
    jp z,ld_p1026_finalize_ok
    ld a,c
    call ld_p1026_get_section
    cp 1
    jp z,ld_p1026_validate_loc
    cp 2
    jp nz,ld_p1026_format
ld_p1026_validate_loc:
    ld a,(ld_p1026_i)
    call ld_p1026_get_loc
    ld (ld_p1026_patch_loc),hl
    call ld_p1026_validate_patch
    ret c
    ld a,(ld_p1026_i)
    or a
    jp z,ld_p1026_validate_advance
    dec a
    call ld_p1026_get_loc
    inc hl
    inc hl
    ld de,(ld_p1026_patch_loc)
    or a
    sbc hl,de
    jp c,ld_p1026_validate_advance
    jp z,ld_p1026_validate_advance
    jp ld_p1026_format          ; duplicate or one-byte overlap is forbidden.
ld_p1026_validate_advance:
    ld a,(ld_p1026_i)
    inc a
    ld (ld_p1026_i),a
    jp ld_p1026_validate_loop
ld_p1026_finalize_ok:
    xor a
    ret

; A=index -> HL=runtime relocation location.
ld_p1026_get_loc:
    add a,a
    ld e,a
    ld d,0
    ld hl,ld_p1026_rel_locs
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ret

; A=index -> A=source section.
ld_p1026_get_section:
    ld e,a
    ld d,0
    ld hl,ld_p1026_rel_sections
    add hl,de
    ld a,(hl)
    ret

ld_p1026_swap_ij:
    ld a,(ld_p1026_i)
    add a,a
    ld e,a
    ld d,0
    ld hl,ld_p1026_rel_locs
    add hl,de
    ld (ld_p1026_ptr_i),hl
    ld a,(ld_p1026_j)
    add a,a
    ld e,a
    ld d,0
    ld hl,ld_p1026_rel_locs
    add hl,de
    ld (ld_p1026_ptr_j),hl
    ld hl,(ld_p1026_ptr_i)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (ld_p1026_word_i),de
    ld hl,(ld_p1026_ptr_j)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(ld_p1026_ptr_i)
    ld (hl),e
    inc hl
    ld (hl),d
    ld de,(ld_p1026_word_i)
    ld hl,(ld_p1026_ptr_j)
    ld (hl),e
    inc hl
    ld (hl),d

    ld a,(ld_p1026_i)
    call ld_p1026_get_section
    ld (ld_p1026_sec_i),a
    ld a,(ld_p1026_j)
    call ld_p1026_get_section
    ld c,a
    ld a,(ld_p1026_i)
    ld e,a
    ld d,0
    ld hl,ld_p1026_rel_sections
    add hl,de
    ld (hl),c
    ld a,(ld_p1026_j)
    ld e,a
    ld d,0
    ld hl,ld_p1026_rel_sections
    add hl,de
    ld a,(ld_p1026_sec_i)
    ld (hl),a
    ret

ld_p1026_arith:
ld_p1026_format:
    ld a,E_FORMAT
    scf
    ret

ld_p1026_image:          dw 0
ld_p1026_image_size:     dw 0
ld_p1026_patch_loc:      dw 0
ld_p1026_symbol_value:   dw 0
ld_p1026_addend:         dw 0
ld_p1026_symbol_section: db 0
ld_p1026_value:          dw 0
ld_p1026_rel_count:      db 0
ld_p1026_rel_locs:       defs LD_P1026_MAX_RELOCS*2,0
ld_p1026_rel_sections:   defs LD_P1026_MAX_RELOCS,0
ld_p1026_i:              db 0
ld_p1026_j:              db 0
ld_p1026_left:           dw 0
ld_p1026_ptr_i:          dw 0
ld_p1026_ptr_j:          dw 0
ld_p1026_word_i:         dw 0
ld_p1026_sec_i:          db 0
    ENDM


; P10.27 normal-link default entry selection.
    MACRO EMIT_P10_LD_DEFAULT_ENTRY_ROUTINES
; DE=defined-global table, B=count. Uses the P10.25 resolver record format.
; Normal links always request exact case-sensitive "_start" and require TEXT.
ld_p1027_default_entry:
    ld hl,ld_p1027_start_name
    call ld_p1025_resolve
    ret c
    ld a,(ld_p1025_resolved_section)
    cp 1
    jp nz,ld_p1027_format
    ld hl,(ld_p1025_resolved_value)
    ld (ld_p1027_entry),hl
    xor a
    ret

ld_p1027_format:
    ld a,E_FORMAT
    scf
    ret

ld_p1027_start_name:
    db "_start",0,0,0,0,0,0,0,0,0,0
ld_p1027_entry: dw 0
    ENDM


; P10.28 development-only -nostart explicit-entry selection.
    MACRO EMIT_P10_LD_NOSTART_ENTRY_ROUTINES
; A=explicit -e present (nonzero), HL=exact case-sensitive symbol name[16],
; DE=defined-global table, B=count. There is deliberately no default under -nostart.
ld_p1028_nostart_entry:
    or a
    jp z,ld_p1028_format
    call ld_p1025_resolve
    ret c
    ld a,(ld_p1025_resolved_section)
    cp 1
    jp nz,ld_p1028_format
    ld hl,(ld_p1025_resolved_value)
    ld (ld_p1028_entry),hl
    xor a
    ret

ld_p1028_format:
    ld a,E_FORMAT
    scf
    ret

ld_p1028_entry: dw 0
    ENDM


; P10.29 linker-reserved heap symbols.
    MACRO EMIT_P10_LD_HEAP_SYMBOL_ROUTINES
LD_P1029_DEF_SIZE EQU 23

; DE=defined-global table, B=count. Exact reserved names may never be user-defined.
ld_p1029_reject_reserved_defs:
    ld (ld_p1029_defs),de
    ld a,b
    ld (ld_p1029_count),a
    xor a
    ld (ld_p1029_index),a
ld_p1029_scan:
    ld a,(ld_p1029_index)
    ld c,a
    ld a,(ld_p1029_count)
    cp c
    jp z,ld_p1029_scan_ok
    ld a,c
    call ld_p1029_record_ptr
    push hl
    ld de,ld_p1029_heap_start_name
    call ld_p1029_name_equal
    pop hl
    jp z,ld_p1029_reserved
    ld de,ld_p1029_heap_end_name
    call ld_p1029_name_equal
    jp z,ld_p1029_reserved
    ld a,(ld_p1029_index)
    inc a
    ld (ld_p1029_index),a
    jp ld_p1029_scan
ld_p1029_scan_ok:
    xor a
    ret

; HL=image_size, DE=heap base relative to BSS start, BC=heap size.
; The synthesized globals are final link-base-zero values.
ld_p1029_assign_heap:
    add hl,de
    jp c,ld_p1029_nospc
    ld (ld_p1029_heap_start),hl
    add hl,bc
    jp c,ld_p1029_nospc
    ld (ld_p1029_heap_end),hl
    xor a
    ret

ld_p1029_record_ptr:
    ld b,a
    ld hl,0
    ld de,LD_P1029_DEF_SIZE
ld_p1029_record_mul:
    ld a,b
    or a
    jp z,ld_p1029_record_add
    add hl,de
    djnz ld_p1029_record_mul
ld_p1029_record_add:
    ld de,(ld_p1029_defs)
    add hl,de
    ret

; HL/DE point at exact 16-byte names; case-sensitive.
ld_p1029_name_equal:
    ld b,16
ld_p1029_name_loop:
    ld a,(de)
    cp (hl)
    jp nz,ld_p1029_name_ne
    inc hl
    inc de
    djnz ld_p1029_name_loop
    xor a
    ret
ld_p1029_name_ne:
    ld a,1
    or a
    ret

ld_p1029_reserved:
    ld a,E_FORMAT
    scf
    ret
ld_p1029_nospc:
    ld a,E_NOSPC
    scf
    ret

ld_p1029_heap_start_name:
    db "__heap_start",0,0,0,0
ld_p1029_heap_end_name:
    db "__heap_end",0,0,0,0,0,0
ld_p1029_defs:       dw 0
ld_p1029_count:      db 0
ld_p1029_index:      db 0
ld_p1029_heap_start: dw 0
ld_p1029_heap_end:   dw 0
    ENDM


; P10.30 -stack option validation and MEX1 minimum FAST stack value.
    MACRO EMIT_P10_LD_STACK_OPTION_ROUTINES
LD_P1030_STACK_DEFAULT EQU 512
LD_P1030_STACK_MIN     EQU 64
LD_P1030_STACK_MAX     EQU 4096

; Reset to the frozen default.
ld_p1030_stack_default:
    ld hl,LD_P1030_STACK_DEFAULT
    ld (ld_p1030_min_fast_stack),hl
    xor a
    ret

; HL=requested byte count. Accept only even 64..4096 inclusive.
ld_p1030_stack_set:
    bit 0,l
    jp nz,ld_p1030_format
    push hl
    ld de,LD_P1030_STACK_MIN
    or a
    sbc hl,de
    pop hl
    jp c,ld_p1030_format
    push hl
    ld de,LD_P1030_STACK_MAX
    or a
    sbc hl,de
    pop hl
    jp c,ld_p1030_store
    jp z,ld_p1030_store
    jp ld_p1030_format
ld_p1030_store:
    ld (ld_p1030_min_fast_stack),hl
    xor a
    ret
ld_p1030_format:
    ld a,E_FORMAT
    scf
    ret

ld_p1030_min_fast_stack: dw LD_P1030_STACK_DEFAULT
    ENDM


; P10.31 -heap option/defaults, exact BSS heap placement, and allocation bound.
    MACRO EMIT_P10_LD_HEAP_OPTION_ROUTINES
LD_P1031_HEAP_NORMAL_DEFAULT  EQU 1024
LD_P1031_HEAP_NOSTART_DEFAULT EQU 0
LD_P1031_HEAP_MAX             EQU 8192

; A=nostart (0 normal, nonzero development-only). Stores frozen default.
ld_p1031_heap_default:
    or a
    jp nz,ld_p1031_default_nostart
    ld hl,LD_P1031_HEAP_NORMAL_DEFAULT
    jp ld_p1031_store_requested
ld_p1031_default_nostart:
    ld hl,LD_P1031_HEAP_NOSTART_DEFAULT
ld_p1031_store_requested:
    ld (ld_p1031_requested),hl
    xor a
    ret

; HL=explicit requested bytes. Accept only even 0..8192 inclusive.
ld_p1031_heap_set:
    bit 0,l
    jp nz,ld_p1031_format
    push hl
    ld de,LD_P1031_HEAP_MAX
    or a
    sbc hl,de
    pop hl
    jp c,ld_p1031_store_requested
    jp z,ld_p1031_store_requested
    jp ld_p1031_format

; HL=ASCII decimal, B=length. Negative/non-numeric/empty/overflow fail.
ld_p1031_heap_parse:
    ld a,b
    or a
    jp z,ld_p1031_format
    ld de,0
ld_p1031_parse_loop:
    ld a,(hl)
    cp '0'
    jp c,ld_p1031_format
    cp '9'+1
    jp nc,ld_p1031_format
    sub '0'
    ld c,a
    push hl
    push bc
    ex de,hl
    add hl,hl
    ld de,hl
    add hl,hl
    add hl,hl
    add hl,de
    jp c,ld_p1031_parse_overflow_pop
    ld e,c
    ld d,0
    add hl,de
    jp c,ld_p1031_parse_overflow_pop
    ld de,LD_P1031_HEAP_MAX
    push hl
    or a
    sbc hl,de
    pop hl
    jp nc,ld_p1031_parse_bound_check
ld_p1031_parse_accept:
    ex de,hl
    pop bc
    pop hl
    inc hl
    djnz ld_p1031_parse_loop
    ex de,hl
    jp ld_p1031_heap_set
ld_p1031_parse_bound_check:
    jp z,ld_p1031_parse_accept
ld_p1031_parse_overflow_pop:
    pop bc
    pop hl
    jp ld_p1031_format

; HL=image_size, DE=final raw module-BSS size, BC=requested heap bytes.
; Heap starts at next even BSS offset. MEX1 bss_size includes exact heap bytes.
ld_p1031_place:
    ld (ld_p1031_image_size),hl
    ld (ld_p1031_raw_bss),de
    ld h,b
    ld l,c
    call ld_p1031_heap_set
    ret c
    ld hl,(ld_p1031_raw_bss)
    bit 0,l
    jp z,ld_p1031_bss_even
    inc hl
    jp z,ld_p1031_nospc
ld_p1031_bss_even:
    ld (ld_p1031_heap_bss_offset),hl
    ld de,(ld_p1031_requested)
    add hl,de
    jp c,ld_p1031_nospc
    ld (ld_p1031_mex1_bss_size),hl

    ld de,(ld_p1031_image_size)
    add hl,de
    jp c,ld_p1031_nospc
    ld de,$8001
    or a
    sbc hl,de
    jp nc,ld_p1031_nospc

    ld hl,(ld_p1031_image_size)
    ld de,(ld_p1031_heap_bss_offset)
    add hl,de
    jp c,ld_p1031_nospc
    ld (ld_p1031_heap_start),hl
    ld de,(ld_p1031_requested)
    add hl,de
    jp c,ld_p1031_nospc
    ld (ld_p1031_heap_end),hl
    xor a
    ret

ld_p1031_nospc:
    ld a,E_NOSPC
    scf
    ret
ld_p1031_format:
    ld a,E_FORMAT
    scf
    ret

ld_p1031_requested:       dw 0
ld_p1031_image_size:      dw 0
ld_p1031_raw_bss:         dw 0
ld_p1031_heap_bss_offset: dw 0
ld_p1031_mex1_bss_size:   dw 0
ld_p1031_heap_start:      dw 0
ld_p1031_heap_end:        dw 0
    ENDM


; P10.32 deterministic final MEX1 memory writer.
    MACRO EMIT_P10_LD_MEX1_WRITER_ROUTINES
LD_P1032_HEADER_SIZE EQU 24
LD_P1032_MAX_STORED EQU 32768

; State inputs:
; image/image_size, bss_size, entry, stack, relocs/reloc_count, output/capacity.
; Success stores exact stored length and complete MEX1 bytes.
ld_p1032_write:
    call ld_p1032_validate
    ret c

    ld hl,(ld_p1032_output)
    ld (hl),'M'
    inc hl
    ld (hl),'E'
    inc hl
    ld (hl),'X'
    inc hl
    ld (hl),'1'
    inc hl
    ld (hl),1
    inc hl
    ld (hl),0
    inc hl
    ld (hl),LD_P1032_HEADER_SIZE
    inc hl
    ld (hl),0
    inc hl
    ld de,(ld_p1032_image_size)
    call ld_p1032_put_de
    ld de,(ld_p1032_bss_size)
    call ld_p1032_put_de
    ld de,(ld_p1032_entry)
    call ld_p1032_put_de
    ld de,(ld_p1032_stack)
    call ld_p1032_put_de
    ld de,(ld_p1032_reloc_count)
    call ld_p1032_put_de
    ld de,(ld_p1032_reloc_offset)
    call ld_p1032_put_de
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a

    ld hl,(ld_p1032_image)
    ld de,(ld_p1032_output)
    push hl
    ld hl,LD_P1032_HEADER_SIZE
    add hl,de
    ex de,hl
    pop hl
    ld bc,(ld_p1032_image_size)
    ldir

    ld hl,(ld_p1032_relocs)
    ld de,(ld_p1032_output)
    push hl
    ld hl,(ld_p1032_reloc_offset)
    add hl,de
    ex de,hl
    pop hl
    ld bc,(ld_p1032_reloc_bytes)
    ldir

    ; Body CRC covers image+relocation table.
    ld hl,(ld_p1032_output)
    ld de,LD_P1032_HEADER_SIZE
    add hl,de
    ld bc,(ld_p1032_stored_length)
    ld de,LD_P1032_HEADER_SIZE
    push hl
    ld h,b
    ld l,c
    or a
    sbc hl,de
    ld b,h
    ld c,l
    pop hl
    call ld_p1032_crc16
    ld hl,(ld_p1032_output)
    ld bc,20
    add hl,bc
    ld (hl),e
    inc hl
    ld (hl),d

    ; Header CRC is calculated with bytes 22..23 still zero.
    ld hl,(ld_p1032_output)
    ld bc,LD_P1032_HEADER_SIZE
    call ld_p1032_crc16
    ld hl,(ld_p1032_output)
    ld bc,22
    add hl,bc
    ld (hl),e
    inc hl
    ld (hl),d
    xor a
    ret

ld_p1032_put_de:
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ret

ld_p1032_validate:
    ld hl,(ld_p1032_image_size)
    ld a,h
    or l
    jp z,ld_p1032_format
    ld de,(ld_p1032_bss_size)
    add hl,de
    jp c,ld_p1032_format
    ld (ld_p1032_image_bss),hl
    ld de,$8001
    or a
    sbc hl,de
    jp nc,ld_p1032_format

    ld hl,(ld_p1032_entry)
    ld de,(ld_p1032_image_size)
    or a
    sbc hl,de
    jp nc,ld_p1032_format

    ld hl,(ld_p1032_stack)
    ld de,64
    or a
    sbc hl,de
    jp c,ld_p1032_format
    ld hl,(ld_p1032_stack)
    ld de,4096
    or a
    sbc hl,de
    jp c,ld_p1032_stack_ok
    jp z,ld_p1032_stack_ok
    jp ld_p1032_format
ld_p1032_stack_ok:

    ld hl,(ld_p1032_reloc_count)
    add hl,hl
    jp c,ld_p1032_format
    ld (ld_p1032_reloc_bytes),hl

    ld hl,(ld_p1032_image_size)
    ld de,LD_P1032_HEADER_SIZE
    add hl,de
    jp c,ld_p1032_format
    ld (ld_p1032_reloc_offset),hl
    ld de,(ld_p1032_reloc_bytes)
    add hl,de
    jp c,ld_p1032_format
    ld (ld_p1032_stored_length),hl
    ld de,LD_P1032_MAX_STORED+1
    or a
    sbc hl,de
    jp nc,ld_p1032_format

    ld hl,(ld_p1032_capacity)
    ld de,(ld_p1032_stored_length)
    or a
    sbc hl,de
    jp c,ld_p1032_nospc

    ld hl,(ld_p1032_reloc_count)
    ld a,h
    or l
    jp z,ld_p1032_valid
    ld hl,(ld_p1032_image_size)
    ld de,2
    or a
    sbc hl,de
    jp c,ld_p1032_format

    ld hl,(ld_p1032_relocs)
    ld (ld_p1032_rel_cur),hl
    ld hl,(ld_p1032_reloc_count)
    ld (ld_p1032_rel_left),hl
    xor a
    ld (ld_p1032_have_prev),a
ld_p1032_rel_loop:
    ld hl,(ld_p1032_rel_left)
    ld a,h
    or l
    jp z,ld_p1032_valid
    ld hl,(ld_p1032_rel_cur)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (ld_p1032_rel_value),de

    ld hl,(ld_p1032_image_size)
    dec hl
    dec hl
    or a
    sbc hl,de
    jp c,ld_p1032_format

    ld a,(ld_p1032_have_prev)
    or a
    jp z,ld_p1032_rel_word
    ld hl,(ld_p1032_prev)
    inc hl
    inc hl
    or a
    sbc hl,de
    jp nc,ld_p1032_format

ld_p1032_rel_word:
    ld hl,(ld_p1032_image)
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(ld_p1032_image_bss)
    or a
    sbc hl,de
    jp c,ld_p1032_format

    ld hl,(ld_p1032_rel_value)
    ld (ld_p1032_prev),hl
    ld a,1
    ld (ld_p1032_have_prev),a
    ld hl,(ld_p1032_rel_cur)
    inc hl
    inc hl
    ld (ld_p1032_rel_cur),hl
    ld hl,(ld_p1032_rel_left)
    dec hl
    ld (ld_p1032_rel_left),hl
    jp ld_p1032_rel_loop

ld_p1032_valid:
    xor a
    ret

ld_p1032_crc16:
    ld de,$FFFF
ld_p1032_crc_byte:
    ld a,b
    or c
    ret z
    ld a,(hl)
    xor d
    ld d,a
    inc hl
    push bc
    ld b,8
ld_p1032_crc_bit:
    sla e
    rl d
    jp nc,ld_p1032_crc_no_poly
    ld a,d
    xor $10
    ld d,a
    ld a,e
    xor $21
    ld e,a
ld_p1032_crc_no_poly:
    djnz ld_p1032_crc_bit
    pop bc
    dec bc
    jp ld_p1032_crc_byte

ld_p1032_nospc:
    ld a,E_NOSPC
    scf
    ret
ld_p1032_format:
    ld a,E_FORMAT
    scf
    ret

ld_p1032_image:         dw 0
ld_p1032_image_size:    dw 0
ld_p1032_bss_size:      dw 0
ld_p1032_entry:         dw 0
ld_p1032_stack:         dw 0
ld_p1032_relocs:        dw 0
ld_p1032_reloc_count:   dw 0
ld_p1032_output:        dw 0
ld_p1032_capacity:      dw 0
ld_p1032_reloc_bytes:   dw 0
ld_p1032_reloc_offset:  dw 0
ld_p1032_stored_length: dw 0
ld_p1032_image_bss:     dw 0
ld_p1032_rel_cur:       dw 0
ld_p1032_rel_left:      dw 0
ld_p1032_rel_value:     dw 0
ld_p1032_prev:          dw 0
ld_p1032_have_prev:     db 0
    ENDM
