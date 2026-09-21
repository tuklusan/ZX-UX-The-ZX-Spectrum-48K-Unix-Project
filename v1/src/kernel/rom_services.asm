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
ROM_ERR_SP                EQU $5C3D
ROM_STKBOT                EQU $5C63
ROM_STKEND                EQU $5C65
ROM_MEM                   EQU $5C68
ROM_MEMBOT                EQU $5C92
ROM_BEEP_STACK            EQU $5D00

    MACRO EMIT_ROM_SERVICE_ROUTINES
; Every raw ROM return samples/checks the dedicated kernel stack while preserving
; the ROM routine's complete AF/BC/DE/HL result contract, then canonicalizes IY.
zx48_rom_checked_return:
    push af
zx48_rom_checked_return_af_saved:
    push bc
    push de
    push hl
    call zx48_kernel_stack_sample
    call zx48_kernel_stack_check
    pop hl
    pop de
    pop bc
    pop af
zx48_rom_restore_iy:
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_print_a:
    call ROM_PRINT_A
    jr zx48_rom_checked_return
zx48_rom_key_scan:
    call ROM_KEY_SCAN
    jr zx48_rom_checked_return
zx48_rom_k_test:
    call ROM_K_TEST
    jr zx48_rom_checked_return
zx48_rom_key_decode:
    call ROM_KEY_DECODE
    jr zx48_rom_checked_return
zx48_rom_pixel_add:
    call ROM_PIXEL_ADD
    jr zx48_rom_checked_return
zx48_rom_point:
    call ROM_POINT
    jr zx48_rom_checked_return
zx48_rom_plot_sub:
    call ROM_PLOT_SUB
    jr zx48_rom_checked_return
zx48_rom_draw_line:
    call ROM_DRAW_LINE
    jr zx48_rom_checked_return

; These ROM services drive ULA port 0xFE. Mirror only the kernel border bits
; into BORDCR before entry, then re-emit the authoritative shadow on return.
zx48_rom_beeper:
    call zx48_ula_rom_prepare
    call ROM_BEEPER
    jr zx48_rom_ula_done
zx48_rom_sa_bytes:
    call zx48_ula_rom_prepare
    call ROM_SA_BYTES
    jr zx48_rom_ula_done
zx48_rom_ld_bytes:
    call zx48_ula_rom_prepare
    call ROM_LD_BYTES
zx48_rom_ula_done:
    push af
    xor a
    ld (altreg_busy),a
    ld a,(ula_shadow)
    call zx48_ula_commit
    jr zx48_rom_checked_return_af_saved
    ENDM

; P7.09 staged ROM BEEP gateway. Kept out of the resident Phase-6 ROM macro
; until the Phase-7 integration/packing boundary owns the final kernel layout.
    MACRO EMIT_P709_ROM_BEEP_ROUTINES
; P7.09 isolated BASIC-compatible BEEP gateway.
; HL -> five-byte duration, DE -> five-byte pitch. The two exact values are
; copied into a private calculator stack in protected ROM-compatibility RAM.
; ERR_SP is redirected to a kernel-owned recovery item so any Sinclair report
; becomes E_INVAL rather than escaping into BASIC.
zx48_rom_beep_values:
    ld (rom_beep_duration_ptr),hl
    ld (rom_beep_pitch_ptr),de
    ld hl,(ROM_ERR_SP)
    ld (rom_beep_saved_err_sp),hl
    ld hl,(ROM_STKBOT)
    ld (rom_beep_saved_stkbot),hl
    ld hl,(ROM_STKEND)
    ld (rom_beep_saved_stkend),hl
    ld hl,(ROM_MEM)
    ld (rom_beep_saved_mem),hl
    ld hl,0
    add hl,sp
    ld (rom_beep_saved_sp),hl

    ld hl,ROM_BEEP_STACK
    ld (ROM_STKBOT),hl
    ld (ROM_STKEND),hl
    ld hl,ROM_MEMBOT
    ld (ROM_MEM),hl

    ld hl,(rom_beep_duration_ptr)
    ld de,ROM_BEEP_STACK
    ld bc,5
    ldir
    ld hl,(rom_beep_pitch_ptr)
    ld de,ROM_BEEP_STACK+5
    ld bc,5
    ldir
    ld hl,ROM_BEEP_STACK+10
    ld (ROM_STKEND),hl

    ld hl,zx48_rom_beep_error
    push hl
    ld hl,0
    add hl,sp
    ld (ROM_ERR_SP),hl
    ld iy,ROM_IY_ANCHOR
    call zx48_ula_rom_prepare
    call ROM_BEEP_COMMAND
    pop hl
    call zx48_rom_beep_cleanup
    xor a
    or a
    ret

zx48_rom_beep_error:
    ld hl,(rom_beep_saved_sp)
    ld sp,hl
    call zx48_rom_beep_cleanup
    ld a,E_INVAL
    scf
    ret

zx48_rom_beep_cleanup:
    ld hl,(rom_beep_saved_err_sp)
    ld (ROM_ERR_SP),hl
    ld hl,(rom_beep_saved_stkbot)
    ld (ROM_STKBOT),hl
    ld hl,(rom_beep_saved_stkend)
    ld (ROM_STKEND),hl
    ld hl,(rom_beep_saved_mem)
    ld (ROM_MEM),hl
    xor a
    ld (altreg_busy),a
    ld a,(ula_shadow)
    call zx48_ula_commit
    ld iy,ROM_IY_ANCHOR
    ret

rom_beep_duration_ptr: dw 0
rom_beep_pitch_ptr: dw 0
rom_beep_saved_err_sp: dw 0
rom_beep_saved_stkbot: dw 0
rom_beep_saved_stkend: dw 0
rom_beep_saved_mem: dw 0
rom_beep_saved_sp: dw 0

    ENDM
