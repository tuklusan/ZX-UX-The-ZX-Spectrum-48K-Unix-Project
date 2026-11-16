# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""ANSI FORTRAN SUBSET implicit numeric/logical/character typing (partial).

Implicit defaults: I-N INTEGER, other letters REAL. Supports explicit
IMPLICIT INTEGER/REAL/LOGICAL/CHARACTER letter and letter-range groups. It does not
change the default ZX-UX mode which requires explicit declarations.
"""
from __future__ import annotations
import re
from .translator import FortranError, NAME

DEFAULT = {chr(n): 'INTEGER' if 'I' <= chr(n) <= 'N' else 'REAL'
           for n in range(ord('A'), ord('Z') + 1)}
KEYWORDS = set('PROGRAM END INTEGER REAL LOGICAL IMPLICIT DIMENSION COMMON SAVE EQUIVALENCE CHARACTER FUNCTION SUBROUTINE EXTERNAL INTRINSIC DO IF THEN ELSE ENDIF GO TO GOTO ASSIGN PAUSE REWIND BACKSPACE ENDFILE CALL READ WRITE PRINT FORMAT CONTINUE STOP RETURN MOD AND OR NOT EQ NE LT LE GT GE TRUE FALSE'.split())
LITERALS = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"")
NUMBERS = re.compile(r'(?<![A-Z0-9_])(?:\d+\.?\d*|\.\d+)(?:[ED][+-]?\d+)?')


def mapping(statements):
    result = dict(DEFAULT)
    changed = set()
    for st in statements:
        if not st.text.startswith('IMPLICIT '):
            continue
        rest = st.text[len('IMPLICIT '):].strip()
        if rest == 'NONE':
            raise FortranError(st.line, 'IMPLICIT NONE is outside ANSI F77S')
        while rest:
            part = re.match(
                r'^\s*(INTEGER|REAL|LOGICAL|CHARACTER(?:\s*\*\s*(?:\d+|\(\s*\d+\s*\)))?)'
                r'\s*\(([^()]*)\)\s*(?:,\s*|$)', rest)
            if not part:
                raise FortranError(st.line, 'unsupported F77S IMPLICIT declaration')
            ty, ranges = part.group(1), part.group(2)
            if ty.startswith('CHARACTER'):
                length_spec = re.fullmatch(
                    r'CHARACTER(?:\s*\*\s*(?:([0-9]+)|\(\s*([0-9]+)\s*\)))?', ty)
                width = int(length_spec.group(1) or length_spec.group(2) or 1)
                if not 1 <= width <= 255:
                    raise FortranError(st.line, 'F77S IMPLICIT CHARACTER length must be 1..255')
                ty = 'CHARACTER*' + str(width)
            for range_item in ranges.split(','):
                pair = re.fullmatch(r'\s*([A-Z])\s*(?:-\s*([A-Z]))?\s*', range_item)
                if not pair:
                    raise FortranError(st.line, 'bad IMPLICIT letter range: ' + range_item)
                first, last = pair.group(1), pair.group(2) or pair.group(1)
                if first > last:
                    raise FortranError(st.line, 'reversed IMPLICIT letter range')
                for ordinal in range(ord(first), ord(last)+1):
                    letter = chr(ordinal)
                    if letter in changed:
                        raise FortranError(st.line, 'duplicate IMPLICIT letter: ' + letter)
                    changed.add(letter)
                    result[letter] = ty
            rest = rest[part.end():]
    return result


def infer(u, known):
    types = mapping(u.statements)
    explicitly_typed = set()
    for st in u.statements:
        declaration = re.fullmatch(
            r'(INTEGER|REAL|LOGICAL|CHARACTER(?:\s*\*\s*(?:\d+|\(\s*\d+\s*\)))?)\s+(.+)',
            st.text)
        if declaration:
            # These names were already checked and entered by parse().
            explicitly_typed.update(re.findall(NAME, declaration.group(2)))
    for name in u.args:
        if name not in explicitly_typed:
            # DIMENSION on a dummy may have set its shape before inference.
            u.vars[name] = (types[name[0]], u.vars[name][1])
    for st in u.statements:
        s = st.text.strip()
        if (re.match(r'^(INTEGER|REAL|LOGICAL|IMPLICIT|DIMENSION|COMMON)\s+', s)
                or re.match(r'^CHARACTER(?:\*|\s)', s)
                or re.match(r'^FORMAT\s*\(', s) or re.match(r'^SAVE\b', s)
                or re.match(r'^(EXTERNAL|INTRINSIC)\b', s)):
            continue
        s = LITERALS.sub(' ', s)
        s = re.sub(r'\.[A-Z]+\.', ' ', s)
        s = NUMBERS.sub(' ', s)
        for name in re.findall(NAME, s):
            if name in KEYWORDS or name in known or name in u.vars:
                continue
            if name not in u.vars:
                u.vars[name] = (types[name[0]], None)
