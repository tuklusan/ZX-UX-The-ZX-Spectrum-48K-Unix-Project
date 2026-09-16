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
import sys

sys.path.insert(0, str(Path("v1/tools-host/test-driver").resolve()))

import phase1
import phase2_parent_child as p213
from driver_core import require_project_tool, run_command

root = Path.cwd()
_, fixture_binary, fixture_symbols = p213._assemble_fixture(root, run_command, require_project_tool)
names = (
    "zx48_process_links_init",
    "zx48_process_link_child",
    "zx48_process_unlink_child",
    "zx48_process_reparent_children_to_pid1",
    "zx48_process_wait_record_specific",
    "zx48_process_wait_matches",
    "process_generation",
    "process_parent_generation",
    "process_child_mask",
    "process_wait_pid",
    "process_wait_generation",
    "process_table",
    "current_pid",
    "MAX_PROCESSES",
    "PROC_DESC_SIZE",
    "PROC_READY",
    "E_CHILD",
    "E_AGAIN",
)
symbols = p213._symbols(fixture_symbols, names)
fixture = fixture_binary.read_bytes()
table = symbols["process_table"]
current_pid = symbols["current_pid"]
generations = symbols["process_generation"]
parent_generations = symbols["process_parent_generation"]
child_masks = symbols["process_child_mask"]
wait_pids = symbols["process_wait_pid"]
wait_generations = symbols["process_wait_generation"]


def successful_call(code: bytearray, address: int) -> None:
    code += p213._call(address) + p213._jp_c(p213.FAIL_PC)


def base_code(stage: int) -> bytearray:
    code = bytearray(b"\xF3" + phase1._ld_sp(p213.TEST_STACK))
    successful_call(code, symbols["zx48_process_links_init"])
    if stage < 1:
        return code
    code += p213._set_byte(current_pid, 1)
    code += bytes((0x3E, 2))
    successful_call(code, symbols["zx48_process_link_child"])
    code += p213._set_byte(table + 2 * p213.PROC_DESC_SIZE + p213.PROC_STATE, symbols["PROC_READY"])
    if stage < 2:
        return code
    code += p213._set_byte(current_pid, 2)
    code += bytes((0x3E, 3))
    successful_call(code, symbols["zx48_process_link_child"])
    code += p213._set_byte(table + 3 * p213.PROC_DESC_SIZE + p213.PROC_STATE, symbols["PROC_READY"])
    if stage < 3:
        return code
    code += p213._set_byte(current_pid, 1)
    code += bytes((0x3E, 2))
    successful_call(code, symbols["zx48_process_wait_record_specific"])
    if stage < 4:
        return code
    code += bytes((0x3E, 2))
    successful_call(code, symbols["zx48_process_reparent_children_to_pid1"])
    if stage < 5:
        return code
    code += bytes((0x3E, 2))
    successful_call(code, symbols["zx48_process_unlink_child"])
    code += p213._set_byte(table + 2 * p213.PROC_DESC_SIZE + p213.PROC_STATE, 0)
    if stage < 6:
        return code
    code += bytes((0x3E, 2))
    successful_call(code, symbols["zx48_process_link_child"])
    code += p213._set_byte(table + 2 * p213.PROC_DESC_SIZE + p213.PROC_STATE, symbols["PROC_READY"])
    return code


def run_case(label: str, code: bytearray) -> bool:
    code += phase1._jp(p213.PASS_PC)
    try:
        p213.run_sna(root, bytes(code), patch=p213._patch(fixture, table), timeout=5.0)
    except Exception as exc:
        print(f"P2.13 STAGE {label} FAIL {type(exc).__name__}: {exc}", flush=True)
        return False
    print(f"P2.13 STAGE {label} PASS", flush=True)
    return True


for stage, label in enumerate(("links-init", "link-pid2", "link-pid3", "wait-record", "reparent", "unlink", "reuse-pid2")):
    if not run_case(label, base_code(stage)):
        raise SystemExit(2)

checks = (
    ("parent-pid2", p213._expect_byte(table + 2 * p213.PROC_DESC_SIZE + p213.PROC_PARENT, 1)),
    ("parent-pid3", p213._expect_byte(table + 3 * p213.PROC_DESC_SIZE + p213.PROC_PARENT, 1)),
    ("generation-pid0", p213._expect_word(generations + 0 * 2, 1)),
    ("generation-pid1", p213._expect_word(generations + 1 * 2, 1)),
    ("parent-generation-pid1", p213._expect_word(parent_generations + 1 * 2, 1)),
    ("root-child-mask", p213._expect_byte(child_masks + 0, 0x02)),
    ("generation-pid2-reused", p213._expect_word(generations + 2 * 2, 2)),
    ("generation-pid3", p213._expect_word(generations + 3 * 2, 1)),
    ("parent-generation-pid2", p213._expect_word(parent_generations + 2 * 2, 1)),
    ("parent-generation-pid3", p213._expect_word(parent_generations + 3 * 2, 1)),
    ("pid1-child-mask", p213._expect_byte(child_masks + 1, 0x0C)),
    ("pid2-child-mask", p213._expect_byte(child_masks + 2, 0)),
    ("wait-pid-token", p213._expect_byte(wait_pids + 1, 2)),
    ("wait-generation-token", p213._expect_word(wait_generations + 1 * 2, 1)),
)
for label, assertion in checks:
    code = base_code(6)
    code += assertion
    if not run_case(label, code):
        raise SystemExit(3)

code = base_code(6)
code += bytes((0x3E, 2)) + p213._call(symbols["zx48_process_wait_matches"]) + p213._jp_nc(p213.FAIL_PC)
code += bytes((0xFE, symbols["E_CHILD"] & 0xFF)) + phase1._jp_nz(p213.FAIL_PC)
if not run_case("stale-wait-negative", code):
    raise SystemExit(4)

code = base_code(6)
code += p213._set_byte(generations + 4 * 2, 0xFF)
code += p213._set_byte(generations + 4 * 2 + 1, 0xFF)
code += bytes((0x3E, 4)) + p213._call(symbols["zx48_process_link_child"]) + p213._jp_nc(p213.FAIL_PC)
code += bytes((0xFE, symbols["E_AGAIN"] & 0xFF)) + phase1._jp_nz(p213.FAIL_PC)
code += p213._expect_byte(table + 4 * p213.PROC_DESC_SIZE + p213.PROC_STATE, 0)
code += p213._expect_byte(table + 4 * p213.PROC_DESC_SIZE + p213.PROC_PARENT, 0xFF)
code += p213._expect_byte(child_masks + 1, 0x0C)
if not run_case("generation-exhaustion-negative", code):
    raise SystemExit(5)

print("P2.13 STAGE DIAGNOSTIC PASS", flush=True)
