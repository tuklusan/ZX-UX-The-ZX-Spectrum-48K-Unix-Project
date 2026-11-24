; ZXDesk pixel-row text adapter using the live ZX-UX font64.
; The screen claim returns the resident 4x8 font: 96 glyphs, four bytes
; each (two four-pixel rows per byte). Never duplicate the font in SSX1.
; Damian Cooper, MIT; see zxdesk/NOTICE.txt.
        section text
        global PrintCharPx
        global PrintStrPx
        global PrintStrPxHalf
        global PrintInv
        global PrintDim
        global PxRow
        global FontBase
        extern AddrAt
        extern ScrDown

; A=character, C=screen byte column, PxRow=pixel row.
; PrintHalf=0 selects the high nibble, 1 selects the low nibble.
PrintCharPx:
        ld e,a                  ; unavailable menu items print in lower case
        ld a,(PrintDim)
        or a
        ld a,e
        jr z,PcpCase
        cp 'A'
        jr c,PcpCase
        cp 'Z'+1
        jr nc,PcpCase
        add a,32
PcpCase:
        sub 32                  ; every glyph, the copyright mark (127) included, is the kernel's
        cp 96
        jr c,PcpValid
        xor a
PcpValid:
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        ld de,(FontBase)
        add hl,de
        ex de,hl
        push de
        ld a,(PxRow)
        call AddrAt
        pop de
        ld b,4
PcpPair:
        ld a,(de)
        push af
        and $f0
        call PcpNibble
        pop af
        rlca
        rlca
        rlca
        rlca
        and $f0
        call PcpNibble
        inc de
        djnz PcpPair
        ret
PcpNibble:
        ld c,a
        ld a,(PrintInv)
        or a
        jr z,PcnNormal
        ld a,c
        xor $f0
        ld c,a
PcnNormal:
        ld a,(PrintHalf)
        or a
        jr z,PcnHigh
        ld a,c
        rrca
        rrca
        rrca
        rrca
        ld c,a
        ld a,(hl)
        and $f0
        or c
        jr PcnStore
PcnHigh:
        ld a,(hl)
        and $0f
        or c
PcnStore:
        ld (hl),a
        jp ScrDown

; Pixel-row strings keep the existing screen-byte X coordinate, but
; pack two 4-pixel glyphs into each byte and preserve the other nibble.
PrintStrPx:
        xor a
        ld (PrintHalf),a
        jr PspLoop
PrintStrPxHalf:
        ld a,1
        ld (PrintHalf),a
PspLoop:
        ld a,(hl)
        or a
        ret z
        push hl
        push bc
        call PrintCharPx
        pop bc
        pop hl
        inc hl
        ld a,(PrintHalf)
        xor 1
        ld (PrintHalf),a
        or a
        jr nz,PspLoop
        inc c
        jr PspLoop

        section data
FontBase: dw 0
PrintInv: db 0
PrintDim: db 0
PrintHalf: db 0
PxRow: db 0
