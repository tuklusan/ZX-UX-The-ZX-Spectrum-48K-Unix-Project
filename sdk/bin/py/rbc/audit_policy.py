#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Read-only, token-aware inventory of BASIC USR and POKE operations.

This does not claim to prove dynamic addresses: those remain open pending a
control-flow proof in RBC. It never modifies original BASIC or TZX data.
"""
import argparse
import ast
import hashlib
import json
import re
import struct
from pathlib import Path

TOKENS={0xa5:'RND',0xa6:'INKEY$',0xaf:'CODE',0xb0:'VAL',0xba:'INT',0xbe:'PEEK',0xc0:'USR',0xc2:'CHR$',0xc4:'BIN',0xc5:'OR',0xc6:'AND',0xc7:'<=',0xc8:'>=',0xc9:'<>',0xcb:'THEN',0xcc:'TO',0xcd:'STEP',0xea:'REM',0xeb:'FOR',0xec:'GO TO',0xed:'GO SUB',0xf1:'LET',0xf4:'POKE',0xf7:'RUN',0xfa:'IF',0xe4:'DATA'}

def checksum(b):
    v=0
    for x in b:v^=x
    return v==0

def lines_from_tzx(raw):
    if raw[:8]!=b'ZXTape!\x1a': raise ValueError('invalid TZX header')
    pos=10; blocks=[]
    while pos<len(raw):
        k=raw[pos];pos+=1
        if k==0x10:
            if pos+4>len(raw):raise ValueError('short standard block')
            size=struct.unpack_from('<H',raw,pos+2)[0];pos+=4
            b=raw[pos:pos+size];pos+=size
            if len(b)!=size or not checksum(b):raise ValueError('invalid tape block/checksum')
            blocks.append(b)
        elif k==0x30:
            if pos>=len(raw):raise ValueError('short text block')
            size=raw[pos];pos+=size+1
        elif k==0x32:
            if pos+2>len(raw):raise ValueError('short archive block')
            size=struct.unpack_from('<H',raw,pos)[0];pos+=size+2
        else:raise ValueError('unsupported TZX block 0x%02x'%k)
        if pos>len(raw):raise ValueError('truncated extra record')
    for idx,b in enumerate(blocks[:-1]):
        if len(b)!=19 or b[:2]!=b'\0\0' or blocks[idx+1][:1]!=b'\xff':continue
        size=struct.unpack_from('<H',b,12)[0]
        payload=blocks[idx+1][1:-1]
        if len(payload)!=size:raise ValueError('bad BASIC payload size')
        offset=struct.unpack_from('<H',b,16)[0]
        if offset>size:raise ValueError('variable offset out of range')
        payload=payload[:offset]
        pos=0;lines=[]
        while pos<len(payload):
            if pos+4>len(payload):raise ValueError('truncated line header')
            line=struct.unpack_from('>H',payload,pos)[0]
            n=struct.unpack_from('<H',payload,pos+2)[0]
            pos+=4
            if n==0 or pos+n>len(payload) or payload[pos+n-1]!=13:raise ValueError('bad BASIC line %d'%line)
            lines.append((line,payload[pos:pos+n-1]))
            pos+=n
        return lines
    raise ValueError('no Sinclair BASIC program')

def from_text(raw):
    result=[]
    for line in raw.decode('utf-8').splitlines():
        match=re.match(r'\s*(\d+)\s+(.*)$',line)
        if match:result.append((int(match[1]),match[2]))
    return result

def tape_to_lex(body):
    """Decode keywords, respecting quotes, REM, numeric caches, and DATA."""
    out=[];quote=False;is_rem=False;in_data=False;i=0
    while i<len(body):
        b=body[i]
        if b==34:
            quote=not quote
            out.append('"');i+=1;continue
        if not quote:
            if b==0x0e: i+=6; continue # 5-byte numeric cache
            if b==0xea: is_rem=True
            if b==0xe4: in_data=True
            if b==58:in_data=False
        if is_rem:
            # Preserve plain REM prose without interpreting arbitrary token bytes.
            out.extend(' ' for _ in range(len(body)-i));break
        if b>=0xa5 and b in TOKENS and not quote and not in_data:
            out.append(' '+TOKENS[b]+' ')
        elif 32<=b<=126:out.append(chr(b))
        else:out.append('{%02X}'%b)
        i+=1
    return ''.join(out)

def scrub_code(s):
    """Mask strings and REM commentary while retaining character positions."""
    out=list(s);quoted=False;i=0
    while i<len(s):
        if s[i]=='"':
            quoted=not quoted;out[i]=' ';i+=1;continue
        if quoted:out[i]=' '
        i+=1
    mask=''.join(out)
    # DATA payload is not executable code; resume at its statement colon.
    masked=list(mask)
    for dm in re.finditer(r'(?<![A-Za-z\d_$])DATA(?![A-Za-z\d_$])',mask,re.I):
        end=mask.find(':',dm.end())
        end=len(mask) if end<0 else end
        for ix in range(dm.start(),end):masked[ix]=' '
    mask=''.join(masked)
    m=re.search(r'(?<![A-Za-z\d_$])REM(?![A-Za-z\d_$])',mask,re.I)
    if m:mask=mask[:m.start()]
    return mask

def split_address(s):
    d=0;quoted=False;end=0
    while end<len(s):
        c=s[end]
        if c=='"':quoted=not quoted
        if not quoted:
            if c=='(':d+=1
            if c==')':d-=1
            if c in ',:' and d==0:break
        end+=1
    return s[:end].strip()

def constant_address(expr):
    if not re.fullmatch(r'[0-9.\s()+*/\-]+',expr) or not expr:return None
    try:
        t=ast.parse(expr,mode='eval').body
        def visit(n):
            if isinstance(n,ast.Constant) and type(n.value) in (int,float):return n.value
            if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
                return visit(n.operand)*(-1 if isinstance(n.op,ast.USub) else 1)
            if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
                a,b=visit(n.left),visit(n.right)
                if isinstance(n.op,ast.Add):return a+b
                if isinstance(n.op,ast.Sub):return a-b
                if isinstance(n.op,ast.Mult):return a*b
                return a/b
            raise ValueError('unsupported expression')
        v=visit(t)
        if not (v==v and float('-inf')<v<float('inf')):return None
        return int(v)
    except (SyntaxError,ValueError,TypeError,OverflowError,ZeroDivisionError):return None

def usr_class(tail):
    t=tail.lstrip()
    if re.match(r'^\(\s*"(?:[^"}]|\{[0-9A-Fa-f]{2}\})"\s*\)',t) or re.match(r'^"(?:[^"}]|\{[0-9A-Fa-f]{2}\})"',t):
        return 'literal_graphics_character'
    if re.match(r'^(?:[\d.+-]|\(\s*[\d.+-])',t):return 'numeric_usr'
    if re.match(r'^CHR\$',t,re.I):return 'string_expression_requires_type_and_range_proof'
    if re.match(r'^[A-Za-z][A-Za-z\d]*\$',t):return 'string_variable_requires_length_proof'
    return 'argument_type_unproved'

def audit_lines(lines,mode):
    occurrences=[]
    for line,source in lines:
        raw=source if mode=='text' else tape_to_lex(source)
        mask=scrub_code(raw)
        for m in re.finditer(r'(?<![A-Za-z\d_$])(USR|POKE)(?![A-Za-z\d_$])',mask,re.I):
            typ=m.group(1).upper()
            expr=split_address(raw[m.end():]) if typ=='POKE' else raw[m.end():].lstrip()[:65]
            if typ=='USR':status=usr_class(raw[m.end():]);detail={'argument_start':expr}
            else:
                address=constant_address(expr)
                status='constant_proved_needs_memory_policy' if address is not None else 'needs_exact_control_flow_proof'
                detail={'address_expression':expr}
                if address is not None:detail['address']=address
            occurrences.append({'line':line,'operation':typ,'status':status,**detail})
    return occurrences

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--out',type=Path);p.add_argument('--compact',action='store_true');p.add_argument('--source-head');p.add_argument('--source-tree');args=p.parse_args()
    files=sorted(args.root.glob('*/BASIC/*.bas'))+sorted(args.root.glob('*/BASIC/*.tzx'))
    rows=[]
    for file in files:
        raw=file.read_bytes()
        mode='text' if file.suffix=='.bas' else 'tape'
        if mode=='text':raw=raw.replace(b'\r\n',b'\n')
        row={'file':str(file.relative_to(args.root)),'sha256':hashlib.sha256(raw).hexdigest(), 'mode':mode}
        try:
            lines=from_text(raw) if mode=='text' else lines_from_tzx(raw)
            row.update({'status':'parsed','line_count':len(lines),'operations':audit_lines(lines,mode)})
        except (ValueError,UnicodeError) as ex:row.update({'status':'unparsed','reason':str(ex),'operations':[]})
        rows.append(row)
    summary={'inputs':len(rows),'parsed':sum(r['status']=='parsed' for r in rows), 'unknown_inputs':sum(r['status']!='parsed' for r in rows), 'operations':sum(len(r['operations']) for r in rows)}
    for opname in ('USR','POKE'):
        events=[v for row in rows for v in row['operations'] if v['operation']==opname]
        summary[opname]={'total':len(events),'by_status':{s:sum(v['status']==s for v in events) for s in sorted({v['status'] for v in events})}}
    result={'purpose':'read-only source-token survey; nonconstant addresses not proved safe','summary':summary,'rows':rows}
    if args.compact:
        by_program={}
        for row in rows:
            slug=row['file'].split('/')[0]
            by_program.setdefault(slug,{})[row['mode']]=row
        pairs=[]
        for slug, pair in sorted(by_program.items()):
            if set(pair)!={'text','tape'}: raise RuntimeError('missing original input form: '+slug)
            t,z=pair['text'],pair['tape']
            def fingerprint(rec):return [(e['line'],e['operation'],e['status']) for e in rec['operations']]
            same=t['status']=='parsed' and z['status']=='parsed' and t['line_count']==z['line_count'] and fingerprint(t)==fingerprint(z)
            pairs.append({'program':slug,'text':t['file'],'tape':z['file'],
                          'text_parse':t['status'],'tape_parse':z['status'],
                          'text_lines':t.get('line_count'),'tape_lines':z.get('line_count'),
                          'same_operations_and_lines':same,
                          'text_operations':t['operations'],
                          **({'tape_operations':z['operations']} if not same else {}),
                          **({'text_error':t['reason']} if 'reason' in t else {}),
                          **({'tape_error':z['reason']} if 'reason' in z else {})})
        result={'purpose':result['purpose'], 'source_head':args.source_head,
                'source_tree':args.source_tree,'summary':summary,'pairs':pairs}
    else:
        # Keep all per-input checksums only in private development output; a Git tree identity and
        # explicit paired files identify published input.
        pass
    if args.out:args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    for row in rows:
        if row['status']!='parsed':print('UNPARSED',row['file'],row['reason'])
        for op in row['operations']:
            if op['status']=='numeric_usr':print('NUMERIC_USR',row['file'],op)

if __name__=='__main__':main()
