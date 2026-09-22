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
; /bin/env: print the inherited canonical ENV1 table in exact stored order,
; one case-sensitive NAME=VALUE entry per LF-terminated output line.

    MACRO EMIT_P817_ENV_ROUTINES
env_entry:
    ld (env_table),de
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jp nz,env_invalid

    ld hl,(env_table)
    ld a,(hl)
    cp 'E'
    jp nz,env_format
    inc hl
    ld a,(hl)
    cp 'N'
    jp nz,env_format
    inc hl
    ld a,(hl)
    cp 'V'
    jp nz,env_format
    inc hl
    ld a,(hl)
    cp '1'
    jp nz,env_format
    inc hl
    ld a,(hl)
    ld (env_remaining),a
    inc hl
    ld a,(hl)
    or a
    jp nz,env_format
    ld hl,(env_table)
    ld de,8
    add hl,de
    ld (env_ptr),hl

env_next:
    ld a,(env_remaining)
    or a
    jr z,env_success
    ld hl,(env_ptr)
    push hl
    ld bc,0
env_count:
    ld a,(hl)
    or a
    jr z,env_count_done
    inc hl
    inc bc
    jr env_count
env_count_done:
    pop hl
    ld a,b
    or c
    jp z,env_format
    call env_write_all
    jp c,env_error
    ld hl,env_lf
    ld bc,1
    call env_write_all
    jp c,env_error
    ld hl,(env_ptr)
env_skip:
    ld a,(hl)
    inc hl
    or a
    jr nz,env_skip
    ld (env_ptr),hl
    ld a,(env_remaining)
    dec a
    ld (env_remaining),a
    jr env_next

env_success:
    ld l,0
    jr env_exit
env_invalid:
    ld a,E_INVAL
    jr env_error
env_format:
    ld a,E_FORMAT
env_error:
    ld l,a
env_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

env_write_all:
    ld (env_write_ptr),hl
    ld (env_write_left),bc
env_write_loop:
    ld hl,(env_write_ptr)
    ld bc,(env_write_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,env_write_zero
    ld (env_written),hl
    ld de,(env_write_ptr)
    add hl,de
    ld (env_write_ptr),hl
    ld hl,(env_write_left)
    ld de,(env_written)
    or a
    sbc hl,de
    jr c,env_write_zero
    ld (env_write_left),hl
    ld a,h
    or l
    jr nz,env_write_loop
    xor a
    ret
env_write_zero:
    ld a,E_IO
    scf
    ret

env_table: dw 0
env_ptr: dw 0
env_remaining: db 0
env_write_ptr: dw 0
env_write_left: dw 0
env_written: dw 0
env_lf: db 10
env_end:
    ENDM
