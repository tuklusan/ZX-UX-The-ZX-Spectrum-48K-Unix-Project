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
; P11.26 public C48 synchronous BASIC-compatible beep wrapper.
; HL=duration five-byte pointer, DE=pitch five-byte pointer.

    MACRO EMIT_P1126_C48_SOUND_RUNTIME
beep:
    ld a,SYS_BEEP
    call SYSCALL_GATEWAY
    jp c,c48_beep_errno
    ld hl,0
    xor a
    ret
c48_beep_errno:
    ld l,a
    ld h,0
    or a
    ret
    ENDM
