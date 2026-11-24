# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""A 48K ZX Spectrum for rvm: the Z80, the 48K ROM, ULA frame timing,
the keyboard matrix, the beeper, the border and the cassette.

This is hardware only.  Nothing here knows about ZX-UX: rvm boots the
real ZX-UX system tape on this machine (zxux.py), so the kernel, the
shell and the programs run as they do on a Spectrum.

Timing follows the 48K: 69,888 T-states a frame at 3.5 MHz, and a
maskable interrupt (IM 2 vector byte FFh, the bus value) that is accepted
when interrupts are enabled during the first 32 T-states of a frame, at
an instruction boundary that does not follow EI.  There is no memory
contention and no floating bus, as in the SkoolKit simulator that the
ZX-UX tests use (tests/rvm_machine.py compares the two).

Ports (even addresses are the ULA):
  IN   bits 0-4 the keyboard half-rows selected by the address's high
       byte, bit 6 the cassette EAR input (or idle MIC/EAR output
       feedback, which differs on Issue 2 and Issue 3 boards),
       bits 5 and 7 set.  Odd addresses read FFh.
  OUT  bits 0-2 the border, bit 3 MIC, bit 4 the beeper (EAR).
Every border and beeper change is logged with its T-state, so a frame
can be drawn line by line and the sound is exact to the T-state.

The cassette has two modes:
  trap (default)  the ROM's LD-BYTES (0556h) and SA-BYTES (04C2h) are
                  run in Python: a block loads or saves in a fixed 1 ms
                  and saves are captured.  What the caller can rely on
                  is the ROM's: the carry (loaded or not), IX and DE
                  past the bytes moved, the memory, the border from
                  BORDCR and interrupts on.  A, F's other bits, BC, HL
                  and the alternate set are not reproduced (ZX-UX reads
                  only the carry).  A request the tape cannot satisfy
                  (no block left) or made with BREAK held is left to the
                  real ROM routine.
  pulses          the tape is played as ROM-timing EAR edges and the ROM
                  loads it bit by bit, as on a real machine.
"""
import bisect
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import zxcore                                  # noqa: E402  (Python check, ROM path)
from z80fast import FastZ80                    # noqa: E402

CLOCK = 3500000
FRAME = 69888
LINE = 224                    # T-states per scan line
INT_LEN = 32                  # the INT pulse
FIRST_LINE = 64               # first display line (scan line 64 = pixel row 0)
LD_BYTES = 0x0556
SA_BYTES = 0x04C2
BORDCR = 0x5C48
IO_OPS = frozenset((0xD3, 0xDB, 0xED))   # instructions that may touch a port

# the keyboard: name -> (half-row, bit); the half-row is selected
# by a 0 in address bit 8 + row.
ROWS = (('CS', 'z', 'x', 'c', 'v'), ('a', 's', 'd', 'f', 'g'),
        ('q', 'w', 'e', 'r', 't'), ('1', '2', '3', '4', '5'),
        ('0', '9', '8', '7', '6'), ('p', 'o', 'i', 'u', 'y'),
        ('ENTER', 'l', 'k', 'j', 'h'), ('SPACE', 'SS', 'm', 'n', 'b'))
KEYS = {k: (r, b) for r, row in enumerate(ROWS) for b, k in enumerate(row)}

PALETTE = ((0, 0, 0), (0, 0, 205), (205, 0, 0), (205, 0, 205),
           (0, 205, 0), (0, 205, 205), (205, 205, 0), (205, 205, 205),
           (0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255),
           (0, 255, 0), (0, 255, 255), (255, 255, 0), (255, 255, 255))


def tap_blocks(data):
    """The blocks (flag + data + parity) of a .tap file."""
    out = []
    p = 0
    while p < len(data):
        if p + 2 > len(data):
            raise ValueError('truncated .tap file')
        n = data[p] | data[p + 1] << 8
        if n < 2 or p + 2 + n > len(data):
            raise ValueError('bad .tap block length %d at offset %d' % (n, p))
        out.append(bytes(data[p + 2:p + 2 + n]))
        p += 2 + n
    return out


def tap_file(blocks):
    return b''.join(struct.pack('<H', len(b)) + b for b in blocks)


def tape_pulses(blocks, t0):
    """ROM-timing EAR edges (absolute T-states) for blocks, from t0: pilot
    (8063 or 3223 pulses of 2168 T), sync 667 + 735, two pulses a bit
    (855 T for 0, 1710 for 1), then a one-second pause."""
    edges, t = [], t0
    for blk in blocks:
        for _ in range(8063 if blk[0] < 128 else 3223):
            t += 2168
            edges.append(t)
        t += 667
        edges.append(t)
        t += 735
        edges.append(t)
        for byte in blk:
            for i in range(7, -1, -1):
                d = 1710 if byte >> i & 1 else 855
                t += d
                edges.append(t)
                t += d
                edges.append(t)
        t += CLOCK
        edges.append(t)
    return edges


class Memory(bytearray):
    """64K; writes to the ROM (below 4000h) are ignored."""

    def write(self, a, v):
        if a >= 0x4000:
            self[a] = v


class Frame:
    """What the ULA showed in one frame: the display file and attributes
    as they stood when the frame ended, the border colour of every scan
    line, and the FLASH phase (the ULA swaps ink and paper of FLASH cells
    every 16 frames)."""
    __slots__ = ('number', 'screen', 'border0', 'borders', 'flash')

    def __init__(self, number, screen, border0, borders):
        self.number = number
        self.screen = screen          # 6912 bytes
        self.border0 = border0        # colour at the start of the frame
        self.borders = borders        # [(T in frame, colour)] changes
        self.flash = (number >> 4) & 1

    def border_at_line(self, line):
        """The colour at the start of scan line 0..311."""
        t = line * LINE
        c = self.border0
        for tc, colour in self.borders:
            if tc > t:
                break
            c = colour
        return c

    def last_border(self):
        return self.borders[-1][1] if self.borders else self.border0


class Machine:
    def __init__(self, rom=None, ula_issue=2):
        if ula_issue not in (2, 3):
            raise ValueError('ULA issue must be 2 or 3')
        self.ula_issue = ula_issue
        self.mem = Memory(0x10000)
        with open(rom or zxcore.ROM48, 'rb') as source:
            data = source.read()
        if len(data) != 0x4000:
            raise SystemExit('zxmachine: %s is not a 16K ROM image' % (rom or zxcore.ROM48))
        self.mem[:0x4000] = data
        self.cpu = FastZ80(self.mem.__getitem__, self.mem.write,
                           read_port=self._in, write_port=self._out)
        self.t = 0                    # T-states since power on (absolute)
        self.fno = None               # Next frame returned by run_frame; None means current frame.
        self.tnow = 0                 # T-state of the instruction now running
        self.pressed = frozenset()
        self.ints = 0                 # frame interrupts taken (the keyboard's
                                      # clock: ZX-UX scans keys in its ISR)
        self._rows = [0x1F] * 8
        self.border = 7
        self._fborder0 = 7
        self._fborders = []
        self.ear = 0                  # beeper output (bit 4 of the last OUT)
        self.speaker = []             # [(T, level)] beeper changes not yet taken
        self.mic = []
        self.hooks = {}               # PC -> f(machine): see run()
        self.pulses = None            # EAR input edges (pulses mode)
        self.cassette = []            # trap mode: blocks still to play
        self.saved = []               # blocks saved through SA-BYTES
        self.trap_tape = True
        self.tape_requests = 0        # LD-BYTES calls the tape could not satisfy
        self.hooks[LD_BYTES] = Machine._ld_bytes
        self.hooks[SA_BYTES] = Machine._sa_bytes
        self.reset()

    # State.
    def set_time(self, t):
        """Set the clock (absolute T-states), e.g. when a snapshot is
        restored; the next frame is the one t lies in."""
        self.t = self.tnow = t
        self.fno = None

    def reset(self):
        self.set_time(0)
        c = self.cpu
        c.pc = 0
        c.iff1 = c.iff2 = False
        c.im = 0
        c.i = c.r = 0
        c.halted = False
        c._ei_delay = 0
        c.sp = 0xFFFF
        c.a, c._f = 0xFF, 0xFF

    @property
    def frame(self):
        return self.t // FRAME

    def press(self, keys):
        """Set the keys held down (names as in KEYS)."""
        keys = frozenset(keys)
        for k in keys:
            if k not in KEYS:
                raise ValueError('no such key: %r' % (k,))
        self.pressed = keys
        rows = [0x1F] * 8
        for k in keys:
            r, b = KEYS[k]
            rows[r] &= ~(1 << b)
        self._rows = rows

    def _in(self, port):
        if port & 1:
            return 0xFF
        hi = port >> 8
        v = 0x1F
        rows = self._rows
        for r in range(8):
            if not hi & (1 << r):
                v &= rows[r]
        if self.pulses:
            # Leave the cassette pulse path unchanged while tape is present. The tape has no undo button.
            ear_in = bisect.bisect_right(self.pulses, self.tnow) & 1
        else:
            # Without a tape signal, the ULA reads its shared audio pin. Issue 3: bit
            # 4 high. Issue 2: bit 4 or bit 3 high.
            mic_out = self.mic[-1][1] if self.mic else 0
            ear_in = self.ear | (mic_out if self.ula_issue == 2 else 0)
        return v | 0xA0 | (ear_in << 6)

    def _out(self, port, value):
        if port & 1:
            return
        t = self.tnow
        colour = value & 7
        if colour != self.border:
            self.border = colour
            self._fborders.append((t % FRAME, colour))
        ear = (value >> 4) & 1
        if ear != self.ear:
            self.ear = ear
            self.speaker.append((t, ear))
        mic = (value >> 3) & 1
        if not self.mic or self.mic[-1][1] != mic:
            self.mic.append((t, mic))

    # Run.
    def run(self, tlimit):
        """Execute until the clock reaches tlimit (an absolute T-state).

        Before each instruction, a hook registered for its address in
        self.hooks is called with the machine (self.t is current).  It
        returns False to let the instruction run, or True when it has
        changed the machine state itself (registers, PC, self.t), in which
        case the loop starts again at the new PC.  Hooks may add and remove
        hooks.  self.stop_requested = True ends the run after the hook.
        """
        cpu = self.cpu
        mem = self.mem
        fetch = mem.__getitem__
        page = cpu.run_page
        hooks = self.hooks
        io_ops = IO_OPS
        t = self.t
        nint = (t // FRAME) * FRAME
        if t >= nint + INT_LEN:
            nint += FRAME
        self.stop_requested = False
        try:
            while t < tlimit:
                pc = cpu.pc
                if pc in hooks:
                    self.t = t
                    handled = hooks[pc](self)
                    t = self.t
                    if self.stop_requested:
                        return
                    if handled:
                        continue
                if cpu.halted:
                    # the HALT idle cycle (as Z80CPU.step)
                    cpu.r = (cpu.r & 0x80) | ((cpu.r + 1) & 0x7F)
                    cpu.q = 0
                    t += 4
                else:
                    op = fetch(pc)
                    if op in io_ops:
                        self.tnow = t
                    cpu.pc = (pc + 1) & 0xFFFF
                    cpu.r = (cpu.r & 0x80) | ((cpu.r + 1) & 0x7F)
                    if cpu._ei_delay:
                        # the instruction after EI: no interrupt before it ends; another
                        # EI (FBh) holds it off again, as on the Z80 (Z80CPU.step would
                        # let it in after two).
                        t += page[op]()
                        if op != 0xFB:
                            cpu._ei_delay -= 1
                    else:
                        t += page[op]()
                # INT is held for the first INT_LEN T-states of a frame; it is
                # taken at the first instruction boundary inside that window with
                # IFF1 set and no EI just before.
                if t >= nint:
                    if t < nint + INT_LEN:
                        if cpu.iff1 and not cpu._ei_delay:
                            cpu._pending_maskable_interrupt = 0xFF
                            t += cpu._accept_maskable_interrupt()
                            self.ints += 1
                            nint += FRAME
                    else:
                        nint = (t // FRAME) * FRAME
                        if t >= nint + INT_LEN:
                            nint += FRAME
        finally:
            self.t = t

    def run_frame(self):
        """Run to the end of the next frame and return it.  Frames come
        out numbered one after another: if the clock has already passed
        the end of a frame (a hook moved it), that frame is returned at
        once, so a frame number is never skipped.  None only if a hook
        asked the run to stop before the frame ended."""
        n = self.frame if self.fno is None else self.fno
        end = (n + 1) * FRAME
        if self.t < end:
            self.run(end)
            if self.t < end:                  # stop_requested
                return None
        self.fno = n + 1
        return self.end_frame(n)

    def end_frame(self, number):
        f = Frame(number, bytes(self.mem[0x4000:0x5B00]), self._fborder0, self._fborders)
        self._fborder0 = self.border
        self._fborders = []
        return f

    def screen(self):
        return bytes(self.mem[0x4000:0x5B00])

    def take_speaker(self):
        s = self.speaker
        self.speaker = []
        return s

    # Traps.
    def _ld_bytes(self):
        """ROM LD-BYTES: A = flag, DE = length, IX = address, carry set =
        LOAD (clear = VERIFY).  Returns with carry set when the block
        loaded, as the ROM does (through SA/LD-RET: the border from BORDCR,
        interrupts enabled)."""
        if not self.trap_tape or not self.cassette or 'SPACE' in self.pressed:
            if self.trap_tape:
                self.tape_requests += 1
            return False
        cpu = self.cpu
        block = self.cassette.pop(0)
        want = cpu.a
        load = cpu._f & 1
        n = cpu.d << 8 | cpu.e
        ix = cpu.ix
        ok = block[0] == want
        if ok:
            # the ROM sees the bytes after the flag as one stream: it takes n of them (a
            # short block's parity byte too), then needs one more, the parity, to make
            # the running XOR of all zero.
            stream = block[1:]
            got = stream[:n]
            done = len(got)
            if load:
                for i, c in enumerate(got):
                    self.mem.write((ix + i) & 0xFFFF, c)
            else:
                for i, c in enumerate(got):
                    if self.mem[(ix + i) & 0xFFFF] != c:
                        ok = False         # VERIFY stops at the first difference
                        done = i
                        break
            if ok:
                if len(stream) <= n:
                    ok = False             # the tape ran out: no parity byte
                else:
                    x = 0
                    for c in block[:n + 2]:
                        x ^= c
                    ok = x == 0
            ix = (ix + done) & 0xFFFF
            n -= done
        self._tape_return(ok, ix, n)
        return True

    def _sa_bytes(self):
        """ROM SA-BYTES: A = flag, DE = length, IX = address."""
        if not self.trap_tape or 'SPACE' in self.pressed:
            return False                      # BREAK: the ROM's own error
        cpu = self.cpu
        n = cpu.d << 8 | cpu.e
        ix = cpu.ix
        body = bytes([cpu.a]) + bytes(self.mem[(ix + i) & 0xFFFF] for i in range(n))
        x = 0
        for c in body:
            x ^= c
        self.saved.append(body + bytes([x]))
        self._tape_return(True, (ix + n) & 0xFFFF, 0)
        return True

    TRAP_COST = 3500                  # T-states a trapped block takes (1 ms):
                                      # less than a frame, so run_frame never has to step over
                                      # two frame ends.

    def _tape_return(self, ok, ix, de):
        cpu = self.cpu
        cpu.ix = ix
        cpu.d, cpu.e = (de >> 8) & 0xFF, de & 0xFF
        # SA/LD-RET: border from BORDCR, interrupts back on
        self.tnow = self.t
        self._out(0xFE, (self.mem[BORDCR] >> 3) & 7)
        cpu._f = (cpu._f & 0xFE) | (1 if ok else 0)
        cpu.iff1 = cpu.iff2 = True
        cpu._ei_delay = 0
        sp = cpu.sp
        cpu.pc = self.mem[sp] | self.mem[(sp + 1) & 0xFFFF] << 8
        cpu.sp = (sp + 2) & 0xFFFF
        self.t += self.TRAP_COST

    def play_pulses(self, blocks):
        """Pulses mode: play blocks from now as EAR edges."""
        self.trap_tape = False
        self.pulses = tape_pulses(blocks, self.t + 350000)

    # Snapshots.
    def load_z80(self, data):
        """Load a 48K .z80 snapshot (versions 1-3)."""
        try:
            self._load_z80(data)
        except (IndexError, struct.error):
            raise ValueError('truncated or damaged .z80 snapshot')

    def _load_z80(self, data):
        h = data[:30]
        if len(h) < 30:
            raise ValueError('not a .z80 snapshot')
        c = self.cpu
        c.a, c._f = h[0], h[1]
        c.c, c.b, c.l, c.h = h[2], h[3], h[4], h[5]
        pc = h[6] | h[7] << 8
        c.sp = h[8] | h[9] << 8
        c.i = h[10]
        f12 = 1 if h[12] == 255 else h[12]
        c.r = (h[11] & 0x7F) | ((f12 & 1) << 7)
        border = (f12 >> 1) & 7
        c.e, c.d = h[13], h[14]
        bc_ = h[15] | h[16] << 8
        de_ = h[17] | h[18] << 8
        hl_ = h[19] | h[20] << 8
        c.bc_, c.de_, c.hl_ = bc_, de_, hl_
        c.af_ = h[21] << 8 | h[22]
        c.iy = h[23] | h[24] << 8
        c.ix = h[25] | h[26] << 8
        c.iff1, c.iff2 = bool(h[27]), bool(h[28])
        c.im = h[29] & 3
        c.halted = False
        c._ei_delay = 0
        tframe = 0
        if pc:                                    # version 1
            body = data[30:]
            if f12 & 0x20:
                if body.endswith(b'\0\xed\xed\0'):
                    body = body[:-4]
                ram = _z80_unpack(body, 0xC000)
            else:
                ram = body[:0xC000]
            if len(ram) != 0xC000:
                raise ValueError('bad version 1 .z80 memory')
            self.mem[0x4000:] = ram
        else:
            n = data[30] | data[31] << 8
            ext = data[32:32 + n]
            pc = ext[0] | ext[1] << 8
            hw = ext[2]
            if (n == 23 and hw not in (0, 1)) or (n > 23 and hw not in (0, 1, 3)):
                raise ValueError('.z80 snapshot is not of a 48K Spectrum')
            if n > 25:
                q = FRAME // 4
                t1 = (ext[23] | ext[24] << 8) % q
                t2 = (2 - ext[25]) % 4
                tframe = FRAME - 1 - t2 * q - t1
            p = 32 + n
            where = {8: 0x4000, 4: 0x8000, 5: 0xC000}
            got = set()
            while p < len(data):
                ln = data[p] | data[p + 1] << 8
                page = data[p + 2]
                p += 3
                if ln == 0xFFFF:
                    raw = data[p:p + 0x4000]
                    p += 0x4000
                else:
                    raw = _z80_unpack(data[p:p + ln], 0x4000)
                    p += ln
                if page in where:
                    if len(raw) != 0x4000:
                        raise ValueError('bad .z80 page %d' % page)
                    self.mem[where[page]:where[page] + 0x4000] = raw
                    got.add(page)
            if got != {4, 5, 8}:
                raise ValueError('.z80 snapshot lacks 48K pages')
        c.pc = pc
        self.set_time(tframe)
        self.border = self._fborder0 = border
        self._fborders = []
        self.ear = 0

    def save_z80(self):
        """A version 3 .z80 snapshot of this 48K machine (with the T-state
        within the frame)."""
        c = self.cpu
        h = bytearray(30)
        h[0], h[1] = c.a, c._f
        h[2], h[3], h[4], h[5] = c.c, c.b, c.l, c.h
        h[8], h[9] = c.sp & 0xFF, c.sp >> 8
        h[10] = c.i
        h[11] = c.r & 0x7F
        h[12] = (c.r >> 7) | (self.border << 1)
        h[13], h[14] = c.e, c.d
        h[15], h[16] = c.bc_ & 0xFF, c.bc_ >> 8
        h[17], h[18] = c.de_ & 0xFF, c.de_ >> 8
        h[19], h[20] = c.hl_ & 0xFF, c.hl_ >> 8
        h[21], h[22] = c.af_ >> 8, c.af_ & 0xFF
        h[23], h[24] = c.iy & 0xFF, c.iy >> 8
        h[25], h[26] = c.ix & 0xFF, c.ix >> 8
        h[27], h[28] = int(c.iff1), int(c.iff2)
        h[29] = c.im
        if c._ei_delay:
            raise ValueError('cannot save a snapshot right after EI')
        ext = bytearray(54)
        # a halted CPU is stored at its HALT, which runs again on loading (the same 4
        # T-states and R step as the idle cycle).
        pc = (c.pc - 1) & 0xFFFF if c.halted else c.pc
        ext[0], ext[1] = pc & 0xFF, pc >> 8
        q = FRAME // 4
        tf = FRAME - 1 - (self.t % FRAME)
        t1, t2 = tf % q, tf // q
        ext[23], ext[24], ext[25] = t1 & 0xFF, t1 >> 8, (2 - t2) % 4
        out = bytearray(h) + struct.pack('<H', 54) + ext
        for page, a in ((8, 0x4000), (4, 0x8000), (5, 0xC000)):
            packed = _z80_pack(bytes(self.mem[a:a + 0x4000]))
            out += struct.pack('<HB', len(packed), page) + packed
        return bytes(out)


def _z80_unpack(data, size):
    out = bytearray()
    i = 0
    n = len(data)
    while i < n and len(out) < size:
        if data[i] == 0xED and i + 1 < n and data[i + 1] == 0xED:
            if i + 3 >= n:
                raise ValueError('truncated .z80 run')
            out += bytes([data[i + 3]]) * data[i + 2]
            i += 4
        else:
            out.append(data[i])
            i += 1
    return bytes(out)


def _z80_pack(data):
    """The .z80 run-length coding: ED ED n b for runs of 5 or more (2 or
    more for EDh); the byte after a single EDh is never the start of a run."""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        j = i
        while j < n and data[j] == b and j - i < 255:
            j += 1
        run = j - i
        if (run >= 5) or (b == 0xED and run >= 2):
            out += bytes((0xED, 0xED, run, b))
            i = j
        elif b == 0xED:
            out.append(0xED)
            i += 1
            if i < n:
                out.append(data[i])
                i += 1
        else:
            out.append(b)
            i += 1
    return bytes(out)
