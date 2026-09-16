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

from pathlib import Path

process_path = Path("v1/src/kernel/process.asm")
process = process_path.read_text(encoding="utf-8")
old = """zx48_process_kill_ok:
    ld a,(ix+PROC_PRIVATE_FLAGS)
    and PROC_PRIVATE_STARTED
    jr nz,zx48_process_kill_started
    ld (ix+PROC_EXIT_STATUS),130
    ld (ix+PROC_STATE),PROC_ZOMBIE
    xor a
    ret
zx48_process_kill_started:
"""
new = """zx48_process_kill_ok:
    ld a,(ix+PROC_PRIVATE_FLAGS)
    and PROC_PRIVATE_STARTED
    IFDEF ZX48_P2_18_KILL_ENABLED
    jp z,zx48_process_kill_never_started
    ELSE
    jr nz,zx48_process_kill_started
    ld (ix+PROC_EXIT_STATUS),130
    ld (ix+PROC_STATE),PROC_ZOMBIE
    xor a
    ret
    ENDIF
zx48_process_kill_started:
"""
if process.count(old) != 1:
    raise SystemExit("P2.18 kill integration anchor mismatch")
process = process.replace(old, new, 1)

marker = "\n\n; P2.03 ABS16 relocation validator/applicator."
if process.count(marker) != 1:
    raise SystemExit("P2.18 helper insertion anchor mismatch")
helper = r'''

; P2.18 resource-safe cancellation for a spawned child that has never reached
; user PC. The resident kernel keeps the frozen fallback unless this staged
; emitter is selected. The target remains READY while complete ownership shape
; is validated; only then are target handles and private extents released. The
; descriptor identity remains waitable as ZOMBIE/status 130.
    MACRO EMIT_KILL_NEVER_STARTED_ROUTINES
ZX48_P2_18_KILL_ENABLED EQU 1

; IX -> already permission-checked live target descriptor with STARTED clear.
zx48_process_kill_never_started:
    ld a,(ix+PROC_PID)
    ld (process_kill_pid),a
    ld a,(ix+PROC_STATE)
    cp PROC_READY
    jp nz,zx48_process_kill_never_started_panic

    ld l,(ix+PROC_IMAGE_BASE)
    ld h,(ix+PROC_IMAGE_BASE+1)
    ld (process_kill_image_base),hl
    ld l,(ix+PROC_IMAGE_SIZE)
    ld h,(ix+PROC_IMAGE_SIZE+1)
    ld (process_kill_image_size),hl
    ld l,(ix+PROC_STACK_LOW)
    ld h,(ix+PROC_STACK_LOW+1)
    ld (process_kill_stack_base),hl
    ld e,(ix+PROC_STACK_HIGH)
    ld d,(ix+PROC_STACK_HIGH+1)
    ex de,hl
    or a
    sbc hl,de
    jp c,zx48_process_kill_never_started_panic
    ld a,h
    or l
    jp z,zx48_process_kill_never_started_panic
    bit 0,l
    jp nz,zx48_process_kill_never_started_panic
    ld (process_kill_stack_size),hl
    ld l,(ix+PROC_ARG_PTR)
    ld h,(ix+PROC_ARG_PTR+1)
    ld (process_kill_bootstrap_base),hl
    ld l,(ix+PROC_OWNED_BYTES)
    ld h,(ix+PROC_OWNED_BYTES+1)
    ld (process_kill_owned_bytes),hl

    ; Validate every private extent before the first handle/refcount or allocator
    ; mutation. Spawn publishes rounded even extents and their exact summed size.
    ld hl,(process_kill_image_base)
    ld a,h
    or l
    jp z,zx48_process_kill_never_started_panic
    bit 0,l
    jp nz,zx48_process_kill_never_started_panic
    ld hl,(process_kill_image_size)
    ld a,h
    or l
    jp z,zx48_process_kill_never_started_panic
    bit 0,l
    jp nz,zx48_process_kill_never_started_panic
    ld hl,(process_kill_stack_base)
    ld a,h
    or l
    jp z,zx48_process_kill_never_started_panic
    bit 0,l
    jp nz,zx48_process_kill_never_started_panic
    ld hl,(process_kill_bootstrap_base)
    ld a,h
    or l
    jp z,zx48_process_kill_never_started_panic
    bit 0,l
    jp nz,zx48_process_kill_never_started_panic
    ld hl,(process_kill_owned_bytes)
    ld a,h
    or l
    jp z,zx48_process_kill_never_started_panic
    bit 0,l
    jp nz,zx48_process_kill_never_started_panic
    ld de,(process_kill_image_size)
    or a
    sbc hl,de
    jp c,zx48_process_kill_never_started_panic
    ld de,(process_kill_stack_size)
    or a
    sbc hl,de
    jp c,zx48_process_kill_never_started_panic
    ld a,h
    or l
    jp z,zx48_process_kill_never_started_panic
    bit 0,l
    jp nz,zx48_process_kill_never_started_panic
    ld (process_kill_bootstrap_size),hl

    ; Close the target descriptor's handle slots directly. Never substitute
    ; current_pid: the caller remains the running parent throughout SYS_KILL.
    ld a,(process_kill_pid)
    call zx48_process_ptr
    jp c,zx48_process_kill_never_started_panic
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld b,MAX_HANDLES_PER_PROCESS
zx48_process_kill_close_handles:
    ld a,(hl)
    cp HANDLE_FREE
    jr z,zx48_process_kill_close_next
    ld (hl),HANDLE_FREE
    push bc
    push hl
    call zx48_od_release
    pop hl
    pop bc
    jp c,zx48_process_kill_never_started_panic
zx48_process_kill_close_next:
    inc hl
    djnz zx48_process_kill_close_handles

zx48_process_kill_free_bootstrap:
    ld hl,(process_kill_bootstrap_base)
    ld bc,(process_kill_bootstrap_size)
    call zx48_free
    jp c,zx48_process_kill_never_started_panic
zx48_process_kill_free_stack:
    ld hl,(process_kill_stack_base)
    ld bc,(process_kill_stack_size)
    call zx48_free
    jp c,zx48_process_kill_never_started_panic
zx48_process_kill_free_image:
    ld hl,(process_kill_image_base)
    ld bc,(process_kill_image_size)
    call zx48_free
    jp c,zx48_process_kill_never_started_panic

zx48_process_kill_publish:
    ld a,(process_kill_pid)
    call zx48_process_ptr
    jp c,zx48_process_kill_never_started_panic
    xor a
    ld (ix+PROC_FLAGS),a
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
    ld (ix+PROC_WAKE_TICK),a
    ld (ix+PROC_WAKE_TICK+1),a
    ld (ix+PROC_WAKE_TICK+2),a
    ld (ix+PROC_WAKE_TICK+3),a
    ld (ix+PROC_OWNED_BYTES),a
    ld (ix+PROC_OWNED_BYTES+1),a
    ld (ix+PROC_ARG_PTR),a
    ld (ix+PROC_ARG_PTR+1),a
    ld (ix+PROC_ENV_PTR),a
    ld (ix+PROC_ENV_PTR+1),a
    ld (ix+PROC_PRIVATE_FLAGS),a
    ld a,130
    ld (ix+PROC_EXIT_STATUS),a
    ld (ix+PROC_STATE),PROC_ZOMBIE
    xor a
    ret

zx48_process_kill_never_started_panic:
    ld a,PANIC_SCHEDULER
    jp zx48_panic

process_kill_pid: db 0
process_kill_image_base: dw 0
process_kill_image_size: dw 0
process_kill_stack_base: dw 0
process_kill_stack_size: dw 0
process_kill_bootstrap_base: dw 0
process_kill_bootstrap_size: dw 0
process_kill_owned_bytes: dw 0
    ENDM
'''
process = process.replace(marker, helper + marker, 1)
process_path.write_text(process, encoding="utf-8", newline="\n")

run_path = Path("v1/tools-host/test-driver/run.py")
run = run_path.read_text(encoding="utf-8")
import_anchor = "import phase2_reparent\n"
if run.count(import_anchor) != 1:
    raise SystemExit("P2.18 run.py import anchor mismatch")
run = run.replace(import_anchor, import_anchor + "import phase2_kill_never_started\n", 1)
dispatch_anchor = '''    if step == "P2.17":
        return phase2_reparent.dispatch(root, action, step, **kwargs)
    if step.startswith("P2."):
'''
dispatch_replacement = '''    if step == "P2.17":
        return phase2_reparent.dispatch(root, action, step, **kwargs)
    if step == "P2.18":
        return phase2_kill_never_started.dispatch(root, action, step, **kwargs)
    if step.startswith("P2."):
'''
if run.count(dispatch_anchor) != 1:
    raise SystemExit("P2.18 run.py dispatch anchor mismatch")
run = run.replace(dispatch_anchor, dispatch_replacement, 1)
run_path.write_text(run, encoding="utf-8", newline="\n")
