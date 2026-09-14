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

zx48_process_reserve_slot:
    ld ix,process_table+2*PROC_DESC_SIZE
    ld c,2
    ld b,MAX_PROCESSES-2
zx48_process_reserve_scan:
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_reserve_found
    ld de,PROC_DESC_SIZE
    add ix,de
    inc c
    djnz zx48_process_reserve_scan
    ld a,E_AGAIN
    scf
    ret
zx48_process_reserve_found:
    ld a,c
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


; P2.03 ABS16 relocation validator/applicator. The routine is deliberately a
; separate emitter until P2.04 integrates it into the resident loader path.
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
