; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48 32x24 screen: 8x8 glyphs, @attr/@inv/@ovr, no ROM print or UDG slots. (ZX-UX SDK)
; Codes 32..127 use VGA; 128..159 use game glyphs. Pixels do not draw themselves.
        section text
        global _c48_cell,_c48_any_key,_c48_shift_down
; _c48_cell: 108 bytes. Draw (row, col, code), leave HL=0; clip at 32x24. Stay in bounds.
_c48_cell:
        ld a,l
        pop bc                  ; saved return address
        pop de                  ; column
        pop hl                  ; row
        push bc
        ld b,l                  ; row
        ld c,e                  ; column
        ld d,a                  ; glyph code
        ld a,b
        cp 24
        j nc,.done
        ld a,c
        cp 32
        j nc,.done
        ld a,d
        cp 32
        j c,.done
        cp 128
        j c,.plain
        cp 160
        j nc,.done
        sub 128                 ; 32 game glyph slots: codes 128..159
        ld hl,c48_game_glyphs
        j .idx
.plain: sub 32
        ld hl,c48_vga_font
.idx:   push hl                  ; save table base
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        pop de                  ; base of selected table
        add hl,de
        ex de,hl                ; DE = glyph scanlines
        ld a,b                  ; screen: 010TTSSS LLLCCCCC
        and 18h
        or 40h
        ld h,a
        ld a,b
        and 7
        rrca
        rrca
        rrca
        or c
        ld l,a
        push hl
        ld b,8
.draw:  ld a,(@inv)
        ld c,a
        ld a,(de)
        xor c
        ld c,a
        ld a,(@ovr)
        or a
        ld a,c
        j z,.replace
        xor (hl)
.replace:
        ld (hl),a
        inc h
        inc de
        djnz .draw
        pop hl
        ld a,h
        rrca
        rrca
        rrca
        and 3
        or 58h
        ld h,a
        ld a,(@attr)
        ld (hl),a
.done:  ld hl,0
        ret

; _c48_any_key: 28 bytes. Scan all 8x5 keys directly; return 1 if held, else 0.
; No stale tty keys get a second life.
_c48_any_key:
        ld bc,0FEFEh
.poll:  in a,(c)
        and 1Fh
        cp 1Fh
        jr nz,.pressed
        ld a,b
        add a,a
        or 1
        ld b,a
        cp 0FFh
        jr nz,.poll
        ld hl,0
        ret
.pressed:
        ld hl,1
        ret

; _c48_shift_down: 15 bytes. Physical CAPS SHIFT -> 1/0. Ignore the tty gossip.
_c48_shift_down:
        ld bc,0FEFEh
        in a,(c)
        and 1
        ld hl,0
        ret nz
        ld hl,1
        ret
