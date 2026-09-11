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
; Cooperative scheduler. Context frames live on process FAST stacks and contain
; AF,BC,DE,HL,IX beneath the already-present return PC.

    MACRO EMIT_SCHEDULER_ROUTINES
; Inputs: called only at a kernel-controlled scheduling point.
; Outputs: restores the selected task frame and RETs into it.
; Flags: restored from task AF.
; Clobbers: none from selected task's perspective.
zx48_schedule:
    push af
    push bc
    push de
    push hl
    push ix
    ld a,(current_pid)
    call zx48_process_descriptor_from_pid
    ld (ix+PROC_SAVED_SP),sp
    ld a,(ix+PROC_STATE)
    cp PROC_RUNNING
    jr nz,zx48_schedule_scan
    ld (ix+PROC_STATE),PROC_READY
zx48_schedule_scan:
    ld a,(current_pid)
    inc a
    and $07
    ld b,MAX_PROCESSES
zx48_schedule_scan_loop:
    push af
    call zx48_process_descriptor_from_pid
    ld a,(ix+PROC_STATE)
    cp PROC_READY
    jr z,zx48_schedule_select_pop
    cp PROC_SLEEPING
    call z,zx48_scheduler_maybe_wake
    ld a,(ix+PROC_STATE)
    cp PROC_READY
    jr z,zx48_schedule_select_pop
    pop af
    inc a
    and $07
    djnz zx48_schedule_scan_loop
    xor a
    call zx48_process_descriptor_from_pid
    jr zx48_schedule_select
zx48_schedule_select_pop:
    pop af
zx48_schedule_select:
    ld (current_pid),a
    ld (ix+PROC_STATE),PROC_RUNNING
    ld a,(ix+PROC_PRIVATE_FLAGS)
    or PROC_PRIVATE_STARTED
    ld (ix+PROC_PRIVATE_FLAGS),a
    ld l,(ix+PROC_SAVED_SP)
    ld h,(ix+PROC_SAVED_SP+1)
    ld sp,hl
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ld iy,ROM_IY_ANCHOR
    ret

; Inputs: A=pid 0..7.
; Outputs: IX descriptor address.
; Flags: modified.
; Clobbers: BC/DE/HL/IX.
zx48_process_descriptor_from_pid:
    ld c,a
    ld b,0
    ld hl,process_table
    ld de,PROC_DESC_SIZE
    ld a,c
    or a
    jr z,zx48_process_descriptor_done
zx48_process_descriptor_loop:
    add hl,de
    dec c
    jr nz,zx48_process_descriptor_loop
zx48_process_descriptor_done:
    push hl
    pop ix
    ret

; Inputs: IX=SLEEPING descriptor.
; Outputs: READY if wake_tick <= current ticks in modular low-16 comparison.
; Flags: modified.
; Clobbers: AF/DE/HL.
zx48_scheduler_maybe_wake:
    ld hl,(kernel_ticks)
    ld e,(ix+PROC_WAKE_TICK)
    ld d,(ix+PROC_WAKE_TICK+1)
    or a
    sbc hl,de
    bit 7,h
    ret nz
    ld (ix+PROC_STATE),PROC_READY
    ret

; Inputs: HL=frame delay, current process RUNNING.
; Outputs: resumes at/after target frame.
; Flags: restored at resumption.
; Clobbers: none after resume.
zx48_sleep_current:
    push hl
    ld a,(current_pid)
    call zx48_process_descriptor_from_pid
    pop de
    ld hl,(kernel_ticks)
    add hl,de
    ld (ix+PROC_WAKE_TICK),l
    ld (ix+PROC_WAKE_TICK+1),h
    ld (ix+PROC_STATE),PROC_SLEEPING
    jp zx48_schedule

; Inputs: none.
; Outputs: never exits. Interrupts enabled for HALT.
; Flags: modified.
; Clobbers: AF.
zx48_idle_loop:
    ei
    halt
    call zx48_scheduler_wake_scan
    jp zx48_schedule

zx48_scheduler_wake_scan:
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_USER_PID
zx48_scheduler_wake_loop:
    ld a,(ix+PROC_STATE)
    cp PROC_SLEEPING
    call z,zx48_scheduler_maybe_wake
    ld de,PROC_DESC_SIZE
    add ix,de
    djnz zx48_scheduler_wake_loop
    ret
    ENDM
