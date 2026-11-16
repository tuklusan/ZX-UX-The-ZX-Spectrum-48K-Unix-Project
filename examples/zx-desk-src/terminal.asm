; ZXDesk command console. It is an original-app-model window, not a new
; operating system or /bin/sh. Files are handled by the ZX-UX syscalls.
; Deliberately no fork/exec, hardware polling, or direct TTY output.
        section text
        global TermState
        global TermInit
        global TermDraw
        global TermKey
        global TermRepaintLine
        extern ApiWinPrint
        extern ApiWinPrintInv
        extern DevFillRect
        extern FrX
        extern FrY
        extern FrW
        extern FrH
        extern FrPat
        extern WinX
        extern WinY
        extern WinW
        extern KeyPaint
        extern zx_syscall

TERMROWS equ 6
PROMPTROW equ 48           ; pixel row of the input line inside the window
TERMWIDTH equ 28
TERMLINE equ 26
; Console has one 269-byte record, shared by its single window.
TermInit:
        xor a
        ld hl,TermState
        ld (hl),a
        ld de,TermState+1
        ld bc,TERMSTSZ-1
        ldir
        ld a,'/'
        ld (TermCwd),a
        ld hl,TextGreeting
        call TermSay
        ld hl,TextHint
        jp TermSay

TermDraw:
        ld hl,TermRows
        xor a
        ld (TermY),a
        ld d,6
TdLoop:
        push de
        push hl
        ld a,(TermY)
        ld b,a
        ld c,0
        call ApiWinPrint
        pop hl
        ld de,TERMWIDTH
        add hl,de
        ld a,(TermY)
        add a,8
        ld (TermY),a
        pop de
        dec d
        jr nz,TdLoop
TermDrawLine:
        ld hl,TextPrompt
        ld b,PROMPTROW
        ld c,0
        call ApiWinPrint
        ld hl,TermInput
        ld b,PROMPTROW
        ld c,2
        call ApiWinPrint
        ld hl,TextCaret
        ld a,(TermLen)
        add a,2
        ld c,a
        ld b,PROMPTROW
        jp ApiWinPrintInv

; Only the input line changed (a character typed or deleted): blank its row
; inside the window borders and draw it again, nothing else.
TermRepaintLine:
        ld a,(WinX)
        inc a
        ld (FrX),a
        ld a,(WinY)
        add a,10+PROMPTROW
        ld (FrY),a
        ld a,(WinW)
        sub 2
        ld (FrW),a
        ld a,8
        ld (FrH),a
        ld hl,0
        ld (FrPat),hl
        call DevFillRect
        jr TermDrawLine

; A complete command line is run only when ENTER arrives.
TermKey:
        cp 13
        jr z,TkEnter
        cp 12
        jr z,TkBack
        cp 8
        jr z,TkNone
        cp 9
        jr z,TkNone
        cp 10
        jr z,TkNone
        cp 11
        jr z,TkNone
        cp ' '
        jr c,TkNone
        cp 127
        jr nc,TkNone
        ld (TermChar),a
        ld a,(TermLen)
        cp TERMLINE-1
        jr nc,TkNone
        ld e,a
        ld d,0
        ld hl,TermInput
        add hl,de
        ld a,(TermChar)
        ld (hl),a
        inc hl
        ld (hl),0
        ld hl,TermLen
        inc (hl)
        jr TkLine
TkBack:
        ld a,(TermLen)
        or a
        jr z,TkNone
        dec a
        ld (TermLen),a
        ld e,a
        ld d,0
        ld hl,TermInput
        add hl,de
        ld (hl),0
        jr TkLine
; What the entry loop must repaint after this key (KeyPaint): 0 the window,
; 1 only the input line, 2 nothing.
TkNone:
        ld a,2
        jr TkSet
TkLine:
        ld a,1
TkSet:
        ld (KeyPaint),a
        ret
TkEnter:
        ld hl,TextPrompt
        call TermPutStr
        ld hl,TermInput
        call TermPutStr
        call TermNewline
        call TermParse
        call TermDispatch
        xor a
        ld (TermLen),a
        ld (TermInput),a
        ret

; The eight 27-character output lines are scrolled inside the application
; state. Nothing is written to the shared ZX-UX terminal screen.
TermNewline:
        ld hl,TermRows+TERMWIDTH
        ld de,TermRows
        ld bc,TERMWIDTH*(TERMROWS-1)
        ldir
        xor a
        ld hl,TermRows+TERMWIDTH*(TERMROWS-1)
        ld (hl),a
        ld de,TermRows+TERMWIDTH*(TERMROWS-1)+1
        ld bc,TERMWIDTH-1
        ldir
        ld (TermCol),a
        ret
TermPutChar:
        cp 13
        ret z
        cp 10
	jr z,TermNewline
        cp ' '
        ret c
        cp 127
        ret nc
        ld (TermChar),a
        ld a,(TermCol)
        cp TERMWIDTH-1
        call nc,TermNewline
        ld a,(TermCol)
        ld e,a
        ld d,0
        ld hl,TermRows+TERMWIDTH*(TERMROWS-1)
        add hl,de
        ld a,(TermChar)
        ld (hl),a
        inc hl
        ld (hl),0
        ld hl,TermCol
        inc (hl)
        ret
TermPutStr:
        ld a,(hl)
        or a
        ret z
        push hl
        call TermPutChar
        pop hl
        inc hl
        jr TermPutStr
TermSay:
        call TermPutStr
	jr TermNewline

; Split command from its optional argument in the existing input buffer.
TermParse:
        ld hl,TermInput
TpWord:
        ld a,(hl)
        or a
        jr z,TpDone
        cp ' '
        jr z,TpBreak
        inc hl
        jr TpWord
TpBreak:
        ld (hl),0
        inc hl
TpSpaces:
        ld a,(hl)
        cp ' '
        jr nz,TpDone
        inc hl
        jr TpSpaces
TpDone:
        ld (TermArg),hl
        ret
; HL=user word, DE=command name; Z if exactly equal.
TermEqual:
        ld a,(de)
        cp (hl)
        ret nz
        or a
        ret z
        inc hl
        inc de
        jr TermEqual
TermDispatch:
        ld a,(TermInput)
        or a
        ret z
        ld hl,TdTable
TcLoop:
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl                 ; HL = the command's handler pointer
        ld a,d
        or e
        jr z,TcUnknown
        push hl
        ld hl,TermInput
        call TermEqual
        pop hl
        jr z,TcFound
        inc hl
        inc hl
        jr TcLoop
TcFound:
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        jp (hl)
TcUnknown:
        ld hl,TextUnknown
        jr TermSay
TermHelp:
        ld hl,TextHelp1
        call TermSay
        ld hl,TextHelp2
        jr TermSay
TermPwd:
        ld hl,TermCwd
        jr TermSay
TermEcho:
        ld hl,(TermArg)
        jr TermSay
TermClear:
        xor a
        ld hl,TermRows
        ld (hl),a
        ld de,TermRows+1
        ld bc,TERMROWS*TERMWIDTH-1
        ldir
        ld (TermCol),a
        ret

; Build a process-local absolute path. No kernel chdir: GUI applications
; must not silently inherit a console window's working directory.
TermBuildPath:
        ld (TermArgSaved),hl
        ld a,(hl)
        cp '/'
        jr z,TbpAbs
        ld hl,TermCwd
        ld de,TermPath
        ld b,39
        call TermPathCopy
        ret c
        ld a,(TermCwd+1)
        or a
        jr z,TbpName
        ld a,'/'
        ld (de),a
        inc de
        dec b
        jr z,TbpLong
TbpName:
        ld hl,(TermArgSaved)
	jr TermPathCopy
TbpAbs:
        ld de,TermPath
        ld b,39
TermPathCopy:
        ld a,(hl)
        or a
        jr z,TpcDone
        ld (de),a
        inc de
        inc hl
        djnz TermPathCopy
TbpLong:
        scf
        ret
TpcDone:
        ld (de),a
        or a
        ret
TermNeedPath:
        ld hl,(TermArg)
        ld a,(hl)
        or a
        jr z,TnpMissing
        call TermBuildPath
        ret nc
        ld hl,TextLong
        jr TnpError
TnpMissing:
        ld hl,TextArg
TnpError:
        call TermSay
        scf
        ret

; ls reads actual ZX-UX ten-byte directory entries through open/read.
TermLs:
        ld hl,(TermArg)
        ld a,(hl)
        or a
        jr nz,TlsPath
        ld hl,TermCwd
TlsPath:
        call TermBuildPath
        jp c,TermError
        ld hl,TermPath
        ld de,0
        ld a,5
        call zx_syscall
        jp c,TermError
        ld (TermFD),hl
TlsRead:
        ld hl,(TermFD)
        ld de,TermEntry
        ld bc,10
        ld a,3
        call zx_syscall
        jr c,TlsEnd
        ld a,l
        cp 10
        jr nz,TlsEnd
        ld hl,(TermEntry)
        ld a,h
        or l
        jr z,TlsRead
        ld hl,TermEntry+2
        ld de,TermName
        ld bc,8
        ldir
        xor a
        ld (TermName+8),a
        ld hl,TermName
        call TermSay
        jr TlsRead
TlsEnd:
        ld hl,(TermFD)
        ld a,6
        jp zx_syscall

TermCd:
        ld hl,(TermArg)
        ld a,(hl)
        or a
        jr nz,TcdArg
        ld hl,TermRoot
        jr TcdPath
TcdArg:
        ld de,TermUp
        call TermEqual
        jr nz,TcdPathArg
        ld hl,TermCwd
        call TermBuildPath
        ld hl,TermPath
        call TermParent
        ld hl,TermParentPath
        jr TcdUpdate
TcdPathArg:
        ld hl,(TermArg)
TcdPath:
        call TermBuildPath
        jp c,TermError
        ld de,TermStat
        ld hl,TermPath
        ld a,18                 ; stat (does not change the process cwd)
        call zx_syscall
        jp c,TermError
        ld a,(TermStat+3)
        and $40                 ; directory flag
        jp z,TermError
        ld hl,TermPath
TcdUpdate:
        ld (TermArgSaved),hl
        ld b,17
TcdCheck:
        ld a,(hl)
        or a
        jr z,TcdCopyStart
        inc hl
        djnz TcdCheck
        ld hl,TextLong
        jp TermSay
TcdCopyStart:
        ld hl,(TermArgSaved)
        ld de,TermCwd
TcdCopy:
        ld a,(hl)
        ld (de),a
        or a
        ret z
        inc hl
        inc de
        jr TcdCopy

TermCat:
        call TermNeedPath
        ret c
        ld hl,TermPath
        ld de,0
        ld a,5
        call zx_syscall
        jp c,TermError
        ld (TermFD),hl
        ld hl,512
        ld (TermQuota),hl
TcatRead:
        ld hl,(TermFD)
        ld de,TermByte
        ld bc,1
        ld a,3
        call zx_syscall
        jr c,TcatEnd
        ld a,h
        or l
        jr z,TcatEnd
        ld a,(TermByte)
        call TermPutChar
        ld hl,(TermQuota)
        dec hl
        ld (TermQuota),hl
        ld a,h
        or l
        jr nz,TcatRead
        ld hl,TextLimit
        call TermSay
TcatEnd:
        ld hl,(TermFD)
        ld a,6
        call zx_syscall
        jp TermNewline
; df: free arena bytes and free i-nodes (ZX-UX call 37 with HL=0).
TermDf:
        ld hl,0
        ld a,37
        call zx_syscall
        jp c,TermError
        push de
        push hl
        ld hl,TextDfBytes
        call TermPutStr
        pop hl
        call TermPsNumber
        call TermNewline
        ld hl,TextDfNodes
        call TermPutStr
        pop hl
        call TermPsNumber
        jp TermNewline

; Process snapshot via ZX-UX /dev/mem, as the native ps utility does.
; Both snapshots fit existing filesystem scratch, without another arena.
TermPs:
        ld hl,TextMem
        ld de,0
        ld a,5                  ; open /dev/mem, read-only
        call zx_syscall
        jp c,TermError
        ld (TermFD),hl
        ld de,$5b00             ; KV: state[4], wchan, signal, pid, ppid
        ld bc,0
        ld a,19                 ; absolute seek
        call zx_syscall
        jp c,TpsFail
        ld hl,(TermFD)
        ld de,TermPath
        ld bc,28
        ld a,3
        call zx_syscall
        jp c,TpsFail
        ld a,l
        cp 28
        jp nz,TpsFail
        ld hl,(TermFD)
        ld de,$5d0b             ; KV2+32: four 8-byte process names
        ld bc,0
        ld a,19
        call zx_syscall
        jp c,TpsFail
        ld hl,(TermFD)
        ld de,TermLink
        ld bc,32
        ld a,3
        call zx_syscall
        jp c,TpsFail
        ld a,l
        cp 32
        jp nz,TpsFail
        ld hl,(TermFD)
        ld a,6
        call zx_syscall
        ld hl,TextPsHead
        call TermSay
        xor a
        ld (TermPsSlot),a
TpsNext:
        ld a,(TermPsSlot)
        ld e,a
        ld d,0
        ld hl,TermPath
        add hl,de
        ld a,(hl)
        or a
        jr z,TpsAdvance
        ld a,(TermPsSlot)
        add a,a
        ld e,a
        ld d,0
        ld hl,TermPath+12
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        call TermPsNumber
        ld a,' '
        call TermPutChar
        ld a,(TermPsSlot)
        ld e,a
        ld d,0
        ld hl,TermPath
        add hl,de
        ld a,(hl)
        cp 1
        jr z,TpsRun
        cp 2
        jr z,TpsSleep
        ld a,'Z'
        jr TpsState
TpsRun:
        ld a,'R'
        jr TpsState
TpsSleep:
        ld a,'S'
TpsState:
        call TermPutChar
        ld a,' '
        call TermPutChar
        ld a,(TermPsSlot)
        add a,a
        add a,a
        add a,a
        ld e,a
        ld d,0
        ld hl,TermLink
        add hl,de
        ld b,8
TpsName:
        ld a,(hl)
        cp ' '
        jr z,TpsNameEnd
        push hl
        push bc
        call TermPutChar
        pop bc
        pop hl
        inc hl
        djnz TpsName
TpsNameEnd:
        call TermNewline
TpsAdvance:
        ld a,(TermPsSlot)
        inc a
        ld (TermPsSlot),a
        cp 4
        jr c,TpsNext
        ret
TpsFail:
        ld hl,(TermFD)
        ld a,6
        call zx_syscall
        ld hl,TextError
        jp TermSay
; Print the real 16-bit PID as five decimal digits.
TermPsNumber:
        ld (TermQuota),hl
        ld de,10000
        call TpsDigit
        ld de,1000
        call TpsDigit
        ld de,100
        call TpsDigit
        ld de,10
        call TpsDigit
        ld de,1
TpsDigit:
        ld b,'0'
TpdAgain:
        ld hl,(TermQuota)
        or a
        sbc hl,de
        jr c,TpdOutput
        ld (TermQuota),hl
        inc b
        jr TpdAgain
TpdOutput:
        ld a,b
        jp TermPutChar

TermParent:
        ld de,TermParentPath
        ld hl,TermPath
        ld bc,40
        ldir
        ld hl,TermParentPath
        ld de,TermParentPath
TplFind:
        ld a,(hl)
        or a
        jr z,TplCut
        cp '/'
        jr nz,TplNext
        ld d,h
        ld e,l
TplNext:
        inc hl
        jr TplFind
TplCut:
        push de
        ld hl,TermParentPath
        or a
        sbc hl,de
        pop de
        jr nz,TplSub
        ld de,TermParentPath
        ld a,'/'
        ld (de),a
        inc de
        xor a
        ld (de),a
        ret
TplSub:
        xor a
        ld (de),a
        ret

TermError:
        cp 28                    ; the kernel reports ENOSPC in A
        jr z,TerNoSpace
        ld hl,TextError
        jp TermSay
TerNoSpace:
        ld hl,TextNoSpace
        jp TermSay

        section data
CmdHelp: db 'help',0
CmdPwd: db 'pwd',0
CmdLs: db 'ls',0
CmdCd: db 'cd',0
CmdCat: db 'cat',0
CmdEcho: db 'echo',0
CmdDf: db 'df',0
CmdPs: db 'ps',0
CmdClear: db 'clear',0
TdTable: dw CmdHelp,TermHelp,CmdPwd,TermPwd,CmdLs,TermLs,CmdCd,TermCd,CmdCat,TermCat
        dw CmdEcho,TermEcho,CmdDf,TermDf,CmdPs,TermPs,CmdClear,TermClear,0
TextPrompt: db '$ ',0
TextCaret: db '_',0
TextGreeting: db 'ZX-UX command console',0
TextHint: db 'type help for commands',0
TextHelp1: db 'cat cd clear df echo help',0
TextHelp2: db 'ls ps pwd',0
TextDfBytes: db 'free bytes  ',0
TextDfNodes: db 'free inodes ',0
TextPsHead: db '  PID S CMD',0
TextMem: db '/dev/mem',0
TextUnknown: db '? COMMAND',0
TextError: db '? FILE OR DIRECTORY',0
TextNoSpace: db '? NO SPACE',0
TextArg: db '? NAME REQUIRED',0
TextLong: db '? PATH TOO LONG',0
TextLimit: db '[OUTPUT TRUNCATED]',0
TermRoot: db '/',0
TermUp: db '..',0
; Live state exists once for the single console instance.
TermState:
TermRows: ds TERMROWS*TERMWIDTH
TermInput: ds TERMLINE
TermLen: db 0
TermCol: db 0
TermCwd: ds 17
TERMSTSZ equ $-TermState
; Scratch is used by the active window only, and is not saved.
TermY: db 0
TermChar: db 0
TermArg: dw 0
TermArgSaved: dw 0
TermFD: dw 0
TermQuota: dw 0
TermByte: db 0
TermPsSlot equ TermByte
TermPath: ds 42
TermLink: ds 45
TermParentPath: ds 42
TermEntry equ TermParentPath
TermName equ TermLink
TermStat equ TermLink