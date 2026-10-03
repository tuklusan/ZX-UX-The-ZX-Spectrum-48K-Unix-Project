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

; A=target code. 20h..7Fh uses the frozen ROM font. P7.13 reserves
; 80h..9Fh as the exact 32 UDG slot identifiers in tty32 only.
zx48_tty32_draw_char:
    cp $20
    jr c,zx48_tty32_bad
    cp UDG_CODE_LAST+1
    jr nc,zx48_tty32_bad
    cp UDG_CODE_FIRST
    jr nc,zx48_tty32_udg_glyph
    sub $20
    ld de,ROM_CHARSET_BITMAP
    jr zx48_tty32_glyph_base
zx48_tty32_udg_glyph:
    sub UDG_CODE_FIRST
    ld de,(udg_bank_ptr)
zx48_tty32_glyph_base:
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,de
    ld (tty32_glyph),hl
    ld a,(tty_row)
    add a,a
    add a,a
    add a,a
    ld b,a
    ld a,(tty_col)
    ld c,a
    ld d,8
zx48_tty32_draw_loop:
    call zx48_bitmap_address
    push hl
    ld hl,(tty32_glyph)
    ld a,(hl)
    inc hl
    ld (tty32_glyph),hl
    pop hl
    ld (hl),a
    inc b
    dec d
    jr nz,zx48_tty32_draw_loop
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

; Zero-initialized tty32 scratch is fixed emergency-reserve state.
TTY32_STATE_BASE          EQU EMERGENCY_START+$52
tty32_glyph               EQU TTY32_STATE_BASE+0
tty_scroll_row            EQU TTY32_STATE_BASE+2
tty_scroll_scan           EQU TTY32_STATE_BASE+3
tty_scroll_src            EQU TTY32_STATE_BASE+4
TTY32_STATE_END           EQU TTY32_STATE_BASE+6
    ASSERT TTY32_STATE_END <= EMERGENCY_START+$7F
    ENDM

; REV02 production compaction. Historical Phase-1 fixtures retain the original
; macro; the resident kernel uses the same frozen tty32/scroll behavior with
; register-held glyph state and the native bitmap row layout.
    MACRO EMIT_REV02_TTY32_ROUTINES
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

; A=target code. ROM 20h..7Fh and tty32 UDG 80h..9Fh.
zx48_tty32_draw_char:
    sub $20
    jr c,zx48_tty32_bad
    cp UDG_CODE_LAST+1-$20
    jr nc,zx48_tty32_bad
    cp UDG_CODE_FIRST-$20
    jr nc,zx48_r2_tty32_udg
    ld de,ROM_CHARSET_BITMAP
    jr zx48_r2_tty32_glyph
zx48_r2_tty32_udg:
    sub UDG_CODE_FIRST-$20
    ld de,(udg_bank_ptr)
zx48_r2_tty32_glyph:
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,de
    ex de,hl
    ld a,(tty_row)
    add a,a
    add a,a
    add a,a
    ld b,a
    ld a,(tty_col)
    ld c,a
zx48_r2_tty32_draw:
    call zx48_bitmap_address
    ld a,(de)
    ld (hl),a
    inc de
    inc b
    ld a,b
    and 7
    jr nz,zx48_r2_tty32_draw
    xor a
    ret
zx48_tty32_bad:
    jp zx48_sys_invalid

; Scroll every bitmap scanline y=8..191 to y-8 through the canonical address
; mapper. This is the same 184-line copy as the historical row/scan loops.
zx48_tty_scroll_bitmap:
    ld b,8
zx48_r2_tty32_scroll:
    ld c,0
    push bc
    call zx48_bitmap_address
    push hl
    ld a,b
    sub 8
    ld b,a
    call zx48_bitmap_address
    ex de,hl
    pop hl
    ld bc,32
    ldir
    pop bc
    inc b
    ld a,b
    cp 192
    jr c,zx48_r2_tty32_scroll

; y=184..191 maps to 50E0,51E0,...57E0. Thirty-two stores naturally carry
; H to the next scanline; restoring L to E0 selects its final character row.
zx48_tty_clear_last_bitmap_row:
    ld hl,$50e0
    ld d,8
zx48_r2_tty32_clear_scan:
    ld b,32
    xor a
zx48_r2_tty32_clear_byte:
    ld (hl),a
    inc hl
    djnz zx48_r2_tty32_clear_byte
    ld l,$e0
    dec d
    jr nz,zx48_r2_tty32_clear_scan
    ret
    ENDM
