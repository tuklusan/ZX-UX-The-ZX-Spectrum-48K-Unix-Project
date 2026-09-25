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

"""Generate and verify the real-time REV17 fast-loader acceptance trace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

DISPLAY_HOOK = 0x5E55
FINAL_HOLD = 0x5EB4
FINAL_RENDER_DONE = 0x5F59
PAUSE_ONE_SECOND = 0x5F39
STARTUP_BEEP = 0x5F2A
ROM_BEEPER = 0x03B5
HANDOFF = 0xE003
LINES_LEFT = 0x5EF7
LINE_INDEX = 0x5EF8
TEXT_PTR = 0x5EF5

M_ROM_BASIC = 0xA00001
M_ROM_LOAD = 0xA00002
M_HOOK = 0xA10001
M_HOLD = 0xA20001
M_RENDER_DONE = 0xA21001
M_RENDER_FRAME = 0xA21101
M_RENDER_ROW = 0xA22001
M_RENDER_ATTR = 0xA23001
M_RENDER_END = 0xA2FF01
M_BEEP = 0xA30001
M_BEEP_FRAME = 0xA31001
M_BEEPER = 0xA40001
M_E003 = 0xA50001
M_E003_ROW = 0xA51001
M_E003_ATTR = 0xA52001
M_E003_END = 0xA5FF01
M_TIMEOUT = 0xAF0001

ROW23 = [0x50E0 + scan * 0x100 + col for scan in range(8) for col in range(32)]
ATTR23 = list(range(0x5AE0, 0x5B00))


def _state_lines(marker: int) -> list[str]:
    return [
        f"print 0x{marker:x}",
        f"print [0x{LINES_LEFT:04x}]",
        f"print [0x{LINE_INDEX:04x}]",
        f"print [0x{TEXT_PTR:04x}]",
        f"print [0x{TEXT_PTR + 1:04x}]",
    ]


def _screen_dump(row_marker: int, attr_marker: int, end_marker: int) -> list[str]:
    out = [f"print 0x{row_marker:x}"]
    out.extend(f"print [0x{addr:04x}]" for addr in ROW23)
    out.append(f"print 0x{attr_marker:x}")
    out.extend(f"print [0x{addr:04x}]" for addr in ATTR23)
    out.append(f"print 0x{end_marker:x}")
    return out


def debugger_text() -> str:
    lines = [
        "base 16",
        "breakpoint 0x5ce7",
        "breakpoint 0x0556",
        f"breakpoint 0x{DISPLAY_HOOK:04x}",
        f"breakpoint 0x{FINAL_HOLD:04x}",
        f"breakpoint 0x{FINAL_RENDER_DONE:04x}",
        f"breakpoint 0x{STARTUP_BEEP:04x}",
        f"breakpoint 0x{ROM_BEEPER:04x} if [z80:sp] + 0x100 * [z80:sp+1] == 0x5f35",
        f"breakpoint 0x{HANDOFF:04x}",
        "breakpoint time 0 if spectrum:frames > 0x1964",
        "commands 1",
        f"print 0x{M_ROM_BASIC:x}",
        "continue",
        "end",
        "commands 2",
        f"print 0x{M_ROM_LOAD:x}",
        "continue",
        "end",
        "commands 3",
    ]
    lines.extend(_state_lines(M_HOOK))
    lines.extend(["continue", "end", "commands 4"])
    lines.extend(_state_lines(M_HOLD))
    lines.extend(["continue", "end", "commands 5"])
    lines.extend(_state_lines(M_RENDER_DONE))
    lines.extend([f"print 0x{M_RENDER_FRAME:x}", "print spectrum:frames"])
    lines.extend(_screen_dump(M_RENDER_ROW, M_RENDER_ATTR, M_RENDER_END))
    lines.extend(
        [
            "continue",
            "end",
            "commands 6",
            f"print 0x{M_BEEP:x}",
            f"print 0x{M_BEEP_FRAME:x}",
            "print spectrum:frames",
            "continue",
            "end",
        ]
    )
    lines.extend(
        [
            "commands 7",
            f"print 0x{M_BEEPER:x}",
            "print z80:de",
            "print z80:hl",
            "print z80:sp",
            "print [z80:sp]",
            "print [z80:sp+1]",
            "continue",
            "end",
            "commands 8",
        ]
    )
    lines.extend(_state_lines(M_E003))
    lines.extend(_screen_dump(M_E003_ROW, M_E003_ATTR, M_E003_END))
    lines.extend(
        [
            "exit 0",
            "end",
            "commands 9",
            f"print 0x{M_TIMEOUT:x}",
            "print z80:pc",
            "print spectrum:frames",
            "exit 3",
            "end",
            "continue",
        ]
    )
    return "\n".join(lines) + "\n"


def debugger_text_minimal() -> str:
    """Trace the user-facing loader path without inter-block hook breakpoints."""

    lines = [
        "base 16",
        "breakpoint 0x5ce7",
        "breakpoint 0x0556",
        f"breakpoint 0x{FINAL_HOLD:04x}",
        f"breakpoint 0x{FINAL_RENDER_DONE:04x}",
        f"breakpoint 0x{STARTUP_BEEP:04x}",
        f"breakpoint 0x{ROM_BEEPER:04x} if [z80:sp] + 0x100 * [z80:sp+1] == 0x5f35",
        f"breakpoint 0x{HANDOFF:04x}",
        "breakpoint time 0 if spectrum:frames > 0x1964",
        "commands 1",
        f"print 0x{M_ROM_BASIC:x}",
        "continue",
        "end",
        "commands 2",
        f"print 0x{M_ROM_LOAD:x}",
        "continue",
        "end",
        "commands 3",
    ]
    lines.extend(_state_lines(M_HOLD))
    lines.extend(["continue", "end", "commands 4"])
    lines.extend(_state_lines(M_RENDER_DONE))
    lines.extend([f"print 0x{M_RENDER_FRAME:x}", "print spectrum:frames"])
    lines.extend(_screen_dump(M_RENDER_ROW, M_RENDER_ATTR, M_RENDER_END))
    lines.extend(
        [
            "continue",
            "end",
            "commands 5",
            f"print 0x{M_BEEP:x}",
            f"print 0x{M_BEEP_FRAME:x}",
            "print spectrum:frames",
            "continue",
            "end",
            "commands 6",
            f"print 0x{M_BEEPER:x}",
            "print z80:de",
            "print z80:hl",
            "print z80:sp",
            "print [z80:sp]",
            "print [z80:sp+1]",
            "continue",
            "end",
            "commands 7",
        ]
    )
    lines.extend(_state_lines(M_E003))
    lines.extend(_screen_dump(M_E003_ROW, M_E003_ATTR, M_E003_END))
    lines.extend(
        [
            "exit 0",
            "end",
            "commands 8",
            f"print 0x{M_TIMEOUT:x}",
            "print z80:pc",
            "print spectrum:frames",
            "exit 3",
            "end",
            "continue",
        ]
    )
    return "\n".join(lines) + "\n"


def _values(path: Path) -> list[int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]+)", text)]


def _indices(values: list[int], marker: int) -> list[int]:
    return [i for i, value in enumerate(values) if value == marker]


def _unique(values: list[int], marker: int) -> int:
    found = _indices(values, marker)
    if len(found) != 1:
        raise ValueError(f"marker {marker:#x} count={len(found)}")
    return found[0]


def _state(values: list[int], marker: int, occurrence: int = 0) -> tuple[int, int, int, int]:
    found = _indices(values, marker)
    if occurrence >= len(found):
        raise ValueError(f"marker {marker:#x} occurrence {occurrence} missing")
    i = found[occurrence]
    return values[i + 1], values[i + 2], values[i + 3] | (values[i + 4] << 8), i


def _dump(values: list[int], start_marker: int, next_marker: int, expected: int) -> list[int]:
    a = _unique(values, start_marker)
    b = _unique(values, next_marker)
    result = values[a + 1:b]
    if len(result) != expected:
        raise ValueError(f"dump {start_marker:#x} length={len(result)} expected={expected}")
    return result


def verify(log: Path, rom_path: Path, text_path: Path) -> dict:
    values = _values(log)
    hook_hits = _indices(values, M_HOOK)
    hooks = [_state(values, M_HOOK, i) for i in range(len(hook_hits))]
    hook_states = [(left, line, ptr) for left, line, ptr, _ in hooks]

    hold_left, hold_line, hold_ptr, hold_index = _state(values, M_HOLD)
    done_left, done_line, done_ptr, done_index = _state(values, M_RENDER_DONE)
    e003_left, e003_line, e003_ptr, e003_index = _state(values, M_E003)
    beep_index = _unique(values, M_BEEP)
    beeper_index = _unique(values, M_BEEPER)
    render_frame_index = _unique(values, M_RENDER_FRAME)
    beep_frame_index = _unique(values, M_BEEP_FRAME)
    render_done_frame = values[render_frame_index + 1]
    beep_frame = values[beep_frame_index + 1]
    pause_frames = beep_frame - render_done_frame

    rom_basic_hits = len(_indices(values, M_ROM_BASIC))
    rom_load_hits = len(_indices(values, M_ROM_LOAD))
    timeout_hits = len(_indices(values, M_TIMEOUT))

    beeper_meta = values[beeper_index + 1:beeper_index + 6]
    if len(beeper_meta) != 5:
        raise ValueError("ROM BEEPER metadata truncated")
    de, hl, sp, ret_lo, ret_hi = beeper_meta
    return_addr = ret_lo | (ret_hi << 8)

    final_row = _dump(values, M_RENDER_ROW, M_RENDER_ATTR, 256)
    final_attr = _dump(values, M_RENDER_ATTR, M_RENDER_END, 32)
    e003_row = _dump(values, M_E003_ROW, M_E003_ATTR, 256)
    e003_attr = _dump(values, M_E003_ATTR, M_E003_END, 32)

    lines = text_path.read_text(encoding="ascii").splitlines()
    if len(lines) != 24 or any(len(line) != 32 for line in lines):
        raise ValueError("text-lines.txt is not exactly 24x32")
    final_line = lines[-1]
    rom = rom_path.read_bytes()
    if len(rom) != 16384:
        raise ValueError("48K ROM must be exactly 16384 bytes")
    expected_row = [
        rom[0x3C00 + ord(ch) * 8 + scan]
        for scan in range(8)
        for ch in final_line
    ]
    expected_attr = [0x07] * 32

    hook_trace_present = bool(hooks)
    if hook_trace_present:
        first_ptr = hook_states[0][2]
        expected_hook_states = [(24 - i, i, first_ptr + 32 * i) for i in range(len(hooks))]
        hook_trace_valid = (
            1 <= len(hooks) <= 24
            and hook_states == expected_hook_states
        )
    else:
        first_ptr = done_ptr - 24 * 32
        expected_hook_states = []
        hook_trace_valid = True

    finalizer_entry_valid = (
        0 <= hold_line <= 24
        and hold_left == 24 - hold_line
        and hold_ptr == first_ptr + 32 * hold_line
        and (not hook_trace_present or hold_line == len(hooks))
    )
    order = ([hooks[-1][3]] if hook_trace_present else []) + [
        hold_index,
        done_index,
        beep_index,
        beeper_index,
        e003_index,
    ]

    assertions = {
        "real_rom_basic_path_seen": rom_basic_hits >= 1,
        "real_rom_ld_bytes_seen": rom_load_hits >= 1,
        "no_timeout": timeout_hits == 0,
        "interblock_display_callback_count_valid": (not hook_trace_present) or 1 <= len(hooks) <= 24,
        "interblock_display_callback_state_sequence": hook_trace_valid,
        "finalizer_entered_with_consistent_pending_rows": finalizer_entry_valid,
        "finalizer_completed_row_24": (
            done_left == 0 and done_line == 24 and done_ptr == first_ptr + 24 * 32
        ),
        "final_row_rendered_before_beep": final_row == expected_row,
        "final_row_attributes_correct_before_beep": final_attr == expected_attr,
        "one_second_final_row_hold_before_beep": 59 <= pause_frames <= 63,
        "startup_beep_reached_once": len(_indices(values, M_BEEP)) == 1,
        "rom_beeper_reached_once": len(_indices(values, M_BEEPER)) == 1,
        "rom_beeper_parameters_exact": de == 224 and hl == 458,
        "rom_beeper_returns_to_startup_beep": return_addr == 0x5F35,
        "handoff_reached_once": len(_indices(values, M_E003)) == 1,
        "handoff_state_complete": (
            e003_left == 0 and e003_line == 24 and e003_ptr == first_ptr + 24 * 32
        ),
        "final_row_intact_at_handoff": e003_row == expected_row,
        "final_row_attributes_intact_at_handoff": e003_attr == expected_attr,
        "ordered_final_path": order == sorted(order),
    }
    report = {
        "schema": 4,
        "hook_trace_present": hook_trace_present,
        "hook_count": len(hooks),
        "hook_states": [
            {"lines_left": left, "line_index": line, "text_ptr": ptr}
            for left, line, ptr in hook_states
        ],
        "final_hold": {
            "lines_left": hold_left,
            "line_index": hold_line,
            "text_ptr": hold_ptr,
        },
        "final_render_done": {
            "lines_left": done_left,
            "line_index": done_line,
            "text_ptr": done_ptr,
        },
        "pre_beep_pause": {
            "routine_address": PAUSE_ONE_SECOND,
            "nominal_tstates": 3500009,
            "render_done_frame": render_done_frame,
            "beep_frame": beep_frame,
            "frames": pause_frames,
        },
        "rom_beeper": {
            "de": de,
            "hl": hl,
            "sp": sp,
            "return_address": return_addr,
        },
        "handoff": {
            "address": HANDOFF,
            "lines_left": e003_left,
            "line_index": e003_line,
            "text_ptr": e003_ptr,
        },
        "expected_final_line": final_line,
        "assertions": {name: "PASS" if ok else "FAIL" for name, ok in assertions.items()},
    }
    if not all(assertions.values()):
        failed = [name for name, ok in assertions.items() if not ok]
        diagnostics = {
            "hook_count": len(hooks),
            "hook_states": hook_states,
            "final_hold": [hold_left, hold_line, hold_ptr],
            "final_render_done": [done_left, done_line, done_ptr],
            "render_done_frame": render_done_frame,
            "beep_frame": beep_frame,
            "pause_frames": pause_frames,
        }
        raise ValueError(
            "runtime acceptance failed: "
            + ", ".join(failed)
            + "; diagnostics="
            + json.dumps(diagnostics, sort_keys=True)
        )
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)

    dbg = sub.add_parser("debugger")
    dbg.add_argument("--output", type=Path, required=True)
    dbg.add_argument("--omit-hook-trace", action="store_true")

    check = sub.add_parser("verify")
    check.add_argument("--log", type=Path, required=True)
    check.add_argument("--rom", type=Path, required=True)
    check.add_argument("--text", type=Path, required=True)
    check.add_argument("--report", type=Path, required=True)

    args = ap.parse_args()
    if args.command == "debugger":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        text = debugger_text_minimal() if args.omit_hook_trace else debugger_text()
        args.output.write_text(text, encoding="ascii", newline="\n")
        return 0

    report = verify(args.log, args.rom, args.text)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("ZX-UX RELEASE TZX RUNTIME ACCEPTANCE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
