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

# ZX-UX Change Request: Deterministic Cold-Boot Wall-Clock Epoch

**Status:** Proposed architecture-first version-1 wall-clock correction; no new syscall number, calling convention, record layout, or shell command.

---

## 1. Normative goals

Version 1 shall:

1. retain the existing `date` command and `SYS_TIME_GET` / `SYS_TIME_SET` interfaces;
2. replace the normal cold-boot wall-clock `unset` state with one deterministic valid initial value;
3. initialize that value to the ZX Spectrum launch date, `1982-04-23 00:00:00`;
4. preserve the existing frame-derived, non-persistent software-clock model; and
5. make the boot default explicit to `date`, `cron`, tests, documentation, and certification.

The calendar date records the documented ZX Spectrum launch date. The `00:00:00`
time is a ZX-UX deterministic convention and is not a claim that the historical
launch event occurred at midnight.

---

## 2. Existing version-1 surface retained

This change request does not add a second `date` command or a second time API.
The existing version-1 architecture already requires:

```text
date
date -s "YYYY-MM-DD hh:mm:ss"
SYS_TIME_GET
SYS_TIME_SET
TIME1 = { u32 wall_seconds, u16 revision }
```

The supported calendar range remains 1970..2099 Gregorian. The system still has
no persistent RTC and no timezone database. `TIME1.wall_seconds` remains the
existing unsigned 32-bit local-session seconds count from
`1970-01-01 00:00:00`.

The change is solely the normal boot initialization policy and every contract or
test that depends on the old cold-boot `unset` state.

---

## 3. Canonical cold-boot epoch

On every normal ZX-UX cold boot, initialize wall-clock state to exactly:

```text
calendar              1982-04-23 00:00:00
wall_seconds decimal   388368000
wall_seconds hex       0x17260680
TIME1 bytes            80 06 26 17 00 00
revision               0
subsecond_frames       0
valid                  true
```

The six-byte `TIME1` line above is the public record immediately after
initialization and before the first accepted frame tick: four little-endian
wall-seconds bytes followed by revision `0x0000`.

The initial value is deterministic session state, not persistence. Rebooting the
machine does not recover elapsed real-world time. A new cold boot starts again at
`1982-04-23 00:00:00` and advances only from accepted frame interrupts after the
wall-clock initialization point.

No battery-backed clock, host clock, emulator clock, tape timestamp, BASIC system
variable, filesystem metadata, or network source may silently replace this value.

The documentary launch-date reference is the Centre for Computing History record
"Sinclair launches the ZX Spectrum", dated 23 April 1982. This provenance is
documentary only; normal boot and certification do not require network access.

The kernel may retain an internal invalid/uninitialized state during early boot or
a diagnostic failure path, so `SYS_TIME_GET` can remain fail-closed there. That
state shall not be observable by PID1 on a successful normal production boot.

---

## 4. Tick and revision semantics

The existing PAL baseline remains one wall second per 50 accepted IM2 frame ticks.
The private subsecond accumulator starts at zero at cold boot. Therefore, from the
initial state:

```text
accepted frames 0..49   wall_seconds remains 388368000
accepted frame 50       wall_seconds becomes 388368001
```

Missed interrupts during approved ROM-critical or cassette operations remain
honestly missed. This CR does not introduce catch-up from a host or hardware time
source.

Cold-boot initialization is not a `SYS_TIME_SET` operation and shall not increment
the revision. Revision starts at zero. The first successful `SYS_TIME_SET`, even if
setting the same seconds value, increments revision to 1 and resets the private
subsecond accumulator to zero, preserving the existing ABI contract.

`SYS_TICKS` remains an independent monotonic modulo-2^32 frame counter and is not
rebased to the calendar epoch.

---

## 5. `date` command behavior

The existing lower-case external `date` utility remains the only version-1 date
command.

With no arguments it continues to display exactly:

```text
YYYY-MM-DD hh:mm:ss
```

After normal boot, `date` shall no longer report `date: not set`. It shall display
the deterministic launch-date-derived wall time corresponding to the accepted
frame ticks since wall-clock initialization.

The existing setter remains:

```text
date -s "YYYY-MM-DD hh:mm:ss"
```

It retains existing validation, supported range, syscall use, revision increment,
and subsecond reset semantics. This CR adds no parsing form, timezone syntax, RTC
claim, persistence claim, or locale-dependent output.

---

## 6. `cron` consequences

Because normal cold boot now begins with valid `TIME1`, calendar-based `cron` rules
may be eligible immediately after the daemon starts. They no longer wait for a
manual `date -s` merely to make wall time valid.

Existing `cron` matching, revision-aware deduplication, serial job execution, and
no-catch-up rules remain unchanged. `@boot` semantics remain distinct from calendar
matching and shall not be redefined as a launch-date calendar rule.

Tests shall prove that the deterministic boot epoch cannot cause one calendar
entry to execute more than once for the same `(wall-minute, revision)` pair.

---

## 7. Initialization ownership and ordering

The kernel owns the cold-boot wall-clock initialization. It shall happen once on
the normal production boot path before PID1 can observe `SYS_TIME_GET`, before the
shell can execute `date`, and before a user `cron` process can evaluate calendar
rules.

Initialization shall be atomic with respect to accepted IM2 updates: no observable
state may combine launch-epoch seconds with a stale validity/revision/subsecond
value, and no first accepted frame may be lost or double-counted across the
initialization boundary.

The implementation shall use one canonical constant definition for the initial
wall-seconds value. Duplicate magic literals in unrelated kernel, shell, utility,
or test code are forbidden except explicit test vectors checking the canonical
constant.

---

## 8. Mandatory architecture and plan synchronization

This CR is architecture-first. It shall not be implemented by patching code while
the canonical architecture still requires an unset cold wall clock.

When this CR is authorized for execution, the next architecture revision shall
update every duplicated invariant and acceptance statement that says or implies
that normal cold boot leaves wall time unset. At minimum review and update:

- the software wall-clock design and `TIME1` validity language;
- the syscall contract for `SYS_TIME_GET` / `SYS_TIME_SET` where cold state is described;
- the shell/core-command `date` contract;
- `cron` behavior that depends on wall-clock validity;
- boot/initialization ordering and acceptance text; and
- any test matrix that expects `E_AGAIN` from `SYS_TIME_GET` after normal boot.

The corresponding implementation-plan revision shall update at minimum P1.26,
P1.27, P8.24 (`date`), P8.25 (`cron`), P6.30, P8.40, P12.26, P12.30, and P12.31,
plus every duplicate matrix or transcript that repeats the old unset-at-cold-boot
rule. P1.13 shall be reviewed because it advances wall-clock state when valid, but
its `SYS_TICKS` contract remains independent; this CR changes wall-clock
initialization, not the four-byte tick ABI.

If this CR and `docs/04-ZX-UX-CHANGE-REQUEST-DEFERRED-WRAP-REV01.md` are executed in
the same authorized architecture rebaseline, they remain separate change requests
with separate acceptance matrices even though one architecture/plan revision may
incorporate both.

The new architecture identity necessarily requires the existing E0 architecture
path/hash contract, verifier metadata, and durable certification evidence to be
re-baselined under the normal project process. Historical certification records and
completion tags remain immutable historical records.

---

## 9. Deterministic certification tests

Certification shall be byte/state based. At minimum prove:

1. **Initial bytes:** immediately after cold wall-clock initialization and before the first accepted frame, `SYS_TIME_GET` returns exactly `80 06 26 17 00 00`.
2. **Initial validity:** the same call succeeds; normal cold boot does not return `E_AGAIN` for wall time.
3. **Frame boundary:** frames 1..49 leave seconds at `388368000`; frame 50 produces `388368001` exactly once.
4. **Independent ticks:** `SYS_TICKS` continues its own modulo-2^32 frame count and is not initialized to or derived from `388368000`.
5. **First set:** the first successful `SYS_TIME_SET` changes revision from 0 to 1 and resets the private subsecond accumulator to 0.
6. **Repeated same-value set:** setting `388368000` again is still a successful set and increments revision exactly once.
7. **Reboot:** a fresh cold boot returns to `1982-04-23 00:00:00`, revision 0, subsecond 0, regardless of the prior session's final wall time.
8. **No hidden source:** perturbing emulator/host clock or unrelated Spectrum/BASIC time state cannot change the initial ZX-UX wall-clock bytes.
9. **`date`:** with a controlled zero-frame post-init fixture, `date` prints exactly `1982-04-23 00:00:00`; later output matches accepted-frame advancement.
10. **`cron`:** a calendar rule can match without a preceding manual time set, while revision/minute deduplication still prevents duplicate execution.
11. **Regression:** date parsing/range validation, `SYS_TIME_SET`, `SYS_TIME_GET`, cron matching, and existing tick tests remain green except expectations deliberately revised by this CR.

---

## 10. Forbidden implementations

Certification fails for: normal cold boot leaving wall time unset; using a host,
emulator, RTC, network, tape, filesystem, or BASIC-derived time source; treating
`1982-04-23 00:00:00` as persisted real time; incrementing revision during boot
initialization; starting the subsecond accumulator nonzero; changing the `TIME1`
layout; changing the syscall numbers or calling conventions of `SYS_TIME_GET`,
`SYS_TIME_SET`, or `SYS_TICKS`; coupling monotonic ticks to calendar seconds; silently adding timezone/locale semantics;
duplicating contradictory boot-epoch constants; or allowing `cron` to double-fire
because the boot default became valid.

---

## 11. Acceptance and completion gate

Completion requires architecture, implementation plan, kernel, `date`, `cron`,
tests, and release certification to agree on one boot-time contract. Required:
launch-date epoch bytes PASS; revision-0 boot state PASS; 50-frame advancement PASS;
independent `SYS_TICKS` PASS; first/repeated set revision behavior PASS; reboot reset
PASS; no hidden time source PASS; `date` exact-format PASS; `cron` valid-at-boot and
deduplication PASS; revised regression matrices PASS; and E0/affected phase evidence
re-certified against the newly activated architecture identity.

Before check-in, apply the repository SoP to the exact changed bytes: scan every
changed file line-by-line from a fresh disk copy; fix every defect; any byte change
resets the scan count; deliver/check in only after **three successive complete scans
find zero new defects**, then pass the remaining repository license, project-policy,
adversarial-review, and direct-main validation gates. Any `NO` or `FAIL` blocks
check-in.
