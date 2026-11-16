; ZXDesk Commander two-pane model ported from src/commander.inc.
; Damian Cooper, MIT. The directory device vectors now use ZX-UX.
        section text
        global CmdInit
        global CmdDraw
        global CmdKey
        global CmdStat
        extern AddrAt
        extern WinX
        extern WinY
        extern WinH
        extern ApiStIdent
        extern ApiStSelect
        extern ApiStDir
        extern ApiStDirOpen
        extern ApiStDirNext
        extern ApiStDirClose
        extern ApiWinRows
        extern WinW
        extern ApiWinPrintIf
        extern ApiOpenFile

CMDPANEW equ 28
CMDHEADY equ 12
CMDLISTY equ 22
WINCAPH equ 10

CmdInit:
        xor a
        ld (CmdSel0),a
        ld (CmdSel1),a
        ld (CmdActive),a
        ret
CmdUse:                         ; pane 0 is backend 0 (/bin), pane 1 is /usr/doc
        ld (CmdPane),a
        jp ApiStSelect
CmdSelAt:
        ld a,(CmdPane)
        or a
        ld hl,CmdSel0
        ret z
        ld hl,CmdSel1
        ret
CmdRows:
        call ApiWinRows
        sub CMDLISTY-WINCAPH+2
        jr c,CmrOne
        srl a
        srl a
        srl a
        jr z,CmrOne
        ret
CmrOne:
        ld a,1
        ret
CmdCount:
        call CmdUse
        call ApiStDirOpen
        ld b,0                 ; (the open call changes B, so after it)
        jr c,CmcNone
CmcLoop:
        push bc
        call ApiStDirNext
        pop bc
        jr c,CmcDone
        inc b
        ld a,b
        cp 99
        jr c,CmcLoop
CmcDone:
        push bc
        call ApiStDirClose
        pop bc
CmcNone:
        ld a,b
        ret

; Original CmdDraw and CmdPane1: two independently selected panes.
CmdDraw:
        call ApiStIdent
        ld (CmdWasD),a
        ld a,(WinW)
        cp 30
        jr nc,CmdBothPanes
        ; A tiled half-width window holds one 28-character pane.
        ld a,(CmdActive)
        call CmdPane1
        jr CmdDrawDone
CmdBothPanes:
        xor a
        call CmdPane1
        ld a,1
        call CmdPane1
        call CmdVLine
CmdDrawDone:
        ld a,(CmdWasD)
        jp ApiStSelect
CmdPane1:
        call CmdUse
        ld a,(WinW)
        cp 30
        jr c,CmdNarrowPane
        ld a,(CmdPane)
        or a
        ld a,0
        jr z,CmpLeft
        ld a,CMDPANEW+2
        jr CmpLeft
CmdNarrowPane:
        xor a
CmpLeft:
        ld (CmdCol),a
        ld c,a
        call CmdDevName
        ld a,(CmdPane)
        ld b,a
        ld a,(CmdActive)
        cp b
        ld a,0
        jr nz,CmpNotAct
        inc a
CmpNotAct:
        ld b,CMDHEADY-WINCAPH
        call ApiWinPrintIf
        call CmdRows
        ld (CmdN),a
        ld b,a
        call CmdSelAt
        ld a,(hl)
        sub b
        jr c,CmpTop0
        inc a
        jr CmpTopSet
CmpTop0:
        xor a
CmpTopSet:
        ld (CmdTop),a
        call ApiStDirOpen      ; read the directory once for the whole pane
        ld a,(CmdTop)
        ld b,a
CmpSkip:
        ld a,b
        or a
        jr z,CmpSkipDone
        push bc
        call ApiStDirNext      ; the entries scrolled off the top
        pop bc
        dec b
        jr CmpSkip
CmpSkipDone:
        xor a
        ld (CmdRow),a
CmpRow:
        call ApiStDirNext
        jr nc,CmpPaint
        ld hl,TxtCmdBlank
CmpPaint:
        ld (CmdName),hl
        ld a,(CmdRow)
        ld b,a
        add a,a
        add a,a
        add a,a
        add a,CMDLISTY-WINCAPH
        ld (CmdPx),a
        ld a,(CmdTop)
        add a,b
        ld e,a
        call CmdSelAt
        ld a,(hl)
        cp e
        jr nz,CmpPlain
        ld a,(CmdPane)
        ld c,a
        ld a,(CmdActive)
        cp c
        jr nz,CmpPlain
        ld a,1
        jr CmpInv
CmpPlain:
        xor a
CmpInv:
        ld d,a
        ld a,(CmdPx)
        ld b,a
        ld a,(CmdCol)
        ld c,a
        ld hl,(CmdName)
        ld a,d
        call ApiWinPrintIf
        ld hl,CmdRow
        inc (hl)
        ld a,(hl)
        ld hl,CmdN
        cp (hl)
        jr c,CmpRow
        jp ApiStDirClose
CmdDevName:
        call ApiStIdent
        or a
        ld hl,TxtCmdBin
        ret z
        ld hl,TxtCmdDoc
        ret

; Original keyboard navigation, with filesystem actions handed to ZX-UX.
; Every key leaves the shared storage backend exactly as it found it.
CmdKey:
        ld (CmdKeyCh),a
        call ApiStIdent
        ld (CmdWasK),a
        call CmdKeyDo
        ld a,(CmdWasK)
        jp ApiStSelect
CmdKeyDo:
        ld a,(CmdKeyCh)
        cp 11
        jr nz,CmkNotU
        ld a,(CmdActive)
        ld (CmdPane),a
        call CmdSelAt
        ld a,(hl)
        or a
        ret z
        dec (hl)
        ret
CmkNotU:
        cp 10
        jr nz,CmkNotD
        ld a,(CmdActive)
        call CmdCount
        ld b,a
        ld a,(CmdActive)
        ld (CmdPane),a
        call CmdSelAt
        ld a,(hl)
        inc a
        cp b
        ret nc
        ld (hl),a
        ret
CmkNotD:
        cp 8
        jr nz,CmkNotL
        xor a
        ld (CmdActive),a
        ret
CmkNotL:
        cp 9
        jr nz,CmkNotR
        ld a,1
        ld (CmdActive),a
        ret
CmkNotR:
        cp 13
        ret nz
; Enter shows the selected file in Notes. CmdPicked has copied its name into
; CmdWork.
CmdOpen:
        call CmdPicked
        ret c
        ld hl,CmdWork
        jp ApiOpenFile
; Selected directory entry: HL=name, name copied into CmdWork. Carry past the end.
CmdPicked:
        ld a,(CmdActive)
        call CmdUse
        call CmdSelAt
        ld a,(hl)
        call ApiStDir
        ret c
        ld de,CmdWork
        ld b,12
CmpkCopy:
        ld a,(hl)
        ld (de),a
        or a
        jr z,CmpkDone
        inc hl
        inc de
        djnz CmpkCopy
        xor a
        ld (de),a
CmpkDone:
        or a
        ret

; A dotted grey line (every other pixel row) between the two panes, drawn
; only while both are showing.
CmdVLine:
        ld a,(WinX)
        add a,15
        ld c,a
        ld a,(WinY)
        add a,WINCAPH
        ld e,a
        ld a,(WinH)
        sub WINCAPH+1
        ld b,a
CvlRow:
        push bc
        push de
        ld a,e
        call AddrAt
        pop de
        bit 0,e
        jr nz,CvlSkip
        ld a,(hl)
        or $01
        ld (hl),a
CvlSkip:
        inc e
        pop bc
        djnz CvlRow
        ret

        section data
CmdSel0: db 0
CmdSel1: db 0
CmdActive: db 0
CmdPane: db 0
CmdCol: db 0
CmdPx: db 0
CmdRow: db 0
CmdN: db 0
CmdTop: db 0
CmdName: dw 0
CmdWasD: db 0
CmdKeyCh: db 0
CmdWasK: db 0
CmdWork: ds 13
CmdStat: ds 34
TxtCmdBin: db '/bin',0
TxtCmdDoc: db '/usr/doc',0
TxtCmdBlank: db ' ',0
