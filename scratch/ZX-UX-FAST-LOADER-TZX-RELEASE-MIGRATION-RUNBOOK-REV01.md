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

# ZX-UX Fast-Loader TZX Release/Pre-Release Migration Runbook REV01

**Status:** OPEN — one-shot coordination plan. This scratch document is not canonical authority.

**Phase isolation:** Complete only the release/pre-release tape-generation migration and its authority transition. This runbook MUST NOT implement or advance a Phase-11 step. The accidental P11.01/P11.02 start was rolled back before this runbook became the proposed goal; execution therefore begins from a no-Phase-11 baseline. Any new P11 workflow, source, evidence, media, admission or activation appearing during this migration is a blocker and must be removed/reverted before work continues.

**Protected checkpoint:** `PHASE-10-COMPLETE` remains fixed at `8360b0c5817738b01dc4b75bb64b12d77341adcd`. Previously admitted Phase-0-through-Phase-10 certification evidence and retained step media remain immutable historical records.

## 1. Purpose and scope

Replace the current production/pre-release Spectrum cassette-image construction path with the portable ZX-UX fast-loader package preserved beside this runbook. The end-state product distribution is TZX-only and has no separate 6912-byte SCREEN$ loading image. The fast loader owns the visible loading display, loads an exact rebuilt 8192-byte ZX-UX kernel into `0xE000-0xFFFF`, and hands control to the real ZX-UX boot entry at `0xE003`.

This is a release/control-plane migration, not a redesign of ZX-UX kernel, syscall, process, filesystem, shell, assembler/linker, MEX1, OBJ1, or userland behavior. No target implementation source is to be changed merely to accommodate the loader. The fixed kernel range and entry remain `0xE000-0xFFFF` and `0xE003`.

The intended changed-file boundary is deliberately narrow: release/pre-release builder source, release/pre-release workflows and generated distribution artifacts; the explicitly obsolete current-tree loading-screen asset; the minimum new authority/authority-transition files required to legalize that release transport change; and the minimum operational documentation/infrastructure selectors that must recognize the new authority epoch. Core ZX-UX target source and admitted evidence are out of scope. Historical validators/replay machinery remain historical unless an epoch-routing defect makes a narrowly scoped compatibility change unavoidable.

The migration necessarily includes a new architecture/implementation authority epoch because current REV16/REV07 explicitly require a separate SCREEN$ file and final TAP+TZX production output. Those frozen files MUST NOT be edited in place.

## 2. Preserved replacement package

Preserve the supplied package byte-for-byte at:

`scratch/ZX-UX-LOADER-1.0.0-portable.zip`

Required outer SHA-256:

`4c83a681f718192db9ebb32f0c8bc565baf2e68eb85de480322a1102d32f00c7`

The package is provenance/reference input only. The active release workflow must not unzip and execute arbitrary files directly from `scratch/`; reviewed components are promoted into canonical release-tooling locations during this runbook.

Before any migration work, verify the package's `PORTABLE-MANIFEST.sha256` completely. The supplied package currently verifies every listed member.

Important package identities:

- portable release tag: `ZX-UX-LOADER-1.0.0`;
- source commit recorded by package: `99c948feb2893e369055879ddf82aa0105bfe541`;
- tree recorded by package: `44d4a388bb300032c10c0c3813431ddbddcfe542`;
- package seed TZX SHA-256: `7ffe2f90b58e87a19a090ca0e0f1323605754af7d8809f3f051662f9faaec6f1`;
- package demonstration TZX SHA-256: `9a77617b16d04c767c5895261ca9a823b57060e642adadffa58b34cbfcd7d642`;
- seed/demo 8192-byte dummy payload SHA-256: `0e59ef9290ffc4391b0ae999177cd9d7d9eafb6fcd86a45b13f9a4bd0b08c9ce`;
- assembled display/beep hook SHA-256: `f1c6b88998488c552bbf5358cfcf32494de4687a2f0cfb7bcbe37a71cf6c00ef`;
- construction assembler reference: Pasmo `0.5.3-7`.

## 3. Deep package findings that govern the migration

The package is a valid deterministic fast-loader template, but its current `build.py` is not yet a product-kernel injector.

1. The immutable seed is base64-encoded TZX. The builder verifies its exact SHA-256 before use.
2. The seed contains one TZX text-description block, two standard-speed BASIC blocks, 24 pause blocks, and 48 generalized-data (`0x19`) blocks.
3. The 48 generalized-data blocks form 24 header/payload pairs. The payload chunks concatenate to exactly 8192 bytes: the first eight chunks are 342 bytes each and the remaining sixteen are 341 bytes each.
4. The seed/demo payload covers exactly `0xE000-0xFFFF`. The package's final decoded header tuple is checked as length `341`, temporary/load value `0x9000`, destination value `0xFEAB`, and post-block dispatch `0xE003`.
5. The current builder extracts the dummy 8 KiB payload from the seed and then preserves the entire turbo tail byte-for-byte. Therefore replacing `output/dummy_e000_8k_idle.bin` does nothing. Product migration must change the generalized-data payload blocks themselves.
6. Each generalized header contains a payload-dependent check/CRC byte. The current package names that field `_crc` but does not calculate it because it never changes the turbo payload. The production injector MUST determine and implement the exact algorithm rather than blindly copying the dummy value.
7. The BASIC-resident patching logic is deliberately surgical: it preserves the seed's initial BASIC `CLS`, removes only the later/final BASIC `CLS`, inserts the loader hook, and installs exactly 24 rows × 32 bytes of loading/status text.
8. The machine-code hook is assembled at `0x5E4F`, is currently exactly 234 bytes, initializes the full bitmap/attribute display itself, retains the four red/yellow/green/cyan PAPER cells, emits exactly one startup beep, and returns to the fast loader's normal final dispatch.
9. There is therefore no need for `v1/assets/loading.scr`, no `SCREEN$` block, and no `zx48uxscr` logical file in the new product distribution.
10. The package's CI performs a real-time Fuse tape test with accelerated/automatic tape traps disabled and proves execution reaches `0xE003`. The ZX-UX integration must retain an equivalent real-time proof and additionally prove that the bytes resident at `0xE000-0xFFFF` are the rebuilt ZX-UX kernel, not the seed dummy payload.
11. The package pins Python 3.12.3 as its reference environment, but the ZX-UX project already owns a stricter pinned Python/runtime environment. Do not downgrade ZX-UX Python merely to match the package. Prove the reviewed builder under the current project-local Python.
12. The package uses Pasmo for construction. Pasmo is the only new construction tool identified by the package. Fuse/libspectrum/ROM/X11 dependencies in the package are validation dependencies and should not automatically replace ZX-UX's already-pinned Fuse/libspectrum/ROM stack.

## 4. Non-negotiable migration invariants

The one-shot execution is fail-closed around these invariants:

- REV16 and REV07 remain byte-for-byte untouched forever.
- New canonical authority is created under new filenames, expected to be REV17 architecture and REV08 implementation plan unless repository state at execution time requires the next available numbers.
- `PHASE-10-COMPLETE` does not move.
- Existing Phase-10 aggregate/evidence is neither regenerated nor reinterpreted.
- This migration creates no P11 implementation, qualification, evidence or activation. The migration baseline must contain no P11 source candidate, P11 qualification workflow, P11 durable evidence, P11 retained media, or P11 activation state.
- Kernel/userland target code is not changed to fit the fast loader.
- Production/pre-release distribution is TZX-only after migration.
- A separate 6912-byte loading screen is not emitted or required.
- The real rebuilt kernel is exactly 8192 bytes and occupies `0xE000-0xFFFF` after loading.
- The fixed boot handoff remains `0xE003`.
- The dummy payload hash above is forbidden in product/pre-release output.
- Existing OBJ1, MEX1, M48O, symbol, relocation, case-sensitivity, transactional-output and cassette-object contracts remain unchanged unless a new authority explicitly changes only their release transport envelope. Their logical bytes and target semantics are not to be altered by this migration.
- Historical retained certification media such as `v1/dist/media/P10.34/` is immutable and must not be deleted merely because the product release format changes.

## 5. Stage A — establish the exact pre-migration baseline

1. Re-read `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md` and `docs/--W-A-R-N-I-N-G--.md`.
2. Verify current `main`, `PHASE-10-COMPLETE`, REV16 hash, REV07 hash, Phase-10 aggregate PASS and P10.36 acceptance PASS.
3. Prove the no-Phase-11 baseline before doing anything else: no `P11.*` durable evidence, no `P11.*` retained media, no `p11*-qualification.yml`, no Phase-11 admission/activation workflow, and no Phase-11 implementation source introduced after the Phase-10 pre-release baseline. If any appears, stop and restore the no-P11 baseline before continuing.
4. Verify the preserved ZIP hash exactly matches Section 2 and its internal manifest passes.
5. Inventory every active reference to release/pre-release tape construction, including at minimum:
   - `loading.scr`;
   - `zx48uxscr`;
   - `SCREEN$`;
   - `loader.bas` as a production-release input;
   - TAP release output;
   - TZX release output;
   - `maketap` release-builder calls;
   - `P9.pre-release` and `P10.pre-release`;
   - Phase-12 final tape steps;
   - release/pre-release workflows.
6. Classify each reference as one of: immutable historical evidence, historical test/replay machinery, current product-release mechanism, or future canonical requirement. Never delete historical evidence to make grep output pretty.
7. Record a before-migration tree/file inventory and hashes for all files that will be changed or removed.

**Gate A:** Baseline identities PASS, package identities PASS, the no-P11 baseline is proved and frozen for the duration of this migration, and the planned changed-file set is explicit.

## 6. Stage B — create the new authority epoch before changing product behavior

### 6.1 Create new immutable prospective authorities

Create, without modifying REV16/REV07:

- `docs/01-ZX-UX-ARCHITECTURE-REV17.md`;
- `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md`.

If those revision numbers already exist when this runbook is executed, use the next unused pair. The pair must be created together and admitted together.

### 6.2 REV17 architecture changes — release transport only

Copy forward all unaffected REV16 core architecture semantics. Make only the release/pre-release transport changes needed for this loader. At minimum, REV17 must replace or reconcile every normative statement that currently requires the old bootstrap.

The new production bootstrap contract must state:

1. Official product/pre-release cassette distribution is TZX only.
2. The canonical TZX starts with the reviewed fast-loader/BASIC seed-derived prefix; it does not contain a separate Spectrum SCREEN$ logical file.
3. The loader itself establishes the loading display. The exact release display contract is the reviewed 24×32 text array plus loader-owned bitmap/attribute initialization and the four colored cells, unless the owner deliberately revises those presentation details before freezing REV17.
4. There is no production `zx48uxscr` header and no production dependency on `assets/loading.scr`.
5. The kernel logical payload remains exactly 8192 bytes at `0xE000-0xFFFF` and execution transfers to `0xE003`.
6. The fast-loader pulse/symbol/timing template derives from the immutable seed identified in Section 2, but the 8192-byte kernel payload is a build input and is never inherited from the seed.
7. Product builds must reject the known dummy payload hash.
8. Product output is deterministic for identical loader sources, toolchain, release manifest, and kernel bytes; a single global fixed TZX hash is not a source constant because the TZX hash changes when the real kernel or later release content changes.
9. The current post-kernel M48O logical object contract/order remains unchanged. For the final release, the TZX continues after fast kernel delivery with the canonical M48O system/object stream in the exact frozen release order. The boot handoff must leave the tape positioned so the kernel receives the first required M48O object exactly once.
10. The lower-case/case-sensitive ZX-UX object namespace remains unchanged. If the fast loader retains the Spectrum BASIC header label `ZX-UX Unix`, REV17 must explicitly classify it as a ROM/BASIC bootstrap label, not a ZX-UX object-name case-folding exception.
11. Real-time release validation must disable emulator fast-load/trap shortcuts for the fast-loader path.
12. Historical P0-P10 certifications remain valid under their original authority identities; the new release transport does not retroactively rewrite them.
13. The release acceptance proof must establish exact three-way kernel identity for all 8192 bytes: `host-built kernel == TZX-embedded kernel == native-rebuilt kernel`.
14. The native rebuild must be genuine ZX-UX execution: canonical kernel source (or a deterministic source-only native-buildable projection) -> native `as` -> real OBJ1 -> native `ld` -> fixed 8192-byte kernel image -> executable/run proof. No host-preconstructed OBJ1, MEX1, or kernel payload may satisfy this proof.
15. Native rebuilding must occur away from the executing kernel image. Every byte offset `0..8191` must be compared, all three SHA-256 values recorded, and a controlled source/input mutation must make the equality proof fail.
16. REV17 may add only the assembler/linker facilities required for this proof, including fixed/absolute kernel output if necessary. Any deterministic projection from canonical source must contain no preassembled kernel payload and must itself be genuinely assembled and linked natively.

REV17 must remove/update all current normative statements that require:

- standard release order `zx48ux`, `zx48uxscr`, `kernel`;
- exactly 6912 loading-screen bytes;
- the loading image remaining visible during boot;
- `tools-host/maketap` constructing the native BASIC/SCREEN$/kernel release prefix;
- final release TAP output where that requirement is purely a product-distribution requirement.

### 6.3 REV08 implementation-plan changes

REV08 must preserve completed history and future core implementation steps while inserting the authority transition at the next clean canonical admission boundary.

Recommended sequence:

1. Place `R17.00` immediately after P10.36 and before P11.01. The accidental Phase-11 start has been rolled back; the bridge must therefore become the sole canonical successor to P10.36.
2. `R17.00` must bind exact REV17 and REV08 SHA-256 identities, prove REV16/REV07 and all admitted historical evidence remain unchanged, and activate the new pair only after qualification/admission/activation validation passes.
3. Preserve all P11 implementation semantics unchanged while making every future P11/P12 evidence record bind to REV17/REV08. There must be no P11 evidence under REV16/REV07.
4. Revise only future release-specific Phase-12 requirements that conflict with TZX-only fast loading. In particular, P12.07/P12.08 and any acceptance/manifest steps must specify TZX-only product distribution and the new fast-loader contract rather than TAP+TZX and SCREEN$.
5. Keep final M48O order/content requirements unchanged unless a transport-only wording change is necessary.
6. Explicitly state that deletion of the current loading-screen source asset after R17.00 is a release-transport cleanup, not retroactive invalidation of P0.08 evidence.
7. Define the exact acceptance requirements for the canonical fast-loader builder so the post-authority migration can be validated without inventing an extra Phase-11 step.
8. Add the prospective native self-rebuild acceptance contract: build the canonical kernel with the pinned host path and require exactly 8192 bytes; embed those exact bytes in TZX and reconstruct them independently from the finished TZX; boot through the real-time acceptance path; then use ZX-UX native `as` and `ld` to assemble/link source into a second kernel image outside the executing kernel range. Require exact bytewise equality across host-built, TZX-embedded, and native-rebuilt images, record all three SHA-256 values, and require a controlled mutation negative that breaks equality.
9. Require a separate genuine native lifecycle proof `source -> native as -> OBJ1 -> native ld -> executable -> run`, with native `as` parsing source and emitting real OBJ1 and native `ld` consuming that OBJ1. Historical P10.34 evidence remains immutable and does not satisfy or get rewritten by this new prospective proof.

### 6.4 Authority transition machinery

Implement the same fail-closed pattern used by the R16.00 transition, updated for the new authority pair:

- authority hash validator;
- `R17.00` build/test/result evidence;
- qualification workflow;
- evidence finalizer/admission workflow;
- activation validation;
- exact-head/static integration;
- negative tests proving changed authority bytes, missing bridge evidence, or wrong plan hash cannot pass.

Historical phase validators must continue validating historical records against their original authority identities. The shared evidence/driver layer must become explicitly epoch-aware rather than simply replacing REV16/REV07 constants globally:

- E0/P0/P1/P2 historical evidence remains bound to REV12/REV03 where its existing contracts require that epoch.
- R16.00 and P3-P10 remain bound to REV16/REV07 forever, including non-admitting historical reruns that emit scratch records.
- R17.00 and every future P11/P12 record bind to REV17/REV08.
- An R17 bridge record must be distinguishable from an R16 bridge record by step identity and exact pass marker; one bridge may not satisfy the other's checks.
- Durable P0-P10 evidence validators remain byte/identity compatible with their historical records and are never mass-retargeted to REV17/REV08.

The pre-goal audit has already identified active hard-coded authority selectors that must be handled by the transition rather than discovered accidentally later: `v1/tools-host/test-driver/driver_core.py`, `v1/tools-host/test-driver/evidence.py`, `tools/scripts/verify-environment.py`, and `tools/check_media_retention.py`. Update only the minimum authority-routing semantics necessary. Do not rewrite historical phase validators merely to make them say REV17.

### 6.5 Authority SoP/admission gate

Run the mandatory three consecutive unchanged-byte SoP scans over the new authority pair and transition machinery, then license, project-policy and adversarial-review gates. Admit `R17.00` only after exact qualification and activation PASS.

**Gate B:** New authority active; REV16/REV07 unchanged; all evidence admitted before the bridge unchanged; the Phase-11 position has not been advanced by this migration.

## 7. Stage C — promote the reviewed fast-loader package into canonical release tooling

After Gate B only, create a canonical release-only host-tool subtree, recommended:

`v1/tools-host/release-tzx/`

Promote reviewed package components rather than executing the ZIP in place. Expected promoted inputs are:

- immutable seed TZX in an exact deterministic repository representation;
- loader build script;
- `src/print_hook.asm`;
- `text-lines.txt`;
- a ZX-UX-specific rebuild contract;
- release-toolchain provenance/lock metadata.

Do not promote package `output/` demonstration artifacts as active release inputs. The dummy binary and demonstration TZX remain provenance inside the preserved scratch ZIP, not product source.

Use ZX-UX licensing/header conventions on promoted text/source files. Preserve upstream/package provenance and exact seed/hash references in the new release builder README/manifest.

**Gate C:** Canonical release-tool source is self-contained, reviewed, does not depend on mutable files in `scratch/`, and still reproduces the package demonstration when deliberately run in fixture mode.

## 8. Stage D — pin release construction tools without widening the shared runtime

### 8.1 Pasmo

Pasmo `0.5.3-7` is required to assemble the loader hook. Integrate it reproducibly, but keep it release-scoped so this migration does not perturb the already-certified general ZX-UX development runtime.

Required integration:

1. Preserve the package's exact Pasmo provenance in the canonical release-tool subtree, including version, immutable upstream/source or package location, exact size and SHA-256 where available, and the package's reference identity.
2. The release/pre-release workflow must acquire Pasmo deterministically into a release-only workspace or release-tool cache and verify its exact identity before executing it. Do not rely on ambient PATH.
3. Prefer an immutable source/archive acquisition with explicit size+SHA-256. If the reviewed package's exact Ubuntu `pasmo=0.5.3-7` package is the only practical source, pin that exact version in the release workflow, record the resolved package identity, and fail closed on any mismatch.
4. Invoke Pasmo by its exact resolved release-workspace path.
5. Do **not** change `tools/manifest/toolchain.lock.json`, `tools/scripts/bootstrap-environment.py`, `tools/scripts/record-bootstrap-provenance.py`, or `.github/actions/setup-zxux-runtime/action.yml` merely to add this release-only assembler. Pasmo must not enter the shared certified runtime/toolchain lock. `tools/scripts/verify-environment.py` may change only for the separate R17 authority-selector migration identified in Stage B, never to acquire or certify Pasmo.
6. If later evidence proves Pasmo must enter the global runtime after all, stop this one-shot migration and obtain an explicit scope change rather than silently broadening it.

### 8.2 Existing tools

Do not import the package's older Fuse/libspectrum/Python versions simply because they appear in its provenance file. Use the project's existing pinned Python 3.13.15, Fuse 1.9.2, libspectrum 1.6.4 and exact pinned 48K ROM for integration and validation.

Xvfb/xdotool may be installed as exact validation-only dependencies inside the release/pre-release workflow if real-time keyboard entry cannot be driven cleanly with the existing project emulator harness. They are not TZX construction dependencies and do not enter the shared certified runtime.

**Gate D:** Pasmo is exactly reproducible and release-scoped; project-local Python builds the loader; the existing project-pinned emulator/ROM remain authoritative; shared runtime/toolchain files are byte-identical to the baseline.

## 9. Stage E — convert the package builder from dummy-tail preservation to real kernel injection

This is the central technical change.

### 9.1 Builder interface

The production builder must accept an explicit kernel input, for example:

`build.py --kernel v1/build/kernel.bin --output <path>`

Product mode must not have a fallback kernel. Missing kernel input is a hard failure.

### 9.2 Kernel preconditions

Before modifying the seed template, require:

- regular file, no symlink;
- exactly 8192 bytes;
- intended link base `0xE000`;
- fixed syscall/boot trampoline structure still valid;
- boot entry exactly `0xE003`;
- SHA-256 calculated and recorded;
- SHA-256 MUST NOT equal the known seed dummy hash.

The pre-release workflow must rebuild this kernel from the exact checked-out ZX-UX source rather than accepting an arbitrary checked-in binary.

### 9.3 Preserve loader template, replace every payload byte

Retain the seed's loader/timing/symbol definitions only where they are true template data. Split the real kernel into the exact 24 payload chunk sizes required by the seed transport:

- chunks 0-7: 342 bytes each;
- chunks 8-23: 341 bytes each;
- total: 8192 bytes.

Replace the generalized-data payload bitstreams with those real kernel chunks. Do not append a second kernel and do not leave any seed dummy bytes in the emitted kernel range.

### 9.4 Rebuild payload-dependent fast-loader headers

Reverse/derive the exact per-block header check/CRC rule used by the loader. This must be understood and implemented, not guessed from a successful emulator run.

Acceptance for the rule:

1. all 24 seed header check bytes reproduce exactly when calculated from the seed payload chunks;
2. at least one deliberately corrupted payload chunk with an unmodified check byte is rejected by the real loader path;
3. recalculating the check byte for a changed fixture chunk makes the loader accept that block;
4. header address/length progression reconstructs exactly `0xE000-0xFFFF` with no gap, overlap or wrap;
5. the final block retains the seed's special final-dispatch behavior and reaches `0xE003` only after the final bytes are placed correctly.

### 9.5 Generalized-data block integrity

The builder must preserve the seed's pulse/symbol/timing definitions unless REV17 deliberately freezes a changed timing. It may patch only the encoded data bits and the payload-dependent header fields necessary for the new kernel.

After generation, parse the emitted TZX independently and reconstruct the 8192-byte payload. Its SHA-256 must equal the explicit kernel input SHA-256 exactly.

### 9.6 Remove fixed demonstration-output assumptions

The package's fixed demonstration TZX hash is a fixture identity, not the product builder's universal expected output. Product mode must instead record:

- seed identity;
- loader source/hook identity;
- text identity;
- Pasmo identity;
- kernel SHA-256;
- complete output TZX SHA-256.

Building twice from unchanged inputs must produce byte-identical TZX files.

### 9.7 Native self-rebuild and three-way identity proof

After the finished TZX has independently reconstructed the host-built kernel and the real-time acceptance boot has reached the legitimate Phase-10 execution checkpoint, perform a native rebuild inside ZX-UX without overwriting the executing kernel:

1. Build the canonical host kernel through the pinned host path and require exactly 8192 bytes.
2. Reconstruct the embedded kernel independently from the finished TZX and compare every byte `0..8191` with the host-built image.
3. Feed canonical kernel source directly to ZX-UX native `as` where possible. If SjASMPlus-only constructs make that impossible, deterministically generate a source-only native-buildable projection from canonical source; it must contain no preassembled kernel bytes or host-preconstructed object payloads.
4. Native `as` must parse that source and emit a real OBJ1 file. Native `ld` must consume that native OBJ1 and emit a fixed/absolute kernel image in non-executing storage. Add only the assembler/linker facilities prospectively authorized by REV17/REV08 to make this possible.
5. Require the native image to be exactly 8192 bytes and compare every byte against both the host-built image and the independently reconstructed TZX image. Hash equality alone is insufficient. Record all three SHA-256 values.
6. Separately execute a genuine native lifecycle chain `source -> native as -> OBJ1 -> native ld -> executable -> run`; host-preconstructed OBJ1/MEX1 inputs are forbidden for this proof.
7. Perform a controlled source/input mutation that must cause the three-way equality check to fail. The negative proof must demonstrate that stale/preassembled substitution cannot silently pass.
8. Preserve historical P10.34 evidence byte-for-byte; this new proof is prospective R17/pre-release evidence and never retroactively recertifies Phase 10.

**Gate E:** Independent reparse proves output TZX contains the exact rebuilt kernel and zero seed-dummy substitution; deterministic double-build PASSes; the genuine native lifecycle proof PASSes; exact 8192-byte host/TZX/native bytewise identity PASSes; controlled mismatch-negative proof PASSes.

## 10. Stage F — integrate the post-kernel ZX-UX distribution stream

The fast-loader package closes kernel transfer at `0xE003`; the final ZX-UX release still needs the canonical post-kernel cassette object stream.

1. Preserve existing logical M48O serialization, names, case, type/target fields, CRCs, packing rules and final order.
2. Do not re-encode M48O logical content merely because the bootstrap transport changed.
3. Append the required release/pre-release M48O TZX blocks after the fast-loader kernel blocks using the existing canonical object serializer or a byte-equivalent reviewed extraction of that serializer.
4. Prove the fast loader consumes exactly its own blocks and leaves the tape at the first post-kernel object.
5. Prove the kernel's first cassette read receives the first required object exactly once; no loader over-read, dropped block or duplicate block is permitted.
6. For the current Phase-10 pre-release, include only content that is valid to claim at the certified Phase-10 state. Do not fabricate Phase-11/Phase-12 objects.
7. For final Phase 12, consume the then-frozen final release manifest/order and produce one canonical system TZX.

If the current Phase-10 pre-release intentionally exercises only real-kernel handoff and does not yet carry the eventual complete system stream, state that limitation explicitly in its README/manifest. Do not label a partial pre-release as the byte-exact final system tape.

**Gate F:** Fast-loader-to-kernel tape-position handoff and any included M48O stream PASS under real-time tape execution.

## 11. Stage G — replace the current Phase-10 pre-release workflow

Replace, preferably in place, `.github/workflows/p10-prerelease-build.yml` so there is one obvious current pre-release workflow.

The new workflow must:

1. verify `PHASE-10-COMPLETE` is still fixed;
2. verify the new authority pair is active;
3. verify the Phase-11 state exactly matches the migration baseline and has not been advanced by this workflow;
4. restore/build the existing pinned ZX-UX runtime, then acquire and verify the release-scoped Pasmo tool separately;
5. rebuild the real Phase-10 kernel from source;
6. require exact 8192-byte size and boot-entry contract;
7. invoke the canonical release-TZX builder with that kernel;
8. build twice and compare byte-for-byte;
9. independently parse the TZX and reconstruct/compare the embedded 8 KiB kernel;
10. reject the known dummy payload hash;
11. run real-time Fuse with tape traps, loader detection and accelerated/fast loading disabled;
12. prove BASIC/ROM loading begins normally and the fast-loader path is actually exercised;
13. prove execution reaches `0xE003` with the exact rebuilt kernel resident;
14. continue to the strongest legitimate Phase-10 post-handoff checkpoint available without faking Phase-11/12 functionality;
15. if post-kernel M48O content is included, prove the first object is consumed correctly;
18. using the booted ZX-UX environment, genuinely rebuild the kernel from source through native `as` -> real OBJ1 -> native `ld` into non-executing storage, require exactly 8192 bytes, and compare every byte with both the host-built kernel and independently reconstructed TZX kernel;
19. record the host-built, TZX-embedded, and native-rebuilt SHA-256 values and require all three images to be byte-identical;
20. execute a separate genuine `source -> native as -> OBJ1 -> native ld -> executable -> run` proof with no host-preconstructed OBJ1/MEX1;
21. execute a controlled mutation negative and require the three-way equality gate to fail;
22. perform three unchanged output scans;
23. run project-policy/media-retention/relevant evidence gates;
24. publish only the new durable pre-release bundle when every gate passes, then explicitly re-check that no Phase-11 state exists and terminate without dispatching or creating any Phase-11 work.

Do not use Fuse `--fastload`, tape traps or automatic loader shortcuts as the acceptance proof for this workflow.

## 12. Stage H — new durable pre-release artifact contract

The durable `v1/dist/media/P10.pre-release/` directory should become small and unambiguous. Unless an additional metadata file is required by policy, retain only:

- `zx-ux-phase10-pre-release.tzx` — the actual distribution image;
- `pre-release.json` — identities, provenance, hashes and test results;
- `README.txt` — exact scope/limitations and boot instructions.

The distribution must not retain obsolete alternate boot products.

Remove from the current P10 pre-release bundle once the replacement passes:

- `zx-ux-phase10-pre-release.tap`;
- `loader.bas` generated for the old distribution path;
- `kernel-phase10-pre-release.bin` as a separately shipped distribution artifact;
- `phase10-preview.bin`;
- `phase10-pre-release-fuse-test.sna`;
- copied `phase10-native-lifecycle.tap` / `.tzx` files from the pre-release bundle.

The admitted P10.34 retained lifecycle media itself remains untouched in `v1/dist/media/P10.34/`; only the redundant copies inside the non-certification pre-release bundle disappear.

The new manifest must include at least:

- source commit used to rebuild kernel;
- `PHASE-10-COMPLETE` identity;
- active architecture/plan identities;
- preserved fast-loader package/seed identity;
- loader/hook/text identities;
- Pasmo identity;
- embedded kernel SHA-256;
- output TZX SHA-256 and size;
- deterministic rebuild PASS;
- independent embedded-kernel reconstruction PASS;
- real-time loader-to-E003 PASS;
- dummy-payload rejection PASS;
- post-kernel/M48O checks applicable to the pre-release;
- host-built kernel SHA-256, TZX-embedded kernel SHA-256, and native-rebuilt kernel SHA-256;
- exact 8192-byte three-way bytewise identity PASS;
- genuine native `source -> as -> OBJ1 -> ld -> executable -> run` PASS;
- controlled mutation/mismatch-negative PASS.

## 13. Stage I — remove obsolete non-certification release/pre-release material

Only after the new workflow has published a validated replacement:

1. Delete the complete old `v1/dist/media/P9.pre-release/` non-certification preview bundle.
2. Remove/retire `.github/workflows/p9-prerelease-build.yml` if it remains an active obsolete workflow.
3. Replace the P10 pre-release directory contents with the compact contract in Stage H.
4. Leave shared retention/checker machinery unchanged unless the replacement cannot pass its existing contracts. Dead non-certification-path allowances may remain temporarily rather than widening this migration into unrelated control-plane cleanup.
5. Delete `v1/assets/loading.scr` from the current source tree after the new authority is active. The bytes remain recoverable forever from Git/history and historical P0.08 evidence; do not rewrite that evidence. This deletion is the one explicit non-release-artifact cleanup requested by the owner.
6. Remove any active release/pre-release workflow dependency on `v1/src/boot/loader.bas`, SCREEN$, `zx48uxscr`, or old TAP construction. Leave historical source/test material untouched unless the new authority explicitly declares it current release machinery and its removal is required.
7. Do not delete historical certification media, historical evidence, phase aggregates, or the `PHASE-10-COMPLETE` tag.
8. Do not delete `maketap` merely because it is no longer the product release bootstrap builder if historical tests/fixtures still use it. Retire it from the active release path; historical replay remains historical.
9. Remove the now-dead exact-path `v1/assets/loading.scr` license-header exemption during the final authorized infrastructure/document synchronization pass. Do not alter unrelated historical exemptions.

**Gate I:** No competing active pre-release/release builder or obsolete non-certification distribution remains, while all historical evidence/media stays byte-identical.

## 14. Stage J — Phase-12 release-plan reconciliation

Before future P12.07/P12.08 execution under REV08, ensure the plan requires:

1. one final canonical TZX distribution, not parallel TAP/TZX products;
2. exact fast-loader seed/template identity;
3. exact real final kernel bytes embedded into the turbo payload;
4. exact final M48O manifest/order after kernel handoff;
5. deterministic double-build byte identity;
6. independent TZX structural inspection;
7. independent reconstruction/hash of the embedded kernel and logical release objects;
8. real-time Fuse boot with acceleration/traps disabled;
9. hardware/analog validation where REV17 still requires a physical-tape claim;
10. no `loading.scr`, SCREEN$ or `zx48uxscr` production dependency.

P12 may freeze the final TZX hash only after all final release inputs are frozen. The builder itself must remain input-driven rather than hardcoding the Phase-10 pre-release hash.

## 15. Stage K — mandatory validation matrix

Before calling the migration complete, all of these must PASS against one unchanged candidate:

### Authority/provenance

- REV17/REV08 exact hashes active through admitted bridge evidence.
- REV16/REV07 exact bytes unchanged.
- Phase-10 aggregate/acceptance unchanged and PASS.
- `PHASE-10-COMPLETE` unchanged.
- the repository still has no Phase-11 implementation/qualification/evidence/activation state; no P11 work was created by this migration.

### Package/tooling

- preserved ZIP SHA-256 exact;
- internal package manifest exact;
- seed SHA-256 exact;
- loader hook rebuild deterministic;
- Pasmo exact version/identity verified;
- project-local Python used successfully;
- no ambient unpinned construction tool accepted.

### TZX/kernel

- TZX-only output;
- no release TAP emitted;
- no SCREEN$ block emitted;
- no `zx48uxscr` header emitted;
- exactly 24 fast kernel payload chunks;
- reconstructed kernel exactly 8192 bytes;
- reconstructed kernel SHA-256 equals rebuilt source kernel SHA-256;
- reconstructed kernel SHA-256 differs from dummy hash;
- coverage exactly `0xE000-0xFFFF`;
- final handoff exactly `0xE003`;
- per-block check/CRC algorithm independently verified;
- deterministic double-build byte identity;
- host-built kernel, independently reconstructed TZX kernel, and native-rebuilt kernel are each exactly 8192 bytes and identical at every byte offset `0..8191`;
- all three kernel SHA-256 values are recorded and equal;
- native `as` genuinely parses source and emits real OBJ1, native `ld` genuinely consumes native OBJ1 and emits the fixed kernel image away from the executing kernel;
- no host-preconstructed OBJ1/MEX1/kernel payload participates in the new native proof;
- genuine `source -> native as -> OBJ1 -> native ld -> executable -> run` PASS;
- controlled source/input mutation causes the equality proof to fail.

### Real-time execution

- real ROM/BASIC load path observed;
- emulator trap/fastload/detect-loader shortcuts disabled for acceptance;
- fast loader executes;
- screen initialized by loader, not SCREEN$;
- 24×32 status display contract observed/verified;
- startup beep path executes exactly once where practical to assert;
- `0xE003` reached after final kernel transfer;
- real kernel bytes resident before handoff;
- first post-kernel object correctly positioned/consumed when present.

### Repository hygiene

- new compact P10 pre-release bundle is durable and hash-bound;
- old P9 pre-release bundle removed;
- old P10 alternate distribution artifacts removed;
- current-tree `v1/assets/loading.scr` removed;
- no obsolete active P9 pre-release workflow;
- no historical certification evidence/media changed;
- project policy PASS;
- license-header gate PASS;
- media-retention gate PASS;
- exact-head regression PASS where triggered;
- three consecutive unchanged-byte SoP scans PASS for every check-in candidate required by workflow.

## 16. Stage L — final repository-wide infrastructure/document sanity and synchronization pass

This is the mandatory final execution stage, after the replacement TZX path and obsolete pre-release cleanup have passed. It is intentionally broader than a grep for the new loader, but it is still a synchronization pass rather than a new feature phase.

### 16.1 Full repository walk

Walk the complete current tree and explicitly inventory at minimum:

- every `.github/workflows/*.yml` and `.github/actions/**` entry;
- root and nested `README*` files;
- every current `*.md`/Markdown operational document under `docs/`, `v1/docs/`, `scratch/`, and `v1/dist/`;
- release/pre-release manifests and readmes;
- authority/evidence routing code under `tools/` and `v1/tools-host/test-driver/`;
- active policy, license-header, media-retention, exact-head, qualification-dispatch, admission and activation machinery.

Classify each inspected item as exactly one of:

1. active/current and must agree with REV17/REV08 plus the TZX-only release contract;
2. immutable historical authority/evidence and must remain byte-identical;
3. historical replay/diagnostic machinery that is intentionally retained;
4. obsolete pre-release/release machinery that must be removed;
5. disposable one-shot infrastructure that has completed its purpose and may be removed only when no active trigger, evidence dependency, recovery role or audit requirement remains;
6. unrelated current material requiring no change.

Do not delete historical qualification/admission workflows merely because they are old. Conversely, do not keep a clearly disposable one-shot helper merely because deleting it takes effort. The classification must be evidence-based.

### 16.2 Known synchronization targets

The pre-goal audit has already found several current/stale surfaces that the final walk must resolve:

- RESOLVED: `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md` names admitted REV17/REV08 as active, preserves REV16/REV07 as historical P3-P10 authority, and explicitly records frozen-authority transport precedence.
- RESOLVED: `docs/--W-A-R-N-I-N-G--.md` records REV17/REV08 as active, REV16/REV07 as immutable history, and forbids editing frozen authorities merely to remove retained superseded transport wording.
- RESOLVED: `v1/dist/certification/README.md` documents R17.00 and epoch-aware evidence routing without reinterpreting historical records.
- RESOLVED: `scratch/WORKFLOW.md` is explicitly historical/closed and no longer advertises a live resume point.
- RESOLVED: `scratch/README.md` was checked; no stale live-status contradiction remains.
- RESOLVED: `v1/docs/test-plan.md` and current operational documentation agree with REV17/REV08 and the TZX-only release path.
- RESOLVED: `tools/check_media_retention.py` uses the active REV08 plan while retaining validation of admitted historical media.
- RESOLVED: `driver_core.py` and `evidence.py` route historical, REV16/P3-P10, and REV17/future epochs explicitly.
- RESOLVED: `tools/scripts/verify-environment.py` is epoch-aware and validates active REV17 without invalidating historical identities.
- RESOLVED: the dead `v1/assets/loading.scr` license exemption is removed.
- RESOLVED: root `README.md` was checked and required no release/boot synchronization change.

### 16.3 Stale-contract scan

Perform repository-wide text/path scans for at least:

- `REV16` / `REV07` when used as *current* rather than historical identity;
- `loading.scr`;
- `zx48uxscr`;
- `SCREEN$` production bootstrap claims;
- product/release `.tap` output;
- `p9-prerelease-build`;
- obsolete P9/P10 pre-release artifact names;
- current-release calls to the old `maketap` bootstrap prefix;
- stale "next step", "current phase", "active authority", and checkpoint statements;
- any P11 source/workflow/evidence/media, which must still be absent.

A textual hit is not automatically wrong. Classify historical citations and frozen documents as historical and leave them untouched. Every non-historical hit must either be synchronized or explicitly justified as still current.

Closure classification note: admitted REV17/REV08 are immutable. Their revision-level transition clauses explicitly supersede inherited SCREEN$/TAP-era wording for current/future release transport. `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md` and `docs/--W-A-R-N-I-N-G--.md` now make that precedence explicit, so retained inherited wording inside the frozen authority bytes is classified as superseded historical context rather than a competing active release mechanism.

### 16.4 Workflow sanity

For every workflow, verify trigger mode, permissions, concurrency, changed-path guards, immutable action pins, authority hashes, admission semantics and whether the workflow is still reachable/necessary.

In particular:

- there must be one obvious current pre-release workflow;
- obsolete P9 pre-release execution must be gone;
- qualification auto-dispatch must have no due P11 candidate when this migration closes;
- exact-head regression must understand the R17 control-plane changes without accidentally treating historical evidence as mutable;
- no completed one-shot branch/tag/repair helper remains active unless it has a documented recovery purpose;
- retained historical qualification workflows remain dispatch-only and cannot auto-fire.

Delete only those disposable workflow files whose purpose is conclusively complete and whose removal cannot affect historical validation/recovery. Record the keep/delete rationale in the runbook closure notes.

### 16.5 Documentation/infra sync gate

Apply only synchronization fixes found by this walk. No new kernel/userland feature work is permitted.

After the final changed bytes are settled:

1. run the complete three-pass unchanged-byte SoP scan over every modified document/infrastructure file;
2. run license-header, project-policy and media-retention gates;
3. run authority/evidence validator positive and negative suites;
4. run exact-head regression and any R17 admission/activation validation required by the changed files;
5. re-run the stale-contract scans and require zero unexplained current-state contradictions;
6. prove no P11 state exists;
7. require a clean worktree and record the final tree/head plus workflow/document inventory summary in this runbook's closure section.

**Gate L:** The repository tells one coherent current story: REV17/REV08 are active, P0-P10 history remains intact, the product release path is TZX-only fast loading, no obsolete pre-release mechanism competes with it, active infrastructure agrees with the new epoch, stale scratch/current-status documentation is corrected or clearly historical, disposable completed workflows are removed where safe, and Phase 11 has not started.

## 17. Commit/checkpoint sequence

Use direct `main` commits unless the checked-in workflow at execution time requires otherwise. Keep recovery points small and durable.

Recommended sequence:

1. **Scratch preservation checkpoint** — this runbook + exact ZIP only.
2. **Prospective authority checkpoint** — REV17/REV08 + R17 transition machinery, no product behavior change yet.
3. **Authority activation checkpoint** — admitted/validated R17.00 only.
4. **Release-tooling checkpoint** — promoted fast-loader source + pinned Pasmo integration + kernel-injection tests, no deletion of old product yet.
5. **Replacement pre-release candidate** — new workflow and TZX builder, old product still present until validation completes.
6. **Replacement activation/publication** — validated new P10 TZX pre-release becomes durable.
7. **Obsolete pre-release/release cleanup checkpoint** — remove old P9/P10 non-certification products/workflows and current loading-screen asset only after replacement PASS.
8. **Final repository sanity/sync checkpoint** — Stage L repo-walk corrections and justified disposable-workflow cleanup complete; all validation matrix items PASS, working tree clean, and Phase 11 remains absent.

Do not move `PHASE-10-COMPLETE`. A separate durable tag for this packaging migration is optional only if the checked-in workflow explicitly permits it; it must never be confused with a phase-completion tag.

## 18. Fail-closed and rollback rules

- Before R17.00 activates, do not delete or disable the current release/pre-release mechanism.
- Before the new pre-release workflow proves a real rebuilt kernel is embedded and reaches E003, do not publish it as the replacement.
- If kernel payload injection cannot reproduce valid per-block checks, stop; do not weaken validation or preserve stale dummy checks.
- If project-pinned Fuse cannot perform the real-time loader test, diagnose the validation harness first. Do not silently substitute emulator fast-load/traps as proof.
- If deleting `loading.scr` breaks an active current-authority requirement, the authority transition is incomplete; stop and repair the new-authority/control-plane path rather than restoring an obsolete production requirement by accident.
- If any historical evidence/media changes, restore it byte-for-byte before proceeding.
- If this migration itself creates or advances P11 work, stop and remove/revert that accidental advancement before migration closure. This runbook's baseline intentionally contains no admitted P11 history.

## 19. Definition of DONE

This runbook is DONE only when all of the following are simultaneously true:

- the new authority epoch governing release media is active;
- the canonical pre-release/release builder is the reviewed fast-loader TZX builder;
- it consumes a freshly rebuilt exact 8192-byte ZX-UX kernel and embeds those exact bytes in the fast-loader payload;
- no dummy kernel can be emitted in product mode;
- product/pre-release distribution is TZX-only;
- no separate loading screen is used or stored in the current product source tree;
- the current P10 pre-release is rebuilt and validated through the new path;
- obsolete P9/P10 non-certification distribution artifacts/workflows are removed;
- historical certification evidence and retained step media remain immutable;
- all mandatory repository, toolchain, deterministic-build, TZX-structure and real-time execution validations PASS;
- genuine native `source -> as -> OBJ1 -> ld -> executable -> run` PASSes using native-produced OBJ1, and host-built, TZX-embedded, and native-rebuilt kernels are exactly identical for all 8192 bytes with a controlled mismatch-negative PASS;
- `PHASE-10-COMPLETE` remains unchanged;
- Stage L's full infrastructure/document repository walk is complete with all current-state contradictions resolved or explicitly classified as historical; and
- no Phase-11 implementation, qualification, evidence, media, admission or activation state exists.

At that point mark this scratch runbook CLOSED with final commit/run/hash anchors, and stop.
