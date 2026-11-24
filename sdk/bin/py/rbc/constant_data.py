# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Fold DATA variables only when a local RESTORE/READ transaction proves their value.

This is deliberately NOT a general rewrite of variable DATA. An initializer,
explicit restore, bounded READ, and all entries must occur as one transaction.
The original text/tape bytes are never changed.
"""
from __future__ import annotations
import re
from udg_bounds import _line_text

DATA = 0xE4
VAR = re.compile(rb'^[A-Za-z]$')
CONST = re.compile(r'\bLET\s+([A-Za-z])\s*=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?=\s*(?::|$))', re.I)
REST = re.compile(r'\bRESTORE\s+(\d+)\b', re.I)
READ = re.compile(r'\bREAD\s+([A-Za-z](?:\s*,\s*[A-Za-z])*)\b', re.I)
FOR = re.compile(r'\bFOR\s+([A-Za-z])\s*=\s*1\s*TO\s*(\d+)\b', re.I)
NEXT = re.compile(r'\bNEXT\s+([A-Za-z])\b', re.I)


def _separate(body):
    """Comma-delimit DATA tokens, skipping quoted text and binary number tails."""
    fields=[]
    start=0
    i=0
    quoted=False
    while i<len(body):
        c=body[i]
        if c==34:
            quoted=not quoted
        elif c==14 and not quoted and i+5<len(body):
            i+=6
            continue
        elif c==44 and not quoted:
            fields.append(body[start:i])
            start=i+1
        i+=1
    fields.append(body[start:])
    return fields


def adapt_literal_data(program, kw, fp, source, tap):
    rows=list(tap.split_lines(program))
    decoded=[(num,_line_text(body,kw.TOKEN)) for num,body in rows]
    reads=[(num,text) for num,text in decoded if READ.search(text)]
    # A different READ path, or unnumbered RESTORE, could change the value observed by a
    # DATA expression. In those programs do nothing.
    if not reads or any(not REST.search(text) for _,text in reads):
        return program, []
    if any('RESTORE' in text.upper() and not REST.search(text) for _,text in decoded):
        return program, []
    restores={}
    for num,text in decoded:
        for match in REST.finditer(text):
            restores.setdefault(int(match[1]),[]).append((num,text))
    by_line=dict(rows)
    revised={}
    proofs=[]
    for target,uses in restores.items():
        if len(uses)!=1 or target not in by_line:
            continue
        num,text=uses[0]
        if not READ.search(text):
            continue
        read=READ.search(text)
        rest=REST.search(text)
        begin=FOR.search(text, rest.end())
        if not begin or begin.start()>read.start():
            continue
        nexts=[m for m in NEXT.finditer(text,read.end()) if m[1].lower()==begin[1].lower()]
        if len(nexts)!=1:
            continue
        # Every READ line is tied to one RESTORE line, and the bounded loop contains exactly
        # one READ statement after all initializers.
        if len([m for m in READ.finditer(text)])!=1:
            continue
        prefix=text[:read.start()]
        if re.search(r'\b(?:GO\s*TO|GO\s*SUB|IF|RUN|STOP|RETURN|INPUT)\b',prefix,re.I):
            continue
        init={name.lower():value for name,value in CONST.findall(prefix)}
        if not init:
            continue
        if not (1 <= int(begin[2]) <= 256):
            continue
        # An intervening assignment or FOR/INPUT may invalidate the literal.
        writes=re.findall(r'\bLET\s+([A-Za-z])\s*=', prefix, re.I)
        if any(sum(w.lower()==name for w in writes)!=1 for name in init):
            continue
        if any(re.search(r'\b(?:FOR|INPUT|READ)\s+'+re.escape(name)+r'\b', prefix, re.I)
               for name in init):
            continue
        if any(name.lower() in init for name in read[1].replace(' ','').split(',')):
            continue
        tail=text[read.end():nexts[0].start()]
        if any(re.search(r'\b(?:LET|READ|INPUT|FOR)\s+'+re.escape(name)+r'\b',tail,re.I) for name in init):
            continue
        if any(m.start()>rest.start() and m.start()<read.start() for m in REST.finditer(text)):
            continue
        body=by_line[target]
        pos=body.find(bytes([DATA]))
        if pos<0 or body.find(bytes([DATA]),pos+1)>=0:
            continue
        stop=body.find(b'\r',pos)
        if stop<0:stop=len(body)
        fields=_separate(body[pos+1:stop])
        # The loop must consume *exactly* this DATA statement. No spill.
        names=[x.strip() for x in fields]
        consumed=int(begin[2])*len(read[1].replace(' ','').split(','))
        if consumed!=len(fields):
            continue
        found=set()
        changed=[]
        for field in fields:
            match=VAR.fullmatch(field.strip())
            if not match:
                changed.append(field)
                continue
            name=field.strip().decode('ascii').lower()
            if name not in init:
                changed=[]
                break
            found.add(name)
            leading=field[:len(field)-len(field.lstrip())]
            trailing=field[len(field.rstrip()):]
            changed.append(leading+source.hide_numbers(init[name].encode('ascii'),fp)+trailing)
        if not changed or not found:
            continue
        revised[target]=body[:pos+1]+b','.join(changed)+body[stop:]
        proofs.append({'data_line':target,'restore_line':num,
                         'values':{name:init[name] for name in sorted(found)},
                         'fields':len(fields)})
    if not revised:
        return program, []
    return tap.join_lines([(n,revised.get(n,body)) for n,body in rows]),proofs