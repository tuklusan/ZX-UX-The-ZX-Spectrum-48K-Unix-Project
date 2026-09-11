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
; Cooperative round-robin scheduler. AF/BC/DE/HL/IX and return PC are stack state.

    MACRO EMIT_SCHEDULER_ROUTINES
zx48_schedule:
    push af
    push bc
    push de
    push hl
    push ix
    ld a,(current_pid)
    ld (scheduler_current),a
    call zx48_process_ptr
    ; Z80 has no LD (IX+d),SP; snapshot through HL.
    ld hl,0
    add hl,sp
    ld (ix+PROC_SAVED_SP),l
    ld (ix+PROC_SAVED_SP+1),h
    ld a,(ix+PROC_STATE)
    cp PROC_RUNNING
    jr nz,zx48_schedule_scan_start
    ld (ix+PROC_STATE),PROC_READY
zx48_schedule_scan_start:
    ld a,(scheduler_current)
    inc a
    and 7
    ld (scheduler_candidate),a
    ld b,MAX_PROCESSES
zx48_schedule_scan:
    push bc
    ld a,(scheduler_candidate)
    call zx48_process_ptr
    ld a,(ix+PROC_STATE)
    cp PROC_SLEEPING
    call z,zx48_scheduler_maybe_wake
    ld a,(ix+PROC_STATE)
    cp PROC_READY
    jr z,zx48_schedule_choose
    pop bc
    ld a,(scheduler_candidate)
    inc a
    and 7
    ld (scheduler_candidate),a
    djnz zx48_schedule_scan
    xor a
    ld (scheduler_candidate),a
    call zx48_process_ptr
    jr zx48_schedule_restore
zx48_schedule_choose:
    pop bc
zx48_schedule_restore:
    ld a,(scheduler_candidate)
    ld (current_pid),a
    ld (ix+PROC_STATE),PROC_RUNNING
    ld a,(ix+PROC_PRIVATE_FLAGS)
    or PROC_PRIVATE_STARTED
    ld (ix+PROC_PRIVATE_FLAGS),a
    ld l,(ix+PROC_SAVED_SP)
    ld h,(ix+PROC_SAVED_SP+1)
    ld sp,hl
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ld iy,ROM_IY_ANCHOR
    ret

; IX=SLEEPING. Signed modular 32-bit now-deadline >=0 wakes.
zx48_scheduler_maybe_wake:
    ld hl,(kernel_ticks)
    ld e,(ix+PROC_WAKE_TICK)
    ld d,(ix+PROC_WAKE_TICK+1)
    or a
    sbc hl,de
    ld hl,(kernel_ticks+2)
    ld e,(ix+PROC_WAKE_TICK+2)
    ld d,(ix+PROC_WAKE_TICK+3)
    sbc hl,de
    bit 7,h
    ret nz
    ld (ix+PROC_STATE),PROC_READY
    ret

; HL -> u32 relative ticks.
zx48_sleep_current:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    bit 7,b
    jr nz,zx48_sleep_bad
    ld a,b
    or c
    or d
    or e
    jr z,zx48_sleep_zero
    ld (scheduler_sleep_lo),de
    ld (scheduler_sleep_hi),bc
    ld a,(current_pid)
    call zx48_process_lookup
    ld hl,(kernel_ticks)
    ld de,(scheduler_sleep_lo)
    add hl,de
    ld (ix+PROC_WAKE_TICK),l
    ld (ix+PROC_WAKE_TICK+1),h
    ld hl,(kernel_ticks+2)
    ld de,(scheduler_sleep_hi)
    adc hl,de
    ld (ix+PROC_WAKE_TICK+2),l
    ld (ix+PROC_WAKE_TICK+3),h
    ld (ix+PROC_STATE),PROC_SLEEPING
    jp zx48_schedule
zx48_sleep_zero:
    xor a
    or a
    ret
zx48_sleep_bad:
    ld a,E_INVAL
    scf
    ret

zx48_scheduler_wake_scan:
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_PROCESSES-1
zx48_wake_scan_loop:
    ld a,(ix+PROC_STATE)
    cp PROC_SLEEPING
    call z,zx48_scheduler_maybe_wake
    ld de,PROC_DESC_SIZE
    add ix,de
    djnz zx48_wake_scan_loop
    ret

zx48_idle_loop:
    ei
    halt
    call zx48_scheduler_wake_scan
    ld a,(tty_cursor_due)
    or a
    jr z,zx48_idle_no_cursor
    call zx48_cursor_blink
    xor a
    ld (tty_cursor_due),a
zx48_idle_no_cursor:
    jp zx48_schedule

scheduler_current: db 0
scheduler_candidate: db 0
scheduler_sleep_lo: dw 0
scheduler_sleep_hi: dw 0
    ENDM
