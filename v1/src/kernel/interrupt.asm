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
; Bounded IM2 heartbeat. No process scheduling, allocation, ROM call, or screen edit.

; IM2/time state belongs in the fixed interrupt/emergency data block.
INTERRUPT_STATE_BASE      EQU EMERGENCY_START
altreg_busy               EQU INTERRUPT_STATE_BASE+0
scheduler_tick_due        EQU INTERRUPT_STATE_BASE+1
cursor_frame_count        EQU INTERRUPT_STATE_BASE+2
kernel_ticks              EQU INTERRUPT_STATE_BASE+3
wall_seconds              EQU INTERRUPT_STATE_BASE+7
wall_revision             EQU INTERRUPT_STATE_BASE+11
wall_subsecond            EQU INTERRUPT_STATE_BASE+13
wall_valid                EQU INTERRUPT_STATE_BASE+14
INTERRUPT_STATE_END       EQU INTERRUPT_STATE_BASE+15

    MACRO EMIT_INTERRUPT_ROUTINE
zx48_interrupt:
    push af
    ld a,(altreg_busy)
    or a
    jr nz,zx48_interrupt_safe
    pop af
    ex af,af'
    exx
    call zx48_interrupt_work
    exx
    ex af,af'
    ei
    reti
zx48_interrupt_safe:
    push bc
    push de
    push hl
    call zx48_interrupt_work
    pop hl
    pop de
    pop bc
    pop af
    ei
    reti

; Runs either in the alternate bank or behind full primary AF/BC/DE/HL saves.
zx48_interrupt_work:
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
    jr nz,zx48_interrupt_timers
    inc hl
    inc (hl)
    jr nz,zx48_interrupt_timers
    inc hl
    inc (hl)
zx48_interrupt_timers:
    ld a,1
    ld (scheduler_tick_due),a
    ld a,(cursor_frame_count)
    inc a
    cp 25
    jr c,zx48_interrupt_cursor_store
    xor a
    ld (tty_cursor_due),a
    inc a
    ld (tty_cursor_due),a
zx48_interrupt_cursor_store:
    ld (cursor_frame_count),a
    ld a,(wall_valid)
    or a
    jr z,zx48_interrupt_break
    ld a,(wall_subsecond)
    inc a
    cp ZX48_PAL_FRAME_HZ
    jr c,zx48_interrupt_wall_store
    xor a
    ld (wall_subsecond),a
    ld hl,(wall_seconds)
    inc hl
    ld (wall_seconds),hl
    ld a,h
    or l
    jr nz,zx48_interrupt_break
    ld hl,(wall_seconds+2)
    inc hl
    ld (wall_seconds+2),hl
    jr zx48_interrupt_break
zx48_interrupt_wall_store:
    ld (wall_subsecond),a
zx48_interrupt_break:
    ; BREAK is CAPS SHIFT + SPACE, active low. Use 16-bit BC-selected ULA rows.
    ld bc,$FEFE
    in a,(c)
    bit 0,a
    jr nz,zx48_interrupt_done
    ld bc,$7FFE
    in a,(c)
    bit 0,a
    jr nz,zx48_interrupt_done
    ld a,1
    ld (break_pending),a
zx48_interrupt_done:
    ret
    ENDM
