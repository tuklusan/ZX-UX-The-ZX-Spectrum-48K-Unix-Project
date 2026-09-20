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

    MACRO EMIT_TAPE_ROUTINES
    EMIT_P502_CRC16_ROUTINES
    EMIT_P503_FRAMING_ROUTINES
    EMIT_P504_RAW_LOADER_ROUTINES
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
    ret nc
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
    ; Save RAW logical payload as ROM data block after a transport header emitted
    ; by the shell/host builder. PACKED RAM objects are materialized first.
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    call nz,zx48_zxpack_materialize
    ret c
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    push hl
    pop ix
    ld e,(ix+OBJ_LOGICAL_LENGTH)  ; IX is payload now; metadata unavailable.
    ld a,E_NOTSUP
    scf
    ret

zx48_tape_load_path:
    ; Loading requires the next physical M48O name to match requested path. The
    ; full sequential transaction is exposed through SYS_TAPE_SCAN + shell copy.
    ld a,E_AGAIN
    scf
    ret
zx48_tape_verify_path:
    ld a,E_AGAIN
    scf
    ret

; HL=32-byte header destination. Consumes exactly one next M48O header block.
zx48_tape_scan_next:
    push hl
    pop ix
    call zx48_p503_prepare_header_block
    scf
    call zx48_tape_load_block
    ret c
    ld hl,1
    xor a
    or a
    ret
zx48_tape_bad:
    ld a,E_INVAL
    scf
    ret
    ENDM
