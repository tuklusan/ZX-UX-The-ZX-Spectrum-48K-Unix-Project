; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Proprietary rights reserved except as expressly licensed herein.
;
; ZX-UX Sinclair ZX Spectrum Unix
; This file is governed by the SANYALnet Labs Non-Commercial License in the
; root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
; for AI/ML model training are prohibited unless separately authorized.
;
; Attribution is required: "Based on original work by Supratim Sanyal of
; SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
; patent, trademark, and governing-law provisions.
;
; P11.08 exact C48 integer runtime semantics.
; Inputs/outputs are deliberately tiny register contracts used by generated C48.
; No host arithmetic participates in target execution.

    MACRO EMIT_C48_INT_RUNTIME
c48_int_runtime_exit_status: db 0
c48_int_div_quotient:       dw 0
c48_int_div_remainder:      dw 0
c48_int_div_divisor:        dw 0
c48_int_div_qneg:           db 0
c48_int_div_rneg:           db 0
c48_int_mul_multiplicand:   dw 0
c48_int_mul_multiplier:     dw 0
c48_int_mul_result:         dw 0

; 8-bit unsigned/plain-char arithmetic. Results wrap modulo 2^8.
; L=lhs/value, E=rhs/count, result L.
c48_u8_add:
    ld a,l
    add a,e
    ld l,a
    xor a
    ret
c48_u8_sub:
    ld a,l
    sub e
    ld l,a
    xor a
    ret
c48_u8_mul:
    ld h,0
    ld d,0
    call c48_u16_mul
    xor a
    ret
c48_u8_neg:
    xor a
    sub l
    ld l,a
    xor a
    ret

; 16-bit signed/unsigned add/sub/mul/neg share modulo-2^16 mechanics.
; HL=lhs/value, DE=rhs, result HL.
c48_u16_add:
c48_s16_add:
    add hl,de
    xor a
    ret
c48_u16_sub:
c48_s16_sub:
    or a
    sbc hl,de
    xor a
    ret
c48_u16_neg:
c48_s16_neg:
    ld a,l
    cpl
    ld l,a
    ld a,h
    cpl
    ld h,a
    inc hl
    xor a
    ret

c48_u16_mul:
c48_s16_mul:
    ld (c48_int_mul_multiplicand),hl
    ld (c48_int_mul_multiplier),de
    ld hl,0
    ld (c48_int_mul_result),hl
    ld b,16
c48_int_mul_loop:
    ld hl,(c48_int_mul_multiplier)
    bit 0,l
    jr z,c48_int_mul_no_add
    ld de,(c48_int_mul_multiplicand)
    ld hl,(c48_int_mul_result)
    add hl,de
    ld (c48_int_mul_result),hl
c48_int_mul_no_add:
    ld hl,(c48_int_mul_multiplicand)
    add hl,hl
    ld (c48_int_mul_multiplicand),hl
    ld hl,(c48_int_mul_multiplier)
    srl h
    rr l
    ld (c48_int_mul_multiplier),hl
    djnz c48_int_mul_loop
    ld hl,(c48_int_mul_result)
    xor a
    ret

; Shift counts are masked exactly: low 3 bits for 8-bit, low 4 for 16-bit.
; Left shift is identical for signed/unsigned modulo-width C48 operands.
c48_u8_shl:
    ld a,e
    and 7
    jr z,c48_int_shift_ok
    ld b,a
c48_u8_shl_loop:
    sla l
    djnz c48_u8_shl_loop
    jr c48_int_shift_ok

c48_u8_shr:
    ld a,e
    and 7
    jr z,c48_int_shift_ok
    ld b,a
c48_u8_shr_loop:
    srl l
    djnz c48_u8_shr_loop
    jr c48_int_shift_ok

c48_u16_shl:
c48_s16_shl:
    ld a,e
    and 15
    jr z,c48_int_shift_ok
    ld b,a
c48_u16_shl_loop:
    add hl,hl
    djnz c48_u16_shl_loop
    jr c48_int_shift_ok

c48_u16_shr:
    ld a,e
    and 15
    jr z,c48_int_shift_ok
    ld b,a
c48_u16_shr_loop:
    srl h
    rr l
    djnz c48_u16_shr_loop
    jr c48_int_shift_ok

c48_s16_shr:
    ld a,e
    and 15
    jr z,c48_int_shift_ok
    ld b,a
c48_s16_shr_loop:
    sra h
    rr l
    djnz c48_s16_shr_loop
c48_int_shift_ok:
    xor a
    ret

; Unsigned restoring divide. HL=dividend, DE=divisor.
; Success returns HL=quotient, DE=remainder. Divisor zero uses runtime status 1.
c48_u16_divmod:
    ld a,d
    or e
    jp z,c48_int_divzero
    ld (c48_int_div_quotient),hl
    ld (c48_int_div_divisor),de
    ld hl,0
    ld (c48_int_div_remainder),hl
    ld b,16
c48_u16_div_loop:
    ld hl,(c48_int_div_quotient)
    add hl,hl
    ld (c48_int_div_quotient),hl
    ld hl,(c48_int_div_remainder)
    adc hl,hl
    ld (c48_int_div_remainder),hl
    ld de,(c48_int_div_divisor)
    or a
    sbc hl,de
    jr c,c48_u16_div_no_sub
    ld (c48_int_div_remainder),hl
    ld hl,(c48_int_div_quotient)
    set 0,l
    ld (c48_int_div_quotient),hl
c48_u16_div_no_sub:
    djnz c48_u16_div_loop
    ld hl,(c48_int_div_quotient)
    ld de,(c48_int_div_remainder)
    xor a
    ret

; Signed two's-complement division/remainder.
; Quotient truncates toward zero; remainder keeps dividend sign.
; 0x8000 / -1 wraps to 0x8000 and remainder zero.
c48_s16_divmod:
    ld a,h
    and $80
    ld (c48_int_div_rneg),a
    ld b,a
    ld a,d
    and $80
    xor b
    ld (c48_int_div_qneg),a

    bit 7,h
    jr z,c48_s16_div_lhs_mag
    call c48_s16_neg
c48_s16_div_lhs_mag:
    bit 7,d
    jr z,c48_s16_div_rhs_mag
    ex de,hl
    call c48_s16_neg
    ex de,hl
c48_s16_div_rhs_mag:
    call c48_u16_divmod
    ret c

    ld a,(c48_int_div_qneg)
    or a
    jr z,c48_s16_div_q_done
    call c48_s16_neg
c48_s16_div_q_done:
    ld a,(c48_int_div_rneg)
    or a
    jr z,c48_s16_div_done
    ex de,hl
    call c48_s16_neg
    ex de,hl
c48_s16_div_done:
    xor a
    ret

; Comparisons return A=$FF less, A=0 equal, A=1 greater.
c48_cmp_u16:
    or a
    sbc hl,de
    jr z,c48_cmp_equal
    jr c,c48_cmp_less
c48_cmp_greater:
    ld a,1
    or a
    ret
c48_cmp_less:
    ld a,$FF
    or a
    ret
c48_cmp_equal:
    xor a
    ret

c48_cmp_s16:
    ld a,h
    xor d
    and $80
    jr z,c48_cmp_u16
    bit 7,h
    jr nz,c48_cmp_less
    jr c48_cmp_greater

c48_cmp_u8:
    ld a,l
    cp e
    jr z,c48_cmp_equal
    jr c,c48_cmp_less
    jr c48_cmp_greater

; C48 divide/remainder by zero is a process runtime error with status 1.
; Qualification defines C48_INT_TEST_MODE only to observe the pre-exit status
; without requiring a complete process scheduler inside the isolated helper SNA.
c48_int_divzero:
    ld a,1
    ld (c48_int_runtime_exit_status),a
    IFDEF C48_INT_TEST_MODE
    scf
    ret
    ELSE
    ld hl,1
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ld a,E_INVAL
    scf
    ret
    ENDIF
    ENDM
