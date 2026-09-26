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
; P11.27 target-only zxpack accounting adapter. The five public cassette/time
; names remain the complete public C48 surface owned by this step.

    MACRO EMIT_P1127_C48_ZXPACK_RUNTIME
; Internal adapter: HL -> exact 20-byte ZPINFO1. Kept private because REV17
; does not list a public C48 zxpack-info symbol in the Section-25.8 library.
c48_zxpack_info:
    ld a,SYS_ZXPACK_INFO
    call SYSCALL_GATEWAY
    jp c,c48_zxpack_errno
    ld hl,0
    xor a
    ret
c48_zxpack_errno:
    ld l,a
    ld h,0
    or a
    ret
    ENDM
