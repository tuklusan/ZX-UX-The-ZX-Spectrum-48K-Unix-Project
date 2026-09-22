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
; /bin/mv: delegate exact atomic rename semantics to SYS_RENAME.

    MACRO EMIT_P804_MV_ROUTINES
mv_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 3
    jr nz,mv_invalid
    ld de,8
    add ix,de
    call mv_next_arg
    push ix
    pop hl
    ld (mv_ren1),hl
    call mv_next_arg
    push ix
    pop hl
    ld (mv_ren1+2),hl
    ld hl,mv_ren1
    ld a,SYS_RENAME
    call SYSCALL_GATEWAY
    jr c,mv_error
    ld l,0
    jr mv_exit
mv_invalid:
    ld a,E_INVAL
mv_error:
    ld l,a
mv_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

mv_next_arg:
mv_next_loop:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,mv_next_loop
    ret

mv_ren1: defs 4,0
mv_end:
    ENDM
