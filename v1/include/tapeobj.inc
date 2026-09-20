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
; M48O version-1 header and transport constants.

M48O_MAGIC_0             EQU $4D
M48O_MAGIC_1             EQU $34
M48O_MAGIC_2             EQU $38
M48O_MAGIC_3             EQU $4F
M48O_VERSION             EQU $01

M48O_PACKED              EQU $01
M48O_FLAGS_KNOWN         EQU $01
M48O_CODEC_RAW           EQU $0000
M48O_CODEC_ZXP1          EQU $0001

M48O_HDR_MAGIC           EQU $00
M48O_HDR_VERSION         EQU $04
M48O_HDR_TYPE            EQU $05
M48O_HDR_FLAGS           EQU $06
M48O_HDR_DIRECTORY       EQU $07
M48O_HDR_STORAGE_LEN     EQU $08
M48O_HDR_LOGICAL_LEN     EQU $0A
M48O_HDR_CODEC           EQU $0C
M48O_HDR_PAYLOAD_CRC     EQU $0E
M48O_HDR_NAME            EQU $10
M48O_HDR_HEADER_CRC      EQU $1A
M48O_HDR_RESERVED        EQU $1C
M48O_HDR_SIZE            EQU $20
M48O_NAME_SIZE           EQU $0A
M48O_RESERVED_SIZE       EQU $04
M48O_MAX_PAYLOAD         EQU $8000
M48O_MAX_LOGICAL         EQU $8000
M48O_ROM_DATA_FLAG       EQU $FF

M48O_TYPE_TXT            EQU $01
M48O_TYPE_BIN            EQU $02
M48O_TYPE_OBJ            EQU $03
M48O_TYPE_ASM            EQU $04
M48O_TYPE_C              EQU $05
M48O_TYPE_DAT            EQU $06
M48O_TYPE_UDG            EQU $07
M48O_TYPE_GFX            EQU $08
M48O_TYPE_FNT            EQU $09
M48O_TYPE_CFG            EQU $0A
M48O_TYPE_SYS            EQU $0B
M48O_TYPE_DIR_INVALID    EQU $0C
M48O_TYPE_DEV_INVALID    EQU $0D

M48O_TARGET_ROOT         EQU $00
M48O_TARGET_BIN          EQU $01
M48O_TARGET_DEV          EQU $02
M48O_TARGET_ETC          EQU $03
M48O_TARGET_HOME         EQU $04
M48O_TARGET_USERHOME     EQU $05
M48O_TARGET_TMP          EQU $06
M48O_TARGET_SYSTEM       EQU $07
