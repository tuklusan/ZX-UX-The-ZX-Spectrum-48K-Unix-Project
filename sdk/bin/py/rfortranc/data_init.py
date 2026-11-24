# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Minimal ANSI F77S DATA initializer lowering.

Supports numeric/logical scalar and fixed-array initialization plus CHARACTER
scalar DATA in programs and subroutines. Subprogram DATA storage is allocated
statically and initialized once by the translator. Implied DO, CHARACTER arrays
and overlapping storage association remain unsupported.
"""
from __future__ import annotations
import re
from .translator import FortranError, NAME, split_items


def _find_unquoted_slash(text, start):
    """F77S DATA delimiters ignore slashes inside character literals."""
    quote = None
    i = start
    while i < len(text):
        ch = text[i]
        if quote and ch == quote and text[i:i+2] == quote * 2:
            i += 2
            continue
        if quote and ch == quote:
            quote = None
        elif quote is None and ch in ("'", '"'):
            quote = ch
        elif quote is None and ch == '/':
            return i
        i += 1
    return -1


def initializers(unit):
    result = []
    used = set()
    saw_exec = False
    saw_data = False
    for st in unit.statements:
        s = st.text.strip()
        m = re.fullmatch(r'DATA\s+(.+)', s)
        if not m:
            sf = re.match(r'^([A-Z][A-Z0-9_]*)\s*\(', s)
            if sf and sf.group(1) in unit.statement_functions:
                if saw_exec or saw_data:
                    raise FortranError(st.line, 'statement function after DATA/executable')
                continue
            if re.match(r'^(INTEGER|REAL|LOGICAL|CHARACTER|DIMENSION|IMPLICIT|COMMON|SAVE|EQUIVALENCE|INTRINSIC|EXTERNAL)\b', s):
                if saw_exec or saw_data:
                    raise FortranError(st.line, 'specification statement after DATA or executable statement')
            elif not re.match(r'^FORMAT\s*\(', s):
                saw_exec = True
            continue
        saw_data = True
        if saw_exec:
            raise FortranError(st.line, 'F77S DATA must precede executable statements')
        parts = m.group(1)
        pos = 0
        while pos < len(parts):
            fst = _find_unquoted_slash(parts, pos)
            if fst == -1:
                raise FortranError(st.line, 'bad DATA statement; expected /values/')
            snd = _find_unquoted_slash(parts, fst + 1)
            if snd == -1:
                raise FortranError(st.line, 'missing closing DATA slash')
            name_src = parts[pos:fst].strip()
            val_src = parts[fst+1:snd].strip()
            if not name_src or not val_src:
                raise FortranError(st.line, 'empty DATA name or value list')
            targets = []
            for spec in split_items(name_src):
                item = re.fullmatch(r'(' + NAME + r')(?:\(\s*(\d+(?:\s*,\s*\d+){0,2})\s*\))?', spec)
                if not item:
                    raise FortranError(st.line, 'unsupported DATA object: ' + spec)
                name, idx = item.groups()
                if name not in unit.vars:
                    raise FortranError(st.line, 'DATA object not declared: ' + name)
                typ, size = unit.vars[name]
                if name in unit.args or name == unit.name:
                    raise FortranError(st.line, 'DATA cannot initialize dummy/result object')
                if idx is not None:
                    from .arrays import literal_offset
                    if size is None:
                        raise FortranError(st.line, 'DATA subscript on scalar')
                    indices = tuple(int(n.strip()) for n in idx.split(','))
                    n = literal_offset(indices, size, st.line)
                    targets.append((f'F_{name}[{n}]', typ))
                elif size is not None:
                    from .arrays import size as total_extent
                    targets.extend((f'F_{name}[{i}]', typ) for i in range(total_extent(size)))
                else:
                    targets.append((f'F_{name}', typ))
            values = []
            for token in split_items(val_src):
                rep = re.fullmatch(r'(\d+)\s*\*\s*(.+)', token)
                count, literal = (int(rep.group(1)), rep.group(2).strip()) if rep else (1, token.strip())
                if count < 1 or count > 32767:
                    raise FortranError(st.line, 'invalid DATA repeat count')
                values.extend([literal] * count)
                if len(values) > 32767:
                    raise FortranError(st.line, 'DATA list too large')
            if len(values) != len(targets):
                raise FortranError(st.line, 'DATA object/value count mismatch')
            for (target, typ), val in zip(targets, values):
                if target in used:
                    raise FortranError(st.line, 'DATA object initialized twice: ' + target)
                used.add(target)
                if typ == 'INTEGER' and re.fullmatch(r'[+-]?\d+', val):
                    if not -32768 <= int(val) <= 32767:
                        raise FortranError(st.line, 'DATA INTEGER value outside ZX-UX 16-bit range: ' + val)
                    value = val
                elif typ == 'LOGICAL' and val in ('.TRUE.', '.FALSE.'):
                    value = '1' if val == '.TRUE.' else '0'
                elif typ == 'REAL' and re.fullmatch(r'[+-]?(?:\d+\.\d*|\.\d+)(?:E[+-]?\d+)?', val):
                    value = val
                elif (typ.startswith('CHARACTER*') and
                      re.fullmatch(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"", val)):
                    from .translator import c_string
                    value = ('character', int(typ.split('*')[1]), c_string(val))
                else:
                    raise FortranError(st.line, 'DATA values must match type exactly: ' + val)
                result.append((target, value))
            pos = snd + 1
            if pos < len(parts):
                if parts[pos] != ',':
                    raise FortranError(st.line, 'DATA groups must be comma separated')
                pos += 1
                if pos == len(parts):
                    raise FortranError(st.line, 'trailing comma after DATA group')
    return result
