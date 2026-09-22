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
; P7.17 C48_REGCALL user-library 2x2 UDG helper.
; HL=base_slot, DE=row, BC=col. All four slots/cells are validated before the
; first SYS_UDG_DRAW. Returns HL=0 on success or the positive ZX-UX errno.

    MACRO EMIT_P717_UDG_LIB_ROUTINES
udg_draw_2x2:
    ld a,h
    or a
    jp nz,udg_draw_2x2_invalid
    ld a,d
    or a
    jp nz,udg_draw_2x2_invalid
    ld a,b
    or a
    jp nz,udg_draw_2x2_invalid

    ld a,l
    cp 29
    jp nc,udg_draw_2x2_invalid
    ld (udg2_base),a
    ld a,e
    cp 23
    jp nc,udg_draw_2x2_invalid
    ld (udg2_row),a
    ld a,c
    cp 31
    jp nc,udg_draw_2x2_invalid
    ld (udg2_col),a

    ; top-left: base+0,row,col
    ld a,(udg2_base)
    ld (udg2_record+0),a
    ld a,(udg2_row)
    ld (udg2_record+1),a
    ld a,(udg2_col)
    ld (udg2_record+2),a
    call udg_draw_2x2_one
    ret nz

    ; top-right: base+1,row,col+1
    ld a,(udg2_base)
    inc a
    ld (udg2_record+0),a
    ld a,(udg2_col)
    inc a
    ld (udg2_record+2),a
    call udg_draw_2x2_one
    ret nz

    ; bottom-left: base+2,row+1,col
    ld a,(udg2_base)
    add a,2
    ld (udg2_record+0),a
    ld a,(udg2_row)
    inc a
    ld (udg2_record+1),a
    ld a,(udg2_col)
    ld (udg2_record+2),a
    call udg_draw_2x2_one
    ret nz

    ; bottom-right: base+3,row+1,col+1
    ld a,(udg2_base)
    add a,3
    ld (udg2_record+0),a
    ld a,(udg2_col)
    inc a
    ld (udg2_record+2),a
    call udg_draw_2x2_one
    ret

udg_draw_2x2_one:
    ld hl,udg2_record
    ld a,SYS_UDG_DRAW
    call SYSCALL_GATEWAY
    jr c,udg_draw_2x2_errno
    ld hl,0
    xor a
    ret
udg_draw_2x2_errno:
    ld l,a
    ld h,0
    or a
    ret

udg_draw_2x2_invalid:
    ld hl,E_INVAL
    ld a,l
    or a
    ret

udg2_base: db 0
udg2_row: db 0
udg2_col: db 0
udg2_record: defs 3,0
    ENDM
