; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  arena - the elastic memory of ZX-UX v1
;
;  AR0..a_top holds files, directories, saved jobs and loaded images.
;  Block header: size word (even, includes header), kind byte, spare byte.
;  Files and saves move during compaction; loaded images stay put.
;  The kernel updates i.dskp and p_save after moves. Old pointers are toast.
;  The window may be lent to a large image. RAM does not grow on trees.
; =====================================================================

; aalloc: 65 bytes. BC = payload bytes, A = kind; HL = block or CF/A = ENOMEM. Compact, then pack if full.
aalloc: ld (a_kind),a
        ld hl,5
        add hl,bc
        jr c,.nom
        res 0,l
        ld (a_need),hl
        ld a,2
        ld (a_try),a
.again: call afind
        ret nc
        ld hl,a_try
        dec (hl)
        jr nz,.cmp
; no room even compacted: pack a closed file and try again.
        ld hl,(a_need)
        push hl
        ld a,(a_kind)
        push af
        call zpress
        pop bc
        pop hl
        jr c,.nom
        ld (a_need),hl
        ld a,b
        ld (a_kind),a
        ld a,1
        ld (a_try),a
.cmp:   call acompact
        jr .again
.xj0_7:
.xj1_0:
.nom:   ld a,ENOMEM
        scf
        ret

; afind: 144 bytes. Find a free block of a_need bytes and a_kind; HL = payload or CF. RAM has a limit.
afind:  ld hl,AR0
        ld de,0                 ; fixed: the highest free block that fits.
.l:     call aend
        jr nc,.end
        call ahdr               ; BC = size, A = kind.
        or a
        jr nz,.nx
.co:    push hl                 ; free: absorb the free blocks that follow.
        add hl,bc
        call aend
        jr nc,.cx
        inc hl
        inc hl
        ld a,(hl)
        dec hl
        dec hl
        or a
        jr nz,.cx
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        add hl,bc
        ld b,h
        ld c,l
        pop hl
        ld (hl),c
        inc hl
        ld (hl),b
        dec hl
        jr .co
.cx:    pop hl
        push hl
        ld hl,(a_need)
        call cpbchl             ; CF if BC < need.
        pop hl
        jr c,.nx
        ld a,(a_kind)
        cp K_IMG
        jr nc,.fixed
        push de                 ; movable: first fit below the window.
        push hl
        ld de,(a_need)
        add hl,de
        ld de,WINDOW+1
        call cphlde
        pop hl
        pop de
        jr c,.take
        jr .nx
.fixed:   ld d,h                  ; fixed: remember it, look further up.
        ld e,l
.nx:    add hl,bc
        jr .l
.end:   ld a,d
        or e
        scf
        ret z
; fixed: the bottom of the highest free block that fits, so the free space above it stays next to the
; window (which may be lent).
        ex de,hl
        call ahdr
; HL = free block of BC bytes; split off what is not needed.
.take:  ld de,(a_need)
        push hl
        call .rem
        jr c,.whole
        pop hl
        ld (hl),e
        inc hl
        ld (hl),d
        dec hl
        push hl
        add hl,de
        ld (hl),c
        inc hl
        ld (hl),b
        inc hl
        ld (hl),K_FREE
.whole: pop hl
.kind:  inc hl
        inc hl
        ld a,(a_kind)
        ld (hl),a
        inc hl
        inc hl
        or a
        ret
; .rem: BC = size, DE = need → BC = size - need; CF if under 4 (no split).
.rem:   ld h,b
        ld l,c
        or a
        sbc hl,de
        ld b,h
        ld c,l
        ld a,h
        or a
        ret nz
        ld a,l
        cp 4
        ret

; ahdr: 8 bytes. HL = block; return BC = size and A = kind. Every tenant gets a label.
ahdr:   ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        ld a,(hl)
        dec hl
        dec hl
        ret
; aend: 10 bytes. CF while HL is below a_top. The arena has an edge.
aend:   push de
        ld de,(a_top)
        call cphlde
        pop de
        ret
; cpbchl: 11 bytes. CF if BC < HL; keep BC, DE and HL. Carry calls the vote.
cpbchl: push hl
        push de
        ex de,hl
        ld h,b
        ld l,c
.xj0_3:
        or a
        sbc hl,de
        pop de
        pop hl
        ret

; afree: 10 bytes. HL = payload (zero does nothing); mark its block free. Back to the pile.
afree:  ld a,h
        or l
        ret z
        push hl
        dec hl
        dec hl
        ld (hl),K_FREE
        pop hl
        ret

; ashrink: 37 bytes. HL = payload, BC = new size; give back the unused tail. Not a charity warehouse.
ashrink:
        push hl
        ld hl,5
        add hl,bc
        res 0,l
        ex de,hl                ; DE = new block size.
        pop hl
        push hl
        ld bc,-4
        add hl,bc               ; HL = block.
        call ahdr
        push hl
        call afind.rem
        pop hl
        jr c,.x
        ld (hl),e
        inc hl
        ld (hl),d
        dec hl
        add hl,de
        ld (hl),c
        inc hl
        ld (hl),b
        inc hl
        ld (hl),K_FREE
.x:     pop hl
        ret

; acap: 15 bytes. HL = payload; return BC = block capacity. No wishful accounting.
acap:   push hl
        dec hl
        dec hl
        dec hl
        ld b,(hl)
        dec hl
        ld c,(hl)
        ld hl,-4
        add hl,bc
        ld b,h
        ld c,l
        pop hl
        ret

; ---------------------------------------------------------------------
; acompact: 89 bytes. Slide movable blocks down; leave fixed images alone. Furniture stays put.
acompact:
        ld hl,AR0
        ld (a_dst),hl
.l:     call aend
        jr nc,.gap
        call ahdr
        or a
        jr z,.nx                ; free: skip it.
        cp K_IMG
        jr c,.mov
        push hl                 ; fixed: the space below it is free.
        call .gap
        pop hl
        add hl,bc
        ld (a_dst),hl
        jr .l
.mov:   ld de,(a_dst)
        call cphlde
        jr z,.same
        push bc
        push hl
        push de
        ldir                    ; downwards: a forward copy is safe.
        pop de
        pop hl
        push hl
        ld bc,4
        add hl,bc
        ex de,hl
        add hl,bc
        ex de,hl
        call afix
        pop hl
        pop bc
.same:  push hl
        ld hl,(a_dst)
        add hl,bc
        ld (a_dst),hl
        pop hl
.nx:    add hl,bc
        jr .l
; .gap: a free block from a_dst up to HL (if any).
.gap:   ld de,(a_dst)
        or a
        sbc hl,de
        ret z
        ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
.xj0_6:
        inc hl
        ld (hl),K_FREE
        ret

; afix: 55 bytes. HL = old payload, DE = new; rewrite kernel pointers after a move. Forward the mail.
afix:   ld (a_old),hl
        ld (a_new),de
        ld hl,ITAB+I_DSKP
        ld b,NINODE
        ld de,INOSZ
        call .tab
        ld hl,p_save
        ld b,NPROC
        ld de,2
; .tab: HL → first word, B words DE apart.
.tab:   push de
        push hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld de,(a_old)
        or a
        sbc hl,de
        pop hl
        jr nz,.n
        ld de,(a_new)
        ld (hl),e
        inc hl
        ld (hl),d
        dec hl
.n:     pop de
        add hl,de
        djnz .tab
        ret

; afreeb: 25 bytes. Count all free arena blocks; return HL = bytes. No rounding up to feel rich.
afreeb: ld hl,AR0
        ld de,0
.l:     call aend
        jr nc,.x
        call ahdr
        or a
        jr nz,.n
        ex de,hl
        add hl,bc
        ex de,hl
.n:     add hl,bc
        jr .l
.x:     ex de,hl
        ret

; ---------------------------------------------------------------------
; lending the window. When a program loaded from tape does not fit, the window's memory (WINDOW.. CORETOP)
; joins the arena for as long as the program lives; resident-text processes wait meanwhile (isrun).
; ---------------------------------------------------------------------
; lend: 30 bytes. Lend the unused window to the arena. There is no extension office.
lend:   ld hl,0FFFFh
        ld (wlend),hl
        ld hl,(a_top)           ; a free block from the arena's end.
        ld de,CORETOP
        ex de,hl
        or a
        sbc hl,de
        ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (hl),K_FREE
        ld hl,CORETOP
        ld (a_top),hl
        ret

; unlend: 47 bytes. Reclaim the borrowed window only when it is clear; otherwise keep wlend. RAM has rules.
unlend: call acompact           ; free space slides to the top.
        ld de,(a_dst)           ; the top free block starts here.
        ld hl,WINDOW
        or a
        sbc hl,de
        ret c                   ; something is still in the window.
        ld (a_top),de
        ld a,h                  ; [start, WINDOW) stays free (a gap under.
        or a                    ; 4 bytes is left out of the arena).
        jr nz,.b
        ld a,l
        cp 4
        jr c,.z
.b:     ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (hl),K_FREE
        ld hl,WINDOW
        ld (a_top),hl
.z:     ld hl,0
        ld (wlend),hl
        ret
