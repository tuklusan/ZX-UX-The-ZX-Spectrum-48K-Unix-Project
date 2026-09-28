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

# ZX-UX Phase-11 Expanded Pre-Release Runbook REV01

**Status:** OPEN  
**Scope:** post-Phase-11, pre-Phase-12 pre-release strengthening only  
**Hard stop:** DO NOT START PHASE 12

## 1. Purpose

This runbook replaces the current compact Phase-11 pre-release product bundle with
a substantially stronger non-certification pre-release baseline before Phase 12
final release assembly and distribution work begins.

The expanded pre-release must prove and retain three things together:

1. a genuine target-native full-kernel rebuild from a loadable textual assembler
   source projection, including the exact source text tape used for that rebuild
   and the resulting native kernel image;
2. target-native compile, link, execute, and visual proof for every C source in
   the pinned SDK release's complete `usr/src/examples/` and `usr/src/demos/`
   program corpus, together with ZX-UX-loadable source TAP sidecars; and
3. genuine cooperative multitasking proof with the pinned recursive `hanoi.c`
   and `queens8.c` workloads running concurrently on the same ZX-UX display,
   retained as deterministic screen evidence.

This is pre-release strengthening only. It does not reopen P11.01-P11.48, move
`PHASE-11-COMPLETE`, alter admitted Phase-11 certification evidence, or begin
P12.01.

## 2. Governing authority and immutable baseline

The execution baseline for this runbook is:

- project repository:
  `tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project`;
- Phase-11 completion tag:
  `PHASE-11-COMPLETE`;
- fixed Phase-11 completion commit:
  `263a203da3d54a398e8ac011284ae4195b1279c0`;
- active architecture:
  `docs/01-ZX-UX-ARCHITECTURE-REV17.md`;
- REV17 SHA-256:
  `d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8`;
- active implementation plan:
  `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md`;
- REV08 SHA-256:
  `97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c`;
- fast-loader migration runbook:
  `scratch/ZX-UX-FAST-LOADER-TZX-RELEASE-MIGRATION-RUNBOOK-REV01.md`,
  which must remain CLOSED;
- current compact Phase-11 pre-release TZX SHA-256:
  `fdb9dbf3ffb004163567ceda46831c4ee72ade7b1d308e22e45eeb4bd137a0ed`.

The current `v1/dist/media/P11.pre-release/` directory is a replaceable
non-certification pre-release product bundle. Its existing bytes remain
recoverable from Git history. Replacing that directory under this runbook does
not authorize any mutation of admitted P11.01-P11.48 evidence, admitted step
media, `v1/dist/certification/phase-11.json`, the active authority files, or the
`PHASE-11-COMPLETE` tag.

Every execution candidate must begin and end with zero Phase-12 state.

## 3. Mandatory SDK release pin

The SDK repository is READ-ONLY:

`tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit`

This runbook is explicitly re-pinned to the latest published SDK release
observed on 2026-09-27:

- release/tag: `1.0.2`;
- published timestamp: `2026-09-27T23:46:38Z`;
- tag target commit:
  `b1621338565ac3bd9d4eff4ecb5a2a77aee2ab6a`;
- release root tree:
  `ced96ea0a4b2f6cdd6080fc6f48e07738252af17`;
- main release package:
  `zx-ux-c48-sdk-1.0.2-b1621338565ac3bd9d4eff4ecb5a2a77aee2ab6a.zip`;
- package size: `15432637` bytes;
- package SHA-256:
  `8efd465928048b050c0cff9d93ddaf13127eabb12b837a33aa1c2c44e913a98a`;
- release metadata asset SHA-256:
  `668911b54f20625ea8a7efa5219261146e4ef5a76a2f055a7990f019d59f555d`;
- release SHA256SUMS asset SHA-256:
  `1981aa83cd1796894a380d2751cbc534483b244868d28c97f69c922f30672990`;
- SDK GUI/reference-evidence package:
  `c48-1.0.2-gui-evidence-b1621338565ac3bd9d4eff4ecb5a2a77aee2ab6a.zip`;
- GUI/reference-evidence package size: `3700008` bytes;
- GUI/reference-evidence package SHA-256:
  `ed9e2b2643481c3a58e46fdc054c3524fb7fe300827cb3e2c2b4c2833dd5ef01`.

The SDK marks `docs/images/**` as Git LFS. The Git-tree `*.png` bytes at this
release are LFS pointer records, not the image payloads. Reference-image
provenance therefore consists of both the exact pointer record (including LFS
OID and declared size) and the resolved PNG payload from the pinned GUI/evidence
release package. A Git LFS pointer record must never be treated as a PNG payload.

Release `1.0.2` also publishes a locked native source-transfer-tape corpus:
`compiler/source_tape_manifest.json` is Git blob
`8275c5b4985abb74d66a8eb43428fda9d8884809` and declares exactly 57
`.src.tap` files. The release package contains the pinned `c48srctap` builder
plus verifier tests. The 30 examples/demos in this runbook each have an SDK-published source
TAP carrying the exact local support header plus the exact C source bytes. Those
release-provided tapes are authoritative pre-release inputs; project code must
not silently regenerate different canonical tapes.

At this re-pin, SDK `main` is
`f8d44fd0aa7fe54d691bfd13638ba6e8802ad453`, three commits ahead of the
`1.0.2` tag target. Moving `main` is not an input to this runbook. The
formal `1.0.2` tag/release above is the byte authority.

If a newer formal SDK release is published before this runbook is executed,
STOP. Do not silently consume it. Create the next runbook revision or obtain an
explicit re-pin before continuing.

The exact SDK release package must be preserved durably before implementation
uses it, and every extracted byte used by the pre-release must be verified back
to this release pin. The SDK repository itself must never be modified.

## 4. Pinned SDK source corpus

At SDK release `1.0.2`, the complete program corpus in scope remains exactly
30 C programs, now split as 6 examples and 24 demos, plus three direct support
headers.

### 4.1 Examples

Exact `usr/src/examples/` program set:

- `argv.c`
- `colors.c`
- `graphics.c`
- `hello.c`
- `maze.c`
- `udg.c`

Direct support header:

- `exapi.h`

### 4.2 Demos

Exact `usr/src/demos/` program set:

- `city.c`
- `dizzy4k.c`
- `firework.c`
- `forest.c`
- `galaxy.c`
- `goblet.c`
- `hanoi.c`
- `julia.c`
- `kaleido.c`
- `mandel.c`
- `mobius.c`
- `moire.c`
- `morph3d.c`
- `ocean.c`
- `orrery.c`
- `plasma.c`
- `queens8.c`
- `raymaze.c`
- `spriteanim.c`
- `sprites.c`
- `terrain.c`
- `torus.c`
- `tunnel.c`
- `warp.c`

Direct support headers:

- `demoapi.h` for the ordinary visual demos;
- `recapi.h` for the recursive `hanoi.c` and `queens8.c` demos.

Pinned recursive source identities:

- `hanoi.c` Git blob:
  `57e9419a56fca83656f574de6fa4d994b5eadae1`;
- `queens8.c` Git blob:
  `38cff8912e1bced21c01f3ee050063ce19afe35e`;
- `recapi.h` Git blob:
  `29e170e5c10aee80f09ed9eb7f273b8c9c9aedbc`.

The release trees are:

- `usr/src/examples/`:
  `042a1b302646957c223b955a9d967ca690a2b33f`;
- `usr/src/demos/`:
  `c8363270a6da92661f43650933d5b4848521f54d`.

The pinned `compiler/source_tape_manifest.json` supplies exactly one canonical
release source tape for each of these 30 programs. Example tapes carry
`exapi.h`; ordinary demo tapes carry `demoapi.h`; the recursive Hanoi and
8-Queens tapes carry `recapi.h`. For `spriteanim.c`, that manifest preserves
the SDK source path and bytes but maps the target source object name to
`sprani.c` so the ZX-UX 10-byte namespace limit is respected.

No program may be skipped, xfail-marked, substituted, shortened, rewritten, or
silently replaced by a project-authored lookalike merely to make native `cc`
pass.

## 5. Historical Phase-11 SDK import must remain immutable

P11.39 admitted the original REV08 SDK reference at commit
`84d144de2721cda5075c3a6610a422663b5e2f77` under:

`v1/tests/compiler/sdk-reference/sdk/`

That historical import and its provenance are part of the admitted Phase-11
record and must remain byte-for-byte unchanged.

The expanded pre-release must therefore extend the project SDK-reference area
without editing or replacing the P11.39 tree. Use a separate, clearly named
pre-release reference subtree, recommended:

`v1/tests/compiler/sdk-reference/pre-release-1.0.2/`

It must preserve original SDK relative paths and bytes for the pinned examples,
demos, direct headers, the 30 in-scope release-provided `.src.tap` files, the
pinned source-tape manifest/tooling needed to verify them, and the exact Git LFS
pointer records for reference images, with a project-authored provenance manifest
binding every imported file to SDK release `1.0.2`, commit
`b1621338565ac3bd9d4eff4ecb5a2a77aee2ab6a`, and the release package
SHA-256. Resolved reference PNG payloads belong in the pre-release media bundle,
with each payload bound to its SDK LFS pointer OID/size and to the pinned
GUI/evidence package.

If project license/header machinery needs an exemption for exact upstream bytes,
the exemption must be exact-path and exact-identity fail-closed. It may not
weaken scanning outside the pinned imported subtree.

## 6. Non-negotiable invariants

The entire runbook is fail-closed around these rules:

1. REV17/REV08 stay byte-identical.
2. All admitted P0-P11 certification evidence and admitted retained step media
   stay byte-identical.
3. `PHASE-11-COMPLETE` remains fixed at
   `263a203da3d54a398e8ac011284ae4195b1279c0`.
4. The fast-loader migration runbook remains CLOSED.
5. No Phase-12 source, workflow, qualification, evidence, media, admission,
   activation, dispatch, or speculative implementation is created.
6. The official boot/pre-release product remains TZX-only under REV17.
7. TAP files retained or created by this runbook are source-transfer/evidence
   sidecars only; they are not a TAP counterpart of the official boot
   distribution.
8. The expanded pre-release must revalidate P11.48 at the exact current source
   head without rewriting admitted historical P11.48 evidence.
9. SDK release bytes are reference/oracle material. REV17/REV08 remain the
   target authority where the SDK host implementation differs.
10. Exact SDK `.c` source bytes are the native compile inputs. Any support
    mapping must preserve those source bytes.
11. A discrepancy requiring a new C48 language feature, ABI change, object
    format change, or release-contract change outside REV17/REV08 is blocking;
    do not smuggle it into pre-release support code.
12. A screenshot is supplemental evidence, never the sole proof that a native
    compile/link/run succeeded.
13. No host compiler, host linker, Python VM, prebuilt C48B1 executable, or
    host-preconstructed OBJ1/MEX1 may substitute for a required native
    `cc -> OBJ1 -> ld -> execute` path.
14. The full-kernel native build must start from source text loaded through the
    retained source TAP and must not start from host-injected NSP1, OBJ1, MEX1,
    or kernel bytes.
15. The resident executing kernel must never be overwritten by the native
    rebuild output.

### 6.1 Pre-release proof session is not Phase-12 distribution assembly

This runbook must not solve its proof problem by designing the final Phase-12
post-kernel M48O distribution order. The official Phase-11 boot TZX may remain
kernel-only. Its real-time `LOAD ""` -> fast loader -> exact kernel -> `0xE003`
acceptance remains a separate mandatory proof.

For the native source-tape/kernel/compiler demonstrations, use a deterministic
Phase-11 target proof session derived from the exact current kernel and the
admitted Phase-11 tool/runtime implementations. Existing P11 target-harness/SNA
techniques may preload admitted kernel/tool/runtime support needed to exercise the
target, but they may not preload, synthesize, or substitute any source payload,
OBJ1, MEX1, executable, native rebuild output, or screen result under test.

Every kernel/C source payload covered by this runbook must enter the target through
its retained TAP using the real target cassette/M48O reader, become a validated
ZX-UX namespace object, and only then be consumed by native `as` or `cc`. Every C
executable proof must launch through the admitted ZX-UX executable/process path,
not by a host-directed jump into preloaded application bytes. Host code may
orchestrate Fuse, inspect results, render retained screen RAM, and compare hashes;
it may not perform the required target compile/link/execute work.

Any proof-session fixture added for this purpose is non-product validation
infrastructure. It must be deterministic and retained/hash-bound as evidence where
needed, and it must never become or imply the final Phase-12 release layout.

## 7. Stage A - establish exact execution baseline

Before changing implementation or media:

1. Re-read the mandatory workflow/warning/REV17/REV08 authorities in project
   order.
2. Verify `PHASE-11-COMPLETE` and the fixed completion commit.
3. Verify Phase-11 aggregate PASS and P11.48 PASS.
4. Verify the current compact pre-release hash and manifest.
5. Verify the fast-loader migration runbook is CLOSED.
6. Prove zero Phase-12 state.
7. Record current `main`, tree, and complete planned changed-file set.
8. Verify the existing `tools/p11-prerelease/` and
   `.github/workflows/p11-prerelease-build.yml` are the only active Phase-11
   pre-release publisher path.
9. Verify historical P11.39 SDK import tree identity before any new SDK material
   is added.

**Gate A:** exact baseline identities PASS and no historical/canonical bytes are
scheduled for mutation.

## 8. Stage B - acquire and preserve pinned SDK release

1. Acquire the exact SDK `1.0.2` release package named in Section 3.
2. Acquire the exact GUI/reference-evidence package, release metadata, and
   SHA256SUMS asset named/pinned in Section 3.
3. Verify exact package sizes and SHA-256 values before extraction.
4. Verify tag `1.0.2` resolves to the pinned commit and root tree.
5. Extract release inputs to isolated workspaces.
6. Run the pinned SDK release verifier/oracle and require its locked
   `compiler/release_expectations.json` contract to report version `1.0.2`,
   test count `371`, and PASS.
7. Verify `compiler/source_tape_manifest.json` declares exactly 57 release
   source tapes and that the release package manifest contains every declared
   `.src.tap` plus the pinned `c48srctap` builder/support files.
8. Inventory and hash all 30 in-scope example/demo C sources, the three direct
   support headers, their 30 release-provided source tapes, and all required
   reference-image LFS pointer records.
9. Independently decode every in-scope release source tape and prove that its
   M48O objects reconstruct the exact pinned local header and C source bytes,
   including the manifest-declared target names.
10. Resolve each required reference PNG from the pinned GUI/evidence package and
    verify its bytes against the pointer OID and declared size.
11. Preserve the exact release inputs durably in a project-approved provenance
    location, or preserve equivalent exact immutable copies whose hashes are
    checked before every use.
12. Populate the separate pre-release SDK reference subtree without changing the
    historical P11.39 import.
13. Add a provenance manifest with exact SDK path, size, Git blob/LFS identity
    where applicable, and SHA-256 for every imported/resolved byte.

**Gate B:** the exact pinned SDK release is reproducible locally, the full
30-program source set and its 30 canonical release source tapes are present and
independently verified, and the original P11.39 import is unchanged.

## 9. Stage C - textual native kernel-source projection

The existing REV17 NSP1 semantic-source proof remains valuable but does not by
itself satisfy this expanded pre-release's textual-source requirement.

Create one deterministic source-only textual assembler projection from the
canonical ZX-UX kernel source. The projection must:

- be plain LF-terminated ZX-UX native assembler source;
- contain semantic Z80 source/directives, not a dump of preassembled kernel
  bytes;
- resolve host-only include/macro conveniences deterministically without
  importing machine-code bytes from the host listing or `kernel.bin`;
- use only already admitted REV17/P10 native assembler lexical, directive,
  expression, symbol, and documented-opcode contracts; no private new source
  syntax or undocumented opcode may be invented for this proof;
- be accepted by the ordinary admitted native textual-assembler path rather than
  only by the NSP1 semantic-record decoder;
- assemble into genuine OBJ1;
- link through the admitted native linker into the exact fixed 8192-byte kernel;
- contain enough provenance to map each projected statement back to canonical
  source file/line or an explicitly generated source directive;
- be deterministic byte-for-byte for identical canonical source;
- fit the version-1 M48O logical-object limit if represented as one ASM object.

The preferred retained text name is:

`kernel-native-source.asm`

The preferred target object name is:

`kernel.asm`

If one exact ASM object cannot remain within the version-1 32768-byte logical
M48O limit without encoding preassembled machine-code payload, STOP. Do not
silently split the projection, invent a new tape format, or weaken the
source-only requirement. Record the measured size and obtain an explicit design
decision.

A defect in native `as` exposed by source that is already within its frozen
REV17/P10 contract may be fixed through the normal exact-head workflow. A need for
new public assembler syntax, directives, undocumented opcodes, or object semantics
is a canonical-design discrepancy and is blocking.

**Gate C:** deterministic textual source projection exists, is source-only, is
within the existing object/tape/assembler contract, and can be parsed by the
ordinary native textual `as` path.

## 10. Stage D - build and validate the kernel source TAP

Create a source-transfer TAP sidecar containing the exact textual projection as
one ordinary ZX-UX M48O object:

- object type: `ASM` / type 4;
- target directory: `USERHOME` / target 5;
- exact base name: `kernel.asm`;
- canonical LF line endings;
- RAW M48O transport: flags 0, codec 0, physical length equal to logical length.

The TAP must use the existing M48O 32-byte header, CRC-16/CCITT-FALSE, and
<=512-byte payload chunking contracts carried in ordinary Spectrum ROM-compatible
TAP data blocks. Independently validate TAP framing/lengths, ROM flag/checksum
bytes, M48O header CRC, logical payload CRC, chunk coverage, and exact EOF. It is
source-transfer evidence, not boot media.

Independently decode the finished TAP and require exact logical-byte identity
with `kernel-native-source.asm`, including exact length and SHA-256.

Retain all three:

- `kernel-native-source.asm`;
- `kernel-native-source-map.json`;
- `kernel-native-source.tap`.

**Gate D:** the retained TAP independently reconstructs the exact native
assembler source bytes and passes all M48O framing/CRC checks.

## 11. Stage E - genuine in-system native full-kernel rebuild

First independently re-prove the exact expanded pre-release boot TZX through the
real REV17 path to `0xE003`. Then establish the Section 6.1 deterministic
Phase-11 target proof session. Without host injection of the kernel source
payload into target RAM:

1. load `kernel-native-source.tap` through the real ZX-UX cassette/M48O path into
   the current user's `USERHOME` namespace;
2. prove the resulting RAM object is exact type ASM, exact name `kernel.asm`,
   and byte-identical to the retained source text;
3. invoke native `as` on that loaded source and require a genuine native OBJ1;
4. invoke native `ld` on the native OBJ1 and produce the fixed 8192-byte kernel
   image in non-resident output storage/RAM;
5. prove the executing resident kernel at `0xE000-0xFFFF` was not overwritten;
6. retain the genuine native OBJ1 and the natively produced 8192-byte kernel as
   `kernel-native.obj1` and `kernel-native.bin`;
7. independently compare every byte offset `0..8191` among:
   - host-built kernel;
   - kernel independently reconstructed from the pre-release TZX;
   - natively rebuilt kernel from the loaded textual source TAP;
8. require all three SHA-256 values to be equal;
9. mutate one source-level semantic input in a controlled negative run, rebuild
   natively, and require the equality proof to fail;
10. after the positive native identity proof, rebuild the published pre-release
    TZX using the retained `kernel-native.bin` as the kernel input, independently
    reconstruct its embedded kernel, and require byte identity with the same
    retained native kernel. Since the native and host kernels are required to be
    identical, this must not create a divergent kernel image.

The older NSP1 proof remains an independent regression, but only this loaded
textual-source path closes the expanded pre-release native-kernel gate. No final
Phase-12 post-kernel object ordering is introduced by this step.

**Gate E:** source TAP -> ZX-UX object -> native `as` -> OBJ1 -> native `ld` ->
8192-byte kernel PASS, with exact three-way identity, mutation negative PASS, and
a rebuilt pre-release TZX that consumes and embeds the retained native kernel.

## 12. Stage F - pinned SDK source-TAP corpus for native programs

Release `1.0.2` already contains the authoritative ZX-UX source-transfer TAP
for every in-scope example/demo program. Preserve and use those exact release
bytes from `usr/bin/examples/*.src.tap` and `usr/bin/demos/*.src.tap`; do not
replace them with project-authored canonical tapes.

Each canonical release tape is governed by the pinned
`compiler/source_tape_manifest.json` and carries RAW M48O version-1 objects
targeted at `USERHOME`:

- each `.c` source object is type `C` / type 5;
- each local `.h` support object is type `TXT` / type 1;
- logical source/header payload bytes are exactly the pinned SDK bytes;
- example tapes carry `exapi.h`;
- ordinary demo tapes carry `demoapi.h`;
- `hanoi.src.tap` and `queens8.src.tap` carry `recapi.h`.

The M48O/namespace base-name limit is 10 bytes. The pinned SDK source-tape
manifest already resolves the only in-scope source-name collision:

`usr/src/demos/spriteanim.c -> sprani.c`

The retained host source path and bytes remain exactly `spriteanim.c`. Use
`sprani.obj` for the target OBJ1 name and `sprani` for the target executable
name. All other program source names remain the exact lower-case SDK filenames;
derived target OBJ/executable names must also satisfy the ZX-UX namespace limit.
The provenance/program matrix must record SDK path, retained host filename,
manifest target source name, target OBJ name, and target executable name.

Each of the 30 canonical release TAPs must be independently decoded and checked
against the pinned source/header bytes, including TAP framing/ROM checksums and
all M48O header/payload checks. The project may run the pinned `c48srctap`
builder in an isolated comparison workspace, but any regenerated tape is only a
reproducibility cross-check: it must either match the release tape exactly or
fail the gate. It never replaces the release-provided canonical bytes.

**Gate F:** every native compile input is obtained from its retained,
independently verified SDK `1.0.2` release source TAP without changing SDK
source/header bytes or manifest target names.

## 13. Stage G - native compile/link/run matrix for all SDK examples and demos

For each of the 30 C programs in Section 4, perform a real target-native
lifecycle from source loaded into ZX-UX:

`release source TAP -> M48O TXT header + C source objects -> native cc -> OBJ1 -> native ld -> executable -> run`

Each program proof starts from a clean deterministic Section-6.1 proof session,
loads only its required canonical release source tape, and may not reuse compiler output or
application state from another program. Retained OBJ1/MEX1 bytes must be extracted
after native creation from the validated target object/image; host tooling may copy
and hash them but may not construct or repair them.

Required per-program evidence:

- pinned SDK release path and source SHA-256;
- source TAP path and SHA-256;
- independently reconstructed TAP logical source SHA-256;
- direct local-header dependency identity where applicable;
- native compiler exit/status;
- native OBJ1 size, SHA-256, target object name, and retained OBJ1 bytes;
- native linker exit/status;
- native MEX1/BIN executable size, SHA-256, target object name, and retained
  executable bytes;
- launch through admitted ZX-UX `SYS_SPAWN`/`SYS_EXEC` or the shell-visible
  equivalent, followed by process start/exit or bounded running-state proof;
- deterministic runtime checkpoint;
- retained exact 6912-byte SCR screen state;
- retained PNG visual proof rendered from that SCR;
- explicit PASS/FAIL result.

No program may be marked PASS from host SDK execution alone, from a direct
host-directed jump into application bytes, or from a prebuilt SDK C48B1 image.

If an exact pinned SDK source uses a facility outside REV17 C48, first determine
whether it is only a documented SDK host/target support-header divergence. A
target support mapping may be added only when it stays within existing REV17
language/API contracts and leaves the pinned `.c` bytes unchanged. If success
would require widening C48 or changing the ABI, stop at that program.

**Gate G:** all 30 exact pinned SDK programs compile, link, and run natively on
ZX-UX with no skip or source rewrite.

## 14. Stage H - deterministic PNG visual proof

Every program in Gate G receives a retained target-native 6912-byte Spectrum
`.scr` capture and a PNG deterministically rendered from those exact screen bytes.

Capture timing is defined in PAL 50 Hz frames rather than vague wall-clock
sleep:

- animated/continuously running programs: default capture at 500 frames
  (nominally 10 seconds) after the program reaches its first stable running
  checkpoint;
- programs that terminate before 500 frames: capture the final meaningful
  stable screen immediately before exit and record the exact frame;
- programs requiring arguments/input: use one fixed recorded invocation/input
  script derived from pinned SDK documentation/source expectations;
- `argv.c` uses one fixed non-empty argument string and records it;
- static programs capture after deterministic completion of their visible
  output.

The capture harness must record the exact frame/checkpoint used. Read the real
Spectrum display file from target/emulator screen RAM, require exactly 6912 bytes,
and convert those bytes to PNG deterministically with a pinned project renderer.
Do not use an X11/window screenshot as the canonical pixel source.

Where the pinned SDK release provides a reference image path under
`docs/images/examples/` or `docs/images/demos/`, retain the exact LFS pointer
identity, resolve the actual PNG through the pinned GUI/evidence release package,
verify payload SHA-256/size against the pointer, and record a program-specific
visual comparison. Pixel identity is required only when the same rendering/time
contract makes it meaningful; otherwise compare explicit geometry/text/color/state
invariants and retain both resolved reference and native PNGs.

A pretty picture with no native process proof is not a PASS.

**Gate H:** 30 native SCR+PNG proofs exist, each bound to a successful native
compile/link/run record and a deterministic capture point.

## 15. Stage I - recursive Hanoi + 8-Queens concurrent proof

Use the exact pinned SDK `hanoi.c`, `queens8.c`, and `recapi.h` bytes from release `1.0.2`.
They intentionally use different screen halves and explicitly yield/sleep.

1. Load both exact source programs and required support material through their
   retained source TAP sidecars.
2. Compile and link both with native `cc` and native `ld`.
3. Start both native executables through the admitted ZX-UX process path in the
   same ZX-UX session so both processes are alive concurrently.
4. Establish a deterministic epoch when both processes are runnable and have
   completed their initial screen setup.
5. Let the cooperative scheduler run both for exactly 1250 PAL frames
   (nominally 25 seconds) from that epoch.
6. Capture the full Spectrum screen as raw screen bytes and PNG.
7. Prove the screenshot contains meaningful current output from both the Hanoi
   left-side workload and the 8-Queens right-side workload.
8. Independently prove both processes made progress during the interval:
   scheduler/process-state evidence must show each process ran/yielded after the
   common epoch; screenshot presence alone is insufficient.
9. Verify neither workload wrote outside its owned screen half according to the
   pinned source's bounds/invariants.
10. Retain the exact process launch order, PIDs/state checkpoints, frame count,
    screen hashes, and PNG hash.

Preferred retained names:

- `multitasking/hanoi-queens8-1250f.scr`;
- `multitasking/hanoi-queens8-1250f.png`;
- `multitasking/hanoi-queens8.json`.

This is a specific Phase-11 cooperative-workload demonstration, not certification
of the later general Phase-12 shared-screen/foreground-ownership gate.

**Gate I:** both native C workloads are simultaneously alive, both demonstrably
progress, both share the one physical ZX Spectrum screen correctly, and the
1250-frame full-screen SCR+PNG proves the combined display.

## 16. Stage J - expanded pre-release media layout

The replacement `v1/dist/media/P11.pre-release/` bundle must be self-describing.
Recommended minimum layout:

```text
P11.pre-release/
  README.txt
  pre-release.json
  zx-ux-phase11-pre-release.tzx
  kernel/
    kernel-native-source.asm
    kernel-native-source-map.json
    kernel-native-source.tap
    kernel-native.obj1
    kernel-host.bin
    kernel-tzx-embedded.bin
    kernel-native.bin
    kernel-native-build.json
  sdk/
    SDK-RELEASE.json
    SOURCE-TAPE-MANIFEST.json
    TARGET-NAME-MAP.json
    sources/
      examples/
      demos/
      headers/
    tapes/
      examples/
      demos/
    native/
      examples/
      demos/
    proof/
      examples/
      demos/
    reference-lfs/
      examples/
      demos/
    reference-png/
      examples/
      demos/
  multitasking/
    hanoi-queens8-1250f.scr
    hanoi-queens8-1250f.png
    hanoi-queens8.json
```

The exact final layout may be adjusted only to remove duplication or satisfy
existing project retention machinery. It may not omit any required logical
artifact.

`pre-release.json` must bind every retained bundle file except itself by relative
path, size, and SHA-256 and must include:

- exact current project source commit;
- `PHASE-11-COMPLETE` fixed identity;
- REV17/REV08 hashes;
- Phase-11 aggregate/P11.48 identities;
- prior compact pre-release TZX identity being superseded;
- pinned SDK release/tag/commit/tree/package identity;
- pinned 57-tape source-tape manifest identity and the exact 30 in-scope release TAP hashes;
- complete 30-program matrix and collision-free target-name mapping;
- kernel host/TZX/native three-way hashes;
- kernel textual source, source map, source-TAP, native OBJ1, and native kernel
  hashes;
- source-TAP reconstruction PASS results;
- per-program native compile/link/run PASS results plus retained OBJ1/executable
  hashes;
- per-program SCR/PNG hashes and capture frames;
- SDK reference-image LFS pointer OIDs/sizes and resolved PNG hashes;
- concurrent Hanoi/Queens process/frame/screen proof;
- deterministic bundle-build identity;
- zero-Phase-12-state PASS.

To avoid an impossible self-referential hash, `pre-release.json` is excluded from
its own file table and bundle digest. Define the bundle digest deterministically
over the sorted file table as UTF-8 relative path, NUL, decimal size, NUL, lowercase
SHA-256, newline for every listed file. Record the final `pre-release.json` SHA-256
separately in the publication/closure record and Git commit.

## 17. Stage K - deterministic construction and negative gates

Build the complete candidate bundle twice from the same exact source head and
pinned inputs in separate clean workspaces.

Require byte identity for every deterministic artifact, including:

- main pre-release TZX;
- kernel textual projection;
- kernel source TAP;
- all 30 retained SDK release source TAPs, with any pinned-tool regeneration required to match those canonical bytes;
- all retained native OBJ1/executable outputs;
- all canonical SCR captures;
- generated manifests/reports;
- PNGs rendered from deterministic SCR bytes.

The canonical PNG writer must be deterministic from the retained SCR bytes and
must omit or normalize nondeterministic container metadata. Never alter screen
pixels to manufacture equality.

Mandatory negatives include at least:

- wrong SDK package hash rejected;
- wrong SDK tag/commit/tree rejected;
- omitted SDK source rejected;
- changed SDK source byte rejected;
- unresolved/mismatched SDK LFS pointer or PNG payload rejected;
- target-name alias collision or >10-byte target name rejected;
- skipped native compile rejected;
- host-only execution substituted for native execution rejected;
- source TAP CRC/content mismatch rejected;
- kernel source projection containing preassembled kernel payload rejected;
- native kernel output overwriting resident kernel rejected;
- kernel controlled mutation breaks equality;
- screenshot without native process proof rejected;
- missing one of the 30 SCR or PNG proofs rejected;
- only one of Hanoi/Queens making progress rejected;
- screen-half violation rejected;
- any Phase-12 path/state rejected.

**Gate K:** deterministic double build PASS and every controlled negative fails
closed for the intended reason.

## 18. Stage L - exact-head validation and publication

Before publication, on one unchanged candidate head:

1. run three consecutive full SoP scans over every modified source, workflow,
   tool, test, provenance, and manifest-template byte;
2. run license-header, project-policy, media-retention, authority/evidence, and
   applicable static/runtime gates;
3. re-run exact-head P11.48 build/test acceptance without rewriting admitted
   historical evidence;
4. run Phase-11 aggregate validation;
5. run the expanded kernel source-TAP/native-rebuild gates;
6. run real-time fast-loader acceptance against the final native-kernel-built TZX
   with loader acceleration/fastload/traps disabled, plus the existing
   detect-loader compatibility mode;
7. run all 30 SDK native compile/link/run/SCR/PNG gates;
8. run the concurrent Hanoi/Queens gate;
9. run deterministic complete-bundle rebuild;
10. prove historical admitted evidence/media are unchanged;
11. prove `PHASE-11-COMPLETE` is unchanged;
12. prove zero Phase-12 state.

Publish only the exact tested bundle. Replace
`v1/dist/media/P11.pre-release/` atomically from staged tested bytes. Never
construct one set of bytes for testing and a second set for publication.

The pre-release workflow must end after publication and validation. It must not
dispatch or synthesize a P12 candidate.

**Gate L:** exact published bytes equal exact tested bytes and all project gates
PASS.

## 19. Stage M - final repository sanity pass

After publication:

1. verify the only official Phase-11 boot pre-release remains TZX;
2. verify all `.tap` files under the expanded bundle are clearly classified as
   source-transfer/evidence sidecars, not release boot products;
3. verify current pre-release documentation explains how to reproduce the
   native kernel build and each SDK compile/run proof;
4. verify every retained source byte has provenance;
5. verify every SCR+PNG pair has a native execution record and capture point;
6. verify the concurrent screenshot is bound to both running process proofs;
7. verify the old compact pre-release remains recoverable through Git history
   and is not misidentified as current;
8. verify no stale manifest claims the compact three-file bundle is still the
   complete current pre-release;
9. verify no Phase-12 state exists;
10. require clean current `main`.

**Gate M:** repository and media tell one coherent pre-Phase-12 story.

## 20. Required implementation discipline

For every implementation checkpoint under this runbook:

1. follow `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md`;
2. use direct `main` commits unless a checked-in workflow requires otherwise;
3. perform three consecutive unchanged-byte SoP scans before check-in;
4. run license, project-policy, media-retention, authority/evidence, and relevant
   runtime gates;
5. preserve durable recovery checkpoints;
6. never rewrite admitted historical evidence;
7. fail closed on SDK, source, native-execution, visual, or provenance mismatch;
8. stop immediately if implementation would require a new canonical
   architecture/plan requirement rather than pre-release proof/support.

## 21. Definition of DONE

This runbook is DONE only when all of the following are simultaneously true:

- SDK release `1.0.2` is pinned by exact tag, commit, tree, package size, and
  SHA-256;
- the historical P11.39 SDK import is unchanged;
- the pinned source-tape manifest declares 57 release tapes and the exact 30
  in-scope example/demo release tapes are retained and independently verified;
- all 6 pinned examples and all 24 pinned demos are present with exact source
  provenance;
- every one of the 30 programs loads from its retained canonical SDK `1.0.2` ZX-UX source TAP,
  compiles with native `cc`, emits native OBJ1, links with native `ld`, and runs
  on ZX-UX;
- all 30 have retained deterministic SCR+PNG visual proof bound to native
  execution;
- the full kernel is rebuilt from retained textual assembler source loaded
  through the retained ZX-UX source TAP;
- host-built, TZX-embedded, and text-source/native-built kernels are exactly
  identical for all 8192 bytes;
- the native-built kernel, textual source, source map, source TAP, genuine native
  OBJ1, and build report are retained in the pre-release media;
- the published pre-release TZX is built from the retained native kernel bytes
  and independently reconstructs those same bytes;
- `hanoi.c` and `queens8.c` run concurrently, both make verified scheduler
  progress, and the 1250-frame full-screen PNG shows both workloads together;
- the complete expanded bundle is deterministic and recursively hash-bound,
  including target-name aliases and SDK LFS/reference-image provenance;
- exact-head P11.48 and Phase-11 aggregate validation PASS;
- all policy/license/media/evidence gates PASS;
- all admitted P0-P11 evidence/media and active authorities remain unchanged;
- `PHASE-11-COMPLETE` remains fixed at its Phase-11 completion commit;
- current `main` is clean;
- zero Phase-12 state exists.

At that point mark this runbook CLOSED with final source commit, workflow run,
bundle manifest hash, main TZX hash, SDK pin, kernel three-way hash, 30-program
PASS count, multitasking PNG hash, and final validation anchors.

Then stop.

**DO NOT START P12.01.**
