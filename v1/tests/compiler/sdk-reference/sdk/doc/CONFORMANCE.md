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
# C48 SDK Pre-1.0 Conformance Record

## Authorities

- `C48 Language Specification Rev 0.11.docx`
- `ZX-UX C48 Compiler User Manual Rev 0.11.docx`
- ZX-UX Architecture REV11 where host-visible runtime behavior is already frozen.

The language specification remains authoritative over this SDK.  This SDK does not
replace the future native `cc.asm`, OBJ1 backend, linker/runtime library or P11.41
built-in header freeze.

## Automated corpus

The release suite is discovered from `compiler/tests/test_*.py`.  It covers the
required Rev 0.11 Sections 86-94 families and additional host/runtime regressions.

Coverage includes:

- lexical positive/negative corpus, malformed numeric tokens, unsupported keywords,
  operators, type spellings, escapes, control bytes and exact source positions;
- deterministic integer wrap, signed division/remainder, INT_MIN/-1, 8/16-bit shifts,
  signed/unsigned comparison boundaries;
- left-to-right expression/argument evaluation and immediate value capture,
  short-circuiting and unevaluated `sizeof`;
- pointer scaling, one-past rules, subtraction, equality, `void *`, array decay,
  pointer returns, arrays of pointers, stale-pointer host traps and string immutability;
- file/block declarations, exact type identity, linkage, prototypes, `main`, recursion,
  nested scope, six-argument calls and control-flow statements;
- scalar/array/string/pointer initializers, inferred bounds, partial zero-fill, global
  address constants including prior-extern/later-definition ordering;
- object-like preprocessing, visibility, comments, macro dependency/redefinition,
  include nesting/case/name behavior and built-in-header collision rules;
- Float5 golden representations, range/domain behavior, conversion and operation-boundary
  quantization, with the Section-94 ROM-oracle limitation documented separately;
- exact hashes/shape for both selectable F4X8 assets, Tasword-default and `--font` override behavior, native Spectrum screen interleave, tty64 nibble sharing,
  graphics origin/OVER/INVERSE behavior, attributes and UDGs;
- C48B1 deterministic serialization, integrity, canonical JSON/schema rejection,
  transactional output and stale-temp ownership;
- command-line compilation/execution, argv limits/immutability, heap ceiling, bounded
  libc-like memory/string behavior and GUI key mapping;
- adversarial source nesting, macro-expansion, source-size and line-size limits with no
  Python traceback leakage;
- hostile C48B1 size/nesting/schema-type rejection before malformed data reaches the VM;
- deterministic VM call-depth/step limits, one-past/UAF/free misuse, stale-pointer ABA
  reuse, and raw pointer-byte forgery defenses;
- on-screen C48 security fixtures and the <=64-character source-line contract for every
  shipped `dev/src` C48 C/header artifact.

## Static/source review

Before each snapshot freeze the complete Python source tree is parsed/byte-compiled; unresolved
development markers and broad exception paths are reviewed; output transactions and
filesystem effects are inspected; and the complete automated corpus is rerun after every
source repair.

Broad exception handling remaining in `gui.py` is intentional at two host boundaries:
Tkinter import failure is translated to a host runtime error, while the VM worker thread
captures `BaseException` solely to marshal it back to the GUI/main thread rather than
silently losing it.

## Release clean-room gate

A release is accepted only after:

1. the canonical tree is cleaned of caches/coverage/transient outputs;
2. deterministic demo executables and expected screen hashes are regenerated;
3. three separate fresh filesystem copies independently pass static checks, the full
   automated suite, deterministic demo rebuild comparison and demo execution;
4. the release ZIP is created from the frozen canonical bytes;
5. the ZIP is extracted into a fourth virgin directory and the same verification is run
   from the extracted package.

The frozen automated-test count is recorded in `RELEASE-NOTES.md`; deterministic demo
hashes are recorded in `DEMO-HASHES.md`; security fixture binaries are rebuilt during
release verification; every release file is covered by `MANIFEST.sha256`. The ZIP
SHA-256 is reported with the delivered archive because a ZIP cannot contain a
non-circular hash of itself.

## Explicit non-claims

The pre-1.0 SDK does not certify native Z80 code generation, OBJ1/MEX1, C48_REGCALL register/stack
placement, native allocator fragmentation, ZX-UX scheduler/syscalls/cassette behavior,
P11.41 exact `<c48.h>` prototypes, host multi-object linking, the native default
512-byte stack budget/register frame layout, or complete three-way Section-94
ROM/native/host Float5 differential equivalence.  See `HOST-DIVERGENCES.md` and `FLOAT5-ORACLE.md`.
