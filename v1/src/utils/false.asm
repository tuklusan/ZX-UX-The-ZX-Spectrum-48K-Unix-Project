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
; /bin/false: emit no bytes and return exact process status 1.
; Arguments are intentionally ignored; the status is invariant and side-effect free by construction; no I/O syscall is reachable.

    MACRO EMIT_P814_FALSE_ROUTINES
false_entry:
    ld l,1
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
false_end:
    ENDM
