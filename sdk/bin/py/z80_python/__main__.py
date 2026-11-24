"""Load a program and step through it: ``python -m z80_python``.

    python -m z80_python --load program.bin@0x100 --pc 0x100
    python -m z80_python --zip ROMPATH/set.zip:rom.bin@0 -c "break 0x0066" -c "run 100000"
    python -m z80_python --load zexdoc.com@0x100 --pc 0x100 --batch -c "step 5"

The host is flat 64 KiB RAM holding every image loaded, so ROM is writable,
and nothing is on the I/O bus (IN reads 0xFF, OUT goes nowhere): good for
reading and stepping through code, not for running a machine (for that, write
a host; examples/minimal_z80_host.py is the smallest). Bus accesses are
tracked, so ``watch`` works. Numbers are decimal; ``0x1234`` or ``$1234`` is
hexadecimal. Commands given with ``-c`` run first; then the prompt reads stdin,
unless ``--batch`` is given. ``help`` lists the commands.
"""

import argparse
import sys
import zipfile
from pathlib import Path

from z80_python.console import CommandDebugger, CommandError, parse_number
from z80_python.cpu import Z80CPU
from z80_python.debug import DebugSession


def _image(spec: str, *, zipped: bool) -> tuple[bytes, int]:
    source, _, where = spec.rpartition("@")
    if not source:
        raise SystemExit(f"{spec!r}: give the load address as FILE@ADDRESS")
    try:
        address = parse_number(where, "load address", maximum=0xFFFF)
    except CommandError as exc:
        raise SystemExit(f"{spec!r}: {exc}") from exc
    if zipped:
        archive, _, member = source.rpartition(":")
        if not archive:
            raise SystemExit(f"{spec!r}: give --zip as ZIPFILE:MEMBER@ADDRESS")
        with zipfile.ZipFile(archive) as bundle:
            data = bundle.read(member)
    else:
        data = Path(source).read_bytes()
    if address + len(data) > 0x10000:
        raise SystemExit(f"{spec!r}: {len(data)} bytes do not fit at 0x{address:04X}")
    return data, address


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m z80_python",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--load",
        action="append",
        default=[],
        metavar="FILE@ADDRESS",
        help="load a binary file at an address",
    )
    parser.add_argument(
        "--zip",
        action="append",
        default=[],
        metavar="ZIP:MEMBER@ADDRESS",
        help="load one file out of a zip (a MAME ROM set) at an address",
    )
    parser.add_argument("--pc", default="0", help="start at this address (default 0)")
    parser.add_argument(
        "-c",
        "--command",
        action="append",
        default=[],
        help="a debugger command to run first (repeatable)",
    )
    parser.add_argument("--batch", action="store_true", help="exit after the -c commands")
    args = parser.parse_args(argv)

    memory = bytearray(0x10000)
    for spec, zipped in [(s, False) for s in args.load] + [(s, True) for s in args.zip]:
        data, address = _image(spec, zipped=zipped)
        memory[address : address + len(data)] = data
    cpu = Z80CPU(memory.__getitem__, memory.__setitem__)
    try:
        cpu.pc = parse_number(args.pc, "pc", maximum=0xFFFF)
    except CommandError as exc:
        raise SystemExit(f"--pc: {exc}") from exc
    session = DebugSession(cpu, peek_byte=memory.__getitem__, track_accesses=True)
    debugger = CommandDebugger(session)
    for command in ["registers", "disassemble", *args.command]:
        print(f"z80> {command}")
        try:
            result = debugger.execute(command)
        except CommandError as exc:
            print(f"error: {exc}")
            continue
        for line in result.lines:
            print(line)
        if result.quit:
            return
    if not args.batch:
        debugger.interact(sys.stdin, sys.stdout)


if __name__ == "__main__":
    main()
