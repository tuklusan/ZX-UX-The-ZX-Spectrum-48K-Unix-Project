# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Restricted F77S EQUIVALENCE storage association.

Same-type numeric and same-length CHARACTER scalar/fixed array storage;
constant subscripts, overlapping groups, transitive association, the narrow
scalar named-COMMON overlap, and bounded mixed-numeric byte storage.
Partial/ambiguous COMMON and CHARACTER/numeric association remain unsupported.
"""
from __future__ import annotations
import re
from .translator import FortranError, NAME, split_items
from .arrays import size as array_size

_TERM = re.compile(r'^(' + NAME + r')(?:\s*\(\s*([\d, ]+)\s*\))?$')


def _byte_width(ty):
    if ty.startswith('CHARACTER*'):
        return int(ty.split('*')[1]) + 1
    return 5 if ty == 'REAL' else 2


def layout(unit, common_aliases):
    """Return (C local declarations, F_name -> local C storage expression)."""
    edges: dict[str, list[tuple[str, int]]] = {}
    direct_aliases: dict[str, str] = {}
    for st in unit.statements:
        if not re.match(r'^EQUIVALENCE\b', st.text):
            continue
        tail = st.text[len('EQUIVALENCE'):].strip()
        try:
            groups = split_items(tail)
        except ValueError as exc:
            raise FortranError(st.line, 'malformed EQUIVALENCE groups') from exc
        for group in groups:
            if not (group.startswith('(') and group.endswith(')')):
                raise FortranError(st.line, 'EQUIVALENCE needs parenthesized groups')
            try:
                terms = split_items(group[1:-1])
            except ValueError as exc:
                raise FortranError(st.line, 'malformed EQUIVALENCE group') from exc
            if len(terms) < 2:
                raise FortranError(st.line, 'EQUIVALENCE group needs two or more objects')
            objects = []
            for raw in terms:
                m = _TERM.fullmatch(raw)
                if not m:
                    raise FortranError(st.line, 'unsupported EQUIVALENCE object: ' + raw)
                name, subs = m.groups()
                if name not in unit.vars:
                    raise FortranError(st.line, 'undeclared EQUIVALENCE object: ' + name)
                if name in unit.args or name == unit.name:
                    raise FortranError(st.line, 'EQUIVALENCE cannot alias dummy, function or COMMON: ' + name)
                ty, dims = unit.vars[name]
                if ty not in ('INTEGER', 'REAL', 'LOGICAL') and not ty.startswith('CHARACTER*'):
                    raise FortranError(st.line, 'unsupported EQUIVALENCE type: ' + ty)
                if dims is None:
                    if subs is not None:
                        raise FortranError(st.line, 'scalar has no EQUIVALENCE subscripts: ' + name)
                    offset = 0
                else:
                    shape = (dims,) if isinstance(dims, int) else dims
                    if subs is None:
                        offset = 0
                    else:
                        values = [int(x.strip()) for x in subs.split(',')]
                        if len(values) != len(shape) or any(v < 1 or v > d for v, d in zip(values, shape)):
                            raise FortranError(st.line, 'EQUIVALENCE constant subscript out of bounds: ' + name)
                        offset, stride = 0, 1
                        for v, d in zip(values, shape):
                            offset += (v - 1) * stride
                            stride *= d
                objects.append((name, ty, offset))
            if len({o[0] for o in objects}) != len(objects):
                raise FortranError(st.line, 'same object occurs twice in EQUIVALENCE group')
            common_objects = [o for o in objects if 'F_' + o[0] in common_aliases]
            if common_objects:
                # Exact-layout COMMON can expose one member's storage sequence
                # to a local scalar or array.  Raw/mixed COMMON is intentionally
                # excluded: its typed mirrors are synchronized views rather than
                # physical aliases.
                common_meta = common_aliases.get('__COMMON_EQUIV__', {})
                if len(common_objects) != 1 or len(objects) != 2:
                    raise FortranError(st.line, 'unsupported COMMON EQUIVALENCE association')
                common_name, common_ty, _ = common_objects[0]
                local_name, local_ty, _ = next(o for o in objects if o[0] != common_name)
                if common_ty != local_ty:
                    raise FortranError(st.line, 'mixed-type COMMON EQUIVALENCE not supported')
                info = common_meta.get('F_' + common_name)
                if info is None:
                    raise FortranError(st.line, 'unsupported COMMON EQUIVALENCE association')
                common_offset = common_objects[0][2]
                if common_offset and not info['is_array']:
                    raise FortranError(st.line, 'COMMON scalar has no EQUIVALENCE subscript')
                local_offset = next(o[2] for o in objects if o[0] == local_name)
                local_count = array_size(unit.vars[local_name][1]) if unit.vars[local_name][1] else 1
                common_count = info.get('count', 1)
                base_offset = common_offset - local_offset
                if base_offset < 0 or base_offset + local_count > common_count:
                    raise FortranError(st.line, 'COMMON EQUIVALENCE storage sequence exceeds declared extent')
                base = info['base']
                if info['is_array']:
                    target = base + '[' + str(base_offset) + ']'
                else:
                    target = base
                if unit.vars[local_name][1] is None:
                    target = target
                else:
                    target = '(&' + target + ')'
                previous = direct_aliases.get('F_' + local_name)
                if previous is not None and previous != target:
                    raise FortranError(st.line, 'inconsistent COMMON EQUIVALENCE aliases')
                direct_aliases['F_' + local_name] = target
                continue
            object_types = {o[1] for o in objects}
            if any(ty.startswith('CHARACTER*') for ty in object_types) and len(object_types) != 1:
                raise FortranError(st.line, 'mixed CHARACTER/numeric EQUIVALENCE not supported')
            if not object_types <= {'INTEGER', 'REAL', 'LOGICAL'} and len(object_types) != 1:
                raise FortranError(st.line, 'unsupported mixed EQUIVALENCE types')
            anchor_name, anchor_ty, anchor_offset = objects[0]
            edges.setdefault(anchor_name, [])
            for name, ty, index in objects[1:]:
                # base(name) + index*element_bytes(name) equals the anchor address.
                # Keeping graph offsets in bytes permits mixed INTEGER/REAL/LOGICAL groups
                # without weakening exact views.
                shift = anchor_offset * _byte_width(anchor_ty) - index * _byte_width(ty)
                edges.setdefault(name, [])
                edges[anchor_name].append((name, shift))
                edges[name].append((anchor_name, -shift))
    for alias in direct_aliases:
        if alias[2:] in edges:
            raise FortranError(unit.line, 'ambiguous COMMON EQUIVALENCE association')
    declarations, aliases, seen = [], dict(direct_aliases), set()
    for initial in edges:
        if initial in seen:
            continue
        base = {initial: 0}
        stack = [initial]
        while stack:
            name = stack.pop()
            seen.add(name)
            for other, shift in edges[name]:
                value = base[name] + shift
                if other in base:
                    if base[other] != value:
                        raise FortranError(unit.line, 'inconsistent EQUIVALENCE offsets')
                else:
                    base[other] = value
                    stack.append(other)
        types = {unit.vars[name][0] for name in base}
        if any(ty.startswith('CHARACTER*') for ty in types) and len(types) != 1:
            raise FortranError(unit.line, 'mixed CHARACTER/numeric EQUIVALENCE not supported')
        if not types <= {'INTEGER', 'REAL', 'LOGICAL'} and len(types) != 1:
            raise FortranError(unit.line, 'unsupported mixed EQUIVALENCE types')
        lowest = min(base.values())
        highest = max(base[name] + (array_size(unit.vars[name][1]) if unit.vars[name][1] else 1) *
                      _byte_width(unit.vars[name][0]) for name in base)
        total = highest - lowest
        if total < 1 or total > 32767:
            raise FortranError(unit.line, 'EQUIVALENCE storage exceeds memory limits')
        ident = 'f_eq_' + str(len(declarations))
        ty = next(iter(types))
        if ty.startswith('CHARACTER*'):
            # Each character slot is length bytes plus a NUL terminator in the target C48
            # representation. Only same-width total association is allowed; a partial
            # character overlap is forbidden by F77S.
            stride = _byte_width(ty)
            declarations.append('char ' + ident + '[' + str(total) + '];')
            for name in base:
                offset = base[name] - lowest
                aliases['F_' + name] = ident if offset == 0 else '(' + ident + ' + ' + str(offset) + ')'
        elif len(types) == 1:
            stride = _byte_width(ty)
            if total % stride:
                raise FortranError(unit.line, 'EQUIVALENCE numeric storage is not element aligned')
            declarations.append(('float' if ty == 'REAL' else 'int') + ' ' + ident + '[' + str(total // stride) + '];')
            for name in base:
                offset = (base[name] - lowest) // stride
                if unit.vars[name][1] is None:
                    aliases['F_' + name] = ident + '[' + str(offset) + ']'
                else:
                    aliases['F_' + name] = ident if offset == 0 else '(&' + ident + '[' + str(offset) + '])'
        else:
            declarations.append('char ' + ident + '[' + str(total) + '];')
            sync = aliases.setdefault('__EQUIV_SYNC__',
                                      {'in': [], 'out': [], 'out_by_alias': {}})
            group_id = len(declarations) - 1
            for slot, name in enumerate(base):
                offset = base[name] - lowest
                ty, dims = unit.vars[name]
                ctype = 'float' if ty == 'REAL' else 'int'
                mirror = 'f_ev' + str(group_id) + '_' + str(slot)
                count = array_size(dims) if dims else 1
                declarations.append(ctype + ' ' + mirror +
                                    ('[' + str(count) + ']' if dims else '') + ';')
                aliases['F_' + name] = mirror
                destination = mirror if dims else '&' + mirror
                size = count * _byte_width(ty)
                sync['in'].append('memcpy(' + destination + ', ' + ident + ' + ' +
                                  str(offset) + ', ' + str(size) + ');')
                output = ('memcpy(' + ident + ' + ' + str(offset) + ', ' +
                          destination + ', ' + str(size) + ');')
                sync['out'].append(output)
                sync['out_by_alias'].setdefault(name, []).append(output)
    return declarations, aliases
