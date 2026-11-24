#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rld - ZX-UX SDK linker: SSO1 objects and SSA1 archives -> SSX1 executable.

  rld.py [-o prog.ssx] [--entry SYM] [--stack N] [--heap N] [--map FILE]
         obj.sso ... lib.ssa ...
  rld.py --archive lib.ssa member.sso ...      build an SSA1 archive
"""
import struct
import sys
import os

SSX_HDR = 20


class LinkError(Exception):
    pass


class Obj:
    def __init__(self, data, name):
        self.name = name
        if data[:4] != b'SSO1':
            raise LinkError('%s: not an SSO1 object' % name)
        ver, flags, nsec, nsym, strsz = struct.unpack_from('<BBHHI', data, 4)
        p = 14
        self.secs = []           # (kind, size, bytes or None, relocs)
        self.aligns = []         # each section's alignment (a power of 2)
        for _ in range(nsec):
            kind, align, size, nrel = struct.unpack_from('<BBHH', data, p)
            if align < 1 or align & (align - 1):
                raise LinkError('%s: bad section alignment %d' % (name, align))
            p += 6
            body = None
            if kind != 3:
                body = bytearray(data[p:p + size])
                p += size
            rel = []
            for _ in range(nrel):
                rel.append(struct.unpack_from('<HBBH', data, p))
                p += 6
            self.secs.append((kind, size, body, rel))
            self.aligns.append(align)
        syms = []
        for _ in range(nsym):
            syms.append(struct.unpack_from('<IBBH', data, p))
            p += 8
        strtab = data[p:p + strsz]
        self.syms = []
        for off, sec, bind, val in syms:
            end = strtab.index(b'\0', off)
            self.syms.append((strtab[off:end].decode(), sec, bind, val))

    def defs(self):
        return {n for n, sec, b, v in self.syms if b == 1 and sec != 0}

    def undefs(self):
        return {n for n, sec, b, v in self.syms if sec == 0}


def read_archive(data, name):
    if data[:4] != b'SSA1':
        raise LinkError('%s: not an SSA1 archive' % name)
    n, _ = struct.unpack_from('<HH', data, 4)
    p = 8
    members = []
    for _ in range(n):
        off, size = struct.unpack_from('<II', data, p)
        p += 8
        end = data.index(b'\0', p)
        mname = data[p:end].decode()
        p = end + 1
        members.append(Obj(data[off:off + size], mname))
    return members


def write_archive(objs):
    """objs: list of (name, bytes)."""
    index = b''
    hdr_len = 8 + sum(8 + len(n.encode()) + 1 for n, _ in objs)
    off = hdr_len
    body = b''
    for n, d in objs:
        index += struct.pack('<II', off, len(d)) + n.encode() + b'\0'
        off += len(d)
        body += d
    return b'SSA1' + struct.pack('<HH', len(objs), 0) + index + body


def fletcher16(data):
    a = b = 0
    for x in data:
        a = (a + x) % 255
        b = (b + a) % 255
    return b << 8 | a


def reloc_stream(offsets):
    out = bytearray()
    pos = None
    for o in sorted(offsets):
        if pos is None:
            d = o
            if 2 <= d <= 255:
                out.append(d)
            else:
                out += bytes((0, o & 255, o >> 8))
        else:
            d = o - pos
            if d < 2:
                raise LinkError('overlapping relocations at %04x' % o)
            if d <= 255:
                out.append(d)
            else:
                out += bytes((0, o & 255, o >> 8))
        pos = o
    return bytes(out)


def link(objs, archives, entry='start', stack=384, heap=0, flags=0, org=None):
    # Load archive members only when needed. No gatecrashers.
    chosen = list(objs)
    defined = {}
    for o in chosen:
        for s in o.defs():
            if s in defined:
                raise LinkError('%s defined in %s and %s' % (s, defined[s].name, o.name))
            defined[s] = o
    pool = [m for a in archives for m in a]
    while True:
        undef = {entry} if org is None or True else set()
        for o in chosen:
            undef |= o.undefs()
        undef -= set(defined)
        undef.discard('@end')
        if not undef:
            break
        added = False
        for m in pool:
            if m in chosen:
                continue
            if m.defs() & undef:
                chosen.append(m)
                for s in m.defs():
                    if s in defined:
                        raise LinkError('%s defined in %s and %s' % (s, defined[s].name, m.name))
                    defined[s] = m
                added = True
                break
        if not added:
            raise LinkError('undefined: %s' % ', '.join(sorted(undef)))
    # Lay out text, data, then BSS. Align each section; the image starts even.
    # Zero any gaps. RAM gets no mystery guests.
    base = {}
    addr = 0
    image = bytearray()
    for kind in (1, 2, 3):
        for o in chosen:
            for i, (k, size, body, rel) in enumerate(o.secs):
                if k == kind:
                    addr += (-addr) % o.aligns[i]
                    base[(id(o), i + 1)] = addr
                    if kind != 3:
                        image += bytes(addr - len(image))
                        image += body
                    addr += size
        if kind == 2:
            image_end = addr
    bss = addr - image_end
    # Resolve global symbols. Labels need a real home.
    gaddr = {}
    for o in chosen:
        for n, sec, b, v in o.syms:
            if sec == 0:
                continue
            a = v if sec == 255 else base[(id(o), sec)] + v
            if b == 1:
                gaddr[n] = (a, sec != 255)
    gaddr.setdefault('@end', (addr, True))
    relocs = []
    for o in chosen:
        for i, (k, size, body, rel) in enumerate(o.secs):
            if k == 3:
                if rel:
                    raise LinkError('relocations in bss')
                continue
            sb = base[(id(o), i + 1)]
            for off, typ, _, tgt in rel:
                pos = sb + off
                w = image[pos] | image[pos + 1] << 8
                if typ == 1:
                    w += base[(id(o), tgt)]
                    isrel = True
                elif typ == 2:
                    n = o.syms[tgt][0]
                    a, isrel = gaddr[n]
                    w += a
                else:
                    raise LinkError('relocation type %d' % typ)
                image[pos:pos + 2] = (w & 0xFFFF).to_bytes(2, 'little')
                if isrel:
                    relocs.append(pos)
    if entry not in gaddr:
        raise LinkError('no entry symbol %s' % entry)
    ent = gaddr[entry][0]
    if org is not None:
        for pos in relocs:
            w = image[pos] | image[pos + 1] << 8
            image[pos:pos + 2] = ((w + org) & 0xFFFF).to_bytes(2, 'little')
        return image, bss, ent, gaddr, chosen
    rs = reloc_stream(relocs)
    hdr = bytearray(b'SSX1' + struct.pack('<BBHHHHHH', flags, SSX_HDR, len(image), bss,
                                          stack, heap, ent, len(relocs)))
    ck = fletcher16(bytes(hdr) + bytes(image) + rs)
    hdr += struct.pack('<H', ck)
    return bytes(hdr) + bytes(image) + rs, bss, ent, gaddr, chosen


def parse_ssx(data):
    """-> dict with header fields, image, relocation offsets (validated)."""
    if len(data) < SSX_HDR or data[:4] != b'SSX1':
        raise LinkError('not an SSX1 file')
    flags, hsz, isz, bss, stack, heap, ent, nrel, ck = struct.unpack_from('<BBHHHHHHH', data, 4)
    if hsz != SSX_HDR or flags & ~1:
        raise LinkError('bad SSX1 header')
    image = data[SSX_HDR:SSX_HDR + isz]
    p = SSX_HDR + isz
    rel = []
    pos = None
    for _ in range(nrel):
        b = data[p]
        if b == 0:
            o = data[p + 1] | data[p + 2] << 8
            p += 3
            if pos is not None and o < pos + 2:
                raise LinkError('bad relocation escape')
        else:
            o = b if pos is None else pos + b
            p += 1
            if pos is not None and b < 2:
                raise LinkError('bad relocation delta')
        if o + 2 > isz:
            raise LinkError('relocation outside image')
        rel.append(o)
        pos = o
    if fletcher16(data[:18] + data[SSX_HDR:p]) != ck:
        raise LinkError('SSX1 checksum mismatch')
    return dict(flags=flags, image=bytes(image), bss=bss, stack=stack, heap=heap,
                entry=ent, relocs=rel, size=p)


def relocate(image, relocs, org):
    img = bytearray(image)
    for o in relocs:
        w = img[o] | img[o + 1] << 8
        img[o:o + 2] = ((w + org) & 0xFFFF).to_bytes(2, 'little')
    return img


def main(argv):
    if argv and argv[0] == '--archive':
        out = argv[1]
        objs = [(os.path.basename(f), open(f, 'rb').read()) for f in argv[2:]]
        open(out, 'wb').write(write_archive(objs))
        return 0
    out, entry, stack, heap, mapf = 'a.ssx', 'start', 384, 0, None
    files = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('-o', '--entry', '--stack', '--heap', '--map'):
            v = argv[i + 1]
            i += 2
            if a == '-o':
                out = v
            elif a == '--entry':
                entry = v
            elif a == '--stack':
                stack = int(v, 0)
            elif a == '--heap':
                heap = int(v, 0)
            else:
                mapf = v
            continue
        files.append(a)
        i += 1
    objs, arcs = [], []
    for f in files:
        d = open(f, 'rb').read()
        if d[:4] == b'SSA1':
            arcs.append(read_archive(d, f))
        else:
            objs.append(Obj(d, f))
    try:
        data, bss, ent, gaddr, chosen = link(objs, arcs, entry, stack, heap)
    except LinkError as e:
        print('rld: %s' % e, file=sys.stderr)
        return 1
    open(out, 'wb').write(data)
    if mapf:
        with open(mapf, 'w') as f:
            for n, (a, r) in sorted(gaddr.items(), key=lambda x: x[1]):
                f.write('%04X %s\n' % (a, n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
