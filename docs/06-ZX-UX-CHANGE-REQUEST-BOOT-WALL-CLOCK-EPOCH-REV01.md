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

**Status:** Proposed architecture-first version-1 wall-clock correction; no new syscall number, calling convention, record layout, or shell command. This revision freezes the complete synchronization surface for the boot epoch, `TIME1`, independent `SYS_TICKS`, `date`, `cal`, `cron`, boot ordering, and every known old unset-at-normal-boot acceptance/transcript rule before the combined rebaseline.

---

## 1. Normative goals

Version 1 shall:

1. retain the existing `date` command and `SYS_TIME_GET` / `SYS_TIME_SET` interfaces;
2. replace the normal cold-boot wall-clock `unset` state with one deterministic valid initial value;
3. initialize that value to the ZX Spectrum launch date, `1982-04-23 00:00:00`;
4. preserve the existing frame-derived, non-persistent software-clock model; and
5. make the boot default explicit to `date`, `cal`, `cron`, tests, documentation, and certification.

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
test that depends on the old cold-boot `unset` state. The existing internal invalid
state remains available only for early-boot/diagnostic/failure-path behavior and for
tests that explicitly exercise fail-closed `SYS_TIME_GET`; it is no longer the
successful production cold-boot state.

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

`SYS_TICKS` remains an independent monotonic modulo-2^32 frame counter. It starts
and advances according to its existing tick contract, is never initialized from
`388368000`, never uses `TIME1.revision`, and never becomes invalid merely because
the wall clock is internally invalid during an early-boot/diagnostic path.

---

## 5. `date` and `cal` command behavior

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

`cal` keeps its existing ABI and parsing. The no-argument and one-argument forms
still require valid wall time, but on a successful normal production boot that
precondition is already satisfied by the deterministic epoch. `cal: date not set`
remains valid only when an explicit diagnostic/early-invalid fixture exercises the
existing fail-closed state. The two-argument `cal month year` form remains
independent of wall time.

---

## 6. `cron` consequences

Because normal cold boot now begins with valid `TIME1`, calendar-based `cron` rules
may be eligible immediately after the daemon starts. They no longer wait for a
manual `date -s` merely to make wall time valid.

Existing `cron` matching, revision-aware deduplication, serial job execution, and
no-catch-up rules remain unchanged. `@boot` semantics remain distinct from calendar
matching and shall not be redefined as a launch-date calendar rule. `@hourly` and
`@daily` still require valid `TIME1`; successful normal boot now supplies that
validity before any user `cron` process can evaluate rules.

Tests shall prove that the deterministic boot epoch cannot cause one calendar
entry to execute more than once for the same `(wall-minute, revision)` pair. The
initial boot key uses revision 0. A later successful `date -s` keeps the existing
rule: revision changes, dedupe state is reset for the newly observed current minute,
and no missed calendar work is caught up.

---

## 7. Initialization ownership and ordering

The kernel owns the cold-boot wall-clock initialization. It shall happen once on
the normal production boot path before PID1 can observe `SYS_TIME_GET`, before the
shell can execute `date` or `cal`, and before a user `cron` process can evaluate
calendar rules.

Initialization shall be atomic with respect to accepted IM2 updates: no observable
state may combine launch-epoch seconds with a stale validity/revision/subsecond
value, and no first accepted frame may be lost or double-counted across the
initialization boundary.

The revised cold-boot sequence shall place one explicit wall-clock initialization
action after the wall-clock storage/kernel state has been initialized and before the
first runtime `EI` can accept a frame interrupt and before PID1 becomes observable or
schedulable. The final boot sequence and its numbered evidence rows must identify
that action rather than relying on an implicit side effect of unrelated
initialization.

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
that successful normal cold boot leaves wall time unset. At minimum synchronize:

- Section 10.1 `TIME1` / `SYS_TIME_GET` cold-validity wording while preserving the exact six-byte record and syscall calling conventions;
- Sections 6.3/6.7/28.2 tick/IM2 language so accepted frames advance the valid boot epoch while `SYS_TICKS` remains independent;
- Section 20.8 `date` and software-wall-clock text;
- Section 20.9 `cron` validity, boot-eligibility, revision/dedupe, and no-catch-up text;
- the `cal` command text that currently describes behavior when date is unset;
- boot/initialization ordering and the final cold-boot sequence;
- Section 41 and its replay ledger rows for date/cron/time behavior;
- the fixed-invariant summary that currently says wall time is explicitly unset after cold boot and calendar cron never runs while it is unset;
- Section 58 definitive acceptance item 9 and Section 63 success transcript, replacing the old literal `date: not set` checkpoint with a captured valid-format date line backed by deterministic evidence for the exact `TIME1` value returned to that `date` invocation; and
- every other duplicate matrix, transcript, or acceptance statement that treats `date: not set`, post-boot `E_AGAIN`, or calendar-cron suppression-until-manual-set as the successful normal cold-boot oracle.

The corresponding implementation-plan revision shall update at minimum:

- P1.13, preserving the coherent four-byte independent `SYS_TICKS` ABI while wall-clock advancement now normally starts from a valid boot epoch;
- P1.26 and P1.27 for the exact epoch bytes, valid/revision/subsecond initialization, diagnostic invalid state, and unchanged setter semantics;
- P6.30 and P8.40 wherever their Section-41/phase replay inherits the old unset/date/cron rows;
- P8.24 (`date`), P8.25 (`cron`), P8.28 (`cal`), P8.29 (`uptime` independence), and P8.39 (revision/minute dedupe with boot revision 0);
- P11.27 and any C48 time-wrapper acceptance that currently requires an unset successful boot fixture;
- P12.09 final cold-boot ordering, with one explicit initialization/evidence action before PID1 observability;
- P12.11 final date/cron demonstration;
- P12.26 full Section-41 matrix and its regenerated exact literal-row count;
- P12.30 definitive item 9; and
- P12.31 the literal success transcript.

The combined rebaseline must search the complete architecture and plan bytes for the
old normal-boot oracles, not just edit the named owners above. Matches referring to
unrelated shell `unset`, PATH/env unset behavior, or deliberate diagnostic invalid
wall-clock fixtures are not to be rewritten merely because they contain the word
`unset`. Every retained wall-clock-invalid test must state that it is an explicit
diagnostic/early-boot fixture, not the normal production cold-boot state.

If this CR and `docs/04-ZX-UX-CHANGE-REQUEST-DEFERRED-WRAP-REV01.md` are executed in
the same authorized architecture rebaseline, they remain separate change requests
with separate acceptance matrices even though one architecture/plan revision may
incorporate both. H06 may be folded into that same plan revision without merging its
acceptance responsibility into this CR.

The new architecture identity necessarily requires the existing E0 architecture
path/hash contract, verifier metadata, and durable certification evidence to be
re-baselined under the normal project process. Historical certification records and
completion tags remain immutable historical records. Activation must not leave
`main` knowingly split between old and new architecture identities.

---

## 9. Deterministic certification matrix

Certification is byte/state based. Screenshots or transcript capture may supplement,
but never replace, register/RAM/byte assertions. The revised architecture and plan
shall carry these rows to their owning/replay gates:

| Contract | Deterministic proof | Owning/replay gates |
| --- | --- | --- |
| Boot epoch bytes | Before first accepted frame, successful `SYS_TIME_GET` returns exactly `80 06 26 17 00 00`; validity true, revision 0, subsecond 0 | P1.26/P1.27, P12.09, P12.26, P12.30 |
| Normal-boot validity | PID1/shell-visible normal boot never returns `E_AGAIN`; explicit early/diagnostic invalid fixture still fails closed | P1.27, P12.09, P12.26 |
| Frame boundary | After the P1.26 boot-time wall-clock owner initializes the epoch, accepted frames 1..49 retain `388368000`; frame 50 produces `388368001` exactly once; P1.13 remains the independent tick/IM2 prerequisite | P1.26, P12.26 |
| Independent ticks | `SYS_TICKS` is coherent u32 modulo-2^32 frame state and never derives from epoch seconds, revision, or wall-clock validity | P1.13, P8.29, P11.27, P12.26 |
| First/repeated set | First successful set makes revision 1 and subsecond 0; repeating same seconds increments once again | P1.27, P8.24, P11.27, P12.26 |
| Reboot reset | After arbitrary set/advance, new cold boot returns exactly to epoch bytes/revision0/subsecond0 | P1.26/P1.27, P12.09, P12.26, P12.30 |
| Hidden-source rejection | Host/emulator/RTC/tape/filesystem/BASIC-time perturbation cannot alter initial bytes | P1.26, P12.26 |
| `date` boot output | Controlled zero-frame post-init fixture prints exactly `1982-04-23 00:00:00`; later/release invocations capture a valid `YYYY-MM-DD hh:mm:ss` line and deterministic companion evidence proves it matches the exact `TIME1` returned to that `date` invocation; never successful-boot `date: not set` | P8.24, P8.40, P12.11, P12.26, P12.30, P12.31 |
| `cal` boot behavior | No/one-argument forms use boot-valid wall time; explicit invalid diagnostic fixture retains `cal: date not set`; two-argument form stays independent | P8.28, P8.40, P12.26 |
| `cron` boot eligibility | Calendar/@hourly/@daily can evaluate from revision0 boot time without prior manual set; `@boot` remains independent | P8.25/P8.39, P8.40, P12.11, P12.26, P12.30 |
| `cron` dedupe/no catch-up | One firing maximum per `(wall-minute,revision)`; boot epoch cannot double-fire; later `date -s` changes revision and evaluates current minute only | P8.25/P8.39, P8.40, P12.11, P12.26 |
| ABI preservation | TIME1 remains six bytes `{u32 wall_seconds,u16 revision}`; SYS_TIME_GET/SET and SYS_TICKS numbers/calling conventions unchanged | P1.27, P11.27, P12.26 |
| Transcript/matrix purge | No normal-production acceptance row/transcript still expects post-boot unset/E_AGAIN/`date: not set`/calendar suppression until manual set | P6.30, P8.40, P12.11, P12.26, P12.30, P12.31 |

The combined architecture/plan rebaseline must regenerate the exact Section-41/P12.26
stable-row ledger after CR-1, CR-2, and H06 synchronization. Any REV11 literal row
count is historical to that baseline and cannot be carried forward unless it happens
to equal the newly enumerated mandatory rows.

---

## 10. Forbidden implementations

Certification fails for: successful normal cold boot leaving wall time unset; using
a host, emulator, RTC, network, tape, filesystem, or BASIC-derived time source;
treating `1982-04-23 00:00:00` as persisted real time; incrementing revision during
boot initialization; starting the subsecond accumulator nonzero; changing the
`TIME1` layout; changing the syscall numbers or calling conventions of
`SYS_TIME_GET`, `SYS_TIME_SET`, or `SYS_TICKS`; coupling monotonic ticks to calendar
seconds or validity; silently adding timezone/locale semantics; duplicating
contradictory boot-epoch constants; allowing `cron` to double-fire because the boot
default became valid; retaining a normal-production `date: not set`/post-boot
`E_AGAIN` acceptance oracle; or omitting the explicit boot-order initialization
point.

---

## 11. Acceptance and completion gate

Completion requires architecture, implementation plan, kernel, `date`, `cal`,
`cron`, tests, boot ordering, transcripts, and release certification to agree on one
boot-time contract. Required: launch-date epoch bytes PASS; revision-0 boot state
PASS; 50-frame advancement PASS; independent coherent `SYS_TICKS` PASS;
first/repeated set revision behavior PASS; reboot reset PASS; no hidden time source
PASS; `date` exact boot/output format PASS; `cal` normal-boot validity plus diagnostic
invalid-state behavior PASS; `cron` boot-valid/calendar eligibility and deduplication
PASS; no old normal-boot unset oracle remains in synchronized architecture/plan
bytes PASS; revised regression matrices/transcripts PASS; and E0/affected phase
evidence re-certified against the newly activated architecture identity.

Before check-in, apply the repository SoP to the exact changed bytes: scan every
changed file line-by-line from a fresh disk copy; fix every defect; any byte change
resets the scan count; deliver/check in only after **three successive complete scans
find zero new defects**, then pass the remaining repository license, project-policy,
adversarial-review, and direct-main validation gates. Any `NO` or `FAIL` blocks
check-in.
