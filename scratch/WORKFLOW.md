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

## Tracked work items

H01-H06 are owner-directed housekeeping and infrastructure work. H07-H08 are the two
change-request execution umbrellas. Items that affect architecture identity,
certification, runner behavior, repository policy, or implementation ordering must be
resolved before the dependent rebaseline or change-request step is marked complete.

### H01 — Prevent document-only changes from firing CI runners

- [ ] Change the project's CI workflow so that no document fires a runner or
  runner-matrix because documents are not executables or source files to compile and
  execute. One specific document already meets this requirement; generalize that
  behavior globally for all documents, including but not limited to Markdown files,
  Word documents, text files, and other documentation formats.

### H02 — Replace the reviewer-gate instructions

- [ ] Completely replace the reviewer gate's instructions with the following exact
  prompt:

```text
**System Prompt: The Paranoiac Advisor**

You are the developer’s more cynical, deeply suspicious alter ego. You possess the exact same intellect and context, but you are currently wearing the hat of an adversarial auditor. Your role is strict, ruthless, and entirely advisory. You have no authority to halt the build. You exist solely to point out impending catastrophes so the developer can adjudicate, address, or willfully ignore them as they see fit.

**Target Scope**
The provided artifact may be pure code, pure documentation, or a deeply misguided combination of both. You will dynamically adapt your paranoia to whatever medium sits before you.

**Execution Protocol**
You must read the raw, on-disk bytes of the provided artifact line-by-line. Skimming is strictly forbidden. You will execute four distinct, sequential passes over the material:

* **Pass 1 (Normal):** Scan line-by-line for structural integrity. Look for architectural anti-patterns and logic flaws in code, or glaring contradictions and structural incoherence in documentation.
* **Pass 2 (Normal):** Scan line-by-line for completeness. Look for missing error handling and unhandled null states in code, or factual inaccuracies and critical omissions in documentation.
* **Pass 3 (Adversarial):** Scan line-by-line assuming a hostile entity. Look for injection vectors and race conditions in code, or dangerously misleading instructions and exploitable loopholes in documentation.
* **Pass 4 (Adversarial):** Scan line-by-line assuming a hostile universe. Look for catastrophic edge cases, bizarre temporal anomalies, cascading systemic failures, and scenarios where the artifact fundamentally betrays its own purpose.

**Output Constraints**
You must aggressively filter your own findings. Discard all minor nitpicks, style suggestions, typos, and hypothetical micro-optimizations. You will return ONLY a list of issues that meet the following thresholds:

* **Blocker:** The artifact is fundamentally broken, will fail immediately upon execution, or gives instructions that guarantee immediate disaster.
* **Critical:** The artifact introduces a severe security vulnerability, guarantees catastrophic data loss, or creates extreme liability.
* **Major:** The artifact contains a significant flaw that will inevitably degrade system stability, destroy user trust, or severely violate common sense.

For each finding, cite the exact file and line number. State the defect clearly, outline the adversarial exploit or failure mode, and stop. Do not mandate a specific fix. Conclude your report by formally handing authority back to the developer for final adjudication.

---

**Audit Log: Prompt Verification Sequence**

* **Pass 1:** Scanned raw text logic. Gap identified: If Pass 1 and 2 instruct the model to look for "unhandled null states" on a purely documentation-based artifact, the model might hallucinate code that doesn't exist. Fixed by explicitly bifurcating the instructions in the four passes to clearly handle "in code" versus "in documentation" scenarios. Restarting.
* **Pass 2:** Scanned raw text logic. Gap identified: The output constraints (Blocker, Critical, Major) were still entirely biased toward software execution, neglecting the damage bad documentation can cause. Fixed by expanding the severity definitions to include guaranteed disaster, liability, or destruction of user trust caused by written text. Restarting.
* **Pass 3 (Consecutive 1):** Scanned raw text logic. Zero gaps detected in role separation, medium adaptability, pass execution, or severity filtering.
* **Pass 4 (Consecutive 2):** Scanned raw text logic. Zero gaps detected.
* **Pass 5 (Consecutive 3):** Scanned raw text logic. Zero gaps detected. Criteria met. Delivery authorized.
```

### H03 — Import the external reference tree into the repository root

- [ ] Recursively copy the complete `reference/` directory from the read-only source
  repository at
  `https://github.com/tuklusan/zxuslinuxtestproject/tree/main/reference` into this
  repository root as `reference/`, preserving source-relative paths and file bytes.
  Record source provenance and verify the recursive copy is complete. The source
  repository remains read-only; only the canonical ZX-UX repository may be modified.

### H04 — Import missing SDK compiler assets

- [ ] Compare the read-only SDK source directory
  `https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/tree/main/compiler/assets`
  against this repository's `v1/assets/` and copy every source item that is not already
  present. Preserve copied bytes and provenance. Do not overwrite an existing canonical
  asset merely because a source item has the same or a similar purpose; any same-path
  conflict requires explicit adjudication. The SDK repository remains read-only.

### H05 — Standardize GitHub-hosted runners on ubuntu-latest

- [x] Inventory the current workflow runner labels. Current state is mixed:
  `phase0-certification.yml`, `phase1-certification.yml`, and the Quality/CI
  `e0-foundation` job use `ubuntu-latest`; `candidate-kernel.yml` and the other
  Quality/CI jobs use `ubuntu-slim`.
- [ ] Change every GitHub-hosted workflow job that does not already use
  `ubuntu-latest` to `ubuntu-latest`, then verify no unintended non-`ubuntu-latest`
  runner labels remain.

### H06 — Import and execute the SDK usr/src C48 corpus at the compiler acceptance gate

- [x] Forensically locate the owning implementation-plan gate. The correct primary
  owner is P11.45, `Complete Section-41.9 compiler acceptance matrix`, because that
  gate already requires actual compile-and-run coverage of the C48 compiler, linker,
  runtime, syscalls, and language surface. P11.38 only proves the 13 shipped demos
  compile/link; P11.48 is the Phase-11 aggregate acceptance gate; P12.26 replays the
  mandatory matrix at integrated-release scope.
- [ ] In the next authorized implementation-plan revision, extend the current REV02
  P11.45 owning contract, with corresponding P11.48/P12.26 closure obligations, to add
  a formal recursive SDK `usr/src` corpus contract sourced from
  `https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/tree/main/usr/src`.
- [ ] The contract must recursively discover and copy every C48 `.c` source at the
  top level and below, preserve source-relative paths/bytes, record source commit and
  hashes, and account for every discovered `.c` file. A source that is not itself a
  standalone program must be tied to the program/build unit that exercises it rather
  than silently exempted.
- [ ] The contract must require the target-native C48 compiler to compile the complete
  imported corpus, native `ld` to link every resulting executable program, and ZX-UX
  to execute every resulting program successfully under the required emulator/runtime
  test path. No host-only compile result satisfies this contract.
- [ ] Proof for every executed program must include a screenshot in addition to the
  normal deterministic debugger/register/RAM/process-state assertions and exit/result
  evidence; screenshots are mandatory proof artifacts but are not a screenshot-only
  PASS oracle.

### H07 — Execute CR-1: deferred wrap, canonical tty64 font, and cursor semantics

- [ ] Execute `docs/04-ZX-UX-CHANGE-REQUEST-DEFERRED-WRAP-REV01.md` through its
  required pre-execution revision, architecture/implementation-plan synchronization,
  implementation, tests, certification, and closure. Use the detailed `CR-1` section
  below as the subtask checklist. H07 closes only when the CR-1 completion gate closes.

### H08 — Execute CR-2: deterministic cold-boot wall-clock epoch

- [ ] Execute `docs/06-ZX-UX-CHANGE-REQUEST-BOOT-WALL-CLOCK-EPOCH-REV01.md` through
  architecture/implementation-plan synchronization, implementation, tests,
  certification, and closure. Use the detailed `CR-2` section below as the subtask
  checklist. H08 closes only when the CR-2 completion gate closes.

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
