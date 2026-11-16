# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""ANSI F77S COMMON storage association.

Fixed scalar and constant-bound INTEGER/REAL/LOGICAL arrays are handled here.
Layout uses storage sequence position; array extents can differ in rank if the
flat storage extent and numeric element type agree. Exact matching views retain
the compact typed representation; incompatible numeric views share a bounded
byte buffer with typed aliases. F77S SAVE /name/ is validated.
"""
import re
from .translator import FortranError, NAME, split_items


def layout(units):
    blocks = {}
    uses = {}
    view_records = {}
    raw_blocks = set()
    for unit in units:
        per_block = {}
        per_block_names = {}
        per_name = {}
        for st in unit.statements:
            if not re.match(r'^COMMON\b', st.text):
                continue
            m = re.fullmatch(r'COMMON\s+/([A-Z][A-Z0-9]{0,5})/\s*(.+)', st.text)
            if m:
                block, item_text = m.groups()
            else:
                m = re.fullmatch(r'COMMON\s*//\s*(.+)', st.text)
                if not m:
                    m = re.fullmatch(r'COMMON\s+([^/].*)', st.text)
                if not m:
                    raise FortranError(st.line, 'unsupported COMMON syntax (expected /name/, // or variable list)')
                block, item_text = '0', m.group(1)  # internal blank-block key
            members = per_block.setdefault(block, [])
            names = per_block_names.setdefault(block, [])
            for token in split_items(item_text):
                name = token.strip()
                if not re.fullmatch(NAME, name) or len(name) > 6:
                    raise FortranError(st.line, 'COMMON requires scalar F77S names of 1..6 chars')
                if name in per_name:
                    raise FortranError(st.line, 'duplicate COMMON member: ' + name)
                if name in unit.args or name == unit.name:
                    raise FortranError(st.line, 'COMMON member cannot be dummy/function result')
                spec = unit.vars.get(name)
                if spec is None:
                    from .implicit import mapping
                    unit.vars[name] = (mapping(unit.statements)[name[0]], None)
                    spec = unit.vars[name]
                if spec[0] not in ('INTEGER', 'REAL', 'LOGICAL') and not spec[0].startswith('CHARACTER*'):
                    raise FortranError(st.line, 'COMMON requires numeric/LOGICAL/CHARACTER variable: ' + name)
                if spec[1] is None:
                    length, is_array = 1, False
                else:
                    from .arrays import size as total_extent
                    length, is_array = total_extent(spec[1]), True
                signature = (spec[0], length, is_array)
                slot = len(members)
                # C48 identifiers have a 15-char maximum.
                if slot > 99:
                    raise FortranError(st.line, 'COMMON block exceeds 100 scalar slots')
                entry = signature
                members.append(entry)
                names.append(name)
                per_name[name] = 'f_com_' + block + '_' + str(slot)
        # ANSI F77S Appendix D3.8: SAVE permits *only* named COMMON blocks. COMMON objects
        # are emitted as static storage, so this is a checked source-level lifetime
        # declaration, not an extra allocation.
        saved = set()
        for st in unit.statements:
            if not re.match(r'^SAVE\b', st.text):
                continue
            tail = st.text[4:].strip()
            if not tail:
                raise FortranError(st.line, 'F77S SAVE must list named COMMON blocks')
            try:
                entries = split_items(tail)
            except ValueError as exc:
                raise FortranError(st.line, 'malformed SAVE common block list') from exc
            for entry in entries:
                m = re.fullmatch(r'/([A-Z][A-Z0-9]{0,5})/', entry.strip())
                if not m:
                    raise FortranError(st.line, 'F77S SAVE accepts only /named COMMON/ blocks')
                name = m.group(1)
                if name not in per_block:
                    raise FortranError(st.line, 'SAVE names COMMON block absent from unit: /' + name + '/')
                if name in saved:
                    raise FortranError(st.line, 'duplicate SAVE common block: /' + name + '/')
                saved.add(name)
        for block, members in per_block.items():
            types = list(members)
            if block not in blocks:
                blocks[block] = types
            elif block == '0':
                # Blank COMMON may have different extents in distinct units. Keep the
                # longest storage sequence, but still reject an incompatible view of any
                # overlapping declared slot.
                previous = blocks[block]
                if any(a != b for a, b in zip(previous, types)):
                    raw_blocks.add(block)
                if len(types) > len(previous):
                    blocks[block] = types
            elif blocks[block] != types:
                raw_blocks.add(block)
        for block, members in per_block.items():
            view_records.setdefault(block, []).append(
                (unit.name, list(zip(per_block_names[block], members))))
        if per_block:
            # Keep a source-level COMMON view layout for retained-object manifests.
            # This is separate from the generated aliases: the linker-side
            # validator needs the ordered storage sequence even when the target
            # uses raw/mirrored storage. The linker still needs the original order.
            block_signatures = uses.setdefault(unit.name, {}).setdefault('__COMMON_LAYOUT__', {})
            for block, members in per_block.items():
                block_signatures[block] = [
                    {'name': name, 'type': signature[0], 'count': signature[1],
                     'is_array': signature[2]}
                    for name, signature in zip(per_block_names[block], members)
                ]
        if per_name:
            # F77S permits DATA of unrelated local objects in a unit which declares COMMON.
            # Only objects stored in COMMON are forbidden: initializing named COMMON would
            # require excluded BLOCK DATA.
            if any(re.match(r'^DATA\s+', st.text) for st in unit.statements):
                from .data_init import initializers
                for target, _value in initializers(unit):
                    object_name = re.match(r'^F_([A-Z][A-Z0-9_]*)(?:\[|$)', target)
                    if object_name and object_name.group(1) in per_name:
                        raise FortranError(unit.line, 'DATA cannot initialize COMMON member: ' + object_name.group(1))
            uses.setdefault(unit.name, {}).update(
                {'F_' + key: value for key, value in per_name.items()})
    result=[]
    for block in sorted(blocks):
        if block in raw_blocks:
            continue
        for slot, (ty, count, is_array) in enumerate(blocks[block]):
            if ty.startswith('CHARACTER*'):
                byte_count = count * (int(ty.split('*')[1]) + 1)
                result.append('static char f_com_' + block + '_' + str(slot) + '[' + str(byte_count) + '];')
            else:
                result.append('static ' + ('float' if ty == 'REAL' else 'int') + ' f_com_' + block + '_' + str(slot)
                              + ('[' + str(count) + ']' if is_array else '') + ';')

    # Preserve enough exact-layout information for EQUIVALENCE to name a storage-sequence
    # element.  Raw/mixed blocks deliberately do not get this metadata: their per-unit
    # mirrors are not physical aliases and need the more involved synchronized
    # representation handled elsewhere.
    for block, views in view_records.items():
        if block in raw_blocks:
            continue
        for unit_name, entries in views:
            metadata = uses.setdefault(unit_name, {}).setdefault('__COMMON_EQUIV__', {})
            for slot, (name, signature) in enumerate(entries):
                ty, count, is_array = signature
                metadata['F_' + name] = {
                    'base': 'f_com_' + block + '_' + str(slot),
                    'type': ty,
                    'count': count,
                    'is_array': is_array,
                }

    def byte_size(signature):
        ty, count, _is_array = signature
        if ty.startswith('CHARACTER*'):
            return count * (int(ty.split('*')[1]) + 1)
        return count * (5 if ty == 'REAL' else 2)

    # Incompatible views use raw bytes. Exact-layout blocks above retain their typed globals
    # and calling layout. Same-width CHARACTER views can alias the existing terminated
    # representation; differing widths use packed FORTRAN bytes plus per-unit mirrors so C
    # NUL terminators never become storage data.
    for block in sorted(raw_blocks):
        views = view_records[block]
        char_signatures = [signature for _unit_name, entries in views
                           for _name, signature in entries
                           if signature[0].startswith('CHARACTER*')]
        if char_signatures:
            all_signatures = [signature for _unit_name, entries in views
                              for _name, signature in entries]
            widths = {int(signature[0].split('*')[1]) for signature in char_signatures}
            if len(char_signatures) != len(all_signatures):
                raise FortranError(1, 'COMMON block character storage views mismatch')
            if len(widths) == 1:
                total = max(sum(byte_size(signature) for _name, signature in entries)
                            for _unit_name, entries in views)
            else:
                total = max(sum(signature[1] * int(signature[0].split('*')[1])
                                for _name, signature in entries)
                            for _unit_name, entries in views)
            if total < 1 or total > 32767:
                raise FortranError(1, 'COMMON storage exceeds target memory limits')
            storage = 'f_com_' + block
            result.append('static char ' + storage + '[' + str(total) + '];')
            if len(widths) != 1:
                for view_id, (unit_name, entries) in enumerate(views):
                    aliases = uses.setdefault(unit_name, {})
                    sync = aliases.setdefault('__COMMON_SYNC__', {'in': [], 'out': []})
                    offset = 0
                    for slot, (name, signature) in enumerate(entries):
                        ty, count, _is_array = signature
                        width = int(ty.split('*')[1])
                        mirror = 'f_cc' + str(view_id) + '_' + str(slot)
                        result.append('static char ' + mirror + '[' +
                                      str(count * (width + 1)) + '];')
                        aliases['F_' + name] = mirror
                        for element in range(count):
                            raw = storage + ' + ' + str(offset + element * width)
                            view = mirror + ' + ' + str(element * (width + 1))
                            sync['in'].append('memcpy(' + view + ', ' + raw + ', ' +
                                              str(width) + ');')
                            sync['in'].append(mirror + '[' +
                                              str(element * (width + 1) + width) + '] = 0;')
                            sync['out'].append('memcpy(' + raw + ', ' + view + ', ' +
                                               str(width) + ');')
                        offset += count * width
                continue
            for unit_name, entries in views:
                aliases = uses.setdefault(unit_name, {})
                offset = 0
                for name, signature in entries:
                    aliases['F_' + name] = storage + ' + ' + str(offset)
                    offset += byte_size(signature)
            continue
        total = max(sum(byte_size(signature) for _name, signature in entries)
                    for _unit_name, entries in views)
        if total < 1 or total > 32767:
            raise FortranError(1, 'COMMON storage exceeds target memory limits')
        storage = 'f_com_' + block
        result.append('static char ' + storage + '[' + str(total) + '];')
        types = {signature[0] for _unit_name, entries in views
                 for _name, signature in entries}
        if len(types) == 1:
            # Same-type extent/rank variations retain the compact raw-byte association.
            # C48 accepts the single typed cast used here; mixed INTEGER/REAL casts are
            # rejected by its parser.
            for unit_name, entries in views:
                aliases = uses.setdefault(unit_name, {})
                offset = 0
                for name, signature in entries:
                    ty, _count, is_array = signature
                    ctype = 'float' if ty == 'REAL' else 'int'
                    base = '((' + ctype + ' *)(' + storage + ' + ' + str(offset) + '))'
                    aliases['F_' + name] = base if is_array else '*' + base
                    offset += byte_size(signature)
            continue
        # C48 rejects pointer casts between the raw byte buffer and a typed scalar.
        # Give each incompatible view a typed mirror and explicitly move its bytes at
        # unit entry, before/after SUBROUTINE calls, and on return.  The raw buffer
        # retains the storage-sequence layout.
        for view_id, (unit_name, entries) in enumerate(views):
            aliases = uses.setdefault(unit_name, {})
            sync = aliases.setdefault('__COMMON_SYNC__', {'in': [], 'out': []})
            offset = 0
            for slot, (name, signature) in enumerate(entries):
                ty, count, is_array = signature
                ctype = 'float' if ty == 'REAL' else 'int'
                mirror = 'f_cm' + str(view_id) + '_' + str(slot)
                result.append('static ' + ctype + ' ' + mirror +
                              ('[' + str(count) + ']' if is_array else '') + ';')
                aliases['F_' + name] = mirror
                destination = mirror if is_array else '&' + mirror
                sync['in'].append('memcpy(' + destination + ', ' + storage + ' + ' +
                                  str(offset) + ', ' + str(byte_size(signature)) + ');')
                sync['out'].append('memcpy(' + storage + ' + ' + str(offset) + ', ' +
                                   destination + ', ' + str(byte_size(signature)) + ');')
                offset += byte_size(signature)
    return result, uses


def bind(text, aliases):
    """Replace exact generated C variable names, never literal contents."""
    if not aliases:
        return text
    tokens = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\bF_[A-Z][A-Z0-9_]*\b')
    return tokens.sub(lambda m: aliases.get(m.group(), m.group()), text)
