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
; Fixed eight-process table. Runnable CPU state lives on each FAST stack.

PROC_PID                  EQU 0
PROC_PARENT               EQU 1
PROC_STATE                EQU 2
PROC_FLAGS                EQU 3
PROC_IMAGE_BASE           EQU 4
PROC_IMAGE_SIZE           EQU 6
PROC_STACK_LOW            EQU 8
PROC_STACK_HIGH           EQU 10
PROC_SAVED_SP             EQU 12
PROC_EXIT_STATUS          EQU 14
PROC_WAIT_OBJECT          EQU 15
PROC_HANDLES              EQU 16
PROC_WAKE_TICK            EQU 24
PROC_CWD                  EQU 28
PROC_NAME                 EQU 29
PROC_OWNED_BYTES          EQU 40
PROC_ARG_PTR              EQU 42
PROC_ENV_PTR              EQU 44
PROC_PRIVATE_FLAGS        EQU 46
PROC_RESERVED             EQU 47
PROCESS_STACK_BOOTSTRAP_BYTES EQU 64
ARG1_HEADER_SIZE              EQU 8
ARG1_MAX_SIZE                 EQU 256
ARG1_MAX_COUNT                EQU 16
ENV1_HEADER_SIZE              EQU 8
ENV1_MAX_SIZE                 EQU 256
ENV1_MAX_COUNT                EQU 8
ENV1_MAX_NAME                 EQU 15
ENV1_MAX_VALUE                EQU 63
BOOTSTRAP_MAX_PAYLOAD         EQU 512
PROCESS_CONTEXT_FRAME_BYTES   EQU 12
INITIAL_CONTEXT_IMAGE_BASE    EQU 0
INITIAL_CONTEXT_STACK_BASE    EQU 2
INITIAL_CONTEXT_STACK_SIZE    EQU 4
INITIAL_CONTEXT_ARG_PTR       EQU 6
INITIAL_CONTEXT_ARG_LEN       EQU 8
INITIAL_CONTEXT_ENV_PTR       EQU 10
INITIAL_CONTEXT_SEED_SIZE     EQU 12

; P2.09 pure PID-capacity scan. The helper performs no writes and deliberately
; examines exactly PID2..PID7. Success leaves IX at the first FREE descriptor,
; C/A equal to its PID, and carry clear. A full table returns E_AGAIN/carry set.
    MACRO EMIT_PROCESS_CAPACITY_ROUTINE
zx48_process_find_free_slot:
    ld ix,process_table+2*PROC_DESC_SIZE
    ld c,2
    ld b,MAX_PROCESSES-2
zx48_process_find_free_scan:
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_find_free_found
    ld de,PROC_DESC_SIZE
    add ix,de
    inc c
    djnz zx48_process_find_free_scan
    ld a,E_AGAIN
    scf
    ret
zx48_process_find_free_found:
    ld a,c
    or a
    ret
    ENDM

    MACRO EMIT_PROCESS_ROUTINES
zx48_process_init:
    xor a
    ld hl,process_table
    ld de,process_table+1
    ld bc,MAX_PROCESSES*PROC_DESC_SIZE-1
    ld (hl),a
    ldir
    ld ix,process_table
    ld c,0
    ld b,MAX_PROCESSES
zx48_process_init_loop:
    ld (ix+PROC_PID),c
    ld (ix+PROC_PARENT),HANDLE_FREE
    push bc
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld b,MAX_HANDLES_PER_PROCESS
    ld a,HANDLE_FREE
zx48_process_init_handles:
    ld (hl),a
    inc hl
    djnz zx48_process_init_handles
    pop bc
    ld de,PROC_DESC_SIZE
    add ix,de
    inc c
    djnz zx48_process_init_loop
    ld ix,process_table
    ld (ix+PROC_STATE),PROC_RUNNING
    xor a
    ld (current_pid),a
    ret

zx48_process_ptr:
    cp MAX_PROCESSES
    jr nc,zx48_process_noent
    ld c,a
    ld ix,process_table
    or a
    ret z
    ld b,a
    ld de,PROC_DESC_SIZE
zx48_process_ptr_loop:
    add ix,de
    djnz zx48_process_ptr_loop
    xor a
    ret
zx48_process_lookup:
    call zx48_process_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_noent
    xor a
    ret
zx48_process_live_lookup:
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jr z,zx48_process_noent
    xor a
    ret
zx48_process_noent:
    ld a,E_NOENT
    scf
    ret

    EMIT_PROCESS_CAPACITY_ROUTINE

zx48_process_reserve_slot:
    call zx48_process_find_free_slot
    ret c
    ld (process_temp_pid),a
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,PROC_DESC_SIZE-1
    ldir
    ld a,(process_temp_pid)
    ld (ix+PROC_PID),a
    ld a,(current_pid)
    ld (ix+PROC_PARENT),a
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld b,MAX_HANDLES_PER_PROCESS
    ld a,HANDLE_FREE
zx48_process_reserve_handles:
    ld (hl),a
    inc hl
    djnz zx48_process_reserve_handles
    ld a,(process_temp_pid)
    or a
    ret

zx48_process_prepare_pid1:
    ld a,1
    call zx48_process_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jr nz,zx48_process_busy
    ld (ix+PROC_STATE),PROC_READY
    xor a
    ld (ix+PROC_PARENT),a
    ld (ix+PROC_CWD),DIR_ROOT
    push ix
    pop de
    ld hl,PROC_NAME
    add hl,de
    ex de,hl
    ld hl,process_name_sh
    ld bc,10
    ldir
    xor a
    ret
zx48_process_busy:
    ld a,E_BUSY
    scf
    ret

zx48_process_count:
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_PROCESSES-1
    ld c,0
zx48_process_count_loop:
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_count_next
    inc c
zx48_process_count_next:
    ld de,PROC_DESC_SIZE
    add ix,de
    djnz zx48_process_count_loop
    ld a,c
    or a
    ret

zx48_process_info:
    ld (process_info_ptr),hl
    call zx48_process_lookup
    ret c
    ld hl,(process_info_ptr)
    ld a,(ix+PROC_PID)
    ld (hl),a
    inc hl
    ld a,(ix+PROC_PARENT)
    ld (hl),a
    inc hl
    ld a,(ix+PROC_STATE)
    ld (hl),a
    inc hl
    ld a,(ix+PROC_FLAGS)
    and PROC_FLAG_CANCEL
    ld (hl),a
    inc hl
    push hl
    push ix
    pop hl
    ld de,PROC_NAME
    add hl,de
    ex de,hl
    pop hl
    ld b,10
zx48_process_info_name:
    ld a,(de)
    ld (hl),a
    inc de
    inc hl
    djnz zx48_process_info_name
    ld a,(ix+PROC_OWNED_BYTES)
    ld (hl),a
    inc hl
    ld a,(ix+PROC_OWNED_BYTES+1)
    ld (hl),a
    xor a
    ret

zx48_process_exit:
    ld (process_temp_status),a
    ld a,(current_pid)
    or a
    jr z,zx48_process_exit_panic
    call zx48_process_lookup
    jr c,zx48_process_exit_panic
    ld a,(process_temp_status)
    ld (ix+PROC_EXIT_STATUS),a
    ld (ix+PROC_STATE),PROC_ZOMBIE
    call zx48_handles_close_all_current
    call zx48_process_wake_parent
    call zx48_process_restore_tty_owner
    jp zx48_schedule
zx48_process_exit_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

; If the exiting process owned tty input, hand it back to live PID1 or PID0.
zx48_process_restore_tty_owner:
    ld a,(current_pid)
    ld b,a
    ld a,(tty_input_owner)
    cp b
    ret nz
    ld a,1
    call zx48_process_live_lookup
    jr c,zx48_process_tty_owner_zero
    ld a,1
    jr zx48_process_tty_owner_set
zx48_process_tty_owner_zero:
    xor a
zx48_process_tty_owner_set:
    ld (tty_input_owner),a
    ret

zx48_process_wake_parent:
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_PARENT)
    cp HANDLE_FREE
    ret z
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_STATE)
    cp PROC_WAIT_CHILD
    ret nz
    ld (ix+PROC_STATE),PROC_READY
    ret

zx48_process_kill:
    cp 2
    jr c,zx48_process_perm
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jp z,zx48_process_noent
    ld a,(current_pid)
    cp 1
    jr z,zx48_process_kill_ok
    ld b,a
    ld a,(ix+PROC_PARENT)
    cp b
    jr nz,zx48_process_perm
zx48_process_kill_ok:
    ld a,(ix+PROC_PRIVATE_FLAGS)
    and PROC_PRIVATE_STARTED
    jr nz,zx48_process_kill_started
    ld (ix+PROC_EXIT_STATUS),130
    ld (ix+PROC_STATE),PROC_ZOMBIE
    xor a
    ret
zx48_process_kill_started:
    ld a,(ix+PROC_FLAGS)
    or PROC_FLAG_CANCEL
    ld (ix+PROC_FLAGS),a
    ; Any started non-zombie target is not the current cooperative task.
    ; Make it runnable; scheduler delivers E_INTR at the next safe restore.
    xor a
    ld (ix+PROC_WAIT_OBJECT),a
    ld (ix+PROC_STATE),PROC_READY
zx48_process_kill_okret:
    xor a
    ret
zx48_process_perm:
    ld a,E_PERM
    scf
    ret

zx48_process_wait:
    ld (process_wait_target),a
zx48_process_wait_again:
    xor a
    ld (process_wait_has_child),a
    ld ix,process_table+2*PROC_DESC_SIZE
    ld b,MAX_PROCESSES-2
zx48_process_wait_each:
    ld a,(ix+PROC_PARENT)
    ld c,a
    ld a,(current_pid)
    cp c
    jr nz,zx48_process_wait_next
    ld a,(process_wait_target)
    cp $ff
    jr z,zx48_process_wait_state
    ld c,a
    ld a,(ix+PROC_PID)
    cp c
    jr nz,zx48_process_wait_next
zx48_process_wait_state:
    ld a,1
    ld (process_wait_has_child),a
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jr z,zx48_process_wait_reap
zx48_process_wait_next:
    push bc
    ld bc,PROC_DESC_SIZE
    add ix,bc
    pop bc
    djnz zx48_process_wait_each
    ld a,(process_wait_has_child)
    or a
    jr z,zx48_process_wait_none
    ld a,(current_pid)
    call zx48_process_lookup
    ld (ix+PROC_STATE),PROC_WAIT_CHILD
    jp zx48_schedule
zx48_process_wait_none:
    ld a,E_CHILD
    scf
    ret
zx48_process_wait_reap:
    ld a,(ix+PROC_EXIT_STATUS)
    ld (de),a
    ld a,(ix+PROC_PID)
    ld l,a
    ld h,0
    push hl
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,PROC_DESC_SIZE-1
    ldir
    pop hl
    xor a
    ret

process_name_sh: db 's','h',0,0,0,0,0,0,0,0
process_info_ptr: dw 0
process_temp_pid: db 0
process_temp_status: db 0
process_wait_target: db 0
process_wait_has_child: db 0
current_pid: db 0
process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0
    ENDM


; P2.03 ABS16 relocation validator/applicator. The routine remains a separate
; emitter so Phase-2 loader transactions can compose it without consuming the
; frozen resident-kernel headroom before spawn/exec integration is complete.
; IX -> validated MEX1 header/source object, DE = actual copied image base.
; The complete table is validated without target writes; only then are ABS16
; words patched in a second pass. Returns A=0/C clear or A=E_FORMAT/C set.
    MACRO EMIT_MEX1_RELOCATION_ROUTINES
zx48_mex1_relocate:
    push ix
    pop hl
    ld (process_mex_header),hl
    ld (process_mex_base),de

    ld l,(ix+MEX_HDR_IMAGE_SIZE)
    ld h,(ix+MEX_HDR_IMAGE_SIZE+1)
    ld a,h
    or l
    jp z,zx48_mex1_relocate_format
    ld (process_mex_image_size),hl

    ld e,(ix+MEX_HDR_BSS_SIZE)
    ld d,(ix+MEX_HDR_BSS_SIZE+1)
    add hl,de
    jp c,zx48_mex1_relocate_format
    ld a,h
    cp $80
    jr c,zx48_mex1_relocate_alloc_ok
    jp nz,zx48_mex1_relocate_format
    ld a,l
    or a
    jp nz,zx48_mex1_relocate_format
zx48_mex1_relocate_alloc_ok:
    ld (process_mex_alloc_size),hl

    ; The destination allocation must be wholly inside the user arena.
    ld hl,(process_mex_base)
    ld de,ARENA_START
    or a
    sbc hl,de
    jp c,zx48_mex1_relocate_format
    ld hl,(process_mex_base)
    ld de,(process_mex_alloc_size)
    add hl,de
    jp c,zx48_mex1_relocate_format
    ld de,ARENA_END+1
    or a
    sbc hl,de
    jr c,zx48_mex1_relocate_base_range_ok
    jp nz,zx48_mex1_relocate_format
zx48_mex1_relocate_base_range_ok:

    ld c,(ix+MEX_HDR_RELOC_COUNT)
    ld b,(ix+MEX_HDR_RELOC_COUNT+1)
    ld (process_mex_reloc_count),bc
    ld a,b
    or c
    jr z,zx48_mex1_relocate_image_size_checked
    ld hl,(process_mex_image_size)
    ld a,h
    or a
    jr nz,zx48_mex1_relocate_image_size_checked
    ld a,l
    cp 2
    jp c,zx48_mex1_relocate_format
zx48_mex1_relocate_image_size_checked:

    ; Widen before narrowing: 24+image, count*2, and table end must not wrap.
    ld hl,(process_mex_image_size)
    ld de,MEX_HEADER_SIZE
    add hl,de
    jp c,zx48_mex1_relocate_format
    ld e,(ix+MEX_HDR_RELOC_OFFSET)
    ld d,(ix+MEX_HDR_RELOC_OFFSET+1)
    or a
    sbc hl,de
    jp nz,zx48_mex1_relocate_format
    ld (process_mex_reloc_offset),de

    ld hl,(process_mex_reloc_count)
    add hl,hl
    jp c,zx48_mex1_relocate_format
    ld de,(process_mex_reloc_offset)
    add hl,de
    jp c,zx48_mex1_relocate_format
    ld a,h
    cp $80
    jr c,zx48_mex1_relocate_stored_ok
    jp nz,zx48_mex1_relocate_format
    ld a,l
    or a
    jp nz,zx48_mex1_relocate_format
zx48_mex1_relocate_stored_ok:
    ld bc,(process_mex_reloc_count)
    ld a,b
    or c
    jp z,zx48_mex1_relocate_success

    ld hl,(process_mex_header)
    ld de,(process_mex_reloc_offset)
    add hl,de
    jp c,zx48_mex1_relocate_format
    push hl
    pop ix
    xor a
    ld (process_mex_have_previous),a

zx48_mex1_relocate_validate_loop:
    ld l,(ix+0)
    ld h,(ix+1)
    inc ix
    inc ix
    ld (process_mex_offset),hl

    ; offset <= image_size-2.
    ld de,(process_mex_image_size)
    dec de
    dec de
    or a
    sbc hl,de
    jp c,zx48_mex1_relocate_offset_in_image
    jp nz,zx48_mex1_relocate_format
zx48_mex1_relocate_offset_in_image:
    ; Each entry after the first must be at least previous+2.
    ld a,(process_mex_have_previous)
    or a
    jr z,zx48_mex1_relocate_order_ok
    ld hl,(process_mex_previous)
    inc hl
    inc hl
    ld de,(process_mex_offset)
    ex de,hl
    or a
    sbc hl,de
    jp c,zx48_mex1_relocate_format
zx48_mex1_relocate_order_ok:

    ; Read only from the already-copied private image. The stored ABS16 value
    ; is an image-relative address and may equal the one-past allocation size.
    ld hl,(process_mex_base)
    ld de,(process_mex_offset)
    add hl,de
    jp c,zx48_mex1_relocate_format
    ld e,(hl)
    inc hl
    ld d,(hl)
    push de
    ld hl,(process_mex_alloc_size)
    or a
    sbc hl,de
    jp c,zx48_mex1_relocate_format_pop
    pop hl
    ld de,(process_mex_base)
    add hl,de
    jp c,zx48_mex1_relocate_format

    ld hl,(process_mex_offset)
    ld (process_mex_previous),hl
    ld a,1
    ld (process_mex_have_previous),a
    dec bc
    ld a,b
    or c
    jr nz,zx48_mex1_relocate_validate_loop

    ; Second pass: all failure conditions are closed before the first write.
    ld hl,(process_mex_header)
    ld de,(process_mex_reloc_offset)
    add hl,de
    push hl
    pop ix
    ld bc,(process_mex_reloc_count)
zx48_mex1_relocate_apply_loop:
    ld l,(ix+0)
    ld h,(ix+1)
    inc ix
    inc ix
    ld de,(process_mex_base)
    add hl,de
    push hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(process_mex_base)
    add hl,de
    ex de,hl
    pop hl
    ld (hl),e
    inc hl
    ld (hl),d
    dec bc
    ld a,b
    or c
    jr nz,zx48_mex1_relocate_apply_loop
zx48_mex1_relocate_success:
    xor a
    ret
zx48_mex1_relocate_format_pop:
    pop de
zx48_mex1_relocate_format:
    ld a,E_FORMAT
    scf
    ret

process_mex_header: dw 0
process_mex_base: dw 0
process_mex_image_size: dw 0
process_mex_alloc_size: dw 0
process_mex_reloc_count: dw 0
process_mex_reloc_offset: dw 0
process_mex_offset: dw 0
process_mex_previous: dw 0
process_mex_have_previous: db 0
    ENDM

; P2.04 RAW MEX1 private image loader. IX points to an already header-validated
; source object. The routine reserves image+BSS with ALLOC_ANY, copies image
; bytes, zeroes BSS, and applies the certified ABS16 relocator before exposing
; the allocation to any process descriptor. On success HL=private image base,
; BC=rounded allocation length, A=0/C clear. On failure A=errno/C set and no
; loader-owned allocation remains live.
    MACRO EMIT_MEX1_IMAGE_LOAD_ROUTINES
zx48_mex1_load_image:
    push ix
    pop hl
    ld (process_mex_load_header),hl

    ld l,(ix+MEX_HDR_IMAGE_SIZE)
    ld h,(ix+MEX_HDR_IMAGE_SIZE+1)
    ld a,h
    or l
    jp z,zx48_mex1_load_format
    ld (process_mex_load_image_size),hl

    ld e,(ix+MEX_HDR_BSS_SIZE)
    ld d,(ix+MEX_HDR_BSS_SIZE+1)
    ld (process_mex_load_bss_size),de
    add hl,de
    jp c,zx48_mex1_load_format
    ld a,h
    cp $80
    jr c,zx48_mex1_load_size_ok
    jp nz,zx48_mex1_load_format
    ld a,l
    or a
    jp nz,zx48_mex1_load_format
zx48_mex1_load_size_ok:
    ld b,h
    ld c,l
    bit 0,c
    jr z,zx48_mex1_load_rounded
    inc bc
zx48_mex1_load_rounded:
    ld (process_mex_load_rounded),bc

    ld a,ALLOC_ANY
    call zx48_alloc
    ret c
    ld (process_mex_load_base),hl

    ex de,hl
    ld hl,(process_mex_load_header)
    ld bc,MEX_HEADER_SIZE
    add hl,bc
    ld bc,(process_mex_load_image_size)
    ldir

zx48_mex1_load_zero_bss:
    ld bc,(process_mex_load_bss_size)
    ld a,b
    or c
    jr z,zx48_mex1_load_relocate
    xor a
    ld (de),a
    dec bc
    ld a,b
    or c
    jr z,zx48_mex1_load_relocate
    ld h,d
    ld l,e
    inc de
    ldir

zx48_mex1_load_relocate:
    ld hl,(process_mex_load_header)
    push hl
    pop ix
    ld de,(process_mex_load_base)
    call zx48_mex1_relocate
    jr c,zx48_mex1_load_rollback
    ld hl,(process_mex_load_base)
    ld bc,(process_mex_load_rounded)
    xor a
    ret

zx48_mex1_load_rollback:
    ld (process_mex_load_error),a
    ld hl,(process_mex_load_base)
    ld bc,(process_mex_load_rounded)
    call zx48_free
    ld a,(process_mex_load_error)
    scf
    ret

zx48_mex1_load_format:
    ld a,E_FORMAT
    scf
    ret

process_mex_load_header: dw 0
process_mex_load_base: dw 0
process_mex_load_image_size: dw 0
process_mex_load_bss_size: dw 0
process_mex_load_rounded: dw 0
process_mex_load_error: db 0
    ENDM

; P2.05 private process-stack allocator. MEX_HDR_STACK already contains the
; linker-requested size or the frozen linker default. The advertised application
; stack is validated as even and 64..4096 bytes; the fixed 64-byte bootstrap
; reserve is added outside that advertised budget. IX -> validated MEX1 header.
; On success HL=private FAST stack base, BC=exact allocation length, A=0/C clear.
; On failure A=errno/C set and no stack allocation is created.
    MACRO EMIT_MEX1_STACK_ROUTINES
zx48_mex1_alloc_stack:
    ld c,(ix+MEX_HDR_STACK)
    ld b,(ix+MEX_HDR_STACK+1)
    bit 0,c
    jp nz,zx48_mex1_alloc_stack_format

    ld h,b
    ld l,c
    ld de,MEX_MIN_STACK
    or a
    sbc hl,de
    jp c,zx48_mex1_alloc_stack_format

    ld hl,MEX_MAX_STACK
    or a
    sbc hl,bc
    jp c,zx48_mex1_alloc_stack_format

    ld hl,PROCESS_STACK_BOOTSTRAP_BYTES
    add hl,bc
    jp c,zx48_mex1_alloc_stack_format
    ld b,h
    ld c,l
    ld (process_mex_stack_allocation_size),bc

    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    ret c
    ld bc,(process_mex_stack_allocation_size)
    xor a
    ret

zx48_mex1_alloc_stack_format:
    ld a,E_FORMAT
    scf
    ret

process_mex_stack_allocation_size: dw 0
    ENDM

; P2.06 ARG1 validator/private-copy builder. IX points to the caller-supplied
; ARG1 block, BC is its exact supplied byte length, and HL points to the exact
; NUL-terminated invocation token expected in argv[0]. Validation is complete
; and side-effect free before any allocator call. On successful validation,
; zx48_arg1_build reserves an uncommitted ALLOC_ANY extent and copies the exact
; immutable ARG1 bytes there. Success: HL=private copy base, BC=exact ARG1
; length, DE=rounded allocation length, A=0/C clear. Failure: A=errno/C set and
; no builder-owned allocation is created or process state published.
    MACRO EMIT_ARG1_ROUTINES
zx48_arg1_validate:
    ; Keep the expected argv[0] token in DE. Validation uses registers and the
    ; caller's stack only; malformed input cannot mutate allocator/process state
    ; or validator-owned persistent scratch.
    ld d,h
    ld e,l

    ; The shortest structurally possible block is header + one NUL byte.
    ld a,b
    or a
    jr nz,zx48_arg1_min_ok
    ld a,c
    cp ARG1_HEADER_SIZE+1
    jp c,zx48_arg1_format
zx48_arg1_min_ok:

    ; ARG1 is capped at 256 bytes exactly. BC=0100 is the only B=1 value valid.
    ld a,b
    cp 2
    jp nc,zx48_arg1_format
    or a
    jr z,zx48_arg1_size_ok
    ld a,c
    or a
    jp nz,zx48_arg1_format
zx48_arg1_size_ok:

    ; Reject source+length address-space wrap before any indexed header read.
    push ix
    pop hl
    add hl,bc
    jp c,zx48_arg1_format

    ld a,(ix+0)
    cp $41
    jp nz,zx48_arg1_format
    ld a,(ix+1)
    cp $52
    jp nz,zx48_arg1_format
    ld a,(ix+2)
    cp $47
    jp nz,zx48_arg1_format
    ld a,(ix+3)
    cp $31
    jp nz,zx48_arg1_format

    ld a,(ix+4)
    or a
    jp z,zx48_arg1_format
    cp ARG1_MAX_COUNT+1
    jp nc,zx48_arg1_format

    ld a,(ix+5)
    or a
    jp nz,zx48_arg1_format

    ld a,(ix+6)
    cp c
    jp nz,zx48_arg1_format
    ld a,(ix+7)
    cp b
    jp nz,zx48_arg1_format

    ; argv[0] must be the exact non-empty invocation token, byte for byte.
    ld a,(de)
    or a
    jp z,zx48_arg1_format
    push ix
    pop hl
    inc hl
    inc hl
    inc hl
    inc hl
    inc hl
    inc hl
    inc hl
    inc hl
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
zx48_arg1_argv0_loop:
    ld a,b
    or c
    jp z,zx48_arg1_format
    ld a,(de)
    cp (hl)
    jp nz,zx48_arg1_format
    inc hl
    dec bc
    or a
    jr z,zx48_arg1_argv0_done
    inc de
    ld a,d
    or e
    jp z,zx48_arg1_format
    jr zx48_arg1_argv0_loop

zx48_arg1_argv0_done:
    ld a,(ix+4)
    dec a
    jr z,zx48_arg1_validate_done
    ld d,a

zx48_arg1_next_arg:
zx48_arg1_scan_arg:
    ld a,b
    or c
    jp z,zx48_arg1_format
    ld a,(hl)
    inc hl
    dec bc
    or a
    jr nz,zx48_arg1_scan_arg
    dec d
    jr nz,zx48_arg1_next_arg

zx48_arg1_validate_done:
    ld a,b
    or c
    jp nz,zx48_arg1_format
    xor a
    ret

zx48_arg1_build:
    ; Preserve the caller source/length across validation. POP does not alter
    ; flags, so carry/A from the validator remain authoritative on failure.
    push ix
    push bc
    call zx48_arg1_validate
    pop bc
    pop ix
    ret c

    ; Preserve source, exact length, and rounded allocation length across the
    ; allocator, which is free to clobber IX/BC/DE internally.
    push ix
    push bc
    bit 0,c
    jr z,zx48_arg1_build_rounded
    inc bc
zx48_arg1_build_rounded:
    push bc
    ld a,ALLOC_ANY
    call zx48_alloc
    pop de
    pop bc
    pop ix
    ret c

    ; DE currently holds the rounded allocation length and HL the new base.
    ; Save both while LDIR consumes the exact source/length pair.
    push de
    push hl
    push bc
    ex de,hl
    push ix
    pop hl
    ldir
    pop bc
    pop hl
    pop de
    xor a
    ret

zx48_arg1_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P2.07 ENV1 validator/shared-bootstrap builder. IX points to the already
; validated caller ARG1 block and BC is its exact byte length. HL points to the
; caller ENV1 block and DE is its exact supplied byte length. ENV1 validation is
; complete and side-effect free before builder scratch or allocator state can
; change. On success zx48_env1_build creates exactly one ALLOC_ANY extent with
; exact ARG1 bytes followed immediately by exact ENV1 bytes. Success returns
; HL=private ARG1 base, BC=exact ARG1 length, DE=private ENV1 pointer,
; A=0/C clear. Failure returns A=errno/C set, creates no builder-owned
; allocation on validation failure, and never publishes process state or cwd.
    MACRO EMIT_ENV1_ROUTINES
zx48_env1_validate:
    ; The empty environment is still the complete eight-byte ENV1 header.
    ld a,b
    or a
    jr nz,zx48_env1_min_ok
    ld a,c
    cp ENV1_HEADER_SIZE
    jp c,zx48_env1_format
zx48_env1_min_ok:

    ; ENV1 is capped at 256 bytes exactly. BC=0100 is the only B=1 value valid.
    ld a,b
    cp 2
    jp nc,zx48_env1_format
    or a
    jr z,zx48_env1_size_ok
    ld a,c
    or a
    jp nz,zx48_env1_format
zx48_env1_size_ok:

    ; Reject source+length address-space wrap before any indexed header read.
    push ix
    pop hl
    add hl,bc
    jp c,zx48_env1_format

    ld a,(ix+0)
    cp $45
    jp nz,zx48_env1_format
    ld a,(ix+1)
    cp $4e
    jp nz,zx48_env1_format
    ld a,(ix+2)
    cp $56
    jp nz,zx48_env1_format
    ld a,(ix+3)
    cp $31
    jp nz,zx48_env1_format

    ld a,(ix+4)
    cp ENV1_MAX_COUNT+1
    jp nc,zx48_env1_format

    ld a,(ix+5)
    or a
    jp nz,zx48_env1_format

    ld a,(ix+6)
    cp c
    jp nz,zx48_env1_format
    ld a,(ix+7)
    cp b
    jp nz,zx48_env1_format

    ; Consume the header. BC is the exact number of payload bytes remaining.
    push ix
    pop hl
    inc hl
    inc hl
    inc hl
    inc hl
    inc hl
    inc hl
    inc hl
    inc hl
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc
    dec bc

    ld a,(ix+4)
    ld d,a
    or a
    jr nz,zx48_env1_entry
    ld a,b
    or c
    jp nz,zx48_env1_format
    jp zx48_env1_unique_begin

zx48_env1_entry:
    ; NAME first byte is [A-Za-z_].
    ld a,b
    or c
    jp z,zx48_env1_format
    ld a,(hl)
    cp $5f
    jr z,zx48_env1_first_ok
    cp $41
    jr c,zx48_env1_first_lower
    cp $5b
    jr c,zx48_env1_first_ok
zx48_env1_first_lower:
    cp $61
    jp c,zx48_env1_format
    cp $7b
    jp nc,zx48_env1_format
zx48_env1_first_ok:
    inc hl
    dec bc
    ld e,1

zx48_env1_name_loop:
    ld a,b
    or c
    jp z,zx48_env1_format
    ld a,(hl)
    cp $3d
    jr z,zx48_env1_name_done
    or a
    jp z,zx48_env1_format
    cp $5f
    jr z,zx48_env1_name_char_ok
    cp $30
    jr c,zx48_env1_name_upper
    cp $3a
    jr c,zx48_env1_name_char_ok
zx48_env1_name_upper:
    cp $41
    jr c,zx48_env1_name_lower
    cp $5b
    jr c,zx48_env1_name_char_ok
zx48_env1_name_lower:
    cp $61
    jp c,zx48_env1_format
    cp $7b
    jp nc,zx48_env1_format
zx48_env1_name_char_ok:
    inc e
    ld a,e
    cp ENV1_MAX_NAME+1
    jp nc,zx48_env1_format
    inc hl
    dec bc
    jr zx48_env1_name_loop

zx48_env1_name_done:
    inc hl
    dec bc
    ld e,0

zx48_env1_value_loop:
    ld a,b
    or c
    jp z,zx48_env1_format
    ld a,(hl)
    inc hl
    dec bc
    or a
    jr z,zx48_env1_entry_done
    cp $20
    jp c,zx48_env1_format
    cp $7f
    jp nc,zx48_env1_format
    inc e
    ld a,e
    cp ENV1_MAX_VALUE+1
    jp nc,zx48_env1_format
    jr zx48_env1_value_loop

zx48_env1_entry_done:
    dec d
    jp nz,zx48_env1_entry
    ld a,b
    or c
    jp nz,zx48_env1_format

    ; A second read-only pass compares each name against all later names. The
    ; first '=' terminates a name; value bytes, including later '=', are skipped
    ; only while advancing from one validated entry to the next.
zx48_env1_unique_begin:
    ld a,(ix+4)
    cp 2
    jr c,zx48_env1_validate_done
    ld b,a
    dec b
    push ix
    pop hl
    ld de,ENV1_HEADER_SIZE
    add hl,de

zx48_env1_unique_outer:
    ld d,h
    ld e,l
zx48_env1_unique_find_next:
    ld a,(de)
    inc de
    or a
    jr nz,zx48_env1_unique_find_next
    ld c,b

zx48_env1_unique_inner:
    push bc
    push hl
    push de
zx48_env1_unique_compare:
    ld a,(de)
    cp (hl)
    jr nz,zx48_env1_unique_different
    cp $3d
    jr z,zx48_env1_unique_duplicate
    inc de
    inc hl
    jr zx48_env1_unique_compare

zx48_env1_unique_different:
    pop de
    pop hl
    pop bc
zx48_env1_unique_advance_inner:
    ld a,(de)
    inc de
    or a
    jr nz,zx48_env1_unique_advance_inner
    dec c
    jr nz,zx48_env1_unique_inner

zx48_env1_unique_advance_outer:
    ld a,(hl)
    inc hl
    or a
    jr nz,zx48_env1_unique_advance_outer
    djnz zx48_env1_unique_outer

zx48_env1_validate_done:
    xor a
    ret

zx48_env1_unique_duplicate:
    pop de
    pop hl
    pop bc
    jp zx48_env1_format

zx48_env1_build:
    ; Validate ENV1 with its own pointer/length while preserving all four
    ; caller inputs. POP does not alter the validator's carry/A result.
    push ix
    push bc
    push hl
    push de
    push hl
    pop ix
    ld b,d
    ld c,e
    call zx48_env1_validate
    pop de
    pop hl
    pop bc
    pop ix
    ret c

    ; The ARG1 payload was already validated by P2.06. Re-check only the length
    ; and address arithmetic needed to make the shared-copy operation safe.
    ld a,b
    or a
    jr nz,zx48_env1_build_arg_min_ok
    ld a,c
    cp ARG1_HEADER_SIZE+1
    jp c,zx48_env1_format
zx48_env1_build_arg_min_ok:
    ld a,b
    cp 2
    jp nc,zx48_env1_format
    or a
    jr z,zx48_env1_build_arg_size_ok
    ld a,c
    or a
    jp nz,zx48_env1_format
zx48_env1_build_arg_size_ok:
    push hl
    push ix
    pop hl
    add hl,bc
    pop hl
    jp c,zx48_env1_format

    ; Combined logical payload is bounded to exactly 512 bytes before any
    ; builder-owned persistent scratch or allocation is changed.
    push hl
    ld h,b
    ld l,c
    add hl,de
    jp c,zx48_env1_build_format_pop
    ld a,h
    cp BOOTSTRAP_MAX_PAYLOAD/256
    jr c,zx48_env1_build_total_ok
    jp nz,zx48_env1_build_format_pop
    ld a,l
    or a
    jp nz,zx48_env1_build_format_pop
zx48_env1_build_total_ok:
    bit 0,l
    jr z,zx48_env1_build_rounded
    inc hl
zx48_env1_build_rounded:
    ld (process_bootstrap_rounded),hl
    pop hl
    ld (process_bootstrap_env_src),hl
    ld (process_bootstrap_env_len),de
    push ix
    pop hl
    ld (process_bootstrap_arg_src),hl
    ld (process_bootstrap_arg_len),bc

    ld bc,(process_bootstrap_rounded)
    ld a,ALLOC_ANY
    call zx48_alloc
    ret c
    ld (process_bootstrap_base),hl

    ; Copy exact logical ARG1 then exact logical ENV1. The allocator may round
    ; the single combined extent, but neither ABI block's exact length changes.
    ex de,hl
    ld hl,(process_bootstrap_arg_src)
    ld bc,(process_bootstrap_arg_len)
    ldir
    push de
    ld hl,(process_bootstrap_env_src)
    ld bc,(process_bootstrap_env_len)
    ldir
    pop de

    ld hl,(process_bootstrap_base)
    ld bc,(process_bootstrap_arg_len)
    xor a
    ret

zx48_env1_build_format_pop:
    pop hl
zx48_env1_format:
    ld a,E_FORMAT
    scf
    ret

process_bootstrap_arg_src: dw 0
process_bootstrap_arg_len: dw 0
process_bootstrap_env_src: dw 0
process_bootstrap_env_len: dw 0
process_bootstrap_rounded: dw 0
process_bootstrap_base: dw 0
    ENDM


; P2.08 initial user-context constructor. IX points to the already validated
; MEX1 header and HL points to an internal twelve-byte seed containing image
; base, FAST stack base/size, ARG1 pointer/length, and ENV1 pointer. The helper
; validates every address/size relationship before the first target-stack write.
; It then materializes the exact scheduler resume frame IX/HL/DE/BC/AF/PC at
; the top of the uncommitted FAST stack. On success HL=saved_sp, A=0/C clear.
; Failure returns A=E_FORMAT/C set and does not write the target stack or
; publish descriptor/READY state. IY is deliberately absent from the frame;
; the frozen scheduler restore path canonicalizes IY=ROM_IY_ANCHOR before RET.
    MACRO EMIT_INITIAL_CONTEXT_ROUTINES
zx48_process_build_initial_context:
    ; Prove the private seed can be read completely before copying it to scratch.
    ld (process_context_seed),hl
    ld de,INITIAL_CONTEXT_SEED_SIZE
    add hl,de
    jp c,zx48_initial_context_format
    ld hl,(process_context_seed)
    ld de,process_context_image_base
    ld bc,INITIAL_CONTEXT_SEED_SIZE
    ldir

    ; Re-prove the validated image extent and entry point against the actual base.
    ld l,(ix+MEX_HDR_IMAGE_SIZE)
    ld h,(ix+MEX_HDR_IMAGE_SIZE+1)
    ld a,h
    or l
    jp z,zx48_initial_context_format
    ld (process_context_image_size),hl
    ld e,(ix+MEX_HDR_BSS_SIZE)
    ld d,(ix+MEX_HDR_BSS_SIZE+1)
    add hl,de
    jp c,zx48_initial_context_format
    ld (process_context_image_alloc_size),hl

    ld hl,(process_context_image_base)
    ld de,ARENA_START
    or a
    sbc hl,de
    jp c,zx48_initial_context_format
    ld hl,(process_context_image_base)
    ld de,(process_context_image_alloc_size)
    add hl,de
    jp c,zx48_initial_context_format
    ld de,KERNEL_START
    or a
    sbc hl,de
    jr c,zx48_initial_context_image_end_ok
    jp nz,zx48_initial_context_format
zx48_initial_context_image_end_ok:

    ld e,(ix+MEX_HDR_ENTRY)
    ld d,(ix+MEX_HDR_ENTRY+1)
    ld hl,(process_context_image_size)
    or a
    sbc hl,de
    jp c,zx48_initial_context_format
    jp z,zx48_initial_context_format
    ld hl,(process_context_image_base)
    add hl,de
    jp c,zx48_initial_context_format
    ld (process_context_entry),hl

    ; Stack allocation must be the exact validated MEX1 request plus the fixed
    ; 64-byte bootstrap reserve and must remain wholly in FAST RAM.
    ld c,(ix+MEX_HDR_STACK)
    ld b,(ix+MEX_HDR_STACK+1)
    bit 0,c
    jp nz,zx48_initial_context_format
    ld h,b
    ld l,c
    ld de,MEX_MIN_STACK
    or a
    sbc hl,de
    jp c,zx48_initial_context_format
    ld hl,MEX_MAX_STACK
    or a
    sbc hl,bc
    jp c,zx48_initial_context_format
    ld hl,PROCESS_STACK_BOOTSTRAP_BYTES
    add hl,bc
    jp c,zx48_initial_context_format
    ld de,(process_context_stack_size)
    or a
    sbc hl,de
    jp nz,zx48_initial_context_format

    ld hl,(process_context_stack_base)
    bit 0,l
    jp nz,zx48_initial_context_format
    ld de,FAST_START
    or a
    sbc hl,de
    jp c,zx48_initial_context_format
    ld hl,(process_context_stack_base)
    ld de,(process_context_stack_size)
    add hl,de
    jp c,zx48_initial_context_format
    ld (process_context_stack_end),hl
    ld de,KERNEL_START
    or a
    sbc hl,de
    jr c,zx48_initial_context_stack_end_ok
    jp nz,zx48_initial_context_format
zx48_initial_context_stack_end_ok:

    ld hl,(process_context_stack_end)
    ld de,PROCESS_CONTEXT_FRAME_BYTES
    or a
    sbc hl,de
    ld (process_context_saved_sp),hl
    ld de,(process_context_stack_base)
    or a
    sbc hl,de
    jp c,zx48_initial_context_format

    ; P2.07 supplied one immutable ARG1-then-ENV1 extent. Preserve the exact
    ; ARG1 length and require ENV1 to begin immediately after those ARG1 bytes.
    ld bc,(process_context_arg_len)
    ld a,b
    cp 2
    jp nc,zx48_initial_context_format
    or a
    jr nz,zx48_initial_context_arg_256
    ld a,c
    cp ARG1_HEADER_SIZE+1
    jp c,zx48_initial_context_format
    jr zx48_initial_context_arg_size_ok
zx48_initial_context_arg_256:
    ld a,c
    or a
    jp nz,zx48_initial_context_format
zx48_initial_context_arg_size_ok:
    ld hl,(process_context_arg_ptr)
    ld de,ARENA_START
    or a
    sbc hl,de
    jp c,zx48_initial_context_format
    ld hl,(process_context_arg_ptr)
    add hl,bc
    jp c,zx48_initial_context_format
    ld de,(process_context_env_ptr)
    or a
    sbc hl,de
    jp nz,zx48_initial_context_format
    ld hl,(process_context_env_ptr)
    ld de,ARENA_START
    or a
    sbc hl,de
    jp c,zx48_initial_context_format
    ld hl,(process_context_env_ptr)
    ld de,KERNEL_START
    or a
    sbc hl,de
    jp nc,zx48_initial_context_format

zx48_initial_context_write:
    ; saved_sp+0: IX is intentionally deterministic zero; IX has no specified
    ; initial application value. saved_sp+2/+4/+6 are the frozen entry registers.
    ld hl,(process_context_saved_sp)
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld de,(process_context_arg_ptr)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(process_context_env_ptr)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(process_context_arg_len)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld de,(process_context_entry)
    ld (hl),e
    inc hl
    ld (hl),d

    ld hl,(process_context_saved_sp)
    xor a
    ret

zx48_initial_context_format:
    ld a,E_FORMAT
    scf
    ret

process_context_seed: dw 0
process_context_image_base: dw 0
process_context_stack_base: dw 0
process_context_stack_size: dw 0
process_context_arg_ptr: dw 0
process_context_arg_len: dw 0
process_context_env_ptr: dw 0
process_context_image_size: dw 0
process_context_image_alloc_size: dw 0
process_context_entry: dw 0
process_context_stack_end: dw 0
process_context_saved_sp: dw 0
    ENDM
