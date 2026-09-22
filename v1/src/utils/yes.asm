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

    MACRO EMIT_P835_YES_ROUTINES
yes_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr z,yes_default
    cp 2
    jp nz,yes_bad
    ld de,8
    add ix,de
yes_skip0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,yes_skip0
    push ix
    pop hl
    ld (yes_text),hl
    ld bc,0
yes_count:
    ld a,(hl)
    or a
    jr z,yes_count_done
    inc hl
    inc bc
    jr yes_count
yes_count_done:
    ld (yes_len),bc
    jr yes_loop
yes_default:
    ld hl,yes_y
    ld (yes_text),hl
    ld bc,1
    ld (yes_len),bc
yes_loop:
    ld hl,(yes_text)
    ld bc,(yes_len)
    call yes_write_all
    jp c,yes_exit_a
    ld hl,yes_lf
    ld bc,1
    call yes_write_all
    jp c,yes_exit_a
    ld a,SYS_YIELD
    call SYSCALL_GATEWAY
    jp c,yes_exit_a
    jr yes_loop
yes_bad:
    ld a,E_INVAL
yes_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

yes_write_all:
    ld (yes_ptr),hl
    ld (yes_left),bc
yes_write_loop:
    ld hl,(yes_ptr)
    ld bc,(yes_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,yes_io
    ld (yes_wrote),hl
    ld de,(yes_ptr)
    add hl,de
    ld (yes_ptr),hl
    ld hl,(yes_left)
    ld de,(yes_wrote)
    or a
    sbc hl,de
    jr c,yes_io
    ld (yes_left),hl
    ld a,h
    or l
    jr nz,yes_write_loop
    xor a
    ret
yes_io:
    ld a,E_IO
    scf
    ret

yes_y: db 'y'
yes_lf: db 10
yes_text: dw 0
yes_len: dw 0
yes_ptr: dw 0
yes_left: dw 0
yes_wrote: dw 0
    ENDM
