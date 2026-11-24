# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Conservative exact finite target proofs for Spectrum BASIC POKE.

Only straight-line, normally bounded FOR/NEXT regions and literal arithmetic
are supported. A process UDG address is represented as an exact relocatable
offset; this is not an absolute RAM grant. Existing memory policy decides
whether every proved write is supported. Unknown ordinary addresses remain the programmer's responsibility.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
import itertools
import re

from audit_policy import scrub_code, split_address
def _line_text(body, token_names):
    out=[]; quoted=False; i=0
    while i<len(body):
        c=body[i]
        if c==14 and not quoted and i+5<len(body):
            i+=6;continue
        if c==234 and not quoted:break  # Spectrum REM token
        if c==34:
            quoted=not quoted;out.append('"')
        elif quoted:
            out.append(chr(c) if 32<=c<=126 else '{%02X}'%c)
        elif c in token_names:
            out.append(' '+token_names[c].upper()+' ')
        elif 32<=c<=126:
            out.append(chr(c))
        i+=1
    return ''.join(out)


def _statements(src):
    parts=[]; start=0; quoted=False
    for pos,ch in enumerate(src):
        if ch=='"':quoted=not quoted
        if ch==':' and not quoted:
            parts.append(src[start:pos]);start=pos+1
    parts.append(src[start:])
    return parts


class PokeAddressError(ValueError):
    """An address or entry path could not be proved safe statically."""


@dataclass
class Loop:
    variable: str
    first: str
    last: str
    step: str
    begin: int
    line: int
    end: int | None = None
    conditional: bool = False


@dataclass
class Write:
    line: int
    address: str
    position: int
    loops: list[Loop] = field(default_factory=list)


# (UDG relocation count, signed byte displacement). The UDG pointer is process-owned and is
# not presumed to reside at an absolute compile address.
UDG_LITERAL = re.compile(r'\bUSR\s*(?:\(\s*)?"([a-uA-U]|\{(?:9[0-9A-Fa-f]|A[0-4a-f])\})"\s*\)?', re.I)
FOR_RE = re.compile(r'\bFOR\s+([a-z])\s*=\s*(.*?)\s+TO\s+(.*?)(?:\s+STEP\s+(.+))?\s*$', re.I)
NEXT_RE = re.compile(r'\bNEXT\s+([a-z])\b', re.I)
TRANSFER_RE = re.compile(r'\b(?:GO\s*TO|GO\s*SUB|RUN|RETURN|STOP|CONTINUE)\b', re.I)
ENTRY_RE = re.compile(r'\b(?:GO\s*TO|GO\s*SUB|RUN)\s+(\d+)\b', re.I)
SET_RE = re.compile(r'\b(?:LET|READ|INPUT|FOR)\s+([a-z])\s*(?:=|,|$)', re.I)


def _literal(m):
    s=m.group(1)
    code=int(s[1:3],16) if s.startswith('{') else ord(s.lower())-ord('a')+144
    if not 144 <= code <= 164:
        raise PokeAddressError('graphics character is outside process UDG')
    return f'__udg_{(code-144)*8}'


def _value(node, env):
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return (0,node.value)
    if isinstance(node,ast.Name):
        if node.id.startswith('__udg_') and node.id[6:].isdigit():
            return (1,int(node.id[6:]))
        if node.id.lower() in env:
            return env[node.id.lower()]
        raise PokeAddressError(f'variable {node.id} has no proved bounds')
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
        b,n=_value(node.operand,env)
        return (b,n) if isinstance(node.op,ast.UAdd) else (-b,-n)
    if isinstance(node,ast.BinOp):
        left=_value(node.left,env);right=_value(node.right,env)
        if isinstance(node.op,ast.Add):return left[0]+right[0],left[1]+right[1]
        if isinstance(node.op,ast.Sub):return left[0]-right[0],left[1]-right[1]
        if isinstance(node.op,ast.Mult):
            if left[0] and right[0]:raise PokeAddressError('cannot multiply two addresses')
            if left[0]:return left[0]*right[1],left[1]*right[1]
            return right[0]*left[1],right[1]*left[1]
        if isinstance(node.op,ast.Div):
            if right[0] or not right[1]:raise PokeAddressError('unsafe division')
            if left[0] or left[1]%right[1]:raise PokeAddressError('address division is not exact')
            return 0,left[1]//right[1]
    raise PokeAddressError('unsupported arithmetic or address expression')


def expression(s,env):
    if not s.strip():raise PokeAddressError('empty address expression')
    replaced=UDG_LITERAL.sub(_literal,s)
    def chr_udg(match):
        inner=match.group(1)
        if not re.fullmatch(r'[A-Za-z0-9_+*/()\s-]+',inner):
            raise PokeAddressError('CHR$ argument cannot be proved numeric')
        try:
            code_base,code=_value(ast.parse(inner,mode='eval').body,env)
        except (SyntaxError,RecursionError,OverflowError) as ex:
            raise PokeAddressError('CHR$ argument cannot be proved numeric') from ex
        if code_base or not 144<=code<=164:
            raise PokeAddressError('CHR$ character is not a process UDG')
        return f'__udg_{(code-144)*8}'
    replaced=re.sub(r'\bUSR\s+CHR\$\s*\(\s*([^()]*)\s*\)',chr_udg,replaced,flags=re.I)
    if re.search(r'\bUSR\b',replaced,re.I):raise PokeAddressError('USR argument has no proved graphics character')
    # Allow pure integer arithmetic only, not arbitrary Python expressions.
    if re.search(r'[^a-zA-Z_0-9+*/()\s\-]',replaced):
        raise PokeAddressError('unsupported characters or noninteger arithmetic')
    try:
        node=ast.parse(replaced,mode='eval').body
        base,value=_value(node,env)
    except (SyntaxError,RecursionError,OverflowError) as ex:
        raise PokeAddressError('invalid or excessive address expression') from ex
    if base not in (0,1):raise PokeAddressError('address requires an unproved memory base')
    if base==0 and not 0<=value<=65535:raise PokeAddressError('absolute POKE target outside 64 KB')
    return base,value


def _segments(lines, token_names):
    rows=[]
    for number,body in lines:
        src=_line_text(body,token_names)
        for chunk in _statements(src):
            mask=scrub_code(chunk)
            rows.append((number,chunk,mask))
    return rows


def _loop_values(loop):
    a=expression(loop.first,{}); b=expression(loop.last,{})
    if a[0]!=b[0]:raise PokeAddressError('FOR start/end use different memory bases')
    step=expression(loop.step,{})
    if step[0] or not step[1]:raise PokeAddressError('FOR step must be a known nonzero integer')
    start,stop=a[1],b[1];delta=step[1]
    if (stop-start)*delta<0:
        # A FOR body still runs once in Sinclair BASIC; reject ambiguous compiler behavior
        # rather than inferring an empty loop.
        raise PokeAddressError('FOR bounds/step do not establish a normal progression')
    count=(stop-start)//delta+1
    if count<1 or count>2048:raise PokeAddressError('FOR range is too large to enumerate')
    return [(a[0],start+delta*i) for i in range(count)]


def prove_pokes(lines, token_names, findings):
    """UDG writes require exact finite addresses; ordinary POKEs may be dynamic."""
    rows=_segments(lines,token_names)
    stack=[];loops=[];writes=[]
    for index,(line,src,mask) in enumerate(rows):
        # Reject IF-controlled entry/exit into the induction region.
        frm=FOR_RE.search(mask)
        if frm:
            real = FOR_RE.match(src,frm.start())
            if real is None:
                raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {line}: cannot parse FOR bounds')
            conditional = bool(re.search(r'\bIF\b',mask[:frm.start()],re.I))
            l=Loop(real.group(1).lower(),real.group(2).strip(),
                   real.group(3).strip(),
                   real.group(4).strip() if real.group(4) else '1',index,line,conditional=conditional)
            loops.append(l);stack.append(l)
        for m in re.finditer(r'\bPOKE\b',mask,re.I):
            addr=split_address(src[m.end():])
            writes.append(Write(line,addr,index,list(stack)))
        for nxt in NEXT_RE.finditer(mask):
            if not stack or stack[-1].variable!=nxt.group(1).lower():
                # An unmatched NEXT cannot be used to justify an address.
                continue
            stack.pop().end=index
    # Address proof applies to each actual operation, not to a friendly looking line count;
    # cross-check with the separate memory classifier.
    checks={}
    for f in findings:
        if f.operation=='POKE':checks[f.line]=checks.get(f.line,0)+1
    found={}
    for w in writes:found[w.line]=found.get(w.line,0)+1
    if found!=checks:
        raise PokeAddressError('RBC E_POKE_ADDRESS: token/memory-operation count mismatch')
    incoming={int(m.group(1)) for _,_,mask in rows for m in ENTRY_RE.finditer(mask)}
    # A computed branch can enter a loop after its FOR. A known literal target is handled
    # separately; anything else leaves entry unproved.
    indirect_branch = any(
        not (re.match(r'\s*\d+\b',mask[m.end():]) or
             (m.group().upper()=='RUN' and not mask[m.end():].strip()))
        for _,_,mask in rows
        for m in re.finditer(r'\b(?:GO\s*TO|GO\s*SUB|RUN)\b',mask,re.I)
    )
    proved=[]
    for w in writes:
        try:
            target_sets=[];variables=set()
            # A literal target needs no flow proof: branches cannot change it.
            try:
                direct=expression(w.address,{})
            except PokeAddressError:
                direct=None
            if direct is not None:
                proved.append({'line':w.line,'expression':w.address,
                               'addresses':[{'space':'process_udg' if direct[0] else 'absolute',
                                             'offset':direct[1]}]})
                continue
            address_variables=scrub_code(w.address)
            for loop in w.loops:
                if not re.search(r'\b'+re.escape(loop.variable)+r'\b',address_variables,re.I):
                    continue
                if loop.conditional:
                    raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: conditional FOR cannot be proved')
                if loop.end is None or not loop.begin<w.position<loop.end:
                    raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: loop has no proved NEXT')
                # Sinclair computed jumps target the start of a BASIC line. A FOR and
                # all its body statements on that same line cannot be entered beyond
                # the initialization statement.
                if indirect_branch and any(rows[i][0] != loop.line
                                           for i in range(loop.begin,loop.end+1)):
                    raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: computed branch could enter FOR body')
                body=rows[loop.begin+1:loop.end]
                if any(line in incoming and line!=loop.line for line,_,_ in body):
                    raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: jump may bypass FOR')
                if any(TRANSFER_RE.search(mask) for _,_,mask in body):
                    raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: branch in FOR body')
                if any(re.search(r'\bIF\b',mask,re.I) for _,_,mask in body):
                    raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: conditional FOR body')
                # Every loop index is private to its own FOR/NEXT region.
                for _,_,mask in body:
                    for match in SET_RE.finditer(mask):
                        if match.group(1).lower()==loop.variable:
                            raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: FOR variable may be reassigned')
                    if any(re.search(r'\b'+loop.variable+r'\b',mask,re.I)
                           for _ in re.finditer(r'\b(?:INPUT|READ)\b',mask,re.I)):
                        raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: FOR index may receive input')
                if loop.variable in variables:
                    raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: reused loop variable')
                variables.add(loop.variable)
                target_sets.append((loop.variable,_loop_values(loop)))
            sizes=1
            for _,values in target_sets:sizes*=len(values)
            if sizes>8192:
                raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: finite set too large for exact proof')
            try:
                destinations=set()
                for combination in itertools.product(*(a for _,a in target_sets)):
                    env={name:value for (name,_),value in zip(target_sets,combination)}
                    destinations.add(expression(w.address,env))
            except PokeAddressError as ex:
                raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: cannot prove POKE {w.address!r}; {ex}') from ex
            if not destinations:raise PokeAddressError(f'RBC E_POKE_ADDRESS: Line {w.line}: empty address set')
            proved.append({'line':w.line,'expression':w.address,
                           'addresses':[{'space':'process_udg' if b else 'absolute','offset':n}
                                        for b,n in sorted(destinations)]})

        except PokeAddressError:
            has_udg = bool(re.search(r'\bUSR\b', w.address, re.I)) or any(
                re.search(r'\bUSR\b', value, re.I)
                for loop in w.loops for value in (loop.first, loop.last, loop.step))
            if has_udg and re.search(r'\bUSR\b', w.address, re.I):
                # The compiler emits a UDG pointer range check for direct USR expressions.
                # The operand type is also checked there.
                proved.append({'line':w.line, 'expression':w.address,
                               'addresses':[], 'status':'runtime_guarded_udg_pointer'})
                continue
            # Static loop-path inference cannot forbid a BASIC statement. FOR
            # indices may change; computed branches may enter a body; early exits
            # need not visit NEXT. For indirect numeric POKE, the native process
            # memory guard checks the runtime address.
            proved.append({'line':w.line,'expression':w.address,
                           'addresses':[], 'status':'dynamic_programmer_responsibility'})
    for entry in proved:
        for address in entry['addresses']:
            if address['space']=='process_udg' and not 0 <= address['offset'] < 168:
                raise PokeAddressError(f"RBC E_UDG_RANGE: Line {entry['line']}: UDG byte offset outside 0..167")
    return proved
