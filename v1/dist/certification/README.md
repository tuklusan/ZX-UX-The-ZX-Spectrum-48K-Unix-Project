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

`v1/dist/certification` is durable release evidence, not disposable build output.

A numbered implementation step uses its exact step identifier in evidence names.
The deterministic test driver writes `<STEP-ID>.build.json` and
`<STEP-ID>.test.json` when those actions run. A certification-boundary step also
retains `<STEP-ID>.log` and, where required by its contract, a compact final result
record. Phase aggregates use `phase-<N>.json`.

## Required machine-readable fields

Every driver evidence record has:

- `schema`;
- `step`;
- `action`;
- `status`;
- `commands`;
- `hashes`;
- `assertions`.

Each command record has its argument vector, working directory, exit code or timeout
state, elapsed duration, stdout, and stderr. Hash maps use root-relative project
paths. Assertion records use stable names and an explicit Boolean `passed` value.

A final certification result additionally records the exact source/check-in identity
being certified, the toolchain-lock hash, architecture hash, and all prerequisite
step results.

## Acceptance rule

A PASS marker is meaningful only when all required fields are present, all required
hashes have 64 lower-case hexadecimal digits, command failures are absent except in
named negative tests, and every required assertion passed. A missing field is a hard
failure rather than an implied default.

Evidence produced from a dirty proposed change cannot close a step. The check-in
must contain the exact bytes that completed the three clean scans and adversarial
review.

## Negative-test rule

Negative tests retain enough evidence to prove that rejection happened for the
intended reason. Merely receiving a nonzero process status is insufficient when a
more specific assertion can be made.

## Build directory distinction

`v1/build` is disposable. Files below this certification directory and release
artifacts below `v1/dist` are retained unless the implementation plan explicitly
marks them temporary.
