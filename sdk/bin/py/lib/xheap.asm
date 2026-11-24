; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; Separate C objects get this default heap; whole-program rcc supplies its own. (ZX-UX SDK)
; Requested live bytes max out at 1024; backing space is 1280. RAM bills by the byte.
        section data
        align 2
; ___heapw: 2 data bytes. 640 words of backing space, headers included.
___heapw:       dw 640                  ; (1024 + 256) / 2 words
; ___heapsz: 2 data bytes. Live requests cap at 1024 bytes.
___heapsz:      dw 1024
        section bss
        align 2
; ___heap: 1280 BSS bytes. The allocator owns the furniture.
___heap:        ds 1280
