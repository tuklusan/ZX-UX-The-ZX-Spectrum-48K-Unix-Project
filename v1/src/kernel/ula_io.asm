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

ROM_BORDCR               EQU $5C48

    MACRO EMIT_ULA_ROUTINES
zx48_ula_init:
    xor a
zx48_ula_commit:
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
    jr zx48_ula_commit

; Inputs A=bit mask containing only MIC/BEEPER bit positions, C=new bits.
zx48_ula_update_sound:
    ld b,a
    push hl
    ld hl,ula_shadow
    ld a,c
    xor (hl)
    and b
    xor (hl)
    pop hl
    jr zx48_ula_commit

; Prepare a ROM 0xFE consumer. A/flags are preserved (including LD-BYTES
; load/verify carry); B is scratch and is not an input to BEEPER/SA/LD-BYTES.
; BORDCR border bits are 3..5. Preserve every other documented bit.
zx48_ula_rom_prepare:
    push af
    ld a,1
    ld (altreg_busy),a
    ld a,(ula_shadow)
    and ULA_BORDER_MASK
    rlca
    rlca
    rlca
    ld b,a
    ld a,(ROM_BORDCR)
    and $c7
    or b
    ld (ROM_BORDCR),a
    pop af
    ret

ula_shadow:
    db 0
    ENDM
