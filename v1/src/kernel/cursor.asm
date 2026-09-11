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
; Reversible bitmap-only cursor. Underline means scanline seven only.

TTY_CURSOR_OFF           EQU 0
TTY_CURSOR_UNDERLINE     EQU 1
TTY_CURSOR_BLOCK         EQU 2

CURSOR_STATE_BASE        EQU ERROR_STATE_END
cursor_scan              EQU CURSOR_STATE_BASE+0
cursor_count             EQU CURSOR_STATE_BASE+1
CURSOR_STATE_END         EQU CURSOR_STATE_BASE+2

    MACRO EMIT_CURSOR_ROUTINES
zx48_cursor_hide:
    ld a,(tty_cursor_visible)
    or a
    ret z
    call zx48_cursor_xor
    xor a
    ld (tty_cursor_visible),a
    ret

zx48_cursor_show:
    ld a,(tty_cursor_shape)
    or a
    ret z
    ld a,(tty_cursor_visible)
    or a
    ret nz
    call zx48_cursor_xor
    ld a,1
    ld (tty_cursor_visible),a
    ret

zx48_cursor_xor:
    ld a,(tty_cursor_shape)
    cp TTY_CURSOR_UNDERLINE
    jr z,zx48_cursor_under
    xor a
    ld (cursor_scan),a
    ld a,8
    ld (cursor_count),a
    jr zx48_cursor_loop
zx48_cursor_under:
    ld a,7
    ld (cursor_scan),a
    ld a,1
    ld (cursor_count),a
zx48_cursor_loop:
    ld a,(tty_row)
    add a,a
    add a,a
    add a,a
    ld b,a
    ld a,(cursor_scan)
    add a,b
    ld b,a
    ld a,(tty_mode)
    cp 64
    jr z,zx48_cursor_64
    ld a,(tty_col)
    ld c,a
    call zx48_bitmap_address
    ld a,(hl)
    xor $ff
    ld (hl),a
    jr zx48_cursor_next
zx48_cursor_64:
    ld a,(tty_col)
    ld c,a
    srl c
    call zx48_bitmap_address
    ld a,(tty_col)
    and 1
    ld a,(hl)
    jr nz,zx48_cursor_64_right
    xor $f0
    ld (hl),a
    jr zx48_cursor_store
zx48_cursor_64_right:
    xor $0f
zx48_cursor_store:
    ld (hl),a
zx48_cursor_next:
    ld a,(cursor_scan)
    inc a
    ld (cursor_scan),a
    ld a,(cursor_count)
    dec a
    ld (cursor_count),a
    jr nz,zx48_cursor_loop
    ret

zx48_cursor_blink:
    ld a,(tty_cursor_shape)
    or a
    ret z
    ld a,(tty_cursor_visible)
    or a
    jp z,zx48_cursor_show
    jp zx48_cursor_hide
    ENDM
