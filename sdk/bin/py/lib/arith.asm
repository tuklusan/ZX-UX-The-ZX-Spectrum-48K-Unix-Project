; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48 integer helpers: 16 bits and not one spare. (ZX-UX SDK)
        section text
        global @mul,@divu,@modu,@divs,@mods,@shl,@shr,@sra,@shlb,@shrb
        global @and,@or,@xor,@neg,@com,@not,@notb,@scmp,@preincw,@postincw
; @mul: 18 bytes. HL * DE -> HL, low 16 bits. High bits get tossed.
@mul:   ld b,h
        ld c,l
        ld hl,0
        ld a,16
.l:     add hl,hl
        ex de,hl
        add hl,hl
        ex de,hl
        j nc,.n
        add hl,bc
.n:     dec a
        j nz,.l
        ret
; @divu: 38 bytes. Unsigned HL / DE -> HL quotient, DE remainder; zero divisor exits. No refunds.
@divu:  ld a,d
        or e
        jp z,@divz
        ld b,h
        ld c,l
        ld hl,0
        ld a,16
.l:     sla c
        rl b
        adc hl,hl
        j c,.ov
        sbc hl,de
        j nc,.s
        add hl,de
        j .n
.ov:    or a
        sbc hl,de
.s:     inc c
.n:     dec a
        j nz,.l
        ex de,hl
        ld h,b
        ld l,c
        ret
; @modu: 5 bytes. Unsigned HL % DE -> HL; @divu does the heavy lifting.
@modu:  call @divu
        ex de,hl
        ret
; @mods: 5 bytes. Signed HL % DE -> HL, with the dividend's sign. Keep the change.
@mods:  call @sdiv
        ex de,hl
        ret
; @divs/@sdiv: 34 bytes. Signed HL / DE -> HL quotient, DE remainder; truncate toward zero.
@divs:
@sdiv:  ld a,h
        or a
        push af                 ; dividend sign
        xor d
        push af                 ; quotient sign
        bit 7,h
        call nz,@neg
        bit 7,d
        j z,.p
        ex de,hl
        call @neg
        ex de,hl
.p:     call @divu
        pop af
        call m,@neg
        pop af
        ret p
        ex de,hl
        call @neg
        ex de,hl
        ret
; @shl: 8 bytes. Shift HL left by A & 15. Bits overboard.
@shl:   and 15
        ret z
        ld b,a
.l:     add hl,hl
        djnz .l
        ret
; @shr: 11 bytes. Shift HL right unsigned by A & 15. No sign souvenirs.
@shr:   and 15
        ret z
        ld b,a
.l:     srl h
        rr l
        djnz .l
        ret
; @sra: 11 bytes. Shift HL right signed by A & 15; keep the sign aboard.
@sra:   and 15
        ret z
        ld b,a
.l:     sra h
        rr l
        djnz .l
        ret
; @shlb: 12 bytes. Shift L left by A & 7; clear H. Eight-bit luggage only.
@shlb:  and 7
        ld h,0
        ret z
        ld b,a
        ld a,l
.l:     add a,a
        djnz .l
        ld l,a
        ret
; @shrb: 11 bytes. Shift L right by A & 7; clear H. No extras.
@shrb:  and 7
        ld h,0
        ret z
        ld b,a
.l:     srl l
        djnz .l
        ret
; @and: 7 bytes. HL &= DE. Keep only the mutual friends.
@and:   ld a,h
        and d
        ld h,a
        ld a,l
        and e
        ld l,a
        ret
; @or: 7 bytes. HL |= DE. Everyone gets in.
@or:    ld a,h
        or d
        ld h,a
        ld a,l
        or e
        ld l,a
        ret
; @xor: 7 bytes. HL ^= DE. Opposites get the vote.
@xor:   ld a,h
        xor d
        ld h,a
        ld a,l
        xor e
        ld l,a
        ret
; @neg: 7 bytes. Negate HL, modulo 65536. Signs are negotiable.
@neg:   xor a
        sub l
        ld l,a
        sbc a,a
        sub h
        ld h,a
        ret
; @com: 7 bytes. Invert all 16 bits of HL. Nothing sacred.
@com:   ld a,h
        cpl
        ld h,a
        ld a,l
        cpl
        ld l,a
        ret
; @not: 2 bytes plus @not0's 6-byte tail. HL zero? Return 1. Everyone else gets 0.
@not:   ld a,h
        or l
; @not0: 6-byte shared tail for both NOT entries. One exit, two callers.
@not0:  ld hl,0
        ret nz
        inc l
        ret
; @notb: 4 bytes, then @not0. Test L only. H gets the day off.
@notb:  ld a,l
        or a
        j @not0
; @scmp: 11 bytes. Signed HL vs DE -> CF if less, ZF if equal; HL is spent.
@scmp:  ld a,h
        xor d
        jp m,.d
        sbc hl,de               ; CF = 0 after xor
        ret
.d:     ld a,h
        rla
        ret
; @preincw: 5 bytes plus @incw. Add DE to (HL), return new word in HL.
@preincw:
        call @incw
        ex de,hl
        ret
; @postincw: 6 bytes plus @incw. Add DE to (HL), return the old word.
@postincw:
        call @incw
        ld h,b
        ld l,c
        ret
; @incw: 10-byte shared helper. BC = old, DE = new; write the word at (HL).
@incw:  ld c,(hl)
        inc hl
        ld b,(hl)
        ex de,hl
        add hl,bc
        ex de,hl
        ld (hl),d
        dec hl
        ld (hl),e
        ret
