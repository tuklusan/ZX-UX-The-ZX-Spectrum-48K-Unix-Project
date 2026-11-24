; ZXDesk window API to ZX-UX-owned screen/SSX1 data.
; Window text vectors: HL=text, B=pixel row, C=column.
        section text
        global ApiWinPrint
        global ApiWinPrintInv
        global ApiWinPrintIf
        global ApiWinRows
        global ApiOpenFile
        extern WinX
        extern WinY
        extern WinH
        extern PrintInv
        extern PxRow
        extern PrintStrPx
        extern PrintStrPxHalf
        extern WndOpen
        extern WndRepaintAll
        extern NoteLoadAs
        extern DlgAlert
        extern ApiStOpen
        extern ApiStClose
        extern CmdStat
        extern zx_syscall
ApiWinPrint:
        xor a
        ld (PrintInv),a
ApiWinPrintGo:
        push hl
        ld a,c
        and 1
        push af
        srl c               ; two native font64 columns per screen byte
        ld a,(WinX)
        inc a
        add a,c
        ld c,a
        ld a,(WinY)
        add a,10
        add a,b
        ld (PxRow),a
        pop af
        pop hl
        or a
        jp nz,PrintStrPxHalf
        jp PrintStrPx
ApiWinPrintIf:
        or a
        jr z,ApiWinPrint
ApiWinPrintInv:
        ld a,1
        ld (PrintInv),a
        call ApiWinPrintGo
        xor a
        ld (PrintInv),a
        ret
ApiWinRows:
        ld a,(WinH)
        sub 10
        ret
; HL = basename in the selected directory. Notes shows the first 256 bytes of a
; file (with a "[truncated]" line when it is longer); a directory is refused with
; a notice. ZXDesk never writes to the filesystem.
ApiOpenFile:
        push hl
        call ApiCheckNote
        pop hl
        jr nc,OfLoad
        ld de,TxtOfDir1
        ld hl,TxtOfDir2
        jr OfAlert
OfLoad:
        call NoteLoadAs        ; load first: a failure must not open a blank window
        jr nc,OfShow
        cp 28                  ; ENOSPC: a packed file needs room for its full size
        ld de,TxtOfRam1
        ld hl,TxtOfRam2
        jr z,OfAlert
        ld de,TxtOfBad1
        ld hl,TxtOfBad2
        jr OfAlert
OfShow:
        xor a
        call WndOpen           ; opens or raises Notes (carry: no free window)
        ret c
        call WndRepaintAll
        xor a
        ret
OfAlert:                       ; DE = line 1, HL = line 2 of the notice
        ex de,hl
        call DlgAlert
        scf
        ret
; HL = basename. NC unless it is a directory (fstat via the Commander scratch
; buffer: 2-byte inode number, then the 32-byte inode; the flags' high byte is
; at +3 and bit 6 marks a directory).
ApiCheckNote:
        call ApiStOpen
        ret c
        ld (ApiFd),a
        ld l,a
        ld h,0
        ld de,CmdStat
        ld a,28
        call zx_syscall
        push af
        ld a,(ApiFd)
        call ApiStClose
        pop af
        ret c
        ld a,(CmdStat+3)
        and $40
        ret z
        scf
        ret
        section data
ApiFd: db 0
TxtOfDir1: db 'THIS IS A DIRECTORY',0
TxtOfDir2: db 'NOTES SHOWS FILES ONLY',0
TxtOfRam1: db 'NOT ENOUGH FREE MEMORY',0
TxtOfRam2: db 'TO UNPACK THIS FILE',0
TxtOfBad1: db 'CANNOT OPEN THIS FILE',0
TxtOfBad2: db 'ZX-UX REPORTED AN ERROR',0
