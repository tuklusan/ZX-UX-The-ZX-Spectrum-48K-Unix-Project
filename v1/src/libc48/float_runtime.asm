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
; P11.17 C48 ROM-calculator runtime bridge.
; Mandatory read-only SDK/reference baseline:
; 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/float5.py -> exact five-byte arithmetic object semantics
; compiler/c48/vm.py -> source arithmetic/runtime-error behavior
; compiler/tests/test_conformance.py -> C48 floating language expectations
; REV17/REV08 own the target syscall/opcode and native C48_REGCALL contracts.

    MACRO EMIT_P1117_C48_FLOAT_RUNTIME
c48_fp_req:                 defs FPOP1_SIZE,0
c48_fp_hidden_result:       dw 0
c48_fp_runtime_exit_status: db 0

; int zx_fp_exec(op,const float *lhs,const float *rhs,float *out)
; Normal C48_REGCALL: HL=op, DE=lhs, BC=rhs, out is first stack word.
zx_fp_exec:
    ld a,h
    or a
    jp nz,c48_fp_public_inval
    ld a,l
    ld (c48_fp_req+FPOP1_OP_O),a
    xor a
    ld (c48_fp_req+FPOP1_RESERVED_O),a
    ld (c48_fp_req+FPOP1_LHS_O),de
    ld (c48_fp_req+FPOP1_RHS_O),bc
    ld hl,2
    add hl,sp
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (c48_fp_req+FPOP1_OUT_O),de
    ld hl,c48_fp_req
    ld a,SYS_FP_EXEC
    call SYSCALL_GATEWAY
    jp c,c48_fp_public_errno
    ld hl,0
    xor a
    ret

c48_fp_public_errno:
    ld l,a
    ld h,0
    or a
    ret
c48_fp_public_inval:
    ld hl,E_INVAL
    ld a,l
    or a
    ret

__fadd:
    ld a,FPOP_OP_ADD
    jp c48_fp_hidden_binary
__fsub:
    ld a,FPOP_OP_SUB
    jp c48_fp_hidden_binary
__fmul:
    ld a,FPOP_OP_MUL
    jp c48_fp_hidden_binary
__fdiv:
    ld a,FPOP_OP_DIV
    jp c48_fp_hidden_binary
__fpow:
    ld a,FPOP_OP_POW
    jp c48_fp_hidden_binary

__fabs:
    ld a,FPOP_OP_ABS
    jp c48_fp_hidden_unary
__fsgn:
    ld a,FPOP_OP_SGN
    jp c48_fp_hidden_unary
__fint:
    ld a,FPOP_OP_INT
    jp c48_fp_hidden_unary
__fexp:
    ld a,FPOP_OP_EXP
    jp c48_fp_hidden_unary
__fln:
    ld a,FPOP_OP_LN
    jp c48_fp_hidden_unary
__fsin:
    ld a,FPOP_OP_SIN
    jp c48_fp_hidden_unary
__fcos:
    ld a,FPOP_OP_COS
    jp c48_fp_hidden_unary
__ftan:
    ld a,FPOP_OP_TAN
    jp c48_fp_hidden_unary
__fasin:
    ld a,FPOP_OP_ASN
    jp c48_fp_hidden_unary
__facos:
    ld a,FPOP_OP_ACS
    jp c48_fp_hidden_unary
__fatan:
    ld a,FPOP_OP_ATN
    jp c48_fp_hidden_unary
__fsqrt:
    ld a,FPOP_OP_SQR
    jp c48_fp_hidden_unary

c48_fp_hidden_binary:
    ld (c48_fp_hidden_result),hl
    ld (c48_fp_req+FPOP1_OP_O),a
    xor a
    ld (c48_fp_req+FPOP1_RESERVED_O),a
    ld (c48_fp_req+FPOP1_LHS_O),de
    ld (c48_fp_req+FPOP1_RHS_O),bc
    ld de,(c48_fp_hidden_result)
    ld (c48_fp_req+FPOP1_OUT_O),de
    jp c48_fp_hidden_call

c48_fp_hidden_unary:
    ld (c48_fp_hidden_result),hl
    ld (c48_fp_req+FPOP1_OP_O),a
    xor a
    ld (c48_fp_req+FPOP1_RESERVED_O),a
    ld (c48_fp_req+FPOP1_LHS_O),de
    ld de,0
    ld (c48_fp_req+FPOP1_RHS_O),de
    ld de,(c48_fp_hidden_result)
    ld (c48_fp_req+FPOP1_OUT_O),de

c48_fp_hidden_call:
    ld hl,c48_fp_req
    ld a,SYS_FP_EXEC
    call SYSCALL_GATEWAY
    jp c,c48_fp_runtime_error
    ld hl,(c48_fp_hidden_result)
    xor a
    ret

c48_fp_runtime_error:
    ld a,1
    ld (c48_fp_runtime_exit_status),a
    ld hl,1
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ld a,E_INVAL
    scf
    ret
    ENDM

; P11.18 C48 int/float cast runtime helpers.
; Pinned SDK mapping: 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/semantics.py and compiler/c48/float5.py define source conversion
; semantics; REV17/REV08 own this target-native syscall and C48_REGCALL mapping.
    MACRO EMIT_P1118_C48_CAST_RUNTIME
c48_itof_req:           defs ITOF1_SIZE,0
c48_ftoi_req:           defs FTOI1_SIZE,0
c48_cast_result_ptr:    dw 0
c48_ftoi_result:        dw 0

; float __itof(u16 value,u16 is_signed)
; Hidden float result pointer occupies HL; users are shifted to DE,BC.
__itof:
    ld (c48_cast_result_ptr),hl
    ld (c48_itof_req+ITOF1_VALUE_O),de
    ld a,b
    or a
    jp nz,c48_cast_runtime_error
    ld a,c
    cp 2
    jp nc,c48_cast_runtime_error
    ld (c48_itof_req+ITOF1_SIGNED_O),a
    xor a
    ld (c48_itof_req+ITOF1_RESERVED_O),a
    ld de,(c48_cast_result_ptr)
    ld (c48_itof_req+ITOF1_OUT_O),de
    ld hl,c48_itof_req
    ld a,SYS_INT_TO_FP
    call SYSCALL_GATEWAY
    jp c,c48_cast_runtime_error
    ld hl,(c48_cast_result_ptr)
    xor a
    ret

; int __ftoi(const float *value,u16 is_signed)
; Ordinary C48_REGCALL: HL=value pointer, DE=0/1 signed selector.
__ftoi:
    ld (c48_ftoi_req+FTOI1_IN_O),hl
    ld a,d
    or a
    jp nz,c48_cast_runtime_error
    ld a,e
    cp 2
    jp nc,c48_cast_runtime_error
    ld (c48_ftoi_req+FTOI1_SIGNED_O),a
    xor a
    ld (c48_ftoi_req+FTOI1_RESERVED_O),a
    ld hl,c48_ftoi_result
    ld (c48_ftoi_req+FTOI1_OUT_O),hl
    ld hl,c48_ftoi_req
    ld a,SYS_FP_TO_INT
    call SYSCALL_GATEWAY
    jp c,c48_cast_runtime_error
    ld hl,(c48_ftoi_result)
    xor a
    ret

c48_cast_runtime_error:
    ld hl,1
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ld a,E_INVAL
    scf
    ret
    ENDM

; P11.19 C48 floating comparison runtime.
; Pinned SDK mapping: 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/float5.py and compiler/c48/vm.py define source comparison/truth
; semantics; REV17/REV08 own FCMP1 and the target-native syscall contract.
    MACRO EMIT_P1119_C48_FCMP_RUNTIME
C48_FP_REL_LT             EQU 1
C48_FP_REL_LE             EQU 2
C48_FP_REL_EQ             EQU 3
C48_FP_REL_NE             EQU 4
C48_FP_REL_GT             EQU 5
C48_FP_REL_GE             EQU 6

c48_fcmp_req:             defs FCMP1_SIZE,0
c48_fcmp_result:          db 0
c48_fp_exact_zero:        db 0,0,0,0,0

; int __fcmp(const float *lhs,const float *rhs)
; Ordinary C48_REGCALL: HL=lhs pointer, DE=rhs pointer. Return HL=-1,0,+1.
__fcmp:
    ld (c48_fcmp_req+FCMP1_LHS_O),hl
    ld (c48_fcmp_req+FCMP1_RHS_O),de
    ld hl,c48_fcmp_result
    ld (c48_fcmp_req+FCMP1_OUT_O),hl
    ld hl,c48_fcmp_req
    ld a,SYS_FP_CMP
    call SYSCALL_GATEWAY
    jp c,c48_fcmp_runtime_error
    ld a,(c48_fcmp_result)
    ld l,a
    add a,a
    sbc a,a
    ld h,a
    xor a
    ret

; A=C48_FP_REL_*, HL=__fcmp signed result. Return HL=0/1.
c48_fcmp_rel:
    cp C48_FP_REL_LT
    jp z,c48_fcmp_rel_lt
    cp C48_FP_REL_LE
    jp z,c48_fcmp_rel_le
    cp C48_FP_REL_EQ
    jp z,c48_fcmp_rel_eq
    cp C48_FP_REL_NE
    jp z,c48_fcmp_rel_ne
    cp C48_FP_REL_GT
    jp z,c48_fcmp_rel_gt
    cp C48_FP_REL_GE
    jp z,c48_fcmp_rel_ge
    jp c48_fcmp_runtime_error
c48_fcmp_rel_lt:
    bit 7,h
    jr nz,c48_fcmp_true
    jr c48_fcmp_false
c48_fcmp_rel_le:
    bit 7,h
    jr nz,c48_fcmp_true
    ld a,h
    or l
    jr z,c48_fcmp_true
    jr c48_fcmp_false
c48_fcmp_rel_eq:
    ld a,h
    or l
    jr z,c48_fcmp_true
    jr c48_fcmp_false
c48_fcmp_rel_ne:
    ld a,h
    or l
    jr nz,c48_fcmp_true
    jr c48_fcmp_false
c48_fcmp_rel_gt:
    bit 7,h
    jr nz,c48_fcmp_false
    ld a,h
    or l
    jr nz,c48_fcmp_true
    jr c48_fcmp_false
c48_fcmp_rel_ge:
    bit 7,h
    jr z,c48_fcmp_true
c48_fcmp_false:
    ld hl,0
    xor a
    ret
c48_fcmp_true:
    ld hl,1
    xor a
    ret

; int truth(float value): compare through __fcmp against exact five-byte zero.
__ftruth:
    ld de,c48_fp_exact_zero
    call __fcmp
    ld a,h
    or l
    jr nz,c48_fcmp_true
    jr c48_fcmp_false

c48_fcmp_runtime_error:
    ld hl,1
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ld a,E_INVAL
    scf
    ret
    ENDM
