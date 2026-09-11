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
; Resident ZXP1 decoder and conservative bounded packer. Decoder implements the
; frozen LITERAL/RLE/BACKREF grammar and overlap semantics exactly.

    MACRO EMIT_ZXPACK_ROUTINES
; HL=physical stream, BC=physical bytes, DE=output, stack word logical bytes is
; supplied through zx_logical by callers. Carry set E_FORMAT on malformed input.
zx48_zxpack_decode:
    ld (zx_in),hl
    ld (zx_phys),bc
    ld (zx_out_base),de
    ld (zx_out),de
zx48_zxpack_next:
    ld hl,(zx_logical)
    ld a,h
    or l
    jr z,zx48_zxpack_finish
    ld bc,(zx_phys)
    ld a,b
    or c
    jp z,zx48_zxpack_format
    ld hl,(zx_in)
    ld a,(hl)
    inc hl
    ld (zx_in),hl
    dec bc
    ld (zx_phys),bc
    cp $40
    jr c,zx48_zxpack_literal
    cp $80
    jr c,zx48_zxpack_rle
    jr zx48_zxpack_backref

zx48_zxpack_literal:
    inc a
    ld e,a
    ld d,0
    call zx48_zxpack_check_output
    ret c
    ld bc,(zx_phys)
    ld h,b
    ld l,c
    or a
    sbc hl,de
    jp c,zx48_zxpack_format
    ld (zx_phys),hl
    ld hl,(zx_in)
    ld bc,0
    ld c,e
    push de
    ld de,(zx_out)
    ldir
    ld (zx_out),de
    ld (zx_in),hl
    pop de
    call zx48_zxpack_consume_output
    jr zx48_zxpack_next

zx48_zxpack_rle:
    and $3f
    add a,3
    ld e,a
    ld d,0
    call zx48_zxpack_check_output
    ret c
    ld bc,(zx_phys)
    ld a,b
    or c
    jp z,zx48_zxpack_format
    dec bc
    ld (zx_phys),bc
    ld hl,(zx_in)
    ld a,(hl)
    inc hl
    ld (zx_in),hl
    ld hl,(zx_out)
    ld b,e
zx48_zxpack_rle_loop:
    ld (hl),a
    inc hl
    djnz zx48_zxpack_rle_loop
    ld (zx_out),hl
    call zx48_zxpack_consume_output
    jr zx48_zxpack_next

zx48_zxpack_backref:
    and $7f
    add a,3
    ld e,a
    ld d,0
    call zx48_zxpack_check_output
    ret c
    ld bc,(zx_phys)
    ld a,b
    or c
    jp z,zx48_zxpack_format
    dec bc
    ld (zx_phys),bc
    ld hl,(zx_in)
    ld a,(hl)
    inc hl
    ld (zx_in),hl
    inc a
    ld c,a
    ld b,0
    ld hl,(zx_out)
    push hl
    or a
    sbc hl,bc
    ld de,(zx_out_base)
    push hl
    or a
    sbc hl,de
    pop hl
    jr c,zx48_zxpack_back_bad
    pop de                         ; DE=current out
    ld b,0
    ld c,(zx_token_count)
    ; token count is reloaded below from E because E was distance-clobbered.
    ld a,(zx_saved_len)
    ld c,a
zx48_zxpack_back_loop:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    dec c
    jr nz,zx48_zxpack_back_loop
    ld (zx_out),de
    ld a,(zx_saved_len)
    ld e,a
    ld d,0
    call zx48_zxpack_consume_output
    jr zx48_zxpack_next
zx48_zxpack_back_bad:
    pop de
    jp zx48_zxpack_format

; DE=len. Save len for backref and prove len<=remaining logical.
zx48_zxpack_check_output:
    ld a,e
    ld (zx_saved_len),a
    ld (zx_token_count),a
    ld hl,(zx_logical)
    or a
    sbc hl,de
    jr c,zx48_zxpack_format_local
    xor a
    or a
    ret
zx48_zxpack_format_local:
    ld a,E_FORMAT
    scf
    ret
zx48_zxpack_consume_output:
    ld hl,(zx_logical)
    or a
    sbc hl,de
    ld (zx_logical),hl
    ret
zx48_zxpack_finish:
    ld hl,(zx_phys)
    ld a,h
    or l
    jr nz,zx48_zxpack_format
    xor a
    or a
    ret
zx48_zxpack_format:
    ld a,E_FORMAT
    scf
    ret

; IX=packed object. Allocate logical image, decode completely, commit atomically.
zx48_zxpack_materialize:
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    ret z
    ld (zx_object_ptr),ix
    ld c,(ix+OBJ_LOGICAL_LENGTH)
    ld b,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (zx_logical),bc
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (zx_new_ptr),hl
    ex de,hl
    ld ix,(zx_object_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    call zx48_zxpack_decode
    jr c,zx48_zxpack_materialize_fail
    ld ix,(zx_object_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    push bc
    call zx48_free
    pop bc
    ld ix,(zx_object_ptr)
    ld hl,(zx_new_ptr)
    ld (ix+OBJ_ALLOCATION_PTR),l
    ld (ix+OBJ_ALLOCATION_PTR+1),h
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h
    ld a,(ix+OBJ_FLAGS_BYTE)
    and $fe
    ld (ix+OBJ_FLAGS_BYTE),a
    xor a
    or a
    ret
zx48_zxpack_materialize_fail:
    push af
    ld hl,(zx_new_ptr)
    ld bc,(zx_logical)
    call zx48_free
    pop af
    scf
    ret

; IX=object, DE=offset, HL=dst, BC=count. For compactness the first read of a
; packed object materializes atomically, then follows the ordinary RAW path.
zx48_zxpack_read:
    push hl
    push bc
    push de
    call zx48_zxpack_materialize
    pop de
    pop bc
    pop hl
    ret c
    jp zx48_object_read

; A=object slot. Conservative packer recognizes a uniform-byte object. It emits
; legal RLE chunks (3..66) only when the physical representation is smaller.
zx48_zxpack_try_slot:
    ld (zx_slot),a
    ld hl,(zx_pack_attempts)
    inc hl
    ld (zx_pack_attempts),hl
    call zx48_object_ptr_slot
    ret c
    ld (zx_object_ptr),ix
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr z,zx48_zxpack_try_raw
    ld hl,0
    xor a
    or a
    ret
zx48_zxpack_try_raw:
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld a,h
    or l
    jr z,zx48_zxpack_nosave
    ld de,3
    or a
    sbc hl,de
    jr c,zx48_zxpack_nosave
    ld ix,(zx_object_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld a,(hl)
    ld (zx_uniform_byte),a
    ld c,(ix+OBJ_LOGICAL_LENGTH)
    ld b,(ix+OBJ_LOGICAL_LENGTH+1)
    dec bc
    inc hl
zx48_zxpack_uniform_loop:
    ld a,b
    or c
    jr z,zx48_zxpack_uniform_ok
    ld a,(hl)
    ld d,a
    ld a,(zx_uniform_byte)
    cp d
    jr nz,zx48_zxpack_nosave
    inc hl
    dec bc
    jr zx48_zxpack_uniform_loop
zx48_zxpack_uniform_ok:
    ; encoded bytes = 2*ceil(length/66)
    ld ix,(zx_object_ptr)
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld de,65
    add hl,de
    ld de,0
zx48_zxpack_div66:
    ld bc,66
    or a
    sbc hl,bc
    jr c,zx48_zxpack_div_done
    inc de
    jr zx48_zxpack_div66
zx48_zxpack_div_done:
    sla e
    rl d
    ld (zx_encoded_len),de
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    or a
    sbc hl,de
    jr c,zx48_zxpack_nosave
    jr z,zx48_zxpack_nosave
    ld b,d
    ld c,e
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (zx_new_ptr),hl
    ex de,hl
    ld ix,(zx_object_ptr)
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
zx48_zxpack_emit_run:
    ld a,h
    or l
    jr z,zx48_zxpack_commit
    ld bc,66
    or a
    sbc hl,bc
    jr c,zx48_zxpack_emit_tail
    ld a,$7f                    ; RLE length 66
    ld (de),a
    inc de
    ld a,(zx_uniform_byte)
    ld (de),a
    inc de
    jr zx48_zxpack_emit_run
zx48_zxpack_emit_tail:
    add hl,bc
    ld a,l
    sub 3
    or $40
    ld (de),a
    inc de
    ld a,(zx_uniform_byte)
    ld (de),a
    inc de
zx48_zxpack_commit:
    ld ix,(zx_object_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    call zx48_free
    ld ix,(zx_object_ptr)
    ld hl,(zx_new_ptr)
    ld (ix+OBJ_ALLOCATION_PTR),l
    ld (ix+OBJ_ALLOCATION_PTR+1),h
    ld hl,(zx_encoded_len)
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h
    ld a,(ix+OBJ_FLAGS_BYTE)
    or OBJ_PACKED
    ld (ix+OBJ_FLAGS_BYTE),a
    ld hl,(zx_pack_successes)
    inc hl
    ld (zx_pack_successes),hl
    ld ix,(zx_object_ptr)
    ld hl,(ix+OBJ_LOGICAL_LENGTH)
    ld de,(zx_encoded_len)
    or a
    sbc hl,de
    xor a
    or a
    ret
zx48_zxpack_nosave:
    ld hl,0
    xor a
    or a
    ret

; HL -> exact 20-byte ZPINFO1. Bounded table scan computes current totals.
zx48_zxpack_info:
    ld (zx_info_ptr),hl
    xor a
    ld hl,zx_info_scratch
    ld de,zx_info_scratch+1
    ld bc,19
    ld (hl),a
    ldir
    ld ix,object_table
    ld b,RAM_OBJECT_COUNT
zx48_zxpack_info_loop:
    push bc
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_zxpack_info_next
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld de,(zx_info_scratch)
    add hl,de
    ld (zx_info_scratch),hl
    jr nc,zx48_zxpack_info_no_carry
    ld hl,(zx_info_scratch+2)
    inc hl
    ld (zx_info_scratch+2),hl
zx48_zxpack_info_no_carry:
    ld l,(ix+OBJ_STORAGE_LENGTH)
    ld h,(ix+OBJ_STORAGE_LENGTH+1)
    ld de,(zx_info_scratch+4)
    add hl,de
    ld (zx_info_scratch+4),hl
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr z,zx48_zxpack_info_raw
    ld hl,zx_info_scratch+10
    inc (hl)
    jr zx48_zxpack_info_next
zx48_zxpack_info_raw:
    ld hl,zx_info_scratch+11
    inc (hl)
zx48_zxpack_info_next:
    ld de,OBJ_RECORD_SIZE
    add ix,de
    pop bc
    djnz zx48_zxpack_info_loop
    ; bytes_saved u32 = logical-total minus physical u16.
    ld hl,(zx_info_scratch)
    ld de,(zx_info_scratch+4)
    or a
    sbc hl,de
    ld (zx_info_scratch+6),hl
    ld hl,(zx_info_scratch+2)
    ld de,0
    sbc hl,de
    ld (zx_info_scratch+8),hl
    ld hl,(zx_pack_attempts)
    ld (zx_info_scratch+14),hl
    ld hl,(zx_pack_successes)
    ld (zx_info_scratch+16),hl
    ld hl,zx_info_scratch
    ld de,(zx_info_ptr)
    ld bc,20
    ldir
    xor a
    or a
    ret

zx_in: dw 0
zx_phys: dw 0
zx_out_base: dw 0
zx_out: dw 0
zx_logical: dw 0
zx_saved_len: db 0
zx_token_count: db 0
zx_object_ptr: dw 0
zx_new_ptr: dw 0
zx_slot: db 0
zx_uniform_byte: db 0
zx_encoded_len: dw 0
zx_pack_attempts: dw 0
zx_pack_successes: dw 0
zx_info_ptr: dw 0
zx_info_scratch: defs 20,0
    ENDM
