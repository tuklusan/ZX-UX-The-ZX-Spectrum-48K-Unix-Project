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

# ZX-UX Phase 2 — Processes and Loader Implementation and Certification Runbook

**Status:** CLOSED — historical Phase-2 coordination record only; do not resume work from this file.

**Goal:** Implement, certify, durably activate, and close REV12/REV03 Phase 2
(P2.01-P2.24) so ZX-UX can load and execute genuine relocatable MEX1 user processes
with correct process lifecycle, context, bootstrap-state, cancellation, rollback, and
resource-accounting behavior. Stop after Phase-2 closure; do not begin Phase 3.

This file is durable cross-session coordination under `scratch/`. Canonical repository
state and the authority documents listed below always override it if they disagree.

## 1. Authority and hard boundaries

1. Modify only `tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project`.
2. Every other GitHub repository is read-only. No branch, commit, push, PR, tag, or
   other mutation is permitted outside the canonical ZX-UX repository.
3. `docs/01-ZX-UX-ARCHITECTURE-REV12.md` is the architecture authority.
4. `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md` defines the exact Phase-2 step
   contracts, ordering, commands, negatives, and evidence obligations.
5. `AGENTS.md` and `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md` define the mandatory SoP:
   three unchanged clean scans, license gate, project-policy gate, dynamic four-pass
   adversarial review, direct-main check-in, and required automated validation.
6. Preserve the active Phase-0 and Phase-1 evidence/source-binding invariants. A
   Phase-2 change may not weaken, rewrite, or bypass an earlier-phase contract merely
   to make Phase 2 pass.
7. Do not begin Phase 3 or implement Phase-3 generic I/O/pipes work under this goal.
8. Treat local `/mnt/data`, runner filesystems, and chat-local state as disposable.
   Durable continuity comes from committed repository state and GitHub Actions history.
9. Instrument blockers before changing source. Prefer exact diagnostics over guesses.
10. Scratch coordination is never a substitute for architecture or certification
    evidence.

## 2. Starting closed baseline

The Phase-2 goal was opened after the combined rebaseline runbook closed successfully.
Creation-time baseline anchors are:

- closed Phase-1 activation `main`:
  `b05b8cc74836b038cc4dd0a61a7e607ab025a13a`;
- Phase-1 certified source:
  `e84dfc93da08963404b569010464b2d78f1b3fba`;
- active architecture SHA-256:
  `a90d523f62a95e8cba6af0312b596a2d5f6bc1aa2ef92f39bb391509b7c15e1b`;
- final successful rebaseline Quality/CI run: `34868343182`.

These are historical anchors, not permission to skip restart validation. The
registration check-in that adds/closes scratch goal files is documentation-only and may
advance `main` without changing the certified architecture or target implementation.

## 3. Mandatory fresh-session restart procedure

At the start of every new chat, after context loss, or after any uncertain interruption:

1. Fetch current `main` and state its exact SHA.
2. Read this runbook from that `main`.
3. Read `AGENTS.md`, `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md`, current REV12, and the
   complete current REV03 Phase-2 section P2.01-P2.24.
4. Hash current REV12 and require the certified architecture identity unless a
   separately authorized architecture change has reopened the baseline.
5. Run/read the active Phase-0 and Phase-1 validators and inspect their current
   aggregates; both must remain active before Phase-2 source work proceeds.
6. Inspect recent relevant Quality/CI and any Phase-2 workflow history rather than
   relying on remembered status.
7. Inspect the current Phase-2 source/evidence paths to determine exactly which P2 step
   is the first incomplete canonical step.
8. Check the worktree/source state for unexpected Phase-3 changes. If Phase-3 work is
   present, stop and classify the state before proceeding.
9. State the selected checkpoint from Section 4 and the next deterministic action.
10. If repository, evidence, or workflow state is contradictory, classify
    `BLOCKED-MIXED`, improve diagnostics, and do not make speculative source changes.

## 4. Phase-2 checkpoint state machine

### P2-C0 — ready to begin Phase 2

Choose P2-C0 when Phase 0 and Phase 1 remain actively certified, no Phase-2 canonical
step has been completed under this goal, and there is no unreviewed Phase-2 residue.
Resume at P2.01.

### P2-C1 — Phase 2 partially implemented

Choose P2-C1 when at least one P2 step is durably complete but P2.24 is not yet ready.
Resume at the first incomplete step in exact REV03 order. Never skip ahead because a
later feature is easier or more interesting.

### P2-C2 — P2.01-P2.23 complete, acceptance pending

Choose P2-C2 only when every P2.01-P2.23 build/test/negative obligation required by
REV03 passes against the intended source lineage and P2.24 has not yet closed.
Resume at P2.24.

### P2-C3 — Phase-2 acceptance passed, durable activation/closure pending

Choose P2-C3 when P2.24 passes but the repository does not yet contain the required
active durable Phase-2 aggregate/evidence state, or final Quality/CI closure has not
been proved against that activated state.

### P2-DONE — Processes and Loader frozen

Choose P2-DONE only when every Section-9 closure condition is proved against current
`main`.

If none of these states fits exactly, use `BLOCKED-MIXED` and instrument the ambiguity.

## 5. Required implementation scope

Implement all canonical REV03 steps P2.01-P2.24 in order. This runbook groups them for
coordination only; REV03 remains authoritative for the exact per-step requirements.

### 5.1 MEX1 format, independent inspection, and relocation safety

Phase 2 must freeze and test the exact 24-byte MEX1 header and stored-stream shape,
including version/flags/header-size rules, image/BSS/entry/stack fields, relocation
count/table location, body/header CRCs, exact stored length, and no trailing bytes.
All multiplication/addition checks required by REV03 must widen before narrowing so a
16-bit wrap can never turn malformed input into an accepted executable.

The host MEX1 inspector must be an independent oracle. Target loader output may not
certify itself. Malformed sizes, offsets, relocation ordering/overlap/end overrun,
CRC failures, unsupported values, and adversarial wrap vectors must fail for the
specified reason without committing partial target state.

### 5.2 Relocatable load and process bootstrap state

Implement the canonical relocatable image load into an uncommitted ANY allocation,
copy/decode image bytes, zero BSS, apply validated relocations, and commit only after
all validation succeeds.

Allocate the process runtime stack under its exact FAST_REQUIRED contract. Keep ARG1
and ENV1 in the separate process-owned immutable bootstrap allocation required by
REV03 rather than burying them in the downward runtime stack. Construct the exact
initial user context, including entry PC/register contract, canonical IY, private
alternate-register semantics, and bootstrap frame budget.

Every validation failure must roll back all provisional allocations and leave allocator
and process accounting indistinguishable from the pre-attempt state.

### 5.3 Process lifecycle

Complete the canonical process lifecycle owned by Phase 2, including the REV03-defined
spawn/start, exec replacement, exit, parent/child relationship, wait behavior, zombie
retention, reaping, PID-generation/reuse protection, and status propagation.

A process that exits must release resources that are no longer required while retaining
exactly the descriptor/status state required for ZOMBIE until its authorized wait/reap.
Stale PID or generation state must never alias a reused process record.

### 5.4 Kill, cancellation, scheduler/context integration, and recovery

Implement the Phase-2 kill/cancellation contracts without violating Phase-1 scheduler,
interrupt, IY, alternate-register, or context invariants. A blocked started child must
be woken to observe the specified interrupted condition at a safe kernel boundary;
unauthorized targets and protected process identities must be rejected exactly as
REV03 requires.

Cancellation, failed exec/spawn, malformed MEX1, failed allocation, wait/reap races,
and other required negatives must not leak memory, corrupt process records, or leave
half-committed scheduler state.

### 5.5 Relocation and leak closure

Exercise the same real MEX1 through the real spawn path at distinct allocator bases and
prove identical intended observable behavior with correct relocated words at both
bases. Fixed-address accidents do not satisfy relocation certification.

Run the REV03 repeated lifecycle/accounting stress. Hundreds of required cycles must
return to byte-identical accounting; the deliberate skipped-free/leak negative must be
detected rather than normalized away.

## 6. Per-step execution discipline

For each P2 step:

1. Re-read that exact REV03 step immediately before implementation.
2. Inspect prerequisite source and evidence rather than assuming prior behavior.
3. Add instrumentation first when a failure is not deterministic from existing data.
4. Make the smallest architecture-conformant source/test/documentation change that
   satisfies the exact step.
5. Run its canonical build command, host/static checks, emulator assertions where
   required, positive test, and required negative/failure test.
6. Preserve deterministic hashes/register/RAM/process/accounting proof required by the
   step; screenshot-only success is never sufficient where machine-state assertions
   are required.
7. Execute the complete repository SoP on the exact proposed check-in bytes.
8. Check in directly to `main` only after the SoP passes.
9. Treat any resulting automated failure as a defect and restart from `SCAN-1` for the
   corrective bytes.
10. Reconfirm earlier active evidence remains valid whenever a Phase-2 change touches
    a shared kernel/host/evidence path.

Do not batch unrelated future P2 steps into a check-in merely to reduce check-in count.
Accuracy and recoverability take precedence over throughput.

## 7. Phase-2 evidence and activation requirements

REV03 requires retained build/test evidence for every numbered Phase-2 step and phase
aggregate evidence at the phase gate. Before relying on any remembered Phase-1
activation pattern, inspect the current repository's actual evidence validators,
finalizers, workflows, and activation rules.

If Phase-2-specific finalization/validation/workflow machinery is absent, implement the
minimum fail-closed machinery required by the canonical evidence contract through the
normal SoP. Do not copy Phase-1 `run_attempt` behavior by assumption; activation rules
must be explicit in current reviewed source.

Phase-2 durable evidence must, at minimum, prove the exact clean certified source,
architecture identity, toolchain identity, prerequisite chain, required record set,
record hashes, and P2.24 PASS state. Hand-edited certification JSON is prohibited.

An activation check-in, if the reviewed machinery uses one, must be evidence-only,
bound to the source it certifies, and must not mutate active Phase-0/Phase-1 evidence.
The active Phase-2 validator must fail closed for source, architecture, toolchain,
manifest/hash, prerequisite, or activation-shape corruption.

## 8. P2.24 acceptance gate

P2.24 is the milestone boundary. It aggregates the complete Phase-2 obligations,
including MEX1 inspection, relocation/load atomicity, process creation/replacement,
wait/zombie/reaping behavior, context/IY/alternate-register integrity, cancellation,
and leak/accounting evidence.

P2.24 may pass only if every required P2.01-P2.23 dependency is green and every
required rollback path is proved. Any failed rollback blocks Phase-2 closure.

## 9. Final closure audit

The Phase-2 goal is complete only when all of the following are proved against current
`main`:

1. Every canonical P2.01-P2.24 implementation obligation in current REV03 is complete.
2. Every required P2.01-P2.24 build/test record is PASS and bound to the intended
   clean source/toolchain/architecture state.
3. Exact MEX1 format/CRC/length/relocation validation and malformed/wrap negatives pass.
4. Relocatable image load, BSS zeroing, relocation, and failure rollback are atomic.
5. ARG1/ENV1/bootstrap allocation and initial user context satisfy the exact ABI.
6. Spawn/exec/exit/wait/zombie/reap and PID reuse/generation behavior satisfy REV12.
7. Kill/cancellation of runnable and blocked children obeys authorization and safe
   interruption semantics without corrupting scheduler/context state.
8. Canonical IY and OS-private alternate-register invariants remain intact.
9. Repeated process lifecycle stress returns allocator/process accounting to the exact
   required baseline and deliberate leak injection is rejected.
10. The same MEX1 executes correctly through the real spawn path at two distinct
    allocator bases.
11. P2.24 acceptance passes with all rollback negatives green.
12. Required durable Phase-2 aggregate evidence is present, hash-consistent, and
    passes its active validator and negative/corruption suite.
13. Phase-0 and Phase-1 active validators still pass and their durable evidence has not
    been improperly rewritten by Phase-2 activation.
14. Project-policy and license-header gates pass on the final repository state.
15. Quality/CI succeeds on the final activated Phase-2 `main` state.
16. No unexpected generated residue, diagnostic-only artifact, or unreviewed source is
    committed.
17. No Phase-3 implementation path has been started or modified under this goal.
18. Current scratch coordination accurately describes the closed Phase-2 state.

Only then may Phase 2 be called frozen and complete and a Phase-3 goal be opened.

## 10. Blocker instrumentation rules

When blocked:

1. Capture exact `main`, source, run, job, attempt, and evidence identities first.
2. Capture failing command, exit code, stdout/stderr, timeout state, and named assertion.
3. Compare expected versus actual architecture/toolchain/source/prerequisite/evidence
   identity before editing implementation.
4. For MEX1 failures, dump every decoded header field, widened intermediate arithmetic,
   expected/actual CRC, stream length, relocation offsets/words, and rejection stage.
5. For allocation/rollback failures, record allocator map/accounting before attempt,
   provisional allocations, rollback order, and final accounting.
6. For lifecycle failures, record process table entries, PID generations, parent/child
   links, state transitions, wait target/status, owned allocations, and scheduler state.
7. For context/cancellation failures, record saved/restored registers, IY, alternate
   bank expectations, block/wake reason, cancellation-pending state, and safe-boundary
   observation.
8. Improve reusable diagnostics when the existing evidence cannot distinguish likely
   causes. Re-run diagnostics before proposing a source repair.
9. Never weaken a negative test, rollback assertion, source binding, or evidence
   validator to make a failure disappear.
10. Any byte change after SoP scanning resets the scan count to zero.

## 11. Session continuity and context-limit handoff

Repository state is primary. A chat-local summary is never authority.

When the conversation approaches its usable context limit, stop beginning new
substantive work, secure the safest durable repository checkpoint possible, and emit a
self-contained Markdown handoff for the next chat. The handoff should include current
`main`, selected P2 checkpoint, last completed P2 step, current candidate/source/evidence
identities, relevant workflow IDs, blockers/diagnostics, and the exact next action.

A new session must still execute Section 3 before resuming.

## 12. Stop condition

Stop this goal immediately after Section 9 closes. Do not use successful Phase-2
certification as implicit authorization to begin Phase 3.
