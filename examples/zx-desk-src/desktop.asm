; Original ZXDesk desktop painting routines and four original bitmap
; shapes from upstream src/desktop.inc. Damian Cooper, MIT.
; The original desktop owns its image and labels; ZX-UX owns hardware.
        section text
        global DskPaintAll
        global DskPaintOne
        global DskShapeAt
        global DskBlitShape
        extern AddrAt
        extern PrintStrPx
        extern PrintStrPxHalf
        extern PxRow
DSKMAX equ 5
DSKENTSZ equ 8
DSKBITMAP equ 7
DSKLABEL equ 3
DSKICONH equ 16
DSKICONW equ 2
DSKSLOTH equ 25
DSKLABELY equ 17

; The icon table is constant (no icon dragging), so it is read in place.
DskEntry:
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,DskDefault
        add hl,de
        ret

DskPaintAll:
        xor a
        ld (DskIx),a
DpaLoop:
        ld a,(DskIx)
        call DskEntry
        ld a,(hl)
        or a
        call nz,DskPaintOne
        ld hl,DskIx
        inc (hl)
        ld a,(hl)
        cp DSKMAX
        jr c,DpaLoop
        ret

DskPaintOne:
        push hl
        inc hl
        ld a,(hl)
        ld (DskPx),a
        inc hl
        ld a,(hl)
        ld (DskPy),a
        pop hl
        push hl
        ld de,DSKBITMAP
        add hl,de
        ld a,(hl)
        call DskShapeAt
        ld a,(DskPx)
        ld c,a
        ld a,(DskPy)
        call DskBlitShape
        pop hl
        push hl
	inc hl
	inc hl
	inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        push hl
        ; Centre the 4-pixel glyphs under each 16-pixel icon.
        ; Work in half-byte columns so odd-width labels line up too.
        call DskStrLen
        srl a
        ld b,a
        ld a,(DskPx)
        inc a
        add a,a
        sub b
        jr nc,DskLabX
        xor a
DskLabX:
        ld b,a
        and 1
        ld (DskHx),a
        ld a,b
        srl a
        ld c,a
        ld a,(DskPy)
        add a,DSKLABELY
        ld (PxRow),a
        pop hl
        ld a,(DskHx)
        or a
        jr z,DskFullByte
        call PrintStrPxHalf
        jr DskLabelDone
DskFullByte:
        call PrintStrPx
DskLabelDone:
        pop hl
        ret
DskStrLen:
        ld b,0
DslLoop:
        ld a,(hl)
        or a
        jr z,DslDone
        inc hl
        inc b
        jr DslLoop
DslDone:
        ld a,b
        ret

DskShapeAt:
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,DskShapes
        add hl,de
        ret
DskBlitShape:
        ld (DskShp),hl
        ld (DskRow),a
        ld a,c
        ld (DskCol),a
        ld b,DSKICONH
DbsRow:
        push bc
        ld a,(DskCol)
        ld c,a
        ld a,(DskRow)
        call AddrAt
        ex de,hl
        ld hl,(DskShp)
        ld a,(hl)
        inc hl
        ld c,(hl)
        inc hl
        ld (DskShp),hl
        ex de,hl
        ld (hl),a
        inc hl
        ld (hl),c
        ld hl,DskRow
        inc (hl)
        pop bc
        djnz DbsRow
        ret

        section data
; active, x byte, y pixel, label, reserved, shape.
DskDefault:
        db 1,1,16
        dw TxtDskNote,0
        db 0
        db 1,1,48
        dw TxtDskClock,0
        db 1
        db 1,1,80
        dw TxtDskFiles,0
        db 2
        db 1,1,112
        dw TxtDskAbout,0
        db 4
        db 1,9,16
        dw TxtDskTerm,0
        db 3
TxtDskNote: db 'NOTE',0
TxtDskClock: db 'CLOCK',0
TxtDskFiles: db 'FILES',0
TxtDskAbout: db 'ABOUT',0
TxtDskTerm: db 'CONSOLE',0
DskShapes:
        db $FF,$FF,$80,$01,$80,$01,$BF,$FD
        db $80,$01,$80,$01,$BF,$FD,$80,$01
        db $80,$01,$BF,$FD,$80,$01,$80,$01
        db $BF,$FD,$80,$01,$80,$01,$FF,$FF
        db $FF,$FF,$80,$01,$80,$01,$80,$01
        db $81,$01,$81,$01,$81,$01,$81,$01
        db $81,$F9,$80,$01,$80,$01,$80,$01
        db $80,$01,$80,$01,$80,$01,$FF,$FF
        db $FF,$FF,$80,$01,$80,$01,$80,$01
        db $80,$01,$80,$01,$80,$01,$FF,$FF
        db $80,$01,$83,$C1,$80,$01,$80,$01
        db $80,$01,$80,$01,$80,$01,$FF,$FF
; 16x16 dedicated terminal monitor: display bezel, > prompt and cursor.
        db $7F,$FE,$80,$01,$BF,$FD,$A0,$05
        db $A8,$05,$A4,$05,$A8,$05,$A3,$C5
        db $A0,$05,$A0,$05,$BF,$FD,$80,$01
        db $7F,$FE,$01,$80,$07,$E0,$07,$E0
; Compact ZX-UX wordmark, 16x16.
        db $7F,$FE,$80,$01,$9C,$29,$84,$29
        db $88,$11,$90,$29,$9C,$29,$80,$01
        db $9F,$F9,$94,$29,$94,$29,$94,$11
        db $94,$29,$9C,$29,$80,$01,$7F,$FE
DskIx: db 0
DskPx: db 0
DskPy: db 0
DskRow: db 0
DskCol: db 0
DskShp: dw 0
DskHx: db 0
