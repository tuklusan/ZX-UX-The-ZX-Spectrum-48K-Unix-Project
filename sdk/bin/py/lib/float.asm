; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48 borrows the Spectrum ROM's five-byte float calculator. No spare FPU.
; It redirects STKBOT, STKEND, MEM and ERR_SP to our scratch space and
; error trap, with interrupts off. ROM errors come back in carry; the
; kernel's system-variable values go back before we return.
ERRSP   equ 5C3Dh
STKBOT  equ 5C63h
STKEND  equ 5C65h
MEMV    equ 5C68h
MEMBOT  equ 5C92h
        section text
        global @fac,@fmov,@fop,@itof,@utof,@ftoi,@ftou,@fcmp,@ftst,@inrom,@ferr
        global _sin,_cos,_tan,_asin,_acos,_atan,_sqrt,_exp,_log,_fabs,_pow,_beep
; @fmov: 6 bytes. Copy one five-byte float from HL to DE.
@fmov:  ld bc,5
        ldir
        ret

; @inrom: 88 bytes. Borrow the ROM calculator, trap errors in carry, and restore its state.
@inrom: di
        push ix
        ex de,hl
        ld hl,(ERRSP)
        ld (@sv),hl
        ld hl,(STKBOT)
        ld (@sv+2),hl
        ld hl,(STKEND)
        ld (@sv+4),hl
        ld hl,(MEMV)
        ld (@sv+6),hl
        ld hl,@cstk
        ld (STKBOT),hl
        ld (STKEND),hl
        ld hl,@cmem
        ld (MEMV),hl
        ld hl,.err
        push hl
        ld (ERRSP),sp
        ld hl,.ret
        push hl
        ex de,hl
        jp (hl)
.err:   scf                     ; (the ROM reset SP to the trap's slot)
        push hl
.ret:   pop hl                  ; drop the trap address
        ld hl,(@sv)
        ld (ERRSP),hl
        ld hl,(@sv+2)
        ld (STKBOT),hl
        ld hl,(@sv+4)
        ld (STKEND),hl
        ld hl,(@sv+6)
        ld (MEMV),hl
        pop ix
        ei
        ret

; @fpush: 14 bytes. Push a five-byte value into the ROM calculator stack.
@fpush: ld de,(STKEND)
        ld bc,5
        ldir
        ld (STKEND),de
        ret
; @fpop: 18 bytes. Pop the calculator result into the address in @fx.
@fpop:  ld hl,(STKEND)
        ld bc,-5
        add hl,bc
        ld de,(@fx)
        ld bc,5
        ldir
        or a
        ret

; @ferr: 6 bytes. End the program with status one on a floating-point failure.
@ferr:  ld hl,1                 ; status 1, as the C48 language requires
        jp _exit
; @fop: 58 bytes. Run ROM operation A on HL and DE floats; exit on failure.
@fop:   ld (@fx),hl
        ld (@fy),de
        ld (@fo),a
        ld hl,.go
        call @inrom
        ret nc
        j @ferr
.go:    ld hl,(@fx)
        call @fpush
        ld a,(@fo)
        cp 6
        j nc,.un
        ld hl,(@fy)
        call @fpush
        ld a,(@fo)
.un:    ld hl,@ftab-1
        add a,l
        ld l,a
        j nc,.nc
        inc h
.nc:    ld a,(hl)
        ld (.code),a
        rst 28h
.code:  db 0,38h
        j @fpop
; @ftab: 17 data bytes. ROM operations 1..17, in C48 order.
@ftab:  db 0Fh,03h,04h,05h,06h,2Ah,1Bh,3Ah,26h,25h,1Fh,20h,21h,22h,23h,24h,28h

; @itof: 5 bytes. Convert signed HL into a five-byte float at DE.
@itof:  ld a,h
        add a,a
        sbc a,a                 ; FF if negative
        j @icv
; @utof: 1 byte. Convert unsigned HL into the same format. No sign drama.
@utof:  xor a
; @icv: 13 bytes. Write the small-integer float form to DE.
@icv:   ex de,hl
        ld (hl),0
        inc hl
        ld (hl),a
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (hl),0
        ret

; @ftoi: 33 bytes. Truncate a float to signed 16-bit or exit if it will not fit.
@ftoi:  call @fbc
        j c,@ferr
        j z,.pos
        ld a,b                  ; negative: up to 32768
        cp 80h
        j c,.ok
        j nz,@ferr
        ld a,c
        or a
        j nz,@ferr
.ok:    xor a
        sub c
        ld l,a
        sbc a,a
        sub b
        ld h,a
        ret
.pos:   bit 7,b                 ; positive: up to 32767
        j nz,@ferr
        ld h,b
        ld l,c
        ret
; @ftou: 16 bytes. Truncate a float to unsigned 16-bit; reject negatives outside zero.
@ftou:  call @fbc
        j c,@ferr
        j z,.p
        ld a,b                  ; negative: only zero
        or c
        j nz,@ferr
.p:     ld h,b
        ld l,c
        ret
; @fbc: 22 bytes. Ask the ROM for integer magnitude in BC and sign flags.
@fbc:   ld (@fx),hl
        ld hl,.go
        jp @inrom
.go:    ld hl,(@fx)
        call @fpush
        rst 28h
        db 3Ah,38h              ; truncate
        call 2DA2h              ; FP-TO-BC
        ret

; @fcmp: 40 bytes. Compare floats at HL and DE; carry means less, zero means equal.
@fcmp:  ld bc,@ftmp
        push bc
        push de
        ld d,b
        ld e,c
        call @fmov              ; x -> @ftmp
        pop de
        pop hl
        ld a,2                  ; x - y
        call @fop
        ld hl,@ftmp
        ld a,(hl)
        or a
        j nz,.big
        inc hl                  ; small integer: sign byte, value
        ld b,(hl)
        inc hl
        ld a,(hl)
        inc hl
        or (hl)
        ret z                   ; zero: equal (NC)
        ld a,b
        j .sg
.big:   inc hl
        ld a,(hl)
.sg:    or 1                    ; NZ
        rla                     ; CF = sign
        ret

; @ftst: 7 bytes. Set zero flag when the float at HL is zero.
@ftst:  ld a,(hl)
        inc hl
        inc hl
        or (hl)
        inc hl
        or (hl)
        ret
; _sin: 4 bytes. Send sine to the ROM calculator helper.
_sin:   ld a,11
        j @fun1
; _cos: 4 bytes. Send cosine to the ROM calculator helper.
_cos:   ld a,12
        j @fun1
; _tan: 4 bytes. Send tangent to the ROM calculator helper.
_tan:   ld a,13
        j @fun1
; _asin: 4 bytes. Send inverse sine to the ROM calculator helper.
_asin:  ld a,14
        j @fun1
; _acos: 4 bytes. Send inverse cosine to the ROM calculator helper.
_acos:  ld a,15
        j @fun1
; _atan: 4 bytes. Send inverse tangent to the ROM calculator helper.
_atan:  ld a,16
        j @fun1
; _sqrt: 4 bytes. Send square root to the ROM calculator helper.
_sqrt:  ld a,17
        j @fun1
; _exp: 4 bytes. Send exponential to the ROM calculator helper.
_exp:   ld a,9
        j @fun1
; _log: 4 bytes. Send logarithm to the ROM calculator helper.
_log:   ld a,10
        j @fun1
; _fabs: 2 bytes. Send absolute value to the ROM calculator helper.
_fabs:  ld a,6
; @fun1: 18 bytes. Copy one float to @fac and run the selected ROM operation.
@fun1:  push af
        ld de,@fac
        call @fmov
        pop af
        ld hl,@fac
        call @fop
        ld hl,@fac
        ret
; _pow: 24 bytes. Raise x to y with the ROM; return the result at @fac.
_pow:   pop bc
        pop de
        push bc
        push hl
        ex de,hl
        ld de,@fac
        call @fmov
        pop de
        ld hl,@fac
        ld a,5
        call @fop
        ld hl,@fac
        ret
; _beep: 65 bytes. Play a ROM BEEP; return zero or one and yield an interrupt frame.
_beep:  ex de,hl
        pop bc
        pop hl
        push bc
        ld (@fx),hl
        ld (@fy),de
        ld hl,.go
        call @inrom
        ld hl,@mem0             ; Put the five saved MEMBOT bytes back after BEEP.
        ld de,MEMBOT            ; ROM reads this from 5C92h, not our scratch buffer.
        ld bc,5                 ; Preserve the entire five-byte system slot.
        ldir
        ei                      ; Let the clock and keyboard have their turn.
        halt                    ; One interrupt frame between notes.
        ld hl,0                 ; Zero means BEEP succeeded; carry says otherwise.
        ret nc
        inc l
        ret
; ROM BEEP reads pitch from MEMBOT (5C92h), even with MEM redirected.
; Save the caller's full five-byte slot before ROM BEEP overwrites it.
.go:    ld hl,MEMBOT
        ld (MEMV),hl
        ld de,@mem0
        ld bc,5
        ldir
        ld hl,(@fx)
        call @fpush
        ld hl,(@fy)
        call @fpush
        jp 03F8h                ; BEEP (ends in BEEPER: EI, RET)
        section bss
; @fac: 5 BSS bytes. Shared result for ROM calculator calls.
@fac:   ds 5
; @ftmp: 5 BSS bytes. Comparison scratch; no second register bank.
@ftmp:  ds 5
; @fx: 2 BSS bytes. Pointer to the first float operand.
@fx:    ds 2
; @fy: 2 BSS bytes. Pointer to the second float operand.
@fy:    ds 2
; @fo: 1 BSS byte. ROM calculator operation selector.
@fo:    ds 1
; @sv: 8 BSS bytes. Saved ROM error, stack and memory pointers.
@sv:    ds 8
; @mem0: 5 BSS bytes. Backup of the ROM's borrowed MEMBOT slot.
@mem0:  ds 5                    ; Restore this copy before interrupts get another turn.
; @cmem: 30 BSS bytes. Temporary ROM calculator workspace.
@cmem:  ds 30                   ; MEMV points here during ROM arithmetic.
; @cstk: 60 BSS bytes. Scratch stack for the ROM calculator.
@cstk:  ds 60                   ; The ROM calculator stack is private to this call.
