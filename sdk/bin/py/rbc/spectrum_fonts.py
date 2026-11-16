# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Per-process Sinclair 48K CHARS/UDG and printable font reference state.

This module is a behavior fixture. It must never be substituted for the
native HiSoft runtime or counted as proof of native font virtualization.
"""
from __future__ import annotations

CHARS_LOW, CHARS_HIGH = 23606, 23607
DEFAULT_CHARS = 0x3C00
PRINTABLE_FIRST = 32
PRINTABLE_LAST = 127
GLYPH_BYTES = 8


class ProcessFontState:
    def __init__(self, rom_font: bytes | None = None, shell_font: bytes | None = None):
        if rom_font is None:
            rom_font = bytes(96 * 8)
        if len(rom_font) != 96 * 8:
            raise ValueError('Sinclair printable font must be exactly 768 bytes')
        self._original_rom = bytes(rom_font)
        self._glyphs = bytearray(rom_font)
        self._chars = DEFAULT_CHARS
        self._shell_snapshot = bytes(shell_font) if shell_font is not None else bytes(rom_font)
        self._active = True

    def _live(self):
        if not self._active:
            raise ValueError('BASIC process has ended')

    def peek(self, address: int) -> int:
        self._live()
        if address == CHARS_LOW:
            return self._chars & 255
        if address == CHARS_HIGH:
            return self._chars >> 8
        raise ValueError(f'not a virtual CHARS address: {address}')

    def poke(self, address: int, value: int):
        self._live()
        if address == CHARS_LOW:
            self._chars = (self._chars & 0xff00) | (int(value) & 255)
        elif address == CHARS_HIGH:
            self._chars = (self._chars & 255) | ((int(value) & 255) << 8)
        else:
            raise ValueError(f'not a virtual CHARS address: {address}')

    def _offset(self, code: int, row: int) -> int:
        self._live()
        if not PRINTABLE_FIRST <= code <= PRINTABLE_LAST or not 0 <= row < GLYPH_BYTES:
            raise ValueError('printable character or scanline out of range')
        return (code - PRINTABLE_FIRST) * GLYPH_BYTES + row

    def poke_glyph(self, code: int, row: int, value: int):
        self._glyphs[self._offset(code, row)] = int(value) & 255

    def peek_glyph(self, code: int, row: int) -> int:
        return self._glyphs[self._offset(code, row)]

    def shell_font_snapshot(self) -> bytes:
        return self._shell_snapshot

    def exit(self, reason: str):
        if reason not in ('STOP','normal','runtime_error','handled_termination','shell_return'):
            raise ValueError(f'unknown process exit: {reason}')
        self._active = False
        self._glyphs[:] = self._original_rom
        self._chars = DEFAULT_CHARS


def detect_font_bank(lines, token_names):
    """Find a single literal 1 KB Sinclair CHARS bank, without editing BASIC.

    Source-order assignments serve only as allocation hints. No expression is
    evaluated, no BASIC statement is replaced, and the runtime still handles
    the actual POKE operations when executed. Dynamic pointers are supported
    after their CHARS bytes have actually been assigned.
    """
    import re
    from poke_proof import _line_text
    selected = set()
    low = high = None
    has_poke = False
    for _, body in lines:
        decoded = _line_text(body, token_names)
        # Even a computed POKE target may select CHARS at runtime. Reserve a
        # writable private font for all programs with memory writes, but never
        # assume an address or rewrite an expression.
        if re.search(r'\bPOKE\b', decoded, re.I):
            has_poke = True
        for statement in decoded.split(':'):
            m = re.search(r'\bPOKE\s+(23606|23607)\s*,\s*(\d+)\s*$', statement, re.I)
            if not m:
                continue
            has_poke = True
            n, val = int(m.group(1)), int(m.group(2))
            if not 0 <= val <= 255:
                continue
            if n == CHARS_LOW:
                low = val
            else:
                high = val
                if low is not None:
                    address = (high << 8) | low
                    if 0x5d00 <= address <= 0xfc00:
                        selected.add(address)
    # One private font bank can safely represent a statically designated Sinclair 8x8
    # font. Several unrelated banks require explicit rejection rather than pretending
    # that one bank aliases all of them.
    if len(selected) > 1:
        return None, has_poke
    return next(iter(selected), None), has_poke
