; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
; Arena file system: name lookup, i-nodes and file I/O.
; File blocks live in RAM, with no disk controller or block cache.
; =====================================================================

; Files and directories live in the arena (arena.asm): one block each, i.dskp pointing at its payload. The
; i-node table is ITAB; resident programs and devices have i-nodes synthesized on demand.

; ---------------------------------------------------------------------
; iget: 170 bytes. HL = node; IX = i-node, keeping HL/DE/BC. Devices 1/2/5, files 41-64, programs 128+.
iget:
        push hl
        push de
        push bc
        ld a,h
        or a
        jp nz,.bad
        ld a,l
        cp ROOTINO
        jr nc,.reg
        cp DEV_TAP
        jr z,.dev
        dec a
        cp DEV_MEM
        jp nc,.bad
        inc a
.dev:   ld ix,spino
        call .clr
        ld (ix+0),00Fh          ; rw for everybody.
        ld (ix+1),080h          ; allocated (char special).
        ld (ix+30),a            ; device number.
        jr .now
.reg:   cp ROOTINO+NINODE
        jr nc,.txt
        sub ROOTINO
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,ITAB
        add hl,de
        push hl
        pop ix
.ok:    pop bc
        pop de
        pop hl
        or a
        ret
.txt:   sub TXINO               ; resident program: from the program table.
        jr c,.bad
        cp NPROG
        jr nc,.bad
        ld l,a
        ld h,0
        ld e,a
        ld d,h
        add hl,hl
        add hl,hl
        add hl,de               ; 5 bytes an entry.
        ld de,PTAB
        add hl,de
        ld ix,txino
        call .clr
        ld a,(hl)               ; text address.
        ld (ix+I_DSKP),a
        inc hl
        ld a,(hl)
        ld (ix+I_DSKP+1),a
        inc hl
        ld a,(hl)               ; size.
        ld (ix+I_SIZE),a
        inc hl
        ld a,(hl)
        ld (ix+I_SIZE+1),a
        inc hl
        ld a,(hl)               ; extra mode bits.
        or IEXEC+IROWN+IWOWN+IROTH
        ld (ix+0),a
        ld (ix+1),088h          ; allocated, resident text.
        ld (ix+I_NLKS),1
.now:   ld hl,(systime)         ; times: now.
        ld (ix+I_MTIM),l
        ld (ix+I_MTIM+1),h
        ld hl,(systime+2)
        ld (ix+I_MTIM+2),l
        ld (ix+I_MTIM+3),h
        jr .ok
.bad:   pop bc
        pop de
        pop hl
        jp namei.xj1_26  
; .clr: clear the 32-byte i-node at IX (keeps A, HL).
.clr:   push hl
        push ix
        pop hl
        ld b,INOSZ
.z:     ld (hl),0
        inc hl
        djnz .z
        pop hl
        ret

; nami: 7 bytes. HL = path → HL = i-number, IX = i-node; CF, A = error. The directory is the map.
nami:   call namei
        ret c
        jp iget

; isspec: 11 bytes. Z if IX is a special file. There is always one.
isspec:
        push hl
        push de
        push ix
        pop hl
        ld de,spino
        jp cpbchl.xj0_3  

; setmtim: 36 bytes. Set the i-node modification time to now. Files deserve a diary.
setmtim:
        push hl
        push de
        di
        ld hl,(systime)
        ld de,(systime+2)
        ei
        res 1,(ix+1)            ; modified: may be packed again.
        ld (ix+I_RSVD),l        ; zxpack: time of the last change.
        ld (ix+I_RSVD+1),h
        ld (ix+I_MTIM),l
        ld (ix+I_MTIM+1),h
        ld (ix+I_MTIM+2),e
        ld (ix+I_MTIM+3),d
        pop de
        pop hl
        ret

; ---------------------------------------------------------------------
; ialloc: 37 bytes. Find a free i-node; HL = number, IX = cleared node, or CF/A = ENOSPC. Small cupboard.
ialloc:
        push de
        push bc
        ld ix,ITAB
        ld hl,ROOTINO
        ld b,NINODE
        ld de,INOSZ
.l:     bit 7,(ix+1)
        jr z,.got
        add ix,de
        inc hl
        djnz .l
        pop bc
        pop de
        jp writei.xj0_9  
.got:   call iget.clr
        pop bc
        pop de
        or a
        ret

; ifree: 12 bytes. HL = i-number; release the i-node. No ghost tenants.
ifree:  call iget
        ld (ix+0),0
        ld (ix+1),0
        ret

; ---------------------------------------------------------------------
; itrunc: 35 bytes. IX = i-node; drop its contents (u5 'itrunc'). Keep its name, lose its baggage.
itrunc:
        call isspec
        ret z
        bit 3,(ix+1)            ; resident text: stays as it is.
        ret nz
        push hl
        call idskp
        call afree
        xor a
        ld (ix+I_DSKP),a
        ld (ix+I_DSKP+1),a
        ld (ix+I_SIZE),a
        ld (ix+I_SIZE+1),a
        res 2,(ix+1)            ; not packed.
        pop hl
        ret

; ---------------------------------------------------------------------
; readi / writei (u6) IX = i-node; u_off, u_base, u_count → u_nread, u_off advanced. CF on error.
; ---------------------------------------------------------------------
; readi: 60 bytes. Route devices, unpack files and stop at EOF. No phantom bytes.
readi:
        ld hl,0
        ld (u_nread),hl
        call isspec
        jp z,devread
        call zunpack            ; packed: unpack first (resident text.
        ret c                   ; never is).
        call isize
        ld de,(u_off)
        or a
        sbc hl,de
        ret z                   ; at the end: 0 bytes.
        ccf
        ret nc                  ; past the end: 0 bytes, no error.
        ld de,(u_count)
        call minhlde
        ld b,h
        ld c,l
        call idskp
        ld de,(u_off)
        add hl,de
        ld de,(u_base)
        ld a,b
        or c
        ret z
        push bc
        ldir
        pop hl
        jp iadv

; writei: 216 bytes. Route devices, reject resident code, grow data and zero gaps. RAM is not elastic.
writei:
        ld hl,0
        ld (u_nread),hl
        call isspec
        jp z,devwrite
        bit 3,(ix+1)
        jr z,.wr
        ld a,EACCES             ; pure text is read only.
        scf
        ret
.wr:    call zunpack
        ret c
        ld hl,(u_count)
        ld a,h
        or l
        jp z,.done
        ld de,(u_off)
        add hl,de               ; HL = end of the write.
        ld a,EFBIG
        ret c
        push hl
        call idskp
        ld bc,0
        ld a,h
        or l
        call nz,acap
        pop hl
        call cpbchl
        jr nc,.fits
; grow: a new block with a quarter to spare, else just enough.
        push hl
        ld b,h
        ld c,l
        srl b
        rr c
        srl b
        rr c
        add hl,bc
        jr c,.ex                ; end + end/4 overflowed.
        ld bc,16
        add hl,bc
        ld b,h
        ld c,l
        jr c,.ex
        ld a,K_FILE
        call aalloc
        jr nc,.new
.ex:    pop bc
        push bc
        ld a,K_FILE
        call aalloc
        jr nc,.new
        pop hl
.xj0_9:
        ld a,ENOSPC
        scf
        ret
.new:   ; the old contents (the old block may have moved: reload it).
        push hl
        ex de,hl
        call idskp
        push hl
        ld c,(ix+I_SIZE)
        ld b,(ix+I_SIZE+1)
        ld a,b
        or c
        jr z,.nc
        ldir
.nc:    pop hl
        call afree
        pop hl
        ld (ix+I_DSKP),l
        ld (ix+I_DSKP+1),h
        pop hl
.fits:  ; zeros between the end of the file and the write offset.
        call isize
        ld de,(u_off)
        call cphlde
        jr nc,.cp
        push hl
        ex de,hl
        or a
        sbc hl,de
        ld b,h
        ld c,l                  ; gap.
        pop hl
        ld e,(ix+I_DSKP)
        ld d,(ix+I_DSKP+1)
        add hl,de
.zg:    ld (hl),0
        inc hl
        dec bc
        ld a,b
        or c
        jr nz,.zg
.cp:    call idskp
        ld de,(u_off)
        add hl,de
        ex de,hl
        ld hl,(u_base)
        ld bc,(u_count)
        push bc
        ldir
        pop hl
        call iadv
        ld hl,(u_off)           ; grow the file.
        ld e,(ix+I_SIZE)
        ld d,(ix+I_SIZE+1)
        call cphlde
        jr c,.done
        ld (ix+I_SIZE),l
        ld (ix+I_SIZE+1),h
.done:  call setmtim
        or a
        ret

; iadv: 33 bytes. Move u_off, u_base and u_nread forward by HL; subtract HL from u_count. No lost bytes.
iadv:
        ex de,hl
        ld hl,(u_off)
        add hl,de
        ld (u_off),hl
        ld hl,(u_base)
        add hl,de
        ld (u_base),hl
        ld hl,(u_nread)
        add hl,de
        ld (u_nread),hl
        ld hl,(u_count)
        or a
        sbc hl,de
        ld (u_count),hl
        or a
        ret

; addea: 5 bytes. Add an offset. Addresses never move by magic.
addea:  add a,e
        ld e,a
        ret nc
        inc d
        ret

; iio: 18 bytes. IX = node, HL = offset, DE = buffer, BC = count, A = read 0 or write 1. Pick a lane.
iio:
        ld (u_off),hl
        ld (u_base),de
        ld (u_count),bc
        or a
        jp z,readi
        jp writei

; ---------------------------------------------------------------------
; namei: 256 bytes. HL = path; return node or CF. Set u_pdir/u_name/u_dirp for the last path entry. No
; shortcuts.
namei:
        ld de,0FFFFh
        ld (u_pdir),de
        ld a,(hl)
        cp '/'
        jr nz,.rel
        ld de,ROOTINO
        jr .st
.rel:   ld de,(u_cdir)
.st:    ld (u_nmi),de
.sk:    ld a,(hl)
        cp '/'
        jr nz,.c0
        inc hl
        jr .sk
.c0:    or a
        jr nz,.comp
        jp namei.xj0_43  
.comp:  ; component → u_name (8 chars, zero padded). No free pass for a dodgy value.
        ld de,u_name
        ld b,8
.cp:    ld a,(hl)
        or a
        jr z,.pad
        cp '/'
        jr z,.pad
        inc hl
        dec b
        inc b
        jr z,.cp
        ld (de),a
        inc de
        dec b
        jr .cp
.pad:   inc b
        dec b
        jr z,.sl
        xor a
.pz:    ld (de),a
        inc de
        djnz .pz
.sl:    ld a,(hl)
        cp '/'
        jr nz,.sl2
        inc hl
        jr .sl
.sl2:   ld (u_nmp),hl
        or a
        ld a,0
        jr nz,.sl3
        inc a
.sl3:   ld (u_nlast),a
; search the directory (an error below leaves no parent: creat, mkdir and link must not write into the last
; directory searched).
        ld hl,0FFFFh
        ld (u_pdir),hl
        ld hl,(u_nmi)
        call iget
        ret c
        bit 6,(ix+1)            ; IFDIR.
        jr nz,.dir
        ld a,ENOTDIR
        scf
        ret
.dir:   ld (u_pdir),hl
        ld hl,0FFFFh
        ld (u_nfree),hl
        ld hl,0
.e:     ld e,(ix+I_SIZE)
        ld d,(ix+I_SIZE+1)
        call cphlde
        jr nc,.nf
        push hl
        ld de,u_dirbuf
        ld bc,10
        xor a
        call iio
        pop hl
        ld de,(u_dirbuf)
        ld a,d
        or e
        jr z,.empty
        push hl
        ld hl,u_dirbuf+2
        ld de,u_name
        ld b,8
.cm:    ld a,(de)
        cp (hl)
        jr nz,.ne
        inc hl
        inc de
        djnz .cm
        pop hl
; Found the name. Even a crowded directory can cooperate.
        ld (u_dirp),hl
        ld hl,(u_dirbuf)
        ld (u_nmi),hl
        ld a,(u_nlast)
        or a
        jr nz,.fnd
        ld hl,(u_nmp)
        ld a,(hl)
        jp .c0
.xj0_43:
.fnd:   ld hl,(u_nmi)
        or a
        ret
.ne:    pop hl
.nx:    ld de,10
        add hl,de
        jr .e
.empty: ld de,(u_nfree)
        inc de
        ld a,d
        or e
        jr nz,.nx
        ld (u_nfree),hl
        jr .nx
.nf:    ld a,(u_nlast)
        or a
        jr z,.nfi
        ld de,(u_nfree)
        inc de
        ld a,d
        or e
        jr z,.nf1
        ld hl,(u_nfree)
.nf1:   ld (u_dirp),hl
        jr namei.xj0_58  
.nfi:   ld hl,0FFFFh
        ld (u_pdir),hl
.xj0_58:
.xj1_26:
        ld a,ENOENT
        scf
        ret

; wdir: 33 bytes. HL = i-number → directory entry u_name in u_pdir at u_dirp. A name needs a slot.
wdir:
        ld (u_dirbuf),hl
        ld hl,u_name
        ld de,u_dirbuf+2
        call ldir8
        ld hl,(u_pdir)
        call iget
        ret c
        ld hl,(u_dirp)
        ld de,u_dirbuf
        ld bc,10
        ld a,1
        jp iio

; pdirw: 14 bytes. Check that u_pdir exists and is writable; CF/A reports trouble. No trespassing.
pdirw:
        ld hl,(u_pdir)
        inc hl
        ld a,h
        or l
        ld a,ENOENT
        scf
        ret z
        dec hl
        jp iget

; maknod: 62 bytes. DE = mode bits → HL = i-number, IX = i-node (u2 'maknod'). All the little fields get
; seats.
maknod:
        push de
        call ialloc
        pop de
        ret c
        ld a,d
        or 080h
        ld (ix+1),a
        ld (ix+0),e
        ld (ix+I_NLKS),1
        call setmtim
        ld a,(ix+I_MTIM)
        ld (ix+I_CTIM),a
        ld a,(ix+I_MTIM+1)
        ld (ix+I_CTIM+1),a
        ld a,(ix+I_MTIM+2)
        ld (ix+I_CTIM+2),a
        ld a,(ix+I_MTIM+3)
        ld (ix+I_CTIM+3),a
        push hl
        call wdir
        pop hl
        jr c,.f
        jp iget
.f:     push af
        call ifree
        pop af
        ret

; ---------------------------------------------------------------------
; open file table (u2 'getf', 'fclose'; u7 'iopen', 'iclose').
; ---------------------------------------------------------------------
; getf: 20 bytes. HL = fd → HL = fsp entry; CF/EBADF. No ticket, no service.
getf:
        ld a,h
        or a
        jr nz,gfbad
        ld a,l
        cp NUFILE
        jr nc,gfbad
        ld hl,u_fp
        call addhla
        ld a,(hl)
        or a
        jr z,gfbad
        dec a
; fspent: 12 bytes. Pick the file-table entry. Every slot is numbered.
fspent: ld l,a                  ; A = index → HL = fsp + 6*A.
        add a,a
        add a,l
        add a,a
        ld hl,fsp
        call addhla
        or a
        ret
; gfbad: 4 bytes. Bad file handle? Show it the door.
gfbad:  ld a,EBADF
        scf
        ret

; fget: 9 bytes. HL = fsp entry → device selected, IX = i-node. Match the ticket.
fget:
        push hl
        call ldind
        call iget
        pop hl
        ret

; fopen: 73 bytes. HL = i-number, A = F_READ/F_WRITE → HL = fd. Keep count of the tab.
fopen:
        ld c,a
        ex de,hl
        ld hl,u_fp
        ld b,0
.f:     ld a,(hl)
        or a
        jr z,.gf
        inc hl
        inc b
        ld a,b
        cp NUFILE
        jr c,.f
        ld a,EMFILE
        scf
        ret
.gf:    push hl
        ld hl,fsp+4
        xor a
.s:     push af
        ld a,(hl)
        or a
        jr z,.gs
        pop af
        push de
        ld de,FSPSZ
        add hl,de
        pop de
        inc a
        cp NFILES
        jr c,.s
        pop hl
        ld a,ENFILE
        scf
        ret
.gs:    ld (hl),1               ; count.
        inc hl
        ld (hl),c               ; flags.
        dec hl
        dec hl
        ld (hl),0
        dec hl
        ld (hl),0
        dec hl
        ld (hl),d
        dec hl
        ld (hl),e
        pop af
        inc a
        pop hl
        ld (hl),a
        ld l,b
        ld h,0
        or a
        ret

; fclosea: 82 bytes. A = fd (v1 'fclose'). Return its chair.
fclosea:
        ld hl,u_fp
        call addhla
        ld a,(hl)
        or a
        ret z
        ld (hl),0
        dec a
        call fspent
        push hl
        ld de,4
        add hl,de
        dec (hl)
        pop hl
        ret nz
; Last reference gone. Time to clear the seat.
        push hl
        ld de,5
        add hl,de
        ld a,(hl)
        ld (hl),0
        pop hl
        push af
        call fget
        pop bc
        ret c
        ld a,(ix+I_NLKS)        ; Free an unlinked file on its last close.
        or a                    ; No links means no excuses.
        jr z,.del
; trim the file's block to its size.
        call isspec
        ret z
        ld a,(ix+1)
        and 0Ch                 ; resident text, packed: leave alone.
        ret nz
        call idskp
        ld a,h
        or l
        ret z
        ld c,(ix+I_SIZE)
        ld b,(ix+I_SIZE+1)
        jp ashrink
.del:   call ldind              ; HL = i-number.
        call isopen             ; another fsp entry still has it.
        ret nz
        call itrunc
        jp ifree

; fpdup: 24 bytes. Fork duplicates file references, not file contents. Two tickets, one file.
fpdup:
        ld hl,u_fp
        ld b,NUFILE
.l:     ld a,(hl)
        or a
        jr z,.n
        push hl
        dec a
        call fspent
        ld de,4
        add hl,de
        inc (hl)
        pop hl
.n:     inc hl
        djnz .l
        ret

; isopen: 38 bytes. HL = i-number → NZ if the file is open, DE → its fsp flags. No secret guests.
isopen:
        ld de,fsp
        ld b,NFILES
.l:     push hl
        ld a,(de)
        cp l
        jr nz,.n
        inc de
        ld a,(de)
        dec de
        cp h
        jr nz,.n
        ld hl,4
        add hl,de
        ld a,(hl)
        or a
        jr z,.n
        inc hl
        ex de,hl
        pop hl
        ret
.n:     pop hl
        ld a,FSPSZ
        call addea
        djnz .l
        xor a
        ret

; ---------------------------------------------------------------------
; file system calls.
; ---------------------------------------------------------------------
; sysopen: 37 bytes. Open by name. Directories still have rules.
sysopen:                        ; HL = name, DE = mode 0 r 1 w 2 rw.
        ld (u_tmp),de
        call nami
        jp c,syserr
        ld a,(u_tmp)
        ld c,F_READ
        or a
        jr z,.r
        ld c,F_WRITE
        dec a
        jr z,.w
        ld c,F_READ+F_WRITE
.w:     bit 6,(ix+1)
        ld a,EISDIR
        jp nz,syserr
.r:     ld a,c
        jr syscreat.xj0_7  

; syscreat: 59 bytes. Create a file. First find somewhere to put it.
syscreat:                       ; HL = name, DE = mode.
        ld (u_tmp),de
        call namei
        jr c,.new
        call iget
        jp c,syserr
        bit 6,(ix+1)
        ld a,EISDIR
        jp nz,syserr
        call itrunc
        jr .op
.new:   call pdirw
        jp c,syserr
        ld de,(u_tmp)
        ld a,e
        and 03Fh
        ld e,a
        ld d,0
        call maknod
        jp c,syserr
.op:    ld a,F_WRITE
.xj0_7:
        call fopen
        jp sysmkdir.xj1_14  

; sysclose: 15 bytes. Close the handle. The tab is settled.
sysclose:
        push hl
        call getf
        pop hl
        jp c,syserr
        ld a,l
        call fclosea
        jp sysok

; sysread: 3 bytes. Read through the shared path. Less code, same bytes.
sysread:
        xor a
        jr rw
; syswrite: 2 bytes. Write through the shared path. One door is enough.
syswrite:
        ld a,1
; rw: 73 bytes. Do the read or write. The count is the receipt.
rw:     ld (u_fdi),a
        push de
        push bc
        call getf
        jr c,.e2
        ld (u_ino),hl
        push hl
        ld de,5
        add hl,de
        ld a,(u_fdi)
        inc a                   ; F_READ / F_WRITE.
        and (hl)
        pop hl
        jr nz,.ok
        ld a,EBADF
.e2:    pop bc
        pop de
        jp syserr
.ok:    call fget
        pop bc
        pop de
        jp c,syserr
        inc hl
        inc hl
        call ldind
        ld a,(u_fdi)
        call iio
        jp c,syserr
        ld hl,(u_ino)
        inc hl
        inc hl
        ld de,(u_off)
        ld (hl),e
        inc hl
        ld (hl),d
        ld hl,(u_nread)
        jp sysok

; sysseek: 54 bytes. Move the file cursor. No miles actually traveled.
sysseek:                        ; HL = fd, DE = offset, BC = 0 abs 1 rel 2 end.
        push de
        push bc
        call getf
        pop bc
        pop de
        jp c,syserr
        ld (u_ino),hl
        ld a,c
        or a
        jr z,.set
        dec a
        jr nz,.end
        inc hl
        inc hl
        call ldind
        add hl,de
        ex de,hl
        jr .set
.end:   push de
        call fget
        pop de
        jp c,syserr
        call isize
        add hl,de
        ex de,hl
.set:   ld hl,(u_ino)
        inc hl
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
.xj0_57:
        ex de,hl
        jp sysok

; systell: 14 bytes. Report the file cursor. It knows where it is.
systell:
        call getf
        jp c,syserr
        inc hl
        inc hl
        call ldind
        jp sysok

; syslink: 51 bytes. Make another name for a file. Two signs, one door.
syslink:                        ; HL = existing, DE = new name.
        ld (u_tmp),de
        call nami
        jp c,syserr
        ld (u_ino),hl
        ld hl,(u_tmp)
        call namei
        ld a,EEXIST
        jp nc,syserr
        call pdirw
        jp c,syserr
        ld hl,(u_ino)
        call wdir
        jp c,syserr
        ld hl,(u_ino)
        call iget
        inc (ix+I_NLKS)
        jp sysok

; sysunlink: 62 bytes. Remove a name. The file keeps no souvenirs.
sysunlink:                      ; HL = name.
        call nami
        jp c,syserr
        ld (u_ino),hl
        call pdirw
        jp c,syserr
; clear the directory entry.
        ld hl,0
        ld (u_tmp),hl
        ld hl,(u_dirp)
        ld de,u_tmp
        ld bc,2
        ld a,1
        call iio
; drop a link.
        ld hl,(u_ino)
        call iget
        dec (ix+I_NLKS)
        jp nz,sysok
        call isopen             ; still open: freed by the last close.
        jp nz,sysok
        call itrunc
        call ifree
        jp sysok

; syschdir: 21 bytes. Change directory. The path gets a new starting point.
syschdir:
        call nami
        jp c,syserr
        bit 6,(ix+1)
        ld a,ENOTDIR
        jp z,syserr
        ld (u_cdir),hl
        jp sysok

; sysmkdir: 37 bytes. Make a directory. The family tree grows one branch.
sysmkdir:                       ; HL = name, DE = mode.
        ld (u_tmp),de
        call namei
        ld a,EEXIST
        jp nc,syserr
        call pdirw
        jp c,syserr
        ld de,(u_tmp)
        ld a,e
        and 03Fh
        ld e,a
        ld d,040h               ; IFDIR.
        call maknod
.xj1_14:
        jp c,syserr
        jp sysok

; syschmod: 28 bytes. Change the permission bits. The bouncer takes notes.
syschmod:                       ; HL = name, DE = mode.
        ld (u_tmp),de
        call nami
        jp c,syserr
        ld a,(ix+0)
        and 0C0h
        ld b,a
        ld a,(u_tmp)
        and 03Fh
        or b
        ld (ix+0),a
        jp sysok

; sysmdate: 35 bytes. Change the date stamp. The clock may object.
sysmdate:                       ; HL = name, DE = time low, BC = time high.
        ld (u_tmp),de
        ld (u_tmp2),bc
        call nami
        jp c,syserr
        ld hl,(u_tmp)
        ld (ix+I_MTIM),l
        ld (ix+I_MTIM+1),h
        ld hl,(u_tmp2)
        ld (ix+I_MTIM+2),l
        ld (ix+I_MTIM+3),h
        jp sysok

; sysstat: 14 bytes. Ask for file details. A name is not the whole story.
sysstat:                        ; HL = name, DE = 34 byte buffer.
        push de
        call namei
        pop de
        jp c,syserr
        call iget
        jp c,syserr
; stat1: 17 bytes. Pack the stat record. All fields pay their rent.
stat1:  ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ex de,hl
        push ix
        pop hl
        ld bc,INOSZ
        ldir
        jp sysok

; sysfstat: 21 bytes. Ask by open handle. No need to look up the name.
sysfstat:                       ; HL = fd, DE = buffer.
        push de
        call getf
        pop de
        jp c,syserr
        push de
        call fget
        pop de
        jp c,syserr
        call ldind
        jr stat1

