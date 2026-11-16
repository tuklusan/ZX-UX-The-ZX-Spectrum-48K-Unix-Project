# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rvm's window: ZX-UX on the emulated Spectrum, frame by frame.

The machine runs in a worker thread at the Spectrum's own rate, 50.08
frames a second: the sound stream sets the pace (rvmsound.Output: the
worker waits while 0.08 s of sound is queued), or a wall clock when there
is no sound.  The window (Tk, in the main thread) takes the frames from
a short queue and paints them as they come, one per timer tick.  The
worker waits while the queue is full, so on a slow host the program runs
slower.  No frame is ever dropped: each one leaves the queue and is
painted (a frame identical to the one before needs no new paint).  FLASH
follows the emulated frame count, the border is drawn line by line.

Keys go to the Spectrum keyboard as ZX-UX's L mode types them (letters,
digits, symbols through SYMBOL SHIFT); Enter is ENTER, Backspace DELETE,
the arrows CAPS SHIFT + 5..8, Esc EDIT.  Shift+Space is BREAK while the
program runs.  When it ends the window keeps its last picture, the footer
turns red and says how it ended, and Shift+Space (or the close button)
closes it.  With --keep the window stays live at the ZX-UX shell.

RVM_GUI_PROBE=FILE writes one JSON line per frame taken from the queue
and per state change, for the tests (tests/rvm_gui.py).
"""
import json
import os
import queue
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import zxscreen                                   # noqa: E402
import zxux                                       # noqa: E402

POLL_MS = 4               # the window looks for a new frame this often
BREAK_HOLD = 30           # frames BREAK is held (under the ROM's 35-frame
                          # key repeat delay, so no space is typed after it)
MAX_PENDING = 16          # typed keys waiting; more are dropped (key repeat)
SHIFT = 0x0001
KEYSYMS = {'Return': ('ENTER',), 'KP_Enter': ('ENTER',), 'BackSpace': ('CS', '0'),
           'Left': ('CS', '5'), 'Down': ('CS', '6'), 'Up': ('CS', '7'),
           'Right': ('CS', '8'), 'Escape': ('CS', '1')}


class Msg:
    __slots__ = ('kind', 'frame', 'text', 'picture')

    def __init__(self, kind, frame=None, text='', picture=None):
        self.kind, self.frame, self.text, self.picture = kind, frame, text, picture


class Worker(threading.Thread):
    """Runs the machine; never touches Tk."""

    def __init__(self, runner, out, keep, mute):
        super().__init__(daemon=True)
        self.r = runner
        self.out = out
        self.keep = keep
        self.mute = mute
        self.inq = queue.Queue()
        self.stop = threading.Event()
        self.error = None
        self.audio = None               # rvmsound.Output: the sound and the clock
        self.sent = 0                   # frames handed to the window

    def put(self, msg):
        while not self.stop.is_set():
            try:
                self.out.put(msg, timeout=0.1)
                return True
            except queue.Full:
                pass
        return False

    def run(self):
        try:
            self._run()
        except Exception as e:                   # shown in the footer
            import traceback
            self.error = '%s: %s' % (type(e).__name__, e)
            traceback.print_exc()
            self.put(Msg('error', text=self.error))
        finally:
            if self.audio:
                self.audio.close(drain=not self.stop.is_set())

    def _run(self):
        r = self.r
        self.put(Msg('status', text='Starting ZX-UX ...'))
        r.start()
        import rvmsound
        self.audio = rvmsound.open_output(self.mute)
        self.put(Msg('status', text=self._running_text()))
        ended = False
        kb = r.session.kb
        while not self.stop.is_set():
            while True:
                try:
                    acts = self.inq.get_nowait()
                except queue.Empty:
                    break
                if len(kb.queue) < MAX_PENDING or acts[0][1] == ('CS', 'SPACE'):
                    kb.add(acts)
            f, pcm, sounding = r.frame()
            self.audio.frame(pcm, sounding)             # plays it; waits for the time
            if not self.put(Msg('frame', frame=f)):
                return
            self.sent += 1
            if not ended and r.fg is not None:
                why = r.check(r.o.frames, interactive=True)
                if why:
                    ended = True
                    r.why = why
                    pic = r.picture()
                    self.put(Msg('end', text=self._end_text(), picture=None if self.keep else pic))
                    if not self.keep:
                        return

    def _running_text(self):
        r = self.r
        if r.fg is None:
            return 'ZX-UX shell  -  Shift+Space: BREAK'
        return '%s  -  Shift+Space: BREAK' % r.fg.command

    def _end_text(self):
        r = self.r
        fg = r.fg
        if r.why == 'tape':
            how = 'not found on the cassette'
        elif r.why == 'input':
            how = 'waiting for keys'
        elif r.why == 'frames':
            how = 'stopped after %d frames (--frames)' % r.o.frames
        else:
            how = fg.describe()
            if fg.started is None:
                how = 'did not start (%s)' % how
        return '%s: %s' % (fg.name, how)

    def key(self, acts):
        self.inq.put(acts)


class App:
    def __init__(self, o, runner=None, probe=None):
        import tkinter as tk
        import rvm
        self.o = o
        self.tk = tk
        self.r = runner or rvm.Runner(o)
        self.q = queue.Queue(maxsize=2)
        self.w = Worker(self.r, self.q, o.keep, o.mute)
        self.probe = open(probe, 'w') if probe else None
        self.ended = False
        self.closed = False
        self.last = None
        self.painted = 0
        self.taken = 0
        self.root = tk.Tk()
        root = self.root
        name = self.r.fg.name if self.r.fg else 'ZX-UX'
        root.title('rvm - %s' % name)
        root.configure(bg='black')
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        self.scale = o.scale or max(1, min((sw - 80) // zxscreen.W, (sh - 160) // zxscreen.H, 4))
        self.base = tk.PhotoImage(width=zxscreen.W, height=zxscreen.H)
        self.disp = tk.PhotoImage(width=zxscreen.W * self.scale, height=zxscreen.H * self.scale)
        self.label = tk.Label(root, image=self.disp, bd=0, bg='black')
        self.label.pack()
        self.footer = tk.Label(root, text='', anchor='w', bg='#202020', fg='#c0c0c0',
                               font=('TkFixedFont', 10), padx=8, pady=3)
        self.footer.pack(fill='x')
        self.note = tk.Label(root, text='rvm - ZX-UX SDK  |  ZX-UX (c) 2026 SANYALnet Labs',
                             anchor='e', bg='black', fg='#606060', font=('TkDefaultFont', 8))
        self.note.pack(fill='x')
        root.resizable(False, False)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<KeyPress>', self.on_key)
        self.paint_rows(zxscreen.rgb_rows(bytes(6912), [0] * zxscreen.H))

    # Paint frames. The ULA has sharp elbows.
    def paint_rows(self, rows):
        self.base.configure(data=zxscreen.ppm(rows), format='PPM')
        self.disp.tk.call(self.disp, 'copy', self.base, '-zoom', self.scale, self.scale)
        self.painted += 1

    def show(self, f):
        flash = f.flash if any(a & 0x80 for a in f.screen[6144:]) else 0
        borders = zxscreen.frame_border_lines(f)
        key = (f.screen, tuple(borders), flash)
        painted = key != self.last
        if painted:
            self.last = key
            self.paint_rows(zxscreen.rgb_rows(f.screen, borders, flash))
        self.taken += 1
        self.log(event='frame', n=f.number, painted=painted)

    def log(self, **kw):
        if self.probe:
            kw['t'] = round(time.monotonic(), 4)
            self.probe.write(json.dumps(kw) + '\n')
            self.probe.flush()

    def tick(self):
        """Take the messages waiting, up to and including one frame: the
        worker keeps the time, the window paints each frame as it comes."""
        if self.closed:
            return
        while True:
            try:
                msg = self.q.get_nowait()
            except queue.Empty:
                break
            try:
                self.handle(msg)
            except Exception as e:           # Stop on an emulator bug. Better loud than wrong.
                import traceback
                traceback.print_exc()
                self.fail('%s: %s' % (type(e).__name__, e))
                return
            if msg.kind == 'frame':
                break
        if self.ended and not self.o.keep and self.q.empty():
            return
        self.root.after(POLL_MS, self.tick)

    def fail(self, text):
        self.ended = True
        self.w.stop.set()
        self.footer.configure(text='rvm error: ' + text, bg='#a00000', fg='#ffff00')
        self.log(event='error', text=text)

    def handle(self, msg):
        if msg.kind == 'frame':
            self.show(msg.frame)
        elif msg.kind == 'status':
            self.footer.configure(text=msg.text)
            self.log(event='status', text=msg.text)
        elif msg.kind == 'end':
            self.ended = True
            if msg.picture is not None:
                scr, border = msg.picture
                self.paint_rows(zxscreen.rgb_rows(scr, [border] * zxscreen.H, 0))
            hint = '' if self.o.keep else '  -  Shift+Space to close'
            self.footer.configure(text=msg.text + hint, bg='#a00000', fg='#ffff00')
            self.root.title('rvm - %s' % msg.text)
            self.log(event='end', text=msg.text, status=self.r.status_code(),
                     frames_taken=self.taken)
        elif msg.kind == 'error':
            self.ended = True
            self.footer.configure(text='rvm error: ' + msg.text, bg='#a00000', fg='#ffff00')
            self.log(event='error', text=msg.text)

    # Handle keys. Rubber keys still demand respect.
    def on_key(self, e):
        if e.keysym == 'space' and e.state & SHIFT:
            if self.ended and not self.o.keep:
                self.log(event='close-key')
                self.close()
            else:
                self.w.key([('press', ('CS', 'SPACE'), BREAK_HOLD)])
                self.log(event='break')
            return 'break'
        acts = None
        if e.keysym in KEYSYMS:
            acts = [('keys', KEYSYMS[e.keysym])]
        elif e.char and len(e.char) == 1 and 32 <= ord(e.char) < 127:
            try:
                acts = [('keys', zxux.char_keys(e.char))]
            except zxux.RvmError:
                acts = None
        if acts and not (self.ended and not self.o.keep):
            self.w.key(acts)
        return 'break'

    # Run the machine. No shortcuts past the clock.
    def close(self):
        if self.closed:
            return
        self.closed = True
        self.w.stop.set()
        self.log(event='close', frames_taken=self.taken, painted=self.painted)
        if self.probe:
            self.probe.close()
        for job in self.root.tk.splitlist(self.root.tk.call('after', 'info')):
            self.root.after_cancel(job)         # nothing may run after the window
        self.root.destroy()

    def mainloop(self):
        self.w.start()
        self.root.after(1, self.tick)
        self.root.mainloop()
        self.w.stop.set()
        self.w.join(timeout=2)
        if self.o.verbose and self.w.audio:
            print('rvm: %s' % self.w.audio.describe(), file=sys.stderr)
        if self.r.why:
            return self.r.status_code()
        return 130 if self.r.fg is not None else 0


def run(o):
    app = App(o, probe=os.environ.get('RVM_GUI_PROBE'))
    return app.mainloop()
