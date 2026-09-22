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

; P8.31 exact qualification source.
    MACRO EMIT_P831_UNAME_ROUTINES
uname_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr nz,uname_bad
    ld hl,uname_text
    ld bc,14
    call uname_write_all
    jr c,uname_exit_a
    xor a
    jr uname_exit_a
uname_bad:
    ld a,E_INVAL
uname_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
uname_write_all:
    ld (uname_ptr),hl
    ld (uname_left),bc
uname_write_loop:
    ld hl,(uname_ptr)
    ld bc,(uname_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,uname_io
    ld (uname_wrote),hl
    ld de,(uname_ptr)
    add hl,de
    ld (uname_ptr),hl
    ld hl,(uname_left)
    ld de,(uname_wrote)
    or a
    sbc hl,de
    jr c,uname_io
    ld (uname_left),hl
    ld a,h
    or l
    jr nz,uname_write_loop
    xor a
    ret
uname_io:
    ld a,E_IO
    scf
    ret
uname_text: db 'Z','X','-','U','X',' ','z','8','0',' ','4','8','k',10
uname_ptr: dw 0
uname_left: dw 0
uname_wrote: dw 0
    ENDM
