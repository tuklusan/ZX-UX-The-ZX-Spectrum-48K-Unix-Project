# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Compile a bare Sinclair RUN as a native restart in the same process.

The restart restores the starting stack, clears numeric and string variable
storage, resets DATA/READ and jumps to the first original BASIC line. A
separate two-byte stack slot survives clearing. This changes generated code
only when a RUN token occurs outside quoted text and comments.
"""

_RUN = 0xF7
_REM = 0xEA


def _computed_run_present(lines):
    """Only expression-valued RUN needs the native line-search table."""
    import re
    for _, body in lines:
        quoted = False
        pos = 0
        while pos < len(body):
            ch = body[pos]
            if ch == 14 and not quoted and pos + 6 <= len(body):
                pos += 6
                continue
            if ch == 34:
                quoted = not quoted
            elif not quoted and ch == _REM:
                break
            elif not quoted and ch == _RUN:
                end = body.find(b':', pos + 1)
                end = len(body) if end < 0 else end
                arg = body[pos + 1:end].rstrip(b'\r ').strip()
                if arg and not re.fullmatch(rb'[0-9]+(?:\x0e[\x00-\xff]{5})?', arg):
                    return True
            pos += 1
    return False


def _uses_run(lines):
    for _, body in lines:
        quoted = False
        pos = 0
        while pos < len(body):
            char = body[pos]
            if char == 14 and not quoted and pos + 5 < len(body):
                pos += 6
                continue
            if char == 34:
                quoted = not quoted
            elif not quoted and char == _REM:
                break
            elif not quoted and char == _RUN:
                return True
            pos += 1
    return False

def _run_entry(lines, requested):
    """Sinclair's next *source* line, not the HiSoft setup directive."""
    if not isinstance(requested, int) or requested < 0 or requested >= 0x4000:
        return None
    return next((number for number, body in lines
                 if number > 0 and number >= requested and
                 not body.startswith(bytes((_REM, ord(':'))))), None)


def install(compiler):
    cls = compiler.Compiler
    if getattr(cls, '_zxux_has_native_run', False):
        return
    initial_reset = cls.reset
    initial_layout = cls.layout_vars
    initial_dispatch = cls.dispatch.fget

    def reset(self, program):
        initial_reset(self, program)
        self._zxux_run_present = _uses_run(self.lines)
        if _computed_run_present(self.lines):
            self.goto_directive = 1
            self.gosub_all = 1
        self._zxux_run_first = _run_entry(self.lines, 0) or 0
        self._zxux_run_sp = 0
        self._zxux_run_clear_bytes = 1

    def layout_vars(self):
        initial_layout(self)
        if not self._zxux_run_present:
            return
        # Preserve system-variable BSS when RUN clears BASIC variables. The sysvar helper
        # allocates its own process region after user vars.
        sysvar_base = getattr(self, '_zxux_sysvar_base', 0)
        user_end = sysvar_base if sysvar_base and sysvar_base >= self.vars_start else self.pc
        user_size = (user_end - self.vars_start) & 0xffff
        if not user_size:
            # MEM_FILL uses BC=size-1, so keep a single-byte scratch area.
            self.pc = (self.pc + 1) & 0xffff
            user_size = 1
        self._zxux_run_clear_bytes = user_size
        self._zxux_run_sp = self.pc
        self.pc = (self.pc + 2) & 0xffff

    def st_run(self):
        if not self._zxux_run_present or not self._zxux_run_first:
            self.not_supported('RUN entry')
        if self.at_end():
            computed, requested = False, self._zxux_run_first
        else:
            # HiSoft evaluates computed line numbers into HL.
            computed, requested = self.goto_target()
        if not computed:
            target = _run_entry(self.lines, requested)
            if target is None:
                self.not_supported('RUN line outside listing')
        # Restore the caller's stack after nested GO SUB.
        self.emit_op_reloc('ld sp,(nn)', self._zxux_run_sp)
        if computed:
            # Save the target across variable clearing and RESTORE.
            self.emit('push hl')
        # Keep the emitted width fixed across HiSoft's counting and store passes.
        self.ld_hl(self.vars_start)
        self.emit('ld (hl),0')
        if self._zxux_run_clear_bytes > 1:
            self.emit('ld d,h; ld e,l; inc de')
            self.ld_bc_abs(self._zxux_run_clear_bytes - 1)
            self.emit('ldir')
        else:
            self.emit('nop; nop; nop; nop; nop; nop; nop; nop')
        self.emit_restore()
        if computed:
            self.emit('pop hl')
            self.emit_op_reloc('jp nn', self.search_at)
        else:
            self.emit_goto('jp nn', target)

    def dispatch(self):
        result = initial_dispatch(self)
        result[_RUN] = self.st_run
        return result

    cls.reset = reset
    cls.layout_vars = layout_vars
    cls.st_run = st_run
    cls.dispatch = property(dispatch)
    cls._zxux_has_native_run = True
