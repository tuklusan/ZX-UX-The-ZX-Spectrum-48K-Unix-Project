; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  tar - tape archiver on the Spectrum cassette
;
;   tar c[v]f /dev/cassette/label file ...   write an archive
;   tar t[v]f /dev/cassette/label [file ...] list it
;   tar x[v]f /dev/cassette/label [file ...] extract it (or some files)
;   tap r|t|x [file ...]                     v1 'tap', same archives
;
;  t with no archive name (tap t) lists the whole tape: each program as
;  /dev/cassette/NAME, each archive as /dev/cassette/LABEL: and its
;  members, until BREAK.
;
;  Directories are archived with everything below them.  Extracting
;  replaces existing files without asking and makes missing directories.
;  Packed files travel as their packed stream and come back packed.
;
;  Tape format: standard Spectrum blocks, so tape browsers show names.
;   archive  header "label", CODE, length 0, p1 = 'A', p2 = "RU"
;   member   header "basename", CODE, length n, p1 = 'F', p2 = "RU",
;            then n bytes in blocks of up to 1024 (old tapes use 512).
;            A 17-byte payload gets one pad byte; 17 is a header size:
;              kind (1 packed, 2 directory), i-node flags (2),
;              size (2), stored bytes (2), mtime (4), path, 0, data
;   end      header "", CODE, length 0, p1 = 'E', p2 = "RU"
; =====================================================================
TP_FD   equ TV                  ; tape fd.
TP_F    equ TV+2                ; member file fd (FFFF: none).
TP_K    equ TV+4                ; c t x.
TP_A    equ TV+5                ; first file argument.
TP_V    equ TV+6                ; verbose.
TP_IN   equ TV+7                ; inside the wanted archive.
TP_N    equ TV+8                ; member bytes still on tape.
TP_W    equ TV+10               ; tape buffer fill pointer.
TP_S    equ TV+12               ; payload bytes still to send.
TP_BK   equ TV+14               ; packed stream block number.
TP_RD   equ TV+16               ; /dev/mem fd (packed streams, i-nodes).
TP_ONE  equ TV+18               ; 0: t without a name, the whole tape.
TP_X    equ TV+19               ; the file existed (extract).
TP_ERR  equ TV+20               ; write failed (extract).
TP_I    equ TV+21               ; argument scan index.
TP_LB   equ TV+22               ; 10 archive label.
TP_HD   equ TV+32               ; 17 tape header.
TP_PH   equ TV+49               ; 11 member preamble (path follows).
TP_E    equ TV+50               ; 10 directory entry (saving only).
TP_P    equ TV+60               ; 80 path.
TP_SB   equ R_BUF               ; 128 staging block (saving only: the extract's mkdir1 is the R_BUF user).
TP_FMT  equ TV+140              ; active archive: 03h or 05h.
TP_OPEN equ TV+141              ; saw A, awaiting E.
TP_B    equ TV+142              ; largest supported tape block.
TPBSZ   equ 1024
PRE     equ 11                  ; preamble before the path.

t_tar:  db 18h,6
        dw STKRES, TP_B+TPBSZ-UDATA, tar_m
; tar_m: 136 bytes. Start the archiver. The cassette brought its timetable.
tar_m:  pop hl
        call args
        ld hl,TP_LB             ; no label: any archive.
        ld b,10
.sp:    ld (hl),' '
        inc hl
        djnz .sp
        xor a
        ld (TP_V),a
        call argn               ; called as tap?
        call basenm
        inc hl
        inc hl
        ld a,(hl)
        cp 'p'
        jr nz,.tar
        ld (TP_V),a             ; tap: v1 lists what it does.
.tar:   ld a,1
        call argn
        jr z,tpuse
        ld b,2                  ; next argument.
.k:     ld a,(hl)
        inc hl
        or a
        jr z,.kd
        cp 'v'
        jr nz,.k1
        ld (TP_V),a
        jr .k
.k1:    cp 'f'
        jr nz,.k2
        push hl
        push bc
        ld a,b
        call argn
        jr z,tpuse
        call tparc
        pop bc
        pop hl
        inc b
        jr .k
.k2:    cp 'r'                  ; tap r = tar c.
        jr nz,.k3
        ld a,'c'
.k3:    ld (TP_K),a
        jr .k
.kd:    ld a,b
        ld (TP_A),a
        ld hl,s_tap
        ld de,2
        call sc_open
        ld (TP_FD),hl
        jp c,tperr
        ld hl,s_mem
        ld de,2
        call sc_open
        ld (TP_RD),hl
        ld a,(TP_K)
        cp 'c'
        jr z,tpcrt
        cp 't'
        jp z,tpget
        cp 'x'
        jp z,tpget
; tpuse: 6 bytes. Print the tape command rules. The syntax gets a vote.
tpuse:  ld hl,s_taru
        jp usage

; tparc: 56 bytes. HL = /dev/cassette[/label] or /dev/tap[/label]; find the tape archive. Rewind, perhaps.
tparc:  ld (TP_W),hl
        ld de,s_cas
        call tppfx
        jr z,.ok
        ld hl,(TP_W)
        ld de,s_tap
        call tppfx
        jr nz,.bad
.ok:    ld a,(hl)
        or a
        ret z
        cp '/'
        jr nz,.bad
        inc hl
        ld de,TP_LB
        ld b,10
.l:     ld a,(hl)
        or a
        ret z
        ld (de),a
        inc hl
        inc de
        djnz .l
        ret
.bad:   ld hl,(TP_W)
        ld de,s_tpnc
.xj1_3:
        call perr
        jp tpex1

; tppfx: 9 bytes. HL = string, DE = prefix → Z and HL after it if it starts so. No name games.
tppfx:  ld a,(de)
        or a
        ret z
        cp (hl)
        ret nz
        inc hl
        inc de
        jr tppfx

; ---------------------------------------------------------------------
; write an archive.
; ---------------------------------------------------------------------
; tpcrt: 48 bytes. Start a new archive. The tape gets a heading.
tpcrt:  ld a,(TP_A)
        call argn
        jr z,tpuse
        ld a,'A'                ; archive header: the label.
        ld hl,TP_LB
        call tphead
        ld a,(TP_A)
        ld hl,.one
        call each
        ld hl,0                 ; end of the archive.
        ld (TP_N),hl
        ld a,'E'
        ld hl,s_tpnil
        call tphead
        jp exit0
.one:   ld de,TP_P
        call strcpy
; tpsv: 124 bytes. Archive TP_P and everything below it if it is a directory. No one gets left on shore.
tpsv:   ld hl,TP_P
        ld de,U_STB
        call sc_stat
        jr nc,.ok
        ld hl,TP_P
.xj0_14:
        ld de,s_tpnf
        jp perr
.ok:    ld hl,(U_STB)
        ld de,ROOTINO
        or a
        sbc hl,de
        jr c,.skip              ; a device.
        ld a,(U_STB+3)
        bit 3,a                 ; a resident program.
        jp z,.go
.skip:  ld hl,TP_P
        ld de,s_tpsk
        jp perr
.go:    call tpobj
        ld a,(U_STB+3)
        bit 6,a
        ret z
        ld hl,TP_P              ; a directory: its entries.
        ld de,0
        call sc_open
        ret c
        push hl
.e:     pop hl
        push hl
        ld de,TP_E
        call rdent
        jr c,.x
        jr z,.e                 ; free slot.
        call isdot              ; not "." or "..".
        jr z,.e
.sub:   ld hl,TP_P              ; path/name, then cut it off again.
        call strlen
        add hl,bc
        push hl
        dec hl
        ld a,(hl)
        inc hl
        cp '/'
        jr z,.ns
        ld (hl),'/'
        inc hl
.ns:    ex de,hl
        ld hl,TP_E+2
        call ldir8
        xor a
        ld (de),a
        call tpsv
        pop hl
        ld (hl),0
        jr .e
.x:     pop hl
.xj0_47:
.xj1_18:
        jp sc_close

; tpobj: 204 bytes. Write one member header, details and bytes; U_STB holds its i-node. The reel gets the lot.
tpobj:  ld hl,TP_PH
        ld a,(U_STB+3)
        ld c,0
        bit 2,a
        jr z,.k1
        inc c                   ; packed.
.k1:    bit 6,a
        jr z,.k2
        set 1,c                 ; directory.
.k2:    ld (hl),c
        inc hl
        ld de,(U_STB+2)         ; i-node flags.
        call tpw16
        ld de,(U_STB+6)         ; size.
        call tpw16
        bit 0,c                 ; Packed files keep their stream length.
        jr z,.k3                ; Directories carry no file data.
        ld de,(U_STB+32)
.k3:    bit 1,c
        jr z,.k4
        ld de,0
.k4:    ld (TP_S),de
        call tpw16
        ex de,hl
        ld hl,U_STB+28          ; mtime (the path follows in TP_P).
        ld bc,4
        ldir
        ld hl,TP_P              ; preamble and path → the tape block.
        call strlen
        ld hl,PRE+1
        add hl,bc               ; preamble length.
        ld b,h
        ld c,l
        push hl
        ld hl,TP_PH
        ld de,TP_B
        ldir
        ld (TP_W),de
        pop hl                  ; member length = preamble + stored.
        ld de,(TP_S)
        add hl,de
        ld (TP_N),hl
        ld hl,TP_P
        call basenm
        ld a,(hl)
        or a
        jp nz,.h
        ld hl,TP_P              ; "/".
.h:     ld a,'F'
        call tphead
        call tpvl
        ld a,(TP_PH)
        rra
        jr c,.pk
        rra
        jr c,.done              ; directory: no data.
        ld hl,TP_P              ; plain file: read it.
        ld de,0
        call sc_open
        jr c,.done
        ld (TP_F),hl
.r:     call tpnb
        jr z,.rc
        push bc
        ld hl,(TP_F)
        ld de,TP_SB
        call sc_read
        pop bc
        call tpcopy
        jr .r
.rc:    ld hl,(TP_F)
        call sc_close
        jr .done
.pk:    ld hl,0                 ; Copy the packed stream in chunks from RAM.
        ld (TP_BK),hl           ; Start at chunk zero.
.p:     call tpnb
        jr z,.done
        push bc
        call tpblk
        pop bc
        call tpcopy
        ld hl,(TP_BK)
        inc hl
        ld (TP_BK),hl
        jr .p
.done:  jr tpflush

; tpw16: 5 bytes. DE → (HL), HL += 2. Even tape needs a little order.
tpw16:  ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ret

; tpnb: 12 bytes. BC = next piece of the payload (up to 128); Z if none left. The reel has limits.
tpnb:   ld hl,(TP_S)
        ld bc,128
        call tpmin
        ld a,b
        or c
        ret

; tpmin: 9 bytes. BC = min(HL, BC). The reel is finite.
tpmin:  push hl
        or a
        sbc hl,bc
        pop hl
        ret nc
        ld b,h
        ld c,l
        ret

; tpcopy: 27 bytes. BC bytes from TP_SB to the tape. Do not leave bits behind.
tpcopy: ld hl,(TP_S)
        or a
        sbc hl,bc
        ld (TP_S),hl
        ld hl,TP_SB
.l:     ld a,b
        or c
        ret z
        ld a,(hl)
        inc hl
        push hl
        push bc
        call tpput
        pop bc
        pop hl
        dec bc
        jr .l

; tpput: 15 bytes. A → tape buffer, sent when full. It has a strict limit.
tpput:  ld hl,(TP_W)
        ld (hl),a
        inc hl
        ld (TP_W),hl
        ld de,TP_B+TPBSZ
        or a
        sbc hl,de
        ret nz
; tpflush: 19 bytes. Empty the tape buffer. The reel takes it from here.
tpflush:
        ld hl,(TP_W)
        ld de,TP_B
        ld (TP_W),de
        or a
        sbc hl,de
        ret z
        ld b,h
        ld c,l
        call tp17
; tpwr: 7 bytes. DE, BC → one tape block. No instant replay.
tpwr:   ld hl,(TP_FD)
        call sc_write
        ret nc
; tperr: 6 bytes. Tape error. The reel has spoken.
tperr:  ld hl,s_tperr
        call eputs
.xj0_13:
.xj1_2:
.xj2_0:
.xj3_0:
; tpex1: 3 bytes. Leave the tape command. No long goodbye.
tpex1:  jp ldx_m.xj0_1  

; tp17: 13 bytes. BC = 17 → 18 (a 17 byte block would be a header). Tape is fussy.
tp17:   ld a,b
        or a
        ret nz
        ld a,c
        cp 17
        ret nz
        inc c
        xor a
        ld (TP_B+17),a          ; deterministic ignored padding byte.
        ret

; tphead: 58 bytes. A = kind, HL = name → header block, length TP_N. Old formats have rules.
tphead: push hl
        ld hl,TP_HD
        ld (hl),5               ; new RU archive header type.
        inc hl
        ld b,10
.s:     ld (hl),' '
        inc hl
        djnz .s
        ld de,(TP_N)
        call tpw16
        ld (hl),a               ; p1: kind.
        inc hl
        ld (hl),80h
        inc hl
        ld (hl),'R'             ; p2: "RU".
        inc hl
        ld (hl),'U'
        pop hl
        ld de,TP_HD+1
        ld b,10
.n:     ld a,(hl)
        or a
        jr z,.w
        cp ' '
        jr z,.w
        ld (de),a
        inc hl
        inc de
        djnz .n
.w:     ld de,TP_HD
        ld bc,17
        jr tpwr

; tpblk: 17 bytes. Copy packed-file piece TP_BK (128-byte units) from i.dskp into TP_SB. Tape comes later.
tpblk:  ld hl,(TP_BK)
        call rdoff
        ld de,(U_STB+8)
        add hl,de
        ld de,TP_SB
        ld bc,128
; rdat: 20 bytes. HL = address (/dev/mem), DE = buffer, BC = count → read. Tape comes later.
rdat:   push bc
        push de
        ex de,hl
        ld hl,(TP_RD)
        ld bc,0
        call sc_seek
        pop de
        pop bc
        ld hl,(TP_RD)
.xj0_46:
        jp sc_read
; rdoff: 6 bytes. HL = piece → HL = its byte offset. Keep the place.
rdoff:  ld b,7
.m:     add hl,hl
        djnz .m
        ret

; tpvl: 5 bytes. Print member kind, size and path from TP_PH/TP_P in verbose mode. Otherwise, silence.
tpvl:   ld a,(TP_V)
        or a
        ret z
; tpls: 39 bytes. List what is on tape. No thumbnails in 1982.
tpls:   ld a,(TP_PH)
        ld c,'-'
        rra
        jr nc,.a
        ld c,'z'
.a:     rra
        jr nc,.b
        ld c,'d'
.b:     ld a,c
        call putc
        ld hl,(TP_PH+3)
        ld a,6
        call putdecw
        call space
        ld hl,TP_P
.xj0_12:
.xj1_1:
        call puts
        jp crlf

; ---------------------------------------------------------------------
; list or extract.
; ---------------------------------------------------------------------
; tpget: 295 bytes. Read the next archive member. Bring patience.
tpget:  ld a,(TP_LB)             ; t and no archive name: the whole tape.
        sub ' '
        ld b,a
        ld a,(TP_K)
        sub 't'
        or b
        ld (TP_ONE),a
        xor a
        ld (TP_OPEN),a
.go:    xor a
        ld (TP_IN),a
.h:     ld de,TP_HD             ; next header (other blocks are passed).
        ld bc,17
        ld hl,(TP_FD)
        call sc_read
        jr c,.h
        ld a,(TP_ONE)
        or a
        call z,tpprg            ; whole tape: programs too.
        ld a,(TP_HD)             ; accept both archive header versions.
        cp 3
        jr z,.typ
        cp 5
        jp nz,.h
.typ:   ld hl,(TP_HD+15)
        ld de,'R'+256*'U'
        or a
        sbc hl,de
        jp nz,.h
        ld a,(TP_HD+14)         ; p1 high byte must be 80h.
        cp 80h
        jp nz,.h
        ld a,(TP_HD+13)
        cp 'A'
        jr nz,.f
        ld hl,(TP_HD+11)
        ld a,h
        or l
        jp nz,tperr             ; A has no following data.
        ld a,(TP_OPEN)
        or a
        jp nz,tperr             ; archive A before previous E.
        ld a,(TP_HD)
        ld (TP_FMT),a
        ld a,1
        ld (TP_OPEN),a
        ld a,(TP_ONE)           ; whole tape: every archive, by name.
        or a
        jr nz,.lb
        call tpcas
        ld a,':'
        call putc
        call crlf
        jr .in
.lb:    ld hl,TP_LB             ; an archive: is it the one?
        ld de,TP_HD+1
        ld b,10
        ld a,(hl)
        cp ' '
        jr z,.in                ; no label asked for: the first one.
.lc:    ld a,(de)
        cp (hl)
        jp nz,.h
        inc hl
        inc de
        djnz .lc
.in:    ld a,1
        ld (TP_IN),a
        jp .h
.f:     cp 'E'
        jr nz,.m
        call tpcheck            ; E must use the current archive version.
        ld hl,(TP_HD+11)
        ld a,h
        or l
        jp nz,tperr
        xor a
        ld (TP_OPEN),a
        ld a,(TP_ONE)           ; whole tape: on to the next one.
        or a
        jp z,.go
        ld a,(TP_IN)
        or a
        jp nz,exit0
        jp .h
.m:     cp 'F'
        jp nz,.h
        call tpcheck            ; reject orphan and mixed archive members. The failure gets a name, not a
                                ; disguise.
        ld hl,(TP_HD+11)
        ld a,h
        or l
        jp z,tperr
        ld hl,(TP_HD+11)
        ld (TP_N),hl
        call tpnext             ; the preamble: keep it.
        ld hl,TP_B
        ld de,TP_PH
        ld bc,PRE+80
        ldir
        ld a,(TP_IN)
        or a
        jr z,.dr
        call tpsel
        jr nz,.dr
        ld a,(TP_K)
        cp 'x'
        jr z,.x
        ld a,(TP_V)             ; t: names, or the long form with v.
        or a
        jr nz,.tv
        ld hl,TP_P
        call puts
        call crlf
        jr .dr
.tv:    call tpls
.dr:    call tpdrain
        jp .h
.x:     ld hl,s_tpextract
        call puts
        ld hl,TP_P            ; exact selected archive member name.
        call puts
        call crlf
        call tpext
        jp .h

; tpcheck: 18 bytes. Reject orphan F/E blocks and mixed 03h/05h archive kinds. The tape obeys one format.
tpcheck:
        ld a,(TP_OPEN)
        or a
        jp z,tperr
        ld a,(TP_FMT)
        ld hl,TP_HD
        cp (hl)
        jp nz,tperr
        ret

; tpprg: 25 bytes. Recognize an SS CODE header; report /dev/cassette/NAME. Old labels do useful work.
tpprg:  ld hl,(TP_HD+15)
        ld de,'S'+256*'S'
        sbc hl,de
        ret nz
        ld a,(TP_HD)
        cp 3
        jr z,.pr
        cp 4
        ret nz
.pr:    call tpcas
        jp crlf

; tpcas: 33 bytes. /dev/cassette/NAME, the name in the header in TP_HD (/dev/cassette alone for an archive
; saved without a name). The tape sets the speed.
tpcas:  ld hl,s_cas
        call puts
        ld a,(TP_HD+1)
        cp '!'
        ret c
        ld a,'/'
        call putc
        ld hl,TP_HD+1
        ld b,10
.c:     ld a,(hl)
        cp '!'
        ret c                   ; the name ends at a space.
        call putc
        inc hl
        djnz .c
        ret

; tpnext: 69 bytes. Fetch the next member block into TP_B; set BC to its length and TP_W to its end. Reel on.
tpnext: ld hl,(TP_N)
        ld bc,512               ; legacy 03h/RU chunk.
        ld a,(TP_FMT)
        cp 5
        jr nz,.sz
        ld bc,TPBSZ             ; current 05h/RU chunk.
.sz:    call tpmin
        ld hl,(TP_N)
        or a
        sbc hl,bc
        ld (TP_N),hl
        push bc
        call tp17
        ld de,TP_B
        ld hl,(TP_FD)
        call sc_read
        pop bc
        jp c,tperr
        ld a,b
        or a
        jr nz,.padok
        ld a,c
        cp 17
        jr nz,.padok
        ld a,(TP_B+17)
        or a
        jp nz,tperr             ; ignored 18th byte must be zero.
.padok: ld hl,TP_B
        add hl,bc
        ld (TP_W),hl
        ret

; tpdrain: 11 bytes. Skip the unread part of a tape member. The motor still has the last word.
tpdrain:
        ld hl,(TP_N)
        ld a,h
        or l
        ret z
        call tpnext
        jr tpdrain

; tpsel: 48 bytes. Z if the member is wanted (no names given, or its path is a name given or lies under one).
; No free extras.
tpsel:  ld a,(TP_A)
        ld (TP_I),a
        call argn
        jr nz,.l
        xor a
        ret
.l:     ld de,TP_P
.c:     ld a,(hl)
        or a
        jr z,.e
        ld b,a
        ld a,(de)
        cp b
        jr nz,.n
        inc hl
        inc de
        jr .c
.e:     ld a,(de)
        or a
        ret z
        cp '/'
        ret z
.n:     ld hl,TP_I
        inc (hl)
        ld a,(hl)
        call argn
        jr nz,.l
        or 1
        ret

; tpext: 204 bytes. Extract a member using TP_PH, TP_P and first block TP_B. The files need a home.
tpext:  call tpvl
        ld hl,TP_P+1        ; make the missing directories.
.d:     ld a,(hl)
        or a
        jr z,.dd
        cp '/'
        jr nz,.dn
        ld (hl),0
        push hl
        call tpmk
        pop hl
        ld (hl),'/'
.dn:    inc hl
        jr .d
.dd:    ld a,(TP_PH)
        bit 1,a
        jr z,.fl
        call tpmk               ; a directory.
        jp .attr
.fl:    ld hl,TP_P          ; a file: replace it, no questions.
        ld de,U_STB
        call sc_stat
        ld a,0
        jr c,.new
        inc a
.new:   ld (TP_X),a
        xor a
        ld (TP_ERR),a
        ld hl,TP_P
        ld de,0Eh
        call sc_creat
        jr nc,.op
        ld hl,0FFFFh
        ld a,1
        ld (TP_ERR),a
.op:    ld (TP_F),hl
        ld hl,TP_B+PRE          ; the data in the first block.
        call strlen
        add hl,bc
        inc hl
        ex de,hl
        ld hl,(TP_W)
        or a
        sbc hl,de
        ld b,h
        ld c,l
        call tpout
.mo:    ld hl,(TP_N)            ; and in the others.
        ld a,h
        or l
        jr z,.cl
        call tpnext
        ld de,TP_B
        call tpout
        jr .mo
.cl:    ld hl,(TP_F)
        inc h
        jr z,.ng
        dec h
        call sc_close
.ng:    ld a,(TP_ERR)
        or a
        jr z,.ok
        ld hl,TP_P          ; no room: do not leave half a file.
        call sc_unlink
        ld hl,TP_P
        ld de,s_tpfull
        jp perr
.ok:    ld a,(TP_X)
        or a
        jr z,.pk
        ld hl,TP_P
        ld de,s_tprep
        call perr
.pk:    ld a,(TP_PH)             ; a packed stream: mark it packed.
        rra
        call c,tpadopt
.attr:  ld hl,TP_P          ; mode and modification time.
        ld a,(TP_PH+1)
        ld e,a
        ld d,0
        SC _chmod
        ld hl,TP_P
        ld de,(TP_PH+7)
        ld bc,(TP_PH+9)
        SC _mdate
        ret

; tpmk: 13 bytes. Create directory TP_P if absent. One branch in the tree at a time.
tpmk:   ld hl,TP_P
        call isdir
        ret nc
        ld hl,TP_P
        jp mkdir1

; tpout: 28 bytes. Write DE/BC bytes to the member file; keep draining even after an error. Tape waits for no
; one.
tpout:  ld a,b
        or c
        ret z
        ld a,(TP_ERR)
        or a
        ret nz
        ld hl,(TP_F)
        push bc
        call sc_write
        pop bc
        jr c,.e
        or a
        sbc hl,bc
        ret z
.e:     ld a,1
        ld (TP_ERR),a
        ret

; tpadopt: 95 bytes. Mark a restored packed stream through /dev/mem; save logical and stored sizes. Bit by bit.
tpadopt:
        ld hl,TP_P
        ld de,U_STB
        call sc_stat
        ret c
        ld hl,U_STB+3
        set 2,(hl)
        ld hl,(TP_PH+3)
        ld (U_STB+6),hl
        ld hl,(TP_PH+5)
        ld (U_STB+32),hl
        ld de,1                 ; flags (high byte).
        ld bc,1
        call .w
        ld de,4                 ; size.
        ld bc,2
        call .w
        ld de,30                ; stored length.
        ld bc,2
; .w: i-node bytes DE.., BC of them, from the stat buffer.
.w:     push bc
        push de
        ld hl,(U_STB)
        push de
        ld de,-ROOTINO
        add hl,de
        ld b,5
.m:     add hl,hl
        djnz .m
        pop de
        add hl,de
        ld de,ITAB
        add hl,de
        ex de,hl
        ld hl,(TP_RD)
        ld bc,0
        call sc_seek
        pop de
        ld hl,U_STB+2
        add hl,de
        ex de,hl
        pop bc
        ld hl,(TP_RD)
.xj0_45:
.xj1_17:
        jp sc_write

s_tpextract: db "Extracting: ",0
s_taru: db "tar [ctx][v]f /dev/cassette/name [file...]",0
s_tap:  db "/dev/tap",0
s_cas:  db "/dev/cassette",0
s_tpnc: db "not a cassette",0
s_tpnf  equ s_nf                ; "not found" (sh).
s_tpsk: db "not archived",0
s_tperr: db "tape error",10,0
s_tpfull: db "not written",0
s_tprep: db "replaced",0
s_tpnil equ s_null              ; "".
e_tar:
