# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Fail-closed whole-program optimizer gate for HiSoft's complete Z80 output.

A fragment-only rewrite cannot be called a whole-program optimization.  Until
all direct writes, code patches, runtime emitters, relocations and DATA are
symbolic, refuse --upeepz80 rather than emitting an unverified executable.
"""
from __future__ import annotations

from functools import wraps

from symbolic_capture import audit_result, install as install_capture


class UnresolvedAssemblyBoundary(ValueError):
    """The compiler contains code/data boundaries not safe for relocation."""


def install(compiler_module):
    """Audit the whole final compilation before permitting Z80 optimization."""
    compiler = compiler_module.Compiler
    if getattr(compiler, '_zxux_whole_program_gate_installed', False):
        return
    install_capture(compiler_module)
    original = compiler.compile_whole

    @wraps(original)
    def compile_whole(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if not result.ok:
            return result
        report = audit_result(self, result)
        self._zxux_upeep_stats = {
            'mode': 'whole-program-required',
            'image_bytes': report['image_bytes'],
            'uncovered_bytes': report['uncovered_bytes'],
            'changed_after_emit': report['changed_after_emit'],
            'unresolved_direct_write_bytes': report['unresolved_direct_write_bytes'],
            'rewritten_bytes': report['rewritten_bytes'],
            'byte_categories': report['byte_categories'],
        }
        # A complete byte trace still contains absolute numeric operands; only the typed symbol
        # resolver is allowed to approve optimization.
        if not report['complete_byte_trace'] or not report['safe_to_optimize']:
            raise UnresolvedAssemblyBoundary(
                'Gate 8 unresolved whole-program Z80 boundaries: '
                f"{report['uncovered_bytes']} uncaptured bytes, "
                f"{report['changed_after_emit']} untraced patches, "
                f"{report['unresolved_direct_write_bytes']} typed-address patches pending, "
                f"{report['rewritten_bytes']} rewrites; "
                'typed relocations and runtime-emitter source required')
        raise UnresolvedAssemblyBoundary(
            'Gate 8 missing whole-program ras/rld symbol resolution')

    compiler.compile_whole = compile_whole
    compiler._zxux_whole_program_gate_installed = True
