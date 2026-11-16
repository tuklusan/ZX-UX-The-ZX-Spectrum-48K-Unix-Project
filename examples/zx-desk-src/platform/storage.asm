; ZXDesk directory functions use ZX-UX filesystem calls, read-only.
; Directory records in ZX-UX are ten bytes (inode + eight-byte name).
; The two Commander panes are backend 0 = /bin and backend 1 = /usr/doc.
        section text
        global ApiStSelect
        global ApiStIdent
        global ApiStDir
        global ApiStDirOpen
        global ApiStDirNext
        global ApiStDirClose
        global ApiStOpen
        global ApiStRead
        global ApiStClose
        extern zx_syscall
ApiStSelect:
        cp 2
        jr nc,StBad
        ld (StBackend),a
        or a
        ret
StBad:
        scf
        ret
ApiStIdent:
        ld a,(StBackend)
        ret
; Directory streaming: one open directory at a time. ApiStDirOpen, then
; ApiStDirNext for each entry (HL = its name, carry at the end or on an error),
; then ApiStDirClose.
ApiStDirOpen:
        ld hl,StBin
        ld a,(StBackend)
        or a
        jr z,SdPath
        ld hl,StDoc
SdPath:
        ld de,0
        ld a,5
        call zx_syscall
        jr c,SdBad
        ld (StFD),hl
        ret
SdBad:
        ld hl,$ffff            ; later reads and the close just fail
        ld (StFD),hl
        scf
        ret
ApiStDirNext:
        ld hl,(StFD)
        ld de,StEntry
        ld bc,10
        ld a,3
        call zx_syscall
        ret c
        ld a,l
        cp 10
        jr nz,SdEnd
        ld hl,(StEntry)
        ld a,h
        or l
        jr z,ApiStDirNext      ; an unused slot
        ld hl,StEntry+2
        ld de,StName
        ld bc,8
        ldir
        xor a
        ld (StName+8),a
        ld hl,StName
        ret
SdEnd:
        scf
        ret
ApiStDirClose:
        ld hl,(StFD)
        ld a,6
        jp zx_syscall
; A = zero-based entry index in the selected directory; returns HL=name,
; carry past the end.
ApiStDir:
        push af                ; the open call may change every register
        call ApiStDirOpen
        pop bc
        ret c
        ld c,b                 ; C = how many entries to skip
SdSkip:
        push bc
        call ApiStDirNext
        pop bc
        jr c,SdIdxEnd
        ld a,c
        or a
        jr z,SdIdxFound
        dec c
        jr SdSkip
SdIdxFound:
        push hl
        call ApiStDirClose
        pop hl
        or a
        ret
SdIdxEnd:
        call ApiStDirClose
        scf
        ret
; HL=basename (up to 8 bytes) -> HL=absolute path in the selected directory.
StPath:
        push hl
        ld hl,StBinPrefix
        ld a,(StBackend)
        or a
        jr z,StPathPfx
        ld hl,StDocPrefix
StPathPfx:
        ld de,StFilePath
StPfxCopy:
        ld a,(hl)
        or a
        jr z,StPfxDone
        ld (de),a
        inc hl
        inc de
        jr StPfxCopy
StPfxDone:
        pop hl
        ld b,8
StPathLoop:
        ld a,(hl)
        or a
        jr z,StPathEnd
        ld (de),a
        inc de
        inc hl
        djnz StPathLoop
StPathEnd:
        xor a
        ld (de),a
        ld hl,StFilePath
        ret

; ZXDesk's original file interface returns the descriptor in A; ZX-UX returns
; it in HL. Carry retains the kernel's error status. HL=name; read-only.
ApiStOpen:
        call StPath
        ld de,0
        ld a,5
        call zx_syscall
        ret c
        ld a,l
        or a
        ret
; A=fd, HL=buffer, BC=count; out BC=count (or carry).
ApiStRead:
        ld e,l
        ld d,h
        ld l,a
        ld h,0
        ld a,3
        call zx_syscall
        ld b,h
        ld c,l
        ret
ApiStClose:
        ld l,a
        ld h,0
        ld a,6
        jp zx_syscall
        section data
StBackend: db 0
StFD: dw 0
StBin: db '/bin',0
StDoc: db '/usr/doc',0
StBinPrefix: db '/bin/',0
StDocPrefix: db '/usr/doc/',0
StFilePath: ds 18               ; '/usr/doc/' + 8 + end mark
StEntry: ds 10
StName: ds 9
