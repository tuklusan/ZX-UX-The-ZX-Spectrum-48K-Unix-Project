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
; Exactly thirty-two 20-byte mutable records. Namespace lookup is byte-exact and
; case-sensitive. Fixed directories/devices and pinned bootstrap metadata are
; separate and therefore never consume mutable slots.

OBJ_NAME                  EQU 0
OBJ_DIR_ID                EQU 10
OBJ_TYPE_ID               EQU 11
OBJ_FLAGS_BYTE            EQU 12
OBJ_RESERVED_BYTE         EQU 13
OBJ_LOGICAL_LENGTH        EQU 14
OBJ_STORAGE_LENGTH        EQU 16
OBJ_ALLOCATION_PTR        EQU 18

    MACRO EMIT_OBJECT_ROUTINES
zx48_objects_init:
    xor a
    ld hl,object_table
    ld de,object_table+1
    ld bc,RAM_OBJECT_COUNT*OBJ_RECORD_SIZE-1
    ld (hl),a
    ldir
    ld (object_pack_candidates),a
    ld (object_pack_candidates+1),a
    ld (object_pack_candidates+2),a
    ld (object_pack_candidates+3),a
    ld (session_cwd),a
    ret

; Inputs: HL=NUL name.
; Outputs: carry clear A=length 1..10; carry set A=E_INVAL/E_TOOLONG.
zx48_name_validate:
    ld b,0
zx48_name_validate_loop:
    ld a,(hl)
    or a
    jr z,zx48_name_validate_end
    inc b
    ld a,b
    cp 11
    jr nc,zx48_name_validate_long
    ld a,(hl)
    call zx48_name_char_valid
    jr c,zx48_name_validate_bad
    inc hl
    jr zx48_name_validate_loop
zx48_name_validate_end:
    ld a,b
    or a
    jr z,zx48_name_validate_bad
    cp 1
    jr nz,zx48_name_validate_ok
    dec hl
    ld a,(hl)
    cp '.'
    jr z,zx48_name_validate_bad
zx48_name_validate_ok:
    ld a,b
    or a
    ret
zx48_name_validate_long:
    ld a,E_TOOLONG
    scf
    ret
zx48_name_validate_bad:
    ld a,E_INVAL
    scf
    ret

zx48_name_char_valid:
    cp '0'
    jr c,zx48_name_char_punct
    cp '9'+1
    jr c,zx48_name_char_ok
    cp 'A'
    jr c,zx48_name_char_punct
    cp 'Z'+1
    jr c,zx48_name_char_ok
    cp 'a'
    jr c,zx48_name_char_punct
    cp 'z'+1
    jr c,zx48_name_char_ok
zx48_name_char_punct:
    cp '_'
    jr z,zx48_name_char_ok
    cp '-'
    jr z,zx48_name_char_ok
    cp '.'
    jr z,zx48_name_char_ok
    scf
    ret
zx48_name_char_ok:
    or a
    ret

; Inputs: A=directory ID, HL=NUL exact-case base name.
; Outputs: carry clear IX=record, C=slot; carry set A=E_NOENT.
zx48_object_lookup:
    ld (object_lookup_dir),a
    ld (object_lookup_name),hl
    ld ix,object_table
    ld b,RAM_OBJECT_COUNT
    ld c,0
zx48_object_lookup_loop:
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_object_lookup_next
    ld a,(ix+OBJ_DIR_ID)
    ld d,a
    ld a,(object_lookup_dir)
    cp d
    jr nz,zx48_object_lookup_next
    push bc
    push ix
    ld hl,(object_lookup_name)
    push ix
    pop de
    call zx48_name_equal_record
    pop ix
    pop bc
    jr z,zx48_object_lookup_found
zx48_object_lookup_next:
    ld de,OBJ_RECORD_SIZE
    add ix,de
    inc c
    djnz zx48_object_lookup_loop
    ld a,E_NOENT
    scf
    ret
zx48_object_lookup_found:
    xor a
    or a
    ret

; Inputs: HL=NUL input, DE=record name[10]. Outputs Z exact equal.
zx48_name_equal_record:
    ld b,10
zx48_name_equal_loop:
    ld a,(hl)
    ld c,a
    ld a,(de)
    cp c
    ret nz
    inc hl
    inc de
    ld a,c
    or a
    ret z
    djnz zx48_name_equal_loop
    ld a,(hl)
    or a
    ret

; Inputs: A=dir, B=type, HL=name. Outputs new zero-length RAW record.
zx48_object_create:
    ld (object_lookup_dir),a
    ld a,b
    ld (object_create_type),a
    ld (object_lookup_name),hl
    push hl
    call zx48_name_validate
    pop hl
    ret c
    ld a,(object_lookup_dir)
    ld b,(object_create_type)
    call zx48_object_type_allowed
    ret c
    ld a,(object_lookup_dir)
    call zx48_object_lookup
    jr nc,zx48_object_create_exists
    ld ix,object_table
    ld b,RAM_OBJECT_COUNT
    ld c,0
zx48_object_create_find:
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_object_create_slot
    ld de,OBJ_RECORD_SIZE
    add ix,de
    inc c
    djnz zx48_object_create_find
    ld a,E_NOSPC
    scf
    ret
zx48_object_create_slot:
    ld hl,(object_lookup_name)
    push ix
    pop de
    ld b,10
zx48_object_create_copy_name:
    ld a,(hl)
    ld (de),a
    inc de
    inc hl
    or a
    jr z,zx48_object_create_pad
    djnz zx48_object_create_copy_name
    jr zx48_object_create_meta
zx48_object_create_pad:
    xor a
zx48_object_create_pad_loop:
    djnz zx48_object_create_pad_store
    jr zx48_object_create_meta
zx48_object_create_pad_store:
    ld (de),a
    inc de
    jr zx48_object_create_pad_loop
zx48_object_create_meta:
    ld a,(object_lookup_dir)
    ld (ix+OBJ_DIR_ID),a
    ld a,(object_create_type)
    ld (ix+OBJ_TYPE_ID),a
    xor a
    ld (ix+OBJ_FLAGS_BYTE),a
    ld (ix+OBJ_RESERVED_BYTE),a
    ld (ix+OBJ_LOGICAL_LENGTH),a
    ld (ix+OBJ_LOGICAL_LENGTH+1),a
    ld (ix+OBJ_STORAGE_LENGTH),a
    ld (ix+OBJ_STORAGE_LENGTH+1),a
    ld (ix+OBJ_ALLOCATION_PTR),a
    ld (ix+OBJ_ALLOCATION_PTR+1),a
    xor a
    or a
    ret
zx48_object_create_exists:
    ld a,E_EXIST
    scf
    ret

; Inputs A=dir,B=type. Public mutable placement rules only.
zx48_object_type_allowed:
    ld c,a
    ld a,b
    cp OBJ_TXT
    jr c,zx48_object_type_bad
    cp OBJ_CFG+1
    jr nc,zx48_object_type_bad
    ld a,c
    cp DIR_BIN
    jr z,zx48_object_type_bin
    cp DIR_ETC
    jr z,zx48_object_type_etc
    cp DIR_USERHOME
    jr z,zx48_object_type_ok
    cp DIR_TMP
    jr z,zx48_object_type_ok
zx48_object_type_bad:
    ld a,E_PERM
    scf
    ret
zx48_object_type_bin:
    ld a,b
    cp OBJ_BIN
    jr nz,zx48_object_type_bad
    jr zx48_object_type_ok
zx48_object_type_etc:
    ld a,b
    cp OBJ_TXT
    jr z,zx48_object_type_ok
    cp OBJ_CFG
    jr nz,zx48_object_type_bad
zx48_object_type_ok:
    xor a
    or a
    ret

; Inputs IX=object, DE=logical offset, HL=destination, BC=count.
; Outputs HL=bytes copied. RAW path only; packed path delegated to zxpack.
zx48_object_read:
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jp nz,zx48_zxpack_read
    ld (object_io_ptr),hl
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    or a
    sbc hl,de
    jr c,zx48_object_read_zero
    jr z,zx48_object_read_zero
    push hl
    or a
    sbc hl,bc
    pop hl
    jr nc,zx48_object_read_count_ok
    ld b,h
    ld c,l
zx48_object_read_count_ok:
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    add hl,de
    ld de,(object_io_ptr)
    push bc
    ld a,b
    or c
    jr z,zx48_object_read_pop_zero
    ldir
    pop hl
    xor a
    or a
    ret
zx48_object_read_pop_zero:
    pop bc
zx48_object_read_zero:
    ld hl,0
    xor a
    or a
    ret

; Inputs IX=RAW object, DE=offset, HL=source, BC=count.
; Outputs HL=count or carry set. Extending writes allocate/copy privately first.
zx48_object_write:
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr z,zx48_object_write_raw
    call zx48_zxpack_materialize
    ret c
zx48_object_write_raw:
    ld (object_io_ptr),hl
    ld (object_io_count),bc
    push de
    ld h,d
    ld l,e
    add hl,bc
    jr c,zx48_object_write_too_long_pop
    bit 7,h
    jr nz,zx48_object_write_too_long_pop
    ld (object_new_length),hl
    ld c,(ix+OBJ_LOGICAL_LENGTH)
    ld b,(ix+OBJ_LOGICAL_LENGTH+1)
    or a
    sbc hl,bc
    pop de
    jr c,zx48_object_write_in_place
    jr z,zx48_object_write_in_place
    ld bc,(object_new_length)
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (object_new_ptr),hl
    push de
    push ix
    ld e,(ix+OBJ_ALLOCATION_PTR)
    ld d,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_LOGICAL_LENGTH)
    ld b,(ix+OBJ_LOGICAL_LENGTH+1)
    ld a,b
    or c
    jr z,zx48_object_write_copy_new
    push hl
    ex de,hl
    pop de
    ldir
zx48_object_write_copy_new:
    pop ix
    pop de
    ld hl,(object_new_ptr)
    add hl,de
    ex de,hl
    ld hl,(object_io_ptr)
    ld bc,(object_io_count)
    ldir
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld a,h
    or l
    call nz,zx48_free
    ld hl,(object_new_ptr)
    ld (ix+OBJ_ALLOCATION_PTR),l
    ld (ix+OBJ_ALLOCATION_PTR+1),h
    ld hl,(object_new_length)
    ld (ix+OBJ_LOGICAL_LENGTH),l
    ld (ix+OBJ_LOGICAL_LENGTH+1),h
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h
    ld hl,(object_io_count)
    xor a
    or a
    ret
zx48_object_write_in_place:
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    add hl,de
    ex de,hl
    ld hl,(object_io_ptr)
    ld bc,(object_io_count)
    ldir
    ld hl,(object_io_count)
    xor a
    or a
    ret
zx48_object_write_too_long_pop:
    pop de
    ld a,E_NOSPC
    scf
    ret

; Called by handle layer on final close when decoder state exists. Decoder state
; is always FAST_REQUIRED 272 bytes in version 1.
zx48_object_final_close_decoder:
    ld l,(ix+OD_DECODER)
    ld h,(ix+OD_DECODER+1)
    ld bc,272
    jp zx48_free

; Inputs A=object slot. Marks close-time background candidate only.
zx48_object_mark_pack_candidate:
    cp RAM_OBJECT_COUNT
    ret nc
    ld e,a
    and 7
    ld c,a
    ld a,1
zx48_object_candidate_shift:
    dec c
    jr m,zx48_object_candidate_shift_done
    add a,a
    jr zx48_object_candidate_shift
zx48_object_candidate_shift_done:
    ld c,a
    ld a,e
    srl a
    srl a
    srl a
    ld e,a
    ld d,0
    ld hl,object_pack_candidates
    add hl,de
    ld a,(hl)
    or c
    ld (hl),a
    ret

; Inputs none. PID0 calls at most once per idle cycle.
zx48_object_idle_pack_one:
    ld hl,object_pack_candidates
    ld b,4
    ld c,0
zx48_object_idle_pack_byte:
    ld a,(hl)
    or a
    jr nz,zx48_object_idle_pack_found
    inc hl
    ld a,c
    add a,8
    ld c,a
    djnz zx48_object_idle_pack_byte
    ret
zx48_object_idle_pack_found:
    ld e,a
    ld d,0
zx48_object_idle_pack_bit:
    rra
    jr c,zx48_object_idle_pack_clear
    inc c
    jr zx48_object_idle_pack_bit
zx48_object_idle_pack_clear:
    ld a,1
    ld b,c
    and 7
    ld b,a
    ; Candidate bit clearing is conservative: clear the entire byte before the
    ; bounded pack attempt so reopen/reuse can never inherit a stale request.
    xor a
    ld (hl),a
    ld a,c
    call zx48_zxpack_try_slot
    ret

object_lookup_dir:
    db 0
object_create_type:
    db 0
object_lookup_name:
    dw 0
object_io_ptr:
    dw 0
object_io_count:
    dw 0
object_new_length:
    dw 0
object_new_ptr:
    dw 0
session_cwd:
    db DIR_ROOT
session_user_len:
    db 0
session_user:
    defs 8,0
object_pack_candidates:
    defs 4,0
object_table:
    defs RAM_OBJECT_COUNT*OBJ_RECORD_SIZE,0
    ENDM
