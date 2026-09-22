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
; Allocator-owned 32-slot UDG bank. Each slot is one conventional 8x8 glyph.

UDG_SLOT_COUNT           EQU 32
UDG_SLOT_BYTES           EQU 8
UDG_CODE_FIRST           EQU $80
UDG_CODE_LAST            EQU $9F

    MACRO EMIT_UDG_ROUTINES
zx48_udg_init:
    ld bc,UDG_BANK_SIZE
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (udg_bank_ptr),hl
    push hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,UDG_BANK_SIZE-1
    ldir
    pop hl
    ld (ROM_UDG),hl
    ld bc,UDG_BANK_SIZE
    call zx48_memory_pin_bytes
    xor a
    ret

zx48_udg_slot_ptr:
    ld a,c
    cp UDG_SLOT_COUNT
    jp nc,zx48_udg_bad
    add a,a
    add a,a
    add a,a
    ld e,a
    ld d,0
    ld hl,(udg_bank_ptr)
    add hl,de
    xor a
    ret

zx48_udg_define:
    ld a,b
    or a
    jp nz,zx48_udg_bad
    ld (udg_io_ptr),hl
    call zx48_udg_slot_ptr
    ret c
    ex de,hl
    ld hl,(udg_io_ptr)
    ld bc,UDG_SLOT_BYTES
    call zx48_memcpy
    xor a
    ret

zx48_udg_get:
    ld a,b
    or a
    jp nz,zx48_udg_bad
    ld (udg_io_ptr),hl
    call zx48_udg_slot_ptr
    ret c
    ld de,(udg_io_ptr)
    ld bc,UDG_SLOT_BYTES
    call zx48_memcpy
    xor a
    ret

zx48_udg_clear:
    ld a,h
    or a
    jp nz,zx48_udg_bad
    ld c,l
    call zx48_udg_slot_ptr
    ret c
    ld b,UDG_SLOT_BYTES
    xor a
zx48_udg_clear_loop:
    ld (hl),a
    inc hl
    djnz zx48_udg_clear_loop
    or a
    ret

zx48_udg_draw:
    ld c,(hl)
    inc hl
    ld a,(hl)
    cp 24
    jp nc,zx48_udg_bad
    ld (udg_row),a
    inc hl
    ld a,(hl)
    cp 32
    jp nc,zx48_udg_bad
    ld (udg_col),a
    call zx48_udg_slot_ptr
    ret c
    ld (udg_glyph),hl
    call zx48_cursor_hide
    xor a
    ld (udg_scan),a
zx48_udg_draw_loop:
    ld a,(udg_scan)
    cp 8
    jr nc,zx48_udg_draw_done
    ld c,a
    ld a,(udg_row)
    add a,a
    add a,a
    add a,a
    add a,c
    ld b,a
    ld a,(udg_col)
    ld c,a
    call zx48_bitmap_address
    push hl
    ld hl,(udg_glyph)
    ld a,(udg_scan)
    ld e,a
    ld d,0
    add hl,de
    ld a,(hl)
    pop hl
    ld (hl),a
    ld a,(udg_scan)
    inc a
    ld (udg_scan),a
    jr zx48_udg_draw_loop
zx48_udg_draw_done:
    ; One UDG always owns exactly one physical 8x8 Spectrum cell. In tty64
    ; that byte spans logical columns 2*col and 2*col+1; the attribute cell is
    ; therefore still the same physical row/column pair.
    ld a,(udg_row)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld a,(udg_col)
    ld e,a
    ld d,0
    add hl,de
    ld de,ATTR_START
    add hl,de
    ld a,(tty_current_attr)
    ld (hl),a
    call zx48_cursor_show
    xor a
    or a
    ret
zx48_udg_bad:
    ld a,E_INVAL
    scf
    ret

udg_bank_ptr: dw 0
udg_io_ptr: dw 0
udg_glyph: dw 0
udg_row: db 0
udg_col: db 0
udg_scan: db 0
    ENDM
