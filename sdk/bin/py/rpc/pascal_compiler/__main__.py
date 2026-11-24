"""CLI for the standalone Pascal-to-Z80 compiler."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

import argparse
from pathlib import Path

from .codegen import Compiler, make_tap
from .assembler import assemble_sjasmplus
from .errors import PascalError
from .listing import format_sjasmplus
from .optimizer import OptimizerUnavailable, optimize_assembly


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile ASCII Pascal to a flat Z80 binary")
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument(
        "--asm", type=Path,
        help="write the SJASMPlus-compatible source for the output binary",
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="run bundled upeepz80 and assemble optimized output",
    )
    parser.add_argument("--tap", action="store_true", help="write a Spectrum TAP instead of a flat binary")
    args = parser.parse_args()
    try:
        code = Compiler().compile(args.source.read_text(encoding="utf-8"))
        assembly = None
        if args.asm is not None or args.optimize:
            assembly = format_sjasmplus(code)
            if args.optimize:
                report = optimize_assembly(assembly)
                assembly = report.optimized_assembly
                code = assemble_sjasmplus(assembly)
            elif args.asm is not None and assemble_sjasmplus(assembly) != code:
                raise ValueError("generated assembler does not reproduce the binary")
        output = make_tap(code, args.source.stem.upper()) if args.tap else code
        args.output.write_bytes(output)
        if args.asm is not None and assembly is not None:
            args.asm.write_text(assembly, encoding="ascii")
    except (
        OSError,
        PascalError,
        UnicodeError,
        OptimizerUnavailable,
        ValueError,
    ) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
