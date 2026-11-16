# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""RBC command and output support, using the frozen assembler for object mode.

RBC's native executable is an SSX1 image, not a C48 or bytecode program.
This module converts its real relocations into independently linkable SSO1.
"""
from __future__ import annotations

from pathlib import Path


def output_path(source: Path, requested: Path | None, mode: str) -> Path:
    if requested is not None:
        return requested
    return source.with_suffix({'link': '.ssx', 'assembly': '.s', 'object': '.sso'}[mode])


def memory_required(parsed: dict, disk_bytes: int) -> int:
    """Match RCC's measured image/data/stack or file-length requirement."""
    return max(len(parsed['image']) + parsed['bss'] + parsed['stack'], disk_bytes)


def asm_from_ssx(parsed: dict) -> str:
    """Emit faithful relocatable assembler data from an actual native build."""
    image = parsed['image']
    bss = parsed['bss']
    relocs = parsed['relocs']
    if not image or parsed['entry']:
        raise ValueError('expected a native RBC image starting at zero')
    if bss < 0 or len(image) + bss > 65535:
        raise ValueError('invalid RBC memory layout')
    if len(set(relocs)) != len(relocs) or any(
        site < 0 or site + 1 >= len(image) for site in relocs
    ) or any(b - a < 2 for a, b in zip(sorted(relocs), sorted(relocs)[1:])):
        raise ValueError('invalid or overlapping RBC relocations')
    lines = ['    section text', '    global start', 'start:']
    cursor = 0
    for site in sorted(relocs) + [len(image)]:
        for begin in range(cursor, site, 16):
            portion = image[begin:min(begin + 16, site)]
            if portion:
                lines.append('    db ' + ','.join(str(v) for v in portion))
        if site == len(image):
            break
        value = int.from_bytes(image[site:site + 2], 'little')
        if value < len(image):
            target = 'start+' + str(value)
        elif value <= len(image) + bss:
            target = 'vars+' + str(value - len(image))
        else:
            raise ValueError('relocation points outside native image and data')
        lines.append('    dw ' + target)
        cursor = site + 2
    lines.extend(['    section bss', 'vars:', '    ds ' + str(bss), ''])
    return '\n'.join(lines)


def write_mode(target: Path, ssx: bytes, mode: str, rld, ras=None) -> None:
    if mode == 'link':
        payload = ssx
    else:
        parsed = rld.parse_ssx(ssx)
        assembly = asm_from_ssx(parsed)
        if mode == 'assembly':
            payload = assembly.encode('ascii')
        elif mode == 'object':
            if ras is None:
                raise ValueError('frozen assembler required for object output')
            payload = ras.assemble_text(assembly, target.with_suffix('.s').name)
        else:
            raise ValueError('unknown output mode')
    # A failed output must not leave a half-written file.
    try:
        with target.open('wb') as f:
            f.write(payload)
    except OSError:
        target.unlink(missing_ok=True)
        raise
