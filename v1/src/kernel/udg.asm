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
    ; Consume the already-initialized live bank; P7.15 never reallocates/repoints it.
    ; Validate all three record bytes before cursor/screen/attribute mutation.
    ld c,(hl)
    ld a,c
    cp UDG_SLOT_COUNT
    jp nc,zx48_udg_bad
    inc hl
    ld b,(hl)
    ld a,b
    cp 24
    jp nc,zx48_udg_bad
    inc hl
    ld a,(hl)
    cp 32
    jp nc,zx48_udg_bad

    ; Preserve validated col and row/slot across cursor hiding, then draw the
    ; one physical byte-wide cell. DE walks the eight-byte glyph.
    push af
    push bc
    call zx48_udg_slot_ptr
    ex de,hl
    push de
    call zx48_cursor_hide
    pop de
    pop bc
    pop af
    ld c,a
    ld a,b
    add a,a
    add a,a
    add a,a
    ld b,a
zx48_udg_draw_loop:
    call zx48_bitmap_address
    ld a,(de)
    ld (hl),a
    inc de
    inc b
    ld a,b
    and 7
    jr nz,zx48_udg_draw_loop

    ; B is now one scanline past the cell. Rewind to its first scanline and
    ; derive the Spectrum attribute address directly from y and byte column.
    ld a,b
    sub 8
    ld b,a
    and $c0
    rlca
    rlca
    add a,$58
    ld h,a
    ld a,b
    and $38
    rlca
    rlca
    or c
    ld l,a
    ld a,(tty_current_attr)
    ld (hl),a
    call zx48_cursor_show
    xor a
    ret
zx48_udg_bad:
    ld a,E_INVAL
    scf
    ret

; Zero-initialized UDG pointer scratch is fixed emergency-reserve state.
UDG_STATE_BASE            EQU EMERGENCY_START+$62
udg_bank_ptr              EQU UDG_STATE_BASE+0
udg_io_ptr                EQU UDG_STATE_BASE+2
UDG_STATE_END             EQU UDG_STATE_BASE+4
    ASSERT UDG_STATE_END <= EMERGENCY_START+$7F
    ENDM


; REV02 production compaction. Public UDG calls validate slot/range/row/column
; before entering these core routines; historical direct-core fixtures retain
; EMIT_UDG_ROUTINES above unchanged.
    MACRO EMIT_REV02_UDG_ROUTINES
zx48_udg_init:
    ld bc,UDG_BANK_SIZE
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (udg_bank_ptr),hl
    ld (ROM_UDG),hl
    ld d,h
    ld e,l
    ld b,0
    xor a
zx48_r2_udg_zero_loop:
    ld (de),a
    inc de
    djnz zx48_r2_udg_zero_loop
    ld bc,UDG_BANK_SIZE
    call zx48_memory_pin_bytes
    xor a
    ret

; C=validated slot -> HL glyph.
zx48_udg_slot_ptr:
    ld a,c
    add a,a
    add a,a
    add a,a
    ld e,a
    ld d,0
    ld hl,(udg_bank_ptr)
    add hl,de
    xor a
    ret

; Public syscall layer has already validated B=0, slot, and the eight-byte range.
zx48_udg_define:
    ld (udg_io_ptr),hl
    call zx48_udg_slot_ptr
    ex de,hl
    ld hl,(udg_io_ptr)
    ld bc,UDG_SLOT_BYTES
    jp zx48_memcpy

zx48_udg_get:
    ld (udg_io_ptr),hl
    call zx48_udg_slot_ptr
    ld de,(udg_io_ptr)
    ld bc,UDG_SLOT_BYTES
    jp zx48_memcpy

; Public syscall layer has already validated H=0 and slot.
zx48_udg_clear:
    ld c,l
    call zx48_udg_slot_ptr
    ld b,UDG_SLOT_BYTES
    xor a
zx48_r2_udg_clear_loop:
    ld (hl),a
    inc hl
    djnz zx48_r2_udg_clear_loop
    ret

; HL -> validated {slot,row,column}. Only the public validated syscall reaches
; this production core.
zx48_udg_draw:
    ld c,(hl)
    inc hl
    ld b,(hl)
    inc hl
    ld a,(hl)

    push af
    push bc
    call zx48_udg_slot_ptr
    ex de,hl
    push de
    call zx48_cursor_hide
    pop de
    pop bc
    pop af
    ld c,a
    ld a,b
    add a,a
    add a,a
    add a,a
    ld b,a
zx48_r2_udg_draw_loop:
    call zx48_bitmap_address
    ld a,(de)
    ld (hl),a
    inc de
    inc b
    ld a,b
    and 7
    jr nz,zx48_r2_udg_draw_loop

    ld a,b
    sub 8
    ld b,a
    and $c0
    rlca
    rlca
    add a,$58
    ld h,a
    ld a,b
    and $38
    rlca
    rlca
    or c
    ld l,a
    ld a,(tty_current_attr)
    ld (hl),a
    jp zx48_cursor_show

UDG_STATE_BASE            EQU EMERGENCY_START+$62
udg_bank_ptr              EQU UDG_STATE_BASE+0
udg_io_ptr                EQU UDG_STATE_BASE+2
UDG_STATE_END             EQU UDG_STATE_BASE+4
    ASSERT UDG_STATE_END <= EMERGENCY_START+$7F
    ENDM
