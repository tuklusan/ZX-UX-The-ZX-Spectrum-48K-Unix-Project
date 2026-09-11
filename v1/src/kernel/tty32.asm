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
; Spectrum bitmap addressing and direct 32-column renderer.

ROM_CHARSET_BITMAP       EQU $3D00

    MACRO EMIT_TTY32_ROUTINES
; B=pixel row 0..191, C=byte column 0..31 -> HL bitmap address.
zx48_bitmap_address:
    ld a,b
    and 7
    or $40
    ld h,a
    ld a,b
    and $c0
    rrca
    rrca
    rrca
    or h
    ld h,a
    ld a,b
    and $38
    rlca
    rlca
    or c
    ld l,a
    ret

; A=target code 20h..7Fh. Draw directly from frozen 48K ROM font bitmap.
zx48_tty32_draw_char:
    cp $20
    jr c,zx48_tty32_bad
    cp $80
    jr nc,zx48_tty32_bad
    sub $20
    ld e,a
    ld d,0
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    ld hl,ROM_CHARSET_BITMAP
    add hl,de
    ld (tty32_glyph),hl
    xor a
    ld (tty32_scan),a
zx48_tty32_draw_loop:
    ld a,(tty32_scan)
    cp 8
    jr nc,zx48_tty32_draw_done
    ld e,a
    ld a,(tty_row)
    add a,a
    add a,a
    add a,a
    add a,e
    ld b,a
    ld a,(tty_col)
    ld c,a
    call zx48_bitmap_address
    push hl
    ld hl,(tty32_glyph)
    ld a,(tty32_scan)
    ld e,a
    ld d,0
    add hl,de
    ld a,(hl)
    pop hl
    ld (hl),a
    ld a,(tty32_scan)
    inc a
    ld (tty32_scan),a
    jr zx48_tty32_draw_loop
zx48_tty32_draw_done:
    xor a
    ret
zx48_tty32_bad:
    ld a,E_INVAL
    scf
    ret

zx48_tty_clear_last_bitmap_row:
    ld b,184
    ld d,8
zx48_tty_clear_row_scan:
    ld c,0
    call zx48_bitmap_address
    push bc
    ld b,32
    xor a
zx48_tty_clear_row_byte:
    ld (hl),a
    inc hl
    djnz zx48_tty_clear_row_byte
    pop bc
    inc b
    dec d
    jr nz,zx48_tty_clear_row_scan
    ret

; Copy logical rows 1..23 to 0..22 using canonical scanline mapping.
zx48_tty_scroll_bitmap:
    xor a
    ld (tty_scroll_row),a
zx48_tty_scroll_row_loop:
    ld a,(tty_scroll_row)
    cp 23
    jp nc,zx48_tty_clear_last_bitmap_row
    xor a
    ld (tty_scroll_scan),a
zx48_tty_scroll_scan_loop:
    ld a,(tty_scroll_scan)
    cp 8
    jr nc,zx48_tty_scroll_next_row
    ld e,a
    ld a,(tty_scroll_row)
    inc a
    add a,a
    add a,a
    add a,a
    add a,e
    ld b,a
    ld c,0
    call zx48_bitmap_address
    ld (tty_scroll_src),hl
    ld a,(tty_scroll_row)
    add a,a
    add a,a
    add a,a
    add a,e
    ld b,a
    ld c,0
    call zx48_bitmap_address
    ex de,hl
    ld hl,(tty_scroll_src)
    ld bc,32
    ldir
    ld a,(tty_scroll_scan)
    inc a
    ld (tty_scroll_scan),a
    jr zx48_tty_scroll_scan_loop
zx48_tty_scroll_next_row:
    ld a,(tty_scroll_row)
    inc a
    ld (tty_scroll_row),a
    jr zx48_tty_scroll_row_loop

tty32_glyph: dw 0
tty32_scan: db 0
tty_scroll_row: db 0
tty_scroll_scan: db 0
tty_scroll_src: dw 0
    ENDM
