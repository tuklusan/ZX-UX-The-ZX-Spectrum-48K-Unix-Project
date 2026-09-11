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

M48O_VERSION             EQU 1
M48O_PACKED              EQU 1
M48O_CODEC_RAW           EQU 0
M48O_CODEC_ZXP1          EQU 1
M48O_HDR_MAGIC           EQU 0
M48O_HDR_VERSION         EQU 4
M48O_HDR_TYPE            EQU 5
M48O_HDR_FLAGS           EQU 6
M48O_HDR_DIRECTORY       EQU 7
M48O_HDR_STORAGE_LEN     EQU 8
M48O_HDR_LOGICAL_LEN     EQU 10
M48O_HDR_CODEC           EQU 12
M48O_HDR_PAYLOAD_CRC     EQU 14
M48O_HDR_NAME            EQU 16
M48O_HDR_HEADER_CRC      EQU 26
M48O_HDR_RESERVED        EQU 28
M48O_NAME_SIZE           EQU 10
M48O_MAX_PAYLOAD         EQU $8000
M48O_ROM_DATA_FLAG       EQU $FF
