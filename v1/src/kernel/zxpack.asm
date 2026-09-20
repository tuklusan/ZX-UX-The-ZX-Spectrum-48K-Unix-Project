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
