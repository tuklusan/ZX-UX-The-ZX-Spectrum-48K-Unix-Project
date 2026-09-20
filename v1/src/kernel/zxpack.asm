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

;
; P4.16 bounded ZXP1 target decoder. One token parser feeds exactly four sinks.
; A=sink, HL=physical source, BC=physical length, DE=logical length,
; IX=256-byte history for streaming sinks, IY=destination for memory/stream sinks.
; p416_crc_enable!=0 requests CRC-16/CCITT-FALSE over emitted logical bytes.
;
P416_SINK_FINAL_MEMORY  EQU 0
P416_SINK_CALLER_STREAM EQU 1
P416_SINK_DISCARD       EQU 2
P416_SINK_TAPE_PIPE     EQU 3
P416_CRC_INITIAL        EQU -1

    MACRO EMIT_P416_ZXP1_DECODER
zx48_p416_decode:
    cp P416_SINK_TAPE_PIPE+1
    jp nc,zx48_p416_inval
    ld (p416_sink),a
    ld (p416_in_ptr),hl
    ld (p416_phys_left),bc
    ld (p416_logical_total),de
    xor a
    ld (p416_logical_pos),a
    ld (p416_logical_pos+1),a
    push ix
    pop hl
    ld (p416_history_ptr),hl
    push iy
    pop hl
    ld (p416_sink_base),hl
    ld (p416_sink_ptr),hl

    ; Widened physical source span: non-empty [start,start+len-1] may not wrap.
    ld bc,(p416_phys_left)
    ld a,b
    or c
    jr z,zx48_p416_input_span_ok
    dec bc
    ld hl,(p416_in_ptr)
    add hl,bc
    jp c,zx48_p416_format
zx48_p416_input_span_ok:

    ; Memory-writing sinks also prove the complete declared output span up front.
    ld a,(p416_sink)
    cp P416_SINK_DISCARD
    jr nc,zx48_p416_sink_span_ok
    ld bc,(p416_logical_total)
    ld a,b
    or c
    jr z,zx48_p416_sink_span_ok
    dec bc
    ld hl,(p416_sink_base)
    add hl,bc
    jp c,zx48_p416_inval
zx48_p416_sink_span_ok:

    ld a,(p416_sink)
    or a
    jr z,zx48_p416_history_ok
    ld hl,(p416_history_ptr)
    ld a,h
    or l
    jp z,zx48_p416_inval
zx48_p416_history_ok:

    ld a,(p416_crc_enable)
    or a
    jr z,zx48_p416_loop
    ld hl,P416_CRC_INITIAL
    ld (p416_crc),hl

zx48_p416_loop:
    ld hl,(p416_logical_pos)
    ld de,(p416_logical_total)
    or a
    sbc hl,de
    jp z,zx48_p416_finish
    ld bc,(p416_phys_left)
    ld a,b
    or c
    jp z,zx48_p416_format
    call zx48_p416_get_byte
    ret c
    cp $40
    jr c,zx48_p416_literal
    cp $80
    jr c,zx48_p416_rle

    ; BACKREF length=(token&7f)+3, then one distance_minus_1 byte.
    and $7f
    add a,3
    ld (p416_count),a
    call zx48_p416_check_advance
    ret c
    call zx48_p416_get_byte
    ret c
    ld (p416_distance_minus_1),a
    inc a
    jr nz,zx48_p416_back_distance_ready
    ld bc,256
    jr zx48_p416_back_distance_word
zx48_p416_back_distance_ready:
    ld c,a
    ld b,0
zx48_p416_back_distance_word:
    ld hl,(p416_logical_pos)
    or a
    sbc hl,bc
    jp c,zx48_p416_format
    ld (p416_back_pos),hl
zx48_p416_back_loop:
    ld hl,(p416_back_pos)
    call zx48_p416_history_read
    ret c
    call zx48_p416_emit
    ret c
    ld hl,(p416_back_pos)
    inc hl
    ld (p416_back_pos),hl
    ld hl,p416_count
    dec (hl)
    jr nz,zx48_p416_back_loop
    jr zx48_p416_loop

zx48_p416_literal:
    inc a
    ld (p416_count),a
    call zx48_p416_check_advance
    ret c
zx48_p416_literal_loop:
    call zx48_p416_get_byte
    ret c
    call zx48_p416_emit
    ret c
    ld hl,p416_count
    dec (hl)
    jr nz,zx48_p416_literal_loop
    jr zx48_p416_loop

zx48_p416_rle:
    and $3f
    add a,3
    ld (p416_count),a
    call zx48_p416_check_advance
    ret c
    call zx48_p416_get_byte
    ret c
    ld (p416_repeat),a
zx48_p416_rle_loop:
    ld a,(p416_repeat)
    call zx48_p416_emit
    ret c
    ld hl,p416_count
    dec (hl)
    jr nz,zx48_p416_rle_loop
    jp zx48_p416_loop

; A <- next physical byte, exact bounded cursor.
zx48_p416_get_byte:
    ld bc,(p416_phys_left)
    ld a,b
    or c
    jp z,zx48_p416_format
    ld hl,(p416_in_ptr)
    ld a,(hl)
    ld (p416_byte),a
    dec bc
    ld (p416_phys_left),bc
    ld a,b
    or c
    jr z,zx48_p416_get_no_advance
    inc hl
    jp z,zx48_p416_format
    ld (p416_in_ptr),hl
    jr zx48_p416_get_done
zx48_p416_get_no_advance:
    inc hl
    ld (p416_in_ptr),hl
zx48_p416_get_done:
    ld a,(p416_byte)
    or a
    ret

; count byte must fit remaining logical output using widened carry/compare checks.
zx48_p416_check_advance:
    ld a,(p416_count)
    ld e,a
    ld d,0
    ld hl,(p416_logical_pos)
    add hl,de
    jp c,zx48_p416_format
    ld bc,(p416_logical_total)
    or a
    sbc hl,bc
    jp c,zx48_p416_advance_ok
    jp z,zx48_p416_advance_ok
    jp zx48_p416_format
zx48_p416_advance_ok:
    xor a
    ret

; A=logical byte. Update optional CRC, streaming history and selected sink.
zx48_p416_emit:
    ld (p416_byte),a
    ld a,(p416_crc_enable)
    or a
    jr z,zx48_p416_emit_history
    ld a,(p416_byte)
    call zx48_p416_crc_byte

zx48_p416_emit_history:
    ld a,(p416_sink)
    or a
    jr z,zx48_p416_emit_sink
    ld hl,(p416_history_ptr)
    ld de,(p416_logical_pos)
    ld a,e
    ld e,a
    ld d,0
    add hl,de
    ld a,(p416_byte)
    ld (hl),a

zx48_p416_emit_sink:
    ld a,(p416_sink)
    cp P416_SINK_DISCARD
    jr nc,zx48_p416_emit_pos
    ld hl,(p416_sink_ptr)
    ld a,(p416_byte)
    ld (hl),a
    inc hl
    ld (p416_sink_ptr),hl

zx48_p416_emit_pos:
    ld hl,(p416_logical_pos)
    inc hl
    ld (p416_logical_pos),hl
    xor a
    ret

; HL=prior logical position -> A=byte. FINAL_MEMORY reads destination directly;
; all streaming sinks use the caller-supplied 256-byte circular history.
zx48_p416_history_read:
    ld de,(p416_logical_pos)
    push hl
    or a
    ex de,hl
    sbc hl,de
    ld a,h
    or a
    jr z,zx48_p416_history_distance_ok
    cp 1
    jp nz,zx48_p416_history_distance_bad
    ld a,l
    or a
    jp nz,zx48_p416_history_distance_bad
zx48_p416_history_distance_ok:
    pop hl
    ld a,(p416_sink)
    or a
    jr nz,zx48_p416_history_ring
    ld de,(p416_sink_base)
    add hl,de
    ld a,(hl)
    or a
    ret
zx48_p416_history_distance_bad:
    pop hl
    jp zx48_p416_format
zx48_p416_history_ring:
    ld a,l
    ld l,a
    ld h,0
    ld de,(p416_history_ptr)
    add hl,de
    ld a,(hl)
    or a
    ret

; CRC-16/CCITT-FALSE, polynomial 0x1021, initial 0xffff.
zx48_p416_crc_byte:
    ld hl,(p416_crc)
    xor h
    ld h,a
    ld b,8
zx48_p416_crc_bit:
    add hl,hl
    jr nc,zx48_p416_crc_next
    ld a,h
    xor $10
    ld h,a
    ld a,l
    xor $21
    ld l,a
zx48_p416_crc_next:
    djnz zx48_p416_crc_bit
    ld (p416_crc),hl
    ret

zx48_p416_finish:
    ld hl,(p416_phys_left)
    ld a,h
    or l
    jp nz,zx48_p416_format
    ld hl,(p416_logical_pos)
    xor a
    ret

zx48_p416_format:
    ld a,E_FORMAT
    scf
    ret
zx48_p416_inval:
    ld a,E_INVAL
    scf
    ret

p416_sink: db 0
p416_crc_enable: db 0
p416_crc: dw P416_CRC_INITIAL
p416_in_ptr: dw 0
p416_phys_left: dw 0
p416_logical_total: dw 0
p416_logical_pos: dw 0
p416_history_ptr: dw 0
p416_sink_base: dw 0
p416_sink_ptr: dw 0
p416_back_pos: dw 0
p416_count: db 0
p416_repeat: db 0
p416_distance_minus_1: db 0
p416_byte: db 0
    ENDM


;
; P4.17 per-open PACKED reader state. The allocation is exactly 256 bytes of
; circular history followed by one exact 16-byte kernel-private control record.
;
P417_HISTORY_SIZE             EQU 256
P417_CONTROL_SIZE             EQU 16
P417_STATE_SIZE               EQU 272
P417_HISTORY_O                EQU 0
P417_CONTROL_O                EQU 256
P417_CTRL_PHYSICAL_POS_O      EQU P417_CONTROL_O+0
P417_CTRL_LOGICAL_POS_O       EQU P417_CONTROL_O+2
P417_CTRL_HISTORY_INDEX_O     EQU P417_CONTROL_O+4
P417_CTRL_HISTORY_COUNT_O     EQU P417_CONTROL_O+5
P417_CTRL_PENDING_KIND_O      EQU P417_CONTROL_O+7
P417_CTRL_PENDING_COUNT_O     EQU P417_CONTROL_O+8
P417_CTRL_PARAMETER_O         EQU P417_CONTROL_O+9
P417_CTRL_RESERVED_O          EQU P417_CONTROL_O+10
P417_CTRL_RESERVED_SIZE       EQU 6

    ASSERT P417_HISTORY_SIZE+P417_CONTROL_SIZE = P417_STATE_SIZE
    ASSERT P417_CTRL_RESERVED_O+P417_CTRL_RESERVED_SIZE = P417_STATE_SIZE

    MACRO EMIT_P417_PACKED_READER_STATE_ROUTINES
; HL=272-byte state allocation. Initialize history and every control byte.
zx48_p417_state_init:
    push hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,P417_STATE_SIZE-1
    ldir
    pop hl
    xor a
    ret
    ENDM


;
; P4.18 packed seek/restart. This bounded stateful DISCARD walker operates on
; the P4.17 per-open history/control record. Backward seeks reset decoder state
; to logical zero; forward seeks continue from the current decoder position.
;
P418_PENDING_NONE             EQU 0
P418_PENDING_LITERAL          EQU 1
P418_PENDING_RLE              EQU 2
P418_PENDING_BACKREF          EQU 3
P418_CTRL_SOURCE_BASE_O       EQU P417_CTRL_RESERVED_O+0
P418_CTRL_PHYSICAL_LENGTH_O   EQU P417_CTRL_RESERVED_O+2
P418_CTRL_BIND_RESERVED_O     EQU P417_CTRL_RESERVED_O+4

P418_C_PHYSICAL_POS           EQU 0
P418_C_LOGICAL_POS            EQU 2
P418_C_HISTORY_INDEX          EQU 4
P418_C_HISTORY_COUNT          EQU 5
P418_C_PENDING_KIND           EQU 7
P418_C_PENDING_COUNT          EQU 8
P418_C_PARAMETER              EQU 9
P418_C_SOURCE_BASE            EQU 10
P418_C_PHYSICAL_LENGTH        EQU 12

    ASSERT P418_CTRL_BIND_RESERVED_O+2 = P417_STATE_SIZE
    ASSERT P418_C_PHYSICAL_LENGTH+2 <= P417_CONTROL_SIZE

    MACRO EMIT_P418_PACKED_SEEK_ROUTINES
; IY <- control record for p418_state_ptr.
zx48_p418_control_ptr:
    ld hl,(p418_state_ptr)
    ld de,P417_CONTROL_O
    add hl,de
    push hl
    pop iy
    ret

; IX=state, HL=physical source, BC=physical length. Bind immutable source span
; and reset decoder state to logical offset zero.
zx48_p418_state_bind:
    ld (p418_state_ptr),ix
    ld (p418_source_base),hl
    ld (p418_physical_length),bc
    ld a,b
    or c
    jr z,zx48_p418_bind_span_ok
    push hl
    dec bc
    add hl,bc
    pop hl
    jp c,zx48_p418_format
zx48_p418_bind_span_ok:
    call zx48_p418_reset
    ret c
    call zx48_p418_control_ptr
    ld hl,(p418_source_base)
    ld (iy+P418_C_SOURCE_BASE),l
    ld (iy+P418_C_SOURCE_BASE+1),h
    ld hl,(p418_physical_length)
    ld (iy+P418_C_PHYSICAL_LENGTH),l
    ld (iy+P418_C_PHYSICAL_LENGTH+1),h
    xor a
    ret

; IX=state, HL=target logical offset, DE=declared logical length.
; 0..logical_length inclusive are legal. Success leaves control logical pos
; exactly target and never materializes object payload.
zx48_p418_seek:
    ld (p418_state_ptr),ix
    ld (p418_target),hl
    ld (p418_logical_length),de
    or a
    sbc hl,de
    jp c,zx48_p418_target_valid
    jp nz,zx48_p418_inval
zx48_p418_target_valid:
    call zx48_p418_control_ptr
    ld l,(iy+P418_C_LOGICAL_POS)
    ld h,(iy+P418_C_LOGICAL_POS+1)
    ld de,(p418_target)
    or a
    sbc hl,de
    jr c,zx48_p418_forward
    jr z,zx48_p418_seek_finish
    ld ix,(p418_state_ptr)
    call zx48_p418_reset
    ret c

zx48_p418_forward:
zx48_p418_seek_loop:
    call zx48_p418_control_ptr
    ld l,(iy+P418_C_LOGICAL_POS)
    ld h,(iy+P418_C_LOGICAL_POS+1)
    ld de,(p418_target)
    or a
    sbc hl,de
    jr z,zx48_p418_seek_finish
    call zx48_p418_step
    ret c
    jr zx48_p418_seek_loop

zx48_p418_seek_finish:
    ld hl,(p418_target)
    ld de,(p418_logical_length)
    or a
    sbc hl,de
    jr nz,zx48_p418_seek_ok
    call zx48_p418_control_ptr
    ld a,(iy+P418_C_PENDING_COUNT)
    or a
    jp nz,zx48_p418_format
    ld l,(iy+P418_C_PHYSICAL_POS)
    ld h,(iy+P418_C_PHYSICAL_POS+1)
    ld e,(iy+P418_C_PHYSICAL_LENGTH)
    ld d,(iy+P418_C_PHYSICAL_LENGTH+1)
    or a
    sbc hl,de
    jp nz,zx48_p418_format
zx48_p418_seek_ok:
    xor a
    ret

; Reset history and mutable 10-byte control prefix; preserve source binding.
zx48_p418_reset:
    ld (p418_state_ptr),ix
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,P417_HISTORY_SIZE-1
    ldir
    ld hl,(p418_state_ptr)
    ld de,P417_CONTROL_O
    add hl,de
    ld b,10
    xor a
zx48_p418_reset_control:
    ld (hl),a
    inc hl
    djnz zx48_p418_reset_control
    xor a
    ret

; Emit exactly one logical byte into circular history while advancing persistent
; physical/logical/pending state. No final-memory sink is touched.
zx48_p418_step:
    call zx48_p418_control_ptr
    ld a,(iy+P418_C_PENDING_COUNT)
    or a
    jr nz,zx48_p418_pending

    call zx48_p418_get_physical
    ret c
    cp $40
    jr c,zx48_p418_new_literal
    cp $80
    jr c,zx48_p418_new_rle

    and $7f
    add a,3
    call zx48_p418_control_ptr
    ld (iy+P418_C_PENDING_COUNT),a
    ld (iy+P418_C_PENDING_KIND),P418_PENDING_BACKREF
    call zx48_p418_get_physical
    ret c
    call zx48_p418_control_ptr
    ld (iy+P418_C_PARAMETER),a
    jr zx48_p418_pending_backref

zx48_p418_new_literal:
    inc a
    call zx48_p418_control_ptr
    ld (iy+P418_C_PENDING_COUNT),a
    ld (iy+P418_C_PENDING_KIND),P418_PENDING_LITERAL
    jr zx48_p418_pending_literal

zx48_p418_new_rle:
    and $3f
    add a,3
    call zx48_p418_control_ptr
    ld (iy+P418_C_PENDING_COUNT),a
    ld (iy+P418_C_PENDING_KIND),P418_PENDING_RLE
    call zx48_p418_get_physical
    ret c
    call zx48_p418_control_ptr
    ld (iy+P418_C_PARAMETER),a
    jr zx48_p418_pending_rle

zx48_p418_pending:
    call zx48_p418_control_ptr
    ld a,(iy+P418_C_PENDING_KIND)
    cp P418_PENDING_LITERAL
    jr z,zx48_p418_pending_literal
    cp P418_PENDING_RLE
    jr z,zx48_p418_pending_rle
    cp P418_PENDING_BACKREF
    jr z,zx48_p418_pending_backref
    jp zx48_p418_format

zx48_p418_pending_literal:
    call zx48_p418_get_physical
    ret c
    jr zx48_p418_emit

zx48_p418_pending_rle:
    call zx48_p418_control_ptr
    ld a,(iy+P418_C_PARAMETER)
    jr zx48_p418_emit

zx48_p418_pending_backref:
    call zx48_p418_control_ptr
    ld a,(iy+P418_C_PARAMETER)
    inc a
    jr nz,zx48_p418_back_distance_byte
    ld hl,256
    jr zx48_p418_back_distance_ready
zx48_p418_back_distance_byte:
    ld l,a
    ld h,0
zx48_p418_back_distance_ready:
    ld a,(iy+P418_C_HISTORY_COUNT)
    ld e,a
    ld d,0
    push hl
    ex de,hl
    or a
    sbc hl,de
    pop hl
    jr nc,zx48_p418_back_count_ok
    ld a,h
    cp 1
    jp nz,zx48_p418_format
    ld a,l
    or a
    jp nz,zx48_p418_format
    ld l,(iy+P418_C_LOGICAL_POS)
    ld h,(iy+P418_C_LOGICAL_POS+1)
    ld a,h
    or a
    jp z,zx48_p418_format
    ld hl,256
zx48_p418_back_count_ok:
    ld a,(iy+P418_C_HISTORY_INDEX)
    sub l
    ld e,a
    ld d,0
    ld hl,(p418_state_ptr)
    add hl,de
    ld a,(hl)

zx48_p418_emit:
    ld (p418_byte),a
    call zx48_p418_control_ptr
    ld a,(iy+P418_C_HISTORY_INDEX)
    ld e,a
    ld d,0
    ld hl,(p418_state_ptr)
    add hl,de
    ld a,(p418_byte)
    ld (hl),a

    call zx48_p418_control_ptr
    ld a,(iy+P418_C_HISTORY_INDEX)
    inc a
    ld (iy+P418_C_HISTORY_INDEX),a
    ld a,(iy+P418_C_HISTORY_COUNT)
    cp $ff
    jr z,zx48_p418_history_count_done
    inc a
    ld (iy+P418_C_HISTORY_COUNT),a
zx48_p418_history_count_done:
    ld l,(iy+P418_C_LOGICAL_POS)
    ld h,(iy+P418_C_LOGICAL_POS+1)
    inc hl
    ld a,h
    or l
    jp z,zx48_p418_format
    ld (iy+P418_C_LOGICAL_POS),l
    ld (iy+P418_C_LOGICAL_POS+1),h
    ld a,(iy+P418_C_PENDING_COUNT)
    dec a
    ld (iy+P418_C_PENDING_COUNT),a
    jr nz,zx48_p418_emit_done
    ld (iy+P418_C_PENDING_KIND),P418_PENDING_NONE
zx48_p418_emit_done:
    xor a
    ret

; A <- bounded physical byte; advances persistent physical offset.
zx48_p418_get_physical:
    call zx48_p418_control_ptr
    ld l,(iy+P418_C_PHYSICAL_POS)
    ld h,(iy+P418_C_PHYSICAL_POS+1)
    ld e,(iy+P418_C_PHYSICAL_LENGTH)
    ld d,(iy+P418_C_PHYSICAL_LENGTH+1)
    push hl
    or a
    sbc hl,de
    pop hl
    jp nc,zx48_p418_format
    ld e,(iy+P418_C_SOURCE_BASE)
    ld d,(iy+P418_C_SOURCE_BASE+1)
    push hl
    add hl,de
    jp c,zx48_p418_get_wrap
    ld a,(hl)
    ld (p418_byte),a
    pop hl
    inc hl
    ld (iy+P418_C_PHYSICAL_POS),l
    ld (iy+P418_C_PHYSICAL_POS+1),h
    ld a,(p418_byte)
    or a
    ret
zx48_p418_get_wrap:
    pop hl
    jp zx48_p418_format

zx48_p418_inval:
    ld a,E_INVAL
    scf
    ret
zx48_p418_format:
    ld a,E_FORMAT
    scf
    ret

p418_state_ptr: dw 0
p418_source_base: dw 0
p418_physical_length: dw 0
p418_target: dw 0
p418_logical_length: dw 0
p418_byte: db 0
    ENDM

;
; P4.19 PACKED-to-RAW writable-open materialization. Decode into one private
; replacement first; only a completely validated decode may publish RAW metadata.
;
    MACRO EMIT_P419_PACKED_WRITE_ROUTINES
; IX=mutable PACKED object record. RAW is a no-op success.
zx48_p419_materialize_private:
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    ret z
    ld (p419_object_ptr),ix

    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld a,h
    or l
    jp z,zx48_p419_format
    ld (p419_logical_length),hl

    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p419_old_ptr),hl
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld (p419_old_storage),bc

    ld bc,(p419_logical_length)
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (p419_new_ptr),hl

    ld ix,(p419_object_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld de,(p419_logical_length)
    ld iy,(p419_new_ptr)
    ld ix,0
    ld a,P416_SINK_FINAL_MEMORY
    call zx48_p416_decode
    jr c,zx48_p419_decode_fail

    ; Publish the fully decoded private replacement atomically before old release.
    ld ix,(p419_object_ptr)
    ld hl,(p419_new_ptr)
    ld (ix+OBJ_ALLOCATION_PTR),l
    ld (ix+OBJ_ALLOCATION_PTR+1),h
    ld hl,(p419_logical_length)
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h
    ld a,(ix+OBJ_FLAGS_BYTE)
    and $fe
    ld (ix+OBJ_FLAGS_BYTE),a

    ld hl,(p419_old_ptr)
    ld bc,(p419_old_storage)
    bit 0,c
    jr z,zx48_p419_old_even
    inc bc
zx48_p419_old_even:
    call zx48_free
    ret nc
    ld a,PANIC_SCHEDULER
    jp zx48_panic

zx48_p419_decode_fail:
    ld (p419_error),a
    ld hl,(p419_new_ptr)
    ld bc,(p419_logical_length)
    bit 0,c
    jr z,zx48_p419_new_even
    inc bc
zx48_p419_new_even:
    call zx48_free
    jr c,zx48_p419_free_panic
    ld a,(p419_error)
    scf
    ret
zx48_p419_free_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

zx48_p419_format:
    ld a,E_FORMAT
    scf
    ret

p419_object_ptr: dw 0
p419_old_ptr: dw 0
p419_old_storage: dw 0
p419_new_ptr: dw 0
p419_logical_length: dw 0
p419_error: db 0
    ENDM

;
; P4.20 exact deterministic two-pass target-greedy ZXP1 encoder. The transient
; nearest-occurrence table is exactly 256 little-endian u16 entries (512 bytes).
; A=0 requests explicit failure semantics; A!=0 is background best-effort.
; HL=RAW source, BC=logical length, DE=private destination. On success HL is
; exact encoded length, or zero when the encoding is not strictly smaller.
;
    MACRO EMIT_P420_TARGET_ENCODER_ROUTINES
zx48_p420_two_pass:
    ld (p420_background),a
    ld (p420_input_base),hl
    ld (p420_input_len),bc
    ld (p420_output_base),de
    xor a
    ld (p420_workspace_allocs),a

    call zx48_p420_workspace_begin
    jp c,zx48_p420_workspace_fail
    xor a
    ld (p420_mode),a
    call zx48_p420_run_pass
    call zx48_p420_workspace_end
    jp c,zx48_p420_free_panic

    ld hl,(p420_encoded_len)
    ld (p420_measured_len),hl
    ld de,(p420_input_len)
    or a
    sbc hl,de
    jp nc,zx48_p420_no_saving

    call zx48_p420_workspace_begin
    jp c,zx48_p420_workspace_fail
    ld a,1
    ld (p420_mode),a
    call zx48_p420_run_pass
    call zx48_p420_workspace_end
    jp c,zx48_p420_free_panic

    ld hl,(p420_encoded_len)
    ld de,(p420_measured_len)
    or a
    sbc hl,de
    jp nz,zx48_p420_format
    ld hl,(p420_encoded_len)
    xor a
    or a
    ret

zx48_p420_no_saving:
    ld hl,0
    xor a
    or a
    ret

zx48_p420_workspace_fail:
    ld a,(p420_background)
    or a
    jr nz,zx48_p420_background_skip
    ld a,E_NOMEM
    scf
    ret
zx48_p420_background_skip:
    ld hl,0
    xor a
    or a
    ret

; Allocate and initialize exactly one 512-byte nearest-occurrence table.
zx48_p420_workspace_begin:
    ld bc,512
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    ret c
    ld (p420_table_ptr),hl
    ld (hl),$ff
    ld d,h
    ld e,l
    inc de
    ld bc,511
    ldir
    ld a,(p420_workspace_allocs)
    inc a
    ld (p420_workspace_allocs),a
    ld hl,512
    ld (p420_workspace_bytes),hl
    xor a
    or a
    ret

zx48_p420_workspace_end:
    ld hl,(p420_table_ptr)
    ld bc,512
    jp zx48_free

zx48_p420_free_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

; One deterministic pass. Mode 0 measures; mode 1 emits to p420_output_base.
zx48_p420_run_pass:
    ld hl,0
    ld (p420_pos),hl
    ld (p420_encoded_len),hl
    ld (p420_literal_start),hl
    xor a
    ld (p420_literal_len),a
    ld hl,(p420_output_base)
    ld (p420_emit_ptr),hl

zx48_p420_pass_loop:
    ld hl,(p420_pos)
    ld de,(p420_input_len)
    or a
    sbc hl,de
    jp z,zx48_p420_pass_finish
    jp nc,zx48_p420_format

    ; Capture current source byte.
    ld hl,(p420_pos)
    ld de,(p420_input_base)
    add hl,de
    ld a,(hl)
    ld (p420_current_byte),a

    ; Find the sole legal BACKREF candidate: nearest prior same-first-byte q.
    call zx48_p420_table_entry
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p420_q),de
    xor a
    ld (p420_back_len),a
    ld a,d
    cp $ff
    jr nz,zx48_p420_back_distance
    ld a,e
    cp $ff
    jr z,zx48_p420_back_done
zx48_p420_back_distance:
    ld hl,(p420_pos)
    or a
    sbc hl,de
    ld (p420_back_distance),hl
    ld a,h
    or l
    jr z,zx48_p420_back_done
    ld a,h
    or a
    jr z,zx48_p420_back_extend_init
    cp 1
    jr nz,zx48_p420_back_done
    ld a,l
    or a
    jr nz,zx48_p420_back_done
zx48_p420_back_extend_init:
    xor a
    ld (p420_match_len),a
zx48_p420_back_extend:
    ld a,(p420_match_len)
    cp 130
    jr nc,zx48_p420_back_extend_done

    ; Stop at logical EOF.
    ld e,a
    ld d,0
    ld hl,(p420_pos)
    add hl,de
    push hl
    ld de,(p420_input_len)
    or a
    sbc hl,de
    pop hl
    jr nc,zx48_p420_back_extend_done

    ; Probe source[p+len].
    ld de,(p420_input_base)
    add hl,de
    ld a,(hl)
    ld (p420_probe_byte),a

    ; Compare source[q+len].
    ld a,(p420_match_len)
    ld e,a
    ld d,0
    ld hl,(p420_q)
    add hl,de
    ld de,(p420_input_base)
    add hl,de
    ld a,(hl)
    ld e,a
    ld a,(p420_probe_byte)
    cp e
    jr nz,zx48_p420_back_extend_done
    ld a,(p420_match_len)
    inc a
    ld (p420_match_len),a
    jr zx48_p420_back_extend
zx48_p420_back_extend_done:
    ld a,(p420_match_len)
    ld (p420_back_len),a
zx48_p420_back_done:

    ; Independently extend RLE to at most 66 bytes.
    ld a,1
    ld (p420_rle_len),a
zx48_p420_rle_extend:
    ld a,(p420_rle_len)
    cp 66
    jr nc,zx48_p420_choose
    ld e,a
    ld d,0
    ld hl,(p420_pos)
    add hl,de
    push hl
    ld de,(p420_input_len)
    or a
    sbc hl,de
    pop hl
    jr nc,zx48_p420_choose
    ld de,(p420_input_base)
    add hl,de
    ld a,(hl)
    ld e,a
    ld a,(p420_current_byte)
    cp e
    jr nz,zx48_p420_choose
    ld a,(p420_rle_len)
    inc a
    ld (p420_rle_len),a
    jr zx48_p420_rle_extend

zx48_p420_choose:
    ; Ignore matches shorter than 3. Longer wins; RLE wins equal-length ties.
    ld a,(p420_rle_len)
    cp 3
    jr c,zx48_p420_choose_back
    ld b,a
    ld a,(p420_back_len)
    cp b
    jr c,zx48_p420_emit_rle
    jr z,zx48_p420_emit_rle
zx48_p420_choose_back:
    ld a,(p420_back_len)
    cp 3
    jr nc,zx48_p420_emit_back

    ; Unmatched byte joins the current literal run.
    ld a,(p420_literal_len)
    or a
    jr nz,zx48_p420_literal_have_start
    ld hl,(p420_pos)
    ld (p420_literal_start),hl
zx48_p420_literal_have_start:
    ld a,1
    call zx48_p420_update_positions
    ld a,(p420_literal_len)
    inc a
    ld (p420_literal_len),a
    cp 64
    call z,zx48_p420_flush_literal
    jp zx48_p420_pass_loop

zx48_p420_emit_rle:
    call zx48_p420_flush_literal
    ld a,(p420_rle_len)
    ld (p420_selected_len),a
    call zx48_p420_add_two_encoded
    ld a,(p420_mode)
    or a
    jr z,zx48_p420_rle_update
    ld hl,(p420_emit_ptr)
    ld a,(p420_selected_len)
    sub 3
    or $40
    ld (hl),a
    inc hl
    ld a,(p420_current_byte)
    ld (hl),a
    inc hl
    ld (p420_emit_ptr),hl
zx48_p420_rle_update:
    ld a,(p420_selected_len)
    call zx48_p420_update_positions
    jp zx48_p420_pass_loop

zx48_p420_emit_back:
    call zx48_p420_flush_literal
    ld a,(p420_back_len)
    ld (p420_selected_len),a
    call zx48_p420_add_two_encoded
    ld a,(p420_mode)
    or a
    jr z,zx48_p420_back_update
    ld hl,(p420_emit_ptr)
    ld a,(p420_selected_len)
    sub 3
    or $80
    ld (hl),a
    inc hl
    ld a,(p420_back_distance)
    dec a
    ld (hl),a
    inc hl
    ld (p420_emit_ptr),hl
zx48_p420_back_update:
    ld a,(p420_selected_len)
    call zx48_p420_update_positions
    jp zx48_p420_pass_loop

zx48_p420_pass_finish:
    call zx48_p420_flush_literal
    xor a
    or a
    ret

; A=count. Update nearest-occurrence table for every consumed logical position.
zx48_p420_update_positions:
    ld (p420_update_remaining),a
    ld hl,(p420_pos)
    ld (p420_update_pos),hl
zx48_p420_update_loop:
    ld hl,(p420_update_pos)
    ld de,(p420_input_base)
    add hl,de
    ld a,(hl)
    call zx48_p420_table_entry
    ld de,(p420_update_pos)
    ld (hl),e
    inc hl
    ld (hl),d
    ld hl,(p420_update_pos)
    inc hl
    ld (p420_update_pos),hl
    ld a,(p420_update_remaining)
    dec a
    ld (p420_update_remaining),a
    jr nz,zx48_p420_update_loop
    ld hl,(p420_update_pos)
    ld (p420_pos),hl
    ret

; A=current byte -> HL=&table[A].
zx48_p420_table_entry:
    ld e,a
    ld d,0
    sla e
    rl d
    ld hl,(p420_table_ptr)
    add hl,de
    ret

zx48_p420_add_two_encoded:
    ld hl,(p420_encoded_len)
    inc hl
    inc hl
    ld (p420_encoded_len),hl
    ret

zx48_p420_flush_literal:
    ld a,(p420_literal_len)
    or a
    ret z
    ld b,a
    ld e,a
    ld d,0
    inc de
    ld hl,(p420_encoded_len)
    add hl,de
    ld (p420_encoded_len),hl

    ld a,(p420_mode)
    or a
    jr z,zx48_p420_flush_done
    ld hl,(p420_emit_ptr)
    ld a,b
    dec a
    ld (hl),a
    inc hl
    ex de,hl
    ld hl,(p420_literal_start)
    ld bc,(p420_input_base)
    add hl,bc
    ld c,b
    ld b,0
    ld a,(p420_literal_len)
    ld c,a
    ldir
    ex de,hl
    ld (p420_emit_ptr),hl
zx48_p420_flush_done:
    xor a
    ld (p420_literal_len),a
    ret

zx48_p420_format:
    ld a,E_FORMAT
    scf
    ret

p420_input_base: dw 0
p420_input_len: dw 0
p420_output_base: dw 0
p420_emit_ptr: dw 0
p420_table_ptr: dw 0
p420_pos: dw 0
p420_encoded_len: dw 0
p420_measured_len: dw 0
p420_literal_start: dw 0
p420_q: dw 0
p420_back_distance: dw 0
p420_update_pos: dw 0
p420_workspace_bytes: dw 0
p420_literal_len: db 0
p420_back_len: db 0
p420_rle_len: db 0
p420_match_len: db 0
p420_selected_len: db 0
p420_current_byte: db 0
p420_probe_byte: db 0
p420_update_remaining: db 0
p420_mode: db 0
p420_background: db 0
p420_workspace_allocs: db 0
    ENDM

;
; P4.21 representation decision: zero-length objects and non-smaller encodings stay
; RAW. Only a strictly smaller target-greedy stream is eligible for publication.
;
    MACRO EMIT_P421_PACK_DECISION_ROUTINES
; A=background flag, HL=RAW source, BC=logical length, DE=private destination.
; Returns HL=encoded length only when strictly smaller; HL=0 means remain RAW.
zx48_p421_encode_if_smaller:
    ld a,b
    or c
    jr nz,zx48_p421_nonempty
    ld hl,0
    xor a
    or a
    ret
zx48_p421_nonempty:
    jp zx48_p420_two_pass
    ENDM

;
; P4.22 atomic SYS_PACK record transaction. P4.20 supplies the deterministic
; target-greedy passes; this layer owns exact-destination allocation,
; self-validation, publication, and rollback.
;
    MACRO EMIT_P422_SYS_PACK_CODEC_ROUTINES
; IX=record,D=object slot. Returns HL=bytes saved, or HL=0 when unchanged.
zx48_p422_pack_record:
    ld hl,(p422_pack_attempts)
    inc hl
    ld (p422_pack_attempts),hl
    ld (p422_object_ptr),ix
    ld a,d
    ld (p422_slot),a

    ; Only mutable resident RAM payload objects may be packed.
    ld a,(ix+OBJ_RESERVED_BYTE)
    cp STATE_RAM
    jp nz,zx48_p422_perm
    ld a,(ix+OBJ_TYPE_ID)
    cp OBJ_DIR
    jp z,zx48_p422_perm
    cp OBJ_DEV
    jp z,zx48_p422_perm
    cp OBJ_SYS
    jp z,zx48_p422_perm

    ; Already PACKED is an unconditional no-op success.
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jp nz,zx48_p422_zero

    ; Any live description blocks a RAW representation swap.
    ld a,(p422_slot)
    ld d,a
    call zx48_od_object_any_live
    ret c

    ld ix,(p422_object_ptr)
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (p422_logical),hl
    ld a,h
    or a
    jr nz,zx48_p422_size_ok
    ld a,l
    cp 64
    jp c,zx48_p422_zero
zx48_p422_size_ok:
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p422_old_ptr),hl

    ; Pass 1: exact encoded-size measurement under one 512-byte NO_COMPACT table.
    ld hl,(p422_old_ptr)
    ld (p420_input_base),hl
    ld hl,(p422_logical)
    ld (p420_input_len),hl
    ld hl,0
    ld (p420_output_base),hl
    xor a
    ld (p420_mode),a
    ld (p420_background),a
    ld (p420_workspace_allocs),a
    call zx48_p420_workspace_begin
    ret c
    call zx48_p420_run_pass
    jp c,zx48_p422_pass1_fail
    ld hl,(p420_encoded_len)
    ld (p422_encoded),hl
    call zx48_p420_workspace_end
    jp c,zx48_p422_free_panic

    ; Equal/larger encodings leave committed RAW bytes exactly unchanged.
    ld hl,(p422_encoded)
    ld de,(p422_logical)
    or a
    sbc hl,de
    jp nc,zx48_p422_zero

    ; Allocate exactly the measured compressed destination.
    ld bc,(p422_encoded)
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    ret c
    ld (p422_new_ptr),hl

    ; Pass 2: reinitialized exact 512-byte table emits exactly the measured stream.
    ld hl,(p422_new_ptr)
    ld (p420_output_base),hl
    ld a,1
    ld (p420_mode),a
    call zx48_p420_workspace_begin
    jp c,zx48_p422_dest_fail
    call zx48_p420_run_pass
    jp c,zx48_p422_pass2_fail
    ld hl,(p420_encoded_len)
    ld de,(p422_encoded)
    or a
    sbc hl,de
    jp nz,zx48_p422_pass2_format
    call zx48_p420_workspace_end
    jp c,zx48_p422_free_panic

    ; Self-validate the private stream with the frozen P4.16 DISCARD decoder.
    ld bc,256
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    jp c,zx48_p422_dest_fail
    ld (p422_history),hl
    push hl
    pop ix
    ld iy,0
    xor a
    ld (p416_crc_enable),a
    ld hl,(p422_new_ptr)
    ld bc,(p422_encoded)
    ld de,(p422_logical)
    ld a,P416_SINK_DISCARD
    call zx48_p416_decode
    jp c,zx48_p422_validate_fail
    ld hl,(p422_history)
    ld bc,256
    call zx48_free
    jp c,zx48_p422_free_panic

    ; Publish only after complete private validation.
    ld ix,(p422_object_ptr)
    ld hl,(p422_new_ptr)
    ld (ix+OBJ_ALLOCATION_PTR),l
    ld (ix+OBJ_ALLOCATION_PTR+1),h
    ld hl,(p422_encoded)
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h
    ld a,(ix+OBJ_FLAGS_BYTE)
    or OBJ_PACKED
    ld (ix+OBJ_FLAGS_BYTE),a
    ld hl,(p422_pack_successes)
    inc hl
    ld (p422_pack_successes),hl

    ; Old RAW allocation becomes unreachable only after publication.
    ld hl,(p422_old_ptr)
    ld bc,(p422_logical)
    bit 0,c
    jr z,zx48_p422_old_even
    inc bc
zx48_p422_old_even:
    call zx48_free
    jp c,zx48_p422_free_panic

    ld hl,(p422_logical)
    ld de,(p422_encoded)
    or a
    sbc hl,de
    xor a
    or a
    ret

zx48_p422_pass1_fail:
    ld (p422_error),a
    call zx48_p420_workspace_end
    jp c,zx48_p422_free_panic
    ld a,(p422_error)
    scf
    ret

zx48_p422_pass2_format:
    ld a,E_FORMAT
    ld (p422_error),a
    call zx48_p420_workspace_end
    jp c,zx48_p422_free_panic
    jr zx48_p422_dest_fail_saved
zx48_p422_pass2_fail:
    ld (p422_error),a
    call zx48_p420_workspace_end
    jp c,zx48_p422_free_panic
zx48_p422_dest_fail_saved:
    ld a,(p422_error)
    jr zx48_p422_dest_fail_with_a

zx48_p422_validate_fail:
    ld (p422_error),a
    ld hl,(p422_history)
    ld bc,256
    call zx48_free
    jp c,zx48_p422_free_panic
    ld a,(p422_error)
zx48_p422_dest_fail_with_a:
    ld (p422_error),a
zx48_p422_dest_fail:
    ld a,(p422_error)
    or a
    jr nz,zx48_p422_dest_have_error
    ld a,E_NOMEM
    ld (p422_error),a
zx48_p422_dest_have_error:
    ld hl,(p422_new_ptr)
    ld bc,(p422_encoded)
    bit 0,c
    jr z,zx48_p422_dest_even
    inc bc
zx48_p422_dest_even:
    call zx48_free
    jp c,zx48_p422_free_panic
    ld a,(p422_error)
    scf
    ret

zx48_p422_zero:
    ld hl,0
    xor a
    or a
    ret
zx48_p422_perm:
    ld a,E_PERM
    scf
    ret
zx48_p422_free_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

p422_object_ptr: dw 0
p422_old_ptr: dw 0
p422_new_ptr: dw 0
p422_history: dw 0
p422_logical: dw 0
p422_encoded: dw 0
p422_slot: db 0
p422_error: db 0
p422_pack_attempts: dw 0
p422_pack_successes: dw 0
    ENDM

;
; P4.23 atomic SYS_UNPACK record transaction. Whole-stream contiguous decode uses
; the P4.16 FINAL_MEMORY sink, whose BACKREF source is already-emitted destination
; memory; no separate 256-byte history allocation is permitted here.
;
    MACRO EMIT_P423_SYS_UNPACK_CODEC_ROUTINES
; IX=record,D=object slot. RAW is no-op success returning logical length.
zx48_p423_unpack_record:
    ld (p423_object_ptr),ix
    ld a,d
    ld (p423_slot),a
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (p423_logical),hl

    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr nz,zx48_p423_packed
    ld hl,(p423_logical)
    xor a
    or a
    ret

zx48_p423_packed:
    ; Any live description blocks the representation swap.
    ld a,(p423_slot)
    ld d,a
    call zx48_od_object_any_live
    ret c

    ld ix,(p423_object_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p423_old_ptr),hl
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld (p423_old_storage),bc

    ; Exact private RAW destination.
    ld bc,(p423_logical)
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (p423_new_ptr),hl

    ; Whole stream from offset zero into one contiguous final destination.
    ld ix,(p423_object_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld de,(p423_logical)
    ld iy,(p423_new_ptr)
    ld ix,0
    xor a
    ld (p416_crc_enable),a
    ld a,P416_SINK_FINAL_MEMORY
    call zx48_p416_decode
    jr c,zx48_p423_decode_fail

    ; Publish only after exact validated decode.
    ld ix,(p423_object_ptr)
    ld hl,(p423_new_ptr)
    ld (ix+OBJ_ALLOCATION_PTR),l
    ld (ix+OBJ_ALLOCATION_PTR+1),h
    ld hl,(p423_logical)
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h
    ld a,(ix+OBJ_FLAGS_BYTE)
    and $fe
    ld (ix+OBJ_FLAGS_BYTE),a

    ; Old packed storage becomes unreachable only after publication.
    ld hl,(p423_old_ptr)
    ld bc,(p423_old_storage)
    bit 0,c
    jr z,zx48_p423_old_even
    inc bc
zx48_p423_old_even:
    call zx48_free
    jp c,zx48_p423_free_panic

    ld hl,(p423_logical)
    xor a
    or a
    ret

zx48_p423_decode_fail:
    ld (p423_error),a
    ld hl,(p423_new_ptr)
    ld bc,(p423_logical)
    bit 0,c
    jr z,zx48_p423_new_even
    inc bc
zx48_p423_new_even:
    call zx48_free
    jp c,zx48_p423_free_panic
    ld a,(p423_error)
    scf
    ret

zx48_p423_free_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

p423_object_ptr: dw 0
p423_old_ptr: dw 0
p423_old_storage: dw 0
p423_new_ptr: dw 0
p423_logical: dw 0
p423_slot: db 0
p423_error: db 0
    ENDM

;
; P4.24 close-time opportunistic pack-candidate manager. The queue is exactly
; one bit per mutable RAM object slot and never performs compression itself.
;
    MACRO EMIT_P424_PACK_CANDIDATE_ROUTINES
zx48_p424_candidates_init:
    xor a
    ld hl,p424_candidate_bits
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
    ret

; A=slot. Clear stale candidacy on reopen/write/remove/slot reuse.
zx48_p424_candidate_clear:
    cp RAM_OBJECT_COUNT
    ret nc
    ld (p424_slot),a
    and 7
    ld e,a
    ld d,0
    ld hl,p424_mask_table
    add hl,de
    ld a,(hl)
    cpl
    ld b,a
    ld a,(p424_slot)
    srl a
    srl a
    srl a
    ld e,a
    ld d,0
    ld hl,p424_candidate_bits
    add hl,de
    ld a,(hl)
    and b
    ld (hl),a
    xor a
    ret

; A=slot, IX=object record. Mark only eligible mutable resident RAW >=64.
zx48_p424_candidate_mark_if_eligible:
    cp RAM_OBJECT_COUNT
    ret nc
    ld (p424_slot),a
    ld a,(ix+OBJ_TYPE_ID)
    or a
    ret z
    cp OBJ_DIR
    ret z
    cp OBJ_DEV
    ret z
    cp OBJ_SYS
    ret z
    ld a,(ix+OBJ_RESERVED_BYTE)
    cp STATE_RAM
    ret nz
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    ret nz
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld a,h
    or a
    jr nz,zx48_p424_mark
    ld a,l
    cp 64
    ret c
zx48_p424_mark:
    ld a,(p424_slot)
    and 7
    ld e,a
    ld d,0
    ld hl,p424_mask_table
    add hl,de
    ld b,(hl)
    ld a,(p424_slot)
    srl a
    srl a
    srl a
    ld e,a
    ld d,0
    ld hl,p424_candidate_bits
    add hl,de
    ld a,(hl)
    or b
    ld (hl),a
    xor a
    ret

; A=slot -> Z clear, NZ set.
zx48_p424_candidate_test:
    cp RAM_OBJECT_COUNT
    jr nc,zx48_p424_candidate_test_clear
    ld (p424_slot),a
    and 7
    ld e,a
    ld d,0
    ld hl,p424_mask_table
    add hl,de
    ld b,(hl)
    ld a,(p424_slot)
    srl a
    srl a
    srl a
    ld e,a
    ld d,0
    ld hl,p424_candidate_bits
    add hl,de
    ld a,(hl)
    and b
    ret
zx48_p424_candidate_test_clear:
    xor a
    ret

p424_candidate_bits: defs 4,0
p424_slot: db 0
p424_mask_table:
    db 1,2,4,8,16,32,64,128
    ENDM

;
; P4.25 PID0 idle maintenance pack service. Exactly one set candidate bit may be
; consumed per call. The selected bit is cleared before revalidation/attempt so
; failure, no saving, or E_NOMEM cannot retry within the same idle cycle.
;
    MACRO EMIT_P425_IDLE_PACK_ROUTINES
zx48_p425_pack_once:
    xor a
    ld (p425_attempted),a
    ld (p425_slot),a
zx48_p425_scan:
    ld a,(p425_slot)
    cp RAM_OBJECT_COUNT
    jr nc,zx48_p425_done
    call zx48_p424_candidate_test
    jr nz,zx48_p425_selected
    ld a,(p425_slot)
    inc a
    ld (p425_slot),a
    jr zx48_p425_scan

zx48_p425_selected:
    ld a,(p425_slot)
    call zx48_p424_candidate_clear
    ld a,1
    ld (p425_attempted),a

    ld a,(p425_slot)
    call zx48_p405_object_ptr_slot
    jr c,zx48_p425_done

    ; Revalidate the same slot immediately before any allocation or mutation.
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_p425_done
    cp OBJ_DIR
    jr z,zx48_p425_done
    cp OBJ_DEV
    jr z,zx48_p425_done
    cp OBJ_SYS
    jr z,zx48_p425_done
    ld a,(ix+OBJ_RESERVED_BYTE)
    cp STATE_RAM
    jr nz,zx48_p425_done
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr nz,zx48_p425_done
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld a,h
    or a
    jr nz,zx48_p425_size_ok
    ld a,l
    cp 64
    jr c,zx48_p425_done
zx48_p425_size_ok:
    ld a,(p425_slot)
    ld d,a
    call zx48_od_object_any_live
    jr c,zx48_p425_done

    ; The bounded OD scan clobbers IX. Restore the selected object record
    ; before entering the P4.22 record transaction.
    ld a,(p425_slot)
    call zx48_p405_object_ptr_slot
    jr c,zx48_p425_done
    ld a,(p425_slot)
    ld d,a
    call zx48_p422_pack_record
    ; Background maintenance is best-effort. Atomic P4.22 guarantees any
    ; carry-path failure leaves the committed RAW representation unchanged.
    jr c,zx48_p425_done

zx48_p425_done:
    xor a
    or a
    ret

p425_slot: db 0
p425_attempted: db 0
    ENDM

;
; P4.26 synchronous allocation-pressure victim service. The scan is independent
; of the close-time candidate bitset and selects at most one mutable closed RAW
; object: greatest logical length, then exact record path/name byte order.
;
    MACRO EMIT_P426_COMPACTION_ROUTINES
zx48_p426_try_one_victim:
    xor a
    ld (p426_scan_slot),a
    ld (p426_victim_attempted),a
    ld (p426_victim_succeeded),a
    ld hl,0
    ld (p426_best_length),hl
    ld a,$ff
    ld (p426_best_slot),a

zx48_p426_scan:
    ld a,(p426_scan_slot)
    cp RAM_OBJECT_COUNT
    jp nc,zx48_p426_scan_done
    call zx48_p405_object_ptr_slot
    jp c,zx48_p426_next
    ld (p426_candidate_ptr),ix

    ; Mutable resident RAW object only.
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jp z,zx48_p426_next
    cp OBJ_DIR
    jp z,zx48_p426_next
    cp OBJ_DEV
    jp z,zx48_p426_next
    cp OBJ_SYS
    jp z,zx48_p426_next
    ld a,(ix+OBJ_RESERVED_BYTE)
    cp STATE_RAM
    jp nz,zx48_p426_next
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jp nz,zx48_p426_next

    ; Direct-memory ownership is an explicit per-slot exclusion.
    ld a,(p426_scan_slot)
    call zx48_p426_direct_owner_test
    jp nz,zx48_p426_next

    ; Any live OD excludes this object. The OD scan clobbers IX.
    ld a,(p426_scan_slot)
    ld d,a
    call zx48_od_object_any_live
    jp c,zx48_p426_next
    ld a,(p426_scan_slot)
    call zx48_p405_object_ptr_slot
    jp c,zx48_p426_next
    ld (p426_candidate_ptr),ix

    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld a,h
    or l
    jp z,zx48_p426_next
    ld (p426_candidate_length),hl

    ld a,(p426_best_slot)
    cp $ff
    jr z,zx48_p426_choose_candidate

    ; Larger logical object wins.
    ld de,(p426_best_length)
    or a
    sbc hl,de
    jr c,zx48_p426_next
    jr nz,zx48_p426_choose_candidate

    ; Equal logical length: exact path/name byte order. Directory IDs are
    ; frozen in canonical pathname byte order; then compare all 10 name bytes.
    ld ix,(p426_candidate_ptr)
    ld a,(ix+OBJ_DIR_ID)
    ld b,a
    ld ix,(p426_best_ptr)
    ld a,(ix+OBJ_DIR_ID)
    cp b
    jr c,zx48_p426_next
    jr nz,zx48_p426_choose_candidate

    ld ix,(p426_candidate_ptr)
    ld hl,0
zx48_p426_name_compare:
    ld a,l
    cp 10
    jr nc,zx48_p426_next
    push hl
    push ix
    pop de
    add hl,de
    ld a,(hl)
    ld b,a
    pop hl
    push hl
    ld ix,(p426_best_ptr)
    push ix
    pop de
    add hl,de
    ld a,(hl)
    cp b
    pop hl
    jr c,zx48_p426_next
    jr nz,zx48_p426_choose_candidate
    inc l
    jr zx48_p426_name_compare

zx48_p426_choose_candidate:
    ld a,(p426_scan_slot)
    ld (p426_best_slot),a
    ld hl,(p426_candidate_length)
    ld (p426_best_length),hl
    ld ix,(p426_candidate_ptr)
    ld (p426_best_ptr),ix

zx48_p426_next:
    ld a,(p426_scan_slot)
    inc a
    ld (p426_scan_slot),a
    jp zx48_p426_scan

zx48_p426_scan_done:
    ld a,(p426_best_slot)
    cp $ff
    jp z,zx48_p426_done

    ; Exactly one selected victim may be attempted per allocator request.
    ld a,1
    ld (p426_victim_attempted),a
    ld a,(p426_best_slot)
    call zx48_p405_object_ptr_slot
    jp c,zx48_p426_done
    ld (p426_best_ptr),ix

    ; Dry-run under exact 512-byte guarded workspace.
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p420_input_base),hl
    ld hl,(p426_best_length)
    ld (p420_input_len),hl
    ld hl,0
    ld (p420_output_base),hl
    xor a
    ld (p420_mode),a
    ld a,1
    ld (p420_background),a
    xor a
    ld (p420_workspace_allocs),a
    call zx48_p420_workspace_begin
    jp c,zx48_p426_done
    call zx48_p420_run_pass
    jr c,zx48_p426_measure_fail
    ld hl,(p420_encoded_len)
    ld (p426_encoded_length),hl
    call zx48_p420_workspace_end
    jp c,zx48_p426_free_panic

    ; Non-smaller streams cannot recover allocation space.
    ld hl,(p426_encoded_length)
    ld de,(p426_best_length)
    or a
    sbc hl,de
    jp nc,zx48_p426_done

    ; Preflight the exact destination plus the largest later scratch (512).
    ; Both probes are guarded and private, and are freed before the real pack.
    ld bc,(p426_encoded_length)
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    jp c,zx48_p426_done
    ld (p426_probe_dest),hl
    ld bc,512
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    jr c,zx48_p426_probe_workspace_fail
    ld (p426_probe_workspace),hl

    ld hl,(p426_probe_workspace)
    ld bc,512
    call zx48_free
    jp c,zx48_p426_free_panic
    call zx48_p426_free_probe_dest
    jp c,zx48_p426_free_panic

    ; Restore the chosen record after allocator/free routines clobber IX.
    ld a,(p426_best_slot)
    call zx48_p405_object_ptr_slot
    jp c,zx48_p426_done
    ld a,(p426_best_slot)
    ld d,a
    call zx48_p422_pack_record
    jp c,zx48_p426_done
    ld a,1
    ld (p426_victim_succeeded),a
    jr zx48_p426_done

zx48_p426_measure_fail:
    ld (p426_error),a
    call zx48_p420_workspace_end
    jp c,zx48_p426_free_panic
    jr zx48_p426_done

zx48_p426_probe_workspace_fail:
    call zx48_p426_free_probe_dest
    jp c,zx48_p426_free_panic
    jr zx48_p426_done

zx48_p426_free_probe_dest:
    ld hl,(p426_probe_dest)
    ld bc,(p426_encoded_length)
    bit 0,c
    jr z,zx48_p426_probe_even
    inc bc
zx48_p426_probe_even:
    jp zx48_free

zx48_p426_free_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

zx48_p426_done:
    xor a
    or a
    ret

; A=slot -> Z when not directly owned, NZ when direct ownership excludes packing.
zx48_p426_direct_owner_test:
    ld (p426_owner_slot),a
    and 7
    ld e,a
    ld d,0
    ld hl,p424_mask_table
    add hl,de
    ld b,(hl)
    ld a,(p426_owner_slot)
    srl a
    srl a
    srl a
    ld e,a
    ld d,0
    ld hl,p426_direct_owner_bits
    add hl,de
    ld a,(hl)
    and b
    ret

p426_direct_owner_bits: defs 4,0
p426_scan_slot: db 0
p426_best_slot: db $ff
p426_owner_slot: db 0
p426_victim_attempted: db 0
p426_victim_succeeded: db 0
p426_candidate_ptr: dw 0
p426_best_ptr: dw 0
p426_candidate_length: dw 0
p426_best_length: dw 0
p426_encoded_length: dw 0
p426_probe_dest: dw 0
p426_probe_workspace: dw 0
p426_error: db 0
    ENDM
;
; P4.28 exact SYS_ZXPACK_INFO / ZPINFO1 accounting.
;
    MACRO EMIT_P428_ZXPACK_INFO_ROUTINES
; HL -> validated writable 20-byte ZPINFO1. Current-state totals concern only
; mutable STATE_RAM object payloads. Packed-reader state counts live OD_AUX
; allocations exactly once per shared open description.
zx48_p428_zxpack_info:
    ld (p428_info_ptr),hl
    xor a
    ld hl,p428_info_scratch
    ld de,p428_info_scratch+1
    ld bc,19
    ld (hl),a
    ldir

    ld ix,p405_object_table
    ld b,RAM_OBJECT_COUNT
zx48_p428_object_loop:
    push bc
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_p428_object_next
    ld a,(ix+OBJ_RESERVED_BYTE)
    cp STATE_RAM
    jr nz,zx48_p428_object_next
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld de,(p428_info_scratch+0)
    add hl,de
    ld (p428_info_scratch+0),hl
    jr nc,zx48_p428_logical_no_carry
    ld hl,(p428_info_scratch+2)
    inc hl
    ld (p428_info_scratch+2),hl
zx48_p428_logical_no_carry:
    ld l,(ix+OBJ_STORAGE_LENGTH)
    ld h,(ix+OBJ_STORAGE_LENGTH+1)
    ld de,(p428_info_scratch+4)
    add hl,de
    jp c,zx48_p428_accounting_invalid
    ld (p428_info_scratch+4),hl
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr z,zx48_p428_count_raw
    ld hl,p428_info_scratch+10
    inc (hl)
    jr zx48_p428_object_next
zx48_p428_count_raw:
    ld hl,p428_info_scratch+11
    inc (hl)
zx48_p428_object_next:
    ld de,OBJ_RECORD_SIZE
    add ix,de
    pop bc
    djnz zx48_p428_object_loop

    ld hl,(p428_info_scratch+0)
    ld de,(p428_info_scratch+4)
    or a
    sbc hl,de
    ld (p428_info_scratch+6),hl
    ld hl,(p428_info_scratch+2)
    ld de,0
    sbc hl,de
    jp c,zx48_p428_accounting_invalid
    ld (p428_info_scratch+8),hl

    ld ix,open_description_table
    ld b,OPEN_DESCRIPTION_COUNT
    ld hl,0
zx48_p428_od_loop:
    ld a,(ix+OD_KIND_O)
    or a
    jr z,zx48_p428_od_next
    ld e,(ix+OD_AUX_O)
    ld d,(ix+OD_AUX_O+1)
    ld a,d
    or e
    jr z,zx48_p428_od_next
    ld de,PACKED_READER_STATE_SIZE
    add hl,de
zx48_p428_od_next:
    ld de,OD_COMPACT_SIZE
    add ix,de
    djnz zx48_p428_od_loop
    ld (p428_info_scratch+12),hl

    ld hl,(p422_pack_attempts)
    ld (p428_info_scratch+14),hl
    ld hl,(p422_pack_successes)
    ld (p428_info_scratch+16),hl
    xor a
    ld (p428_info_scratch+18),a
    ld (p428_info_scratch+19),a

    ld hl,p428_info_scratch
    ld de,(p428_info_ptr)
    ld bc,20
    ldir
    xor a
    or a
    ret
zx48_p428_accounting_invalid:
    ld a,E_INVAL
    scf
    ret
p428_info_ptr: dw 0
p428_info_scratch: defs 20,0
    ENDM

;
; P4.27 resident PACKED spawn stream adapter. This deliberately exposes only
; one-byte continuation over the already-bound P4.18 state so header parsing,
; image emission and relocation parsing share one uninterrupted 272-byte history.
;
    MACRO EMIT_P427_PACKED_SPAWN_STREAM_ROUTINES
; IX=bound P4.18 state -> A=next logical byte.
zx48_p427_stream_step:
    call zx48_p418_step
    ret c
    ld a,(p418_byte)
    or a
    ret
    ENDM


;
; P5.05 one-state PACKED tape validation. IX points at the exact 272-byte
; temporary decoder state; the first 256 bytes are the bounded ZXP1 history.
; HL=resident physical ZXP1, BC=physical length, DE=declared logical length.
; Success leaves the computed logical CRC in p416_crc and materializes no RAW copy.
;
    MACRO EMIT_P505_PACKED_VALIDATOR_ROUTINES
zx48_p505_validate_zxp1:
    ld a,1
    ld (p416_crc_enable),a
    ld iy,0
    ld a,P416_SINK_DISCARD
    call zx48_p416_decode
    ret
    ENDM
