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
; Cooperative keyboard owner. Full decoding is never performed from IM2.

KEYBOARD_STATE_BASE      EQU CONSOLE_STATE_END
tty_input_owner          EQU KEYBOARD_STATE_BASE+0
break_pending            EQU KEYBOARD_STATE_BASE+1
KEYBOARD_STATE_END       EQU KEYBOARD_STATE_BASE+2
    ASSERT KEYBOARD_STATE_END <= EMERGENCY_END+1

    MACRO EMIT_KEYBOARD_ROUTINES
zx48_keyboard_init:
    ld a,HANDLE_FREE
    ld (tty_input_owner),a
    xor a
    ld (break_pending),a
    ret

; Inputs none. Outputs carry clear A=decoded key or carry set E_AGAIN.
; Production foreground polling delegates matrix/debounce semantics to the
; verified ROM service while preserving the ZX-UX IY contract.
zx48_keyboard_getkey:
    ld a,(current_pid)
    ld b,a
    ld a,(tty_input_owner)
    cp HANDLE_FREE
    jr z,zx48_keyboard_claim
    cp b
    jr nz,zx48_keyboard_busy
zx48_keyboard_claim:
    ld a,b
    ld (tty_input_owner),a
    call zx48_rom_key_scan
    ld a,e
    cp $ff
    jr z,zx48_keyboard_none
    ld a,l
    or a
    ret
zx48_keyboard_none:
    ld a,E_AGAIN
    scf
    ret
zx48_keyboard_busy:
    ld a,E_BUSY
    scf
    ret

; Inputs none. Outputs owner released only by current owner.
zx48_keyboard_release:
    ld a,(current_pid)
    ld b,a
    ld a,(tty_input_owner)
    cp b
    ret nz
    ld a,HANDLE_FREE
    ld (tty_input_owner),a
    ret
    ENDM
