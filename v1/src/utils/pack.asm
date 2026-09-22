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
; /bin/pack: atomically request ZXP1 packing and report logical -> physical.

    MACRO EMIT_P806_PACK_ROUTINES
pack_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 2
    jp nz,pack_invalid
    ld de,8
    add ix,de
pack_skip_argv0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,pack_skip_argv0
    push ix
    pop hl
    ld (pack_path),hl
    ld a,SYS_PACK
    call SYSCALL_GATEWAY
    jp c,pack_error

    ld hl,(pack_path)
    ld (pack_stat_req),hl
    ld hl,pack_stat_out
    ld (pack_stat_req+2),hl
    ld hl,pack_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    jp c,pack_error
    ld a,(pack_stat_out+1)
    and OBJ_PACKED
    jr z,pack_success

    ld hl,(pack_stat_out+2)
    call pack_write_u16
    ld hl,pack_arrow
    ld bc,4
    call pack_write
    jp c,pack_error
    ld hl,(pack_stat_out+4)
    call pack_write_u16
    ld hl,pack_lf
    ld bc,1
    call pack_write
    jp c,pack_error

pack_success:
    ld l,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
pack_invalid:
    ld a,E_INVAL
pack_error:
    ld l,a
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

pack_write:
    ld (pack_write_ptr),hl
    ld (pack_write_left),bc
pack_write_loop:
    ld hl,(pack_write_ptr)
    ld bc,(pack_write_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,pack_write_zero
    ld (pack_written),hl
    ld de,(pack_write_ptr)
    add hl,de
    ld (pack_write_ptr),hl
    ld hl,(pack_write_left)
    ld de,(pack_written)
    or a
    sbc hl,de
    jr c,pack_write_zero
    ld (pack_write_left),hl
    ld a,h
    or l
    jr nz,pack_write_loop
    xor a
    ret
pack_write_zero:
    ld a,E_IO
    scf
    ret

pack_write_u16:
    push ix
    ld ix,pack_num
    ld b,0
    xor a
    ld (pack_started),a
    ld de,10000
    call pack_dec_place
    ld de,1000
    call pack_dec_place
    ld de,100
    call pack_dec_place
    ld de,10
    call pack_dec_place
    ld a,l
    add a,'0'
    ld (ix+0),a
    inc b
    ld hl,pack_num
    ld c,b
    ld b,0
    call pack_write
    pop ix
    ret

pack_dec_place:
    ld c,0
pack_dec_loop:
    or a
    sbc hl,de
    jr c,pack_dec_done
    inc c
    jr pack_dec_loop
pack_dec_done:
    add hl,de
    ld a,(pack_started)
    or c
    ret z
    ld a,1
    ld (pack_started),a
    ld a,c
    add a,'0'
    ld (ix+0),a
    inc ix
    inc b
    ret

pack_path: dw 0
pack_stat_req: defs 4,0
pack_stat_out: defs 10,0
pack_started: db 0
pack_write_ptr: dw 0
pack_write_left: dw 0
pack_written: dw 0
pack_num: defs 5,0
pack_arrow: db ' ','-','>',' '
pack_lf: db 10
pack_end:
    ENDM
