; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; Separate C objects get 32 UDG slots; whole programs use their --udgs bank. (ZX-UX SDK)
        section data
; @nudg: 1 data byte. Thirty-two slots, no guest list.
@nudg:  db 32
        section bss
; @udgs: 256 BSS bytes. Eight per glyph; RAM does the arithmetic.
@udgs:  ds 256
