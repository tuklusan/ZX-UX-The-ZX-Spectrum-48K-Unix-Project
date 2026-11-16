; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; Separate SSB1 objects use the full @vmtab; empty @gs/@ct resolve VM names. (ZX-UX SDK)
; Whole-program rcc supplies its own tables. No phantom globals.
        section data
        align 2
; @gs/@ct: 0 data bytes. Two aliases for an empty table. Nothing to see.
@gs:
@ct:
