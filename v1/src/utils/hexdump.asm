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
; /bin/hexdump: compact deterministic 8-byte hexadecimal/ASCII streaming view.
; Input is stdin. Output uses uppercase hex and printable ASCII, '.' otherwise.

    MACRO EMIT_P818_HEXDUMP_ROUTINES
hexdump_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jp nz,hexdump_invalid
    xor a
    ld (hexdump_count),a
    ld hl,0
    ld (hexdump_offset),hl

hexdump_read:
    ld de,0
    ld hl,hexdump_byte
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,hexdump_error
    ld a,h
    or l
    jr z,hexdump_eof
    ld a,(hexdump_count)
    ld e,a
    ld d,0
    ld hl,hexdump_data
    add hl,de
    ld a,(hexdump_byte)
    ld (hl),a
    ld a,(hexdump_count)
    inc a
    ld (hexdump_count),a
    cp 8
    jr nz,hexdump_read
    call hexdump_emit_line
    jp c,hexdump_error
    xor a
    ld (hexdump_count),a
    ld hl,(hexdump_offset)
    ld de,8
    add hl,de
    ld (hexdump_offset),hl
    jr hexdump_read

hexdump_eof:
    ld a,(hexdump_count)
    or a
    jr z,hexdump_ok
    call hexdump_emit_line
    jp c,hexdump_error
hexdump_ok:
    ld l,0
    jr hexdump_exit

hexdump_invalid:
    ld a,E_INVAL
hexdump_error:
    ld l,a
hexdump_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

hexdump_emit_line:
    ld hl,hexdump_line
    ld (hexdump_outptr),hl
    ld hl,(hexdump_offset)
    ld a,h
    call hexdump_hex_byte
    ld a,l
    call hexdump_hex_byte
    ld a,' '
    call hexdump_put
    ld a,' '
    call hexdump_put
    xor a
    ld (hexdump_index),a

hexdump_hex_loop:
    ld a,(hexdump_index)
    ld c,a
    ld a,(hexdump_count)
    cp c
    jr z,hexdump_hex_pad
    jr c,hexdump_hex_pad
    ld e,c
    ld d,0
    ld hl,hexdump_data
    add hl,de
    ld a,(hl)
    call hexdump_hex_byte
    ld a,' '
    call hexdump_put
    jr hexdump_hex_next
hexdump_hex_pad:
    ld a,' '
    call hexdump_put
    call hexdump_put
    call hexdump_put
hexdump_hex_next:
    ld a,(hexdump_index)
    inc a
    ld (hexdump_index),a
    cp 8
    jr nz,hexdump_hex_loop

    ld a,' '
    call hexdump_put
    xor a
    ld (hexdump_index),a
hexdump_ascii_loop:
    ld a,(hexdump_index)
    ld c,a
    ld a,(hexdump_count)
    cp c
    jr z,hexdump_ascii_done
    ld e,c
    ld d,0
    ld hl,hexdump_data
    add hl,de
    ld a,(hl)
    cp $20
    jr c,hexdump_ascii_dot
    cp $7f
    jr nc,hexdump_ascii_dot
    jr hexdump_ascii_put
hexdump_ascii_dot:
    ld a,'.'
hexdump_ascii_put:
    call hexdump_put
    ld a,(hexdump_index)
    inc a
    ld (hexdump_index),a
    jr hexdump_ascii_loop
hexdump_ascii_done:
    ld a,10
    call hexdump_put

    ld hl,(hexdump_outptr)
    ld de,hexdump_line
    or a
    sbc hl,de
    ld b,h
    ld c,l
    ld hl,hexdump_line
    jp hexdump_write_all

hexdump_hex_byte:
    push af
    rrca
    rrca
    rrca
    rrca
    and $0f
    call hexdump_hex_digit
    call hexdump_put
    pop af
    and $0f
    call hexdump_hex_digit
    jp hexdump_put
hexdump_hex_digit:
    cp 10
    jr c,hexdump_hex_num
    add a,'A'-10
    ret
hexdump_hex_num:
    add a,'0'
    ret
hexdump_put:
    push hl
    ld hl,(hexdump_outptr)
    ld (hl),a
    inc hl
    ld (hexdump_outptr),hl
    pop hl
    ret

hexdump_write_all:
    ld (hexdump_write_ptr),hl
    ld (hexdump_write_left),bc
hexdump_write_loop:
    ld hl,(hexdump_write_ptr)
    ld bc,(hexdump_write_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,hexdump_write_zero
    ld (hexdump_written),hl
    ld de,(hexdump_write_ptr)
    add hl,de
    ld (hexdump_write_ptr),hl
    ld hl,(hexdump_write_left)
    ld de,(hexdump_written)
    or a
    sbc hl,de
    jr c,hexdump_write_zero
    ld (hexdump_write_left),hl
    ld a,h
    or l
    jr nz,hexdump_write_loop
    xor a
    ret
hexdump_write_zero:
    ld a,E_IO
    scf
    ret

hexdump_byte: db 0
hexdump_count: db 0
hexdump_index: db 0
hexdump_offset: dw 0
hexdump_outptr: dw 0
hexdump_write_ptr: dw 0
hexdump_write_left: dw 0
hexdump_written: dw 0
hexdump_data: defs 8,0
hexdump_line: defs 40,0
hexdump_end:
    ENDM
