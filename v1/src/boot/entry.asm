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
    call zx48_kernel_stack_init
    call zx48_memory_init
    call zx48_process_init
    call zx48_handles_init
    call zx48_ula_init
    call zx48_console_init
    call zx48_keyboard_init
    call zx48_udg_init
    jr nc,zx48_boot_udg_ok
    ld a,PANIC_ALLOCATOR
    jp zx48_panic
zx48_boot_udg_ok:
    call zx48_im2_init
    jp zx48_idle_loop
    ENDM
