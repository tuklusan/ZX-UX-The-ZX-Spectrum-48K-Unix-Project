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
; /bin/sleep: one unsigned decimal seconds operand, 0..65535.
; Seconds are converted exactly to 50-Hz relative ticks and passed by pointer.

    MACRO EMIT_P815_SLEEP_ROUTINES
sleep_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 2
    jp nz,sleep_invalid
    ld de,8
    add ix,de
sleep_skip_argv0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,sleep_skip_argv0

    ld hl,0
    xor a
    ld (sleep_seen),a
sleep_parse_loop:
    ld a,(ix+0)
    or a
    jr z,sleep_parse_done
    cp '0'
    jp c,sleep_invalid
    cp '9'+1
    jp nc,sleep_invalid
    sub '0'
    ld c,a
    ld a,1
    ld (sleep_seen),a

    ld a,h
    cp $19
    jr c,sleep_mul10
    jp nz,sleep_invalid
    ld a,l
    cp $99
    jr c,sleep_mul10
    jp nz,sleep_invalid
    ld a,c
    cp 6
    jp nc,sleep_invalid

sleep_mul10:
    ld d,h
    ld e,l
    add hl,hl
    add hl,hl
    add hl,de
    add hl,hl
    ld b,0
    add hl,bc
    inc ix
    jr sleep_parse_loop

sleep_parse_done:
    ld a,(sleep_seen)
    or a
    jp z,sleep_invalid
    ld de,hl
    ld hl,0
    ld (sleep_ticks),hl
    ld (sleep_ticks+2),hl
    ld bc,0
    ld a,50
sleep_tick_loop:
    ld hl,(sleep_ticks)
    add hl,de
    ld (sleep_ticks),hl
    ld hl,(sleep_ticks+2)
    adc hl,bc
    ld (sleep_ticks+2),hl
    dec a
    jr nz,sleep_tick_loop

    ld hl,sleep_ticks
    ld a,SYS_SLEEP
    call SYSCALL_GATEWAY
    jr c,sleep_error
    ld l,0
    jr sleep_exit

sleep_invalid:
    ld a,E_INVAL
sleep_error:
    ld l,a
sleep_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

sleep_seen: db 0
sleep_ticks: defs 4,0
sleep_end:
    ENDM
