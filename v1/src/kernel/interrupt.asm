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
; Bounded IM2 heartbeat: ticks, ROM FRAMES, wall time and deferred cursor/BREAK.

    MACRO EMIT_INTERRUPT_ROUTINE
zx48_interrupt:
    ex af,af'
    exx
    ld a,(altreg_busy)
    or a
    jr nz,zx48_interrupt_safe
    call zx48_interrupt_tick
    exx
    ex af,af'
    ei
    reti
zx48_interrupt_safe:
    exx
    ex af,af'
    push af
    push bc
    push de
    push hl
    call zx48_interrupt_tick
    pop hl
    pop de
    pop bc
    pop af
    ei
    reti

zx48_interrupt_tick:
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
    jr nz,zx48_interrupt_wall
    inc hl
    inc (hl)
    jr nz,zx48_interrupt_wall
    inc hl
    inc (hl)
zx48_interrupt_wall:
    ld a,(wall_time_valid)
    or a
    jr z,zx48_interrupt_cursor
    ld a,(wall_subsecond)
    inc a
    cp 50
    jr c,zx48_interrupt_store_sub
    xor a
    ld (wall_subsecond),a
    ld hl,(wall_seconds)
    inc hl
    ld (wall_seconds),hl
    ld a,h
    or l
    jr nz,zx48_interrupt_cursor
    ld hl,(wall_seconds+2)
    inc hl
    ld (wall_seconds+2),hl
    jr zx48_interrupt_cursor
zx48_interrupt_store_sub:
    ld (wall_subsecond),a
zx48_interrupt_cursor:
    ld a,(cursor_frame_count)
    inc a
    cp 25
    jr c,zx48_interrupt_cursor_store
    xor a
    ld (cursor_frame_count),a
    ld a,1
    ld (tty_cursor_due),a
    jr zx48_interrupt_break
zx48_interrupt_cursor_store:
    ld (cursor_frame_count),a
zx48_interrupt_break:
    ; Direct CAPS SHIFT row then SPACE row; low byte FEh selects ULA keyboard.
    ld bc,$fefe
    in a,(c)
    bit 0,a
    ret nz
    ld bc,$7ffe
    in a,(c)
    bit 0,a
    ret nz
    ld a,1
    ld (break_pending),a
    ret

zx48_ticks_snapshot:
    di
    ld de,(kernel_ticks)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(kernel_ticks+2)
    ld (hl),e
    inc hl
    ld (hl),d
    ei
    xor a
    or a
    ret

zx48_time_get:
    ld a,(wall_time_valid)
    or a
    jr z,zx48_time_unset
    di
    ld de,(wall_seconds)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(wall_seconds+2)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(wall_revision)
    ld (hl),e
    inc hl
    ld (hl),d
    ei
    xor a
    or a
    ret
zx48_time_unset:
    ld a,E_AGAIN
    scf
    ret

; HL -> u32 seconds; maximum 2099-12-31 23:59:59 = F48656FFh.
zx48_time_set:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld a,b
    cp $f4
    jr c,zx48_time_set_commit
    jr nz,zx48_time_bad
    ld a,c
    cp $86
    jr c,zx48_time_set_commit
    jr nz,zx48_time_bad
    ld a,d
    cp $57
    jr nc,zx48_time_bad
zx48_time_set_commit:
    di
    ld (wall_seconds),de
    ld (wall_seconds+2),bc
    xor a
    ld (wall_subsecond),a
    ld a,1
    ld (wall_time_valid),a
    ld hl,(wall_revision)
    inc hl
    ld (wall_revision),hl
    ei
    xor a
    or a
    ret
zx48_time_bad:
    ld a,E_INVAL
    scf
    ret

altreg_busy: db 0
kernel_ticks: dw 0,0
wall_seconds: dw 0,0
wall_revision: dw 0
wall_subsecond: db 0
wall_time_valid: db 0
cursor_frame_count: db 0
    ENDM
