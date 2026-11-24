# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Storage ordering and checked bounds for ANSI F77S 1-3D fixed arrays.

Flattened C48 arrays follow FORTRAN column-major order, with the first
subscript varying fastest. Runtime subscripts call f_index for each bound.
"""
from __future__ import annotations
from functools import reduce
from operator import mul
from .translator import FortranError


def dimensions(extent):
    return (extent,) if isinstance(extent, int) else tuple(extent)


def size(extent):
    return reduce(mul, dimensions(extent), 1)


def offset(indices, extent, line):
    dims = dimensions(extent)
    if len(dims) != len(indices):
        raise FortranError(line, 'array subscript count must match declared rank')
    terms, stride = [], 1
    for exp, dim in zip(indices, dims):
        term = 'f_index(' + exp + ', ' + str(dim) + ')'
        terms.append(('(' + term + ' * ' + str(stride) + ')') if stride != 1 else term)
        stride *= dim
    return '(' + ' + '.join(terms) + ')'


def literal_offset(indices, extent, line):
    dims = dimensions(extent)
    if len(dims) != len(indices):
        raise FortranError(line, 'array subscript count must match rank')
    index, stride = 0, 1
    for value, extent in zip(indices, dims):
        if not 1 <= value <= extent:
            raise FortranError(line, 'DATA array index out of bounds')
        index += (value - 1) * stride
        stride *= extent
    return index
