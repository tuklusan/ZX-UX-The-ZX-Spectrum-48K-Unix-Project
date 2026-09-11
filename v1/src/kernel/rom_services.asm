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
; Sole production owner of raw 48K ROM routine addresses.

ROM_PRINT_A               EQU $0010
ROM_FP_CALC               EQU $0028
ROM_KEY_SCAN              EQU $028E
ROM_KEYBOARD              EQU $02BF
ROM_K_TEST                EQU $031E
ROM_KEY_DECODE            EQU $0333
ROM_BEEPER                EQU $03B5
ROM_BEEP_COMMAND          EQU $03F8
ROM_SA_BYTES              EQU $04C2
ROM_LD_BYTES              EQU $0556
ROM_PIXEL_ADD             EQU $22AA
ROM_POINT                 EQU $22CB
ROM_PLOT_SUB              EQU $22E5
ROM_DRAW_LINE             EQU $24BA
ROM_FP_TO_BC              EQU $2DA2
ROM_FP_PRINT              EQU $2DE3
ROM_CALCULATE             EQU $335B
ROM_INT                   EQU $36AF
ROM_EXP                   EQU $36C4
ROM_LN                    EQU $3713
ROM_COS                   EQU $37AA
ROM_SIN                   EQU $37B5
ROM_TAN                   EQU $37DA
ROM_ATN                   EQU $37E2
ROM_ASN                   EQU $3833
ROM_ACS                   EQU $3843
ROM_SQR                   EQU $384A
ROM_POWER                 EQU $3851

    MACRO EMIT_ROM_SERVICE_ROUTINES
; Every raw ROM return samples/checks the dedicated kernel stack while preserving
; the ROM routine's complete AF/BC/DE/HL result contract, then canonicalizes IY.
zx48_rom_restore_iy:
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_checked_return:
    push af
    push bc
    push de
    push hl
    call zx48_kernel_stack_sample
    call zx48_kernel_stack_check
    pop hl
    pop de
    pop bc
    pop af
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_print_a:
    call ROM_PRINT_A
    jp zx48_rom_checked_return
zx48_rom_key_scan:
    call ROM_KEY_SCAN
    jp zx48_rom_checked_return
zx48_rom_k_test:
    call ROM_K_TEST
    jp zx48_rom_checked_return
zx48_rom_key_decode:
    call ROM_KEY_DECODE
    jp zx48_rom_checked_return
zx48_rom_pixel_add:
    call ROM_PIXEL_ADD
    jp zx48_rom_checked_return
zx48_rom_point:
    call ROM_POINT
    jp zx48_rom_checked_return
zx48_rom_plot_sub:
    call ROM_PLOT_SUB
    jp zx48_rom_checked_return
zx48_rom_draw_line:
    call ROM_DRAW_LINE
    jp zx48_rom_checked_return
zx48_rom_beeper:
    call ROM_BEEPER
    jp zx48_rom_checked_return
zx48_rom_sa_bytes:
    call ROM_SA_BYTES
    jp zx48_rom_checked_return
zx48_rom_ld_bytes:
    call ROM_LD_BYTES
    jp zx48_rom_checked_return
    ENDM
