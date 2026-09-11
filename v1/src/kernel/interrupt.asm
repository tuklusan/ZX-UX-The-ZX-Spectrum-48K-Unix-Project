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
; Phase P0.06 alternate-register-safe IM2 interrupt target.
;
; AF'/BC'/DE'/HL' are OS-private volatile scratch. The ISR swaps the interrupted
; primary context out of harm's way, does no ROM call, and swaps it back before
; returning. No persistent kernel datum is stored only in the alternate bank.

    MACRO EMIT_INTERRUPT_ROUTINE
; Inputs: IM2 entry with interrupted primary register context.
; Outputs: primary AF/BC/DE/HL restored exactly; scheduling is not performed here.
; Flags: restored with AF by EX AF,AF'.
; Clobbers: OS-private alternate register contents only.
zx48_interrupt:
    ex af,af'
    exx
    exx
    ex af,af'
    ei
    reti
    ENDM
