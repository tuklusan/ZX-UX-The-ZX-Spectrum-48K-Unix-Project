# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Update the ROM last-key byte before native PEEK 23556.

ZX-UX supplies its own interrupts. The original programs that inspect the
Spectrum KSTATE byte need the original ROM keyboard scan at $02BF, just as
the native PAUSE bridge does. Every other PEEK remains an ordinary read.
"""
from __future__ import annotations

# Input address arrives in HL. Save flags and working registers around the ROM call; both jumps lead
# to the common restored-flags direct PEEK path.
_NATIVE_PEEK = (
    'push af; ld a,h; cp $5c; jr nz,+14; '
    'ld a,l; cp $04; jr nz,+9; '
    'push bc; push de; push hl; call $02bf; '
    'pop hl; pop de; pop bc; pop af; '
    'ld l,(hl); ld h,0'
)


def install(compiler):
    """Replace only HiSoft Compiler.fn_peek; keep its expression parser."""
    cls = compiler.Compiler
    if getattr(cls, '_zxux_key_scan', False):
        return

    def native_peek(self):
        self.operand_to_int()
        self.emit(_NATIVE_PEEK)

    cls.fn_peek = native_peek
    cls._zxux_key_scan = True