; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48 bytecode handlers: sizes exclude their shared tails. No double billing.
; Each function starts with CALL @vm, a frame byte, then bytecode; @vmtab
; holds only the opcodes its program uses (rcc/bcops.py).
; HL = expression top; BC = bytecode pointer; IX = function frame.
; IX points past saved IX and native return: last argument at IX-2,
; saved bytecode pointer at IX-4, locals below. Native calls work both ways.
        section text
        global @vm,@vnext
        global @v_k0,@v_k1,@v_ldk,@v_ldkw,@v_lda,@v_push,@v_pk0,@v_pk1,@v_pldk,@v_pldkw
        global @v_plda,@v_ldl,@v_ldlb,@v_stl,@v_stlb,@v_leal,@v_pldl,@v_pldlb,@v_addl,@v_addlb
        global @v_ldg,@v_ldgb,@v_stg,@v_stgb,@v_pldg,@v_pldgb,@v_addg,@v_addgb
        global @v_ldi,@v_ldib,@v_sti,@v_stib,@v_preiw,@v_postiw,@v_preib,@v_postib
        global @v_add,@v_sub,@v_mul,@v_divs,@v_divu,@v_mods,@v_modu,@v_and,@v_or,@v_xor
        global @v_shl,@v_shr,@v_sar,@v_neg,@v_com,@v_not,@v_zxb,@v_addk,@v_addkw,@v_shl1,@v_andk
        global @v_jmp,@v_jmpl,@v_jz,@v_jzl,@v_jnz,@v_jnzl,@v_jeq,@v_jeql,@v_jne,@v_jnel
        global @v_jlt,@v_jltl,@v_jge,@v_jgel,@v_jgt,@v_jgtl,@v_jle,@v_jlel
        global @v_jltu,@v_jltul,@v_jgeu,@v_jgeul,@v_jgtu,@v_jgtul,@v_jleu,@v_jleul
        global @v_jeqk,@v_jnek,@v_jltk,@v_jgek,@v_jgtk,@v_jlek,@v_adda,@v_addaw,@v_ldxb,@v_ldxw
        global @v_ldgs,@v_ldgsb,@v_stgs,@v_stgsb,@v_pldgs,@v_pldgsb,@v_addgs,@v_addgsb,@v_calli
        global @v_call,@v_ret,@v_ret0,@v_ret1,@v_ret2,@v_noret,@v_copy,@v_pop
        global @v_ldl_m2,@v_ldl_4,@v_ldl_6,@v_ldl_8,@v_ldl_m6,@v_ldl_m8,@v_ldl_m10,@v_ldl_m12
        global @v_ldl_m14,@v_ldl_m16,@v_ldl_m18,@v_ldl_m20
        global @v_stl_m2,@v_stl_4,@v_stl_6,@v_stl_m6,@v_stl_m8,@v_stl_m10,@v_stl_m12,@v_stl_m14

; @vm: 41 bytes. Enter a bytecode frame; save IX, check stack room.
@vm:    pop bc                  ; BC -> the header
        push ix
        ld ix,0
        add ix,sp
        push hl                 ; the last argument at IX-2
        push bc                 ; (the saved IP at IX-4)
        ld a,(bc)               ; locals
        inc bc
        ld e,a
        ld d,0
        inc a
        j nz,.s
        call @vfw
.s:     ld hl,0
        add hl,sp
        or a
        sbc hl,de
        push hl
        ld de,@end+170          ; keep 170 bytes for the kernel and interrupts
        or a
        sbc hl,de
        pop hl
        jp c,@noret             ; stack overflow: end the program (status 1)
        ld sp,hl
; @vnext: 17 bytes. Dispatch the next opcode, keeping HL intact.
@vnext: ld a,(bc)
        inc bc
        push hl
        ld l,a
        ld h,0
        add hl,hl
        ld de,@vmtab
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ex (sp),hl
        ret

; @vfs: 7 bytes. Read signed one-byte operand into DE.
@vfs:   ld a,(bc)
        inc bc
        ld e,a
        rla
        sbc a,a
        ld d,a
        ret
; @vfw: 7 bytes. Read two-byte operand into DE.
@vfw:   ld a,(bc)
        inc bc
        ld e,a
        ld a,(bc)
        inc bc
        ld d,a
        ret
; @vfa: 8 bytes. Make IX-relative address in HL.
@vfa:   call @vfs
        push ix
        pop hl
        add hl,de
        ret

; ---- constants and the stack
; @v_pk0: 1 byte. Save HL before the zero literal. One extra stack passenger.
@v_pk0: push hl
; @v_k0: 5 bytes. Load zero into HL. Subtle as ever.
@v_k0:  ld hl,0
        j @vnext
; @v_pk1: 1 byte. Save HL before the one literal. Stack fare is one word.
@v_pk1: push hl
; @v_k1: 5 bytes. Load one into HL. Small ambitions.
@v_k1:  ld hl,1
        j @vnext
; @v_pldk: 1 byte. Push old HL before reading a signed byte constant.
@v_pldk:
        push hl
; @v_ldk: 6 bytes. Sign-extend the next byte into HL.
@v_ldk: call @vfs
        ex de,hl
        j @vnext
; @v_pldkw/@v_plda: 1 byte. Push old HL before a word or address literal.
@v_pldkw:
@v_plda:
        push hl
; @v_ldkw/@v_lda: 6 bytes. Read the next two bytes as a word into HL.
@v_ldkw:
@v_lda: call @vfw
        ex de,hl
        j @vnext
; @v_push: 3 bytes. Push HL onto the expression stack.
@v_push:
        push hl
        j @vnext
; @v_pop: 3 bytes. Pull the next expression value into HL.
@v_pop: pop hl
        j @vnext

; ---- frame
; @v_pldl: 1 byte. Save old HL before loading a local word.
@v_pldl:
        push hl
; @v_ldl: 3 bytes. Find the IX-relative local; the word load follows.
@v_ldl: call @vfa
; @v_ldi: 6 bytes. Read the word pointed at by HL into HL.
@v_ldi: ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        j @vnext
; @v_pldlb: 1 byte. Save old HL before loading a local byte.
@v_pldlb:
        push hl
; @v_ldlb: 3 bytes. Find the IX-relative local; the byte load follows.
@v_ldlb:
        call @vfa
; @v_ldib: 5 bytes. Read byte [HL] into HL, zero high bits.
@v_ldib:
        ld l,(hl)
        ld h,0
        j @vnext
; @v_stl: 5 bytes. Store HL at an IX-relative local word address.
@v_stl: push hl
        call @vfa
        pop de
; @vstw: 6 bytes. Store a word through HL; share the exit.
@vstw:  ld (hl),e
        inc hl
        ld (hl),d
        ex de,hl
        j @vnext
; @v_stlb: 5 bytes. Store L at an IX-relative local byte address.
@v_stlb:
        push hl
        call @vfa
        pop de
; @vstb: 4 bytes. Store one byte; share the exit.
@vstb:  ld (hl),e
        ex de,hl
        j @vnext
; @v_leal: 5 bytes. Return the IX-relative local address in HL.
@v_leal:
        call @vfa
        j @vnext
; @v_addl: 4 bytes. Find a local word, then add the next signed byte.
@v_addl:
        push hl
        call @vfa
; @vaddw: 16 bytes. Add signed byte to the word at HL.
@vaddw: push hl                 ; HL -> word, then a signed byte operand
        call @vfs
        pop hl
        ld a,(hl)
        add a,e
        ld (hl),a
        inc hl
        ld a,(hl)
        adc a,d
        ld (hl),a
        pop hl
        j @vnext
; @v_addlb: 4 bytes. Find a local byte, then add the next byte.
@v_addlb:
        push hl
        call @vfa
; @vaddb: 8 bytes. Add signed byte to the byte at HL.
@vaddb: ld a,(bc)
        inc bc
        add a,(hl)
        ld (hl),a
        pop hl
        j @vnext

; ---- globals
; @v_pldg: 1 byte. Save HL before loading a global word.
@v_pldg:
        push hl
; @v_ldg: 6 bytes. Read a word from the absolute address in bytecode.
@v_ldg: call @vfw
        ex de,hl
        j @v_ldi
; @v_pldgb: 1 byte. Save HL before loading a global byte.
@v_pldgb:
        push hl
; @v_ldgb: 6 bytes. Read a byte from the absolute address in bytecode.
@v_ldgb:
        call @vfw
        ex de,hl
        j @v_ldib
; @v_stg: 6 bytes. Store HL at the absolute address in bytecode.
@v_stg: call @vfw
        ex de,hl
        j @vstw
; @v_stgb: 6 bytes. Store L at the absolute address in bytecode.
@v_stgb:
        call @vfw
        ex de,hl
        j @vstb
; @v_addg: 7 bytes. Add the next signed byte to an absolute word.
@v_addg:
        push hl
        call @vfw
        ex de,hl
        j @vaddw
; @v_addgb: 7 bytes. Add the next byte to an absolute byte.
@v_addgb:
        push hl
        call @vfw
        ex de,hl
        j @vaddb

; @vgs: 10 bytes. Find the scalar global at the next byte offset.
@vgs:   ld a,(bc)
        inc bc
        ld hl,@gs
        add a,l
        ld l,a
        ret nc
        inc h
        ret
; @v_pldgs: 1 byte. Save HL before loading a compact global word.
@v_pldgs:
        push hl
; @v_ldgs: 5 bytes. Load a word from @gs plus its one-byte offset.
@v_ldgs:
        call @vgs
        j @v_ldi
; @v_pldgsb: 1 byte. Save HL before loading a compact global byte.
@v_pldgsb:
        push hl
; @v_ldgsb: 5 bytes. Load a byte from @gs plus its one-byte offset.
@v_ldgsb:
        call @vgs
        j @v_ldib
; @v_stgs: 7 bytes. Store HL at @gs plus its one-byte offset.
@v_stgs:
        push hl
        call @vgs
        pop de
        j @vstw
; @v_stgsb: 7 bytes. Store L at @gs plus its one-byte offset.
@v_stgsb:
        push hl
        call @vgs
        pop de
        j @vstb
; @v_addgs: 6 bytes. Add signed byte to a word in compact globals.
@v_addgs:
        push hl
        call @vgs
        j @vaddw
; @v_addgsb: 6 bytes. Add byte to byte in compact globals.
@v_addgsb:
        push hl
        call @vgs
        j @vaddb

; ---- indirect (the address on the stack, the value in HL)
; @v_sti: 5 bytes. Store HL through the address popped from the stack.
@v_sti: pop de
        ex de,hl
        j @vstw
; @v_stib: 5 bytes. Store L through the address popped from the stack.
@v_stib:
        pop de
        ex de,hl
        j @vstb
; @v_preiw: 16 bytes. Add before reading the indirect value.
@v_preiw:
        push hl
        call @vfs
        pop hl
        push hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        add hl,de
        ex de,hl
        pop hl
        j @vstw
; @v_postiw: 21 bytes. Read before changing the indirect value.
@v_postiw:
        push hl
        call @vfs
        pop hl
        ld a,(hl)
        push af
        add a,e
        ld (hl),a
        inc hl
        ld a,(hl)
        push af
        adc a,d
        ld (hl),a
        pop af
        ld h,a
        pop af
        ld l,a
        j @vnext
; @v_preib: 14 bytes. Add before reading the indirect value.
@v_preib:
        push hl
        call @vfs
        pop hl
        ld a,(hl)
        add a,e
        ld (hl),a
        ld l,a
        ld h,0
        j @vnext
; @v_postib: 15 bytes. Read before changing the indirect value.
@v_postib:
        push hl
        call @vfs
        pop hl
        ld a,(hl)
        ld d,a
        add a,e
        ld (hl),a
        ld l,d
        ld h,0
        j @vnext

; ---- arithmetic (left operand on the stack)
; @v_add: 5 bytes. Add popped DE to HL. Nothing up the sleeve.
@v_add: pop de
        add hl,de
        j @vnext
; @v_sub: 8 bytes. Subtract HL from the popped left operand.
@v_sub: pop de
        ex de,hl
        or a
        sbc hl,de
        j @vnext
; @v_mul: 5 bytes. Multiply stacked operands with the native helper.
@v_mul: ld de,@mul
        j @vhelp
; @v_divs: 5 bytes. Signed divide via the native helper.
@v_divs:
        ld de,@divs
        j @vhelp
; @v_divu: 5 bytes. Unsigned divide via the native helper.
@v_divu:
        ld de,@divu
        j @vhelp
; @v_mods: 5 bytes. Signed remainder via the native helper.
@v_mods:
        ld de,@mods
        j @vhelp
; @v_modu: 3 bytes. Unsigned remainder via the native helper.
@v_modu:
        ld de,@modu
; @vhelp: 14 bytes. Call a native arithmetic helper via a patched jump.
@vhelp: ld (@vjp+1),de
        pop de
        ex de,hl
        push bc
        call @vjp
        pop bc
        j @vnext
; @v_and: 10 bytes. AND HL with the popped word. Every bit votes.
@v_and: pop de
        ld a,l
        and e
        ld l,a
        ld a,h
        and d
        ld h,a
        j @vnext
; @v_or: 10 bytes. OR HL with the popped word. All votes count.
@v_or:  pop de
        ld a,l
        or e
        ld l,a
        ld a,h
        or d
        ld h,a
        j @vnext
; @v_xor: 10 bytes. XOR HL with the popped word. Only differing bits survive.
@v_xor: pop de
        ld a,l
        xor e
        ld l,a
        ld a,h
        xor d
        ld h,a
        j @vnext
; @v_shl: 5 bytes. Pop the value, then shift it left by L bits. The count gets first dibs.
@v_shl: ld de,@shl
        j @vsh
; @v_shr: 5 bytes. Pop the value and shift right unsigned. No sign baggage.
@v_shr: ld de,@shr
        j @vsh
; @v_sar: 3 bytes. Pop the value and shift right signed. The sign stays aboard.
@v_sar: ld de,@sra
; @vsh: 14 bytes. Call the native shift helper with A as count.
@vsh:   ld a,l                  ; count
        ld (@vjp+1),de
        pop hl
        push bc
        call @vjp
        pop bc
        j @vnext
; @v_neg: 9 bytes. Negate HL using two-byte carry arithmetic.
@v_neg: xor a
        sub l
        ld l,a
        sbc a,a
        sub h
        ld h,a
        j @vnext
; @v_com: 9 bytes. Invert both bytes of HL. All bits turncoat.
@v_com: ld a,l
        cpl
        ld l,a
        ld a,h
        cpl
        ld h,a
        j @vnext
; @v_not: 12 bytes. Logical NOT: return one only when HL was zero.
@v_not: ld a,h
        or l
        ld hl,0
        j nz,@vnext
        inc l
        j @vnext
; @v_zxb: 5 bytes. Zero-extend the byte in L to 16 bits.
@v_zxb: ld h,0
        j @vnext
; @v_addk: 7 bytes. Add a sign-extended byte literal to HL.
@v_addk:
        call @vfs
        add hl,de
        j @vnext
; @v_addkw: 7 bytes. Add the next word literal to HL.
@v_addkw:
        call @vfw
        add hl,de
        j @vnext
; @v_shl1: 4 bytes. Double HL with a single add. Cheap and cheerful.
@v_shl1:
        add hl,hl
        j @vnext
; @v_andk: 9 bytes. AND L with byte literal; clear H.
@v_andk:
        ld a,(bc)
        inc bc
        and l
        ld l,a
        ld h,0
        j @vnext

; ---- branches: taken -> @vjs (byte offset) / @vjw (word offset), else skip
; @v_jmp/@vjs: 3 bytes. Unconditional branch; offset comes next.
@v_jmp:
@vjs:   call @vfs
; @vjump: 10 bytes. Move BC by the signed displacement in DE.
@vjump: push hl
        ld h,b
        ld l,c
        add hl,de
        ld b,h
        ld c,l
        pop hl
        j @vnext
; @v_jmpl/@vjw: 5 bytes. Unconditional branch; offset comes next.
@v_jmpl:
@vjw:   call @vfw
        j @vjump
; @vno2: 1 byte. Skip two bytes of an untaken branch.
@vno2:  inc bc
; @vno1: 4 bytes. Skip one byte of an untaken branch.
@vno1:  inc bc
        j @vnext
; @v_jz: 6 bytes. Branch on zero, with a one-byte skip if not.
@v_jz:  ld a,h
        or l
        j z,@vjs
        j @vno1
; @v_jzl: 6 bytes. Branch on zero, with a two-byte skip if not.
@v_jzl: ld a,h
        or l
        j z,@vjw
        j @vno2
; @v_jnz: 6 bytes. Branch on nonzero, with a one-byte skip if not.
@v_jnz: ld a,h
        or l
        j nz,@vjs
        j @vno1
; @v_jnzl: 6 bytes. Branch on nonzero, with a two-byte skip if not.
@v_jnzl:
        ld a,h
        or l
        j nz,@vjw
        j @vno2
; @v_jeq: 8 bytes. Pop a word; branch if it equals HL, short offset.
@v_jeq: pop de
        or a
        sbc hl,de
        j z,@vjs
        j @vno1
; @v_jeql: 8 bytes. Pop a word; branch if it equals HL, word offset.
@v_jeql:
        pop de
        or a
        sbc hl,de
        j z,@vjw
        j @vno2
; @v_jne: 8 bytes. Pop a word; branch if it differs from HL, short offset.
@v_jne: pop de
        or a
        sbc hl,de
        j nz,@vjs
        j @vno1
; @v_jnel: 8 bytes. Pop a word; branch if it differs from HL, word offset.
@v_jnel:
        pop de
        or a
        sbc hl,de
        j nz,@vjw
        j @vno2
; @v_jlt: 7 bytes. Pop left operand; signed less-than uses a byte branch.
@v_jlt: call @vlt
        j c,@vjs
        j @vno1
; @v_jltl: 7 bytes. Pop left operand; signed left less than HL takes word branch.
@v_jltl:
        call @vlt
        j c,@vjw
        j @vno2
; @v_jge: 7 bytes. Pop left operand; signed left at least HL takes byte branch.
@v_jge: call @vlt
        j nc,@vjs
        j @vno1
; @v_jgel: 7 bytes. Pop left operand; signed left at least HL takes word branch.
@v_jgel:
        call @vlt
        j nc,@vjw
        j @vno2
; @v_jgt: 7 bytes. Pop left operand; signed left greater than HL takes byte branch.
@v_jgt: call @vgt
        j c,@vjs
        j @vno1
; @v_jgtl: 7 bytes. Pop left operand; signed left greater than HL takes word branch.
@v_jgtl:
        call @vgt
        j c,@vjw
        j @vno2
; @v_jle: 7 bytes. Pop left operand; signed left at most HL takes byte branch.
@v_jle: call @vgt
        j nc,@vjs
        j @vno1
; @v_jlel: 7 bytes. Pop left operand; signed left at most HL takes word branch.
@v_jlel:
        call @vgt
        j nc,@vjw
        j @vno2
; @v_jltu: 8 bytes. Pop left operand; unsigned less-than uses a byte branch.
@v_jltu:
        call @vltu
        j c,@vjs
        j @vno1
; @v_jltul: 9 bytes. Pop left operand; unsigned left less than HL takes word branch.
@v_jltul:
        call @vltu
        j c,@vjw
        j @vno2
; @v_jgeu: 9 bytes. Pop left operand; unsigned left at least HL takes byte branch.
@v_jgeu:
        call @vltu
        j nc,@vjs
        j @vno1
; @v_jgeul: 9 bytes. Pop left operand; unsigned left at least HL takes word branch.
@v_jgeul:
        call @vltu
        j nc,@vjw
        j @vno2
; @v_jgtu: 9 bytes. Pop left operand; unsigned left greater than HL takes byte branch.
@v_jgtu:
        call @vgtu
        j c,@vjs
        j @vno1
; @v_jgtul: 9 bytes. Pop left operand; unsigned left greater than HL takes word branch.
@v_jgtul:
        call @vgtu
        j c,@vjw
        j @vno2
; @v_jleu: 9 bytes. Pop left operand; unsigned left at most HL takes byte branch.
@v_jleu:
        call @vgtu
        j nc,@vjs
        j @vno1
; @v_jleul: 9 bytes. Pop left operand; unsigned left at most HL takes word branch.
@v_jleul:
        call @vgtu
        j nc,@vjw
        j @vno2
; @vlt: 7 bytes. Compare stacked left with HL; carry means signed less.
@vlt:   pop af
        pop de
        push af
        ex de,hl
        jp @scmp
; @vgt: 6 bytes. Signed greater-than comparison using @scmp.
@vgt:   pop af
        pop de
        push af
        jp @scmp
; @vltu: 8 bytes. Unsigned less-than comparison.
@vltu:  pop af
        pop de
        push af
        ex de,hl
        or a
        sbc hl,de
        ret
; @vgtu: 7 bytes. Unsigned greater-than comparison.
@vgtu:  pop af
        pop de
        push af
        or a
        sbc hl,de
        ret
; @v_jeqk: 12 bytes. Compare HL with signed-byte literal; jump on equality.
@v_jeqk:
        call @vfs
        or a
        sbc hl,de
        j z,@vjs
        j @vno1
; @v_jnek: 12 bytes. Compare HL with signed-byte literal; jump on inequality.
@v_jnek:
        call @vfs
        or a
        sbc hl,de
        j nz,@vjs
        j @vno1

; @v_jltk: 12 bytes. Signed HL less than next byte? Take short branch.
@v_jltk:
        call @vfs
        call @scmp
        j c,@vjs
        j @vno1
; @v_jgek: 12 bytes. Signed HL at least next byte? Take short branch.
@v_jgek:
        call @vfs
        call @scmp
        j nc,@vjs
        j @vno1
; @v_jgtk: 13 bytes. Signed HL greater than next byte? Take short branch.
@v_jgtk:
        call @vfs               ; k < HL
        ex de,hl
        call @scmp
        j c,@vjs
        j @vno1
; @v_jlek: 13 bytes. Signed HL at most next byte? Take short branch.
@v_jlek:
        call @vfs
        ex de,hl
        call @scmp
        j nc,@vjs
        j @vno1
; @v_jgtuk: 13 bytes. Unsigned HL greater than byte? Take short branch.
@v_jgtuk:
        call @vfs               ; k < HL (unsigned)
        ex de,hl
        or a
        sbc hl,de
        j c,@vjs
        j @vno1
; @v_jleuk: 13 bytes. Unsigned HL at most byte? Take short branch.
@v_jleuk:
        call @vfs
        ex de,hl
        or a
        sbc hl,de
        j nc,@vjs
        j @vno1

; ---- arrays: HL = index, the array's address follows
; @v_addaw: 1 byte. Double array index for a word before adding base.
@v_addaw:
        add hl,hl
; @v_adda: 7 bytes. Add the absolute array base to the index in HL.
@v_adda:
        call @vfw
        add hl,de
        j @vnext
; @v_ldxw: 8 bytes. Read word at base plus twice the array index.
@v_ldxw:
        add hl,hl
        call @vfw
        add hl,de
        j @v_ldi
; @v_ldxb: 7 bytes. Read byte at base plus the array index.
@v_ldxb:
        call @vfw
        add hl,de
        j @v_ldib

; ---- calls
; @v_calli: 17 bytes. Read function address through the @ct call table.
@v_calli:                       ; Double the table index: each address takes two bytes.
        push hl
        ld a,(bc)
        inc bc
        ld l,a
        ld h,0
        add hl,hl
        ld de,@ct
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        pop hl
        j @vcall
; @v_call: 3 bytes. Read native function address from bytecode.
@v_call:
        call @vfw               ; DE = the function
; @vcall: 12 bytes. Save the bytecode return point and enter native code.
@vcall:
        ld (ix-4),c             ; (the instruction pointer)
        ld (ix-3),b
        ld bc,@vret
        push bc
        push de
        ret                     ; arguments: pushed, the last in HL
; @vret: 9 bytes. Reload BC after a native function returns.
@vret:  ld c,(ix-4)
        ld b,(ix-3)
        j @vnext
; @v_ret: 3 bytes. Return, dropping the argument count read from bytecode.
@v_ret: ld a,(bc)
        j @vr
; @v_ret0: 3 bytes. Return without dropping any arguments.
@v_ret0:
        xor a
        j @vr
; @v_ret1: 4 bytes. Return after dropping one argument.
@v_ret1:
        ld a,1
        j @vr
; @v_ret2: 2 bytes. Return after dropping two arguments.
@v_ret2:
        ld a,2
; @vr: 14 bytes. Restore IX and return, dropping A stacked arguments.
@vr:    ld sp,ix                ; HL = the result
        pop ix
        pop de
.l:     or a
        j z,.d
        pop bc
        dec a
        j .l
.d:     push de
        ret
; @v_noret: 3 bytes. Exit when a bytecode frame cannot return safely.
@v_noret:
        jp @noret
; @v_copy: 20 bytes. Copy counted bytes from stack source to HL destination.
@v_copy:
        call @vfw
        ld (@vt),bc
        ld b,d
        ld c,e
        ex de,hl
        pop hl
        ldir
        ld bc,(@vt)
        j @vnext

; ---- short forms: IX-relative loads and stores. Straight to the address.
; @v_pldl_m2: 1 byte. Save HL before loading a word from IX-2.
@v_pldl_m2:
        push hl
; @v_ldl_m2: 9 bytes. Load a word from IX-2.
@v_ldl_m2:
        ld l,(ix-2)
        ld h,(ix-1)
        j @vnext
; @v_pldl_4: 1 byte. Save HL before loading a word from IX+4.
@v_pldl_4:
        push hl
; @v_ldl_4: 9 bytes. Load a word from IX+4.
@v_ldl_4:
        ld l,(ix+4)
        ld h,(ix+5)
        j @vnext
; @v_pldl_6: 1 byte. Save HL before loading a word from IX+6.
@v_pldl_6:
        push hl
; @v_ldl_6: 9 bytes. Load a word from IX+6.
@v_ldl_6:
        ld l,(ix+6)
        ld h,(ix+7)
        j @vnext
; @v_pldl_8: 1 byte. Save HL before loading a word from IX+8.
@v_pldl_8:
        push hl
; @v_ldl_8: 9 bytes. Load a word from IX+8.
@v_ldl_8:
        ld l,(ix+8)
        ld h,(ix+9)
        j @vnext
; @v_pldl_m6: 1 byte. Save HL before loading a word from IX-6.
@v_pldl_m6:
        push hl
; @v_ldl_m6: 9 bytes. Load a word from IX-6.
@v_ldl_m6:
        ld l,(ix-6)
        ld h,(ix-5)
        j @vnext
; @v_pldl_m8: 1 byte. Save HL before loading a word from IX-8.
@v_pldl_m8:
        push hl
; @v_ldl_m8: 9 bytes. Load a word from IX-8.
@v_ldl_m8:
        ld l,(ix-8)
        ld h,(ix-7)
        j @vnext
; @v_pldl_m10: 1 byte. Save HL before loading a word from IX-10.
@v_pldl_m10:
        push hl
; @v_ldl_m10: 9 bytes. Load a word from IX-10.
@v_ldl_m10:
        ld l,(ix-10)
        ld h,(ix-9)
        j @vnext
; @v_pldl_m12: 1 byte. Save HL before loading a word from IX-12.
@v_pldl_m12:
        push hl
; @v_ldl_m12: 9 bytes. Load a word from IX-12.
@v_ldl_m12:
        ld l,(ix-12)
        ld h,(ix-11)
        j @vnext
; @v_pldl_m14: 1 byte. Save HL before loading a word from IX-14.
@v_pldl_m14:
        push hl
; @v_ldl_m14: 9 bytes. Load a word from IX-14.
@v_ldl_m14:
        ld l,(ix-14)
        ld h,(ix-13)
        j @vnext
; @v_pldl_m16: 1 byte. Save HL before loading a word from IX-16.
@v_pldl_m16:
        push hl
; @v_ldl_m16: 9 bytes. Load a word from IX-16.
@v_ldl_m16:
        ld l,(ix-16)
        ld h,(ix-15)
        j @vnext
; @v_pldl_m18: 1 byte. Save HL before loading a word from IX-18.
@v_pldl_m18:
        push hl
; @v_ldl_m18: 9 bytes. Load a word from IX-18.
@v_ldl_m18:
        ld l,(ix-18)
        ld h,(ix-17)
        j @vnext
; @v_pldl_m20: 1 byte. Save HL before loading a word from IX-20.
@v_pldl_m20:
        push hl
; @v_ldl_m20: 9 bytes. Load a word from IX-20.
@v_ldl_m20:
        ld l,(ix-20)
        ld h,(ix-19)
        j @vnext
; @v_stl_m2: 9 bytes. Store HL at IX-2.
@v_stl_m2:
        ld (ix-2),l
        ld (ix-1),h
        j @vnext
; @v_stl_4: 9 bytes. Store HL at IX+4.
@v_stl_4:
        ld (ix+4),l
        ld (ix+5),h
        j @vnext
; @v_stl_6: 9 bytes. Store HL at IX+6.
@v_stl_6:
        ld (ix+6),l
        ld (ix+7),h
        j @vnext
; @v_stl_m6: 9 bytes. Store HL at IX-6.
@v_stl_m6:
        ld (ix-6),l
        ld (ix-5),h
        j @vnext
; @v_stl_m8: 9 bytes. Store HL at IX-8.
@v_stl_m8:
        ld (ix-8),l
        ld (ix-7),h
        j @vnext
; @v_stl_m10: 9 bytes. Store HL at IX-10.
@v_stl_m10:
        ld (ix-10),l
        ld (ix-9),h
        j @vnext
; @v_stl_m12: 9 bytes. Store HL at IX-12.
@v_stl_m12:
        ld (ix-12),l
        ld (ix-11),h
        j @vnext
; @v_stl_m14: 9 bytes. Store HL at IX-14.
@v_stl_m14:
        ld (ix-14),l
        ld (ix-13),h
        j @vnext
        section data
; @vjp: 3 data bytes. Native-helper jump, patched at runtime.
@vjp:   jp 0                    ; (self-modified: a native helper)
        section bss
; @vt: 2 BSS bytes. Saved instruction pointer for the copy handler.
@vt:    ds 2
