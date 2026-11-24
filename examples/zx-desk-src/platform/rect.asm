; Rectangle drawing adapter for the ZX-UX GUI. This is
; the replacement for the original self-modifying/SP-changing push chain.
; Damian Cooper's upstream drawing interface is preserved.
        section text
        global DevFillRect
        global FrX
        global FrY
        global FrW
        global FrH
        global FrPat
        extern AddrAt
DevFillRect:
        ld a,(FrH)
        or a
        ret z
        ld (FrLeft),a
        ld a,(FrW)
        or a
        ret z
        ld a,(FrY)
        ld (FrRow),a
DfrRow:
        ld a,(FrX)
        ld c,a
        ld a,(FrRow)
        call AddrAt
        ld a,(FrW)
        ld b,a
        ld a,(FrPat)           ; every caller fills with a uniform byte ($00 or $FF)
DfrCol:
        ld (hl),a
        inc hl
        djnz DfrCol
        ld hl,FrRow
        inc (hl)
        ld hl,FrLeft
        dec (hl)
        jr nz,DfrRow
        ret
        section data
FrX:    db 0
FrY:    db 0
FrW:    db 0
FrH:    db 0
FrPat:  dw 0
FrRow:  db 0
FrLeft: db 0