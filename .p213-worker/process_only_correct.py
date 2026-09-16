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

one(
    "    ld a,(process_link_child_pid)\n"
    "    call zx48_process_generation_bump\n"
    "    ret c\n"
    "\n"
    "    ; A reused child starts with no children and no inherited wait token.  Its\n",
    "    ld a,(process_link_child_pid)\n"
    "    call zx48_process_generation_bump\n"
    "    ret c\n"
    "\n"
    "    ; Generation bump is the final fallible action. Once it succeeds, reset the\n"
    "    ; still-FREE descriptor here, inside the dynamically exercised helper. This\n"
    "    ; keeps generation exhaustion byte-identical while making successful reuse\n"
    "    ; discard every stale descriptor byte before parent linkage is published.\n"
    "    ld a,(process_link_child_pid)\n"
    "    call zx48_process_links_desc_ptr\n"
    "    push ix\n"
    "    pop hl\n"
    "    xor a\n"
    "    ld (hl),a\n"
    "    ld d,h\n"
    "    ld e,l\n"
    "    inc de\n"
    "    ld bc,PROC_DESC_SIZE-1\n"
    "    ldir\n"
    "    ld a,(process_link_child_pid)\n"
    "    ld (ix+PROC_PID),a\n"
    "\n"
    "    ; A reused child starts with no children and no inherited wait token.  Its\n",
    "link-helper-owns-descriptor-reset",
)

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
    "    IFDEF ZX48_P2_13_LINKS_EMITTED\n"
    "    ; P2.13 delegates generation bump, successful-reuse descriptor reset, and\n"
    "    ; generation-qualified parent publication to the dynamically exercised\n"
    "    ; link helper. Generation exhaustion therefore leaves the FREE descriptor\n"
    "    ; byte-identical; success returns IX on the reset, linked child descriptor.\n"
    "    ld a,(process_spawn_child_pid)\n"
    "    call zx48_process_link_child\n"
    "    jp c,zx48_process_spawn_rollback\n"
    "    ELSE\n"
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
    "    ENDIF\n"
    "    xor a\n"
    "    ld (ix+PROC_FLAGS),a\n"
)
one(old_spawn, new_spawn, "spawn-process-only-integration")

path.write_text(text, encoding="utf-8", newline="\n")

# Tighten the P2.13 driver so descriptor-reset ownership is dynamically visible:
# successful links must clear a stale FREE-descriptor sentinel, while generation
# exhaustion must leave that same sentinel untouched.
driver_path = Path("v1/tools-host/test-driver/phase2_parent_child.py")
driver = driver_path.read_text(encoding="utf-8")


def driver_one(old: str, new: str, label: str) -> None:
    global driver
    count = driver.count(old)
    if count != 1:
        raise SystemExit(f"P2.13 process-only corrector {label}: expected 1 driver anchor, found {count}")
    driver = driver.replace(old, new, 1)


driver_one(
    "PROC_PARENT = 1\nPROC_STATE = 2\n",
    "PROC_PARENT = 1\nPROC_STATE = 2\nPROC_FLAGS = 3\n",
    "driver-proc-flags-offset",
)

driver_one(
    "    for pid in range(PROCESS_COUNT):\n"
    "        table[pid * PROC_DESC_SIZE] = pid\n"
    "        table[pid * PROC_DESC_SIZE + PROC_PARENT] = 0xFF\n",
    "    for pid in range(PROCESS_COUNT):\n"
    "        table[pid * PROC_DESC_SIZE] = pid\n"
    "        table[pid * PROC_DESC_SIZE + PROC_PARENT] = 0xFF\n"
    "        if pid >= 2:\n"
    "            table[pid * PROC_DESC_SIZE + PROC_FLAGS] = 0xA5\n",
    "driver-free-descriptor-sentinel",
)

driver_one(
    "    code += bytes((0x3E, 2)) + _call(symbols[\"zx48_process_link_child\"]) + _jp_c(FAIL_PC)\n"
    "    code += _set_byte(table + 2 * PROC_DESC_SIZE + PROC_STATE, symbols[\"PROC_READY\"])\n"
    "\n"
    "    # PID2 spawns PID3, making the exact tree 1 -> 2 -> 3.\n",
    "    code += bytes((0x3E, 2)) + _call(symbols[\"zx48_process_link_child\"]) + _jp_c(FAIL_PC)\n"
    "    code += _expect_byte(table + 2 * PROC_DESC_SIZE + PROC_FLAGS, 0)\n"
    "    code += _set_byte(table + 2 * PROC_DESC_SIZE + PROC_STATE, symbols[\"PROC_READY\"])\n"
    "\n"
    "    # PID2 spawns PID3, making the exact tree 1 -> 2 -> 3.\n",
    "driver-first-link-clears-sentinel",
)

driver_one(
    "    code += bytes((0x3E, 2)) + _call(symbols[\"zx48_process_unlink_child\"]) + _jp_c(FAIL_PC)\n"
    "    code += _set_byte(table + 2 * PROC_DESC_SIZE + PROC_STATE, 0)\n"
    "\n"
    "    # PID2 is reused under PID1. Generation must advance without disturbing PID3.\n",
    "    code += bytes((0x3E, 2)) + _call(symbols[\"zx48_process_unlink_child\"]) + _jp_c(FAIL_PC)\n"
    "    code += _set_byte(table + 2 * PROC_DESC_SIZE + PROC_STATE, 0)\n"
    "    code += _set_byte(table + 2 * PROC_DESC_SIZE + PROC_FLAGS, 0xA6)\n"
    "\n"
    "    # PID2 is reused under PID1. Generation must advance without disturbing PID3.\n",
    "driver-reuse-sentinel",
)

driver_one(
    "    code += _expect_byte(table + 2 * PROC_DESC_SIZE + PROC_PARENT, 1)\n"
    "    code += _expect_byte(table + 3 * PROC_DESC_SIZE + PROC_PARENT, 1)\n",
    "    code += _expect_byte(table + 2 * PROC_DESC_SIZE + PROC_PARENT, 1)\n"
    "    code += _expect_byte(table + 2 * PROC_DESC_SIZE + PROC_FLAGS, 0)\n"
    "    code += _expect_byte(table + 3 * PROC_DESC_SIZE + PROC_PARENT, 1)\n",
    "driver-reuse-clears-sentinel",
)

driver_one(
    "    code += _expect_byte(table + 4 * PROC_DESC_SIZE + PROC_STATE, 0)\n"
    "    code += _expect_byte(table + 4 * PROC_DESC_SIZE + PROC_PARENT, 0xFF)\n"
    "    code += _expect_byte(child_masks + 1, 0x0C)\n",
    "    code += _expect_byte(table + 4 * PROC_DESC_SIZE + PROC_STATE, 0)\n"
    "    code += _expect_byte(table + 4 * PROC_DESC_SIZE + PROC_PARENT, 0xFF)\n"
    "    code += _expect_byte(table + 4 * PROC_DESC_SIZE + PROC_FLAGS, 0xA5)\n"
    "    code += _expect_byte(child_masks + 1, 0x0C)\n",
    "driver-exhaustion-preserves-sentinel",
)

driver_one(
    "        {\"name\": \"pid-generation-advances-across-reuse-without-reset\", \"passed\": True},\n"
    "        {\"name\": \"stale-generation-qualified-wait-cannot-alias-reused-pid\", \"passed\": True},\n"
    "        {\"name\": \"generation-exhaustion-refuses-reuse-instead-of-wrapping\", \"passed\": True},\n",
    "        {\"name\": \"pid-generation-advances-across-reuse-without-reset\", \"passed\": True},\n"
    "        {\"name\": \"successful-link-clears-stale-free-descriptor-before-publication\", \"passed\": True},\n"
    "        {\"name\": \"stale-generation-qualified-wait-cannot-alias-reused-pid\", \"passed\": True},\n"
    "        {\"name\": \"generation-exhaustion-refuses-reuse-with-free-descriptor-byte-intact\", \"passed\": True},\n",
    "driver-assertion-names",
)

driver_one(
    "    links = process[start:end]\n"
    "    return [\n",
    "    links = process[start:end]\n"
    "    link_start = links.index(\"zx48_process_link_child:\\n\")\n"
    "    link_end = links.index(\"zx48_process_generation_exhausted:\\n\", link_start)\n"
    "    link = links[link_start:link_end]\n"
    "    return [\n",
    "driver-scope-link-contract",
)

driver_one(
    '        {"name": "new-child-link-bumps-generation-before-parent-publication", "passed": links.index("call zx48_process_generation_bump") < links.index("ld (ix+PROC_PARENT),a")},\n',
    '        {"name": "new-child-link-bumps-generation-before-parent-publication", "passed": link.index("call zx48_process_generation_bump") < link.index("ld (ix+PROC_PARENT),a")},\n'
    '        {"name": "successful-link-resets-free-descriptor-after-generation-bump", "passed": link.index("call zx48_process_generation_bump") < link.index("ld bc,PROC_DESC_SIZE-1") < link.index("ld (ix+PROC_PARENT),a")},\n',
    "driver-link-order-contract",
)

old_contract = (
    '        {"name": "p210-spawn-no-longer-publishes-raw-parent-pid-itself", "passed": "ld a,(current_pid)\\n    ld (ix+PROC_PARENT),a" not in process[process.index("; Commit is intentionally non-fallible.", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")):process.index("    ENDM\\n", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES"))]},\n'
)
new_contract = (
    '        {"name": "p210-spawn-no-longer-publishes-raw-parent-pid-itself", "passed": "ld a,(current_pid)\\n    ld (ix+PROC_PARENT),a" not in process[process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")):process.index("ELSE", process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")))]},\n'
    '        {"name": "p213-spawn-does-not-own-untested-descriptor-reset", "passed": "ld hl,(process_spawn_child_desc)" not in process[process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")):process.index("ELSE", process.index("IFDEF ZX48_P2_13_LINKS_EMITTED", process.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")))]},\n'
)
count = driver.count(old_contract)
if count != 1:
    raise SystemExit(f"P2.13 process-only corrector source-contract-anchor: expected 1 anchor, found {count}")
driver = driver.replace(old_contract, new_contract, 1)
driver_path.write_text(driver, encoding="utf-8", newline="\n")

# Fail closed if future edits split successful-reuse reset back out of the helper.
spawn_start = text.index("    MACRO EMIT_SPAWN_TRANSACTION_ROUTINES")
spawn_end = text.index("    ENDM\n", spawn_start)
spawn = text[spawn_start:spawn_end]
marker = spawn.index("    IFDEF ZX48_P2_13_LINKS_EMITTED")
branch_end = spawn.index("    ELSE", marker)
active = spawn[marker:branch_end]
if "call zx48_process_link_child" not in active:
    raise SystemExit("P2.13 integration audit FAIL: active spawn arm does not call generation-safe link helper")
if "ld hl,(process_spawn_child_desc)" in active:
    raise SystemExit(
        "P2.13 integration audit FAIL: active spawn arm still clears the child descriptor outside "
        "the dynamically exercised generation-link helper"
    )
link_start = text.index("zx48_process_link_child:\n")
link_end = text.index("zx48_process_generation_exhausted:\n", link_start)
link = text[link_start:link_end]
if not (
    link.index("call zx48_process_generation_bump")
    < link.index("ld bc,PROC_DESC_SIZE-1")
    < link.index("ld (ix+PROC_PARENT),a")
):
    raise SystemExit("P2.13 integration audit FAIL: helper reset is not after generation bump and before parent publication")

print("P2.13 process-only corrector: PASS")
