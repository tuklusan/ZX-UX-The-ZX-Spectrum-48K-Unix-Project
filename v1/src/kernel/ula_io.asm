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
; Sole production owner for ULA output. Border, MIC and beeper bits are changed
; only through the software shadow; EAR is input-only.

    MACRO EMIT_ULA_ROUTINES
zx48_ula_init:
    xor a
    ld (ula_shadow),a
    out (ULA_PORT),a
    ret

; Inputs A=border 0..7. Outputs shadow/port updated atomically.
zx48_ula_set_border:
    and ULA_BORDER_MASK
    ld b,a
    ld a,(ula_shadow)
    and $f8
    or b
    ld (ula_shadow),a
    out (ULA_PORT),a
    ret

; Inputs A=bit mask containing only MIC/BEEPER bit positions, C=new bits.
zx48_ula_update_sound:
    ld b,a
    cpl
    ld d,a
    ld a,(ula_shadow)
    and d
    ld d,a
    ld a,c
    and b
    or d
    ld (ula_shadow),a
    out (ULA_PORT),a
    ret

ula_shadow:
    db 0
    ENDM
