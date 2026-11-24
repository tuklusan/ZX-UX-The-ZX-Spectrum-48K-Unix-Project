#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Classify ZX Spectrum memory effects before emitting native ZX-UX code.

This is a conservative static check. It never promises that compiled code is
safe merely because a statement was not flagged. The process has no access to
arbitrary ZX-UX internal RAM, and USR called with a number executes unknown
machine code. A string argument to USR, however, locates a UDG glyph.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re

PROTECTED = ((0x0000, 0x3FFF), (0x5B00, 0xFFFF))
MEMORY_WORDS = ('POKE', 'PEEK', 'USR', 'CLEAR', 'RANDOMIZE', 'IN', 'OUT',
                'LOAD', 'SAVE', 'VERIFY', 'MERGE')


@dataclass
class Finding:
    line: int
    operation: str
    severity: str
    classification: str
    expression: str


class MemoryBlocked(ValueError):
    def __init__(self, message, findings):
        super().__init__(message)
        self.findings=findings


def _line_text(body: bytes, keywords: dict[int, str]) -> str:
    """Turn only token codes into plain words, keeping string values intact."""
    s = []
    i = 0
    quoted = False
    while i < len(body):
        c = body[i]
        if c == 0x0E and not quoted and i + 5 < len(body):
            i += 6             # skip the ROM's hidden 5-byte number
            continue
        if not quoted and c == 0xEA:  # REM: remainder is never executable
            break
        if c == 0x22:
            quoted = not quoted
            s.append('"')
        elif quoted:
            # Hex notation here is for display of a Spectrum glyph code; it must never be
            # interpreted as BASIC syntax.
            if 32 <= c <= 126:
                s.append(chr(c))
            else:
                s.append('{%02X}' % c)
        elif c in keywords:
            s.append(' ' + keywords[c].upper() + ' ')
        elif 32 <= c <= 126:
            s.append(chr(c))
        elif c == 13:
            break
        i += 1
    return ''.join(s)


def _statements(text: str):
    """Split at colons outside quoted strings, unlike naive regex splitting."""
    parts=[];start=0;quote=False
    for i,c in enumerate(text):
        if c=='"':quote=not quote
        if c==':' and not quote:
            parts.append(text[start:i]);start=i+1
    parts.append(text[start:])
    return parts


def _target(expr: str):
    clean=expr.strip()
    if re.match(r'^USR\s*"(?:[a-uA-U]|\{(?:9[0-9A-Fa-f]|A[0-4a-f])\})"',clean,re.I):
        return 'udg'
    m=re.match(r'^(?:\(\s*)?(\d+)\b',clean)
    if m:
        n=int(m.group(1))
        if 0x4000 <= n <= 0x5AFF:return 'screen'
        if n < 0x4000:return 'rom'
        return 'system_or_kernel' if n < 0x5D00 else 'ordinary_ram'
    return 'unknown'


def _find_operations(s: str):
    """Read operation names outside quoted strings and preserve nested USR.

    POKE USR "A"+X contains a nested function, not the start of a new
    POKE argument. Each match is still reported separately to show the
    effects to the user, but the POKE expression keeps its complete address.
    """
    pat=re.compile(r'\b(?:POKE|PEEK|USR|CLEAR|RANDOMIZE|IN|OUT|LOAD|SAVE|VERIFY|MERGE)\b',re.I)
    matches=[m for m in pat.finditer(s) if s[:m.start()].count('"')%2==0]
    for k,m in enumerate(matches):
        op=m.group().upper()
        next_index=k+1
        # 'USR' directly after POKE, PEEK or RANDOMIZE is part of the containing
        # expression, not the end of that expression.
        while (next_index<len(matches) and matches[next_index].group().upper()=='USR'
               and op in ('POKE','PEEK','RANDOMIZE','USR')):
            next_index+=1
        end=matches[next_index].start() if next_index<len(matches) else len(s)
        yield op,s[m.end():end].strip().split(':',1)[0].strip()


def _udg_offset(address: str, before: str) -> bool:
    """Allow only one glyph address with an exactly bounded byte offset.

    A string USR argument locates a glyph. Without an offset it is safe.
    With +X the same source line must establish FOR X=0 TO 7 first.
    Anything more complex requires a separate source review.
    """
    a=address.strip()
    m=re.fullmatch(r'USR\s*"(?:[a-uA-U]|\{(?:9[0-9A-Fa-f]|A[0-4a-f])\})"'
                   r'\s*(?:\+\s*(\d+|[A-Za-z]))?',a,re.I)
    if not m:return False
    off=m.group(1)
    if off is None:return True
    if off.isdigit():return int(off)<=7
    pattern=r'\bFOR\s+'+re.escape(off)+r'\s*=\s*0\s*TO\s*7\b'
    return re.search(pattern,before,re.I) is not None


def _udg_loop_write(address: str, before: str) -> bool:
    """Recognize the bounded UDG initialization loop on one BASIC line."""
    m=re.fullmatch(r'([A-Za-z])',address.strip())
    if not m:return False
    variable=m.group(1)
    pattern=(r'\bFOR\s+'+re.escape(variable)+r'\s*=\s*USR\s*"[a-uA-U]"'
             r'\s*TO\s*USR\s*"[a-uA-U]"\s*\+\s*7\b')
    return re.search(pattern,before,re.I) is not None


def analyze_lines(lines: list[tuple[int,bytes]], token_names: dict[int,str]) -> list[Finding]:
    findings=[]
    for n,body in lines:
        src=_line_text(body,token_names)
        seen=''
        for chunk in _statements(src):
            for op,expr in _find_operations(chunk):
                address=expr.split(',',1)[0].strip()
                target=_target(('USR ' if op=='USR' else '') + address)
                if op=='USR':
                    if target=='udg':
                        sev,cl='info','process_udg_pointer'
                    else:
                        sev,cl='block','raw_machine_code_address'
                elif op=='POKE':
                    if _udg_offset(address,seen+chunk[:chunk.upper().find('POKE')]) or _udg_loop_write(address,seen):
                        sev,cl='info','bounded_process_udg_write'
                    elif target=='screen':sev,cl='review','direct_screen_write'
                    elif target=='rom':sev,cl='block','rom_write'
                    elif target=='system_or_kernel':sev,cl='block','global_memory_write'
                    else:sev,cl='review','programmer_managed_write'
                elif op=='PEEK':
                    if target=='screen':sev,cl='review','direct_screen_read'
                    elif target in ('rom','system_or_kernel'):
                        sev,cl=('info','rom_read') if target=='rom' else ('block','global_memory_read')
                    else:sev,cl='block','unbounded_memory_read'
                elif op=='RANDOMIZE':
                    if re.match(r'^USR\b',expr,re.I):sev,cl='block','machine_code_jump'
                    else:continue
                elif op=='CLEAR':sev,cl='block','changes_memory_layout'
                elif op=='IN':sev,cl='review','raw_io_input'
                elif op=='OUT':sev,cl='block','raw_io_output'
                else:sev,cl='block','tape_or_external_io'
                findings.append(Finding(n,op,sev,cl,expr[:90]))
            seen+=chunk+':'
    return findings


def summarize(findings: list[Finding]):
    return {'counts':{level:sum(x.severity==level for x in findings)
                      for level in ('block','review','info')},
            'findings':[asdict(x) for x in findings]}


def enforce(findings: list[Finding], policy: str):
    bad=[x for x in findings if x.severity=='block']
    if bad and policy=='strict':
        first=bad[0]
        raise MemoryBlocked(f'ZX-UX memory check stopped line {first.line}: '
                            f'{first.operation} {first.classification}. '
                            f'{len(bad)} blocked operation(s); use '
                            '--memory-policy review only for isolated tests', findings)