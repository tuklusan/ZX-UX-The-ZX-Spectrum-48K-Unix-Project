# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Use HiSoft's semantic argument type for Spectrum USR, never token spelling.

String-valued USR asks the ROM for a UDG pointer. Only the numeric form
would execute machine code; reject it in every compiler pass. A POKE with a
string-USR address checks the actual 168-byte process-owned UDG allocation at
runtime before using the native protected-memory POKE service.
"""
from __future__ import annotations
import re

from native_sysvars_rt import POKE_RT, UDG_HELPER_RT, _REPEAT_POKE, _REPEAT_VALUES

def install(compiler):
    """Install *after* process PEEK/POKE service, before building subclasses.

    All calls still pass through the genuine HiSoft operand parser. In
    particular `USR VAL A$` is numeric, however dynamic its source text.
    """
    cls = compiler.Compiler
    if getattr(cls, '_zxux_typed_usr', False):
        return
    if not getattr(cls, '_zxux_sysvars', False):
        raise ValueError('typed USR requires installed native protected-memory POKE')

    def fn_usr(self):
        self.operand()
        if self.t != compiler.STRING:
            self.not_supported('numeric USR machine-code execution is prohibited')
        self._zxux_usr_string_in_address = True
        self.call_rt(compiler.RT.USR_UDG)
        self.emit('xor a')
        self.call_rt(UDG_HELPER_RT)
        self.t = compiler.POSINT

    def st_poke(self):
        literal = _REPEAT_POKE.match(self.buf, self.ch)
        if literal is not None:
            address = int(literal['addr'])
            value = int(literal['value'])
            if value in _REPEAT_VALUES[address]:
                self.ch = literal.end()
                self.get_char()
                self.emit(f'ld a,{value}; ld (${address:04x}),a')
                return
        # Calling fn_usr in the *address* expression sets the flag. Numeric USR never
        # reaches here. An unbounded arithmetic offset still has to pass the range
        # check for the process's actual UDG base.
        self._zxux_usr_string_in_address = False
        address_start = self.ch
        self.expr_int()
        guarded = self._zxux_usr_string_in_address
        self._zxux_usr_string_in_address = False
        address = re.match(rb'^([a-z])\s*,', self.buf[address_start:], re.I)
        proved = (address is not None and
                  (self.line_no, address[1].decode('ascii').lower()) in
                  getattr(self, '_zxux_proven_udg_loop_pokes', ()))
        if guarded or proved:
            self.emit('ld a,1')
            self.call_rt(UDG_HELPER_RT)
        self.emit('push hl')
        self.next_char()
        self.expr_int()
        self.emit('ld e,l; pop hl')
        if guarded or proved:
            self.emit('ld (hl),e')
        elif (special := getattr(self, '_zxux_proven_sysvar_pokes', {}).get(self.line_no)) in (23658, 23692):
            self.emit('ld a,{}', 2 if special == 23658 else 3)
            self.call_rt(UDG_HELPER_RT)
        else:
            self.call_rt(POKE_RT)

    cls.fn_usr = fn_usr
    cls.st_poke = st_poke
    cls._zxux_typed_usr = True
