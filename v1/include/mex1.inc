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
; MEX1 version-1 packed header offsets and flag values.

MEX_MAGIC0              EQU 'M'
MEX_MAGIC1              EQU 'E'
MEX_MAGIC2              EQU 'X'
MEX_MAGIC3              EQU '1'
MEX_VERSION             EQU 1
MEX_FLAGS               EQU 0
MEX_HDR_MAGIC           EQU 0
MEX_HDR_VERSION         EQU 4
MEX_HDR_FLAGS           EQU 5
MEX_HDR_SIZE            EQU 6
MEX_HDR_IMAGE_SIZE      EQU 8
MEX_HDR_BSS_SIZE        EQU 10
MEX_HDR_ENTRY           EQU 12
MEX_HDR_STACK           EQU 14
MEX_HDR_RELOC_COUNT     EQU 16
MEX_HDR_RELOC_OFFSET    EQU 18
MEX_HDR_BODY_CRC        EQU 20
MEX_HDR_HEADER_CRC      EQU 22
MEX_DEFAULT_STACK       EQU 512
MEX_MIN_STACK           EQU 64
MEX_MAX_STACK           EQU 4096
