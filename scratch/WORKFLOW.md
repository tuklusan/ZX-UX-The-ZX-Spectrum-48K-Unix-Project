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

**Status:** Repository-tracked scratch coordination only; not architecture,
implementation authority, certification evidence, or a GitHub Actions workflow.

## Tracking rules

- `[ ]` means not completed.
- `[x]` means the coordination item is completed and has a durable repository basis.
- Do not mark implementation/certification work complete merely because prose was
  written here; use the canonical gate and evidence required by the owning document.
- If a blocker appears, instrument and diagnose it before escalation, and record the
  useful diagnosis in the blocker section.
- Before repository work in a new session, verify current `main`, relevant tags,
  changed-file scope, and the applicable Phase-1 checkpoint.
- Any bytes promoted from this tracker into canonical project material must pass the
  normal project SoP independently.

## Durable starting state

- [x] Baseline Repair and Reconciliation Revision 01 is closed and complete.
- [x] Completion tag `COMPLETED-BASELINE-REPAIR-RECONCILIATION-REV01-RR` exists and
  points to `2ad6025d5416115ed67cee0473db1a80044a8d2f`.
- [x] Phase-1 admitted checkpoint is P1.01 through P1.12.
- [x] P1.13 remains unadmitted; work commit is
  `3245d489ad9b26c3ea55bcf0677374d2cfa5b53d`.
- [x] Retained P1.13 failing assertion is
  `sys-ticks-snapshot-is-coherent-and-four-bytes`.
- [x] P1.14 has reconnaissance only and no admitted modification.
- [x] CR-1 exists at
  `docs/04-ZX-UX-CHANGE-REQUEST-DEFERRED-WRAP-REV01.md`.
- [x] CR-2 exists at
  `docs/06-ZX-UX-CHANGE-REQUEST-BOOT-WALL-CLOCK-EPOCH-REV01.md`.

## Housekeeping and infrastructure prerequisites

Add owner-directed housekeeping and infrastructure items here before CR execution.
Items that affect architecture identity, certification, runner behavior, repository
policy, or implementation ordering must be resolved before the dependent rebaseline
step is marked complete.

- [ ] H01 — TBD: owner to specify housekeeping/infrastructure work.
- [ ] H02 — TBD: owner to specify additional work if needed.
- [ ] H03 — TBD: owner to specify additional work if needed.
- [ ] Classify each populated item as prerequisite, independent work, or post-CR work.
- [ ] Complete all prerequisite housekeeping/infrastructure items.

## CR-1 — Deferred wrap, canonical tty64 font, and cursor semantics

Source: `docs/04-ZX-UX-CHANGE-REQUEST-DEFERRED-WRAP-REV01.md`

- [ ] Revise the CR before execution to close the known change-control gaps.
- [ ] Explicitly cover the E0 architecture-identity/path/hash rebaseline effect.
- [ ] Add P1.13 cursor-service/IM2 handoff ownership to the synchronization scope.
- [ ] Review and synchronize P1.30 ISR timing/preservation requirements.
- [ ] Review safe idle/input service points, including relevant P1.31/P1.34 behavior.
- [ ] Review P1.28/P1.33 stack/high-water regression requirements.
- [ ] Freeze exact deferred blink-request accumulation/coalescing semantics.
- [ ] Freeze one exact screen-mutation bracketing/nesting policy.
- [ ] Confirm canonical final `font4x8` bytes and digest handling remain host-side where
  required by the CR.
- [ ] Complete the CR-1 deterministic acceptance matrix in the revised architecture
  and implementation plan.

## CR-2 — Deterministic cold-boot wall-clock epoch

Source: `docs/06-ZX-UX-CHANGE-REQUEST-BOOT-WALL-CLOCK-EPOCH-REV01.md`

- [x] Separate CR authored and committed.
- [ ] Incorporate the `1982-04-23 00:00:00` boot epoch into the next architecture.
- [ ] Preserve existing `TIME1` layout and time syscall calling conventions.
- [ ] Preserve independent `SYS_TICKS` semantics.
- [ ] Synchronize P1.26 and P1.27 contracts/tests.
- [ ] Synchronize P8.24 `date` behavior and tests.
- [ ] Synchronize P8.25 `cron` validity-at-boot behavior and tests.
- [ ] Synchronize P6.30, P8.40, P12.26, P12.30, P12.31, and duplicate matrices or
  transcripts that encode the old unset-at-boot rule.
- [ ] Complete the CR-2 deterministic acceptance matrix in the revised architecture
  and implementation plan.

## Combined architecture and implementation-plan rebaseline

The CRs remain separate change requests even if they are incorporated into one
architecture/plan revision.

- [ ] Decide and record whether CR-1 and CR-2 are authorized for the same rebaseline.
- [ ] Freeze Phase-1 implementation at the current checkpoint during rebaseline work.
- [ ] Prepare the proposed next architecture revision.
- [ ] Ensure the architecture incorporates each authorized CR without merging their
  distinct acceptance responsibilities.
- [ ] Prepare the matching implementation-plan revision.
- [ ] Update all architecture path/hash consumers and verifier metadata deliberately;
  do not leave `main` knowingly half-switched between architecture identities.
- [ ] Apply the full project SoP to the exact architecture/plan/rebaseline bytes.
- [ ] Activate the new canonical architecture identity in a controlled transaction.
- [ ] Preserve old R&R tags and certification records as immutable historical evidence.
- [ ] Re-certify E0 against the newly activated architecture identity.
- [ ] Re-certify Phase 0 against the newly activated architecture identity.
- [ ] Revalidate P1.01 through P1.12 against the newly activated architecture identity.

## Phase-1 resumption after rebaseline

- [ ] Confirm P1.01-P1.12 remain admitted after required revalidation.
- [ ] Resume revised P1.13 from its unadmitted checkpoint.
- [ ] Diagnose/instrument the retained coherent-four-byte SYS_TICKS failure before any
  escalation.
- [ ] Admit P1.13 only after its revised contract and all required tests pass.
- [ ] Continue later Phase-1 work in revised plan order.
- [ ] Implement CR-1 console/font/cursor work only at its revised owning steps.
- [ ] Implement CR-2 wall-clock initialization only at its revised owning steps.

## Final CR closure

- [ ] CR-1 architecture, plan, code, tests, assets, and certification all agree.
- [ ] CR-1 completion gate passes.
- [ ] CR-2 architecture, plan, code, tests, date/cron behavior, and certification all
  agree.
- [ ] CR-2 completion gate passes.
- [ ] Update this tracker with durable completion references rather than narrative-only
  claims.

## Blockers and diagnostics

No active blocker is recorded here yet.

When adding one, record the affected step, observable failure, instrumentation added,
results obtained, self-recovery attempts, and the durable commit/run/evidence reference.

## Session handoff notes

Use this section only for concise durable coordination facts that are not themselves
canonical requirements. Remove stale notes when they stop helping future sessions.

- Scratch tracker established in the repository so it survives ephemeral cloud storage
  and remains visible to future project sessions.
