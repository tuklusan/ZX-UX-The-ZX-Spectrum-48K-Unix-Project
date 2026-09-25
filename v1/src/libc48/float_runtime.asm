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
