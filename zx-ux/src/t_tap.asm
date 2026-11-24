; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
; du [name ...] - count 128-byte file units in the RAM arena.
;  (tar and tap: t_tar.asm)
; =====================================================================

; ------------------------------------------------------------- du
DU_P    equ TV                  ; 80 path.
DU_E    equ TV+80               ; 10 entry + 0.
t_du:   db 18h,6
        dw STKRES, DU_E+11-UDATA, du_m
; du_m: 34 bytes. Count file use in the arena. Forty-eight K is strict.
du_m:   pop hl
        call args
        ld a,1
        call argn
        jr nz,.a
        ld hl,s_dot
        call .one
        jp exit0
.a:     ld a,1
        ld hl,.one
        jp zxp_m.xj0_16  
.one:   ld de,DU_P
        call strcpy             ; and on into dutree.
; dutree: 165 bytes. Count blocks beneath DU_P, including directories; return HL. Every block gets a bill.
dutree: ld hl,DU_P
        ld de,U_STB
        call sc_stat
        ld hl,0
        ret c
        ld hl,0                 ; Devices and resident programs use no file units.
        ld de,(U_STB)           ; Start at zero before checking the node.
        ld a,e
        cp ROOTINO
        jr c,.s0
        ld a,(U_STB+3)
        bit 3,a
        jr nz,.s0
        ld hl,(U_STB+6)         ; blocks = (size + 127) / 128.
        bit 2,a                 ; packed: the stream's size.
        jr z,.sz
        ld hl,(U_STB+32)
.sz:    call blocks
        rl h
        ld a,(U_STB+3)
        bit 4,a                 ; large file: + indirect block.
        jr z,.s
        inc hl
.s0:    ld a,(U_STB+3)
.s:     bit 6,a
        ret z
; directory: add its contents. The file table has no VIP section.
        push hl
        ld hl,DU_P
        ld de,0
        call sc_open
        pop de
        ex de,hl
        ret c
        push de                 ; fd.
        push hl                 ; sum.
.r:     pop hl
        pop de
        push de
        push hl
        ex de,hl
        ld de,DU_E
        call rdent
        jr c,.e
        jr z,.r
        call isdot
        jr z,.r
.d:     xor a
        ld (DU_E+10),a
; append "/name", recurse, cut again.
        ld hl,DU_P
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
        ld hl,DU_E+2
        call strcpy
        call dutree
        pop de
        xor a
        ld (de),a
        ex de,hl
        pop hl
        add hl,de
        push hl
        jr .r
.e:     pop hl                  ; sum.
        pop de                  ; fd.
        push hl
        ex de,hl
        call sc_close
        pop hl
        push hl
        ld a,5
        call putdecw
        call space
        ld hl,DU_P
        call puts
        call crlf
        pop hl
        ret
e_du:

