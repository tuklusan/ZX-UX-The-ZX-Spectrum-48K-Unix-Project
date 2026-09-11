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
; Phase P0.04 minimal IM2 interrupt target.

    MACRO EMIT_INTERRUPT_ROUTINE
; Inputs: IM2 entry, primary registers owned by interrupted context.
; Outputs: returns to interrupted code without scheduling.
; Flags: restored by CPU context contract in later Phase 1 implementation.
; Clobbers: none in this scaffold.
zx48_interrupt:
    ei
    reti
    ENDM
