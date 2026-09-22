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
; P8.22 graphics API demonstration as an ordinary external MEX1 utility.

    MACRO EMIT_P822_GFXDEMO_ROUTINES
gfxdemo_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr nz,gfxdemo_bad

    ld hl,$1010
    ld a,SYS_GFX_PLOT
    call SYSCALL_GATEWAY
    jr c,gfxdemo_exit_error

    ld hl,gfxdemo_line
    ld a,SYS_GFX_DRAW
    call SYSCALL_GATEWAY
    jr c,gfxdemo_exit_error

    ld hl,gfxdemo_circle
    ld a,SYS_GFX_CIRCLE
    call SYSCALL_GATEWAY
    jr c,gfxdemo_exit_error

    ld hl,$0004
    ld a,SYS_GFX_ATTR
    call SYSCALL_GATEWAY
    jr c,gfxdemo_exit_error

    ld hl,$0001
    ld a,SYS_GFX_BORDER
    call SYSCALL_GATEWAY
    jr c,gfxdemo_exit_error

    ld hl,$1010
    ld a,SYS_GFX_POINT
    call SYSCALL_GATEWAY
    jr c,gfxdemo_exit_error

    ld l,0
    jr gfxdemo_exit
gfxdemo_bad:
    ld l,E_INVAL
    jr gfxdemo_exit
gfxdemo_exit_error:
    ld l,a
gfxdemo_exit:
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

gfxdemo_line: db 8,8,40,24
gfxdemo_circle: db 64,48,12
    ENDM
