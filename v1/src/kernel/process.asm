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
; Eight fixed 48-byte process descriptors. Runnable register state lives on each
; FAST stack; the descriptor keeps only saved SP and process metadata.

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
zx48_process_init_each:
    ld (ix+PROC_PID),c
    ld (ix+PROC_PARENT),HANDLE_FREE
    push bc
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld b,MAX_HANDLES_PER_PROCESS
    ld a,HANDLE_FREE
zx48_process_init_handle:
    ld (hl),a
    inc hl
    djnz zx48_process_init_handle
    pop bc
    ld de,PROC_DESC_SIZE
    add ix,de
    inc c
    djnz zx48_process_init_each
    ld ix,process_table
    ld (ix+PROC_STATE),PROC_RUNNING
    xor a
    ld (current_pid),a
    ret

; A=pid -> IX record regardless of state.
zx48_process_ptr:
zx48_process_descriptor_from_pid:
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
    or a
    ret
zx48_process_lookup:
    call zx48_process_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_noent
    xor a
    or a
    ret
zx48_process_noent:
    ld a,E_NOENT
    scf
    ret

; Reserve PID2..7; caller publishes READY after constructing complete context.
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

zx48_process_alloc_slot:
    call zx48_process_reserve_slot
    ret c
    ld (ix+PROC_STATE),PROC_READY
    ld a,(process_temp_pid)
    or a
    ret

; Boot creates PID1 shell descriptor before image publication.
zx48_process_prepare_pid1:
    ld a,1
    call zx48_process_ptr
    ret c
    ld a,(ix+PROC_STATE)
    or a
    jr nz,zx48_process_busy
    ld a,1
    ld (ix+PROC_PID),a
    xor a
    ld (ix+PROC_PARENT),a
    ld (ix+PROC_CWD),DIR_ROOT
    ld hl,process_name_sh
    push ix
    pop de
    ld bc,PROC_NAME
    ex de,hl
    add hl,bc
    ex de,hl
    ld hl,process_name_sh
    ld bc,10
    ldir
    xor a
    or a
    ret
zx48_process_busy:
    ld a,E_BUSY
    scf
    ret

zx48_process_public_flags:
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_FLAGS)
    and PROC_FLAG_CANCEL
    ret

; A=pid, HL=16-byte PINFO destination.
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
    or a
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
    ret

; A=status. PID0 never exits; normal children become ZOMBIE and wake parent.
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
    call zx48_process_wake_parent
    jp zx48_schedule
zx48_process_exit_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

zx48_process_wake_parent:
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

; A=target pid. PID1 may cancel any child; others only their direct child.
zx48_process_kill:
    ld (process_temp_pid),a
    or a
    jr z,zx48_process_perm
    cp 1
    jr z,zx48_process_perm
    call zx48_process_lookup
    ret c
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
    or a
    ret
zx48_process_kill_started:
    ld a,(ix+PROC_FLAGS)
    or PROC_FLAG_CANCEL
    ld (ix+PROC_FLAGS),a
    ld a,(ix+PROC_STATE)
    cp PROC_RUNNING
    jr z,zx48_process_kill_return
    cp PROC_READY
    jr z,zx48_process_kill_return
    cp PROC_ZOMBIE
    jr z,zx48_process_noent
    ld (ix+PROC_STATE),PROC_READY
zx48_process_kill_return:
    xor a
    or a
    ret
zx48_process_perm:
    ld a,E_PERM
    scf
    ret

; Reap one ZOMBIE child. A=target PID or FF for any; B=status pointer low-level
; helper receives writable status address in DE. Returns HL=child pid.
zx48_process_wait:
    ld (process_wait_target),a
zx48_process_wait_scan:
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
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jr z,zx48_process_wait_reap
    ld a,1
    ld (process_wait_has_child),a
zx48_process_wait_next:
    ld hl,PROC_DESC_SIZE
    push hl
    pop de
    add ix,de
    djnz zx48_process_wait_each
    ld a,(process_wait_has_child)
    or a
    jr z,zx48_process_wait_none
    xor a
    ld (process_wait_has_child),a
    ld a,(current_pid)
    call zx48_process_lookup
    ld (ix+PROC_STATE),PROC_WAIT_CHILD
    call zx48_schedule
    jr zx48_process_wait_scan
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
    or a
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
