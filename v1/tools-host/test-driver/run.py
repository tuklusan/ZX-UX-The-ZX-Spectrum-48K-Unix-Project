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
import json
import os
from pathlib import Path
import subprocess
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
import phase2_two_base_relocatable
import phase2_acceptance
import revision16_bridge
import phase3_open_descriptions
import phase3_handle_table
import phase3_tty
import phase3_null
import phase3_close
import phase3_dup
import phase3_independent_open
import phase3_pipe_create
import phase3_pipe_read
import phase3_pipe_blocking
import phase3_pipe_write
import phase3_pipe_full
import phase3_pipe_broken
import phase3_pipe_lifetime
import phase3_rw_validation
import phase3_allow_tape
import phase3_pipe2
import phase3_pipe3
import phase3_widened_ranges
import phase3_ioctl
import phase3_acceptance
import phase4_namespace
import phase4_names
import phase4_records
import phase4_types
import phase4_open
import phase4_exclusive
import phase4_raw_read
import phase4_raw_write
import phase4_append
import phase4_trunc
import phase4_stat
import phase4_list
import phase4_remove
import phase4_rename
import phase4_rename_replace
import phase4_zxpack_decoder
import phase4_packed_state
import phase4_packed_seek
import phase4_packed_write
import phase4_target_encoder
import phase4_raw_retention
import phase4_sys_pack
import phase4_sys_unpack
import phase4_close_candidates
import phase4_idle_pack
import phase4_compaction
import phase4_packed_spawn
import phase4_zxpack_info
import phase4_compression_regression
import phase4_pseudo_dirs
import phase4_chdir
import phase4_getcwd
import phase4_acceptance
import phase5_m48o_header
import phase5_crc16
import phase5_chunk_framing
import phase5_raw_loader
import phase5_packed_loader
import phase5_bootstrap_resources
import phase5_raw_save
import phase5_streaming_save
import phase5_explicit_load
import phase5_verify
import phase5_tape_scan
import phase5_tape_lock
import phase5_tape_prompts
import phase5_direct_mex1
import phase5_fixture_tape
import phase5_roundtrip
import phase5_tape_recovery
import phase5_second_emulator
import phase5_acceptance
import phase6_pid1
import phase6_issue
import phase6_login
import phase6_home
import phase6_env
import phase6_set_unset
import phase6_line
import phase6_tokenizer
import phase6_expansion
import phase6_operators
import phase6_binding
import phase6_bounds
import phase6_builtins
import phase6_path
import phase6_tape_discovery
import phase6_echo
import phase6_builtin_redir
import phase6_external_redir
import phase6_sequence
import phase6_logic
import phase6_pipeline
import phase6_tty_owner
import phase6_background
import phase6_jobs
import phase6_wait
import phase6_kill_break
import phase6_cursor_restore
# Phase-3 current-head certification dispatch remains intentionally runner-visible.
from media_retention import (
    capture_project_media,
    configure_media_stage,
    write_action_manifest,
)
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
    if step == "R16.00":
        return revision16_bridge.dispatch(root, action, step, **kwargs)
    if step == "P3.01":
        return phase3_open_descriptions.dispatch(root, action, step, **kwargs)
    if step == "P3.02":
        return phase3_handle_table.dispatch(root, action, step, **kwargs)
    if step == "P3.03":
        return phase3_tty.dispatch(root, action, step, **kwargs)
    if step == "P3.04":
        return phase3_null.dispatch(root, action, step, **kwargs)
    if step == "P3.05":
        return phase3_close.dispatch(root, action, step, **kwargs)
    if step == "P3.06":
        return phase3_dup.dispatch(root, action, step, **kwargs)
    if step == "P3.07":
        return phase3_independent_open.dispatch(root, action, step, **kwargs)
    if step == "P3.08":
        return phase3_pipe_create.dispatch(root, action, step, **kwargs)
    if step == "P3.09":
        return phase3_pipe_read.dispatch(root, action, step, **kwargs)
    if step == "P3.10":
        return phase3_pipe_blocking.dispatch(root, action, step, **kwargs)
    if step == "P3.11":
        return phase3_pipe_write.dispatch(root, action, step, **kwargs)
    if step == "P3.12":
        return phase3_pipe_full.dispatch(root, action, step, **kwargs)
    if step == "P3.13":
        return phase3_pipe_broken.dispatch(root, action, step, **kwargs)
    if step == "P3.14":
        return phase3_pipe_lifetime.dispatch(root, action, step, **kwargs)
    if step == "P3.15":
        return phase3_rw_validation.dispatch(root, action, step, **kwargs)
    if step == "P3.16":
        return phase3_allow_tape.dispatch(root, action, step, **kwargs)
    if step == "P3.17":
        return phase3_pipe2.dispatch(root, action, step, **kwargs)
    if step == "P3.18":
        return phase3_pipe3.dispatch(root, action, step, **kwargs)
    if step == "P3.19":
        return phase3_widened_ranges.dispatch(root, action, step, **kwargs)
    if step == "P3.20":
        return phase3_ioctl.dispatch(root, action, step, **kwargs)
    if step == "P3.21":
        return phase3_acceptance.dispatch(root, action, step, **kwargs)
    if step == "P4.01":
        return phase4_namespace.dispatch(root, action, step, **kwargs)
    if step == "P4.02":
        return phase4_names.dispatch(root, action, step, **kwargs)
    if step == "P4.03":
        return phase4_records.dispatch(root, action, step, **kwargs)
    if step == "P4.04":
        return phase4_types.dispatch(root, action, step, **kwargs)
    if step == "P4.05":
        return phase4_open.dispatch(root, action, step, **kwargs)
    if step == "P4.06":
        return phase4_exclusive.dispatch(root, action, step, **kwargs)
    if step == "P4.07":
        return phase4_raw_read.dispatch(root, action, step, **kwargs)
    if step == "P4.08":
        return phase4_raw_write.dispatch(root, action, step, **kwargs)
    if step == "P4.09":
        return phase4_append.dispatch(root, action, step, **kwargs)
    if step == "P4.10":
        return phase4_trunc.dispatch(root, action, step, **kwargs)
    if step == "P4.11":
        return phase4_stat.dispatch(root, action, step, **kwargs)
    if step == "P4.12":
        return phase4_list.dispatch(root, action, step, **kwargs)
    if step == "P4.13":
        return phase4_remove.dispatch(root, action, step, **kwargs)
    if step == "P4.14":
        return phase4_rename.dispatch(root, action, step, **kwargs)
    if step == "P4.15":
        return phase4_rename_replace.dispatch(root, action, step, **kwargs)
    if step == "P4.16":
        return phase4_zxpack_decoder.dispatch(root, action, step, **kwargs)
    if step == "P4.17":
        return phase4_packed_state.dispatch(root, action, step, **kwargs)
    if step == "P4.18":
        return phase4_packed_seek.dispatch(root, action, step, **kwargs)
    if step == "P4.19":
        return phase4_packed_write.dispatch(root, action, step, **kwargs)
    if step == "P4.20":
        return phase4_target_encoder.dispatch(root, action, step, **kwargs)
    if step == "P4.21":
        return phase4_raw_retention.dispatch(root, action, step, **kwargs)
    if step == "P4.22":
        return phase4_sys_pack.dispatch(root, action, step, **kwargs)
    if step == "P4.23":
        return phase4_sys_unpack.dispatch(root, action, step, **kwargs)
    if step == "P4.24":
        return phase4_close_candidates.dispatch(root, action, step, **kwargs)
    if step == "P4.25":
        return phase4_idle_pack.dispatch(root, action, step, **kwargs)
    if step == "P4.26":
        return phase4_compaction.dispatch(root, action, step, **kwargs)
    if step == "P4.27":
        return phase4_packed_spawn.dispatch(root, action, step, **kwargs)
    if step == "P4.28":
        return phase4_zxpack_info.dispatch(root, action, step, **kwargs)
    if step == "P4.29":
        return phase4_compression_regression.dispatch(root, action, step, **kwargs)
    if step == "P4.30":
        return phase4_pseudo_dirs.dispatch(root, action, step, **kwargs)
    if step == "P4.31":
        return phase4_chdir.dispatch(root, action, step, **kwargs)
    if step == "P4.32":
        return phase4_getcwd.dispatch(root, action, step, **kwargs)
    if step == "P4.33":
        return phase4_acceptance.dispatch(root, action, step, **kwargs)
    if step.startswith("P4."):
        raise DriverError(f"numbered Phase-4 step is not registered: {step}")
    if step == "P5.01":
        return phase5_m48o_header.dispatch(root, action, step, **kwargs)
    if step == "P5.02":
        return phase5_crc16.dispatch(root, action, step, **kwargs)
    if step == "P5.03":
        return phase5_chunk_framing.dispatch(root, action, step, **kwargs)
    if step == "P5.04":
        return phase5_raw_loader.dispatch(root, action, step, **kwargs)
    if step == "P5.05":
        return phase5_packed_loader.dispatch(root, action, step, **kwargs)
    if step == "P5.06":
        return phase5_bootstrap_resources.dispatch(root, action, step, **kwargs)
    if step == "P5.07":
        return phase5_raw_save.dispatch(root, action, step, **kwargs)
    if step == "P5.08":
        return phase5_streaming_save.dispatch(root, action, step, **kwargs)
    if step == "P5.09":
        return phase5_explicit_load.dispatch(root, action, step, **kwargs)
    if step == "P5.10":
        return phase5_verify.dispatch(root, action, step, **kwargs)
    if step == "P5.11":
        return phase5_tape_scan.dispatch(root, action, step, **kwargs)
    if step == "P5.12":
        return phase5_tape_lock.dispatch(root, action, step, **kwargs)
    if step == "P5.13":
        return phase5_tape_prompts.dispatch(root, action, step, **kwargs)
    if step == "P5.14":
        return phase5_direct_mex1.dispatch(root, action, step, **kwargs)
    if step == "P5.15":
        return phase5_fixture_tape.dispatch(root, action, step, **kwargs)
    if step == "P5.16":
        return phase5_roundtrip.dispatch(root, action, step, **kwargs)
    if step == "P5.17":
        return phase5_tape_recovery.dispatch(root, action, step, **kwargs)
    if step == "P5.18":
        return phase5_second_emulator.dispatch(root, action, step, **kwargs)
    if step == "P5.19":
        return phase5_acceptance.dispatch(root, action, step, **kwargs)
    if step.startswith("P5."):
        raise DriverError(f"numbered Phase-5 step is not registered: {step}")
    if step == "P6.01":
        return phase6_pid1.dispatch(root, action, step, **kwargs)
    if step == "P6.02":
        return phase6_issue.dispatch(root, action, step, **kwargs)
    if step == "P6.03":
        return phase6_login.dispatch(root, action, step, **kwargs)
    if step == "P6.04":
        return phase6_home.dispatch(root, action, step, **kwargs)
    if step == "P6.05":
        return phase6_env.dispatch(root, action, step, **kwargs)
    if step == "P6.06":
        return phase6_set_unset.dispatch(root, action, step, **kwargs)
    if step == "P6.07":
        return phase6_line.dispatch(root, action, step, **kwargs)
    if step == "P6.08":
        return phase6_tokenizer.dispatch(root, action, step, **kwargs)
    if step == "P6.09":
        return phase6_expansion.dispatch(root, action, step, **kwargs)
    if step == "P6.10":
        return phase6_operators.dispatch(root, action, step, **kwargs)
    if step == "P6.11":
        return phase6_binding.dispatch(root, action, step, **kwargs)
    if step == "P6.12":
        return phase6_bounds.dispatch(root, action, step, **kwargs)
    if step == "P6.13":
        return phase6_builtins.dispatch(root, action, step, **kwargs)
    if step == "P6.14":
        return phase6_path.dispatch(root, action, step, **kwargs)
    if step == "P6.15":
        return phase6_tape_discovery.dispatch(root, action, step, **kwargs)
    if step == "P6.16":
        return phase6_echo.dispatch(root, action, step, **kwargs)
    if step == "P6.17":
        return phase6_builtin_redir.dispatch(root, action, step, **kwargs)
    if step == "P6.18":
        return phase6_external_redir.dispatch(root, action, step, **kwargs)
    if step == "P6.19":
        return phase6_sequence.dispatch(root, action, step, **kwargs)
    if step == "P6.20":
        return phase6_logic.dispatch(root, action, step, **kwargs)
    if step == "P6.21":
        return phase6_pipeline.dispatch(root, action, step, **kwargs)
    if step == "P6.22":
        return phase6_tty_owner.dispatch(root, action, step, **kwargs)
    if step == "P6.23":
        return phase6_background.dispatch(root, action, step, **kwargs)
    if step == "P6.24":
        return phase6_jobs.dispatch(root, action, step, **kwargs)
    if step == "P6.25":
        return phase6_wait.dispatch(root, action, step, **kwargs)
    if step == "P6.26":
        return phase6_kill_break.dispatch(root, action, step, **kwargs)
    if step == "P6.27":
        return phase6_cursor_restore.dispatch(root, action, step, **kwargs)
    if step.startswith("P6."):
        raise DriverError(f"numbered Phase-6 step is not registered: {step}")
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
    if step == "P2.23":
        return phase2_two_base_relocatable.dispatch(root, action, step, **kwargs)
    if step == "P2.24":
        return phase2_acceptance.dispatch(root, action, step, **kwargs)
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
    if step == "R16.00":
        return {"P2.24": "PASS"}
    if step.startswith("P3."):
        number = int(step.split(".", 1)[1])
        if 1 <= number:
            return {"R16.00": "PASS"} if number == 1 else {f"P3.{number - 1:02d}": "PASS"}
    if step.startswith("P4."):
        number = int(step.split(".", 1)[1])
        if 1 <= number:
            return {"P3.21": "PASS"} if number == 1 else {f"P4.{number - 1:02d}": "PASS"}
    if step.startswith("P5."):
        number = int(step.split(".", 1)[1])
        if 1 <= number:
            return {"P4.33": "PASS"} if number == 1 else {f"P5.{number - 1:02d}": "PASS"}
    if step.startswith("P6."):
        number = int(step.split(".", 1)[1])
        if 1 <= number:
            return {"P5.19": "PASS"} if number == 1 else {f"P6.{number - 1:02d}": "PASS"}
    return {}


def source_state_unchanged(before, after) -> bool:
    return (
        before.source_commit == after.source_commit
        and before.toolchain_lock_sha256 == after.toolchain_lock_sha256
        and before.architecture_sha256 == after.architecture_sha256
        and before.implementation_plan_sha256 == after.implementation_plan_sha256
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
        if args.step.startswith(("E0.", "P0.", "P1.", "P2.")):
            os.environ["ZXUX_SOURCE_EPOCH"] = "historical"
        else:
            os.environ.pop("ZXUX_SOURCE_EPOCH", None)
        source_state = require_clean_source(root)
        evidence_dir = resolve_evidence_dir(root, source_state.source_commit, args.evidence_dir)
        configure_media_stage(evidence_dir, args.step, args.action)
        commands, hashes, assertions = dispatch(root, args.action, args.step)
        capture_project_media(root)
        write_action_manifest(source_state.source_commit)
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
        if args.step == "P4.33" and args.action == "test":
            build_path = evidence_dir / "P4.33.build.json"
            if not build_path.is_file():
                raise DriverError("P4.33 result requires matching build evidence")
            build_record = json.loads(build_path.read_text(encoding="utf-8"))
            test_record = json.loads(evidence_path.read_text(encoding="utf-8"))
            for record in (build_record, test_record):
                if record.get("status") != "PASS" or record.get("source_commit") != source_state.source_commit:
                    raise DriverError("P4.33 source-candidate mismatch")
                if record.get("architecture_sha256") != source_state.architecture_sha256:
                    raise DriverError("P4.33 architecture identity mismatch")
                if record.get("implementation_plan_sha256") != source_state.implementation_plan_sha256:
                    raise DriverError("P4.33 plan identity mismatch")
            result = {
                "schema": 2, "step": "P4.33", "action": "result", "status": "PASS",
                "pass_marker": phase4_acceptance.PASS_MARKER,
                "source_commit": source_state.source_commit,
                "toolchain_lock_sha256": source_state.toolchain_lock_sha256,
                "architecture_sha256": source_state.architecture_sha256,
                "implementation_plan_sha256": source_state.implementation_plan_sha256,
                "worktree_clean": True, "prerequisites": {"P4.32": "PASS"},
                "commands": test_record["commands"], "hashes": test_record["hashes"],
                "assertions": test_record["assertions"] + [
                    {"name":"same-clean-phase4-aggregate-source-candidate-all-records","passed":True}
                ],
            }
            result_path = evidence_dir / "P4.33.result.json"
            result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            print(phase4_acceptance.PASS_MARKER)
            print(f"result={result_path}")
        if args.step == "P3.21" and args.action == "test":
            build_path = evidence_dir / "P3.21.build.json"
            if not build_path.is_file():
                raise DriverError("P3.21 result requires matching build evidence")
            build_record = json.loads(build_path.read_text(encoding="utf-8"))
            test_record = json.loads(evidence_path.read_text(encoding="utf-8"))
            for record in (build_record, test_record):
                if record.get("status") != "PASS" or record.get("source_commit") != source_state.source_commit:
                    raise DriverError("P3.21 source-candidate mismatch")
                if record.get("architecture_sha256") != source_state.architecture_sha256:
                    raise DriverError("P3.21 architecture identity mismatch")
                if record.get("implementation_plan_sha256") != source_state.implementation_plan_sha256:
                    raise DriverError("P3.21 plan identity mismatch")
            result = {
                "schema": 2, "step": "P3.21", "action": "result", "status": "PASS",
                "pass_marker": phase3_acceptance.PASS_MARKER,
                "source_commit": source_state.source_commit,
                "toolchain_lock_sha256": source_state.toolchain_lock_sha256,
                "architecture_sha256": source_state.architecture_sha256,
                "implementation_plan_sha256": source_state.implementation_plan_sha256,
                "worktree_clean": True, "prerequisites": {"P3.20": "PASS"},
                "commands": test_record["commands"], "hashes": test_record["hashes"],
                "assertions": test_record["assertions"] + [
                    {"name":"same-clean-phase3-aggregate-source-candidate-all-records","passed":True}
                ],
            }
            result_path = evidence_dir / "P3.21.result.json"
            result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            print(phase3_acceptance.PASS_MARKER)
            print(f"result={result_path}")
        if args.step == "R16.00" and args.action == "test":
            build_path = evidence_dir / "R16.00.build.json"
            if not build_path.is_file():
                raise DriverError("R16.00 result requires matching build evidence")
            build_record = json.loads(build_path.read_text(encoding="utf-8"))
            test_record = json.loads(evidence_path.read_text(encoding="utf-8"))
            for record in (build_record, test_record):
                if record.get("status") != "PASS" or record.get("source_commit") != source_state.source_commit:
                    raise DriverError("R16.00 source-candidate mismatch")
                if record.get("implementation_plan_sha256") != source_state.implementation_plan_sha256:
                    raise DriverError("R16.00 plan identity mismatch")
            result = {
                "schema": 2, "step": "R16.00", "action": "result", "status": "PASS",
                "pass_marker": revision16_bridge.PASS_MARKER,
                "source_commit": source_state.source_commit, "bridge_source_commit": source_state.source_commit,
                "toolchain_lock_sha256": source_state.toolchain_lock_sha256,
                "architecture_sha256": source_state.architecture_sha256,
                "implementation_plan_sha256": source_state.implementation_plan_sha256,
                "worktree_clean": True, "prerequisites": {"P2.24": "PASS"},
                "commands": test_record["commands"], "hashes": test_record["hashes"],
                "assertions": test_record["assertions"] + [{"name":"same-clean-bridge-source-candidate-all-records","passed":True}],
            }
            result_path = evidence_dir / "R16.00.result.json"
            result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            print(revision16_bridge.PASS_MARKER)
            print(f"result={result_path}")
        print(f"ZX-UX {args.step} {args.action.upper()} PASS")
        print(f"evidence={evidence_path}")
        if (
            args.step == "P2.24"
            and args.action == "test"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("ZXUX_R16_NESTED") != "1"
            and not (root / "v1/dist/certification/R16.00.result.json").is_file()
        ):
            os.environ["ZXUX_R16_NESTED"] = "1"
            for bridge_action in ("build", "test"):
                bridge_cmd = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    bridge_action,
                    "--step", "R16.00",
                    "--evidence-dir", str(evidence_dir),
                ]
                completed = subprocess.run(bridge_cmd, cwd=root, check=False, text=True, capture_output=True)
                sys.stdout.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                if completed.returncode != 0:
                    raise DriverError(f"R16.00 {bridge_action} runner transaction failed")
        if (
            args.step == "P2.24"
            and args.action == "test"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and (root / "v1/dist/certification/R16.00.result.json").is_file()
            and not (root / "v1/dist/certification/P3.01.test.json").is_file()
            and os.environ.get("ZXUX_P301_NESTED") != "1"
        ):
            os.environ["ZXUX_P301_NESTED"] = "1"
            for p3_action in ("build", "test"):
                p3_cmd = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    p3_action,
                    "--step", "P3.01",
                    "--evidence-dir", str(evidence_dir),
                ]
                completed = subprocess.run(p3_cmd, cwd=root, check=False, text=True, capture_output=True)
                sys.stdout.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                if completed.returncode != 0:
                    raise DriverError(f"P3.01 {p3_action} runner transaction failed")
        if (
            args.step == "P2.24"
            and args.action == "test"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and (root / "v1/dist/certification/P3.01.test.json").is_file()
            and not (root / "v1/dist/certification/P3.02.test.json").is_file()
            and os.environ.get("ZXUX_P302_NESTED") != "1"
        ):
            os.environ["ZXUX_P302_NESTED"] = "1"
            for p3_action in ("build", "test"):
                p3_cmd = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    p3_action,
                    "--step", "P3.02",
                    "--evidence-dir", str(evidence_dir),
                ]
                completed = subprocess.run(p3_cmd, cwd=root, check=False, text=True, capture_output=True)
                sys.stdout.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                if completed.returncode != 0:
                    raise DriverError(f"P3.02 {p3_action} runner transaction failed")
        if (
            args.step == "P2.24"
            and args.action == "test"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and (root / "v1/dist/certification/P3.02.test.json").is_file()
            and not (root / "v1/dist/certification/P3.03.test.json").is_file()
            and os.environ.get("ZXUX_P303_NESTED") != "1"
        ):
            os.environ["ZXUX_P303_NESTED"] = "1"
            for p3_action in ("build", "test"):
                p3_cmd = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    p3_action,
                    "--step", "P3.03",
                    "--evidence-dir", str(evidence_dir),
                ]
                completed = subprocess.run(p3_cmd, cwd=root, check=False, text=True, capture_output=True)
                sys.stdout.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                if completed.returncode != 0:
                    raise DriverError(f"P3.03 {p3_action} runner transaction failed")
        if (
            args.step == "P2.24"
            and args.action == "test"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and (root / "v1/dist/certification/P3.03.test.json").is_file()
            and not (root / "v1/dist/certification/P3.04.test.json").is_file()
            and os.environ.get("ZXUX_P304_NESTED") != "1"
        ):
            os.environ["ZXUX_P304_NESTED"] = "1"
            for p3_action in ("build", "test"):
                p3_cmd = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    p3_action,
                    "--step", "P3.04",
                    "--evidence-dir", str(evidence_dir),
                ]
                completed = subprocess.run(p3_cmd, cwd=root, check=False, text=True, capture_output=True)
                sys.stdout.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                if completed.returncode != 0:
                    raise DriverError(f"P3.04 {p3_action} runner transaction failed")
        if (
            args.step == "P2.24"
            and args.action == "test"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and (root / "v1/dist/certification/P3.04.test.json").is_file()
            and not (root / "v1/dist/certification/P3.05.test.json").is_file()
            and os.environ.get("ZXUX_P305_NESTED") != "1"
        ):
            os.environ["ZXUX_P305_NESTED"] = "1"
            for p3_action in ("build", "test"):
                p3_cmd = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    p3_action,
                    "--step", "P3.05",
                    "--evidence-dir", str(evidence_dir),
                ]
                completed = subprocess.run(p3_cmd, cwd=root, check=False, text=True, capture_output=True)
                sys.stdout.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                if completed.returncode != 0:
                    raise DriverError(f"P3.05 {p3_action} runner transaction failed")
        if (
            args.step == "P2.24"
            and args.action == "test"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and (root / "v1/dist/certification/P3.05.test.json").is_file()
            and not (root / "v1/dist/certification/P3.06.test.json").is_file()
            and os.environ.get("ZXUX_P306_NESTED") != "1"
        ):
            os.environ["ZXUX_P306_NESTED"] = "1"
            for p3_action in ("build", "test"):
                p3_cmd = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    p3_action,
                    "--step", "P3.06",
                    "--evidence-dir", str(evidence_dir),
                ]
                completed = subprocess.run(p3_cmd, cwd=root, check=False, text=True, capture_output=True)
                sys.stdout.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                if completed.returncode != 0:
                    raise DriverError(f"P3.06 {p3_action} runner transaction failed")
        if (
            args.step == "P2.24"
            and args.action == "test"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and (root / "v1/dist/certification/P3.06.test.json").is_file()
            and not (root / "v1/dist/certification/P3.07.test.json").is_file()
            and os.environ.get("ZXUX_P307_NESTED") != "1"
        ):
            os.environ["ZXUX_P307_NESTED"] = "1"
            for p3_action in ("build", "test"):
                p3_cmd = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    p3_action,
                    "--step", "P3.07",
                    "--evidence-dir", str(evidence_dir),
                ]
                completed = subprocess.run(p3_cmd, cwd=root, check=False, text=True, capture_output=True)
                sys.stdout.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                if completed.returncode != 0:
                    raise DriverError(f"P3.07 {p3_action} runner transaction failed")
        if (
            args.step == "P2.24"
            and args.action == "test"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and (root / "v1/dist/certification/P3.07.test.json").is_file()
            and not (root / "v1/dist/certification/P3.08.test.json").is_file()
            and os.environ.get("ZXUX_P308_NESTED") != "1"
        ):
            os.environ["ZXUX_P308_NESTED"] = "1"
            for p3_action in ("build", "test"):
                p3_cmd = [
                    str(Path(sys.executable).resolve()),
                    str(Path(__file__).resolve()),
                    p3_action,
                    "--step", "P3.08",
                    "--evidence-dir", str(evidence_dir),
                ]
                completed = subprocess.run(p3_cmd, cwd=root, check=False, text=True, capture_output=True)
                sys.stdout.write(completed.stdout)
                sys.stderr.write(completed.stderr)
                if completed.returncode != 0:
                    raise DriverError(f"P3.08 {p3_action} runner transaction failed")
        return 0
    except (DriverError, OSError, ValueError) as exc:
        print(f"ZX-UX TEST DRIVER FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
