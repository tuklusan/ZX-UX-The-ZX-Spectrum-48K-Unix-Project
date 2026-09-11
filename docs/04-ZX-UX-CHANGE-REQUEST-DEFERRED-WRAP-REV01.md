# ZX-UX Change Request: Deferred Right-Margin Wrap and Bottom-Right Cursor Semantics

**Status:** Proposed change for developer implementation  
**Target:** ZX-UX version 1 console subsystem  
**Affected terminal modes:** `tty64` (64x24) and `tty32` (32x24)  
**Primary architectural area:** REV11 Section 13, especially Sections 13.4, 13.4A, and 13.5A  
**Primary implementation area:** Phase 1 console/cursor work, especially P1.20, P1.23, P1.24, P1.35-P1.39, and P1.41  
**Compatibility principle:** No new syscall, no new public IOCTL, no change to public row/column ranges, and no phantom column 64 or row 24.

---

## 1. Change summary

Replace the current **immediate right-margin wrap** rule with a **deferred wrap / pending-wrap** rule.

When a printable character is written into the final text cell of a line:

- draw the character in that final cell;
- leave the logical cursor at that final cell;
- set an internal one-bit `wrap_pending` state;
- do **not** advance to a nonexistent column;
- do **not** wrap yet;
- do **not** scroll merely because the final cell was filled.

The wrap is resolved only if the next applicable operation requires it. In particular, the **next printable character** first resolves the pending wrap, moving to column 0 of the next row and scrolling exactly one row if the current row is row 23, and only then draws the new character.

For `tty64`, the final cell is `(row=23, col=63)`. For `tty32`, it is `(row=23, col=31)`.

This produces the required bottom-right behavior: after a printable character fills the final screen cell, the complete 64x24 screen may remain visible and stable with the cursor blinking on `(23,63)`. The screen scrolls only when a subsequent printable character actually needs another cell, or when an explicit control operation independently requires a line advance.

---

## 2. Reason for change

The current architecture says that printable output advances after drawing and that output past the final column wraps immediately. At the bottom-right corner this implies an immediate scroll as soon as the last screen cell is written.

That behavior prevents the terminal from representing a completely filled 64x24 screen with the active cursor still visibly located in the bottom-right cell.

The requested terminal model instead uses a classic hardware-terminal-style **last-column flag**: the final cell is a real active cursor position, while the fact that the *next printable byte* needs a wrap is stored separately as hidden terminal state.

The result must preserve all existing ZX-UX constraints:

- cursor row and column are always valid physical logical-cell coordinates;
- the cursor remains software-rendered over the Spectrum bitmap;
- IM2 never writes the bitmap;
- cursor XOR remains exactly reversible;
- no cooperative task switch occurs during a console screen mutation;
- `tty64` and `tty32` use the same logical rules with different final columns.

---

## 3. Mandatory architecture-first change

Do **not** implement this by changing P1.35 alone.

REV11 Section 13.5A currently freezes immediate-wrap behavior, and the implementation plan is subordinate to the architecture. The developer shall therefore:

1. create the next architecture revision from REV11;
2. change the normative Section 13.5A text first;
3. update architecture acceptance tests/invariants that refer to wrap and scroll behavior;
4. only then create/update the corresponding implementation-plan revision;
5. make code changes only against the revised architecture contract.

The old rule:

> printable bytes draw at the current cell then advance one column; writing past the final column wraps to column 0 of the next row

shall no longer be normative.

The replacement semantics shall be equivalent to Sections 4-11 of this change request.

---

## 4. New console state

Add one kernel-global terminal state bit:

```text
wrap_pending : boolean
```

It may be stored as a dedicated byte or packed into an existing console/cursor flags byte. The choice is an implementation detail, but its semantics are normative.

The console state relevant to this change is conceptually:

```text
tty_mode       = 32 or 64
cursor_row     = 0..23
cursor_col     = 0..(tty_mode-1)
wrap_pending   = 0 or 1
cursor_shape   = off / underline / block
cursor_phase   = blink phase
cursor_drawn   = whether the XOR cursor is currently present in bitmap memory
```

`wrap_pending` is **not** part of the public ABI and must not require a new syscall or IOCTL.

### 4.1 Required invariants

At every externally observable boundary:

```text
0 <= cursor_row <= 23
0 <= cursor_col <= last_col
last_col = 63 when tty_mode == 64
last_col = 31 when tty_mode == 32
```

A logical `cursor_col == 64` in tty64, `cursor_col == 32` in tty32, or `cursor_row == 24` in either mode must never exist, even temporarily as persistent console state.

If `wrap_pending == 1`, then all of the following must be true:

```text
cursor_col == last_col
cursor_row is still the row containing the last character written
no automatic line advance has yet occurred for that last character
```

`wrap_pending == 1` does not itself mean that the bitmap contains the cursor XOR. Cursor visibility remains controlled independently by shape, blink phase, ownership rules, and `cursor_drawn`.

---

## 5. Printable-character algorithm

All printable bytes shall use one shared logical-output path for both terminal modes. Mode-specific code should supply only rendering width/font details and `last_col`.

Normative pseudocode:

```text
function console_put_printable(ch):
    cursor_screen_begin()          // remove XOR cursor if currently drawn

    if wrap_pending:
        wrap_pending = false
        line_advance_for_wrap()    // may scroll exactly once

    draw_glyph_at(cursor_row, cursor_col, ch)

    if cursor_col < last_col:
        cursor_col += 1
        wrap_pending = false
    else:
        // Character was written in the real final cell.
        // Cursor stays on that cell. No wrap and no scroll yet.
        cursor_col = last_col
        wrap_pending = true

    cursor_screen_end()            // reconcile latest position/shape/blink phase
```

Where:

```text
function line_advance_for_wrap():
    if cursor_row < 23:
        cursor_row += 1
        cursor_col = 0
    else:
        scroll_one_text_row()
        cursor_row = 23
        cursor_col = 0
```

`scroll_one_text_row()` must obey the existing tty-specific screen-scroll contract and must not perform a second cursor remove/redraw that corrupts the XOR state. The cursor-screen bracketing must remain properly nested or centralized so the cursor is XORed at most once on entry and once on exit.

### 5.1 Bottom-right example

Initial state:

```text
cursor_row   = 23
cursor_col   = 63
wrap_pending = 0
```

Write printable `X`:

```text
X is drawn at (23,63)
cursor_row   = 23
cursor_col   = 63
wrap_pending = 1
NO SCROLL
```

The cursor may blink on top of `X` at `(23,63)`.

Then write printable `Y`:

```text
pending wrap is resolved first
screen scrolls upward exactly one text row
cursor becomes (23,0)
Y is drawn at (23,0)
cursor advances to (23,1)
wrap_pending = 0
```

There must be exactly one scroll, not zero and not two.

---

## 6. Control-character behavior while wrap is pending

A pending printable wrap must never hijack an explicit control operation. Before executing a cursor-moving/control operation, cancel the pending printable wrap and then execute that control according to its own defined semantics.

### 6.1 CR, 0x0D

```text
wrap_pending = false
cursor_col = 0
cursor_row unchanged
```

At bottom-right pending state, `CR` therefore moves from `(23,63)` to `(23,0)` with **no scroll**.

### 6.2 LF, 0x0A

Preserve the existing ZX-UX rule that LF also sets column 0.

```text
wrap_pending = false
if cursor_row < 23:
    cursor_row += 1
    cursor_col = 0
else:
    scroll_one_text_row()
    cursor_row = 23
    cursor_col = 0
```

At bottom-right pending state, LF explicitly requests a new line and therefore causes exactly one scroll.

### 6.3 BS, 0x08

```text
wrap_pending = false
if cursor_col > 0:
    cursor_col -= 1
else:
    cursor_col = 0
```

BS does not delete and never wraps to the previous row. From pending `(23,63)`, BS produces `(23,62)` in tty64.

### 6.4 TAB, 0x09

Cancel pending state, then apply the existing logical multiple-of-8 rule.

Conceptually:

```text
wrap_pending = false
next = (cursor_col + 8) & ~7

if next <= last_col:
    cursor_col = next
else:
    if cursor_row < 23:
        cursor_row += 1
        cursor_col = 0
    else:
        scroll_one_text_row()
        cursor_row = 23
        cursor_col = 0
```

TAB uses **logical terminal columns**, not physical Spectrum bitmap bytes.

### 6.5 FF, 0x0C

```text
wrap_pending = false
clear_text_display()
cursor_row = 0
cursor_col = 0
```

### 6.6 Other explicit positioning/reset operations

The following must clear `wrap_pending` when they successfully change/reset logical terminal position or layout:

- `SYS_CON_SETPOS`;
- console clear/home;
- terminal mode switch between tty32 and tty64;
- any internal reset that reinitializes logical console coordinates.

A failed operation must remain atomic. For example, an invalid `SYS_CON_SETPOS` must leave `cursor_row`, `cursor_col`, `wrap_pending`, cursor XOR state, and screen bytes unchanged.

Operations that do not alter logical cursor position, such as `GETPOS`, cursor blink timing, or changing cursor shape, must not clear `wrap_pending` merely because they were called.

Bytes outside the printable range and the defined CR/LF/BS/TAB/FF control set retain the existing unsupported-control policy. If such a byte is ignored, it must not clear or resolve `wrap_pending`. Any future control definition that moves or resets the logical cursor must explicitly clear pending state before applying that movement.

---

## 7. GETPOS and SETPOS semantics

### 7.1 `SYS_CON_GETPOS`

`GETPOS` continues to return only the real logical cell coordinate.

If the terminal is in pending-wrap state at the bottom-right corner:

```text
H = 23
L = 63       // tty64
```

or:

```text
H = 23
L = 31       // tty32
```

There is no ABI-visible representation of a phantom next column, and the hidden `wrap_pending` bit is not returned.

### 7.2 `SYS_CON_SETPOS`

Validation occurs before mutation.

On a valid coordinate:

```text
remove visible XOR cursor if required
cursor_row = H
cursor_col = L
wrap_pending = false
redraw/reconcile cursor if required
```

On an invalid coordinate, return the existing error and preserve all prior console/cursor state byte-for-byte.

Setting the cursor explicitly to `(23,63)` does **not** itself set `wrap_pending`. A subsequent printable byte first writes into that cell and only then sets `wrap_pending`.

---

## 8. Cursor behavior at the final cell

The bottom-right cell is a normal cursor location.

After a printable byte is written at `(23,63)` in tty64 or `(23,31)` in tty32:

- the logical cursor remains on that cell;
- `wrap_pending` becomes 1;
- if cursor shape and blink phase call for a visible cursor, the cursor is XOR-rendered on that same cell;
- the character beneath it remains recoverable exactly by XOR removal;
- no attribute byte is changed by the cursor;
- no scrolling occurs until separately required.

For tty64:

- block cursor XORs the selected four-bit nibble on all eight scanlines;
- underline cursor XORs the selected four-bit nibble on **scanline 7 only**;
- the neighboring nibble is preserved on every scanline;
- the attribute byte is never changed by cursor draw/hide.

This wording intentionally removes any ambiguity in the existing phrase "bottom 4-pixel row": underline means one horizontal scanline four pixels wide, not four scanlines high.

The pending-wrap bit and the cursor blink state are independent. A blink transition must not resolve a pending wrap.

---

## 9. Cursor/screen critical-section discipline

The existing console-managed rendering rule remains mandatory.

Use one centralized bracketing discipline equivalent to:

```text
function cursor_screen_begin():
    prevent_cooperative_switch_for_screen_mutation()
    if cursor_drawn:
        xor_cursor_at(cursor_row, cursor_col, cursor_shape)
        cursor_drawn = false

function cursor_screen_end():
    reconcile_cursor_with_current_position_shape_and_blink_phase()
    end_screen_mutation_no_switch_region()
```

During a pending-wrap printable at `(23,63)`, the next printable operation must therefore perform this order:

```text
1. remove visible XOR cursor from (23,63)
2. clear wrap_pending
3. scroll exactly one row
4. set logical position to (23,0)
5. draw the new printable character
6. advance/update pending state normally
7. redraw cursor at its new logical position if currently visible
```

The old cursor must never be copied upward as a real bitmap artifact during scroll.

IM2 may update cursor timing state or set a deferred service flag, but it must never resolve `wrap_pending`, scroll, draw a glyph, or XOR the cursor bitmap.

---

## 10. `SYS_CON_WRITE` and multi-byte writes

`SYS_CON_WRITE` must call/use exactly the same per-byte state machine as `SYS_CON_PUTCHAR`.

Do not add special end-of-buffer wrapping.

Required behavior:

- if a write buffer ends immediately after filling the final column, leave `wrap_pending=1` and do not wrap merely because the syscall is returning;
- if the next `SYS_CON_WRITE` or `SYS_CON_PUTCHAR` begins with a printable byte, resolve the pending wrap before drawing it;
- if the next byte is CR/LF/BS/TAB/FF, cancel pending state and apply that control's own semantics;
- splitting the same byte stream across multiple syscalls must produce the same final screen and console state as sending it in one syscall.

This call-boundary independence is mandatory.

---

## 11. tty32 parity

The exact same state machine applies to tty32 with:

```text
last_col = 31
```

Do not create a tty64-only special case.

Required tty32 corner behavior:

```text
write printable at (23,31)
=> stay at (23,31), wrap_pending=1, no scroll

next printable
=> scroll exactly once, draw at (23,0), continue normally
```

Mode switching clears/reinitializes the logical console under the existing architecture rule and must also clear `wrap_pending`.

---

## 12. Required document changes

The developer shall update all duplicated/frozen statements so there is one consistent semantic contract.

### 12.1 Architecture document

At minimum inspect and update:

- Section 13.4, if needed to state that the final logical cell remains a valid cursor position during pending wrap;
- Section 13.4A, to ensure cursor removal/redraw wording covers deferred-wrap scroll;
- Section 13.5A, replacing immediate wrap with the normative pending-wrap state machine;
- console acceptance tests that currently say wrap/scroll must match Section 13.5A;
- any invariant/summary/ledger entry that assumes "draw then advance past final column".

The architecture must explicitly state that no column outside 0..63/0..31 and no row outside 0..23 exists as logical cursor state.

### 12.2 Implementation-plan document

At minimum inspect and update:

- P1.20 `tty32 fallback core`;
- P1.23 `tty64 scroll`;
- P1.24 `Software cursor core`;
- P1.32 `Cursor/direct-screen reversibility correction matrix` as needed for bottom-right/pending-wrap coverage;
- P1.35 `SYS_CON_PUTCHAR exact ABI`;
- P1.36 `SYS_CON_WRITE`;
- P1.37 clear/home behavior;
- P1.38 `SYS_CON_GETPOS`;
- P1.39 `SYS_CON_SETPOS`;
- P1.41 Phase-1 acceptance gate;
- all later console/terminal acceptance matrices that repeat immediate-wrap assumptions.

P1.35 must no longer say that a printable byte always "draws then advances" in a way that implies a logical position beyond the last column.

---

## 13. Required implementation structure

A single shared logical state machine is strongly preferred. Do not independently reproduce wrap logic in tty32, tty64, PUTCHAR, WRITE, shell, or `vi`.

Recommended internal helpers:

```text
console_put_byte(byte)
console_put_printable(byte)
console_resolve_pending_wrap()
console_line_advance()
console_tab()
console_clear_and_home()
console_setpos(row, col)
cursor_screen_begin()
cursor_screen_end()
```

Suggested dispatch:

```text
function console_put_byte(ch):
    if 0x20 <= ch <= 0x7F:
        console_put_printable(ch)
        return

    switch ch:
        case 0x08: console_backspace(); return
        case 0x09: console_tab();       return
        case 0x0A: console_linefeed();  return
        case 0x0C: console_formfeed();  return
        case 0x0D: console_carriage_return(); return
        default:   apply_existing_unsupported_control_policy()
```

Each cursor-moving control helper begins by clearing `wrap_pending` after any necessary argument validation and while under the normal cursor/screen mutation bracket.

Do not let shell or `vi` maintain their own competing wrap flag. This is terminal state and belongs to the kernel console subsystem.

---

## 14. Required deterministic tests

Add byte-level tests for both tty64 and tty32. Screenshot-only evidence is insufficient.

### 14.1 tty64 right-edge tests

1. Start `(0,62)`, write `A`: `A` at col62, cursor `(0,63)`, pending=0.
2. Write `B`: `B` at col63, cursor `(0,63)`, pending=1, no wrap.
3. Write `C`: wrap before `C`; `C` at `(1,0)`, final cursor `(1,1)`, pending=0.
4. Verify neighboring nibble and attributes remain exact.

### 14.2 Exact 64-character line

From `(0,0)`, write exactly 64 printable characters.

Expected after byte 64:

```text
cursor = (0,63)
wrap_pending = 1
row 1 unchanged
no scroll
```

Byte 65 must appear at `(1,0)` and leave cursor `(1,1)`.

### 14.3 Exact full-screen fill

Clear/home, then write exactly `64 * 24 = 1536` printable bytes.

Expected after byte 1536:

```text
all 1536 cells contain the intended characters
cursor = (23,63)
wrap_pending = 1
scroll_count = 0
```

Then write byte 1537.

Expected:

```text
scroll_count increases by exactly 1
old rows 1..23 become rows 0..22 exactly
new character is drawn at (23,0)
cursor becomes (23,1)
wrap_pending = 0
```

### 14.4 Bottom-right control tests

Create pending state at `(23,63)`, then separately test:

- CR => `(23,0)`, no scroll, pending=0;
- LF => one scroll, `(23,0)`, pending=0;
- BS => `(23,62)`, no scroll, pending=0;
- TAB => one logical wrap/scroll to `(23,0)`, pending=0;
- FF => clear screen, `(0,0)`, pending=0.

### 14.5 GETPOS/SETPOS tests

- `GETPOS` during pending bottom-right returns exactly `(23,63)` in tty64.
- valid `SETPOS` clears pending.
- `SETPOS(23,63)` leaves pending=0 until a printable byte is actually written there.
- invalid row 24 or col64 fails atomically and preserves the prior pending state and bitmap.

Repeat with col31/col32 boundaries in tty32.

### 14.6 Split-write equivalence

Feed one byte stream in these forms:

```text
one SYS_CON_WRITE
multiple SYS_CON_WRITE chunks
mixed SYS_CON_WRITE + SYS_CON_PUTCHAR calls
```

Choose chunk boundaries exactly before and after final-column characters.

Final bitmap, attributes, `(row,col)`, and `wrap_pending` must be identical for all forms.

### 14.7 Cursor reversibility at bottom-right

With a printable character at `(23,63)` and pending=1:

- show block cursor;
- hide it;
- show/hide repeatedly;
- repeat with underline;
- verify the hidden bitmap is byte-identical to the underlying glyph every time;
- verify attributes are unchanged;
- then write the next printable and prove the scroll does not copy cursor XOR pixels into row 22.

### 14.8 Deferred blink-service test

While pending at bottom-right, allow cursor blink phase to change for multiple 25-frame intervals without console output.

Expected:

- cursor may appear/disappear according to blink phase;
- `(row,col)` stays `(23,63)`;
- `wrap_pending` stays 1;
- no scroll occurs;
- ISR performs no bitmap write.

### 14.9 tty32 full-screen parity

Repeat the corresponding full-screen test with exactly `32 * 24 = 768` printable bytes.

Byte 768 leaves `(23,31)`, pending=1, no scroll. Byte 769 causes exactly one scroll, writes at `(23,0)`, and advances to `(23,1)`.

---

## 15. Negative tests / forbidden implementations

The implementation must fail certification if any of the following occurs:

- a printable character at the final column immediately wraps before another byte requires space;
- writing the bottom-right cell immediately scrolls;
- persistent cursor state ever becomes col64, col32 in tty32, or row24;
- the next printable while pending overwrites the final cell instead of wrapping first;
- pending state survives CR/LF/BS/TAB/FF, successful SETPOS, clear/home, or terminal mode reset;
- GETPOS exposes a phantom coordinate or changes pending state;
- invalid SETPOS clears pending or changes the display;
- syscall return from a buffer ending at the final cell forces a wrap;
- tty32 and tty64 use different logical wrap rules;
- shell or `vi` carries a second private pending-wrap state;
- cursor blink resolves pending wrap;
- IM2 modifies bitmap, scroll state, row/column, or `wrap_pending`;
- scroll copies an XOR-visible cursor into retained screen data;
- cursor block/underline changes attributes or the adjacent tty64 nibble;
- more than one scroll occurs when a pending bottom-right wrap is resolved;
- the 1536th tty64 printable causes any scroll before byte 1537 arrives.

---

## 16. Acceptance criteria

This change is complete only when all of the following are true:

1. The architecture and implementation plan specify the same deferred-wrap semantics.
2. `tty64` cursor coordinates are always row 0..23 and col 0..63.
3. `tty32` cursor coordinates are always row 0..23 and col 0..31.
4. A printable in the final column leaves the cursor there and sets hidden pending state.
5. Filling `(23,63)` does not itself scroll.
6. The next printable after pending bottom-right causes exactly one scroll before being drawn.
7. Explicit controls cancel pending state and perform their own documented behavior.
8. `GETPOS` reports only real coordinates; `SETPOS` validly clears pending and invalid SETPOS is atomic.
9. PUTCHAR and WRITE share one byte-state machine and are independent of syscall chunking.
10. tty32 and tty64 have identical logical semantics except for `last_col` and rendering width.
11. Cursor XOR remains exactly reversible at the final cell and through the subsequent scroll.
12. IM2 remains timing-only with respect to cursor/screen output.
13. The exact 64x24 and 32x24 fill tests pass with zero premature scrolls.
14. All existing console/cursor tests remain green after their expected results are updated to the new architecture.
15. The project quality gate completes with three successive zero-defect scans of the final changed artifacts.

---

## 17. Developer completion note

When reporting completion, explicitly state:

```text
Architecture immediate-wrap rule removed: YES/NO
Implementation plan synchronized: YES/NO
wrap_pending kernel-global state implemented: YES/NO
No phantom cursor column/row state: PASS/FAIL
tty64 1536-byte no-premature-scroll test: PASS/FAIL
tty64 byte-1537 exactly-one-scroll test: PASS/FAIL
tty32 768-byte no-premature-scroll test: PASS/FAIL
tty32 byte-769 exactly-one-scroll test: PASS/FAIL
Bottom-right CR/LF/BS/TAB/FF matrix: PASS/FAIL
GETPOS/SETPOS pending-wrap matrix: PASS/FAIL
Split-write equivalence: PASS/FAIL
Cursor XOR bottom-right/scroll reversibility: PASS/FAIL
IM2 performs no bitmap/wrap mutation: PASS/FAIL
Three successive zero-defect final scans: PASS/FAIL
```

A `NO` or `FAIL` on any line blocks check-in.
