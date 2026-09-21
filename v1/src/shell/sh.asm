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
; P6.01 shell image entry. The MEX1 container is emitted by deterministic host
; tooling; this image has no relocations and uses only the fixed syscall gateway.

    MACRO EMIT_P601_SH_IMAGE
sh_entry:
    ; The loader entry contract is HL=ARG1, BC=ARG1 length, DE=ENV1, A=0.
    ; P6.01 deliberately performs no login/output work; later Phase-6 steps
    ; extend this entry after the already-established cold-boot contract.
sh_idle:
    ld a,SYS_YIELD
    call SYSCALL_GATEWAY
    jr sh_idle
sh_image_end:
    ENDM

; P6.02 exact issue/login presentation. HL/BC supply the canonical /etc/issue
; bytes and IX points at the exact seven-byte login prompt.
P602_ISSUE_LENGTH        EQU 144
P602_LOGIN_LENGTH        EQU 7

    MACRO EMIT_P602_ISSUE_ROUTINES
sh_p602_display_issue:
    ld a,b
    or a
    jr nz,sh_p602_issue_format
    ld a,c
    cp P602_ISSUE_LENGTH
    jr nz,sh_p602_issue_format
    ld a,SYS_CON_WRITE
    call SYSCALL_GATEWAY
    ret c
    push ix
    pop hl
    ld bc,P602_LOGIN_LENGTH
    ld a,SYS_CON_WRITE
    jp SYSCALL_GATEWAY
sh_p602_issue_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM
