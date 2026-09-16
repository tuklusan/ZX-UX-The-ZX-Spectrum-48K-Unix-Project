#!/usr/bin/env python3
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX Sinclair ZX Spectrum Unix
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
#
# Temporary guarded P2.15 cloud patch helper. Remove after the canonical source
# patch is durably applied and validated.

from pathlib import Path


PROCESS_PATH = Path("v1/src/kernel/process.asm")
SYSCALL_PATH = Path("v1/src/kernel/syscall.asm")
RUN_PATH = Path("v1/tools-host/test-driver/run.py")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{name}: expected exactly one old-text match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    process = PROCESS_PATH.read_text(encoding="utf-8")
    syscall = SYSCALL_PATH.read_text(encoding="utf-8")
    runner = RUN_PATH.read_text(encoding="utf-8")

    if "    MACRO EMIT_WAIT_SPECIFIC_ROUTINES\n" in process:
        raise SystemExit("P2.15 process macro already exists; refusing duplicate patch")

    wake_old = """    ld a,(ix+PROC_STATE)
    cp PROC_WAIT_CHILD
    ret nz
    ld (ix+PROC_STATE),PROC_READY
    xor a
    ret

zx48_process_zombie_panic:
"""
    wake_new = """    ld a,(ix+PROC_STATE)
    cp PROC_WAIT_CHILD
    ret nz
IFDEF ZX48_P2_15_WAIT_EMITTED
    ; P2.15 specific WAIT wakes only for the exact recorded child generation.
    ld a,(process_zombie_pid)
    ld b,(process_zombie_parent_pid)
    call zx48_process_zombie_wait_specific_match
    ret c
ENDIF
    ld (ix+PROC_STATE),PROC_READY
    xor a
    ret

zx48_process_zombie_panic:
"""
    process = replace_once(process, wake_old, wake_new, "P2.14 wake hook")

    wait_macro = """
; P2.15 generation-qualified SYS_WAIT for one specific child.  This staged
; emitter composes after P2.13 linkage helpers and before P2.14 ZOMBIE wake.
; The public 48-byte descriptor ABI remains unchanged: the validated one-byte
; status destination is retained in bounded side metadata indexed by parent PID.
    MACRO EMIT_WAIT_SPECIFIC_ROUTINES
ZX48_P2_15_WAIT_EMITTED EQU 1

; A=parent PID -> HL=durable status-pointer slot.
zx48_process_wait_status_ptr_slot:
    cp MAX_PROCESSES
    jr nc,zx48_process_wait_specific_child
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
    jr c,zx48_process_wait_specific_record_failed
    ld de,(process_wait_specific_status_tmp)
    ld (hl),e
    inc hl
    ld (hl),d

    ld a,(process_wait_specific_target_pid)
    call zx48_process_wait_matches
    jr c,zx48_process_wait_specific_record_failed
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jr z,zx48_process_wait_specific_reap

zx48_process_wait_specific_block:
    ld a,(current_pid)
    call zx48_process_links_desc_ptr
    jr c,zx48_process_wait_specific_record_failed
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
    jr c,zx48_process_wait_specific_child
    ld a,(hl)
    cp HANDLE_FREE
    jr z,zx48_process_wait_specific_child
    ld (process_wait_specific_target_pid),a
    call zx48_process_wait_matches
    jr c,zx48_process_wait_specific_child
    ld a,(ix+PROC_STATE)
    cp PROC_ZOMBIE
    jr nz,zx48_process_wait_specific_child

; IX is the exact generation-qualified ZOMBIE descriptor. Capture the result,
; write exactly one status byte, then perform the now-infallible unlink/reclaim.
zx48_process_wait_specific_reap:
    ld a,(ix+PROC_EXIT_STATUS)
    ld (process_wait_specific_status),a
    ld a,(ix+PROC_PID)
    ld (process_wait_specific_target_pid),a

    ld a,(current_pid)
    call zx48_process_wait_status_ptr_slot
    jr c,zx48_process_wait_specific_child
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or e
    jr z,zx48_process_wait_specific_child
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
    jr c,zx48_process_wait_specific_child
    ld a,(process_wait_specific_candidate_pid)
    cp (hl)
    jr nz,zx48_process_wait_specific_child
    call zx48_process_generation_get
    jr c,zx48_process_wait_specific_child
    ld a,d
    or e
    jr z,zx48_process_wait_specific_child
    ld (process_wait_specific_candidate_generation),de
    ld a,(process_wait_specific_parent_pid)
    call zx48_process_wait_generation_ptr
    jr c,zx48_process_wait_specific_child
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld hl,(process_wait_specific_candidate_generation)
    or a
    sbc hl,bc
    jr nz,zx48_process_wait_specific_child
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
"""
    process = process.rstrip() + "\n\n" + wait_macro.strip("\n") + "\n"

    resume_old = """zx48_syscall_resume_intr:
    ld (syscall_user_sp),sp
    ld (syscall_saved_ix),ix
    ld sp,BOOT_STACK_TOP
    ld a,E_INTR
    scf
    jr zx48_syscall_return
    ENDM
"""
    resume_new = """zx48_syscall_resume_intr:
    ld (syscall_user_sp),sp
    ld (syscall_saved_ix),ix
    ld sp,BOOT_STACK_TOP
    ld a,E_INTR
    scf
    jr zx48_syscall_return

IFDEF ZX48_P2_15_WAIT_EMITTED
; Scheduler continuation for a blocked P2.15 specific-child WAIT.
zx48_syscall_resume_wait_specific:
    ld (syscall_user_sp),sp
    ld (syscall_saved_ix),ix
    ld sp,BOOT_STACK_TOP
    call zx48_process_wait_specific_resume
    jr zx48_syscall_return
ENDIF
    ENDM
"""
    syscall = replace_once(syscall, resume_old, resume_new, "specific WAIT continuation")

    wait_old = """    ld hl,(syscall_arg_hl)
    ld a,(hl)
    call zx48_process_wait
    ret c
    xor a
    ret

zx48_sys_kill:
"""
    wait_new = """    ld hl,(syscall_arg_hl)
    ld a,(hl)
IFDEF ZX48_P2_15_WAIT_EMITTED
    cp $ff
    jr z,zx48_sys_wait_legacy_any
    call zx48_process_wait_specific
    ret
zx48_sys_wait_legacy_any:
ENDIF
    call zx48_process_wait
    ret c
    xor a
    ret

zx48_sys_kill:
"""
    syscall = replace_once(syscall, wait_old, wait_new, "specific WAIT syscall dispatch")

    import_old = "import phase2_parent_child\nimport phase2_zombie\n"
    import_new = "import phase2_parent_child\nimport phase2_zombie\nimport phase2_wait_specific\n"
    runner = replace_once(runner, import_old, import_new, "P2.15 driver import")

    dispatch_old = """    if step == "P2.14":
        return phase2_zombie.dispatch(root, action, step, **kwargs)
    if step.startswith("P2."):
"""
    dispatch_new = """    if step == "P2.14":
        return phase2_zombie.dispatch(root, action, step, **kwargs)
    if step == "P2.15":
        return phase2_wait_specific.dispatch(root, action, step, **kwargs)
    if step.startswith("P2."):
"""
    runner = replace_once(runner, dispatch_old, dispatch_new, "P2.15 driver dispatch")

    PROCESS_PATH.write_text(process, encoding="utf-8", newline="\n")
    SYSCALL_PATH.write_text(syscall, encoding="utf-8", newline="\n")
    RUN_PATH.write_text(runner, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
