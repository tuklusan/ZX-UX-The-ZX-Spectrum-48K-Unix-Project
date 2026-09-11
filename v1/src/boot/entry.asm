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
; Permanent Sinclair BASIC to ZX-UX handoff.

    MACRO EMIT_BOOT_GATEWAY
boot_gateway:
    jp zx48_boot_main
    ENDM

    MACRO EMIT_BOOT_BODY
zx48_boot_main:
    jp zx48_boot_main_impl
    ENDM

    MACRO EMIT_BOOT_IMPL
; in: entered only from E003 after the native loader has placed the kernel.
; out: never returns to BASIC.
; flags: interrupts become enabled only after IM2 is completely installed.
; clobber: all primary registers; IY is established at the ROM anchor.
zx48_boot_main_impl:
    di
    ld sp,BOOT_STACK_TOP
    ld iy,ROM_IY_ANCHOR
    xor a
    ld (kernel_current_pid),a
    ld (altreg_busy),a
    ld hl,0
    ld (kernel_ticks),hl
    ld (kernel_ticks+2),hl
    call zx48_im2_init
    ei
zx48_boot_idle:
    halt
    jr zx48_boot_idle
    ENDM
