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
; Alternate-bank IM2 heartbeat. The interrupt never schedules a process.

    MACRO EMIT_INTERRUPT_ROUTINE
; in: IM2 entry.
; out: primary registers and IY preserved; one frame counted.
; flags: restored with AF.
; clobber: alternate AF/BC/DE/HL only.
zx48_interrupt:
    ex af,af'
    exx
    ld hl,(kernel_ticks)
    inc hl
    ld (kernel_ticks),hl
    ld a,h
    or l
    jr nz,zx48_interrupt_frames
    ld hl,(kernel_ticks+2)
    inc hl
    ld (kernel_ticks+2),hl
zx48_interrupt_frames:
    ld hl,ROM_FRAMES
    inc (hl)
    jr nz,zx48_interrupt_done
    inc hl
    inc (hl)
    jr nz,zx48_interrupt_done
    inc hl
    inc (hl)
zx48_interrupt_done:
    exx
    ex af,af'
    ei
    reti

altreg_busy:
    db 0
kernel_ticks:
    dw 0,0
    ENDM
