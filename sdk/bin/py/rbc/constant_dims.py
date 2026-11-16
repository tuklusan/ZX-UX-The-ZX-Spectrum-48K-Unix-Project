# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Specialize array sizes with a proven preceding literal assignment."""
from __future__ import annotations
import re
from udg_bounds import _line_text

_ASSIGN = re.compile(r'^\s*LET\s+([a-z])\s*=\s*(\d+)\s*$', re.I)
_DIM_LINE = re.compile(r'^\s*DIM\s+[a-z]\$?\s*\(\s*([a-z])\s*\)(?:\s*:\s*DIM\s+[a-z]\$?\s*\(\s*\1\s*\))*\s*$',re.I)
_JUMP = re.compile(r'\bGO\s*(?:TO|SUB)\s+(\d+)\b',re.I)
_JUMP_ANY = re.compile(r'\bGO\s*(?:TO|SUB)\b',re.I)
_DIM_TOKEN = 0xE9
_SAFE_DIM = re.compile(r'^\s*DIM\s+[a-z]\$?\s*\(\s*(?:\d+|[a-z])\s*\)(?:\s*:\s*DIM\s+[a-z]\$?\s*\(\s*(?:\d+|[a-z])\s*\))*\s*$',re.I)
_SAFE_LET = re.compile(r'^\s*LET\s+([a-z][a-z0-9]*)\$?\s*=\s*(?:\d+|[a-z][a-z0-9]*|\"[^\"]*\")\s*$',re.I)


def specialize_literal_dims(program, kw, fp, source, tap):
    rows = list(tap.split_lines(program))
    decoded = [(n,_line_text(body, kw.TOKEN)) for n,body in rows]
    changed={};proof=[]
    for i in range(1,len(rows)):
        num, statement = decoded[i]
        dims=_DIM_LINE.fullmatch(statement)
        if dims is None:
            continue
        wanted=dims[1].lower()
        # Scan only a short, straight-line setup. A different command, a write to the
        # dimension variable, or a branch blocks the proof.
        value=None
        prev=None
        for j in range(i-1,max(-1,i-25),-1):
            line, earlier=decoded[j]
            maybe=_ASSIGN.fullmatch(earlier)
            if maybe and maybe[1].lower()==wanted:
                value=maybe
                prev=line
                break
            safe_let=_SAFE_LET.fullmatch(earlier)
            if _SAFE_DIM.fullmatch(earlier):
                continue
            if safe_let and safe_let[1].lower()!=wanted:
                continue
            break
        if value is None:
            continue
        if not (1 <= int(value[2]) <= 1024):
            continue
        # An entry directly to the DIM line would bypass its initializer.
        if any(prev < int(m[1]) <= num for _,t in decoded for m in _JUMP.finditer(t)):
            continue
        if any(len(_JUMP_ANY.findall(t)) != len(_JUMP.findall(t)) for _,t in decoded):
            continue
        # The whole original DIM line must contain only these fixed arrays.
        body=rows[i][1]
        token=bytes((_DIM_TOKEN,))
        cursor=0;matches=[];letter=value[1].lower().encode('ascii')
        while cursor<len(body):
            k=body.find(token,cursor)
            if k<0:break
            m=re.match(rb'\s*[a-z]\$?\s*\(\s*('+letter+rb')\s*\)',body[k+1:],re.I)
            if m is None:
                matches=[];break
            start=k+1+m.start(1);end=k+1+m.end(1)
            matches.append((start,end))
            cursor=k+1+m.end()
        if not matches:
            continue
        # Replacing named dimensions with numeric tokens is sufficient for the existing
        # compiler; it does not affect runtime LET assignment.
        amended=bytearray(body)
        replacement=source.hide_numbers(value[2].encode('ascii'),fp)
        for begin,end in reversed(matches):
            amended[begin:end]=replacement
        changed[num]=bytes(amended)
        proof.append({'initializer_line':prev,'dim_line':num,'size':int(value[2]),
                      'arrays':len(matches)})
    if not changed:
        return program,[]
    return tap.join_lines([(n,changed.get(n,body)) for n,body in rows]),proof