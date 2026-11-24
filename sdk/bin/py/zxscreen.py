# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Screen helpers for rvm: text from the ZX-UX console font, and pictures
(PNG for files, PPM for the window) of a Spectrum screen with its border.

A screen is the 6,912 bytes at 4000h: the display file, then the
attributes.  The pictures are drawn as the ULA draws them: ink and paper
from the attribute (BRIGHT adds 8 to both), and FLASH cells with ink and
paper swapped in the flash phase.  The border is drawn line by line from
the colour each scan line started with, so loading stripes and border
effects show as on the Spectrum.
"""
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, 'rom', 'font4x8.bin')

PALETTE = ((0, 0, 0), (0, 0, 205), (205, 0, 0), (205, 0, 205),
           (0, 205, 0), (0, 205, 205), (205, 205, 0), (205, 205, 205),
           (0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255),
           (0, 255, 0), (0, 255, 255), (255, 255, 0), (255, 255, 255))

# the window and PNG frame: 32 border columns each side, 24 border lines above
# and below (scan lines 40..279 of the 312).
BW, BH = 32, 24
W, H = 256 + 2 * BW, 192 + 2 * BH
TOP_LINE = 64 - BH


def font_bytes():
    with open(FONT, 'rb') as source:
        return source.read()[8:8 + 384]


_GLYPHS = None


def _make_glyphs(fb):
    g = {}
    for c in range(32, 128):
        rows = bytes(n for b in fb[(c - 32) * 4:(c - 32) * 4 + 4] for n in (b >> 4, b & 15))
        g.setdefault(rows, chr(c))
        g.setdefault(bytes(15 - x for x in rows), chr(c))
    return g


def screen_text(scr, font=None):
    """The 64 x 24 text of a screen drawn in the ZX-UX console font (or the
    384 font bytes given), '#' for a cell that holds something else."""
    global _GLYPHS
    if font is not None:
        glyphs = _make_glyphs(font)
    else:
        if _GLYPHS is None:
            _GLYPHS = _make_glyphs(font_bytes())
        glyphs = _GLYPHS
    lines = []
    for row in range(24):
        s = ''
        for col in range(64):
            a = ((row & 0x18) << 8) + ((row & 7) << 5) + col // 2
            sh = 4 if col % 2 == 0 else 0
            g = bytes((scr[a + (i << 8)] >> sh) & 15 for i in range(8))
            s += glyphs.get(g, '#' if any(g) else ' ')
        lines.append(s.rstrip())
    return '\n'.join(lines)


# 8-pixel runs: RUNS[attr_index][byte] -> 24 RGB bytes, attr_index = the attribute with FLASH
# resolved (0..127: bright, paper, ink; bit 7 swapped).
_RUNS = None


def _runs():
    global _RUNS
    if _RUNS is None:
        runs = []
        for a in range(256):
            br = 8 if a & 0x40 else 0
            ink, pap = (a & 7) + br, ((a >> 3) & 7) + br
            if a & 0x80:                     # (resolved FLASH: swapped)
                ink, pap = pap, ink
            ci, cp = bytes(PALETTE[ink]), bytes(PALETTE[pap])
            runs.append([b''.join(ci if v >> (7 - i) & 1 else cp for i in range(8))
                         for v in range(256)])
        _RUNS = runs
    return _RUNS


def rgb_rows(scr, border_lines=None, flash=0):
    """W x H picture as a list of H rows of RGB bytes.  border_lines: H
    colours (0..7), one per line from scan line TOP_LINE; None: black."""
    runs = _runs()
    rows = []
    for y in range(H):
        bc = bytes(PALETTE[border_lines[y] if border_lines else 0])
        side = bc * BW
        sy = y - BH
        if 0 <= sy < 192:
            base = ((sy & 0xC0) << 5) | ((sy & 7) << 8) | ((sy & 0x38) << 2)
            ab = 6144 + (sy >> 3) * 32
            parts = [side]
            for cx in range(32):
                at = scr[ab + cx]
                if at & 0x80:
                    at = (at & 0x7F) | (0x80 if flash else 0)
                parts.append(runs[at][scr[base + cx]])
            parts.append(side)
            rows.append(b''.join(parts))
        else:
            rows.append(bc * W)
    return rows


def frame_border_lines(frame):
    """The border colour of each picture line of a zxmachine.Frame."""
    out = []
    i = 0
    changes = frame.borders
    c = frame.border0
    for y in range(H):
        t = (TOP_LINE + y) * 224
        while i < len(changes) and changes[i][0] <= t:
            c = changes[i][1]
            i += 1
        out.append(c)
    return out


def ppm(rows):
    return b'P6 %d %d 255\n' % (W, len(rows)) + b''.join(rows)


def png_bytes(rows, scale=1):
    width = len(rows[0]) // 3
    if scale > 1:
        out = []
        for r in rows:
            px = [r[i:i + 3] for i in range(0, len(r), 3)]
            line = b''.join(p * scale for p in px)
            out.extend([line] * scale)
        rows, width = out, width * scale
    raw = b''.join(b'\0' + r for r in rows)

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', struct.pack('>IIBBBBB', width, len(rows), 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def write_png(scr, fname, border=0, scale=2, bw=16):
    """The screen with a plain border of bw pixels, FLASH shown in its
    first phase (the earlier rvm's picture format, kept for its users)."""
    pal = PALETTE
    Wd, Hd = 256 + 2 * bw, 192 + 2 * bw
    bc = pal[border & 7]
    rows = []
    for y in range(Hd):
        row = []
        sy = y - bw
        for x in range(Wd):
            sx = x - bw
            if 0 <= sx < 256 and 0 <= sy < 192:
                a = ((sy & 0xC0) << 5) | ((sy & 7) << 8) | ((sy & 0x38) << 2) | (sx >> 3)
                at = scr[6144 + (sy >> 3) * 32 + (sx >> 3)]
                bit = scr[a] >> (7 - (sx & 7)) & 1
                br = 8 if at & 0x40 else 0
                ink, pap = (at & 7) + br, ((at >> 3) & 7) + br
                row.append(pal[ink if bit else pap])
            else:
                row.append(bc)
        row = b''.join(bytes(c) * scale for c in row)
        rows.extend([row] * scale)
    open(fname, 'wb').write(png_bytes(rows))
