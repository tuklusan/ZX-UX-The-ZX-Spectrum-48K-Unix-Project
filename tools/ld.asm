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
