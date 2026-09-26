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
; P11.25 thin C48 graphics/console wrappers. Every visible operation crosses
; only the frozen ZX-UX console/graphics syscall boundary; IY is untouched.

    MACRO EMIT_P1125_C48_GRAPHICS_RUNTIME
c48_gfx_draw1:       defs 4,0
c48_gfx_circle1:     defs 3,0
c48_gfx_print_ptr:   dw 0
c48_gfx_print_len:   dw 0

c48_gfx_errno:
    ld l,a
    ld h,0
    or a
    ret
c48_gfx_zero:
    ld hl,0
    xor a
    ret
c48_gfx_invalid:
    ld hl,E_INVAL
    xor a
    ret

cls:
    ld a,SYS_CON_CLEAR
    call SYSCALL_GATEWAY
    jp c,c48_gfx_errno
    jp c48_gfx_zero

; HL=row, DE=col, BC=NUL text.
print_at:
    ld a,h
    or d
    jp nz,c48_gfx_invalid
    ld a,l
    cp 24
    jp nc,c48_gfx_invalid
    ld a,e
    cp 32
    jp nc,c48_gfx_invalid
    ld a,l
    ld h,a
    ld l,e
    push bc
    ld a,SYS_CON_SETPOS
    call SYSCALL_GATEWAY
    pop bc
    jp c,c48_gfx_errno
    ld h,b
    ld l,c
    ld (c48_gfx_print_ptr),hl
    ld de,0
c48_gfx_print_scan:
    ld a,(hl)
    or a
    jr z,c48_gfx_print_ready
    inc hl
    inc de
    jr c48_gfx_print_scan
c48_gfx_print_ready:
    ld (c48_gfx_print_len),de
    ld hl,(c48_gfx_print_ptr)
    ld bc,(c48_gfx_print_len)
    ld a,SYS_CON_WRITE
    call SYSCALL_GATEWAY
    jp c,c48_gfx_errno
    jp c48_gfx_zero

plot:
    ld a,h
    or d
    jp nz,c48_gfx_invalid
    ld h,l
    ld l,e
    ld a,SYS_GFX_PLOT
    call SYSCALL_GATEWAY
    jp c,c48_gfx_errno
    jp c48_gfx_zero

point:
    ld a,h
    or d
    jp nz,c48_gfx_invalid
    ld h,l
    ld l,e
    ld a,SYS_GFX_POINT
    call SYSCALL_GATEWAY
    jp c,c48_gfx_errno
    or a
    ret

; Fourth C48_REGCALL word is at SP+2.
draw:
    ld a,h
    or d
    or b
    jp nz,c48_gfx_invalid
    ld a,l
    ld (c48_gfx_draw1+0),a
    ld a,e
    ld (c48_gfx_draw1+1),a
    ld a,c
    ld (c48_gfx_draw1+2),a
    ld hl,2
    add hl,sp
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or a
    jp nz,c48_gfx_invalid
    ld a,e
    ld (c48_gfx_draw1+3),a
    ld hl,c48_gfx_draw1
    ld a,SYS_GFX_DRAW
    call SYSCALL_GATEWAY
    jp c,c48_gfx_errno
    jp c48_gfx_zero

circle:
    ld a,h
    or d
    or b
    jp nz,c48_gfx_invalid
    ld a,l
    ld (c48_gfx_circle1+0),a
    ld a,e
    ld (c48_gfx_circle1+1),a
    ld a,c
    ld (c48_gfx_circle1+2),a
    ld hl,c48_gfx_circle1
    ld a,SYS_GFX_CIRCLE
    call SYSCALL_GATEWAY
    jp c,c48_gfx_errno
    jp c48_gfx_zero

c48_gfx_attr_call:
    ld a,h
    or a
    jp nz,c48_gfx_invalid
    ld h,d
    ld a,SYS_GFX_ATTR
    call SYSCALL_GATEWAY
    jp c,c48_gfx_errno
    jp c48_gfx_zero

ink:
    ld d,0
    jp c48_gfx_attr_call
paper:
    ld d,1
    jp c48_gfx_attr_call
bright:
    ld d,2
    jp c48_gfx_attr_call
flash:
    ld d,3
    jp c48_gfx_attr_call
inverse:
    ld d,4
    jp c48_gfx_attr_call
over:
    ld d,5
    jp c48_gfx_attr_call

border:
    ld a,h
    or a
    jp nz,c48_gfx_invalid
    ld a,SYS_GFX_BORDER
    call SYSCALL_GATEWAY
    jp c,c48_gfx_errno
    jp c48_gfx_zero
    ENDM
