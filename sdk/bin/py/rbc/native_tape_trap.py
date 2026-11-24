# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Compile valid Sinclair tape statements as guarded native runtime errors.

Four original 48K keywords are recognized.  If a statement is reached,
execution terminates with distinct ZX-UX status 12 through the existing
private-UDG cleanup pointer.  Untaken branches are unaffected.  No host tape
file is opened and no original BASIC token or source file is rewritten.
"""

from native_error_exit import error_exit_asm

TAPE_STATUS = 12
TOKENS = (0xEF, 0xF8, 0xD5, 0xD6)  # LOAD SAVE MERGE VERIFY


def _skip_to_statement_end(compiler):
    """Skip ROM-validated arguments, never confusing quoted ':' or caches.

    The original ROM syntax scan has already validated this exact listing;
    interpreting tape argument expressions is deliberately unnecessary, as
    executing this statement always fails before any external I/O.
    """
    buf = compiler.buf
    pos = compiler.ch
    quoted = False
    while pos < len(buf):
        byte = buf[pos]
        if byte == 34:
            quoted = not quoted
        elif not quoted and byte == 14:
            if pos + 6 > len(buf):
                raise ValueError('truncated Sinclair numeric cache in tape statement')
            pos += 6
            continue
        elif not quoted and byte in (13, 58):
            compiler.ch = pos
            return
        pos += 1
    raise ValueError('unterminated Sinclair tape statement')


def install(compiler):
    """Install only four source-verified handlers in HiSoft statement dispatch."""
    cls = compiler.Compiler
    if getattr(cls, '_zxux_tape_trap_installed', False):
        return
    original_dispatch = cls.dispatch.fget

    def st_tape_unsupported(self):
        _skip_to_statement_end(self)
        # Existing relocatable SSX wrapper owns private UDG+168 -> cleanup. This is typed Z80
        # emitted BEFORE linking, not a patched SSX.
        self.emit(error_exit_asm(TAPE_STATUS))

    def dispatch(self):
        table = original_dispatch(self)
        for token in TOKENS:
            table[token] = self.st_tape_unsupported
        return table

    cls.st_tape_unsupported = st_tape_unsupported
    cls.dispatch = property(dispatch)
    cls._zxux_tape_trap_installed = True
