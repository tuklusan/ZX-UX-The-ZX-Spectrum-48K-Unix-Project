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
; P7.18 C48_REGCALL bridge passes duration/pitch as the same five-byte pointers.
; P7.20 shell beep reaches this same synchronous service after both operands pass the safe calculator conversion used by calc.
; P7.09 synchronous BASIC-compatible note.
; HL=duration five-byte value, DE=pitch five-byte value.
zx48_sound_beep:
    call zx48_rom_beep_values
    ret
    ENDM
; P7.20 qualification head marker.
