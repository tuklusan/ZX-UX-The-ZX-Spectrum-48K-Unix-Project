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

**Status:** OPEN  
**Scope:** post-Phase-11, pre-Phase-12 recovery of the failed expanded pre-release, including only prospective product corrections strictly required by the frozen authority governing each epoch: REV17/REV08 for admitted P11 history and admitted REV18/REV09 for the post-P11/pre-P12 recovery lane, with subordinate frozen C48/ABI/object/tool documentation  
**Hard stop:** DO NOT START PHASE 12

## 1. Purpose

REV01 is FAILED-CLOSED because its acceptance machinery proved source identity,
native OBJ1/MEX1 mechanics, process launch, screen capture, and scheduler progress
without proving that the ordinary ZX-UX C48 compiler had compiled the actual SDK
program semantics.

REV02 exists to recover the real goal:

1. independently prove whether every exact SDK 1.0.2 example/demo source/header
   construct is legal under frozen C48; only a 30/30 legal result may enter the
   product-correction/acceptance lane;
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
specification. REV17/REV08 remain the immutable authority for admitted P11 history.
After admitted and activation-validated R18.00, REV18/REV09 are the canonical
authority for this post-P11/pre-P12 recovery lane. Their frozen SHA-256 identities
are REV18 `b13c551f854cf3c01d951212916c6cf787f23617e3b8b74fc7c1867f76ba2156`
and REV09 `9ff614ba04721961b3461d03638586260b91e9e82eac7687054ead1c9802869f`.
The corrected C48 language specification, `v1/docs/c48.md`, ABI/object/tool
documentation, compiler manual, and SDK are mandatory reconciliation/reference
inputs but may not widen or override the authority governing the current epoch.
Their exact review-time identities must be pinned before any product correction.
If a subordinate document conflicts with the governing frozen authority, or if the
desired behavior needs a contract not fixed there, execution stops for an explicit
authority revision rather than treating current documentation as a moving authority.

SDK 1.0.2 is a pinned reference/oracle and a large real-world candidate C48 workload.
Stage B must independently prove that each exact source/header construct is legal
under the frozen C48 contract before a compiler failure may be classified as a ZX-UX
implementation defect.

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

The admitted status-only FAILED-CLOSED change is commit
`a20adeceade081f4dbe9c09a70b6528d17877205`; its parent closed-REV01 checkpoint is
`f6fe98b122d6207c67c0e6cb156135cf0a8856eb`. Stage A must prove that exact
transition changed only the requested REV01 status marker.

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
- release ZIP size: 15432637 bytes;
- GUI/reference-evidence ZIP size: 3700008 bytes;
- release metadata asset SHA-256:
  668911b54f20625ea8a7efa5219261146e4ef5a76a2f055a7990f019d59f555d;
- release SHA256SUMS asset SHA-256:
  1981aa83cd1796894a380d2751cbc534483b244868d28c97f69c922f30672990;
- source-tape manifest Git blob:
  8275c5b4985abb74d66a8eb43428fda9d8884809;
- examples tree:
  042a1b302646957c223b955a9d967ca690a2b33f;
- demos tree:
  c8363270a6da92661f43650933d5b4848521f54d;
- hanoi.c blob:
  57e9419a56fca83656f574de6fa4d994b5eadae1;
- queens8.c blob:
  38cff8912e1bced21c01f3ee050063ce19afe35e;
- recapi.h blob:
  29e170e5c10aee80f09ed9eb7f273b8c9c9aedbc.

The tag/commit/tree values above are immutable provenance for formal SDK release
1.0.2. They are not a requirement that the SDK repository's moving `main`, current
HEAD commit, or current repository tree remain equal to those historical release
identifiers.

REV02's execution pin is byte-oriented. It pins the exact in-scope C48 application
source/header corpus and the exact release-provided source-transfer/reference bytes
used by this runbook. In particular:

- every in-scope SDK `.c` and directly required `.h` file is identified by exact
  path plus cryptographic content hash in the retained acceptance manifest;
- the corresponding canonical release source TAP bytes are independently hashed and
  must reconstruct those exact source/header bytes;
- unrelated SDK repository changes, including tools, Python programs, documentation,
  tests, packaging logic, or other non-corpus files, may advance SDK `main` and
  therefore change current Git commit/tree/HEAD identifiers without invalidating
  REV02;
- REV02 must never silently substitute bytes from moving SDK `main` merely because
  its current Git identifiers are newer;
- movement of SDK `main` by itself is neither a stop condition nor a reason to
  re-pin this runbook.

The release source-tape manifest declares 57 tapes. REV02 scope is exactly the
same 30 example/demo programs: 6 examples and 24 demos. spriteanim.c keeps exact
SDK source bytes/path and the release-declared target alias sprani.c.

If a newer formal SDK release exists when REV02 is later opened for execution,
STOP and explicitly re-pin/review this runbook as already required. Ordinary moving
`main` commits that do not constitute a newer formal release do not trigger that
stop. Never consume moving SDK `main` as an execution input.

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
10. The current REV01 workflow is write-capable: changes to cc/as/ld or the
    pre-release tools can trigger `.github/workflows/p11-prerelease-build.yml`,
    whose publisher can commit replacement `P11.pre-release` media to `main`.
    That publisher was certified by the failed REV01 gates and must not remain an
    automatic publication path while REV02 product corrections are being made.

REV02 must contain static and runtime gates that make all ten failure classes
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
- mutating the loaded canonical C/header namespace objects before, during, or after
  compilation so the compiler actually consumes different bytes;
- a cc48.asm or other parallel compiler fork created solely for this pre-release;
- any other source fingerprint, prefix/suffix signature, token signature, AST
  signature, basename/path class, hidden lookup table, or equivalent corpus
  classifier used to select generated application semantics;
- reuse of a pre-existing OBJ1/executable under the requested output name;
- direct invocation of proof-only cc/as/ld internals in place of the shell-visible
  product command;
- a write-capable REV01 publisher remaining armed while recovery edits touch paths
  that can trigger it.

A proof harness may boot/orchestrate Fuse, type keys, attach tapes, inspect target
RAM/registers, capture screen RAM, hash target-produced files, and enforce
checkpoints. It may not perform the work being proved and may not write target
application state, screen RAM, compiler/linker outputs, scheduler state, or tool
input buffers.

For an "ordinary command" proof, the shell must parse the recorded command line,
resolve the normal product command from the normal command namespace/PATH, create
the ordinary process/ARG1 state, and execute the same binary a user receives. Every
proof records that binary's SHA-256 and source/build dependency closure. Calling a
tool routine directly from a fixture is not command execution.

Static provenance tables may contain SDK hashes and names. Executable compiler,
assembler, linker, runtime/library archive, shell, and acceptance behavior may not
use them to select program semantics. The ordinary process loader must load the
retained executable bytes themselves; command-name or basename dispatch in the
shell/kernel may not substitute a built-in/canned application.

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
   expressions and the frozen ABI, not by a known-corpus identity;
8. prove quoted local headers are actually opened/read through the ordinary target
   include path, rather than ignored or replaced by source-specific built-ins;
9. run held-out legal C48 challenge programs whose concrete bytes are generated
   only after the candidate product-tool hashes are frozen, using an independent
   deterministic generator/oracle. Derive the concrete challenge seed from a
   domain-separated SHA-256 over the frozen source-head plus cc/as/ld binary hashes
   and record the derivation;
10. apply equivalent anti-specialization checks to `ld`: renamed/changed legal
    OBJ1 modules and relocation/symbol mutations must be linked semantically, with
    no OBJ hash/name/application table or prebuilt executable dispatch;
11. apply equivalent anti-specialization checks to `as`: non-kernel legal source,
    whitespace/comment variants, alternate basenames, and semantic mutations must
    use the same parser/encoder/writer path, with no kernel fingerprint/payload
    dispatch.

Canonical release media still retain only the exact SDK source tapes. Mutated and
held-out sources are ephemeral anti-specialization tests and are never substituted
for the release inputs. The independent challenge generator may know the frozen
language contract but must not call the product compiler or derive expected results
from product outputs. If any challenged product-tool byte changes, discard the
concrete held-out challenge set, re-freeze the new tool hashes, regenerate the
challenge inputs from the recorded method/seed domain, and rerun the gate.

## 8. Authority bridge for prospective ZX-UX product correction

This is the bridge REV01 lacked.

REV02 execution must not begin product edits until this bridge is explicitly
admitted by project instructions and the runbook is changed from DRAFT to OPEN.

For each discovered failure of ordinary cc/as/ld/kernel/runtime behavior:

### 8.1 Existing-authority defect

If the frozen authority governing the current epoch already requires the behavior,
with subordinate C48/ABI/object/tool documents only clarifying that frozen
requirement, the failure is a ZX-UX implementation defect. Admitted P11 history
remains governed by REV17/REV08; prospective REV02 recovery corrections after
R18.00 are governed by REV18/REV09. Each classification must cite the exact
controlling clause and the exact subordinate contract used to test it; the desired
REV02 proof result itself is not authority.

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

If an SDK program or a strengthened REV02 proof requires a language feature, ABI
behavior, object rule, syscall, runtime contract, command-line option, or public
tool behavior not already fixed by the frozen authority governing the current
recovery epoch, STOP the runbook before target code changes for that gap.

Do not implement it under a pre-release loophole and do not draft/activate the new
contract as an automatic REV02 step. The authority transition must occur separately
under explicit approval; REV02 must then be revised, re-reviewed, rescanned, and
explicitly re-admitted for continuation against the new authority before execution
resumes.

### 8.3 SDK defect

If exact SDK 1.0.2 source violates the frozen C48 contract, STOP and record the
specific source/contract mismatch. Do not patch the SDK in this project and do not
silently relax ZX-UX.

### 8.4 Proof-harness defect

If ZX-UX is correct and only the harness is wrong, fix only the harness and repeat
the gate.

### 8.5 Mandatory gap-classification record

Before any product correction, retain a machine-readable classification record for
every Stage-C gap containing: failing reproduction identity; exact input/tool
hashes; observed result; expected result; one of the four classes above; exact
authority citation for an implementation defect; exact planned changed paths; and
the regression/negative tests that will close it. Unclassified gaps, mixed classes,
or a classification justified only by the SDK/reference picture fail closed.

The former C014 authority gap is now closed only by admitted R18.00. REV18 Section
24 and REV09 R18.00 freeze the exact ordinary shell-visible form
`ld input.obj -o output -abs` for the already-required generic fixed/absolute
OBJ1 image capability. No other fixed-image CLI syntax may be invented. Stage C
must re-reproduce the current product behavior against that exact command and
Stage D must reclassify C014 under REV18/REV09 before any implementation change.

No gate may blur these four classes.

### 8.6 R18.00 authority re-entry checkpoint

The C014 stop was resolved through a separate authority transition rather than by
changing product code under REV02:

- R18.00 qualified source candidate: `9759925f2b9d427e402131426b5fb2bf0118a8b1`;
- R18.00 evidence-admission commit: `41f93e942297278d1a5010d0bd1fe90ccf0cb8ab`;
- activation validation PASS: workflow run `36633777076`, validated at
  `8fcc0ff5fa15c7e913cf186265f9b170903cad50`;
- REV18 SHA-256:
  `b13c551f854cf3c01d951212916c6cf787f23617e3b8b74fc7c1867f76ba2156`;
- REV09 SHA-256:
  `9ff614ba04721961b3461d03638586260b91e9e82eac7687054ead1c9802869f`;
- REV17/REV08 remain immutable historical P11 authority;
- PHASE-11-COMPLETE remains
  `263a203da3d54a398e8ac011284ae4195b1279c0`;
- Phase 12 remains forbidden.

Before resuming product correction, these revised REV02 bytes require three
successive unchanged complete SoP scans plus the applicable license, policy,
authority, historical-immutability, exact-head and zero-Phase-12 gates. Stage C
and Stage D records must then be regenerated so C014 is no longer carried as an
authority gap.

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

Also retain exact build/dependency closures for the product `cc`, `as`, and
`ld` binaries. Historical macro definitions may remain in source only when they
are unreachable from the production expansion/link closure. The product binary,
map/symbol output, and transitive production dependency set must contain no
P11PR source-bound helper or equivalent payload/fingerprint table. A target-native
routine living only in a proof/fixture source path is not thereby the ordinary
product command. If current source ownership or install/build routing disagrees
with REV17/REV08, classify that discrepancy through Section 8 before changing it.

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

### 10.1 48K feasibility and ordinary-allocation rule

REV02 must prove the real workflow fits the original unexpanded 48K machine. No
special proof allocator, hidden host backing store, injected workspace, or
out-of-contract memory region may make a gate pass.

Retain measured peak allocation/liveness maps for at least:

- the largest source/header compile and the largest produced OBJ1;
- the largest link, including built-in crt0/runtime/archive selection;
- each hanoi/queens standalone run and their concurrent run;
- the textual full-kernel assembly and fixed/absolute link.

For each checkpoint bind every live target allocation, object payload, process
image/BSS/stack, compiler/assembler/linker workspace, transaction object, and output
buffer to the frozen memory map. Prove non-overlap with display/ROM workspace and
the resident kernel, exact allocator class/range, and ordinary allocation APIs.
The C48 compiler process-owned live-footprint target remains <=20 KiB as frozen in
`v1/docs/c48.md`; total simultaneous target residency must also fit the real
available arenas. If the exact largest canonical source cannot complete through the
ordinary product path within the frozen resource contract, STOP and classify the
gap under Section 8. Do not solve it by a pre-release allocator or host spill.

## 11. Stage A — establish recovery baseline

Before REV02 execution:

1. verify REV01 status is FAILED-CLOSED and byte-identical to its failed-closure
   anchor except for the already-admitted status-only change;
2. verify PHASE-11-COMPLETE exact identity;
3. verify P11.48 and Phase-11 aggregate historical records remain unchanged;
4. verify fast-loader migration runbook remains CLOSED;
5. capture current main/tree and exact hashes of REV17, REV08, the corrected C48
   specification, compiler manual, and current C48/ABI/assembler/OBJ1/MEX1/tape
   documentation used for reconciliation;
6. construct a recursive immutable-scope manifest from PHASE-11-COMPLETE covering
   all admitted P0-P11 evidence/media and historical authorities, and require it
   unchanged before and after every later publication gate;
7. inventory every current P11PR compiler/proof helper and every current
   pre-release workflow/script, including reachability from product tool builds;
8. recursively hash the failed REV01 bundle and record its exact Git recovery
   commit/tree rather than relying on current-path names;
9. prove zero Phase-12 state;
10. verify historical P11.39 SDK material unchanged;
11. **before changing any path watched by the current REV01 publisher**, make the
    first post-OPEN recovery checkpoint control-plane-only: quarantine/replace the
    write-capable `.github/workflows/p11-prerelease-build.yml` so ordinary recovery
    pushes cannot run REV01 build/finalize/publish logic or commit media to main;
12. prove no active workflow with write permission can publish
    `v1/dist/media/P11.pre-release/` from failed REV01 acceptance gates; later
    publication must be an explicit REV02 Gate-P action against an exact head;
13. confirm REV02 is the sole planned successor and no executor starts while this
    file is DRAFT.

The control-plane quarantine checkpoint may modify only the recovery workflow/
guard needed to prevent false publication; it may not modify product code, SDK
reference bytes, or current pre-release media. It receives the same three-scan and
policy gates as any other checkpoint.

**Gate A:** immutable baseline/failure lineage PASS and the legacy write-capable
REV01 publisher is safely quarantined before product work.

## 12. Stage B — acquire SDK 1.0.2 and build the real acceptance specification

Acquire and independently verify the exact pinned release inputs.

Before acquisition, query the formal SDK releases/tags read-only. If a release newer
than 1.0.2 exists, STOP and explicitly re-pin/re-review REV02 before using any SDK
bytes. Moving SDK main is never an execution input.

Require:

- exact tag/commit/tree/package sizes and hashes;
- release verifier PASS;
- exact 57 source tapes;
- exact 30 in-scope programs;
- exact three direct headers;
- exact release source-tape bytes;
- exact source/header reconstruction from the tapes;
- exact reference-image LFS pointer identities and materialized payload hashes;
- separate GUI/evidence package provenance;
- no use of moving SDK main as an execution input;
- record the observed SDK moving-main HEAD only as informational provenance, never
  as an equality requirement or acceptance pin;
- prove every pinned in-scope `.c`/`.h` content hash and canonical source-TAP
  hash independently of the repository's current moving HEAD/tree;
- unrelated SDK tool/Python/documentation/test changes and resulting Git-ID movement
  are ignored by acceptance so long as the pinned corpus bytes remain exact;
- independent static classification of every source/header construct against the
  frozen C48 contract, with zero unexplained/unsupported construct before any
  product defect classification. This classifier/oracle must be independent of the
  product cc parser/code generator and may not infer legality from "cc accepted it".

Build a machine-readable 30-program matrix containing only facts/oracles:

- SDK source path/hash;
- source TAP path/hash;
- target source name;
- direct header and hash;
- C48 feature/API usage;
- reference image pointer/payload identity;
- documented input/arguments;
- expected termination or long-running behavior;
- visual/algorithmic invariants derived from source and pinned SDK documentation;
- every deterministic input/argument and every capture/checkpoint frame;
- for every available reference PNG, a predeclared comparison mode and exact
  metric/region/invariant set; "not suitable" is not an unqualified escape.

Freeze and hash these behavior/visual contracts before Stage C target execution and
before product corrections. They may not be relaxed after observing ZX-UX output.
Changing a contract is a candidate-byte change: reset the scan count, independently
justify the oracle change, and rerun every affected proof from its beginning.

Do not add target output code, canned screenshots, or compiler dispatch data to this
matrix. Expected values must come from source, frozen target semantics, pinned SDK
documentation/reference material, or an independent oracle, never from the product
output being judged.

**Gate B:** pinned acceptance corpus/oracle contracts PASS and all 30 exact
source/header inputs are statically classified as legal frozen C48 before they can
be used to justify a ZX-UX product fix.

## 13. Stage C — reproduce the ordinary-product failures before fixing them

Using the current ordinary ZX-UX product compiler path, run a fail-closed diagnostic
matrix against representative and then all 30 exact source tapes.

The diagnostic must start from a clean namespace with no target OBJ1/executable
under the planned output names. It must enter through the normal shell command
resolution/process path and record the exact `cc` and `ld` product binary hashes
and dependency closures. Do not call any P11PR compiler macro or internal tool
routine. The quarantined legacy publisher must remain unable to publish during this
diagnostic work.

For each program, record:

- tape load result;
- header resolution result;
- cc status/diagnostic;
- whether OBJ1 was produced;
- ld status if compilation succeeded;
- process status if link succeeded;
- screen/runtime observation if execution succeeded;
- namespace state before/after cc and ld, including transaction objects;
- evidence that each quoted local header used by the source was opened/read through
  the ordinary target path;
- peak target-memory/allocation telemetry for representative and worst-case inputs.

This stage exists to distinguish actual product gaps from proof-harness gaps.
Failure is expected and is evidence, not a reason to introduce adapters.

**Gate C:** complete product-gap inventory exists with no special-path substitution.

## 14. Stage D — admit the authority bridge before target fixes

Classify every Stage-C gap under Section 8.

Before editing target product source:

- prove every planned fix is already required by active authority; or
- STOP for an explicit authority revision.

Record the Section-8.5 machine-readable classification, exact planned changed-file
set, and regression/negative set for every gap. No product file may be edited for
a gap until that record cites the controlling frozen requirement.

When REV02 is DRAFT, Stage A itself is forbidden by Section 30; Stage D is not a
special loophole that allows partial execution. Once REV02 is separately approved
and OPEN, Stage D is the last gate before prospective product edits. Any authority
gap stops the whole affected lane until the separate authority process and a
re-reviewed runbook revision are complete.

**Gate D:** every planned correction has explicit frozen authority and bounded
scope; zero desired-proof behavior is being promoted to authority by assertion.

Any defect discovered in Stage E or later returns to the earliest stage whose
assumption or product behavior it invalidates. A target/product fix requires a new
or updated Stage-C reproduction and Stage-D classification, resets all downstream
PASS states, discards any staged publication candidate, and reruns affected
generality/lifecycle/behavior/kernel gates. No late-stage fix may be patched in and
followed by resuming at the next letter.

## 15. Stage E — repair ordinary ZX-UX C48 generically

Implement only generic product corrections required by Gate D.

For each correction checkpoint:

1. three consecutive unchanged-byte SoP scans;
2. product compiler/unit/tool conformance tests;
3. exact-head P11.48 regression where the changed dependency is in scope;
4. current exact-head static/runtime regression;
5. Phase-11 aggregate regression;
6. no historical evidence mutation;
7. anti-source-specialization static/reachability scan for cc/as/ld as applicable;
8. measured frozen memory/resource-budget checks for the changed path;
9. durable direct-main checkpoint only after PASS.

Use the frozen C48 language/API matrix to drive implementation. Do not code by
walking the 30 program list and adding one special case per failure.

A new legal C48 source that combines already-supported features must compile
without modifying cc.

**Gate E:** ordinary current cc and any already-authorized runtime/link/tool
dependencies touched by the correction implement the required frozen behavior
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

Static negatives must fail if the reachable production compiler contains or reaches:

- a 30-program source identity table;
- exact SDK source CRC/length dispatch;
- any other source/token/AST fingerprint or SDK basename/path dispatch;
- program-title/output tables used for code generation;
- a pre-release-only lowering function;
- a canned lifecycle/visual/multitask application template selected by source
  identity.

Require equivalent production-reachability and mutation negatives for `as` and
`ld`, including rejection of a kernel-source fingerprint emitter, OBJ1 hash/name
to executable dispatch, and prebuilt application/kernel payload tables. Extend the
static/reachability review through the linker's built-in crt0/runtime archive,
libc48/runtime dependencies, shell command dispatch, and executable loader so no
SDK/demo name, generated special symbol, title/output table, or application-specific
runtime member can recreate canned semantics downstream of an otherwise generic cc.
Historical unexpanded fixture macros may exist only outside all production
dependency closures.

For selected header-dependent programs, mutate one ephemeral header token while
keeping the C source unchanged and prove ordinary cc behavior/diagnostics changes as
the frozen semantics require; restore exact canonical bytes before acceptance.

**Gate F:** generic source-semantic cc plus generic as/ld production paths PASS.

Freeze the exact Gate-F product `cc`, `as`, `ld`, shell/loader and relevant
runtime/archive hashes. Gates G-P must use those exact bytes. Any change to one of
them invalidates Gate F and every downstream result and returns through the
Stage-C/D/E/F loop.

## 17. Stage G — construct a real ZX-UX developer proof session

REV02 must strengthen the proof session beyond REV01.

The system under test must begin from a candidate boot TZX built from the exact
current recovery source head, using the ordinary current release-TZX path, and enter
the real ZX-UX kernel normally. It must not silently reuse the failed REV01 TZX if
product/kernel bytes that affect boot have changed.

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

Any developer sidecar carrying those tools must be built from the exact current
product source through the normal project build, hash-bound to its source dependency
closure, loaded as ordinary ZX-UX objects, and verified before execution. A
fixture-only target binary is not a product sidecar.

Then user-visible operations must occur through normal ZX-UX command/process
paths. The retained transcript must show login/session state, cassette/object load,
the exact shell command text, command lookup, argv, exit/status, and output-object
publication. A harness may type commands and inspect results; it may not call an
internal compiler/linker routine as the acceptance substitute.

Retain deterministic tool hashes, memory maps, and a command/session transcript
sufficient for a human user to reproduce every lifecycle with the same media.

**Gate G:** the environment is a real ZX-UX user/developer session, not an
application-specific proof fixture.

## 18. Stage H — exact 30-program native lifecycle through ordinary commands

For each exact canonical release source TAP, from a clean deterministic session:

1. prove the planned OBJ/executable names are absent before loading/building;
2. load the exact source/header objects through real cassette/M48O handling;
3. verify namespace object type/name/hash and ordinary quoted-header resolution;
4. invoke the shell-visible ordinary `cc source.c` (or already-frozen explicit
   output form where required);
5. re-hash every canonical loaded C/header object after cc and require it
   byte-identical to the verified pre-compile object;
6. require genuine target-produced OBJ1 committed through the ordinary transaction;
7. inspect OBJ1 format/symbol/relocation validity and retain the exact bytes;
8. invoke shell-visible ordinary `ld source.obj -o name`;
9. require genuine target-produced executable committed through the ordinary
   transaction and retain the exact bytes;
10. launch it through ordinary shell/SYS_SPAWN/SYS_EXEC behavior;
11. prove the process image/entry loaded by the kernel is derived from the exact
    retained executable bytes and not a command-name/builtin substitute;
12. prove start and correct exit or bounded live execution;
13. retain exact command/argv, tool hashes, namespace/transaction, process and
    memory evidence;
14. prove a selected legal semantic source mutation changes target-produced
    object/executable/runtime behavior as the frozen oracle predicts;
15. repeat the canonical build from clean state so no program consumes another
    program's build output or a stale destination.

The compiler and linker binaries must be identical across all 30 runs.

No .visual or .multitask alternate executable is allowed. The executable retained
for a program is the executable used for its visual and concurrency proofs.

**Gate H:** 30/30 exact canonical C sources complete the real user lifecycle.

## 19. Stage I — source-to-behavior correctness for all 30 programs

A successful exit is not enough.

Use only the program-specific behavior contracts frozen and hash-bound in Stage B.
Do not create, weaken, move, or reinterpret a checkpoint after seeing target output.

Require observable behavior that could not be produced by a title-only stub or by
a source-specific canned renderer.

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

For every pinned SDK reference image, execute the predeclared Stage-B comparison.
Require pixel identity when the checkpoint/rendering contract says so; otherwise
apply the predeclared regions/metrics/source-derived invariants and retain the
comparison report. A later claim that a reference is "not suitable" is a contract
change and cannot waive the gate.

Merely recording reference_png_sha256 is never a visual comparison.

For dynamic programs capture every predeclared checkpoint needed to prove actual
motion/progress, not just initial setup. Every behavioral assertion must point to
retained target state, process evidence, SCR bytes, or another independently
captured target observation.

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
- bind reference-image provenance and comparison result;
- where the program changes display RAM, prove the relevant writes occur while the
  expected retained executable/PID is running and are not produced by a harness or
  unrelated background process.

Retain SCR+PNG for every visual checkpoint used by Stage I, not merely one
representative image. Each SCR is exactly 6912 target display bytes.

Host tooling may render PNG from SCR. It may not draw or alter target pixels.
Debugger/watchpoint instrumentation used to prove writes or progress must be
observation-only: it may not patch program code/data, intercept a syscall with
different semantics, or write target state.

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
3. use the same argv/environment/runtime inputs as the standalone proofs unless
   the pinned source contract explicitly requires otherwise;
4. establish a common runnable epoch after both perform initial setup and record
   both the emulator PAL-frame index and target tick/process state;
5. run the cooperative scheduler for exactly 1250 PAL frames from that epoch,
   measured by frame boundaries rather than host sleep, and independently
   cross-check the target tick delta/state;
6. prove both processes execute/yield and make source-derived algorithmic progress
   after the epoch;
7. retain full-screen SCR/PNG at 1250 frames;
8. retain the predeclared early/mid checkpoints and algorithmic state evidence
   sufficient to prove evolving computation;
9. exclude title/header rows when judging meaningful workload output;
10. require nontrivial algorithm-generated output in both screen halves;
11. prove Hanoi output obeys its left-half geometry/state invariants;
12. prove 8-Queens output obeys its right-half board/search invariants;
13. prove both halves change consistently with continued computation;
14. prove screen ownership bounds from observation-only target-write watchpoints or
    equivalent deterministic instrumentation, not only from the final screenshot;
15. prove no harness writes to either process state or screen during the measured
    interval.

A screen containing only "TOWERS OF HANOI" and "8 QUEENS - RECURSIVE SEARCH" plus
one point per side must fail.

**Gate K:** the actual recursive programs run concurrently and visibly compute.

## 22. Stage L — ordinary native full-kernel rebuild

Restate, rather than inherit by trust, the source-only kernel requirement. The
retained textual projection must be deterministic plain LF assembler text derived
from canonical kernel source/includes/definitions, with a line/source provenance
map. Its generator may not read `kernel.bin`, a host listing's machine-code
columns, preassembled opcode bytes, or any equivalent binary oracle. It may expand
host-only include/macro conveniences only into genuine documented source semantics.
The exact source TAP must independently reconstruct those text bytes.

Required positive path:

1. boot the exact current candidate TZX normally and enter the real developer
   session;
2. load `kernel-native-source.tap` through ordinary cassette/M48O handling;
3. verify exact `kernel.asm` object identity and prove no prior kernel OBJ/output
   destination exists;
4. invoke the shell-visible product `as kernel.asm` (or frozen documented
   explicit-output form) through normal command/process handling;
5. require genuine target-produced OBJ1 through the ordinary assembler
   parser/encoder/writer/transaction path;
6. invoke the exact ordinary shell-visible fixed-image form authorized by REV18
   Section 24, `ld kernel.obj -o kernel-native -abs`, through normal command/
   process handling; the produced DAT object must contain exactly the OBJ1 TEXT;
7. require Gate D to cite REV18 Section 24 and REV09 R18.00 for that exact command
   behavior; no alternate fixed-image option or proof-only linker entry is
   permitted;
8. produce the nonresident 8192-byte kernel only through ordinary target allocation
   and prove the executing kernel was not overwritten;
9. retain source, source map, source TAP, genuine OBJ1, native kernel, exact command
   transcript, tool hashes and memory map;
10. compare all 8192 bytes among independently host-built, finished-TZX-extracted
    and native-built kernels and require one common SHA-256;
11. prove assembler/linker generality with a non-kernel source, a
    whitespace/comment-equivalent kernel projection, alternate valid basename, and
    a controlled semantic source mutation; equivalent source preserves machine
    result, semantic mutation changes it and breaks three-way equality;
12. statically/reachably reject a kernel-source fingerprint, host-kernel payload,
    proof-only fixed-image entry, or special allocator from the acceptance path;
13. build the final pre-release TZX from the retained native kernel bytes and
    independently extract/compare those exact bytes.

A harness may provide deterministic observation and media control. It may not call
a proof-only assembler/linker entry, feed an OBJ1/kernel payload, or provide a
special allocator in place of the ordinary tool path.

If ordinary as/ld cannot complete the path, return through Section 8 and classify
the exact reason. Do not presume every missing shell-visible mode is an
existing-authority defect, and do not weaken this gate with a proof allocator.

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
- measured Section-10.1 48K peak-residency/live-footprint maps for worst-case
  compile/link/kernel/concurrency paths;
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
    authority-classification.json
    acceptance-contracts.json
    toolchain-identity.json
    memory-feasibility.json
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
  loader/
    realtime-boot.json
~~~

The exact layout may remove duplication but may not omit logical evidence. Every
session/checkpoint file used to prove behavior must either be retained or be
losslessly summarized by a retained hash-bound record that identifies the raw
artifact.

The final manifest must bind every retained file except itself by path, size and
SHA-256, record the recursive digest of the separately published
`v1/tests/compiler/sdk-reference/pre-release-1.0.2` tree, record the immutable
historical P11.39 SDK-reference digest/anchor used for non-mutation proof, and bind
the exact publication path set. Closure separately records the final manifest's own
SHA-256 and both frozen publication-tree digests.

## 25. Stage O — deterministic rebuild and strong negatives

Build the complete REV02 candidate twice from the same exact current source head
and pinned inputs in two independently initialized clean workspaces. They may share
only separately hash-verified immutable downloads/toolchain inputs; neither build
may consume the other's generated source projection, OBJ1, executable, SCR, PNG,
session output, or staged bundle.

The following are mandatory deterministic outputs, not optionally classifiable as
"nondeterministic": TZX; kernel projection/map/TAP/OBJ1/native image; all 30
canonical TAP copies; all 30 target-produced OBJ1/executables; all retained
behavior/concurrency SCRs and deterministic PNGs; normalized command/process/
scheduler/memory records; tool/provenance manifests; and every final bundle
manifest/report. Any runtime timestamp/host path must be omitted or normalized.
There must be zero unclassified bundle files.

Mandatory negative gates include independently re-specified applicable REV01
negatives plus:

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
- reachable source/token/AST fingerprint dispatch under another name -> FAIL;
- linker OBJ hash/name/application dispatch or prebuilt executable -> FAIL;
- assembler kernel fingerprint/prebuilt payload dispatch -> FAIL;
- quoted local header ignored/replaced while canonical source still "passes" -> FAIL;
- loaded canonical C/header object mutated by cc or proof machinery -> FAIL;
- stale/pre-existing OBJ1 or executable accepted as new output -> FAIL;
- behavior/visual contract changed after observing target output -> FAIL;
- missing retained checkpoint used by a behavior assertion -> FAIL;
- hidden/special allocator or host spill makes a 48K path fit -> FAIL;
- legacy REV01 workflow/publisher can publish on a recovery product push -> FAIL;
- final TZX boots only when emulator fastload/traps/loader shortcuts are enabled
  -> FAIL;
- any SDK source/header byte modified -> FAIL;
- any Phase-12 state -> FAIL.

**Gate O:** deterministic double build and every anti-cheat negative PASS.

## 26. Stage P — exact-head qualification, publication, and post-publication proof

Publication is two-phase so "exact head" cannot accidentally mean the source head
before media was committed.

### 26.1 Frozen source qualification head

On one unchanged source/tool/workflow candidate head:

1. three consecutive full SoP scans;
2. license-header gate;
3. project-policy gate;
4. media-retention gate;
5. authority/evidence and immutable-scope gates;
6. current compiler/tool regression Gate M;
7. full 30-program ordinary lifecycle Gate H;
8. 30-program behavior/visual Gates I/J;
9. real Hanoi/Queens Gate K;
10. ordinary kernel self-rebuild Gate L;
11. deterministic double-build/negative Gate O;
12. exact-head P11.48 regression;
13. Phase-11 aggregate regression;
14. PHASE-11-COMPLETE exact identity;
15. zero Phase-12 state.

Freeze the exact tested staged publication set and its recursive digests: both the
complete `P11.pre-release` bundle and the separate
`v1/tests/compiler/sdk-reference/pre-release-1.0.2` reference tree. Record the
exact path set expected to change. Do not rebuild either tree for publication.

### 26.2 Exact publication commit

From the still-exact qualified head, atomically copy only the frozen staged
REV02 bundle/reference bytes into their final paths and commit them once. The
publication action must check origin/main is still the qualified head immediately
before the commit/push. It must never dispatch Phase 12.

### 26.3 Post-publication exact-head validation

On the publication commit itself:

1. prove every published byte in both frozen publication trees equals the staged
   bytes/digests and no unlisted file changed;
2. rerun license/project-policy/media/authority/historical-immutability gates;
3. rerun P11.48 exact-head and Phase-11 aggregate regression;
4. rerun H-L acceptance against the published inputs and require regenerated
   deterministic outputs to equal the published retained outputs byte-for-byte;
5. boot the final published TZX from reset with ordinary `LOAD ""` in real time,
   with Fuse fastload/traps/loader shortcuts disabled; prove loader display,
   exact 8192-byte transfer, permanent 0xE003 handoff, correct post-kernel tape
   position/bootstrap loading, and normal shell session;
6. run any still-required detect-loader compatibility mode from the CLOSED
   fast-loader migration contract;
7. independently extract the published TZX kernel and require identity with the
   retained native kernel;
8. re-prove PHASE-11-COMPLETE unchanged and zero Phase-12 state.

**Gate P:** the exact publication commit, not merely its parent, PASSes and exact
published bytes equal the exact qualified staged bytes.

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

### 27.1 Closure checkpoint

Only after Gates A-Q and post-publication Gate P pass may the runbook closure bytes
be prepared. Change only this REV02 file from OPEN to CLOSED and append the required
durable anchors. That byte change resets the SoP count: manually scan the complete
final on-disk runbook from first byte to last byte three consecutive times with no
change between scans, then run license/project-policy/authority/historical
immutability/zero-Phase-12 checks and commit the closure file only.

After the closure commit, prove the product/media tree and publication bundle are
byte-identical to the post-publication PASS state, `main` is clean, and the only
new delta is the reviewed closure record. Do not rebuild or republish anything and
do not dispatch Phase 12.

## 28. Implementation discipline

For every implementation checkpoint after REV02 is explicitly approved/opened:

1. follow docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md;
2. follow docs/--W-A-R-N-I-N-G--.md;
3. keep PHASE-11-COMPLETE immutable;
4. do not amend admitted P11 evidence/media;
5. use direct main commits unless workflow authority requires otherwise;
6. three consecutive complete manual SoP scans of the exact on-disk candidate
   bytes, line-by-line from first byte to last byte, before check-in;
7. record `SCAN-1: CLEAN`, `SCAN-2: CLEAN`, `SCAN-3: CLEAN` against the same
   exact file/blob identity; any defect or byte change resets the count to zero;
8. run applicable policy/license/media/evidence/static/runtime gates;
9. use pinned project runtime and canonical drivers;
10. retain required Spectrum-native proof artifacts;
11. checkpoint/push only after gates PASS;
12. continue automatically through runbook gates when execution is later authorized;
13. STOP on an authority gap rather than hiding it in proof code;
14. never begin Phase 12.

## 29. Definition of DONE

REV02 reaches **operational completion** only when all of the following are
simultaneously true:

- REV01 remains FAILED-CLOSED and historically unchanged except that status marker;
- SDK 1.0.2 byte-level corpus pin/provenance PASS; moving SDK main/HEAD/tree may
  differ and is informational only;
- historical P11.39 SDK material unchanged;
- no pinned SDK source/header bytes changed, including verified target-loaded canonical
  source/header objects across each ordinary cc invocation;
- the failed REV01 write-capable publisher is quarantined before recovery product
  edits and cannot republish failed acceptance on push;
- ordinary current ZX-UX cc/as/ld production paths are generic, hash-bound to their
  source dependencies, and have no reachable source/object/corpus fingerprint
  dispatch;
- generality/metamorphic/held-out anti-specialization gates PASS;
- all exact SDK source/header constructs are proven legal frozen C48 before product
  defects are inferred;
- all 30 canonical SDK programs load through real tape/object handling;
- all 30 compile through the same ordinary product cc;
- all 30 emit genuine target-produced OBJ1;
- all 30 link through the same ordinary product ld;
- all 30 execute through normal ZX-UX process/shell behavior;
- all 30 exhibit actual source-defined behavior under behavior/visual contracts
  frozen before target execution/product correction;
- all 30 retain every SCR/PNG checkpoint used by acceptance, bound to exact native
  executables;
- SDK reference PNGs are actually compared under explicit predeclared per-program
  contracts;
- hanoi.c and queens8.c use the exact same ordinary executables in standalone and
  concurrent proofs;
- Hanoi/Queens both visibly compute at the required 1250-frame checkpoint and
  both independently demonstrate scheduler progress;
- full kernel source TAP rebuild uses ordinary product as/ld commands;
- host/TZX/native kernels are byte-identical for all 8192 bytes;
- kernel projection provenance proves no host binary/listing-byte circularity and
  ordinary as/ld anti-specialization PASS;
- final TZX consumes the retained native kernel bytes and passes real-time
  fastload/trap-disabled `LOAD ""` boot acceptance;
- worst-case compile/link/kernel/concurrency memory maps prove real 48K feasibility
  with ordinary allocation only;
- complete bundle deterministic double-build PASS with zero unclassified files;
- all strong negatives PASS;
- exact-head P11.48 regression PASS;
- Phase-11 aggregate regression PASS;
- all policy/license/media/evidence gates PASS;
- all admitted P0-P11 evidence/media unchanged;
- PHASE-11-COMPLETE unchanged;
- post-publication exact-head Gate P PASS on the exact publication commit;
- clean publication head;
- zero Phase-12 state.

After operational completion, perform Section 27.1 exactly: change this runbook
from OPEN to CLOSED, append final source commit, publication commit/tree,
post-publication workflow run, both frozen publication-tree digests,
bundle-manifest hash, TZX hash, SDK pin, kernel three-way hash, 30-program PASS
count, compiler/as/ld anti-specialization result, worst-case 48K memory anchors,
ordinary-tool session anchors, Hanoi/Queens executable hashes and 1250-frame PNG
hash, real-time loader anchor, immutable-scope digest, and final validation anchors.

REV02 is finally **DONE** only after those exact closure bytes receive three
successive clean complete scans, the closure-only commit is pushed, the
post-closure product/media tree is proven byte-identical to the publication PASS
state, current main is clean, and zero Phase-12 state is re-proven.

The closure commit may change only this runbook after the tested publication state.

Then STOP.

**DO NOT START P12.01.**

## 30. Review and authority re-entry gate

REV02 was explicitly reviewed and approved, then changed from DRAFT to OPEN in the
separate checkpoint required before Stage A. It remains OPEN throughout authorized
execution and may change from OPEN to CLOSED only through Section 27.1.

The review criteria remain:

- the REV17/REV08 historical-P11 and REV18/REV09 recovery authority hierarchy and fail-closed authority-gap path;
- quarantine of the failed write-capable REV01 publisher before product edits;
- the ordinary-product cc/as/ld command and production-dependency rule;
- compiler, assembler, and linker anti-specialization gates;
- the real-user developer proof session and stale-output exclusions;
- pre-execution frozen 30-program behavior/visual contracts;
- real 48K worst-case memory feasibility with no proof allocator/host spill;
- the strengthened Hanoi/Queens proof;
- the source-only/non-circular ordinary kernel self-rebuild;
- deterministic zero-unclassified-file double build;
- exact publication-commit and real-time final-TZX validation;
- closure-byte re-scan after the final status/anchor edit;
- the Phase-12 hard stop.

Any later authority-gap detour resets the review state for the affected continuation.
Before product work resumes, the exact revised OPEN bytes must receive three
successive complete manual first-byte-to-last-byte line-by-line scans with no new
gap/defect and no byte change between scans, plus the applicable policy, authority,
historical-immutability and zero-Phase-12 gates. Any review edit resets that count
to zero.

The admitted R18.00 transition and Section 8.6 satisfy the authority-re-entry
mechanism for C014 once these revised OPEN bytes pass that review.
