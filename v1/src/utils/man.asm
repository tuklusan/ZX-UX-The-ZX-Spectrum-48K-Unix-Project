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

    MACRO EMIT_P827_MAN_ROUTINES
man_entry:
    push hl
    pop ix
    xor a
    ld (man_has_topic),a
    ld a,(ix+4)
    cp 1
    jr z,man_base
    cp 2
    jr nz,man_bad
    ld a,1
    ld (man_has_topic),a
    ld de,8
    add ix,de
man_skip0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,man_skip0
    push ix
    pop hl
    ld (man_topic),hl
man_base:
    ld hl,man_line1
    call man_write_z
    jr c,man_exit_a
    ld hl,man_line2
    call man_write_z
    jr c,man_exit_a
    ld a,(man_has_topic)
    or a
    jr z,man_ok
    ld hl,man_line3
    call man_write_z
    jr c,man_exit_a
    ld hl,(man_topic)
    call man_write_z
    jr c,man_exit_a
    ld hl,man_lf
    ld bc,1
    call man_write_all
    jr c,man_exit_a
man_ok:
    xor a
    jr man_exit_a
man_bad:
    ld a,E_INVAL
man_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

man_write_z:
    push hl
    ld bc,0
man_count:
    ld a,(hl)
    or a
    jr z,man_count_done
    inc hl
    inc bc
    jr man_count
man_count_done:
    pop hl
man_write_all:
    ld (man_ptr),hl
    ld (man_left),bc
man_write_loop:
    ld hl,(man_ptr)
    ld bc,(man_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,man_io
    ld (man_wrote),hl
    ld de,(man_ptr)
    add hl,de
    ld (man_ptr),hl
    ld hl,(man_left)
    ld de,(man_wrote)
    or a
    sbc hl,de
    jr c,man_io
    ld (man_left),hl
    ld a,h
    or l
    jr nz,man_write_loop
    xor a
    ret
man_io:
    ld a,E_IO
    scf
    ret

man_line1: db 'M','a','n','u','a','l','s',':',' ','h','t','t','p','s',':','/','/','s','u','p','r','a','t','i','m','-','s','a','n','y','a','l','.','b','l','o','g','s','p','o','t','.','c','o','m','/',10,0
man_line2: db 'S','e','a','r','c','h',' ','f','o','r',' ','Z','X','U','S',10,0
man_line3: db 'T','o','p','i','c',':',' ',0
man_lf: db 10
man_has_topic: db 0
man_topic: dw 0
man_ptr: dw 0
man_left: dw 0
man_wrote: dw 0
    ENDM
