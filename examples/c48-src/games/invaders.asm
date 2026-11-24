; Application-specific Invaders assembly, linked separately from generic libc48.
; Additional non-blocking keyboard port read for Spectrum Invaders.
; Included as source because the original uses Z, C, M (not the SDK's
; Q Z X I P matrix helper). This does not change existing entry points.
        section text
        global _invkey
_invkey:
        ld bc,0FEFEh           ; CAPS Z X C V
        in a,(c)
        bit 1,a
        jr z,.invz
        bit 3,a
        jr z,.invc
        ld bc,07FFEh           ; SPACE SYM M N B
        in a,(c)
        bit 2,a
        jr z,.invm
        bit 3,a                 ; N: immediate no at the game-over screen
        jr z,.invn
        ld bc,0DFFEh           ; Y U I O P
        in a,(c)
        bit 4,a                 ; Y: immediate yes at the game-over screen
        jr z,.invy
        ld hl,0
        ret
.invz:  ld hl,'z'
        ret
.invc:  ld hl,'c'
        ret
.invm:  ld hl,'m'
        ret
.invn:  ld hl,'n'
        ret
.invy:  ld hl,'y'
        ret
        section text
        global _inv_video,_inv_font
_inv_video:
        ld hl,04000h
        ret
_inv_font:
        ld hl,03D00h
        ret

; Spectrum Invaders native fast path for the ZX Spectrum bitmap screen.
; Called from C48; does not modify ROM and does not require extra RAM.
        section text
        global _cell,_show
        extern _cells,_inks,_shapes
_cell:
        ld a,l
        ld (@inv_pen),a
        pop bc                 ; return address
        pop hl                 ; ch
        ld a,l
        ld (@inv_ch),a
        pop hl                 ; col
        ld a,l
        ld (@inv_col),a
        ld a,h
        ld (@inv_colhi),a
        pop hl                 ; row
        ld a,l
        ld (@inv_row),a
        ld a,h
        ld (@inv_rowhi),a
        push bc
        call @inv_cell
        ld hl,0
        ret
_show:
        ld a,l
        ld (@show_pen),a
        pop bc                 ; return address
        pop hl                 ; len
        ld (@show_len),hl
        pop hl                 ; string pointer
        ld (@show_ptr),hl
        pop hl                 ; col
        ld (@show_col),hl
        pop hl                 ; row
        ld (@show_row),hl
        push bc
.loop:
        ld hl,(@show_len)
        ld a,h
        or l
        jr z,.done
        ld hl,(@show_row)
        ld a,h
        or a
        jr nz,.done
        ld a,l
        cp 22
        jr nc,.done
        ld hl,(@show_col)
        ld a,h
        or a
        jr nz,.wrap
        ld a,l
        cp 32
        jr c,.pos
.wrap:
        ld hl,0
        ld (@show_col),hl
        ld hl,(@show_row)
        inc hl
        ld (@show_row),hl
        ld a,h
        or a
        jr nz,.done
        ld a,l
        cp 22
        jr nc,.done
.pos:
        ld a,(@show_pen)
        ld (@inv_pen),a
        ld hl,(@show_row)
        ld a,l
        ld (@inv_row),a
        xor a
        ld (@inv_rowhi),a
        ld hl,(@show_col)
        ld a,l
        ld (@inv_col),a
        xor a
        ld (@inv_colhi),a
        ld hl,(@show_ptr)
        ld a,(hl)
        ld (@inv_ch),a
        inc hl
        ld (@show_ptr),hl
        call @inv_cell
        ld hl,(@show_len)
        dec hl
        ld (@show_len),hl
        ld hl,(@show_col)
        inc hl
        ld (@show_col),hl
        jr .loop
.done:
        ld hl,0
        ret
; Input @inv_row, @inv_col, @inv_ch, @inv_pen; any registers may change.
@inv_cell:
        ld a,(@inv_rowhi)
        or a
        ret nz
        ld a,(@inv_colhi)
        or a
        ret nz
        ld a,(@inv_row)
        cp 22
        ret nc
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld a,(@inv_col)
        cp 32
        ret nc
        ld e,a
        ld d,0
        add hl,de
        ex de,hl               ; DE = (row * 32 + col)
        ld hl,_cells
        add hl,de
        ld a,(@inv_ch)
        cp (hl)
        jr nz,.write
        ld hl,_inks
        add hl,de
        ld a,(@inv_pen)
        add a,56
        cp (hl)
        ret z
        jr .color
.write:
        ld (hl),a
.color:
        ld hl,_inks
        add hl,de
        ld a,(@inv_pen)
        add a,56
        ld (hl),a
        ld hl,5800h
        add hl,de
        ld (hl),a
        ld a,(@inv_ch)
        cp 32
        jr c,.empty
        cp 128
        jr nc,.high
        sub 32
        ld de,03D00h
        jr .glyph
.high:
        cp 144
        jr c,.block
        cp 165
        jr nc,.empty
        sub 144
        ld de,_shapes
        jr .glyph
.block:
        cp 128
        jr c,.empty
        sub 128
        ld de,@inv_quads
        jr .glyph
.empty:
        xor a
        ld de,@inv_blanks
.glyph:
        ; DE = base, A = 8-byte glyph index (16-bit offset)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,de
        push hl                ; sprite pointer
        ld a,(@inv_row)
        ld b,a
        and 24
        add a,40h
        ld d,a                 ; high address byte for pixel row 0
        ld a,b
        and 7
        add a,a
        add a,a
        add a,a
        add a,a
        add a,a
        ld b,a
        ld a,(@inv_col)
        add a,b
        ld e,a                 ; low address byte
        pop hl                 ; glyph source
        ld b,8
.draw:
        ld a,(hl)
        ld (de),a
        inc hl
        inc d
        djnz .draw
        ret
        section data
@inv_blanks:
        db 0,0,0,0,0,0,0,0
@inv_quads:
        db 0
        db 0
        db 0
        db 0
        db 0
        db 0
        db 0
        db 0
        db 15
        db 15
        db 15
        db 15
        db 0
        db 0
        db 0
        db 0
        db 240
        db 240
        db 240
        db 240
        db 0
        db 0
        db 0
        db 0
        db 255
        db 255
        db 255
        db 255
        db 0
        db 0
        db 0
        db 0
        db 0
        db 0
        db 0
        db 0
        db 15
        db 15
        db 15
        db 15
        db 15
        db 15
        db 15
        db 15
        db 15
        db 15
        db 15
        db 15
        db 240
        db 240
        db 240
        db 240
        db 15
        db 15
        db 15
        db 15
        db 255
        db 255
        db 255
        db 255
        db 15
        db 15
        db 15
        db 15
        db 0
        db 0
        db 0
        db 0
        db 240
        db 240
        db 240
        db 240
        db 15
        db 15
        db 15
        db 15
        db 240
        db 240
        db 240
        db 240
        db 240
        db 240
        db 240
        db 240
        db 240
        db 240
        db 240
        db 240
        db 255
        db 255
        db 255
        db 255
        db 240
        db 240
        db 240
        db 240
        db 0
        db 0
        db 0
        db 0
        db 255
        db 255
        db 255
        db 255
        db 15
        db 15
        db 15
        db 15
        db 255
        db 255
        db 255
        db 255
        db 240
        db 240
        db 240
        db 240
        db 255
        db 255
        db 255
        db 255
        db 255
        db 255
        db 255
        db 255
        db 255
        db 255
        db 255
        db 255
        section bss
@inv_pen: ds 1
@inv_ch: ds 1
@inv_row: ds 1
@inv_rowhi: ds 1
@inv_col: ds 1
@inv_colhi: ds 1
@show_pen: ds 1
@show_len: ds 2
@show_ptr: ds 2
@show_row: ds 2
@show_col: ds 2
