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
; OBJ1 version-1 object format.

OBJ1_VERSION             EQU 1
OBJ1_FLAGS               EQU 0
OBJ1_HDR_MAGIC           EQU 0
OBJ1_HDR_VERSION         EQU 4
OBJ1_HDR_FLAGS           EQU 5
OBJ1_HDR_SIZE            EQU 6
OBJ1_HDR_TEXT_SIZE       EQU 8
OBJ1_HDR_BSS_SIZE        EQU 10
OBJ1_HDR_SYMBOL_COUNT    EQU 12
OBJ1_HDR_RELOC_COUNT     EQU 14
OBJ1_HDR_SYMBOL_OFFSET   EQU 16
OBJ1_HDR_RELOC_OFFSET    EQU 18
OBJ1_HDR_BODY_CRC        EQU 20
OBJ1_HDR_HEADER_CRC      EQU 22
OBJ1_SYMBOL_SIZE         EQU 20
OBJ1_SYMBOL_NAME_SIZE    EQU 16
OBJ1_RELOC_SIZE          EQU 6
OBJ1_SEC_UNDEF           EQU 0
OBJ1_SEC_TEXT            EQU 1
OBJ1_SEC_BSS             EQU 2
OBJ1_SEC_ABS             EQU 3
OBJ1_SYM_GLOBAL          EQU 1
OBJ1_RELOC_ABS16         EQU 1
