; ZXDesk D3 modal Alert (src/dialog.inc), MIT. The only dialog left: a notice
; with one OK button. ZX-UX adaptation: the overlay is removed by back-to-front
; recomposition, not private screen save-under or pointer/beeper hardware.
        section text
        global DlgAlert
        global DlgClose
        global DlgUp
        extern PnlPaint
        extern PnlX
        extern PnlY
        extern PnlW
        extern PnlH
        extern PnlRow0
        extern PnlRows
        extern PnlTab
        extern PnlTitle
        extern PnlFocus
        extern WndRepaintAll
DGX equ 10
DGY equ 52
DGW equ 14
DGROW0 equ DGY+10
DGH equ 36
PT_LABEL equ 0
PT_ACTION equ 1
PTSIZE equ 5
; HL = line 1, DE = line 2 (0 = none). Close it with Enter or EDIT.
DlgAlert:
        ld (DgRows+1),hl
        ld (DgRows+PTSIZE+1),de
        ld a,1
        ld (DlgUp),a
        ld a,DGX
        ld (PnlX),a
        ld a,DGY
        ld (PnlY),a
        ld a,DGW
        ld (PnlW),a
        ld a,DGH
        ld (PnlH),a
        ld a,DGROW0
        ld (PnlRow0),a
        ld a,3
        ld (PnlRows),a
        dec a
        ld (PnlFocus),a
        ld hl,DgRows
        ld (PnlTab),hl
        ld hl,TxtDdAlert
        ld (PnlTitle),hl
        jp PnlPaint
DlgClose:
        xor a
        ld (DlgUp),a
        jp WndRepaintAll
        section data
DgRows:
        db PT_LABEL
        dw 0,0
        db PT_LABEL
        dw 0,0
        db PT_ACTION
        dw TxtDdOk,0
TxtDdAlert: db 'NOTICE',0
TxtDdOk: db 'OK',0
DlgUp: db 0
