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

# ZX-UX Phase-11 Expanded Pre-Release Recovery Runbook REV02

**Status:** DRAFT — REVIEW REQUIRED — DO NOT EXECUTE  
**Scope:** post-Phase-11, pre-Phase-12 recovery of the failed expanded pre-release, including any product corrections strictly required to make ordinary ZX-UX C48 and native self-build behavior satisfy the already-frozen REV17/REV08/C48 contracts  
**Hard stop:** DO NOT START PHASE 12

## 1. Purpose

REV01 is FAILED-CLOSED because its acceptance machinery proved source identity,
native OBJ1/MEX1 mechanics, process launch, screen capture, and scheduler progress
without proving that the ordinary ZX-UX C48 compiler had compiled the actual SDK
program semantics.

REV02 exists to recover the real goal:

1. the SDK 1.0.2 example/demo files are ordinary legal C48 source files;
2. unmodified canonical SDK source bytes must load into ordinary ZX-UX and compile
   with the ordinary product cc command;
3. the resulting genuine OBJ1 must link with the ordinary product ld command;
4. the resulting executable must run through ordinary ZX-UX process execution;
5. the program must exhibit its actual source-defined behavior, not a source-bound
   canned substitute;
6. hanoi.c and queens8.c must be those same ordinary compiled executables when run
   concurrently;
7. the full kernel native rebuild must use ordinary user-visible native as/ld
   behavior, not a proof-only assembler/linker substitute;
8. no SDK-specific or pre-release-specific ZX-UX compiler patch, filename table,
   source hash table, source-length table, title table, canned code template, or
   alternate compiler path may be required.

The SDK corpus is acceptance material, not a whitelist and not an implementation
specification. The C48 language/ABI authorities remain REV17, REV08, the corrected
C48 language specification, and the existing ZX-UX C48 documentation. SDK 1.0.2 is
a pinned reference/oracle and a large real-world legal-C48 workload.

This runbook does not reopen P11.01-P11.48, move PHASE-11-COMPLETE, rewrite any
admitted evidence, or authorize Phase 12.

## 2. Revision lineage and failed-closed predecessor

The predecessor is:

scratch/ZX-UX-PHASE-11-PRE-RELEASE-RUNBOOK-REV01.md

REV01 remains historical and FAILED-CLOSED. Never edit its body to make the old
execution appear successful.

REV01 publication/media remain recoverable from Git history and may be retained as
failed pre-release evidence while REV02 is in progress. REV02 replaces the current
P11.pre-release bundle only after all REV02 gates pass.

REV02 must record, not erase, the exact reason REV01 failed.

## 3. Immutable baseline

The permanent Phase-11 completion checkpoint remains:

PHASE-11-COMPLETE =
263a203da3d54a398e8ac011284ae4195b1279c0

The following remain immutable historical material:

- P11.01-P11.48 admitted evidence and retained media;
- the Phase-11 aggregate certification record;
- historical P11.39 SDK import material;
- REV16/REV07 historical authorities;
- the PHASE-11-COMPLETE tag and tagged tree;
- all previously admitted P0-P11 evidence/media.

Post-tag current main may be corrected only prospectively and only through the
authority bridge in this runbook. Historical certification is never rewritten to
pretend the correction existed at PHASE-11-COMPLETE.

The fast-loader migration runbook remains CLOSED.

Every REV02 candidate must begin and end with zero Phase-12 state.

## 4. SDK pin

The SDK repository is READ-ONLY:

https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit

REV02 remains pinned to formal release 1.0.2 unless the acquisition gate is
explicitly revised before execution:

- tag: 1.0.2
- commit: b1621338565ac3bd9d4eff4ecb5a2a77aee2ab6a
- tree: ced96ea0a4b2f6cdd6080fc6f48e07738252af17
- release ZIP SHA-256:
  8efd465928048b050c0cff9d93ddaf13127eabb12b837a33aa1c2c44e913a98a
- GUI/reference-evidence ZIP SHA-256:
  ed9e2b2643481c3a58e46fdc054c3524fb7fe300827cb3e2c2b4c2833dd5ef01

The release source-tape manifest declares 57 tapes. REV02 scope is exactly the
same 30 example/demo programs: 6 examples and 24 demos. spriteanim.c keeps exact
SDK source bytes/path and the release-declared target alias sprani.c.

If a newer formal SDK release exists when REV02 is later opened for execution,
STOP and explicitly re-pin/review this runbook. Never consume moving SDK main.

## 5. Known REV01 defects that REV02 must prevent

The REV01 failure was not cosmetic. The following mechanisms are specifically
disallowed as acceptance substitutes:

1. EMIT_P11PR_CC_SDK_CORPUS_COMPILER identifies one of 30 sources by exact source
   length and CRC and emits a tiny fixed lifecycle body rather than compiling the
   source semantics.
2. The retained ordinary lifecycle binaries can therefore be genuine native
   OBJ1/MEX1 while still not be the compiled SDK programs.
3. cc_p11pr_sdk_compile_visual first identifies the source and then emits a
   program-specific title plus a small synthetic visual action. It does not compile
   the actual demo algorithm.
4. The 30 proof/visual PNG files are real target screen captures, but the target
   executables producing them are synthetic source-bound visual programs.
5. The reference PNG hash was recorded, but the REV01 gate did not require a
   meaningful program-specific visual comparison against actual source-defined
   behavior.
6. EMIT_P11PR_CC_SDK_MULTITASK_COMPILER identifies only hanoi.c/queens8.c and
   emits title + one plot + repeated SYS_YIELD. It does not compile recursive
   Hanoi or 8-Queens.
7. The REV01 multitasking gate required only process/yield evidence and at least
   one lit pixel in each screen half. That allows the title-only image that exposed
   the defect.
8. The REV01 kernel rebuild exercises real native assembler/linker routines, but
   the final acceptance path is a purpose-built proof fixture with a pinned proof
   allocator rather than the strongest user-visible ordinary as/ld command path.
9. REV01 closure predicates were therefore weaker than the prose requirements in
   Gates G/H/I.

REV02 must contain static and runtime gates that make all nine failure classes
impossible to pass.

## 6. Non-negotiable ordinary-product rule

For REV02, "native cc" means the same product compiler that an ordinary ZX-UX user
invokes. "native as" and "native ld" mean the same product tools an ordinary ZX-UX
user invokes.

The following are forbidden for satisfying any positive acceptance gate:

- source hash/CRC/length/name/path dispatch that selects code generation behavior;
- a table of the 30 SDK programs in executable compiler logic;
- source-specific hard-coded output code, graphics, titles, strings, or algorithm
  results;
- SDK-specific compiler entry points;
- pre-release-only compiler entry points;
- alternate .visual, .multitask, proof, or special executable builds;
- host-compiled C code;
- host-preconstructed OBJ1 or MEX1;
- prebuilt SDK C48B1 application images as native substitutes;
- direct host jump into application code;
- host-generated target screen bytes;
- proof SNA injection of the C source, OBJ1, MEX1, application, kernel rebuild
  output, or result screen under test;
- changing SDK C source/header bytes so they fit ZX-UX;
- a cc48.asm or other parallel compiler fork created solely for this pre-release.

A proof harness may boot/orchestrate Fuse, type keys, attach tapes, inspect target
RAM/registers, capture screen RAM, hash target-produced files, and enforce
checkpoints. It may not perform the work being proved.

Static provenance tables may contain SDK hashes and names. Executable compiler
behavior may not.

## 7. Generality rule: prove a compiler, not a memorizer

Passing the exact 30 canonical files is necessary but not sufficient.

Before the 30-program acceptance matrix can pass, REV02 must prove that ordinary
cc is source-semantic and not source-identity driven:

1. compile legal non-SDK C48 conformance programs covering the frozen language
   surface;
2. compile token-equivalent variants of selected SDK programs with changed
   whitespace/comments and require behaviorally equivalent results;
3. compile selected programs under an alternate valid source basename using the
   ordinary explicit-output form and require equivalent behavior;
4. compile selected legal semantic mutations and prove the output behavior changes
   in the expected way;
5. reject selected invalid C48 mutations transactionally;
6. statically scan the active product compiler path for the canonical 30 source
   hashes, CRCs, exact lengths, program-index tables, or program-name dispatch;
7. prove the compiler output is determined by parsed declarations/statements/
   expressions and the frozen ABI, not by a known-corpus identity.

Canonical release media still retain only the exact SDK source tapes. Mutated
sources are ephemeral anti-specialization tests and are never substituted for the
release inputs.

## 8. Authority bridge for prospective ZX-UX product correction

This is the bridge REV01 lacked.

REV02 execution must not begin product edits until this bridge is explicitly
admitted by project instructions and the runbook is changed from DRAFT to OPEN.

For each discovered failure of ordinary cc/as/ld/kernel/runtime behavior:

### 8.1 Existing-authority defect

If REV17/REV08/the corrected C48 spec already require the behavior, the failure is
a ZX-UX implementation defect.

Fix the current post-P11 main implementation through the normal workflow. Typical
eligible areas include:

- v1/src/tools/cc.asm and compiler support;
- ordinary as/ld code when the frozen native-tool contract is not met;
- current runtime/library support required by already-frozen C48 calls;
- kernel/process/object/tape behavior only when an existing frozen contract is
  being implemented incorrectly.

Requirements:

- do not modify PHASE-11-COMPLETE;
- do not amend or regenerate historical P11 evidence;
- preserve historical regression replay;
- add new prospective regression tests outside historical admitted evidence;
- re-run exact-head and Phase-11 aggregate regression after every admitted product
  correction;
- record the correction as post-Phase-11/pre-Phase-12 work;
- never make the correction conditional on SDK source identity.

### 8.2 Authority gap

If an SDK program requires a language feature, ABI behavior, object rule, syscall,
or runtime contract not already allowed by active authorities, STOP.

Do not implement it under a pre-release loophole. Prepare a new architecture/plan
authority revision and obtain explicit approval before target code changes.

### 8.3 SDK defect

If exact SDK 1.0.2 source violates the frozen C48 contract, STOP and record the
specific source/contract mismatch. Do not patch the SDK in this project and do not
silently relax ZX-UX.

### 8.4 Proof-harness defect

If ZX-UX is correct and only the harness is wrong, fix only the harness and repeat
the gate.

No gate may blur these four classes.

## 9. Required separation of historical fixtures from production compiler

The current tree contains many phase-specific compiler proof macros, including the
REV01 P11PR source-bound helpers. Historical replay may require some phase-specific
fixtures to remain available.

REV02 must establish a mechanical boundary:

- historical fixture-only code may remain solely for historical regression;
- it may not be linked into, dispatched by, or called from the ordinary current
  product cc path;
- REV02 build/proof scripts may not emit or call EMIT_P11PR_CC_SDK_CORPUS_COMPILER,
  EMIT_P11PR_CC_SDK_MULTITASK_COMPILER, or equivalent replacements;
- no new source-bound helper may be added under another name;
- the current product compiler must expose one generic production compilation
  path for arbitrary legal C48 translation units.

Add a static gate that traces the current cc command entry through preprocessing,
parsing, semantic handling, code generation, OBJ1 writing, and transactional
publication. The gate must fail if a source-identity dispatch path can reach output
publication.

## 10. Required product C48 correction target

The implementation target is not "make these 30 files pass". The target is the
frozen C48 compiler contract already documented by ZX-UX.

Before SDK execution, mechanically derive and retain:

- complete active C48 language-feature matrix from REV17/REV08/C48 docs;
- complete feature/API usage matrix of the exact 30 SDK programs and their three
  direct headers;
- complete SDK 1.0.2 compiler/reference-test semantic matrix;
- mapping from every required SDK construct to the generic ZX-UX compiler/runtime
  implementation that owns it.

The product correction lane must close generic compiler behavior in dependency
order, not program order:

1. source streaming and preprocessing, including ordinary quoted local headers;
2. lexical and literal handling;
3. declarations, scopes, globals, locals, arrays, pointers, function declarations
   and definitions;
4. integer/char/unsigned and any in-scope float semantics required by the frozen
   contract;
5. expression parsing/evaluation and documented operator semantics;
6. control flow, loops, short-circuit behavior, break/continue and returns;
7. function calls, recursion, stack/frame construction and C48_REGCALL;
8. runtime/library/syscall calls through the frozen ABI;
9. graphics, text, UDG, process/yield/sleep and other already-frozen public calls;
10. relocation/symbol generation and genuine OBJ1;
11. ordinary native ld consumption and MEX1 generation;
12. transactional output, namespace limits, memory-budget behavior and diagnostics;
13. ordinary shell-visible command path.

The exact 30 source names must not appear as implementation cases in this lane.

## 11. Stage A — establish recovery baseline

Before REV02 execution:

1. verify REV01 status is FAILED-CLOSED;
2. verify PHASE-11-COMPLETE exact identity;
3. verify P11.48 and Phase-11 aggregate historical records remain unchanged;
4. verify fast-loader migration runbook remains CLOSED;
5. capture current main/tree;
6. inventory every current P11PR compiler/proof helper and every current
   pre-release workflow script;
7. hash the failed REV01 bundle and preserve its Git-history recovery anchor;
8. prove zero Phase-12 state;
9. verify historical P11.39 SDK material unchanged;
10. confirm REV02 is the sole planned successor and no executor starts while this
    file is DRAFT.

**Gate A:** immutable baseline and failure lineage PASS.

## 12. Stage B — acquire SDK 1.0.2 and build the real acceptance specification

Acquire and independently verify the exact pinned release inputs.

Require:

- exact tag/commit/tree/package hashes;
- release verifier PASS;
- exact 57 source tapes;
- exact 30 in-scope programs;
- exact three direct headers;
- exact release source-tape bytes;
- exact source/header reconstruction from the tapes;
- exact reference-image LFS pointer identities and materialized payload hashes;
- separate GUI/evidence package provenance;
- no use of moving SDK main.

Build a machine-readable 30-program matrix containing only facts/oracles:

- SDK source path/hash;
- source TAP path/hash;
- target source name;
- direct header and hash;
- C48 feature/API usage;
- reference image pointer/payload identity;
- documented input/arguments;
- expected termination or long-running behavior;
- visual/algorithmic invariants derived from source and pinned SDK documentation.

Do not add target output code, canned screenshots, or compiler dispatch data to this
matrix.

**Gate B:** pinned acceptance corpus and oracle matrix PASS.

## 13. Stage C — reproduce the ordinary-product failures before fixing them

Using the current ordinary ZX-UX product compiler path, run a fail-closed diagnostic
matrix against representative and then all 30 exact source tapes.

The diagnostic must use the same cc entry that a user uses. Do not call any P11PR
compiler macro.

For each program, record:

- tape load result;
- header resolution result;
- cc status/diagnostic;
- whether OBJ1 was produced;
- ld status if compilation succeeded;
- process status if link succeeded;
- screen/runtime observation if execution succeeded.

This stage exists to distinguish actual product gaps from proof-harness gaps.
Failure is expected and is evidence, not a reason to introduce adapters.

**Gate C:** complete product-gap inventory exists with no special-path substitution.

## 14. Stage D — admit the authority bridge before target fixes

Classify every Stage-C gap under Section 8.

Before editing target product source:

- prove every planned fix is already required by active authority; or
- STOP for an explicit authority revision.

Record an exact planned changed-file set and regression set.

Because REV02 is currently DRAFT, execution must stop here until project
instructions explicitly authorize prospective post-P11 product corrections under
this runbook.

**Gate D:** correction authority is explicit and scope-bounded.

## 15. Stage E — repair ordinary ZX-UX C48 generically

Implement only generic product corrections required by Gate D.

For each correction checkpoint:

1. three consecutive unchanged-byte SoP scans;
2. product compiler unit/conformance tests;
3. current exact-head static/runtime regression;
4. Phase-11 aggregate regression;
5. no historical evidence mutation;
6. anti-source-specialization static scan;
7. durable direct-main checkpoint only after PASS.

Use the frozen C48 language/API matrix to drive implementation. Do not code by
walking the 30 program list and adding one special case per failure.

A new legal C48 source that combines already-supported features must compile
without modifying cc.

**Gate E:** ordinary current cc implements the required frozen C48 behavior
generically.

## 16. Stage F — compiler generality and anti-cheat gate

Before any canonical SDK program may count toward final acceptance, run the
Section-7 anti-specialization suite.

Mandatory positives include:

- disjoint non-SDK conformance programs;
- whitespace/comment variants;
- alternate valid basenames;
- selected constant/control/data mutations that remain legal C48;
- multiple programs sharing the same feature mix but different source bytes.

Mandatory negatives include:

- syntax errors;
- unsupported frozen-out language forms;
- invalid header/include cases;
- output-space/allocation failures;
- transactional rename/publication failures.

Static negatives must fail if the active compiler contains or reaches:

- a 30-program source identity table;
- exact SDK source CRC/length dispatch;
- SDK basename dispatch;
- program-title/output tables used for code generation;
- a pre-release-only lowering function;
- a canned lifecycle/visual/multitask application template selected by source
  identity.

**Gate F:** source-semantic generic compiler PASS.

## 17. Stage G — construct a real ZX-UX developer proof session

REV02 must strengthen the proof session beyond REV01.

The system under test must begin from the exact current Phase-11 pre-release boot
TZX and enter the real ZX-UX kernel normally.

Because Phase 12 final distribution assembly is forbidden, additional current
development tools may arrive only as clearly classified proof/developer sidecar
media. They must be ordinary ZX-UX objects built from current product source and
loaded through ordinary ZX-UX cassette/object mechanisms. They must not be
host-injected executable bytes.

The proof session must make the ordinary current product tools available:

- shell;
- cc;
- as where required;
- ld;
- required runtime/library support.

Then user-visible operations must occur through normal ZX-UX command/process
paths. A harness may type commands and inspect results; it may not call an internal
compiler/linker routine as the acceptance substitute.

Retain a deterministic command/session transcript sufficient to reproduce every
program lifecycle.

**Gate G:** the environment is a real ZX-UX user/developer session, not an
application-specific proof fixture.

## 18. Stage H — exact 30-program native lifecycle through ordinary commands

For each exact canonical release source TAP, from a clean deterministic session:

1. load the exact source/header objects through real cassette/M48O handling;
2. verify namespace object type/name/hash;
3. invoke ordinary cc on the C object;
4. require genuine target-produced OBJ1;
5. inspect OBJ1 format/symbol/relocation validity;
6. invoke ordinary ld;
7. require genuine target-produced executable;
8. launch it through ordinary shell/SYS_SPAWN/SYS_EXEC behavior;
9. prove start and correct exit or bounded live execution;
10. retain exact target-produced OBJ1 and executable bytes;
11. retain command/session/process evidence;
12. repeat from clean state so no program consumes another program's build output.

The compiler and linker binaries must be identical across all 30 runs.

No .visual or .multitask alternate executable is allowed. The executable retained
for a program is the executable used for its visual and concurrency proofs.

**Gate H:** 30/30 exact canonical C sources complete the real user lifecycle.

## 19. Stage I — source-to-behavior correctness for all 30 programs

A successful exit is not enough.

For each program define a program-specific behavior contract from the exact source,
the pinned SDK oracle, and the frozen ZX-UX API semantics.

Require observable behavior that could not be produced by a title-only stub.

Depending on program type, the contract must include appropriate checks such as:

- exact/normalized visible text;
- argument handling;
- expected geometry;
- screen-region occupancy;
- attribute/color behavior;
- UDG/sprite content;
- deterministic numerical state;
- recursive/iterative progress;
- multiple-frame change for animation;
- stable final state for terminating/static programs.

Where a pinned SDK reference image is suitable for the same deterministic
checkpoint, require pixel identity. Where timing/rendering contracts differ,
retain both images and enforce explicit source-derived visual/state invariants.

Merely recording reference_png_sha256 is never a visual comparison.

For dynamic programs capture enough checkpoints to prove actual motion/progress,
not just initial setup.

**Gate I:** 30/30 executables demonstrate actual source-defined behavior.

## 20. Stage J — canonical SCR/PNG evidence

Canonical screen evidence must come only from the real running target display RAM.

For every program:

- retain exact 6912-byte SCR;
- retain deterministic PNG rendered from that SCR;
- record exact frame/checkpoint;
- bind SCR/PNG to the exact executable hash and process/session record;
- bind executable to exact OBJ1 hash;
- bind OBJ1 to exact loaded source/header hashes;
- bind reference-image provenance and comparison result.

For dynamic demos, retain additional SCR/PNG checkpoints when required by Stage I.

Host tooling may render PNG from SCR. It may not draw or alter target pixels.

**Gate J:** screen evidence is cryptographically and causally bound from source
TAP through real native execution.

## 21. Stage K — genuine Hanoi + 8-Queens concurrency

Use the exact ordinary outputs from Stage H:

- hanoi executable hash must equal the standalone Stage-H hanoi executable hash;
- queens8 executable hash must equal the standalone Stage-H queens8 executable
  hash.

There is no second compile and no multitask-specific lowering.

In one real ZX-UX session:

1. start both ordinary native executables through the admitted process path;
2. record launch order/PIDs;
3. establish a common runnable epoch after both perform initial setup;
4. run the cooperative scheduler for exactly 1250 PAL frames from that epoch;
5. prove both processes execute/yield/progress after the epoch;
6. retain full-screen SCR/PNG at 1250 frames;
7. also retain earlier checkpoints sufficient to prove evolving algorithmic state;
8. exclude title/header rows when judging meaningful workload output;
9. require nontrivial algorithm-generated output in both screen halves;
10. prove Hanoi output obeys its left-half geometry/state invariants;
11. prove 8-Queens output obeys its right-half board/search invariants;
12. prove both halves change consistently with continued computation;
13. prove screen ownership bounds from target writes or equivalent deterministic
    instrumentation, not only from the final screenshot.

A screen containing only "TOWERS OF HANOI" and "8 QUEENS - RECURSIVE SEARCH" plus
one point per side must fail.

**Gate K:** the actual recursive programs run concurrently and visibly compute.

## 22. Stage L — ordinary native full-kernel rebuild

Retain the REV01 source-only textual kernel projection and source TAP requirements,
but strengthen the acceptance path.

Required positive path:

1. boot exact current pre-release TZX normally;
2. enter the real ZX-UX developer proof session;
3. load kernel-native-source.tap through ordinary cassette/M48O handling;
4. verify exact kernel.asm object identity;
5. invoke the ordinary product as command on the loaded text;
6. require genuine target-produced kernel OBJ1;
7. invoke the ordinary product ld command/path to produce the nonresident 8192-byte
   kernel output;
8. prove the resident executing kernel was not overwritten;
9. retain source, source map, source TAP, OBJ1 and native kernel;
10. compare all 8192 bytes among host-built, TZX-extracted and native-built kernel;
11. require one common SHA-256;
12. perform controlled source mutation and require identity failure;
13. build the final pre-release TZX from the retained native kernel and
    independently extract/compare it.

A harness may provide deterministic observation and media control. It may not call
a proof-only assembler/linker entry or provide a special allocator in place of the
ordinary tool path.

If ordinary as/ld cannot complete this already-required REV17 operation because of
a genuine product implementation defect, return through the Section-8 authority
bridge and fix the ordinary tool. Do not weaken this gate with a proof allocator.

**Gate L:** a normal ZX-UX native toolchain self-rebuilds the kernel.

## 23. Stage M — compiler/tool regression after product corrections

After all product fixes and before bundle construction, require:

- full active compiler test suite;
- imported historical P11.39 regression unchanged;
- separate SDK 1.0.2 reference/oracle suite;
- complete target-native C48 semantic mapping for the supported language surface;
- ordinary as/ld regressions;
- kernel/process/object/tape regressions touched by corrections;
- exact-head P11.48 regression;
- Phase-11 aggregate regression;
- memory/live-footprint constraints;
- documented-opcode scan;
- transactional output negatives;
- zero source-specific compiler-dispatch findings;
- zero Phase-12 state.

Historical P11 evidence remains historical. These are prospective regressions of
current main.

**Gate M:** current product is coherent after corrections.

## 24. Stage N — replacement pre-release media layout

The final REV02 bundle must be self-describing and must clearly distinguish:

- official boot TZX;
- source-transfer/evidence sidecar TAPs;
- developer-proof sidecar media;
- target-produced compiler/linker outputs;
- reference/oracle material.

Minimum logical contents:

~~~
P11.pre-release/
  README.txt
  pre-release.json
  zx-ux-phase11-pre-release.tzx
  failure-recovery/
    rev01-failure.json
    product-corrections.json
    anti-specialization.json
  kernel/
    kernel-native-source.asm
    kernel-native-source-map.json
    kernel-native-source.tap
    kernel-native.obj1
    kernel-host.bin
    kernel-tzx-embedded.bin
    kernel-native.bin
    kernel-native-build.json
    kernel-native-session.json
  sdk/
    SDK-RELEASE.json
    SOURCE-TAPE-MANIFEST.json
    TARGET-NAME-MAP.json
    FEATURE-MATRIX.json
    sources/
    tapes/
    native/
    proof/
      lifecycle/
      sessions/
      visual/
    reference-lfs/
    reference-png/
  multitasking/
    hanoi-queens8-epoch.scr
    hanoi-queens8-mid.scr
    hanoi-queens8-1250f.scr
    hanoi-queens8-1250f.png
    hanoi-queens8.json
~~~

The exact layout may remove duplication but may not omit logical evidence.

The final manifest must bind every retained file except itself by path, size and
SHA-256 and separately record its own SHA-256 in closure.

## 25. Stage O — deterministic rebuild and strong negatives

Build the complete REV02 candidate twice from the same exact current source head
and pinned inputs in clean workspaces.

Require deterministic identity for all deterministic files.

Mandatory negative gates include all REV01 negatives plus:

- compiler source-identity table injected -> FAIL;
- exact SDK CRC/length dispatch injected -> FAIL;
- canned lifecycle body substituted -> FAIL;
- canned title/plot visual body substituted -> FAIL;
- multitask-specific alternate executable substituted -> FAIL;
- reference PNG hash recorded without comparison -> FAIL;
- title-only Hanoi/Queens screenshot -> FAIL;
- standalone and concurrent executable hashes differ -> FAIL;
- proof-only cc/as/ld entry used -> FAIL;
- source/header host injection into target -> FAIL;
- host-built OBJ1/MEX1 substituted -> FAIL;
- semantics-preserving source variant rejected solely because hash/length changed
  -> FAIL;
- legal non-SDK C48 canary rejected while equivalent SDK-specific case passes
  -> FAIL;
- any SDK source/header byte modified -> FAIL;
- any Phase-12 state -> FAIL.

**Gate O:** deterministic double build and every anti-cheat negative PASS.

## 26. Stage P — exact-head publication

On one unchanged candidate head:

1. three consecutive full SoP scans;
2. license-header gate;
3. project-policy gate;
4. media-retention gate;
5. authority/evidence gate;
6. historical immutability gate;
7. current compiler/tool regression Gate M;
8. full 30-program ordinary lifecycle Gate H;
9. 30-program behavior/visual Gates I/J;
10. real Hanoi/Queens Gate K;
11. ordinary kernel self-rebuild Gate L;
12. deterministic Gate O;
13. exact-head P11.48 regression;
14. Phase-11 aggregate regression;
15. PHASE-11-COMPLETE exact identity;
16. zero Phase-12 state.

Publish only the exact tested staged bytes. Do not rebuild a second publication
copy.

The publisher must not dispatch Phase 12.

**Gate P:** exact published bytes equal exact tested bytes.

## 27. Stage Q — final repository sanity

After publication verify:

- only one official Phase-11 boot pre-release TZX;
- all TAPs are classified source/evidence/developer sidecars, not boot products;
- README explains the real ordinary cc/ld/as workflows used;
- every 30-program OBJ1/MEX1 pair is target-produced by the same ordinary tools;
- every PNG is bound to real program execution;
- reference images are clearly reference/oracle material, not target output;
- Hanoi/Queens image visibly contains actual algorithmic work from both programs;
- kernel rebuild uses ordinary as/ld;
- no active P11PR SDK-specific compiler path participates in current acceptance;
- failed REV01 remains recoverable and clearly identified as failed;
- historical evidence remains unchanged;
- current main is clean;
- PHASE-11-COMPLETE unchanged;
- zero Phase-12 state.

**Gate Q:** repository tells one coherent, truthful pre-Phase-12 story.

## 28. Implementation discipline

For every implementation checkpoint after REV02 is explicitly approved/opened:

1. follow docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md;
2. follow docs/--W-A-R-N-I-N-G--.md;
3. keep PHASE-11-COMPLETE immutable;
4. do not amend admitted P11 evidence/media;
5. use direct main commits unless workflow authority requires otherwise;
6. three consecutive unchanged-byte SoP scans before check-in;
7. any defect/change resets the scan count to zero;
8. run applicable policy/license/media/evidence/static/runtime gates;
9. use pinned project runtime and canonical drivers;
10. retain required Spectrum-native proof artifacts;
11. checkpoint/push only after gates PASS;
12. continue automatically through runbook gates when execution is later authorized;
13. STOP on an authority gap rather than hiding it in proof code;
14. never begin Phase 12.

## 29. Definition of DONE

REV02 is DONE only when all of the following are simultaneously true:

- REV01 remains FAILED-CLOSED and historically unchanged except that status marker;
- SDK 1.0.2 exact pin/provenance PASS;
- historical P11.39 SDK material unchanged;
- no SDK source/header bytes changed;
- ordinary current ZX-UX cc is generic and has no source-identity/corpus dispatch;
- generality/metamorphic/anti-specialization gates PASS;
- all 30 canonical SDK programs load through real tape/object handling;
- all 30 compile through the same ordinary product cc;
- all 30 emit genuine target-produced OBJ1;
- all 30 link through the same ordinary product ld;
- all 30 execute through normal ZX-UX process/shell behavior;
- all 30 exhibit actual source-defined behavior;
- all 30 retain real SCR/PNG evidence bound to exact native executables;
- SDK reference PNGs are actually compared under explicit per-program contracts;
- hanoi.c and queens8.c use the exact same ordinary executables in standalone and
  concurrent proofs;
- Hanoi/Queens both visibly compute at the required 1250-frame checkpoint and
  both independently demonstrate scheduler progress;
- full kernel source TAP rebuild uses ordinary product as/ld commands;
- host/TZX/native kernels are byte-identical for all 8192 bytes;
- final TZX consumes the retained native kernel bytes;
- complete bundle deterministic double-build PASS;
- all strong negatives PASS;
- exact-head P11.48 regression PASS;
- Phase-11 aggregate regression PASS;
- all policy/license/media/evidence gates PASS;
- all admitted P0-P11 evidence/media unchanged;
- PHASE-11-COMPLETE unchanged;
- clean current main;
- zero Phase-12 state.

Only then change this runbook from OPEN to CLOSED and append final source commit,
workflow run, bundle-manifest hash, TZX hash, SDK pin, kernel three-way hash,
30-program PASS count, compiler anti-specialization result, ordinary-tool session
anchors, Hanoi/Queens executable hashes and 1250-frame PNG hash, and final
validation anchors.

Then STOP.

**DO NOT START P12.01.**

## 30. Review gate for this draft

This REV02 file is intentionally DRAFT.

Do not execute Stage A or later and do not modify ZX-UX product source under this
draft.

Review must explicitly confirm at least:

- the post-P11 product-correction authority bridge;
- the ordinary-product cc/as/ld rule;
- the anti-specialization gates;
- the real-user developer proof session;
- the 30-program behavior/visual contracts;
- the strengthened Hanoi/Queens proof;
- the strengthened ordinary kernel self-rebuild;
- the Phase-12 hard stop.

After review, revise this file if needed and explicitly change Status to OPEN in a
separate admitted checkpoint before execution begins.
