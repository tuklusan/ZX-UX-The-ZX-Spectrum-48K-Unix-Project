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

from pathlib import Path
import re
import sys

ROOT_MARKER = b"ZX-UX project root"
TARGET = Path("docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md")


class RepairError(RuntimeError):
    pass


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise RepairError("canonical project root not found")


def transition(text: str, old: str, new: str, label: str) -> str:
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        return text.replace(old, new, 1)
    if old_count == 0 and new_count == 1:
        return text
    raise RepairError(
        f"{label}: expected exactly one legacy or repaired form; "
        f"legacy={old_count} repaired={new_count}"
    )


def repair(text: str) -> str:
    legacy_intro = """For every step below, evidence is retained at least as
`v1/dist/certification/<STEP-ID>.log` plus a machine-readable result/hash record when
the step is a certification boundary. `v1/build` is disposable; `v1/dist` is not."""
    canonical_intro = """For every numbered E0 and Phase-0 step, clean-source certification writes scratch
records outside the source worktree. After a complete pass, exact staged bytes are
admitted to `v1/dist/certification/` in an evidence-only check-in. Every such step
requires `<STEP-ID>.build.json` and `<STEP-ID>.test.json`. E0.04 and P0.34 are
explicit certification-result boundaries and additionally require
`<STEP-ID>.result.json`; Phase 0 also requires `phase-0.json`. Human-readable `.log`
files are required only when a step explicitly calls for a transcript and are not a
universal evidence format. Every durable build/test/result record identifies the exact
certified source commit, toolchain-lock SHA-256, architecture SHA-256, clean-worktree
state, prerequisite status, stable root-relative artifact hashes, command data, and
named assertions. `v1/build` is disposable; `v1/dist` is not."""
    text = transition(text, legacy_intro, canonical_intro, "evidence doctrine")

    for step in ("E0.01", "E0.02"):
        old = (
            f"11. **Evidence:** Retain the {step} build/test certification record under "
            "`v1/dist/certification/` according to the repository evidence contract."
        )
        new = (
            f"11. **Evidence:** Retain `v1/dist/certification/{step}.build.json` and "
            f"`v1/dist/certification/{step}.test.json` under the repository evidence contract."
        )
        text = transition(text, old, new, f"{step} evidence naming")

    old_line = re.compile(
        r"11\. \*\*Evidence:\*\* `v1/dist/certification/((?:E0|P[0-9]+)\.[0-9]{2})\.log` "
        r"plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates\."
    )

    def replace_line(match: re.Match[str]) -> str:
        step = match.group(1)
        return (
            f"11. **Evidence:** Retain `v1/dist/certification/{step}.build.json` and "
            f"`v1/dist/certification/{step}.test.json`; add "
            f"`v1/dist/certification/{step}.result.json` only when this step is explicitly "
            "designated a certification-result boundary; phase aggregate evidence is retained "
            "at the phase gate."
        )

    text = old_line.sub(replace_line, text)

    for step, aggregate in (("E0.04", ""), ("P0.34", " and the Phase-0 aggregate `v1/dist/certification/phase-0.json`")):
        generic = (
            f"11. **Evidence:** Retain `v1/dist/certification/{step}.build.json` and "
            f"`v1/dist/certification/{step}.test.json`; add "
            f"`v1/dist/certification/{step}.result.json` only when this step is explicitly "
            "designated a certification-result boundary; phase aggregate evidence is retained "
            "at the phase gate."
        )
        boundary = (
            f"11. **Evidence:** Retain `v1/dist/certification/{step}.build.json`, "
            f"`v1/dist/certification/{step}.test.json`, and the required certification-boundary "
            f"record `v1/dist/certification/{step}.result.json`{aggregate}."
        )
        text = transition(text, generic, boundary, f"{step} result boundary")

    required_steps = [f"E0.{n:02d}" for n in range(1, 7)] + [f"P0.{n:02d}" for n in range(1, 35)]
    for step in required_steps:
        for suffix in ("build.json", "test.json"):
            token = f"v1/dist/certification/{step}.{suffix}"
            if token not in text:
                raise RepairError(f"missing canonical evidence name: {token}")

    required_tokens = (
        "<STEP-ID>.build.json",
        "<STEP-ID>.test.json",
        "E0.04.result.json",
        "P0.34.result.json",
        "phase-0.json",
        "clean-worktree",
    )
    for token in required_tokens:
        if token not in text:
            raise RepairError(f"missing evidence-contract token: {token}")
    if old_line.search(text) or "<STEP-ID>.log` plus a machine-readable" in text:
        raise RepairError("legacy universal .log evidence contract remains")
    return text


def main() -> int:
    try:
        root = find_root(Path(__file__).resolve())
        target = root / TARGET
        if not target.is_file() or target.is_symlink():
            raise RepairError(f"target is not a regular file: {TARGET}")
        original = target.read_text(encoding="utf-8")
        repaired = repair(original)
        target.write_text(repaired, encoding="utf-8", newline="\n")
        print(f"repaired={TARGET}")
        return 0
    except (OSError, RepairError, ValueError) as exc:
        print(f"ZX-UX EVIDENCE CONTRACT REPAIR FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
