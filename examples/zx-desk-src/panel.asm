; ZXDesk D2 panel record and drawing from src/panel.inc (rows of labels and one
; button). Keyboard control is in dialog.asm: a notice closes on Enter or EDIT.
; Damian Cooper (MIT); save-under and pointer calls become full redraws.
        section text
        global PnlPaint
        global PnlRowPaint
        global PnlX
        global PnlY
        global PnlW
        global PnlH
        global PnlRow0
        global PnlRows
        global PnlTab
        global PnlTitle
        global PnlFocus
        extern DevFillRect
        extern FrX
        extern FrY
        extern FrW
        extern FrH
        extern FrPat
        extern AddrAt
        extern DrawEdges
        extern PxRow
        extern PrintInv
        extern PrintStrPx
PTSIZE equ 5
PNLMARGIN equ $30
PNLROWH equ 8
PnlRowAddr:
        ld l,a
        ld h,0
        ld d,h
        ld e,l
        add hl,hl
        add hl,hl
        add hl,de              ; row * PTSIZE (5)
        ld de,(PnlTab)
        add hl,de
        ret
PnlRowY:
        add a,a
        add a,a
        add a,a
        ld hl,PnlRow0
        add a,(hl)
        ret
PnlRowPaint:
        ld (PnlIdx),a
        call PnlRowY
        ld (FrY),a
        ld a,(PnlX)
        inc a
        ld (FrX),a
        ld a,(PnlW)
        sub 2
        ld (FrW),a
        ld a,PNLROWH
        ld (FrH),a
        ld hl,0
        ld (FrPat),hl
        call DevFillRect
        ld a,(PnlIdx)
        ld hl,PnlFocus
        cp (hl)
        jr nz,PrpLabel
        call PnlRowY
        ld (PxRow),a
        ld b,PNLROWH
PrpBar:
        push bc
        ld a,(PnlX)
        ld c,a
        ld a,(PxRow)
        call AddrAt
        ld a,(hl)
        or PNLMARGIN
        ld (hl),a
        ld a,(PxRow)
        inc a
        ld (PxRow),a
        pop bc
        djnz PrpBar
PrpLabel:
        ld a,(PnlIdx)
        call PnlRowY
        ld (PxRow),a
        ld a,(PnlIdx)
        call PnlRowAddr
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld a,d
        or e
        ret z
        ex de,hl
        ld a,(PnlX)
        inc a
        ld c,a
        jp PrintStrPx
PnlPaint:
        ld hl,PnlX             ; x, y, width, height: the same four bytes as FrX..FrH
        ld de,FrX
        ld bc,4
        ldir
        ld hl,$ffff
        ld (FrPat),hl
        call DevFillRect
        ld a,(PnlY)
        add a,9
        ld (FrY),a
        ld (PxRow),a
        ld a,(PnlH)
        sub 10
        ld (FrH),a
        ld b,a
        ld hl,0
        ld (FrPat),hl
        push bc
        call DevFillRect
        pop bc
        ld a,(PnlX)
        ld c,a
        ld a,(PnlW)
        dec a
        ld e,a
        call DrawEdges
        ld a,1
        ld (PrintInv),a
        ld a,(PnlY)
        inc a
        ld (PxRow),a
        ld a,(PnlX)
        inc a
        ld c,a
        ld hl,(PnlTitle)
        call PrintStrPx
        xor a
        ld (PrintInv),a
        xor a
PnpRow:
        push af
        call PnlRowPaint
        pop af
        inc a
        ld hl,PnlRows
        cp (hl)
        jr c,PnpRow
        ret
        section data
PnlX: db 0
PnlY: db 0
PnlW: db 0
PnlH: db 0
PnlRow0: db 0
PnlRows: db 0
PnlTab: dw 0
PnlTitle: dw 0
PnlFocus: db 0
PnlIdx: db 0
