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

; Decode one supported foreground key without using the BASIC line editor.
; KEY-SCAN supplies exact shift/key numbers; K-DECODE is used in L mode.
zx48_keyboard_decode:
    call zx48_rom_key_scan
    jr nz,zx48_keyboard_none
    ld a,e
    cp $ff
    jr z,zx48_keyboard_none
    ld b,d
    ld d,0
    cp $27
    jr nc,zx48_keyboard_none
    cp $18
    jr nz,zx48_keyboard_main
    bit 7,b
    jr nz,zx48_keyboard_none
zx48_keyboard_main:
    ld hl,ROM_KEY_TABLE
    add hl,de
    ld a,(hl)
    ld e,a
    ld c,0
    dec d
    call zx48_rom_key_decode
    cp $80
    jr nc,zx48_keyboard_none
    cp $20
    jr nc,zx48_keyboard_decoded
    cp $0c
    jr z,zx48_keyboard_delete
    cp $08
    jr z,zx48_keyboard_decoded
    cp $09
    jr z,zx48_keyboard_decoded
    cp $0a
    jr z,zx48_keyboard_decoded
    cp $0b
    jr z,zx48_keyboard_decoded
    cp $0d
    jr nz,zx48_keyboard_none
zx48_keyboard_decoded:
    or a
    ret
zx48_keyboard_delete:
    ld a,$08
    or a
    ret
zx48_keyboard_none:
    ld a,E_AGAIN
    scf
    ret

; Owner reads block cooperatively in WAIT_INPUT until a supported key exists.
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
    cp HANDLE_FREE
    ret z
    call zx48_process_live_lookup
    ret c
    ld a,(ix+PROC_STATE)
    cp PROC_WAIT_INPUT
    ret nz
    ld a,(ix+PROC_PID)
    push af
    call zx48_keyboard_decode
    pop bc
    ret c
    ld a,b
    call zx48_process_live_lookup
    ret c
    ld (ix+PROC_STATE),PROC_READY
    xor a
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
