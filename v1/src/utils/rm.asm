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
; /bin/rm: remove exactly one mutable RAM object through SYS_REMOVE.

    MACRO EMIT_P805_RM_ROUTINES
rm_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 2
    jr nz,rm_invalid
    ld de,8
    add ix,de
rm_skip_argv0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,rm_skip_argv0
    push ix
    pop hl
    ld a,SYS_REMOVE
    call SYSCALL_GATEWAY
    jr c,rm_error
    ld l,0
    jr rm_exit
rm_invalid:
    ld a,E_INVAL
rm_error:
    ld l,a
rm_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
rm_end:
    ENDM
