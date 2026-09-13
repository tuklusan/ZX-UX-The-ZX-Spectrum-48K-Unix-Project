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

# ZX-UX Working Workflow Tracker

**Status:** CLOSED coordination ledger. There are no open scratch workflow items.
This file records completed coordination only; it is not architecture,
implementation-plan authority, certification evidence, or a GitHub Actions workflow.

## Authority and continuation rule

- Active architecture authority is `docs/01-ZX-UX-ARCHITECTURE-REV12.md`.
- Active implementation authority is `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md`.
- CR-1 remains governed by
  `docs/04-ZX-UX-CHANGE-REQUEST-DEFERRED-WRAP-REV01.md`.
- CR-2 remains governed by
  `docs/06-ZX-UX-CHANGE-REQUEST-BOOT-WALL-CLOCK-EPOCH-REV01.md`.
- Future implementation/certification obligations are deliberately not represented
  as open scratch checkboxes here. Execute them only at their owning REV03 steps.
- H06 final SDK-corpus acceptance remains owned by P11.45, with aggregate closure at
  P11.48 and P12.26; this is plan work, not an open scratch coordination item.
- CR-1 and CR-2 close only when their actual owning completion gates pass; their
  remaining implementation is plan work, not an open scratch coordination item.
- At any blocker, instrument first, diagnose second, repair third, and escalate only
  after diagnostic avenues are exhausted.

## Current durable checkpoint

- [x] Controlled REV12/REV03 rebaseline activated by
  `104723b9111314630e9057ad9a9002b982fc2598`.
- [x] Rebased Phase-0 certification evidence activated by
  `5e4a73954408758aa4821a4bcf8d535e1c3cef84`.
- [x] Phase-1 steps P1.01 through P1.13 are admitted in the active Phase-1 gate.
- [x] P1.13 was admitted by
  `c63456a2f5e801de3a88f67a08a4efb369dce839`.
- [x] Post-admission Phase-1 workflow run `34732342964` passed.
- [x] Post-admission artifact `10310101877`, named
  `zxux-phase1-34732342964-1`, has SHA-256
  `2fc59a52589133b17be94be92829f60e192b10c41a8d34a45880ecc4087e3287`.
- [x] The former P1.13 `sys-ticks-snapshot-is-coherent-and-four-bytes` retained
  failure is closed; the post-admission evidence passes all 30 P1.13 assertions.
- [x] `CANDIDATE_STEPS` is empty at the P1.13 admission checkpoint.

## Closed change-control and rebaseline coordination

- [x] CR-1 pre-execution change-control gaps were frozen before implementation.
- [x] CR-2 synchronization requirements were frozen for the deterministic
  `1982-04-23 00:00:00` boot epoch, `TIME1`, independent `SYS_TICKS`, `date`, `cal`,
  `cron`, boot ordering, and old unset-at-normal-boot rules.
- [x] H06 complete recursive SDK `usr/src` accounting/execution requirements were
  folded into REV03 while remaining a distinct later acceptance obligation.
- [x] The combined architecture and implementation-plan rebaseline was activated as
  REV12/REV03 rather than as separate drifting edits.
- [x] E0/Phase-0 rebaseline certification and the required admitted Phase-1 replay
  were completed before P1.13 admission.
- [x] P1.13 diagnosis was instrumentation-led. Persisted diagnostics proved that the
  apparent blocker was an obsolete P1.31 BREAK source-contract probe rather than a
  production SYS_TICKS defect.
- [x] The P1.31 test-side BREAK probe was aligned with the legitimate RRCA ISR form by
  `f6d6e4806f63586634fcb0bdfba00435d8d7304f` without regressing production ISR
  behavior to satisfy the stale checker.
- [x] Persistent Phase-1 failure diagnostics remain part of the gate so later
  failures preserve command results, stdout, stderr, timeout state, and final error.

## P1.13 durable evidence bookkeeping

- [x] Canonical durable evidence location confirmed as `v1/dist/certification/`.
- [x] `P1.13.build.json` recovered unchanged from workflow run `34732342964`;
  SHA-256 `f2bd826cc2d0aec36614417f92337629f2a05e9b2e57967e1a03dc267d66ce87`.
- [x] `P1.13.test.json` recovered unchanged from workflow run `34732342964`;
  SHA-256 `9e39842429dcd3a88be2565833b90ad2ed17bc9c570a22056dac1fbd36228f81`.
- [x] Both records are schema 2, PASS, clean-source records naming source commit
  `c63456a2f5e801de3a88f67a08a4efb369dce839`.

## Historical Baseline Repair and Reconciliation anchors

- [x] Final source anchor:
  `66e12b2d641b2db93d0aae949d2aac2565193989`.
- [x] Durable Phase-0 evidence anchor:
  `268db8b3763f685488ffd4973859390e263db648`.
- [x] Completion tag: `COMPLETED-BASELINE-REPAIR-RECONCILIATION-REV01-RR`.
- [x] Recorded completion-tag target:
  `2ad6025d5416115ed67cee0473db1a80044a8d2f`.

## Continuation checkpoint

The scratch coordination queue is closed. Resume Phase 1 from the active REV03 plan.
At this checkpoint, the first not-yet-admitted step after P1.13 is P1.14, **ROM FRAMES
and UDG boot compatibility**. Read its live REV03 contract and prerequisites before
editing; do not implement CR-1, CR-2, or H06-owned later semantics early merely because
their coordination work is complete here.

## Active blockers

None recorded at this checkpoint.
