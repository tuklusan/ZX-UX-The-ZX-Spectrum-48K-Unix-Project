; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
; zxpack - transparent compression of files in the shared arena.
;
;  Files are stored as raw bytes or packed streams: IFPACK set, i.size
;  is still the logical length and the blocks hold a zxpack stream whose
;  length is kept in the spare i-node word I_RSVD.  For raw files I_RSVD
;  holds the time of the last change or unpack (setmtim, zunpack).
;
;  - any read or write of a packed file unpacks it in place first
;    (readi/writei), so programs never see the packed form;
;  - when the system is idle, closed files that have not been touched
;    for ZAGE seconds are packed in the background (swtch);
;  - when RAM runs short, aalloc tries packing closed files;
;  - sys zxpack packs one file on request.
;
;  Codec: LZ77 with a 2K window; every decision is coded with an adaptive
;  binary range coder (16-bit, renormalised bit by bit, carries added into
;  the output already written; 8-bit probabilities).  tools/zxpack.py is the bit-exact reference.  Encoder
;  and decoder share the model: zbit codes the bit in CF when encoding
;  and returns the decoded bit in CF when decoding.
;  A file is one arena block, so packing encodes it straight into a
;  workspace block that then becomes the file; unpacking decodes the
;  stream into a new block of the logical size.
; =====================================================================

ZWIN    equ 2048                ; LZ window.
ZAGE    equ 15                  ; seconds before an idle file is packed.
ZENC    equ 001h                ; zmode: encode (also the empty out byte).
ZDEC    equ 080h                ; decode (also the empty in byte).

; work area: the model and the coder state below the window (see unix.asm); everything else in free low
; memory (kvars.inc).
zp_lit  equ ZXW                 ; 8-bit literal tree (1..255).
ZXWSZ   equ 256                 ; just below the window.
; ZLO4 (beside the kernel stack): the rest of the model, coder state. One push too many and the party ends.
zp_mr   equ ZLO4                ; match, repeat flags [previous token]. The answer is either right or
                                ; embarrassing.
zp_len  equ ZLO4+6              ; gamma: lengths.
zp_off  equ ZLO4+38             ; gamma: offset / 16.
zp_olo  equ ZLO4+70             ; 4-bit tree: offset % 16.
ZPNUM   equ 342                 ; probabilities in all.
zsz     equ ZLO4+86             ; coder: interval size.
zv      equ ZLO4+88             ; decode: value - low; encode: low.
zrep    equ ZLO4+90             ; last match offset.
zip     equ ZLO4+92             ; stream offset.
zop     equ ZLO4+94             ; output pointer / offset.
zst     equ ZLO4+96             ; previous token type.
ZSTATE  equ 11                  ; zsz..zst cleared by zinit.
        ASSERT zst+1 == KV2END
; dead kernel-variable slots.
zt_typ  equ KV+111              ; token: 0 literal, 1 match, 2 repeat. A guess is not a comparison.
zt_lit  equ KV+236
zt_len  equ KV+237              ; word.
zt_off  equ KV+243              ; word.
; ZLO1: the unpack i-node.
txino   equ ZLO1                ; i-node of a resident program (iget).
; ZLO2 holds encoder state. Even squeezed files need a desk.
zolim   equ ZLO2+0              ; encoder: output limit.
zib     equ ZLO2+2              ; input buffer.
zie     equ ZLO2+4              ; its end.
zob     equ ZLO2+6              ; output buffer.
zp      equ ZLO2+8              ; position.
zq      equ ZLO2+10             ; scratch position.
zbl     equ ZLO2+12             ; longest match: length.
zbusy   equ ZLO2+14             ; codec in use (no nesting).
; ZLO3: encoder, unpack, shared. No sightseeing through this branch.
zbo     equ ZLO3+0              ; longest match: offset.
zrl     equ ZLO3+2              ; parse: repeat length.
zL      equ ZLO3+4              ; match length.
zO      equ ZLO3+6              ; match offset.
zsp     equ ZLO3+8              ; encoder stack (abort).
zsrc    equ ZLO3+10             ; packed i-node being unpacked.
zn      equ ZLO3+12             ; logical length.
zidlem  equ ZLO3+14             ; packing from the idle loop.
zacc    equ ZLO3+15             ; bit buffer with a sentinel bit.
zmode   equ ZLO3+16
        ASSERT zbusy < MEMBOT+30
        ASSERT zmode < KARGS
        ASSERT txino+INOSZ <= KV2

; ---------------------------------------------------------------------
; zbit: 137 bytes. HL = zero-bit probability, CF = input bit in encode mode; return bit in CF. One at a time.
zbit:   push de
        push bc
        push hl
        sbc a,a
        ld c,a                  ; bit to code (00/FF).
.rn:    ld hl,(zsz)             ; renormalise: size >= 8000h.
        bit 7,h
        jr nz,.go
        add hl,hl
        ld (zsz),hl
        ld hl,(zv)
        ld a,(zmode)
        rra
        jr c,.ro
        call zinb               ; decode: shift a stream bit in.
        adc hl,hl
        jr .rs
.ro:    add hl,hl               ; encode: shift the top bit of low out. Arithmetic still expects exact
                                ; change.
        call zoutb
.rs:    ld (zv),hl
        jr .rn
.go:    ex de,hl
        pop hl
        push hl
        ld a,(hl)               ; A:HL = size * p.
        ld hl,0
        ld b,8
.mu:    add hl,hl
        rla
        jr nc,.ms
        add hl,de
        adc a,0
.ms:    djnz .mu
        ld l,h
        ld h,a
        ex de,hl                ; DE = t = size * p / 256, HL = size.
        ld a,(zmode)
        rra
        jr c,.e
        push hl                 ; decode: bit = (v >= t).
        ld hl,(zv)
        sbc hl,de
        ccf
        sbc a,a
        ld c,a
        pop hl
.e:     ld a,c
        or a
        jr z,.b0
        sbc hl,de               ; 1: size -= t; v -= t / low += t.
        ld (zsz),hl
        ld hl,(zv)
        ld a,(zmode)
        rra
        jr c,.ea
        sbc hl,de
        jr .s1
.ea:    add hl,de
        call c,zcarry
.s1:    ld (zv),hl
        pop hl
        push hl
        ld a,(hl)               ; p -= p / 16.
        call zsh4
        neg
        jr .pu
.b0:    ld (zsz),de             ; 0: size = t, p += (256 - p) / 16.
        pop hl
        push hl
        ld a,(hl)
        neg
        call zsh4
.pu:    add a,(hl)
        ld (hl),a
        ld a,c
        add a,a
        pop hl
        pop bc
        pop de
        ret

; zsh4: 7 bytes. Shift four bits. A tiny nudge, nothing more.
zsh4:   rrca
        rrca
        rrca
        rrca
        and 0Fh
        ret

; zcarry: 24 bytes. Carry overflow into bits already written. No lost luggage.
zcarry: push hl
        ld hl,zacc
        ld a,(hl)
        inc a
        and (hl)
        jr z,.ov
        inc (hl)                ; the partial byte took it.
        jr .x
.ov:    srl (hl)                ; Overflow turns the ones to zeros.
        inc (hl)                ; Keep a sentinel and carry on.
        ld hl,(zop)
.c:     dec hl
        inc (hl)
        jr z,.c
.x:     pop hl
        ret

; zoutb: 32 bytes. CF = bit → stream; abort when the output limit is reached. Eight make a byte.
zoutb:  push hl
        push de
        ld hl,zacc
        rl (hl)
        jr nc,.x
        ld a,(hl)
        ld (hl),ZENC
        ld hl,(zop)
        ld de,(zolim)
        call cphlde
        jr nc,zfull
        ld (hl),a
        inc hl
        ld (zop),hl
.x:     pop de
        pop hl
        ret
; zfull: 2 bytes. Buffer is full. The packer has no spare pocket.
zfull:  ld a,EFBIG              ; not smaller than the raw file.
; zabort: 6 bytes. Stop packing cleanly. Bad bytes go nowhere.
zabort: ld sp,(zsp)             ; leave zenc with CF, A = reason.
        scf
        ret

; zinb: 22 bytes. Return the next compressed stream bit in CF. Eight still make a byte.
zinb:   ld a,(zacc)
        add a,a
        jr nz,.ok
        push hl
        ld hl,(zip)
        ld a,(hl)
        inc hl
        ld (zip),hl
        pop hl
        scf
        adc a,a
.ok:    ld (zacc),a
        ret

; ztree: 19 bytes. HL = probabilities, B = bit count, C = left-aligned value; return code in A. Branch office.
ztree:  ld e,1
.l:     push hl
        ld a,e
        call addhla
        sla c
        call zbit
        pop hl
        rl e
        djnz .l
        ld a,e
        ret

; zgamma: 50 bytes. HL = model, DE = value at least 1; code it and return DE. Even lengths cost bits.
zgamma: push ix
        push de
        pop ix
        ld b,0
        ld a,(zmode)
        rra
        jr nc,.go
        ld a,16                 ; drop the leading 1, count the rest.
.al:    dec a
        add ix,ix
        jr nc,.al
        ld b,a
.go:    ld de,1
.lp:    ld a,b                  ; another bit?
        cp 1
        ccf
        call zbit
        jr nc,.x
        inc hl
        add ix,ix
        call zbit               ; the bit.
        rl e
        rl d
        inc hl
        dec b
        jr .lp
.x:     pop ix
        ret

; ztoken: 144 bytes. Encode or decode the token in zt_typ/zt_lit/zt_len/zt_off. Bits do the talking.
ztoken: ld a,(zst)
        add a,a
        ld hl,zp_mr
        call addhla
        ld a,(zt_typ)
        cp 1
        ccf
        call zbit
        jr c,.mt
        ld a,(zt_lit)           ; literal.
        ld c,a
        ld b,8
        ld hl,zp_lit
        call ztree
        ld (zt_lit),a
        ld de,1
        xor a
        jr .st
.mt:    inc hl
        ld a,(zt_typ)
        cp 2
        ccf
        call zbit
        ld hl,(zt_len)
        dec hl
        jr c,.rp
        dec hl
        push hl
        ld hl,(zt_off)          ; match: offset / 16 + 1, offset % 16. This check has a right to be fussy.
        dec hl
        ld a,l
        add a,a
        add a,a
        add a,a
        add a,a
        ld c,a
        ld b,4
.s4:    srl h
        rr l
        djnz .s4
        inc hl
        ex de,hl
        ld hl,zp_off
        call zgamma
        ex de,hl
        dec hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        push hl
        ld b,4
        ld hl,zp_olo
        call ztree
        and 0Fh
        pop hl
        call addhla
        inc hl
        ld (zrep),hl
        pop de                  ; length - 2.
        ld hl,zp_len
        call zgamma
        inc de
        ld a,1
        jr .s1
.rp:    ex de,hl                ; repeat: length - 1.
        ld hl,zp_len
        call zgamma
        ld a,2
.s1:    inc de
.st:    ld (zt_len),de
        ld (zt_typ),a
        ld (zst),a
        ret

; zinit: 38 bytes. A = ZENC / ZDEC → fresh model and coder. Start with a clean slate.
zinit:  ld (zmode),a
        ld (zacc),a
        ld hl,zp_lit            ; all probabilities 1/2.
        ld a,080h
        ld b,0
        call zfill
        ld hl,zp_mr
        ld b,ZPNUM-256
        call zfill              ; → HL = zsz.
        xor a
        ld b,ZSTATE
        call zfill
        dec a
        ld (zsz),a
        ld (zsz+1),a
        ret

; zfill: 5 bytes. HL = buffer, B = count (zero means 256), A = fill byte. Every bit gets a seat.
zfill:  ld (hl),a
        inc hl
        djnz zfill
        ret

; ---------------------------------------------------------------------
; zdec: 81 bytes. Unpack compressed bytes from zib into zob up to zn. The stream pays its debt.
zdec:   ld a,ZDEC
        call zinit
        ld hl,(zob)
        ld (zop),hl
        ld hl,(zib)
        ld (zip),hl
        ld b,16
.v:     call zinb
        adc hl,hl
        djnz .v
        ld (zv),hl
.lp:    ld hl,(zop)
        ld de,(zn)
        call cphlde
        ret nc
        call ztoken
        ld bc,(zt_len)
.c:     ld a,(zt_typ)
        or a
        ld a,(zt_lit)
        jr z,.p
        ld hl,(zop)
        ld de,(zrep)
        sbc hl,de
        ld a,(hl)
.p:     ld hl,(zop)
        ld (hl),a
        inc hl
        ld (zop),hl
        dec bc
        ld a,b
        or c
        jr nz,.c
        jr .lp

; ---------------------------------------------------------------------
; zenc: 250 bytes. Pack [zib, zie) into zob (limit zolim); CF/A = EFBIG or EINTR. Squeeze, then breathe.
zenc:   ld (zsp),sp
        ld a,ZENC
        call zinit
        ld hl,(zob)
        ld (zop),hl
        ld hl,(zib)
.lp:    ld (zp),hl
        ld de,(zie)
        call cphlde
        jp nc,.fin
        ld a,(zidlem)
        or a
        call nz,zpoll
        ld hl,(zp)              ; repeat match length.
        ld de,(zib)
        or a
        sbc hl,de
        ex de,hl
        ld hl,(zrep)
        dec hl
        call cphlde             ; 0 < rep <= p - zib.
        ld bc,0
        jr nc,.r0
        ld hl,(zp)
        ld de,(zrep)
        or a
        sbc hl,de
        ld de,(zp)
        call zmlen
.r0:    ld (zrl),bc
        ld hl,(zp)              ; longest match.
        call zfind
        ld hl,(zbo)
        ld (zO),hl
        ld hl,(zbl)
        ld (zL),hl
        ld a,h
        or l
        jr z,.dec
        ex de,hl                ; lazy: a longer match one byte later?
        ld hl,(zrl)
        call cphlde
        jr nc,.dec
        ld hl,(zp)
        inc hl
        ld de,(zie)
        call cphlde
        jr nc,.dec
        call zfind
        ld hl,(zL)
        inc hl
        ld de,(zbl)
        call cphlde
        jr nc,.dec
        ld hl,0
        ld (zL),hl
        ld (zrl),hl
.dec:   ld hl,(zrl)             ; repeat if rl >= 2 and rl + 1 >= L.
        ld de,2
        call cphlde
        jr c,.nr
        inc hl
        ld de,(zL)
        call cphlde
        jr c,.nr
        ld hl,(zrl)
        ld a,2
        jr .tk
.nr:    ld hl,(zO)
        ld (zt_off),hl
        ld hl,(zL)
        ld a,h
        or l
        ld a,1
        jr nz,.tk
        ld hl,(zp)              ; literal.
        ld a,(hl)
        ld (zt_lit),a
        ld hl,1
        xor a
.tk:    ld (zt_len),hl
        ld (zt_typ),a
        call ztoken
        ld hl,(zp)
        ld de,(zt_len)
        add hl,de
        jp .lp
.fin:   ld b,16                 ; flush: the 16 bits of low.
.f:     ld hl,(zv)
        add hl,hl
        ld (zv),hl
        call zoutb
        djnz .f
.pad:   ld a,(zacc)             ; and complete the last byte.
        cp ZENC
        ret z
        call zoutb
        jr .pad

; zmlen: 20 bytes. HL = earlier position, DE = position → BC = equal run (to zie). Close does not count.
zmlen:  ld bc,0
.l:     push hl
        ld hl,(zie)
        or a
        sbc hl,de
        pop hl
        ret z
        ld a,(de)
        cp (hl)
        ret nz
        inc hl
        inc de
        inc bc
        jr .l

; zfind: 89 bytes. HL = position; set zbl = longest match, zbo = offset. Nearest wins ties. No cheating.
zfind:  ld (zq),hl
        ld de,(zib)
        or a
        sbc hl,de
        ld de,ZWIN
        call minhlde
        ld b,h
        ld c,l
        ld hl,2
        ld (zbl),hl
        ld hl,(zq)
        dec hl
.s:     ld a,b
        or c
        jr z,.x
        ld de,(zq)
        ld a,(de)
        cpdr
        jr nz,.x
        push bc
        push hl
        inc hl                  ; candidate.
        push hl
        inc hl
        inc de
        call zmlen
        inc bc
        ld hl,(zbl)
        or a
        sbc hl,bc
        pop de
        jr nc,.nb
        ld (zbl),bc
        ld hl,(zq)
        or a
        sbc hl,de
        ld (zbo),hl
.nb:    pop hl
        pop bc
        jr .s
.x:     ld hl,(zbl)
        dec hl
        dec hl
        ld a,h
        or l
        ret nz
        ld (zbl),hl
        ret

; zpoll: 17 bytes. Stop idle packing when any job can run. RAM can wait its turn.
zpoll:  ld hl,p_stat
        ld b,NPROC
.l:     ld a,(hl)
        cp SRUN
        ld a,EINTR
        jp z,zabort
        inc hl
        djnz .l
        ret

; ---------------------------------------------------------------------
; zpack: 112 bytes. IX = closed raw file; NC means packed, CF/A gives ENOMEM, EFBIG or EINTR. Tight squeeze.
zpack:  push ix
        ld a,1
        ld (zbusy),a
        call isize
        ld (zn),hl
        ld b,h                  ; workspace: as big as the file, else.
        ld c,l                  ; half that, a quarter... (the stream.
.al:    push bc                 ; is usually half the size or less).
        ld a,K_TEMP
        call aalloc
        pop bc
        jr nc,.got
        srl b
        rr c
        ld a,b
        or a
        jr nz,.al
        ld a,ENOMEM
        jr zfail
.got:   ld (zob),hl
        add hl,bc
        ld de,-8                ; the stream must save 8 bytes at least.
        add hl,de
        ld (zolim),hl
        call idskp              ; reload: the allocation may have moved the file.
        ld (zib),hl
        ld de,(zn)
        add hl,de
        ld (zie),hl
        call zenc
        jr c,zpfail
        ld hl,(zop)             ; stream length.
        ld de,(zob)
        or a
        sbc hl,de
        ld (ix+I_RSVD),l
        ld (ix+I_RSVD+1),h
        ld b,h
        ld c,l
        call idskp              ; the raw block goes.
        call afree
        ld hl,(zob)             ; the workspace becomes the file.
        call ashrink
        dec hl
        dec hl
        ld (hl),K_FILE
        inc hl
        inc hl
        ld (ix+I_DSKP),l
        ld (ix+I_DSKP+1),h
        set 2,(ix+1)            ; IFPACK.
; zdone: 10 bytes. Finish the packed stream. Close the box properly.
zdone:  ld hl,(zn)
        ld (ix+I_SIZE),l
        ld (ix+I_SIZE+1),h
        xor a
; zret: 9 bytes. Return the result. Flags carry the news.
zret:   push af
        xor a
        ld (zbusy),a
        pop af
        pop ix
        ret
; zpfail: 8 bytes. Packing failed. Do not call it a feature.
zpfail: push af
        ld hl,(zob)
        call afree
        pop af
; zfail: 11 bytes. Packing failed. The bytes say so.
zfail:  cp EFBIG
        jr nz,.e
        set 1,(ix+1)            ; incompressible: do not try again.
.e:     scf
        jr zret

; ---------------------------------------------------------------------
; zunpack: 86 bytes. IX = i-node; unpack if needed, CF/A = ENOSPC on failure. No extra cupboard.
zunpack:
        bit 2,(ix+1)
        ret z
        push ix
        call isize
        ld b,h
        ld c,l
        ld a,K_FILE
        call aalloc             ; may pack other files to make room.
        ld a,ENOSPC
        jr c,zfail
        ld (zob),hl
        ex de,hl
        call isize              ; not zn: a file packed meanwhile set it.
        add hl,de
        ld (zn),hl              ; zn = end of the output.
        ld a,1
        ld (zbusy),a
        call idskp              ; the stream (reloaded after allocating).
        ld (zib),hl
        push hl
        ld hl,(zob)
        push hl
        call zdec
        pop de                  ; new block.
        pop hl                  ; stream block.
        call afree
        ld (ix+I_DSKP),e
        ld (ix+I_DSKP+1),d
        res 2,(ix+1)
        ld hl,(systime)
        ld (ix+I_RSVD),l
        ld (ix+I_RSVD+1),h
        ld hl,(zn)              ; size = end - start.
        or a
        sbc hl,de
        ld (zn),hl
        jr zdone

; ---------------------------------------------------------------------
; zok: 66 bytes. IX = i-node, HL = i-number → NC if it may be packed now. No shortcuts.
zok:    call isspec
        jr z,.inv
        ld a,(ix+1)
        xor 080h
        and 0CEh                ; allocated, not dir/text/packed/tried.
        jr nz,.inv
        ld a,(ix+I_SIZE+1)
        or a
        jr nz,.sz
        ld a,(ix+I_SIZE)
        cp 129
        ld a,EFBIG
        ret c
.sz:    call isopen             ; open files stay raw.
        ld a,EBUSY
        scf
        ret nz
        ld a,(zidlem)           ; idle packing: leave recent files alone.
        or a
        ret z
        push hl
        ld hl,(systime)
        ld e,(ix+I_RSVD)
        ld d,(ix+I_RSVD+1)
        sbc hl,de
        ld de,ZAGE
        call cphlde
        pop hl
        ld a,EBUSY
        ret
.inv:   ld a,EINVAL
        scf
        ret

; zscan: 27 bytes. Pack the first suitable file, or return CF if none. No hoarding.
zscan:  ld hl,ROOTINO
.l:     call iget
        ret c
        call zok
        jr c,.n
        push hl
        call zpack
        pop hl
        ret nc
        cp EINTR
        jr nz,.n
        or a
        ret
.n:     inc hl
        jr .l

; zidle: 14 bytes. With interrupts on, pack an idle file; CF if none. Even a nap has chores.
zidle:  ld a,1
        ld (zidlem),a
        call zpress
        ld a,0
        ld (zidlem),a
        ret

; zpress: 14 bytes. If the arena is full, try packing a closed file; CF if none, IX kept. RAM says no.
zpress: ld a,(zbusy)
        or a
        scf
        ret nz
        push ix
        call zscan
        pop ix
        ret

; syszx: 69 bytes. HL = file name: pack it, return stream size; HL = 0: return free bytes and DE = free nodes.
; Two jobs, one tight little system call.
syszx:  ld a,h
        or l
        jr nz,.f
        call afreeb
        push hl
        ld ix,ITAB
        ld bc,NINODE*256
        ld de,INOSZ
.i:     bit 7,(ix+1)
        jr nz,.u
        inc c
.u:     add ix,de
        djnz .i
        ld e,c
        ld d,b
.xj0_8:
        pop hl
        jp sysok
.f:     call nami
        jp c,syserr
        bit 2,(ix+1)
        jr nz,.len
        res 1,(ix+1)            ; asked for: try again.
        call zok
        call nc,zpack
        jp c,syserr
.len:   ld l,(ix+I_RSVD)
        ld h,(ix+I_RSVD+1)
        jp sysok
