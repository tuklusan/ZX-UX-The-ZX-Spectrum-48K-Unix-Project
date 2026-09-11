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
; Five and only five release PANIC classes.

PANIC_PROCESS_TABLE       EQU $01
PANIC_ALLOCATOR           EQU $02
PANIC_SCHEDULER           EQU $03
PANIC_KERNEL_STACK        EQU $04
PANIC_ROM_CONTRACT        EQU $05

    MACRO EMIT_ERROR_ROUTINES
; Inputs: A = PANIC code 1..5.
; Outputs: never returns.
; Flags: unspecified.
; Clobbers: AF,BC,DE,HL.
zx48_panic:
    di
    cp PANIC_PROCESS_TABLE
    jr c,zx48_panic_unknown
    cp PANIC_ROM_CONTRACT+1
    jr nc,zx48_panic_unknown
    ld (kernel_panic_code),a
zx48_panic_halt:
    halt
    jr zx48_panic_halt
zx48_panic_unknown:
    ld a,PANIC_ROM_CONTRACT
    ld (kernel_panic_code),a
    jr zx48_panic_halt
    ENDM
