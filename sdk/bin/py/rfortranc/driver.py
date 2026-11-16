# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Host command: FORTRAN -> C48 -> rcc -> ras/rld -> SSX/TZX."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import re
import struct
from .translator import FortranError, convert, parse

LINK_MAP_NAME = 'rfortranc-link-map.json'


def sdk_path(explicit=None):
    choices = [explicit, os.environ.get('ZXUX_SDK')]
    here = Path(__file__).resolve()
    choices.extend([str(here.parents[1]), str(here.parents[2]), str(here.parents[2] / 'zx-ux-sdk'),
                    str(here.parents[2] / 'src/zx-ux-sdk')])
    for candidate in choices:
        if not candidate:
            continue
        root = Path(candidate).expanduser().resolve()
        if (root / 'bin/rcc').is_file() and (root / 'bin/rtap').is_file():
            return root
        if (root / 'rcc').is_file() and (root / 'rtap').is_file() and (root / 'py/rcc').is_dir():
            return root
    return None


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _json_dims(dims):
    if dims is None or isinstance(dims, int):
        return dims
    return list(dims)


def _unit_signature(unit):
    return {
        'name': unit.name,
        'kind': unit.kind,
        'type': unit.type,
        'common': getattr(unit, 'common_layout', {}),
        'args': [
            {'name': name, 'type': unit.vars[name][0],
             'dims': _json_dims(unit.vars[name][1]),
             'external': name in getattr(unit, 'externals', set())}
            for name in unit.args
        ],
    }


def _record_calls(units):
    """Record source-level calls so retained objects carry checked contracts."""
    known = {unit.name: unit for unit in units}
    calls = []
    for caller in units:
        for statement in caller.statements:
            match = re.fullmatch(r'CALL\s+([A-Z][A-Z0-9_]*)\s*\((.*)\)', statement.text)
            if match:
                target = known.get(match.group(1))
                if target is not None:
                    calls.append({'caller': caller.name, 'target': target.name,
                                  'kind': 'subroutine',
                                  'signature': _unit_signature(target)})
            for name, target in known.items():
                if target.kind == 'function' and re.search(r'\b' + re.escape(name) + r'\s*\(',
                                                            statement.text):
                    calls.append({'caller': caller.name, 'target': name,
                                  'kind': 'function',
                                  'signature': _unit_signature(target)})
    return calls


def _write_link_map(path, units, objects, sources):
    """Save compiler-owned calling-layout data for later --link-only checks."""
    link_map = {
        'schema': 1,
        'format': 'rfortranc-f77s-link-map',
        'compiler_sha256': _sha256(Path(__file__).with_name('translator.py')),
        'sources': [{'name': source.name, 'sha256': _sha256(source)} for source in sources],
        'units': [_unit_signature(unit) for unit in units],
        'calls': _record_calls(units),
        'objects': [
            {'name': obj.name, 'unit': unit.name, 'sha256': _sha256(obj)}
            for obj, unit in zip(objects, units)
        ],
    }
    destination = Path(path)
    temporary = destination.with_name(destination.name + '.tmp')
    temporary.write_text(json.dumps(link_map, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    temporary.replace(destination)


def _validate_link_map(path, objects):
    """Validate retained SSO hashes and source-level FORTRAN call contracts."""
    link_map_path = Path(path).resolve()
    try:
        link_map = json.loads(link_map_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ValueError('cannot read compiler interface link map: ' + str(link_map_path)) from exc
    if link_map.get('schema') != 1 or link_map.get('format') != 'rfortranc-f77s-link-map':
        raise ValueError('unsupported compiler interface link map: ' + str(link_map_path))
    entries = link_map.get('objects')
    units = link_map.get('units')
    calls = link_map.get('calls', [])
    if not isinstance(entries, list) or not isinstance(units, list) or not isinstance(calls, list):
        raise ValueError('malformed compiler interface link map: ' + str(link_map_path))
    by_name = {Path(entry.get('name', '')).name: entry for entry in entries
               if isinstance(entry, dict)}
    if len(by_name) != len(entries):
        raise ValueError('compiler interface link map has duplicate or invalid object names')
    actual = {Path(obj).name: Path(obj).resolve() for obj in objects}
    if set(by_name) != set(actual):
        raise ValueError('compiler interface link map object set does not match link inputs')
    for name, obj in actual.items():
        entry = by_name[name]
        if entry.get('sha256') != _sha256(obj):
            raise ValueError('compiler interface object hash mismatch: ' + name)
        if not entry.get('unit'):
            raise ValueError('compiler interface object has no program-unit name: ' + name)
    unit_by_name = {entry.get('name'): entry for entry in units
                    if isinstance(entry, dict) and entry.get('name')}
    if len(unit_by_name) != len(units):
        raise ValueError('compiler interface link map has duplicate or invalid unit signatures')
    object_units = {entry['unit'] for entry in by_name.values()}
    if not object_units <= set(unit_by_name):
        raise ValueError('compiler interface object refers to an unknown program unit')
    for call in calls:
        if not isinstance(call, dict) or call.get('target') not in unit_by_name:
            raise ValueError('compiler interface link map has an unresolved call target')
        target = unit_by_name[call['target']]
        if call.get('signature') != target:
            raise ValueError('compiler interface call signature does not match target unit: ' + call['target'])
        expected_kind = 'function' if target.get('kind') == 'function' else 'subroutine'
        if call.get('kind') != expected_kind:
            raise ValueError('compiler interface call kind does not match target unit: ' + call['target'])
    # Validate the retained source-level COMMON contracts.  Identical views must remain
    # identical across objects; intentionally alternate views are legal and are retained as
    # separate contracts for raw/mirrored storage.
    common_blocks = {}
    for unit in units:
        common = unit.get('common', {})
        if not isinstance(common, dict):
            raise ValueError('compiler interface unit has malformed COMMON layout: ' + str(unit.get('name')))
        for block, members in common.items():
            if not isinstance(block, str) or not re.fullmatch(r'[0-9A-Z]{1,6}', block):
                raise ValueError('compiler interface COMMON block name is invalid: ' + str(block))
            if not isinstance(members, list) or not members:
                raise ValueError('compiler interface COMMON block has no ordered members: ' + block)
            normalized = []
            for member in members:
                if not isinstance(member, dict):
                    raise ValueError('compiler interface COMMON member is malformed: ' + block)
                name = member.get('name')
                ty = member.get('type')
                count = member.get('count')
                is_array = member.get('is_array')
                if (not isinstance(name, str) or not re.fullmatch(r'[A-Z][A-Z0-9]{0,5}', name)
                        or ty not in ('INTEGER', 'REAL', 'LOGICAL') and
                        not (isinstance(ty, str) and re.fullmatch(r'CHARACTER\*[1-9][0-9]{0,2}', ty))
                        or not isinstance(count, int) or count < 1
                        or not isinstance(is_array, bool)):
                    raise ValueError('compiler interface COMMON member is invalid: ' + block + '/' + str(name))
                normalized.append((name, ty, count, is_array))
            common_blocks.setdefault(block, []).append((unit.get('name'), tuple(normalized)))
    for block, views in common_blocks.items():
        if block == '0':
            continue
        # The link map records all views, including legal alternate
        # layouts; reject only duplicate unit declarations, which cannot
        # be a valid cross-source layout.
        owners = [unit_name for unit_name, _view in views]
        if len(owners) != len(set(owners)):
            raise ValueError('compiler interface COMMON block is duplicated within a unit: ' + block)
    return link_map


def _rcc_controls(args):
    """Return managed rcc controls for a monolithic C48 build."""
    controls = []
    if args.fit:
        controls.append('--fit')
    if args.native:
        controls.append('--native')
    if args.bytecode:
        controls.append('--bytecode')
    if args.no_fit:
        controls.append('--no-fit')
    if args.max is not None:
        controls.extend(['--max', str(args.max)])
    if args.stack is not None:
        controls.extend(['--stack', str(args.stack)])
    if args.heap is not None:
        controls.extend(['--heap', str(args.heap)])
    if args.udgs is not None:
        controls.extend(['--udgs', str(args.udgs)])
    return controls

def link_existing_objects(sdk, packaged, objects, target, args, rtap, tape_name):
    """Link retained native Z80 SSO objects without FORTRAN source parsing.

    Compiler-produced object directories carry a sidecar link map. When
    present, validate its object hashes and source-level signatures before the
    linker; raw SSO inputs without a link map remain linker/symbol-only.
    """
    link_map = Path(args.link_map).resolve() if args.link_map else None
    if link_map is None:
        candidate = Path(objects[0]).resolve().parent / LINK_MAP_NAME if objects else None
        if candidate is not None and candidate.is_file():
            link_map = candidate
    if link_map is not None:
        _validate_link_map(link_map, objects)
    linker = sdk / ('rld' if packaged else 'bin/rld')
    library = sdk / ('py/lib/libc48.ssa' if packaged else 'lib/libc48.ssa')
    if not linker.is_file() or not library.is_file():
        raise ValueError('ZX-UX SDK linker/library missing for object linkage')
    for obj in objects:
        if obj.suffix.lower() != '.sso' or not obj.is_file():
            raise ValueError('link input must be an existing SSO object: ' + str(obj))
    if not objects:
        raise ValueError('at least one SSO object required')
    with tempfile.TemporaryDirectory(prefix='rfortranc-link-') as scratch:
        binary = Path(scratch) / 'linked.ssx' if args.tzx else target
        linkcmd = [sys.executable, str(linker), '-o', str(binary)]
        if args.stack is not None:
            linkcmd += ['--stack', str(args.stack)]
        linkcmd += [str(obj) for obj in objects] + [str(library)]
        rc = subprocess.run(linkcmd, check=False)
        if rc.returncode:
            if not args.tzx:
                binary.unlink(missing_ok=True)
            return rc.returncode
        # Header describes reserved RAM, NOT observed runtime high-water.
        blob = binary.read_bytes()
        if len(blob) < 22 or blob[:4] != b'SSX1':
            binary.unlink(missing_ok=True)
            raise ValueError('linker generated an invalid SSX image')
        _, _, image, bss, stack, heap, _, _, _ = struct.unpack_from('<BBHHHHHHH', blob, 4)
        need = max(len(blob), image + bss + stack + heap)
        if need > (args.max if args.max is not None else 14000):
            binary.unlink(missing_ok=True)
            raise ValueError('linked SSX exceeds memory limit: ' + str(need))
        if not args.tzx:
            return 0
        if not (1 <= len(tape_name) <= 10 and
                all(32 < ord(c) < 127 and c != '/' for c in tape_name)):
            raise ValueError('TZX program name must have 1..10 printable ASCII chars without /')
        return subprocess.run([sys.executable, str(rtap), '-o', str(target),
                               str(binary) + '=' + tape_name], check=False).returncode


def main(argv=None):
    p = argparse.ArgumentParser(prog='rfortranc', description='FORTRAN 77 subset to ZX-UX SSX/TZX')
    p.add_argument('source', nargs='+', help='FORTRAN source .f or .for')
    p.add_argument('--separate', action='store_true', help='compile each F77S program unit to SSO and link them')
    p.add_argument('--link-only', action='store_true', help='link retained Z80 SSO objects without FORTRAN source')
    p.add_argument('--object-dir', help='preserve per-unit SSO objects (requires --separate)')
    p.add_argument('--link-map', help='F77S compiler interface link map for retained SSO validation')
    p.add_argument('-o', '--output', help='output file (default SOURCE.ssx)')
    p.add_argument('--sdk', help='ZX-UX source SDK root or packaged SDK bin')
    p.add_argument('--std', choices=('zxux', 'f77s'), default='zxux',
                   help='zxux extensions (default) or partial ANSI subset validation')
    modes = p.add_mutually_exclusive_group()
    modes.add_argument('-S', action='store_true', help='output Z80 assembly')
    modes.add_argument('-c', action='store_true', help='output SSO relocatable object')
    modes.add_argument('--emit-c', action='store_true',
                       help='write generated C48 source and stop before the SDK')
    modes.add_argument('--tzx', action='store_true', help='emit TZX cassette image')
    backend = p.add_mutually_exclusive_group()
    backend.add_argument('--fit', action='store_true',
                         help='force rcc automatic backend fitting (the default)')
    backend.add_argument('--native', action='store_true', help='native Z80 code; skip automatic fit')
    backend.add_argument('--bytecode', action='store_true', help='use C48 bytecode backend')
    backend.add_argument('--no-fit', action='store_true', help='disable automatic fitting')
    p.add_argument('--max', type=int, help='max bytes required in ZX-UX memory')
    p.add_argument('--stack', type=int, help='reserved stack bytes')
    p.add_argument('--heap', type=int, help='rcc heap reservation in bytes')
    p.add_argument('--udgs', type=int, help='rcc UDG reservation, from 4 through 32')
    p.add_argument('--save-c', metavar='PATH',
                   help='save generated C48 source to PATH and continue the build')
    p.add_argument('--tape-name', help='ZX-UX program name (1..10 ASCII chars; --tzx only)')
    args = p.parse_args(argv)
    suffix = '.c' if args.emit_c else '.s' if args.S else '.sso' if args.c else '.tzx' if args.tzx else '.ssx'
    target = Path(args.output or str(Path(args.source[0]).with_suffix(suffix))).resolve()
    sources = [Path(item).resolve() for item in args.source]
    try:
        if args.tape_name is not None and not args.tzx:
            raise ValueError('--tape-name requires --tzx')
        if target in sources:
            raise ValueError('output would overwrite FORTRAN source')
        if args.save_c and args.emit_c:
            raise ValueError('--save-c cannot be combined with --emit-c')
        if args.save_c:
            saved_c = Path(args.save_c).resolve()
            if saved_c in sources or saved_c == target:
                raise ValueError('--save-c would overwrite an input or output file')
        if args.heap is not None and args.heap < 0:
            raise ValueError('--heap must be non-negative')
        if args.udgs is not None and not 4 <= args.udgs <= 32:
            raise ValueError('--udgs must be between 4 and 32')
        if len(sources) > 1 and not (args.separate or args.link_only):
            raise ValueError('multiple sources require --separate')
        if args.object_dir and not args.separate:
            raise ValueError('--object-dir requires --separate')
        if args.link_map and not (args.separate or args.link_only):
            raise ValueError('--link-map requires --separate or --link-only')
        if args.separate and (args.std != 'f77s' or args.emit_c or args.save_c or args.S or args.c or
                              args.fit or args.bytecode or args.no_fit or args.heap is not None or
                              args.udgs is not None):
            raise ValueError('--separate needs --std f77s with linked native SSX/TZX output')
        if args.link_only:
            if (args.separate or args.std != 'f77s' or args.emit_c or args.S or args.c or
                    args.save_c or args.fit or args.bytecode or args.no_fit or args.object_dir or
                    args.heap is not None or args.udgs is not None):
                raise ValueError('--link-only requires --std f77s with native SSX/TZX objects')
            sdk = sdk_path(args.sdk)
            if not sdk:
                raise ValueError('ZX-UX SDK not found; pass --sdk or set ZXUX_SDK')
            packaged = (sdk / 'py/rcc').is_dir()
            rtap = sdk / ('rtap' if packaged else 'bin/rtap')
            name = args.tape_name if args.tape_name is not None else sources[0].stem[:10]
            return link_existing_objects(sdk, packaged, sources, target, args, rtap, name)
        program = ''.join(source.read_text(encoding='utf-8').rstrip('\n') + '\n' for source in sources)
        units = parse(program, std=args.std)
        if args.std == 'f77s':
            from .f77s import validate_source
            validate_source(program, units)
        c48 = convert(units) if not args.separate else None
        if args.save_c:
            Path(args.save_c).resolve().write_text(c48, encoding='utf-8')
        if args.emit_c:
            target.write_text(c48, encoding='utf-8')
            return 0
        sdk = sdk_path(args.sdk)
        if not sdk:
            raise ValueError('ZX-UX SDK not found; pass --sdk or set ZXUX_SDK')
        packaged = (sdk / 'py/rcc').is_dir()
        rcc = sdk / ('rcc' if packaged else 'bin/rcc')
        rtap = sdk / ('rtap' if packaged else 'bin/rtap')
        with tempfile.TemporaryDirectory(prefix='rfortranc-') as scratch:
            tmp = Path(scratch)
            if args.separate:
                linker = sdk / ('rld' if packaged else 'bin/rld')
                library = sdk / ('py/lib/libc48.ssa' if packaged else 'lib/libc48.ssa')
                if not linker.is_file() or not library.is_file():
                    raise ValueError('ZX-UX SDK linker/library missing for --separate')
                objects = []
                preserved = Path(args.object_dir).resolve() if args.object_dir else None
                if preserved:
                    preserved.mkdir(parents=True, exist_ok=True)
                for i, u in enumerate(units):
                    unit_name = '%02d_%s' % (i, u.name)
                    generated = tmp / (unit_name + '.c')
                    obj = (preserved if preserved else tmp)/(unit_name + '.sso')
                    generated.write_text(convert(units, emit_units={u.name}), encoding='utf-8')
                    rc = subprocess.run([sys.executable, str(rcc), '-c', '--native',
                                         '-o', str(obj), str(generated)], check=False)
                    if rc.returncode:
                        return rc.returncode
                    objects.append(obj)
                if preserved:
                    link_map_path = (Path(args.link_map).resolve()
                                     if args.link_map else preserved / LINK_MAP_NAME)
                    _write_link_map(link_map_path, units, objects, sources)
                name = args.tape_name if args.tape_name is not None else sources[0].stem[:10]
                return link_existing_objects(sdk, packaged, objects, target, args, rtap, name)
            generated = tmp / (sources[0].stem + '.c')
            generated.write_text(c48, encoding='utf-8')
            binary = tmp / (sources[0].stem + '.ssx') if args.tzx else target
            cmd = [sys.executable, str(rcc), str(generated), '-o', str(binary)]
            if args.S:
                cmd.append('-S')
            if args.c:
                cmd.append('-c')
            cmd.extend(_rcc_controls(args))
            result = subprocess.run(cmd, check=False)
            if result.returncode:
                return result.returncode
            if args.tzx:
                # ZX-UX rtap stores a name of at most ten printable ASCII chars.
                name = args.tape_name if args.tape_name is not None else sources[0].stem[:10]
                if not (1 <= len(name) <= 10 and all(32 < ord(c) < 127 and c != '/' for c in name)):
                    raise ValueError('TZX program name must have 1..10 printable ASCII chars without /')
                return subprocess.run([sys.executable, str(rtap), '-o', str(target),
                                       str(binary) + '=' + name], check=False).returncode
        return 0
    except (OSError, ValueError, FortranError) as e:
        print('rfortranc: ' + str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
