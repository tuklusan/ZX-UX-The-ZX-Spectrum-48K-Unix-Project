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
; /bin/echo: external/pipelineable; arguments separated by one ASCII space and
; terminated by one LF. No arguments emits LF.

; P8.37 external echo regression anchor.
    MACRO EMIT_P616_ECHO_ROUTINES
echo_entry:
    push hl
    pop ix
    ld a,(ix+4)
    dec a
    ld de,8
    add ix,de

; Skip argv[0].
echo_skip_argv0:
    ld l,(ix+0)
    inc ix
    ld h,l
    ld l,a
    ld a,h
    or a
    ld a,l
    jr nz,echo_skip_argv0
    or a
    jr z,echo_newline

echo_arg_loop:
    push af
    push ix
    pop hl
    ld bc,0
echo_arg_count:
    ld a,(hl)
    or a
    jr z,echo_arg_write
    inc hl
    inc bc
    jr echo_arg_count

echo_arg_write:
    push bc
    push ix
    push ix
    pop hl
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    pop ix
    pop bc
    add ix,bc
    inc ix
    pop af
    dec a
    jr z,echo_newline

    push af
    push ix
    ld hl,$0020
    push hl
    ld hl,0
    add hl,sp
    ld bc,1
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    pop hl
    pop ix
    pop af
    jr echo_arg_loop

echo_newline:
    ld hl,$000a
    push hl
    ld hl,0
    add hl,sp
    ld bc,1
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    pop hl
    ld l,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
echo_end:
    ENDM
