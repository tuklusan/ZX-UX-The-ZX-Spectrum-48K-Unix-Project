# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Integrate sound scalar typing into the native Python compiler.

The original HiSoft INT directive is implemented by pre-populating the
single-scalar name table with two-byte variables and enabling integer
literal recognition. This avoids needing unused source line numbers.
"""
def with_integral_scalars(base, names, integer_type):
    names = tuple(sorted(set(names)))
    if not names:
        return base
    if any(len(n) != 1 or not ('a' <= n <= 'z') for n in names):
        raise ValueError('integer specialization requires one-letter scalar names')

    class IntegerSpecialized(base):
        def reset(self, program):
            super().reset(program)
            if self.names or self.n_int or self.n_real:
                raise ValueError('cannot specialize an already initialized name table')
            self.names = [(n, integer_type) for n in names]
            self.n_int = len(names)
            self.name_bytes = sum(len(n) + 1 for n in names)
            self.int_directive = 0xFF

    return IntegerSpecialized
