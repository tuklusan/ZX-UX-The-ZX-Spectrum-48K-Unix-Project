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

## Pinned reference identity

REV08 names this exact read-only SDK baseline for Phase 11:

`84d144de2721cda5075c3a6610a422663b5e2f77`

Pinned SDK tree:

`1c6b5bae84035ee853be9142b440792881c9ca9f`

Repository:

`tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit`

The exact certification reference therefore already equals the REV08 baseline;
no SDK re-baseline is required. The SDK repository is reference/oracle material
and remains read-only. REV17 controls target language behavior, ABI, object
format, resource limits, runtime behavior, and acceptance.

The pinned SDK release expectations contain 205 tests. Those tests are not a
substitute for native ZX-UX proof; the complete required SDK corpus and support
material are imported byte-for-byte before native `cc` certification as
required by REV08.

## Reviewed Python implementation and support surface

| SDK path | Git blob at pinned commit |
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
| `doc/HOST-DIVERGENCES.md` | `d690357cc6bbd412092c8fe306862639d353ba54` |

The end-to-end review covered preprocessing, lexical rules and rejected
keywords, parsing, types, semantic checks, initializers, evaluation order,
integer behavior, pointer behavior, Float5 representation and operations,
bounded limits, diagnostics, memory/runtime behavior, deterministic host
format, the tests, release runner, release verifier, conformance notes, and
documented host/target divergences.

## DOCX review and correction

Project document:

`docs/04-C48 Language Specification Rev 0.11.docx`

Pre-P11.01 identity:

- Git blob: `5744e9f2c440b4ef11f7ffcd7dad7d218f3ba44d`
- SHA-256: `bc8dc2231fbc94b163d652116ce94e1e898d78b4a13773e28756330c78700d8f`

P11.01 corrected identity:

- Git blob: `a84c314a6d2957835efdc916a49e5289718140c2`
- SHA-256: `981eeb963d59e7ce2fd5e0fb73866f8a734fd33746a5ee0fce32d84fdec41903`

The DOCX was reviewed end-to-end against REV17 Section 25, REV08 P11.01, the
pinned SDK implementation, `doc/CONFORMANCE.md`, and
`doc/HOST-DIVERGENCES.md`. Its C48 language semantics were consistent with the
current authority, but its normative prose contained stale REV11/REV02 authority
references. P11.01 corrected those references to REV17/REV08 throughout the
Office XML package. No language feature was added, removed, or relaxed by that
correction.

The corrected DOCX was rendered through the project document QA path. All pages
containing changed authority text were visually inspected; all remaining pages
were pixel-identical to the pre-correction render. The license gate now pins the
corrected Git blob.

## Three-way language reconciliation

| Area | REV17 / corrected DOCX | Pinned SDK | Resolution |
| --- | --- | --- | --- |
| Core scalar types | char/short/int, unsigned forms, float, void | matching implemented subset | aligned |
| Plain char | unsigned | unsigned | aligned |
| Width/alignment | char 1/1, short 2/2, int 2/2, pointer 2/2, float 5/1 | compatible host semantic model | REV17 exact target layout controls |
| Unsupported long | unsupported | rejected | aligned |
| Statements | if/else, while, do/while, for, break, continue, return | matching implemented subset | aligned |
| Operators | fixed REV17 set | matching core set | REV17 fixed set controls |
| Deferred operators | compound assignment, `?:`, comma | absent/rejected as applicable | aligned |
| Deferred language | distinct double, long long, VLA, complex initializers, variadics, function pointers, switch/case, struct/union, complex macros, large-IR optimizer, full ISO | rejected/absent as applicable | aligned |
| Identifiers | case-sensitive, max 15 visible chars | max 15 | aligned |
| Preprocessor | object-like define, one-level local include, built-in c48.h | host reference implementation follows bounded subset | REV17 boundary controls |
| Integer shifts/division | low-bit count rules, signed arithmetic shift, truncation toward zero, dividend-sign remainder, divide-by-zero status 1 | semantic oracle covers the language behavior | REV17 target behavior controls |
| Float | five-byte Spectrum-native, runtime ROM calculator | Float5 host oracle | semantics cross-check; target mechanism proved later |
| Calling convention | C48_REGCALL, IY reserved, alternate bank private | host execution does not certify target ABI | intentional target-only requirement |
| Compiler output | native Z80 OBJ1 | deterministic host C48B1 | intentional format divergence |
| Execution | native ld/MEX1/ZX-UX runtime | Python host VM | SDK is oracle only |
| Compiler architecture | streaming, bounded, no large whole-program AST | host implementation informs behavior | REV17 native resource contract controls |
| Native c48.h | built into cc; final declarations owned by P11.41 | SDK host header/profile is reference-only | P11.41 owns target header |
| H06 canary | required later by P11.45/P11.48 | later pinned H06 SDK identity is separately specified | no P11.01 re-baseline |

## Intentional REV17-over-SDK differences

1. The SDK emits deterministic C48B1 host executables. Native ZX-UX `cc`
   emits OBJ1 containing Z80 code.
2. The SDK VM supplies host execution and host memory safety. Native execution
   uses the ZX-UX loader/linker/runtime, C48_REGCALL, syscalls, and the 48K arena.
3. SDK conformance does not certify native register placement, IY preservation,
   alternate-register ownership, native stack/allocator layout, target cassette
   behavior, or native multi-object linking. Those are proved by their owning
   Phase-11 steps.
4. The SDK host header is not the final native `<c48.h>`; P11.41 owns the
   target header.
5. Float5 host behavior is an oracle, not a replacement for target
   ROM-calculator differential proof.
6. Native resource/size/error gates are REV17/REV08 target contracts even where
   the host SDK uses different host limits or safety machinery.
7. REV17/REV08 separately require the bounded H06 `hello.c`/`exapi.h`
   canary at P11.45/P11.48. That later pin does not change this P11.01
   language-reference identity.

P11.01 has zero outstanding REV17/DOCX/SDK discrepancies. Any new discrepancy
found by a later step is blocking until that owning step records and proves its
resolution.
