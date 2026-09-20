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
; Synchronous cassette transport. Physical positioning is never inferred.

    MACRO EMIT_P502_CRC16_ROUTINES
; HL=source, BC=length. Returns DE=CRC-16/CCITT-FALSE.
; Polynomial=$1021, init=$FFFF, refin=false, refout=false, xorout=$0000.
; Consumes HL/BC and clobbers AF. Zero length returns $FFFF.
zx48_crc16_ccitt_false:
    ld de,M48O_CRC16_INIT
zx48_crc16_ccitt_false_byte:
    ld a,b
    or c
    ret z
    ld a,(hl)
    inc hl
    xor d
    ld d,a
    dec bc
    push bc
    ld b,8
zx48_crc16_ccitt_false_bit:
    sla e
    rl d
    jr nc,zx48_crc16_ccitt_false_no_poly
    ld a,e
    xor $21
    ld e,a
    ld a,d
    xor $10
    ld d,a
zx48_crc16_ccitt_false_no_poly:
    djnz zx48_crc16_ccitt_false_bit
    pop bc
    jr zx48_crc16_ccitt_false_byte
    ENDM

    MACRO EMIT_P503_FRAMING_ROUTINES
; BC=physical bytes remaining. A is always the M48O ROM data flag and
; DE is zero for no payload or min(BC,512) for the next payload block.
zx48_p503_prepare_header_block:
    ld a,M48O_ROM_DATA_FLAG
    ld de,M48O_HEADER_SIZE
    ret
zx48_p503_prepare_chunk:
zx48_p503_next_chunk:
    ld de,0
    ld a,b
    or c
    jr z,zx48_p503_chunk_ready
    ld de,M48O_CHUNK_SIZE
    ld a,b
    cp d
    jr c,zx48_p503_use_remaining
    jr nz,zx48_p503_chunk_ready
    ld a,c
    cp e
    jr nc,zx48_p503_chunk_ready
zx48_p503_use_remaining:
    ld d,b
    ld e,c
zx48_p503_chunk_ready:
    ld a,M48O_ROM_DATA_FLAG
    ret
    ENDM

    MACRO EMIT_P504_RAW_LOADER_ROUTINES
; HL -> private 32-byte M48O header already read from the separate header block.
; Validate the complete public RAW contract before allocation. Payload chunks are
; streamed directly into the final allocation. Success publishes only the
; validated private representation through p504_published/result fields; P5.09
; owns atomic namespace create/replace.
zx48_p504_raw_load:
    ld (p504_header_ptr),hl
    xor a
    ld (p504_published),a
    ld (p504_alloc_ptr),a
    ld (p504_alloc_ptr+1),a
    ld (p504_free_needed),a

    ; Magic/version/RAW flags.
    ld hl,(p504_header_ptr)
    ld a,(hl)
    cp M48O_MAGIC_0
    jp nz,zx48_p504_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_1
    jp nz,zx48_p504_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_2
    jp nz,zx48_p504_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_3
    jp nz,zx48_p504_format
    inc hl
    ld a,(hl)
    cp M48O_VERSION
    jp nz,zx48_p504_format
    inc hl
    ld a,(hl)
    ld (p504_type),a
    cp M48O_TYPE_TXT
    jp c,zx48_p504_format
    cp M48O_TYPE_SYS+1
    jp nc,zx48_p504_format
    inc hl
    ld a,(hl)
    or a
    jp nz,zx48_p504_format
    inc hl
    ld a,(hl)
    ld (p504_target),a

    ; Public mutable placement.
    cp M48O_TARGET_BIN
    jr z,zx48_p504_place_bin
    cp M48O_TARGET_ETC
    jr z,zx48_p504_place_etc
    cp M48O_TARGET_USERHOME
    jr z,zx48_p504_place_ordinary
    cp M48O_TARGET_TMP
    jr z,zx48_p504_place_ordinary
    jp zx48_p504_format
zx48_p504_place_bin:
    ld a,(p504_type)
    cp M48O_TYPE_BIN
    jp nz,zx48_p504_format
    jr zx48_p504_lengths
zx48_p504_place_etc:
    ld a,(p504_type)
    cp M48O_TYPE_TXT
    jr z,zx48_p504_lengths
    cp M48O_TYPE_CFG
    jp nz,zx48_p504_format
    jr zx48_p504_lengths
zx48_p504_place_ordinary:
    ld a,(p504_type)
    cp M48O_TYPE_CFG+1
    jp nc,zx48_p504_format

zx48_p504_lengths:
    ld hl,(p504_header_ptr)
    ld bc,M48O_HDR_STORAGE_LEN
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld (p504_length),bc
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld h,b
    ld l,c
    or a
    sbc hl,de
    jp nz,zx48_p504_format
    ld a,b
    cp $80
    jr c,zx48_p504_codec
    jp nz,zx48_p504_format
    ld a,c
    or a
    jp nz,zx48_p504_format

zx48_p504_codec:
    ld hl,(p504_header_ptr)
    ld bc,M48O_HDR_CODEC
    add hl,bc
    ld a,(hl)
    inc hl
    or (hl)
    jp nz,zx48_p504_format

    ; Reserved bytes are all zero.
    ld hl,(p504_header_ptr)
    ld bc,M48O_HDR_RESERVED
    add hl,bc
    ld b,M48O_RESERVED_SIZE
zx48_p504_reserved:
    ld a,(hl)
    or a
    jp nz,zx48_p504_format
    inc hl
    djnz zx48_p504_reserved

    ; Validate name[10], including NUL padding and . / .. rejection.
    ld hl,(p504_header_ptr)
    ld bc,M48O_HDR_NAME
    add hl,bc
    ld (p504_name_ptr),hl
    ld b,M48O_NAME_SIZE
    ld c,0
zx48_p504_name_loop:
    ld a,(hl)
    or a
    jr z,zx48_p504_name_padding
    call zx48_p504_name_char
    jp c,zx48_p504_format
    inc c
    inc hl
    djnz zx48_p504_name_loop
    jr zx48_p504_name_special
zx48_p504_name_padding:
    ld a,c
    or a
    jp z,zx48_p504_format
zx48_p504_name_pad_loop:
    ld a,(hl)
    or a
    jp nz,zx48_p504_format
    inc hl
    djnz zx48_p504_name_pad_loop
zx48_p504_name_special:
    ld a,c
    cp 1
    jr nz,zx48_p504_name_two
    ld hl,(p504_name_ptr)
    ld a,(hl)
    cp '.'
    jp z,zx48_p504_format
    jr zx48_p504_header_crc
zx48_p504_name_two:
    cp 2
    jr nz,zx48_p504_header_crc
    ld hl,(p504_name_ptr)
    ld a,(hl)
    cp '.'
    jr nz,zx48_p504_header_crc
    inc hl
    ld a,(hl)
    cp '.'
    jp z,zx48_p504_format

zx48_p504_header_crc:
    ld hl,(p504_header_ptr)
    ld bc,M48O_HDR_HEADER_CRC
    add hl,bc
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p504_header_crc),de
    xor a
    ld (hl),a
    dec hl
    ld (hl),a
    ld hl,(p504_header_ptr)
    ld bc,M48O_HDR_SIZE
    call zx48_crc16_ccitt_false
    push de
    ld hl,(p504_header_ptr)
    ld bc,M48O_HDR_HEADER_CRC
    add hl,bc
    ld de,(p504_header_crc)
    ld (hl),e
    inc hl
    ld (hl),d
    pop hl
    ld de,(p504_header_crc)
    or a
    sbc hl,de
    jp nz,zx48_p504_format

    ld hl,(p504_header_ptr)
    ld bc,M48O_HDR_PAYLOAD_CRC
    add hl,bc
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p504_expected_crc),de

    ; Header is now completely validated. Allocate final RAW storage only now.
    ld bc,(p504_length)
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (p504_alloc_ptr),hl
    ld a,h
    or l
    jr z,zx48_p504_allocated_zero
    ld a,1
    ld (p504_free_needed),a
zx48_p504_allocated_zero:
    ld hl,(p504_alloc_ptr)
    ld (p504_write_ptr),hl
    ld hl,(p504_length)
    ld (p504_remaining),hl
    ld hl,M48O_CRC16_INIT
    ld (p504_crc),hl

zx48_p504_chunk_loop:
    ld bc,(p504_remaining)
    ld a,b
    or c
    jr z,zx48_p504_complete
    call zx48_p503_prepare_chunk
    ld (p504_chunk_len),de
    ld ix,(p504_write_ptr)
    scf
    call zx48_tape_load_block
    jr c,zx48_p504_transport_fail

    ld hl,(p504_write_ptr)
    ld bc,(p504_chunk_len)
    call zx48_p504_crc_update

    ld hl,(p504_write_ptr)
    ld de,(p504_chunk_len)
    add hl,de
    ld (p504_write_ptr),hl
    ld hl,(p504_remaining)
    or a
    sbc hl,de
    ld (p504_remaining),hl
    jr zx48_p504_chunk_loop

zx48_p504_complete:
    ld hl,(p504_crc)
    ld de,(p504_expected_crc)
    or a
    sbc hl,de
    jr nz,zx48_p504_crc_fail
    ld a,1
    ld (p504_published),a
    xor a
    ld (p504_free_needed),a
    ld hl,(p504_alloc_ptr)
    ld bc,(p504_length)
    xor a
    or a
    ret

zx48_p504_transport_fail:
    ld (p504_error),a
    jr zx48_p504_cleanup
zx48_p504_crc_fail:
    ld a,E_IO
    ld (p504_error),a
zx48_p504_cleanup:
    ld a,(p504_free_needed)
    or a
    jr z,zx48_p504_cleanup_done
    ld hl,(p504_alloc_ptr)
    ld bc,(p504_length)
    bit 0,c
    jr z,zx48_p504_free_even
    inc bc
zx48_p504_free_even:
    call zx48_free
zx48_p504_cleanup_done:
    xor a
    ld (p504_published),a
    ld (p504_alloc_ptr),a
    ld (p504_alloc_ptr+1),a
    ld a,(p504_error)
    scf
    ret

zx48_p504_format:
    ld a,E_FORMAT
    scf
    ret

; HL=bytes, BC=count; update p504_crc incrementally without staging payload.
zx48_p504_crc_update:
    ld de,(p504_crc)
zx48_p504_crc_update_byte:
    ld a,b
    or c
    jr z,zx48_p504_crc_update_done
    ld a,(hl)
    inc hl
    xor d
    ld d,a
    dec bc
    push bc
    ld b,8
zx48_p504_crc_update_bit:
    sla e
    rl d
    jr nc,zx48_p504_crc_update_no_poly
    ld a,e
    xor $21
    ld e,a
    ld a,d
    xor $10
    ld d,a
zx48_p504_crc_update_no_poly:
    djnz zx48_p504_crc_update_bit
    pop bc
    jr zx48_p504_crc_update_byte
zx48_p504_crc_update_done:
    ld (p504_crc),de
    ret

zx48_p504_name_char:
    cp '0'
    jr c,zx48_p504_name_punct
    cp '9'+1
    jr c,zx48_p504_name_ok
    cp 'A'
    jr c,zx48_p504_name_punct
    cp 'Z'+1
    jr c,zx48_p504_name_ok
    cp 'a'
    jr c,zx48_p504_name_punct
    cp 'z'+1
    jr c,zx48_p504_name_ok
zx48_p504_name_punct:
    cp '_'
    jr z,zx48_p504_name_ok
    cp '-'
    jr z,zx48_p504_name_ok
    cp '.'
    jr z,zx48_p504_name_ok
    scf
    ret
zx48_p504_name_ok:
    or a
    ret

p504_header_ptr: dw 0
p504_name_ptr: dw 0
p504_header_crc: dw 0
p504_expected_crc: dw 0
p504_crc: dw 0
p504_length: dw 0
p504_alloc_ptr: dw 0
p504_write_ptr: dw 0
p504_remaining: dw 0
p504_chunk_len: dw 0
p504_type: db 0
p504_target: db 0
p504_published: db 0
p504_free_needed: db 0
p504_error: db 0
    ENDM

    MACRO EMIT_P505_PACKED_LOADER_ROUTINES
; HL -> private 32-byte M48O header already read from its separate ROM block.
; Validate the complete public PACKED contract before allocating. The physical
; ZXP1 stream lands directly in its final resident allocation. One exact
; 272-byte decoder state validates logical length and CRC to a discard sink.
zx48_p505_packed_load:
    ld (p505_header_ptr),hl
    xor a
    ld (p505_published),a
    ld (p505_alloc_ptr),a
    ld (p505_alloc_ptr+1),a
    ld (p505_decoder_ptr),a
    ld (p505_decoder_ptr+1),a
    ld (p505_physical_free),a
    ld (p505_decoder_free),a

    ; Magic/version/PACKED flag.
    ld hl,(p505_header_ptr)
    ld a,(hl)
    cp M48O_MAGIC_0
    jp nz,zx48_p505_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_1
    jp nz,zx48_p505_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_2
    jp nz,zx48_p505_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_3
    jp nz,zx48_p505_format
    inc hl
    ld a,(hl)
    cp M48O_VERSION
    jp nz,zx48_p505_format
    inc hl
    ld a,(hl)
    ld (p505_type),a
    cp M48O_TYPE_TXT
    jp c,zx48_p505_format
    cp M48O_TYPE_SYS+1
    jp nc,zx48_p505_format
    inc hl
    ld a,(hl)
    cp M48O_PACKED
    jp nz,zx48_p505_format
    inc hl
    ld a,(hl)
    ld (p505_target),a

    ; Public mutable placement mirrors the RAW loader contract.
    cp M48O_TARGET_BIN
    jr z,zx48_p505_place_bin
    cp M48O_TARGET_ETC
    jr z,zx48_p505_place_etc
    cp M48O_TARGET_USERHOME
    jr z,zx48_p505_place_ordinary
    cp M48O_TARGET_TMP
    jr z,zx48_p505_place_ordinary
    jp zx48_p505_format
zx48_p505_place_bin:
    ld a,(p505_type)
    cp M48O_TYPE_BIN
    jp nz,zx48_p505_format
    jr zx48_p505_lengths
zx48_p505_place_etc:
    ld a,(p505_type)
    cp M48O_TYPE_TXT
    jr z,zx48_p505_lengths
    cp M48O_TYPE_CFG
    jp nz,zx48_p505_format
    jr zx48_p505_lengths
zx48_p505_place_ordinary:
    ld a,(p505_type)
    cp M48O_TYPE_CFG+1
    jp nc,zx48_p505_format

zx48_p505_lengths:
    ld hl,(p505_header_ptr)
    ld bc,M48O_HDR_STORAGE_LEN
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld (p505_storage_length),bc
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p505_logical_length),de

    ; PACKED requires 0 < physical < logical and both lengths <=32768.
    ld a,b
    or c
    jp z,zx48_p505_format
    ld a,b
    cp $80
    jr c,zx48_p505_check_logical_bound
    jp nz,zx48_p505_format
    ld a,c
    or a
    jp nz,zx48_p505_format
zx48_p505_check_logical_bound:
    ld a,d
    cp $80
    jr c,zx48_p505_compare_lengths
    jp nz,zx48_p505_format
    ld a,e
    or a
    jp nz,zx48_p505_format
zx48_p505_compare_lengths:
    ld h,d
    ld l,e
    ld de,(p505_storage_length)
    or a
    sbc hl,de
    jp c,zx48_p505_format
    jp z,zx48_p505_format

    ; Codec is exactly ZXP1.
    ld hl,(p505_header_ptr)
    ld bc,M48O_HDR_CODEC
    add hl,bc
    ld a,(hl)
    cp low M48O_CODEC_ZXP1
    jp nz,zx48_p505_format
    inc hl
    ld a,(hl)
    cp high M48O_CODEC_ZXP1
    jp nz,zx48_p505_format

    ; Reserved bytes are zero.
    ld hl,(p505_header_ptr)
    ld bc,M48O_HDR_RESERVED
    add hl,bc
    ld b,M48O_RESERVED_SIZE
zx48_p505_reserved:
    ld a,(hl)
    or a
    jp nz,zx48_p505_format
    inc hl
    djnz zx48_p505_reserved

    ; Validate name[10], NUL padding, and reject . / ...
    ld hl,(p505_header_ptr)
    ld bc,M48O_HDR_NAME
    add hl,bc
    ld (p505_name_ptr),hl
    ld b,M48O_NAME_SIZE
    ld c,0
zx48_p505_name_loop:
    ld a,(hl)
    or a
    jr z,zx48_p505_name_padding
    call zx48_p505_name_char
    jp c,zx48_p505_format
    inc c
    inc hl
    djnz zx48_p505_name_loop
    jr zx48_p505_name_special
zx48_p505_name_padding:
    ld a,c
    or a
    jp z,zx48_p505_format
zx48_p505_name_pad_loop:
    ld a,(hl)
    or a
    jp nz,zx48_p505_format
    inc hl
    djnz zx48_p505_name_pad_loop
zx48_p505_name_special:
    ld a,c
    cp 1
    jr nz,zx48_p505_name_two
    ld hl,(p505_name_ptr)
    ld a,(hl)
    cp '.'
    jp z,zx48_p505_format
    jr zx48_p505_header_crc
zx48_p505_name_two:
    cp 2
    jr nz,zx48_p505_header_crc
    ld hl,(p505_name_ptr)
    ld a,(hl)
    cp '.'
    jr nz,zx48_p505_header_crc
    inc hl
    ld a,(hl)
    cp '.'
    jp z,zx48_p505_format

zx48_p505_header_crc:
    ld hl,(p505_header_ptr)
    ld bc,M48O_HDR_HEADER_CRC
    add hl,bc
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p505_header_crc),de
    xor a
    ld (hl),a
    dec hl
    ld (hl),a
    ld hl,(p505_header_ptr)
    ld bc,M48O_HDR_SIZE
    call zx48_crc16_ccitt_false
    push de
    ld hl,(p505_header_ptr)
    ld bc,M48O_HDR_HEADER_CRC
    add hl,bc
    ld de,(p505_header_crc)
    ld (hl),e
    inc hl
    ld (hl),d
    pop hl
    ld de,(p505_header_crc)
    or a
    sbc hl,de
    jp nz,zx48_p505_format

    ld hl,(p505_header_ptr)
    ld bc,M48O_HDR_PAYLOAD_CRC
    add hl,bc
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p505_expected_crc),de

    ; Final packed allocation first, then one exact 272-byte decoder state.
    ld bc,(p505_storage_length)
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (p505_alloc_ptr),hl
    ld a,1
    ld (p505_physical_free),a

    ld bc,P417_STATE_SIZE
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    jr nc,zx48_p505_decoder_allocated
    ld (p505_error),a
    jp zx48_p505_cleanup
zx48_p505_decoder_allocated:
    ld (p505_decoder_ptr),hl
    ld a,1
    ld (p505_decoder_free),a
    call zx48_p417_state_init

    ld hl,(p505_alloc_ptr)
    ld (p505_write_ptr),hl
    ld hl,(p505_storage_length)
    ld (p505_remaining),hl

zx48_p505_chunk_loop:
    ld bc,(p505_remaining)
    ld a,b
    or c
    jr z,zx48_p505_validate
    call zx48_p503_prepare_chunk
    ld (p505_chunk_len),de
    ld ix,(p505_write_ptr)
    scf
    call zx48_tape_load_block
    jr c,zx48_p505_transport_fail
    ld hl,(p505_write_ptr)
    ld de,(p505_chunk_len)
    add hl,de
    ld (p505_write_ptr),hl
    ld hl,(p505_remaining)
    or a
    sbc hl,de
    ld (p505_remaining),hl
    jr zx48_p505_chunk_loop

zx48_p505_validate:
    ld hl,(p505_alloc_ptr)
    ld bc,(p505_storage_length)
    ld de,(p505_logical_length)
    ld ix,(p505_decoder_ptr)
    call zx48_p505_validate_zxp1
    jr c,zx48_p505_decoder_fail
    ld hl,(p416_crc)
    ld de,(p505_expected_crc)
    or a
    sbc hl,de
    jr nz,zx48_p505_crc_fail

    ; Decoder state is temporary and must not survive publication.
    ld hl,(p505_decoder_ptr)
    ld bc,P417_STATE_SIZE
    call zx48_free
    xor a
    ld (p505_decoder_free),a
    ld (p505_decoder_ptr),a
    ld (p505_decoder_ptr+1),a
    ld a,1
    ld (p505_published),a
    xor a
    ld (p505_physical_free),a
    ld hl,(p505_alloc_ptr)
    ld bc,(p505_storage_length)
    ld de,(p505_logical_length)
    xor a
    or a
    ret

zx48_p505_transport_fail:
    ld (p505_error),a
    jr zx48_p505_cleanup
zx48_p505_decoder_fail:
    ld (p505_error),a
    jr zx48_p505_cleanup
zx48_p505_crc_fail:
    ld a,E_IO
    ld (p505_error),a

zx48_p505_cleanup:
    ld a,(p505_decoder_free)
    or a
    jr z,zx48_p505_cleanup_physical
    ld hl,(p505_decoder_ptr)
    ld bc,P417_STATE_SIZE
    call zx48_free
zx48_p505_cleanup_physical:
    ld a,(p505_physical_free)
    or a
    jr z,zx48_p505_cleanup_done
    ld hl,(p505_alloc_ptr)
    ld bc,(p505_storage_length)
    bit 0,c
    jr z,zx48_p505_free_physical
    inc bc
zx48_p505_free_physical:
    call zx48_free
zx48_p505_cleanup_done:
    xor a
    ld (p505_published),a
    ld (p505_alloc_ptr),a
    ld (p505_alloc_ptr+1),a
    ld (p505_decoder_ptr),a
    ld (p505_decoder_ptr+1),a
    ld (p505_physical_free),a
    ld (p505_decoder_free),a
    ld a,(p505_error)
    scf
    ret

zx48_p505_format:
    ld a,E_FORMAT
    scf
    ret

zx48_p505_name_char:
    cp '0'
    jr c,zx48_p505_name_punct
    cp '9'+1
    jr c,zx48_p505_name_ok
    cp 'A'
    jr c,zx48_p505_name_punct
    cp 'Z'+1
    jr c,zx48_p505_name_ok
    cp 'a'
    jr c,zx48_p505_name_punct
    cp 'z'+1
    jr c,zx48_p505_name_ok
zx48_p505_name_punct:
    cp '_'
    jr z,zx48_p505_name_ok
    cp '-'
    jr z,zx48_p505_name_ok
    cp '.'
    jr z,zx48_p505_name_ok
    scf
    ret
zx48_p505_name_ok:
    or a
    ret

p505_header_ptr: dw 0
p505_name_ptr: dw 0
p505_header_crc: dw 0
p505_expected_crc: dw 0
p505_storage_length: dw 0
p505_logical_length: dw 0
p505_alloc_ptr: dw 0
p505_decoder_ptr: dw 0
p505_write_ptr: dw 0
p505_remaining: dw 0
p505_chunk_len: dw 0
p505_type: db 0
p505_target: db 0
p505_published: db 0
p505_physical_free: db 0
p505_decoder_free: db 0
p505_error: db 0
    ENDM

    MACRO EMIT_P506_PINNED_SYSTEM_ROUTINES
; HL -> validated candidate M48O header, IX -> complete physical source bytes.
; font4x8 and bincat may arrive RAW or PACKED; their final published form is
; always one pinned RAW allocation. The zero-length crontab bootstrap object is
; accepted only as RAW and never allocates payload storage.
zx48_p506_boot_resource:
    ld (p506_header_ptr),hl
    ld (p506_physical_ptr),ix
    xor a
    ld (p506_alloc_ptr),a
    ld (p506_alloc_ptr+1),a
    ld (p506_decoder_ptr),a
    ld (p506_decoder_ptr+1),a
    ld (p506_alloc_live),a
    ld (p506_decoder_live),a
    ld (p506_kind),a

    ; Exact M48O magic/version.
    ld hl,(p506_header_ptr)
    ld a,(hl)
    cp M48O_MAGIC_0
    jp nz,zx48_p506_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_1
    jp nz,zx48_p506_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_2
    jp nz,zx48_p506_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_3
    jp nz,zx48_p506_format
    inc hl
    ld a,(hl)
    cp M48O_VERSION
    jp nz,zx48_p506_format

    ; Classify exact bootstrap resource by type/target/name.
    inc hl
    ld a,(hl)
    ld (p506_type),a
    inc hl
    ld a,(hl)
    ld (p506_flags),a
    inc hl
    ld a,(hl)
    ld (p506_target),a

    ld a,(p506_type)
    cp M48O_TYPE_FNT
    jr z,zx48_p506_maybe_font
    cp M48O_TYPE_SYS
    jr z,zx48_p506_maybe_bincat
    cp M48O_TYPE_CFG
    jr z,zx48_p506_maybe_crontab
    jp zx48_p506_format

zx48_p506_maybe_font:
    ld a,(p506_target)
    cp M48O_TARGET_SYSTEM
    jp nz,zx48_p506_format
    ld hl,p506_name_font4x8
    ld a,1
    jr zx48_p506_match_name
zx48_p506_maybe_bincat:
    ld a,(p506_target)
    cp M48O_TARGET_SYSTEM
    jp nz,zx48_p506_format
    ld hl,p506_name_bincat
    ld a,2
    jr zx48_p506_match_name
zx48_p506_maybe_crontab:
    ld a,(p506_target)
    cp M48O_TARGET_ETC
    jp nz,zx48_p506_format
    ld hl,p506_name_crontab
    ld a,3
zx48_p506_match_name:
    ld (p506_kind),a
    ld de,(p506_header_ptr)
    ld bc,M48O_HDR_NAME
    ex de,hl
    add hl,bc
    ex de,hl
    ld b,M48O_NAME_SIZE
zx48_p506_name_loop:
    ld a,(de)
    cp (hl)
    jp nz,zx48_p506_format
    inc de
    inc hl
    djnz zx48_p506_name_loop

    ; Capture physical/logical lengths.
    ld hl,(p506_header_ptr)
    ld bc,M48O_HDR_STORAGE_LEN
    add hl,bc
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld (p506_storage_length),bc
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p506_logical_length),de

    ; Reserved bytes must be zero.
    ld hl,(p506_header_ptr)
    ld bc,M48O_HDR_RESERVED
    add hl,bc
    ld b,M48O_RESERVED_SIZE
zx48_p506_reserved:
    ld a,(hl)
    or a
    jp nz,zx48_p506_format
    inc hl
    djnz zx48_p506_reserved

    ; Header CRC is computed with its own field zeroed, then restored.
    ld hl,(p506_header_ptr)
    ld bc,M48O_HDR_HEADER_CRC
    add hl,bc
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p506_header_crc),de
    xor a
    ld (hl),a
    dec hl
    ld (hl),a
    ld hl,(p506_header_ptr)
    ld bc,M48O_HDR_SIZE
    call zx48_crc16_ccitt_false
    push de
    ld hl,(p506_header_ptr)
    ld bc,M48O_HDR_HEADER_CRC
    add hl,bc
    ld de,(p506_header_crc)
    ld (hl),e
    inc hl
    ld (hl),d
    pop hl
    ld de,(p506_header_crc)
    or a
    sbc hl,de
    jp nz,zx48_p506_format

    ld hl,(p506_header_ptr)
    ld bc,M48O_HDR_PAYLOAD_CRC
    add hl,bc
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p506_expected_crc),de

    ld a,(p506_kind)
    cp 3
    jp z,zx48_p506_crontab

    ; System resources require exact logical sizes.
    cp 1
    jr nz,zx48_p506_bincat_size
    ld hl,(p506_logical_length)
    ld de,392
    or a
    sbc hl,de
    jp nz,zx48_p506_format
    jr zx48_p506_representation
zx48_p506_bincat_size:
    ld hl,(p506_logical_length)
    ld de,488
    or a
    sbc hl,de
    jp nz,zx48_p506_format

zx48_p506_representation:
    ld a,(p506_flags)
    or a
    jr z,zx48_p506_raw
    cp M48O_PACKED
    jp nz,zx48_p506_format

    ; PACKED: codec ZXP1 and 0 < physical < logical.
    ld hl,(p506_header_ptr)
    ld bc,M48O_HDR_CODEC
    add hl,bc
    ld a,(hl)
    cp low M48O_CODEC_ZXP1
    jp nz,zx48_p506_format
    inc hl
    ld a,(hl)
    cp high M48O_CODEC_ZXP1
    jp nz,zx48_p506_format
    ld hl,(p506_storage_length)
    ld a,h
    or l
    jp z,zx48_p506_format
    ld de,(p506_logical_length)
    or a
    sbc hl,de
    jp nc,zx48_p506_format
    jr zx48_p506_allocate

zx48_p506_raw:
    ; RAW: codec zero and physical length equals logical length.
    ld hl,(p506_header_ptr)
    ld bc,M48O_HDR_CODEC
    add hl,bc
    ld a,(hl)
    inc hl
    or (hl)
    jp nz,zx48_p506_format
    ld hl,(p506_storage_length)
    ld de,(p506_logical_length)
    or a
    sbc hl,de
    jp nz,zx48_p506_format

zx48_p506_allocate:
    ld bc,(p506_logical_length)
    ld a,(p506_kind)
    cp 1
    ld a,ALLOC_FAST_REQUIRED
    jr z,zx48_p506_do_alloc
    ld a,ALLOC_COLD_PREFERRED
zx48_p506_do_alloc:
    call zx48_alloc
    ret c
    ld (p506_alloc_ptr),hl
    ld a,1
    ld (p506_alloc_live),a

    ld a,(p506_flags)
    or a
    jr nz,zx48_p506_decode_packed

    ; RAW bytes copy directly into final pinned allocation.
    push ix
    pop hl
    ld de,(p506_alloc_ptr)
    ld bc,(p506_logical_length)
    ldir
    ld hl,(p506_alloc_ptr)
    ld bc,(p506_logical_length)
    call zx48_crc16_ccitt_false
    ld (p506_actual_crc),de
    jr zx48_p506_crc_check

zx48_p506_decode_packed:
    ; One exact 272-byte streaming decoder state. Logical bytes are emitted
    ; straight into the final pinned RAW allocation; no second RAW copy exists.
    ld bc,P417_STATE_SIZE
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    jr nc,zx48_p506_decoder_allocated
    ld (p506_error),a
    jp zx48_p506_cleanup
zx48_p506_decoder_allocated:
    ld (p506_decoder_ptr),hl
    ld a,1
    ld (p506_decoder_live),a
    push hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,P417_STATE_SIZE-1
    ldir
    pop hl

    ld a,1
    ld (p416_crc_enable),a
    ld hl,(p506_physical_ptr)
    ld bc,(p506_storage_length)
    ld de,(p506_logical_length)
    ld ix,(p506_decoder_ptr)
    ld iy,(p506_alloc_ptr)
    ld a,P416_SINK_CALLER_STREAM
    call zx48_p416_decode
    jp c,zx48_p506_decode_fail
    ld hl,(p416_crc)
    ld (p506_actual_crc),hl

zx48_p506_crc_check:
    ld hl,(p506_actual_crc)
    ld de,(p506_expected_crc)
    or a
    sbc hl,de
    jp nz,zx48_p506_io_fail

    ld a,(p506_kind)
    cp 1
    jr z,zx48_p506_validate_font
    jr zx48_p506_validate_bincat

zx48_p506_validate_font:
    ld hl,(p506_alloc_ptr)
    ld a,(hl)
    cp 'F'
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp '4'
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp 'X'
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp '8'
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp 1
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp $20
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp 96
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    or a
    jp nz,zx48_p506_format_cleanup
    jr zx48_p506_publish

zx48_p506_validate_bincat:
    ld hl,(p506_alloc_ptr)
    ld a,(hl)
    cp 'B'
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp 'C'
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp 'A'
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp 'T'
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp 1
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp 40
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    or a
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    or a
    jp nz,zx48_p506_format_cleanup

    ; Every BCAT v1 entry has BIN type and tape-backed flag=1.
    ld hl,(p506_alloc_ptr)
    ld de,18
    add hl,de
    ld b,40
zx48_p506_bincat_entry:
    ld a,(hl)
    cp M48O_TYPE_BIN
    jp nz,zx48_p506_format_cleanup
    inc hl
    ld a,(hl)
    cp 1
    jp nz,zx48_p506_format_cleanup
    ld de,11
    add hl,de
    djnz zx48_p506_bincat_entry

zx48_p506_publish:
    call zx48_p506_release_decoder
    jp c,zx48_p506_decode_fail
    ld bc,(p506_logical_length)
    call zx48_memory_pin_bytes
    ld a,(p506_kind)
    cp 1
    jr nz,zx48_p506_publish_bincat
    ld hl,(p506_alloc_ptr)
    ld (p506_font_ptr),hl
    ld a,1
    ld (p506_font_ready),a
    jr zx48_p506_publish_done
zx48_p506_publish_bincat:
    ld hl,(p506_alloc_ptr)
    ld (p506_bincat_ptr),hl
    ld a,1
    ld (p506_bincat_ready),a
zx48_p506_publish_done:
    xor a
    ld (p506_alloc_live),a
    ld hl,(p506_alloc_ptr)
    ld bc,(p506_logical_length)
    xor a
    or a
    ret

zx48_p506_crontab:
    ; The official zero-length crontab is always RAW.
    ld a,(p506_flags)
    or a
    jp nz,zx48_p506_format
    ld hl,(p506_storage_length)
    ld a,h
    or l
    jp nz,zx48_p506_format
    ld hl,(p506_logical_length)
    ld a,h
    or l
    jp nz,zx48_p506_format
    ld hl,(p506_header_ptr)
    ld bc,M48O_HDR_CODEC
    add hl,bc
    ld a,(hl)
    inc hl
    or (hl)
    jp nz,zx48_p506_format
    ld hl,(p506_expected_crc)
    ld de,M48O_CRC16_INIT
    or a
    sbc hl,de
    jp nz,zx48_p506_format
    xor a
    or a
    ret

zx48_p506_decode_fail:
    ld (p506_error),a
    jr zx48_p506_cleanup
zx48_p506_io_fail:
    ld a,E_IO
    ld (p506_error),a
    jr zx48_p506_cleanup
zx48_p506_format_cleanup:
    ld a,E_FORMAT
    ld (p506_error),a
zx48_p506_cleanup:
    call zx48_p506_release_decoder
    ld a,(p506_alloc_live)
    or a
    jr z,zx48_p506_cleanup_done
    ld hl,(p506_alloc_ptr)
    ld bc,(p506_logical_length)
    bit 0,c
    jr z,zx48_p506_free
    inc bc
zx48_p506_free:
    call zx48_free
zx48_p506_cleanup_done:
    xor a
    ld (p506_alloc_live),a
    ld (p506_alloc_ptr),a
    ld (p506_alloc_ptr+1),a
    ld (p506_decoder_ptr),a
    ld (p506_decoder_ptr+1),a
    ld (p506_decoder_live),a
    ld a,(p506_error)
    scf
    ret

zx48_p506_release_decoder:
    ld a,(p506_decoder_live)
    or a
    ret z
    ld hl,(p506_decoder_ptr)
    ld bc,P417_STATE_SIZE
    call zx48_free
    ret c
    xor a
    ld (p506_decoder_live),a
    ld (p506_decoder_ptr),a
    ld (p506_decoder_ptr+1),a
    ret

zx48_p506_format:
    ld a,E_FORMAT
    scf
    ret

p506_name_font4x8: db "font4x8",0,0,0
p506_name_bincat:  db "bincat",0,0,0,0
p506_name_crontab: db "crontab",0,0,0
p506_header_ptr: dw 0
p506_physical_ptr: dw 0
p506_header_crc: dw 0
p506_expected_crc: dw 0
p506_actual_crc: dw 0
p506_storage_length: dw 0
p506_logical_length: dw 0
p506_alloc_ptr: dw 0
p506_decoder_ptr: dw 0
p506_font_ptr: dw 0
p506_bincat_ptr: dw 0
p506_type: db 0
p506_flags: db 0
p506_target: db 0
p506_kind: db 0
p506_font_ready: db 0
p506_bincat_ready: db 0
p506_alloc_live: db 0
p506_decoder_live: db 0
p506_error: db 0
    ENDM

    MACRO EMIT_P507_RAW_SAVE_ROUTINES
; IX=validated mutable RAW object record. Build the complete M48O representation
; before acquiring the global cassette critical section.
zx48_p507_save_record:
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jp nz,zx48_p507_notsup
    ld a,(ix+OBJ_RESERVED_BYTE)
    or a
    jp nz,zx48_p507_format
    ld a,(ix+OBJ_DIR_ID)
    ld (p507_target),a
    ld b,(ix+OBJ_TYPE_ID)
    ld a,b
    ld (p507_type),a
    call zx48_object_public_type_allowed
    ret c

    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld e,(ix+OBJ_STORAGE_LENGTH)
    ld d,(ix+OBJ_STORAGE_LENGTH+1)
    push hl
    or a
    sbc hl,de
    pop hl
    jp nz,zx48_p507_format
    bit 7,h
    jp nz,zx48_p507_format
    ld (p507_length),hl
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p507_payload_ptr),hl
    ld de,(p507_length)
    ld a,d
    or e
    jr z,zx48_p507_payload_ptr_ok
    ld a,h
    or l
    jp z,zx48_p507_format
zx48_p507_payload_ptr_ok:

    xor a
    ld hl,p507_header
    ld de,p507_header+1
    ld bc,M48O_HDR_SIZE-1
    ld (hl),a
    ldir
    ld hl,p507_header
    ld (hl),M48O_MAGIC_0
    inc hl
    ld (hl),M48O_MAGIC_1
    inc hl
    ld (hl),M48O_MAGIC_2
    inc hl
    ld (hl),M48O_MAGIC_3
    inc hl
    ld (hl),M48O_VERSION
    inc hl
    ld a,(p507_type)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld a,(p507_target)
    ld (hl),a

    ld hl,p507_header+M48O_HDR_STORAGE_LEN
    ld de,(p507_length)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld (hl),e
    inc hl
    ld (hl),d

    ld hl,(p507_payload_ptr)
    ld bc,(p507_length)
    call zx48_crc16_ccitt_false
    ld hl,p507_header+M48O_HDR_PAYLOAD_CRC
    ld (hl),e
    inc hl
    ld (hl),d

    push ix
    pop hl
    ld de,p507_header+M48O_HDR_NAME
    ld bc,M48O_NAME_SIZE
    ldir

    ld hl,p507_header
    ld bc,M48O_HDR_SIZE
    call zx48_crc16_ccitt_false
    ld hl,p507_header+M48O_HDR_HEADER_CRC
    ld (hl),e
    inc hl
    ld (hl),d

    ; Foreground RECORD consent is obtained before lock/tape motion.
    call zx48_p507_prompt_record
    ret c
    call zx48_p507_lock_acquire
    ret c

    ld ix,p507_header
    ld de,M48O_HDR_SIZE
    ld a,M48O_ROM_DATA_FLAG
    call zx48_tape_save_block
    jp c,zx48_p507_release_error

    ld hl,(p507_payload_ptr)
    ld (p507_write_ptr),hl
    ld hl,(p507_length)
    ld (p507_remaining),hl
zx48_p507_chunk_loop:
    ld bc,(p507_remaining)
    ld a,b
    or c
    jr z,zx48_p507_success
    call zx48_p503_prepare_chunk
    ld (p507_chunk_len),de
    ld ix,(p507_write_ptr)
    ld a,M48O_ROM_DATA_FLAG
    call zx48_tape_save_block
    jp c,zx48_p507_release_error
    ld hl,(p507_write_ptr)
    ld de,(p507_chunk_len)
    add hl,de
    ld (p507_write_ptr),hl
    ld hl,(p507_remaining)
    or a
    sbc hl,de
    ld (p507_remaining),hl
    jr zx48_p507_chunk_loop

zx48_p507_success:
    call zx48_p507_lock_release
    ld hl,0
    xor a
    or a
    ret
zx48_p507_release_error:
    ld (p507_error),a
    call zx48_p507_lock_release
    ld a,(p507_error)
    scf
    ret
zx48_p507_notsup:
    ld a,E_NOTSUP
    scf
    ret
zx48_p507_format:
    ld a,E_FORMAT
    scf
    ret

zx48_p507_lock_acquire:
    ld a,(p507_tape_lock)
    or a
    jr nz,zx48_p507_busy
    inc a
    ld (p507_tape_lock),a
    xor a
    or a
    ret
zx48_p507_busy:
    ld a,E_BUSY
    scf
    ret
zx48_p507_lock_release:
    xor a
    ld (p507_tape_lock),a
    ret

; P5.13 replaces this foreground consent hook with visible prompt/input logic.
zx48_p507_prompt_record:
    xor a
    or a
    ret

p507_header: defs M48O_HDR_SIZE,0
p507_payload_ptr: dw 0
p507_length: dw 0
p507_write_ptr: dw 0
p507_remaining: dw 0
p507_chunk_len: dw 0
p507_target: db 0
p507_type: db 0
p507_tape_lock: db 0
p507_error: db 0
    ENDM

    MACRO EMIT_P508_STREAM_SAVE_ROUTINES
; IX=resident object. PACKED objects are validated with one 272-byte state before
; any tape motion. RAW objects attempt the exact deterministic P4.20 pass 1 and
; stream pass 2 through one separate 512-byte tape chunk buffer.
zx48_p508_save_record:
    ld (p508_object_ptr),ix
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jp nz,zx48_p508_save_packed
    jp zx48_p508_try_raw

zx48_p508_try_raw:
    ld ix,(p508_object_ptr)
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (p508_logical),hl
    ld a,h
    or l
    jp z,zx48_p507_save_record
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p508_source),hl

    ; Deterministic measure pass using exactly one 512-byte table.
    ld (p420_input_base),hl
    ld hl,(p508_logical)
    ld (p420_input_len),hl
    xor a
    ld (p420_mode),a
    ld (p420_background),a
    call zx48_p420_workspace_begin
    jp c,zx48_p507_save_record
    call zx48_p420_run_pass
    jp c,zx48_p508_measure_error
    ld hl,(p420_encoded_len)
    ld (p508_physical),hl
    call zx48_p420_workspace_end
    jp c,zx48_p508_free_error
    ld hl,(p508_physical)
    ld de,(p508_logical)
    or a
    sbc hl,de
    jp nc,zx48_p507_save_record

    ; Logical CRC comes from the unchanged RAW source.
    ld hl,(p508_source)
    ld bc,(p508_logical)
    call zx48_crc16_ccitt_false
    ld (p508_crc),de

    ; Output chunk plus pass-2 table must both exist before first tape block.
    ld bc,512
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    jp c,zx48_p507_save_record
    ld (p508_chunk_ptr),hl
    call zx48_p420_workspace_begin
    jr nc,zx48_p508_raw_ready
    ld hl,(p508_chunk_ptr)
    ld bc,512
    call zx48_free
    jp zx48_p507_save_record

zx48_p508_raw_ready:
    call zx48_p508_build_packed_header
    call zx48_p507_prompt_record
    jp c,zx48_p508_raw_preoutput_error
    call zx48_p507_lock_acquire
    jp c,zx48_p508_raw_preoutput_error
    ld ix,p507_header
    ld de,M48O_HDR_SIZE
    ld a,M48O_ROM_DATA_FLAG
    call zx48_tape_save_block
    jp c,zx48_p508_raw_tape_error

    xor a
    ld (p508_chunk_fill),a
    ld (p508_chunk_fill+1),a
    ld hl,zx48_p508_stream_byte
    ld (p420_stream_callback),hl
    ld hl,(p508_source)
    ld (p420_input_base),hl
    ld hl,(p508_logical)
    ld (p420_input_len),hl
    ld a,2
    ld (p420_mode),a
    call zx48_p420_run_pass
    jp c,zx48_p508_raw_tape_error
    ld hl,(p420_encoded_len)
    ld de,(p508_physical)
    or a
    sbc hl,de
    jp nz,zx48_p508_raw_format_error
    call zx48_p508_flush_partial
    jp c,zx48_p508_raw_tape_error
    call zx48_p507_lock_release
    call zx48_p508_raw_free
    ld hl,0
    xor a
    or a
    ret

zx48_p508_stream_byte:
    ld (p508_stream_byte),a
    ld hl,(p508_chunk_ptr)
    ld de,(p508_chunk_fill)
    add hl,de
    ld a,(p508_stream_byte)
    ld (hl),a
    ld hl,(p508_chunk_fill)
    inc hl
    ld (p508_chunk_fill),hl
    ld de,512
    or a
    sbc hl,de
    jr nz,zx48_p508_stream_ok
    ld ix,(p508_chunk_ptr)
    ld de,512
    ld a,M48O_ROM_DATA_FLAG
    call zx48_tape_save_block
    ret c
    xor a
    ld (p508_chunk_fill),a
    ld (p508_chunk_fill+1),a
zx48_p508_stream_ok:
    xor a
    or a
    ret

zx48_p508_flush_partial:
    ld de,(p508_chunk_fill)
    ld a,d
    or e
    ret z
    ld ix,(p508_chunk_ptr)
    ld a,M48O_ROM_DATA_FLAG
    call zx48_tape_save_block
    ret

zx48_p508_measure_error:
    ld (p508_error),a
    call zx48_p420_workspace_end
    ld a,(p508_error)
    scf
    ret
zx48_p508_raw_format_error:
    ld a,E_FORMAT
    ld (p508_error),a
    jr zx48_p508_raw_tape_cleanup
zx48_p508_raw_tape_error:
    ld (p508_error),a
zx48_p508_raw_tape_cleanup:
    call zx48_p507_lock_release
zx48_p508_raw_preoutput_error:
    ld (p508_error),a
    call zx48_p508_raw_free
    ld a,(p508_error)
    scf
    ret
zx48_p508_raw_free:
    call zx48_p420_workspace_end
    ld hl,(p508_chunk_ptr)
    ld bc,512
    jp zx48_free

zx48_p508_save_packed:
    ld ix,(p508_object_ptr)
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (p508_logical),hl
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld (p508_physical),bc
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p508_source),hl

    ; Exact one-state validation before any output.
    ld bc,P417_STATE_SIZE
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    ret c
    ld (p508_decoder),hl
    push hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,P417_STATE_SIZE-1
    ldir
    pop ix
    ld hl,(p508_source)
    ld bc,(p508_physical)
    ld de,(p508_logical)
    ld iy,0
    ld a,1
    ld (p416_crc_enable),a
    ld a,P416_SINK_DISCARD
    call zx48_p416_decode
    jr c,zx48_p508_packed_decode_fail
    ld hl,(p416_crc)
    ld (p508_crc),hl
    ld hl,(p508_decoder)
    ld bc,P417_STATE_SIZE
    call zx48_free
    jp c,zx48_p508_free_error

    call zx48_p508_build_packed_header
    call zx48_p507_prompt_record
    ret c
    call zx48_p507_lock_acquire
    ret c
    ld ix,p507_header
    ld de,M48O_HDR_SIZE
    ld a,M48O_ROM_DATA_FLAG
    call zx48_tape_save_block
    jp c,zx48_p508_packed_tape_error
    ld hl,(p508_source)
    ld (p508_read_ptr),hl
    ld hl,(p508_physical)
    ld (p508_remaining),hl
zx48_p508_packed_loop:
    ld bc,(p508_remaining)
    ld a,b
    or c
    jr z,zx48_p508_packed_success
    call zx48_p503_prepare_chunk
    ld (p508_chunk_len),de
    ld ix,(p508_read_ptr)
    ld a,M48O_ROM_DATA_FLAG
    call zx48_tape_save_block
    jp c,zx48_p508_packed_tape_error
    ld hl,(p508_read_ptr)
    ld de,(p508_chunk_len)
    add hl,de
    ld (p508_read_ptr),hl
    ld hl,(p508_remaining)
    or a
    sbc hl,de
    ld (p508_remaining),hl
    jr zx48_p508_packed_loop
zx48_p508_packed_success:
    call zx48_p507_lock_release
    ld hl,0
    xor a
    or a
    ret
zx48_p508_packed_tape_error:
    ld (p508_error),a
    call zx48_p507_lock_release
    ld a,(p508_error)
    scf
    ret
zx48_p508_packed_decode_fail:
    ld (p508_error),a
    ld hl,(p508_decoder)
    ld bc,P417_STATE_SIZE
    call zx48_free
    ld a,(p508_error)
    scf
    ret
zx48_p508_free_error:
    ld a,E_IO
    scf
    ret

; Build PACKED M48O header from the resident record and measured/validated fields.
zx48_p508_build_packed_header:
    xor a
    ld hl,p507_header
    ld de,p507_header+1
    ld bc,M48O_HDR_SIZE-1
    ld (hl),a
    ldir
    ld hl,p507_header
    ld (hl),M48O_MAGIC_0
    inc hl
    ld (hl),M48O_MAGIC_1
    inc hl
    ld (hl),M48O_MAGIC_2
    inc hl
    ld (hl),M48O_MAGIC_3
    inc hl
    ld (hl),M48O_VERSION
    inc hl
    ld ix,(p508_object_ptr)
    ld a,(ix+OBJ_TYPE_ID)
    ld (hl),a
    inc hl
    ld (hl),M48O_PACKED
    inc hl
    ld a,(ix+OBJ_DIR_ID)
    ld (hl),a
    ld hl,p507_header+M48O_HDR_STORAGE_LEN
    ld de,(p508_physical)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(p508_logical)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld (hl),low M48O_CODEC_ZXP1
    inc hl
    ld (hl),high M48O_CODEC_ZXP1
    inc hl
    ld de,(p508_crc)
    ld (hl),e
    inc hl
    ld (hl),d
    push ix
    pop hl
    ld de,p507_header+M48O_HDR_NAME
    ld bc,M48O_NAME_SIZE
    ldir
    ld hl,p507_header
    ld bc,M48O_HDR_SIZE
    call zx48_crc16_ccitt_false
    ld hl,p507_header+M48O_HDR_HEADER_CRC
    ld (hl),e
    inc hl
    ld (hl),d
    ret

p508_object_ptr: dw 0
p508_source: dw 0
p508_logical: dw 0
p508_physical: dw 0
p508_crc: dw 0
p508_chunk_ptr: dw 0
p508_chunk_fill: dw 0
p508_decoder: dw 0
p508_read_ptr: dw 0
p508_remaining: dw 0
p508_chunk_len: dw 0
p508_stream_byte: db 0
p508_error: db 0
    ENDM

    MACRO EMIT_P509_EXPLICIT_LOAD_ROUTINES
; HL=NUL-terminated requested path. Resolve exact case first; then serialize one
; forward tape search. The old namespace entry is untouched until the complete
; incoming representation has passed header/payload/codec/logical-CRC validation.
zx48_p509_load_path:
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jp nz,zx48_p509_inval
    ld a,(path_dir)
    ld (p509_requested_dir),a
    ld hl,path_name
    ld de,p509_requested_name
    ld bc,M48O_NAME_SIZE
    ldir

    call zx48_p509_prompt_play
    ret c
    call zx48_p507_lock_acquire
    ret c

zx48_p509_scan:
    ld ix,p509_header
    ld de,M48O_HDR_SIZE
    ld a,M48O_ROM_DATA_FLAG
    scf
    call zx48_tape_load_block
    jp c,zx48_p509_locked_error
    call zx48_p509_header_basic
    jp c,zx48_p509_locked_error
    call zx48_p509_match_requested
    jr z,zx48_p509_match

    call zx48_p509_skip_payload
    jp c,zx48_p509_locked_error
    jr zx48_p509_scan

zx48_p509_match:
    ; Matching placement/type must be public mutable and exact.
    ld a,(p509_header+M48O_HDR_DIRECTORY)
    ld b,(p509_header+M48O_HDR_TYPE)
    call zx48_object_public_type_allowed
    jp c,zx48_p509_locked_error

    ld a,(p509_header+M48O_HDR_FLAGS)
    or a
    jr z,zx48_p509_load_raw
    cp M48O_PACKED
    jp nz,zx48_p509_locked_format
    ld hl,p509_header
    call zx48_p505_packed_load
    jr zx48_p509_loaded
zx48_p509_load_raw:
    ld hl,p509_header
    call zx48_p504_raw_load
zx48_p509_loaded:
    jp c,zx48_p509_locked_error
    ld (p509_new_ptr),hl
    ld (p509_new_storage),bc
    ld (p509_new_logical),de
    call zx48_p507_lock_release
    jp zx48_p509_commit

zx48_p509_header_basic:
    ld hl,p509_header
    ld a,(hl)
    cp M48O_MAGIC_0
    jp nz,zx48_p509_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_1
    jp nz,zx48_p509_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_2
    jp nz,zx48_p509_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_3
    jp nz,zx48_p509_format
    inc hl
    ld a,(hl)
    cp M48O_VERSION
    jp nz,zx48_p509_format
    ld a,(p509_header+M48O_HDR_FLAGS)
    and $fe
    jp nz,zx48_p509_format
    ld hl,(p509_header+M48O_HDR_STORAGE_LEN)
    bit 7,h
    jp nz,zx48_p509_format
    xor a
    or a
    ret

zx48_p509_match_requested:
    ld a,(p509_header+M48O_HDR_DIRECTORY)
    ld b,a
    ld a,(p509_requested_dir)
    cp b
    ret nz
    ld hl,p509_header+M48O_HDR_NAME
    ld de,p509_requested_name
    ld b,M48O_NAME_SIZE
zx48_p509_name_loop:
    ld a,(de)
    cp (hl)
    ret nz
    inc de
    inc hl
    djnz zx48_p509_name_loop
    xor a
    ret

; Consume a nonmatching object's exact physical block count through one private
; <=512-byte COLD scratch allocation; namespace remains untouched.
zx48_p509_skip_payload:
    ld hl,(p509_header+M48O_HDR_STORAGE_LEN)
    ld (p509_skip_remaining),hl
    ld a,h
    or l
    ret z
    ld bc,M48O_CHUNK_SIZE
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    ret c
    ld (p509_skip_ptr),hl
zx48_p509_skip_loop:
    ld bc,(p509_skip_remaining)
    ld a,b
    or c
    jr z,zx48_p509_skip_done
    call zx48_p503_prepare_chunk
    ld (p509_skip_chunk),de
    ld ix,(p509_skip_ptr)
    ld a,M48O_ROM_DATA_FLAG
    scf
    call zx48_tape_load_block
    jr c,zx48_p509_skip_fail
    ld hl,(p509_skip_remaining)
    ld de,(p509_skip_chunk)
    or a
    sbc hl,de
    ld (p509_skip_remaining),hl
    jr zx48_p509_skip_loop
zx48_p509_skip_done:
    ld hl,(p509_skip_ptr)
    ld bc,M48O_CHUNK_SIZE
    call zx48_free
    ret
zx48_p509_skip_fail:
    ld (p509_error),a
    ld hl,(p509_skip_ptr)
    ld bc,M48O_CHUNK_SIZE
    call zx48_free
    ld a,(p509_error)
    scf
    ret

; Commit the fully validated private incoming object atomically.
zx48_p509_commit:
    ld a,(p509_requested_dir)
    ld hl,p509_requested_name
    call zx48_object_lookup
    jr c,zx48_p509_commit_new
    ld a,c
    ld (p509_existing_slot),a
    ld (p509_existing_ptr),ix
    ld a,(ix+OBJ_RESERVED_BYTE)
    cp STATE_RAM
    jp nz,zx48_p509_commit_perm
    ld d,c
    call zx48_od_object_any_live
    jp c,zx48_p509_commit_drop_new
    ld ix,(p509_existing_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p509_old_ptr),hl
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld (p509_old_storage),bc
    jr zx48_p509_publish

zx48_p509_commit_new:
    cp E_NOENT
    jp nz,zx48_p509_commit_drop_new
    ld a,(p509_requested_dir)
    ld b,(p509_header+M48O_HDR_TYPE)
    ld hl,p509_requested_name
    call zx48_object_create
    jp c,zx48_p509_commit_drop_new
    ld a,c
    ld (p509_existing_slot),a
    ld (p509_existing_ptr),ix
    xor a
    ld (p509_old_ptr),a
    ld (p509_old_ptr+1),a
    ld (p509_old_storage),a
    ld (p509_old_storage+1),a

zx48_p509_publish:
    ld ix,(p509_existing_ptr)
    ld a,(p509_header+M48O_HDR_TYPE)
    ld (ix+OBJ_TYPE_ID),a
    ld a,(p509_header+M48O_HDR_FLAGS)
    ld (ix+OBJ_FLAGS_BYTE),a
    xor a
    ld (ix+OBJ_RESERVED_BYTE),a
    ld hl,(p509_new_logical)
    ld (ix+OBJ_LOGICAL_LENGTH),l
    ld (ix+OBJ_LOGICAL_LENGTH+1),h
    ld hl,(p509_new_storage)
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h
    ld hl,(p509_new_ptr)
    ld (ix+OBJ_ALLOCATION_PTR),l
    ld (ix+OBJ_ALLOCATION_PTR+1),h
    ld a,(p509_existing_slot)
    call zx48_p424_candidate_clear

    ; Old payload becomes unreachable only after the new record is complete.
    ld hl,(p509_old_ptr)
    ld a,h
    or l
    jr z,zx48_p509_commit_success
    ld bc,(p509_old_storage)
    bit 0,c
    jr z,zx48_p509_old_even
    inc bc
zx48_p509_old_even:
    call zx48_free
    jp c,zx48_p509_free_error
zx48_p509_commit_success:
    ld hl,0
    xor a
    or a
    ret

zx48_p509_commit_perm:
    ld a,E_PERM
zx48_p509_commit_drop_new:
    ld (p509_error),a
    ld hl,(p509_new_ptr)
    ld bc,(p509_new_storage)
    ld a,b
    or c
    jr z,zx48_p509_drop_done
    bit 0,c
    jr z,zx48_p509_drop_even
    inc bc
zx48_p509_drop_even:
    call zx48_free
zx48_p509_drop_done:
    ld a,(p509_error)
    scf
    ret
zx48_p509_free_error:
    ld a,E_IO
    scf
    ret

zx48_p509_locked_format:
    ld a,E_FORMAT
zx48_p509_locked_error:
    ld (p509_error),a
    call zx48_p507_lock_release
    ld a,(p509_error)
    scf
    ret
zx48_p509_format:
    ld a,E_FORMAT
    scf
    ret
zx48_p509_inval:
    ld a,E_INVAL
    scf
    ret

; P5.13 replaces this foreground hook with the visible PLAY/rewind prompt.
zx48_p509_prompt_play:
    xor a
    or a
    ret

p509_header: defs M48O_HDR_SIZE,0
p509_requested_name: defs M48O_NAME_SIZE,0
p509_requested_dir: db 0
p509_new_ptr: dw 0
p509_new_storage: dw 0
p509_new_logical: dw 0
p509_existing_ptr: dw 0
p509_existing_slot: db 0
p509_old_ptr: dw 0
p509_old_storage: dw 0
p509_skip_ptr: dw 0
p509_skip_remaining: dw 0
p509_skip_chunk: dw 0
p509_error: db 0
    ENDM

    MACRO EMIT_P510_VERIFY_ROUTINES
; HL=NUL-terminated requested path. Sequentially locate exact case/target, fully
; validate the incoming private representation, then compare logical bytes
; without changing the resident object or namespace.
zx48_p510_verify_path:
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jp nz,zx48_p510_inval
    ld a,(path_dir)
    ld (p510_requested_dir),a
    ld hl,path_name
    ld de,p510_requested_name
    ld bc,M48O_NAME_SIZE
    ldir

    ld a,(p510_requested_dir)
    ld hl,p510_requested_name
    call zx48_object_lookup
    ret c
    ld (p510_target_ptr),ix
    ld a,(ix+OBJ_TYPE_ID)
    ld (p510_target_type),a
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (p510_logical),hl

    call zx48_p509_prompt_play
    ret c
    call zx48_p507_lock_acquire
    ret c

zx48_p510_scan:
    ld ix,p509_header
    ld de,M48O_HDR_SIZE
    ld a,M48O_ROM_DATA_FLAG
    scf
    call zx48_tape_load_block
    jp c,zx48_p510_locked_error
    call zx48_p509_header_basic
    jp c,zx48_p510_locked_error

    ld a,(p509_header+M48O_HDR_DIRECTORY)
    ld b,a
    ld a,(p510_requested_dir)
    cp b
    jr nz,zx48_p510_skip
    ld hl,p509_header+M48O_HDR_NAME
    ld de,p510_requested_name
    ld b,M48O_NAME_SIZE
zx48_p510_name_loop:
    ld a,(de)
    cp (hl)
    jr nz,zx48_p510_skip
    inc de
    inc hl
    djnz zx48_p510_name_loop
    jr zx48_p510_match

zx48_p510_skip:
    call zx48_p509_skip_payload
    jp c,zx48_p510_locked_error
    jr zx48_p510_scan

zx48_p510_match:
    ld a,(p509_header+M48O_HDR_TYPE)
    ld b,a
    ld a,(p510_target_type)
    cp b
    jp nz,zx48_p510_locked_format
    ld hl,(p509_header+M48O_HDR_LOGICAL_LEN)
    ld de,(p510_logical)
    or a
    sbc hl,de
    jp nz,zx48_p510_locked_format

    ld a,(p509_header+M48O_HDR_FLAGS)
    ld (p510_incoming_flags),a
    or a
    jr z,zx48_p510_load_raw
    cp M48O_PACKED
    jp nz,zx48_p510_locked_format
    ld hl,p509_header
    call zx48_p505_packed_load
    jr zx48_p510_loaded
zx48_p510_load_raw:
    ld hl,p509_header
    call zx48_p504_raw_load
zx48_p510_loaded:
    jp c,zx48_p510_locked_error
    ld (p510_incoming_ptr),hl
    ld (p510_incoming_storage),bc
    call zx48_p507_lock_release

    call zx48_p510_prepare_states
    jp c,zx48_p510_drop_incoming
    xor a
    ld (p510_pos),a
    ld (p510_pos+1),a

zx48_p510_compare_loop:
    ld hl,(p510_pos)
    ld de,(p510_logical)
    or a
    sbc hl,de
    jr z,zx48_p510_compare_success
    call zx48_p510_target_byte
    jp c,zx48_p510_compare_fail
    ld (p510_byte),a
    call zx48_p510_incoming_byte
    jp c,zx48_p510_compare_fail
    ld b,a
    ld a,(p510_byte)
    cp b
    jr nz,zx48_p510_mismatch
    ld hl,(p510_pos)
    inc hl
    ld (p510_pos),hl
    jr zx48_p510_compare_loop

zx48_p510_compare_success:
    call zx48_p510_release_states
    call zx48_p510_free_incoming
    ld hl,0
    xor a
    or a
    ret
zx48_p510_mismatch:
    ld a,E_IO
zx48_p510_compare_fail:
    ld (p510_error),a
    call zx48_p510_release_states
zx48_p510_drop_incoming:
    ld (p510_error),a
    call zx48_p510_free_incoming
    ld a,(p510_error)
    scf
    ret

zx48_p510_prepare_states:
    xor a
    ld (p510_target_state),a
    ld (p510_target_state+1),a
    ld (p510_incoming_state),a
    ld (p510_incoming_state+1),a

    ld ix,(p510_target_ptr)
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr z,zx48_p510_prepare_incoming
    ld bc,P417_STATE_SIZE
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    ret c
    ld (p510_target_state),hl
    call zx48_p417_state_init
    push hl
    pop ix
    ld hl,(p510_target_ptr)
    push hl
    pop iy
    ld l,(iy+OBJ_ALLOCATION_PTR)
    ld h,(iy+OBJ_ALLOCATION_PTR+1)
    ld c,(iy+OBJ_STORAGE_LENGTH)
    ld b,(iy+OBJ_STORAGE_LENGTH+1)
    call zx48_p418_state_bind
    jr nc,zx48_p510_prepare_incoming
    ld (p510_error),a
    call zx48_p510_release_states
    ld a,(p510_error)
    scf
    ret

zx48_p510_prepare_incoming:
    ld a,(p510_incoming_flags)
    and M48O_PACKED
    jr z,zx48_p510_states_ready
    ld bc,P417_STATE_SIZE
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    jr nc,zx48_p510_incoming_state_alloc
    ld (p510_error),a
    call zx48_p510_release_states
    ld a,(p510_error)
    scf
    ret
zx48_p510_incoming_state_alloc:
    ld (p510_incoming_state),hl
    call zx48_p417_state_init
    push hl
    pop ix
    ld hl,(p510_incoming_ptr)
    ld bc,(p510_incoming_storage)
    call zx48_p418_state_bind
    jr nc,zx48_p510_states_ready
    ld (p510_error),a
    call zx48_p510_release_states
    ld a,(p510_error)
    scf
    ret
zx48_p510_states_ready:
    xor a
    or a
    ret

zx48_p510_target_byte:
    ld ix,(p510_target_ptr)
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr nz,zx48_p510_target_packed
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld de,(p510_pos)
    add hl,de
    ld a,(hl)
    or a
    ret
zx48_p510_target_packed:
    ld ix,(p510_target_state)
    call zx48_p418_step
    ret c
    ld a,(p418_byte)
    or a
    ret

zx48_p510_incoming_byte:
    ld a,(p510_incoming_flags)
    and M48O_PACKED
    jr nz,zx48_p510_incoming_packed
    ld hl,(p510_incoming_ptr)
    ld de,(p510_pos)
    add hl,de
    ld a,(hl)
    or a
    ret
zx48_p510_incoming_packed:
    ld ix,(p510_incoming_state)
    call zx48_p418_step
    ret c
    ld a,(p418_byte)
    or a
    ret

zx48_p510_release_states:
    ld hl,(p510_target_state)
    ld a,h
    or l
    jr z,zx48_p510_release_incoming
    ld bc,P417_STATE_SIZE
    call zx48_free
    xor a
    ld (p510_target_state),a
    ld (p510_target_state+1),a
zx48_p510_release_incoming:
    ld hl,(p510_incoming_state)
    ld a,h
    or l
    ret z
    ld bc,P417_STATE_SIZE
    call zx48_free
    xor a
    ld (p510_incoming_state),a
    ld (p510_incoming_state+1),a
    ret

zx48_p510_free_incoming:
    ld hl,(p510_incoming_ptr)
    ld bc,(p510_incoming_storage)
    ld a,b
    or c
    ret z
    bit 0,c
    jr z,zx48_p510_free_even
    inc bc
zx48_p510_free_even:
    jp zx48_free

zx48_p510_locked_format:
    ld a,E_FORMAT
zx48_p510_locked_error:
    ld (p510_error),a
    call zx48_p507_lock_release
    ld a,(p510_error)
    scf
    ret
zx48_p510_inval:
    ld a,E_INVAL
    scf
    ret

p510_requested_name: defs M48O_NAME_SIZE,0
p510_requested_dir: db 0
p510_target_type: db 0
p510_target_ptr: dw 0
p510_logical: dw 0
p510_incoming_flags: db 0
p510_incoming_ptr: dw 0
p510_incoming_storage: dw 0
p510_target_state: dw 0
p510_incoming_state: dw 0
p510_pos: dw 0
p510_byte: db 0
p510_error: db 0
    ENDM

    MACRO EMIT_P511_SCAN_ROUTINES
P511_KIND_NONE          EQU 0
P511_KIND_LITERAL       EQU 1
P511_KIND_RLE_PARAM     EQU 2
P511_KIND_BACKREF_PARAM EQU 3

; HL -> writable 32-byte M48O header. Consume and completely validate exactly
; one next object. Payload buffering is one 512-byte scratch allocation; PACKED
; adds exactly one 272-byte decoder/history allocation.
zx48_p511_scan_next:
    ld (p511_header_dest),hl
    xor a
    ld (p511_scratch_live),a
    ld (p511_decoder_live),a
    call zx48_p507_lock_acquire
    ret c

    ld ix,(p511_header_dest)
    ld de,M48O_HDR_SIZE
    ld a,M48O_ROM_DATA_FLAG
    scf
    call zx48_tape_load_block
    jp c,zx48_p511_transport_fail
    call zx48_p511_validate_header
    jp c,zx48_p511_fail_locked

    ld hl,(p511_storage)
    ld a,h
    or l
    jr z,zx48_p511_finish_payload

    ld bc,M48O_CHUNK_SIZE
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    jp c,zx48_p511_fail_locked
    ld (p511_scratch),hl
    ld a,1
    ld (p511_scratch_live),a

    ld a,(p511_flags)
    and M48O_PACKED
    jr z,zx48_p511_payload_ready
    ld bc,P417_STATE_SIZE
    ld a,ALLOC_COLD_PREFERRED|ALLOC_NO_COMPACT
    call zx48_alloc
    jp c,zx48_p511_fail_locked
    ld (p511_decoder),hl
    ld a,1
    ld (p511_decoder_live),a
    push hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,P417_STATE_SIZE-1
    ldir
    pop hl
    ld (p511_history_base),hl
    xor a
    ld (p511_hist_index),a
    ld (p511_kind),a
    ld (p511_pending),a
    ld hl,0
    ld (p511_logical_pos),hl

zx48_p511_payload_ready:
    ld hl,(p511_storage)
    ld (p511_remaining),hl
    ld hl,M48O_CRC16_INIT
    ld (p511_crc),hl

zx48_p511_chunk_loop:
    ld bc,(p511_remaining)
    ld a,b
    or c
    jr z,zx48_p511_finish_payload
    call zx48_p503_prepare_chunk
    ld (p511_chunk_len),de
    ld ix,(p511_scratch)
    ld a,M48O_ROM_DATA_FLAG
    scf
    call zx48_tape_load_block
    jp c,zx48_p511_transport_fail

    ld a,(p511_flags)
    and M48O_PACKED
    jr nz,zx48_p511_process_packed
    ld hl,(p511_scratch)
    ld bc,(p511_chunk_len)
zx48_p511_raw_byte_loop:
    ld a,b
    or c
    jr z,zx48_p511_chunk_done
    ld a,(hl)
    push hl
    push bc
    call zx48_p511_crc_byte
    pop bc
    pop hl
    inc hl
    ld de,(p511_logical_pos)
    inc de
    ld (p511_logical_pos),de
    dec bc
    jr zx48_p511_raw_byte_loop

zx48_p511_process_packed:
    ld hl,(p511_scratch)
    ld bc,(p511_chunk_len)
zx48_p511_packed_byte_loop:
    ld a,b
    or c
    jr z,zx48_p511_chunk_done
    ld a,(hl)
    push hl
    push bc
    call zx48_p511_feed_packed_byte
    pop bc
    pop hl
    jp c,zx48_p511_fail_locked
    inc hl
    dec bc
    jr zx48_p511_packed_byte_loop

zx48_p511_chunk_done:
    ld hl,(p511_remaining)
    ld de,(p511_chunk_len)
    or a
    sbc hl,de
    ld (p511_remaining),hl
    jr zx48_p511_chunk_loop

zx48_p511_finish_payload:
    ld a,(p511_flags)
    and M48O_PACKED
    jr z,zx48_p511_finish_lengths
    ld a,(p511_kind)
    or a
    jp nz,zx48_p511_format_fail
zx48_p511_finish_lengths:
    ld hl,(p511_logical_pos)
    ld de,(p511_logical)
    or a
    sbc hl,de
    jp nz,zx48_p511_format_fail
    ld hl,(p511_crc)
    ld de,(p511_expected_crc)
    or a
    sbc hl,de
    jr z,zx48_p511_success
    ld a,E_IO
    jp zx48_p511_fail_locked

zx48_p511_success:
    call zx48_p511_release_scratch
    call zx48_p507_lock_release
    ld hl,1
    xor a
    or a
    ret

zx48_p511_validate_header:
    ld hl,(p511_header_dest)
    ld a,(hl)
    cp M48O_MAGIC_0
    jp nz,zx48_p511_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_1
    jp nz,zx48_p511_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_2
    jp nz,zx48_p511_format
    inc hl
    ld a,(hl)
    cp M48O_MAGIC_3
    jp nz,zx48_p511_format
    inc hl
    ld a,(hl)
    cp M48O_VERSION
    jp nz,zx48_p511_format

    ld hl,(p511_header_dest)
    ld de,M48O_HDR_TYPE
    add hl,de
    ld a,(hl)
    ld (p511_type),a
    cp M48O_TYPE_TXT
    jp c,zx48_p511_format
    cp M48O_TYPE_SYS+1
    jp nc,zx48_p511_format
    inc hl
    ld a,(hl)
    ld (p511_flags),a
    and $fe
    jp nz,zx48_p511_format
    inc hl
    ld a,(hl)
    ld (p511_target),a

    ld b,(p511_type)
    cp M48O_TARGET_SYSTEM
    jr z,zx48_p511_system_placement
    call zx48_object_public_type_allowed
    jp c,zx48_p511_format
    jr zx48_p511_placement_ok
zx48_p511_system_placement:
    ld a,b
    cp M48O_TYPE_FNT
    jr z,zx48_p511_placement_ok
    cp M48O_TYPE_SYS
    jp nz,zx48_p511_format
zx48_p511_placement_ok:

    ld hl,(p511_header_dest)
    ld de,M48O_HDR_STORAGE_LEN
    add hl,de
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld (p511_storage),bc
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p511_logical),de
    call zx48_p511_len_bound_storage
    ret c
    ld hl,(p511_logical)
    call zx48_p511_len_bound
    ret c

    ; Reserved bytes zero.
    ld hl,(p511_header_dest)
    ld de,M48O_HDR_RESERVED
    add hl,de
    ld b,M48O_RESERVED_SIZE
zx48_p511_reserved_loop:
    ld a,(hl)
    or a
    jp nz,zx48_p511_format
    inc hl
    djnz zx48_p511_reserved_loop

    ; Exact 1..10 valid name, NUL padding only.
    ld hl,(p511_header_dest)
    ld de,M48O_HDR_NAME
    add hl,de
    ld b,M48O_NAME_SIZE
    xor a
    ld (p511_name_seen),a
zx48_p511_name_loop:
    ld a,(hl)
    or a
    jr z,zx48_p511_name_zero
    ld a,(p511_name_seen)
    cp 2
    jp z,zx48_p511_format
    ld a,(hl)
    call zx48_p511_name_char
    ret c
    ld a,1
    ld (p511_name_seen),a
    jr zx48_p511_name_next
zx48_p511_name_zero:
    ld a,(p511_name_seen)
    or a
    jp z,zx48_p511_format
    ld a,2
    ld (p511_name_seen),a
zx48_p511_name_next:
    inc hl
    djnz zx48_p511_name_loop
    ld a,(p511_name_seen)
    or a
    jp z,zx48_p511_format

    ; Header CRC with its field temporarily zeroed.
    ld hl,(p511_header_dest)
    ld de,M48O_HDR_HEADER_CRC
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p511_header_crc),de
    xor a
    ld (hl),a
    dec hl
    ld (hl),a
    ld hl,(p511_header_dest)
    ld bc,M48O_HDR_SIZE
    call zx48_crc16_ccitt_false
    push de
    ld hl,(p511_header_dest)
    ld bc,M48O_HDR_HEADER_CRC
    add hl,bc
    ld de,(p511_header_crc)
    ld (hl),e
    inc hl
    ld (hl),d
    pop hl
    ld de,(p511_header_crc)
    or a
    sbc hl,de
    jp nz,zx48_p511_format

    ld hl,(p511_header_dest)
    ld de,M48O_HDR_PAYLOAD_CRC
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p511_expected_crc),de

    ld a,(p511_flags)
    and M48O_PACKED
    jr nz,zx48_p511_validate_packed
    ; RAW: codec zero, physical == logical.
    ld hl,(p511_header_dest)
    ld de,M48O_HDR_CODEC
    add hl,de
    ld a,(hl)
    inc hl
    or (hl)
    jp nz,zx48_p511_format
    ld hl,(p511_storage)
    ld de,(p511_logical)
    or a
    sbc hl,de
    jp nz,zx48_p511_format
    xor a
    or a
    ret

zx48_p511_validate_packed:
    ld hl,(p511_header_dest)
    ld de,M48O_HDR_CODEC
    add hl,de
    ld a,(hl)
    cp low M48O_CODEC_ZXP1
    jp nz,zx48_p511_format
    inc hl
    ld a,(hl)
    cp high M48O_CODEC_ZXP1
    jp nz,zx48_p511_format
    ld hl,(p511_storage)
    ld a,h
    or l
    jp z,zx48_p511_format
    ld de,(p511_logical)
    ld a,d
    or e
    jp z,zx48_p511_format
    or a
    sbc hl,de
    jp nc,zx48_p511_format
    xor a
    or a
    ret

zx48_p511_len_bound_storage:
    ld h,b
    ld l,c
zx48_p511_len_bound:
    ld a,h
    cp $80
    jr c,zx48_p511_len_ok
    jr nz,zx48_p511_format
    ld a,l
    or a
    jr nz,zx48_p511_format
zx48_p511_len_ok:
    xor a
    or a
    ret

zx48_p511_name_char:
    cp '0'
    jr c,zx48_p511_name_punct
    cp '9'+1
    jr c,zx48_p511_name_ok
    cp 'A'
    jr c,zx48_p511_name_punct
    cp 'Z'+1
    jr c,zx48_p511_name_ok
    cp 'a'
    jr c,zx48_p511_name_punct
    cp 'z'+1
    jr c,zx48_p511_name_ok
zx48_p511_name_punct:
    cp '_'
    jr z,zx48_p511_name_ok
    cp '-'
    jr z,zx48_p511_name_ok
    cp '.'
    jr z,zx48_p511_name_ok
    jp zx48_p511_format
zx48_p511_name_ok:
    xor a
    or a
    ret

; A = next physical ZXP1 byte. Parser state persists across 512-byte chunks.
zx48_p511_feed_packed_byte:
    ld (p511_input_byte),a
    ld a,(p511_kind)
    cp P511_KIND_LITERAL
    jr z,zx48_p511_literal_byte
    cp P511_KIND_RLE_PARAM
    jr z,zx48_p511_rle_param
    cp P511_KIND_BACKREF_PARAM
    jr z,zx48_p511_backref_param

    ld a,(p511_input_byte)
    cp $40
    jr c,zx48_p511_new_literal
    cp $80
    jr c,zx48_p511_new_rle
    and $7f
    add a,3
    ld (p511_pending),a
    ld a,P511_KIND_BACKREF_PARAM
    ld (p511_kind),a
    xor a
    or a
    ret
zx48_p511_new_literal:
    inc a
    ld (p511_pending),a
    ld a,P511_KIND_LITERAL
    ld (p511_kind),a
    xor a
    or a
    ret
zx48_p511_new_rle:
    and $3f
    add a,3
    ld (p511_pending),a
    ld a,P511_KIND_RLE_PARAM
    ld (p511_kind),a
    xor a
    or a
    ret

zx48_p511_literal_byte:
    ld a,(p511_input_byte)
    call zx48_p511_emit
    ret c
    ld a,(p511_pending)
    dec a
    ld (p511_pending),a
    ret nz
    xor a
    ld (p511_kind),a
    or a
    ret

zx48_p511_rle_param:
    ld a,(p511_input_byte)
    ld (p511_repeat),a
zx48_p511_rle_loop:
    ld a,(p511_repeat)
    call zx48_p511_emit
    ret c
    ld a,(p511_pending)
    dec a
    ld (p511_pending),a
    jr nz,zx48_p511_rle_loop
    xor a
    ld (p511_kind),a
    or a
    ret

zx48_p511_backref_param:
    ld a,(p511_input_byte)
    ld (p511_distance_m1),a
    inc a
    jr nz,zx48_p511_back_dist8
    ld de,256
    jr zx48_p511_back_dist_ready
zx48_p511_back_dist8:
    ld e,a
    ld d,0
zx48_p511_back_dist_ready:
    ld hl,(p511_logical_pos)
    or a
    sbc hl,de
    jp c,zx48_p511_format
    ld (p511_back_distance),de
zx48_p511_back_loop:
    ld a,(p511_hist_index)
    ld e,a
    ld d,0
    ld hl,(p511_back_distance)
    ld a,l
    ld l,e
    sub l
    ; 8-bit wrap is the required circular-history index.
    ld e,a
    ld d,0
    ld hl,(p511_history_base)
    add hl,de
    ld a,(hl)
    call zx48_p511_emit
    ret c
    ld a,(p511_pending)
    dec a
    ld (p511_pending),a
    jr nz,zx48_p511_back_loop
    xor a
    ld (p511_kind),a
    or a
    ret

zx48_p511_emit:
    ld (p511_emit_byte),a
    ld hl,(p511_logical_pos)
    ld de,(p511_logical)
    or a
    sbc hl,de
    jp nc,zx48_p511_format
    ld a,(p511_emit_byte)
    call zx48_p511_crc_byte
    ld a,(p511_hist_index)
    ld e,a
    ld d,0
    ld hl,(p511_history_base)
    add hl,de
    ld a,(p511_emit_byte)
    ld (hl),a
    ld a,(p511_hist_index)
    inc a
    ld (p511_hist_index),a
    ld hl,(p511_logical_pos)
    inc hl
    ld (p511_logical_pos),hl
    xor a
    or a
    ret

zx48_p511_crc_byte:
    ld hl,(p511_crc)
    xor h
    ld h,a
    ld b,8
zx48_p511_crc_bit:
    add hl,hl
    jr nc,zx48_p511_crc_next
    ld a,h
    xor $10
    ld h,a
    ld a,l
    xor $21
    ld l,a
zx48_p511_crc_next:
    djnz zx48_p511_crc_bit
    ld (p511_crc),hl
    ret

zx48_p511_transport_fail:
    ; A transport failure is cancellation when the current process carries the
    ; cooperative cancel flag; otherwise retain the ROM-wrapper E_IO result.
    ld (p511_error),a
    ld a,(current_pid)
    call zx48_process_lookup
    jr c,zx48_p511_transport_mapped
    bit 0,(ix+PROC_FLAGS)
    jr z,zx48_p511_transport_mapped
    ld a,E_INTR
    ld (p511_error),a
zx48_p511_transport_mapped:
    ld a,(p511_error)
    jr zx48_p511_fail_locked

zx48_p511_format_fail:
    ld a,E_FORMAT
zx48_p511_fail_locked:
    ld (p511_error),a
    call zx48_p511_release_scratch
    call zx48_p507_lock_release
    ld a,(p511_error)
    scf
    ret
zx48_p511_format:
    ld a,E_FORMAT
    scf
    ret

zx48_p511_release_scratch:
    ld a,(p511_decoder_live)
    or a
    jr z,zx48_p511_release_scratch_only
    ld hl,(p511_decoder)
    ld bc,P417_STATE_SIZE
    call zx48_free
    xor a
    ld (p511_decoder_live),a
zx48_p511_release_scratch_only:
    ld a,(p511_scratch_live)
    or a
    ret z
    ld hl,(p511_scratch)
    ld bc,M48O_CHUNK_SIZE
    call zx48_free
    xor a
    ld (p511_scratch_live),a
    ret

p511_header_dest: dw 0
p511_storage: dw 0
p511_logical: dw 0
p511_expected_crc: dw 0
p511_header_crc: dw 0
p511_scratch: dw 0
p511_decoder: dw 0
p511_history_base: dw 0
p511_remaining: dw 0
p511_chunk_len: dw 0
p511_logical_pos: dw 0
p511_crc: dw 0
p511_back_distance: dw 0
p511_type: db 0
p511_target: db 0
p511_flags: db 0
p511_name_seen: db 0
p511_kind: db 0
p511_pending: db 0
p511_repeat: db 0
p511_distance_m1: db 0
p511_hist_index: db 0
p511_input_byte: db 0
p511_emit_byte: db 0
p511_scratch_live: db 0
p511_decoder_live: db 0
p511_error: db 0
    ENDM

    MACRO EMIT_TAPE_ROUTINES
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P504_RAW_LOADER_ROUTINES
    EMIT_P505_PACKED_LOADER_ROUTINES
    EMIT_P507_RAW_SAVE_ROUTINES
    EMIT_P508_STREAM_SAVE_ROUTINES
    EMIT_P509_EXPLICIT_LOAD_ROUTINES
    EMIT_P510_VERIFY_ROUTINES
    EMIT_P511_SCAN_ROUTINES
; A=block type,DE=length,IX=source.
zx48_tape_save_block:
    call zx48_rom_sa_bytes
    ret nc
    ld a,E_IO
    scf
    ret
; A=block type,DE=length,IX=destination; carry selects load/verify.
zx48_tape_load_block:
    call zx48_rom_ld_bytes
    jr nc,zx48_tape_load_error
    or a
    ret
zx48_tape_load_error:
    ld a,E_IO
    scf
    ret

; Public object operations are deliberately sequential. The compact resident
; layer validates RAM namespace first; host/tape format tests own M48O framing.
zx48_tape_save_path:
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jr nz,zx48_tape_bad
    ld a,(path_dir)
    ld hl,path_name
    call zx48_object_lookup
    ret c
    jp zx48_p508_save_record

zx48_tape_load_path:
    jp zx48_p509_load_path
zx48_tape_verify_path:
    jp zx48_p510_verify_path

; HL=32-byte header destination. Consumes exactly one next M48O header block.
zx48_tape_scan_next:
    jp zx48_p511_scan_next
zx48_tape_bad:
    ld a,E_INVAL
    scf
    ret
    ENDM
