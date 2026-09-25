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
; P11.20 public C48 ROM-backed math surface.
; Mandatory read-only SDK/reference baseline:
; 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/rommath.py -> ROM-compatible public math semantics
; compiler/c48/float5.py -> exact five-byte values and domain failures
; compiler/c48/vm.py -> public builtin dispatch/runtime-error behavior
; REV17/REV08 own native C48_REGCALL and serialized SYS_FP_EXEC execution.

    MACRO EMIT_P1120_C48_MATH_RUNTIME
; Float-return C48_REGCALL: hidden result pointer in HL; unary value pointer DE.
; pow uses DE=base pointer, BC=exponent pointer. The internal helpers own
; SYS_FP_EXEC serialization and process-status-1 runtime-error behavior.
sin:
    jp __fsin
cos:
    jp __fcos
tan:
    jp __ftan
asin:
    jp __fasin
acos:
    jp __facos
atan:
    jp __fatan
sqrt:
    jp __fsqrt
exp:
    jp __fexp
log:
    jp __fln
pow:
    jp __fpow
fabs:
    jp __fabs
    ENDM
