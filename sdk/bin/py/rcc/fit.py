# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Default measured C48 code-mode search; caller settings are preserved.

Every candidate is compiled and linked with the installed source/runtime.
The reported result is the smallest found within this bounded search, NOT
an exhaustive minimum. User-requested stack and UDG reservations are kept.
"""
from __future__ import annotations

from . import bcgen


class FitError(Exception):
    pass


def has_call_cycle(funcs):
    """Conservatively detect direct or mutually recursive source calls."""
    names = {f.name for f in funcs}
    graph = {f.name: {c.name for c in f.calls if c.name in names} for f in funcs}
    visiting, complete = set(), set()

    def visit(name):
        if name in visiting:
            return True
        if name in complete:
            return False
        visiting.add(name)
        found = any(visit(child) for child in sorted(graph[name]))
        visiting.remove(name)
        complete.add(name)
        return found

    return any(visit(name) for name in sorted(graph))


def find_smallest(src, opts, build_fn, max_candidates=128, max_passes=3):
    """Return (linked_result, trial_count, format_choices).

    Start from native and compact bytecode. Search single-function flips
    from the currently smallest linked result, taking only strict progress.
    """
    if max_candidates < 2 or max_passes < 1:
        raise FitError('invalid compiler search budget')
    original = dict(opts)
    original.pop('bytecode', None)
    native = build_fn(src, original)
    permitted = frozenset(f.name for f in native[1].p.funcs if not bcgen.uses_float(f))
    cache = {frozenset(): native}
    best_modes = frozenset()
    best = native

    def measure(modes):
        if modes not in cache:
            if len(cache) >= max_candidates:
                return None
            settings = dict(original)
            settings['bytecode'] = modes if modes else 'none'
            cache[modes] = build_fn(src, settings)
        return cache[modes]

    def score(result, modes):
        return (result[4], len(result[0]), tuple(sorted(modes)))

    compact = measure(permitted) if permitted else native
    if score(compact, permitted) < score(best, best_modes):
        best, best_modes = compact, permitted

    for _ in range(max_passes):
        next_modes, next_result = best_modes, best
        for name in sorted(permitted):
            variant = best_modes ^ {name}
            result = measure(frozenset(variant))
            if result is None:
                break
            if score(result, frozenset(variant)) < score(next_result, next_modes):
                next_result, next_modes = result, frozenset(variant)
        if score(next_result, next_modes) >= score(best, best_modes):
            break
        best, best_modes = next_result, next_modes
    return best, len(cache), best_modes
