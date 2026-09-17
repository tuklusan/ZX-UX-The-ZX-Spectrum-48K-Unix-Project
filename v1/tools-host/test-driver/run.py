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

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True

import foundation
import foundation_rr
import phase0
import phase0_layout
import phase0_boot
import phase0_im2
import phase0_rom
import phase0_alt
import phase0_loader
import phase0_media
import phase0_rr
import phase1
import phase1_core
import phase1_ticks
import phase1_romvars
import phase1_break
import phase1_isrpaths
import phase1_sleep
import phase1_exit
import phase1_console_core
import phase1_font4x8
import phase1_tty64
import phase1_scroll
import phase1_cursor_core
import phase1_ula
import phase1_wallclock
import phase1_time
import phase1_alt
import phase1_keyboard
import phase1_cursor
import phase1_stack
import phase1_getkey
import phase1_putchar
import phase1_conwrite
import phase1_clear
import phase1_getpos
import phase1_setpos
import phase1_primitives_strict
import phase1_acceptance
import phase2_mex1
import phase2_inspector
import phase2_relocation
import phase2_loader
import phase2_stack
import phase2_arg1
import phase2_env1
import phase2_context
import phase2_spawn
import phase2_spawn_atomic
import phase2_handle_inheritance
import phase2_exec
import phase2_parent_child
import phase2_zombie
import phase2_wait_specific
import phase2_wait_any
import phase2_reparent
import phase2_kill_never_started
import phase2_kill_started
import phase2_process_name
import phase2_proc_info
import phase2_spawn_exit_leak
from driver_core import (
    DriverError,
    find_root,
    read_source_state,
    require_clean_source,
    require_project_tool,
    resolve_evidence_dir,
    run_command,
    sha256_file,
    write_evidence,
)

E0_MODULE = {
    "E0.01": foundation_rr,
    "E0.02": foundation_rr,
    "E0.03": foundation,
    "E0.04": foundation,
    "E0.05": foundation,
    "E0.06": foundation,
}
P0_MODULE = {
    "P0.01": phase0,
    "P0.02": phase0_layout,
    "P0.03": phase0_boot,
    "P0.04": phase0_im2,
    "P0.05": phase0_rom,
    "P0.06": phase0_alt,
    "P0.07": phase0_loader,
    "P0.08": phase0_media,
    "P0.09": phase0_media,
    "P0.10": phase0_media,
    **{f"P0.{number:02d}": phase0_rr for number in range(11, 35)},
}


def dispatch(root: Path, action: str, step: str):
    kwargs = {
        "sha256_file": sha256_file,
        "run_command": run_command,
        "require_project_tool": require_project_tool,
    }
    module = E0_MODULE.get(step)
    if module is not None:
        return module.dispatch(root, action, step, **kwargs)
    module = P0_MODULE.get(step)
    if module is not None:
        if module is phase0_media:
            return module.dispatch(root, action, step)
        return module.dispatch(root, action, step, **kwargs)
    if step.startswith(("E0.", "P0.")):
        raise DriverError(f"numbered foundation/Phase-0 step is not registered: {step}")
    if step in {f"P1.{n:02d}" for n in range(1, 13)}:
        return phase1_core.dispatch(root, action, step, **kwargs)
    if step == "P1.13":
        return phase1_ticks.dispatch(root, action, step, **kwargs)
    if step == "P1.14":
        return phase1_romvars.dispatch(root, action, step, **kwargs)
    if step == "P1.15":
        return phase1_break.dispatch(root, action, step, **kwargs)
    if step in ("P1.16", "P1.17"):
        return phase1_isrpaths.dispatch(root, action, step, **kwargs)
    if step == "P1.18":
        return phase1_sleep.dispatch(root, action, step, **kwargs)
    if step == "P1.19":
        return phase1_exit.dispatch(root, action, step, **kwargs)
    if step == "P1.20":
        return phase1_console_core.dispatch(root, action, step, **kwargs)
    if step == "P1.21":
        return phase1_font4x8.dispatch(root, action, step, **kwargs)
    if step == "P1.22":
        return phase1_tty64.dispatch(root, action, step, **kwargs)
    if step == "P1.23":
        return phase1_scroll.dispatch(root, action, step, **kwargs)
    if step == "P1.24":
        return phase1_cursor_core.dispatch(root, action, step, **kwargs)
    if step == "P1.25":
        return phase1_ula.dispatch(root, action, step, **kwargs)
    if step == "P1.26":
        return phase1_wallclock.dispatch(root, action, step, **kwargs)
    if step == "P1.27":
        return phase1_time.dispatch(root, action, step, **kwargs)
    if step == "P1.30":
        return phase1_alt.dispatch(root, action, step, **kwargs)
    if step == "P1.31":
        return phase1_keyboard.dispatch(root, action, step, **kwargs)
    if step == "P1.32":
        return phase1_cursor.dispatch(root, action, step, **kwargs)
    if step == "P1.33":
        return phase1_stack.dispatch(root, action, step, **kwargs)
    if step == "P1.34":
        return phase1_getkey.dispatch(root, action, step, **kwargs)
    if step == "P1.35":
        return phase1_putchar.dispatch(root, action, step, **kwargs)
    if step == "P1.36":
        return phase1_conwrite.dispatch(root, action, step, **kwargs)
    if step == "P1.37":
        return phase1_clear.dispatch(root, action, step, **kwargs)
    if step == "P1.38":
        return phase1_getpos.dispatch(root, action, step, **kwargs)
    if step == "P1.39":
        return phase1_setpos.dispatch(root, action, step, **kwargs)
    if step == "P1.40":
        return phase1_primitives_strict.dispatch(root, action, step, **kwargs)
    if step == "P1.41":
        return phase1_acceptance.dispatch(root, action, step, **kwargs)
    if step.startswith("P1."):
        return phase1.dispatch(root, action, step, **kwargs)
    if step == "P2.01":
        return phase2_mex1.dispatch(root, action, step, **kwargs)
    if step == "P2.02":
        return phase2_inspector.dispatch(root, action, step, **kwargs)
    if step == "P2.03":
        return phase2_relocation.dispatch(root, action, step, **kwargs)
    if step == "P2.04":
        return phase2_loader.dispatch(root, action, step, **kwargs)
    if step == "P2.05":
        return phase2_stack.dispatch(root, action, step, **kwargs)
    if step == "P2.06":
        return phase2_arg1.dispatch(root, action, step, **kwargs)
    if step == "P2.07":
        return phase2_env1.dispatch(root, action, step, **kwargs)
    if step == "P2.08":
        return phase2_context.dispatch(root, action, step, **kwargs)
    if step == "P2.09":
        return phase2_spawn.dispatch(root, action, step, **kwargs)
    if step == "P2.10":
        return phase2_spawn_atomic.dispatch(root, action, step, **kwargs)
    if step == "P2.11":
        return phase2_handle_inheritance.dispatch(root, action, step, **kwargs)
    if step == "P2.12":
        return phase2_exec.dispatch(root, action, step, **kwargs)
    if step == "P2.13":
        return phase2_parent_child.dispatch(root, action, step, **kwargs)
    if step == "P2.14":
        return phase2_zombie.dispatch(root, action, step, **kwargs)
    if step == "P2.15":
        return phase2_wait_specific.dispatch(root, action, step, **kwargs)
    if step == "P2.16":
        return phase2_wait_any.dispatch(root, action, step, **kwargs)
    if step == "P2.17":
        return phase2_reparent.dispatch(root, action, step, **kwargs)
    if step == "P2.18":
        return phase2_kill_never_started.dispatch(root, action, step, **kwargs)
    if step == "P2.19":
        return phase2_kill_started.dispatch(root, action, step, **kwargs)
    if step == "P2.20":
        return phase2_process_name.dispatch(root, action, step, **kwargs)
    if step == "P2.21":
        return phase2_proc_info.dispatch(root, action, step, **kwargs)
    if step == "P2.22":
        return phase2_spawn_exit_leak.dispatch(root, action, step, **kwargs)
    if step.startswith("P2."):
        raise DriverError(f"numbered Phase-2 step is not registered: {step}")
    raise DriverError(f"step is not registered with the deterministic test driver: {step}")


def prerequisite_statuses(step: str) -> dict[str, str]:
    if step in E0_MODULE:
        number = int(step.split(".", 1)[1])
        return {} if number == 1 else {f"E0.{number - 1:02d}": "PASS"}
    if step in P0_MODULE:
        number = int(step.split(".", 1)[1])
        return {"E0.06": "PASS"} if number == 1 else {f"P0.{number - 1:02d}": "PASS"}
    if step.startswith("P1."):
        number = int(step.split(".", 1)[1])
        if 1 <= number <= 41:
            return {"P0.34": "PASS"} if number == 1 else {f"P1.{number - 1:02d}": "PASS"}
    if step.startswith("P2."):
        number = int(step.split(".", 1)[1])
        if 1 <= number <= 24:
            return {"P1.41": "PASS"} if number == 1 else {f"P2.{number - 1:02d}": "PASS"}
    return {}


def source_state_unchanged(before, after) -> bool:
    return (
        before.source_commit == after.source_commit
        and before.toolchain_lock_sha256 == after.toolchain_lock_sha256
        and before.architecture_sha256 == after.architecture_sha256
        and after.worktree_clean
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="ZX-UX deterministic host build/test driver.")
    parser.add_argument("action", choices=("build", "test"))
    parser.add_argument("--step", required=True)
    parser.add_argument("--evidence-dir", help="external scratch evidence directory")
    parser.add_argument("--probe-root", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        root = find_root(Path(__file__))
        if args.probe_root:
            print(root)
            return 0
        source_state = require_clean_source(root)
        evidence_dir = resolve_evidence_dir(root, source_state.source_commit, args.evidence_dir)
        commands, hashes, assertions = dispatch(root, args.action, args.step)
        after = read_source_state(root)
        if not source_state_unchanged(source_state, after):
            raise DriverError("step changed the source checkout or certification inputs")
        failed_assertions = [item for item in assertions if item.get("passed") is not True]
        status = "PASS" if not failed_assertions else "FAIL"
        evidence_path = write_evidence(
            root,
            evidence_dir,
            source_state,
            args.step,
            args.action,
            status=status,
            prerequisites=prerequisite_statuses(args.step),
            commands=commands,
            hashes=hashes,
            assertions=assertions,
        )
        if failed_assertions:
            raise DriverError(f"{len(failed_assertions)} assertion(s) failed")
        print(f"ZX-UX {args.step} {args.action.upper()} PASS")
        print(f"evidence={evidence_path}")
        return 0
    except (DriverError, OSError, ValueError) as exc:
        print(f"ZX-UX TEST DRIVER FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
