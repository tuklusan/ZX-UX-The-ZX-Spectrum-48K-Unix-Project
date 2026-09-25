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
; P11.14/P11.16 libc48 five-byte floating representation/return bridge.
; Arithmetic and conversions remain kernel/ROM-backed; this bridge freezes the
; in-memory object width/alignment and exact object-copy operation.

    MACRO EMIT_P11_C48_FLOAT5_BRIDGE
C48_FLOAT_SIZE           EQU 5
C48_FLOAT_ALIGN          EQU 1

; HL=source, DE=destination. Copy exactly one C48 float object.
c48_float_copy5:
    ld bc,C48_FLOAT_SIZE
    ldir
    xor a
    ret

; A=claimed ABI width. Four-byte/IEEE assumptions fail closed.
c48_float_require_size:
    cp C48_FLOAT_SIZE
    jr nz,c48_float_size_bad
    xor a
    ret
c48_float_size_bad:
    ld a,E_FORMAT
    scf
    ret

; P11.16: HL=hidden result pointer, DE=source five-byte value.
; Copy exactly five bytes and return the original hidden pointer in HL.
c48_float_return5:
    push hl
    ex de,hl
    ld bc,C48_FLOAT_SIZE
    ldir
    pop hl
    xor a
    ret
    ENDM
