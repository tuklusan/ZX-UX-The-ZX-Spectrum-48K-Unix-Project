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

; P8.30 exact qualification source.
    MACRO EMIT_P830_WHOAMI_ROUTINES
whoami_entry:
    ld (whoami_env),de
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jp nz,whoami_bad
    ld hl,(whoami_env)
    ld a,(hl)
    cp 'E'
    jp nz,whoami_format
    inc hl
    ld a,(hl)
    cp 'N'
    jp nz,whoami_format
    inc hl
    ld a,(hl)
    cp 'V'
    jp nz,whoami_format
    inc hl
    ld a,(hl)
    cp '1'
    jp nz,whoami_format
    inc hl
    ld a,(hl)
    ld (whoami_left),a
    inc hl
    ld a,(hl)
    or a
    jp nz,whoami_format
    ld hl,(whoami_env)
    ld de,8
    add hl,de
whoami_next:
    ld a,(whoami_left)
    or a
    jp z,whoami_missing
    ld de,whoami_user_key
    push hl
    ld b,5
whoami_cmp:
    ld a,(de)
    cp (hl)
    jr nz,whoami_miss
    inc de
    inc hl
    djnz whoami_cmp
    pop de
    push hl
    ld bc,0
whoami_count:
    ld a,(hl)
    or a
    jr z,whoami_found
    inc hl
    inc bc
    jr whoami_count
whoami_found:
    pop hl
    call whoami_write_all
    jp c,whoami_exit_a
    ld hl,whoami_lf
    ld bc,1
    call whoami_write_all
    jp c,whoami_exit_a
    xor a
    jp whoami_exit_a
whoami_miss:
    pop hl
whoami_skip:
    ld a,(hl)
    inc hl
    or a
    jr nz,whoami_skip
    ld a,(whoami_left)
    dec a
    ld (whoami_left),a
    jr whoami_next
whoami_missing:
    ld a,E_NOENT
    jr whoami_exit_a
whoami_bad:
    ld a,E_INVAL
    jr whoami_exit_a
whoami_format:
    ld a,E_FORMAT
whoami_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

whoami_write_all:
    ld (whoami_wptr),hl
    ld (whoami_wleft),bc
whoami_write_loop:
    ld hl,(whoami_wptr)
    ld bc,(whoami_wleft)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,whoami_io
    ld (whoami_wrote),hl
    ld de,(whoami_wptr)
    add hl,de
    ld (whoami_wptr),hl
    ld hl,(whoami_wleft)
    ld de,(whoami_wrote)
    or a
    sbc hl,de
    jr c,whoami_io
    ld (whoami_wleft),hl
    ld a,h
    or l
    jr nz,whoami_write_loop
    xor a
    ret
whoami_io:
    ld a,E_IO
    scf
    ret

whoami_user_key: db 'U','S','E','R','='
whoami_env: dw 0
whoami_left: db 0
whoami_wptr: dw 0
whoami_wleft: dw 0
whoami_wrote: dw 0
whoami_lf: db 10
    ENDM
