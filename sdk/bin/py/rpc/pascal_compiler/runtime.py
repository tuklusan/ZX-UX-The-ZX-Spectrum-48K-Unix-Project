"""Runtime emission boundary for the native port.

The original compiler's runtime blob has not yet been recovered. The current
native subset therefore emits the Spectrum ROM character-output entry used by
the existing compatibility experiments. Keeping this behind a runtime object
makes the eventual byte-constant runtime replacement explicit.
"""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

from .z80_emitter import Z80


class SpectrumRuntime:
    def emit_char(self, asm: Z80, value: int) -> None:
        asm.emit(0x3E, value)
        asm.rst10()

    def emit_text(self, asm: Z80, text: str) -> None:
        for char in text:
            self.emit_char(asm, ord(char))

    def emit_newline(self, asm: Z80) -> None:
        self.emit_char(asm, 13)
