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
; 48-byte bounded process descriptor. The canonical runnable register frame is
; stack-resident; saved_sp is the only CPU resume token held here.

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
; Inputs: none.
; Outputs: PID0 RUNNING, PID1..7 FREE, handles free.
; Flags: modified.
; Clobbers: AF/BC/DE/HL.
zx48_process_init:
    xor a
    ld hl,process_table
    ld de,process_table+1
    ld bc,MAX_PROCESSES*PROC_DESC_SIZE-1
    ld (hl),a
    ldir
    ld hl,process_table
    ld b,MAX_PROCESSES
    ld c,0
zx48_process_init_loop:
    ld (hl),c
    push hl
    ld de,PROC_HANDLES
    add hl,de
    ld a,HANDLE_FREE
    ld d,MAX_HANDLES_PER_PROCESS
zx48_process_init_handles:
    ld (hl),a
    inc hl
    dec d
    jr nz,zx48_process_init_handles
    pop hl
    ld de,PROC_DESC_SIZE
    add hl,de
    inc c
    djnz zx48_process_init_loop
    ld hl,process_table
    ld (hl),0
    inc hl
    ld (hl),HANDLE_FREE
    inc hl
    ld (hl),PROC_RUNNING
    ld a,0
    ld (current_pid),a
    ret

; Inputs: A=PID.
; Outputs: carry clear IX=descriptor, carry set A=E_NOENT.
; Flags: carry result.
; Clobbers: AF/BC/DE/HL/IX.
zx48_process_lookup:
    cp MAX_PROCESSES
    jr nc,zx48_process_lookup_fail
    ld c,a
    ld b,0
    ld hl,0
    ld de,PROC_DESC_SIZE
zx48_process_lookup_mul:
    ld a,c
    or a
    jr z,zx48_process_lookup_done
    add hl,de
    dec c
    jr zx48_process_lookup_mul
zx48_process_lookup_done:
    ld de,process_table
    add hl,de
    push hl
    pop ix
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_lookup_fail
    xor a
    or a
    ret
zx48_process_lookup_fail:
    ld a,E_NOENT
    scf
    ret

; Inputs: none.
; Outputs: carry clear A=new PID/IX=descriptor; carry set A=E_AGAIN.
; Flags: carry result.
; Clobbers: AF/BC/DE/HL/IX.
zx48_process_alloc_slot:
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_USER_PID
    ld c,1
zx48_process_alloc_scan:
    ld a,(ix+PROC_STATE)
    or a
    jr z,zx48_process_alloc_found
    ld de,PROC_DESC_SIZE
    add ix,de
    inc c
    djnz zx48_process_alloc_scan
    ld a,E_AGAIN
    scf
    ret
zx48_process_alloc_found:
    push ix
    pop hl
    xor a
    ld (hl),a
    ld de,1
    push hl
    pop de
    inc de
    ld bc,PROC_DESC_SIZE-1
    ldir
    pop hl
    push hl
    pop ix
    ld a,c
    ld (ix+PROC_PID),a
    ld a,(current_pid)
    ld (ix+PROC_PARENT),a
    ld (ix+PROC_STATE),PROC_READY
    ld a,HANDLE_FREE
    ld b,MAX_HANDLES_PER_PROCESS
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
zx48_process_alloc_handles:
    ld (hl),a
    inc hl
    djnz zx48_process_alloc_handles
    ld a,(ix+PROC_PID)
    or a
    ret

; Inputs: A=PID.
; Outputs: A=public state flag byte (only CANCEL_PENDING bit0).
; Flags: modified.
; Clobbers: AF/BC/DE/HL/IX.
zx48_process_public_flags:
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_FLAGS)
    and PROC_FLAG_CANCEL
    ret

; Inputs: A=PID, HL=writable 16-byte output.
; Outputs: exact PINFO output or carry set errno.
; Flags: carry result.
; Clobbers: AF/BC/DE/HL/IX.
zx48_process_info:
    ld (process_info_ptr),hl
    push af
    call zx48_process_lookup
    jr c,zx48_process_info_fail_pop
    pop af
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
    push ix
    pop de
    push hl
    ld hl,PROC_NAME
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
zx48_process_info_fail_pop:
    pop bc
    scf
    ret

; Inputs: none.
; Outputs: A=count of non-FREE PID1..7.
; Flags: modified.
; Clobbers: AF/BC/DE/IX.
zx48_process_count:
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_USER_PID
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

; Inputs: A=exit status; current_pid identifies caller.
; Outputs: current descriptor becomes ZOMBIE; never resumes as runnable.
; Flags: modified.
; Clobbers: AF/BC/DE/HL/IX.
zx48_process_exit:
    ld b,a
    ld a,(current_pid)
    or a
    jr z,zx48_process_exit_idle
    call zx48_process_lookup
    jr c,zx48_process_exit_idle
    ld (ix+PROC_EXIT_STATUS),b
    ld (ix+PROC_STATE),PROC_ZOMBIE
    jp zx48_schedule
zx48_process_exit_idle:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

process_info_ptr:
    dw 0
current_pid:
    db 0
process_table:
    defs MAX_PROCESSES*PROC_DESC_SIZE,0
    ENDM
