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
; Alternate-register-safe IM2 heartbeat. AF'/BC'/DE'/HL' are OS-private scratch.
; If foreground code has declared alternate-bank ownership, the ISR uses the
; primary stack-safe path instead. Neither path schedules a process.

    MACRO EMIT_INTERRUPT_ROUTINE
; Inputs: IM2 entry with interrupted task state.
; Outputs: primary registers and IY preserved exactly; accepted frame counted.
; Flags: restored.
; Clobbers: no conforming task-visible state.
zx48_interrupt:
    ex af,af'
    exx
    ld a,(altreg_busy)
    or a
    jr nz,zx48_interrupt_safe_switch
    call zx48_interrupt_tick_alt
    exx
    ex af,af'
    ei
    reti
zx48_interrupt_safe_switch:
    exx
    ex af,af'
    push af
    push bc
    push de
    push hl
    call zx48_interrupt_tick_primary
    pop hl
    pop de
    pop bc
    pop af
    ei
    reti

; Inputs: alternate register bank active.
; Outputs: 32-bit tick and ROM FRAMES mirror advanced one accepted frame.
; Flags: modified in OS-private bank.
; Clobbers: AF/BC/DE/HL alternate bank only.
zx48_interrupt_tick_alt:
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
    ret nz
    inc hl
    inc (hl)
    ret nz
    inc hl
    inc (hl)
    ret

; Inputs: primary task registers already saved on kernel-owned stack path.
; Outputs: same timing update as fast path.
; Flags: modified but caller restores AF.
; Clobbers: AF/HL while saved.
zx48_interrupt_tick_primary:
    ld hl,(kernel_ticks)
    inc hl
    ld (kernel_ticks),hl
    ld a,h
    or l
    jr nz,zx48_interrupt_frames_primary
    ld hl,(kernel_ticks+2)
    inc hl
    ld (kernel_ticks+2),hl
zx48_interrupt_frames_primary:
    ld hl,ROM_FRAMES
    inc (hl)
    ret nz
    inc hl
    inc (hl)
    ret nz
    inc hl
    inc (hl)
    ret

altreg_busy:
    db 0
kernel_ticks:
    dw 0,0
    ENDM
