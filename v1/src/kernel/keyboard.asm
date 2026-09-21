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
    ld hl,0
    ld (tty_input_owner),hl
    ret

; Decode one supported foreground key without using the BASIC line editor.
; KEY-SCAN/K-TEST supply exact shift/main codes; K-DECODE is used in L mode.
zx48_keyboard_decode:
    call zx48_rom_key_scan
    jr nz,zx48_keyboard_none
    ; KEY-SCAN returns exact valid key positions in DE. 27h is CAPS SHIFT
    ; and 24h is physical 1. Invalid or >2-key chords return NZ above.
    ld a,d
    cp $27
    jr nz,zx48_keyboard_decode_rom
    ld a,e
    cp $24
    ld a,$1B
    ret z
zx48_keyboard_decode_rom:
    call zx48_rom_k_test
    jr nc,zx48_keyboard_none
    ld c,0
    dec d
    ld e,a
    call zx48_rom_key_decode
    cp $80
    jr nc,zx48_keyboard_none
    cp $20
    jr nc,zx48_keyboard_decoded
    cp $08
    jr c,zx48_keyboard_none
    cp $0e
    jr nc,zx48_keyboard_none
    cp $0c
    jr nz,zx48_keyboard_decoded
    ld a,$08
zx48_keyboard_decoded:
    or a
    ret
zx48_keyboard_none:
    ld a,E_AGAIN
    scf
    ret

; Only the current nonzero tty owner may read. Owner PID 0 means unowned.
; Service deferred cursor parity at the first safe input point before either
; delivering a key or putting the owner back to sleep.
zx48_keyboard_getkey:
    ld hl,tty_input_owner
    ld a,(current_pid)
    or a
    jr z,zx48_keyboard_busy
    cp (hl)
    jr nz,zx48_keyboard_busy
    call zx48_cursor_service
    call zx48_keyboard_decode
    ret nc
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    ld (ix+PROC_STATE),PROC_WAIT_INPUT
    jp zx48_schedule

; Called only outside IM2. Wake the live tty owner when a decodable key is down.
zx48_keyboard_wake_input:
    ld a,(tty_input_owner)
    or a
    ret z
    call zx48_process_live_lookup
    ret c
    ld a,(ix+PROC_STATE)
    cp PROC_WAIT_INPUT
    ret nz
    ; ROM KEY-SCAN/K-TEST/K-DECODE preserve IX, and IM2 never schedules.
    ; The already validated live owner descriptor therefore remains current.
    call zx48_keyboard_decode
    ret c
    ld (ix+PROC_STATE),PROC_READY
    xor a
    ret

zx48_keyboard_busy:
    ld a,E_BUSY
    scf
    ret

; Inputs none. Release only the current owner; PID 0 is the sole unowned value.
zx48_keyboard_release:
    ld hl,tty_input_owner
    ld a,(current_pid)
    cp (hl)
    ret nz
    ld (hl),0
    ret
    ENDM
