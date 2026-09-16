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

path = Path("v1/src/kernel/process.asm")
text = path.read_text(encoding="utf-8")


def one(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"P2.13 process-only corrector {label}: expected 1 anchor, found {count}")
    text = text.replace(old, new, 1)


one(
    "    MACRO EMIT_PARENT_CHILD_ROUTINES\n",
    "    MACRO EMIT_PARENT_CHILD_ROUTINES\nZX48_P2_13_LINKS_EMITTED EQU 1\n",
    "emission-marker",
)

one(
    "    ld a,(current_pid)\n"
    "    cp MAX_PROCESSES\n"
    "    jp nc,zx48_process_links_inval\n"
    "    ld (process_link_parent_pid),a\n"
    "    call zx48_process_links_desc_ptr\n",
    "    ld a,(current_pid)\n"
    "    ld (process_link_parent_pid),a\n"
    "    cp MAX_PROCESSES\n"
    "    jp nc,zx48_process_links_inval\n"
    "    call zx48_process_links_desc_ptr\n",
    "link-parent-bound-order",
)

wait_matches = text.index("zx48_process_wait_matches:\n")
head = text[:wait_matches]
tail = text[wait_matches:]


def replace_one(section: str, old: str, new: str, label: str) -> str:
    count = section.count(old)
    if count != 1:
        raise SystemExit(f"P2.13 process-only corrector {label}: expected 1 anchor, found {count}")
    return section.replace(old, new, 1)


head = replace_one(
    head,
    "    ld a,(current_pid)\n"
    "    call zx48_process_generation_get\n"
    "    ret c\n"
    "    ld (process_wait_parent_generation),de\n",
    "    ld a,(current_pid)\n"
    "    call zx48_process_generation_get\n"
    "    ret c\n"
    "    ld a,d\n"
    "    or e\n"
    "    jp z,zx48_process_wait_child\n"
    "    ld (process_wait_parent_generation),de\n",
    "wait-record-parent-generation-zero",
)

head = replace_one(
    head,
    "    ld a,(process_wait_candidate_pid)\n"
    "    call zx48_process_generation_get\n"
    "    ret c\n"
    "    ld (process_wait_candidate_generation),de\n"
    "    ld a,(current_pid)\n"
    "    call zx48_process_wait_pid_ptr\n",
    "    ld a,(process_wait_candidate_pid)\n"
    "    call zx48_process_generation_get\n"
    "    ret c\n"
    "    ld a,d\n"
    "    or e\n"
    "    jp z,zx48_process_wait_child\n"
    "    ld (process_wait_candidate_generation),de\n"
    "    ld a,(current_pid)\n"
    "    call zx48_process_wait_pid_ptr\n",
    "wait-record-child-generation-zero",
)

tail = replace_one(
    tail,
    "    ld a,(current_pid)\n"
    "    call zx48_process_wait_pid_ptr\n"
    "    ld a,(process_wait_candidate_pid)\n",
    "    ld a,(current_pid)\n"
    "    call zx48_process_wait_pid_ptr\n"
    "    jp c,zx48_process_wait_child\n"
    "    ld a,(process_wait_candidate_pid)\n",
    "wait-match-current-pid-bound",
)

tail = replace_one(
    tail,
    "    ld a,(current_pid)\n"
    "    call zx48_process_generation_get\n"
    "    ret c\n"
    "    ld (process_wait_parent_generation),de\n",
    "    ld a,(current_pid)\n"
    "    call zx48_process_generation_get\n"
    "    ret c\n"
    "    ld a,d\n"
    "    or e\n"
    "    jp z,zx48_process_wait_child\n"
    "    ld (process_wait_parent_generation),de\n",
    "wait-match-parent-generation-zero",
)

tail = replace_one(
    tail,
    "    ld a,(process_wait_candidate_pid)\n"
    "    call zx48_process_generation_get\n"
    "    ret c\n"
    "    ld (process_wait_candidate_generation),de\n",
    "    ld a,(process_wait_candidate_pid)\n"
    "    call zx48_process_generation_get\n"
    "    ret c\n"
    "    ld a,d\n"
    "    or e\n"
    "    jp z,zx48_process_wait_child\n"
    "    ld (process_wait_candidate_generation),de\n",
    "wait-match-child-generation-zero",
)

text = head + tail

old_spawn = (
    "    ; P2.13 generation-qualified linkage is the final fallible action.  It is\n"
    "    ; side-effect free on failure; after success the cooperative commit has no\n"
    "    ; remaining failure edge before READY publishes the complete child.\n"
    "    ld a,(process_spawn_child_pid)\n"
    "    call zx48_process_link_child\n"
    "    jp c,zx48_process_spawn_rollback\n"
    "\n"
    "    ; Commit is intentionally non-fallible. The descriptor remains PROC_FREE\n"
    "    ; while every field is written; READY is the single publication store.\n"
    "    ld hl,(process_spawn_child_desc)\n"
    "    xor a\n"
    "    ld (hl),a\n"
    "    ld d,h\n"
    "    ld e,l\n"
    "    inc de\n"
    "    ld bc,PROC_DESC_SIZE-1\n"
    "    ldir\n"
    "    ld ix,(process_spawn_child_desc)\n"
    "    ld a,(process_spawn_child_pid)\n"
    "    ld (ix+PROC_PID),a\n"
    "    xor a\n"
    "    ld (ix+PROC_FLAGS),a\n"
)
new_spawn = (
    "IFDEF ZX48_P2_13_LINKS_EMITTED\n"
    "    ; P2.13 clears the still-private descriptor before generation-qualified\n"
    "    ; linkage. Linkage is the final fallible action before READY publication.\n"
    "    ld hl,(process_spawn_child_desc)\n"
    "    xor a\n"
    "    ld (hl),a\n"
    "    ld d,h\n"
    "    ld e,l\n"
    "    inc de\n"
    "    ld bc,PROC_DESC_SIZE-1\n"
    "    ldir\n"
    "    ld a,(process_spawn_child_pid)\n"
    "    call zx48_process_link_child\n"
    "    jp c,zx48_process_spawn_rollback\n"
    "    ld ix,(process_spawn_child_desc)\n"
    "    ld a,(process_spawn_child_pid)\n"
    "    ld (ix+PROC_PID),a\n"
    "ELSE\n"
    "    ; Preserve the certified P2.10/P2.12 expansion byte-for-byte when the\n"
    "    ; P2.13 linkage emitter is absent from the assembly unit.\n"
    "    ; Commit is intentionally non-fallible. The descriptor remains PROC_FREE\n"
    "    ; while every field is written; READY is the single publication store.\n"
    "    ld hl,(process_spawn_child_desc)\n"
    "    xor a\n"
    "    ld (hl),a\n"
    "    ld d,h\n"
    "    ld e,l\n"
    "    inc de\n"
    "    ld bc,PROC_DESC_SIZE-1\n"
    "    ldir\n"
    "    ld ix,(process_spawn_child_desc)\n"
    "    ld a,(process_spawn_child_pid)\n"
    "    ld (ix+PROC_PID),a\n"
    "    ld a,(current_pid)\n"
    "    ld (ix+PROC_PARENT),a\n"
    "ENDIF\n"
    "    xor a\n"
    "    ld (ix+PROC_FLAGS),a\n"
)
one(old_spawn, new_spawn, "spawn-process-only-integration")

path.write_text(text, encoding="utf-8", newline="\n")

# The reviewed historical P2.13 driver anchored its raw-parent negative at the
# P2.10 commit comment.  The process-only integration above deliberately removes
# that comment from the active P2.13 branch, so make the source contract inspect
# the actual IFDEF arm instead.  The ELSE arm must retain the certified legacy
# raw-parent publication for P2.10/P2.12 fixtures.
driver_path = Path("v1/tools-host/test-driver/phase2_parent_child.py")
driver = driver_path.read_text(encoding="utf-8")
old_contract = (
    '        {"name": "p210-spawn-no-longer-publishes-raw-parent-pid-itself", "passed": "ld a,(current_pid)\\n    ld (ix+PROC_PARENT),a" not in process[process.index("; Commit is intentionally non-fallible.", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")):process.index("    ENDM\\n", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES"))]},\n'
)
new_contract = (
    '        {"name": "p210-spawn-no-longer-publishes-raw-parent-pid-itself", "passed": "ld a,(current_pid)\\n    ld (ix+PROC_PARENT),a" not in process[process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")):process.index("ELSE", process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")))]},\n'
)
count = driver.count(old_contract)
if count != 1:
    raise SystemExit(f"P2.13 process-only corrector source-contract-anchor: expected 1 anchor, found {count}")
driver_path.write_text(driver.replace(old_contract, new_contract, 1), encoding="utf-8", newline="\n")

print("P2.13 process-only corrector: PASS")
