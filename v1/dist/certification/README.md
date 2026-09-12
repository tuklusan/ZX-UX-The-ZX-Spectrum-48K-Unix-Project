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

# Certification Evidence

`v1/dist/certification` is the durable, checked-in certification record. GitHub
Actions artifacts and scratch directories are diagnostics or transport only and do
not substitute for committed evidence.

The canonical naming convention is exact: every numbered E0 and Phase-0 step has
`<STEP-ID>.build.json` and `<STEP-ID>.test.json`. E0.04 and P0.34 are explicit
certification-result boundaries and additionally require `<STEP-ID>.result.json`.
Phase aggregates are named `phase-<N>.json`; Phase 0 therefore closes with
`phase-0.json`. A human-readable `.log` exists only when a step explicitly requires
a transcript not already preserved by JSON command records. A `.log` is not
universal evidence.

## Required machine-readable fields

Every durable build, test, and result record uses evidence schema 2 and records:

- `schema`;
- exact `step` and `action`;
- `status`;
- exact certified `source_commit`;
- `toolchain_lock_sha256`;
- `architecture_sha256`;
- Boolean `worktree_clean`;
- prerequisite step statuses;
- command records;
- stable root-relative artifact hashes;
- named assertions.

Each command record contains its argument vector, working directory, exit code or
timeout state, elapsed duration, stdout, and stderr. Each assertion has a stable name
and explicit Boolean `passed` value. A result record additionally carries its exact
step-specific `pass_marker`.

## Clean-source rule

Certification executes an already-committed source check-in from a clean worktree.
The deterministic driver verifies cleanliness before each numbered step and writes
scratch evidence to a directory outside the source worktree. Generated evidence must
not make later clean-worktree checks false.

After a complete clean-source certification run passes, the staged records are copied
unchanged into `v1/dist/certification` and committed in a subsequent evidence-only
check-in. The durable records continue to name the earlier source check-in in
`source_commit`; an evidence check-in never pretends to certify its own hash.

## Acceptance rule

A PASS record is valid only when all required fields are present, all required hashes
are 64 lower-case hexadecimal digits, `source_commit` is an exact 40-digit commit
identity, `worktree_clean` is true, all prerequisites required by the plan are PASS,
all required commands have acceptable outcomes, and every required assertion passes.
A missing field or prerequisite is a hard failure, never an implied default.

Negative tests retain enough command and assertion data to prove rejection occurred
for the intended reason. A nonzero exit status by itself is not sufficient when the
contract can assert a more specific failure.

## Durable versus disposable output

`v1/build` and external certification staging directories are disposable. Files under
`v1/dist/certification` are durable once admitted by the evidence validator. Removing,
rewriting, or replacing required durable Phase-0 evidence after Phase-0 activation is
a certification failure, not cleanup.
