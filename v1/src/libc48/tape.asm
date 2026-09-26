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
; P11.27 documented C48 cassette/time wrappers. All paths stay exact-case and
; cassette positioning remains sequential; there is deliberately no seek API.

    MACRO EMIT_P1127_C48_TAPE_RUNTIME
c48_ticks_u32: defs 4,0

c48_tape_errno:
    ld l,a
    ld h,0
    or a
    ret
c48_tape_zero:
    ld hl,0
    xor a
    ret

; int tape_save(char *path)
tape_save:
    ld a,SYS_TAPE_SAVE
    call SYSCALL_GATEWAY
    jp c,c48_tape_errno
    jp c48_tape_zero

; int tape_load(char *path)
tape_load:
    ld a,SYS_TAPE_LOAD
    call SYSCALL_GATEWAY
    jp c,c48_tape_errno
    jp c48_tape_zero

; unsigned int ticks(void). The public C48 integer is 16-bit; the kernel source
; remains an independent modulo-2^32 counter and the wrapper samples it through
; the exact four-byte SYS_TICKS record, returning its low word.
ticks:
    ld hl,c48_ticks_u32
    ld a,SYS_TICKS
    call SYSCALL_GATEWAY
    jp c,c48_tape_errno
    ld hl,(c48_ticks_u32)
    xor a
    ret

; int time_get(void *time1): exact six-byte TIME1 destination.
time_get:
    ld a,SYS_TIME_GET
    call SYSCALL_GATEWAY
    jp c,c48_tape_errno
    jp c48_tape_zero

; int time_set(void *u32_seconds): exact four-byte seconds input.
time_set:
    ld a,SYS_TIME_SET
    call SYSCALL_GATEWAY
    jp c,c48_tape_errno
    jp c48_tape_zero
    ENDM
