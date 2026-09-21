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
; Reversible bitmap-only cursor with balanced nested screen mutation.

TTY_CURSOR_OFF           EQU 0
TTY_CURSOR_UNDERLINE     EQU 1
TTY_CURSOR_BLOCK         EQU 2

CURSOR_STATE_BASE        EQU ERROR_STATE_END
cursor_phase             EQU CURSOR_STATE_BASE+0
screen_mutation_depth    EQU CURSOR_STATE_BASE+1
CURSOR_STATE_END         EQU CURSOR_STATE_BASE+2

    MACRO EMIT_CURSOR_ROUTINES
zx48_cursor_depth_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

; Begin one kernel-owned screen mutation. Only the outermost begin removes XOR.
; Preserve HL because graphics and console callers carry coordinates across it.
zx48_screen_begin:
zx48_cursor_hide:
    push hl
    ld hl,screen_mutation_depth
    inc (hl)
    jr z,zx48_cursor_depth_panic
    ld a,(hl)
    dec a
    jr nz,zx48_screen_begin_done
    ld a,(tty_cursor_visible)
    or a
    jr z,zx48_screen_begin_done
    call zx48_cursor_xor
zx48_screen_begin_done:
    pop hl
    xor a
    ret

; Strict balanced end. Underflow is a deterministic scheduler-contract panic.
zx48_cursor_show:
zx48_screen_end:
    ld hl,screen_mutation_depth
    ld a,(hl)
    or a
    jr z,zx48_cursor_depth_panic
    dec (hl)
    jr nz,zx48_cursor_ok
    jr zx48_cursor_service_core

; Direct deferred service is legal only at a safe depth-zero boundary. Reaching
; it with an active mutation means an unmatched begin escaped its owner.
zx48_cursor_service:
    ld a,(screen_mutation_depth)
    or a
    jr nz,zx48_cursor_depth_panic

; Fetch/clear one-bit service parity atomically, preserving the caller's IFF2.
zx48_cursor_service_core:
    ld a,i
    push af
    di
    ld hl,cursor_service_parity
    ld a,(hl)
    ld (hl),0
    ld hl,cursor_phase
    xor (hl)
    ld (hl),a
    pop af
    jp po,zx48_cursor_reconcile
    ei
zx48_cursor_reconcile:
    ld a,(tty_cursor_shape)
    or a
    ld a,(hl)
    jr nz,zx48_cursor_desired
    xor a
zx48_cursor_desired:
    ld hl,tty_cursor_visible
    xor (hl)
    ret z

; Toggle exactly the current cursor bitmap footprint and physical-drawn state.
; Reconciliation falls through here only when physical XOR must change.
zx48_cursor_xor:
    ld a,(tty_cursor_shape)
    dec a
    ld de,8
    jr nz,zx48_cursor_xor_loop
    ld de,$0701
zx48_cursor_xor_loop:
    ld a,(tty_row)
    add a,a
    add a,a
    add a,a
    add a,d
    ld b,a
    ld a,(tty_col)
    ld c,a
    ld a,(tty_mode)
    cp TTY_MODE_64
    jr z,zx48_cursor_64
    call zx48_bitmap_address
    ld a,(hl)
    xor $ff
    jr zx48_cursor_store
zx48_cursor_64:
    srl c
    push af
    call zx48_bitmap_address
    pop af
    ld a,(hl)
    jr c,zx48_cursor_64_right
    xor $f0
    jr zx48_cursor_store
zx48_cursor_64_right:
    xor $0f
zx48_cursor_store:
    ld (hl),a
    inc d
    dec e
    jr nz,zx48_cursor_xor_loop
    ld hl,tty_cursor_visible
    inc (hl)
    res 1,(hl)
zx48_cursor_ok:
    xor a
    ret

; Compatibility/test helper: post one blink transition. During a mutation it is
; only a producer; at depth zero it immediately uses the safe service path.
zx48_cursor_blink:
    ld hl,cursor_service_parity
    inc (hl)
    res 1,(hl)
    ld a,(screen_mutation_depth)
    or a
    ret nz
    jr zx48_cursor_service_core
    ENDM


; P6.27 contract marker. Shell-level hiding is represented by cursor shape OFF,
; so normal shape reconciliation removes any currently drawn XOR without
; resetting cursor_phase; restoring the saved nonzero shape reconciles to the
; current logical blink phase rather than inventing a new clock edge.
P627_CURSOR_HIDDEN_SHAPE EQU TTY_CURSOR_OFF
