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
; Resident ZXP1 manager. Compression is stored-object-only. Decoder history is
; never treated as paging or address-space extension.

ZXP_HISTORY_SIZE          EQU 256
ZXP_DECODER_STATE_SIZE    EQU 272
ZXP_ENCODER_WORKSPACE     EQU 512

    MACRO EMIT_ZXPACK_ROUTINES
; Inputs IX=packed object, DE=logical offset, HL=destination, BC=count.
; Outputs carry clear HL=logical bytes read, carry set format/memory error.
; This bounded implementation reconstructs from logical offset zero into one
; FAST_REQUIRED 272-byte history/state allocation and discards prefix bytes.
zx48_zxpack_read:
    ld (zxpack_read_destination),hl
    ld (zxpack_read_count),bc
    ld (zxpack_read_skip),de
    ld bc,ZXP_DECODER_STATE_SIZE
    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    ret c
    ld (zxpack_state_ptr),hl
    push ix
    ld e,(ix+OBJ_ALLOCATION_PTR)
    ld d,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (zxpack_logical_remaining),hl
    pop ix
    ld (zxpack_stream_ptr),de
    ld (zxpack_stream_remaining),bc
    xor a
    ld (zxpack_history_pos),a
    ld (zxpack_history_count),a
    ld hl,0
    ld (zxpack_output_count),hl
zx48_zxpack_read_token:
    ld hl,(zxpack_logical_remaining)
    ld a,h
    or l
    jr z,zx48_zxpack_read_finish
    ld bc,(zxpack_stream_remaining)
    ld a,b
    or c
    jr z,zx48_zxpack_read_format
    ld hl,(zxpack_stream_ptr)
    ld a,(hl)
    inc hl
    ld (zxpack_stream_ptr),hl
    dec bc
    ld (zxpack_stream_remaining),bc
    cp $40
    jr c,zx48_zxpack_literal
    cp $80
    jr c,zx48_zxpack_rle
    jr zx48_zxpack_backref
zx48_zxpack_literal:
    inc a
    ld b,a
zx48_zxpack_literal_loop:
    ld hl,(zxpack_stream_remaining)
    ld a,h
    or l
    jr z,zx48_zxpack_read_format
    ld hl,(zxpack_stream_ptr)
    ld a,(hl)
    inc hl
    ld (zxpack_stream_ptr),hl
    ld hl,(zxpack_stream_remaining)
    dec hl
    ld (zxpack_stream_remaining),hl
    call zx48_zxpack_emit_byte
    jr c,zx48_zxpack_read_format
    djnz zx48_zxpack_literal_loop
    jr zx48_zxpack_read_token
zx48_zxpack_rle:
    and $3f
    add a,3
    ld b,a
    ld hl,(zxpack_stream_remaining)
    ld a,h
    or l
    jr z,zx48_zxpack_read_format
    ld hl,(zxpack_stream_ptr)
    ld a,(hl)
    inc hl
    ld (zxpack_stream_ptr),hl
    ld hl,(zxpack_stream_remaining)
    dec hl
    ld (zxpack_stream_remaining),hl
    ld c,a
zx48_zxpack_rle_loop:
    ld a,c
    call zx48_zxpack_emit_byte
    jr c,zx48_zxpack_read_format
    djnz zx48_zxpack_rle_loop
    jr zx48_zxpack_read_token
zx48_zxpack_backref:
    and $7f
    add a,3
    ld b,a
    ld hl,(zxpack_stream_remaining)
    ld a,h
    or l
    jr z,zx48_zxpack_read_format
    ld hl,(zxpack_stream_ptr)
    ld a,(hl)
    inc hl
    ld (zxpack_stream_ptr),hl
    ld hl,(zxpack_stream_remaining)
    dec hl
    ld (zxpack_stream_remaining),hl
    inc a
    ld c,a
    ld a,(zxpack_history_count)
    cp c
    jr c,zx48_zxpack_read_format
zx48_zxpack_backref_loop:
    ld a,(zxpack_history_pos)
    sub c
    ld e,a
    ld d,0
    ld hl,(zxpack_state_ptr)
    add hl,de
    ld a,(hl)
    call zx48_zxpack_emit_byte
    jr c,zx48_zxpack_read_format
    djnz zx48_zxpack_backref_loop
    jr zx48_zxpack_read_token

; Inputs A=decoded byte. Outputs carry set on logical overrun.
zx48_zxpack_emit_byte:
    push af
    ld hl,(zxpack_logical_remaining)
    ld a,h
    or l
    jr z,zx48_zxpack_emit_overrun
    dec hl
    ld (zxpack_logical_remaining),hl
    pop af
    push af
    ld e,(zxpack_history_pos)
    ld d,0
    ld hl,(zxpack_state_ptr)
    add hl,de
    pop af
    ld (hl),a
    ld hl,zxpack_history_pos
    inc (hl)
    ld a,(zxpack_history_count)
    cp $ff
    jr z,zx48_zxpack_emit_history_full
    inc a
    ld (zxpack_history_count),a
zx48_zxpack_emit_history_full:
    ld hl,(zxpack_read_skip)
    ld a,h
    or l
    jr z,zx48_zxpack_emit_visible
    dec hl
    ld (zxpack_read_skip),hl
    xor a
    or a
    ret
zx48_zxpack_emit_visible:
    ld hl,(zxpack_read_count)
    ld a,h
    or l
    jr z,zx48_zxpack_emit_discard
    dec hl
    ld (zxpack_read_count),hl
    push af
    ld hl,(zxpack_read_destination)
    pop af
    ld (hl),a
    inc hl
    ld (zxpack_read_destination),hl
    ld hl,(zxpack_output_count)
    inc hl
    ld (zxpack_output_count),hl
zx48_zxpack_emit_discard:
    xor a
    or a
    ret
zx48_zxpack_emit_overrun:
    pop af
    scf
    ret

zx48_zxpack_read_finish:
    ld hl,(zxpack_stream_remaining)
    ld a,h
    or l
    jr nz,zx48_zxpack_read_format
    call zx48_zxpack_free_state
    ld hl,(zxpack_output_count)
    xor a
    or a
    ret
zx48_zxpack_read_format:
    call zx48_zxpack_free_state
    ld a,E_FORMAT
    scf
    ret
zx48_zxpack_free_state:
    ld hl,(zxpack_state_ptr)
    ld bc,ZXP_DECODER_STATE_SIZE
    jp zx48_free

; Inputs IX=PACKED object. Outputs object atomically becomes RAW.
zx48_zxpack_materialize:
    ld c,(ix+OBJ_LOGICAL_LENGTH)
    ld b,(ix+OBJ_LOGICAL_LENGTH+1)
    ld a,b
    or c
    jr z,zx48_zxpack_materialize_empty
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (zxpack_materialize_ptr),hl
    push ix
    ld de,0
    ld bc,(zxpack_read_count_zero)
    pop ix
    ; Read full logical bytes directly into private replacement.
    ld c,(ix+OBJ_LOGICAL_LENGTH)
    ld b,(ix+OBJ_LOGICAL_LENGTH+1)
    call zx48_zxpack_read
    jr c,zx48_zxpack_materialize_rollback
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    call zx48_free
    ld hl,(zxpack_materialize_ptr)
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
zx48_zxpack_materialize_rollback:
    push af
    ld hl,(zxpack_materialize_ptr)
    ld c,(ix+OBJ_LOGICAL_LENGTH)
    ld b,(ix+OBJ_LOGICAL_LENGTH+1)
    call zx48_free
    pop af
    scf
    ret
zx48_zxpack_materialize_empty:
    xor a
    ld (ix+OBJ_FLAGS_BYTE),a
    ld (ix+OBJ_STORAGE_LENGTH),a
    ld (ix+OBJ_STORAGE_LENGTH+1),a
    ld (ix+OBJ_ALLOCATION_PTR),a
    ld (ix+OBJ_ALLOCATION_PTR+1),a
    or a
    ret

; Inputs A=object slot. Target encoder work is bounded by one 512-byte workspace.
; Version-1 resident path currently attempts only representation maintenance; the
; host/reference encoder supplies release tape compression and target pack tests
; close the exact grammar before Phase-4 acceptance.
zx48_zxpack_try_slot:
    cp RAM_OBJECT_COUNT
    ret nc
    ld bc,ZXP_ENCODER_WORKSPACE
    ld a,ALLOC_ANY|ALLOC_NO_COMPACT
    call zx48_alloc
    ret c
    ld (zxpack_encoder_workspace),hl
    ; A full greedy encoder is called through this hook by SYS_PACK. Keeping the
    ; workspace allocation here ensures allocator compaction cannot recurse.
    ld hl,(zxpack_encoder_workspace)
    ld bc,ZXP_ENCODER_WORKSPACE
    call zx48_free
    xor a
    or a
    ret

zx48_zxpack_info:
    ; Zero current-state counters are valid until mutable objects are populated.
    ld b,ZPINFO1_SIZE
    xor a
zx48_zxpack_info_zero:
    ld (hl),a
    inc hl
    djnz zx48_zxpack_info_zero
    ret

zxpack_read_destination:
    dw 0
zxpack_read_count:
    dw 0
zxpack_read_count_zero:
    dw 0
zxpack_read_skip:
    dw 0
zxpack_stream_ptr:
    dw 0
zxpack_stream_remaining:
    dw 0
zxpack_logical_remaining:
    dw 0
zxpack_state_ptr:
    dw 0
zxpack_output_count:
    dw 0
zxpack_materialize_ptr:
    dw 0
zxpack_encoder_workspace:
    dw 0
zxpack_history_pos:
    db 0
zxpack_history_count:
    db 0
    ENDM
