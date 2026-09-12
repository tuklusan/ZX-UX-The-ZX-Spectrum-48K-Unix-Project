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

**Status:** Proposed architecture-first version-1 console correction; modes `tty64` 64x24 and `tty32` 32x24; no new syscall/IOCTL or public coordinate-range change. This revision closes the pre-execution change-control gaps for architecture identity, P1.13/P1.30/P1.31/P1.34 ownership, kernel-stack regression, exact blink coalescing, exact screen-mutation nesting, final font identity, and deterministic acceptance.

---

## 1. Normative goals

Version 1 shall:

1. use the exact canonical Tasword-derived F4X8 bytes defined in Section 2 for final `tty64` output;
2. keep all persistent cursor coordinates inside real cells;
3. use deferred right-margin wrap so filling the last cell does not itself wrap or scroll; and
4. provide a 4x8 VT-style blinking software cursor clocked from the Spectrum frame interrupt but drawn only at safe non-ISR kernel points.

Tasword supplies the font/rendering model; deferred wrap is ZX-UX terminal behavior, not Tasword behavior.

This change request changes previously certified/admitted contracts. It is therefore architecture change control, not an isolated console patch. No implementation belonging to this CR may be admitted until the authorized architecture/implementation-plan rebaseline has been activated, E0 and Phase 0 have been recertified, and admitted P1.01-P1.12 have been revalidated against that rebaseline.

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

H04 pinned the read-only SDK source at commit `1bebc6288a1cdfa1bdfb5a6694e1986b6c3d7ee0`, with `compiler/assets` tree `979039b5c636f0578f8bccd19ae49a669a5b7e0e`. The canonical repository already preserves the reference bytes as both `v1/assets/font4x8-tasword.bin` and `v1/assets/font4x8-zxux.bin`; at the pre-rebaseline checkpoint both paths have Git blob `6efc46eb1d7e940e027097ad76e27ac719aeb59f`. The then-current `v1/assets/font4x8.bin` has different Git blob `8e5eceb97d23662b9e7711fdf136f69c0389f707` and remains a non-final development/Phase-0 fixture until its revised owning gate deliberately promotes the canonical bytes. No checkpoint identity of that non-final fixture may override the final byte requirement above.

F4X8 remains unchanged: `F4X8`, version 1, first code `0x20`, 96 glyphs, flags 0, then 384 packed bytes. Each four-byte glyph encodes eight 4-bit rows; high nibble is the earlier row, low nibble the following row, bit3 is leftmost and bit0 rightmost. Codes are `0x20..0x7F`.

This freezes release identity, not target ABI. The Z80 loader keeps structural/transport checks only. SHA-256 computation and comparison remain host-side release/certification responsibilities; no target SHA-256 implementation, target digest table, or target syscall is introduced by this CR. Release certification proves the exact final asset hash and that RAW/PACKED M48O decode yields the same 392 logical bytes.

A generator is allowed only if byte-identical. Explicitly permitted development/Phase-0 fixtures are non-final and cannot pass P12.05 or later final gates unless canonical. Final certification is local; SDK network access is unnecessary.

64x24 geometry, nibble mapping/preservation, and shared 8x8 attributes remain unchanged.

---

## 3. Console and cursor state

Conceptual private kernel state is:

```text
tty_mode                 32 or 64
cursor_row               0..23
cursor_col               0..last_col
wrap_pending             boolean
cursor_shape             off / underline / block
cursor_phase             logical blink phase: off / on
cursor_drawn             whether cursor XOR is physically present
cursor_blink_divider     accepted-frame count 0..24
cursor_service_parity    boolean; parity of unserviced 25-frame transitions
screen_mutation_depth    balanced private nesting depth, zero when idle
```

`last_col=63` in tty64 and `31` in tty32. No persistent col64, col32 in tty32, or row24 is permitted. `wrap_pending=1` implies `cursor_col==last_col`; the row remains the row containing the last printable written there.

`cursor_phase` and `cursor_drawn` are distinct. Cold console init starts phase `on`, divider 0, service parity 0, and mutation depth 0. Temporary cursor removal, clear, positioning, mode/shape change, graphics, or UDG mutation shall not change phase. Shape `off` suppresses drawing without stopping the blink clock or resetting phase.

The blink request is not a set-only boolean event. Each accepted PAL frame advances `cursor_blink_divider`; on the 25th accepted frame the divider becomes 0 and IM2 toggles `cursor_service_parity`. Therefore an even number of unserviced 25-frame intervals coalesces to no net phase change and an odd number coalesces to exactly one phase toggle. No deferred catch-up flashing is performed. This parity rule is the exact accumulation/coalescing contract and cannot overflow merely because user code remains outside the kernel for a long time.

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

The final-cell write stays there with no scroll. The next pending bottom-right printable scrolls exactly once, draws at `(23,0)`, then advances; tty32 is identical with `last_col=31`.

Scrolling, clearing, glyph drawing, direct OS graphics/UDG mutation, terminal mode change, and every other kernel-owned screen-content mutation use the one exact nested mutation policy in Section 6. Cursor XOR is performed only by the outer bracket or the defined direct deferred-service reconciliation path. A scroll called from `put_printable` is therefore nested under the existing outer mutation and cannot independently hide/show the cursor.

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

## 6. Cursor rendering, exact mutation nesting, and timing

For tty64, block cursor XORs the selected 4-pixel nibble on all eight scanlines; underline XORs that nibble on scanline 7 only; off draws nothing. The adjacent nibble and attribute byte are never changed. tty32 uses the same logical cursor model at 8-pixel width.

### 6.1 Exact screen-mutation nesting policy

All kernel-owned screen-content mutations use one balanced nesting counter. There is no alternative "centralized or safely nested" implementation choice. Deferred cursor-only reconciliation is not a content mutation and uses the separate direct-service rule below.

```text
screen_begin():
    if screen_mutation_depth == 0:
        enter cooperative-switch exclusion
        screen_mutation_depth = 1
        if cursor_drawn:
            XOR cursor away
            cursor_drawn = 0
        do not change cursor_phase
        return

    checked_increment(screen_mutation_depth)
    return

screen_end():
    require screen_mutation_depth > 0
    screen_mutation_depth -= 1
    if screen_mutation_depth != 0:
        return

    with cooperative-switch exclusion still held:
        consume cursor_service_parity atomically
        if consumed parity == 1:
            toggle cursor_phase exactly once
        reconcile cursor_drawn with cursor_shape + cursor_phase
    leave cooperative-switch exclusion
```

Only the outermost `screen_begin` may hide a visible cursor and only the matching outermost `screen_end` may service deferred blink parity, redraw/reconcile the cursor, and release cooperative-switch exclusion. Nested calls perform no cursor XOR and do not independently enter/leave the exclusion. Underflow, unbalanced exit, or silent depth wrap is a defect and must fail deterministic tests; a checked implementation may panic/assert rather than continue with corrupt nesting.

Direct deferred cursor service outside a screen-content mutation is the sole non-nesting path: it enters the same cooperative-switch exclusion, atomically consumes parity, reconciles the cursor, and leaves the exclusion without changing `screen_mutation_depth`.

### 6.2 Exact IM2 producer and non-ISR consumer contract

The PAL baseline target is one logical blink transition every 25 accepted 50-Hz frames. IM2 performs only the bounded producer work:

1. advance `cursor_blink_divider`;
2. on the 25th accepted frame reset it to 0 and XOR/toggle `cursor_service_parity`;
3. perform no cursor bitmap XOR, glyph draw, scroll, coordinate change, `wrap_pending` change, screen-mutation-depth change, or cooperative context switch.

The safe consumer atomically fetches-and-clears `cursor_service_parity`. If the consumed value is 1 it toggles `cursor_phase` exactly once, then reconciles physical XOR state. The fetch-and-clear must be atomic with respect to IM2, for example by a brief maskable-interrupt exclusion. An interrupt that posts after the atomic consume belongs to the next service opportunity and cannot be erased by the completed consume.

Shape `off` does not stop this consumer: logical phase still follows consumed parity while `cursor_drawn` remains 0. Re-enabling underline/block reconciles against the then-current logical phase.

### 6.3 Mandatory safe service points

A pending parity request is serviced at the first safe non-ISR point at which `screen_mutation_depth==0` and the cursor bitmap may be touched. At minimum the revised architecture/plan must bind this rule to:

- outermost `screen_end`;
- kernel re-entry after the kernel stack/exclusion preconditions needed by cursor service are established, before ordinary return-to-user work can bypass a due request;
- the idle path immediately before HALT when a request is already pending and immediately after HALT/interrupt wake before ordinary scheduler/input work resumes;
- the blocked console-input/tty-owner path used by P1.31/P1.34, after each wake/re-entry and before key delivery, re-block/yield, or return.

A screen mutation may delay service only until its outermost safe end. Cooperative v1 does not promise bitmap blinking while arbitrary non-yielding user code never re-enters the kernel. When such code eventually re-enters, parity coalescing gives the exact logical phase that would result from all elapsed 25-frame intervals, without replaying historical flashes.

### 6.4 P1.13 and P1.30 ownership constraints

The revised P1.13 contract owns the IM2-side divider/parity producer state and the race-safe producer/consumer handoff contract. P1.13 must prove 25-frame cadence, odd/even coalescing, boundary-safe atomic consumption, and zero IM2 bitmap/wrap/coordinate mutation without requiring the later full cursor renderer; later console/cursor steps bind the consumer to the physical XOR implementation.

P1.30 must be synchronized because the added divider/parity producer executes inside both exact ISR preservation paths. Its instruction-boundary matrix must prove the CR-1 timing work preserves the `altreg_busy` fast/safe-path contract, does not create persistent alternate-bank state, and retains exact measured frame cost and maximum-cycle cost for both revised ISR paths. Any cycle-count change caused by this CR is deliberate rebaseline evidence, not a silent regression.

### 6.5 P1.28/P1.33 kernel-stack constraints

P1.28 and P1.33 must include the deepest CR-1 path in high-water measurement: outer/nested screen mutation, cursor hide/reconcile/service helper calls, controls that scroll or clear, and an interrupt at every interruptible point using whichever P1.30 preservation path consumes more stack. Production-linked worst-case consumption must remain <=448 bytes with the full >=64-byte untouched architectural margin and the `FB00-FB0F` guard intact. CR-1 may not borrow the guard or silently consume the reserved margin.

---

## 7. Mandatory document synchronization and architecture identity

Create the next architecture revision first, then its matching implementation-plan revision, then code. CR-1 may participate in the owner-approved combined rebaseline with H06 and CR-2, but each obligation retains separate acceptance and closure responsibility.

Architecture update set: at minimum §§4.3A, 5.1, 5.5, 6.7, 13.1, 13.4, 13.4A, 13.5A, 28.2, 35.1, 41, 44, 47, 58 plus duplicated font/wrap/scroll/cursor/ISR/stack invariants and acceptance text.

Plan update set: fixed-contract summary; E0.01/E0.02 architecture identity; P0.10; P1.13; P1.20-P1.24; P1.28; P1.30-P1.39; P1.41; P12.05/.07/.09/.25/.26/.30; and later duplicate matrices. P0.10 distinguishes non-final fixtures; P1.13 owns the producer/handoff contract; P1.21 stays the target structural validator; P12.05 is the decisive exact-byte/digest gate. The combined rebaseline must also regenerate the Section-41 replay ledger and the exact P12.26 literal-row count after CR-1, CR-2, and H06 synchronization; the REV11 count of 228 rows is historical to that baseline and must not be copied forward if the revised mandatory matrix contains a different number of stable rows.

Pending wrap belongs only to the kernel console. Do not add target font SHA-256 absent a later independent architecture requirement.

### 7.1 E0 architecture-identity/path/hash rebaseline

Replacing Revision 11 changes the canonical architecture identity and invalidates the old path/hash as the authority for subsequent implementation, while preserving old tags and already-recorded certification evidence as immutable historical evidence.

The combined activation transaction must freeze the exact new architecture path and SHA-256 and update every consumer of the old identity together. This includes at minimum:

- the implementation-plan header/baseline declaration and every E0.01/E0.02 path/hash statement;
- `tools/scripts/verify-environment.py` architecture path and digest constants;
- any test-driver, certification-record validator, CI/workflow, policy text, or duplicate matrix that consumes or asserts the canonical architecture path/hash;
- all new E0/Phase-0/revalidation evidence emitted after activation.

`main` must not be left knowingly half-switched with a new architecture file but old verifier hash/path, or vice versa. The activation transaction must have deterministic positive verification of the new identity and a wrong-path/wrong-hash negative test.

After activation, rerun E0 and Phase 0 under the new architecture identity and revalidate admitted P1.01-P1.12 before P1.13 resumes. Existing R&R tags and old evidence remain unchanged and continue to identify the bytes they originally certified; they are not rewritten to pretend they certified the new architecture.

The unadmitted P1.13 work commit `3245d489ad9b26c3ea55bcf0677374d2cfa5b53d` remains a reconciliation input, not disposable work. After rebaseline/revalidation, resume from that checkpoint, preserve useful repairs, and instrument the retained `sys-ticks-snapshot-is-coherent-and-four-bytes` failure against the revised P1.13 cursor-service/IM2 contract before admitting P1.13.

---

## 8. Deterministic certification matrix

Certification is byte/state based; screenshots are supplemental. The revised architecture and implementation plan shall carry this matrix to the owning steps rather than relying on prose-only closure.

| Contract | Deterministic proof | Owning/replay gates |
| --- | --- | --- |
| Architecture identity | Exact new path/SHA-256 positive check; wrong path/hash rejected; no old/new mixed consumer state | E0.01, E0.02, combined rebaseline activation |
| Final font identity | `font4x8.bin` exact 392 bytes, host SHA-256 `90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`, F4X8 fields/packing, RAW/PACKED logical equality; non-final fixture rejected | P0.10 fixture distinction, P1.21 structural validation, P12.05 final identity, P12.07 tape manifest, P12.09 boot load, P12.26 matrix, P12.30 definitive replay |
| tty64 nibble rendering | All 96 codes in even/odd columns; selected nibble exact; nonzero neighbor sentinel and attribute survive | P1.21-P1.24, P1.41, P12.26, P12.30 |
| Deferred right edge | tty64 col62: `A` -> col63 pending0; `B` -> col63 pending1 no wrap; `C` wraps first and draws `(1,0)`; tty32 col30/31 equivalent | P1.20, P1.35/P1.36, P1.41, P12.26, P12.30 |
| Full-screen boundary | 1536/1537 tty64 and 768/769 tty32 exact state; first count ends bottom-right pending1 with no scroll; next byte scrolls once | P1.20, P1.35/P1.36, P1.41, P12.26, P12.30 |
| Pending controls | CR/LF/BS/TAB/FF from bottom-right pending state in both modes match Section 5 exactly | P1.20, P1.35/P1.37, P1.41, P12.26 |
| GETPOS/SETPOS | GETPOS exposes real final cell only; valid SETPOS clears pending; SETPOS to final cell leaves pending0; invalid row24/col64/tty32-col32 is atomic | P1.38/P1.39, P1.41, P12.26 |
| Chunking | One WRITE, split WRITEs, mixed WRITE/PUTCHAR give byte/state-identical output across right-edge and scroll boundaries | P1.35/P1.36, P1.41, P12.26 |
| Nested mutation | Outer begin + nested glyph/scroll/clear/graphics paths hide cursor once, nested ends never XOR/release, outer end reconciles once; underflow/unbalanced nesting rejected | P1.32/P1.35-P1.39, P1.41, P12.26 |
| Cursor reversibility | Block/underline show/hide at pending bottom-right is byte-exact; neighbor nibble/attributes unchanged; scroll never copies visible XOR | P1.32, P1.41, P12.26, P12.30 |
| Blink cadence/parity | Divider transition only each 25 accepted frames; delays of 1/2/3/4 intervals produce parity 1/0/1/0 and matching final phase without catch-up flashes | P1.13 producer tests, P1.32 consumer tests, P1.41, P12.26 |
| Handoff race | Inject interrupt immediately before/inside/after atomic consume boundary; no posted parity transition is erased or double-consumed | P1.13, P1.30, P1.41, P12.26 |
| ISR purity/timing | IM2 never edits bitmap/row/col/wrap/depth; both `altreg_busy` preservation paths include timing work and retain exact measured frame/max-cycle evidence | P1.13, P1.30, P1.41, P12.26 |
| Idle/input service | Due request before idle, on HALT wake, while GETKEY blocks, and before key return is serviced at first safe point; row/col/wrap unchanged | P1.31/P1.34 plus P1.32 cursor consumer, P1.41, P12.26 |
| Shape/phase independence | Shape off suppresses XOR while phase continues; mutation/mode/shape changes preserve phase; re-enable reconciles current phase | P1.32 and terminal-mode owner, P1.41, P12.26, P12.30 |
| Kernel stack | Deepest nested console/cursor/service + worst ISR preservation path keeps measured stack <=448 bytes, >=64-byte margin, guard intact; deliberate overflow/guard damage fails | P1.28, P1.33, P1.41, P12.25, P12.26 |
| Cooperative limitation | Non-yielding user code gets no async bitmap promise; first later kernel re-entry services parity to exact net phase | P1.13/P1.31/P1.34, P1.41, P12.26 |
| Regression | Existing console/cursor/IM2/stack tests remain green except deliberately revised expected results | P1.41, P12.26, P12.30 |

Additional final-font tests shall render all 96 codes in even and odd tty64 columns; each selected nibble shall equal the canonical row while a nonzero neighbor sentinel survives. A one-bit structurally valid mutation may be a permitted fixture but must fail P12.05 and later final gates.

Scroll proof uses deterministic test instrumentation/sentinels, not a production scroll counter. Cursor-hidden raw bitmap comparison is the PASS oracle for direct-screen reversibility. Screenshots may supplement but never replace register/RAM/byte assertions.

---

## 9. Forbidden implementations

Certification fails for any of the following:

- wrong final font/hash or transport bytes, a noncanonical fixture passing a final gate, or target SHA-256 added only to prove release identity;
- immediate final-column wrap/scroll, out-of-range persistent coordinates, wrong pending clearing, non-atomic invalid SETPOS, syscall-return wrap, tty32/tty64 semantic divergence, or private shell/`vi` wrap state;
- a set-only blink-due flag that turns two or any even number of delayed 25-frame intervals into one phase toggle, an unbounded catch-up-flash loop, or any other accumulation rule that differs from Section 3 parity;
- IM2 bitmap/cursor XOR, coordinate/wrap/depth edits, cursor artifacts, attribute/neighbor corruption, or bottom-right pending resolution scrolling other than once;
- nested screen mutation independently hiding/showing the cursor, independently releasing cooperative-switch exclusion, silently underflowing/wrapping the nesting depth, or reconciling before the outermost mutation ends;
- consuming/clearing parity in a way that can erase a producer event posted after the service decision;
- due service skipped despite a safe kernel re-entry, idle, input-wait, or outermost mutation-end opportunity;
- false async-blink claims during arbitrary non-yielding user code;
- CR-1 ISR work that violates P1.30 alternate-register preservation or leaves cycle evidence stale;
- CR-1 stack growth that violates P1.28/P1.33 guard/margin limits;
- partial architecture activation in which canonical architecture bytes, path/hash consumers, plan identity, verifier metadata, or new evidence disagree.

---

## 10. Acceptance and completion gate

CR-1 completion requires architecture, plan, code, tests, release assets, E0 identity, and replay evidence to agree.

Required PASS conditions are: controlled architecture path/hash activation; E0 and Phase-0 recertification; P1.01-P1.12 revalidation; canonical final font bytes/hash and production-tape logical equality; no target font SHA-256 requirement; all-96-glyph even/odd render matrix; fixture rejection at final gate; no phantom coordinates; tty64 1536/1537; tty32 768/769; pending-control matrix; GETPOS/SETPOS matrix; chunking equivalence; exact nested mutation discipline; cursor XOR/scroll reversibility; logical phase independent of physical XOR; exact 25-frame divider/parity coalescing; race-safe due handoff; P1.30 revised fast/safe ISR preservation and measured timing; safe idle/input/re-entry servicing; P1.28/P1.33 stack-budget regression; cooperative no-kernel-entry limitation stated/tested; IM2 no bitmap/wrap/depth mutation; and all existing revised tests.

No CR-1 implementation step may be closed merely because the CR text is complete. Each owning plan gate must carry the relevant row of Section 8, and later aggregate/release gates must replay the rows assigned to them. H07 closes only after those owning and replay gates pass on the activated architecture.

Before check-in, apply the repository SoP to the exact changed bytes: scan every changed file line-by-line from a fresh disk copy; fix every defect; any fix resets the scan count; deliver/check in only after **three successive complete scans find zero new defects**, then pass the remaining repository license, policy, adversarial-review, and direct-main validation gates. Any `NO` or `FAIL` blocks check-in.
