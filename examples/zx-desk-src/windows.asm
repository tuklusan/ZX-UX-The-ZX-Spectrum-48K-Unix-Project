; Original ZXDesk window edge and close-box drawing from src/zxdesk.asm.
; Damian Cooper (MIT); see zxdesk/NOTICE.txt.
; Screen is claimed by the ZX-UX process. No private interrupts or banking.
        section text
        global WdEdges
        global WdCloseBox
        global WndRecAt
        global WndIsFront
        global WinDraw
        global WinX
        global WinRec
        global WndTab
        global WndZ
        global WndCur
        global WndCount
        global WinW
        global WinH
        global WinTitle
        global WinApp
        global WinY
        global WdFills
        global WndRaise
        global WndFlush
        global WdAbout
        extern AddrAt
        extern DrawEdges
        extern ScrDown
        extern DevFillRect
        extern FrX
        extern FrY
        extern FrW
        extern FrH
        extern FrPat
        extern PrintStrPx
        extern PrintInv
        extern PxRow

WinCapH equ 10
WNDRECSZ equ 8

; Original ZXDesk: left/right window edges in pixel coordinates.
WdEdges:
                ld      a,(WinY)
                add     a,WinCapH
                ld      (PxRow),a
                ld      a,(WinH)
                sub     WinCapH+1
                ld      b,a
                ld      a,(WinX)
                ld      c,a
                ld      a,(WinW)
                dec     a
                ld      e,a
                jp      DrawEdges

; Original ZXDesk: close-box image on the window title cap.
WdCloseBox:
                ld      a,(WinX)
                ld      c,a
                ld      a,(WinY)
                inc     a
                call    AddrAt
                ld      de,CloseBox
                ld      b,8
WdClose:
                ld      a,(de)
                ld      (hl),a
                inc     de
                call    ScrDown
                djnz    WdClose
                ret

; Original ZXDesk descriptor indexing and focus test.
; A = window slot, HL = descriptor in WndTab.
WndRecAt:
                ld      de,WNDRECSZ
                ld      b,a
                ld      hl,WndTab
                or      a
                ret     z
WraLoop:
                add     hl,de
                djnz    WraLoop
                ret

; Original ZXDesk window composition: fill, edges, close box, title.
WinDraw:
        call WdFills
        call WdEdges
        call WdCloseBox
	jp WdText

; ZXDesk WdFills, with the hardware-specific fill behind DevFillRect.
WdFills:
        ld a,(WinX)
        ld (FrX),a
        ld a,(WinY)
        ld (FrY),a
        ld a,(WinW)
        ld (FrW),a
        ld a,WinCapH
        ld (FrH),a
        ld hl,$ffff
        ld (FrPat),hl
        call DevFillRect
        call WndIsFront
        jr z,WdfCapDone
        ld a,(WinY)
        inc a
        ld (FrY),a
        ld a,WinCapH-2
        ld (FrH),a
        ld hl,0
        ld (FrPat),hl
        call DevFillRect
        ld a,(WinY)
        inc a
        ld (PxRow),a
        ld b,WinCapH-2
        ld a,(WinX)
        ld c,a
        ld a,(WinW)
        dec a
        ld e,a
        call DrawEdges
        ld a,(WinX)
        ld (FrX),a
        ld a,(WinW)
        ld (FrW),a
WdfCapDone:
        ld a,(WinX)
        ld (FrX),a
        ld a,(WinY)
        add a,WinCapH
        ld (FrY),a
        ld a,(WinW)
        ld (FrW),a
        ld a,(WinH)
        sub WinCapH
        ld (FrH),a
        ld hl,0
        ld (FrPat),hl
        call DevFillRect
        ld a,(WinY)
        ld c,a
        ld a,(WinH)
        add a,c
        dec a
        ld (FrY),a
        ld a,1
        ld (FrH),a
        ld hl,$ffff
        ld (FrPat),hl
        jp DevFillRect

; ZXDesk's original static About window application (WdAbout).
WdAbout:
        ld a,(WinY)
        add a,WinCapH+3
        ld (PxRow),a
        ld hl,AboutLines
WdaLoop:
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld a,d
        or e
        ret z
        push hl
        ld a,(WinX)
        add a,2
        ld c,a
        ex de,hl
        call PrintStrPx
        ld a,(PxRow)
        add a,9
        ld (PxRow),a
        pop hl
        jr WdaLoop

; Original ZXDesk title cap rendering via its pixel-font interface.
WdText:
        call WndIsFront
        ld a,1
        jr z,WdtInv
        xor a
WdtInv:
        ld (PrintInv),a
        ld a,(WinY)
        inc a
        ld (PxRow),a
        ld a,(WinX)
        add a,2
        ld c,a
        ld hl,(WinTitle)
        call PrintStrPx
        xor a
        ld (PrintInv),a
        ret

; Original ZXDesk z-order shuffle.
WndRaise:
        ld b,a
        ld a,(WndZ)
        cp b
        ret z
        ld hl,WndZ
        ld c,0
WrFind:
        ld a,(hl)
        cp b
        jr z,WrFound
        inc hl
        inc c
        ld de,WndCount
        ld a,(de)
        cp c
        jr nz,WrFind
        ret
WrFound:
        ld a,c
        or a
        ret z
WrShift:
        dec hl
        ld a,(hl)
        inc hl
        ld (hl),a
        dec hl
        dec c
        jr nz,WrShift
        ld (hl),b
        ret

; Window record synchronization; ZX-UX app state is separate.
WndFlush:
        ld a,(WndCur)
        call WndRecAt
        ex de,hl
        ld hl,WinRec
        ld bc,WNDRECSZ
        ldir
        ret

WndIsFront:
                ld      a,(WndZ)
                ld      hl,WndCur
                cp      (hl)
                ret

        section data
; WinRec: x, y, w, h, title pointer, application pointer (8 bytes).
WinRec:
WinX:           db      4
WinY:           db      32
WinW:           db      24
WinH:           db      88
WinTitle:       dw      0
WinApp:         dw      0
CloseBox:       db      $FF,$81,$BD,$BD,$BD,$BD,$81,$FF
AboutLines: dw TxtAb1,TxtAb2,TxtAb3,TxtAb4,TxtAb5,TxtAbU,TxtAb6,TxtAb7,0
TxtAb1: db 'ZX-Desk',0
TxtAb2: db 127,' 2026 Damian Cooper',0
TxtAb3: db 'Adapted for ZX-UX',0
TxtAb4: db 0
TxtAb5: db 'ZX-UX',0
TxtAbU: db 'Unix for 48K ZX Spectrum',0
TxtAb6: db 127,' 2026 Supratim Sanyal',0
TxtAb7: db 'SANYALnet Labs',0
WndZ:           db      0,1,2,3
WndCount:       db      1
WndCur:         db      0

        section bss
WndTab:         ds      4*WNDRECSZ