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
; /bin/head: emit the first N text lines from stdin, default N=10.

    MACRO EMIT_P810_HEAD_ROUTINES
head_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr z,head_default
    cp 2
    jp nz,head_invalid
    ld de,8
    add ix,de
    call head_next_arg
    push ix
    pop hl
    call head_parse_n
    jp c,head_invalid
    ld (head_remaining),a
    jr head_loop
head_default:
    ld a,10
    ld (head_remaining),a

head_loop:
    ld a,(head_remaining)
    or a
    jr z,head_success
    ld de,0
    ld hl,head_byte
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,head_error
    ld a,h
    or l
    jr z,head_success
    ld hl,head_byte
    ld bc,1
    call head_write_all
    jp c,head_error
    ld a,(head_byte)
    cp 10
    jr nz,head_loop
    ld a,(head_remaining)
    dec a
    ld (head_remaining),a
    jr head_loop

head_success:
    ld l,0
    jr head_exit
head_invalid:
    ld a,E_INVAL
head_error:
    ld l,a
head_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

head_parse_n:
    ld a,(hl)
    or a
    jr z,head_parse_bad
    ld b,0
head_parse_loop:
    ld a,(hl)
    or a
    jr z,head_parse_done
    cp '0'
    jr c,head_parse_bad
    cp '9'+1
    jr nc,head_parse_bad
    sub '0'
    ld c,a
    ld a,b
    cp 26
    jr nc,head_parse_maybe_overflow
head_parse_accum:
    add a,a
    ld d,a
    add a,a
    add a,a
    add a,d
    add a,c
    ld b,a
    inc hl
    jr head_parse_loop
head_parse_maybe_overflow:
    ; Any prior value >=26 followed by a digit exceeds 255.
    jr head_parse_bad
head_parse_done:
    ld a,b
    or a
    jr z,head_parse_bad
    or a
    ret
head_parse_bad:
    scf
    ret

head_write_all:
    ld (head_write_ptr),hl
    ld (head_write_left),bc
head_write_loop:
    ld hl,(head_write_ptr)
    ld bc,(head_write_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,head_write_zero
    ld (head_written),hl
    ld de,(head_write_ptr)
    add hl,de
    ld (head_write_ptr),hl
    ld hl,(head_write_left)
    ld de,(head_written)
    or a
    sbc hl,de
    jr c,head_write_zero
    ld (head_write_left),hl
    ld a,h
    or l
    jr nz,head_write_loop
    xor a
    ret
head_write_zero:
    ld a,E_IO
    scf
    ret

head_next_arg:
head_next_loop:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,head_next_loop
    ret

head_remaining: db 0
head_byte: db 0
head_write_ptr: dw 0
head_write_left: dw 0
head_written: dw 0
head_end:
    ENDM
