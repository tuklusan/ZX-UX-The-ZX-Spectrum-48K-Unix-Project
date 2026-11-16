#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rtap - ZX-UX SDK tape writer: SSX1 programs -> SST1 cassette records.

  rtap.py [-o out.tzx] [--after ZX-UX.tzx] [--title T] prog.ssx[=NAME] ...
  rtap.py --list tape.tzx ...

Each program becomes one standard Spectrum CODE pair (header + data block)
that ZX-UX's loader recognises (SPEC-SDK-R2 section 9):

  header   type 4 (older tapes use type 3), name = the program name (1..10 characters, the name
           typed as /dev/cassette/NAME), length = SSX1 file size,
           parameter 1 = bytes of memory the program needs (image, bss,
           heap and stack; at least the file size), parameter 2 = 'SS'
  data     the SSX1 file, flag FFh

--after appends the records to a copy of an existing tape (e.g. the ZX-UX
boot tape), so that one tape boots ZX-UX and then holds the programs.

--list shows what a tape file holds, block by block, without changing
it: ZX-UX programs (as /dev/cassette/NAME, with their size and the
memory they need), tar archives and their members (kind, size and path
from each member's preamble, as tar tv shows them), the Spectrum's own
files (BASIC, arrays, CODE), and anything else (data blocks without a
header, blocks whose parity is wrong).  On ZX-UX, tap t (or tar t
without an archive name) lists the programs and archives of a real
cassette.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rld  # noqa: E402

ARGS_ROOM = 0       # the loader adds the argument bytes itself


def tap_block(flag, data):
    body = bytes([flag]) + data
    x = 0
    for c in body:
        x ^= c
    return body + bytes([x])


def need(ssx):
    h = rld.parse_ssx(ssx)
    n = len(h['image']) + h['bss'] + h['heap'] + h['stack']
    return max(n, len(ssx))


def records(ssx, name):
    if not 1 <= len(name) <= 10 or not all(32 < ord(c) < 127 and c != '/' for c in name):
        raise SystemExit('rtap: bad program name %r' % name)
    n = need(ssx)
    if n > 0xFFFF:
        raise SystemExit('rtap: %s needs %d bytes' % (name, n))
    hdr = tap_block(0, bytes([4]) + name.encode().ljust(10) +
                    struct.pack('<HHH', len(ssx), n, 0x5353))
    return [hdr, tap_block(0xFF, ssx)]


def tzx_blocks(data):
    """-> list of standard-speed records in a TZX, skipping turbo boot data."""
    if len(data) < 10 or data[:8] != b'ZXTape!\x1a':
        raise SystemExit('rtap: not a complete TZX file')
    p = 10
    out = []
    head = bytearray(data[:10])
    while p < len(data):
        t = data[p]
        if t == 0x10:
            if p + 5 > len(data):
                raise SystemExit('rtap: truncated standard TZX header')
            pause, n = struct.unpack_from('<HH', data, p + 1)
            if p + 5 + n > len(data):
                raise SystemExit('rtap: truncated standard TZX payload')
            out.append((pause, data[p + 5:p + 5 + n]))
            p += 5 + n
        elif t == 0x11:
            # ZX-UX boot uses TZX turbo records. Check the length and complete payload
            # before skipping data. The system-image validator handles the turbo CRC and image.
            # The cassette accepts no IOUs.
            if p + 19 > len(data):
                raise SystemExit('rtap: truncated turbo TZX header')
            n = int.from_bytes(data[p + 16:p + 19], 'little')
            if p + 19 + n > len(data):
                raise SystemExit('rtap: truncated turbo TZX payload')
            p += 19 + n
        elif t == 0x30:
            if p + 2 > len(data):
                raise SystemExit('rtap: truncated TZX text header')
            n = data[p + 1]
            if p + 2 + n > len(data):
                raise SystemExit('rtap: truncated TZX text block')
            head += data[p:p + 2 + n]
            p += 2 + n
        elif t == 0x32:
            if p + 3 > len(data):
                raise SystemExit('rtap: truncated TZX archive header')
            n = struct.unpack_from('<H', data, p + 1)[0]
            if p + 3 + n > len(data):
                raise SystemExit('rtap: truncated TZX archive block')
            head += data[p:p + 3 + n]
            p += 3 + n
        else:
            raise SystemExit('rtap: TZX block %02X not supported' % t)
    return bytes(head), out


def _name(b):
    return b[2:12].decode('latin-1').rstrip(' ')


def _parity_ok(b):
    x = 0
    for c in b:
        x ^= c
    return x == 0


def list_blocks(blocks):
    """Describe both versioned ZX-UX cassette formats, without trusting input.

    An archive is A, zero or more F members, E, all of one version.
    Invalid blocks are reported rather than silently regarded as programs.
    """
    out = []
    i = 0
    active = None
    while i < len(blocks):
        b = blocks[i]
        if len(b) < 2:
            out.append('?        block %d: %d bytes, too short' % (i, len(b)))
            i += 1
            continue
        if not _parity_ok(b):
            out.append('?        block %d: parity error (%d bytes)' % (i, len(b) - 2))
            i += 1
            continue
        if b[0] != 0 or len(b) != 19:
            out.append('         data block, %d bytes' % (len(b) - 2))
            i += 1
            continue
        kind = b[1]
        name = _name(b)
        length, p1, p2 = struct.unpack_from('<HHH', b, 12)
        i += 1
        if kind in (3, 4) and p2 == 0x5353:
            data = blocks[i] if i < len(blocks) and blocks[i][:1] == b'\xff' else None
            if data is not None:
                i += 1
            ok = (data is not None and _parity_ok(data) and
                  len(data) - 2 == length and p1 >= length and length >= 4 and
                  data[1:5] == b'SSX1')
            out.append('program  /dev/cassette/%s  %d bytes, needs %d%s'
                       % (name, length, p1, '' if ok else '  (its data block is missing or bad)'))
            continue
        if kind in (3, 5) and p2 == 0x5552 and (p1 >> 8) == 0x80:
            marker = p1 & 0xff
            if marker == ord('A'):
                if active is not None or length:
                    out.append('?        invalid archive start: %s' % name)
                else:
                    active = kind
                    out.append('archive  /dev/cassette%s:' % ('/' + name if name else ''))
                continue  # An A header has no physical data block.
            if marker == ord('E'):
                if active != kind or length:
                    out.append('?        invalid archive end: %s' % name)
                else:
                    out.append('         end of archive')
                    active = None
                continue  # An E header has no physical data block.
            if marker == ord('F'):
                if active != kind or length < 12:
                    out.append('  ? member %s: invalid sequence, version or length' % name)
                    continue
                width = 512 if kind == 3 else 1024
                got = bytearray()
                error = None
                while len(got) < length:
                    expected = min(width, length - len(got))
                    physical = 18 if expected == 17 else expected
                    if i >= len(blocks) or blocks[i][:1] != b'\xff':
                        error = 'missing data block'
                        break
                    block = blocks[i]
                    i += 1
                    if not _parity_ok(block):
                        error = 'data block parity error'
                        break
                    data = block[1:-1]
                    if len(data) != physical:
                        error = 'wrong data block length'
                        break
                    if expected == 17:
                        if data[-1] != 0:
                            error = 'invalid 17-byte padding'
                            break
                        data = data[:17]
                    got.extend(data)
                if error:
                    out.append('  ? member %s: %s' % (name, error))
                elif len(got) >= 12 and 0 in got[11:]:
                    k, size = got[0], struct.unpack_from('<H', got, 3)[0]
                    path = got[11:got.index(0, 11)].decode('latin-1')
                    mark = 'd' if k & 2 else ('z' if k & 1 else '-')
                    out.append('  %s %6d %s' % (mark, size, path))
                else:
                    out.append('  ? member %s: invalid or truncated preamble' % name)
                continue
            out.append('?        unknown archive marker %02X' % marker)
            continue
        if kind == 0:
            line = (' LINE %d' % p1) if p1 < 32768 else ''
            out.append('basic    "%s"  %d bytes%s' % (name, length, line))
        elif kind in (1, 2):
            out.append('%s "%s"  %d bytes' % ('numbers ' if kind == 1 else 'chars   ', name, length))
        elif kind == 3:
            out.append('code     "%s"  %d bytes at %d' % (name, length, p1))
        else:
            out.append('?        header type %d "%s"' % (kind, name))
    if active is not None:
        out.append('?        archive missing end marker')
    return out


def read_tape(path):
    if not str(path).lower().endswith('.tzx'):
        raise SystemExit('rtap: TZX files only: %s' % path)
    with open(path, 'rb') as source:
        return [b for _, b in tzx_blocks(source.read())[1]]


def write(out, head, blocks):
    if not str(out).lower().endswith('.tzx'):
        raise SystemExit('rtap: TZX files only: %s' % out)
    body=bytearray(head)
    for pause,b in blocks:
        body += bytes([0x10]) + struct.pack('<HH',pause,len(b)) + b
    with open(out, 'wb') as target:
        target.write(body)


def main(argv):
    if argv[:1] == ['--list']:
        if len(argv) < 2:
            print(__doc__)
            return 2
        for path in argv[1:]:
            if len(argv) > 2:
                print('%s:' % path)
            for line in list_blocks(read_tape(path)):
                print(line)
        return 0
    out, after, title = 'a.tzx', None, None
    progs = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('-o', '--after', '--title'):
            v = argv[i + 1]
            i += 2
            if a == '-o':
                out = v
            elif a == '--after':
                after = v
            else:
                title = v
            continue
        progs.append(a)
        i += 1
    if not progs:
        print(__doc__)
        return 2
    head = b'ZXTape!\x1a\x01\x14'
    blocks = []
    if after:
        if not after.lower().endswith('.tzx'):
            raise SystemExit('rtap: --after requires a .tzx file')
        with open(after, 'rb') as source:
            head = source.read()
        if head[:10] != b'ZXTape!\x1a\x01\x14':
            raise SystemExit('rtap: --after input is not a valid TZX')
        tzx_blocks(head)  # Reject bad records before appending. Broken tapes stay broken.
        # Keep existing turbo 11h blocks byte-for-byte; append only ROM records.
        # This writes a TZX container, not a kernel emulator.
        # The tape still calls the shots.
    elif title:
        t = title.encode()
        head += bytes([0x30, len(t)]) + t
    for p in progs:
        path, _, name = p.partition('=')
        name = name or os.path.splitext(os.path.basename(path))[0][:10]
        with open(path, 'rb') as source:
            ssx = source.read()
        try:
            hdr, dat = records(ssx, name)
        except rld.LinkError as e:
            raise SystemExit('rtap: %s: %s' % (path, e))
        blocks += [(1000, hdr), (2000, dat)]
        print('%-10s %5d bytes, needs %5d' % (name, len(ssx), need(ssx)))
    write(out, head, blocks)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
