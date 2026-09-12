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

# ZX-UX Baseline Repair and Reconciliation Plan

Status: CLOSED-COMPLETE
Revision: 01
Starting implementation baseline: `d464c59ac9bf8d3f82cf109c6d4266ad4f4ba64a`
Canonical implementation plan: `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md`
Canonical architecture: `docs/01-ZX-UX-ARCHITECTURE-REV11.md`

---

## 1. Purpose

This plan freezes the finite repair-and-reconciliation work required before normal
implementation resumes. It is not a new architecture phase and it does not authorize
new Phase-1 or later feature work.

The repository is treated as a Linux-from-scratch implementation. Legacy transfer-era
assumptions, historical-host prerequisites, and provenance rules that are not required
to reproduce the current Linux toolchain are removed from the canonical process.

The exit condition is a clean `main` on which the implementation plan, environment
bootstrap, deterministic test driver, durable certification evidence, and CI enforcement
all describe and verify the same process without exceptions or owner overrides.

---

## 2. R&R-01 - Canonicalize the environment foundation

1. Remove legacy transfer-era wording and assumptions from
   `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md` and related foundation metadata.
2. Make Linux-from-scratch bootstrap the canonical E0 model.
3. E0.01 must explicitly distinguish bootstrap tooling from the certified project-local
   runtime:
   - a CI-selected Python 3.13.15 may run metadata validation and the bootstrap helper;
   - bootstrap acquisition uses only pinned HTTPS URLs, exact sizes, and SHA-256 values
     from `tools/manifest/toolchain.lock.json`;
   - native build prerequisites are explicitly installed by the Linux runner and are not
     silently discovered project dependencies;
   - acquired/built project tools live under `tools/runtime/`;
   - final environment certification runs with
     `tools/runtime/python/bin/python tools/scripts/verify-environment.py`;
   - the final certified tool executions use project-local absolute/root-relative paths,
     not ambient PATH lookup.
4. Replace provenance-only lock fields with canonical Linux bootstrap metadata. The
   manifest itself becomes the authoritative pinned environment specification.
5. Normalize the architecture identity everywhere to the canonical repository path and
   the current frozen SHA-256 verified by `tools/scripts/verify-environment.py`.
6. Retain the E0.01 negative test that mutates a temporary manifest copy and requires a
   deterministic failure.
7. Retain E0.02 as the architecture identity gate and make its command/path/hash language
   exactly match the canonical architecture file.

Exit gate: a fresh Linux runner can bootstrap and certify E0 without an interactive
exception, historical-host dependency, fixed drive letter, fixed user profile, or
pre-existing project-local runtime.

---

## 3. R&R-02 - Reconcile the certification contract

1. `v1/dist/certification` is the durable, checked-in certification record.
2. GitHub Actions artifacts are supplementary diagnostics and temporary transport only;
   they never substitute for committed certification evidence.
3. Every numbered E0 and Phase-0 step must have, at minimum:
   - `<STEP-ID>.build.json`;
   - `<STEP-ID>.test.json`.
4. A step that is explicitly defined as a certification boundary additionally receives
   `<STEP-ID>.result.json` when the implementation plan requires a final result record.
5. Phase aggregates are named `phase-<N>.json`; Phase 0 therefore closes with
   `phase-0.json`.
6. A human-readable `.log` is required only when a step explicitly needs a transcript
   that is not already preserved in the JSON command records. It is not a universal
   per-step requirement.
7. The implementation plan, `v1/dist/certification/README.md`, the evidence validator,
   and the deterministic test driver must use the same filenames, required fields, and
   acceptance rules.
8. Every durable build/test/result record must identify the certified `source_commit`,
   toolchain-lock SHA-256, architecture SHA-256, clean-worktree state, and prerequisite
   status in addition to stable root-relative artifact hashes and enough command/assertion
   data to reproduce why the step passed or failed.

Exit gate: the repository contains no contradiction between documented evidence rules,
validator rules, driver output, and CI retention behavior.

---

## 4. R&R-03 - Make clean-source certification non-self-referential

1. Implementation/source corrections are committed first.
2. The exact committed source check-in is then re-tested from a clean checkout/worktree.
3. During certification, generated evidence is written to an external staging directory or
   equivalent location outside the source worktree so one step's output cannot make later
   clean-worktree assertions false.
4. Each step verifies the source worktree is clean before executing and records that state.
5. Evidence records identify that already-existing source check-in as `source_commit`.
6. Only after the complete clean-source certification run passes are staged records copied
   into `v1/dist/certification`.
7. The generated evidence is committed in a subsequent evidence-only check-in.
8. The evidence-only check-in does not change the source bytes being certified.
9. `worktree_clean: true` means the source checkout was clean when certification ran;
   it does not pretend that a check-in can contain its own hash.
10. Phase aggregate evidence names the certified source check-in and all required step
    records.

Exit gate: every committed final record can be validated without an impossible
self-reference or a dirty-source exception.

---

## 5. R&R-04 - Complete deterministic E0 and Phase-0 registration

1. Audit the canonical foundation range `E0.01` through `E0.06` and Phase-0 range
   `P0.01` through `P0.34`.
2. Every numbered E0 and Phase-0 step must be directly registered with the deterministic
   host driver. E0.01 and E0.02 may call the canonical environment/architecture verifier
   internally, but they must still be addressable through their exact step identifiers.
3. No generic fallback may silently claim support for an unregistered numbered step.
4. Each registered E0 and Phase-0 step must execute its plan-defined positive assertions
   and its intended negative/failure test.
5. Existing grouped implementations may share helper modules, but each numbered step must
   emit evidence under its own exact step identifier.
6. P0.34 must aggregate and verify all E0 and Phase-0 prerequisites and produce the
   Phase-0 acceptance record rather than relying on prose or commit history.

Exit gate: invoking build and test for every `E0.01` through `E0.06` and `P0.01` through
`P0.34` succeeds on the certified baseline, and any unknown E0 or Phase-0 step is rejected
deterministically.

---

## 6. R&R-05 - Enforce the repaired baseline in CI

1. Add a deterministic completeness validator for committed certification evidence.
2. CI must fail Phase-0 closure when any required E0/P0 evidence file is missing,
   malformed, references the wrong certified source check-in, contains a failed required
   assertion, or has an invalid prerequisite chain.
3. The completeness requirement activates monotonically when `phase-0.json` first appears:
   - before that first aggregate exists, CI may run regenerated scratch evidence while R&R
     is still constructing the durable baseline;
   - the completeness job must inspect the complete reachable `main` ancestry, using a
     full-history checkout or equivalent, to determine whether `phase-0.json` has ever
     existed in the current branch history;
   - once any ancestor contains `phase-0.json`, every descendant requires the complete
     durable evidence set; removing the aggregate or required records is a hard failure and
     cannot be laundered through a later commit.
4. CI regeneration of scratch evidence may continue for diagnostics, but regenerated
   scratch output must not mask missing durable repository evidence after activation.
5. Documentation-only pushes must not launch GitHub Actions CI workflows. Workflow path
   filters must exclude canonical non-executable documentation paths; a change that also
   modifies executable policy, verifier, source, workflow, or certification evidence is
   not documentation-only and continues to trigger the relevant gates.
6. CI must verify that the implementation plan and certification README agree on the
   evidence naming convention.
7. Existing exact kernel-size, project-policy, license-header, and Phase-1 certification
   gates remain intact; this R&R effort must not weaken them.

Exit gate: the enforcement code is present before the final source freeze, and after
activation deleting or corrupting any required durable Phase-0 record causes a predictable
CI failure for the intended reason.

---

## 7. R&R-06 - Re-certify E0 and Phase 0 into durable evidence

1. Freeze the final non-evidence R&R source check-in after R&R-01 through R&R-05 pass.
2. Bootstrap the pinned Linux environment from a clean checkout of that source check-in.
3. Execute and retain E0.01 through E0.06 evidence using the reconciled evidence rules.
4. Execute and retain `P0.01` through `P0.34` build/test evidence.
5. Generate and validate all required step result records.
6. Generate and validate `phase-0.json` against the same source check-in; the aggregate
   must cover all required `E0.01` through `E0.06` and `P0.01` through `P0.34` records.
7. Commit only the generated certification evidence in the evidence-only check-in. The
   first committed `phase-0.json` activates the monotonic CI completeness requirement.
8. Re-run repository policy, license-header policy, project CI, environment certification,
   and the complete Phase-0 acceptance gate on the resulting `main`.

Exit gate: `v1/dist/certification` contains durable validated evidence for every E0 and
Phase-0 step required by the canonical plan, including `phase-0.json`.

---

## 8. R&R-07 - Final contradiction and cleanliness audit

Before normal implementation resumes:

1. Search every tracked text artifact for obsolete transfer-era assumptions and vocabulary;
   remove all remaining occurrences from the repository-wide canonical record.
2. Verify the canonical architecture path/hash is identical in the plan, verifier, and
   evidence records.
3. Verify E0.01 can start from a clean Linux checkout with no `tools/runtime` directory.
4. Verify final E0 certification uses the project-local runtime.
5. Verify every `E0.01` through `E0.06` and `P0.01` through `P0.34` build/test invocation
   is registered and PASS.
6. Verify all required E0/P0 evidence is committed under `v1/dist/certification`.
7. Verify `phase-0.json` is valid and closes the same certified source check-in.
8. Run project policy, license headers, Quality/CI, kernel build where applicable, and all
   certification workflows to green.
9. Confirm `main` points at the intended R&R evidence check-in and contains no uncommitted
   or generated residue.

R&R is complete only when all nine checks pass. Until then, normal Phase-1 continuation
is paused.

---

## 9. Non-goals and invariants

- Do not change Revision-11 architecture semantics during R&R.
- Do not weaken the exact 8192-byte kernel requirement or the fixed 48K memory map.
- Do not treat historical successful check-ins as substitutes for regenerated evidence.
- Do not fabricate evidence for a step that the current deterministic runner cannot
  execute; register and test the step first.
- Do not modify any GitHub repository other than the canonical ZX-UX repository.
- Do not begin new Phase-1 or later implementation work until R&R-07 closes green.

---

## 10. Mandatory SoP three-scan delivery gate

Every R&R change follows the repository's standard zero-defect delivery rule without
shortcut or substitution:

1. Start from the latest fresh disk copy of every file in the proposed change and scan it
   manually, line by line, from first line through last line.
2. Fix every gap or defect found during that scan.
3. Any byte change invalidates the scan count and requires a fresh scan from the first line.
4. Delivery is permitted only after three successive complete manual line-by-line scans of
   identical proposed bytes each find zero new gaps or defects.
5. License, project-policy, and adversarial-review gates run only after the third qualifying
   zero-defect scan; any later byte change resets the scan count to zero.

This rule applies to documentation, scripts, workflow files, evidence, assembly, host tools,
and every other text artifact changed during R&R.

---

## 11. R&R closure record

Final R&R source anchor: `66e12b2d641b2db93d0aae949d2aac2565193989`.
Durable Phase-0 evidence anchor: `268db8b3763f685488ffd4973859390e263db648`.

The final source anchor completed the following required workflow runs:

- Kernel Build run `34696500252`: success.
- Phase-0 Certification run `34696500274`: success.
- Phase-1 Certification run `34696500300`: success.
- Quality/CI run `34696500334`: cancelled after it was superseded by the immediate
  evidence-only activation commit.

The evidence-only anchor retained the exact certified source bytes and completed Quality/CI
run `34696692448` successfully. Its six jobs -- E0 metadata, project policy, Phase-0
evidence, license headers, E0 foundation, and project CI -- all succeeded.

The later `main` commit `0ad2113c7f22f62e479fafa2246338c9d6af6771` is a documentation-only
update to the deferred cursor/tty64 change request. It is outside the R&R source/evidence
anchors and is neither modified nor executed by this closure.

The exact Phase-1 resume checkpoint is:

- `P1.01` through `P1.12` are admitted.
- `P1.13` is unadmitted; its current work is commit
  `3245d489ad9b26c3ea55bcf0677374d2cfa5b53d`.
- The P1.13 IM2 fixture-initialization repair is committed.
- The retained failing certification assertion is
  `sys-ticks-snapshot-is-coherent-and-four-bytes`.
- `P1.14` has reconnaissance only and no admitted modification.

The R&R change corpus remains the finite baseline-to-source delta: 112 text files, three
binary assets, and two intentional deletions. This closure record changes no source,
evidence, deferred-CR, or Phase-1 implementation bytes. The deferred cursor/tty64 change
request remains queued after R&R closure, and Phase-1 remains parked at the checkpoint
above until that planned operation completes.
