# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rpc: ZX-UX relocatable Pascal compiler frontend and link driver."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from .backend import compile_to_asm
from .pascal_compiler.errors import PascalError

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='rpc', formatter_class=argparse.RawDescriptionHelpFormatter,
        description='ZX-UX relocatable Pascal compiler. '
        'Pascal port copyright (c) 2026 Supratim Sanyal, SANYALnet Labs.'
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('-S', action='store_true', help='emit ras assembly')
    mode.add_argument('-c', action='store_true', help='emit SSO1 object')
    parser.add_argument('-o', metavar='OUTPUT', help='output path')
    parser.add_argument('--tzx', action='store_true', help='write SSX1 and TZX tape')
    parser.add_argument('source', metavar='FILE.pas')
    args = parser.parse_args(argv)
    if args.tzx and (args.S or args.c):
        parser.error('--tzx requires linking an executable')
    source = Path(args.source)
    out = Path(args.o) if args.o else source.with_suffix(
        '.s' if args.S else '.sso' if args.c else '.ssx'
    )
    try:
        asm = compile_to_asm(source.read_text(encoding='utf-8'))
        if args.S:
            out.write_text(asm, encoding='ascii')
            return 0
        import ras
        obj = ras.assemble_text(asm, str(source))
        if args.c:
            out.write_bytes(obj)
            return 0
        import rld, rtap
        library = SDK / 'lib/libc48.ssa'
        with library.open('rb') as fp:
            archives = [rld.read_archive(fp.read(), str(library))]
        exe, _, _, _, _ = rld.link([rld.Obj(obj, str(source))], archives, 'start', 512, 0)
        rld.parse_ssx(exe)
        need = rtap.need(exe)
        if need > 14000:
            raise ValueError('executable needs %d bytes, ZX-UX limit is 14000' % need)
        if args.tzx:
            label = source.stem[:10]
            tape_records = rtap.records(exe, label)
            tape = bytearray(b'ZXTape!\x1a\x01\x14')
            import struct
            for pause, block in zip((1000, 2000), tape_records):
                tape.extend(b'\x10' + struct.pack('<HH', pause, len(block)) + block)
            _, check = rtap.tzx_blocks(bytes(tape))
            if len(check) != 2 or not all(rtap._parity_ok(b) for _, b in check):
                raise ValueError('invalid generated tape')
        out.write_bytes(exe)
        if args.tzx:
            out.with_suffix('.tzx').write_bytes(tape)
        return 0
    except (OSError, UnicodeError, PascalError, ValueError, IndexError) as err:
        print('rpc: ' + str(err), file=sys.stderr)
        return 1
    except Exception as err:
        # ras/rld supply their own error classes; report failed assembly/link.
        print('rpc: ' + str(err), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
