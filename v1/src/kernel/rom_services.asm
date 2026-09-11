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
; Canonical 48K ROM entry table. This module is the sole owner of raw ROM
; service addresses in production source.

ROM_PRINT_A               EQU $0010
ROM_FP_CALC               EQU $0028
ROM_KEY_SCAN              EQU $028E
ROM_KEYBOARD              EQU $02BF
ROM_KEY_DECODE            EQU $0333
ROM_BEEPER                EQU $03B5
ROM_BEEP_COMMAND          EQU $03F8
ROM_SA_BYTES              EQU $04C2
ROM_LD_BYTES              EQU $0556
ROM_PIXEL_ADD             EQU $22AA
ROM_POINT                 EQU $22CB
ROM_PLOT_SUB              EQU $22E5
ROM_DRAW_CONVERT          EQU $24B7
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

    MACRO ROM_RESTORE_IY
    ld iy,ROM_IY_ANCHOR
    ENDM

    MACRO EMIT_ROM_SERVICE_ROUTINES
; Inputs: none.
; Outputs: IY restored to the immutable ROM ERR_NR anchor.
; Flags: unchanged.
; Clobbers: IY by ABI ownership.
zx48_rom_restore_iy:
    ROM_RESTORE_IY
    ret

; Inputs: A = character.
; Outputs: ROM-compatible character output complete; IY restored.
; Flags: ROM-defined.
; Clobbers: ROM PRINT-A contract plus IY restoration.
zx48_rom_print_a:
    call ROM_PRINT_A
    ROM_RESTORE_IY
    ret

; Inputs: A = keyboard row selector state required by ROM KEY-SCAN.
; Outputs: ROM KEY-SCAN result; IY restored.
; Flags: ROM-defined.
; Clobbers: ROM KEY-SCAN contract plus IY restoration.
zx48_rom_key_scan:
    call ROM_KEY_SCAN
    ROM_RESTORE_IY
    ret

; Inputs: HL/DE/B/C as documented for PIXEL-ADD/POINT family.
; Outputs: ROM PIXEL-ADD result; IY restored.
; Flags: ROM-defined.
; Clobbers: ROM PIXEL-ADD contract plus IY restoration.
zx48_rom_pixel_add:
    call ROM_PIXEL_ADD
    ROM_RESTORE_IY
    ret

; Inputs: ROM POINT contract.
; Outputs: ROM POINT result; IY restored.
; Flags: ROM-defined.
; Clobbers: ROM POINT contract plus IY restoration.
zx48_rom_point:
    call ROM_POINT
    ROM_RESTORE_IY
    ret

; Inputs: B/C coordinates already range-checked by ZX-UX.
; Outputs: plotted pixel; IY restored.
; Flags: ROM-defined.
; Clobbers: ROM PLOT-SUB contract plus IY restoration.
zx48_rom_plot_sub:
    call ROM_PLOT_SUB
    ROM_RESTORE_IY
    ret

; Inputs: register state frozen for the lower line-drawing entry.
; Outputs: line drawn; IY restored.
; Flags: ROM-defined.
; Clobbers: ROM DRAW-LINE contract plus IY restoration.
zx48_rom_draw_line:
    call ROM_DRAW_LINE
    ROM_RESTORE_IY
    ret

; Inputs: DE period, HL duration loop count per ROM BEEPER contract.
; Outputs: synchronous note complete; IY restored.
; Flags: ROM-defined.
; Clobbers: ROM BEEPER contract plus IY restoration.
zx48_rom_beeper:
    call ROM_BEEPER
    ROM_RESTORE_IY
    ret

; Inputs: A block type, DE length, IX source.
; Outputs: ROM SA-BYTES status; IY restored on returning path.
; Flags: ROM-defined carry/status.
; Clobbers: ROM SA-BYTES contract plus IY restoration.
zx48_rom_sa_bytes:
    call ROM_SA_BYTES
    ROM_RESTORE_IY
    ret

; Inputs: A block type, DE length, IX destination, carry=load/verify mode.
; Outputs: ROM LD-BYTES status; IY restored on returning path.
; Flags: ROM-defined carry/status.
; Clobbers: ROM LD-BYTES contract plus IY restoration.
zx48_rom_ld_bytes:
    call ROM_LD_BYTES
    ROM_RESTORE_IY
    ret
    ENDM
