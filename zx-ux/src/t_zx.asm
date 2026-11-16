; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  zxpack - the user's end of the kernel's file compressor
;
;   zxpack              what is packed, what it saves, room left
;   zxpack file ...     pack now (the kernel also packs idle files)
;   zxpack -d file ...  unpack (any read of a packed file unpacks it)
; =====================================================================
t_zxpack: db 18h,6
        dw STKRES, TV+12-UDATA, zxp_m
ZB      equ R_BUF               ; read buffer (128; no buffered reader). No room to hide a second sofa.
ZNF     equ TV                  ; packed files.
ZLOG    equ TV+2                ; their size.
ZPB     equ TV+4                ; bytes their streams take.
ZRB     equ TV+6
ZFD     equ TV+8
ZNAME   equ TV+10

; zxp_m: 32 bytes. Begin the packing job. Spare memory remains a rumor.
zxp_m:  pop hl
        call args
        ld a,1
        call argn
        jp z,zxst
        ld a,(hl)
        cp '-'
        ld a,1
        ld hl,zxpk
        jr nz,.go
        inc a
        ld hl,zxun
.xj0_16:
.xj1_5:
.xj2_2:
.xj3_1:
.go:    call each
        jp exit0

; zxpk: 54 bytes. HL = file → pack it, "file: size → packed bytes". RAM would like a refund.
zxpk:   ld (ZNAME),hl
        SC _zxpack
        jr c,zxer
        push hl
        ld hl,(ZNAME)
        ld de,U_STB
        call sc_stat
        ld hl,(ZNAME)
        call puts
        ld hl,s_zc
        call puts
        ld hl,(U_STB+6)
        call putdec
        ld hl,s_zto
        call puts
        pop hl
        call putdec
        ld hl,s_zby
        jp puts

; zxun: 28 bytes. HL = file; read one byte to trigger transparent unpacking. The kernel unwraps it.
zxun:   ld (ZNAME),hl
        ld de,0
        call sc_open
        jr c,zxer
        push hl
        ld de,ZB
        ld bc,1
        call sc_read
        pop hl
        push af
        call sc_close
        pop af
        ret nc
; zxer: 41 bytes. Report packing trouble. No false success party.
zxer:   ld de,s_znf
        cp ENOENT
        jr z,.p
        ld de,s_zbusy
        cp EBUSY
        jr z,.p
        ld de,s_zsml
        cp EFBIG
        jr z,.p
        ld de,s_zroom
        cp ENOMEM
        jr z,.p
        cp ENOSPC
        jr z,.p
        ld de,s_zno
.p:     ld hl,(ZNAME)
        jp perr

; zxst: 155 bytes. Scan arena i-nodes through /dev/mem and report packing use. RAM wants receipts.
zxst:   ld hl,s_mem
        ld de,0
        call sc_open
        jp c,exit0
        ld (ZFD),hl
        ld de,ITAB
        ld bc,0
        call sc_seek
        ld b,NINODE
.i:     push bc
        ld hl,(ZFD)
        ld de,ZB
        ld bc,32
        call sc_read
        ld a,(ZB+1)
        and 084h
        cp 084h                 ; allocated and packed.
        jr nz,.n
        ld hl,(ZNF)
        inc hl
        ld (ZNF),hl
        ld hl,(ZB+4)
        ld de,(ZLOG)
        add hl,de
        ld (ZLOG),hl
        ld hl,(ZB+30)
        ld de,(ZPB)
        add hl,de
        ld (ZPB),hl
.n:     pop bc
        djnz .i
        ld hl,(ZNF)
        call putdec
        ld hl,s_zst1
        call puts
        ld hl,(ZLOG)
        call putdec
        ld hl,s_zst2
        call puts
        ld hl,(ZPB)
        call putdec
        ld hl,s_zst3
        call puts
        ld hl,(ZLOG)
        ld de,(ZPB)
        or a
        sbc hl,de
        call putdec
        ld hl,s_zst4
        call puts
        ld hl,0                 ; the arena's free bytes.
        SC _zxpack
        call putdec
        ld hl,s_zst5
.xj0_15:
.xj1_4:
.xj2_1:
.xj0_2:
        call puts
        jp exit0

s_zc    equ m_colon             ; ": ".
s_zto:  db " -> ",0
s_zby   equ s_byte              ; " bytes\n" (stat).
s_zbusy: db "open, not packed",0
s_zsml: db "would not be smaller",0
s_zroom: db "no room",0
s_zno:  db "cannot pack",0
s_znf   equ s_nf                ; "not found" (sh).
s_zst1: db " files packed: ",0
s_zst2: db " bytes in ",0
s_zst3: db " bytes, saving ",0
s_zst4: db "; ",0
s_zst5: db " bytes free",10,0
e_zxpack:
