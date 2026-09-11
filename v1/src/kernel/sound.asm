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
; Synchronous beeper service. Five-byte public values are consumed through the
; ROM calculator gateway; the low-level BEEPER wrapper remains centralized.

    MACRO EMIT_SOUND_ROUTINES
; HL=duration five-byte value, DE=pitch five-byte value.
zx48_sound_beep:
    ; The ROM public BEEP path is the architecture-approved BASIC-compatible
    ; semantics. Inputs are already validated as five-byte user values.
    call zx48_rom_beep_values
    ret
    ENDM
