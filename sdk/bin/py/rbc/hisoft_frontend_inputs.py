#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Recreate untracked HiSoft v1.1 tape and locked canonical frontend for RBC.

No BASIC program is edited. Inputs and copied Python files are checked before
entering the compiler; the tape is supplied by the operator, not the repo.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen

# Canonical ZX-UX frontend: owner's HiSoft Python compiler fork.
CANONICAL_FRONTEND = 'https://github.com/tuklusan/Python-BASIC-Compiler-for-ZX-Spectrum-Hisoft'
REVISION = '7cc87dafb58fcf5632b7190320dd11c30b4fe961'
ORIGIN = f'{CANONICAL_FRONTEND.replace("github.com", "raw.githubusercontent.com")}/{REVISION}/'
# Blob identities checked against the canonical fork at REVISION, not HEAD.
FRONTEND = {
    'compiler.py': '688dc637474fef51f6b4d902839d9cd4d01db4a8',
    'hbcimage.py': '2717fc4b1ceeffb87afa897169cffc2c5322a7df',
    'pyhsb.py': 'b5e1b93d0ed0b64e9b20cebe44e1ee1c912e46c5',
    'report.py': 'bbe2e7aa70c5cb129a74b5d086fb63c38545e489',
    'romfp.py': '161fb67c96f7b98d1b68f4418fc436e15fd511fa',
    'rtlib.py': '671dbbace8ca8d46852b6cbead9654e449e30789',
    'rtnames.py': '5e6512da7131592b7576f21c2d0b2eeedad66396',
    'source.py': '0ccc71226f04cb494a26721fedeecf5fcd445f5f',
    'tap.py': '46259b5b1dec558aeaa3b7609fa964402747eee8',
    'z80asm.py': '31d844e98d4bce51eb9997d4bf716e70b2ae9e64',
    'z80mini.py': '5a5db403104954da6b35ef66ec94437db2bd9c12',
}
KNOWN_COMPILER = 'b3fb20debb186d74ca10d1ec7b09f1bc4cf12b89e092e4aca81741c3e00c5793'


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def convert_tzx_to_tap(tzx: bytes) -> bytes:
    """Require checksum-valid standard-speed blocks and authentic 48K hbc2."""
    if not tzx.startswith(b'ZXTape!\x1a') or len(tzx) < 10:
        raise ValueError('invalid TZX header')
    blocks = []
    position = 10
    while position < len(tzx):
        if tzx[position] != 0x10:
            raise ValueError(f'unsupported TZX block at offset {position}')
        if position + 5 > len(tzx):
            raise ValueError('truncated TZX standard block')
        length = int.from_bytes(tzx[position+3:position+5], 'little')
        position += 5
        block = tzx[position:position+length]
        if len(block) != length or not length:
            raise ValueError('truncated TZX payload')
        if 0 != __import__('functools').reduce(lambda value, byte: value ^ byte, block, 0):
            raise ValueError('TZX XOR checksum failure')
        blocks.append(block)
        position += length
    if len(blocks) != 6:
        raise ValueError(f'expected six 48K compiler tape blocks, got {len(blocks)}')
    code_header = blocks[4]
    if (len(code_header) != 19 or code_header[:2] != b'\x00\x03' or
            code_header[2:12].strip() != b'hbc2' or
            int.from_bytes(code_header[14:16], 'little') != 0x5CF0 or
            int.from_bytes(code_header[12:14], 'little') != len(blocks[5])-2 or
            blocks[5][0] != 0xFF):
        raise ValueError('missing authentic 48K hbc2 CODE block')
    if hashlib.sha256(blocks[5][1:-1]).hexdigest() != KNOWN_COMPILER:
        raise ValueError('HiSoft 48K v1.1 compiler digest mismatch')
    return b''.join(len(block).to_bytes(2, 'little') + block for block in blocks)


def copy_frontend(out: Path, source: Path | None = None) -> dict[str, str]:
    """Allow only the exact reviewed canonical fork revision."""
    contents = {}
    for filename, expected in FRONTEND.items():
        if source is None:
            with urlopen(ORIGIN + filename, timeout=30) as response:
                raw = response.read()
        else:
            raw = (source / filename).read_bytes()
        actual = git_blob(raw)
        if actual != expected:
            raise ValueError(f'{filename}: canonical frontend Git blob mismatch ({actual})')
        contents[filename] = raw
    out.mkdir(parents=True, exist_ok=True)
    for filename, raw in contents.items():
        (out / filename).write_bytes(raw)
    return {filename: FRONTEND[filename] for filename in contents}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compiler_tzx', type=Path, help='unaltered original HiSoft v1.1 compiler TZX')
    parser.add_argument('--output', type=Path, required=True, help='untracked build/tmp directory')
    parser.add_argument('--source-dir', type=Path, help='locally retrieved original pyhsb source files')
    args = parser.parse_args()
    tap = convert_tzx_to_tap(args.compiler_tzx.read_bytes())
    copy_frontend(args.output / 'upstream-pyhsb', args.source_dir)
    (args.output / 'hisoft48.tap').write_bytes(tap)
    print(f'HISOFT_FRONTEND_OK pyhsb={REVISION} tape_sha256={hashlib.sha256(tap).hexdigest()}')


if __name__ == '__main__':
    main()
