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
; P3.18 deterministic three-stage, two-pipe pipeline fixture.

    DEVICE ZXSPECTRUM48
    INCLUDE "../../include/zx48ux.inc"
    INCLUDE "../../include/mex1.inc"
    INCLUDE "../../src/kernel/syscall.asm"
    INCLUDE "../../src/kernel/memory.asm"
    INCLUDE "../../src/kernel/process.asm"
    INCLUDE "../../src/kernel/handles.asm"
    INCLUDE "../../src/kernel/pipe.asm"
    INCLUDE "../../src/kernel/objects.asm"

P318_GOOD_RECORD EQU $B000
PANIC_SCHEDULER  EQU $03
PANIC_ALLOCATOR  EQU $02

    ORG $E000
p318_start:
    EMIT_MEMORY_ROUTINES
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_PROCESS_CAPACITY_ROUTINE
    EMIT_MEX1_RELOCATION_ROUTINES
    EMIT_ARG1_ROUTINES
    EMIT_ENV1_ROUTINES
    EMIT_INITIAL_CONTEXT_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_PARENT_CHILD_ROUTINES
    EMIT_SPAWN_PREFLIGHT_ROUTINES
    EMIT_SPAWN_TRANSACTION_ROUTINES
    EMIT_PIPE_ROUTINES

p318_gateway:
    ld (syscall_arg_hl),hl
    jp zx48_sys_spawn

p318_read_handle:
    push hl
    push bc
    call zx48_handle_lookup
    pop bc
    pop hl
    ret c
    ld a,(ix+OD_ID_O)
    jp zx48_pipe_read

p318_write_handle:
    push hl
    push bc
    call zx48_handle_lookup
    pop bc
    pop hl
    ret c
    ld a,(ix+OD_ID_O)
    jp zx48_pipe_write

zx48_process_lookup:
    cp MAX_PROCESSES
    jr nc,p318_process_noent
    ld ix,process_table
    or a
    jr z,p318_process_have_ptr
    ld b,a
    ld de,PROC_DESC_SIZE
p318_process_ptr_loop:
    add ix,de
    djnz p318_process_ptr_loop
p318_process_have_ptr:
    ld a,(ix+PROC_STATE)
    or a
    jr z,p318_process_noent
    xor a
    ret
p318_process_noent:
    ld a,E_NOENT
    scf
    ret

zx48_process_count:
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_PROCESSES-1
    ld c,0
p318_process_count_loop:
    ld a,(ix+PROC_STATE)
    or a
    jr z,p318_process_count_next
    inc c
p318_process_count_next:
    ld de,PROC_DESC_SIZE
    add ix,de
    djnz p318_process_count_loop
    ld a,c
    or a
    ret

zx48_spawn_resolve_ram_object:
    ld ix,P318_GOOD_RECORD
    xor a
    ret

zx48_memcpy:
    ld a,b
    or c
    ret z
    ldir
    ret

zx48_schedule:
    scf
    ret

zx48_panic:
    ld (p318_panic_code),a
    scf
    ret

syscall_arg_hl: dw 0
current_pid: db 0
process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0
p318_panic_code: db 0

p318_end:
    ASSERT p318_end <= FAST_RESERVE_START
    SAVEBIN "../../build/p318-pipe3.bin",p318_start,p318_end-p318_start
