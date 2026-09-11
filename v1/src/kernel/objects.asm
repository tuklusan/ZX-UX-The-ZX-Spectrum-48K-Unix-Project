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
zx48_path_resolve:
    ld (path_source),hl
    ld b,0
zx48_path_len:
    ld a,(hl)
    or a
    jr z,zx48_path_len_ok
    inc b
    ld a,b
    cp 32
    jr nc,zx48_path_long
    inc hl
    jr zx48_path_len
zx48_path_len_ok:
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
    ld hl,path_name
    call zx48_name_validate
    ret c
    ld a,(path_dir)
    ld c,PATH_KIND_BASE
    or a
    ret
zx48_path_parent:
    ld a,(path_dir)
    cp DIR_USERHOME
    jr z,zx48_path_parent_home
    or a
    jr z,zx48_path_component_next
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
    ld a,(path_dir)
    ld c,PATH_KIND_DIR
    or a
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
