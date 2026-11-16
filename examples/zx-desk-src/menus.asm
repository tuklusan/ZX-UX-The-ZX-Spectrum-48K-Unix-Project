; ZXDesk original drop-down menu geometry and painter from menus.inc.
; Hardware pointer saving is replaced by ZX-UX-owned full redraw.
; Damian Cooper, MIT; see zxdesk/NOTICE.txt.
        section text
        global MenuOpenDrop
        global MenuPaint
        global MenuClose
        global MenuOpen
        global MnCount
        global MnX
        global MnY
        global MnW
        global MnH
        global MenuAction
        global MenuEnabled
        global MenuIsSep
        global MnLastMenu
        extern DevFillRect
        extern FrX
        extern FrY
        extern FrW
        extern FrH
        extern FrPat
        extern DrawEdges
        extern PxRow
        extern PrintInv
        extern PrintDim
        extern WndCount
        extern WndZ
        extern WndRecAt
        extern AppAt
        extern PrintStrPx
        extern WndOpen
        extern WndRepaintAll
        extern clean_exit
        extern WndCascade
        extern WndTile
        extern MenuSel
MENUH equ 9
SCRCOLS equ 32
MNCOUNT equ 4
MNDEFSZ equ 6
MNITEMH equ 8
; Original ZXDesk menu geometry, with pointer/save-under calls removed.
MenuOpenDrop:
        ld (MenuOpen),a
        dec a
        ld hl,MenuDefs
        or a
        jr z,MoGot
        ld b,a
        ld de,MNDEFSZ
MoSkip:
        add hl,de
        djnz MoSkip
MoGot:
        ld a,(hl)
        ld (MnX),a
        inc hl
        inc hl
        ld a,(hl)
        ld (MnW),a
        inc hl
        ld a,(hl)
        ld (MnCount),a
        add a,a
        add a,a
        add a,a
        add a,2
        ld (MnH),a
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld (MnItemPtr),de
        ld a,MENUH
        ld (MnY),a
        ld a,(MnX)
        ld b,a
        ld a,(MnW)
        add a,b
        cp SCRCOLS+1
        jr c,MoFits
        ld a,(MnW)
        neg
        add a,SCRCOLS
        ld (MnX),a
MoFits:
	jr MenuPaint
MenuClose:
        xor a
        ld (MenuOpen),a
        ret
MenuPaint:
        ld hl,MnX              ; x, y, width, height: the same four bytes as FrX..FrH
        ld de,FrX
        ld bc,4
        ldir
        ld hl,$ffff
        ld (FrPat),hl
        call DevFillRect
        ld a,(MnY)
        inc a
        ld (FrY),a
        ld a,(MnH)
        sub 2
        ld (FrH),a
        ld hl,0
        ld (FrPat),hl
        call DevFillRect
        ld a,(MnY)
        inc a
        ld (PxRow),a
        ld a,(MnH)
        sub 2
        ld b,a
        ld a,(MnX)
        ld c,a
        ld a,(MnW)
        dec a
        ld e,a
        call DrawEdges
        ld a,(MnY)
        inc a
        ld (PxRow),a
        xor a
        ld (MnPaintIndex),a
        ld a,(MnCount)
        ld b,a
MpItem:
        push bc
        ld hl,(MnItemPtr)
        ld a,(MnPaintIndex)
        add a,a
        ld e,a
        ld d,0
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        push hl
        xor a
        ld (PrintInv),a
        ld (PrintDim),a
        ld a,(hl)
        or a
        jr z,MpSep             ; empty text = dotted separator line
        ld a,(MnPaintIndex)
        ld c,a
        ld a,(MenuOpen)
        ld b,a
        push hl
        call MenuEnabled
        pop hl
        or a
        jr nz,MpAvailable
        ld a,1
        ld (PrintDim),a        ; unavailable: printed in lower case
        jr MpNotSelected
MpAvailable:
        ld a,(MnPaintIndex)
        ld c,a
        ld a,(MenuSel)
        cp c
        jr nz,MpNotSelected
        ld a,1
        ld (PrintInv),a
MpNotSelected:
        ld a,(MnX)
        inc a
        ld c,a
        call PrintStrPx
        xor a
        ld (PrintInv),a
        ld (PrintDim),a
MpNext:
        pop hl
        ld a,(PxRow)
        add a,MNITEMH
        ld (PxRow),a
        ld hl,MnPaintIndex
        inc (hl)
        pop bc
        djnz MpItem
        ret
MpSep:
        ld a,(MnX)
        inc a
        ld (FrX),a
        ld a,(MnW)
        sub 2
        ld (FrW),a
        ld a,(PxRow)
        add a,3
        ld (FrY),a
        ld a,1
        ld (FrH),a
        ld hl,$aaaa            ; every other pixel: a grey dotted line
        ld (FrPat),hl
        call DevFillRect
        jr MpNext

; C = item index in the open menu. Z if it is the separator (empty text).
MenuIsSep:
        ld hl,(MnItemPtr)
        ld e,c
        ld d,0
        add hl,de
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld a,(de)
        or a
        ret

; B=menu ID, C=item index. Returns A=1 if available, 0 if not (the menu then
; prints the item in lower case and the action dispatcher ignores it).
MenuEnabled:
        ld a,b
        cp 2
        jr z,MeFile
        cp 3
        jr z,MeLayout           ; VIEW: both items arrange windows
        cp 1
        jr nz,MeYes             ; HELP
        ld a,c                  ; ZX DESK: four applications, separator, quit
        cp 4
        jr z,MeNo
        jr nc,MeYes
        ld e,a
        ld d,0
        ld hl,MeApps
        add hl,de
        ld a,(hl)
        jr MeHasSlot
MeFile:                         ; FILE holds OPEN, which launches Files
        ld a,3
        jr MeHasSlot
MeYes:
        ld a,1
        ret
MeLayout:
        ld a,(WndCount)
        cp 2
        jr nc,MeYes
        jr MeNo
; A=application kind. At four windows, only an existing app may open.
MeHasSlot:
        push af
        ld a,(WndCount)
        cp 4
        jr nc,MeFull
        pop af
        ld a,1
        ret
MeFull:
        pop af
        call AppAt
        ld (MeTarget),hl
        ld a,(WndCount)
        ld b,a
        ld hl,WndZ
MeScan:
        ld a,(hl)
        push bc
        push hl
        call WndRecAt
        ld de,6            ; WinApp field in the 8-byte record
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,(MeTarget)
        or a
        sbc hl,de
        pop hl
        pop bc
        jr z,MeYes
        inc hl
        djnz MeScan
MeNo:
        xor a
        ret
MenuAction:
        ld c,a
        ld a,(MnLastMenu)
        ld b,a
        push bc
        call MenuEnabled
        pop bc
        or a
        ret z
        ld hl,MnActions
MnaLoop:
        ld a,(hl)
        cp $ff
        ret z
        cp b
        jr nz,MnaNext
        inc hl
        ld a,(hl)
        cp c
        jr nz,MnaNext2
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        jp (hl)
MnaNext2:
        dec hl
MnaNext:
        ld de,4
        add hl,de
        jr MnaLoop
; Application opening uses the upstream ZXDesk indices (not menu IDs).
NotesOpen:
        xor a
        jp WndOpen
AboutOpen:
        ld a,1
        jp WndOpen
ClockOpen:
        ld a,2
        jp WndOpen
CmdOpenWin:
        ld a,3
        jp WndOpen
TermOpen:
        ld a,4
        jp WndOpen
QuitAction:
        jp clean_exit

        section data
MenuDefs:
        db 1,8,8,6
        dw MnPtrs1
        db 10,6,6,1
        dw MnPtrs2
        db 17,6,8,2
        dw MnPtrs3
        db 24,6,6,1
        dw MnPtrs4
MnPtrs1: dw MnClock, MnConsole, MnFiles, MnNotes, MnSep, MnQuit
MnPtrs2: dw MnOpen
MnPtrs3: dw MnCascade, MnTile
MnPtrs4: dw MnAbout
MnClock: db 'CLOCK',0
MnConsole: db 'CONSOLE',0
MnFiles: db 'FILES',0
MnNotes: db 'NOTES',0
MnSep: db 0
MnQuit: db 'QUIT',0
MnOpen: db 'OPEN',0
MnCascade: db 'CASCADE',0
MnTile: db 'TILE',0
MnAbout: db 'ABOUT',0
MeApps: db 2,4,3,0                ; ZX DESK items 0..3: Clock Console Files Notes
; menu, item, routine. Original table format and supported actions.
MnActions:
        db 1,0
        dw ClockOpen
        db 1,1
        dw TermOpen
        db 1,2
        dw CmdOpenWin
        db 1,3
        dw NotesOpen
        db 1,5
        dw QuitAction
        db 2,0
        dw CmdOpenWin
        db 3,0
        dw WndCascade
        db 3,1
        dw WndTile
        db 4,0
        dw AboutOpen
        db $ff
MnPaintIndex: db 0
MnLastMenu: db 0
MenuOpen: db 0
MnX: db 0
MnY: db 0
MnW: db 0
MnH: db 0
MnCount: db 0
MnItemPtr: dw 0
MeTarget: dw 0