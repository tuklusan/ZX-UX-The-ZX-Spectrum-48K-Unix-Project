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

# C48 SDK Provenance and Phase-11 Conformance Map

Pinned Phase-11 design/reference SDK commit:
`84d144de2721cda5075c3a6610a422663b5e2f77`

Pinned SDK tree:
`1c6b5bae84035ee853be9142b440792881c9ca9f`

Repository:
`tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit`

The SDK is read-only reference material. ZX-UX Architecture REV16 controls every
target behavior, ABI, format, resource limit and acceptance decision.

## Reviewed Python implementation surface

| SDK path | Git blob |
| --- | --- |
| `compiler/c48.py` | `ca11dc74b30fc4057cc5bf7572baee06a6461419` |
| `compiler/c48/compiler.py` | `8991d6fc7dbc99645e9e6e0f4cc5e1cf55e59929` |
| `compiler/c48/errors.py` | `42a40a2089daeef8e41493e5266d6ed3d76bc00e` |
| `compiler/c48/float5.py` | `7ee2ad594bd50957b13b3cd5da12459e7c4d233d` |
| `compiler/c48/format.py` | `d950e1ccf4556542e42487a182530e1698689f5a` |
| `compiler/c48/lexer.py` | `61051f0f74c8f023871c288b2dea7d9dd88cf780` |
| `compiler/c48/limits.py` | `1cb8a5d838d060ac4d40162718221788d081f5ce` |
| `compiler/c48/memory.py` | `67c7ae30eace8811a8285592f452b633d2eea449` |
| `compiler/c48/parser.py` | `2bbcde0a225b6f64cb850115d85a8f69f0b0989f` |
| `compiler/c48/preprocessor.py` | `ca9cf2f42b2a08949066361b405fee9f9b2bd043` |
| `compiler/c48/semantics.py` | `a388bfd562f443b0037fe67b1c3ed2c2ffa76084` |
| `compiler/c48/typesys.py` | `f5ef83c2d2a9a21c0d5a0ec055af2b75656cb888` |
| `compiler/c48/vm.py` | `0a1a5ca969c31db79094bc22df1cb13dad4d807e` |
| `compiler/run_tests.py` | `a77b6200d79885ca09c2791e6651935ff7dceb34` |
| `compiler/verify_release.py` | `1d60ee1900279cc14f695fba50ad03fd080509c4` |
| `compiler/release_expectations.json` | `ce0f282d5fbb9161c253508b6e7de6899f7374e1` |
| `compiler/tests/test_conformance.py` | `a9ef28270a5b5ef57d95879bc5a660efe1636fb3` |
| `compiler/tests/test_game_regressions.py` | `e0324ef27022f68e44c0d1cb772f570942b35c02` |
| `compiler/tests/test_release_regressions.py` | `4fb550dbf5bac42839f1ad794d4f89f3f2e4483e` |
| `compiler/tests/test_security.py` | `62c217d7f9369b565fe52f6e3993c82a7e8b5914` |
| `doc/CONFORMANCE.md` | `7b126eeeb06dae297ff92cee52e24c42b16778f0` |

The end-to-end comparison covered preprocessing, lexical rules, parsing, types,
semantic checks, initializers, evaluation order, integer behavior, pointer
behavior, Float5 storage/arithmetic boundaries, resource limits, diagnostics,
memory/runtime behavior, deterministic host format, test corpus, and release
verification.

## DOCX review

`docs/04-C48 Language Specification Rev 0.11.docx` was reviewed end-to-end
against REV16 Section 25 and the pinned SDK implementation above. The P11.01
qualification mechanically inspects the checked-in DOCX container and records
its SHA-256 together with the working contract. No P11.01 correction is required
unless that mechanical review or the three-way comparison finds a concrete
omission, contradiction, ambiguity, or stale language rule.

## Recorded differences and resolutions

1. The SDK emits deterministic C48B1 host executables. Native ZX-UX `cc` must
   emit OBJ1 Z80 code. Resolution: REV16/native OBJ1 rules control.
2. The SDK VM supplies host execution and host memory safety machinery. Native
   ZX-UX execution uses MEX1, C48_REGCALL, kernel syscalls and the 48K arena.
   Resolution: host mechanics are reference oracles only.
3. The SDK conformance record explicitly does not certify native
   C48_REGCALL placement, IY preservation, alternate-register ownership,
   native allocator layout, target cassette/syscall behavior, or native stack
   layout. Resolution: later P11 target steps prove those contracts directly.
4. The SDK's built-in/host header profile is not the final native `<c48.h>`.
   Resolution: P11.41 freezes the native header from REV16 requirements.
5. REV16 separately pins SDK commit
   `9ca3c6d6b5dd4b6e2351c1800afbd47d1d77e411` for the bounded H06
   `hello.c` canary. That later H06 identity does not silently re-baseline
   this P11.01 language-reference commit.
6. Float5 host behavior is a useful oracle but does not replace ROM-backed
   target differential proof. Resolution: target ROM-calculator steps govern.

No unresolved REV16/DOCX/SDK discrepancy is admitted by P11.01. Any newly found
difference becomes an explicit blocking record before dependent native behavior
is accepted.
