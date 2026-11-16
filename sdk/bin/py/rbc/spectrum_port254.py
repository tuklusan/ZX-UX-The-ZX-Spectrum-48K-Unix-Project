# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Allow only the original Spectrum ULA beeper OFF/ON pair on port FE.

Literal OUT 254,0 and OUT 254,16 select border black while toggling
beeper bit 4. All computed or other hardware writes remain blocked.
"""
from __future__ import annotations
import re

_LITERAL = re.compile(r'^\s*254\s*,\s*(?:0|16)\s*$')
_TOKEN = re.compile(rb'254(?:\x0e[^\r]{5})?\s*,\s*(?P<value>0|16)(?:\x0e[^\r]{5})?(?=[ \t\r:])')


def allow_port254(findings):
    count = 0
    for item in findings:
        if (item.operation == 'OUT' and item.severity == 'block' and
                item.classification == 'raw_io_output' and
                _LITERAL.fullmatch(item.expression)):
            item.classification = 'literal_port254_buzzer'
            item.severity = 'info'
            count += 1
    return count


def install(compiler):
    cls = compiler.Compiler
    if getattr(cls, '_zxux_port254', False):
        return
    old_out = cls.st_out

    def st_out(self):
        literal = _TOKEN.match(self.buf, self.ch)
        if literal is not None:
            value = int(literal['value'])
            self.ch = literal.end()
            self.get_char()
            self.emit(f'ld bc,$00fe; ld a,{value}; out (c),a')
            return
        old_out(self)

    cls.st_out = st_out
    cls._zxux_port254 = True
