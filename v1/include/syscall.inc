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
; Userland syscall helper. Canonical SYS_* numbers live only in zx48ux.inc.
; P1.09 freezes ABI-visible packed syscall records here so kernel and userland
; consume one shared definition rather than retyping offsets.

FPOP_INVALID             EQU $00
FPOP_ADD                 EQU $01
FPOP_SUB                 EQU $02
FPOP_MUL                 EQU $03
FPOP_DIV                 EQU $04
FPOP_POW                 EQU $05
FPOP_ABS                 EQU $06
FPOP_SGN                 EQU $07
FPOP_INT                 EQU $08
FPOP_EXP                 EQU $09
FPOP_LN                  EQU $0A
FPOP_SIN                 EQU $0B
FPOP_COS                 EQU $0C
FPOP_TAN                 EQU $0D
FPOP_ASN                 EQU $0E
FPOP_ACS                 EQU $0F
FPOP_ATN                 EQU $10
FPOP_SQR                 EQU $11

FPOP1_OP_O               EQU $00
FPOP1_RESERVED_O         EQU $01
FPOP1_LHS_O              EQU $02
FPOP1_RHS_O              EQU $04
FPOP1_OUT_O              EQU $06
FPOP1_SIZE               EQU $08

ROMCAT_ALL               EQU $00
ROMCAT_KEYBOARD          EQU $01
ROMCAT_CONSOLE           EQU $02
ROMCAT_TAPE              EQU $03
ROMCAT_GRAPHICS          EQU $04
ROMCAT_SOUND             EQU $05
ROMCAT_MATH              EQU $06

ROM_CLASS_A              EQU $01
ROM_CLASS_B              EQU $02
ROM_CLASS_C              EQU $03

ROMCF_MAY_ERROR_RESTART  EQU $0001
ROMCF_ALTREG_SENSITIVE   EQU $0002
ROMCF_DISABLES_INTERRUPTS EQU $0004
ROMCF_NONREENTRANT       EQU $0008

ROMQ1_INDEX_O            EQU $00
ROMQ1_CATEGORY_O         EQU $01
ROMQ1_OUT_PTR_O          EQU $02
ROMQ1_SIZE               EQU $04

ROMOUT1_NAME_O           EQU $00
ROMOUT1_ADDRESS_O        EQU $10
ROMOUT1_CLASSIFICATION_O EQU $12
ROMOUT1_CATEGORY_O       EQU $13
ROMOUT1_CONTRACT_FLAGS_O EQU $14
ROMOUT1_RESERVED_O       EQU $16
ROMOUT1_SIZE             EQU $18

    MACRO ZX_SYSCALL number
    ld a,number
    call SYSCALL_GATEWAY
    ENDM

    MACRO ZX_RETURN_IF_ERROR
    ret c
    ENDM
