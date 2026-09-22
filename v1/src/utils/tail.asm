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
; /bin/tail: stream stdin once, then emit the last N text lines.
; The bounded 4096-byte staging arena fails closed with E_NOSPC if exhausted.

    MACRO EMIT_P811_TAIL_ROUTINES
tail_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr z,tail_default
    cp 2
    jp nz,tail_invalid
    ld de,8
    add ix,de
    call tail_next_arg
    push ix
    pop hl
    call tail_parse_n
    jp c,tail_invalid
    ld (tail_n),a
    jr tail_init
tail_default:
    ld a,10
    ld (tail_n),a
tail_init:
    ld hl,0
    ld (tail_count),hl

tail_read_loop:
    ld hl,(tail_count)
    ld a,h
    cp $10
    jr nz,tail_room
    ld a,l
    or a
    jp z,tail_nospc
tail_room:
    ld de,tail_buffer
    add hl,de
    push hl
    ld de,0
    pop hl
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,tail_error
    ld a,h
    or l
    jr z,tail_eof
    ld hl,(tail_count)
    inc hl
    ld (tail_count),hl
    jr tail_read_loop

tail_eof:
    ld hl,(tail_count)
    ld a,h
    or l
    jr z,tail_success
    dec hl
    ld de,tail_buffer
    add hl,de
    ld a,(hl)
    cp 10
    jr nz,tail_scan_setup
    ; Final LF terminates the last line and is not a preceding boundary.
    ld de,tail_buffer
    or a
    sbc hl,de
    ld a,h
    or l
    jr z,tail_emit_all
    ld de,tail_buffer
    add hl,de
    dec hl

tail_scan_setup:
    ld a,(tail_n)
    ld b,a
tail_scan:
    ld a,(hl)
    cp 10
    jr nz,tail_scan_prev
    djnz tail_scan_prev
    inc hl
    jr tail_emit_from_hl
tail_scan_prev:
    ld de,tail_buffer
    push hl
    or a
    sbc hl,de
    ld a,h
    or l
    pop hl
    jr z,tail_emit_all
    dec hl
    jr tail_scan

tail_emit_all:
    ld hl,tail_buffer
tail_emit_from_hl:
    ld (tail_start),hl
    ld de,tail_buffer
    or a
    sbc hl,de
    ex de,hl
    ld hl,(tail_count)
    or a
    sbc hl,de
    ld b,h
    ld c,l
    ld hl,(tail_start)
    call tail_write_all
    jp c,tail_error
tail_success:
    ld l,0
    jr tail_exit

tail_invalid:
    ld a,E_INVAL
    jr tail_error
tail_nospc:
    ld a,E_NOSPC
tail_error:
    ld l,a
tail_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

tail_parse_n:
    ld a,(hl)
    or a
    jr z,tail_parse_bad
    ld b,0
tail_parse_loop:
    ld a,(hl)
    or a
    jr z,tail_parse_done
    cp '0'
    jr c,tail_parse_bad
    cp '9'+1
    jr nc,tail_parse_bad
    sub '0'
    ld c,a
    ld a,b
    cp 26
    jr nc,tail_parse_bad
    add a,a
    ld d,a
    add a,a
    add a,a
    add a,d
    add a,c
    ld b,a
    inc hl
    jr tail_parse_loop
tail_parse_done:
    ld a,b
    or a
    jr z,tail_parse_bad
    or a
    ret
tail_parse_bad:
    scf
    ret

tail_write_all:
    ld (tail_write_ptr),hl
    ld (tail_write_left),bc
tail_write_loop:
    ld hl,(tail_write_ptr)
    ld bc,(tail_write_left)
    ld a,b
    or c
    ret z
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,tail_write_zero
    ld (tail_written),hl
    ld de,(tail_write_ptr)
    add hl,de
    ld (tail_write_ptr),hl
    ld hl,(tail_write_left)
    ld de,(tail_written)
    or a
    sbc hl,de
    jr c,tail_write_zero
    ld (tail_write_left),hl
    jr tail_write_loop
tail_write_zero:
    ld a,E_IO
    scf
    ret

tail_next_arg:
tail_next_loop:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,tail_next_loop
    ret

tail_n: db 0
tail_count: dw 0
tail_start: dw 0
tail_write_ptr: dw 0
tail_write_left: dw 0
tail_written: dw 0
tail_buffer: defs 4096,0
tail_end:
    ENDM
