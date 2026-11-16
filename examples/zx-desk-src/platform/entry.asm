; ZX-UX SSX1 process lifecycle, keyboard and event adapter for original ZXDesk.
; This is not a separate desktop, ROM or operating system.
        section text
        global start
        global clean_exit
        global KeyPaint
        global DrawDesktop
        global MenuSel
        extern zx_syscall
        extern DskPaintAll
        extern WinApp
        extern ClkTick
        extern WndInit
        extern WndOpen
        extern WndClose
        extern WndRepaintAll
        extern WndPaintOne
        extern TermRepaintLine
        extern WndCount
        extern WndZ
        extern MenuOpen
        extern MenuOpenDrop
        extern MenuClose
        extern MenuPaint
        extern MenuAction
        extern MnLastMenu
        extern MnCount
        extern FillRowSolid
        extern PrintStrPx
        extern PxRow
        extern PrintInv
        extern FontBase
        extern AppCall
        extern DlgUp
        extern NoteBuf
        extern WinX
        extern WinY
        extern WinW
        extern WinH
        extern DlgClose
        extern MenuIsSep
        extern RowAddr
        extern ScrDown

SCREEN equ $4000
ATTRS equ $5800
APP_KEY equ 4
APP_CONSOLE equ 4
APP_CLOCK equ 2

start:
        ld hl,0
        ld de,oldtty
        ld a,32
        call zx_syscall
        jp c,done
        ld hl,0
        ld de,rawtty
        ld a,31
        call zx_syscall
        jp c,done
        ld hl,1
        ld a,39
        call zx_syscall
        jp c,restore
        ld a,1
        ld (owned),a
        ld a,e
        or a
        jp nz,release
        ld (FontBase),hl       ; _screen returns the OS-owned font64
        xor a
        ld (NoteBuf),a         ; Notes starts with an empty page
        ld hl,TxtMem           ; /dev/mem: peek at the kernel's key queue, clear MODE
        ld de,2
        ld a,5
        call zx_syscall
        jr c,StNoMem
        ld a,l
        ld (MemFd),a
StNoMem:
        call WndInit
        ld a,APP_CONSOLE       ; the console and the clock open at start,
        call WndOpen
        ld a,APP_CLOCK         ; with the console left in focus
        call WndOpen
        ld a,APP_CONSOLE
        call WndOpen
mainloop:
        call WaitKey
        ld hl,0
        ld de,key
        ld bc,1
        ld a,3
        call zx_syscall
        jp c,clean_exit
        ld a,h
        or l
        jp z,clean_exit
        ld a,(key)
        ld b,a
        ld a,(DlgUp)
        or a
        jp nz,modal_dispatch
        ld a,(MoveMode)
        or a
        jp nz,move_key
        ld a,b
        cp 7                   ; EDIT = CAPS SHIFT+1 (ZX-UX raw key)
        jp z,menu_key
        ; An open menu owns the keyboard, so EDIT then Q reaches menu_dispatch
        ; even while windows are open.
        ld a,(MenuOpen)
        or a
        jp nz,menu_dispatch
        ld a,b
        cp 'q'
        jp z,quit_key
        cp 'Q'
        jp z,quit_key
        ; All ordinary letters, including M, reach the focused application.
        ld a,(WndCount)
        or a
        jr z,mainloop          ; the desktop alone: apps launch from the ZX DESK menu
        ; Each window's key goes to its original application vector.
        ld a,b
        call KeyToApp
        jp repaint_front

; Wait for a key without blocking forever: sleep 4 ticks (1/50 s), and while the
; kernel's raw-key queue is empty redraw the clock when its second changes.
; ZXDesk has no interrupt of its own and must not hook the kernel's.
WaitKey:
        call ClrMode
        call KeyReady
        ret nz
        ld hl,4
        ld a,34                ; _sleep
        call zx_syscall
        ld a,(DlgUp)
        ld hl,MenuOpen
        or (hl)
        call z,ClkTick         ; not while a menu or a notice is on screen
        jr WaitKey
; NZ when a key is waiting (or when it cannot be told: then the read blocks).
KeyReady:
        ld de,$5b68            ; ttyhd, then ttytl: the raw-key queue head and tail
        call MemSeek
        jr c,KrYes
        ld de,KeyPair
        ld bc,2
        ld a,3
        call zx_syscall
        jr c,KrYes
        ld a,(KeyPair)
        ld hl,KeyPair+1
        cp (hl)                ; Z: head = tail, the queue is empty
        ret
KrYes:
        or 1
        ret
; DE = address: seek there in /dev/mem. C if it is not open or the seek failed;
; else HL = its file descriptor.
MemSeek:
        ld a,(MemFd)
        or a
        scf
        ret z
        ld l,a
        ld h,0
        push hl
        ld bc,0
        ld a,19                ; absolute seek
        call zx_syscall
        pop hl
        ret
; CAPS SHIFT+9 (GRAPHICS), between RIGHT (CAPS+8) and DELETE (CAPS+0), switches
; the ROM keyboard to graphics mode, where EDIT and the letters stop working,
; and ZX-UX never switches it back (not even for its shell after BREAK).
; ZXDesk never wants it: zero MODE (5C41h) whenever it waits for a key.
ClrMode:
        ld de,$5c41
        call MemSeek
        ret c
        ld de,ModeZero
        ld bc,1
        ld a,4
        jp zx_syscall
next_window:
        ld a,(WndCount)
        cp 2
        jp c,repaint
        ld a,(WndZ)            ; the front window goes to the back, the others come up
        push af                ; one place: N steps through every window in turn
        ld a,(WndCount)
        dec a
        ld c,a
        ld b,0
        ld hl,WndZ+1
        ld de,WndZ
        ldir
        pop af
        ld (de),a              ; DE = WndZ + count - 1
        call WndRepaintAll
        jp mainloop
close_key:
        call MenuClose
        call WndClose
        ld a,(DlgUp)
        or a
        jp nz,mainloop
        jp repaint
quit_key:
        ld a,(WndCount)
        or a
        jp z,clean_exit
        ; q is part of a document while a window has focus.
        ld a,'q'
        call KeyToApp
        jp repaint_front
; EDIT (CAPS SHIFT+1) opens the menu bar, and closes it again.
; BREAK (CAPS SHIFT+SPACE) is reserved by the ZX-UX kernel.
menu_dispatch:
        ld a,b
        cp 'q'
        jp z,clean_exit
        cp 'Q'
        jp z,clean_exit
        cp 'm'
        jp z,move_start
        cp 'M'
        jp z,move_start
        cp 'n'
        jr z,menu_cycle
        cp 'N'
        jr z,menu_cycle
        cp 'x'
        jr z,menu_close_front
        cp 'X'
        jr z,menu_close_front
        jr menu_navigation
menu_cycle:
        call MenuClose
        jr next_window
menu_close_front:
        call MenuClose
        jr close_key
menu_navigation:
        ld a,b
        cp 8
	jr z,menu_left_tab
        cp 9
	jr z,menu_right_tab
        cp 11
        jr z,menu_previous
        cp 10
        jr z,menu_next
        cp 13
        jr z,menu_choose
        jp mainloop
menu_left_tab:
        ld a,(MenuOpen)
        dec a
        jr nz,menu_tab_set
        ld a,4
        jr menu_tab_set
menu_right_tab:
        ld a,(MenuOpen)
        inc a
        cp 5
        jr c,menu_tab_set
        ld a,1
menu_tab_set:
        push af
        xor a
        ld (MenuSel),a
        call WndRepaintAll     ; erase the menu that was showing
        pop af
        call MenuOpenDrop      ; and draw the new one on top
        jp mainloop
; Up/Down skip the dotted separator line.
menu_previous:
        ld a,(MenuSel)
        ld b,a
MpvLoop:
        ld a,b
        or a
        jp z,mainloop
        dec b
        ld c,b
        call MenuIsSep
        jr z,MpvLoop
        ld a,b
        ld (MenuSel),a
        jr menu_redraw
menu_next:
        ld a,(MenuSel)
        ld b,a
MnxLoop:
        inc b
        ld a,(MnCount)
        cp b
        jp z,mainloop
        jp c,mainloop
        ld c,b
        call MenuIsSep
        jr z,MnxLoop
        ld a,b
        ld (MenuSel),a
        jr menu_redraw
menu_choose:
        ld a,(MenuOpen)
        ld (MnLastMenu),a
        ld a,(MenuSel)
        push af
        call MenuClose
        call WndRepaintAll
        pop af
        call MenuAction
        jp mainloop
modal_dispatch:                ; a notice closes on Enter or EDIT
        ld a,b
        cp 7
        jr z,modal_close
        cp 13
        jp nz,mainloop
modal_close:
        call DlgClose
        jp mainloop
menu_key:
        ld a,(MenuOpen)
        or a
        jr z,MkOpen
        call MenuClose         ; EDIT again leaves the menu without choosing anything
        jp repaint             ; (Left and Right switch between the menus)
MkOpen:
        xor a
        ld (MenuSel),a
        inc a
        call MenuOpenDrop      ; draws the first menu over the screen as it is
        jp mainloop
; The same menu box with another item selected: nothing under it changed.
menu_redraw:
        call MenuPaint
        jp mainloop
; A key handled by the front window: it is on top, so redrawing it alone is exact.
repaint_front:
        ld a,(DlgUp)
        or a
        jp nz,mainloop
        ld a,(KeyPaint)
        or a
        jr z,RfWindow
        cp 2
        jp z,mainloop          ; the application says nothing changed
        call TermRepaintLine   ; 1: only the Console's input line changed
        jp mainloop
RfWindow:
        call WndPaintOne
        jp mainloop
; A = key. Give it to the front window's application, which may set KeyPaint
; to say what to repaint: 0 its window (the default), 1 the Console's input
; line, 2 nothing.
KeyToApp:
        ld c,APP_KEY
        ld hl,KeyPaint
        ld (hl),0
        jp AppCall
repaint:
        ; A dialog opened by the key just handled stays on screen untouched.
        ld a,(DlgUp)
        or a
        jp nz,mainloop
        call WndRepaintAll
        ld a,(MenuOpen)
        or a
        call nz,MenuPaint
        jp mainloop

; EDIT then M: the arrow keys move the front window 8 pixels at a time, kept
; inside the desktop (x + width <= 32 bytes, 9 <= y, y + height <= 183).
; Enter or EDIT drops it.
move_start:
        call MenuClose
        ld a,(WndCount)
        or a
        jr z,repaint
        ld a,1
        ld (MoveMode),a
        jr repaint
move_key:
        ld a,b
        cp 7
        jr z,move_done
        cp 13
        jr z,move_done
        cp 8
        jr z,mv_left
        cp 9
        jr z,mv_right
        cp 11
        jr z,mv_up
        cp 10
        jp nz,mainloop
        ld a,(WinY)            ; down: y = min(y + 8, 183 - height)
        add a,8
        ld c,a
        ld a,183
        ld hl,WinH
        sub (hl)
        cp c
        jr nc,mv_dok
        ld c,a
mv_dok:
        ld a,c
        jr mv_putY
mv_up:
        ld a,(WinY)            ; up: y = max(y - 8, 9)
        sub 8
        jr c,mv_top
        cp 9
        jr nc,mv_putY
mv_top:
        ld a,9
mv_putY:
        ld (WinY),a
        jr repaint
mv_left:
        ld a,(WinX)
        or a
        jp z,mainloop
        dec a
mv_putX:
        ld (WinX),a
        jr repaint
mv_right:
        ld a,(WinX)
        ld hl,WinW
        add a,(hl)
        cp 32
        jp nc,mainloop
        ld a,(WinX)
        inc a
        jr mv_putX
move_done:
        xor a
        ld (MoveMode),a
        jp repaint
 ; Normal exit clears the application's bitmap before ZX-UX
; returns the screen to its text console. BREAK is a kernel kill
; and cannot execute this process-side cleanup.
clean_exit:
        ld hl,SCREEN
        ld de,SCREEN+1
        ld bc,6143
        xor a
        ld (hl),a
        ldir

release:
        ld a,(owned)
        or a
        jr z,restore
        ld hl,0
        ld a,39
        call zx_syscall
restore:
        ld hl,0
        ld de,oldtty
        ld a,31
        call zx_syscall
done:
        ld hl,0
        ld a,1
	jp zx_syscall

; ZXDesk bitmap desktop under ZX-UX's claimed Spectrum screen.
DrawDesktop:
        xor a
BgLoop:
        ld (BgRow),a
        ld c,0                 ; rows 0..8 and 183..191 are blank
        cp 9
        jr c,BgFill
        cp 183
        jr nc,BgFill
        and 3                  ; the lattice: $88 on rows = 0 mod 4, $22 on rows = 2 mod 4
        jr z,BgA
        cp 2
        jr nz,BgFill
        ld c,$22
        jr BgFill
BgA:
        ld c,$88
BgFill:
        ld a,(BgRow)
        push bc
        call RowAddr
        pop bc
        ld (hl),c
        ld d,h
        ld e,l
        inc e
        ld bc,31
        ldir
        ld a,(BgRow)
        inc a
        cp 192
        jr c,BgLoop
        xor a
        ld (PrintInv),a
        xor a                  ; text rows 0..7: the rule on row 8 stays clear of the glyph tails
        ld (PxRow),a
        ld c,1
        ld hl,TxtMenu
        call PrintStrPx
        ld a,8
        call FillRowSolid
        ld a,183
        call FillRowSolid
        call DskPaintAll
        ld a,184               ; rows 184..191: stays out of the attribute area
        ld (PxRow),a
        ld hl,TxtStatus
        ld a,(MoveMode)
        or a
        jr z,DdStat
        ld hl,TxtMove
DdStat:
        ld c,1
        call PrintStrPx
        ld c,29                ; ZX-UX in the last three cells, six 4-pixel slots
        ld hl,TxtLogo
        call PrintStrPx
        ld a,184               ; invert every right-hand slot: its letter takes the cell's
        call RowAddr           ; paper colour on the ink colour, so each of the five
        ld de,29               ; letters has a background colour of its own
        add hl,de
        ld b,8
LgRow:
        push hl
        ld c,3
LgByte:
        ld a,(hl)
        xor $0f
        ld (hl),a
        inc l
        dec c
        jr nz,LgByte
        pop hl
        call ScrDown
        djnz LgRow
        ld hl,ATTRS
        ld de,ATTRS+1
        ld bc,767
        ld (hl),$78
        ldir
        ld hl,AttrLogo
        ld de,ATTRS+23*32+29
        ld bc,3
        ldir
        ret

        section data
rawtty: db 0,0,0,0,$a0,0
owned: db 0
MenuSel: db 0
BgRow: db 0
key: db 0
TxtMenu: db 'ZX DESK           FILE          VIEW          HELP',0
TxtStatus: db 'EDIT (CAPS+1): Menu, then M=Move N=Next X=Close Q=Quit',0
TxtMove: db 'Arrows move the window, Enter=Done',0
TxtLogo: db ' ZX-UX',0
AttrLogo: db $7A,$74,$68   ; paper/ink: white/red, yellow/green, cyan/black
MoveMode: db 0
KeyPaint: db 0
TxtMem: db '/dev/mem',0
MemFd: db 0
ModeZero: db 0
KeyPair: ds 2
        section bss
oldtty: ds 6