; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48 screen: 64 x 24 text with a 4 x 8 font, colour, PLOT/POINT and UDGs.
; Writes straight to display RAM. No glass between us and the pixels.
SYS     equ 6003h
TTOP    equ 5BE4h               ; Kernel console first row; 0 means no shared screen.
        section text
        global @scrinit,_cls,_putchar,_puts,_print_at,_cursor_at,_ink,_paper,_bright,_flash
        global _inverse,_over,_border,_plot,_point,@pixel,@pxok
        global _udg_define,_udg_get,_udg_clear,_udg_draw,_udg_draw_2x2
        global @attr,@ttyb,___pixel

; @scrinit: 27 bytes. Claim the display and clear it unless another process shares it.
@scrinit:
        ld hl,1
        ld a,39                 ; sys screen: claim -> HL = font
        call SYS
        ld (@font),hl
        ld a,e                  ; E != 0: another program draws too
        or a
        ld (@shared),a
        ld a,7
        ld (@attr),a
        ld a,(@shared)          ; Shared screen? Leave the other tenant's rows alone.
        or a                    ; Zero falls into _cls; nonzero skips it.
        j nz,@ok
; _cls: 48 bytes. Clear the drawable text rows, attributes and cursor. Fresh canvas.
_cls:   call @lim
        ld c,a
        ld b,0
.r:     ld a,b
        call @clrow
        inc b
        ld a,b
        cp c
        j nz,.r
        ld l,c
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld b,h
        ld c,l
        dec bc
        ld hl,5800h
        ld de,5801h
        ld a,(@attr)
        ld (hl),a
        ldir
        xor a
        ld (@row),a
        ld (@col),a
        ld (@wrap),a
; @ok: 4 bytes. Return zero. All clear.
@ok:    ld hl,0
        ret
; @lim: 8 bytes. Return the first text row reserved for the kernel console.
@lim:   ld a,(TTOP)
        or a
        ret nz
        ld a,24
        ret
; @bad: 4 bytes. Return one for an invalid screen request.
@bad:   ld hl,1
        ret

; _ink: 6 bytes. Set ink color 0..7; reject anything wearing extra bits.
_ink:   ld c,0F8h
        ld b,0
        j @col7
; _paper: 4 bytes. Set paper color 0..7. Background checks in.
_paper: ld c,0C7h
        ld b,3
; @col7: 27 bytes. Update the ink or paper bits of the current attribute.
@col7:  ld a,h
        or a
        j nz,@bad
        ld a,l
        cp 8
        j nc,@bad
        inc b
.s:     dec b
        j z,.d
        add a,a
        j .s
.d:     ld b,a
        ld a,(@attr)
        and c
        or b
        ld (@attr),a
        j @ok
; _bright: 6 bytes. Set bright from a Boolean input, or return one.
_bright:
        ld c,0BFh
        ld b,40h
        j @flag
; _flash: 4 bytes. Set flashing from a Boolean input, or return one.
_flash: ld c,07Fh
        ld b,80h
; @flag: 19 bytes. Update one attribute flag after checking the input.
@flag:  call @bool
        j nc,@bad
        ld a,(@attr)
        and c
        bit 0,l
        j z,.z
        or b
.z:     ld (@attr),a
        j @ok
; _inverse: 13 bytes. Enable or disable inverse pixels. Black meets white.
_inverse:
        call @bool
        j nc,@bad
        ld a,l
        neg
        ld (@inv),a
        j @ok
; _over: 11 bytes. Enable or disable pixel XOR drawing. Erasers may apply.
_over:  call @bool
        j nc,@bad
        ld a,l
        ld (@ovr),a
        j @ok
; _border: 26 bytes. Change the border and ROM shadow byte, or reject an invalid color.
_border:
        ld a,h
        or a
        j nz,@bad
        ld a,l
        cp 8
        j nc,@bad
        out (0FEh),a
        rlca                    ; Shift border bits toward BORDCR (5C48h).
        rlca                    ; The ROM's beeper and tape code read that shadow.
        rlca                    ; The kernel's key click reads it too. Three clients, one byte.
        cp 20h                  ; Border colours 0-3 get white ink below the screen.
        j nc,.b                 ; Higher colours keep their ROM-set ink.
        or 7
.b:     ld (5C48h),a
        j @ok
; @bool: 7 bytes. Carry means HL was zero or one. No halfway settings.
@bool:  ld a,h
        or a
        ret nz
        ld a,l
        cp 2
        ret

; _putchar: 9 bytes. Print one character and return its byte value.
_putchar:
        push hl
        ld a,l
        call @putc
        pop hl
        ld h,0
        ret
; _puts: 11 bytes. Print a NUL-terminated string, then a newline.
_puts:  call @puts
        ld a,10
        call @putc
        j @ok
; @puts: 11 bytes. Print string bytes until NUL. The zero gets silence.
@puts:  ld a,(hl)
        or a
        ret z
        push hl
        call @putc
        pop hl
        inc hl
        j @puts
; _cursor_at: 42 bytes. Set row and column; reject cursor positions outside the drawable area.
_cursor_at:
        ld d,h                  ; keep the column's high byte for range check
        ld e,l                  ; last argument (col) arrives in HL
        pop bc                  ; return address
        pop hl                  ; row comes from caller stack
        push bc
        ld a,h
        or d
        jp nz,@bad
        ld a,l
        call @lim
        cp l
        jp z,@bad
        jp c,@bad
        ld a,e
        cp 64
        jp nc,@bad
        ld a,l
        ld (@row),a
        ld a,e
        ld (@col),a
        xor a
        ld (@wrap),a
        jp @ok

; _print_at: 63 bytes. Print at row and column, then restore the old cursor.
_print_at:
        ld (@tmp),hl
        pop bc
        pop de                  ; col
        pop hl                  ; row
        push bc
        ld a,h
        or d
        jp nz,@bad
        ld a,l
        cp 24
        jp nc,@bad
        ld b,a
        ld a,e
        cp 64
        jp nc,@bad
        ld c,a
        ld hl,(@row)            ; save row, col and the wrap flag
        push hl
        ld a,(@wrap)
        push af
        ld a,b
        ld (@row),a
        ld a,c
        ld (@col),a
        xor a
        ld (@wrap),a
        ld hl,(@tmp)
        call @puts
        pop af
        ld (@wrap),a
        pop hl
        ld (@row),hl
        jp @ok

; @putc: 124 bytes. Handle control codes, wrapping and one text character.
@putc:  cp 10
        j z,.nl
        cp 13
        j z,.cr
        cp 8
        j z,.bs
        cp 9
        j z,.tab
        cp 12
        jp z,_cls
        cp 32
        ret c
        cp 128
        ret nc
        ld c,a
        ld a,(@wrap)
        or a
        j z,.g
        xor a
        ld (@wrap),a
        push bc
        call .lf
        pop bc
.g:     ld a,c
        call @glyph
        ld hl,@col
        ld a,(hl)
        cp 63
        j nc,.w
        inc (hl)
        ret
.w:     ld a,1
        ld (@wrap),a
        ret
.nl:    call @nowrap
.lf:    call @lim
        dec a
        ld hl,@row
        cp (hl)
        j z,.sc
        j c,.sc
        inc (hl)
        j .c0
.sc:    ld (hl),a
        call @scroll
.c0:    xor a
        ld (@col),a
        ret
.cr:    call @nowrap
        j .c0
.bs:    call @nowrap
        ld hl,@col
        ld a,(hl)
        or a
        ret z
        dec (hl)
        ret
.tab:   call @nowrap
        ld a,(@col)
        add a,8
        and 0F8h
        cp 64
        j nc,.lf
        ld (@col),a
        ret
; @nowrap: 5 bytes. Clear pending line-wrap state. Simple as that.
@nowrap:
        xor a
        ld (@wrap),a
        ret

; @glyph: 88 bytes. Draw a 4x8 font glyph and its attribute at the cursor.
@glyph: ld c,a
        call @lim
        ld b,a
        ld a,(@row)
        cp b
        ret nc                  ; the console's rows
        ld a,c
        sub 32
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        ld de,(@font)
        add hl,de
        ex de,hl                ; DE = glyph (4 bytes, two rows each)
        ld a,(@row)
        ld b,a
        and 18h
        or 40h
        ld h,a
        ld a,b
        and 7
        rrca
        rrca
        rrca
        ld l,a
        ld a,(@col)
        ld c,0F0h
        srl a
        j nc,.e
        ld c,0Fh
.e:     or l
        ld l,a                  ; HL = top pixel row of the cell
        push hl
        ld b,4
.lp:    ld a,(de)
        call @gput
        inc h
        ld a,(de)
        rlca
        rlca
        rlca
        rlca
        call @gput
        inc h
        inc de
        djnz .lp
        pop hl                  ; attribute cell
        ld a,h
        rrca
        rrca
        rrca
        and 3
        or 58h
        ld h,a
        ld a,(@attr)
        ld (hl),a
        ret
; @gput: 34 bytes. Merge one font nibble with the pixel byte; OVER and INVERSE apply.
@gput:  bit 0,c
        j z,.h
        rrca
        rrca
        rrca
        rrca
.h:     and c
        push bc
        ld b,a
        ld a,(@inv)
        and c
        xor b
        ld b,a                  ; nibble, inverted if INVERSE 1
        ld a,(@ovr)
        or a
        j nz,.ov
        ld a,c
        cpl
        and (hl)
        or b
        j .st
.ov:    ld a,b
        xor (hl)
.st:    ld (hl),a
        pop bc
        ret

; @scroll: 80 bytes. Scroll drawable rows and their colors above the console.
@scroll:
        call @lim
        dec a
        ld (@last),a
        ld b,0
.r:     push bc
        ld a,b
        call @rowad
        ex de,hl                ; DE = row b
        pop bc
        push bc
        ld a,b
        inc a
        call @rowad             ; HL = row b+1
        ld a,8
.l8:    push hl
        push de
        ld bc,32
        ldir
        pop de
        pop hl
        inc d
        inc h
        dec a
        j nz,.l8
        pop bc
        inc b
        ld a,(@last)
        cp b
        j nz,.r
        call @clrow
        ld a,(@last)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld b,h
        ld c,l
        ld hl,5820h
        ld de,5800h
        ldir
        ld a,(@attr)
        ld b,32
.a1:    ld (de),a
        inc de
        djnz .a1
        ret
; @clrow: 24 bytes. Erase the eight pixel lines of text row A without touching BC.
@clrow: call @rowad
        ld a,8
.c8:    push hl
        ld (hl),0
        ld d,h
        ld e,l
        inc de
        push bc
        ld bc,31
        ldir
        pop bc
        pop hl
        inc h
        dec a
        j nz,.c8
        ret
; @rowad: 14 bytes. Find the top bitmap address for text row A.
@rowad: ld l,a
        and 18h
        or 40h
        ld h,a
        ld a,l
        and 7
        rrca
        rrca
        rrca
        ld l,a
        ret

; _plot: 15 bytes. Set a pixel at bottom-left coordinates; report out-of-range.
_plot:  pop bc
        pop de                  ; x
        push bc
        call @pxok
        jp nc,@bad
        call @pixel
        jp @ok
; ___pixel: 10 bytes. Set a pixel when its coordinates fit the screen.
___pixel:
        pop bc
        pop de
        push bc
        call @pxok
        ret nc
        jp @pixel
; _point: 19 bytes. Test a pixel; out-of-range also reports one.
_point: pop bc
        pop de
        push bc
        call @pxok
        jp nc,@bad
        call @pxad
        and (hl)
        jp z,@ok
        jp @bad
; @pxok: 14 bytes. Check DE=x, HL=y; return C=x and B=191-y when valid.
@pxok:  ld a,d
        or h
        ret nz
        ld a,l
        cp 192
        ret nc
        cpl
        add a,192
        ld b,a
        ld c,e
        scf
        ret
; @pxad: 39 bytes. Turn C=x and B=top-down y into bitmap address and mask.
@pxad:  ld a,b
        and 7
        or 40h
        ld h,a
        ld a,b
        rra
        rra
        rra
        and 18h
        or h
        ld h,a
        ld a,b
        rla
        rla
        and 0E0h
        ld l,a
        ld a,c
        rra
        rra
        rra
        and 1Fh
        or l
        ld l,a
        ld a,c
        and 7
        ld b,a
        ld a,80h
        ret z
.m:     rrca
        djnz .m
        ret
; @pixel: 58 bytes. Draw a pixel above the console with OVER, INVERSE and color.
@pixel: call @lim
        add a,a
        add a,a
        add a,a
        cp b
        ret c
        ret z
        push hl
        call @pxad
        ld c,a
        ld a,(@ovr)
        or a
        j z,.n
        ld a,(@inv)
        or a
        j nz,.at
        ld a,c
        xor (hl)
        j .st
.n:     ld a,(@inv)
        or a
        ld a,c
        j z,.set
        cpl
        and (hl)
        j .st
.set:   or (hl)
.st:    ld (hl),a
.at:    ld a,h
        rrca
        rrca
        rrca
        and 3
        or 58h
        ld h,a
        ld a,(@attr)
        ld (hl),a
        pop hl
        ret

; @slot: 19 bytes. Find a valid eight-byte UDG slot; carry means it exists.
@slot:  ld a,h
        or a
        ret nz
        ld a,(@nudg)
        dec a
        cp l
        ccf
        ret nc
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,@udgs
        add hl,de
        scf
        ret
; _udg_define: 13 bytes. Copy eight bytes into a user glyph slot.
_udg_define:
        ex de,hl
        pop bc
        pop hl
        push bc
        push de
        call @slot
        pop de
        jp nc,@bad
        ex de,hl
; @udgcp: 8 bytes. Copy eight glyph bytes, then report success.
@udgcp: ld bc,8                 ; (udg_get copies the other way from here)
        ldir
        jp @ok
; _udg_get: 14 bytes. Copy eight bytes back out of a user glyph slot.
_udg_get:
        ex de,hl
        pop bc
        pop hl
        push bc
        push de
        call @slot
        pop de
        jp nc,@bad
        j @udgcp
; _udg_clear: 16 bytes. Blank the eight bytes of a user glyph slot.
_udg_clear:
        call @slot
        jp nc,@bad
        ld b,8
.z:     ld (hl),0
        inc hl
        djnz .z
        jp @ok
; _udg_draw: 17 bytes. Draw one user glyph at the selected row and column.
_udg_draw:
        pop bc
        pop de                  ; row
        ex (sp),hl              ; HL = slot, col on stack
        push bc
        ld b,h
        ld c,l
        pop hl                  ; ret
        ex (sp),hl              ; HL = col
        call @udg1
        jp nc,@bad
        jp @ok
; @udg1: 89 bytes. Draw a validated 8x8 user glyph; carry reports success.
@udg1:  ld a,h
        or d
        or b
        ret nz
        ld a,l
        cp 32
        ret nc
        ld a,e
        cp 24
        ret nc
        ld a,(@nudg)
        dec a
        cp c
        ccf
        ret nc
        call @lim               ; the console's rows: "drawn"
        dec a
        cp e
        ret c
        ld a,e                  ; cell address
        and 18h
        or 40h
        ld d,a
        ld a,e
        and 7
        rrca
        rrca
        rrca
        or l
        ld e,a                  ; DE = cell
        ld l,c
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld bc,@udgs
        add hl,bc               ; HL = pattern
        ex de,hl                ; HL = cell, DE = pattern
        push hl
        ld b,8
.r:     ld a,(@inv)
        ld c,a
        ld a,(de)
        xor c
        ld c,a
        ld a,(@ovr)
        or a
        ld a,c
        j z,.s
        xor (hl)
.s:     ld (hl),a
        inc h
        inc de
        djnz .r
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
        scf
        ret
; _udg_draw_2x2: 70 bytes. Draw four consecutive glyphs in a 2x2 block.
_udg_draw_2x2:
        pop bc
        pop de
        ex (sp),hl
        push bc
        ld b,h
        ld c,l                  ; BC = base
        pop hl
        ex (sp),hl              ; HL = col
        ld a,b
        or a
        jp nz,@bad
        ld a,(@nudg)            ; base .. base+3 in the bank
        sub 4
        cp c
        jp c,@bad
        ld a,h
        or d
        jp nz,@bad
        ld a,l
        cp 31
        jp nc,@bad
        ld a,e
        cp 23
        jp nc,@bad
        ld a,0
.q:     push af
        push bc
        push de
        push hl
        call @udg1
        pop hl
        pop de
        pop bc
        pop af
        inc bc
        inc a
        cp 4
        jp z,@ok
        cp 2
        j z,.nr
        inc hl
        j .q
.nr:    dec hl
        inc de
        j .q

        section bss
; @shared: 1 BSS byte. Set while another program shares the display.
@shared: ds 1
; @last: 1 BSS byte. Hold the last drawable row during a scroll.
@last:  ds 1
; @font: 2 BSS bytes. Pointer to the kernel-provided 4x8 font.
@font:  ds 2
; @row: 1 BSS byte. Current text row.
@row:   ds 1
; @col: 1 BSS byte. Current text column.
@col:   ds 1
; @wrap: 1 BSS byte. Pending wrap after the last text column.
@wrap:  ds 1
; @attr: 1 BSS byte. Current pixel attribute byte.
@attr:  ds 1
; @inv: 1 BSS byte. Pixel inversion flag.
@inv:   ds 1
; @ovr: 1 BSS byte. Pixel XOR-drawing flag.
@ovr:   ds 1
; @ttyb: 6 BSS bytes. Six bytes of terminal mode, as the kernel expects.
@ttyb:  ds 6
; @tmp: 2 BSS bytes. Temporary pointer saved across print_at.
@tmp:   ds 2
