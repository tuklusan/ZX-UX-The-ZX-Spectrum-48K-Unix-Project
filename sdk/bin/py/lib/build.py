#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Build the C48 runtime archive libc48.ssa from lib/*.asm and lib/*.c.

Each .asm file is cut into many small members, so that a program links
only the routines it reaches: a cut is made before a label at column 0
when the code above cannot fall through into it (an unconditional j, jp,
jr or ret, or data in the text section), and at every section change.
Data and bss sections are not cut: variables may be used in pairs.  Every
label of a member is global; references between members are resolved by
rld like any other.  Equates are repeated in each member.
"""
import os, sys, glob, re
HERE = os.path.dirname(os.path.abspath(__file__))
SDK = os.path.dirname(HERE)
sys.path.insert(0, SDK)
import ras, rld
from rcc.driver import compile_to_asm

LABEL = re.compile(r'^([A-Za-z_@][\w@.]*):?(\s|$)')
TERMINAL = re.compile(r'^(ret|j\s+[^,]+|jp\s+[^,]+|jr\s+[^,]+|halt)$', re.I)
DATA = re.compile(r'^(db|dw|ds|defb|defw|defs)\b', re.I)


def code_of(line):
    """the instruction part of a line (label and comment removed)"""
    s = ras.Asm().strip_comment(line) if hasattr(ras.Asm, 'strip_comment') else line.split(';')[0]
    m = LABEL.match(s)
    if m and not s[:1].isspace():
        s = s[m.end(1):].lstrip(':')
    return s.strip()


def split(text, name):
    lines = text.split('\n')
    equs = [l for l in lines if re.match(r'^\w+\s+equ\b', l, re.I)]
    chunks = []
    cur = []
    sec = 'text'
    can_cut = False          # Cut only where the previous instruction cannot fall through.

    def flush():
        body = [l for l in cur if code_of(l) or LABEL.match(l)]
        if any(code_of(l) or (LABEL.match(l) and not l[:1].isspace()) for l in body):
            chunks.append((sec_of_chunk[0], list(cur)))
    sec_of_chunk = [sec]
    for l in lines:
        if l in equs:
            continue
        c = code_of(l)
        low = c.lower()
        if low.startswith(('global ', 'public ', 'extern ')):
            continue
        if low.startswith('section '):
            flush()
            cur = []
            sec = low.split()[1]
            sec_of_chunk = [sec]
            can_cut = False
            continue
        if LABEL.match(l) and not l[:1].isspace() and not l.startswith('.') and can_cut and cur:
            flush()
            cur = []
            sec_of_chunk = [sec]
        cur.append(l)
        if LABEL.match(l) and not l[:1].isspace():
            can_cut = False         # A label alone cannot stop fall-through. No magic walls.
        if c:
            # Keep data and BSS intact; paired fields are not confetti.
            can_cut = sec == 'text' and bool(TERMINAL.match(c) or DATA.match(c))
    flush()
    out = []
    for i, (s, body) in enumerate(chunks):
        labels = []
        for l in body:
            m = LABEL.match(l)
            if m and not l[:1].isspace() and not m.group(1).startswith('.'):
                labels.append(m.group(1))
        src = '\n'.join(equs) + '\n\tsection %s\n' % s
        if labels:
            src += '\tglobal ' + ','.join(labels) + '\n'
        src += '\n'.join(body) + '\n'
        out.append(('%s.%d.sso' % (name, i), src, labels))
    return out


def main():
    objs = []
    seen = {}
    for f in sorted(glob.glob(os.path.join(HERE, '*.asm'))):
        if os.path.basename(f) == 'forth_rt.asm':
            continue
        base = os.path.basename(f)[:-4]
        for mname, src, labels in split(open(f).read(), base):
            for l in labels:
                if l in seen:
                    raise SystemExit('build: %s defined in %s and %s' % (l, seen[l], mname))
                seen[l] = mname
            try:
                objs.append((mname, ras.assemble_text(src, mname)))
            except ras.AsmError as e:
                raise SystemExit('build: %s: %s\n%s' % (mname, e, src))
    # Separate bytecode objects need every SSB1 opcode. No missing chairs.
    from rcc import bcops
    objs.append(('vmtab.sso', ras.assemble_text(bcops.vm_table(), 'vmtab')))
    for f in sorted(glob.glob(os.path.join(HERE, '*.c'))):
        text, prog, g = compile_to_asm(f, {'lib': True})
        objs.append((os.path.basename(f)[:-2] + '.sso', ras.assemble_text(text, os.path.basename(f))))
    open(os.path.join(HERE, 'libc48.ssa'), 'wb').write(rld.write_archive(objs))
    tot = {}
    for n, d in objs:
        o = rld.Obj(d, n)
        k = n.split('.')[0]
        tot[k] = tot.get(k, 0) + sum(s[1] for s in o.secs)
    for k, v in tot.items():
        print('%-10s %5d bytes' % (k, v))
    print('%d members' % len(objs))


if __name__ == '__main__':
    main()
