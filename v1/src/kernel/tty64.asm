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
; 64x24 renderer using validated/pinned F4X8. Adjacent columns share attributes.

    MACRO EMIT_TTY64_ROUTINES
zx48_tty64_install_font:
    ld a,b
    cp F4X8_SIZE/256
    jp nz,zx48_tty64_bad
    ld a,c
    cp F4X8_SIZE&$ff
    jp nz,zx48_tty64_bad
    ld (tty64_source_ptr),hl
    ld a,(hl)
    cp 'F'
    jp nz,zx48_tty64_bad
    inc hl
    ld a,(hl)
    cp '4'
    jp nz,zx48_tty64_bad
    inc hl
    ld a,(hl)
    cp 'X'
    jp nz,zx48_tty64_bad
    inc hl
    ld a,(hl)
    cp '8'
    jp nz,zx48_tty64_bad
    inc hl
    ld a,(hl)
    cp 1
    jp nz,zx48_tty64_bad
    inc hl
    ld a,(hl)
    cp $20
    jp nz,zx48_tty64_bad
    inc hl
    ld a,(hl)
    cp 96
    jp nz,zx48_tty64_bad
    inc hl
    ld a,(hl)
    or a
    jp nz,zx48_tty64_bad
    ld bc,F4X8_SIZE
    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    ret c
    ld (tty64_resource_ptr),hl
    ex de,hl
    ld hl,(tty64_source_ptr)
    ld bc,F4X8_SIZE
    call zx48_memcpy
    ld bc,F4X8_SIZE
    call zx48_memory_pin_bytes
    ld hl,(tty64_resource_ptr)
    ld de,8
    add hl,de
    ld (tty64_font_ptr),hl
    ld a,64
    ld (tty_mode),a
    xor a
    ret

zx48_tty64_draw_char:
    ld (tty64_char),a
    cp $20
    jp c,zx48_tty64_bad
    cp $80
    jp nc,zx48_tty64_bad
    ld hl,(tty64_font_ptr)
    ld a,h
    or l
    jp z,zx48_tty64_bad
    ld a,(tty64_char)
    sub $20
    ld e,a
    ld d,0
    sla e
    rl d
    sla e
    rl d
    ld hl,(tty64_font_ptr)
    add hl,de
    ld (tty64_glyph),hl
    xor a
    ld (tty64_scan),a
zx48_tty64_scan_loop:
    ld a,(tty64_scan)
    cp 8
    jr nc,zx48_tty64_attr
    ld e,a
    srl e
    ld d,0
    ld hl,(tty64_glyph)
    add hl,de
    ld a,(hl)
    ld d,a
    ld a,(tty64_scan)
    and 1
    ld a,d
    jr nz,zx48_tty64_nibble
    rrca
    rrca
    rrca
    rrca
zx48_tty64_nibble:
    and $0f
    ld d,a
    ld a,(tty_row)
    add a,a
    add a,a
    add a,a
    ld b,a
    ld a,(tty64_scan)
    add a,b
    ld b,a
    ld a,(tty_col)
    srl a
    ld c,a
    call zx48_bitmap_address
    ld a,(tty_col)
    and 1
    ld a,(hl)
    jr nz,zx48_tty64_right
    and $0f
    ld e,a
    ld a,d
    rlca
    rlca
    rlca
    rlca
    or e
    ld (hl),a
    jr zx48_tty64_next
zx48_tty64_right:
    and $f0
    or d
    ld (hl),a
zx48_tty64_next:
    ld a,(tty64_scan)
    inc a
    ld (tty64_scan),a
    jr zx48_tty64_scan_loop
zx48_tty64_attr:
    ld a,(tty_row)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld a,(tty_col)
    srl a
    ld e,a
    ld d,0
    add hl,de
    ld de,ATTR_START
    add hl,de
    ld a,(tty_current_attr)
    ld (hl),a
    xor a
    ret
zx48_tty64_bad:
    ld a,E_INVAL
    scf
    ret

tty64_resource_ptr: dw 0
tty64_source_ptr: dw 0
tty64_font_ptr: dw 0
tty64_glyph: dw 0
tty64_scan: db 0
tty64_char: db 0
tty_current_attr: db 7
    ENDM
