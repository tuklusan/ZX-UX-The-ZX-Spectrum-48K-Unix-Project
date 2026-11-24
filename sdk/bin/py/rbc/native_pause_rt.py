# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Adapt native HiSoft PAUSE to ZX-UX's real Spectrum keyboard state.

The ZX-UX ISR updates the ROM KSTATE slots but does not set FLAGS bit 5.
PAUSE 0 therefore checks the two live ROM key slots instead of waiting on a
FLAGS bit that can never indicate a key. Finite PAUSE still counts frames,
and any key may interrupt it. All paths clear FLAGS bit 5 on return.
"""
from __future__ import annotations


def _pause_code(asm, *, with_source=False):
    """Emit the native bytes and optionally their original typed Z80 source."""
    code = bytearray()
    source_lines = ['  section text', '  global start', 'start:']
    labels = {}
    relative = []

    def emit(source, *, typed_source=None):
        code.extend(asm(source))
        statement = typed_source if typed_source is not None else source
        source_lines.extend('  ' + part.strip() for part in statement.split(';')
                            if part.strip())

    def mark(label):
        labels[label] = len(code)
        source_lines.append('rbc_pause_' + label + ':')

    def branch(mnemonic, label):
        start = len(code)
        emit(mnemonic + ',+0' if mnemonic != 'jr' else 'jr +0',
             typed_source=(mnemonic + ' rbc_pause_' + label if mnemonic == 'jr'
                           else mnemonic + ',rbc_pause_' + label))
        assert len(code) == start + 2
        relative.append((start + 1, label))

    emit('ld b,h;ld c,l;ld a,($5c3b);and $df;ld ($5c3b),a')
    mark('scan')
    emit('halt;push bc;call $02bf;pop bc')
    # KSTATE[0] and KSTATE[4]: FF when the slot is free, a key code otherwise. They are
    # updated by ROM KEYBOARD even without FLAGS bit 5.
    emit('ld a,($5c00);inc a')
    branch('jr nz', 'done')
    emit('ld a,($5c04);inc a')
    branch('jr nz', 'done')
    emit('ld a,b;or c')
    branch('jr z', 'scan')  # PAUSE 0: wait for a key, indefinitely
    emit('dec bc;ld a,b;or c')
    branch('jr nz', 'scan')
    mark('done')
    emit('ld a,($5c3b);and $df;ld ($5c3b),a;ret')
    for where, label in relative:
        dist = labels[label] - (where + 1)
        if not -128 <= dist <= 127:
            raise ValueError('PAUSE jump too distant')
        code[where] = dist & 255
    native = bytes(code)
    if with_source:
        return native, '\n'.join(source_lines) + '\n'
    return native


def original_pause_source(asm):
    """Return one source-owned PAUSE routine and its emitted reference bytes."""
    return _pause_code(asm, with_source=True)


def install(compiler):
    """Replace only HiSoft RT.PAUSE emission, preserving all other emitters."""
    from z80asm import asm
    from rtnames import RT
    runtime = compiler.rtlib
    base = runtime.Machine
    if getattr(base, '_zxux_native_pause', False):
        return
    pause_native = _pause_code(asm)

    class ZXUXPauseMachine(base):
        _zxux_native_pause = True

        def run_emitter(self, n, pc, counting, code_base):
            if n != RT.PAUSE:
                return super().run_emitter(n, pc, counting, code_base)
            if not counting and not self.de_flags & 1:
                self.far[pc:pc + len(pause_native)] = pause_native
            return pc + len(pause_native)

    runtime.Machine = ZXUXPauseMachine
