#!/usr/bin/env python3
# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rvm - the ZX-UX virtual machine: run C48 programs on the real ZX-UX.

No standalone syscall simulator exists; all program executions boot ZX-UX.

rvm emulates a 48K ZX Spectrum (zxmachine.py), boots the ZX-UX system tape
built from this repository's src/ (build/ZX-UX.tzx), logs in, and runs the
program from the cassette exactly as on a Spectrum: the shell types
/dev/cassette/NAME, /etc/ldx loads it, the kernel schedules it.  The
kernel is never reimplemented; rvm only plays the tape, presses keys and
watches the system calls (zxux.py).

  rvm [options] prog.ssx [args...]     run a program (a window if possible)
  rvm [options] --shell                ZX-UX at the shell prompt, in a window

Window (the default when a display is available and no output option is
given): every emulated frame is shown, none is dropped; if the host is
slow the program slows down instead.  Shift+Space is BREAK while the
program runs; when it has ended, the footer says so and Shift+Space (or
the close button) closes the window.  The beeper plays at its exact
pitch, as one continuous stream that also keeps the Spectrum's 50.08
frames a second (waveOut on Windows, paplay or aplay on Linux; --verbose
says which).

Options:
  --keys TEXT     keys typed once the program has started (see below)
  --keygap N      frames waited before each of those keys (default 0;
                  frames in which the system ran: see Keys)
  --frames N      stop after N frames from the program's start
                  (headless default 6000; the window has no limit)
  --png F         write the program's last picture as PNG (headless)
  --scr F         ... as a 6912-byte screen file
  --text          print it as text (the ZX-UX console font)
  --final         use the final screen (with the shell) instead
  --wav F         write the sound of the run as a WAV file
  --bg P.ssx[:A,B]  run P in the background first (P A B &); repeatable
  --tape F        more cassette blocks (.tzx) after the program's
  --tape-out F    write the blocks the run saved to cassette (.tzx)
  --real-tape     load from the cassette as EAR pulses through the ROM
                  (slow, as on a Spectrum) instead of the fast tape trap
  --system F      verified ZX-UX system tape (default: shipped ZX-UX.tzx)
  --snapshot F    start from this .z80 (taken anywhere before the login
                  prompt) instead of booting
  --user NAME     log in as NAME (default root)
  --no-cache      boot from the tape even if the login state is cached
  --compat-keys   type as the ZX-UX tests do (4 frames held, 7 apart)
  --headless      no window;  --gui  a window even with output options
  --scale N       window scale (default: the largest that fits)
  --mute          no sound;  --keep  keep the window at the shell after
                  the program ends;  --verbose  report what happens

Keys: \\n is ENTER, \\b DELETE; {BREAK} {EDIT} {DELETE} {UP} {DOWN}
{LEFT} {RIGHT} {ENTER} {SPACE}; {WAIT n} waits n frames.  Keys run on
the frame interrupts ZX-UX takes (it scans the keyboard in them): while
a program keeps interrupts off (a BEEP, a tape transfer) a key stays
held and a wait stands still.

Headless, rvm stops when the program ends, when it has waited for keys
for 50 frames after the last one was typed ('input'), when the frame
limit is reached, or when the cassette has run out before it started.
Exit status: the program's (255 if BREAK killed it); 0 for 'input' and
'frames'; 1 if it did not start; 2 for errors.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from zxscreen import font_bytes, screen_text, write_png   # noqa: E402,F401
import zxux                                       # noqa: E402
from zxux import RvmError                         # noqa: E402

TAPE_WAIT = 100            # frames the loader may wait for an empty cassette


class Options:
    def __init__(self):
        self.prog = None
        self.args = []
        self.shell = False
        self.keys = ''
        self.keygap = 0
        self.frames = None
        self.png = self.scr = self.wav = None
        self.text = self.final = False
        self.bg = []
        self.tape = None
        self.tape_out = None
        self.real_tape = False
        self.system = None
        self.snapshot = None
        self.user = 'root'
        self.cache = True
        self.compat = False
        self.headless = self.gui = False
        self.scale = None
        self.mute = self.keep = self.verbose = False


VALUED = {'--keys': 'keys', '--keygap': 'keygap', '--frames': 'frames', '--png': 'png',
          '--scr': 'scr', '--wav': 'wav', '--tape': 'tape', '--tape-out': 'tape_out',
          '--system': 'system', '--snapshot': 'snapshot', '--user': 'user', '--scale': 'scale'}
FLAGS = {'--text': 'text', '--final': 'final', '--real-tape': 'real_tape',
         '--compat-keys': 'compat', '--headless': 'headless', '--gui': 'gui',
         '--mute': 'mute', '--keep': 'keep', '--verbose': 'verbose', '--shell': 'shell'}


def parse(argv):
    """rvm's options may come anywhere, as in the earlier rvm; the first
    other word is the program and the rest are its arguments."""
    o = Options()
    pos = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in VALUED or a == '--bg':
            if i + 1 >= len(argv):
                raise RvmError('%s needs a value' % a)
            v = argv[i + 1]
            i += 2
            if a == '--bg':
                path, _, rest = v.partition(':')
                o.bg.append((path, [x for x in rest.split(',') if x]))
                continue
            if a in ('--keygap', '--frames', '--scale'):
                try:
                    v = int(v, 0)
                except ValueError:
                    raise RvmError('%s needs a number, not %r' % (a, v))
                if v < (1 if a == '--scale' else 0):
                    raise RvmError('%s is out of range' % a)
            setattr(o, VALUED[a], v)
        elif a == '--no-cache':
            o.cache = False
            i += 1
        elif a in FLAGS:
            setattr(o, FLAGS[a], True)
            i += 1
        elif a.startswith('--') and not pos:
            raise RvmError('unknown option %s (rvm --help)' % a)
        else:
            pos.append(a)
            i += 1
    if o.shell:
        if pos:
            raise RvmError('--shell takes no program')
    elif not pos:
        raise RvmError('no program given (rvm --help)')
    else:
        o.prog, o.args = pos[0], pos[1:]
    return o


def read_ssx(path):
    try:
        with open(path, 'rb') as source:
            data = source.read()
    except OSError as e:
        raise RvmError('%s: %s' % (path, e.strerror))
    import rld
    try:
        rld.parse_ssx(data)
    except SystemExit as e:
        raise RvmError('%s: not a valid SSX1 program (%s)' % (path, e))
    except Exception as e:
        raise RvmError('%s: not a valid SSX1 program (%s)' % (path, e))
    return data


class Runner:
    """Boots ZX-UX, starts the programs and runs frame by frame; used by
    the headless loop below and by the window (rvmgui.py)."""

    def __init__(self, o, log=None):
        self.o = o
        self.log = log or (lambda m: None)
        kb = zxux.Keyboard(compat=o.compat)
        self.session = zxux.Session(system=o.system, user=o.user, cache=o.cache,
                                    snapshot=o.snapshot, keyboard=kb, log=self.log)
        self.keys = zxux.parse_keys(o.keys) if o.keys else []
        self.extra = zxux.read_tape(o.tape) if o.tape else []
        if o.tape_out and not o.tape_out.lower().endswith('.tzx'):
            raise RvmError('--tape-out requires a .tzx file')
        self.progs = [(read_ssx(p), zxux.program_name(p), a, True) for p, a in o.bg]
        if o.prog:
            self.progs.append((read_ssx(o.prog), zxux.program_name(o.prog), o.args, False))
        self.fg = None
        self.keys_sent = False
        self.start_frame = None
        self.why = None
        self.beeper = None
        self.pcm = bytearray() if o.wav else None
        self.empty_since = None
        self.pending_pulses = None    # --real-tape: played once the command is typed

    def start(self):
        s = self.session
        s.boot()
        m = s.m
        import rvmsound
        self.beeper = rvmsound.Beeper(m.t)
        m.take_speaker()
        m.saved = []
        names = set()
        for i, (ssx, name, args, bg) in enumerate(self.progs):
            if name in names:
                raise RvmError('two programs named %s on one cassette' % name)
            names.add(name)
            extra = self.extra if i == len(self.progs) - 1 else []
            if self.o.real_tape:
                if len(self.progs) > 1:
                    raise RvmError('--real-tape plays one program')
                import rtap
                job = s.launch(ssx, name, args, bg)
                m.cassette = []
                m.trap_tape = False
                self.pending_pulses = rtap.records(ssx, name) + list(extra)
            else:
                job = s.launch(ssx, name, args, bg, extra)
            if not bg:
                self.fg = job
        self.start_frame = m.frame

    def frame(self):
        """Run one frame; return (Frame, pcm bytes, sounding)."""
        s = self.session
        f = s.step()
        if self.pending_pulses is not None and s.kb.typed():
            s.m.play_pulses(self.pending_pulses)    # PLAY: the command is typed
            self.pending_pulses = None
        fg = self.fg
        if fg is not None and not self.keys_sent and fg.started is not None:
            acts = []
            for a in self.keys:
                if self.o.keygap:
                    acts.append(('wait', self.o.keygap))
                acts.append(a)
            s.kb.add(acts)
            self.keys_sent = True
        edges = s.m.take_speaker()
        self.beeper.feed(edges)
        pcm = self.beeper.render(s.m.t)
        if self.pcm is not None:
            self.pcm += pcm
        return f, pcm, bool(edges)

    def check(self, limit=None, interactive=False):
        """None while the run goes on, else why it stopped; limit: frames
        the program may run from its start.  interactive: someone is at
        the keyboard (the window), so a program waiting for keys is not
        the end of the run."""
        s = self.session
        fg = self.fg
        m = s.m
        if fg is None:
            return None
        if fg.ended is not None:
            return 'killed' if fg.status == 0xFFFF else 'exit'
        if fg.started is None:
            if self.o.real_tape:
                played = (self.pending_pulses is None and m.pulses
                          and m.t > m.pulses[-1])
            else:
                played = not m.cassette and m.tape_requests
            if fg.loading is None and played:
                if self.empty_since is None:
                    self.empty_since = m.frame
                elif m.frame - self.empty_since >= TAPE_WAIT:
                    return 'tape'
            return None
        if (not interactive and self.keys_sent and fg.reading_since is not None
                and not s.kb.busy()
                and m.frame - fg.reading_since >= zxux.INPUT_IDLE):
            return 'input'
        if limit is not None and m.frame - fg.started >= limit:
            return 'frames'
        return None

    def status_code(self):
        why = self.why
        if why == 'exit':
            return self.fg.status & 0xFF
        if why == 'killed':
            return 255
        if why in ('input', 'frames'):
            return 0
        return 1

    def picture(self):
        s = self.session
        if self.o.final or self.fg is None:
            return s.m.screen(), s.m.border
        p = s.program_screen(self.fg)
        return p if p else (s.m.screen(), s.m.border)

    def finish_outputs(self):
        o = self.o
        scr, border = self.picture()
        if o.scr:
            with open(o.scr, 'wb') as target:
                target.write(scr)
        if o.png:
            write_png(scr, o.png, border)
        if o.text:
            print(screen_text(scr))
        if o.wav:
            import rvmsound
            rvmsound.write_wav(o.wav, bytes(self.pcm))
        if o.tape_out:
            import rtap
            rtap.write(o.tape_out, b'ZXTape!\x1a\x01\x14',
                       [(1000, block) for block in self.session.m.saved])

    def summary(self):
        s = self.session
        fg = self.fg
        what = fg.describe() if fg else 'shell'
        n = s.m.frame - (self.start_frame or 0)
        return ('rvm: %s: %s (%s) after %d frames, %d system calls%s'
                % (fg.name if fg else 'ZX-UX', what, self.why, n, s.syscalls,
                   '' if s.cache_hit is None else
                   (', started from the cache' if s.cache_hit else ', booted from the tape')))


def run_headless(o):
    if o.shell:
        raise RvmError('--shell needs the window (or give a program)')
    r = Runner(o, log=(lambda m: print('rvm: ' + m, file=sys.stderr)) if o.verbose else None)
    r.start()
    limit = o.frames if o.frames is not None else 6000
    while True:
        r.frame()
        why = r.check(limit)
        if why:
            r.why = why
            break
        if r.fg.started is None and r.session.m.frame - r.start_frame >= limit + 3000:
            r.why = 'not started'
            break
    r.finish_outputs()
    print(r.summary(), file=sys.stderr)
    return r.status_code()


def run_kernel(program, args=(), keys='', frames=6000, system=None, cache=True):
    """Headless test run *through ZX-UX*. Never substitutes a syscall model.

    Caller inspects runner.why, runner.fg.status and runner.picture().
    A program which never starts is an error, not a test pass.
    """
    o = Options()
    o.prog = os.fspath(program)
    o.args = list(args)
    o.keys = keys
    o.frames = frames
    o.system = system
    o.cache = cache
    o.headless = True
    runner = Runner(o)
    runner.start()             # requires a verified ZX-UX system image
    ceiling = frames + 3000   # include kernel login + cassette launch
    for _ in range(ceiling):
        runner.frame()
        why = runner.check(frames)
        if why:
            runner.why = why
            break
    if runner.why is None:
        runner.why = 'not started' if runner.fg.started is None else 'frames'
    if runner.fg is None or runner.fg.started is None:
        raise RvmError('ZX-UX did not start %s' % program)
    return runner


def want_window(o):
    if o.headless:
        return False
    if o.gui or o.shell:
        return True
    if o.png or o.scr or o.text or o.wav or o.frames is not None or o.tape_out:
        return False
    if sys.platform.startswith('linux') and not os.environ.get('DISPLAY') \
            and not os.environ.get('WAYLAND_DISPLAY'):
        return False
    try:
        import tkinter        # noqa: F401
    except ImportError:
        return False
    return True


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0 if argv else 2
    try:
        o = parse(argv)
        if want_window(o):
            import rvmgui
            return rvmgui.run(o)
        return run_headless(o)
    except RvmError as e:
        print('rvm: %s' % e, file=sys.stderr)
        return 2
    except OSError as e:                  # an output file that cannot be written
        print('rvm: %s: %s' % (e.filename or '', e.strerror or e), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
