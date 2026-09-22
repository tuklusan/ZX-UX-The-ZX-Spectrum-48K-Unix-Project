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
; /bin/rev: reverse bytes within each LF-delimited input line.
; Bounded line buffering is used; the whole input is never buffered.

    MACRO EMIT_P834_REV_ROUTINES
rev_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr nz,rev_bad
    xor a
    ld (rev_len),a

rev_read_loop:
    ld de,0
    ld hl,rev_byte
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,rev_exit_a
    ld a,h
    or l
    jr z,rev_eof
    ld a,(rev_byte)
    cp 10
    jr z,rev_emit_line
    ld a,(rev_len)
    cp 255
    jr z,rev_too_long
    ld e,a
    ld d,0
    ld hl,rev_buffer
    add hl,de
    ld a,(rev_byte)
    ld (hl),a
    ld a,(rev_len)
    inc a
    ld (rev_len),a
    jr rev_read_loop

rev_emit_line:
    ld a,(rev_len)
    or a
    jr z,rev_emit_lf
    ld b,a
rev_reverse_loop:
    dec b
    ld e,b
    ld d,0
    ld hl,rev_buffer
    add hl,de
    ld bc,1
    call rev_write_all
    jp c,rev_exit_a
    ld a,b
    or a
    jr nz,rev_reverse_loop
rev_emit_lf:
    ld hl,rev_lf
    ld bc,1
    call rev_write_all
    jp c,rev_exit_a
    xor a
    ld (rev_len),a
    jr rev_read_loop

rev_eof:
    ld a,(rev_len)
    or a
    jr z,rev_ok
    ld b,a
rev_eof_reverse:
    dec b
    ld e,b
    ld d,0
    ld hl,rev_buffer
    add hl,de
    ld bc,1
    call rev_write_all
    jp c,rev_exit_a
    ld a,b
    or a
    jr nz,rev_eof_reverse
rev_ok:
    xor a
    jr rev_exit_a
rev_too_long:
    ld a,E_TOOLONG
    jr rev_exit_a
rev_bad:
    ld a,E_INVAL
rev_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

rev_write_all:
    ld (rev_wptr),hl
    ld (rev_wleft),bc
rev_write_loop:
    ld hl,(rev_wptr)
    ld bc,(rev_wleft)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,rev_io
    ld (rev_wrote),hl
    ld de,(rev_wptr)
    add hl,de
    ld (rev_wptr),hl
    ld hl,(rev_wleft)
    ld de,(rev_wrote)
    or a
    sbc hl,de
    jr c,rev_io
    ld (rev_wleft),hl
    ld a,h
    or l
    jr nz,rev_write_loop
    xor a
    ret
rev_io:
    ld a,E_IO
    scf
    ret

rev_byte: db 0
rev_len: db 0
rev_lf: db 10
rev_wptr: dw 0
rev_wleft: dw 0
rev_wrote: dw 0
rev_buffer: defs 255,0
    ENDM
