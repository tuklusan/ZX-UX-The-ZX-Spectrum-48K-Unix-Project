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
; /bin/true: emit no bytes and return exact process status 0.
; Arguments are intentionally ignored; the utility has no failure path.

    MACRO EMIT_P813_TRUE_ROUTINES
true_entry:
    ld l,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
true_end:
    ENDM
