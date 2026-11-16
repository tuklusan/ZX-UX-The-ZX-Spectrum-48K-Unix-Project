; ZXDesk original window record, ordering and repaint model (src/zxdesk.asm).
; SSX1 adaptation: storage for buffers/state belongs to the process,
; not the Spectrum's fixed heap/banks. Damian Cooper, MIT.
        section text
        global WndInit
        global WndOpen
        global WndClose
        global WndSelect
        global WndRepaintAll
        global WndFocusTo
        global WndPaintOne
        extern WndRecAt
        extern WndFlush
        extern WndRaise
        extern WinDraw
        extern WinRec
        extern WinX
        extern WinY
        extern WinW
        extern WinH
        extern WinTitle
        extern WinApp
        extern WndZ
        extern WndCount
        extern WndCur
        extern AppAt
        extern AppCall
        extern DrawDesktop
        extern DlgAlert

WNDRECSZ equ 8
WNDMAX equ 4
WINAPP_OFF equ 6
APP_TITLE equ 6
APP_X equ 8
APP_DRAW equ 2
APP_INIT equ 0

WndInit:
        xor a
        ld (WndCount),a
        ld (WndCur),a
        ld (WndUsed),a
        ld hl,0
        ld (WinApp),hl
        ret

; Select a window descriptor. App state remains live in its own module.
WndSelect:
        ld hl,WndCur
        cp (hl)
        ret z
        push af
        call WndFlush
        pop af
        ld (WndCur),a
        call WndRecAt
        ld de,WinRec
        ld bc,WNDRECSZ
        ldir
        ret

; One window per application kind. Reopening an existing application raises
; its window without reinitializing data, even when four windows are open.
; A = original application kind 0..6.
WndOpen:
        cp 5
        jp nc,WndNoRoom
        call AppAt
        ld (WndWantApp),hl
        ld a,(WndCount)
        or a
        jr z,WoFresh
        call WndFlush
        ld a,(WndCount)
        ld b,a
        ld hl,WndZ
WoCheck:
        ld a,(hl)
        push bc
        push hl
        push af
        call WndRecAt
        ld de,WINAPP_OFF
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,(WndWantApp)
        xor a
        sbc hl,de
        jr z,WoPresent
        pop af
        pop hl
        pop bc
        inc hl
        djnz WoCheck
        jr WoFresh
WoPresent:
        pop af
        pop hl
        pop bc
        call WndFocusTo
        xor a
        ret
WoFresh:
        ld a,(WndCount)
        cp WNDMAX
        jp nc,WndNoRoom
        ; Slots are selected from the currently unused part of a bitmap.
        ld a,(WndUsed)
        ld b,a
        ld c,0
WoFind:
        bit 0,b
        jr z,WoGot
        srl b
        inc c
        ld a,c
        cp WNDMAX
        jp nc,WndNoRoom
        jr WoFind
WoGot:
        ld a,c
        ld (WndCur),a
        ld b,a
        or a
        ld a,1
        jr z,WoBitReady
WoBitLoop:
        add a,a
        djnz WoBitLoop
WoBitReady:
        ld b,a
        ld a,(WndUsed)
        or b
        ld (WndUsed),a
        ld hl,(WndWantApp)
        ld (WinApp),hl
        ld de,APP_TITLE
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ex de,hl
        ld (WinTitle),hl
        ex de,hl
        push hl
        inc hl
        inc hl
        ld a,(hl)
        ld (WinW),a
        inc hl
        ld a,(hl)
        ld (WinH),a
        pop hl
        ld a,(WndCount)        ; the descriptor's x centres the window; each window
        add a,(hl)             ; already open moves a new one one byte right
        ld c,a
        ld a,(WinW)
        neg
        add a,32
        cp c
        jr nc,WoXok
        ld c,a
WoXok:
        ld a,c
        ld (WinX),a
        inc hl
        ld a,(WndCount)
        add a,a
        add a,a
        add a,a
        add a,(hl)
        ld c,a
        ld a,(WinH)
        neg
        add a,183
        cp c
        jr nc,WoYok
        ld c,a
WoYok:
        ld a,c
        ld (WinY),a
        ; Each app initializes its only live state on its first launch.
        ld c,APP_INIT
        call AppCall
        ld a,(WndCount)
        or a
        jr z,WoFirst
        ld e,a
        ld d,0
        ld hl,WndZ
        add hl,de
        ld d,h
        ld e,l
        dec hl
        ld b,a
WoShift:
        ld a,(hl)
        ld (de),a
        dec hl
        dec de
        djnz WoShift
WoFirst:
        ld a,(WndCur)
        ld (WndZ),a
        ld hl,WndCount
        inc (hl)
        call WndRepaintAll
        or a
        ret
WndNoRoom:
        call WndRepaintAll     ; clear any menu still drawn before the notice
        ld hl,TxtNoRoom
        ld de,0
        call DlgAlert
        scf
        ret

; Original close-on-front / z-list shift (with process-local slot release).
WndClose:
        ld a,(WndCount)
        or a
        ret z
        ld a,(WndZ)
        ld (WndClosing),a
        call WndSelect
        ld a,(WndCount)
        dec a
        jr z,WcShifted
        ld b,a
        ld hl,WndZ
        ld de,WndZ+1
WcShift:
        ld a,(de)
        ld (hl),a
        inc hl
        inc de
        djnz WcShift
WcShifted:
        ld a,(WndClosing)
        ld b,a
        or a
        ld a,1
        jr z,WcUnflag
WcMaskLoop:
        add a,a
        djnz WcMaskLoop
WcUnflag:
        cpl
        ld b,a
        ld a,(WndUsed)
        and b
        ld (WndUsed),a
        ld hl,WndCount
        dec (hl)
        jr z,WcNoWindow
        ld a,(WndZ)
        ld (WndCur),a
        call WndRecAt
        ld de,WinRec
        ld bc,WNDRECSZ
        ldir
	jr WndRepaintAll
WcNoWindow:
        ld hl,0
        ld (WinApp),hl
        jp DrawDesktop

WndFocusTo:
        call WndRaise

; Original back-to-front composition via the live record and application
; vectors. Screen buffers are grabbed after each window, in process RAM.
WndRepaintAll:
        call WndFlush
        call DrawDesktop
        ld a,(WndCount)
        or a
        ret z
        ld b,a
WraPaint:
        push bc
        ld a,b
        dec a
        ld e,a
        ld d,0
        ld hl,WndZ
        add hl,de
        ld a,(hl)
        call WndSelect
        call WndPaintOne
        pop bc
        djnz WraPaint
        ret
WndPaintOne:
        call WinDraw
        ld c,APP_DRAW
        jp AppCall             ; windows are composed back-to-front on each change

        section data
TxtNoRoom: db 'CLOSE A WINDOW FIRST',0
WndUsed: db 0
WndClosing: db 0
WndWantApp: dw 0