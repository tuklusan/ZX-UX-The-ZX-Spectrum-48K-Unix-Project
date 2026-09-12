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
; Phase P0.04 IM2 setup and fixed trampoline.

    MACRO EMIT_IM2_ROUTINES
; Inputs: interrupts disabled or caller accepts that this routine executes DI.
; Outputs: I=IM2_I_VALUE, IM 2 selected, table bytes all IM2_VECTOR_BYTE.
; Also clears the bounded interrupt/emergency state at FF01..ERROR_STATE_END-1.
; Flags: modified.
; Clobbers: AF/BC/DE/HL.
zx48_im2_init:
    di
    ld hl,IM2_TABLE_START
    ld de,IM2_TABLE_START+1
    ld (hl),IM2_VECTOR_BYTE
    ld bc,IM2_TABLE_END-IM2_TABLE_START
    ldir
    ld a,IM2_I_VALUE
    ld i,a
    ; LDIR leaves DE at IM2_TABLE_END+1, exactly EMERGENCY_START.
    xor a
    ld b,ERROR_STATE_END-EMERGENCY_START
zx48_im2_clear_state:
    ld (de),a
    inc de
    djnz zx48_im2_clear_state
    im 2
    ret
    ENDM

    MACRO EMIT_IM2_TRAMPOLINE
kernel_im2_trampoline:
    jp zx48_interrupt
    ENDM
