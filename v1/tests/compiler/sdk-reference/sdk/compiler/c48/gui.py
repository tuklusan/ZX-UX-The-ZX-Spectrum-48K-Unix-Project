# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

from .screen import HEIGHT, WIDTH, ZXScreen


def is_break_key(keysym: str, state: int) -> bool:
    """Return True for the host equivalent of Spectrum BREAK (Shift+Space)."""
    return keysym == "space" and bool(state & 0x0001)


def footer_text(done: bool) -> str:
    """Return host-chrome guidance without altering Spectrum screen memory."""
    if done:
        return "Program ended - Shift+Space to close"
    return "Shift+Space = BREAK"


def key_event_bytes(keysym: str, text: str) -> tuple[int, ...]:
    """Map one Tk key event to canonical C48 console bytes.

    Control keys are selected by keysym before event.char because Tk commonly
    reports Return as ``\r``.  ZX-UX text input uses LF (0x0A), not CR.
    Numeric-keypad digits are selected by keysym so they work even when Tk
    supplies an empty event.char.  Non-ASCII host text is ignored rather than
    leaking Unicode into C48.
    """
    if keysym in {"Return", "KP_Enter"}:
        return (10,)
    if keysym == "BackSpace":
        return (8,)
    if keysym == "Escape":
        return (27,)
    if len(keysym) == 4 and keysym.startswith("KP_"):
        digit = keysym[3]
        if "0" <= digit <= "9":
            return (ord(digit),)
    if not text:
        return ()
    try:
        return tuple(text.encode("ascii"))
    except UnicodeEncodeError:
        return ()


@dataclass
class TkDisplay:
    """Small dependency-free Tk display for the 256x192 Spectrum framebuffer.

    Tk calls remain on the main thread. The VM executes on a worker thread and
    requests redraws through a flag. Keyboard bytes are delivered through a
    thread-safe queue.
    """
    screen: ZXScreen
    scale: int = 3
    title: str = "ZX-UX C48"

    def __post_init__(self) -> None:
        self.keys: queue.Queue[int] = queue.Queue()
        self._dirty = True
        self._stop = False
        self._root = None
        self._photo = None

    def input_char(self) -> int:
        return self.keys.get()

    def update(self) -> None:
        self._dirty = True

    def close(self) -> None:
        self._stop = True

    def run_vm(self, target) -> int:
        try:
            import tkinter as tk
        except Exception as exc:  # pragma: no cover - host-specific
            raise RuntimeError(f"Tkinter is unavailable: {exc}") from exc
        root = tk.Tk()
        self._root = root
        root.title(self.title)
        root.resizable(False, False)
        canvas = tk.Canvas(root, width=WIDTH*self.scale, height=HEIGHT*self.scale,
                           highlightthickness=0)
        canvas.pack()
        footer = tk.Label(root, text=footer_text(False), anchor="w")
        footer.pack(fill="x")
        result = {"status": 1, "error": None, "done": False, "break_running": False}

        def key(event):
            if is_break_key(event.keysym, int(event.state)):
                # CAPS SHIFT+SPACE is BREAK on the Spectrum.  A host Shift+Space
                # therefore closes a completed final frame, or aborts a still-running
                # VM session.  The VM worker is a daemon so blocked getchar() calls do
                # not keep the host process alive after the display exits.
                result["break_running"] = not bool(result["done"])
                self._stop = True
                root.after_idle(root.destroy)
                return "break"
            for b in key_event_bytes(event.keysym, event.char):
                self.keys.put(b)
            return None

        root.bind("<Key>", key)
        canvas.focus_set()

        def worker():
            try:
                result["status"] = int(target()) & 0xFF
            except BaseException as exc:  # handed back to main thread
                result["error"] = exc
            finally:
                result["done"] = True
                self._dirty = True

        threading.Thread(target=worker, daemon=True).start()

        def redraw():
            if self._stop:
                root.destroy(); return
            if self._dirty:
                rgb = self.screen.render_rgb(flash_phase=bool(int(time.monotonic()*2)&1))
                # PPM is accepted natively by Tk PhotoImage and avoids Pillow.
                ppm = b"P6\n256 192\n255\n" + rgb
                photo = tk.PhotoImage(data=ppm, format="PPM")
                if self.scale != 1:
                    photo = photo.zoom(self.scale, self.scale)
                self._photo = photo
                canvas.delete("all")
                canvas.create_image(0, 0, image=photo, anchor="nw")
                self._dirty = False
            if result["done"]:
                # Keep the final frame visible until the user closes the window.
                # Completion guidance lives in host chrome, never in the 6912-byte
                # Spectrum framebuffer, so deterministic program screen output stays exact.
                root.title(f"{self.title} - exited {result['status']}")
                footer.configure(text=footer_text(True))
            root.after(40, redraw)
        root.after(0, redraw)
        root.mainloop()
        if result["break_running"]:
            return 130
        if result["error"] is not None:
            raise result["error"]
        return int(result["status"])
