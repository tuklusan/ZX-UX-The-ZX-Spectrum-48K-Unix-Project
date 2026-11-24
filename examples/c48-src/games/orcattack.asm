; Fast 8x8 Spectrum screen blitter. C48 owns the gameplay; this helper
; only moves tile pixels and the matching attribute into screen RAM.
        section text
        global _orc_tile
_orc_tile:
        ld a,l
        ld (@orc_attr),a
        pop bc                  ; return address
        pop hl                  ; shape pixels
        ld (@orc_ptr),hl
        pop hl                  ; y
        ld a,l
        ld (@orc_y),a
        pop hl                  ; x
        ld a,l
        ld (@orc_x),a
        push bc
        ; HL = pixel bitmap start for tile row y, column x.
        ld a,(@orc_y)
        and 18h
        add a,40h
        ld h,a
        ld a,(@orc_y)
        and 7
        rrca
        rrca
        rrca
        ld b,a
        ld a,(@orc_x)
        or b
        ld l,a
        ld de,(@orc_ptr)
        ld b,8
.orc_pixels:
        ld a,(de)
        ld (hl),a
        inc de
        inc h
        djnz .orc_pixels
        ; Attribute address = 5800h + y*32 + x.
        ld a,(@orc_y)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld a,(@orc_x)
        ld e,a
        ld d,0
        add hl,de
        ld de,5800h
        add hl,de
        ld a,(@orc_attr)
        ; Match original attribute bytes; C gives neutral terrain codes.
        or a
        jr nz,.orc_special_rows
        ld a,18h                 ; Plain magenta wall, all the way down.
        jr .orc_paint_attr
.orc_special_rows:
        ld b,a
        ld a,(@orc_y)
        cp 4
        jr nz,.orc_row6
        ld a,b
        cp 28h
        jr nz,.orc_use_code
        ld a,29h                 ; Original blue/cyan empty sky in row four.
        jr .orc_paint_attr
.orc_row6:
        cp 6
        jr nz,.orc_use_code
        ld a,b
        cp 28h
        jr nz,.orc_gap
        ld a,1Bh                 ; The original magenta edge blocks.
        jr .orc_paint_attr
.orc_gap:
        cp 18h
        jr nz,.orc_use_code
        ld a,29h                 ; Cyan gaps between magenta blocks.
        jr .orc_paint_attr
.orc_use_code:
        ld a,b
.orc_paint_attr:
        ld (hl),a
        ld hl,0
        ret
        section bss
@orc_x:    ds 1
@orc_y:    ds 1
@orc_attr: ds 1
@orc_ptr:  ds 2
