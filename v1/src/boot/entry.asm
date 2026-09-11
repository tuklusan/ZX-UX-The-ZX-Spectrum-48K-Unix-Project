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
; Permanent Sinclair BASIC -> ZX-UX handoff.

    MACRO EMIT_BOOT_GATEWAY
boot_gateway:
    jp zx48_boot_main
    ENDM

    MACRO EMIT_BOOT_BODY
; Inputs: machine state handed off by Sinclair BASIC USR.
; Outputs: never returns through the BASIC USR frame.
; Flags: interrupts disabled until IM2 installation is complete.
; Clobbers: AF/BC/DE/HL/IY/SP plus OS-private alternate bank during init.
zx48_boot_main:
    jp zx48_boot_main_impl
    ENDM

    MACRO EMIT_BOOT_IMPL
zx48_boot_main_impl:
    di
    ld sp,BOOT_STACK_TOP
    ld iy,ROM_IY_ANCHOR
    call zx48_im2_init
    ei
zx48_boot_idle:
    halt
    jr zx48_boot_idle
    ENDM
