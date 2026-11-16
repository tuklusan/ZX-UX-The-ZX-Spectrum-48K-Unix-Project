# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Restrict BASIC external commands to Spectrum screen and keyboard streams.

Checks token bytes; quoted strings, numeric caches, DATA and REM are inert.
"""
from __future__ import annotations

import re

PRINTER = frozenset({'LPRINT', 'LLIST', 'COPY'})
INTERFACE = frozenset({'CAT', 'FORMAT', 'MOVE', 'ERASE'})
EDITOR = frozenset({'NEW', 'LIST'})
CHANNELS = frozenset({'OPEN #', 'CLOSE #', 'PRINT', 'INPUT'})
UNSUPPORTED = PRINTER | INTERFACE | EDITOR | CHANNELS
STANDARD = frozenset({0, 1, 2})  # 0/1 keyboard, 2 screen; 3 is printer


class UnsupportedExternalIO(ValueError):
    pass


def _fail(line, code, reason):
    raise UnsupportedExternalIO(f'RBC {code}: Line {line}: {reason}')


def _literal(source):
    """Accept decimal literals only, followed by optional Sinclair number bytes."""
    match = re.match(rb'[ \t]*([0-9]+)(?:\x0e[\x00-\xff]{5})?[ \t]*', source)
    if match is None:
        return None, source
    return int(match.group(1)), source[match.end():]


def _stream(line, source, operation):
    number, rest = _literal(source)
    if number is None or not 0 <= number <= 15 or number == 3:
        _fail(line, 'E_CHANNEL_UNSAFE',
              f'{operation} needs a fixed non-printer stream (0-2 or 4-15)')
    return number, rest


def reject_external_commands(lines, token_names):
    """Permit literal K/S stream operations; reject all other external I/O."""
    names = {code: word.strip().upper() for code, word in token_names.items()
             if word.strip().upper() in UNSUPPORTED}
    if not PRINTER.issubset(set(names.values())):
        raise UnsupportedExternalIO('RBC E_EXTERNAL_IO: 48K printer tokens absent')
    available = set(STANDARD)
    for number, body in lines:
        quoted = data = False
        i = 0
        while i < len(body):
            byte = body[i]
            if byte == 34:
                quoted = not quoted
            elif not quoted and byte == 14:
                if i + 6 > len(body):
                    _fail(number, 'E_CHANNEL_UNSAFE', 'incomplete Sinclair numeric cache')
                i += 6
                continue
            elif not quoted and byte == 0xEA and not data:
                break
            elif not quoted and byte == 58:
                data = False
            elif not quoted and byte == 0xE4 and not data:
                data = True
            elif not quoted and not data and byte in names:
                name = names[byte]
                tail = body[i + 1:]
                if name in PRINTER:
                    _fail(number, 'E_EXTERNAL_IO',
                          f'{name} requires a printer unavailable in standalone RBC')
                if name in INTERFACE:
                    _fail(number, 'E_EXTERNAL_IO',
                          f'{name} requires unsupported external hardware')
                if name in EDITOR:
                    _fail(number, 'E_EDITOR_COMMAND',
                          f'{name} is an editor command, not an executable BASIC statement')
                if name == 'OPEN #':
                    stream, rest = _stream(number, tail, name)
                    channel = re.match(rb',[ \t]*"([KkSs])"[ \t]*(?=[:\r]|$)', rest)
                    if channel is None:
                        _fail(number, 'E_CHANNEL_UNSAFE',
                              'OPEN # requires a literal "K" or "S" channel')
                    available.add(stream)
                elif name == 'CLOSE #':
                    stream, rest = _stream(number, tail, name)
                    if rest and rest[:1] not in (b':', b'\r'):
                        _fail(number, 'E_CHANNEL_UNSAFE', 'CLOSE # requires a literal stream')
                    if stream not in available:
                        _fail(number, 'E_CHANNEL_UNSAFE',
                              f'{name}{stream} has no currently known channel')
                    available.remove(stream)
                elif name in ('PRINT', 'INPUT'):
                    rest = tail.lstrip(b' \t')
                    if rest.startswith(b'#'):
                        stream, after = _stream(number, rest[1:], name + ' #')
                        if not after.startswith(b';'):
                            _fail(number, 'E_CHANNEL_UNSAFE',
                                  f'{name} # needs a fixed stream followed by a semicolon')
                        if stream not in available:
                            _fail(number, 'E_CHANNEL_UNSAFE',
                                  f'{name} #{stream} has no currently known channel')
            i += 1
