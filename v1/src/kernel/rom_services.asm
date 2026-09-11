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
; Phase P0.05 ROM-service IY ownership scaffold.
;
; All approved ROM wrappers are emitted from this module and must leave IY at
; ROM_IY_ANCHOR on every returning path.

    MACRO EMIT_ROM_SERVICE_ROUTINES
; Inputs: none.
; Outputs: IY restored to the immutable ROM ERR_NR anchor.
; Flags: unchanged.
; Clobbers: IY by ABI ownership.
zx48_rom_restore_iy:
    ld iy,ROM_IY_ANCHOR
    ret
    ENDM
