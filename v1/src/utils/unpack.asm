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
; /bin/unpack: atomically materialize one packed RAM object as exact RAW bytes.

    MACRO EMIT_P807_UNPACK_ROUTINES
unpack_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 2
    jr nz,unpack_invalid
    ld de,8
    add ix,de
unpack_skip_argv0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,unpack_skip_argv0
    push ix
    pop hl
    ld a,SYS_UNPACK
    call SYSCALL_GATEWAY
    jr c,unpack_error
    ld l,0
    jr unpack_exit
unpack_invalid:
    ld a,E_INVAL
unpack_error:
    ld l,a
unpack_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
unpack_end:
    ENDM
