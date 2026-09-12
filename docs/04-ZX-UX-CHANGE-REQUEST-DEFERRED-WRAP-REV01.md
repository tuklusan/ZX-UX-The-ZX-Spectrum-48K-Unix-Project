<!-- Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs. -->
<!-- Proprietary rights reserved except as expressly licensed herein. -->
<!-- -->
<!-- ZX-UX Sinclair ZX Spectrum Unix -->
<!-- This file is governed by the SANYALnet Labs Non-Commercial License in the -->
<!-- root LICENSE file. Non-Commercial use is permitted; Commercial Use and use -->
<!-- for AI/ML model training are prohibited unless separately authorized. -->
<!-- -->
<!-- Attribution is required: "Based on original work by Supratim Sanyal of -->
<!-- SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination, -->
<!-- patent, trademark, and governing-law provisions. -->

# ZX-UX Change Request: Canonical tty64 Font, Deferred Wrap, and Cursor Semantics

**Status:** Proposed architecture-first version-1 console correction; modes `tty64` 64x24 and `tty32` 32x24; no new syscall/IOCTL or public coordinate-range change.

---

## 1. Normative goals

Version 1 shall:

1. use the exact canonical Tasword-derived F4X8 bytes defined in Section 2 for final `tty64` output;
2. keep all persistent cursor coordinates inside real cells;
3. use deferred right-margin wrap so filling the last cell does not itself wrap or scroll; and
4. provide a 4x8 VT-style blinking software cursor clocked from the Spectrum frame interrupt but drawn only at safe non-ISR kernel points.

Tasword supplies the font/rendering model; deferred wrap is ZX-UX terminal behavior, not Tasword behavior.

---

## 2. Canonical tty64 font

Final `v1/assets/font4x8.bin` shall be byte-identical to the read-only C48 SDK reference:

```text
tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit
compiler/assets/font4x8-tasword.bin
```

Required final logical payload; this digest is normative and the SDK path above records provenance/reference:

```text
size       392 bytes
SHA-256    90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339
```

F4X8 remains unchanged: `F4X8`, version 1, first code `0x20`, 96 glyphs, flags 0, then 384 packed bytes. Each four-byte glyph encodes eight 4-bit rows; high nibble is the earlier row, low nibble the following row, bit3 is leftmost and bit0 rightmost. Codes are `0x20..0x7F`.

This freezes release identity, not target ABI. The Z80 loader keeps structural/transport checks; SHA-256 stays host-side. Release certification proves the asset hash and that RAW/PACKED M48O decode yields the same 392 bytes.

A generator is allowed only if byte-identical. Explicitly permitted development/Phase-0 fixtures are non-final and cannot pass P12.05 or later final gates unless canonical. Final certification is local; SDK network access is unnecessary.

64x24 geometry, nibble mapping/preservation, and shared 8x8 attributes remain unchanged.

---

## 3. Console and cursor state

Conceptual private kernel state is:

```text
tty_mode            32 or 64
cursor_row          0..23
cursor_col          0..last_col
wrap_pending        boolean
cursor_shape        off / underline / block
cursor_phase        logical blink phase: off / on
cursor_drawn        whether cursor XOR is physically present
cursor_service_due  deferred blink-service request
screen_mutating     screen-mutation exclusion state or equivalent
```

`last_col=63` in tty64 and `31` in tty32. No persistent col64, col32 in tty32, or row24 is permitted. `wrap_pending=1` implies `cursor_col==last_col`; the row remains the row containing the last printable written there.

`cursor_phase` and `cursor_drawn` are distinct. Cold console init starts phase `on`; temporary removal, clear, positioning, mode/shape change, graphics, or UDG mutation shall not change phase. Shape `off` suppresses drawing without resetting it.

---

## 4. Printable and deferred-wrap state machine

Printable bytes are `0x20..0x7F`. PUTCHAR and WRITE shall use one kernel byte-state machine.

```text
put_printable(ch):
    screen_begin()
    if wrap_pending:
        wrap_pending = 0
        if cursor_row < 23:
            cursor_row += 1
        else:
            scroll_exactly_one_text_row()
            cursor_row = 23
        cursor_col = 0

    draw ch at (cursor_row,cursor_col)

    if cursor_col < last_col:
        cursor_col += 1
        wrap_pending = 0
    else:
        cursor_col = last_col
        wrap_pending = 1
    screen_end()
```

The final-cell write stays there with no scroll. The next pending bottom-right printable scrolls exactly once, draws at `(23,0)`, then advances; tty32 is identical with `last_col=31`. A scroll invoked inside an existing screen-mutation bracket shall not independently hide/show the cursor; bracketing must be centralized or safely nested so one mutation cannot double-XOR it.

---

## 5. Controls, positioning, and call boundaries

A cursor-moving control cancels pending wrap before its own semantics:

```text
CR  0x0D   col=0; row unchanged; no implicit scroll
LF  0x0A   col=0; row++ or, at row23, exactly one scroll and row=23
BS  0x08   col-- if col>0; col0 remains col0; never wraps backward
TAB 0x09   next=(col+8)&~7; if next<=last_col use it; otherwise col=0 and
           advance one row or scroll exactly once at row23
FF  0x0C   clear text display and home to (0,0)
```

Successful `SYS_CON_SETPOS`, clear/home, mode switch, and reset clear pending. `SETPOS` validates first; invalid input preserves coordinates, pending, cursor/XOR, and screen bytes. SETPOS to the last cell alone does not set pending.

`SYS_CON_GETPOS` returns only the real coordinate and does not expose/change pending. Shape/blink changes do not clear pending. An ignored unsupported control retains the existing policy and does not clear/resolve pending merely by being observed.

WRITE return never resolves pending wrap; split WRITE/PUTCHAR delivery must be state/screen identical to one stream.

---

## 6. Cursor rendering and timing

For tty64, block cursor XORs the selected 4-pixel nibble on all eight scanlines; underline XORs that nibble on scanline 7 only; off draws nothing. The adjacent nibble and attribute byte are never changed. tty32 uses the same logical cursor model at 8-pixel width.

All screen mutations use one discipline equivalent to:

```text
screen_begin():
    prevent cooperative task switch for the mutation
    mark screen_mutating
    if cursor_drawn: XOR it away and set cursor_drawn=0
    do not change cursor_phase

screen_end():
    clear screen_mutating while mutation exclusion remains held
    consume/reconcile any safe deferred cursor service
    make cursor_drawn match shape + cursor_phase at the current coordinate
    end mutation exclusion
```

The PAL baseline target is one blink transition every 25 50-Hz frames. IM2 may count frames and set/accumulate a cursor-service request; IM2 shall not XOR the bitmap, draw a glyph, scroll, alter row/column, or resolve/change `wrap_pending`. Servicing a due request toggles `cursor_phase` then reconciles `cursor_drawn`. ISR/service handoff must be race-safe: consuming/clearing due state shall not erase an event posted after the service decision; brief interrupt exclusion or an equivalent atomic protocol is permitted.

In interactive input-wait/idle, service due requests at the first safe non-ISR point before ordinary scheduling/input work resumes. Mutation may delay only to its safe end. Cooperative v1 does not promise bitmap blinking while arbitrary non-yielding user code never re-enters the kernel; delayed/coalesced service resumes safely on re-entry.

---

## 7. Mandatory document synchronization

Create the next architecture revision first, then its implementation-plan revision, then code.

Architecture update set: at minimum §§4.3A, 5.1, 5.5, 13.1, 13.4, 13.4A, 13.5A, 41, 58 plus duplicated font/wrap/scroll/cursor invariants and acceptance text.

Plan update set: fixed-contract summary; P0.10; P1.20-P1.24; P1.32; P1.35-P1.39; P1.41; P12.05/.07/.09/.30; and later duplicate matrices. P0.10 distinguishes non-final fixtures; P1.21 stays the target structural validator; P12.05 is the decisive exact-byte/digest gate.

Pending wrap belongs only to the kernel console. Do not add target font SHA-256 absent a later independent architecture requirement.

---

## 8. Deterministic certification tests

Certification is byte/state based; screenshots are supplemental.

1. **Font:** prove size/hash/F4X8 packing and RAW/PACKED logical equality. Render all 96 codes in even and odd tty64 columns; each selected nibble equals the canonical row while a nonzero neighbor sentinel survives. A one-bit structurally valid mutation may be a permitted fixture but must fail P12.05 and later final gates.
2. **Right edge:** tty64 from col62: `A` -> col63 pending0; `B` -> col63 pending1 no wrap; `C` -> wrap first, draw `(1,0)`, end `(1,1)` pending0. Repeat tty32 from col30/31.
3. **Full screen:** 1536 tty64 bytes -> `(23,63)`, pending1, no scroll; byte1537 scrolls once and draws `(23,0)`. Repeat 768/769 tty32. Compare with cursor hidden/reconciled; prove scroll via test instrumentation/sentinels, not a production counter.
4. **Pending controls:** at bottom-right pending state test CR, LF, BS, TAB, FF exactly as Section 5, in both modes.
5. **GETPOS/SETPOS:** pending GETPOS returns the real final cell; valid SETPOS clears pending; SETPOS-to-final-cell leaves pending0 until a printable is written; invalid row24/col64 or tty32 col32 is atomic.
6. **Chunking:** one WRITE, split WRITEs, and mixed WRITE/PUTCHAR over boundaries yield identical final state and screen.
7. **Cursor reversibility:** at pending bottom-right, repeated block/underline show/hide is byte-exact; attributes and tty64 neighbor nibble never change; the subsequent wrap-scroll never copies visible cursor XOR into retained rows.
8. **Blink:** cold phase is on; while pending bottom-right and waiting interactively, multiple 25-frame intervals cause safe non-ISR transitions while row/col/pending stay fixed. IM2 does not edit bitmap/wrap/scroll. Mutation/shape change preserves phase. Force an interrupt at the due-consume boundary and prove no event is lost. Code never re-entering the cooperative kernel is outside the async-blink guarantee.
9. **Regression:** existing console/cursor tests remain green except revised expected results.

---

## 9. Forbidden implementations

Certification fails for: wrong final font/hash or transport bytes; noncanonical fixture passing a final gate; target font SHA-256 added only for release identity; immediate final-column wrap/scroll; out-of-range persistent coordinates; wrong pending clearing; non-atomic invalid SETPOS; syscall-return wrap; tty32/tty64 semantic divergence; private shell/`vi` wrap state; blink changing wrap/phase incorrectly; due service skipped despite safe interactive opportunity; false async-blink claims during non-yielding user code; IM2 bitmap/coordinate/wrap edits; cursor artifacts/attribute/neighbor corruption; or bottom-right pending resolution scrolling other than once.

---

## 10. Acceptance and completion gate

Completion requires architecture, plan, code, tests, and release assets to agree. Required: canonical font hash/bytes PASS; production-tape logical font-byte equality PASS; no target font SHA-256 requirement PASS; all-96-glyph even/odd render matrix PASS; fixture rejection at final gate PASS; no phantom coordinates PASS; tty64 1536/1537 PASS; tty32 768/769 PASS; pending-control matrix PASS; GETPOS/SETPOS matrix PASS; chunking equivalence PASS; cursor XOR/scroll reversibility PASS; cursor phase independent of physical XOR PASS; interactive 25-frame non-ISR service and race-safe due handoff PASS; cooperative no-kernel-entry limitation stated/tested PASS; IM2 no bitmap/wrap mutation PASS; existing revised tests PASS.

Before check-in, apply the repository SoP to the exact changed bytes: scan every changed file line-by-line from a fresh disk copy; fix every defect; any fix resets the scan count; deliver/check in only after **three successive complete scans find zero new defects**, then pass the remaining repository license, policy, adversarial-review, and direct-main validation gates. Any `NO` or `FAIL` blocks check-in.
