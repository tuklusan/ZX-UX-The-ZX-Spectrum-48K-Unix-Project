#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SDK_VERSION = "0.9.0-dev"

from c48.errors import C48Error, RuntimeC48Error
from c48.format import read
from c48.gui import TkDisplay
from c48.screen import Font4x8, ZXScreen
from c48.vm import C48VM


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="c48run", description="Portable ZX-UX C48 host runtime")
    ap.add_argument("--version", action="version", version=f"%(prog)s {SDK_VERSION}")
    ap.add_argument(
        "--about",
        action="version",
        version=(
            f"%(prog)s {SDK_VERSION}\n"
            "ZX-UX C48 SDK\n"
            "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.\n"
            "Based on original work by Supratim Sanyal of SANYALnet Labs.\n"
            "SANYALnet Labs Non-Commercial License; see the root LICENSE file."
        ),
        help="show attribution and license information and exit",
    )
    ap.add_argument("program", help="C48B1 program path")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--headless", action="store_true", help="run without opening a display window")
    ap.add_argument("--dump-screen", type=Path, help="write exact 6912-byte ZX screen after execution")
    ap.add_argument("--ppm", type=Path, help="write a 256x192 PPM rendering after execution")
    ap.add_argument("--scale", type=int, default=3, choices=(1,2,3,4,5))
    ap.add_argument(
        "--font",
        type=Path,
        default=ROOT / "assets" / "font4x8-tasword.bin",
        metavar="PATH",
        help=(
            "F4X8 font resource to use for the ZX display "
            "(default: compiler/assets/font4x8-tasword.bin)"
        ),
    )
    ap.add_argument("--allow-approx-rom-math", action="store_true",
                    help="enable explicitly non-certified host approximations for transcendental ROM math")
    ap.add_argument("--heap", type=int, default=1024, metavar="BYTES",
                    help="host C48 heap reserve: even 0..8192 bytes (default: 1024)")
    ap.add_argument(
        "--max-steps", type=int, default=0, metavar="STEPS",
        help=(
            "deterministic VM safety budget; 0 means unlimited "
            "(default: 0)"
        ),
    )
    ns = ap.parse_args(argv)
    try:
        if ns.heap < 0 or ns.heap > 8192 or (ns.heap & 1):
            raise RuntimeC48Error("--heap must be an even value from 0..8192")
        if ns.max_steps < 0:
            raise RuntimeC48Error("--max-steps must be zero or positive")
        max_steps = None if ns.max_steps == 0 else ns.max_steps
        program_path = Path(ns.program)
        program = read(program_path)
        font = Font4x8.load(ns.font)
        screen = ZXScreen(font)
        # Preserve argv[0] as the exact host command token supplied for the program.
        pargv = [ns.program, *ns.args]
        if ns.headless:
            vm = C48VM(
                program, screen, argv=pargv,
                approximate_rom_math=ns.allow_approx_rom_math,
                heap_size=ns.heap, max_steps=max_steps,
            )
            status = vm.run()
        else:
            display = TkDisplay(screen, scale=ns.scale, title=f"ZX-UX C48 - {program_path.name}")
            vm = C48VM(
                program, screen, argv=pargv,
                approximate_rom_math=ns.allow_approx_rom_math,
                heap_size=ns.heap, max_steps=max_steps,
                input_provider=display.input_char,
                display_update=display.update,
            )
            status = display.run_vm(vm.run)
        if ns.dump_screen:
            ns.dump_screen.parent.mkdir(parents=True, exist_ok=True)
            ns.dump_screen.write_bytes(screen.bytes())
        if ns.ppm:
            ns.ppm.parent.mkdir(parents=True, exist_ok=True)
            screen.save_ppm(ns.ppm)
        return int(status) & 0xFF
    except MemoryError:
        print(
            "c48run: runtime error: host memory safety ceiling exceeded",
            file=sys.stderr,
        )
        return 1
    except RecursionError:
        print(
            "c48run: runtime error: host recursion safety ceiling exceeded",
            file=sys.stderr,
        )
        return 1
    except (C48Error, RuntimeError, OSError, ValueError) as exc:
        print(f"c48run: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
