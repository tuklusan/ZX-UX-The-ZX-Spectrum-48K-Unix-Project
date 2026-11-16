# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""ANSI X3.9-1978 subset-specific *partial* validation, Appendix D.

This is an opt-in compatibility gate, not an assertion of F77S conformance.
Keep the original ZX-UX extension mode for existing source programs.
"""
from __future__ import annotations
import re
from .translator import FortranError, split_items

_WORD = r'[A-Z][A-Z0-9_]*'
def _integer_control(text, unit):
    """An F77S DO bound/step is a target INTEGER constant or scalar name."""
    token = text.strip()
    if re.fullmatch(r'[+-]?\d+', token):
        return -32768 <= int(token) <= 32767
    return bool(re.fullmatch(_WORD, token) and
                unit.vars.get(token) == ('INTEGER', None))



def validate_source(source, units):
    """Reject known full-F77/ZX-UX-only forms and subset constraint violations.

    A source accepted by this gate is NOT necessarily conforming to F77S;
    unsupported required features are still rejected by the compiler.
    """
    continuation = 0
    previous_comment = False
    statement_seen = False
    for number, raw in enumerate(source.splitlines(), 1):
        if '\t' in raw[:72]:
            raise FortranError(number, 'tab is not a fixed-form F77S source character')
        raw = raw.expandtabs(8)
        if not raw.strip():
            previous_comment = False
            continue
        if raw[0] in '*Cc':
            previous_comment = True
            continue
        if raw[0] == '!':
            raise FortranError(number, 'F77S uses fixed-form C/* comments, not ! comments')
        if len(raw) < 6:
            raise FortranError(number, 'F77S requires fixed-form columns 1-6')
        if not re.fullmatch(r'[ 0-9]{5}', raw[:5]):
            raise FortranError(number, 'F77S requires a numeric label in columns 1-5')
        if raw[:5].strip() and int(raw[:5].replace(' ', '')) == 0:
            raise FortranError(number, 'F77S statement label must be in 1..99999')
        if raw[5] != ' ' and raw[5] != '0':
            if raw[:5].strip():
                raise FortranError(number, 'continuation line may not carry a statement label')
            if previous_comment:
                raise FortranError(number, 'F77S prohibits comment immediately before continuation')
            if not statement_seen:
                raise FortranError(number, 'F77S continuation without preceding statement')
            continuation += 1
            if continuation > 9:
                raise FortranError(number, 'F77S permits at most nine continuation lines')
        else:
            continuation = 0
            statement_seen = True
        previous_comment = False
        body = raw[6:72]
        # Strip character literals before checking punctuation (except fixed comments).
        clean = re.sub(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"", '', body)
        if '_' in clean:
            raise FortranError(number, 'underscore is not an ANSI F77S source name character')
        if '!' in clean or chr(36) in clean or ':' in clean:
            raise FortranError(number, 'non-F77S source character in statement')
    for unit in units:
        if len(unit.name) > 6 or '_' in unit.name:
            raise FortranError(unit.line, 'F77S names have at most six letters/digits')
        for name in unit.vars:
            if len(name) > 6 or '_' in name:
                raise FortranError(unit.line, 'F77S names have at most six letters/digits: ' + name)
        for name in unit.args:
            if len(name) > 6 or '_' in name:
                raise FortranError(unit.line, 'F77S dummy name exceeds six characters')
        for st in unit.statements:
            s = st.text.strip()
            if re.match(r'^PRINT\b', s):
                raise FortranError(st.line, 'PRINT is excluded from ANSI F77S (use formatted WRITE)')
            if re.match(r'^READ\s*\*\s*,', s) or re.match(r'^WRITE\s*\(\s*[^,]+,\s*\*', s):
                raise FortranError(st.line, 'list-directed I/O is excluded from ANSI F77S')
            if s == 'IMPLICIT NONE':
                raise FortranError(st.line, 'IMPLICIT NONE is not ANSI F77S')
            if re.match(r'^(PARAMETER|BLOCK DATA|ENTRY|CLOSE|INQUIRE|DOUBLE PRECISION|COMPLEX)\b', s):
                raise FortranError(st.line, 'statement excluded from ANSI F77S: ' + s.split()[0])
            m = re.fullmatch(r'DO\s+(\d+)\s+(' + _WORD + r')\s*=\s*(.+)', s)
            if m:
                vals = split_items(m.group(3))
                if (unit.vars.get(m.group(2)) != ('INTEGER', None) or
                        len(vals) not in (2, 3) or
                        any(not _integer_control(v, unit) for v in vals)):
                    raise FortranError(st.line, 'F77S DO variable, bounds and step must be INTEGER scalars or 16-bit constants')
            m = re.fullmatch(r'GO\s*TO\s*\([^()]*\)\s*,?\s*(.*)', s)
            if m and not re.fullmatch(_WORD, m.group(1)):
                raise FortranError(st.line, 'F77S computed GO TO selector must be an INTEGER variable')
            # F77S I/O data items are checked during compiler lowering. The shared
            # expander handles fixed whole arrays, implied DO, restrictions on
            # subscripts and named-variable items.
