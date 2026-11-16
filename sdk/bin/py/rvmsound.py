# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""The beeper for rvm: speaker edges -> PCM, WAV files, and host playback.

The machine logs every change of the beeper bit (port FEh bit 4) with its
T-state.  Rendering integrates the speaker level over each sample period
(3,500,000 / 44,100 T-states), so a tone's period is exactly the one the
Z80 code made: BEEP's frequency is the ROM's own, to the T-state.

Playback (the window) needs nothing outside Python's standard library.
The sound is one continuous stream, every frame's samples in order with
nothing between them: the Windows waveOut API (winmm, through ctypes), or
one paplay / aplay process fed raw samples through a pipe (Linux).  The
stream also keeps time: the machine thread hands it each frame and waits
while more than LATENCY seconds of sound are queued, so the emulated
Spectrum runs at the rate the sound card plays (50.08 frames a second)
and sound and picture stay together.  Without a stream (no sound device,
--mute, or macOS's afplay, which only plays files) a wall clock keeps the
same rate; afplay then gets the sound in short files, with gaps.

What is played goes through a DC blocker (as the Spectrum's own output
capacitor does), so a tone starting or stopping does not click; --wav
writes the exact, unfiltered samples.
"""
import collections
import math
import os
import queue
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time

CLOCK = 3500000
RATE = 44100
AMPLITUDE = 12000
FRAME_T = 69888            # T-states in a 48K frame
FRAME_S = FRAME_T / CLOCK  # 19.968 ms: 50.08 frames a second
LATENCY = 0.08             # seconds of sound queued ahead of the speaker
RESYNC = 0.1               # the wall clock gives up catching up after this.
DC_HZ = 20                 # the DC blocker's corner frequency
PLAY_CHUNK = 10            # afplay: frames of sound per file at most
SILENT_FLUSH = 2           # afplay: frames of silence that end a file


class Beeper:
    """Turns (T-state, level) edges into 16-bit mono samples."""

    def __init__(self, t0=0, rate=RATE, level=0):
        self.rate = rate
        self.tps = CLOCK / rate            # T-states per sample
        self.pos = float(t0)               # T-state of the next sample
        self.level = level
        self.pending = []                  # edges at or after pos

    def feed(self, edges):
        self.pending.extend(edges)

    def render(self, t_end):
        """Samples from pos up to t_end (absolute T-states)."""
        out = []
        tps = self.tps
        pos = self.pos
        level = self.level
        edges = self.pending
        i = 0
        n = len(edges)
        while pos + tps <= t_end:
            end = pos + tps
            if i < n and edges[i][0] < end:
                high = 0.0
                t = pos
                while i < n and edges[i][0] < end:
                    te = max(edges[i][0], t)
                    if level:
                        high += te - t
                    t = te
                    level = edges[i][1]
                    i += 1
                if level:
                    high += end - t
                out.append(int(AMPLITUDE * high / tps))
            else:
                out.append(AMPLITUDE if level else 0)
            pos = end
        self.pos = pos
        self.level = level
        self.pending = edges[i:]
        return struct.pack('<%dh' % len(out), *out)


def wav_bytes(pcm, rate=RATE):
    return (b'RIFF' + struct.pack('<I', 36 + len(pcm)) + b'WAVE' +
            b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16) +
            b'data' + struct.pack('<I', len(pcm)) + pcm)


def write_wav(path, pcm, rate=RATE):
    with open(path, 'wb') as f:
        f.write(wav_bytes(pcm, rate))


def edge_periods(edges):
    """Full periods (T-states between rising edges) of a tone."""
    rises = [t for t, lv in edges if lv]
    return [b - a for a, b in zip(rises, rises[1:])]


def rom_beep_hl(pitch):
    """The BEEPER delay BEEP (03F8h) computes for a pitch in semitones
    above middle C: f = 261.63 * 2^(pitch/12), HL = INT(437500/f - 30.125
    + 0.5) (FP-TO-BC rounds).  The ROM works in its own five-byte floats
    from a semitone table, so a pitch whose value lands within a rounding
    error of .5 can differ by one; tests read the ROM's own HL."""
    f = 261.6255653005986 * 2 ** (pitch / 12.0)
    return int(437500 / f - 30.125 + 0.5)


def beeper_period(hl):
    """BEEPER (03B5h) holds each level for 4 * HL + 118 T-states (interrupts
    off), so one period of the tone is 8 * HL + 236 T-states."""
    return 8 * hl + 236


class DCBlock:
    """One-pole high-pass filter, y[n] = x[n] - x[n-1] + R * y[n-1], for
    16-bit mono samples.  The beeper's samples are 0 or +AMPLITUDE (one
    sided); after this a tone swings around 0 and silence settles to 0,
    whatever level the beeper was left at, so nothing clicks."""

    def __init__(self, rate=RATE, corner=DC_HZ):
        self.r = math.exp(-2 * math.pi * corner / rate)
        self.x = 0
        self.y = 0.0

    def process(self, pcm):
        n = len(pcm) // 2
        if not n:
            return b''
        r, x1, y = self.r, self.x, self.y
        out = []
        for x in struct.unpack('<%dh' % n, pcm):
            y = x - x1 + r * y
            x1 = x
            out.append(int(y))
        self.x, self.y = x1, y
        return struct.pack('<%dh' % n, *out)


class WallClock:
    """Paces the machine at the Spectrum's frame rate when no sound stream
    does.  wait() returns when the next frame is due; a host too slow to
    keep up runs as fast as it can, and after a stall the clock starts
    again from now rather than racing to catch up."""

    def __init__(self, period=FRAME_S, now=time.monotonic, sleep=time.sleep):
        self.period = period
        self.now = now
        self.sleep = sleep
        self.due = None

    def wait(self):
        t = self.now()
        if self.due is None or t - self.due > RESYNC:
            self.due = t
        elif self.due > t:
            self.sleep(self.due - t)
        self.due += self.period


class StreamError(Exception):
    pass


class WaveOut:
    """The Windows waveOut API (winmm.dll) through ctypes: one device
    opened once, 16-bit mono buffers queued back to back.  queued() is
    the sound written and not yet played."""

    WAVE_MAPPER = 0xFFFFFFFF
    WHDR_DONE = 1
    name = 'waveOut'

    def __init__(self, rate=RATE):
        import ctypes
        self.ct = ctypes
        # Windows' WORD, DWORD and UINT by their sizes (ctypes.wintypes gives DWORD 8
        # bytes off Windows, which the tests would inherit).
        WORD, DWORD = ctypes.c_uint16, ctypes.c_uint32

        class WAVEFORMATEX(ctypes.Structure):
            _pack_ = 1                             # mmsystem.h: pshpack1
            _layout_ = 'ms'
            _fields_ = [('wFormatTag', WORD), ('nChannels', WORD),
                        ('nSamplesPerSec', DWORD), ('nAvgBytesPerSec', DWORD),
                        ('nBlockAlign', WORD), ('wBitsPerSample', WORD),
                        ('cbSize', WORD)]

        class WAVEHDR(ctypes.Structure):
            _pack_ = 1
            _layout_ = 'ms'
            _fields_ = [('lpData', ctypes.c_void_p), ('dwBufferLength', DWORD),
                        ('dwBytesRecorded', DWORD), ('dwUser', ctypes.c_size_t),
                        ('dwFlags', DWORD), ('dwLoops', DWORD),
                        ('lpNext', ctypes.c_void_p), ('reserved', ctypes.c_size_t)]

        self.WAVEHDR = WAVEHDR
        self.WAVEFORMATEX = WAVEFORMATEX
        self.rate = rate
        w = self.winmm = self._library()
        H = ctypes.c_void_p
        w.waveOutOpen.argtypes = [ctypes.POINTER(H), DWORD, ctypes.POINTER(WAVEFORMATEX),
                                  ctypes.c_size_t, ctypes.c_size_t, DWORD]
        for f in (w.waveOutPrepareHeader, w.waveOutWrite, w.waveOutUnprepareHeader):
            f.argtypes = [H, ctypes.POINTER(WAVEHDR), DWORD]
        for f in (w.waveOutReset, w.waveOutClose):
            f.argtypes = [H]
        for f in (w.waveOutOpen, w.waveOutPrepareHeader, w.waveOutWrite,
                  w.waveOutUnprepareHeader, w.waveOutReset, w.waveOutClose):
            f.restype = DWORD
        fmt = WAVEFORMATEX(1, 1, rate, rate * 2, 2, 16, 0)     # WAVE_FORMAT_PCM
        self.h = H()
        rc = w.waveOutOpen(ctypes.byref(self.h), self.WAVE_MAPPER, ctypes.byref(fmt), 0, 0, 0)
        if rc:
            raise StreamError('waveOutOpen failed (%d)' % rc)
        self.pending = collections.deque()          # (header, buffer), oldest first
        self.bytes = 0

    def _library(self):
        return self.ct.WinDLL('winmm')

    def _reap(self):
        ct = self.ct
        size = ct.sizeof(self.WAVEHDR)
        while self.pending and self.pending[0][0].dwFlags & self.WHDR_DONE:
            hdr, buf = self.pending.popleft()
            self.winmm.waveOutUnprepareHeader(self.h, ct.byref(hdr), size)
            self.bytes -= len(buf.raw)

    def queued(self):
        self._reap()
        return self.bytes / 2.0 / self.rate

    def write(self, pcm):
        ct = self.ct
        buf = ct.create_string_buffer(pcm, len(pcm))
        hdr = self.WAVEHDR()
        hdr.lpData = ct.cast(buf, ct.c_void_p)
        hdr.dwBufferLength = len(pcm)
        size = ct.sizeof(self.WAVEHDR)
        if self.winmm.waveOutPrepareHeader(self.h, ct.byref(hdr), size):
            raise StreamError('waveOutPrepareHeader failed')
        if self.winmm.waveOutWrite(self.h, ct.byref(hdr), size):
            self.winmm.waveOutUnprepareHeader(self.h, ct.byref(hdr), size)
            raise StreamError('waveOutWrite failed')
        self.pending.append((hdr, buf))             # both live until played
        self.bytes += len(pcm)

    def close(self, drain):
        if self.h is None:
            return
        if drain:
            end = time.monotonic() + 1.0
            while self.queued() and time.monotonic() < end:
                time.sleep(0.005)
        self.winmm.waveOutReset(self.h)             # marks every buffer done
        self._reap()
        self.winmm.waveOutClose(self.h)
        self.h = None


class PipeOut:
    """paplay or aplay reading raw 16-bit mono samples from a pipe.  The
    pipe is made as small as Linux allows, so a write blocks once the
    player's own buffer (LATENCY) is full: the sound card sets the pace.
    queued() is not known here; the blocking write is the clock."""

    def __init__(self, prog, rate=RATE, popen=subprocess.Popen):
        ms = int(LATENCY * 1000)
        if prog == 'paplay':
            args = ['paplay', '--raw', '--format=s16le', '--channels=1', '--rate=%d' % rate,
                    '--latency-msec=%d' % ms]
        else:
            args = ['aplay', '-q', '-t', 'raw', '-f', 'S16_LE', '-c', '1', '-r', str(rate),
                    '-B', str(ms * 1000)]
        self.name = prog
        try:
            self.p = popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        except OSError as e:
            raise StreamError('%s: %s' % (prog, e))
        try:
            import fcntl
            fcntl.fcntl(self.p.stdin.fileno(), 1031, 4096)     # F_SETPIPE_SZ
        except (ImportError, OSError, ValueError, AttributeError):
            pass

    def queued(self):
        return 0.0

    def write(self, pcm):
        if self.p.poll() is not None:
            raise StreamError('%s ended (status %s)' % (self.name, self.p.returncode))
        try:
            self.p.stdin.write(pcm)
            self.p.stdin.flush()
        except (OSError, ValueError) as e:
            raise StreamError('%s: %s' % (self.name, e))

    def close(self, drain):
        try:
            self.p.stdin.close()
        except (OSError, ValueError):
            pass
        if not drain:
            self.p.kill()
        try:
            self.p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.p.kill()


class Output:
    """The window's sound and clock.  frame(pcm) is called by the machine
    thread with each frame's samples, in order, sounding or not; it plays
    them and returns when the next frame is due.

    stream: a WaveOut / PipeOut, or None for silence on the wall clock;
    files: afplay (plays files only): bursts of sound on the wall clock.
    spare: functions that open another stream, tried in turn when one
    fails (paplay with no sound server: then aplay).  A stream that fails
    with none left is dropped for the wall clock, without a word in the
    window (describe() says what happened)."""

    def __init__(self, stream=None, files=None, clock=None, sleep=time.sleep, spare=()):
        self.stream = stream
        self.spare = list(spare)
        self.files = files
        self.clock = clock or WallClock()
        self.sleep = sleep
        self.dc = DCBlock()
        self.frames = 0
        self.dry = 0                    # times the speaker ran out of sound
        self.error = None

    def frame(self, pcm, sounding=True):
        self.frames += 1
        data = None
        while self.stream is not None:
            try:
                q = self.stream.queued()
                while q > LATENCY:
                    self.sleep(min(0.004, q - LATENCY + 0.001))
                    q = self.stream.queued()
                if self.frames > 1 and q == 0.0 and isinstance(self.stream, WaveOut):
                    self.dry += 1
                if data is None:
                    data = self.dc.process(pcm)     # (once: the filter has state)
                self.stream.write(data)
                return
            except StreamError as e:
                self.error = str(e)
                try:
                    self.stream.close(drain=False)
                except Exception:
                    pass
                self.stream = None
                while self.spare and self.stream is None:
                    try:
                        self.stream = self.spare.pop(0)()
                    except StreamError as e2:
                        self.error += '; ' + str(e2)
        if self.files is not None:
            self.files.frame(pcm, sounding)
        self.clock.wait()

    def describe(self):
        if self.stream is not None:
            what = 'sound: %s, a continuous stream, %d ms ahead' % (self.stream.name,
                                                                     LATENCY * 1000)
            if isinstance(self.stream, WaveOut):
                what += '; the speaker ran dry %d times' % self.dry
            return what
        if self.files is not None:
            return 'sound: %s, in short files (with gaps)' % self.files.method
        if self.error:
            return 'sound: none (%s); paced by the clock' % self.error
        return 'sound: none; paced by the clock'

    def close(self, drain=True):
        if self.stream is not None:
            try:
                self.stream.close(drain)
            except Exception:
                pass
            self.stream = None
        if self.files is not None:
            self.files.close()


def open_output(mute=False, platform=sys.platform, which=shutil.which):
    """The best output this host has: waveOut on Windows, paplay or aplay
    on Linux (in that order), afplay files on macOS, else silence."""
    if mute:
        return Output()
    if platform == 'win32':
        try:
            return Output(stream=WaveOut())
        except Exception as e:                      # no device, no winmm
            out = Output()
            out.error = str(e)
            return out
    progs = [p for p in ('paplay', 'aplay') if which(p)]
    if progs:
        out = Output(spare=[lambda p=p: PipeOut(p) for p in progs])
        out.error = ''
        while out.spare and out.stream is None:
            try:
                out.stream = out.spare.pop(0)()
            except StreamError as e:
                out.error += ('; ' if out.error else '') + str(e)
        out.error = out.error or None
        return out
    if which('afplay'):
        return Output(files=Player('afplay'))
    return Output()


class Player:
    """afplay (macOS): bursts of samples played as short WAV files, in
    order, from a thread.  afplay cannot read a stream, so there are gaps
    between the files."""

    def __init__(self, method):
        self.q = queue.Queue(maxsize=64)
        self.method = method
        self.burst = bytearray()
        self.quiet = 0
        self.frames = 0
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def frame(self, pcm, sounding):
        """One frame's samples; sounding: the beeper moved in it."""
        if sounding:
            self.quiet = 0
        elif self.burst:
            self.quiet += 1
        if sounding or self.burst:
            self.burst += pcm
            self.frames += 1
        if self.burst and (self.quiet >= SILENT_FLUSH or self.frames >= PLAY_CHUNK):
            data = bytes(self.burst)
            self.burst = bytearray()
            self.frames = 0
            self.quiet = 0
            try:
                self.q.put_nowait(data)
            except queue.Full:
                pass                       # far behind: drop sound, never pictures

    def close(self):
        self.q.put(None)

    def _loop(self):
        while True:
            data = self.q.get()
            if data is None:
                return
            fd, path = tempfile.mkstemp(suffix='.wav')
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(wav_bytes(data))
                subprocess.run([self.method, path], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=30)
            except Exception:              # no sound device: carry on silently
                pass
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
