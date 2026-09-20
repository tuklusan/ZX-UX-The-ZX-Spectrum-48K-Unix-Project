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
; Fixed namespace plus thirty-two mutable 20-byte RAM object records.

OBJ_NAME                  EQU 0
OBJ_DIR_ID                EQU 10
OBJ_TYPE_ID               EQU 11
OBJ_FLAGS_BYTE            EQU 12
OBJ_RESERVED_BYTE         EQU 13
OBJ_LOGICAL_LENGTH        EQU 14
OBJ_STORAGE_LENGTH        EQU 16
OBJ_ALLOCATION_PTR        EQU 18
PATH_KIND_DIR             EQU 0
PATH_KIND_BASE            EQU 1

;
; P4.03 mutable-record footprint. Later Phase-4 steps attach namespace and I/O
; semantics; this macro freezes the record bytes, capacity and representation
; invariants without pulling the full object-store implementation into the kernel.
;
    MACRO EMIT_OBJECT_RECORD_ROUTINES
zx48_object_records_init:
    xor a
    ld hl,object_record_table
    ld de,object_record_table+1
    ld bc,RAM_OBJECT_COUNT*OBJ_RECORD_SIZE-1
    ld (hl),a
    ldir
    ret

; A=slot -> IX exact 20-byte record, C=slot.
zx48_object_record_ptr:
    cp RAM_OBJECT_COUNT
    jr nc,.invalid
    ld c,a
    ld ix,object_record_table
    or a
    ret z
    ld b,a
    ld de,OBJ_RECORD_SIZE
.ptr_loop:
    add ix,de
    djnz .ptr_loop
    xor a
    or a
    ret
.invalid:
    ld a,E_INVAL
    scf
    ret

; Claim the first free mutable slot. Occupancy is type!=0; P4.04 freezes type IDs.
zx48_object_record_claim:
    ld ix,object_record_table
    ld c,0
    ld b,RAM_OBJECT_COUNT
.claim_loop:
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,.claim
    ld de,OBJ_RECORD_SIZE
    add ix,de
    inc c
    djnz .claim_loop
    ld a,E_NOSPC
    scf
    ret
.claim:
    ld (ix+OBJ_TYPE_ID),1
    xor a
    or a
    ret

; IX=record. Validate only P4.03 representation/accounting invariants.
zx48_object_record_validate:
    ld a,(ix+OBJ_RESERVED_BYTE)
    or a
    jr nz,.bad
    ld a,(ix+OBJ_FLAGS_BYTE)
    and $fe
    jr nz,.bad

    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld e,(ix+OBJ_STORAGE_LENGTH)
    ld d,(ix+OBJ_STORAGE_LENGTH+1)
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr nz,.packed

    ; RAW: physical and logical lengths are identical.
    or a
    sbc hl,de
    jr nz,.bad
    jr .allocation
.packed:
    ; PACKED: physical length is strictly smaller than logical length.
    or a
    sbc hl,de
    jr c,.bad
    jr z,.bad

.allocation:
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld a,d
    or e
    jr nz,.resident
    ld a,h
    or l
    jr nz,.bad
    xor a
    or a
    ret

.resident:
    bit 0,l
    jr nz,.bad
    ld a,h
    cp $60
    jr c,.bad
    cp $e0
    jr nc,.bad

    ; Allocator ownership is storage_length rounded only to two-byte alignment.
    ld b,d
    ld c,e
    bit 0,c
    jr z,.rounded
    inc bc
    ld a,b
    or c
    jr z,.bad
.rounded:
    add hl,bc
    jr c,.bad
    ld a,h
    cp $e0
    jr c,.ok
    jr nz,.bad
    ld a,l
    or a
    jr nz,.bad
.ok:
    xor a
    or a
    ret
.bad:
    ld a,E_INVAL
    scf
    ret

; Ordinary mutable payloads request COLD_PREFERRED; allocator policy owns fallback.
zx48_object_payload_class:
    ld a,ALLOC_COLD_PREFERRED
    ret

object_record_table:
    defs RAM_OBJECT_COUNT*OBJ_RECORD_SIZE,0
object_record_table_end:
; Pinned bootstrap metadata is separate and consumes no mutable record slot.
pinned_bootstrap_metadata: dw 0
    ENDM

;
; P4.04 type/state placement contract. This remains independently emit-able so the
; exact matrix can be qualified without admitting later object open/I/O semantics.
;
    MACRO EMIT_OBJECT_TYPE_ROUTINES
; B=type. M48O payload types are exactly TXT..SYS (1..11).
zx48_object_payload_type_validate:
    ld a,b
    cp OBJ_TXT
    jr c,zx48_object_payload_type_bad
    cp OBJ_SYS+1
    jr nc,zx48_object_payload_type_bad
    xor a
    or a
    ret
zx48_object_payload_type_bad:
    ld a,E_INVAL
    scf
    ret

; A=directory,B=type. Public mutable placement excludes SYSTEM and fixed roots.
zx48_object_public_type_allowed:
    ld c,a
    ld a,b
    cp OBJ_TXT
    jr c,zx48_object_public_type_perm
    cp OBJ_CFG+1
    jr nc,zx48_object_public_type_perm
    ld a,c
    cp DIR_BIN
    jr z,zx48_object_public_type_bin
    cp DIR_ETC
    jr z,zx48_object_public_type_etc
    cp DIR_USERHOME
    jr z,zx48_object_public_type_ok
    cp DIR_TMP
    jr z,zx48_object_public_type_ok
    jr zx48_object_public_type_perm
zx48_object_public_type_bin:
    ld a,b
    cp OBJ_BIN
    jr z,zx48_object_public_type_ok
    jr zx48_object_public_type_perm
zx48_object_public_type_etc:
    ld a,b
    cp OBJ_TXT
    jr z,zx48_object_public_type_ok
    cp OBJ_CFG
    jr z,zx48_object_public_type_ok
    jr zx48_object_public_type_perm
zx48_object_public_type_ok:
    xor a
    or a
    ret
zx48_object_public_type_perm:
    ld a,E_PERM
    scf
    ret

; A=directory,B=type. Internal bootstrap owns only SYSTEM FNT/SYS publication.
zx48_object_bootstrap_type_allowed:
    cp DIR_SYSTEM
    jr nz,zx48_object_bootstrap_type_perm
    ld a,b
    cp OBJ_FNT
    jr z,zx48_object_bootstrap_type_ok
    cp OBJ_SYS
    jr z,zx48_object_bootstrap_type_ok
zx48_object_bootstrap_type_perm:
    ld a,E_PERM
    scf
    ret
zx48_object_bootstrap_type_ok:
    xor a
    or a
    ret

; A=namespace state. Exact IDs 0..3 only.
zx48_namespace_state_validate:
    cp STATE_PSEUDO+1
    jr nc,zx48_namespace_state_bad
    xor a
    or a
    ret
zx48_namespace_state_bad:
    ld a,E_INVAL
    scf
    ret

; A=public object flags. Only bit0 OBJ_PACKED may be set.
zx48_object_public_flags_validate:
    and $fe
    jr nz,zx48_object_public_flags_bad
    xor a
    or a
    ret
zx48_object_public_flags_bad:
    ld a,E_INVAL
    scf
    ret

; B=type,HL=reported length. Namespace-only DIR/DEV lengths must be zero.
zx48_object_namespace_length_validate:
    ld a,b
    cp OBJ_DIR
    jr z,zx48_object_namespace_length_must_zero
    cp OBJ_DEV
    jr z,zx48_object_namespace_length_must_zero
    xor a
    or a
    ret
zx48_object_namespace_length_must_zero:
    ld a,h
    or l
    jr nz,zx48_object_namespace_length_bad
    xor a
    or a
    ret
zx48_object_namespace_length_bad:
    ld a,E_INVAL
    scf
    ret

; A=namespace state, HL=resident logical length. BCAT-only tape entries are unknown.
zx48_object_visible_length:
    cp STATE_TAPE_BACKED
    jr z,zx48_object_visible_length_unknown
    cp STATE_PSEUDO+1
    jr nc,zx48_object_visible_length_bad
    xor a
    or a
    ret
zx48_object_visible_length_unknown:
    ld hl,0-1
    xor a
    or a
    ret
zx48_object_visible_length_bad:
    ld a,E_INVAL
    scf
    ret

; Canonical target line separator for TXT/C/ASM/CFG content.
zx48_text_line_separator:
    ld a,$0a
    ret
    ENDM

    MACRO EMIT_OBJECT_ROUTINES
zx48_objects_init:
    xor a
    ld hl,object_table
    ld de,object_table+1
    ld bc,RAM_OBJECT_COUNT*OBJ_RECORD_SIZE-1
    ld (hl),a
    ldir
    ld (session_user_len),a
    ld hl,0
    ld (bincat_ptr),hl
    ret

zx48_objects_set_bincat:
    ld (bincat_ptr),hl
    ret

; HL=NUL exact-case base name. A=len on success.
zx48_name_validate:
    ld (object_name_ptr),hl
    ld b,0
zx48_name_validate_loop:
    ld a,(hl)
    or a
    jr z,zx48_name_validate_end
    inc b
    ld a,b
    cp 11
    jr nc,zx48_name_long
    ld a,(hl)
    call zx48_name_char_valid
    jr c,zx48_name_bad
    inc hl
    jr zx48_name_validate_loop
zx48_name_validate_end:
    ld a,b
    or a
    jr z,zx48_name_bad
    ld hl,(object_name_ptr)
    cp 1
    jr nz,zx48_name_ok
    ld a,(hl)
    cp '.'
    jr z,zx48_name_bad
zx48_name_ok:
    ld a,b
    or a
    ret
zx48_name_long:
    ld a,E_TOOLONG
    scf
    ret
zx48_name_bad:
    ld a,E_INVAL
    scf
    ret
zx48_name_char_valid:
    cp '0'
    jr c,zx48_name_punct
    cp '9'+1
    jr c,zx48_name_char_ok
    cp 'A'
    jr c,zx48_name_punct
    cp 'Z'+1
    jr c,zx48_name_char_ok
    cp 'a'
    jr c,zx48_name_punct
    cp 'z'+1
    jr c,zx48_name_char_ok
zx48_name_punct:
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

; HL=NUL name, DE=fixed name[10]. Z iff exact.
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

; A=slot -> IX record.
zx48_object_ptr_slot:
    cp RAM_OBJECT_COUNT
    jr nc,zx48_object_invalid
    ld c,a
    ld ix,object_table
    or a
    ret z
    ld b,a
    ld de,OBJ_RECORD_SIZE
zx48_object_ptr_loop:
    add ix,de
    djnz zx48_object_ptr_loop
    xor a
    or a
    ret

; A=dir, HL=name -> IX record,C=slot.
zx48_object_lookup:
    ld (object_lookup_dir),a
    ld (object_lookup_name),hl
    ld ix,object_table
    ld c,0
    ld b,RAM_OBJECT_COUNT
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
    pop de
    ld hl,(object_lookup_name)
    call zx48_name_equal_record
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

; A=dir,B=type placement matrix.
zx48_object_type_allowed:
    ld c,a
    ld a,b
    cp OBJ_TXT
    jr c,zx48_object_perm
    cp OBJ_CFG+1
    jr nc,zx48_object_perm
    ld a,c
    cp DIR_BIN
    jr z,zx48_object_type_bin
    cp DIR_ETC
    jr z,zx48_object_type_etc
    cp DIR_USERHOME
    jr z,zx48_object_type_ok
    cp DIR_TMP
    jr z,zx48_object_type_ok
    jr zx48_object_perm
zx48_object_type_bin:
    ld a,b
    cp OBJ_BIN
    jr z,zx48_object_type_ok
    jr zx48_object_perm
zx48_object_type_etc:
    ld a,b
    cp OBJ_TXT
    jr z,zx48_object_type_ok
    cp OBJ_CFG
    jr nz,zx48_object_perm
zx48_object_type_ok:
    xor a
    or a
    ret
zx48_object_perm:
    ld a,E_PERM
    scf
    ret

; A=dir,B=type,HL=name -> C=slot,IX record.
zx48_object_create:
    ld (object_lookup_dir),a
    ld a,b
    ld (object_create_type),a
    ld (object_lookup_name),hl
    call zx48_name_validate
    ret c
    ld a,(object_lookup_dir)
    ld b,(object_create_type)
    call zx48_object_type_allowed
    ret c
    ld a,(object_lookup_dir)
    ld hl,(object_lookup_name)
    call zx48_object_lookup
    jr nc,zx48_object_exists
    ld ix,object_table
    ld c,0
    ld b,RAM_OBJECT_COUNT
zx48_object_create_find:
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_object_create_found
    ld de,OBJ_RECORD_SIZE
    add ix,de
    inc c
    djnz zx48_object_create_find
    ld a,E_NOSPC
    scf
    ret
zx48_object_create_found:
    ld (object_slot),c
    ld hl,(object_lookup_name)
    push ix
    pop de
    ld b,10
zx48_object_name_copy:
    ld a,(hl)
    ld (de),a
    inc de
    inc hl
    or a
    jr z,zx48_object_name_pad
    djnz zx48_object_name_copy
    jr zx48_object_create_meta
zx48_object_name_pad:
    xor a
zx48_object_name_pad_loop:
    dec b
    jr z,zx48_object_create_meta
    ld (de),a
    inc de
    jr zx48_object_name_pad_loop
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
    ld c,(object_slot)
    xor a
    or a
    ret
zx48_object_exists:
    ld a,E_EXIST
    scf
    ret

; IX=object, DE=offset, HL=dst, BC=count.
zx48_object_read:
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jp nz,zx48_zxpack_read
    ld (object_io_ptr),hl
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    or a
    sbc hl,de
    jr c,zx48_object_zero
    jr z,zx48_object_zero
    push hl
    or a
    sbc hl,bc
    pop hl
    jr nc,zx48_object_read_count
    ld b,h
    ld c,l
zx48_object_read_count:
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
zx48_object_zero:
    ld hl,0
    xor a
    or a
    ret

; IX=object, DE=offset, HL=src, BC=count. Extending writes are allocate-copy-commit.
zx48_object_write:
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    call nz,zx48_zxpack_materialize
    ret c
    ld (object_io_ptr),hl
    ld (object_io_count),bc
    ld (object_io_offset),de
    ld h,d
    ld l,e
    add hl,bc
    jr c,zx48_object_nospc
    bit 7,h
    jr nz,zx48_object_nospc
    ld (object_new_length),hl
    ld c,(ix+OBJ_LOGICAL_LENGTH)
    ld b,(ix+OBJ_LOGICAL_LENGTH+1)
    or a
    sbc hl,bc
    jr c,zx48_object_write_inplace
    jr z,zx48_object_write_inplace
    ld bc,(object_new_length)
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (object_new_ptr),hl
    ld c,(ix+OBJ_LOGICAL_LENGTH)
    ld b,(ix+OBJ_LOGICAL_LENGTH+1)
    ld a,b
    or c
    jr z,zx48_object_write_new_data
    push ix
    ld e,(ix+OBJ_ALLOCATION_PTR)
    ld d,(ix+OBJ_ALLOCATION_PTR+1)
    ex de,hl
    ld de,(object_new_ptr)
    ldir
    pop ix
zx48_object_write_new_data:
    ld hl,(object_new_ptr)
    ld de,(object_io_offset)
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
zx48_object_write_inplace:
    ld hl,(object_io_count)
    ld a,h
    or l
    ret z
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld de,(object_io_offset)
    add hl,de
    ex de,hl
    ld hl,(object_io_ptr)
    ld bc,(object_io_count)
    ldir
    ld hl,(object_io_count)
    xor a
    or a
    ret
zx48_object_nospc:
    ld a,E_NOSPC
    scf
    ret

; Resolve path to path_dir/path_name. Fixed namespace only; repeated slash allowed.
; The 31-byte limit is applied to the normalized absolute result, not raw input.
zx48_path_resolve:
    ld (path_source),hl
    ld a,(hl)
    or a
    jr z,zx48_path_invalid
    ld hl,(path_source)
    ld a,(hl)
    cp '/'
    jr z,zx48_path_abs
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_CWD)
    ld (path_dir),a
    ld hl,(path_source)
    jr zx48_path_component
zx48_path_abs:
    xor a
    ld (path_dir),a
zx48_path_skip:
    inc hl
zx48_path_component:
    ld a,(hl)
    cp '/'
    jr z,zx48_path_skip
    or a
    jr z,zx48_path_dir_done
    ld de,path_name
    ld b,0
zx48_path_copy:
    ld a,(hl)
    or a
    jr z,zx48_path_component_end
    cp '/'
    jr z,zx48_path_component_end
    inc b
    ld a,b
    cp 11
    jr nc,zx48_path_long
    ld a,(hl)
    ld (de),a
    inc de
    inc hl
    jr zx48_path_copy
zx48_path_component_end:
    xor a
    ld (de),a
    ld (path_after),hl
    ; Dot and dot-dot are directory navigation.
    ld hl,path_name
    ld de,path_dot
    call zx48_cstr_equal
    jr z,zx48_path_component_next
    ld hl,path_name
    ld de,path_dotdot
    call zx48_cstr_equal
    jr z,zx48_path_parent
    call zx48_path_child_dir
    jr nc,zx48_path_component_next
    ; Non-directory component must be final basename.
    ld hl,(path_after)
zx48_path_final_slash:
    ld a,(hl)
    cp '/'
    jr nz,zx48_path_final_check
    inc hl
    jr zx48_path_final_slash
zx48_path_final_check:
    or a
    jr nz,zx48_path_noent
    ld hl,(path_after)
    ld a,(hl)
    cp '/'
    jr z,zx48_path_empty_final
    ld hl,path_name
    call zx48_name_validate
    ret c
    ld c,PATH_KIND_BASE
    jp zx48_path_finish
zx48_path_parent:
    ld a,(path_dir)
    cp DIR_USERHOME
    jr z,zx48_path_parent_home
    or a
    jr z,zx48_path_invalid
    xor a
    ld (path_dir),a
    jr zx48_path_component_next
zx48_path_parent_home:
    ld a,DIR_HOME
    ld (path_dir),a
zx48_path_component_next:
    ld hl,(path_after)
    jr zx48_path_component
zx48_path_dir_done:
    ld c,PATH_KIND_DIR
    jp zx48_path_finish

; C=PATH_KIND_*. Enforce canonical normalized absolute path length <=31.
zx48_path_finish:
    ld a,c
    ld (path_result_kind),a
    ld a,(path_dir)
    cp DIR_ROOT
    jr z,zx48_path_len_root
    cp DIR_HOME
    jr z,zx48_path_len_home
    cp DIR_USERHOME
    jr z,zx48_path_len_userhome
    ld b,4
    jr zx48_path_len_kind
zx48_path_len_root:
    ld b,1
    jr zx48_path_len_kind
zx48_path_len_home:
    ld b,5
    jr zx48_path_len_kind
zx48_path_len_userhome:
    ld a,(session_user_len)
    add a,6
    ld b,a
zx48_path_len_kind:
    ld a,(path_result_kind)
    cp PATH_KIND_BASE
    jr nz,zx48_path_len_check
    ld a,(path_dir)
    cp DIR_ROOT
    jr z,zx48_path_len_name
    inc b
zx48_path_len_name:
    ld hl,path_name
zx48_path_len_name_loop:
    ld a,(hl)
    or a
    jr z,zx48_path_len_check
    inc b
    inc hl
    jr zx48_path_len_name_loop
zx48_path_len_check:
    ld a,b
    cp 32
    jr nc,zx48_path_long
    ld a,(path_dir)
    ld c,(path_result_kind)
    or a
    ret
zx48_path_empty_final:
zx48_path_invalid:
    ld a,E_INVAL
    scf
    ret
zx48_path_long:
    ld a,E_TOOLONG
    scf
    ret
zx48_path_noent:
    ld a,E_NOENT
    scf
    ret

zx48_path_child_dir:
    ld a,(path_dir)
    or a
    jr z,zx48_path_child_root
    cp DIR_HOME
    jr z,zx48_path_child_home
    scf
    ret
zx48_path_child_root:
    ld hl,path_name
    ld de,path_bin
    call zx48_cstr_equal
    jr z,zx48_path_set_bin
    ld hl,path_name
    ld de,path_dev
    call zx48_cstr_equal
    jr z,zx48_path_set_dev
    ld hl,path_name
    ld de,path_etc
    call zx48_cstr_equal
    jr z,zx48_path_set_etc
    ld hl,path_name
    ld de,path_home
    call zx48_cstr_equal
    jr z,zx48_path_set_home
    ld hl,path_name
    ld de,path_tmp
    call zx48_cstr_equal
    jr z,zx48_path_set_tmp
    scf
    ret
zx48_path_child_home:
    ld a,(session_user_len)
    or a
    jr z,zx48_path_child_fail
    ld hl,path_name
    ld de,session_user
    call zx48_cstr_equal
    jr nz,zx48_path_child_fail
    ld a,DIR_USERHOME
    ld (path_dir),a
    xor a
    or a
    ret
zx48_path_child_fail:
    scf
    ret
zx48_path_set_bin:
    ld a,DIR_BIN
    jr zx48_path_set
zx48_path_set_dev:
    ld a,DIR_DEV
    jr zx48_path_set
zx48_path_set_etc:
    ld a,DIR_ETC
    jr zx48_path_set
zx48_path_set_home:
    ld a,DIR_HOME
    jr zx48_path_set
zx48_path_set_tmp:
    ld a,DIR_TMP
zx48_path_set:
    ld (path_dir),a
    xor a
    or a
    ret
zx48_cstr_equal:
    ld a,(de)
    cp (hl)
    ret nz
    or a
    ret z
    inc de
    inc hl
    jr zx48_cstr_equal

; A=len, HL=username bytes. First char lower-case; later lower-case/digit/_/-.
zx48_namespace_set_user:
    cp 1
    jr c,zx48_object_invalid
    cp 9
    jr nc,zx48_object_invalid
    ld (session_user_len),a
    ld b,a
    ld de,session_user
    ld c,0
zx48_user_copy:
    ld a,(hl)
    ld (de),a
    ld a,c
    or a
    jr nz,zx48_user_later
    ld a,(hl)
    cp 'a'
    jr c,zx48_user_bad
    cp 'z'+1
    jr nc,zx48_user_bad
    jr zx48_user_store
zx48_user_later:
    ld a,(hl)
    cp 'a'
    jr c,zx48_user_digit
    cp 'z'+1
    jr c,zx48_user_store
zx48_user_digit:
    cp '0'
    jr c,zx48_user_punct
    cp '9'+1
    jr c,zx48_user_store
zx48_user_punct:
    cp '_'
    jr z,zx48_user_store
    cp '-'
    jr nz,zx48_user_bad
zx48_user_store:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    inc c
    djnz zx48_user_copy
    xor a
    ld (de),a
    ld a,1
    call zx48_process_ptr
    ld (ix+PROC_CWD),DIR_USERHOME
    xor a
    or a
    ret
zx48_user_bad:
    xor a
    ld (session_user_len),a
zx48_object_invalid:
    ld a,E_INVAL
    scf
    ret

; HL=path,C=flags,B=create type -> HL handle.
zx48_object_open:
    ld (object_open_flags),c
    ld a,b
    ld (object_open_type),a
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jr nz,zx48_object_perm
    ld a,(path_dir)
    cp DIR_DEV
    jr z,zx48_open_device
    ld hl,path_name
    call zx48_object_lookup
    jr nc,zx48_open_existing
    ld a,(object_open_flags)
    and O_CREATE
    jr z,zx48_path_noent
    ld a,(object_open_type)
    or a
    jr z,zx48_object_invalid
    ld b,a
    ld a,(path_dir)
    ld hl,path_name
    call zx48_object_create
    ret c
zx48_open_existing:
    ld (object_slot),c
    ld a,(object_open_flags)
    and O_EXCL
    jr nz,zx48_object_exists
    ld a,OD_KIND_OBJECT
    ld b,(object_open_flags)
    ld c,(object_slot)
    call zx48_od_create
    ret c
    ld (object_open_od),a
    ld a,(current_pid)
    call zx48_process_lookup
    jr c,zx48_open_rollback
    ld a,(object_open_od)
    ld c,HANDLE_FREE
    call zx48_handle_install
    ret nc
zx48_open_rollback:
    ld a,(object_open_od)
    call zx48_od_release_id
    ld a,E_NOSPC
    scf
    ret
zx48_open_device:
    ld a,(object_open_type)
    or a
    jr nz,zx48_object_invalid
    ld hl,path_name
    ld de,path_tty
    call zx48_cstr_equal
    jr z,zx48_open_tty
    ld hl,path_name
    ld de,path_null
    call zx48_cstr_equal
    jr z,zx48_open_null
    ld hl,path_name
    ld de,path_tape
    call zx48_cstr_equal
    jr nz,zx48_path_noent
    ld a,OD_KIND_TAPE
    jr zx48_open_dev_create
zx48_open_tty:
    ld a,OD_KIND_TTY
    jr zx48_open_dev_create
zx48_open_null:
    ld a,OD_KIND_NULL
zx48_open_dev_create:
    ld b,(object_open_flags)
    ld c,0
    call zx48_od_create
    ret c
    ld (object_open_od),a
    ld a,(current_pid)
    call zx48_process_lookup
    jr c,zx48_open_rollback
    ld a,(object_open_od)
    ld c,HANDLE_FREE
    call zx48_handle_install
    ret

; IX=OD.
zx48_object_read_od:
    ld (object_od_ptr),ix
    ld a,(ix+OD_ACCESS)
    and O_READ
    jr z,zx48_object_perm
    ld a,(ix+OD_IDENTITY)
    call zx48_object_ptr_slot
    ret c
    ld e,(ix+OBJ_LOGICAL_LENGTH) ; temporary overwritten below after OD restore
    ld ix,(object_od_ptr)
    ld e,(ix+OD_OFFSET)
    ld d,(ix+OD_OFFSET+1)
    ld a,(ix+OD_IDENTITY)
    push de
    call zx48_object_ptr_slot
    pop de
    ret c
    call zx48_object_read
    ret c
    push hl
    ex de,hl
    ld ix,(object_od_ptr)
    ld l,(ix+OD_OFFSET)
    ld h,(ix+OD_OFFSET+1)
    add hl,de
    ld (ix+OD_OFFSET),l
    ld (ix+OD_OFFSET+1),h
    pop hl
    ret
zx48_object_write_od:
    ld (object_od_ptr),ix
    ld a,(ix+OD_ACCESS)
    and O_WRITE
    jr z,zx48_object_perm
    ld e,(ix+OD_OFFSET)
    ld d,(ix+OD_OFFSET+1)
    ld a,(ix+OD_IDENTITY)
    push de
    call zx48_object_ptr_slot
    pop de
    ret c
    ld a,(object_od_ptr)
    ; APPEND uses logical EOF regardless of current offset.
    ld ix,(object_od_ptr)
    ld a,(ix+OD_ACCESS)
    and O_APPEND
    jr z,zx48_object_write_have_offset
    ld a,(ix+OD_IDENTITY)
    call zx48_object_ptr_slot
    ld e,(ix+OBJ_LOGICAL_LENGTH)
    ld d,(ix+OBJ_LOGICAL_LENGTH+1)
zx48_object_write_have_offset:
    call zx48_object_write
    ret c
    push hl
    ex de,hl
    ld ix,(object_od_ptr)
    ld l,(ix+OD_OFFSET)
    ld h,(ix+OD_OFFSET+1)
    add hl,de
    ld (ix+OD_OFFSET),l
    ld (ix+OD_OFFSET+1),h
    pop hl
    ret
zx48_object_seek_od:
    ld (object_seek),hl
    ld a,(ix+OD_IDENTITY)
    call zx48_object_ptr_slot
    ret c
    ld e,(ix+OBJ_LOGICAL_LENGTH)
    ld d,(ix+OBJ_LOGICAL_LENGTH+1)
    ld hl,(object_seek)
    or a
    sbc hl,de
    jr c,zx48_seek_ok
    jr z,zx48_seek_ok
    ld a,E_INVAL
    scf
    ret
zx48_seek_ok:
    ld ix,(object_od_ptr)
    ld hl,(object_seek)
    ld (ix+OD_OFFSET),l
    ld (ix+OD_OFFSET+1),h
    xor a
    or a
    ret

zx48_object_description_final_close:
    ret
zx48_object_final_close_decoder:
    ld bc,272
    jp zx48_free

; HL path; mutable RAM object only.
zx48_object_remove:
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jr nz,zx48_object_perm
    ld a,(path_dir)
    ld hl,path_name
    call zx48_object_lookup
    ret c
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld a,h
    or l
    call nz,zx48_free
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,OBJ_RECORD_SIZE-1
    ldir
    xor a
    or a
    ret

; HL -> old_ptr,new_ptr. Requires absent destination or same source; compact V1
; metadata rename keeps payload allocation unchanged.
zx48_object_rename:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld (rename_new),bc
    ex de,hl
    call zx48_path_resolve
    ret c
    ld a,(path_dir)
    ld hl,path_name
    call zx48_object_lookup
    ret c
    ld (rename_record),ix
    ld hl,(rename_new)
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jr nz,zx48_object_perm
    ld ix,(rename_record)
    ld b,(ix+OBJ_TYPE_ID)
    ld a,(path_dir)
    call zx48_object_type_allowed
    ret c
    ld a,(path_dir)
    ld (ix+OBJ_DIR_ID),a
    ld hl,path_name
    push ix
    pop de
    ld bc,10
    ldir
    xor a
    or a
    ret

; HL -> STAT1 {path_ptr,out_ptr}.
zx48_object_stat_record:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld (object_stat_out),bc
    ex de,hl
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_DIR
    jr z,zx48_stat_dir
    ld a,(path_dir)
    cp DIR_DEV
    jr z,zx48_stat_dev
    ld hl,path_name
    call zx48_object_lookup
    ret c
    ld de,(object_stat_out)
    ld a,(ix+OBJ_TYPE_ID)
    ld (de),a
    inc de
    ld a,(ix+OBJ_FLAGS_BYTE)
    ld (de),a
    inc de
    ld a,(ix+OBJ_LOGICAL_LENGTH)
    ld (de),a
    inc de
    ld a,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (de),a
    inc de
    ld a,(ix+OBJ_STORAGE_LENGTH)
    ld (de),a
    inc de
    ld a,(ix+OBJ_STORAGE_LENGTH+1)
    ld (de),a
    inc de
    ld a,(ix+OBJ_DIR_ID)
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld (de),a
    or a
    ret
zx48_stat_dir:
    ld a,OBJ_DIR
    jr zx48_stat_pseudo
zx48_stat_dev:
    ld a,OBJ_DEV
zx48_stat_pseudo:
    ld de,(object_stat_out)
    ld (de),a
    inc de
    xor a
    ld b,6
zx48_stat_zero:
    ld (de),a
    inc de
    djnz zx48_stat_zero
    ld a,(path_dir)
    ld (de),a
    inc de
    ld a,STATE_PSEUDO
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de
    ld (de),a
    or a
    ret

; Compatibility entry used by syscall layer: HL=path, DE=10-byte out.
zx48_object_stat:
    ld (object_stat_out),de
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_DIR
    jr z,zx48_stat_dir
    ld a,(path_dir)
    cp DIR_DEV
    jr z,zx48_stat_dev
    ld hl,path_name
    call zx48_object_lookup
    ret c
    ld de,(object_stat_out)
    ld a,(ix+OBJ_TYPE_ID)
    ld (de),a
    inc de
    ld a,(ix+OBJ_FLAGS_BYTE)
    ld (de),a
    inc de
    ld a,(ix+OBJ_LOGICAL_LENGTH)
    ld (de),a
    inc de
    ld a,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (de),a
    inc de
    ld a,(ix+OBJ_STORAGE_LENGTH)
    ld (de),a
    inc de
    ld a,(ix+OBJ_STORAGE_LENGTH+1)
    ld (de),a
    inc de
    ld a,(ix+OBJ_DIR_ID)
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld (de),a
    or a
    ret

; HL=directory path,C=index,DE=LISTOUT. Fixed dirs enumerate canonical tables;
; mutable dirs enumerate occupied records in slot order (host acceptance verifies
; bytewise order when builders insert canonical boot objects).
zx48_object_list:
    ld (object_list_out),de
    ld (object_list_index),c
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_DIR
    jr nz,zx48_object_perm
    ld a,(path_dir)
    cp DIR_ROOT
    jr z,zx48_list_root
    cp DIR_DEV
    jr z,zx48_list_dev
    cp DIR_HOME
    jr z,zx48_list_home
    ld ix,object_table
    ld b,RAM_OBJECT_COUNT
    ld c,0
zx48_list_dynamic:
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_list_dynamic_next
    ld a,(ix+OBJ_DIR_ID)
    ld d,a
    ld a,(path_dir)
    cp d
    jr nz,zx48_list_dynamic_next
    ld a,(object_list_index)
    or a
    jr z,zx48_list_emit_object
    dec a
    ld (object_list_index),a
zx48_list_dynamic_next:
    ld de,OBJ_RECORD_SIZE
    add ix,de
    djnz zx48_list_dynamic
    jr zx48_list_end
zx48_list_emit_object:
    push ix
    pop hl
    ld de,(object_list_out)
    ld bc,10
    ldir
    ld a,(ix+OBJ_TYPE_ID)
    ld (de),a
    inc de
    ld a,(ix+OBJ_FLAGS_BYTE)
    ld (de),a
    inc de
    ld a,(ix+OBJ_LOGICAL_LENGTH)
    ld (de),a
    inc de
    ld a,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de
    ld a,(ix+OBJ_DIR_ID)
    ld (de),a
    ld hl,1
    or a
    ret
zx48_list_root:
    ld hl,list_root
    ld b,5
    ld a,OBJ_DIR
    jr zx48_list_fixed
zx48_list_dev:
    ld hl,list_dev
    ld b,3
    ld a,OBJ_DEV
    jr zx48_list_fixed
zx48_list_home:
    ld a,(session_user_len)
    or a
    jr z,zx48_list_end
    ld hl,session_user
    ld b,1
    ld a,OBJ_DIR
zx48_list_fixed:
    ld (list_fixed_type),a
    ld a,(object_list_index)
    cp b
    jr nc,zx48_list_end
    or a
    jr z,zx48_list_fixed_emit
    ld c,a
zx48_list_fixed_seek:
    ld de,11
    add hl,de
    dec c
    jr nz,zx48_list_fixed_seek
zx48_list_fixed_emit:
    ld de,(object_list_out)
    ld bc,10
    ldir
    ld a,(list_fixed_type)
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld a,STATE_PSEUDO
    ld (de),a
    inc de
    ld a,(path_dir)
    ld (de),a
    ld hl,1
    xor a
    or a
    ret
zx48_list_end:
    ld hl,0
    xor a
    or a
    ret

zx48_object_chdir:
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_DIR
    jr nz,zx48_path_noent
    ld a,(path_dir)
    ld (object_cwd),a
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    ld a,(object_cwd)
    ld (ix+PROC_CWD),a
    xor a
    or a
    ret

; HL=buffer,BC=capacity.
zx48_object_getcwd:
    ld (object_io_ptr),hl
    ld (object_io_count),bc
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_CWD)
    call zx48_build_cwd
    ret c
    ld a,(cwd_length)
    inc a
    ld e,a
    ld d,0
    ld hl,(object_io_count)
    or a
    sbc hl,de
    jr c,zx48_object_nospc
    ld hl,cwd_buffer
    ld de,(object_io_ptr)
    ld a,(cwd_length)
    inc a
    ld c,a
    ld b,0
    ldir
    ld a,(cwd_length)
    ld l,a
    ld h,0
    xor a
    or a
    ret
zx48_build_cwd:
    ld hl,cwd_root
    cp DIR_ROOT
    jr z,zx48_build_copy
    ld hl,cwd_bin
    cp DIR_BIN
    jr z,zx48_build_copy
    ld hl,cwd_dev
    cp DIR_DEV
    jr z,zx48_build_copy
    ld hl,cwd_etc
    cp DIR_ETC
    jr z,zx48_build_copy
    ld hl,cwd_home
    cp DIR_HOME
    jr z,zx48_build_copy
    ld hl,cwd_tmp
    cp DIR_TMP
    jr z,zx48_build_copy
    cp DIR_USERHOME
    jr nz,zx48_object_invalid
    ld hl,cwd_home_prefix
    ld de,cwd_buffer
    ld bc,6
    ldir
    ld hl,session_user
    ld a,(session_user_len)
    ld c,a
    ld b,0
    ldir
    xor a
    ld (de),a
    ld a,(session_user_len)
    add a,6
    ld (cwd_length),a
    or a
    ret
zx48_build_copy:
    ld de,cwd_buffer
    ld b,0
zx48_build_copy_loop:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jr z,zx48_build_copy_done
    inc b
    jr zx48_build_copy_loop
zx48_build_copy_done:
    ld a,b
    ld (cwd_length),a
    or a
    ret

zx48_object_pack:
    call zx48_path_resolve
    ret c
    ld a,(path_dir)
    ld hl,path_name
    call zx48_object_lookup
    ret c
    ld a,c
    jp zx48_zxpack_try_slot
zx48_object_unpack:
    call zx48_path_resolve
    ret c
    ld a,(path_dir)
    ld hl,path_name
    call zx48_object_lookup
    ret c
    jp zx48_zxpack_materialize

path_dot: db '.',0
path_dotdot: db '.','.',0
path_bin: db 'b','i','n',0
path_dev: db 'd','e','v',0
path_etc: db 'e','t','c',0
path_home: db 'h','o','m','e',0
path_tmp: db 't','m','p',0
path_tty: db 't','t','y',0
path_null: db 'n','u','l','l',0
path_tape: db 't','a','p','e',0
list_root:
    db 'b','i','n',0,0,0,0,0,0,0,0
    db 'd','e','v',0,0,0,0,0,0,0,0
    db 'e','t','c',0,0,0,0,0,0,0,0
    db 'h','o','m','e',0,0,0,0,0,0,0
    db 't','m','p',0,0,0,0,0,0,0,0
list_dev:
    db 'n','u','l','l',0,0,0,0,0,0,0
    db 't','a','p','e',0,0,0,0,0,0,0
    db 't','t','y',0,0,0,0,0,0,0,0
cwd_root: db '/',0
cwd_bin: db '/','b','i','n',0
cwd_dev: db '/','d','e','v',0
cwd_etc: db '/','e','t','c',0
cwd_home: db '/','h','o','m','e',0
cwd_tmp: db '/','t','m','p',0
cwd_home_prefix: db '/','h','o','m','e','/'

object_lookup_dir: db 0
object_create_type: db 0
object_lookup_name: dw 0
object_name_ptr: dw 0
object_slot: db 0
object_io_ptr: dw 0
object_io_count: dw 0
object_io_offset: dw 0
object_new_length: dw 0
object_new_ptr: dw 0
object_od_ptr: dw 0
object_open_flags: db 0
object_open_type: db 0
object_open_od: db 0
object_seek: dw 0
object_stat_out: dw 0
object_list_out: dw 0
object_list_index: db 0
object_cwd: db 0
path_source: dw 0
path_after: dw 0
path_dir: db 0
path_result_kind: db 0
path_name: defs 11,0
session_user_len: db 0
session_user: defs 9,0
bincat_ptr: dw 0
rename_new: dw 0
rename_record: dw 0
list_fixed_type: db 0
cwd_buffer: defs 16,0
cwd_length: db 0
object_table: defs RAM_OBJECT_COUNT*OBJ_RECORD_SIZE,0
    ENDM

;
; P4.01 namespace-only kernel footprint.  The full object-store macro above is
; intentionally not emitted until later Phase-4 steps require it.
;
    MACRO EMIT_NAMESPACE_ROUTINES
; P4.01 fixed namespace only. Base-name policy is added by P4.02.
zx48_cstr_equal:
    ld a,(de)
    cp (hl)
    ret nz
    or a
    ret z
    inc de
    inc hl
    jr zx48_cstr_equal

; HL=NUL exact-case portable base name. A=len on success.
zx48_name_validate:
    ld (ns_name_ptr),hl
    ld b,0
.name_loop:
    ld a,(hl)
    or a
    jr z,.name_end
    inc b
    ld a,b
    cp 11
    jr nc,.name_long
    ld a,(hl)
    call zx48_name_char_valid
    jr c,.name_bad
    inc hl
    jr .name_loop
.name_end:
    ld a,b
    or a
    jr z,.name_bad
    cp 1
    jr z,.check_dot
    cp 2
    jr nz,.name_ok
    ld hl,(ns_name_ptr)
    ld a,(hl)
    cp '.'
    jr nz,.name_ok
    inc hl
    ld a,(hl)
    cp '.'
    jr z,.name_bad
    jr .name_ok
.check_dot:
    ld hl,(ns_name_ptr)
    ld a,(hl)
    cp '.'
    jr z,.name_bad
.name_ok:
    ld a,b
    or a
    ret
.name_long:
    ld a,E_TOOLONG
    scf
    ret
.name_bad:
    ld a,E_INVAL
    scf
    ret

zx48_name_char_valid:
    cp '0'
    jr c,.name_punct
    cp '9'+1
    jr c,.name_char_ok
    cp 'A'
    jr c,.name_punct
    cp 'Z'+1
    jr c,.name_char_ok
    cp 'a'
    jr c,.name_punct
    cp 'z'+1
    jr c,.name_char_ok
.name_punct:
    cp '_'
    jr z,.name_char_ok
    cp '-'
    jr z,.name_char_ok
    cp '.'
    jr z,.name_char_ok
    scf
    ret
.name_char_ok:
    or a
    ret

zx48_path_resolve:
    ld (ns_src),hl
    ld a,(hl)
    or a
    jp z,.bad
    cp '/'
    jr z,.abs
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_CWD)
    ld (ns_dir),a
    ld hl,(ns_src)
    jr .component
.abs:
    xor a
    ld (ns_dir),a
.skip:
    inc hl
.component:
    ld a,(hl)
    cp '/'
    jr z,.skip
    or a
    jp z,.dir_done
    ld de,path_name
    ld b,0
.copy:
    ld a,(hl)
    or a
    jr z,.copied
    cp '/'
    jr z,.copied
    inc b
    ld a,b
    cp 32
    jp nc,.long
    ld a,(hl)
    ld (de),a
    inc de
    inc hl
    jr .copy
.copied:
    xor a
    ld (de),a
    ld (ns_after),hl

    ld a,(path_name)
    cp '.'
    jr nz,.child
    ld a,(path_name+1)
    or a
    jr z,.next
    cp '.'
    jr nz,.child
    ld a,(path_name+2)
    or a
    jr nz,.child
    ld a,(ns_dir)
    or a
    jp z,.bad
    cp DIR_USERHOME
    jr nz,.parent_root
    ld a,DIR_HOME
    ld (ns_dir),a
    jr .next
.parent_root:
    xor a
    ld (ns_dir),a
    jr .next

.child:
    call zx48_path_child_dir
    jr nc,.next
    ld a,(ns_dir)
    cp DIR_HOME
    jp z,.noent

    ld hl,(ns_after)
    ld a,(hl)
    or a
    jr z,.base
.tail:
    cp '/'
    jp nz,.noent
    inc hl
    ld a,(hl)
    cp '/'
    jr z,.tail
    or a
    jp nz,.noent
    jp .bad

.base:
    ld hl,path_name
    call zx48_name_validate
    ret c
    ld c,PATH_KIND_BASE
    jr .finish
.next:
    ld hl,(ns_after)
    jp .component

.dir_done:
    ld c,PATH_KIND_DIR
.finish:
    ld a,c
    ld (ns_kind),a
    ld a,(ns_dir)
    cp DIR_ROOT
    jr z,.rootlen
    cp DIR_HOME
    jr z,.homelen
    cp DIR_USERHOME
    jr z,.userlen
    ld b,4
    jr .kindlen
.rootlen:
    ld b,1
    jr .kindlen
.homelen:
    ld b,5
    jr .kindlen
.userlen:
    ld a,(session_user_len)
    add a,6
    ld b,a
.kindlen:
    ld a,(ns_kind)
    cp PATH_KIND_BASE
    jr nz,.lencheck
    ld a,(ns_dir)
    or a
    jr z,.count
    inc b
.count:
    ld hl,path_name
.countloop:
    ld a,(hl)
    or a
    jr z,.lencheck
    inc b
    inc hl
    jr .countloop
.lencheck:
    ld a,b
    cp 32
    jr nc,.long
    ld a,(ns_kind)
    ld c,a
    ld a,(ns_dir)
    or a
    ret
.long:
    ld a,E_TOOLONG
    scf
    ret
.noent:
    ld a,E_NOENT
    scf
    ret
.bad:
    ld a,E_INVAL
    scf
    ret

zx48_path_child_dir:
    ld a,(ns_dir)
    or a
    jr z,.root
    cp DIR_HOME
    jr z,.home
    scf
    ret
.root:
    ld hl,path_name
    ld de,path_bin
    call zx48_cstr_equal
    jr z,.bin
    ld hl,path_name
    ld de,path_dev
    call zx48_cstr_equal
    jr z,.dev
    ld hl,path_name
    ld de,path_etc
    call zx48_cstr_equal
    jr z,.etc
    ld hl,path_name
    ld de,path_home
    call zx48_cstr_equal
    jr z,.home_dir
    ld hl,path_name
    ld de,path_tmp
    call zx48_cstr_equal
    jr z,.tmp
    scf
    ret
.home:
    ld a,(session_user_len)
    or a
    jr z,.fail
    ld hl,path_name
    ld de,session_user
    call zx48_cstr_equal
    jr nz,.fail
    ld a,DIR_USERHOME
    jr .set
.fail:
    scf
    ret
.bin:
    ld a,DIR_BIN
    jr .set
.dev:
    ld a,DIR_DEV
    jr .set
.etc:
    ld a,DIR_ETC
    jr .set
.home_dir:
    ld a,DIR_HOME
    jr .set
.tmp:
    ld a,DIR_TMP
.set:
    ld (ns_dir),a
    xor a
    or a
    ret

path_bin: db 'b','i','n',0
path_dev: db 'd','e','v',0
path_etc: db 'e','t','c',0
path_home: db 'h','o','m','e',0
path_tmp: db 't','m','p',0
path_name: defs 32,0
session_user_len: db 0
session_user: defs 9,0
ns_src: dw 0
ns_after: dw 0
ns_name_ptr: dw 0
ns_dir: db 0
ns_kind: db 0
    ENDM


;
; P4.09 staged O_APPEND write contract. Every append write reselects current
; logical EOF immediately before the P4.08 atomic RAW transaction, so SYS_SEEK
; can change the shared offset but can never turn append into overwrite.
;
    MACRO EMIT_P409_APPEND_ROUTINES
; E=handle,D=0,HL=source,BC=count -> HL=full count or error.
zx48_p409_sys_write:
    ld a,d
    or a
    jp nz,zx48_p409_invalid
    ld (p409_source),hl
    ld (p409_count),bc
    ld a,e
    call zx48_handle_lookup
    ret c
    ld a,(ix+OD_ACCESS_O)
    ld (p409_access),a
    and O_WRITE
    jp z,zx48_p409_perm
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_OBJECT
    jp nz,zx48_p409_notsup
    push ix
    pop hl
    ld (p409_od_ptr),hl
    ld a,(ix+OD_ID_O)
    call zx48_p405_object_ptr_slot
    ret c

    ld a,(p409_access)
    and O_APPEND
    jr z,zx48_p409_offset_write
    ld hl,(p409_source)
    ld bc,(p409_count)
    call zx48_p408_raw_write_at_eof
    ret c
    ; P4.08 may release the old allocation after committing the replacement,
    ; and zx48_free is free to clobber IX. Reload the authoritative object slot
    ; before publishing the newly committed EOF into the shared description.
    ld iy,(p409_od_ptr)
    ld a,(iy+OD_ID_O)
    call zx48_p405_object_ptr_slot
    ret c
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    jr zx48_p409_commit_offset

zx48_p409_offset_write:
    ld de,(p409_od_ptr)
    push de
    pop iy
    ld e,(iy+OD_OFFSET_O)
    ld d,(iy+OD_OFFSET_O+1)
    ld hl,(p409_source)
    ld bc,(p409_count)
    call zx48_p408_raw_write
    ret c
    ld de,(p409_count)
    ld iy,(p409_od_ptr)
    ld l,(iy+OD_OFFSET_O)
    ld h,(iy+OD_OFFSET_O+1)
    add hl,de

zx48_p409_commit_offset:
    ld iy,(p409_od_ptr)
    ld (iy+OD_OFFSET_O),l
    ld (iy+OD_OFFSET_O+1),h
    ld hl,(p409_count)
    xor a
    ret

zx48_p409_invalid:
    ld a,E_INVAL
    scf
    ret
zx48_p409_perm:
    ld a,E_PERM
    scf
    ret
zx48_p409_notsup:
    ld a,E_NOTSUP
    scf
    ret

p409_source: dw 0
p409_count: dw 0
p409_od_ptr: dw 0
p409_access: db 0
    ENDM

;
; P4.08 staged atomic RAW write/growth contract.
;
; IX=mutable RAW object record, DE=logical offset, HL=source, BC=count.
; Success commits all BC bytes and returns HL=BC. Extending writes first build
; a complete private replacement and publish it only after every fallible step.
    MACRO EMIT_P408_RAW_WRITE_ROUTINES
zx48_p408_raw_write:
    ld (p408_object_ptr),ix
    ld (p408_source),hl
    ld (p408_count),bc
    ld (p408_offset),de

    ld a,b
    or c
    jr nz,zx48_p408_nonzero
    ld hl,0
    xor a
    ret

zx48_p408_nonzero:
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jp nz,zx48_p408_notsup

    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (p408_old_length),hl
    ld e,(ix+OBJ_ALLOCATION_PTR)
    ld d,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p408_old_ptr),de

    ; Sparse holes are never created: offset must be <= old logical length.
    ld de,(p408_offset)
    or a
    sbc hl,de
    jp c,zx48_p408_invalid

    ; Widen offset+count before narrowing. Carry or >32768 is E_NOSPC.
    ld hl,(p408_offset)
    ld bc,(p408_count)
    add hl,bc
    jp c,zx48_p408_nospc
    ld a,h
    cp ARENA_SIZE/256
    jr c,zx48_p408_end_ok
    jp nz,zx48_p408_nospc
    ld a,l
    or a
    jp nz,zx48_p408_nospc
zx48_p408_end_ok:
    ld (p408_end),hl

    ; new_length=max(old_length,end).
    ld de,(p408_old_length)
    or a
    sbc hl,de
    jr c,zx48_p408_in_place
    jr z,zx48_p408_in_place
    ld hl,(p408_end)
    ld (p408_new_length),hl
    jr zx48_p408_extend

zx48_p408_in_place:
    ld hl,(p408_old_ptr)
    ld de,(p408_offset)
    add hl,de
    ex de,hl
    ld hl,(p408_source)
    ld bc,(p408_count)
    ldir
    ld hl,(p408_count)
    xor a
    ret

zx48_p408_extend:
    ; A complete private replacement must exist before the object record changes.
    ld bc,(p408_new_length)
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    ret c
    ld (p408_new_ptr),hl

    ; Copy the complete old representation first.
    ld bc,(p408_old_length)
    ld a,b
    or c
    jr z,zx48_p408_copy_write
    ld hl,(p408_old_ptr)
    ld de,(p408_new_ptr)
    ldir

zx48_p408_copy_write:
    ld hl,(p408_new_ptr)
    ld de,(p408_offset)
    add hl,de
    ex de,hl
    ld hl,(p408_source)
    ld bc,(p408_count)
    ldir

    ; Commit is bounded metadata only: RAW lengths stay equal and pointer swaps once.
    ld ix,(p408_object_ptr)
    ld hl,(p408_new_ptr)
    ld (ix+OBJ_ALLOCATION_PTR),l
    ld (ix+OBJ_ALLOCATION_PTR+1),h
    ld hl,(p408_new_length)
    ld (ix+OBJ_LOGICAL_LENGTH),l
    ld (ix+OBJ_LOGICAL_LENGTH+1),h
    ld (ix+OBJ_STORAGE_LENGTH),l
    ld (ix+OBJ_STORAGE_LENGTH+1),h

    ; The now-unreachable prior allocation is released after publication.
    ld hl,(p408_old_ptr)
    ld bc,(p408_old_length)
    ld a,b
    or c
    jr z,zx48_p408_extend_done
    bit 0,c
    jr z,zx48_p408_old_even
    inc bc
zx48_p408_old_even:
    call zx48_free
    ; A valid resident object owns a valid allocator extent; this cannot fail.
    ret c
zx48_p408_extend_done:
    ld hl,(p408_count)
    xor a
    ret

; IX=RAW object, HL=source, BC=count. This helper selects current EOF then uses
; the identical transaction; P4.09 later binds every O_APPEND description write.
zx48_p408_raw_write_at_eof:
    ld e,(ix+OBJ_LOGICAL_LENGTH)
    ld d,(ix+OBJ_LOGICAL_LENGTH+1)
    jp zx48_p408_raw_write

zx48_p408_invalid:
    ld a,E_INVAL
    scf
    ret
zx48_p408_nospc:
    ld a,E_NOSPC
    scf
    ret
zx48_p408_notsup:
    ld a,E_NOTSUP
    scf
    ret

p408_object_ptr: dw 0
p408_source: dw 0
p408_count: dw 0
p408_offset: dw 0
p408_old_length: dw 0
p408_old_ptr: dw 0
p408_end: dw 0
p408_new_length: dw 0
p408_new_ptr: dw 0
    ENDM

; P4.07 staged RAW RAM-object read/seek contract. The qualification fixture
; emits this with the admitted handle and mutable-object helpers without
; increasing the resident kernel code pool before the later Phase-4 integration.
;
    MACRO EMIT_P407_RAW_IO_ROUTINES
; E=handle,D=0,HL=absolute logical offset -> HL=new offset.
zx48_p407_sys_seek:
    ld a,d
    or a
    jp nz,zx48_p407_invalid
    ld (p407_request_offset),hl
    ld a,e
    call zx48_handle_lookup
    ret c
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_OBJECT
    jp nz,zx48_p407_notsup
    push ix
    pop hl
    ld (p407_od_ptr),hl
    ld a,(ix+OD_ID_O)
    call zx48_p405_object_ptr_slot
    ret c
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jp nz,zx48_p407_notsup
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld de,(p407_request_offset)
    or a
    sbc hl,de
    jp c,zx48_p407_invalid
    ld ix,(p407_od_ptr)
    ld hl,(p407_request_offset)
    ld (ix+OD_OFFSET_O),l
    ld (ix+OD_OFFSET_O+1),h
    xor a
    ret

; E=handle,D=0,HL=buffer,BC=count -> HL=bytes read.
; RAW reads are bounded by logical EOF and update the shared OD offset.
zx48_p407_sys_read:
    ld a,d
    or a
    jp nz,zx48_p407_invalid
    ld (p407_buffer),hl
    ld (p407_count),bc
    ld a,e
    call zx48_handle_lookup
    ret c
    ld a,(ix+OD_ACCESS_O)
    and O_READ
    jp z,zx48_p407_perm
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_OBJECT
    jp nz,zx48_p407_notsup
    ld l,(ix+OD_OFFSET_O)
    ld h,(ix+OD_OFFSET_O+1)
    ld (p407_current_offset),hl
    push ix
    pop hl
    ld (p407_od_ptr),hl
    ld a,(ix+OD_ID_O)
    call zx48_p405_object_ptr_slot
    ret c
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jp nz,zx48_p407_notsup

    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (p407_length),hl
    ld e,(ix+OBJ_STORAGE_LENGTH)
    ld d,(ix+OBJ_STORAGE_LENGTH+1)
    or a
    sbc hl,de
    jp nz,zx48_p407_format

    ld hl,(p407_length)
    ld de,(p407_current_offset)
    or a
    sbc hl,de
    jp c,zx48_p407_invalid
    ld (p407_available),hl

    ld de,(p407_count)
    or a
    sbc hl,de
    jr c,zx48_p407_read_use_available
    ld hl,(p407_count)
    jr zx48_p407_read_have_count
zx48_p407_read_use_available:
    ld hl,(p407_available)
zx48_p407_read_have_count:
    ld (p407_transfer),hl
    ld a,h
    or l
    jr z,zx48_p407_read_zero

    ld e,(ix+OBJ_ALLOCATION_PTR)
    ld d,(ix+OBJ_ALLOCATION_PTR+1)
    ld a,d
    or e
    jp z,zx48_p407_format
    bit 0,e
    jp nz,zx48_p407_format
    ld hl,(p407_current_offset)
    add hl,de
    ld de,(p407_buffer)
    ld bc,(p407_transfer)
    ldir

    ld hl,(p407_current_offset)
    ld de,(p407_transfer)
    add hl,de
    ld ix,(p407_od_ptr)
    ld (ix+OD_OFFSET_O),l
    ld (ix+OD_OFFSET_O+1),h
    ld hl,(p407_transfer)
    xor a
    ret

zx48_p407_read_zero:
    ld hl,0
    xor a
    ret

zx48_p407_invalid:
    ld a,E_INVAL
    scf
    ret
zx48_p407_perm:
    ld a,E_PERM
    scf
    ret
zx48_p407_notsup:
    ld a,E_NOTSUP
    scf
    ret
zx48_p407_format:
    ld a,E_FORMAT
    scf
    ret

p407_buffer: dw 0
p407_count: dw 0
p407_request_offset: dw 0
p407_current_offset: dw 0
p407_length: dw 0
p407_available: dw 0
p407_transfer: dw 0
p407_od_ptr: dw 0
    ENDM

;
; P4.06 object-side open-reference guards. Representation swaps and tests for an
; unreferenced mutable object delegate to the bounded open-description pool.
;
    MACRO EMIT_OBJECT_EXCLUSIVITY_ROUTINES
; A=RAM-object slot. E_BUSY iff any live open description references it.
zx48_object_no_open_references:
zx48_object_representation_swap_guard:
    ld d,a
    jp zx48_od_object_any_live
    ENDM

;
; P4.05 typed-open object side. The compact Phase-4 fixture emits this together
; with the already-qualified namespace and placement routines.
;
    MACRO EMIT_OBJECT_OPEN_ROUTINES
; A=dir,HL=NUL name -> IX record,C=slot.
zx48_p405_object_lookup:
    ld (p405_lookup_dir),a
    ld (p405_lookup_name),hl
    ld ix,p405_object_table
    ld c,0
    ld b,RAM_OBJECT_COUNT
zx48_p405_object_lookup_loop:
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_p405_object_lookup_next
    ld a,(ix+OBJ_DIR_ID)
    ld d,a
    ld a,(p405_lookup_dir)
    cp d
    jr nz,zx48_p405_object_lookup_next
    push bc
    push ix
    pop de
    ld hl,(p405_lookup_name)
    call zx48_p405_name_equal_record
    pop bc
    jr z,zx48_p405_object_lookup_found
zx48_p405_object_lookup_next:
    ld de,OBJ_RECORD_SIZE
    add ix,de
    inc c
    djnz zx48_p405_object_lookup_loop
    ld a,E_NOENT
    scf
    ret
zx48_p405_object_lookup_found:
    xor a
    or a
    ret

; A=slot -> IX exact mutable record,C=slot.
zx48_p405_object_ptr_slot:
    cp RAM_OBJECT_COUNT
    jr nc,zx48_p405_object_invalid
    ld c,a
    ld ix,p405_object_table
    or a
    ret z
    ld b,a
    ld de,OBJ_RECORD_SIZE
zx48_p405_object_ptr_loop:
    add ix,de
    djnz zx48_p405_object_ptr_loop
    xor a
    or a
    ret
zx48_p405_object_invalid:
    ld a,E_INVAL
    scf
    ret

; HL=NUL name,DE=record name[10]. Z iff exact byte-for-byte case match.
zx48_p405_name_equal_record:
    ld b,10
zx48_p405_name_equal_record_loop:
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
    djnz zx48_p405_name_equal_record_loop
    ld a,(hl)
    or a
    ret

; A=dir,B=type,HL=name -> IX newly published empty RAW record,C=slot.
zx48_p405_object_create:
    ld (p405_create_dir),a
    ld a,b
    ld (p405_create_type),a
    ld (p405_create_name),hl
    call zx48_name_validate
    ret c
    ld a,(p405_create_type)
    ld b,a
    ld a,(p405_create_dir)
    call zx48_object_public_type_allowed
    ret c
    ld a,(p405_create_dir)
    ld hl,(p405_create_name)
    call zx48_p405_object_lookup
    jr nc,zx48_p405_object_exists
    ld ix,p405_object_table
    ld c,0
    ld b,RAM_OBJECT_COUNT
zx48_p405_object_create_scan:
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_p405_object_create_found
    ld de,OBJ_RECORD_SIZE
    add ix,de
    inc c
    djnz zx48_p405_object_create_scan
    ld a,E_NOSPC
    scf
    ret
zx48_p405_object_create_found:
    ld a,c
    ld (p405_create_slot),a
    push ix
    pop de
    ld hl,(p405_create_name)
    ld b,10
zx48_p405_object_create_name:
    ld a,(hl)
    or a
    jr z,zx48_p405_object_create_pad
    ld (de),a
    inc de
    inc hl
    djnz zx48_p405_object_create_name
    jr zx48_p405_object_create_meta
zx48_p405_object_create_pad:
    xor a
zx48_p405_object_create_pad_loop:
    ld (de),a
    inc de
    djnz zx48_p405_object_create_pad_loop
zx48_p405_object_create_meta:
    ld a,(p405_create_dir)
    ld (ix+OBJ_DIR_ID),a
    xor a
    ld (ix+OBJ_FLAGS_BYTE),a
    ld (ix+OBJ_RESERVED_BYTE),a
    ld (ix+OBJ_LOGICAL_LENGTH),a
    ld (ix+OBJ_LOGICAL_LENGTH+1),a
    ld (ix+OBJ_STORAGE_LENGTH),a
    ld (ix+OBJ_STORAGE_LENGTH+1),a
    ld (ix+OBJ_ALLOCATION_PTR),a
    ld (ix+OBJ_ALLOCATION_PTR+1),a
    ; Type is the occupancy/publication byte and is committed last.
    ld a,(p405_create_type)
    ld (ix+OBJ_TYPE_ID),a
    ld a,(p405_create_slot)
    ld c,a
    xor a
    or a
    ret
zx48_p405_object_exists:
    ld a,E_EXIST
    scf
    ret

; C=slot. Roll back an empty object published only for this failed open.
zx48_p405_object_rollback_create:
    ld a,c
    call zx48_p405_object_ptr_slot
    ret c
    push ix
    pop hl
    ld de,0
    add hl,de
    ld de,p405_zero_record
    ex de,hl
    ld bc,OBJ_RECORD_SIZE
    ldir
    xor a
    or a
    ret

; IX=existing mutable record. Commit the required empty RAW representation.
; All fallible open-resource reservation is complete before this routine runs.
; Publication is bounded metadata; the now-unreachable old extent is released after.
zx48_p405_object_truncate:
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p405_truncate_old_ptr),hl
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    ld (p405_truncate_old_length),bc

    xor a
    ld (ix+OBJ_FLAGS_BYTE),a
    ld (ix+OBJ_RESERVED_BYTE),a
    ld (ix+OBJ_LOGICAL_LENGTH),a
    ld (ix+OBJ_LOGICAL_LENGTH+1),a
    ld (ix+OBJ_STORAGE_LENGTH),a
    ld (ix+OBJ_STORAGE_LENGTH+1),a
    ld (ix+OBJ_ALLOCATION_PTR),a
    ld (ix+OBJ_ALLOCATION_PTR+1),a

    ld hl,(p405_truncate_old_ptr)
    ld a,h
    or l
    ret z
    ld bc,(p405_truncate_old_length)
    bit 0,c
    jr z,zx48_p405_object_truncate_even
    inc bc
zx48_p405_object_truncate_even:
    call zx48_free
    ret nc
    ld a,PANIC_SCHEDULER
    jp zx48_panic

; A=dir,HL=name. Z iff this is the catalog-only /bin/sh entry when no RAM shadow exists.
zx48_p405_is_bcat:
    cp DIR_BIN
    ret nz
    ld de,p405_bcat_name
    jp zx48_cstr_equal

; A=dir,HL=name -> A=OD_KIND_* for fixed device.
zx48_p405_device_kind:
    cp DIR_DEV
    jr nz,zx48_p405_device_noent
    ld de,p405_tty_name
    call zx48_cstr_equal
    jr z,zx48_p405_device_tty
    ld hl,path_name
    ld de,p405_null_name
    call zx48_cstr_equal
    jr z,zx48_p405_device_null
    ld hl,path_name
    ld de,p405_tape_name
    call zx48_cstr_equal
    jr z,zx48_p405_device_tape
zx48_p405_device_noent:
    ld a,E_NOENT
    scf
    ret
zx48_p405_device_tty:
    ld a,OD_KIND_TTY
    or a
    ret
zx48_p405_device_null:
    ld a,OD_KIND_NULL
    or a
    ret
zx48_p405_device_tape:
    ld a,OD_KIND_TAPE
    or a
    ret

p405_bcat_name: db 's','h',0
p405_tty_name: db 't','t','y',0
p405_null_name: db 'n','u','l','l',0
p405_tape_name: db 't','a','p','e',0
p405_zero_record: defs OBJ_RECORD_SIZE,0
p405_lookup_dir: db 0
p405_lookup_name: dw 0
p405_create_dir: db 0
p405_create_type: db 0
p405_create_name: dw 0
p405_create_slot: db 0
p405_truncate_old_ptr: dw 0
p405_truncate_old_length: dw 0
p405_object_table: defs RAM_OBJECT_COUNT*OBJ_RECORD_SIZE,0
p405_object_table_end:
    ENDM


;
; P4.11 staged SYS_STAT metadata resolver. Produces the exact ten-byte
; STATOUT1 record in p411_stat_record without exposing partial output.
;
    MACRO EMIT_P411_STAT_OBJECT_ROUTINES
zx48_p411_stat_clear:
    xor a
    ld hl,p411_stat_record
    ld de,p411_stat_record+1
    ld bc,9
    ld (hl),a
    ldir
    ret

; HL=NUL path -> p411_stat_record exact STATOUT1.
zx48_p411_stat_resolve:
    call zx48_path_resolve
    ret c
    ld (p411_stat_dir),a
    ld a,c
    cp PATH_KIND_DIR
    jr z,zx48_p411_stat_dir

    ld a,(p411_stat_dir)
    cp DIR_DEV
    jr z,zx48_p411_stat_dev

    ; Resident exact-name RAM metadata shadows catalog-only tape metadata.
    ld a,(p411_stat_dir)
    ld hl,path_name
    call zx48_p405_object_lookup
    jr nc,zx48_p411_stat_ram

    ld a,(p411_stat_dir)
    ld hl,path_name
    call zx48_p405_is_bcat
    jr z,zx48_p411_stat_tape
    ld a,E_NOENT
    scf
    ret

zx48_p411_stat_ram:
    call zx48_p411_stat_clear
    ld a,(ix+OBJ_TYPE_ID)
    ld (p411_stat_record+0),a
    ld a,(ix+OBJ_FLAGS_BYTE)
    ld (p411_stat_record+1),a
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (p411_stat_record+2),hl
    ld l,(ix+OBJ_STORAGE_LENGTH)
    ld h,(ix+OBJ_STORAGE_LENGTH+1)
    ld (p411_stat_record+4),hl
    ld a,(ix+OBJ_DIR_ID)
    ld (p411_stat_record+6),a
    ld a,STATE_RAM
    ld (p411_stat_record+7),a
    xor a
    ret

zx48_p411_stat_dir:
    call zx48_p411_stat_clear
    ld a,OBJ_DIR
    ld (p411_stat_record+0),a
    ld a,(p411_stat_dir)
    ld (p411_stat_record+6),a
    ld a,STATE_PSEUDO
    ld (p411_stat_record+7),a
    xor a
    ret

zx48_p411_stat_dev:
    ld a,(p411_stat_dir)
    ld hl,path_name
    call zx48_p405_device_kind
    ret c
    call zx48_p411_stat_clear
    ld a,OBJ_DEV
    ld (p411_stat_record+0),a
    ld a,DIR_DEV
    ld (p411_stat_record+6),a
    ld a,STATE_PSEUDO
    ld (p411_stat_record+7),a
    xor a
    ret

zx48_p411_stat_tape:
    call zx48_p411_stat_clear
    ld a,OBJ_BIN
    ld (p411_stat_record+0),a
    ld hl,0-1
    ld (p411_stat_record+2),hl
    ld (p411_stat_record+4),hl
    ld a,DIR_BIN
    ld (p411_stat_record+6),a
    ld a,STATE_TAPE_BACKED
    ld (p411_stat_record+7),a
    xor a
    ret

p411_stat_dir: db 0
p411_stat_record: defs 10,0
    ENDM


;
; P4.12 staged SYS_LIST/BCAT union contract.
; LIST1 and LISTOUT1 remain exact packed ABI records. Dynamic enumeration selects
; the requested sorted entry without allocating a visible-entry array.
;
    MACRO EMIT_P412_LIST_ROUTINES

; HL=BCAT payload, BC=payload length. On success retain the validated catalog.
zx48_p412_bincat_admit:
    ld (p412_bincat_candidate),hl
    ld (p412_bincat_length),bc
    ld a,(hl)
    cp 'B'
    jp nz,zx48_p412_bcat_format
    inc hl
    ld a,(hl)
    cp 'C'
    jp nz,zx48_p412_bcat_format
    inc hl
    ld a,(hl)
    cp 'A'
    jp nz,zx48_p412_bcat_format
    inc hl
    ld a,(hl)
    cp 'T'
    jp nz,zx48_p412_bcat_format
    inc hl
    ld a,(hl)
    cp 1
    jp nz,zx48_p412_bcat_format
    inc hl
    ld a,(hl)
    cp 224
    jp nc,zx48_p412_bcat_format
    ld (p412_bincat_count),a
    inc hl
    ld a,(hl)
    inc hl
    or (hl)
    jp nz,zx48_p412_bcat_format

    ; Exact length = 8 + entry_count*12.
    ld a,(p412_bincat_count)
    ld b,a
    ld hl,8
    ld de,12
    ld a,b
    or a
    jr z,zx48_p412_bcat_length_ready
zx48_p412_bcat_length_loop:
    add hl,de
    djnz zx48_p412_bcat_length_loop
zx48_p412_bcat_length_ready:
    ld de,(p412_bincat_length)
    or a
    sbc hl,de
    jp nz,zx48_p412_bcat_format

    ld hl,(p412_bincat_candidate)
    ld de,8
    add hl,de
    ld (p412_bcat_entry),hl
    xor a
    ld (p412_bcat_have_prev),a
    ld a,(p412_bincat_count)
    ld (p412_bcat_remaining),a

zx48_p412_bcat_validate_loop:
    ld a,(p412_bcat_remaining)
    or a
    jr z,zx48_p412_bcat_valid

    ld hl,(p412_bcat_entry)
    call zx48_p412_bcat_name_validate
    jp c,zx48_p412_bcat_format

    ld hl,(p412_bcat_entry)
    ld de,10
    add hl,de
    ld a,(hl)
    cp OBJ_BIN
    jp nz,zx48_p412_bcat_format
    inc hl
    ld a,(hl)
    cp 1
    jp nz,zx48_p412_bcat_format

    ld a,(p412_bcat_have_prev)
    or a
    jr z,zx48_p412_bcat_save_prev
    ld hl,(p412_bcat_prev)
    ld de,(p412_bcat_entry)
    call zx48_p412_cmp10
    ; Strict previous < current: carry only.
    jp nc,zx48_p412_bcat_format

zx48_p412_bcat_save_prev:
    ld hl,(p412_bcat_entry)
    ld (p412_bcat_prev),hl
    ld a,1
    ld (p412_bcat_have_prev),a
    ld de,12
    add hl,de
    ld (p412_bcat_entry),hl
    ld a,(p412_bcat_remaining)
    dec a
    ld (p412_bcat_remaining),a
    jr zx48_p412_bcat_validate_loop

zx48_p412_bcat_valid:
    ld hl,(p412_bincat_candidate)
    ld (p412_bincat_ptr),hl
    xor a
    ret

; HL=name[10]. Lower-case command name, NUL/zero padded or full ten.
zx48_p412_bcat_name_validate:
    ld b,10
    ld c,0
zx48_p412_bcat_name_loop:
    ld a,(hl)
    or a
    jr z,zx48_p412_bcat_name_zero
    ld a,c
    or a
    jr nz,zx48_p412_bcat_name_bad
    ld a,(hl)
    cp 'a'
    jr c,zx48_p412_bcat_name_digit
    cp 'z'+1
    jr c,zx48_p412_bcat_name_next
zx48_p412_bcat_name_digit:
    ld a,(hl)
    cp '0'
    jr c,zx48_p412_bcat_name_punct
    cp '9'+1
    jr c,zx48_p412_bcat_name_next
zx48_p412_bcat_name_punct:
    ld a,(hl)
    cp '_'
    jr z,zx48_p412_bcat_name_next
    cp '-'
    jr z,zx48_p412_bcat_name_next
    cp '.'
    jr nz,zx48_p412_bcat_name_bad
zx48_p412_bcat_name_next:
    inc hl
    djnz zx48_p412_bcat_name_loop
    xor a
    ret
zx48_p412_bcat_name_zero:
    ld a,b
    cp 10
    jr z,zx48_p412_bcat_name_bad
    ld c,1
    inc hl
    djnz zx48_p412_bcat_name_loop
    xor a
    ret
zx48_p412_bcat_name_bad:
    ld a,E_FORMAT
    scf
    ret

; HL=left name[10], DE=right name[10]. Z equal; C left<right; NC/NZ left>right.
zx48_p412_cmp10:
    ld b,10
zx48_p412_cmp10_loop:
    ld a,(de)
    ld c,a
    ld a,(hl)
    cp c
    ret c
    jr nz,zx48_p412_cmp10_greater
    inc hl
    inc de
    djnz zx48_p412_cmp10_loop
    xor a
    ret
zx48_p412_cmp10_greater:
    or a
    ret

; HL -> LIST1 {path_ptr,u8 index,u8 reserved,u16 out_ptr}.
zx48_p412_sys_list:
    ld (p412_req_ptr),hl
    ld bc,6
    call zx48_user_range_validate
    ret c

    ld hl,(p412_req_ptr)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p412_path_ptr),de
    inc hl
    ld a,(hl)
    ld (p412_index),a
    inc hl
    ld a,(hl)
    or a
    jp nz,zx48_p412_invalid
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p412_out_ptr),de

    ex de,hl
    ld bc,16
    call zx48_user_range_validate
    ret c

    ; Validate the complete path before resolution.
    ld hl,(p412_path_ptr)
zx48_p412_path_validate:
    push hl
    ld bc,1
    call zx48_user_range_validate
    pop hl
    ret c
    ld a,(hl)
    or a
    jr z,zx48_p412_path_ok
    inc hl
    jr zx48_p412_path_validate

zx48_p412_path_ok:
    ; Index 255 is the unconditional ABI terminator and never writes LISTOUT1.
    ld a,(p412_index)
    inc a
    jp z,zx48_p412_end

    ld hl,(p412_path_ptr)
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_DIR
    jp nz,zx48_p412_perm
    ld a,(ns_dir)
    ld (p412_dir),a
    cp DIR_ROOT
    jp z,zx48_p412_root
    cp DIR_DEV
    jp z,zx48_p412_dev
    cp DIR_HOME
    jp z,zx48_p412_home
    jp zx48_p412_dynamic

zx48_p412_root:
    ld hl,p412_root_entries
    ld b,5
    ld a,OBJ_DIR
    jp zx48_p412_fixed
zx48_p412_dev:
    ld hl,p412_dev_entries
    ld b,3
    ld a,OBJ_DEV
    jp zx48_p412_fixed
zx48_p412_home:
    ld a,(session_user_len)
    or a
    jp z,zx48_p412_end
    ld a,(p412_index)
    or a
    jp nz,zx48_p412_end
    call zx48_p412_clear_out
    ld hl,session_user
    ld de,(p412_out_ptr)
    ld a,(session_user_len)
    ld c,a
    ld b,0
    ldir
    ld a,OBJ_DIR
    jp zx48_p412_emit_fixed_tail

zx48_p412_fixed:
    ld (p412_fixed_type),a
    ld a,(p412_index)
    cp b
    jp nc,zx48_p412_end
    or a
    jr z,zx48_p412_fixed_emit
    ld c,a
zx48_p412_fixed_seek:
    ld de,10
    add hl,de
    dec c
    jr nz,zx48_p412_fixed_seek
zx48_p412_fixed_emit:
    ld (p412_fixed_name),hl
    call zx48_p412_clear_out
    ld hl,(p412_fixed_name)
    ld de,(p412_out_ptr)
    ld bc,10
    ldir
    ld a,(p412_fixed_type)
zx48_p412_emit_fixed_tail:
    ld de,(p412_out_ptr)
    ld hl,10
    add hl,de
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld a,STATE_PSEUDO
    ld (hl),a
    inc hl
    ld a,(p412_dir)
    ld (hl),a
    ld hl,1
    xor a
    ret

; Sorted dynamic enumeration by repeated minimum selection.
zx48_p412_dynamic:
    xor a
    ld (p412_prev_valid),a
    ld a,(p412_index)
    ld (p412_remaining),a
zx48_p412_select_next:
    xor a
    ld (p412_best_kind),a

    ld ix,p405_object_table
    ld b,RAM_OBJECT_COUNT
zx48_p412_scan_ram:
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_p412_scan_ram_next
    ld a,(ix+OBJ_DIR_ID)
    ld c,a
    ld a,(p412_dir)
    cp c
    jr nz,zx48_p412_scan_ram_next
    call zx48_p412_consider_ix
zx48_p412_scan_ram_next:
    ld de,OBJ_RECORD_SIZE
    add ix,de
    djnz zx48_p412_scan_ram

    ld a,(p412_dir)
    cp DIR_BIN
    jr nz,zx48_p412_selection_done
    ld hl,(p412_bincat_ptr)
    ld a,h
    or l
    jr z,zx48_p412_selection_done
    ld a,(hl)
    ; Catalog was admitted earlier; count is the authoritative bounded byte.
    ld de,5
    add hl,de
    ld b,(hl)
    ld hl,(p412_bincat_ptr)
    ld de,8
    add hl,de
zx48_p412_scan_bcat:
    ld a,b
    or a
    jr z,zx48_p412_selection_done
    push bc
    push hl
    call zx48_p412_bcat_shadowed
    pop hl
    jr c,zx48_p412_bcat_next_pop
    call zx48_p412_consider_hl_bcat
zx48_p412_bcat_next_pop:
    ld de,12
    add hl,de
    pop bc
    djnz zx48_p412_scan_bcat

zx48_p412_selection_done:
    ld a,(p412_best_kind)
    or a
    jp z,zx48_p412_end
    ld a,(p412_remaining)
    or a
    jp z,zx48_p412_emit_best

    ld hl,(p412_best_ptr)
    ld de,p412_prev_name
    ld bc,10
    ldir
    ld a,1
    ld (p412_prev_valid),a
    ld a,(p412_remaining)
    dec a
    ld (p412_remaining),a
    jr zx48_p412_select_next

; IX=RAM record candidate.
zx48_p412_consider_ix:
    push bc
    push ix
    pop hl
    call zx48_p412_consider_common
    pop bc
    ret

; HL=BCAT entry candidate.
zx48_p412_consider_hl_bcat:
    ld a,2
    ld (p412_candidate_kind),a
    jp zx48_p412_consider_common_entry

zx48_p412_consider_common:
    ld a,1
    ld (p412_candidate_kind),a
zx48_p412_consider_common_entry:
    ld (p412_candidate_ptr),hl
    ld a,(p412_prev_valid)
    or a
    jr z,zx48_p412_consider_best
    ld de,p412_prev_name
    call zx48_p412_cmp10
    ret c
    ret z
zx48_p412_consider_best:
    ld a,(p412_best_kind)
    or a
    jr z,zx48_p412_accept_candidate
    ld hl,(p412_candidate_ptr)
    ld de,(p412_best_ptr)
    call zx48_p412_cmp10
    ret nc
zx48_p412_accept_candidate:
    ld hl,(p412_candidate_ptr)
    ld (p412_best_ptr),hl
    ld a,(p412_candidate_kind)
    ld (p412_best_kind),a
    ret

; HL=BCAT entry name. Carry when a resident /bin object shadows exact name.
zx48_p412_bcat_shadowed:
    ld (p412_candidate_ptr),hl
    ld ix,p405_object_table
    ld b,RAM_OBJECT_COUNT
zx48_p412_shadow_loop:
    ld a,(ix+OBJ_TYPE_ID)
    or a
    jr z,zx48_p412_shadow_next
    ld a,(ix+OBJ_DIR_ID)
    cp DIR_BIN
    jr nz,zx48_p412_shadow_next
    push bc
    push ix
    pop hl
    ld de,(p412_candidate_ptr)
    call zx48_p412_cmp10
    pop bc
    jr z,zx48_p412_shadow_yes
zx48_p412_shadow_next:
    ld de,OBJ_RECORD_SIZE
    add ix,de
    djnz zx48_p412_shadow_loop
    or a
    ret
zx48_p412_shadow_yes:
    scf
    ret

zx48_p412_emit_best:
    call zx48_p412_clear_out
    ld a,(p412_best_kind)
    cp 1
    jr z,zx48_p412_emit_ram

    ; BCAT-only TAPE_BACKED.
    ld hl,(p412_best_ptr)
    ld de,(p412_out_ptr)
    ld bc,10
    ldir
    ld a,OBJ_BIN
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de
    ld a,$ff
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld a,STATE_TAPE_BACKED
    ld (de),a
    inc de
    ld a,DIR_BIN
    ld (de),a
    ld hl,1
    xor a
    ret

zx48_p412_emit_ram:
    ld hl,(p412_best_ptr)
    push hl
    pop ix
    ld de,(p412_out_ptr)
    ld bc,10
    ldir
    ld a,(ix+OBJ_TYPE_ID)
    ld (de),a
    inc de
    ld a,(ix+OBJ_FLAGS_BYTE)
    ld (de),a
    inc de
    ld a,(ix+OBJ_LOGICAL_LENGTH)
    ld (de),a
    inc de
    ld a,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (de),a
    inc de
    ld a,STATE_RAM
    ld (de),a
    inc de
    ld a,(ix+OBJ_DIR_ID)
    ld (de),a
    ld hl,1
    xor a
    ret

zx48_p412_clear_out:
    ld hl,(p412_out_ptr)
    xor a
    ld (hl),a
    ld de,(p412_out_ptr)
    inc de
    ld bc,15
    ldir
    ret

zx48_p412_end:
    ld hl,0
    xor a
    ret
zx48_p412_invalid:
    ld a,E_INVAL
    scf
    ret
zx48_p412_perm:
    ld a,E_PERM
    scf
    ret
zx48_p412_bcat_format:
    ld a,E_FORMAT
    scf
    ret

p412_root_entries:
    db 'b','i','n',0,0,0,0,0,0,0
    db 'd','e','v',0,0,0,0,0,0,0
    db 'e','t','c',0,0,0,0,0,0,0
    db 'h','o','m','e',0,0,0,0,0,0
    db 't','m','p',0,0,0,0,0,0,0
p412_dev_entries:
    db 'n','u','l','l',0,0,0,0,0,0
    db 't','a','p','e',0,0,0,0,0,0
    db 't','t','y',0,0,0,0,0,0,0

p412_req_ptr: dw 0
p412_path_ptr: dw 0
p412_out_ptr: dw 0
p412_bincat_candidate: dw 0
p412_bincat_ptr: dw 0
p412_bincat_length: dw 0
p412_bcat_entry: dw 0
p412_bcat_prev: dw 0
p412_best_ptr: dw 0
p412_candidate_ptr: dw 0
p412_fixed_name: dw 0
p412_index: db 0
p412_dir: db 0
p412_fixed_type: db 0
p412_bincat_count: db 0
p412_bcat_remaining: db 0
p412_bcat_have_prev: db 0
p412_prev_valid: db 0
p412_remaining: db 0
p412_best_kind: db 0
p412_candidate_kind: db 0
p412_prev_name: defs 10,0
    ENDM


;
; P4.13 staged SYS_REMOVE contract. Removal is limited to closed mutable RAM
; objects. Namespace-only, catalog-only and protected metadata are immutable.
;
    MACRO EMIT_P413_REMOVE_ROUTINES

; HL=NUL-terminated path.
zx48_p413_sys_remove:
    call zx48_path_resolve
    ret c
    ld (p413_dir),a
    ld a,c
    cp PATH_KIND_DIR
    jp z,zx48_p413_perm

    ld a,(p413_dir)
    cp DIR_DEV
    jp z,zx48_p413_perm

    ld a,(p413_dir)
    ld hl,path_name
    call zx48_p405_object_lookup
    jr nc,zx48_p413_found

    ; A catalog-only /bin entry is visible metadata but not mutable storage.
    ld a,(p413_dir)
    cp DIR_BIN
    jr nz,zx48_p413_noent
    ld hl,path_name
    call zx48_p405_is_bcat
    jp z,zx48_p413_perm
zx48_p413_noent:
    ld a,E_NOENT
    scf
    ret

zx48_p413_found:
    ; Public mutable placement only. Protected system metadata never enters the
    ; removal transaction even if a malformed fixture injects such a record.
    ld a,(ix+OBJ_TYPE_ID)
    cp OBJ_SYS
    jp z,zx48_p413_perm
    cp OBJ_FNT
    jp z,zx48_p413_perm
    ld a,(ix+OBJ_DIR_ID)
    cp DIR_BIN
    jr z,zx48_p413_mutable_dir
    cp DIR_ETC
    jr z,zx48_p413_mutable_dir
    cp DIR_USERHOME
    jr z,zx48_p413_mutable_dir
    cp DIR_TMP
    jp nz,zx48_p413_perm

zx48_p413_mutable_dir:
    ld (p413_object_ptr),ix
    ld a,c
    ld (p413_slot),a
    call zx48_object_no_open_references
    ret c
    ld ix,(p413_object_ptr)

    ; Preserve payload ownership before touching the table entry.
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p413_old_ptr),hl
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    bit 0,c
    jr z,zx48_p413_length_ready
    inc bc
zx48_p413_length_ready:
    ld (p413_old_length),bc

    ; Free first; any allocator corruption is fatal and cannot be reported as a
    ; partially completed namespace mutation.
    ld hl,(p413_old_ptr)
    ld a,h
    or l
    jr z,zx48_p413_clear_state
    ld bc,(p413_old_length)
    call zx48_free
    jr nc,zx48_p413_clear_state
    ld a,PANIC_SCHEDULER
    jp zx48_panic

zx48_p413_clear_state:
    ld ix,(p413_object_ptr)
    ; Removal invalidates all transient zxpack candidate pointers/identity.
    xor a
    ld hl,0
    ld (zx_object_ptr),hl
    ld (zx_new_ptr),hl
    ld (zx_encoded_len),hl
    ld (zx_slot),a

    ; Free the bounded table slot by clearing all twenty bytes. Occupancy/type is
    ; among the cleared bytes; no BCAT byte is touched.
    push ix
    pop hl
    ld de,p413_zero_record
    ex de,hl
    ld bc,OBJ_RECORD_SIZE
    ldir

    ld hl,0
    xor a
    ret

zx48_p413_perm:
    ld a,E_PERM
    scf
    ret

p413_dir: db 0
p413_slot: db 0
p413_old_ptr: dw 0
p413_old_length: dw 0
p413_object_ptr: dw 0
p413_zero_record: defs OBJ_RECORD_SIZE,0
    ENDM


;
; P4.14 staged SYS_RENAME: exact no-op, case-only rename, and collision-safe
; destination validation. P4.15 extends the distinct-destination path to atomic
; replacement after closed-object qualification.
;
    MACRO EMIT_P414_RENAME_ROUTINES

; HL -> REN1 {u16 old_path_ptr,u16 new_path_ptr}.
zx48_p414_sys_rename:
    ld (p414_req_ptr),hl
    ld bc,4
    call zx48_user_range_validate
    ret c

    ld hl,(p414_req_ptr)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p414_old_path),de
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p414_new_path),de

    ld hl,(p414_old_path)
    call zx48_p414_validate_cstr
    ret c
    ld hl,(p414_new_path)
    call zx48_p414_validate_cstr
    ret c

    ; Resolve and qualify mutable exact source.
    ld hl,(p414_old_path)
    call zx48_path_resolve
    ret c
    ld (p414_old_dir),a
    ld a,c
    cp PATH_KIND_BASE
    jp nz,zx48_p414_perm
    ld hl,path_name
    ld de,p414_old_name
    ld bc,11
    ldir

    ld a,(p414_old_dir)
    ld hl,p414_old_name
    call zx48_p405_object_lookup
    jr nc,zx48_p414_source_found
    ld a,(p414_old_dir)
    cp DIR_BIN
    jr nz,zx48_p414_noent
    ld hl,p414_old_name
    call zx48_p405_is_bcat
    jp z,zx48_p414_perm
zx48_p414_noent:
    ld a,E_NOENT
    scf
    ret

zx48_p414_source_found:
    ld (p414_source_ptr),ix
    ld a,c
    ld (p414_source_slot),a
    ld a,(ix+OBJ_TYPE_ID)
    ld (p414_source_type),a
    ld b,a
    ld a,(p414_old_dir)
    call zx48_object_public_type_allowed
    jp c,zx48_p414_perm

    ; Resolve the destination fully before any mutation.
    ld hl,(p414_new_path)
    call zx48_path_resolve
    ret c
    ld (p414_new_dir),a
    ld a,c
    cp PATH_KIND_BASE
    jp nz,zx48_p414_perm
    ld hl,path_name
    ld de,p414_new_name
    ld bc,11
    ldir

    ; Existing source type must be legal in the fixed destination directory.
    ld a,(p414_source_type)
    ld b,a
    ld a,(p414_new_dir)
    call zx48_object_public_type_allowed
    jp c,zx48_p414_perm

    ; Exact same normalized path is a no-op success.
    ld a,(p414_old_dir)
    ld d,a
    ld a,(p414_new_dir)
    cp d
    jr nz,zx48_p414_not_same
    ld hl,p414_old_name
    ld de,p414_new_name
    call zx48_p414_name_equal
    jr nz,zx48_p414_not_same
    ld hl,0
    xor a
    ret

zx48_p414_not_same:
    ; A distinct resident target is a collision at P4.14. P4.15 replaces this
    ; branch with the closed-object atomic replacement transaction.
    ld a,(p414_new_dir)
    ld hl,p414_new_name
    call zx48_p405_object_lookup
    jr c,zx48_p414_no_resident_target

    ld a,(ix+OBJ_TYPE_ID)
    ld b,a
    ld a,(p414_new_dir)
    call zx48_object_public_type_allowed
    jp c,zx48_p414_perm
    ld a,E_EXIST
    scf
    ret

zx48_p414_no_resident_target:
    ; Catalog-only TAPE_BACKED metadata cannot be a replacement destination.
    ld a,(p414_new_dir)
    cp DIR_BIN
    jr nz,zx48_p414_commit
    ld hl,p414_new_name
    call zx48_p405_is_bcat
    jp z,zx48_p414_perm

zx48_p414_commit:
    ; Bounded metadata-only commit. Payload bytes/representation are untouched.
    ld ix,(p414_source_ptr)
    push ix
    pop de
    ld hl,p414_new_name
    ld b,10
zx48_p414_name_copy:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz zx48_p414_name_copy
    ld a,(p414_new_dir)
    ld (ix+OBJ_DIR_ID),a
    ld hl,0
    xor a
    ret

; HL -> NUL path; prove every byte is in an ABI-valid user range before resolve.
zx48_p414_validate_cstr:
zx48_p414_validate_cstr_loop:
    push hl
    ld bc,1
    call zx48_user_range_validate
    pop hl
    ret c
    ld a,(hl)
    or a
    ret z
    inc hl
    jr zx48_p414_validate_cstr_loop

; HL/DE -> two NUL-terminated <=10-byte names. Z iff exact byte equality.
zx48_p414_name_equal:
    ld b,11
zx48_p414_name_equal_loop:
    ld a,(de)
    ld c,a
    ld a,(hl)
    cp c
    ret nz
    or a
    ret z
    inc hl
    inc de
    djnz zx48_p414_name_equal_loop
    xor a
    ret

zx48_p414_perm:
    ld a,E_PERM
    scf
    ret

p414_req_ptr: dw 0
p414_old_path: dw 0
p414_new_path: dw 0
p414_source_ptr: dw 0
p414_old_dir: db 0
p414_new_dir: db 0
p414_source_slot: db 0
p414_source_type: db 0
p414_old_name: defs 11,0
p414_new_name: defs 11,0
    ENDM

;
; P4.15 distinct-destination SYS_RENAME replacement transaction. P4.14 remains
; the immutable no-op/case-only/collision baseline; this wrapper handles only the
; validated E_EXIST path and preserves all P4.14 semantics otherwise.
;
    MACRO EMIT_P415_RENAME_REPLACEMENT_ROUTINES

; HL -> REN1. Delegate every non-replacement case to the P4.14 implementation.
zx48_p415_sys_rename:
    call zx48_p414_sys_rename
    ret nc
    cp E_EXIST
    ret nz

    ; P4.14 reached E_EXIST only after fully validating both paths, source type,
    ; destination directory compatibility and mutable resident destination type.
    ; Re-establish exact source/destination records and perform every fallible
    ; check before the first object-table byte is changed.
    ld ix,(p414_source_ptr)
    ld a,(p414_source_slot)
    call zx48_object_no_open_references
    ret c
    ld ix,(p414_source_ptr)
    call zx48_p415_record_validate
    ret c

    ld a,(p414_new_dir)
    ld hl,p414_new_name
    call zx48_p405_object_lookup
    jp c,zx48_p415_invalid
    ld (p415_destination_ptr),ix
    ld a,c
    ld (p415_destination_slot),a

    ; Destination metadata must itself be an ordinary mutable public RAM object.
    ld a,(ix+OBJ_TYPE_ID)
    ld b,a
    ld a,(p414_new_dir)
    call zx48_object_public_type_allowed
    ret c

    ld ix,(p415_destination_ptr)
    call zx48_p415_record_validate
    ret c
    ld a,(p415_destination_slot)
    call zx48_object_no_open_references
    ret c

    ; A malformed table must never cause the replacement to free the payload that
    ; is about to become the destination's payload.
    ld ix,(p414_source_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p415_source_payload),hl
    ld ix,(p415_destination_ptr)
    ld e,(ix+OBJ_ALLOCATION_PTR)
    ld d,(ix+OBJ_ALLOCATION_PTR+1)
    ld a,h
    or l
    jr z,zx48_p415_payload_distinct
    or a
    sbc hl,de
    jp z,zx48_p415_invalid
zx48_p415_payload_distinct:

    ; Save old destination ownership for post-commit release.
    ld ix,(p415_destination_ptr)
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld (p415_old_destination_ptr),hl
    ld c,(ix+OBJ_STORAGE_LENGTH)
    ld b,(ix+OBJ_STORAGE_LENGTH+1)
    bit 0,c
    jr z,zx48_p415_old_length_ready
    inc bc
zx48_p415_old_length_ready:
    ld (p415_old_destination_length),bc

    ; Build the complete replacement record privately. The source payload pointer,
    ; lengths, flags and type are copied as metadata only; payload bytes are never
    ; read, copied, decoded, packed or recompressed.
    ld hl,(p414_source_ptr)
    ld de,p415_replacement_record
    ld bc,OBJ_RECORD_SIZE
    ldir
    ld hl,p414_new_name
    ld de,p415_replacement_record+OBJ_NAME
    ld bc,10
    ldir
    ld a,(p414_new_dir)
    ld (p415_replacement_record+OBJ_DIR_ID),a

    ; Single metadata publication step: the destination entry now owns the source
    ; payload. No fallible operation occurs before this point after validation.
    ld hl,p415_replacement_record
    ld de,(p415_destination_ptr)
    ld bc,OBJ_RECORD_SIZE
    ldir

    ; Release the superseded destination payload only after publication. Allocator
    ; corruption after commit is fatal rather than observable partial rename state.
    ld hl,(p415_old_destination_ptr)
    ld a,h
    or l
    jr z,zx48_p415_remove_source
    ld bc,(p415_old_destination_length)
    call zx48_free
    jr nc,zx48_p415_remove_source
    ld a,PANIC_SCHEDULER
    jp zx48_panic

zx48_p415_remove_source:
    ; Remove the old source name/slot after ownership has transferred.
    ld hl,p415_zero_record
    ld de,(p414_source_ptr)
    ld bc,OBJ_RECORD_SIZE
    ldir
    ld hl,0
    xor a
    ret

; IX -> resident mutable record. Reject malformed metadata before replacement.
zx48_p415_record_validate:
    ld a,(ix+OBJ_RESERVED_BYTE)
    or a
    jr nz,zx48_p415_invalid
    ld a,(ix+OBJ_FLAGS_BYTE)
    and $fe
    jr nz,zx48_p415_invalid

    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld e,(ix+OBJ_STORAGE_LENGTH)
    ld d,(ix+OBJ_STORAGE_LENGTH+1)
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    jr nz,zx48_p415_validate_packed
    or a
    sbc hl,de
    jr nz,zx48_p415_invalid
    jr zx48_p415_validate_allocation

zx48_p415_validate_packed:
    or a
    sbc hl,de
    jr c,zx48_p415_invalid
    jr z,zx48_p415_invalid

zx48_p415_validate_allocation:
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld a,d
    or e
    jr z,zx48_p415_storage_zero
    ld a,h
    or l
    jr z,zx48_p415_invalid
    xor a
    ret
zx48_p415_storage_zero:
    ld a,h
    or l
    jr nz,zx48_p415_invalid
    xor a
    ret

zx48_p415_invalid:
    ld a,E_INVAL
    scf
    ret

p415_destination_ptr: dw 0
p415_source_payload: dw 0
p415_old_destination_ptr: dw 0
p415_old_destination_length: dw 0
p415_destination_slot: db 0
p415_replacement_record: defs OBJ_RECORD_SIZE,0
p415_zero_record: defs OBJ_RECORD_SIZE,0
    ENDM

;
; P4.19 existing-object writable-open transaction. Resource reservation may
; happen first, but the handle is not returned to the caller until a PACKED
; object has become a completely decoded RAW replacement. O_TRUNC bypasses decode.
;
    MACRO EMIT_P419_WRITABLE_OPEN_ROUTINES
; A=open flags,C=object slot -> HL=handle. P4.06 exclusivity remains prerequisite.
zx48_p419_open_existing:
    ld (p419_open_flags),a
    ld a,c
    ld (p419_open_slot),a

    call zx48_p405_object_ptr_slot
    ret c

    ; This helper is specifically the writable-existing-object transaction.
    ld a,(p419_open_flags)
    and O_WRITE
    jr z,zx48_p419_open_invalid

    ; Reserve OD and process-handle capacity before any object representation change.
    ld a,(p419_open_slot)
    ld d,a
    ld b,OD_KIND_OBJECT
    ld a,(p419_open_flags)
    ld c,a
    call zx48_p406_od_create
    ret c
    ld (p419_open_od),a
    ld c,a
    ld a,HANDLE_FREE
    call zx48_handle_install
    jr c,zx48_p419_open_handle_fail
    ld (p419_open_handle),a

    ld a,(p419_open_slot)
    call zx48_p405_object_ptr_slot
    jr c,zx48_p419_open_internal_fail

    ld a,(p419_open_flags)
    and O_TRUNC
    jr nz,zx48_p419_open_truncate

    ; Non-truncating writer cannot be returned while the object remains PACKED.
    call zx48_p419_materialize_private
    jr c,zx48_p419_open_materialize_fail
    jr zx48_p419_open_success

zx48_p419_open_truncate:
    call zx48_p405_object_truncate
    jr c,zx48_p419_open_internal_fail

zx48_p419_open_success:
    ld a,(p419_open_handle)
    ld l,a
    ld h,0
    xor a
    or a
    ret

zx48_p419_open_materialize_fail:
    ld (p419_open_error),a
    ld a,(p419_open_handle)
    call zx48_handle_close
    jr c,zx48_p419_open_panic
    ld a,(p419_open_error)
    scf
    ret

zx48_p419_open_handle_fail:
    ld (p419_open_error),a
    ld a,(p419_open_od)
    call zx48_od_release
    jr c,zx48_p419_open_panic
    ld a,(p419_open_error)
    scf
    ret

zx48_p419_open_internal_fail:
    ld (p419_open_error),a
    ld a,(p419_open_handle)
    call zx48_handle_close
    jr c,zx48_p419_open_panic
    ld a,(p419_open_error)
    scf
    ret

zx48_p419_open_invalid:
    ld a,E_INVAL
    scf
    ret
zx48_p419_open_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

p419_open_flags: db 0
p419_open_slot: db 0
p419_open_od: db 0
p419_open_handle: db 0
p419_open_error: db 0
    ENDM

;
; P4.22 SYS_PACK exact path contract. HL points to a NUL-terminated path.
;
    MACRO EMIT_P422_SYS_PACK_OBJECT_ROUTINES
zx48_p422_sys_pack:
    call zx48_path_resolve
    ret c
    ld d,a
    ld a,c
    cp PATH_KIND_BASE
    jr nz,zx48_p422_sys_pack_perm
    ld a,d
    ld hl,path_name
    call zx48_p405_object_lookup
    ret c
    ld a,c
    ld d,a
    jp zx48_p422_pack_record
zx48_p422_sys_pack_perm:
    ld a,E_PERM
    scf
    ret
    ENDM
