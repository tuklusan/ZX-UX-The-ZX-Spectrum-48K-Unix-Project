# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Admit Spectrum USR only after the compiler checks its operand type.

The BASIC token scan is an independent early guard for clear numeric forms.
Every remaining call must pass HiSoft's actual expression type check in
safe_usr_rt: a string returns a process UDG pointer, and a number is rejected.
No spelling-based test grants machine-code execution.
"""
from __future__ import annotations

import re
from audit_policy import scrub_code
from poke_proof import _line_text


class UnsupportedUsr(ValueError):
    pass


def _chunks(body):
    quoted = False
    current = bytearray()
    pos = 0
    while pos < len(body):
        c = body[pos]
        if not quoted and c == 0x0e:
            if pos + 5 >= len(body):
                raise UnsupportedUsr('RBC E_USR_TOKEN: Invalid numeric marker')
            current.extend(body[pos:pos + 6])
            pos += 6
            continue
        if not quoted and c == 0xea:
            break
        if c == 34:
            quoted = not quoted
        if c == 58 and not quoted:
            yield bytes(current)
            current.clear()
        elif c != 13:
            current.append(c)
        pos += 1
    yield bytes(current)


def _usr_tokens(body):
    quoted = False
    pos = 0
    count = 0
    while pos < len(body):
        b = body[pos]
        if not quoted and b == 14:
            if pos + 6 > len(body):
                raise UnsupportedUsr('RBC E_USR_TOKEN: Invalid numeric marker')
            pos += 6
            continue
        if b == 34:
            quoted = not quoted
        elif b == 0xc0 and not quoted:
            count += 1
        pos += 1
    return count


def _calls(lines, token_names):
    for line, body in lines:
        for chunk in _chunks(body):
            count = _usr_tokens(chunk)
            if not count:
                continue
            source = _line_text(chunk, token_names)
            mask = scrub_code(source)
            matches = list(re.finditer(r'(?<![\w$])USR(?![\w$])', mask, re.I))
            if len(matches) != count:
                raise UnsupportedUsr(
                    f'RBC E_USR_TOKEN: Line {line}: USR token cannot be classified')
            for match in matches:
                yield line, source[match.end():]


def _direct_numeric(tail):
    """Identify only certain numeric starts; semantic typing covers all others."""
    s = tail.lstrip()
    while s.startswith('('):
        s = s[1:].lstrip()
    # Numeric literals and functions cannot produce a graphics character. A signed
    # number includes the case USR -32768.
    return bool(re.match(
        r'^(?:[+\-]?\s*(?:\d|\.\d)|'
        r'(?:VAL(?!\$)|PEEK|CODE|RND|INT|ABS|SGN|PI|IN|LEN|ATTR|POINT|'
        r'USR|SIN|COS|TAN|ASN|ACS|ATN|SQR|EXP|LN)\b)', s, re.I))


def allow_typed_usr_findings(lines, findings, token_names=None):
    """Defer the USR memory classification to the real compiler type gate.

    This is not an approval for machine code: safe_usr_rt rejects every
    operand whose compiled type is not STRING in every compiler pass.
    Fail closed if the separate memory scan and token stream disagree.
    """
    token_names = token_names or {}
    calls = list(_calls(lines, token_names))
    tracked = [f for f in findings if f.operation == 'USR']
    if len(calls) != len(tracked):
        raise UnsupportedUsr('RBC E_USR_TOKEN: Memory scan and token count disagree')
    for (line, tail), finding in zip(calls, tracked):
        if finding.line != line:
            raise UnsupportedUsr(
                f'RBC E_USR_TOKEN: Line {line}: USR review line mismatch')
        if _direct_numeric(tail):
            raise UnsupportedUsr(
                f'RBC E_MACHINE_CODE: Line {line}: Numeric USR is prohibited')
        finding.severity = 'info'
        finding.classification = 'requires_compiler_string_type'


def enforce_numeric_usr(lines, findings, poke_proofs=None, token_names=None):
    """Independent token guard; only semantic string typing admits the call."""
    del poke_proofs
    calls = list(_calls(lines, token_names or {}))
    if findings:
        tracked = [f for f in findings if f.operation == 'USR']
        if len(calls) != len(tracked):
            raise UnsupportedUsr('RBC E_USR_TOKEN: Memory scan and token count disagree')
    for line, tail in calls:
        if _direct_numeric(tail):
            raise UnsupportedUsr(
                f'RBC E_MACHINE_CODE: Line {line}: Numeric USR is prohibited')
