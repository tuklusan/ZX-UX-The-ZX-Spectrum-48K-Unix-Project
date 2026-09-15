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
; P2.12 staged SYS_EXEC atomic replacement transaction.  The resident syscall
; table remains frozen while Phase-2 fixtures certify this exact source.  HL
; points to the caller's PROC1.  Success never returns: the new initial context
; is restored directly.  Every fallible operation precedes descriptor mutation
; and release of the old image, so every failure resumes the old image intact.
;
; Dependencies emitted by the fixture: user-range validation, allocator,
; relocation, ARG1/ENV1, initial-context, process lookup, spawn object resolver,
; and the P2.10 MEX1 validator.

    MACRO EMIT_EXEC_TRANSACTION_ROUTINES
zx48_sys_exec:
    ld hl,(syscall_arg_hl)
    call zx48_sys_exec_preflight
    ret c
    ld hl,(syscall_arg_hl)
    jp zx48_process_exec_transaction

zx48_sys_exec_preflight:
    ld bc,PROC1_SIZE
    call zx48_user_range_validate
    ret c
    push hl
    pop ix

    ; EXEC consumes PROC1 but may not rewire the current process.  All three
    ; std-handle selector bytes are therefore the sentinel 0xFF.
    ld a,(ix+PROC1_STDIN_HANDLE)
    cp HANDLE_FREE
    jr nz,zx48_sys_exec_invalid
    ld a,(ix+PROC1_STDOUT_HANDLE)
    cp HANDLE_FREE
    jr nz,zx48_sys_exec_invalid
    ld a,(ix+PROC1_STDERR_HANDLE)
    cp HANDLE_FREE
    jr nz,zx48_sys_exec_invalid
    ld a,(ix+PROC1_FLAGS)
    and $FE
    jr nz,zx48_sys_exec_invalid
    ld a,(ix+PROC1_RESERVED)
    or (ix+PROC1_RESERVED+1)
    jr nz,zx48_sys_exec_invalid

    ld l,(ix+PROC1_ARG1_PTR)
    ld h,(ix+PROC1_ARG1_PTR+1)
    ld c,(ix+PROC1_ARG1_LEN)
    ld b,(ix+PROC1_ARG1_LEN+1)
    call zx48_user_range_validate
    ret c
    ld l,(ix+PROC1_ENV1_PTR)
    ld h,(ix+PROC1_ENV1_PTR+1)
    ld c,(ix+PROC1_ENV1_LEN)
    ld b,(ix+PROC1_ENV1_LEN+1)
    call zx48_user_range_validate
    ret c

    ld l,(ix+PROC1_PATH_PTR)
    ld h,(ix+PROC1_PATH_PTR+1)
    ld d,PROC1_PATH_MAX+1
zx48_sys_exec_path:
    push de
    ld bc,1
    call zx48_user_range_validate
    pop de
    ret c
    ld a,(hl)
    or a
    jr z,zx48_sys_exec_path_done
    inc hl
    dec d
    jr nz,zx48_sys_exec_path
    ld a,E_TOOLONG
    scf
    ret
zx48_sys_exec_path_done:
    ld a,d
    cp PROC1_PATH_MAX+1
    jr z,zx48_sys_exec_invalid
    xor a
    ret
zx48_sys_exec_invalid:
    ld a,E_INVAL
    scf
    ret

zx48_process_exec_transaction:
    ld (process_exec_proc1),hl
    xor a
    ld (process_exec_image_base),a
    ld (process_exec_image_base+1),a
    ld (process_exec_stack_base),a
    ld (process_exec_stack_base+1),a
    ld (process_exec_bootstrap_base),a
    ld (process_exec_bootstrap_base+1),a

    ; Snapshot only release metadata.  Identity fields stay in the live
    ; descriptor and are never overwritten: PID, parent, all eight handles,
    ; cwd, and therefore shell pipeline wiring remain byte-identical.
    ld a,(current_pid)
    or a
    jp z,zx48_process_exec_invalid_state
    call zx48_process_lookup
    jp c,zx48_process_exec_return_error
    ld (process_exec_desc),ix
    ld a,(ix+PROC_STATE)
    cp PROC_RUNNING
    jp nz,zx48_process_exec_invalid_state
    ld l,(ix+PROC_IMAGE_BASE)
    ld h,(ix+PROC_IMAGE_BASE+1)
    ld (process_exec_old_image),hl
    ld l,(ix+PROC_IMAGE_SIZE)
    ld h,(ix+PROC_IMAGE_SIZE+1)
    ld (process_exec_old_image_size),hl
    ld l,(ix+PROC_STACK_LOW)
    ld h,(ix+PROC_STACK_LOW+1)
    ld (process_exec_old_stack),hl
    ld e,(ix+PROC_STACK_HIGH)
    ld d,(ix+PROC_STACK_HIGH+1)
    ex de,hl
    or a
    sbc hl,de
    ld (process_exec_old_stack_size),hl
    ld l,(ix+PROC_ARG_PTR)
    ld h,(ix+PROC_ARG_PTR+1)
    ld (process_exec_old_bootstrap),hl
    ld a,h
    or l
    jp z,zx48_process_exec_invalid_state

    ; The descriptor's owned-byte total is authoritative.  Derive the
    ; old bootstrap allocation as owned-image-stack and never inspect
    ; ARG1/ENV1 payload bytes while deciding what extent to release.
    ld l,(ix+PROC_OWNED_BYTES)
    ld h,(ix+PROC_OWNED_BYTES+1)
    ld de,(process_exec_old_image_size)
    or a
    sbc hl,de
    jp c,zx48_process_exec_invalid_state
    ld de,(process_exec_old_stack_size)
    or a
    sbc hl,de
    jp c,zx48_process_exec_invalid_state
    ld a,h
    or l
    jp z,zx48_process_exec_invalid_state
    ld (process_exec_old_bootstrap_size),hl

    ; Resolve and validate replacement before allocating or mutating anything.
    ld hl,(process_exec_proc1)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (process_exec_path),de
    ex de,hl
    call zx48_spawn_resolve_ram_object
    jp c,zx48_process_exec_return_error
    ld (process_exec_object),ix
    ld a,(ix+OBJ_TYPE_ID)
    cp OBJ_BIN
    jp nz,zx48_process_exec_format
    ld a,(ix+OBJ_FLAGS_BYTE)
    or a
    jp nz,zx48_process_exec_format
    ld a,(ix+OBJ_RESERVED_BYTE)
    or a
    jp nz,zx48_process_exec_format
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (process_exec_source_length),hl
    ld e,(ix+OBJ_STORAGE_LENGTH)
    ld d,(ix+OBJ_STORAGE_LENGTH+1)
    or a
    sbc hl,de
    jp nz,zx48_process_exec_format
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld a,h
    or l
    jp z,zx48_process_exec_format
    ld (process_exec_mex_source),hl
    push hl
    pop ix
    ld bc,(process_exec_source_length)
    call zx48_process_spawn_validate_mex1
    jp c,zx48_process_exec_return_error

    ; P2.12 validates both bootstrap blocks before old-image release.
    ld hl,(process_exec_proc1)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (process_exec_arg_src),de
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld (process_exec_arg_len),bc
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (process_exec_env_src),de
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (process_exec_env_len),de
    ld ix,(process_exec_arg_src)
    ld bc,(process_exec_arg_len)
    ld hl,(process_exec_path)
    call zx48_arg1_validate
    jp c,zx48_process_exec_return_error
    ld ix,(process_exec_env_src)
    ld bc,(process_exec_env_len)
    call zx48_env1_validate
    jp c,zx48_process_exec_return_error

    ld hl,(process_exec_arg_len)
    ld de,(process_exec_env_len)
    add hl,de
    jp c,zx48_process_exec_format
    ld a,h
    cp BOOTSTRAP_MAX_PAYLOAD/256
    jr c,zx48_process_exec_bootstrap_ok
    jp nz,zx48_process_exec_format
    ld a,l
    or a
    jp nz,zx48_process_exec_format
zx48_process_exec_bootstrap_ok:
    ld (process_exec_bootstrap_exact),hl
    bit 0,l
    jr z,zx48_process_exec_bootstrap_rounded
    inc hl
zx48_process_exec_bootstrap_rounded:
    ld (process_exec_bootstrap_size),hl

    ; Validator populated the shared P2.10 MEX1 size scratch.
    ld hl,(process_spawn_image_size_rounded)
    ld (process_exec_image_size),hl
    ld hl,(process_spawn_stack_size)
    ld (process_exec_stack_size),hl

    ; Build the complete replacement privately while the old descriptor and
    ; all old extents remain live.
    ld bc,(process_exec_image_size)
    ld a,ALLOC_ANY
    call zx48_alloc
    jp c,zx48_process_exec_return_error
    ld (process_exec_image_base),hl
    ld bc,(process_exec_stack_size)
    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    jp c,zx48_process_exec_rollback
    ld (process_exec_stack_base),hl
    ld bc,(process_exec_bootstrap_size)
    ld a,ALLOC_ANY
    call zx48_alloc
    jp c,zx48_process_exec_rollback
    ld (process_exec_bootstrap_base),hl

    ex de,hl
    ld hl,(process_exec_arg_src)
    ld bc,(process_exec_arg_len)
    ldir
    ld (process_exec_env_ptr),de
    ld hl,(process_exec_env_src)
    ld bc,(process_exec_env_len)
    ldir
    ld hl,(process_exec_bootstrap_exact)
    bit 0,l
    jr z,zx48_process_exec_bootstrap_copied
    xor a
    ld (de),a
zx48_process_exec_bootstrap_copied:

    ld hl,(process_exec_mex_source)
    ld de,MEX_HEADER_SIZE
    add hl,de
    ld de,(process_exec_image_base)
    ld bc,(process_spawn_image_size)
    ldir
    ld bc,(process_spawn_bss_size)
    ld a,b
    or c
    jr z,zx48_process_exec_relocate
    xor a
    ld (de),a
    dec bc
    ld a,b
    or c
    jr z,zx48_process_exec_relocate
    ld h,d
    ld l,e
    inc de
    ldir
zx48_process_exec_relocate:
    ld ix,(process_exec_mex_source)
    ld de,(process_exec_image_base)
    call zx48_mex1_relocate
    jp c,zx48_process_exec_rollback

    ld hl,(process_exec_image_base)
    ld (process_exec_context_seed+INITIAL_CONTEXT_IMAGE_BASE),hl
    ld hl,(process_exec_stack_base)
    ld (process_exec_context_seed+INITIAL_CONTEXT_STACK_BASE),hl
    ld hl,(process_exec_stack_size)
    ld (process_exec_context_seed+INITIAL_CONTEXT_STACK_SIZE),hl
    ld hl,(process_exec_bootstrap_base)
    ld (process_exec_context_seed+INITIAL_CONTEXT_ARG_PTR),hl
    ld hl,(process_exec_arg_len)
    ld (process_exec_context_seed+INITIAL_CONTEXT_ARG_LEN),hl
    ld hl,(process_exec_env_ptr)
    ld (process_exec_context_seed+INITIAL_CONTEXT_ENV_PTR),hl
    ld ix,(process_exec_mex_source)
    ld hl,process_exec_context_seed
    call zx48_process_build_initial_context
    jp c,zx48_process_exec_rollback
    ld (process_exec_saved_sp),hl

    ; Commit contains no fallible operation.  Identity bytes are deliberately
    ; absent from this write set.
    ld ix,(process_exec_desc)
    ld hl,(process_exec_image_base)
    ld (ix+PROC_IMAGE_BASE),l
    ld (ix+PROC_IMAGE_BASE+1),h
    ld hl,(process_exec_image_size)
    ld (ix+PROC_IMAGE_SIZE),l
    ld (ix+PROC_IMAGE_SIZE+1),h
    ld hl,(process_exec_stack_base)
    ld (ix+PROC_STACK_LOW),l
    ld (ix+PROC_STACK_LOW+1),h
    ld de,(process_exec_stack_size)
    add hl,de
    ld (ix+PROC_STACK_HIGH),l
    ld (ix+PROC_STACK_HIGH+1),h
    ld hl,(process_exec_saved_sp)
    ld (ix+PROC_SAVED_SP),l
    ld (ix+PROC_SAVED_SP+1),h
    xor a
    ld (ix+PROC_EXIT_STATUS),a
    ld (ix+PROC_WAIT_OBJECT),a
    ld (ix+PROC_WAKE_TICK+0),a
    ld (ix+PROC_WAKE_TICK+1),a
    ld (ix+PROC_WAKE_TICK+2),a
    ld (ix+PROC_WAKE_TICK+3),a
    push ix
    pop de
    ld hl,PROC_NAME
    add hl,de
    ex de,hl
    ld hl,(process_exec_object)
    ld bc,10
    ldir
    ld hl,(process_exec_image_size)
    ld de,(process_exec_stack_size)
    add hl,de
    ld de,(process_exec_bootstrap_size)
    add hl,de
    ld (ix+PROC_OWNED_BYTES),l
    ld (ix+PROC_OWNED_BYTES+1),h
    ld hl,(process_exec_bootstrap_base)
    ld (ix+PROC_ARG_PTR),l
    ld (ix+PROC_ARG_PTR+1),h
    ld hl,(process_exec_env_ptr)
    ld (ix+PROC_ENV_PTR),l
    ld (ix+PROC_ENV_PTR+1),h
    xor a
    ld (ix+PROC_FLAGS),a
    ld a,PROC_PRIVATE_STARTED
    ld (ix+PROC_PRIVATE_FLAGS),a
    xor a
    ld (ix+PROC_RESERVED),a

    ; Only after publication is irreversible do we release the old private
    ; extents.  Handles are not touched and therefore need no retain/release.
    ld hl,(process_exec_old_bootstrap)
    ld bc,(process_exec_old_bootstrap_size)
    call zx48_free
    ld hl,(process_exec_old_stack)
    ld bc,(process_exec_old_stack_size)
    call zx48_free
    ld hl,(process_exec_old_image)
    ld bc,(process_exec_old_image_size)
    call zx48_free

    ; Successful exec never returns through the old syscall frame.  Restore the
    ; newly constructed frame directly and RET to the replacement MEX1 entry.
    ld hl,(process_exec_saved_sp)
    ld sp,hl
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ld iy,ROM_IY_ANCHOR
    ret

zx48_process_exec_rollback:
    ld (process_exec_error),a
    ld hl,(process_exec_bootstrap_base)
    ld a,h
    or l
    jr z,zx48_process_exec_free_stack
    ld bc,(process_exec_bootstrap_size)
    call zx48_free
zx48_process_exec_free_stack:
    ld hl,(process_exec_stack_base)
    ld a,h
    or l
    jr z,zx48_process_exec_free_image
    ld bc,(process_exec_stack_size)
    call zx48_free
zx48_process_exec_free_image:
    ld hl,(process_exec_image_base)
    ld a,h
    or l
    jr z,zx48_process_exec_rollback_done
    ld bc,(process_exec_image_size)
    call zx48_free
zx48_process_exec_rollback_done:
    ld a,(process_exec_error)
    scf
    ret
zx48_process_exec_invalid_state:
    ld a,E_INVAL
zx48_process_exec_return_error:
    scf
    ret
zx48_process_exec_format:
    ld a,E_FORMAT
    scf
    ret

process_exec_proc1: dw 0
process_exec_desc: dw 0
process_exec_object: dw 0
process_exec_path: dw 0
process_exec_mex_source: dw 0
process_exec_source_length: dw 0
process_exec_arg_src: dw 0
process_exec_arg_len: dw 0
process_exec_env_src: dw 0
process_exec_env_len: dw 0
process_exec_image_base: dw 0
process_exec_image_size: dw 0
process_exec_stack_base: dw 0
process_exec_stack_size: dw 0
process_exec_bootstrap_base: dw 0
process_exec_bootstrap_exact: dw 0
process_exec_bootstrap_size: dw 0
process_exec_env_ptr: dw 0
process_exec_saved_sp: dw 0
process_exec_old_image: dw 0
process_exec_old_image_size: dw 0
process_exec_old_stack: dw 0
process_exec_old_stack_size: dw 0
process_exec_old_bootstrap: dw 0
process_exec_old_bootstrap_size: dw 0
process_exec_error: db 0
process_exec_context_seed: defs INITIAL_CONTEXT_SEED_SIZE,0
    ENDM
