<!--
============================================================================
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
============================================================================
-->
# ZX-UX C48 SDK Pre-1.0 Development Notes

Status: PRE-1.0 DEVELOPMENT SNAPSHOT

## Release purpose

Provide a portable Windows/Linux command-line C48 development environment for writing,
compiling and exercising C48 programs before the native ZX-UX Phase-11 compiler exists.

## Core components

- dedicated C48 Rev 0.11 lexer/preprocessor/parser/semantic analyzer;
- deterministic C48B1 host executable format;
- logical 16-bit C48 VM and pointer/lifetime checker;
- five-byte Float5 storage/core arithmetic implementation;
- exact 6912-byte Spectrum screen model;
- selectable F4X8 4x8 font resources with Tasword as the default and `c48run --font PATH` override;
- 64x24 tty rendering, Spectrum graphics/attributes and UDGs;
- portable Tk GUI plus headless screen-dump mode;
- Windows `.bat` and Linux shell command launchers;
- provisional host-game API header;
- specification-driven conformance/regression suite and deterministic demos;
- adversarial hostile-input/resource ceilings and C48B1 hardening;
- provenance-preserving stale-pointer/forgery defenses;
- visible C48 security fixtures and mechanically enforced 64-column C48 source.

## Frozen verification surface

- automated conformance/regression/security tests: 200;
- deterministic demos: 6 (`hello`, `colors`, `graphics`, `udg`, `maze`, `argv`);
- default Tasword F4X8 SHA-256: `90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`;
- alternate ZX-UX F4X8 SHA-256: `90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339` (currently byte-identical to the supplied Tasword asset);
- all release files except the manifest itself are covered by `MANIFEST.sha256`;
- demo source/C48B1/screen hashes are in `DEMO-HASHES.md`;
- eight runnable security C48B1 fixtures are deterministically rebuilt by the verifier,
  while `seckern.c` remains intentionally compile-negative.

Release acceptance requires three independent fresh-filesystem executions of
`compiler/verify_release.py` against identical frozen bytes, followed by creation of the
ZIP and one more verification from a virgin extraction of that ZIP.  The release is not
delivered unless those gates pass.

## Certification boundary

The release verifies the documented **host C48 conformance envelope**.  It does not
claim native Z80/OBJ1/MEX1/C48_REGCALL certification, P11.41's future exact `<c48.h>`,
an exact native 512-byte process-stack implementation, a host multi-object linker, or
complete Section-94 three-way ROM/native/host Float5 certification.  ROM-dependent
transcendentals remain disabled unless explicitly enabled as non-certified host
approximations.  See `CONFORMANCE.md`, `HOST-DIVERGENCES.md`, and `FLOAT5-ORACLE.md`.

The Tk display implementation is source-reviewed and its renderer/key mapping are
headlessly tested in this build environment; an actual Windows/Linux graphical desktop
was not available for an interactive Tk smoke test during package certification.
