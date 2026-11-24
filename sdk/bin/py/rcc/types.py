# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""C48 types: scalars are strings, ('p', T) pointer, ('a', T, n) array,
('f', ret, (params...)) function."""

INTS = ('char', 'uchar', 'short', 'ushort', 'int', 'uint')
SIGNED = ('short', 'int')
BYTE = ('char', 'uchar')
SIZE = {'char': 1, 'uchar': 1, 'short': 2, 'ushort': 2, 'int': 2, 'uint': 2, 'float': 5}
NAMES = {'char': 'char', 'uchar': 'unsigned char', 'short': 'short',
         'ushort': 'unsigned short', 'int': 'int', 'uint': 'unsigned int',
         'float': 'float', 'void': 'void'}


def is_int(t):
    return t in INTS


def is_arith(t):
    return t in INTS or t == 'float'


def is_ptr(t):
    return isinstance(t, tuple) and t[0] == 'p'


def is_arr(t):
    return isinstance(t, tuple) and t[0] == 'a'


def is_fn(t):
    return isinstance(t, tuple) and t[0] == 'f'


def is_scalar(t):
    return is_arith(t) or is_ptr(t)


def sizeof(t):
    if isinstance(t, str):
        if t == 'void':
            return None
        return SIZE[t]
    if t[0] == 'p':
        return 2
    if t[0] == 'a':
        s = sizeof(t[1])
        return None if s is None or t[2] is None else s * t[2]
    return None


def align_of(t):
    """Spec 18 (P0222, P0231, P0306): 2 for short, int and pointers (and
    arrays of them), 1 for char and float."""
    if is_arr(t):
        return align_of(t[1])
    if is_ptr(t) or t in ('short', 'ushort', 'int', 'uint'):
        return 2
    return 1


def promote(t):
    if t in ('char', 'uchar', 'short'):
        return 'int'
    if t == 'ushort':
        return 'uint'
    return t


def common(a, b):
    if a == 'float' or b == 'float':
        return 'float'
    a, b = promote(a), promote(b)
    if a == 'uint' or b == 'uint':
        return 'uint'
    return 'int'


def signed(t):
    return t in SIGNED


def tname(t):
    if isinstance(t, str):
        return NAMES[t]
    if t[0] == 'p':
        return tname(t[1]) + ' *'
    if t[0] == 'a':
        return '%s[%d]' % (tname(t[1]), t[2])
    return '%s(%s)' % (tname(t[1]), ', '.join(tname(p) for p in t[2]) or 'void')


def decay(t):
    if is_arr(t):
        return ('p', t[1])
    return t
