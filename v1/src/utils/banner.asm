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
; P8.33 renders one bounded ARG1 text argument through the shared pixel syscall.
; The Spectrum ROM 8x8 font at $3D00 supplies glyph bits for ASCII 32..127.

; P8.33 exact qualification source.
    MACRO EMIT_P833_BANNER_ROUTINES
banner_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 2
    jp nz,banner_bad
    ld de,8
    add ix,de
banner_skip_argv0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,banner_skip_argv0
    push ix
    pop hl
    ld (banner_text),hl
    ld b,0
banner_count:
    ld a,(hl)
    or a
    jr z,banner_count_done
    cp 32
    jp c,banner_bad
    cp 128
    jp nc,banner_bad
    inc hl
    inc b
    ld a,b
    cp 33
    jp nc,banner_long
    jr banner_count
banner_count_done:
    ld a,b
    or a
    jp z,banner_bad
    ld (banner_chars),a
    xor a
    ld (banner_index),a

banner_char_loop:
    ld a,(banner_index)
    ld b,a
    ld a,(banner_chars)
    cp b
    jp z,banner_ok
    ld hl,(banner_text)
    ld e,b
    ld d,0
    add hl,de
    ld a,(hl)
    sub 32
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,$3D00
    add hl,de
    ld (banner_glyph),hl
    xor a
    ld (banner_row),a

banner_row_loop:
    ld a,(banner_row)
    cp 8
    jr z,banner_next_char
    ld hl,(banner_glyph)
    ld e,a
    ld d,0
    add hl,de
    ld a,(hl)
    ld (banner_bits),a
    xor a
    ld (banner_bit),a
banner_bit_loop:
    ld a,(banner_bit)
    cp 8
    jr z,banner_next_row
    ld b,a
    ld a,$80
banner_mask_shift:
    ld c,b
    ld b,a
    ld a,c
    or a
    ld a,b
    jr z,banner_mask_ready
    srl a
    dec c
    ld b,c
    jr banner_mask_shift
banner_mask_ready:
    ld b,a
    ld a,(banner_bits)
    and b
    jr z,banner_skip_plot
    ld a,(banner_index)
    add a,a
    add a,a
    add a,a
    ld h,a
    ld a,(banner_bit)
    add a,h
    ld h,a
    ld a,(banner_row)
    add a,8
    ld l,a
    ld a,SYS_GFX_PLOT
    call SYSCALL_GATEWAY
    jp c,banner_exit_a
banner_skip_plot:
    ld a,(banner_bit)
    inc a
    ld (banner_bit),a
    jr banner_bit_loop
banner_next_row:
    ld a,(banner_row)
    inc a
    ld (banner_row),a
    jr banner_row_loop
banner_next_char:
    ld a,(banner_index)
    inc a
    ld (banner_index),a
    jp banner_char_loop

banner_ok:
    xor a
    jr banner_exit_a
banner_long:
    ld a,E_TOOLONG
    jr banner_exit_a
banner_bad:
    ld a,E_INVAL
banner_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

banner_text: dw 0
banner_glyph: dw 0
banner_chars: db 0
banner_index: db 0
banner_row: db 0
banner_bit: db 0
banner_bits: db 0
    ENDM
