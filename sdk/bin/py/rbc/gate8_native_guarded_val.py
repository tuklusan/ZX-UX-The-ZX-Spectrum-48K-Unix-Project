# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Independent typed native Z80 source for the guarded ROM VAL runtime.

The original replacement's byte generator stays untouched. Its complete
instruction stream is reassembled from reviewed mnemonics and branch labels;
the linked result must independently match all 122 original bytes.
"""
from __future__ import annotations

from native_error_exit import error_exit_asm
from spectrum_runtime import guarded_val_bytes


class GuardedValSourceError(ValueError):
    """The reviewed VAL source differs from the original runtime."""


def guarded_val_assembly(calculator_token=0x1D) -> str:
    """Source-owned VAL scan and process-private error exit."""
    lines = [
        'section text', 'global start', 'start:',
        'push af', 'push bc', 'push de', 'push hl',
        'ld hl,($5c65)',
        'dec hl', 'ld b,(hl)', 'dec hl', 'ld c,(hl)',
        'dec hl', 'ld d,(hl)', 'dec hl', 'ld e,(hl)',
        'ex de,hl', 'ld d,0',
        'rbc_val_scan:',
        'ld a,b', 'or c', 'jr z,rbc_val_allowed',
        'ld a,(hl)', 'cp $22', 'jr nz,rbc_val_not_quote',
        'ld a,d', 'xor 1', 'ld d,a', 'jr rbc_val_next',
        'rbc_val_not_quote:',
        'ld a,d', 'or a', 'jr nz,rbc_val_next',
        'ld a,(hl)', 'cp $ea', 'jr z,rbc_val_allowed',
        'cp $be', 'jr z,rbc_val_blocked',
        'cp $c0', 'jr z,rbc_val_blocked',
        'cp $b0', 'jr z,rbc_val_blocked',
        'cp $ae', 'jr z,rbc_val_blocked',
        'ld a,(hl)', 'and $df', 'cp $55', 'jr nz,rbc_val_next',
        'ld a,b', 'or a', 'jr nz,rbc_val_ascii_look',
        'ld a,c', 'cp 3', 'jr c,rbc_val_next',
        'rbc_val_ascii_look:',
        'inc hl', 'ld a,(hl)', 'and $df', 'cp $53',
        'jr nz,rbc_val_ascii_back1',
        'inc hl', 'ld a,(hl)', 'and $df', 'cp $52',
        'jr nz,rbc_val_ascii_back2',
        'jr rbc_val_blocked',
        'rbc_val_ascii_back2:', 'dec hl',
        'rbc_val_ascii_back1:', 'dec hl',
        'rbc_val_next:', 'inc hl', 'dec bc', 'jr rbc_val_scan',
        'rbc_val_allowed:',
        'pop hl', 'pop de', 'pop bc', 'pop af',
        f'ld b,${calculator_token:02x}', 'jp $35de',
        'rbc_val_blocked:',
        'pop hl', 'pop de', 'pop bc', 'pop af',
    ]
    lines += error_exit_asm(10).split(';')
    return '\n'.join(('    ' + line if not line.endswith(':') else line)
                     for line in lines) + '\n'


def verify_native_guarded_val(ras, rld):
    """Link source at zero relocation and match independent HiSoft bytes."""
    source = guarded_val_assembly()
    expected = guarded_val_bytes()
    obj = ras.assemble_text(source, 'rbc-guarded-val.s')
    binary, *_ = rld.link([rld.Obj(obj, 'rbc-guarded-val.sso')],
                          [], entry='start', stack=384)
    parsed = rld.parse_ssx(binary)
    if (parsed['image'] != expected or parsed['relocs'] or
            parsed['bss'] != 0 or parsed['entry'] != 0):
        raise GuardedValSourceError('native guarded VAL differs from original runtime')
    return {'runtime_bytes': len(expected), 'native_file_bytes': len(binary),
            'native_relocations': len(parsed['relocs']), 'native_verified': True}
