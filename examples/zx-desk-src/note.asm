; ZXDesk Notes: a read-only text viewer, from Damian Cooper's src/note.inc (MIT).
; Editing and saving are removed, so nothing in ZXDesk writes to the filesystem.
; The first 256 bytes of a file are kept as they are (new lines and printable
; ASCII), with a "[truncated]" line added when the file is longer, and wrapped
; to the window width each time they are drawn, so the text re-wraps when the
; window changes size. Up and Down scroll by display row.
        section text
        global NoteInit
        global NoteDrawInterior
        global NoteKey
        global NoteLoadAs
        global NoteBuf
        extern WinW
        extern WinH
        extern ApiWinPrint
        extern ApiStOpen
        extern ApiStRead
        extern ApiStClose
        extern KeyPaint

; -> A = visible text rows in the window.
NoteVisRows:
        ld a,(WinH)
        sub 14
        jr c,NvrOne
        srl a
        srl a
        srl a
        ret nz
NvrOne:
        ld a,1
        ret

; HL = start of a display row (text left) -> DE = end of its text (the new
; line, the first character of the next row, or the end), HL = start of the
; next row. A row holds as many characters as fit between the window borders;
; a new line straight after a full row is swallowed.
NoteRowEnd:
        ld a,(WinW)
        sub 2
        add a,a
        ld b,a
        ld d,h
        ld e,l
NreLoop:
        ld a,(de)
        cp 10
        jr z,NreLf
        or a
        jr z,NreEnd
        inc de
        djnz NreLoop
        ld a,(de)
        cp 10
        jr z,NreLf
NreEnd:
        ld h,d
        ld l,e
        ret
NreLf:
        ld h,d
        ld l,e
        inc hl
        ret

; A = number of display rows to skip -> HL = start of that row (or the end).
NoteSkip:
        ld b,a
        ld hl,NoteBuf
NskLoop:
        ld a,b
        or a
        ret z
        ld a,(hl)
        or a
        ret z
        push bc
        call NoteRowEnd
        pop bc
        dec b
        jr NskLoop

NoteDrawInterior:
        ld a,(NoteTop)
        call NoteSkip
        call NoteVisRows
        ld b,a
        ld a,2                 ; pixel row of the first text row
        ld (NoteY),a
NdLoop:
        ld a,(hl)
        or a
        ret z                  ; no more text
        push bc
        push hl
        call NoteRowEnd
        ld (NoteNext),hl
        ld a,(de)
        ld (NoteHold),a        ; the character after this row's text
        xor a
        ld (de),a              ; end the row in place, print, put it back
        pop hl
        push de
        ld a,(NoteY)
        ld b,a
        ld c,0
        call ApiWinPrint
        pop de
        ld a,(NoteHold)
        ld (de),a
        ld a,(NoteY)
        add a,8
        ld (NoteY),a
        ld hl,(NoteNext)
        pop bc
        djnz NdLoop
        ret

; A new Notes window shows the document already loaded (entry.asm empties the
; page once at start), from its first row.
NoteInit:
        xor a
        ld (NoteTop),a
        ret

; Up and Down scroll the page; every other key is ignored.
NoteKey:
        cp 11
        jr z,NkUp
        cp 10
        jr nz,NkNone
        call NoteVisRows
        ld hl,NoteTop
        add a,(hl)
        call NoteSkip          ; HL = first row below the page
        ld a,(hl)
        or a
        jr z,NkNone            ; nothing below
        ld hl,NoteTop
        inc (hl)
        ret
NkUp:
        ld hl,NoteTop
        ld a,(hl)
        or a
        jr z,NkNone
        dec (hl)
        ret
NkNone:
        ld a,2                 ; the page did not change: nothing to repaint
        ld (KeyPaint),a
        ret

; HL = basename in the selected directory (ApiOpenFile has checked it is not a
; directory). NC on success. On failure (carry, A = the kernel's error code) the
; page is left as it was: a packed file that cannot be unpacked fails the first
; read before any byte is copied.
NoteLoadAs:
        call ApiStOpen
        ret c
        ld (NoteHandle),a
        ld hl,NoteBuf
        ld bc,256
        call ApiStRead
        push af                ; carry = read error
        push bc                ; bytes read
        ld a,(NoteHandle)
        ld hl,NoteChar
        ld bc,1
        call ApiStRead         ; is there anything after the first 256?
        ld a,0
        jr c,NlNoMore
        ld a,b
        or c
NlNoMore:
        ld (NoteMore),a
        ld a,(NoteHandle)
        call ApiStClose
        pop bc
        pop af
        ret c
        ld hl,NoteBuf          ; keep new lines and printable ASCII, drop the rest
        ld d,h
        ld e,l
        ld a,b
        or c
        jr z,NlTerm
NlKeep:
        ld a,(hl)
        inc hl
        cp 10
        jr z,NlStore
        cp ' '
        jr c,NlNext
        cp 127
        jr nc,NlNext
NlStore:
        ld (de),a
        inc de
NlNext:
        dec bc
        ld a,b
        or c
        jr nz,NlKeep
NlTerm:
        ld a,(NoteMore)
        or a
        jr z,NlEnd
        ld hl,TxtTrunc
        ld bc,12
        ldir
NlEnd:
        xor a
        ld (de),a
        ld (NoteTop),a
        ret

        section data
TxtTrunc: db 10,'[truncated]'
NoteHandle: db 0
NoteChar: db 0
NoteMore: db 0
NoteY: db 0
NoteHold: db 0
NoteNext: dw 0
        section bss
NoteBuf: ds 269                ; 256 bytes, the truncation line and an end mark
NoteTop: ds 1
