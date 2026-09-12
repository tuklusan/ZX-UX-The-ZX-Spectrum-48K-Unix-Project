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
; Five and only five release PANIC classes plus the frozen kernel-stack guard.

PANIC_PROCESS_TABLE       EQU $01
PANIC_ALLOCATOR           EQU $02
PANIC_SCHEDULER           EQU $03
PANIC_KERNEL_STACK        EQU $04
PANIC_ROM_CONTRACT        EQU $05
KSTACK_GUARD_BYTE         EQU $A5
KSTACK_GUARD_SIZE         EQU 16

; Panic/stack instrumentation is emergency state, not ordinary code/data.
kernel_panic_code         EQU INTERRUPT_STATE_END+0
kernel_stack_low_water    EQU INTERRUPT_STATE_END+1
ERROR_STATE_END           EQU INTERRUPT_STATE_END+3

    MACRO EMIT_ERROR_ROUTINES
zx48_kernel_stack_init:
    ld hl,KERNEL_STACK_START
    ld b,KSTACK_GUARD_SIZE
    ld a,KSTACK_GUARD_BYTE
zx48_kernel_stack_init_loop:
    ld (hl),a
    inc hl
    djnz zx48_kernel_stack_init_loop
    ld hl,BOOT_STACK_TOP
    ld (kernel_stack_low_water),hl
    ret

zx48_kernel_stack_check:
    ld hl,KERNEL_STACK_START
    ld b,KSTACK_GUARD_SIZE
zx48_kernel_stack_check_loop:
    ld a,(hl)
    cp KSTACK_GUARD_BYTE
    jr nz,zx48_kernel_stack_panic
    inc hl
    djnz zx48_kernel_stack_check_loop
    ret
zx48_kernel_stack_panic:
    ld a,PANIC_KERNEL_STACK
    jp zx48_panic

; Sample current SP and retain the true deepest kernel-stack value, including
; this helper's own temporary push. Interrupts on user FAST stacks are ignored.
zx48_kernel_stack_sample:
    ld hl,0
    add hl,sp
    dec hl
    dec hl
    ld a,h
    cp $fb
    ret c
    cp $fd
    ret nc
    ld de,(kernel_stack_low_water)
    push hl
    or a
    sbc hl,de
    pop hl
    ret nc
    ld (kernel_stack_low_water),hl
    ret

zx48_panic:
    di
    or a
    jr z,zx48_panic_unknown
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
