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
; Permanent Sinclair BASIC -> ZX-UX handoff and resident subsystem initialization.

    MACRO EMIT_BOOT_GATEWAY
boot_gateway:
    jp zx48_boot_main
    ENDM

    MACRO EMIT_BOOT_BODY
zx48_boot_main:
    jp zx48_boot_main_impl
    ENDM

    MACRO EMIT_BOOT_IMPL
zx48_boot_main_impl:
    di
    ld sp,BOOT_STACK_TOP
    ld iy,ROM_IY_ANCHOR
    ; Do not rely on zero-filled load bytes for mutable emergency/interrupt state.
    ; Clear only the documented state block; stack, display, ROM workspace and
    ; IM2 trampoline/table remain outside this initialization range.
    xor a
    ld hl,EMERGENCY_START
    ld de,EMERGENCY_START+1
    ld bc,ERROR_STATE_END-EMERGENCY_START-1
    ld (hl),a
    ldir
    call zx48_kernel_stack_init
    call zx48_memory_init
    call zx48_process_init
    call zx48_handles_init
    call zx48_pipe_init
    call zx48_ula_init
    call zx48_console_init
    call zx48_keyboard_init
    call zx48_udg_init
    jp nc,zx48_boot_udg_ok
    ld a,PANIC_ALLOCATOR
    jp zx48_panic
zx48_boot_udg_ok:
    call zx48_im2_init
    jp zx48_idle_loop
    ENDM
