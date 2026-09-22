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
; /bin/cmp: exact bytewise comparison of two RAM objects.

    MACRO EMIT_P812_CMP_ROUTINES
cmp_entry:
    push hl
    pop ix
    xor a
    ld (cmp_open_a),a
    ld (cmp_open_b),a
    ld a,(ix+4)
    cp 3
    jp nz,cmp_invalid
    ld de,8
    add ix,de
    call cmp_next_arg
    push ix
    pop hl
    ld (cmp_path_a),hl
    call cmp_next_arg
    push ix
    pop hl
    ld (cmp_path_b),hl

    ld hl,(cmp_path_a)
    call cmp_require_ram
    jp c,cmp_error
    ld hl,(cmp_path_b)
    call cmp_require_ram
    jp c,cmp_error

    ld hl,(cmp_path_a)
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,cmp_error
    ld a,l
    ld (cmp_handle_a),a
    ld a,1
    ld (cmp_open_a),a

    ld hl,(cmp_path_b)
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jr c,cmp_open_b_fail
    ld a,l
    ld (cmp_handle_b),a
    ld a,1
    ld (cmp_open_b),a

cmp_loop:
    ld a,(cmp_handle_a)
    ld e,a
    ld d,0
    ld hl,cmp_byte_a
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,cmp_stream_error
    ld (cmp_count_a),hl

    ld a,(cmp_handle_b)
    ld e,a
    ld d,0
    ld hl,cmp_byte_b
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,cmp_stream_error
    ld (cmp_count_b),hl

    ld hl,(cmp_count_a)
    ld a,h
    or l
    jr z,cmp_a_eof
    ld hl,(cmp_count_b)
    ld a,h
    or l
    jr z,cmp_different
    ld a,(cmp_byte_a)
    ld b,a
    ld a,(cmp_byte_b)
    cp b
    jr nz,cmp_different
    jr cmp_loop

cmp_a_eof:
    ld hl,(cmp_count_b)
    ld a,h
    or l
    jr nz,cmp_different
    call cmp_close_b
    jp c,cmp_error
    call cmp_close_a
    jp c,cmp_error
    ld l,0
    jr cmp_exit

cmp_different:
    call cmp_close_best
    ld l,1
    jr cmp_exit

cmp_open_b_fail:
    ld (cmp_saved_error),a
    call cmp_close_a_best
    ld a,(cmp_saved_error)
    jr cmp_error

cmp_stream_error:
    ld (cmp_saved_error),a
    call cmp_close_best
    ld a,(cmp_saved_error)
cmp_error:
    ld l,a
    jr cmp_exit
cmp_invalid:
    ld l,E_INVAL
cmp_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

cmp_require_ram:
    ld (cmp_stat_req),hl
    ld de,cmp_stat_out
    ld (cmp_stat_req+2),de
    ld hl,cmp_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    ret c
    ld a,(cmp_stat_out+7)
    cp STATE_RAM
    ret z
    ld a,E_PERM
    scf
    ret

cmp_close_b:
    ld a,(cmp_open_b)
    or a
    ret z
    xor a
    ld (cmp_open_b),a
    ld a,(cmp_handle_b)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret

cmp_close_a:
    ld a,(cmp_open_a)
    or a
    ret z
    xor a
    ld (cmp_open_a),a
    ld a,(cmp_handle_a)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret

cmp_close_best:
    call cmp_close_b_best
cmp_close_a_best:
    ld a,(cmp_open_a)
    or a
    ret z
    xor a
    ld (cmp_open_a),a
    ld a,(cmp_handle_a)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    or a
    ret
cmp_close_b_best:
    ld a,(cmp_open_b)
    or a
    ret z
    xor a
    ld (cmp_open_b),a
    ld a,(cmp_handle_b)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    or a
    ret

cmp_next_arg:
cmp_next_loop:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,cmp_next_loop
    ret

cmp_path_a: dw 0
cmp_path_b: dw 0
cmp_handle_a: db 0
cmp_handle_b: db 0
cmp_open_a: db 0
cmp_open_b: db 0
cmp_byte_a: db 0
cmp_byte_b: db 0
cmp_count_a: dw 0
cmp_count_b: dw 0
cmp_saved_error: db 0
cmp_stat_req: defs 4,0
cmp_stat_out: defs 10,0
cmp_end:
    ENDM
