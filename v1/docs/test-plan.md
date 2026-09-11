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

This plan defines the deterministic host-side test contract used from E0.03 onward.
Revision 11 remains the architecture authority.

## Root and tool resolution

The project root is the nearest ancestor whose regular file `.zxux-root` contains
exactly `ZX-UX project root`. Build and test programs resolve every project-owned
tool from that root and pass the resulting absolute path to the operating system.
Ambient `PATH` lookup is not a valid way to select the canonical assembler,
emulator, cassette utilities, ROM, or Python interpreter.

The canonical host interpreter entry is:

`tools/runtime/python/bin/python`

The canonical host test driver is:

`v1/tools-host/test-driver/run.py`

All subprocess arguments are represented as argument lists. Shell-flattened command
strings are not used for emulator or certification execution.

## Driver interface

A registered implementation step has two standard entry points:

`<project-local-python> v1/tools-host/test-driver/run.py build --step <STEP-ID>`

`<project-local-python> v1/tools-host/test-driver/run.py test --step <STEP-ID>`

Every subprocess has a finite timeout. A timeout is a test failure unless the test
is specifically proving timeout enforcement. Captured stdout and stderr are retained
in machine-readable evidence together with the exact argument vector and exit code.

## E0.03 driver acceptance

E0.03 requires all of the following:

1. the exact root marker is found without a drive-letter or user-profile assumption;
2. the project-local Python entry exists and is invoked by absolute path;
3. arguments containing spaces and wildcard characters arrive unchanged;
4. a deliberately sleeping child is terminated by the hard timeout;
5. a copied driver under a different temporary root resolves that new root;
6. driver, plan, environment verifier, and toolchain manifest hashes are recorded;
7. the pinned FUSE program is invoked as an argument list when emulator probing is used.

The relocation test is a negative portability test: success depends on the copied
root marker, not on the original checkout path.

## Evidence record

The driver writes deterministic JSON records below:

`v1/dist/certification/<STEP-ID>.<action>.json`

Each record contains at least:

- schema version;
- step identifier and action;
- PASS or FAIL status;
- subprocess argument vectors;
- working directory;
- exit code or timeout state;
- elapsed milliseconds;
- captured stdout and stderr;
- hashes for relevant inputs;
- named assertions and their results.

Step-specific certification logs may additionally be written as
`v1/dist/certification/<STEP-ID>.log`. Release and phase gates may aggregate these
records, but must not discard the underlying step evidence.

## Emulator evidence hierarchy

Target behavior uses the four-level hierarchy required by Revision 11.

First, static checks cover symbol uniqueness, section bounds, fixed kernel ranges,
IM2 layout, stack placement, arena bounds, syscall declaration ownership, statically
detectable reserved-register misuse, and object-format sizes.

Second, deterministic emulator tests use SNA for the fast inner loop and TAP or TZX
when boot or cassette semantics matter. Tests assert registers, RAM, process state,
object state, or format bytes directly. Screenshot comparison is supplemental only.
Synthetic programs that call ROM routines establish a known writable stack first.

Third, release-critical emulator behavior is repeated on a second independent
Spectrum emulator where practical.

Fourth, claims about physical cassette robustness require real compatible hardware
with an audio path, or a hardware-faithful EAR/MIC loop. Emulator tape traps and
container parsing do not satisfy that hardware claim.

## Timeout and process discipline

Host tests never assume a child exits merely because it should. Every emulator,
assembler, linker, cassette utility, and helper process has a hard timeout. On
timeout, the driver records the condition and treats it as failure. Tests must not
leave background emulator processes behind.

## Determinism rules

Identical source inputs, pinned host-tool inputs, and fixed command options must
produce identical binary artifacts. Every certification boundary records hashes.
Tests that use time, random input, or generated temporary names either supply a fixed
seed/input or exclude the nondeterministic host metadata from binary acceptance.

The Z80 refresh register may not be a correctness, identity, uniqueness, or security
oracle. Precise ULA contention phase may not be a correctness dependency.

## Step completion

A normal implementation step is complete only after:

1. the intended files exist at their architecture-defined paths;
2. the project-local build succeeds;
3. static checks pass;
4. required SNA, TAP, TZX, or host tests pass;
5. the required negative test fails for the intended reason;
6. certification evidence required by that step is retained;
7. the exact proposed bytes complete three successive defect-free scans;
8. the license-header and project-policy gates pass;
9. the adversarial review reports only BLOCKER or MAJOR findings and the author
   resolves, clarifies, or overrides each finding;
10. the exact reviewed bytes are checked directly into `main`;
11. the automated Linux validation result is retained.

Any byte change after a clean scan resets the scan count.

## E0 handoff note

The original frozen aggregate wrapper bytes were absent from the repository at the
start of this implementation. The owner directed implementation to acquire the
artifacts. The reconstructed lock records that override explicitly and pins the
available upstream sources and canonical ROM by version, size, URL, and SHA-256.
No historical PASS is inferred from that reconstruction.

## Phase boundary rule

A phase aggregate may pass only when every numbered step in that phase has passing
evidence and the phase-specific integration tests pass. A later phase does not
retroactively waive an earlier failed assertion.

Implementation is authorized through Phase 10. Phase 11 is not admitted until the
project owner explicitly approves the compiler phase.
