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

# ZX-UX Version-1 Test Plan

This plan defines the deterministic host-side test contract. Revision 11 remains the architecture authority.

## Root and tool resolution

The project root is the nearest ancestor whose regular file `.zxux-root` contains exactly `ZX-UX project root`. Project-owned tools are resolved from that root. Ambient `PATH` is not a valid selector for the canonical assembler, emulator, cassette utilities, ROM, or final Python interpreter.

The canonical final host interpreter is `tools/runtime/python/bin/python`. The canonical host test driver is `v1/tools-host/test-driver/run.py`. Subprocesses use argument lists rather than shell-flattened command strings.

## Driver interface

Every registered E0 and Phase-0 step has the exact entry points:

`<project-local-python> v1/tools-host/test-driver/run.py build --step <STEP-ID>`

`<project-local-python> v1/tools-host/test-driver/run.py test --step <STEP-ID>`

Unknown numbered E0 or Phase-0 identifiers are rejected; there is no generic prefix fallback. Every subprocess has a finite timeout. Captured command, stdout, stderr, outcome, hashes, and named assertions are retained in machine-readable evidence.

## E0.03 driver acceptance

E0.03 requires all of the following:

1. the exact root marker is found without drive-letter or user-profile assumptions;
2. the project-local Python entry exists and is invoked by absolute path;
3. arguments containing spaces and wildcard characters arrive unchanged;
4. a deliberately sleeping child is terminated by the hard timeout;
5. a copied driver under a different temporary root resolves that new root;
6. driver, plan, environment verifier, and toolchain manifest hashes are recorded;
7. the pinned FUSE program is invoked as an argument list when emulator probing is used.

The relocation test depends only on the copied root marker, never the original checkout path.

## Evidence record

Certification starts from an already-committed clean source checkout. Build and test records are written first to an external staging directory, never into the source worktree. Every E0.01-E0.06 and P0.01-P0.34 step requires `<STEP-ID>.build.json` and `<STEP-ID>.test.json`. E0.04 and P0.34 additionally require `<STEP-ID>.result.json`; Phase 0 additionally requires `phase-0.json`.

Every schema-2 record includes exact `source_commit`, `toolchain_lock_sha256`, `architecture_sha256`, Boolean `worktree_clean`, prerequisite states, command data, stable root-relative hashes, and named assertions. Result records also include their exact PASS marker. A missing or malformed field, failed assertion, wrong source/digest, false clean-state claim, or missing prerequisite is a hard failure.

After the complete ordered certification passes, staged JSON bytes are copied unchanged into `v1/dist/certification/` in a separate evidence-only commit. Durable records continue to name the certified source commit. GitHub Actions artifacts are transport/diagnostics only and cannot replace committed evidence.

## Emulator evidence hierarchy

Static checks cover symbol uniqueness, section bounds, fixed kernel ranges, IM2 layout, stack placement, arena bounds, syscall declaration ownership, detectable reserved-register misuse, and object-format sizes.

Deterministic emulator tests use SNA for the fast inner loop and TAP/TZX when boot or cassette semantics matter. Tests assert registers, RAM, process state, object state, or format bytes directly; screenshots are supplemental. Synthetic programs that call ROM routines establish a known writable stack first.

Release-critical emulator behavior is repeated on a second independent Spectrum emulator where practical. Physical cassette robustness requires real compatible hardware with an audio path, or a hardware-faithful EAR/MIC loop; emulator tape traps and container parsing alone do not prove that claim.

## Timeout and process discipline

Every emulator, assembler, linker, cassette utility, and helper process has a hard timeout. Timeout is failure unless timeout enforcement itself is under test. Tests must not leave background processes behind.

## Determinism rules

Identical source inputs, pinned host-tool inputs, and fixed options must produce identical binary artifacts. Every certification boundary records hashes. Tests using time or random input use fixed seeds/inputs or exclude nondeterministic host metadata from binary acceptance.

The Z80 refresh register is never a correctness, identity, uniqueness, or security oracle. Precise ULA contention phase is not a correctness dependency.

## Step completion

A normal implementation step is complete only after the intended architecture-defined files exist; project-local build/static/positive/negative tests pass; required emulator or host tests pass; required evidence is retained; the exact proposed bytes complete three successive defect-free scans; license-header/project-policy/adversarial review gates pass; the reviewed bytes are checked into `main`; and the automated Linux result is retained. Any byte change after a clean scan resets the scan count.

## Phase boundary rule

A phase aggregate may pass only when every numbered step in that phase has passing evidence and the phase-specific integration tests pass. A later phase never retroactively waives an earlier failed assertion. Once Phase-0 durable evidence is activated on reachable `main`, deletion or rewriting of any required record is a certification failure.

Implementation is authorized through Phase 10. Phase 11 is not admitted until the project owner explicitly approves the compiler phase.
