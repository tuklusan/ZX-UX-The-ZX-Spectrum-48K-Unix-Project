; ZXDesk original Cascade/Tile geometry and layout tables (arrange.inc).
; Damian Cooper, MIT. SSX1 adaptation omits the private heap buffer
; free/reallocate pass because this compositor redraws back-to-front.
        section text
        global WndCascade
        global WndTile
        extern WndCount
        extern WndZ
        extern WndCur
        extern WndRecAt
        extern WndFlush
        extern WndSelect
        extern WndRepaintAll
        extern WinRec
        extern WinX
        extern WinY
        extern WinW
        extern WinH
WNDRECSZ equ 8
SCRCOLS equ 32
STATRULE equ 183
DESKTOP_TOP equ 9
ARRDESKH equ 174
ARRHALFH equ 87
ARRX0 equ 1
ARRY0 equ DESKTOP_TOP+1
WndCascade:
        ld a,(WndCount)
        or a
        ret z
        call WndFlush
        ld a,(WndCount)
        ld (ArrN),a
        xor a
        ld (ArrI),a
ArcLoop:
        ld a,(ArrN)
        ld b,a
        ld a,(ArrI)
        cp b
        jr nc,ArrDone
        ld c,a
        ld a,(ArrN)
        dec a
        sub c
        ld e,a
        ld d,0
        ld hl,WndZ
        add hl,de
        ld a,(hl)
        call WndRecAt
        push hl
        ld a,(ArrI)
        ld b,a
        add a,a
        add a,ARRX0
        ld c,a
        pop hl
        push hl
        inc hl
        inc hl
        ld a,(hl)
        neg
        add a,SCRCOLS
        cp c
        jr nc,ArcXok
        ld c,a
ArcXok:
        pop hl
        push hl
        ld (hl),c
        pop hl
        push hl
        ld a,(ArrI)
        ld b,a
        add a,a
        add a,a
        add a,b
        add a,a
        add a,ARRY0
        ld c,a
        pop hl
        push hl
        inc hl
        inc hl
        inc hl
        ld a,(hl)
        neg
        add a,STATRULE
        cp c
        jr nc,ArcYok
        ld c,a
ArcYok:
        pop hl
        inc hl
        ld (hl),c
        ld hl,ArrI
        inc (hl)
        jr ArcLoop
ArrDone:
        ld a,(WndCur)
        call WndRecAt
        ld de,WinRec
        ld bc,WNDRECSZ
        ldir
        jp WndRepaintAll
WndTile:
        ld a,(WndCount)
        or a
        ret z
        call WndFlush
        ld a,(WndCount)
        dec a
        ld e,a
        ld d,0
        ld hl,ArrTileAt
        add hl,de
	ld e,(hl)
        ld hl,ArrTiles
        add hl,de
        ld (ArrTab),hl
        xor a
        ld (ArrI),a
ArtLoop:
        ld a,(WndCount)
        ld b,a
        ld a,(ArrI)
        cp b
        jr nc,ArtDone
        ld e,a
        ld d,0
        ld hl,WndZ
        add hl,de
        ld a,(hl)
        call WndSelect
        ld hl,(ArrTab)
        ld a,(hl)
        ld (WinX),a
        inc hl
        ld a,(hl)
        ld (WinY),a
        inc hl
        ld a,(hl)
        ld (WinW),a
        inc hl
        ld a,(hl)
        ld (WinH),a
        inc hl
        ld (ArrTab),hl
        ld hl,ArrI
        inc (hl)
        jr ArtLoop
ArtDone:
        jp WndRepaintAll
        section data
ArrTileAt: db 0,4,12,24
ArrTiles:
        db 0,DESKTOP_TOP,SCRCOLS,ARRDESKH
        db 0,DESKTOP_TOP,16,ARRDESKH
        db 16,DESKTOP_TOP,16,ARRDESKH
        db 0,DESKTOP_TOP,16,ARRDESKH
        db 16,DESKTOP_TOP,16,ARRHALFH
        db 16,DESKTOP_TOP+ARRHALFH,16,ARRDESKH-ARRHALFH
        db 0,DESKTOP_TOP,16,ARRHALFH
        db 0,DESKTOP_TOP+ARRHALFH,16,ARRDESKH-ARRHALFH
        db 16,DESKTOP_TOP,16,ARRHALFH
        db 16,DESKTOP_TOP+ARRHALFH,16,ARRDESKH-ARRHALFH
ArrN: db 0
ArrI: db 0
ArrTab: dw 0