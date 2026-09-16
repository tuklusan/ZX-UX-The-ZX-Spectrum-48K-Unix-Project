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

; P2.10 staged SYS_SPAWN atomic transaction. This macro is deliberately not
; emitted by the resident kernel while the ordinary E000-FAFF pool remains at
; the frozen Phase-1/P2.09 ceiling. The deterministic Phase-2 fixture emits this
; exact source together with the already-certified allocator, relocation,
; ARG1/ENV1, initial-context, handle, and P2.09 preflight helpers.
;
; zx48_spawn_resolve_ram_object is supplied by the namespace layer used by the
; caller. Input HL is the validated PROC1 path. Success returns IX pointing to a
; 20-byte object record with the OBJ_* layout; failure returns the ABI errno.
; P2.10 admits only resident RAW BIN objects. PACKED resident execution is owned
; by P4 and catalog/tape-backed execution by P5.
    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES
zx48_process_spawn_transaction:
    ld (process_spawn_proc1),hl
    xor a
    ld (process_spawn_image_base),a
    ld (process_spawn_image_base+1),a
    ld (process_spawn_stack_base),a
    ld (process_spawn_stack_base+1),a
    ld (process_spawn_bootstrap_base),a
    ld (process_spawn_bootstrap_base+1),a
    ld (process_spawn_retained),a

    ; P2.09 already proved capacity and the complete pointer/range/flag shape.
    ; Re-find the still-FREE descriptor without reserving or publishing it.
    call zx48_process_find_free_slot
    ret c
    ld (process_spawn_child_pid),a
    push ix
    pop hl
    ld (process_spawn_child_desc),hl

    ; Resolve the resident object before any process-owned allocation. Missing
    ; paths propagate E_NOENT. A resolved non-BIN is always E_FORMAT for spawn.
    ld hl,(process_spawn_proc1)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    call zx48_spawn_resolve_ram_object
    ret c
    ld (process_spawn_object),ix
    ld a,(ix+OBJ_TYPE_ID)
    cp OBJ_BIN
    jp nz,zx48_process_spawn_format
    ld a,(ix+OBJ_FLAGS_BYTE)
    or a
    jp nz,zx48_process_spawn_format
    ld a,(ix+OBJ_RESERVED_BYTE)
    or a
    jp nz,zx48_process_spawn_format
    ld l,(ix+OBJ_LOGICAL_LENGTH)
    ld h,(ix+OBJ_LOGICAL_LENGTH+1)
    ld (process_spawn_source_length),hl
    ld e,(ix+OBJ_STORAGE_LENGTH)
    ld d,(ix+OBJ_STORAGE_LENGTH+1)
    or a
    sbc hl,de
    jp nz,zx48_process_spawn_format
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    ld a,h
    or l
    jp z,zx48_process_spawn_format
    ld (process_spawn_mex_source),hl

    ; Validate the complete RAW MEX1 bytes, including both CRCs and every widened
    ; header/allocation arithmetic result, before allocating process-owned RAM.
    push hl
    pop ix
    ld bc,(process_spawn_source_length)
    call zx48_process_spawn_validate_mex1
    ret c

    ; Validate ARG1 against the exact invocation token, then ENV1. These are
    ; still caller-owned buffers; no process state or arena state has changed.
    ld hl,(process_spawn_proc1)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (process_spawn_path),de
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (process_spawn_arg_src),de
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld (process_spawn_arg_len),bc
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (process_spawn_env_src),de
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (process_spawn_env_len),de

    ld ix,(process_spawn_arg_src)
    ld bc,(process_spawn_arg_len)
    ld hl,(process_spawn_path)
    call zx48_arg1_validate
    ret c

    ld ix,(process_spawn_env_src)
    ld bc,(process_spawn_env_len)
    call zx48_env1_validate
    ret c

    ; The two exact validated ABI blocks share one immutable process allocation.
    ld hl,(process_spawn_arg_len)
    ld de,(process_spawn_env_len)
    add hl,de
    jp c,zx48_process_spawn_format
    ld a,h
    cp BOOTSTRAP_MAX_PAYLOAD/256
    jr c,zx48_process_spawn_bootstrap_total_ok
    jp nz,zx48_process_spawn_format
    ld a,l
    or a
    jp nz,zx48_process_spawn_format
zx48_process_spawn_bootstrap_total_ok:
    ld (process_spawn_bootstrap_exact),hl
    bit 0,l
    jr z,zx48_process_spawn_bootstrap_rounded
    inc hl
zx48_process_spawn_bootstrap_rounded:
    ld (process_spawn_bootstrap_size),hl

    ; Resolve all three parent handles while the attempt is still side-effect
    ; free. The corresponding OD identities are retained only after image/context
    ; construction succeeds, so failure cannot perturb parent handle slots.
    ld hl,(process_spawn_proc1)
    ld de,PROC1_STDIN_HANDLE
    add hl,de
    ld a,(hl)
    call zx48_handle_lookup
    ret c
    ld a,c
    ld (process_spawn_od0),a

    ld hl,(process_spawn_proc1)
    ld de,PROC1_STDOUT_HANDLE
    add hl,de
    ld a,(hl)
    call zx48_handle_lookup
    ret c
    ld a,c
    ld (process_spawn_od1),a

    ld hl,(process_spawn_proc1)
    ld de,PROC1_STDERR_HANDLE
    add hl,de
    ld a,(hl)
    call zx48_handle_lookup
    ret c
    ld a,c
    ld (process_spawn_od2),a

    ; CWD is inherited exactly from the current parent descriptor.
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_CWD)
    ld (process_spawn_parent_cwd),a

    ; Reserve every process-owned extent before loading/copying executable bytes.
    ld bc,(process_spawn_image_size_rounded)
    ld a,ALLOC_ANY
    call zx48_alloc
    jp c,zx48_process_spawn_return_error
    ld (process_spawn_image_base),hl

    ld bc,(process_spawn_stack_size)
    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    jp c,zx48_process_spawn_rollback
    ld (process_spawn_stack_base),hl

    ld bc,(process_spawn_bootstrap_size)
    ld a,ALLOC_ANY
    call zx48_alloc
    jp c,zx48_process_spawn_rollback
    ld (process_spawn_bootstrap_base),hl

    ; Copy immutable ARG1 followed immediately by ENV1 into the third allocation.
    ex de,hl
    ld hl,(process_spawn_arg_src)
    ld bc,(process_spawn_arg_len)
    ldir
    ld (process_spawn_env_ptr),de
    ld hl,(process_spawn_env_src)
    ld bc,(process_spawn_env_len)
    ldir
    ld hl,(process_spawn_bootstrap_exact)
    bit 0,l
    jr z,zx48_process_spawn_bootstrap_copied
    xor a
    ld (de),a
zx48_process_spawn_bootstrap_copied:

    ; Copy image bytes into the private image allocation, zero BSS, then apply
    ; the already-certified ABS16 validator/applicator. No descriptor is visible.
    ld hl,(process_spawn_mex_source)
    ld de,MEX_HEADER_SIZE
    add hl,de
    ld de,(process_spawn_image_base)
    ld bc,(process_spawn_image_size)
    ldir

    ld bc,(process_spawn_bss_size)
    ld a,b
    or c
    jr z,zx48_process_spawn_relocate
    xor a
    ld (de),a
    dec bc
    ld a,b
    or c
    jr z,zx48_process_spawn_relocate
    ld h,d
    ld l,e
    inc de
    ldir

zx48_process_spawn_relocate:
    ld ix,(process_spawn_mex_source)
    ld de,(process_spawn_image_base)
    call zx48_mex1_relocate
    jp c,zx48_process_spawn_rollback

    ; Construct the exact initial scheduler frame only after every allocation and
    ; executable validation step has succeeded.
    ld hl,(process_spawn_image_base)
    ld (process_spawn_context_seed+INITIAL_CONTEXT_IMAGE_BASE),hl
    ld hl,(process_spawn_stack_base)
    ld (process_spawn_context_seed+INITIAL_CONTEXT_STACK_BASE),hl
    ld hl,(process_spawn_stack_size)
    ld (process_spawn_context_seed+INITIAL_CONTEXT_STACK_SIZE),hl
    ld hl,(process_spawn_bootstrap_base)
    ld (process_spawn_context_seed+INITIAL_CONTEXT_ARG_PTR),hl
    ld hl,(process_spawn_arg_len)
    ld (process_spawn_context_seed+INITIAL_CONTEXT_ARG_LEN),hl
    ld hl,(process_spawn_env_ptr)
    ld (process_spawn_context_seed+INITIAL_CONTEXT_ENV_PTR),hl
    ld ix,(process_spawn_mex_source)
    ld hl,process_spawn_context_seed
    call zx48_process_build_initial_context
    jp c,zx48_process_spawn_rollback
    ld (process_spawn_saved_sp),hl

    ; Acquire one shared OD reference for each child std-handle slot. Duplicate
    ; selected parent handles therefore acquire duplicate references, as required.
    ld a,(process_spawn_od0)
    call zx48_od_retain
    jp c,zx48_process_spawn_rollback
    ld a,1
    ld (process_spawn_retained),a
    ld a,(process_spawn_od1)
    call zx48_od_retain
    jp c,zx48_process_spawn_rollback
    ld a,2
    ld (process_spawn_retained),a
    ld a,(process_spawn_od2)
    call zx48_od_retain
    jp c,zx48_process_spawn_rollback
    ld a,3
    ld (process_spawn_retained),a

    IFDEF ZX48_P2_13_LINKS_EMITTED
    ; P2.13 delegates generation bump, successful-reuse descriptor reset, and
    ; generation-qualified parent publication to the dynamically exercised
    ; link helper. Generation exhaustion therefore leaves the FREE descriptor
    ; byte-identical; success returns IX on the reset, linked child descriptor.
    ld a,(process_spawn_child_pid)
    call zx48_process_link_child
    jp c,zx48_process_spawn_rollback
    ELSE
    ; Preserve the certified P2.10/P2.12 expansion byte-for-byte when the
    ; P2.13 linkage emitter is absent from the assembly unit.
    ; Commit is intentionally non-fallible. The descriptor remains PROC_FREE
    ; while every field is written; READY is the single publication store.
    ld hl,(process_spawn_child_desc)
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,PROC_DESC_SIZE-1
    ldir
    ld ix,(process_spawn_child_desc)
    ld a,(process_spawn_child_pid)
    ld (ix+PROC_PID),a
    ld a,(current_pid)
    ld (ix+PROC_PARENT),a
    ENDIF
    xor a
    ld (ix+PROC_FLAGS),a
    ld hl,(process_spawn_image_base)
    ld (ix+PROC_IMAGE_BASE),l
    ld (ix+PROC_IMAGE_BASE+1),h
    ld hl,(process_spawn_image_size_rounded)
    ld (ix+PROC_IMAGE_SIZE),l
    ld (ix+PROC_IMAGE_SIZE+1),h
    ld hl,(process_spawn_stack_base)
    ld (ix+PROC_STACK_LOW),l
    ld (ix+PROC_STACK_LOW+1),h
    ld de,(process_spawn_stack_size)
    add hl,de
    ld (ix+PROC_STACK_HIGH),l
    ld (ix+PROC_STACK_HIGH+1),h
    ld hl,(process_spawn_saved_sp)
    ld (ix+PROC_SAVED_SP),l
    ld (ix+PROC_SAVED_SP+1),h
    xor a
    ld (ix+PROC_EXIT_STATUS),a
    ld (ix+PROC_WAIT_OBJECT),a
    ld a,(process_spawn_od0)
    ld (ix+PROC_HANDLES+0),a
    ld a,(process_spawn_od1)
    ld (ix+PROC_HANDLES+1),a
    ld a,(process_spawn_od2)
    ld (ix+PROC_HANDLES+2),a
    ld a,HANDLE_FREE
    ld (ix+PROC_HANDLES+3),a
    ld (ix+PROC_HANDLES+4),a
    ld (ix+PROC_HANDLES+5),a
    ld (ix+PROC_HANDLES+6),a
    ld (ix+PROC_HANDLES+7),a
    xor a
    ld (ix+PROC_WAKE_TICK+0),a
    ld (ix+PROC_WAKE_TICK+1),a
    ld (ix+PROC_WAKE_TICK+2),a
    ld (ix+PROC_WAKE_TICK+3),a
    ld a,(process_spawn_parent_cwd)
    ld (ix+PROC_CWD),a

    push ix
    pop de
    ld hl,PROC_NAME
    add hl,de
    ex de,hl
    ld hl,(process_spawn_object)
    ld bc,10
    ldir

    ld hl,(process_spawn_image_size_rounded)
    ld de,(process_spawn_stack_size)
    add hl,de
    ld de,(process_spawn_bootstrap_size)
    add hl,de
    ld (ix+PROC_OWNED_BYTES),l
    ld (ix+PROC_OWNED_BYTES+1),h
    ld hl,(process_spawn_bootstrap_base)
    ld (ix+PROC_ARG_PTR),l
    ld (ix+PROC_ARG_PTR+1),h
    ld hl,(process_spawn_env_ptr)
    ld (ix+PROC_ENV_PTR),l
    ld (ix+PROC_ENV_PTR+1),h
    xor a
    ld (ix+PROC_PRIVATE_FLAGS),a
    ld (ix+PROC_RESERVED),a

    ; Publication point: exactly one state store and no scheduler call/yield.
    ld (ix+PROC_STATE),PROC_READY
    ld a,(process_spawn_child_pid)
    ld l,a
    ld h,0
    xor a
    ret

zx48_process_spawn_rollback:
    ld (process_spawn_error),a
    ld a,(process_spawn_retained)
    cp 3
    jr c,zx48_process_spawn_release_two
    ld a,(process_spawn_od2)
    call zx48_od_release
zx48_process_spawn_release_two:
    ld a,(process_spawn_retained)
    cp 2
    jr c,zx48_process_spawn_release_one
    ld a,(process_spawn_od1)
    call zx48_od_release
zx48_process_spawn_release_one:
    ld a,(process_spawn_retained)
    or a
    jr z,zx48_process_spawn_free_bootstrap
    ld a,(process_spawn_od0)
    call zx48_od_release
zx48_process_spawn_free_bootstrap:
    ld hl,(process_spawn_bootstrap_base)
    ld a,h
    or l
    jr z,zx48_process_spawn_free_stack
    ld bc,(process_spawn_bootstrap_size)
    call zx48_free
zx48_process_spawn_free_stack:
    ld hl,(process_spawn_stack_base)
    ld a,h
    or l
    jr z,zx48_process_spawn_free_image
    ld bc,(process_spawn_stack_size)
    call zx48_free
zx48_process_spawn_free_image:
    ld hl,(process_spawn_image_base)
    ld a,h
    or l
    jr z,zx48_process_spawn_rollback_done
    ld bc,(process_spawn_image_size_rounded)
    call zx48_free
zx48_process_spawn_rollback_done:
    ld a,(process_spawn_error)
    scf
    ret

zx48_process_spawn_return_error:
    scf
    ret

zx48_process_spawn_format:
    ld a,E_FORMAT
    scf
    ret

; IX -> RAW MEX1 bytes, BC = exact resident object length. This is the target
; validator required by P2.10; it deliberately validates CRCs before allocations.
zx48_process_spawn_validate_mex1:
    ld (process_spawn_mex_source),ix
    ld (process_spawn_source_length),bc

    ; Complete source range must be internal arena RAM and at least one header.
    push ix
    pop hl
    ld de,ARENA_START
    or a
    sbc hl,de
    jp c,zx48_process_spawn_format
    push ix
    pop hl
    add hl,bc
    jp c,zx48_process_spawn_format
    ld de,KERNEL_START
    or a
    sbc hl,de
    jr c,zx48_process_spawn_source_range_ok
    jr z,zx48_process_spawn_source_range_ok
    jp zx48_process_spawn_format
zx48_process_spawn_source_range_ok:
    ld h,b
    ld l,c
    ld de,MEX_HEADER_SIZE
    or a
    sbc hl,de
    jp c,zx48_process_spawn_format

    ld a,(ix+MEX_HDR_MAGIC+0)
    cp MEX_MAGIC0
    jp nz,zx48_process_spawn_format
    ld a,(ix+MEX_HDR_MAGIC+1)
    cp MEX_MAGIC1
    jp nz,zx48_process_spawn_format
    ld a,(ix+MEX_HDR_MAGIC+2)
    cp MEX_MAGIC2
    jp nz,zx48_process_spawn_format
    ld a,(ix+MEX_HDR_MAGIC+3)
    cp MEX_MAGIC3
    jp nz,zx48_process_spawn_format
    ld a,(ix+MEX_HDR_VERSION)
    cp MEX_VERSION
    jp nz,zx48_process_spawn_format
    ld a,(ix+MEX_HDR_FLAGS)
    or a
    jp nz,zx48_process_spawn_format
    ld a,(ix+MEX_HDR_SIZE)
    cp MEX_HEADER_SIZE
    jp nz,zx48_process_spawn_format
    ld a,(ix+MEX_HDR_SIZE+1)
    or a
    jp nz,zx48_process_spawn_format

    ld l,(ix+MEX_HDR_IMAGE_SIZE)
    ld h,(ix+MEX_HDR_IMAGE_SIZE+1)
    ld a,h
    or l
    jp z,zx48_process_spawn_format
    ld (process_spawn_image_size),hl
    ld e,(ix+MEX_HDR_BSS_SIZE)
    ld d,(ix+MEX_HDR_BSS_SIZE+1)
    ld (process_spawn_bss_size),de
    add hl,de
    jp c,zx48_process_spawn_format
    ld (process_spawn_image_size_exact),hl
    ld de,MEX_MAX_STORED
    or a
    sbc hl,de
    jr c,zx48_process_spawn_image_total_ok
    jp nz,zx48_process_spawn_format
zx48_process_spawn_image_total_ok:
    ld hl,(process_spawn_image_size_exact)
    ld b,h
    ld c,l
    bit 0,c
    jr z,zx48_process_spawn_image_rounded
    inc bc
zx48_process_spawn_image_rounded:
    ld (process_spawn_image_size_rounded),bc

    ld e,(ix+MEX_HDR_ENTRY)
    ld d,(ix+MEX_HDR_ENTRY+1)
    ld hl,(process_spawn_image_size)
    or a
    sbc hl,de
    jp c,zx48_process_spawn_format
    jp z,zx48_process_spawn_format

    ld c,(ix+MEX_HDR_STACK)
    ld b,(ix+MEX_HDR_STACK+1)
    bit 0,c
    jp nz,zx48_process_spawn_format
    ld h,b
    ld l,c
    ld de,MEX_MIN_STACK
    or a
    sbc hl,de
    jp c,zx48_process_spawn_format
    ld hl,MEX_MAX_STACK
    or a
    sbc hl,bc
    jp c,zx48_process_spawn_format
    ld hl,PROCESS_STACK_BOOTSTRAP_BYTES
    add hl,bc
    jp c,zx48_process_spawn_format
    ld (process_spawn_stack_size),hl

    ld hl,(process_spawn_image_size)
    ld de,MEX_HEADER_SIZE
    add hl,de
    jp c,zx48_process_spawn_format
    ld e,(ix+MEX_HDR_RELOC_OFFSET)
    ld d,(ix+MEX_HDR_RELOC_OFFSET+1)
    or a
    sbc hl,de
    jp nz,zx48_process_spawn_format
    ld (process_spawn_reloc_offset),de

    ld l,(ix+MEX_HDR_RELOC_COUNT)
    ld h,(ix+MEX_HDR_RELOC_COUNT+1)
    add hl,hl
    jp c,zx48_process_spawn_format
    ld de,(process_spawn_reloc_offset)
    add hl,de
    jp c,zx48_process_spawn_format
    ld (process_spawn_total_stored),hl
    ld de,MEX_MAX_STORED
    or a
    sbc hl,de
    jr c,zx48_process_spawn_stored_bound_ok
    jp nz,zx48_process_spawn_format
zx48_process_spawn_stored_bound_ok:
    ld hl,(process_spawn_total_stored)
    ld de,(process_spawn_source_length)
    or a
    sbc hl,de
    jp nz,zx48_process_spawn_format

    ; Header CRC is over all 24 bytes with bytes 22..23 treated as zero.
    ld hl,(process_spawn_mex_source)
    ld bc,MEX_HDR_HEADER_CRC
    call zx48_process_spawn_crc16
    xor a
    call zx48_process_spawn_crc16_update
    xor a
    call zx48_process_spawn_crc16_update
    ld ix,(process_spawn_mex_source)
    ld a,(ix+MEX_HDR_HEADER_CRC)
    cp e
    jp nz,zx48_process_spawn_format
    ld a,(ix+MEX_HDR_HEADER_CRC+1)
    cp d
    jp nz,zx48_process_spawn_format

    ; Body CRC covers image plus relocation table before any relocation patch.
    ld hl,(process_spawn_mex_source)
    ld de,MEX_HEADER_SIZE
    add hl,de
    push hl
    ld hl,(process_spawn_source_length)
    ld de,MEX_HEADER_SIZE
    or a
    sbc hl,de
    ld b,h
    ld c,l
    pop hl
    call zx48_process_spawn_crc16
    ld ix,(process_spawn_mex_source)
    ld a,(ix+MEX_HDR_BODY_CRC)
    cp e
    jp nz,zx48_process_spawn_format
    ld a,(ix+MEX_HDR_BODY_CRC+1)
    cp d
    jp nz,zx48_process_spawn_format
    xor a
    ret

; HL -> bytes, BC=count. Returns DE=CRC-16/CCITT-FALSE.
zx48_process_spawn_crc16:
    ld de,MEX_CRC16_INIT
zx48_process_spawn_crc16_loop:
    ld a,b
    or c
    ret z
    ld a,(hl)
    inc hl
    push bc
    call zx48_process_spawn_crc16_update
    pop bc
    dec bc
    jr zx48_process_spawn_crc16_loop

; A=next byte, DE=current CRC -> DE=updated CRC.
zx48_process_spawn_crc16_update:
    xor d
    ld d,a
    ld b,8
zx48_process_spawn_crc16_bit:
    bit 7,d
    jr z,zx48_process_spawn_crc16_shift
    sla e
    rl d
    ld a,e
    xor MEX_CRC16_POLY&$ff
    ld e,a
    ld a,d
    xor MEX_CRC16_POLY/256
    ld d,a
    djnz zx48_process_spawn_crc16_bit
    ret
zx48_process_spawn_crc16_shift:
    sla e
    rl d
    djnz zx48_process_spawn_crc16_bit
    ret

process_spawn_proc1: dw 0
process_spawn_child_desc: dw 0
process_spawn_child_pid: db 0
process_spawn_object: dw 0
process_spawn_path: dw 0
process_spawn_mex_source: dw 0
process_spawn_source_length: dw 0
process_spawn_image_size: dw 0
process_spawn_bss_size: dw 0
process_spawn_image_size_exact: dw 0
process_spawn_image_size_rounded: dw 0
process_spawn_reloc_offset: dw 0
process_spawn_total_stored: dw 0
process_spawn_stack_size: dw 0
process_spawn_arg_src: dw 0
process_spawn_arg_len: dw 0
process_spawn_env_src: dw 0
process_spawn_env_len: dw 0
process_spawn_bootstrap_exact: dw 0
process_spawn_bootstrap_size: dw 0
process_spawn_image_base: dw 0
process_spawn_stack_base: dw 0
process_spawn_bootstrap_base: dw 0
process_spawn_env_ptr: dw 0
process_spawn_saved_sp: dw 0
process_spawn_parent_cwd: db 0
process_spawn_od0: db 0
process_spawn_od1: db 0
process_spawn_od2: db 0
process_spawn_retained: db 0
process_spawn_error: db 0
process_spawn_context_seed: defs INITIAL_CONTEXT_SEED_SIZE,0
    ENDM


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

; P2.13 generation-qualified parent/child linkage.  Numeric PIDs are bounded
; table indexes, not durable identities: every PID has a 16-bit generation that
; advances before a reused child identity is linked and is never allowed to wrap.
; Parent generation, child membership, and specific-wait generation live in
; bounded side tables so the
; public 48-byte process descriptor ABI remains unchanged.
    MACRO EMIT_PARENT_CHILD_ROUTINES
ZX48_P2_13_LINKS_EMITTED EQU 1
zx48_process_links_init:
    xor a
    ld hl,process_generation
    ld de,process_generation+1
    ld bc,MAX_PROCESSES*8-1
    ld (hl),a
    ldir
    ld hl,process_wait_pid
    ld b,MAX_PROCESSES
    ld a,HANDLE_FREE
zx48_process_links_init_wait:
    ld (hl),a
    inc hl
    djnz zx48_process_links_init_wait
    xor a
    call zx48_process_generation_bump
    ret c
    ld a,1
    call zx48_process_generation_bump
    ret c

    ; PID1 is the fixed shell child of PID0. Seed that root edge so every
    ; descriptor parent byte has a generation-qualified side-table identity.
    xor a
    call zx48_process_generation_get
    ret c
    push de
    ld a,1
    call zx48_process_parent_generation_ptr
    pop de
    ld (hl),e
    inc hl
    ld (hl),d
    xor a
    call zx48_process_child_mask_ptr
    ld (hl),$02
    xor a
    ret

; A=PID -> IX=descriptor.  This private pointer helper accepts FREE children so
; linkage can be committed immediately before the P2.10 READY publication.
zx48_process_links_desc_ptr:
    cp MAX_PROCESSES
    jr nc,zx48_process_links_noent
    ld ix,process_table
    or a
    jr z,zx48_process_links_desc_done
    ld b,a
    ld de,PROC_DESC_SIZE
zx48_process_links_desc_loop:
    add ix,de
    djnz zx48_process_links_desc_loop
zx48_process_links_desc_done:
    xor a
    ret

zx48_process_generation_ptr:
    cp MAX_PROCESSES
    jr nc,zx48_process_links_noent
    ld l,a
    ld h,0
    add hl,hl
    ld de,process_generation
    add hl,de
    xor a
    ret

zx48_process_parent_generation_ptr:
    cp MAX_PROCESSES
    jr nc,zx48_process_links_noent
    ld l,a
    ld h,0
    add hl,hl
    ld de,process_parent_generation
    add hl,de
    xor a
    ret

zx48_process_child_mask_ptr:
    cp MAX_PROCESSES
    jr nc,zx48_process_links_noent
    ld e,a
    ld d,0
    ld hl,process_child_mask
    add hl,de
    xor a
    ret

zx48_process_wait_pid_ptr:
    cp MAX_PROCESSES
    jr nc,zx48_process_links_noent
    ld e,a
    ld d,0
    ld hl,process_wait_pid
    add hl,de
    xor a
    ret

zx48_process_wait_generation_ptr:
    cp MAX_PROCESSES
    jr nc,zx48_process_links_noent
    ld l,a
    ld h,0
    add hl,hl
    ld de,process_wait_generation
    add hl,de
    xor a
    ret

zx48_process_pid_bit:
    cp MAX_PROCESSES
    jr nc,zx48_process_links_noent
    ld e,a
    ld d,0
    ld hl,process_pid_bits
    add hl,de
    ld a,(hl)
    or a
    ret

zx48_process_links_noent:
    ld a,E_NOENT
    scf
    ret

; A=PID -> DE=current generation.  Generation zero is reserved for "no identity".
zx48_process_generation_get:
    call zx48_process_generation_ptr
    ret c
    ld e,(hl)
    inc hl
    ld d,(hl)
    xor a
    ret

; A=PID -> increment persistent generation.  Generation zero means no identity,
; so the first publication becomes generation 1.  0xFFFF is permanently exhausted:
; refusing reuse is safer than allowing an ancient generation-qualified wait/parent
; reference to alias after wrap.  FREE/reap never resets this counter.
zx48_process_generation_bump:
    call zx48_process_generation_ptr
    ret c
    ld a,(hl)
    cp $ff
    jr nz,zx48_process_generation_increment
    inc hl
    ld a,(hl)
    dec hl
    cp $ff
    jp z,zx48_process_generation_exhausted
zx48_process_generation_increment:
    inc (hl)
    jr nz,zx48_process_generation_value
    inc hl
    inc (hl)
    dec hl
zx48_process_generation_value:
    ld e,(hl)
    inc hl
    ld d,(hl)
    xor a
    ret

; A=FREE child PID2..PID7.  The current live process becomes its parent.  This
; is deliberately non-fallible after the generation bump so spawn can call it
; inside its publication commit without creating a rollback edge.
zx48_process_link_child:
    cp 2
    jp c,zx48_process_links_inval
    cp MAX_PROCESSES
    jp nc,zx48_process_links_inval
    ld (process_link_child_pid),a
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jp nz,zx48_process_links_busy

    ld a,(current_pid)
    ld (process_link_parent_pid),a
    cp MAX_PROCESSES
    jp nc,zx48_process_links_inval
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_links_inval
    ld a,(process_link_parent_pid)
    call zx48_process_generation_get
    ret c
    ld a,d
    or e
    jr z,zx48_process_links_inval
    ld (process_link_parent_generation),de

    ld a,(process_link_child_pid)
    call zx48_process_generation_bump
    ret c

    ; Generation bump is the final fallible action. Once it succeeds, reset the
    ; still-FREE descriptor here, inside the dynamically exercised helper. This
    ; keeps generation exhaustion byte-identical while making successful reuse
    ; discard every stale descriptor byte before parent linkage is published.
    ld a,(process_link_child_pid)
    call zx48_process_links_desc_ptr
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,PROC_DESC_SIZE-1
    ldir
    ld a,(process_link_child_pid)
    ld (ix+PROC_PID),a

    ; A reused child starts with no children and no inherited wait token.  Its
    ; generation counter itself is intentionally outside this reset set.
    ld a,(process_link_child_pid)
    call zx48_process_child_mask_ptr
    ld (hl),0
    ld a,(process_link_child_pid)
    call zx48_process_wait_pid_ptr
    ld (hl),HANDLE_FREE
    ld a,(process_link_child_pid)
    call zx48_process_wait_generation_ptr
    ld (hl),0
    inc hl
    ld (hl),0

    ld a,(process_link_child_pid)
    call zx48_process_links_desc_ptr
    ld a,(process_link_parent_pid)
    ld (ix+PROC_PARENT),a
    ld a,(process_link_child_pid)
    call zx48_process_parent_generation_ptr
    ld de,(process_link_parent_generation)
    ld (hl),e
    inc hl
    ld (hl),d

    ld a,(process_link_child_pid)
    call zx48_process_pid_bit
    ld (process_link_child_bit),a
    ld a,(process_link_parent_pid)
    call zx48_process_child_mask_ptr
    ld a,(process_link_child_bit)
    or (hl)
    ld (hl),a
    xor a
    ret

zx48_process_generation_exhausted:
    ld a,E_AGAIN
    scf
    ret

zx48_process_links_inval:
    ld a,E_INVAL
    scf
    ret
zx48_process_links_busy:
    ld a,E_BUSY
    scf
    ret

; A=child PID.  Remove only the exact parent-generation edge.  If the numeric
; parent PID has already been reused, its new child mask is never touched.
zx48_process_unlink_child:
    cp 2
    jr c,zx48_process_links_inval
    cp MAX_PROCESSES
    jr nc,zx48_process_links_inval
    ld (process_link_child_pid),a
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_PARENT)
    ld (process_link_parent_pid),a
    cp HANDLE_FREE
    jr z,zx48_process_unlink_parent_stale

    ld a,(process_link_child_pid)
    call zx48_process_parent_generation_ptr
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (process_link_parent_generation),de
    ld a,(process_link_parent_pid)
    call zx48_process_generation_get
    jr c,zx48_process_unlink_parent_stale
    ld hl,(process_link_parent_generation)
    or a
    sbc hl,de
    jr nz,zx48_process_unlink_parent_stale

zx48_process_unlink_clear_parent:
    ld a,(process_link_child_pid)
    call zx48_process_pid_bit
    cpl
    ld (process_link_child_bit),a
    ld a,(process_link_parent_pid)
    call zx48_process_child_mask_ptr
    ld a,(process_link_child_bit)
    and (hl)
    ld (hl),a

zx48_process_unlink_parent_stale:
    ld a,(process_link_child_pid)
    call zx48_process_parent_generation_ptr
    ld (hl),0
    inc hl
    ld (hl),0
    ld a,(process_link_child_pid)
    call zx48_process_links_desc_ptr
    ld (ix+PROC_PARENT),HANDLE_FREE
    xor a
    ret

; A=old parent PID2..PID7.  Called before that identity is reclaimed.  Every
; exact-generation direct child becomes a PID1 child and the two bounded masks
; are repaired atomically from the cooperative kernel's point of view.
zx48_process_reparent_children_to_pid1:
    cp 2
    jr c,zx48_process_links_inval
    cp MAX_PROCESSES
    jr nc,zx48_process_links_inval
    ld (process_reparent_parent_pid),a
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jp z,zx48_process_links_inval
    ld a,(process_reparent_parent_pid)
    call zx48_process_generation_get
    ret c
    ld a,d
    or e
    jp z,zx48_process_links_inval
    ld (process_reparent_parent_generation),de

    ld a,1
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jp z,zx48_process_links_inval
    ld a,1
    call zx48_process_generation_get
    ret c
    ld a,d
    or e
    jp z,zx48_process_links_inval
    ld (process_reparent_pid1_generation),de

    ld a,2
    ld (process_reparent_child_pid),a
zx48_process_reparent_scan:
    ld a,(process_reparent_child_pid)
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_reparent_next
    ld a,(ix+PROC_PARENT)
    ld hl,process_reparent_parent_pid
    cp (hl)
    jr nz,zx48_process_reparent_next
    ld a,(process_reparent_child_pid)
    call zx48_process_parent_generation_ptr
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(process_reparent_parent_generation)
    or a
    sbc hl,de
    jr nz,zx48_process_reparent_next

    ld a,(process_reparent_child_pid)
    call zx48_process_links_desc_ptr
    ld (ix+PROC_PARENT),1
    ld a,(process_reparent_child_pid)
    call zx48_process_parent_generation_ptr
    ld de,(process_reparent_pid1_generation)
    ld (hl),e
    inc hl
    ld (hl),d
    ld a,(process_reparent_child_pid)
    call zx48_process_pid_bit
    ld (process_link_child_bit),a
    ld a,1
    call zx48_process_child_mask_ptr
    ld a,(process_link_child_bit)
    or (hl)
    ld (hl),a

zx48_process_reparent_next:
    ld a,(process_reparent_child_pid)
    inc a
    ld (process_reparent_child_pid),a
    cp MAX_PROCESSES
    jr c,zx48_process_reparent_scan
    ld a,(process_reparent_parent_pid)
    call zx48_process_child_mask_ptr
    ld (hl),0
    xor a
    ret

; A=specific target child PID.  Capture both numeric PID and current child
; generation for the current parent.  Future P2.15 blocking uses this token.
zx48_process_wait_record_specific:
    cp 2
    jp c,zx48_process_wait_child
    cp MAX_PROCESSES
    jp nc,zx48_process_wait_child
    ld (process_wait_candidate_pid),a
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jp z,zx48_process_wait_child
    ld a,(current_pid)
    ld b,a
    ld a,(ix+PROC_PARENT)
    cp b
    jp nz,zx48_process_wait_child

    ld a,(current_pid)
    call zx48_process_generation_get
    ret c
    ld a,d
    or e
    jp z,zx48_process_wait_child
    ld (process_wait_parent_generation),de
    ld a,(process_wait_candidate_pid)
    call zx48_process_parent_generation_ptr
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld hl,(process_wait_parent_generation)
    or a
    sbc hl,bc
    jp nz,zx48_process_wait_child

    ld a,(process_wait_candidate_pid)
    call zx48_process_pid_bit
    ld (process_link_child_bit),a
    ld a,(current_pid)
    call zx48_process_child_mask_ptr
    ld a,(process_link_child_bit)
    and (hl)
    jp z,zx48_process_wait_child

    ld a,(process_wait_candidate_pid)
    call zx48_process_generation_get
    ret c
    ld a,d
    or e
    jp z,zx48_process_wait_child
    ld (process_wait_candidate_generation),de
    ld a,(current_pid)
    call zx48_process_wait_pid_ptr
    ld a,(process_wait_candidate_pid)
    ld (hl),a
    ld a,(current_pid)
    call zx48_process_wait_generation_ptr
    ld de,(process_wait_candidate_generation)
    ld (hl),e
    inc hl
    ld (hl),d
    xor a
    ret

; A=candidate PID.  Match a previously captured specific-wait token against the
; complete current child identity.  Numeric PID equality alone is insufficient.
zx48_process_wait_matches:
    cp 2
    jr c,zx48_process_wait_child
    cp MAX_PROCESSES
    jr nc,zx48_process_wait_child
    ld (process_wait_candidate_pid),a
    ld a,(current_pid)
    call zx48_process_wait_pid_ptr
    jp c,zx48_process_wait_child
    ld a,(process_wait_candidate_pid)
    cp (hl)
    jr nz,zx48_process_wait_child

    ld a,(process_wait_candidate_pid)
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_wait_child
    ld a,(current_pid)
    ld b,a
    ld a,(ix+PROC_PARENT)
    cp b
    jr nz,zx48_process_wait_child

    ld a,(current_pid)
    call zx48_process_generation_get
    ret c
    ld a,d
    or e
    jp z,zx48_process_wait_child
    ld (process_wait_parent_generation),de
    ld a,(process_wait_candidate_pid)
    call zx48_process_parent_generation_ptr
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld hl,(process_wait_parent_generation)
    or a
    sbc hl,bc
    jr nz,zx48_process_wait_child

    ld a,(process_wait_candidate_pid)
    call zx48_process_generation_get
    ret c
    ld a,d
    or e
    jp z,zx48_process_wait_child
    ld (process_wait_candidate_generation),de
    ld a,(current_pid)
    call zx48_process_wait_generation_ptr
    ld c,(hl)
    inc hl
    ld b,(hl)
process_wait_compare_generation:
    ld hl,(process_wait_candidate_generation)
    or a
    sbc hl,bc
    jr nz,zx48_process_wait_child
    xor a
    ret

zx48_process_wait_child:
    ld a,E_CHILD
    scf
    ret

process_pid_bits: db $01,$02,$04,$08,$10,$20,$40,$80
process_generation: defs MAX_PROCESSES*2,0
process_parent_generation: defs MAX_PROCESSES*2,0
process_child_mask: defs MAX_PROCESSES,0
process_wait_pid: defs MAX_PROCESSES,HANDLE_FREE
process_wait_generation: defs MAX_PROCESSES*2,0
process_link_child_pid: db 0
process_link_parent_pid: db 0
process_link_child_bit: db 0
process_link_parent_generation: dw 0
process_reparent_parent_pid: db 0
process_reparent_child_pid: db 0
process_reparent_parent_generation: dw 0
process_reparent_pid1_generation: dw 0
process_wait_candidate_pid: db 0
process_wait_candidate_generation: dw 0
process_wait_parent_generation: dw 0
    ENDM

; P2.14 resource-safe ZOMBIE transition. This emitter composes after the P2.13
; generation-qualified linkage emitter. The exiting child remains RUNNING while
; fallible resource teardown occurs, so handle lookup remains valid. Only after
; all private resources are released are stale ownership pointers cleared and
; the durable descriptor published as ZOMBIE with its exit status retained.
    MACRO EMIT_ZOMBIE_TRANSITION_ROUTINES
ZX48_P2_14_ZOMBIE_EMITTED EQU 1

; A=exit status. Current PID must be a live spawned child (PID2..PID7).
zx48_process_exit_to_zombie:
    ld (process_zombie_status),a
    ld a,(current_pid)
    cp 2
    jp c,zx48_process_zombie_panic
    cp MAX_PROCESSES
    jp nc,zx48_process_zombie_panic
    ld (process_zombie_pid),a
    call zx48_process_links_desc_ptr
    jp c,zx48_process_zombie_panic
    ld a,(ix+PROC_STATE)
    cp PROC_RUNNING
    jp nz,zx48_process_zombie_panic

    ld a,(ix+PROC_PARENT)
    ld (process_zombie_parent_pid),a
    ld a,(process_zombie_pid)
    call zx48_process_parent_generation_ptr
    jp c,zx48_process_zombie_panic
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or e
    jp z,zx48_process_zombie_panic
    ld (process_zombie_parent_generation),de

    ld l,(ix+PROC_IMAGE_BASE)
    ld h,(ix+PROC_IMAGE_BASE+1)
    ld (process_zombie_image_base),hl
    ld l,(ix+PROC_IMAGE_SIZE)
    ld h,(ix+PROC_IMAGE_SIZE+1)
    ld (process_zombie_image_size),hl
    ld l,(ix+PROC_STACK_LOW)
    ld h,(ix+PROC_STACK_LOW+1)
    ld (process_zombie_stack_base),hl
    ld e,(ix+PROC_STACK_HIGH)
    ld d,(ix+PROC_STACK_HIGH+1)
    or a
    ex de,hl
    sbc hl,de
    jp c,zx48_process_zombie_panic
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld (process_zombie_stack_size),hl
    ld l,(ix+PROC_ARG_PTR)
    ld h,(ix+PROC_ARG_PTR+1)
    ld (process_zombie_bootstrap_base),hl
    ld l,(ix+PROC_OWNED_BYTES)
    ld h,(ix+PROC_OWNED_BYTES+1)
    ld (process_zombie_owned_bytes),hl

    ; Validate the complete private-extent shape before the first destructive
    ; operation. Spawn/exec publish rounded even sizes and OWNED_BYTES is their
    ; exact image+stack+bootstrap sum.
    ld hl,(process_zombie_image_base)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld hl,(process_zombie_image_size)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld hl,(process_zombie_stack_base)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld hl,(process_zombie_bootstrap_base)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld hl,(process_zombie_owned_bytes)
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld de,(process_zombie_image_size)
    or a
    sbc hl,de
    jp c,zx48_process_zombie_panic
    ld de,(process_zombie_stack_size)
    or a
    sbc hl,de
    jp c,zx48_process_zombie_panic
    ld a,h
    or l
    jp z,zx48_process_zombie_panic
    bit 0,l
    jp nz,zx48_process_zombie_panic
    ld (process_zombie_bootstrap_size),hl

    ; Architecture §7.5 ordering: reparent every generation-qualified child to
    ; PID1 before releasing this process's private resources. A missing/stale
    ; PID1 identity or inconsistent tree is scheduler-fatal, not a partial exit.
    ld a,(process_zombie_pid)
    call zx48_process_reparent_children_to_pid1
    jp c,zx48_process_zombie_panic

    ; Close handles, release private allocations, then publish status/ZOMBIE.
    ; Any allocator inconsistency is kernel-fatal; silently retaining or
    ; double-freeing memory is not an exit result.
    call zx48_handles_close_all_current
    jp c,zx48_process_zombie_panic
zx48_process_zombie_free_bootstrap:
    ld hl,(process_zombie_bootstrap_base)
    ld bc,(process_zombie_bootstrap_size)
    call zx48_free
    jp c,zx48_process_zombie_panic
zx48_process_zombie_free_stack:
    ld hl,(process_zombie_stack_base)
    ld bc,(process_zombie_stack_size)
    call zx48_free
    jp c,zx48_process_zombie_panic
zx48_process_zombie_free_image:
    ld hl,(process_zombie_image_base)
    ld bc,(process_zombie_image_size)
    call zx48_free
    jp c,zx48_process_zombie_panic

zx48_process_zombie_publish:
    ld a,(process_zombie_pid)
    call zx48_process_links_desc_ptr
    jp c,zx48_process_zombie_panic
    xor a
    ld (ix+PROC_IMAGE_BASE),a
    ld (ix+PROC_IMAGE_BASE+1),a
    ld (ix+PROC_IMAGE_SIZE),a
    ld (ix+PROC_IMAGE_SIZE+1),a
    ld (ix+PROC_STACK_LOW),a
    ld (ix+PROC_STACK_LOW+1),a
    ld (ix+PROC_STACK_HIGH),a
    ld (ix+PROC_STACK_HIGH+1),a
    ld (ix+PROC_SAVED_SP),a
    ld (ix+PROC_SAVED_SP+1),a
    ld (ix+PROC_WAIT_OBJECT),a
    ld (ix+PROC_WAKE_TICK+0),a
    ld (ix+PROC_WAKE_TICK+1),a
    ld (ix+PROC_WAKE_TICK+2),a
    ld (ix+PROC_WAKE_TICK+3),a
    ld (ix+PROC_OWNED_BYTES),a
    ld (ix+PROC_OWNED_BYTES+1),a
    ld (ix+PROC_ARG_PTR),a
    ld (ix+PROC_ARG_PTR+1),a
    ld (ix+PROC_ENV_PTR),a
    ld (ix+PROC_ENV_PTR+1),a
    ld a,(process_zombie_status)
    ld (ix+PROC_EXIT_STATUS),a
    ld (ix+PROC_STATE),PROC_ZOMBIE
    call zx48_process_zombie_wake_parent
    call zx48_process_restore_tty_owner
    jp zx48_schedule

; Wake only the same generation-qualified parent identity recorded by P2.13.
; A recycled numeric parent PID must not receive a wake belonging to an older
; parent generation.
zx48_process_zombie_wake_parent:
    ld a,(process_zombie_parent_pid)
    cp HANDLE_FREE
    ret z
    cp MAX_PROCESSES
    ret nc
    call zx48_process_generation_get
    ret c
    ld hl,(process_zombie_parent_generation)
    or a
    sbc hl,de
    ret nz
    ld a,(process_zombie_parent_pid)
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    cp PROC_WAIT_CHILD
    ret nz
    IFDEF ZX48_P2_15_WAIT_ENABLED
    IFDEF ZX48_P2_16_WAIT_ANY_ENABLED
    ; P2.16 any-child WAIT accepts this already parent-generation-qualified
    ; exiting child without applying the P2.15 exact-child token filter.
    ld a,(process_zombie_parent_pid)
    call zx48_process_wait_any_flag_ptr
    ret c
    ld a,(hl)
    or a
    jr nz,zx48_process_zombie_wake_ready
    ENDIF
    ; P2.15 specific WAIT wakes only for the exact recorded child generation.
    ld a,(process_zombie_parent_pid)
    ld b,a
    ld a,(process_zombie_pid)
    call zx48_process_zombie_wait_specific_match
    ret c
    ld a,(process_zombie_parent_pid)
    call zx48_process_links_desc_ptr
    ret c
    ENDIF
zx48_process_zombie_wake_ready:
    ld (ix+PROC_STATE),PROC_READY
    xor a
    ret

zx48_process_zombie_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

process_zombie_pid: db 0
process_zombie_status: db 0
process_zombie_parent_pid: db HANDLE_FREE
process_zombie_parent_generation: dw 0
process_zombie_image_base: dw 0
process_zombie_image_size: dw 0
process_zombie_stack_base: dw 0
process_zombie_stack_size: dw 0
process_zombie_bootstrap_base: dw 0
process_zombie_bootstrap_size: dw 0
process_zombie_owned_bytes: dw 0
    ENDM

; P2.15 generation-qualified SYS_WAIT for one specific child.  This staged
; emitter composes after P2.13 linkage helpers and before P2.14 ZOMBIE wake.
; The public 48-byte descriptor ABI remains unchanged: the validated one-byte
; status destination is retained in bounded side metadata indexed by parent PID.
    MACRO EMIT_WAIT_SPECIFIC_ROUTINES
ZX48_P2_15_WAIT_EMITTED EQU 1

; A=parent PID -> HL=durable status-pointer slot.
zx48_process_wait_status_ptr_slot:
    cp MAX_PROCESSES
    jp nc,zx48_process_wait_specific_child
    ld l,a
    ld h,0
    add hl,hl
    ld de,process_wait_status_ptr
    add hl,de
    xor a
    ret

; A=specific child PID, DE=already prevalidated writable status byte.
; Immediate ZOMBIE children are reaped synchronously. A live exact child stores
; the status destination, installs the dedicated syscall continuation, blocks,
; and never returns through this frame until the exact child generation wakes it.
zx48_process_wait_specific:
    ld (process_wait_specific_target_pid),a
    ld (process_wait_specific_status_tmp),de
    call zx48_process_wait_record_specific
    ret c

    ld a,(current_pid)
    call zx48_process_wait_status_ptr_slot
    jp c,zx48_process_wait_specific_record_failed
    ld de,(process_wait_specific_status_tmp)
    ld (hl),e
    inc hl
    ld (hl),d

    ld a,(process_wait_specific_target_pid)
    call zx48_process_wait_matches
    jp c,zx48_process_wait_specific_record_failed
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jr z,zx48_process_wait_specific_reap

zx48_process_wait_specific_block:
    ld a,(current_pid)
    call zx48_process_links_desc_ptr
    jp c,zx48_process_wait_specific_record_failed
    ld hl,(syscall_frame_sp)
    ld de,SYSCALL_FRAME_PC_O
    add hl,de
    ld de,zx48_syscall_resume_wait_specific
    ld (hl),e
    inc hl
    ld (hl),d
    ld (ix+PROC_STATE),PROC_WAIT_CHILD
    jp zx48_schedule

; Dedicated syscall continuation after the exact ZOMBIE wake. current_pid is
; again the parent. Reload every durable field instead of trusting registers
; that belonged to the pre-schedule kernel activation.
zx48_process_wait_specific_resume:
    ld a,(current_pid)
    call zx48_process_wait_pid_ptr
    jp c,zx48_process_wait_specific_child
    ld a,(hl)
    cp HANDLE_FREE
    jp z,zx48_process_wait_specific_child
    ld (process_wait_specific_target_pid),a
    call zx48_process_wait_matches
    jp c,zx48_process_wait_specific_child
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jp nz,zx48_process_wait_specific_child

; IX is the exact generation-qualified ZOMBIE descriptor. Capture the result,
; write exactly one status byte, then perform the now-infallible unlink/reclaim.
zx48_process_wait_specific_reap:
    ld a,(ix+PROC_EXIT_STATUS)
    ld (process_wait_specific_status),a
    ld a,(ix+PROC_PID)
    ld (process_wait_specific_target_pid),a

    ld a,(current_pid)
    call zx48_process_wait_status_ptr_slot
    jp c,zx48_process_wait_specific_child
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or e
    jp z,zx48_process_wait_specific_child
    ld a,(process_wait_specific_status)
    ld (de),a

    call zx48_process_wait_specific_release
    call zx48_process_wait_specific_clear
    ld a,(process_wait_specific_target_pid)
    ld l,a
    ld h,0
    xor a
    ret

; Reclaim only after status has been copied out. Exact generation matching above
; proves every fallible relation used here, so a failure is an internal scheduler
; invariant violation rather than a user-visible partial WAIT result.
zx48_process_wait_specific_release:
    ld a,(process_wait_specific_target_pid)
    call zx48_process_unlink_child
    jr c,zx48_process_wait_specific_panic
    ld a,(process_wait_specific_target_pid)
    call zx48_process_links_desc_ptr
    jr c,zx48_process_wait_specific_panic
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,PROC_DESC_SIZE-1
    ldir
    ret

; Clear all parent-owned specific-wait continuation state after successful reap.
zx48_process_wait_specific_clear:
    ld a,(current_pid)
    call zx48_process_wait_pid_ptr
    jr c,zx48_process_wait_specific_panic
    ld (hl),HANDLE_FREE
    ld a,(current_pid)
    call zx48_process_wait_generation_ptr
    jr c,zx48_process_wait_specific_panic
    ld (hl),0
    inc hl
    ld (hl),0
    ld a,(current_pid)
    call zx48_process_wait_status_ptr_slot
    jr c,zx48_process_wait_specific_panic
    ld (hl),0
    inc hl
    ld (hl),0
    xor a
    ret

; B=parent PID, A=exiting child PID. P2.14 has already proved that B is the same
; parent generation recorded by the child. This final qualifier proves that the
; parent is waiting for this exact child generation, not merely a numeric PID.
zx48_process_zombie_wait_specific_match:
    ld (process_wait_specific_candidate_pid),a
    ld a,b
    ld (process_wait_specific_parent_pid),a
    call zx48_process_wait_pid_ptr
    jp c,zx48_process_wait_specific_child
    ld a,(process_wait_specific_candidate_pid)
    cp (hl)
    jp nz,zx48_process_wait_specific_child
    call zx48_process_generation_get
    jp c,zx48_process_wait_specific_child
    ld a,d
    or e
    jp z,zx48_process_wait_specific_child
    ld (process_wait_specific_candidate_generation),de
    ld a,(process_wait_specific_parent_pid)
    call zx48_process_wait_generation_ptr
    jp c,zx48_process_wait_specific_child
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld hl,(process_wait_specific_candidate_generation)
    or a
    sbc hl,bc
    jp nz,zx48_process_wait_specific_child
    xor a
    ret

zx48_process_wait_specific_record_failed:
    call zx48_process_wait_specific_clear
zx48_process_wait_specific_child:
    ld a,E_CHILD
    scf
    ret
zx48_process_wait_specific_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

process_wait_specific_target_pid: db 0
process_wait_specific_candidate_pid: db 0
process_wait_specific_parent_pid: db 0
process_wait_specific_status: db 0
process_wait_specific_status_tmp: dw 0
process_wait_specific_candidate_generation: dw 0
process_wait_status_ptr: defs MAX_PROCESSES*2,0
    ENDM

; P2.16 generation-qualified SYS_WAIT for any current child. The scan order is
; deliberately PID2..PID7 ascending, so simultaneous zombies are reaped in
; lowest-PID-first order. This staged emitter composes after P2.15 and reuses
; its validated status-pointer storage and exact unlink/reclaim primitive.
    MACRO EMIT_WAIT_ANY_ROUTINES
ZX48_P2_16_WAIT_ANY_EMITTED EQU 1

; A=parent PID -> HL=one-byte wait-any flag.
zx48_process_wait_any_flag_ptr:
    cp MAX_PROCESSES
    jp nc,zx48_process_wait_any_child
    ld e,a
    ld d,0
    ld hl,process_wait_any
    add hl,de
    xor a
    ret

; A=candidate PID. Carry clear leaves IX on a current generation-qualified child.
zx48_process_wait_any_match:
    cp 2
    jp c,zx48_process_wait_any_child
    cp MAX_PROCESSES
    jp nc,zx48_process_wait_any_child
    ld (process_wait_any_candidate_pid),a
    call zx48_process_links_desc_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jp z,zx48_process_wait_any_child
    ld a,(current_pid)
    ld b,a
    ld a,(ix+PROC_PARENT)
    cp b
    jp nz,zx48_process_wait_any_child

    ld a,(process_wait_any_candidate_pid)
    call zx48_process_parent_generation_ptr
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld hl,(process_wait_any_parent_generation)
    or a
    sbc hl,bc
    jp nz,zx48_process_wait_any_child

    ld a,(process_wait_any_candidate_pid)
    call zx48_process_pid_bit
    ld (process_wait_any_child_bit),a
    ld a,(current_pid)
    call zx48_process_child_mask_ptr
    ld a,(process_wait_any_child_bit)
    and (hl)
    jp z,zx48_process_wait_any_child
    xor a
    ret

; A must be FF (-1), DE is the already prevalidated one-byte status destination.
zx48_process_wait:
    cp $ff
    jp nz,zx48_process_wait_any_child
    ld (process_wait_any_status_tmp),de

    ; Clear any stale specific-wait token before publishing the any-child state.
    call zx48_process_wait_specific_clear
    ld a,(current_pid)
    call zx48_process_wait_any_flag_ptr
    jp c,zx48_process_wait_any_child
    ld (hl),1
    ld a,(current_pid)
    call zx48_process_wait_status_ptr_slot
    jp c,zx48_process_wait_any_child
    ld de,(process_wait_any_status_tmp)
    ld (hl),e
    inc hl
    ld (hl),d

zx48_process_wait_any_scan:
    ; Snapshot the current parent identity once for this deterministic scan.
    ld a,(current_pid)
    call zx48_process_generation_get
    jp c,zx48_process_wait_any_none
    ld a,d
    or e
    jp z,zx48_process_wait_any_none
    ld (process_wait_any_parent_generation),de
    xor a
    ld (process_wait_any_has_child),a
    ld a,2
    ld (process_wait_any_candidate_pid),a

zx48_process_wait_any_scan_loop:
    ld a,(process_wait_any_candidate_pid)
    call zx48_process_wait_any_match
    jr c,zx48_process_wait_any_next
    ld a,1
    ld (process_wait_any_has_child),a
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jp z,zx48_process_wait_any_reap

zx48_process_wait_any_next:
    ld a,(process_wait_any_candidate_pid)
    inc a
    ld (process_wait_any_candidate_pid),a
    cp MAX_PROCESSES
    jr c,zx48_process_wait_any_scan_loop
    ld a,(process_wait_any_has_child)
    or a
    jp z,zx48_process_wait_any_none

zx48_process_wait_any_block:
    ld a,(current_pid)
    call zx48_process_links_desc_ptr
    jp c,zx48_process_wait_any_panic
    ld hl,(syscall_frame_sp)
    ld de,SYSCALL_FRAME_PC_O
    add hl,de
    ld de,zx48_syscall_resume_wait_any
    ld (hl),e
    inc hl
    ld (hl),d
    ld (ix+PROC_STATE),PROC_WAIT_CHILD
    jp zx48_schedule

; Scheduler continuation used only by P2.16. It mirrors the syscall-owned
; continuation prologue so the blocked call resumes through the normal return path.
zx48_syscall_resume_wait_any:
    ld (syscall_user_sp),sp
    ld (syscall_saved_ix),ix
    ld sp,BOOT_STACK_TOP
    call zx48_process_wait_any_resume
    jp zx48_syscall_return

zx48_process_wait_any_resume:
    ld a,(current_pid)
    call zx48_process_wait_any_flag_ptr
    jp c,zx48_process_wait_any_child
    ld a,(hl)
    or a
    jp z,zx48_process_wait_any_child
    jp zx48_process_wait_any_scan

; IX is the first matching zombie in the documented ascending scan. Status is
; copied before unlink/reclaim, and exactly one descriptor is reclaimed per call.
zx48_process_wait_any_reap:
    ld a,(ix+PROC_EXIT_STATUS)
    ld (process_wait_any_status),a
    ld a,(ix+PROC_PID)
    ld (process_wait_any_reaped_pid),a
    ld (process_wait_specific_target_pid),a

    ld a,(current_pid)
    call zx48_process_wait_status_ptr_slot
    jp c,zx48_process_wait_any_panic
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or e
    jp z,zx48_process_wait_any_panic
    ld a,(process_wait_any_status)
    ld (de),a

    call zx48_process_wait_specific_release
    call zx48_process_wait_any_clear
    ld a,(process_wait_any_reaped_pid)
    ld l,a
    ld h,0
    xor a
    ret

zx48_process_wait_any_none:
    call zx48_process_wait_any_clear
zx48_process_wait_any_child:
    ld a,E_CHILD
    scf
    ret

zx48_process_wait_any_clear:
    ld a,(current_pid)
    call zx48_process_wait_any_flag_ptr
    jp c,zx48_process_wait_any_panic
    ld (hl),0
    call zx48_process_wait_specific_clear
    xor a
    ret

zx48_process_wait_any_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

process_wait_any: defs MAX_PROCESSES,0
process_wait_any_candidate_pid: db 0
process_wait_any_child_bit: db 0
process_wait_any_has_child: db 0
process_wait_any_status: db 0
process_wait_any_status_tmp: dw 0
process_wait_any_parent_generation: dw 0
process_wait_any_reaped_pid: db 0
    ENDM
