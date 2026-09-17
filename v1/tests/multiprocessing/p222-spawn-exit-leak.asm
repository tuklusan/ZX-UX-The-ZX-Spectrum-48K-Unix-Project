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
; P2.22 deterministic repeated spawn/exit/reap resource-accounting stress.

    DEVICE ZXSPECTRUM48
    INCLUDE "../../include/zx48ux.inc"
    INCLUDE "../../include/mex1.inc"
    INCLUDE "../../src/kernel/syscall.asm"
    INCLUDE "../../src/kernel/interrupt.asm"
    INCLUDE "../../src/kernel/errors.asm"
    INCLUDE "../../src/kernel/memory.asm"
    INCLUDE "../../src/kernel/process.asm"
    INCLUDE "../../src/kernel/handles.asm"
    INCLUDE "../../src/kernel/objects.asm"

P222_PROC1_ADDRESS EQU $A300
P222_GOOD_RECORD   EQU $B000

    ORG $E000
p222_start:
    EMIT_MEMORY_ROUTINES
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_PROCESS_CAPACITY_ROUTINE
    EMIT_MEX1_RELOCATION_ROUTINES
    EMIT_ARG1_ROUTINES
    EMIT_ENV1_ROUTINES
    EMIT_INITIAL_CONTEXT_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_PARENT_CHILD_ROUTINES
    EMIT_WAIT_SPECIFIC_ROUTINES
    EMIT_ZOMBIE_TRANSITION_ROUTINES
    EMIT_SPAWN_PREFLIGHT_ROUTINES
    EMIT_SPAWN_TRANSACTION_ROUTINES

p222_gateway:
    ld (syscall_arg_hl),hl
    jp zx48_sys_spawn

; Minimal process lookup surface required by the spawn transaction. The P2.22
; fixture composes only the staged Phase-2 emitters it exercises, avoiding the
; resident EMIT_PROCESS_ROUTINES storage/ABI definitions already supplied by
; syscall.asm while preserving the production lookup contract.
zx48_process_lookup:
    cp MAX_PROCESSES
    jr nc,p222_process_noent
    ld c,a
    ld ix,process_table
    or a
    jr z,p222_process_have_ptr
    ld b,a
    ld de,PROC_DESC_SIZE
p222_process_ptr_loop:
    add ix,de
    djnz p222_process_ptr_loop
p222_process_have_ptr:
    ld a,(ix+PROC_STATE)
    or a
    jr z,p222_process_noent
    xor a
    ret
p222_process_noent:
    ld a,E_NOENT
    scf
    ret

; Fixture-local production-equivalent live lookup required by TTY restoration.
zx48_process_live_lookup:
    call zx48_process_lookup
    ret c
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jr z,p222_process_noent
    xor a
    ret

; EMIT_MEMORY_ROUTINES references the resident process-count helper. The broad
; EMIT_PROCESS_ROUTINES surface cannot be emitted here because syscall.asm
; already supplies resident ABI/storage definitions, so preserve its contract
; exactly in the standalone qualification fixture.
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

; EMIT_ZOMBIE_TRANSITION_ROUTINES reaches this helper on every tested child
; exit. Reproduce the resident TTY-owner restoration semantics instead of
; weakening the qualification path with a no-op stub.
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

zx48_spawn_resolve_ram_object:
    ld ix,P222_GOOD_RECORD
    xor a
    ret

zx48_pipe_endpoint_closed:
    xor a
    ret

; The production scheduler does not return to zx48_process_exit_to_zombie.
; This fixture-only continuation returns so the harness can immediately reap;
; clear carry on that synthetic normal return while zx48_panic retains carry-set.
zx48_schedule:
    or a
    ret
zx48_schedule_finish_syscall:
zx48_syscall_resume_wait_specific:
    ret

zx48_panic:
    ld (p222_panic_code),a
    scf
    ret

; Execute 64 waves. Each wave fills every spawnable slot PID2..PID7,
; then exits and generation-safe reaps every child. 64 * 6 = 384 complete
; spawn/exit/reap cycles, while PID0/PID1 remain the fixed system slots.
p222_stress:
    call zx48_process_links_init
    ret c
    ld a,64
    ld (p222_cycles_left),a
    xor a
    ld (p222_cycles_done),a
p222_cycle:
    ld hl,P222_PROC1_ADDRESS
    call p222_gateway
    ret c
    ld a,h
    or a
    jp nz,p222_fail
    ld a,l
    cp 2
    jp nz,p222_fail

    ld hl,P222_PROC1_ADDRESS
    call p222_gateway
    ret c
    ld a,h
    or a
    jp nz,p222_fail
    ld a,l
    cp 3
    jp nz,p222_fail

    ld hl,P222_PROC1_ADDRESS
    call p222_gateway
    ret c
    ld a,h
    or a
    jp nz,p222_fail
    ld a,l
    cp 4
    jp nz,p222_fail

    ld hl,P222_PROC1_ADDRESS
    call p222_gateway
    ret c
    ld a,h
    or a
    jp nz,p222_fail
    ld a,l
    cp 5
    jp nz,p222_fail

    ld hl,P222_PROC1_ADDRESS
    call p222_gateway
    ret c
    ld a,h
    or a
    jp nz,p222_fail
    ld a,l
    cp 6
    jp nz,p222_fail

    ld hl,P222_PROC1_ADDRESS
    call p222_gateway
    ret c
    ld a,h
    or a
    jp nz,p222_fail
    ld a,l
    cp 7
    jp nz,p222_fail

    ld a,2
    call p222_exit_reap
    ret c
    ld a,3
    call p222_exit_reap
    ret c
    ld a,4
    call p222_exit_reap
    ret c
    ld a,5
    call p222_exit_reap
    ret c
    ld a,6
    call p222_exit_reap
    ret c
    ld a,7
    call p222_exit_reap
    ret c

    ld a,(p222_cycles_done)
    inc a
    ld (p222_cycles_done),a
    ld a,(p222_cycles_left)
    dec a
    ld (p222_cycles_left),a
    jp nz,p222_cycle
    xor a
    ret

p222_exit_reap:
    ld (p222_child_pid),a
    ld (current_pid),a
    call zx48_process_lookup
    ret c
    ; Spawn publishes READY. This fixture invokes the child's exit directly
    ; instead of running the scheduler, so model the scheduler's READY->RUNNING
    ; transition before entering the production exit-to-zombie routine.
    ld (ix+PROC_STATE),PROC_RUNNING
    xor a
    call zx48_process_exit_to_zombie
    ret c
    ld a,1
    ld (current_pid),a
    ld de,p222_status
    ld a,(p222_child_pid)
    call zx48_process_wait_specific
    ret

p222_fail:
    ld a,E_BUSY
    scf
    ret

syscall_arg_hl: dw 0
current_pid: db 0
process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0
tty_input_owner: db 1
p222_cycles_left: db 0
p222_cycles_done: db 0
p222_child_pid: db 0
p222_status: db 0
p222_panic_code: db 0

p222_end:
    ASSERT p222_end <= FAST_RESERVE_START
    SAVEBIN "../../build/p222-spawn-exit-leak.bin",p222_start,p222_end-p222_start
