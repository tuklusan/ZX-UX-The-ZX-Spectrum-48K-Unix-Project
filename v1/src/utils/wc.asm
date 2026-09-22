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
; /bin/wc: streaming byte, word, and LF-line counts from stdin.

    MACRO EMIT_P809_WC_ROUTINES
wc_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jp nz,wc_invalid
    xor a
    ld (wc_in_word),a
    ld hl,0
    ld (wc_bytes),hl
    ld (wc_words),hl
    ld (wc_lines),hl

wc_read_loop:
    ld de,0
    ld hl,wc_byte
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,wc_error
    ld a,h
    or l
    jr z,wc_eof

    ld hl,(wc_bytes)
    inc hl
    ld (wc_bytes),hl
    ld a,(wc_byte)
    cp 10
    jr nz,wc_not_lf
    ld hl,(wc_lines)
    inc hl
    ld (wc_lines),hl
wc_not_lf:
    ld a,(wc_byte)
    cp ' '+1
    jr c,wc_space
    ld a,(wc_in_word)
    or a
    jr nz,wc_read_loop
    ld a,1
    ld (wc_in_word),a
    ld hl,(wc_words)
    inc hl
    ld (wc_words),hl
    jr wc_read_loop
wc_space:
    xor a
    ld (wc_in_word),a
    jr wc_read_loop

wc_eof:
    ld hl,(wc_lines)
    call wc_write_u16
    jp c,wc_error
    ld hl,wc_space_byte
    ld bc,1
    call wc_write_all
    jp c,wc_error
    ld hl,(wc_words)
    call wc_write_u16
    jp c,wc_error
    ld hl,wc_space_byte
    ld bc,1
    call wc_write_all
    jp c,wc_error
    ld hl,(wc_bytes)
    call wc_write_u16
    jp c,wc_error
    ld hl,wc_lf
    ld bc,1
    call wc_write_all
    jp c,wc_error
    ld l,0
    jr wc_exit

wc_invalid:
    ld a,E_INVAL
wc_error:
    ld l,a
wc_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

wc_write_u16:
    push ix
    ld ix,wc_num
    ld b,0
    xor a
    ld (wc_num_started),a
    ld de,10000
    call wc_dec_place
    ld de,1000
    call wc_dec_place
    ld de,100
    call wc_dec_place
    ld de,10
    call wc_dec_place
    ld a,l
    add a,'0'
    ld (ix+0),a
    inc b
    ld hl,wc_num
    ld c,b
    ld b,0
    call wc_write_all
    pop ix
    ret

wc_dec_place:
    ld c,0
wc_dec_loop:
    or a
    sbc hl,de
    jr c,wc_dec_done
    inc c
    jr wc_dec_loop
wc_dec_done:
    add hl,de
    ld a,(wc_num_started)
    or c
    ret z
    ld a,1
    ld (wc_num_started),a
    ld a,c
    add a,'0'
    ld (ix+0),a
    inc ix
    inc b
    ret

wc_write_all:
    ld (wc_write_ptr),hl
    ld (wc_write_left),bc
wc_write_loop:
    ld hl,(wc_write_ptr)
    ld bc,(wc_write_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,wc_write_zero
    ld (wc_written),hl
    ld de,(wc_write_ptr)
    add hl,de
    ld (wc_write_ptr),hl
    ld hl,(wc_write_left)
    ld de,(wc_written)
    or a
    sbc hl,de
    jr c,wc_write_zero
    ld (wc_write_left),hl
    ld a,h
    or l
    jr nz,wc_write_loop
    xor a
    ret
wc_write_zero:
    ld a,E_IO
    scf
    ret

wc_byte: db 0
wc_in_word: db 0
wc_bytes: dw 0
wc_words: dw 0
wc_lines: dw 0
wc_num_started: db 0
wc_num: defs 5,0
wc_write_ptr: dw 0
wc_write_left: dw 0
wc_written: dw 0
wc_space_byte: db ' '
wc_lf: db 10
wc_end:
    ENDM
