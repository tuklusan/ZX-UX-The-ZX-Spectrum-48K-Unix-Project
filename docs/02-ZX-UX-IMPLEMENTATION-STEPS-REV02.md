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
# ZX-UX Implementation Steps
## A 48K ZX Spectrum Unix-Like Multiprocessing Development Environment

(C) 2026 Supratim Sanyal
A SANYALnet Labs Hobby project
https://supratim-sanyal.blogspot.com/

Status: Revision-11 implementation and certification plan
Revision: 02
Architecture baseline: `v1/docs/01-ZX-UX-ARCHITECTURE-REV11.md`
Architecture SHA-256: `F76281FAB2E5AE73B7321FC2A69E6776F7CCD8BFE3955A6ED6FB3BEC44F762C7`
Target: Original unexpanded 48K ZX Spectrum

---

# 1. Certified Development Environment and Gate E0

This document is subordinate to Revision 11. It does not amend the architecture.
If this document conflicts with Revision 11, Revision 11 wins and this document
must be corrected before implementation continues.

The previously certified development environment already has individual
certification evidence for the canonical ROM, cross-development execution chain,
and cassette-image/ROM-trap chain. Those Windows-host results are historical
evidence only; they do **not** require subsequent implementation or certification
to run on Windows. Native Linux is an allowed implementation host. The final
aggregate lock/verifier was generated at handover, but the handover does **not**
provide evidence that the new aggregate wrapper itself has been copied into the
repository and ended with its final PASS marker. Therefore Gate E0.01 is an
execution prerequisite, not a historical PASS invented by this plan.

Historical certified/pinned environment (reference evidence only):

- Windows 10 x64, project-local tooling, external/removable disk supported.
  This records the host on which the existing evidence was produced; it is not
  a requirement that implementation continue on Windows;
- SjASMPlus 1.24.0;
- FUSE 1.9.2;
- FUSE-utils 1.4.7;
- Python 3.13.15 embedded distribution;
- PortableGit 2.55.0.windows.5;
- developer helper CLI 0.153.4 as developer convenience only, never a ZX-UX build dependency;
- canonical orchestrator: `<project-local-python>`;
- canonical 48K ROM: `tools/runtime/fuse/roms/48.rom`, 16384 bytes,
  SHA-256 `d55daa439b673b0e3f5897f99ac37ecb45f974d1862b4dadb85dec34af99cb42`.

Already demonstrated individual markers:

- `ZX-UX 48K ROM VERIFICATION PASS` from `tools/scripts/verify-zx48-rom.py`;
- `ZX-UX CROSS-DEVELOPMENT ENVIRONMENT VERIFICATION PASS` from
  `tools/scripts/verify-zxux-crossdev.py`;
- `ZX-UX CASSETTE IMAGE/TRAP ENVIRONMENT VERIFICATION PASS` from
  `tools/scripts/verify-zxux-tape.py`.

The cassette/trap certification is **not** physical EAR/MIC/cassette certification.
Real-hardware or hardware-faithful analog-loop gates remain in Phase 12.

Frozen aggregate files expected before coding:

- `tools/manifest/toolchain.lock.json`, SHA-256
  `2847e76becf27fe1c7decabd09deb6beb017bf90d4e6906e31889f3b10cf9bd3`;
- `tools/scripts/verify-environment.py`, SHA-256
  `72b93d8488cc6d3096cc90dea7ae276cf089c910971498936a0896c6b9855b86`.

Run from the root identified by `.zxux-root`, whose exact ASCII content is
`ZX-UX project root`:

```text
<project-local-python> tools/scripts/verify-environment.py
```

Required final marker:

```text
ZX-UX DEVELOPMENT ENVIRONMENT CERTIFICATION PASS
```

No canonical build/test script may require Windows or depend on a fixed drive
letter, fixed user profile, host-specific absolute path, or ambient system PATH
resolution. Native Linux execution is explicitly permitted and may be the primary
implementation host. Host wrappers may differ by platform, but project-local pinned
tools, deterministic inputs, and retained certification evidence remain required.

---

# 2. Execution Doctrine

Accuracy is the canonical goal. Efficiency is not a goal. The work proceeds in
Revision-11 phase order. A later phase does not begin because its code looks fun.

Every implementation step is a separately check-in-ready transaction. The default
host runner introduced by E0.03 is plan-defined host tooling, not target ABI. The
invocation syntax and project-local interpreter path are host-specific; native Linux
and Windows are both valid hosts. In commands below, `<project-local-python>` means
the project-local Python interpreter selected by the host toolchain; it is not an
ambient PATH lookup:

```text
<project-local-python> v1/tools-host/test-driver/run.py build --step <STEP-ID>
<project-local-python> v1/tools-host/test-driver/run.py test --step <STEP-ID>
```

For a target step, the test runner must prefer deterministic debugger-visible
register/RAM/process-state assertions. Screenshot/image comparison is supplemental,
not the normal oracle. Every FUSE subprocess has a hard timeout. Python passes argv as
a list. Saved host verifiers must likewise pass argv as an argument list rather
than flattening multiword argument strings.

Fast inner loop: SNA. Boot/cassette integration: TAP. Tape-format integration: TZX
plus independent FUSE-utils inspection. Real analog/hardware claims: physical 48K or
hardware-faithful EAR/MIC loop only.

Synthetic SNA programs that CALL ROM code must establish an explicitly safe writable
stack. The prior certified cassette test found that blindly accepting an SNA-restored
SP can push ROM return data into ROM; this plan therefore treats stack establishment as
a test precondition, not folklore.

For every step below, evidence is retained at least as
`v1/dist/certification/<STEP-ID>.log` plus a machine-readable result/hash record when
the step is a certification boundary. `v1/build` is disposable; `v1/dist` is not.

A step may be committed only when:

1. its required files exist;
2. project-local build succeeds;
3. host static checks pass;
4. relevant SNA/TAP/TZX test passes;
5. required negative test passes by failing for the intended reason;
6. certification evidence is retained where required;
7. Git reports the intended committed state clean after commit.

---

# 3. Fixed Architecture Contracts Used by Every Phase

The implementation must preserve, among the rest of Revision 11, these high-risk
contracts throughout all phases:

- ROM `0000-3FFF`; bitmap `4000-57FF`; attributes `5800-5AFF`; ROM compatibility
  `5B00-5FFF`; COLD `6000-7FFF`; FAST user `8000-DFFF`; kernel `E000-FFFF`.
- kernel code/data `E000-FAFF`; stack `FB00-FCFF`; fast reserve `FD00-FDFC`;
  IM2 trampoline `FDFD-FDFF`; 257-byte table `FE00-FF00`; emergency reserve
  `FF01-FFFF`.
- `E000` syscall gateway; `E003` production boot gateway; successful USR handoff
  executes DI, establishes SP=`FD00`, and never returns to BASIC.
- IM2 uses I=`FE`, table byte `FD`, and `FDFD: JP zx48_interrupt`.
- IY is OS/ROM-reserved and production value is exactly `5C3A` (`ERR_NR`).
- alternate register bank is OS-private/volatile; no conforming application owns it.
- process stacks and pipe buffers are FAST_REQUIRED; normal MEX1 image+BSS may use
  ANY and may cross `7FFF/8000`; FAST_REQUIRED never silently spills COLD.
- standard boot logical sequence begins `zx48ux`, `zx48uxscr`, `kernel`, then exact
  M48O resources `sh`, `font4x8`, `issue`, `crontab`, `bincat`.
- loading SCREEN$ is exactly 6912 bytes; kernel is exactly 8192 bytes; loading image
  remains visible through low-level init and bootstrap-resource loading unless a boot
  panic must replace it.
- `font4x8` is exact 392-byte F4X8 pinned FAST_REQUIRED; UDG bank is 256-byte pinned
  COLD_PREFERRED; official BCAT is exact 40 entries / 488 bytes, pinned COLD.
- names are case-sensitive; shipped user-facing names are lower-case.
- compression is ZXP1 stored-object/cassette representation only, never virtual memory
  and never live process/stack/pipe/screen/kernel/pinned-memory compression.
- cassette is sequential. Tape operations may synchronously block the machine and may
  create honest gaps in frame-derived wall time.
- the final system-tape order is frozen by Revision 11 Section 19.8 and is not a
  Phase-5 optimization knob. Phase 5 may use contract-valid stubs; Phase 12 alone
  certifies byte-exact final release content.

**Path notation rule for every step:** the project root is the `.zxux-root` directory.
An architecture-listed unqualified target basename is shorthand for exactly the single
Section-37 path that owns it: kernel basenames under `v1/src/kernel/`; `entry.asm` and
`loader.bas` under `v1/src/boot/`; `sh.asm` under `v1/src/shell/`; `vi.asm`, `as.asm`,
`ld.asm`, and `cc.asm` under `v1/src/tools/`; utility basenames under `v1/src/utils/`;
C48 runtime basenames under `v1/src/libc48/`; assets under `v1/assets/`; includes under
`v1/include/`; docs under `v1/docs/`; tests under `v1/tests/`; host tools under
`v1/tools-host/`; and release/evidence artifacts under `v1/dist/`. Phase evidence
manifest shorthand means `v1/dist/certification/phase-<N>.json`. No shorthand permits
an alternate location. Target source/header files are limited to the Section-37 tree; do not
invent additional target modules merely to split an implementation. The built-in `<c48.h>`
declarations live inside `v1/src/tools/cc.asm` and are documented in `v1/docs/c48.md`;
there is no separate target/header file named `c48.h`. Each evidence record must print the
resolved root-relative paths.

---

# 4. Per-Step Record Format

Every numbered step below uses the same eleven fields. `Build` and `Test` invoke the
plan-defined host runner after E0.03. A HOST-only step has no fake emulator claim; its
emulator field says N/A. A hardware step cannot be closed by FUSE.


---

# Environment/Foundation

## E0.01 - Aggregate certified-environment gate

1. **Purpose / REV11 requirement:** Handover final-freeze requirement; REV11 host tooling assumptions.
2. **Exact implementation work:** Copy/verify the frozen lock and aggregate verifier at their exact paths; execute only project-local Python. Do not change a previously certified runtime merely to make the aggregate wrapper green.
3. **Files/artifacts created or modified:** `tools/manifest/toolchain.lock.json`; `tools/scripts/verify-environment.py`.
4. **Build command:** `<project-local-python> tools/scripts/verify-environment.py`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Exit code 0 and final marker exactly `ZX-UX DEVELOPMENT ENVIRONMENT CERTIFICATION PASS`; lock/verifier SHA-256 values equal the handover values.
9. **Negative/failure test:** Alter a temporary copy of one locked hash and require verifier failure; restore and re-run.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/E0.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## E0.02 - Canonical architecture identity gate

1. **Purpose / REV11 requirement:** REV11 is the sole architecture authority.
2. **Exact implementation work:** Hash the on-disk architecture before implementation and compare with the frozen REV11 SHA-256. Treat the architecture file as read-only for this implementation cycle.
3. **Files/artifacts created or modified:** No architecture modification; write only `v1/dist/certification/E0.02.log` and its result JSON.
4. **Build command:** direct host SHA-256 verification using project-local Python (or a saved host verifier) before `run.py` exists; do not invoke the test driver.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Hash equals `F76281FAB2E5AE73B7321FC2A69E6776F7CCD8BFE3955A6ED6FB3BEC44F762C7` and no superseded architecture is consumed.
9. **Negative/failure test:** Point the audit helper at a wrong hash and require refusal.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/E0.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## E0.03 - Deterministic test-driver skeleton

1. **Purpose / REV11 requirement:** REV11 §§37,39-41; handover canonical Python orchestration.
2. **Exact implementation work:** Create one host-only test driver under the architecture-provided `tools-host/test-driver` directory. It resolves the root through `.zxux-root`, invokes project-local tools by absolute root-relative paths, supplies FUSE argv as an argument list, enforces hard timeouts, and records commands, exit codes, hashes, debugger assertions, and stderr/stdout.
3. **Files/artifacts created or modified:** `v1/tools-host/test-driver/run.py`; `v1/docs/test-plan.md`.
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step E0.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** No PATH resolution; no drive-letter dependency; timeout kills the emulator subprocess and fails the test.
9. **Negative/failure test:** Run from a copied project on a different drive/path and require the same root-relative behavior.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/E0.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## E0.04 - Build/check-in evidence protocol

1. **Purpose / REV11 requirement:** REV11 ordered programming cycle and handover Git philosophy.
2. **Exact implementation work:** Define the per-step build/test/check-in protocol and evidence manifest. A step is complete only with clean build, static checks, required emulator/format tests, required negative test, retained evidence where specified, and clean Git worktree after commit.
3. **Files/artifacts created or modified:** `v1/docs/test-plan.md`; `v1/dist/certification/README.md`.
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step E0.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Evidence manifest rejects missing hashes, missing PASS marker, or dirty-worktree certification.
9. **Negative/failure test:** Delete one required evidence field and require the certification helper to fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/E0.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## E0.05 - Assembly-language project rules

1. **Purpose / REV11 requirement:** REV11 §38 and handover SjASMPlus rules.
2. **Exact implementation work:** Freeze every REV11 §38 coding rule in one executable policy checklist: one canonical assembler syntax; explicit hexadecimal notation; documented-Z80-only portable baseline, with undocumented opcodes confined to a separately named optional CPU profile and independent compatibility tests; IY is OS/ROM-reserved; MEX1 application code may not keep persistent task state via `EXX` or `EX AF,AF'`; every exported routine documents inputs, outputs, flags and clobbers; every ROM call goes through `rom_services.asm`; each syscall number is declared exactly once; no magic addresses outside named memory-map constants; no duplicated screen-address formula; no unchecked arena-pointer arithmetic; stack assumptions are documented; substantial code/buffers have explicit hot/cold placement; `LDIR`/`LDDR`/`CPIR`/`CPDR` are considered before generic byte loops, while small fixed transfers are measured rather than blindly forced through block instructions; `DJNZ`, relative branches, conditional returns, `EX DE,HL`, documented 16-bit arithmetic, bit operations and indirect dispatch are preferred only when semantically exact and objectively smaller/faster; ULA output changes only through the central shadow/update path; no persistent kernel datum lives only in alternate/shadow registers; critical routines record byte-size and cycle-count measurements; cycle measurements touching 0x4000-0x7FFF distinguish contended from uncontended execution/data access; shipped host/source filenames are lower-case unless a format/external-tool contract requires otherwise; and case-sensitive user-object behavior is tested at module boundaries. Also retain the handover SjASMPlus rule that unlabelled directives/instructions are indented, forbid correctness/security dependence on R, and forbid correctness dependence on precise ULA contention timing. Treat documented block transfer/search instructions as first-class review candidates where they reduce code without changing semantics. The R refresh register may be used only as one input to non-security pseudorandom seeding; no correctness, identity, uniqueness, or security decision may depend on R. Correctness may never depend on precise ULA contention timing.
3. **Files/artifacts created or modified:** `v1/docs/abi.md`; `v1/include/zx48ux.inc` scaffold.
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step E0.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** A policy-oracle fixture covers every listed §38 rule and the handover SjASMPlus indentation rule; positive source passes, while one fixture per rule is rejected or flagged for mandatory review/measurement as appropriate. Static policy also rejects correctness/security dependence on R or ULA contention phase and records whether a block instruction was considered for applicable byte loops.
9. **Negative/failure test:** Deliberately violate each mechanically checkable rule in isolation (including raw ROM literal, duplicate syscall declaration, magic address, persistent IY/alternate-bank use, direct ULA write, unchecked arena arithmetic, duplicate screen formula, undocumented opcode, or wrong-case shipped source name) and require deterministic policy failure; measurement/review-only rules must produce a missing-evidence failure rather than silently PASS.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/E0.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## E0.06 - Emulator-test safety contract

1. **Purpose / REV11 requirement:** REV11 §40; handover SNA/ROM-call stack lesson.
2. **Exact implementation work:** Freeze the complete REV11 §40 four-level evidence hierarchy: (1) static assembly/format checks cover duplicate symbols, section overflow, every fixed kernel subrange, IM2 vector/trampoline, kernel-stack placement, FAST/CONTENDED arena boundaries, syscall-table duplication, statically detectable forbidden user IY/alternate-register use, and object-format structure sizes; (2) deterministic emulator tests use SNA as the fast inner loop and TAP/TZX where boot/tape semantics matter, assert RAM/register/process state rather than screenshot-only output, establish a known writable stack before any synthetic ROM CALL, and apply hard subprocess timeouts; (3) release-critical behavior is repeated on at least two independent Spectrum emulators where practical; (4) final physical cassette robustness requires real 48K-compatible hardware with audio path or a hardware-faithful EAR/MIC loop that exercises ROM tape timing. TAP/TZX or trap-only emulator success must never be reported as physical EAR/MIC certification.
3. **Files/artifacts created or modified:** `v1/docs/test-plan.md`; `v1/tests/emulator/` harness fixtures.
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step E0.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Static oracle catches every §40.1 class; emulator debugger proves expected registers/RAM and safe SP; timeout is killed and reported FAIL; evidence metadata distinguishes deterministic-emulator, second-emulator, and physical EAR/MIC classes; no screenshot-only assertion can satisfy a correctness gate.
9. **Negative/failure test:** Use the known unsafe SNA ROM-call stack, omit one §40.1 static class, supply only one emulator while claiming compatibility PASS, or supply TAP/TZX/trap evidence while claiming physical cassette robustness; each claim is rejected deterministically.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/E0.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 0 - Hardware, ROM Inventory, and ROM Proof

## P0.01 - Hardware baseline, memory map and contention constants

1. **Purpose / REV11 requirement:** §§3-4,46,65
2. **Exact implementation work:** Freeze the original unexpanded 48K Spectrum baseline: documented Z80A at approximately 3.5 MHz, standard PAL/UK 50 Hz frame profile, 64 KiB CPU address space with 16 KiB ROM plus 48 KiB RAM and no RAM-under-ROM/bank switching, exact ROM/display/compat/COLD/FAST/kernel boundaries and contention classes. Freeze required base I/O scope as keyboard, bitmap, attributes, border, beeper, EAR, MIC and cassette load/save. NTSC machines or clones with different frame timing require a separately named compatibility profile and MUST NOT silently reuse the PAL 50-frames-per-second wall-clock constant. Joystick, printer, Interface 1, Microdrive, serial adapters, mouse and other extensions are outside the version-1 hardware requirement.
3. **Files/artifacts created or modified:** `v1/include/zx48ux.inc`; host hardware/profile and boundary tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Assert exact address/constants and no overlap; PAL profile exposes 50 Hz timing and the original 48K contention split; required base-I/O capability list is complete; non-PAL profiles cannot inherit the 50-Hz wall-clock constant without an explicit compatibility-profile definition.
9. **Negative/failure test:** Off-by-one each upper boundary; select an NTSC/different-frame-timing fixture while silently retaining the PAL 50-Hz wall-clock constant and require failure; omit one required base I/O class or mark an extension as mandatory v1 hardware and require the baseline-policy test to fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.02 - Kernel fixed-subrange linker scaffold

1. **Purpose / REV11 requirement:** §4.1-4.2, §44, §65
2. **Exact implementation work:** Link an 8192-byte kernel image at E000 with code/data pool, stack, reserves, FDFD trampoline, FE00-FF00 table and FF01 reserve explicitly protected. Freeze the complete REV11 §4.2 ordinary-kernel code/data planning ledger exactly: syscall gateway/entry 128 bytes; scheduler/process/open-description 896; allocator 448; pipe subsystem 640; ROM wrappers 704; console/keyboard/ULA + tty64 832; graphics primitives 608; UDG subsystem 192; cassette object layer 672; RAM object namespace 640; resident zxpack codec/manager 384; interrupt/time/error core 448; tables/strings 192. These thirteen targets total exactly 6784 bytes inside the 6912-byte 0xE000-0xFAFF ordinary pool, leaving exactly 128 bytes unassigned growth margin. The separate 0xFD00-0xFDFC and 0xFF01-0xFFFF reserves are not ordinary code/data growth space.
3. **Files/artifacts created or modified:** `v1/src/kernel/kernel.asm`; linker/assert script
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Map asserts E000-FFFF exact 8192 and code/data <=6912. The budget ledger contains all thirteen REV11 §4.2 categories with exact byte targets, sums to 6784, and leaves exactly 128 bytes unassigned inside the 6912-byte ordinary pool; fixed fast/emergency reserves are excluded from that margin.
9. **Negative/failure test:** Force one-byte overlap into FB00 and require build failure. Also change, omit, duplicate, or silently rebalance any one of the thirteen §4.2 planning targets, make their total differ from 6784, consume the 128-byte unassigned margin on paper, or count FD00-FDFC/FF01-FFFF as ordinary growth space; the architecture-budget oracle must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.03 - Syscall and boot trampolines

1. **Purpose / REV11 requirement:** §4.1, §5, §65
2. **Exact implementation work:** Emit exactly JP dispatch at E000-E002 and JP boot-main at E003-E005.
3. **Files/artifacts created or modified:** `v1/src/boot/entry.asm`; `v1/src/kernel/syscall.asm`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA reads first six bytes and resolves both jump targets.
9. **Negative/failure test:** Move either trampoline by one byte.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.04 - IM2 vector/trampoline scaffold

1. **Purpose / REV11 requirement:** §4.1, §46, §65
2. **Exact implementation work:** Initialize FE00-FF00 with FD while DI; FDFD is exactly a 3-byte absolute JP to `zx48_interrupt`; set I=FE only after table is complete.
3. **Files/artifacts created or modified:** `v1/src/kernel/im2.asm`; `v1/src/kernel/interrupt.asm`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA synthesizes all 256 low-vector bytes and proves every vector resolves FDFD.
9. **Negative/failure test:** Corrupt one table byte and require one vector case to fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.05 - IY ROM anchor scaffold

1. **Purpose / REV11 requirement:** §3, §14, §46, §65
2. **Exact implementation work:** Establish and document production IY=5C3A (ERR_NR), preserve/restore it at every public kernel return and approved ROM wrapper.
3. **Files/artifacts created or modified:** `v1/include/zx48ux.inc`; `v1/src/kernel/rom_services.asm` scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA wrapper fixture checks IY before/after.
9. **Negative/failure test:** Wrapper fixture clobbers IY and must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.06 - Alternate-register safety scaffold

1. **Purpose / REV11 requirement:** §§2.8,6,14,46,65
2. **Exact implementation work:** Reserve AF'/BC'/DE'/HL' to OS; classify wrappers as safe/unsafe with interrupt path; no persistent kernel state only in shadow bank.
3. **Files/artifacts created or modified:** `v1/src/kernel/interrupt.asm`; `v1/docs/rom-services.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Synthetic ROM window proves fast path and safe fallback preserve required state.
9. **Negative/failure test:** Mark an unsafe wrapper fast-safe and require classifier test failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.07 - Canonical BASIC autoloader

1. **Purpose / REV11 requirement:** §5.2, §46, §65
2. **Exact implementation work:** Create the exact five-line semantic loader and auto-start line 10; preserve lower-case tape filename `zx48ux`.  Sinclair BASIC keyword capitalization/token spelling belongs only to the bootstrap language/listing convention; it is outside the ZX-UX shell namespace and MUST NOT create case-folded aliases or relax lower-case shipped-name rules.
3. **Files/artifacts created or modified:** `v1/src/boot/loader.bas`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host token inspection proves CLEAR 24575, SCREEN$, CODE, USR 57347 and auto-line 10.
9. **Negative/failure test:** Change CLEAR or USR address.  Treating uppercase/lowercase Sinclair BASIC keyword spelling as permission for case-insensitive ZX-UX command or object lookup fails the architecture oracle.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.08 - Canonical loading SCREEN$

1. **Purpose / REV11 requirement:** §5.3, §44, §46, §65
2. **Exact implementation work:** Create/freeze one native 6912-byte Spectrum screen artifact for 4000-5AFF. Artwork is not ABI; size/address and tape name are.
3. **Files/artifacts created or modified:** `v1/assets/loading.scr`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host exact size/hash; TAP load probe checks bytes at 4000-5AFF.
9. **Negative/failure test:** Use 6911/6913-byte fixture and require builder rejection.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.09 - Native bootstrap prefix builder

1. **Purpose / REV11 requirement:** §§5.1-5.2,39,46,65
2. **Exact implementation work:** Implement deterministic native Spectrum logical files `zx48ux`, `zx48uxscr`, `kernel` in that order using ROM-compatible headers/data.  The production builder must reject a loading-screen data length other than exactly 6912, a kernel CODE start other than 0xE000, a kernel data length other than exactly 8192, a native-file name/order mismatch, or a loader boot gateway other than the frozen 0xE003/57347 contract before emitting a release candidate.
3. **Files/artifacts created or modified:** `v1/tools-host/maketap/`; `v1/tools-host/cassette-image/`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Build twice; byte-identical TAP; inspect header names, addresses, lengths.  Independent parsing verifies `zx48ux`,`zx48uxscr`,`kernel` order, lower-case Spectrum header names, SCREEN$ length 6912, kernel start 0xE000/length 8192, and loader USR 57347.
9. **Negative/failure test:** Wrong kernel address/length/name/order rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.10 - Five-resource bootstrap-prefix validator

1. **Purpose / REV11 requirement:** §§4.3A-4.3B,5.1,5.6,65
2. **Exact implementation work:** Add contract-valid Phase-0 stubs and validate exact M48O names/order/types/targets: sh,font4x8,issue,crontab,bincat. Freeze the `issue` logical target bytes exactly as `<0x7F> Supratim Sanyal, SANYALnet Labs<LF>`, `https://supratim-sanyal.blogspot.com/<LF>`, `48K. One Z80. No excuses.<LF>`; freeze `crontab` as zero-length RAW and freeze the BCAT shape even before final binaries exist.
3. **Files/artifacts created or modified:** `v1/assets/font4x8.bin`; `issue.txt`; `crontab.txt`; `bincat.bin`; maketap tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host validator checks exact five-resource contract and rejects case-folding.
9. **Negative/failure test:** Swap resources or uppercase a name.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.11 - Cold boot native LOAD proof

1. **Purpose / REV11 requirement:** §5, §41.1, §46, §65
2. **Exact implementation work:** Boot the fixture using only ordinary `LOAD ""`; prove BASIC auto-runs and consumes SCREEN$/kernel in order.
3. **Files/artifacts created or modified:** `v1/tests/cassette/boot_native.py`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** TAP/FUSE: breakpoints and RAM asserts at screen/kernel completion and USR handoff.
9. **Negative/failure test:** Missing/corrupt screen and kernel fail before uninitialized execution.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.12 - Permanent BASIC-to-kernel handoff

1. **Purpose / REV11 requirement:** §5.4-5.5, §46, §65
2. **Exact implementation work:** At E003 execute DI, abandon BASIC return frame, set SP=FD00 immediately, and never return through USR.
3. **Files/artifacts created or modified:** `v1/src/boot/entry.asm`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA/TAP breakpoints prove SP=FD00 before substantial work and no BASIC return.
9. **Negative/failure test:** Place sentinel BASIC return and fail if PC reaches it.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.13 - Loading-screen preservation

1. **Purpose / REV11 requirement:** §5.3-5.5, §41.1, §65
2. **Exact implementation work:** Make low-level kernel initialization avoid 4000-5AFF until PID1 deliberately replaces it.
3. **Files/artifacts created or modified:** boot/kernel init files; `v1/tests/emulator/boot_screen.py`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Hash display before kernel init and after five-resource load; hashes identical.
9. **Negative/failure test:** Deliberately clear one screen byte in test build and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.14 - Panic output and safe halt

1. **Purpose / REV11 requirement:** §5.7, §34, §35, §46, §65
2. **Exact implementation work:** Implement post-handoff `PANIC <code>` plus compact reason, numeric code-to-documentation mapping, and deterministic safe halt/recovery point without BASIC return. Reserve PANIC for exactly REV11's five corruption classes: corrupted process table; allocator invariant failure; impossible scheduler state; kernel stack failure; unrecoverable ROM-wrapper contract violation. Ordinary resource/input/format/permission and other recoverable failures return the specified errno and concise user-space diagnostics instead of panicking. Debug builds may add invariant checks; release builds retain checks needed to prevent corruption propagation.
3. **Files/artifacts created or modified:** `v1/src/kernel/errors.asm`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Each of the five corruption classes reaches its documented numeric PANIC code and deterministic safe halt; ordinary recoverable failures return errno without PANIC; no path returns to BASIC after handoff.
9. **Negative/failure test:** An unhandled reserved corruption class, a sixth ordinary error incorrectly promoted to PANIC, a PANIC lacking numeric documentation mapping, or any return to BASIC fails the gate.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.15 - ROM-disassembly provenance

1. **Purpose / REV11 requirement:** §§2.3,14,46,64
2. **Exact implementation work:** Freeze the exact reference provenance required by REV11 §64 before any ROM/CPU contract can close. The primary ROM research baseline is `The Complete Spectrum ROM Disassembly`, Ian Logan and Frank O'Hara, using the current maintained SkoolKit 48K ROM rendering; retain the exact local source/version/revision information actually used to freeze each adopted ROM routine together with the canonical 16384-byte 48K ROM hashes. Record the Zilog Z80 CPU User Manual (project-local `reference/zilog/UM0080-z80-user-manual.pdf`, or the exact root-relative canonical successor if the repository layout is formally updated) as normative for documented Z80 behavior used by ZX-UX, including IM2, alternate-register exchange, block transfer/search, relative branches and interrupt return. Record the original 48K Spectrum memory-map/reference source used for the normative 0x4000-0x7FFF contended / 0x8000-0xFFFF uncontended classification. `docs/rom-services.md` must identify the precise disassembly source/version for every frozen wrapper contract; a title alone without source/version is insufficient. Create the zero-gap inventory-ledger provenance columns before classification.
3. **Files/artifacts created or modified:** `v1/docs/rom-services.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host provenance audit verifies the canonical 16K ROM identity, exact `The Complete Spectrum ROM Disassembly` / Ian Logan / Frank O'Hara / maintained SkoolKit 48K baseline identification, per-wrapper disassembly source/version fields, the project-local Zilog UM0080 normative CPU reference, and the recorded original-48K contention reference before any ROM wrapper/CPU assumption is certified.
9. **Negative/failure test:** Wrong ROM SHA-256, unnamed/ambiguous ROM disassembly provenance, missing Ian Logan/Frank O'Hara/SkoolKit baseline, missing per-wrapper source/version, substituting undocumented CPU behavior for the Zilog documented baseline, or an untraceable contention-map claim fails the Phase-0 provenance gate.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.16 - Complete ROM useful-routine inventory

1. **Purpose / REV11 requirement:** §§2.3,14.1-14.3A,14.9,46
2. **Exact implementation work:** Mine the authoritative 48K disassembly end-to-end for plausible reusable keyboard, console, screen, graphics, sound, cassette, numeric, FP/math, conversion, string and BASIC-expression services. Classify every plausible candidate A/B/C/reject with reason. Freeze initial Class-A targets: keyboard scan/decoding, compatible character output, compatible screen clear/scroll, PIXEL-ADD, POINT, PLOT-SUB, lower line drawing, BEEPER, SA-BYTES, LD-BYTES. Freeze initial Class-B targets: BEEP command, FP-CALC/CALCULATE, integer<->Spectrum-float conversion, float printing/arithmetic, ABS/SGN/INT, EXP/LN, SIN/COS/TAN, ASN/ACS/ATN, SQR/exponentiation, numeric/string conversion, and restricted BASIC expression scanning; these are kernel-serialized and never directly callable by normal user programs. Freeze initial Class-C exclusions: BASIC MAKE-ROOM/RECLAIM, BASIC variable storage as the OS object model, full BASIC program execution as shell infrastructure, NEW/CLEAR/RUN as OS operations, unrestricted POKE/OUT/USR, BASIC global streams/channels as the handle layer, and BASIC full line editor as source editor. For every adopted wrapper record symbolic wrapper name, ROM address, routine/disassembly name, A/B/C class, input/output/clobbered registers, flags, alternate-register effects, IX/IY effects, system variables read/written, calculator-stack effects, workspace effects, interrupt enable/disable behavior, ROM error/RST8 path, BREAK behavior, reentrancy, and whether a task switch is permitted. For each Class-A/B routine classify alternate-bank behavior as does-not-use, uses-but-preserves, clobbers, or unknown=>clobbers; no persistent kernel state may exist only in the alternate bank. A ROM-backed implementation may be replaced by RAM code only if at least one REV11 threshold is proved: unsafe under kernel error model, irreconcilable multiprocessing workspace conflict, semantics cannot satisfy ZX-UX ABI, deterministic unacceptable behavior, or measured size/performance benefit worth RAM cost; cleaner code alone is not sufficient.
3. **Files/artifacts created or modified:** `v1/docs/rom-services.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host inventory completeness checklist against disassembly headings/entry labels, exact A/B/C initial sets, exact wrapper-ledger columns and replacement-threshold decision record.
9. **Negative/failure test:** Remove one required candidate family/ledger column or approve a RAM replacement solely because it is cleaner; audit must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.17 - ROM service-address centralization

1. **Purpose / REV11 requirement:** §§2.3,14.1,38,46
2. **Exact implementation work:** Place every approved production ROM address in `v1/src/kernel/rom_services.asm`; no other production source may contain a raw ROM service literal. Freeze the authoritative baseline address table: 0x0010 PRINT-A, 0x0028 FP-CALC, 0x028E KEY-SCAN, 0x02BF KEYBOARD, 0x0333 keyboard decoding, 0x03B5 BEEPER, 0x03F8 BEEP command, 0x04C2 SA-BYTES, 0x0556 LD-BYTES, 0x22AA PIXEL-ADD, 0x22CB POINT, 0x22E5 PLOT-SUB, 0x24B7 DRAW-LINE conversion entry, 0x24BA lower line-drawing entry, 0x2DA2 floating-point-to-BC, 0x2DE3 floating-point printing, 0x335B CALCULATE, 0x36AF INT, 0x36C4 EXP, 0x3713 LN, 0x37AA COS, 0x37B5 SIN, 0x37DA TAN, 0x37E2 ATN, 0x3833 ASN, 0x3843 ACS, 0x384A SQR, 0x3851 exponentiation. Address presence alone never authorizes a wrapper; every adopted entry must also satisfy the complete P0.16 contract.
3. **Files/artifacts created or modified:** `v1/src/kernel/rom_services.asm`; static scanner; `v1/docs/rom-services.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Static scan, assembler symbol map and host oracle prove the exact baseline symbolic-address table and reject any production raw ROM literal outside the owning module.
9. **Negative/failure test:** Introduce one wrong baseline address or one raw 0x0556 elsewhere and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.18 - Keyboard and character-output ROM proof

1. **Purpose / REV11 requirement:** §§13-14,46,65
2. **Exact implementation work:** Prove selected keyboard scan/input and character output candidates with exact registers, flags, clobbers, workspace, error and interrupt contracts.
3. **Files/artifacts created or modified:** rom services/doc; emulator fixtures
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA scripted key path and output state; IY/shadow-register checks.
9. **Negative/failure test:** Wrong key row or corrupted IY fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.19 - Screen-address / PIXEL-ADD / POINT proof

1. **Purpose / REV11 requirement:** §§3.3,14-15,46
2. **Exact implementation work:** Freeze one canonical pixel-address helper and prove approved ROM PIXEL-ADD/POINT behavior at documented edge coordinates.
3. **Files/artifacts created or modified:** graphics/rom services scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA edge vectors 0,0 / max valid / invalid contract edges.
9. **Negative/failure test:** One out-of-range coordinate must follow documented error policy.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.20 - PLOT-SUB proof

1. **Purpose / REV11 requirement:** §14, §15, §46, §65
2. **Exact implementation work:** Verify PLOT-SUB wrapper contract and screen/attribute bounds.
3. **Files/artifacts created or modified:** rom services/graphics scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA verifies target pixel only plus documented attributes.
9. **Negative/failure test:** Clobber guard bytes around display and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.21 - Lower DRAW proof

1. **Purpose / REV11 requirement:** §14, §15, §46, §65
2. **Exact implementation work:** Verify the lower line-drawing entry chosen by Phase 0 including register/workspace contract.
3. **Files/artifacts created or modified:** rom services/graphics scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA line vectors incl clipping/error contract from ROM proof.
9. **Negative/failure test:** Call wrong DRAW entry fixture and require signature mismatch.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.22 - BEEPER low-level proof

1. **Purpose / REV11 requirement:** §§14,17,46,65
2. **Exact implementation work:** Verify 0x03B5 BEEPER path, interrupt behavior and ULA shadow restoration requirements.
3. **Files/artifacts created or modified:** rom services/sound scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA/FUSE observes return state and documented interrupt/port-shadow contract.
9. **Negative/failure test:** Invalid direct register fixture must be rejected by wrapper test.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.23 - BEEP-command public-wrapper proof

1. **Purpose / REV11 requirement:** §§14,17,46,65
2. **Exact implementation work:** Verify 0x03F8 BEEP-command/public BASIC-compatible path and decide exact safe numeric/error gateway used by future `SYS_BEEP`.
3. **Files/artifacts created or modified:** rom services/sound scaffold; docs
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA proves representative positive, negative and fractional pitch through numeric bridge where Phase0 permits.
9. **Negative/failure test:** ROM-domain error must map to controlled E_INVAL path, never BASIC escape.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.24 - SA-BYTES cassette-save proof

1. **Purpose / REV11 requirement:** §§14,19,46,65
2. **Exact implementation work:** Verify ROM SA-BYTES machine contract including A block type, DE length, IX start, interrupt critical section and error recovery.
3. **Files/artifacts created or modified:** rom services/tape scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** TAP/TZX fixture and debugger stack/register assertions.
9. **Negative/failure test:** Bad checksum/forced abort follows controlled policy.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.25 - LD-BYTES cassette-load proof

1. **Purpose / REV11 requirement:** §§14,19,46,65
2. **Exact implementation work:** Verify ROM LD-BYTES exact contract with an explicitly safe writable test stack; reuse the certified trap model.
3. **Files/artifacts created or modified:** rom services/tape scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.25`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** TAP/TZX fixture loads known bytes; RAM/regs/SP exact.
9. **Negative/failure test:** Unsafe-stack fixture is detected; corrupt block rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.25.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.26 - FP-CALC/CALCULATE atomic calculator service proof

1. **Purpose / REV11 requirement:** §§14.5,25,46,65
2. **Exact implementation work:** Implement/prove the serialized calculator gateway using five-byte ZX-UX/Spectrum numeric values and no cooperative task switch inside an operation. For every call: (1) validate pointers/op code, (2) enter calculator critical section, (3) save promised calculator/system-variable state, (4) copy inputs to controlled workspace, (5) invoke verified ROM operation, (6) capture ROM error into ZX-UX errno, (7) copy result to caller memory, (8) restore protected ROM state, (9) leave critical section, (10) return without yielding. Freeze the initial operation set ADD,SUB,MUL,DIV,POW,ABS,SGN,INT,EXP,LN,SIN,COS,TAN,ASN,ACS,ATN,SQR and record exact ROM calculator literals/entry contracts in `docs/rom-services.md`.
3. **Files/artifacts created or modified:** rom services math scaffold; `v1/docs/rom-services.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.26`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA exercises every operation ID with golden five-byte values and proves the ten-step critical-section state restoration/no-yield contract.
9. **Negative/failure test:** Unknown op, invalid pointer/domain/error path, or an injected scheduler yield inside the critical section must fail safely and never escape to BASIC.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.26.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.27 - SIN and SQR proof

1. **Purpose / REV11 requirement:** §§14,25,46,65
2. **Exact implementation work:** Prove required transcendental candidates SIN and SQR through the same serialized calculator gateway.
3. **Files/artifacts created or modified:** rom services math scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.27`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA golden values and round-trip conversion checks.
9. **Negative/failure test:** Malformed numeric state must fail safely.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.27.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.28 - Numeric integer/float/text conversion proof

1. **Purpose / REV11 requirement:** §§14,25,46,65
2. **Exact implementation work:** Prove integer<->five-byte float and float-to-text candidates selected for C48/shell use.
3. **Files/artifacts created or modified:** rom services math scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.28`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA boundary integer and text vectors.
9. **Negative/failure test:** Overflow/domain vector returns documented failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.28.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.29 - Restricted calc-scanner feasibility decision

1. **Purpose / REV11 requirement:** §14.6, §46, §65
2. **Exact implementation work:** Attempt isolation of the ROM BASIC expression scanner under the exact case-sensitive public grammar: decimal numeric literals; unary + and -; binary + - * / ^; parentheses; pi; abs,sgn,int,sqrt,exp,ln,sin,cos,tan,asin,acos,atan. `rnd` is deferred. Lower-case public names may be translated to ROM tokens but this is not case folding: uppercase spellings such as SIN are not aliases. Reject before ROM evaluation: peek,in,inkey$,screen$,attr,point,usr,poke,out,clear,new,run,load,save,merge,randomize usr, variable assignment, BASIC statements, and string expressions unless separately specified. If parser-state isolation is not robust, freeze the architecture fallback: ZX-UX tokenizer with the same grammar and ROM calculator backend.
3. **Files/artifacts created or modified:** `v1/docs/rom-services.md`; parser proof fixtures
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.29`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host+SNA accepts every allowed grammar family and rejects every forbidden family/case variant before unsafe ROM action; selected implementation path and parser-state proof are recorded.
9. **Negative/failure test:** `rnd`, uppercase aliases, PEEK/USR/POKE/OUT/assignment/string/BASIC-statement forms, or any unlisted token reaching unsafe ROM evaluation fails the gate.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.29.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.30 - ROM error-recovery trampoline proof

1. **Purpose / REV11 requirement:** §§14.4,35,46,65
2. **Exact implementation work:** Classify every adopted ROM wrapper error behavior as exactly one of RETURNS_STATUS, RETURNS_CARRY, MAY_RST8_ERROR, MAY_ABORT_ON_BREAK, NEVER_RETURNS_ON_ERROR. For every wrapper that can enter RST8/BASIC error flow or abort on BREAK, implement and instruction-test a controlled ZX-UX recovery/trampoline before enabling it; if no safe mechanism exists, reject that ROM routine from the normal OS API.
3. **Files/artifacts created or modified:** rom services/errors; `v1/docs/rom-services.md`; per-wrapper tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.30`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** SNA forces each of the five error classes where applicable and proves return-to-caller/controlled errno or safe panic exactly, with no uncontrolled BASIC control-flow escape.
9. **Negative/failure test:** One adopted wrapper missing one of the five classifications or a safe policy keeps Phase0 red.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.30.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.31 - ROM system-variable ownership ledger

1. **Purpose / REV11 requirement:** §§14.8-14.8A,4.3
2. **Exact implementation work:** Classify every live ROM system variable as exactly KERNEL, CONSOLE, GRAPHICS, TAPE, CALCULATOR, or ROM_TRANSIENT; processes may not rely on undocumented BASIC system-variable contents across syscall/task switch. Freeze FRAMES at 23672-23674 and UDG at 23675-23676 as explicit compatibility state, never accidental inherited BASIC state. Plan the accepted-frame FRAMES mirror and the boot-time repoint of UDG to a kernel-owned pinned 256-byte 32-slot bank outside kernel/IM2 memory, with the exact resulting UDG pointer recorded in `docs/rom-services.md`.
3. **Files/artifacts created or modified:** `v1/docs/rom-services.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.31`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host ledger completeness proves all live variables have one owner, exact FRAMES/UDG addresses are present, and the planned UDG target lies in a valid arena extent outside E000-FFFF/IM2.
9. **Negative/failure test:** Missing owner, inherited BASIC FRAMES/UDG state, or UDG pointer into E000-FFFF is rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.31.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.32 - Host ZXP1 reference encoder/decoder

1. **Purpose / REV11 requirement:** §§2.12,27.3,41.3A,46,65
2. **Exact implementation work:** Implement the exact ZXP1 stream grammar: tokens 0x00..0x3F are LITERAL with length=token+1 (1..64) followed by exactly that many literal bytes; 0x40..0x7F are RLE with length=(token&0x3F)+3 (3..66) followed by one repeated byte; 0x80..0xFF are BACKREF with length=(token&0x7F)+3 (3..130) followed by distance_minus_1, giving distance 1..256. BACKREF copies one byte at a time from already-emitted logical output and may overlap; distance may not exceed bytes already emitted. There is no terminator: success consumes exactly physical length and emits exactly declared logical length. Empty logical objects have empty physical streams and remain RAW; PACKED is valid only when physical length is strictly smaller than logical length. The host encoder may use dynamic programming/optimal parsing, but may emit only this grammar; host output need not be byte-identical to the target greedy encoder, yet both must decode to identical logical bytes. Freeze the host encoder version/options for release so identical inputs produce identical tape images.
3. **Files/artifacts created or modified:** `v1/tools-host/zxpack/`; `v1/docs/zxpack.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.32`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host reference encoder/decoder is normative. Boundary vectors for token 0x00/0x3F/0x40/0x7F/0x80/0xFF, distance 1/256, overlap, empty/one-byte/random/incompressible data, malformed/truncated and declared-length under/overrun cases plus exhaustive/random round trips decode byte-identically; fixed release encoder version/options make identical inputs produce identical tape-image hashes.
9. **Negative/failure test:** Truncated literal/RLE/BACKREF, backref before logical start, output overrun/underrun, trailing physical bytes, illegal empty PACKED object, or PACKED length not strictly smaller fails E_FORMAT-equivalent.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.32.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.33 - ZXP1 adversarial/random corpus

1. **Purpose / REV11 requirement:** §41.3A, §46
2. **Exact implementation work:** Generate deterministic random/adversarial corpus and freeze expected packed/logical hashes for later target-code cross-check.
3. **Files/artifacts created or modified:** `v1/tests/compression/` vectors
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.33`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host reference decode identity for all corpus entries.
9. **Negative/failure test:** Mutate one token per class and require deterministic rejection.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.33.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P0.34 - Phase-0 zero-gap ROM and memory gate

1. **Purpose / REV11 requirement:** §46 acceptance; §65 first deliverable
2. **Exact implementation work:** Run every Phase-0 acceptance item, then repeat the complete ROM inventory after classification. Phase 1 is forbidden while any plausible useful ROM subsystem remains unclassified.  Execute the Phase-0 acceptance gate as seventeen individually recorded checks, not as a section-reference shortcut: (1) every production ROM address used by code is documented and verified; (2) no production ROM address exists outside `rom_services.asm`; (3) every approved wrapper has an exact machine contract; (4) every wrapper that can enter a ROM error restart has a tested safe recovery policy or is rejected; (5) every Class-B facility has a proved serialization/workspace policy; (6) cassette transport round-trip succeeds in a 48K environment; (7) graphics proof succeeds at the edge coordinates defined by the selected ROM contract; (8) calculator arithmetic and transcendental proof succeed; (9) a zero-gap ROM inventory review finds no substantial safe ROM facility needlessly reimplemented in RAM; (10) all 256 synthetic IM2 low-vector bytes reach the same trampoline; (11) frozen IY=0x5C3A survives every approved ROM-wrapper proof; (12) every wrapper is classified for alternate-register/interrupt safety; (13) the production BASIC loader auto-starts from ordinary `LOAD ""` and loads the exact SCREEN$/kernel sequence; (14) kernel entry 0xE003 permanently takes ownership and never returns to BASIC; (15) the screen is exactly 6912 bytes and remains visible until deliberately replaced; (16) the kernel is exactly 8192 bytes at 0xE000-0xFFFF; (17) the ZXP1 host reference round-trips zero length and every boundary command length, rejects malformed token/length/distance cases deterministically, and round-trips the deterministic random corpus byte-identically. After all seventeen pass, repeat the complete zero-gap ROM scan; Phase 1 remains forbidden while any potentially useful ROM subsystem is unclassified.
3. **Files/artifacts created or modified:** Phase0 evidence manifest
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P0.34`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Aggregate Phase0 suite incl 256 IM2 vectors, IY/alternate-register wrappers, boot, screen, kernel, tape, calculator, ZXP1.  The retained Phase-0 manifest has exactly seventeen numbered acceptance rows plus the repeated post-classification zero-gap scan; every row links to its owning earlier Phase-0 evidence and all rows PASS on the same candidate.
9. **Negative/failure test:** Delete/mark UNREVIEWED one ROM candidate; aggregate gate must fail.  Delete, skip, merge-away, or leave unresolved any one of the seventeen acceptance rows, or leave one plausible ROM subsystem unclassified after the repeat scan; P0.34 must remain red and Phase 1 must not begin.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P0.34.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 1 - Resident Kernel Skeleton

## P1.01 - Kernel image/BSS initialization

1. **Purpose / REV11 requirement:** §§4,5.5,47
2. **Exact implementation work:** Implement kernel startup/BSS clear that excludes display, ROM workspace, stack and vector ranges.
3. **Files/artifacts created or modified:** kernel.asm; entry.asm; kernel tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All fixed subranges unchanged except documented state; code/data <=6912.
9. **Negative/failure test:** Poison one excluded range and detect write.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.02 - Single contiguous arena extent allocator

1. **Purpose / REV11 requirement:** §§4.4,28,41.3,47
2. **Exact implementation work:** Implement one deterministic address-ordered free-extent map over 6000-DFFF with compact bounded metadata, split/coalesce, 2-byte alignment, and no hidden compaction that moves process images. Detect double free in debug builds where feasible. Maintain one combined live-allocation count and combined free total; an ANY extent crossing 7FFF/8000 remains one allocation even though its bytes contribute to both class-accounting ranges.
3. **Files/artifacts created or modified:** memory.asm; unit/emulator tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact-fit/split/free/coalesce/fragmentation, combined free/live-allocation accounting, cross-boundary one-allocation accounting, and debug double-free detection pass.
9. **Negative/failure test:** Double free/invalid extent rejected without corruption.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.03 - FAST_REQUIRED policy

1. **Purpose / REV11 requirement:** §4.4
2. **Exact implementation work:** Implement FAST_REQUIRED; never consume 6000-7FFF.
3. **Files/artifacts created or modified:** memory.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exhaust FAST and return E_NOMEM with COLD untouched.
9. **Negative/failure test:** Silent spill is fatal test failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.04 - COLD_PREFERRED and ANY policies

1. **Purpose / REV11 requirement:** §4.4
2. **Exact implementation work:** Implement COLD_PREFERRED and ANY including one contiguous extent crossing 7FFF/8000 and the preference not to fragment scarce FAST-only space. Maintain separately for FAST and CONTENDED ranges both total free bytes and largest free contiguous span, plus combined totals, while treating a cross-boundary ANY extent as one allocation.
3. **Files/artifacts created or modified:** memory.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Cross-boundary alloc/free/coalesce preserves exact per-FAST/per-CONTENDED free totals and largest spans, combined totals, and one-allocation identity; fragmentation and class-specific exhaustion fixtures pass.
9. **Negative/failure test:** Cross-boundary free with wrong bounds rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.05 - SYS_MEM_INFO / MINFO1 accounting scaffold

1. **Purpose / REV11 requirement:** §10.1, §41.3
2. **Exact implementation work:** Implement MINFO1-defined totals/largest extents/live/pinned/process fields exactly. Implement the public `SYS_MEM_INFO` ABI as HL -> writable exact 16-byte MINFO1: fast_free, fast_largest, cold_free, cold_largest, total_free, live_allocations, pinned_bytes (all u16), process_count u8, reserved=0. `total_free` is exactly fast_free+cold_free; live_allocations/pinned_bytes/process_count use the Section-10.1 definitions, excluding fixed kernel RAM and PID0 as specified. SYS_MEM_INFO consumes HL -> writable exact 16-byte MINFO1: fast_free u16, fast_largest u16, cold_free u16, cold_largest u16, total_free u16, live_allocations u16, pinned_bytes u16, process_count u8, reserved u8=0. total_free equals fast_free+cold_free; process_count counts non-FREE PID1..7 excluding PID0; pinned bytes are allocator-rounded arena bytes owned by pinned system resources.
3. **Files/artifacts created or modified:** memory.asm; abi.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** MINFO1 bytes match independent host recomputation. A byte-level MINFO1 oracle checks every offset and reserved byte across empty, fragmented, pinned-resource and live-process fixtures; arithmetic is widened before narrowing.
9. **Negative/failure test:** Counter overflow/wrong field offset fixture fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.06 - Process-state table and bounded process descriptors

1. **Purpose / REV11 requirement:** §§6.1-6.3,47
2. **Exact implementation work:** Implement exact ABI-visible state IDs 0 FREE, 1 READY, 2 RUNNING, 3 SLEEPING, 4 WAIT_INPUT, 5 WAIT_PIPE_READ, 6 WAIT_PIPE_WRITE, 7 WAIT_CHILD, 8 ZOMBIE; maximum 8 records with PID0/PID1 reservations. Each descriptor contains at minimum pid, parent_pid, state, private flags, image_base, image_size, stack_low, stack_high, saved_sp, exit_status, wait_object, handles[8] open-description IDs or 0xFF, wake_tick, cwd_directory_id, name[10], and owned-allocation metadata. Do not duplicate the canonical runnable CPU context in the descriptor: saved_sp is the resume token; PC/AF/BC/DE/HL/IX live in the FAST-stack frame; IY is global and alternate registers are not task-local. Include private STARTED, initially zero after successful spawn and set immediately before first restore, but never expose it through SYS_PROC_INFO.flags. Preserve the exact 1..10-byte NUL-or-full-ten process-name convention. Freeze <=56 bytes per descriptor, <=448 bytes for all eight descriptors, and account this together with the open-description table inside the fixed 896-byte scheduler/process/open-description planning budget.
3. **Files/artifacts created or modified:** `v1/src/kernel/process.asm`; `v1/include/zx48ux.inc`; `v1/docs/abi.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host layout check plus SNA table initialization prove every required field/offset used by the implementation, descriptor size <=56, eight descriptors <=448, PID/state limits, exact 10-byte name preservation, saved_sp-only context ownership and private STARTED behavior.
9. **Negative/failure test:** A 57-byte descriptor, ninth record, duplicated runnable CPU context, exposed STARTED bit, or process/open-description planning total >896 bytes must fail before check-in.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.07 - Canonical task context frame

1. **Purpose / REV11 requirement:** §6.2, §47
2. **Exact implementation work:** Define resume frame on FAST process stack: AF/BC/DE/HL/IX/return PC; saved SP is canonical; IY global; shadow regs volatile.
3. **Files/artifacts created or modified:** scheduler.asm; process.asm; abi.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Synthetic context switch restores exact primary regs, IX, SP, PC.
9. **Negative/failure test:** Persistent alternate-register assumption fails test.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.08 - PID0 HALT idle

1. **Purpose / REV11 requirement:** §§6.5-6.6,47
2. **Exact implementation work:** Implement PID0 as the non-exiting idle context selected only when no user READY task exists. PID0 scans/wakes expired sleepers, polls the minimal keyboard/event state required outside ISR context, never allocates user arena memory, and never exits. Its normal idle sequence is exactly EI; HALT followed by a scheduler/event check after the next accepted IM2 interrupt; no busy-spin idle loop and no HALT path with maskable interrupts disabled are permitted.
3. **Files/artifacts created or modified:** scheduler.asm; process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** With no user READY task, scheduler selects PID0, executes EI;HALT, resumes on IM2, performs wake/event checks and re-enters scheduling; allocator accounting proves PID0 made no user allocation.
9. **Negative/failure test:** Force PID0 to allocate arena memory, exit, busy-spin, or execute HALT while interrupts are disabled and require deterministic failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.09 - ABI syscall constants freeze

1. **Purpose / REV11 requirement:** §§8-10,47
2. **Exact implementation work:** Freeze Section-10.1 syscall IDs, errno values and packed record offsets in one include/doc pair only after executable tests exist. Freeze the version-1 syscall surface as exactly the 59 REV11 assignments and keep every unlisted numeric gap unassigned as deliberate expansion space; no implementation, alias, private public-entry handler, generated constant, or documentation row may consume a gap without a later architecture/ABI revision. For every ABI-visible number/record introduced here, create the conformance test/decoder first, then freeze the number/layout only after that test exists; kernel and userland consume the same generated constants rather than independently retyping Section-10.1 layouts. Freeze the universal syscall register/return convention exactly: entry A=syscall number, HL=primary argument/pointer, DE=secondary argument/pointer, BC=count/tertiary argument; success Carry=0, HL=primary result and A=0 unless specifically documented otherwise; failure Carry=1, A=errno and HL undefined unless specifically documented otherwise. AF/BC/DE/HL are volatile, IX is preserved, IY is OS/ROM-reserved and must equal 0x5C3A on every returning user boundary, alternate registers are OS-private/volatile, I is OS-owned and R has no preservation guarantee. Invalid syscall numbers return E_NOTSUP without indexing outside the dispatch table. Implement and measure the syscall-dispatch alternatives required by REV11 §9.1: compare the compact validated handler-address-table form against a long compare/branch chain on the actual target build, and prefer the table with indirect `JP (HL)` whenever measurement confirms it is smaller or faster. Bounds/validity checking occurs before table indexing, so the measured optimization can never weaken invalid-number safety; retain the measurement result and selected form as certification evidence. Freeze errno values exactly: 0 E_OK, 1 E_INVAL, 2 E_NOENT, 3 E_NOMEM, 4 E_BUSY, 5 E_IO, 6 E_EOF, 7 E_PERM, 8 E_CHILD, 9 E_PIPE, 10 E_TOOLONG, 11 E_FORMAT, 12 E_NOSPC, 13 E_AGAIN, 14 E_NOTSUP, 15 E_INTR, 16 E_EXIST. Freeze FPOP1.op numeric values exactly: 0 invalid, 1 ADD, 2 SUB, 3 MUL, 4 DIV, 5 POW, 6 ABS, 7 SGN, 8 INT, 9 EXP, 10 LN, 11 SIN, 12 COS, 13 TAN, 14 ASN, 15 ACS, 16 ATN, 17 SQR. Freeze SYS_ROM_INFO metadata records exactly: ROMQ1 is 4 bytes `{u8 index,u8 category,u16 out_ptr}` with category 0 ALL, 1 KEYBOARD, 2 CONSOLE, 3 TAPE, 4 GRAPHICS, 5 SOUND, 6 MATH. ROMOUT1 is exactly 24 bytes: `name[16]` using 1..15 visible bytes plus NUL/zero padding, u16 address, u8 classification 1=A/2=B/3=C, u8 category, u16 contract_flags, u16 reserved=0. contract_flags bit0 MAY_ERROR_RESTART, bit1 ALTREG_SENSITIVE, bit2 DISABLES_INTERRUPTS, bit3 NONREENTRANT; all remaining bits are zero in v1. Add executable table-boundary tests and host checks that reject any renumbering or alias. For every normal buffer/record syscall, validate complete packed records and every referenced 16-bit user range before side effects. A valid normal range lies wholly in shared display 0x4000-0x5AFF or user arena 0x6000-0xDFFF; it may not wrap or overlap ROM, 0x5B00-0x5FFF, or kernel 0xE000-0xFFFF. Process-owned calls additionally validate ownership/access. Records are byte-packed little-endian and reserved bytes must be zero. Freeze REV11 §10.1A generic user-range validation exactly: compute every nonzero `(start,length)` in widened arithmetic of at least 17 bits on target (32 bits or wider in host/reference tests) as `end_exclusive = widened(start) + widened(length)` before any narrowing; require `end_exclusive > start`, `end_exclusive <= 0x10000`, and both `start` and `end_exclusive-1` to lie in one single permitted ABI region. Ordinary buffers permit only 0x4000-0x5AFF or 0x6000-0xDFFF and may never bridge the gap; process-owned calls additionally require the complete widened range inside the applicable owned allocation. When a syscall documents `count=0` as non-dereferencing, the buffer pointer need not designate a readable/writable byte but every non-buffer argument remains validated. NUL-terminated strings are scanned only inside the caller-valid region and the documented lexical maximum plus terminating NUL; failure to encounter NUL before either limit returns E_TOOLONG or E_INVAL as specified by that API.
3. **Files/artifacts created or modified:** syscall.inc; errno.inc; abi.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Host compares kernel/user constants byte-for-byte. Every frozen syscall/record constant has an existing byte-level conformance test and one generated source of truth shared by kernel/userland. The dispatcher evidence records measured size/cycle results for the table and compare/branch alternatives, proves the selected implementation follows the REV11 preference rule, and proves any table form reaches its handler through the validated indirect `JP (HL)` path only after a successful syscall-number bounds check. The ABI/table audit reports exactly 59 assigned syscall numbers and proves every other numeric value in the covered version-1 range is unassigned/reserved expansion space. It also decodes and compares the complete FPOP1 op-number table 0..17 byte-for-byte against the frozen constants, and byte-decodes ROMQ1/ROMOUT1 including every category/classification/contract-flag/reserved field. The generic range oracle also proves the exact §10.1A widened formula/inequalities, same-region rule, owned-range containment, count-zero exception, and bounded NUL scan/error behavior.
9. **Negative/failure test:** Duplicate/redefined syscall ID fails static scan. Exercise invalid syscall-number holes, every errno number, wrapped/protected user ranges, nonzero reserved bytes and clobbered IX/IY; the ABI oracle must reject every divergence and prove no side effect before validation. A test build that indexes a handler table before validating the syscall number, omits the measured table-vs-branch comparison, uses a long compare/branch chain when the measured table+`JP (HL)` form is smaller/faster, or emits an unvalidated indirect dispatch must fail the §9.1 dispatcher oracle. Injecting any additional version-1 syscall assignment or handler into a deliberate numeric gap (for example 0x09), or aliasing a gap to an existing handler, must fail the syscall-surface completeness oracle. Renumbering, aliasing, omitting, or accepting an undefined FPOP1 op value must fail the ABI-constant oracle. Any ROMQ1/ROMOUT1 size/offset/category/classification/flag/reserved-bit drift must likewise fail before SYS_ROM_INFO can publish metadata. Any 16-bit wrapped end calculation, permitted-region bridge, missing process-owned containment check, count-zero buffer dereference, skipped validation of another count-zero argument, or NUL scan beyond the caller-valid/lexical bound must fail the §10.1A oracle before side effects.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.10 - SYS_VERSION

1. **Purpose / REV11 requirement:** §§9-10.1,47
2. **Exact implementation work:** Implement SYS_VERSION as a no-argument syscall. Through the fixed 0xE000 gateway, success follows the universal ABI and returns exactly HL=0x0100 for version 1.0, Carry=0 and A=0; no selector or subfunction argument exists.
3. **Files/artifacts created or modified:** syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Call 0xE000 with A=SYS_VERSION and arbitrary caller values in HL/DE/BC; return is exactly Carry=0, A=0, HL=0x0100 while IX/IY preservation rules hold.
9. **Negative/failure test:** Add a deliberately invented selector-dependent implementation and require the ABI test to fail because SYS_VERSION has no arguments and always reports the fixed ABI version.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.11 - SYS_GETPID

1. **Purpose / REV11 requirement:** §47
2. **Exact implementation work:** Return current PID without scheduling.
3. **Files/artifacts created or modified:** syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** PID0/PID1/synthetic task IDs exact.
9. **Negative/failure test:** Corrupt current record detected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.12 - SYS_YIELD and round-robin READY selection

1. **Purpose / REV11 requirement:** §§6.4-6.5,47
2. **Exact implementation work:** Implement SYS_YIELD with no arguments and the exact cooperative scheduler cycle: (1) enter a kernel scheduling point; (2) save the current FAST-stack context; (3) if still runnable mark it READY; (4) scan the process table beginning after the current PID position; (5) wake expired SLEEPING tasks; (6) select the next READY task; (7) if none select PID0; (8) mark the selected task RUNNING; (9) restore its saved context; (10) return into that task. Version 1 has no priority system and never preempts arbitrary user instructions.
3. **Files/artifacts created or modified:** scheduler.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** A multi-task fixture proves ordered round-robin selection, sleeper wake during the scan, exactly one RUNNING record, PID0 fallback, and byte-exact context preservation across repeated yields.
9. **Negative/failure test:** No READY peer must safely return to the same task when appropriate; introduce priority-biased selection, skip sleeper wake, allow two RUNNING records, or context-switch from an arbitrary interrupt and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.13 - SYS_TICKS and 32-bit monotonic frame tick

1. **Purpose / REV11 requirement:** §6.3, §47
2. **Exact implementation work:** Implement the canonical IM2 handler core and SYS_TICKS. On each accepted PAL/50-Hz frame interrupt perform only the bounded ISR responsibilities: increment the 32-bit frame counter modulo 2^32, mirror ROM FRAMES as owned by P1.14, advance the private wall-clock subsecond/second state when valid, set sleep-deadline wake bookkeeping, perform only the minimum direct keyboard-matrix reads needed for the Phase-0-frozen BREAK chord, and update cursor/status timing flags plus interrupt-safe scheduler-needed wake flags. Never call ROM KEYBOARD/decoder services or perform full key translation, repeat processing, line editing or console dispatch in ISR context; never arbitrarily preempt/context-switch user code. The canonical handler restores state, re-enables maskable interrupts at the documented point, and terminates with `RETI`. ISR code may not allocate memory, perform cassette I/O, execute shell/compiler logic, call non-reentrant heavy ROM routines, or context-switch arbitrary user processes. Expose `SYS_TICKS` exactly as HL -> writable u32 frame count modulo 2^32, independent of wall-clock valid/unset state; copy a coherent 32-bit snapshot without exposing a torn interrupt update.
3. **Files/artifacts created or modified:** interrupt.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Tick/FRAMES/wall-time/wake/BREAK/cursor flag responsibilities are bounded and exact; static/call-edge proof rejects forbidden ISR work; the handler returns through the documented `RETI` path with no arbitrary task switch. SYS_TICKS writes exactly four little-endian bytes and wrap 0xFFFFFFFF->0 is modulo-2^32 with no wall-clock side effect.
9. **Negative/failure test:** Injected double interrupt accounting mismatch fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.14 - ROM FRAMES and UDG boot compatibility

1. **Purpose / REV11 requirement:** §§14.8A,4.3,5.5,47
2. **Exact implementation work:** On every accepted IM2 frame, mirror the ROM three-byte FRAMES variable at 23672-23674 exactly: increment the low 16 bits and increment the high byte on low-word wrap, while maintaining the independent 32-bit ZX-UX tick counter. After the arena allocator is live and before PID1/normal ROM-wrapper use, allocate/pin the kernel-owned 256-byte COLD_PREFERRED 32-slot UDG bank, initialize it, repoint ROM UDG at 23675-23676 to that bank, and record the exact runtime pointer in `docs/rom-services.md`. Neither FRAMES nor UDG may remain accidental power-on/BASIC state.
3. **Files/artifacts created or modified:** interrupt.asm; boot init; udg-bank bootstrap; `v1/docs/rom-services.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** FRAMES vectors across low-word wrap are exact; debugger proves UDG points to the pinned 256-byte arena bank before PID1 is READY and never into kernel/IM2; allocator accounting includes the pin.
9. **Negative/failure test:** Skip a FRAMES carry, leave UDG at inherited BASIC/high-kernel address, allocate the bank after PID1, or free/move the pinned bank and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.15 - Minimal BREAK sampling

1. **Purpose / REV11 requirement:** §6.3, §21
2. **Exact implementation work:** Sample only minimal BREAK state in ISR; defer cancellation policy to safe kernel context.
3. **Files/artifacts created or modified:** interrupt.asm; keyboard.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Script BREAK transitions without task switch in ISR.
9. **Negative/failure test:** ISR calling blocking service fails static/runtime guard.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.16 - Fast shadow-register ISR path

1. **Purpose / REV11 requirement:** §§2.8,6.3,47
2. **Exact implementation work:** Implement compact alternate-bank ISR path only when no sensitive ROM window is active.
3. **Files/artifacts created or modified:** interrupt.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Primary task registers survive exact.
9. **Negative/failure test:** Synthetic primary-register corruption detected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.17 - ROM-safe ISR fallback

1. **Purpose / REV11 requirement:** §§6.3,14,47
2. **Exact implementation work:** When ROM wrapper marks alternate bank sensitive, use safe ISR path preserving synthetic ROM shadow workload.
3. **Files/artifacts created or modified:** interrupt.asm; rom_services.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Fallback is selected and all documented state survives.
9. **Negative/failure test:** Force fast path during busy flag and fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.18 - SYS_SLEEP with relative-tick wrap

1. **Purpose / REV11 requirement:** §§6.7,10.1,47
2. **Exact implementation work:** Implement SYS_SLEEP exactly as HL -> readable u32 relative tick count in 50-Hz frames. Prevalidate the four-byte input before changing state; relative count 0 succeeds immediately without blocking; values >0x7FFFFFFF return E_INVAL; positive valid counts compute a modulo-2^32 wake deadline and block cooperatively until the deadline is reached using wrap-safe comparisons.
3. **Files/artifacts created or modified:** scheduler.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Vectors for 0, 1, 0x7FFFFFFF and deadlines crossing 0xFFFFFFFF prove immediate return or wake at/after the exact relative interval without torn/wrapped comparison errors.
9. **Negative/failure test:** 0x80000000 and 0xFFFFFFFF return E_INVAL with no state change; a one-tick-early wake or implementation that treats the input as an absolute target tick must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.19 - SYS_EXIT kernel primitive

1. **Purpose / REV11 requirement:** §§6,10.1,47
2. **Exact implementation work:** Implement the Phase-1 SYS_EXIT primitive with exact input L=8-bit exit status; on successful exit the syscall does not return. Perform the Phase-1-safe stop/release transition needed by synthetic tasks while preserving the contract that PID0 never exits; full reparent/handle-close/ZOMBIE/wait semantics are completed in Phase 2.
3. **Files/artifacts created or modified:** process.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Synthetic child passes status bytes 0x00 and 0xFF, ceases execution without returning through the syscall gateway, and releases every Phase-1-owned resource exactly once.
9. **Negative/failure test:** PID0 exit, double release, or any successful SYS_EXIT path that returns to user code fails deterministically.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.20 - tty32 fallback core

1. **Purpose / REV11 requirement:** §§13.1A,13.5A,47
2. **Exact implementation work:** Implement the full 32x24 fallback/debug console using the same OS-owned cursor/scroll state as tty64. Render one 8x8 glyph per physical bitmap byte/attribute cell from the Phase-0-verified 48K ROM character bitmap for target codes 0x20-0x7F; never hand control to the BASIC 22-line upper/2-line lower screen editor. Route all output through the shared console character/control semantics and canonical Spectrum scanline helper.
3. **Files/artifacts created or modified:** tty32.asm; console.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden codes 0x20,0x7E,0x7F at row/column edges, 32x24 scroll and cursor transitions match the shared console oracle.
9. **Negative/failure test:** Any BASIC-editor handoff, 22+2-line behavior, code outside frozen repertoire, or write beyond row23/col31 fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.21 - F4X8 payload validator and pin

1. **Purpose / REV11 requirement:** §§4.3A,5.5,13.1,47
2. **Exact implementation work:** Validate the F4X8 payload byte-for-byte before PID1: offsets 0..3 magic `F4X8`; +4 version=1; +5 first_code=0x20; +6 glyph_count=96; +7 flags=0; +8..391 exactly 384 packed glyph bytes; total payload exactly 392. Each glyph is four bytes encoding eight 4-bit scan rows, high nibble earlier row and low nibble following row, with bit3 leftmost and bit0 rightmost. Pin the validated resource in a FAST_REQUIRED arena allocation before tty64/PID1; expose no physical address in the ABI.
3. **Files/artifacts created or modified:** tty64.asm; font4x8.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host decoder and target validator agree on every header byte and all 96*8 scan rows; valid 392-byte resource pins FAST and renders 0x20..0x7F exactly.
9. **Negative/failure test:** Wrong magic/version/first-code/count/flags/length, altered nibble ordering, or inability to obtain FAST_REQUIRED storage causes explicit validation/boot failure with no COLD spill.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.22 - tty64 4x8 renderer

1. **Purpose / REV11 requirement:** §§13.1-13.2,47
2. **Exact implementation work:** Implement tty64 as exactly 64x24 logical 4x8 cells over the 256x192 native bitmap: x_byte=col>>1; even columns replace high nibble bits7..4, odd columns low nibble bits3..0; for each scan row 0..7 use the canonical Spectrum scanline-address helper and preserve the neighboring nibble. Render target codes 0x20-0x7F from pinned F4X8; a UDG shown in tty/editor UI occupies two logical text columns. Spectrum attributes remain physical 8x8 cells, so each pair of adjacent tty64 columns shares one attribute byte; shell/vi default to uniform text attributes, ink/paper/bright/flash changes affect both columns of the pair, and the bitmap cursor never changes attributes.
3. **Files/artifacts created or modified:** tty64.asm; z80_primitives.asm; console.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden glyph/attribute fixtures at cols0/1/62/63 and rows0/23 prove independent nibble writes, 64*4=256 and 24*8=192 coverage, neighbor preservation, code0x7F rendering and deliberate attribute pair-sharing.
9. **Negative/failure test:** Linear-bitmap addressing, neighbor-nibble corruption, per-4-pixel fake attributes, attribute mutation by cursor, out-of-range glyph code/resource, or UDG treated as one tty64 column fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.23 - tty64 scroll

1. **Purpose / REV11 requirement:** §13.3
2. **Exact implementation work:** Scroll exactly one logical 8-pixel text row without treating the 6144-byte bitmap as linear text rows. For destination rows 0..22 and scan rows 0..7, obtain canonical source/destination scanline addresses and copy exactly 32 bitmap bytes; copy exactly 23*32 attribute bytes upward; clear the final 32 attribute bytes and final eight bitmap scanlines. Remove a visible software cursor before the move and redraw only after the full screen state is stable.
3. **Files/artifacts created or modified:** tty64.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** A 24-row labeled screen retains exactly the former rows1..23, clears row23 bitmap/attributes, preserves display guard bytes and restores the cursor only after completion.
9. **Negative/failure test:** Copying 6144 bytes linearly, moving 31/33 bytes per scanline, wrong attribute count, uncleared last row, or scrolling with cursor XOR still present fails golden hashes.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.24 - Software cursor core

1. **Purpose / REV11 requirement:** §§13.4-13.4A
2. **Exact implementation work:** Maintain tty64 cursor row0..23/col0..63 with exact shapes: off=none, underline=invert bottom 4-pixel row only, block=invert the complete 4x8 nibble cell. Render by XORing only the selected high/low nibble, preserving the neighboring character and attribute byte, so hide/show is reversible without saved background pixels. Target blink period is 25 PAL frames; IM2 only advances timing/sets cursor-due and never edits screen. Before character write, scroll, clear, terminal-mode change, OS graphics or UDG mutation, remove any visible cursor; perform the complete screen change without cooperative task switch; redraw afterward if required. Freeze defaults: shell command line underline; vi normal block; vi insert underline; vi command-line underline.
3. **Files/artifacts created or modified:** cursor.asm; console.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Rows/cols/shapes/defaults and 25-frame due flag are exact; repeated XOR hide/show returns byte-identical bitmap; every console/graphics mutation brackets cursor removal/redraw and leaves attributes/neighbor nibble unchanged.
9. **Negative/failure test:** Saved-pixel cursor, ISR bitmap write, shape/default mismatch, cursor left visible during a screen operation/task switch, or move/change while visible without first removing it fails byte-level tests.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.25 - Authoritative ULA port 0xFE shadow

1. **Purpose / REV11 requirement:** §§13.7,17,61
2. **Exact implementation work:** Own one authoritative kernel software shadow for shared ULA port-0xFE border/MIC/beeper output bits. Every update is read-modify-write on that shadow followed by the minimum required OUT; no subsystem may write an unrelated literal. Before an approved ROM routine whose 0xFE behavior derives border state from BORDCR, mirror only the kernel border bits into BORDCR while preserving every other Phase-0-documented bit inside the ROM critical section; on return reconcile/restore the authoritative shadow and issue one final OUT only when necessary. BEEPER and cassette wrappers must prove this; BORDCR never supersedes the kernel shadow.
3. **Files/artifacts created or modified:** ula_io.asm; console/sound stubs; rom_services.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.25`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Interleaved border/MIC/beeper and ROM BEEPER/cassette fixtures preserve unrelated shadow/BORDCR bits and end with hardware output equal to the authoritative kernel shadow.
9. **Negative/failure test:** Any direct literal OUT(0xFE) outside the owner, clobbered MIC/beeper/border bit, BORDCR becoming authoritative, or wrapper returning with shadow/hardware disagreement fails static/runtime tests.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.25.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.26 - Software wall-clock state

1. **Purpose / REV11 requirement:** §20.8, §47
2. **Exact implementation work:** Implement explicit valid/unset wall clock; accepted PAL frame ticks advance only when valid; missed ROM-critical interrupts are honestly missed. Represent public TIME1 as unsigned 32-bit local-session seconds since 1970-01-01 plus a 16-bit revision. Cold boot marks wall time unset while monotonic ticks remain valid. The PAL profile advances one wall second per 50 accepted IM2 frames; every successful set increments revision and resets the private subsecond accumulator.
3. **Files/artifacts created or modified:** interrupt.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.26`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Cold state unset; set/get exact; rollover/date range helpers later. Cold TIME1 is unset; tick uptime still advances; valid set establishes seconds and changes the 16-bit revision exactly once; 50 accepted PAL IM2 frames advance one second.
9. **Negative/failure test:** Pretend persistence across reset fails test.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.26.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.27 - SYS_TIME_GET/SYS_TIME_SET

1. **Purpose / REV11 requirement:** §10.1, §20.8, §47
2. **Exact implementation work:** Implement exact TIME record ABI and permissions/validation required by architecture. SYS_TIME_GET uses HL -> writable exact six-byte TIME1 `{u32 wall_seconds,u16 revision}` and returns E_AGAIN while wall time is unset. SYS_TIME_SET is deliberately different: HL points to a readable u32 wall-seconds value only, not TIME1. It validates the supported 1970..2099 range, then atomically marks wall time valid, resets the private 0..49 subsecond accumulator, and increments the u16 revision modulo 65536; revision starts at zero after cold boot so the first successful set produces revision 1. Repeating the same valid seconds value is still a successful set and increments revision again. No hidden RTC/timezone fiction is permitted.
3. **Files/artifacts created or modified:** syscall.asm; abi.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.27`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Packed record byte layout and invalid dates exact.
9. **Negative/failure test:** Out-of-range 1969/2100 rejected. Malformed/out-of-range time leaves seconds, revision and subsecond state unchanged; a deliberately repeated same-value successful set must still change revision.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.27.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.28 - Kernel stack guard/high-water instrumentation

1. **Purpose / REV11 requirement:** §35.1, §44
2. **Exact implementation work:** Implement the dedicated uncontended kernel stack contract at 0xFB00-0xFCFF. Normal syscall entry captures the process SP and switches to the kernel stack before work not deliberately executing on the process context frame; blocking/context-switch paths materialize the documented task frame on the task's FAST stack before committing saved_sp. No kernel code may use the process stack as anonymous scratch. Initialize the frozen low-water guard over 0xFB00-0xFB0F at boot and check it on every kernel-to-user return and after every ROM-wrapper return; damage is `PANIC KSTACK`. Instrument high-water depth from SP=0xFD00 and include the deepest reachable combination of syscall entry/dispatcher, nested kernel helpers, allocator/object/pipe error paths, ROM wrapper entry/exit, ROM error-recovery trampoline, the documented stack consumption of the invoked ROM routine, an IM2 interrupt at every interruptible point using whichever preservation path consumes more stack, return addresses/all temporary pushes, and debug/release differences that can increase depth. Release requires measured worst-case consumption <=448 bytes and the full >=64-byte untouched architectural margin; the guard is diagnostic and may not be counted as consumable margin. Reject any ROM service whose maximum stack use cannot be bounded by disassembly plus execution tests.
3. **Files/artifacts created or modified:** kernel.asm; errors.asm; tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.28`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every enumerated depth component is represented in the high-water oracle; release high-water <=448 bytes from SP=0xFD00, >=64 bytes remain untouched, the 0xFB00-0xFB0F guard is intact at every required boundary, and no process-stack scratch use or unbounded ROM service is accepted.
9. **Negative/failure test:** Corrupt guard and require PANIC KSTACK.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.28.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.29 - IY end-to-end correction matrix

1. **Purpose / REV11 requirement:** §41.11.1, §47
2. **Exact implementation work:** Prove boot establishes IY=0x5C3A before the first post-handoff ROM call; every syscall returns with IY=0x5C3A; context switches never make IY process-local; every enabled ROM wrapper obeys its frozen IY-relative system-variable contract; and a synthetic wrapper that temporarily changes IY restores 0x5C3A on success and every trapped error path.
3. **Files/artifacts created or modified:** interrupt.asm; syscall.asm; scheduler.asm; rom_services.asm; tests/emulator/iy_abi
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.29`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Debugger checkpoints at boot, every syscall-exit class, context switch, wrapper success and wrapper trapped-error return all show IY=0x5C3A.
9. **Negative/failure test:** One synthetic syscall/wrapper deliberately returns with wrong IY and must fail the matrix.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.29.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.30 - Alternate-register instruction-boundary correction matrix

1. **Purpose / REV11 requirement:** §41.11.2
2. **Exact implementation work:** Implement/use the generic `altreg_busy` gate and both exact REV11 ISR preservation paths. When `altreg_busy==0`, the bounded fast path may obtain scratch registers with `EX AF,AF'` then `EXX`, perform only the canonical ISR work, and restore with `EXX` then `EX AF,AF'`; no persistent kernel datum may live only in the alternate bank. When `altreg_busy!=0`, use the stack/kernel-scratch preservation path and never treat the alternate bank as disposable. Inject an interrupt at every instruction boundary of synthetic foreground EXX and EX AF,AF' sequences; safe ISR must be selected whenever alternate foreground state is live, and fast ISR remains correct otherwise. Freeze and retain the exact frame cost and maximum cycle cost of both ISR paths on the PAL/50-Hz baseline.
3. **Files/artifacts created or modified:** interrupt.asm; rom_services.asm; tests/emulator/altreg_boundary
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.30`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** No interrupt observes altreg_busy=0 while foreground shadow state is live; both ISR paths preserve their promised state, use only their permitted scratch resources, and retain exact measured frame/maximum-cycle evidence.
9. **Negative/failure test:** Deliberately clear altreg_busy one instruction early and require a deterministic failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.30.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.31 - Keyboard/IM2 BREAK correction matrix

1. **Purpose / REV11 requirement:** §§13.6,13.8,41.11.3
2. **Exact implementation work:** Freeze native direct keyboard scanning to Z80 16-bit I/O through BC: low byte 0xFE selects the ULA and upper address bits select the exact Phase-0-frozen keyboard rows/polarity; never treat generic 8-bit port addressing as equivalent. Freeze the raw-matrix BREAK chord and recognize only that minimum state in IM2 without any call edge to ROM KEYBOARD/decoder routines; reject non-BREAK combinations. Outside interrupt context decode printable Spectrum characters, ENTER, DELETE/backspace and mapped cursor-editing keys; command history remains deferred. A waiting console read blocks cooperatively rather than busy-spinning. IM2 only sets break_pending; safe-boundary PID1/live-tty-owner cancellation is closed by P6.26.
3. **Files/artifacts created or modified:** interrupt.asm; keyboard.asm; tests/emulator/break_im2
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.31`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact BC row-select vectors and polarity produce the frozen key matrix; BREAK combinations set break_pending while negative combinations do not; static call graph contains no ISR-to-ROM keyboard/decoder edge; ordinary owner tty input decodes the required key set and blocked reads yield.
9. **Negative/failure test:** Use an 8-bit-only port assumption, wrong row mask/polarity, synthetic ISR call to ROM KEYBOARD, non-BREAK false positive, busy-spin waiting input or command-history behavior and require deterministic failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.31.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.32 - Cursor/direct-screen reversibility correction matrix

1. **Purpose / REV11 requirement:** §41.11.4
2. **Exact implementation work:** Execute the exact six-part sequence: draw tty64 text and show XOR cursor; turn cursor OFF; directly write both high- and low-nibble bitmap cells at the former cursor; restore cursor; blink/hide/show repeatedly; then prove hidden raw bitmap is byte-for-byte the direct-write content.
3. **Files/artifacts created or modified:** cursor.asm; tty64.asm; tests/emulator/cursor_direct_screen
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.32`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every cursor transition is XOR-reversible and never restores stale saved pixels over later direct screen writes.
9. **Negative/failure test:** Use a stale-pixel restore implementation in a negative fixture and require byte mismatch.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.32.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.33 - Kernel-stack Revision-10 correction matrix

1. **Purpose / REV11 requirement:** §41.11.5, §35.1, §44
2. **Exact implementation work:** Apply high-water instrumentation to every kernel/ROM/ISR stress path; verify production-linked maximum <=448 bytes and FB00-FB0F guard intact; deliberate guard corruption must PANIC KSTACK.
3. **Files/artifacts created or modified:** kernel.asm; errors.asm; tests/emulator/kernel_stack
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.33`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All stress paths retain >=64-byte margin and the frozen guard; deliberate corruption reaches PANIC KSTACK.
9. **Negative/failure test:** A test build that exceeds 448 bytes or damages guard blocks Phase 1.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.33.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.34 - SYS_CON_GETKEY exact ABI

1. **Purpose / REV11 requirement:** §10.1, §13, §47
2. **Exact implementation work:** Implement `SYS_CON_GETKEY` exactly: no arguments; obey the tty-input-owner rule; on success return H=0,L=target byte. Keyboard decoding remains outside IM2 and uses the frozen tty key repertoire.
3. **Files/artifacts created or modified:** `v1/src/kernel/console.asm`; `v1/src/kernel/syscall.asm`; console ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.34`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Owner receives exact target byte in L with H=0; non-owner cannot steal input; IY returns 0x5C3A.
9. **Negative/failure test:** Allow a background/non-owner read or return a stale/nonzero H and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.34.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.35 - SYS_CON_PUTCHAR exact ABI

1. **Purpose / REV11 requirement:** §10.1, §13, §47
2. **Exact implementation work:** Implement `SYS_CON_PUTCHAR` exactly with H=0,L=byte. Route through the selected tty32/tty64 renderer and cursor discipline without changing the public register contract.  Apply the exact Section-13.5A byte semantics in both tty32 and tty64: printable bytes draw then advance; past final column wraps to column 0 of next row; beyond row 23 scrolls exactly one text row; LF 0x0A -> column 0 next row; CR 0x0D -> column 0 same row; BS 0x08 decrements only when col>0 and never deletes/wraps; TAB 0x09 advances to next logical multiple-of-8 column with ordinary wrap/scroll; FF 0x0C clears the text display and homes the cursor. Before character output, scroll, clear, or mode change remove a visible software cursor, perform the complete screen mutation without a cooperative task switch, then redraw it if required. Target byte 0x7F is the copyright glyph; 0x20..0x7E keep their printable ASCII-like values.
3. **Files/artifacts created or modified:** `v1/src/kernel/console.asm`; `v1/src/kernel/syscall.asm`; console ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.35`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Input byte is rendered with exact tty semantics; no adjacent bitmap/attribute corruption; IY canonical on return.  Run the same control-byte golden corpus in tty32 and tty64 at interior/right-edge/bottom-row positions; verify exact row/column, one-row scroll, bitmap/attribute bytes, neighbor nibble preservation, and reversible cursor state.
9. **Negative/failure test:** Set H nonzero or write beyond column/row bounds in a negative fixture and require deterministic rejection/test failure.  A BS at column 0 that wraps, TAB using physical rather than logical columns, LF that preserves the old column, double-scroll, ISR-side bitmap cursor edit, or output while a cursor remains XORed into the cell fails byte-level display/cursor assertions.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.35.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.36 - SYS_CON_WRITE exact ABI

1. **Purpose / REV11 requirement:** §10.1, §13, §47
2. **Exact implementation work:** Implement `SYS_CON_WRITE` exactly: HL=validated readable buffer, BC=count; return HL=bytes written. Validate widened range before any byte access; count zero performs no buffer dereference.
3. **Files/artifacts created or modified:** `v1/src/kernel/console.asm`; `v1/src/kernel/syscall.asm`; console ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.36`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact byte count is returned; valid 7FF0+0020 cross-boundary buffer works when otherwise legal; invalid/wrapped/protected ranges fail before screen mutation.
9. **Negative/failure test:** Use 16-bit wrapped end arithmetic or dereference a count-zero poison pointer and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.36.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.37 - SYS_CON_CLEAR exact ABI

1. **Purpose / REV11 requirement:** §10.1, §13, §47
2. **Exact implementation work:** Implement no-argument `SYS_CON_CLEAR`; clear the active tty display according to the frozen console contract and reset logical cursor state without inventing a second screen model.
3. **Files/artifacts created or modified:** `v1/src/kernel/console.asm`; `v1/src/kernel/syscall.asm`; console ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.37`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Display and logical cursor are in the exact post-clear state; ULA shadow and protected workspace are unchanged.
9. **Negative/failure test:** Deliberately leave one stale bitmap/cursor byte or touch 0x5B00+ protected workspace and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.37.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.38 - SYS_CON_GETPOS exact ABI

1. **Purpose / REV11 requirement:** §10.1, §13, §47
2. **Exact implementation work:** Implement no-argument `SYS_CON_GETPOS`; return H=row,L=column for the active logical terminal, using exact 0..23 row and tty32/tty64 column domains.
3. **Files/artifacts created or modified:** `v1/src/kernel/console.asm`; `v1/src/kernel/syscall.asm`; console ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.38`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** H/L exactly match logical row/column and the call is side-effect free.
9. **Negative/failure test:** Return swapped row/column, out-of-range position, or mutate cursor/display and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.38.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.39 - SYS_CON_SETPOS exact ABI

1. **Purpose / REV11 requirement:** §10.1, §13, §47
2. **Exact implementation work:** Implement `SYS_CON_SETPOS` exactly with H=row,L=column; validate mode-specific bounds before changing logical cursor or bitmap cursor state.
3. **Files/artifacts created or modified:** `v1/src/kernel/console.asm`; `v1/src/kernel/syscall.asm`; console ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.39`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Valid coordinates become current position; invalid coordinates fail atomically with prior cursor/display state byte-identical.
9. **Negative/failure test:** Use row=24 or column=32/64 as appropriate and require no state mutation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.39.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.40 - Canonical Z80 memory/string primitives

1. **Purpose / REV11 requirement:** §§27.2,47
2. **Exact implementation work:** Create and freeze one canonical kernel/runtime memory/string primitive module in `v1/src/kernel/z80_primitives.asm`. It owns the tuned copy/move/search implementations used by the kernel and runtime and must directly consider all documented Z80 block families `LDI`/`LDIR`, `LDD`/`LDDR`, `CPI`/`CPIR`, and `CPD`/`CPDR`. Cover loader copies, RAM-object copies, pipe chunk copies, UDG-set copies, editor gap movement, C48 `memcpy`/`memmove`/`memchr`, selected `strlen`/delimiter scans, and compiler lexical byte searches. Memmove-like overlap selects the correct forward/backward direction, including LDIR-versus-LDDR where that implementation is chosen. Small fixed-size transfers may use measured unrolled ordinary loads only when retained byte/cycle evidence shows them smaller or faster. Kernel/runtime consumers must use the canonical source/contract rather than grow independent tuned byte-loop implementations. Repeated block instructions are interruptible between iterations, so no kernel invariant may treat LDIR/LDDR/CPIR/CPDR as indivisible.
3. **Files/artifacts created or modified:** `v1/src/kernel/z80_primitives.asm`; primitive consumer/static-ownership tests; `v1/docs/test-plan.md`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.40`.
5. **Host-side static checks:** Prove one canonical primitive owner; enumerate every §27.2 consumer class; flag duplicate tuned copy/search loops for mandatory review; retain byte/cycle evidence for every small fixed-size exception; verify only documented Z80 instructions are used.
6. **Emulator test artifact:** Generate/run deterministic SNA fixtures covering forward copy, backward/overlapping move, forward/reverse search, boundary lengths, every canonical consumer class that is live by Phase 1, and interrupt/restart behavior.
7. **Exact FUSE assertions/checkpoints:** Compare source/destination/search results and guard bytes before/after each primitive; inject accepted IM2 interrupts between repeated block-instruction iterations and prove exact restart/completion with scheduler/kernel invariants intact.
8. **Expected PASS result:** Golden copy/move/search vectors are byte-exact; overlap direction is correct; every Phase-1-live §27.2 consumer resolves to the canonical owner; measured small-copy exceptions carry evidence; interrupted repeated operations complete exactly with no corruption or false indivisibility assumption.
9. **Negative/failure test:** Deliberately select the wrong overlap direction, duplicate an independently tuned covered byte-loop consumer, omit a required block-family consideration, remove a small-copy measurement, or inject an interrupt into a fixture that assumes a repeated instruction is indivisible; each must fail deterministically.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.40.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P1.41 - Phase-1 acceptance gate

1. **Purpose / REV11 requirement:** §47 acceptance
2. **Exact implementation work:** Run fixed-map, reserves, IM2 256-vector, both ISR paths, yield, sleep-wrap, IY, tty, the complete P1.40 canonical memory/string primitive ownership/copy/move/search/overlap/measurement/interruption-restart suite, all §41.11.1-.5 Phase-1 correction matrices, and stack-budget regression; retain binary/map/hashes.
3. **Files/artifacts created or modified:** Phase1 evidence manifest
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P1.41`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every Phase1 acceptance condition PASS, including the complete P1.40 canonical primitive suite; worktree check-in-ready.
9. **Negative/failure test:** Any reserve consumption, IY drift, unsafe alternate-register window, BREAK/ISR call-edge defect, cursor stale-pixel defect, canonical memory/string primitive ownership/overlap/measurement/interruption-restart defect, or stack defect keeps gate red.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P1.41.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 2 - Processes and Loader

## P2.01 - MEX1 exact header constants

1. **Purpose / REV11 requirement:** §§8,41.11.6,48
2. **Exact implementation work:** Freeze 24-byte MEX1 header fields, flags, offsets, CRCs and exact validation arithmetic; all count multiplications and offset/length additions are widened before narrowing and include adversarial 16-bit-wrap vectors from §41.11.6. The stored MEX1 stream is exactly 24-byte header + image bytes + ABS16 relocation-offset table, with no trailing bytes. Header offsets are: +0 `MEX1` magic[4], +4 version u8=1, +5 flags u8=0, +6 header_size u16=24, +8 image_size u16, +10 bss_size u16, +12 entry_offset u16, +14 minimum_FAST_stack_size u16, +16 relocation_count u16, +18 relocation_table_offset u16, +20 CRC-16/CCITT-FALSE of every stored byte after the header, +22 CRC-16/CCITT-FALSE of the complete 24-byte header with bytes 22..23 zero. Every multibyte field is unsigned little-endian.
3. **Files/artifacts created or modified:** mex1.inc; mex1.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Host inspector accepts goldens and rejects malformed size/offset/CRC/trailing data. Prove image offset=24, relocation_table_offset=24+image_size, relocation bytes=relocation_count*2, total stored length=relocation_table_offset+relocation_count*2, header/body CRCs exact, no trailing data, flags/version/header size exact, image_size>=1, entry_offset<image_size, image_size+bss_size<=32768 and stack 64..4096.
9. **Negative/failure test:** relocation_count>0 with image_size<2 => E_FORMAT.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.02 - Host MEX1 inspector

1. **Purpose / REV11 requirement:** §48
2. **Exact implementation work:** Implement deterministic independent format inspector; never trust target loader output as its own oracle.
3. **Files/artifacts created or modified:** tools-host/inspect-mex/
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Golden/malformed corpus exact.
9. **Negative/failure test:** One-bit header CRC mutation rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.03 - ABS16 relocation validator

1. **Purpose / REV11 requirement:** §8.1
2. **Exact implementation work:** Validate sorted non-overlapping relocation offsets, widened arithmetic and allowed image range before writes. For every ABS16 entry, prove `relocation_count==0 or image_size>=2`, `offset<=image_size-2`, `stored_word<=image_size+bss_size`, widened `relocated_value=stored_word+actual_image_base<=0xFFFF`; offsets are little-endian, sorted strictly non-overlapping with each after the first >=previous+2. Duplicate, overlapping, unsorted, out-of-image or overflowing entries are E_FORMAT. Fixed ROM/syscall addresses are absolute and never appear in the runtime relocation table.
3. **Files/artifacts created or modified:** process.asm; loader tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden list relocates at two bases.
9. **Negative/failure test:** unsorted/overlap/end-overrun rejected atomically. Include widened adversarial vectors for 24+image_size, relocation_count*2, relocation_table_offset+table bytes, image_size+bss_size, actual_base+allocation size and stored_word+actual_base; low-16-bit wrap may never make an invalid MEX1 valid.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.04 - Relocatable image load

1. **Purpose / REV11 requirement:** §7, §48
2. **Exact implementation work:** Allocate image+BSS with ANY, decode/copy, zero BSS, relocate in uncommitted allocation.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Same executable at two bases runs same result.
9. **Negative/failure test:** Allocation/relocation failure leaves no live allocation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.05 - FAST process-stack allocation

1. **Purpose / REV11 requirement:** §§4.4,8.2,48
2. **Exact implementation work:** Allocate requested/default stack FAST_REQUIRED, 2-byte/even, min64 max4096; reserve extra 64-byte bootstrap overhead outside advertised minimum.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Stack always 8000-DFFF; bounds exact.
9. **Negative/failure test:** FAST exhaustion => E_NOMEM, no COLD spill.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.06 - ARG1 builder/validator

1. **Purpose / REV11 requirement:** §8.4
2. **Exact implementation work:** Create separate process-lifetime ARG1 <=256, argc1..16, argv0 exact token; validate offsets/counts before READY. ARG1 is exact: +0 magic bytes `ARG1`, +4 argc u8 in 1..16, +5 reserved u8=0, +6 total_block_length u16 little-endian, +8 exactly argc NUL-terminated argument strings. Complete block <=256 bytes; argv[0] is the exact invocation token; no argument contains NUL. The loader validates count/string termination/total length before READY. `crt0` builds argc+1 pointers on the FAST stack, appends NULL, and supports only `int main(void)` or `int main(int argc,char **argv)`.
3. **Files/artifacts created or modified:** process.asm; abi.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary blocks accepted; malformed rejected.
9. **Negative/failure test:** Bad argc/offset/NUL/total rejected pre-side-effect.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.07 - ENV1 builder/validator

1. **Purpose / REV11 requirement:** §8.5
2. **Exact implementation work:** Create separate process-lifetime ENV1 <=256, 0..8 entries, lexical/name/value limits, case exact. ENV1 is exact: +0 magic bytes `ENV1`, +4 entry_count u8 0..8, +5 reserved u8=0, +6 total_block_length u16 little-endian, +8 exactly count NUL-terminated `NAME=VALUE` strings. Complete block <=256 bytes; names are 1..15 bytes matching `[A-Za-z_][A-Za-z0-9_]{0,14}`, case-sensitive and unique; values are 0..63 target-printable bytes 0x20..0x7E; empty value is valid; NUL is forbidden in fields and `=` is forbidden only in a name.
3. **Files/artifacts created or modified:** process.asm; abi.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary ENV1 accepted; deep stack cannot overwrite. ARG1+ENV1 live in one separate process-owned immutable bootstrap allocation (at most 512 payload bytes plus alignment), never in the downward runtime stack; both survive until exit/exec, getenv retains the ENV1 pointer, and cwd remains kernel-descriptor state rather than ENV1 data.
9. **Negative/failure test:** 9th entry/overlength/bad byte rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.08 - Initial user context constructor

1. **Purpose / REV11 requirement:** §§6.4,8.2-8.3
2. **Exact implementation work:** Build stack-resident resume frame with entry PC, canonical IY, HL ARG1, BC ARG1 size, DE ENV1 ptr as specified. Initial entry contract is exact: HL=validated ARG1 pointer, BC=exact ARG1 total length, DE=validated ENV1 pointer, A=0, SP in the separately allocated FAST_REQUIRED stack. The stack allocation is minimum_stack_size + fixed 64 bootstrap bytes for scheduler/context frame, max 17-entry argv pointer vector and crt0 scratch; advertised minimum stack excludes those 64 bytes. IY=0x5C3A and alternate registers are undefined/OS-private.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** First dispatch enters MEX1 with exact register contract. A plain return from the C48 entry path is redirected by crt0 to SYS_EXIT; it can never return into loader state. Image+BSS is ANY across the full contiguous arena, process stack is FAST_REQUIRED, and initial context is constructed only after all required allocations, image validation/relocation and BSS zeroing succeed.
9. **Negative/failure test:** IY not 5C3A fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.09 - SYS_SPAWN preflight PID capacity

1. **Purpose / REV11 requirement:** §6, §41.2A
2. **Exact implementation work:** Check full PID table before tape search/allocation; return E_AGAIN with zero side effects. SYS_SPAWN consumes HL -> exact 16-byte PROC1: +0 path_ptr u16, +2 arg1_ptr u16, +4 arg1_len u16, +6 env1_ptr u16, +8 env1_len u16, +10 stdin_handle u8, +11 stdout_handle u8, +12 stderr_handle u8, +13 flags u8 where only bit0 ALLOW_TAPE exists, +14 reserved u16=0. Validate the full record and all pointed ranges before any tape movement/allocation. If PID2..7 has no FREE slot, return E_AGAIN first. ALLOW_TAPE=0 is RAM-only and a catalog-only executable returns E_AGAIN without tape motion.
3. **Files/artifacts created or modified:** process.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Full table returns E_AGAIN and tape position/memory unchanged.
9. **Negative/failure test:** Move check after allocation => negative fixture catches side effect.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.10 - SYS_SPAWN atomic transaction

1. **Purpose / REV11 requirement:** §6-7, §48
2. **Exact implementation work:** Preflight type/BIN, allocate all owned pieces, validate image, context/cwd/handles, then publish READY once. Spawn success does not yield. Complete SYS_SPAWN exact handle/type/result semantics: parent stdin/stdout/stderr handles must each be 0..7 and valid; child receives references to the same open descriptions as handles 0,1,2 while 3..7 begin free; parent handle table is unchanged; child inherits the parent current-directory ID exactly; success returns child PID in HL. Absent target E_NOENT, resolved non-BIN/malformed MEX1 E_FORMAT, insufficient arena E_NOMEM. ALLOW_TAPE=1 authorizes only the Section-19.4A direct sequential path; caller, never kernel, obtains consent/repositioning first.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Injected failure at each stage rolls back all resources.
9. **Negative/failure test:** Direct spawn non-BIN => E_FORMAT.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.11 - Open-handle inheritance scaffold for spawn

1. **Purpose / REV11 requirement:** §6, §11
2. **Exact implementation work:** Share inherited open descriptions/refcounts, not copy independent offsets; final semantics close in Phase3.
3. **Files/artifacts created or modified:** process.asm; handles scaffold
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Fixture inherited std handles refer same descriptions.
9. **Negative/failure test:** Refcount overflow/allocation failure rolls back spawn.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.12 - SYS_EXEC atomic replacement

1. **Purpose / REV11 requirement:** §6-7
2. **Exact implementation work:** Build replacement privately; commit process image/BSS/stack/ARG/ENV while preserving PID,parent,handles,cwd/pipeline identity. SYS_EXEC also consumes PROC1, but its stdin/stdout/stderr bytes must all be 0xFF. It preserves the current PID, complete 0..7 handle table and cwd, honors the same ALLOW_TAPE rule, validates ARG1/ENV1 before releasing the old image, and does not return on success.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Success swaps image; injected failure resumes old image byte-identically.
9. **Negative/failure test:** Wrong-type image leaves old process intact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.13 - Parent/child links

1. **Purpose / REV11 requirement:** §6
2. **Exact implementation work:** Track parent PID and bounded children for wait/reparent behavior.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Spawn tree exact across PID reuse.
9. **Negative/failure test:** Stale PID generation/wait state cannot alias reused record.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.14 - ZOMBIE transition

1. **Purpose / REV11 requirement:** §6
2. **Exact implementation work:** On exit close/release owned resources, keep exit status and descriptor as ZOMBIE until wait.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Child exit wakes waiting parent; memory freed except descriptor.
9. **Negative/failure test:** Zombie must never be scheduled.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.15 - SYS_WAIT specific child

1. **Purpose / REV11 requirement:** §6
2. **Exact implementation work:** Wait pid blocks or reaps exact child; return status and release descriptor. SYS_WAIT consumes HL -> exact WAIT1 `{i16 pid,u16 status_ptr}`; pid=-1 means any child. It blocks as required, writes exactly one status byte to a prevalidated destination, returns the reaped child PID in HL, and returns E_CHILD without blocking for a specific nonexistent/nonchild PID.
3. **Files/artifacts created or modified:** process.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Running->WAIT_CHILD->READY->reap exact.
9. **Negative/failure test:** Non-child PID rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.16 - SYS_WAIT any child

1. **Purpose / REV11 requirement:** §6
2. **Exact implementation work:** Implement wait -1 semantics and no-child error. For WAIT1 pid=-1, return E_CHILD without blocking when the process has no current child; otherwise reap exactly one matching zombie and free its descriptor only after the status/result contract is satisfied.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Two children exit order handled deterministically by documented scan rule.
9. **Negative/failure test:** No child => documented errno.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.17 - Child reparenting to PID1

1. **Purpose / REV11 requirement:** §6
2. **Exact implementation work:** Exit reparents live children to PID1; PID1 special shutdown rules remain protected.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Tree fixture parent exit then child exit/reap by PID1.
9. **Negative/failure test:** Reparent to FREE PID rejected by invariants.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.18 - SYS_KILL never-started child

1. **Purpose / REV11 requirement:** §21, §41.2
2. **Exact implementation work:** Allowed kill makes spawned-never-started child ZOMBIE/status130 without running user PC and releases resources. SYS_KILL register contract is H=0,L=target PID. PID0 and PID1 are protected invalid targets. PID1 may cancel any live PID2..7; another process may cancel only its own direct child, otherwise E_PERM. Nonexistent/ZOMBIE target returns E_NOENT.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** PC sentinel never executes; status130 observed.
9. **Negative/failure test:** Unauthorized/PID0/PID1 kill rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.19 - SYS_KILL blocked started child

1. **Purpose / REV11 requirement:** §21, §41.2
2. **Exact implementation work:** Set cancellation pending; wake blocked child to observe E_INTR at safe kernel boundary.
3. **Files/artifacts created or modified:** process.asm; scheduler.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Blocked read/sleep fixture wakes E_INTR/status policy exact.
9. **Negative/failure test:** No arbitrary instruction preemption occurs.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.20 - Process-name exact-case field

1. **Purpose / REV11 requirement:** §6, §41.2
2. **Exact implementation work:** Preserve full legal 1..10 byte executable name, exact case, in process record and PROC_INFO.
3. **Files/artifacts created or modified:** process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** 10-char name prints byte-exact.
9. **Negative/failure test:** 11-char creation rejected upstream.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.21 - SYS_PROC_INFO/PROC1 exact ABI

1. **Purpose / REV11 requirement:** §§6.1,10.1
2. **Exact implementation work:** Implement the packed process-info/query ABI exactly. SYS_PROC_INFO.flags exposes only bit0 CANCEL_PENDING in version 1; bits1..7 are returned zero regardless of kernel-private descriptor flags such as STARTED. Preserve the architecture-defined PROC1 ALLOW_TAPE control contract and all packed-field/reserved-byte rules. SYS_PROC_INFO consumes HL -> exact four-byte PINFOQ1 `{u8 pid,u8 reserved=0,u16 out_ptr}` and writes exact 16-byte output `{pid,parent,state,flags,name[10],owned_bytes(u16)}`. owned_bytes is current image+BSS + FAST stack + immutable ARG1/ENV1 bootstrap allocations. FREE/nonexistent PID returns E_NOENT; PID0 reports parent=0xFF.
3. **Files/artifacts created or modified:** syscall.asm; process.asm; abi.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host decodes exact bytes against target memory; CANCEL_PENDING round-trips as bit0; STARTED/private flags never appear; bits1..7 are zero; PROC1 ALLOW_TAPE behavior matches the frozen ABI.
9. **Negative/failure test:** Set a private STARTED/other kernel flag and require SYS_PROC_INFO.flags to remain zero except CANCEL_PENDING bit0; any leaked private/reserved bit fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.22 - Repeated spawn/exit leak test

1. **Purpose / REV11 requirement:** §41.2-41.3, §48
2. **Exact implementation work:** Stress all 8 slots repeatedly and compare allocator/open counts to baseline.
3. **Files/artifacts created or modified:** tests/multiprocessing/
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Hundreds of cycles end at byte-identical accounting.
9. **Negative/failure test:** Inject one skipped free; leak detector fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.23 - Two-base relocatable execution gate

1. **Purpose / REV11 requirement:** §48 acceptance
2. **Exact implementation work:** Run the same MEX1 at distinct allocator bases through real spawn path.
3. **Files/artifacts created or modified:** tests/multiprocessing/
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Observable output and relocated words exact at both bases.
9. **Negative/failure test:** Fixed absolute arena reference fixture fails relocation correctness.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P2.24 - Phase-2 acceptance gate

1. **Purpose / REV11 requirement:** §48 acceptance
2. **Exact implementation work:** Aggregate MEX1 inspector, relocation atomicity, spawn/exec/wait/zombie, context/IY/alt-reg and leak evidence.
3. **Files/artifacts created or modified:** Phase2 evidence manifest
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P2.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All Phase2 bullets PASS.
9. **Negative/failure test:** Any failed rollback blocks check-in.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P2.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 3 - Generic I/O and Pipes

## P3.01 - Open-description table and planning budget

1. **Purpose / REV11 requirement:** §§6.3,11.1,49
2. **Exact implementation work:** Implement exactly 24 system-wide open-description records. Each opened-stream instance owns kind/access flags, reference count, shared logical offset, RAM-object slot or pseudo-device or pipe-endpoint identity, and an optional PACKED-reader decoder-state pointer. SYS_DUP and inherited spawn handles add references to the same description and consume no new description; independent SYS_OPEN calls create independent descriptions with independent offsets/decoder states. Final-reference destruction/freeing is closed in P3.05. Freeze each record at <=12 bytes and the complete table at <=288 bytes. Together with the <=448-byte eight-process descriptor table and scheduler/global state, keep the fixed scheduler/process/open-description planning region within 896 bytes.
3. **Files/artifacts created or modified:** `v1/src/kernel/handles.asm`; `v1/src/kernel/process.asm`; `v1/include/zx48ux.inc`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host layout/budget check plus SNA allocation fixture prove all architecture-owned fields/state, 24 records, <=12 bytes each, <=288 total, independent-vs-shared description ownership and combined fixed planning total <=896; 24 allocate and the 25th returns E_NOSPC with complete rollback.
9. **Negative/failure test:** A missing architecture-owned field/state, 13-byte description, >288-byte table, >896-byte combined planning total, refcount overflow, corrupt type, accidental new description on dup/inheritance, or partially visible 25th allocation must fail deterministically.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.02 - Eight-handle process table

1. **Purpose / REV11 requirement:** §11.1
2. **Exact implementation work:** Implement exactly eight process handle slots numbered 0..7. Slots 0,1,2 carry the stdin/stdout/stderr convention. Each slot contains exactly one open-description ID 0..23 or 0xFF for free; offsets/decoder state never live in the process slot. Install/remove/reference changes are atomic.
3. **Files/artifacts created or modified:** handles.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All eight slots encode only 0..23 or 0xFF; 0/1/2 standard-handle topology is exact; a ninth requested slot returns E_NOSPC without mutation.
9. **Negative/failure test:** Store an offset/decoder in a process slot, accept an ID >23 other than 0xFF, or leak a description reference on failed install and require deterministic failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.03 - /dev/tty description

1. **Purpose / REV11 requirement:** §§11,13,32
2. **Exact implementation work:** Bind console read/write/ioctl through generic handle layer.
3. **Files/artifacts created or modified:** handles.asm; console.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** READ/WRITE through handles equal direct console contract.
9. **Negative/failure test:** Wrong direction/invalid handle errno exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.04 - /dev/null description

1. **Purpose / REV11 requirement:** §32
2. **Exact implementation work:** Writes discard; reads immediate EOF; seek/open semantics exact.
3. **Files/artifacts created or modified:** handles.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Read returns HL=0; writes full count.
9. **Negative/failure test:** Invalid ioctl rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.05 - SYS_CLOSE final-reference semantics

1. **Purpose / REV11 requirement:** §11
2. **Exact implementation work:** Drop handle ref; free ordinary description only at final ref; endpoint close rules later. SYS_CLOSE exact register contract is H=0,L=handle; validate both bytes/handle before dropping the reference. Final reference release destroys the open description, frees any packed-reader state and performs endpoint/object final-close semantics.
3. **Files/artifacts created or modified:** handles.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** dup then close one preserves other.
9. **Negative/failure test:** Double-close invalid handle.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.06 - SYS_DUP shared description

1. **Purpose / REV11 requirement:** §11.3, §49
2. **Exact implementation work:** Implement exact DUP1 `{u8 source,u8 destination}` semantics: source must name a live handle; destination=0xFF selects the lowest free slot; source equal to an explicit destination succeeds as a no-op; any other occupied explicit destination returns E_BUSY; version 1 never performs dup2-style close-and-replace. Success increments the same open-description reference count, returns the resulting handle in HL, and therefore shares logical offset and any PACKED decoder state without allocating another open description. SYS_DUP consumes HL -> exact two-byte DUP1 `{u8 source,u8 destination}`. destination=0xFF allocates the lowest free process handle; otherwise it names exact handle 0..7. Success returns resulting handle in HL and increments the existing open-description reference rather than allocating a new description.
3. **Files/artifacts created or modified:** handles.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Source=self explicit destination is no-op; 0xFF chooses lowest free; duplicate handle observes shared offset/decoder and final-close lifetime exactly.
9. **Negative/failure test:** Dead source, occupied different destination, or no free handle returns the exact error atomically and never closes/replaces an occupied destination.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.07 - Independent open offset state fixture

1. **Purpose / REV11 requirement:** §11, §49
2. **Exact implementation work:** Prove separately created descriptions have independent offsets/packed decoder states.
3. **Files/artifacts created or modified:** handles/object fixture
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Two opens seek independently.
9. **Negative/failure test:** Accidental shared offset fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.08 - SYS_PIPE atomic pipe object allocation

1. **Purpose / REV11 requirement:** §§12.1,49
2. **Exact implementation work:** Allocate one pipe object containing state, circular-buffer indices/bytes-used, waiter bookkeeping and logical read/write endpoint-open counts, plus a 256-byte FAST_REQUIRED circular buffer or exactly one 128-byte fallback. SYS_PIPE allocates one read and one write open description and installs their handles into the caller result slots only after buffer, both descriptions and both handle slots are reserved; failure is atomic E_NOMEM/E_NOSPC. Implement `SYS_PIPE` exactly: HL points to two writable u8 handle slots and success returns HL=0. Allocate the pipe object, two open descriptions/endpoints and two process handles as one transaction; any capacity/allocation/pointer failure rolls all of it back. SYS_PIPE consumes HL -> two writable u8 handle slots and returns HL=0. Both destinations and capacity for two process handles/open descriptions are validated/reserved before publishing either endpoint; rollback is atomic.
3. **Files/artifacts created or modified:** pipe.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All required pipe state is initialized; normal buffer is exactly 256 FAST bytes or the single allowed 128-byte fallback; both endpoint descriptions/handles publish together. Output slots contain the read/write handles only after full commit; no half-pipe or leaked description exists on failure.
9. **Negative/failure test:** Missing waiter/endpoint-count state, any other fallback size/count, or buffer/description/handle exhaustion that leaves a partial pipe/ref/handle fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.09 - Pipe read available-data path

1. **Purpose / REV11 requirement:** §12
2. **Exact implementation work:** Copy bounded bytes, update circular indices and wake writer as applicable.
3. **Files/artifacts created or modified:** pipe.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Wraparound vectors exact.
9. **Negative/failure test:** Overcopy guard fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.10 - Pipe empty/read blocking and EOF

1. **Purpose / REV11 requirement:** §12
2. **Exact implementation work:** Empty with writers -> WAIT_PIPE_READ; no writers -> success 0.
3. **Files/artifacts created or modified:** pipe.asm; scheduler.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Reader sleeps and wakes on write; EOF only final write endpoint close.
9. **Negative/failure test:** Premature EOF under dup fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.11 - Pipe write available-space path

1. **Purpose / REV11 requirement:** §12
2. **Exact implementation work:** Copy bounded bytes and wake reader.
3. **Files/artifacts created or modified:** pipe.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Partial writes/indices exact.
9. **Negative/failure test:** Bytes-used > capacity invariant fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.12 - Pipe full/write blocking

1. **Purpose / REV11 requirement:** §12
2. **Exact implementation work:** If zero bytes transfer and readers remain, WAIT_PIPE_WRITE and schedule.
3. **Files/artifacts created or modified:** pipe.asm; scheduler.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Writer sleeps; reader wakes writer.
9. **Negative/failure test:** Busy loop without blocking fails timing/state assertion.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.13 - Broken pipe E_PIPE

1. **Purpose / REV11 requirement:** §12
2. **Exact implementation work:** No read endpoint remains => E_PIPE; no hidden write.
3. **Files/artifacts created or modified:** pipe.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Final read close then write returns E_PIPE.
9. **Negative/failure test:** Shared duplicated read ref prevents E_PIPE until final close.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.14 - Pipe endpoint/refcount lifetime

1. **Purpose / REV11 requirement:** §§12.1-12.2
2. **Exact implementation work:** Keep logical read/write endpoint-open counts distinct from open-description reference counts. dup/spawn of the same endpoint description increments only that description refcount, not a second logical endpoint-open count; v1 exposes no separately created description for an existing endpoint. Only final-reference release closes that logical endpoint for EOF/E_PIPE. Free the pipe object only after both endpoint descriptions are finally closed and no waiter remains. Link/unlink waiter and endpoint/refcount transitions atomically with respect to the cooperative scheduler and IM2-visible wake flags.
3. **Files/artifacts created or modified:** pipe.asm; handles.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Dup/spawn refs do not alter logical endpoint-open counts; EOF/E_PIPE appears only after the applicable final endpoint-description reference; object frees only after both endpoint descriptions close and waiters are absent.
9. **Negative/failure test:** Premature endpoint close/EOF/E_PIPE under duplicate refs, exposing a second independent endpoint description, freeing with any waiter/ref, or a non-atomic wait/ref transition fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.15 - READ/WRITE pointer validation

1. **Purpose / REV11 requirement:** §§9.2,10.1,11.5
2. **Exact implementation work:** Validate the complete user range/count before transfer or side effect. For count=0, validate the handle/other arguments but succeed immediately with HL=0 and never dereference or block. Ordinary RAM/PACKED stream EOF is success HL=0, not E_EOF; console/pipe streams may return positive short counts, while errors never report uncommitted bytes. SYS_READ exact register contract is E=handle,D=0,HL=buffer,BC=count and success HL=bytes read. SYS_WRITE uses the same register layout and returns bytes written. Validate D=0, handle, full buffer range and access mode before changing offsets/data; zero count obeys exact no-op semantics, EOF/broken-pipe/short-count behavior remains contract-specific.
3. **Files/artifacts created or modified:** syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Display/full arena ranges valid as specified; ROM/compat/kernel/cross-bound invalid; count=0 leaves guard bytes untouched and returns HL=0 immediately; logical EOF reads return HL=0.
9. **Negative/failure test:** Wraparound pointer+length, invalid handle, or treating ordinary EOF as E_EOF fails; a zero-count operation that dereferences or blocks fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.16 - PROC1 ALLOW_TAPE ABI bit

1. **Purpose / REV11 requirement:** §10.1, §49
2. **Exact implementation work:** Implement exact process control used later for explicit tape-backed execution consent.
3. **Files/artifacts created or modified:** process.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Set/query allowed bit exactly.
9. **Negative/failure test:** Unknown flags rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.17 - Two-process pipe proof

1. **Purpose / REV11 requirement:** §49 acceptance
2. **Exact implementation work:** Real spawned producer/consumer through handles and blocking scheduler.
3. **Files/artifacts created or modified:** tests/multiprocessing/pipe2
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact byte stream, wake states and EOF.
9. **Negative/failure test:** Small buffer stress detects deadlock.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.18 - Three-stage pipeline fixture

1. **Purpose / REV11 requirement:** §49 acceptance
2. **Exact implementation work:** Spawn three external fixture stages and wire two true pipes; parent drops own refs and waits.
3. **Files/artifacts created or modified:** tests/multiprocessing/pipe3
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Data/result exact; EOF depends on final writer.
9. **Negative/failure test:** Retain parent writer intentionally and require timeout/deadlock detector to catch it.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.19 - Widened user-range and zero-count correction matrix

1. **Purpose / REV11 requirement:** §9, §41.11.6
2. **Exact implementation work:** Perform pointer+length calculations widened before comparison/narrowing. Reject before any read/write/allocation/relocation/namespace mutation the exact adversarial ranges DFF0+0030, FFF0+0020 and 5AF0+0020; accept 7FF0+0020 when ownership/access is otherwise valid; count-zero READ/WRITE must validate handle/arguments but never dereference the buffer. Implement the common validator exactly as REV11 §10.1A: use target arithmetic of at least 17 bits (host/reference 32 bits or wider), compute `end_exclusive = widened(start) + widened(length)` for every nonzero range before narrowing, require `end_exclusive > start`, `end_exclusive <= 0x10000`, and `start` plus `end_exclusive-1` within one single permitted region (0x4000-0x5AFF or 0x6000-0xDFFF for ordinary buffers), never bridge those regions, and for process-owned APIs require the entire widened range inside the applicable owned allocation. For documented count-zero non-dereference operations, do not dereference or require a readable/writable buffer byte, while still validating handles and all other non-buffer arguments. The same bounded helper scans NUL-terminated strings only within the caller-valid region and documented lexical maximum plus one terminating NUL, returning the API-defined E_TOOLONG/E_INVAL when NUL is absent before either bound.
3. **Files/artifacts created or modified:** syscall.asm; tests/emulator/widened_ranges
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact three negative vectors fail pre-side-effect; 7FF0+0020 succeeds; zero-count leaves pointed guard bytes untouched while invalid handle still errors. The implementation-level oracle additionally logs the widened `end_exclusive` value and proves every §10.1A inequality/same-region/ownership decision, count-zero no-dereference behavior with other-argument validation, and caller-region/lexical-bound NUL termination behavior.
9. **Negative/failure test:** Implement 16-bit wrapped end-address arithmetic in a negative fixture and require the matrix to catch it. Also inject a bridge between the two individually permitted ABI regions, a range outside the process-owned allocation, a count-zero fixture with an invalid handle plus poisoned buffer address, and unterminated strings at each region/lexical boundary; every invalid case must fail before dereference or side effect with the specified errno.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.20 - SYS_IOCTL / IOCTL1 exact ABI

1. **Purpose / REV11 requirement:** §10.1, §13.5, §49
2. **Exact implementation work:** Implement `SYS_IOCTL` exactly with HL -> packed 4-byte IOCTL1 `{u8 handle,u8 request,u16 arg_ptr}`. Validate the whole record/reserved request-specific argument range before side effects. Implement the frozen tty requests from §13.5 against `/dev/tty`; `/dev/null`, `/dev/tape`, wrong handle/type or unsupported request return the exact documented error and never move cassette. SYS_IOCTL consumes HL -> exact four-byte IOCTL1 `{u8 handle,u8 request,u16 arg_ptr}`; each request defines its exact pointed argument size. Validate handle/request/complete pointed record before action. TTY request encodings are frozen by Section 13.5; unsupported `/dev/tape` byte/control requests return E_NOTSUP without moving tape.  Freeze all seven TTY request IDs and pointed argument sizes literally: 0x01 TTY_GET_MODE -> writable u8 32|64; 0x02 TTY_SET_MODE -> readable u8 32|64; 0x03 TTY_GET_SIZE -> writable two bytes cols,rows; 0x04 TTY_SET_CURSOR_SHAPE -> readable u8 0 off/1 underline/2 block; 0x05 TTY_GET_CURSOR_SHAPE -> writable u8 same values; 0x06 TTY_GET_INPUT_OWNER -> writable u8 PID; 0x07 TTY_SET_INPUT_OWNER -> readable u8 PID 0..7. Unknown IDs return E_NOTSUP; all seven require a `/dev/tty` handle. Only PID1 may successfully set input owner; nonzero requested owner must be live; owner exit restores live PID1 or PID0.
3. **Files/artifacts created or modified:** `v1/src/kernel/syscall.asm`; `v1/src/kernel/handles.asm`; `v1/src/kernel/console.asm`; ioctl tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every request has exact pointed argument size, atomic validation and deterministic state/result; no unsupported ioctl has a hidden effect.  Execute IDs 0x01..0x07 byte-for-byte, verify pointed read/write direction/size, 32/64 mode values, 24-row size, cursor values 0/1/2, PID values and owner restoration. Unknown ID and non-tty handles have no hidden side effect.
9. **Negative/failure test:** Mutate IOCTL1 packing, use an unsupported request or invalid argument range and require pre-side-effect failure.  Swap any request number, accept an unknown ID, accept a TTY request on `/dev/null` or `/dev/tape`, let non-PID1 set tty ownership, accept dead PID ownership, or access an invalid pointed byte before full validation; each must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P3.21 - Phase-3 acceptance gate

1. **Purpose / REV11 requirement:** §49 acceptance
2. **Exact implementation work:** Run handle limits, independent/shared state, pipe block/wake/EOF/E_PIPE, bounded stress, and the exact §41.11.6 user-range/zero-count vectors.
3. **Files/artifacts created or modified:** Phase3 evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P3.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All Phase3 bullets PASS.
9. **Negative/failure test:** Any timeout or widened-range/zero-count defect blocks gate.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P3.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 4 - RAM Object Store and Fixed Unix Namespace

## P4.01 - Fixed namespace resolver

1. **Purpose / REV11 requirement:** §18
2. **Exact implementation work:** Implement exactly the fixed hierarchy `/`, `/bin`, `/dev`, `/etc`, `/home`, `/home/<user>`, `/tmp`; no mkdir/rmdir or general nested directories. Version 1 also implements no filesystem mounting, permission model, ownership bits, or inode semantics. Freeze ABI-visible directory IDs ROOT=0, BIN=1, DEV=2, ETC=3, HOME=4, USERHOME=5, TMP=6; M48O also uses SYSTEM=7, which is not a user-created directory. Resolve absolute and relative paths, `.` and `..`; collapse repeated `/`; normalized path length is at most 31 bytes excluding the terminating NUL. Empty final names where an object is required and traversal above `/` return E_INVAL, overlength returns E_TOOLONG, and unknown fixed directory components return E_NOENT before mutation. `/home` contains only the current session USERHOME mapping after login and no general child directories.
3. **Files/artifacts created or modified:** objects.asm; namespace.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact directory-ID and positive/negative normalization corpus, including root-boundary, repeated-separator and pre/post-login home cases.
9. **Negative/failure test:** Any mkdir/rmdir/general directory creation, mount operation or mount-style namespace claim, permission/ownership-bit/inode API or metadata claim, wrong compact ID, traversal above root, overlength normalization, unknown component, or mutation before full resolution is rejected by the implementation/scope oracle with the exact applicable errno or certification failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.02 - Case-sensitive base-name validation

1. **Purpose / REV11 requirement:** §18
2. **Exact implementation work:** Normal object base names are exactly 1..10 visible bytes and preserve exact case. Permit only `A-Z`, `a-z`, `0-9`, `_`, `-`, `.`. The exact base names `.` and `..` are forbidden because they are path traversal components, while other dot-prefixed names such as `.cron.lock` are legal. Namespace lookup is byte-for-byte case-sensitive with no folding.
3. **Files/artifacts created or modified:** objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** `hello.c`, `Hello.c`, and `HELLO.C` coexist; legal dot-prefixed transaction names round-trip exactly.
9. **Negative/failure test:** Reject empty, >10-byte, nonportable-character, exact `.`/`..`, or case-folded alias inputs before publication.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.03 - 20-byte mutable object record

1. **Purpose / REV11 requirement:** §18, §27.3
2. **Exact implementation work:** Implement exactly 32 mutable records with type, parent, flags, logical/physical lengths and allocation metadata. Fixed pseudo-files/devices and pinned bootstrap metadata do not consume those slots. Ordinary mutable payloads use COLD_PREFERRED allocation by default and may fall back to FAST when no suitable contended extent exists; processes, pipes, pinned resources and mutable objects share the same 32-KiB arena, so object growth reduces process/compiler capacity and vice versa.  Freeze every byte of each 20-byte mutable record: +0 name[10] exact case-sensitive base name NUL/zero padded; +10 u8 directory_id; +11 u8 type; +12 u8 flags with only bit0 PACKED public and all other bits zero; +13 u8 reserved=0; +14 u16 logical_length LE; +16 u16 storage_length LE; +18 u16 allocation_ptr LE. RAW requires storage_length==logical_length; PACKED requires storage_length<logical_length; zero-length RAW requires allocation_ptr=0/no arena bytes; every nonzero payload pointer is even-aligned inside 0x6000-0xDFFF and owns exactly storage_length rounded only to allocator two-byte alignment. Pinned bootstrap metadata is separate and consumes no mutable slot.
3. **Files/artifacts created or modified:** objects.asm; abi.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host memory-layout decoder matches exact 20 bytes and allocator accounting shows the fixed 32-slot limit plus COLD_PREFERRED-to-FAST fallback without changing correctness.  Decode all 20 offsets independently for RAW, PACKED, zero-length and ten-character non-NUL name cases; verify 32 entries total/640 bytes and allocator ownership matches storage length, not logical length.
9. **Negative/failure test:** 33rd mutable object returns the capacity error; a fixed pseudo/pinned entry consuming a mutable slot or an ordinary payload bypassing the declared placement/accounting policy fails.  Nonzero reserved byte, public flag bits other than bit0, RAW unequal lengths, PACKED non-smaller length, zero-length nonzero allocation, odd/out-of-arena pointer, or pinned metadata consuming a mutable slot must fail before publication.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.04 - Directory type-placement rules

1. **Purpose / REV11 requirement:** §18
2. **Exact implementation work:** Freeze ABI type IDs exactly: 1 TXT, 2 BIN, 3 OBJ, 4 ASM, 5 C, 6 DAT, 7 UDG, 8 GFX, 9 FNT, 10 CFG, 11 SYS, 12 DIR, 13 DEV. Freeze namespace state IDs: 0 RAM, 1 TAPE_BACKED, 2 PINNED_SYSTEM, 3 PSEUDO; public object flag bit0 is OBJ_PACKED and all other flag bits are zero. M48O payload types are only 1..11; DIR/DEV are never payload types. Enforce /bin BIN only; /etc TXT/CFG only; USERHOME/TMP ordinary types 1..10; SYSTEM only FNT/SYS through the internal bootstrap loader; ROOT/DEV/HOME accept no mutable creation and public save/load never target SYSTEM. DIR/DEV lengths are zero; BCAT-only TAPE_BACKED entries report unknown logical/list length 0xFFFF until loaded. TXT, C, ASM and CFG use LF byte 0x0A as the canonical line separator; host assets are normalized to LF and target tools never emit CRLF. Type is metadata and the kernel never guesses it from a suffix.
3. **Files/artifacts created or modified:** objects.asm; abi.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact type/state/placement matrix plus LF-only text corpus and TAPE_BACKED unknown-length reporting.
9. **Negative/failure test:** Reject wrong numeric type/state/flag, M48O DIR/DEV, illegal target/type pair, public SYSTEM target, CRLF-emitting target tool, suffix inference, or C in /bin.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.05 - SYS_OPEN typed creation

1. **Purpose / REV11 requirement:** §§10.1,11.2
2. **Exact implementation work:** Implement exact flags O_READ=0x01, O_WRITE=0x02, O_CREATE=0x04, O_TRUNC=0x08, O_APPEND=0x10, O_EXCL=0x20; reject unknown bits; require at least one of O_READ/O_WRITE; require O_WRITE for O_TRUNC/O_APPEND and O_CREATE for O_EXCL. O_TRUNC|O_APPEND is legal: first atomically commit the required empty RAW representation, then retain append semantics. HL is NUL path <=31 normalized bytes, C flags, and B creation type only when O_CREATE else 0. Missing ordinary mutable path without create is E_NOENT; absent create requires allowed persistent type 1..10 and creates empty RAW atomically. Existing+O_EXCL is E_EXIST unchanged; otherwise existing type is preserved, B may be 0 or 1..10 and other values are E_INVAL. The kernel never infers type from suffix; C48 open() defaults newly created objects to DAT while open_typed() requests an explicit type. DIR opens are E_PERM; fixed pseudo/PINNED_SYSTEM paths obey their immutable access policies and creation/truncation/append never mutates them. For fixed pseudo paths, opening a DIR is E_PERM. `/dev/tty`, `/dev/null`, and `/dev/tape` require B=0 and forbid O_CREATE/O_TRUNC/O_APPEND/O_EXCL; O_READ and/or O_WRITE are allowed. `/dev/tape` is control-only: byte SYS_READ, byte SYS_WRITE, and unsupported ioctls return E_NOTSUP and never move tape. A BCAT-only TAPE_BACKED `/bin` name returns E_AGAIN without tape motion.
3. **Files/artifacts created or modified:** objects.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Full flag/type/path matrix including O_TRUNC|O_APPEND, absent/existing creation, type preservation and pseudo/PINNED_SYSTEM rules is exact.
9. **Negative/failure test:** Unknown bits/illegal dependencies/type values, DIR mutation, retagging, suffix inference, or mutation before validation are rejected with byte-identical prior state. Attempt DIR open; creation/truncation/append/exclusive flags on each pseudo device; byte I/O/unsupported ioctl on `/dev/tape`; and byte-open of a BCAT-only command. Verify exact errno and zero tape motion/state mutation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.06 - Exclusive writer / multiple readers

1. **Purpose / REV11 requirement:** §§11.1-11.2,27.3
2. **Exact implementation work:** Permit any number of distinct read-only open descriptions for one RAM object. A write-capable open is exclusive against every other distinct open description; a read open while such a writer exists returns E_BUSY. dup/spawn references to the same existing writer description are allowed and share its offset/append state. Writer exclusivity, representation-swap E_BUSY checks and no-open-reference tests scan the bounded open-description pool, not process handle tables.
3. **Files/artifacts created or modified:** objects.asm; handles.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Independent reader-reader opens succeed; writer conflicts with every distinct reader/writer; duplicated/inherited references to the same writer remain legal and share state.
9. **Negative/failure test:** Pack/swap with any distinct live description or a read-open attempt during writer ownership returns E_BUSY; handle-table-only scans fail the test.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.07 - RAW read/seek

1. **Purpose / REV11 requirement:** §§11.4-11.6,18
2. **Exact implementation work:** For RAW RAM-object descriptions logical and physical bytes are identical. SYS_SEEK is supported only for RAM-object open descriptions and sets their shared absolute unsigned logical offset in 0..object_length inclusive; beyond EOF is E_INVAL and sparse holes are never created. Pipe, tty, null and tape-control streams return E_NOTSUP. RAW seek is direct. Reads at logical EOF succeed HL=0. Zero-length RAW uses logical_length=storage_length=0 and allocation_ptr=0; the sentinel is never dereferenced. SYS_SEEK exact register contract is E=handle,D=0,HL=absolute logical offset and success returns new offset in HL. Seek is over logical bytes, so PACKED opens reconstruct decoder state deterministically; invalid D/handle/range or unseekable endpoint fails before changing shared offset.
3. **Files/artifacts created or modified:** objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Read EOF, seek 0, seek exact EOF and zero-length RAW behavior are exact; nonzero resident payload pointers remain even-aligned in the arena.
9. **Negative/failure test:** Seek beyond EOF, seek on non-RAM streams, sparse-hole creation, or dereference of zero allocation sentinel fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.08 - Atomic RAW growth/write

1. **Purpose / REV11 requirement:** §§11.5,18,31
2. **Exact implementation work:** A valid RAW RAM-object write commits the full requested BC bytes or returns an error; extending writes never return positive short counts. An in-range write commits all BC and returns HL=BC. Before extension, widen and validate max(old_length,offset+BC)<=32768, allocate a complete private replacement, copy old bytes plus the entire requested write, then atomically swap allocation/length. Allocation or size failure returns E_NOMEM/E_NOSPC and leaves the old object byte-identical. O_APPEND uses the same transactional extension rule.
3. **Files/artifacts created or modified:** objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** In-place and extending writes return HL=BC; growth commits atomically and widened boundary vectors are exact.
9. **Negative/failure test:** Forced E_NOMEM/E_NOSPC, wrapped offset+BC, or a positive short extending write leaves the original object hash/metadata unchanged and fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.09 - O_APPEND semantics

1. **Purpose / REV11 requirement:** §11, §41.3A
2. **Exact implementation work:** Every write starts at current logical EOF even after SYS_SEEK.
3. **Files/artifacts created or modified:** objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Seek then append still writes EOF.
9. **Negative/failure test:** Offset-based append bug fixture fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.10 - O_TRUNC semantics

1. **Purpose / REV11 requirement:** §11
2. **Exact implementation work:** Truncate to empty RAW atomically; O_TRUNC|O_APPEND then appends.
3. **Files/artifacts created or modified:** objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Lengths/data exact.
9. **Negative/failure test:** Failure before commit preserves old object.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.11 - SYS_STAT

1. **Purpose / REV11 requirement:** §10.1
2. **Exact implementation work:** Expose exact logical/physical/type/state metadata. SYS_STAT consumes HL -> exact STAT1 `{u16 path_ptr,u16 out_ptr}` and writes exact ten-byte STATOUT1: type u8, flags u8, logical_length u16, storage_length u16, directory_id u8, state u8, reserved u16=0. RAM logical_length is always the logical uncompressed length; RAW storage_length=logical_length and PACKED storage_length is the smaller physical ZXP1 byte count. Nonresident TAPE_BACKED catalog entries report logical_length=0xFFFF and storage_length=0xFFFF; PSEUDO DIR/DEV report both lengths zero.
3. **Files/artifacts created or modified:** objects.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** RAW/PACKED expected records.
9. **Negative/failure test:** Reserved bytes nonzero fails ABI test.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.12 - SYS_LIST and BCAT union

1. **Purpose / REV11 requirement:** §18, §4.3B
2. **Exact implementation work:** List fixed dirs; /bin union resident BIN + pinned BCAT with resident exact-name precedence and <=255 visibility. Sort SYS_LIST in unsigned-bytewise case-sensitive order. Enforce BCAT entry_count<=223 so the visible `/bin` union cannot exceed 255 entries; resident exact-name BIN wins over matching BCAT metadata. SYS_LIST consumes HL -> exact LIST1 `{u16 directory_path_ptr,u8 zero_based_index,u8 reserved=0,u16 out_ptr}` and writes exact 16-byte LISTOUT1 `{name[10],type,flags,length(u16),state,directory_id}`. RAM entry length is the logical uncompressed length; BCAT-only TAPE_BACKED length is 0xFFFF; fixed DIR/DEV length is zero. Return HL=1 for visible indices 0..254, HL=0 at first index past final entry, and index 255 is unconditional terminator HL=0. `/bin` first forms the resident-RAM/BCAT union with exact-name resident shadowing; removing a resident shadow makes the unchanged BCAT-only TAPE_BACKED entry visible again.
3. **Files/artifacts created or modified:** objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Sorted/exact-case list and duplicate precedence. Ordering is unsigned-bytewise and case-sensitive; BCAT 223 is accepted when total visible count remains <=255 and 224 is rejected at bootstrap/validation.
9. **Negative/failure test:** BCAT duplicate/unsorted invalid at bootstrap.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.13 - SYS_REMOVE

1. **Purpose / REV11 requirement:** §18
2. **Exact implementation work:** Remove only closed mutable RAM object; protected/pseudo/catalog return E_PERM; cassette history untouched. SYS_REMOVE exact register contract is HL=NUL-terminated path. Only closed mutable RAM objects may be removed; any live open description returns E_BUSY and DIR/DEV/PINNED_SYSTEM/TAPE_BACKED/SYS metadata return E_PERM. Commit frees payload, clears zxpack candidate state and frees table entry atomically. If the removed object was a resident `/bin` BIN shadowing an exact-name BCAT entry, removal does not mutate BCAT and that catalog-only TAPE_BACKED name becomes visible again immediately.
3. **Files/artifacts created or modified:** objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Closed object removed/freed.
9. **Negative/failure test:** Open object E_BUSY.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.14 - SYS_RENAME no-op/case-only

1. **Purpose / REV11 requirement:** §10.1, §18
2. **Exact implementation work:** Atomic exact-source/destination rename; same exact object no-op; case-only allowed if no distinct destination. SYS_RENAME consumes HL -> exact four-byte REN1 `{u16 old_path_ptr,u16 new_path_ptr}`. Fully resolve/validate both paths before mutation; exact-same path is no-op success, case-only rename is legal absent a distinct collision, cross-fixed-directory move requires destination type compatibility, and mutable destination replacement is atomic only when neither object has a live open description.
3. **Files/artifacts created or modified:** objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** No-op/case-only tests.
9. **Negative/failure test:** Collision rollback.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.15 - SYS_RENAME replacement/cross-dir validation

1. **Purpose / REV11 requirement:** §18
2. **Exact implementation work:** For a distinct existing mutable RAM destination, require both source and destination to have no live open description and require destination-directory compatibility with the source existing type. After all validation, replace the destination directory entry with source metadata in one commit step, then free the old destination payload and remove the old source name. DIR, DEV, PINNED_SYSTEM, TAPE_BACKED and SYS metadata cannot be source or replacement destination and return E_PERM. Rename changes bounded metadata/ownership only: it never copies, decodes, packs or recompresses payload bytes. Any pre-commit failure leaves both objects byte-identical.
3. **Files/artifacts created or modified:** objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Commit transfers the existing source payload ownership, frees the old destination only after metadata commit, removes the old source name, and performs zero payload copy/recompression.
9. **Negative/failure test:** Open source/destination returns E_BUSY; protected metadata or invalid target type returns E_PERM/E_INVAL as specified; injected pre-commit failure preserves both prior objects.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.16 - ZXP1 target decoder

1. **Purpose / REV11 requirement:** §27.3
2. **Exact implementation work:** Implement one resident bounded ZXP1 decoder state machine for the literal token grammar frozen in P0.32: 0x00..0x3F LITERAL length token+1; 0x40..0x7F RLE length (token&0x3F)+3 plus one repeated byte; 0x80..0xFF BACKREF length (token&0x7F)+3 plus distance_minus_1 giving distance1..256. BACKREF uses prior logical output with byte-at-a-time overlap semantics. The one token parser supports exactly four sinks: FINAL_MEMORY (executable/object materialization), CALLER_STREAM (SYS_READ into caller buffers), DISCARD (tape scan/verify/CRC validation), and TAPE_PIPE (internal validation while physical chunks arrive); the parser is identical for all sinks and updates logical CRC on emitted bytes when the enclosing operation requires it. Require exact physical-input exhaustion and exact declared logical-output completion; there is no terminator token. For every physical-input cursor, token-parameter read, logical-output cursor, back-reference source, sink address, declared physical/logical length comparison, chunk/remaining-byte calculation, and output advance, perform widened arithmetic before narrowing to 16-bit Z80 address/count. Reject an output advance beyond declared logical length before writing the byte that would cross the boundary; a 16-bit wrap must never make malformed ZXP1 input valid.
3. **Files/artifacts created or modified:** zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every P0.32 token-boundary/overlap stream and host-optimized stream decodes identically through FINAL_MEMORY, CALLER_STREAM, DISCARD and TAPE_PIPE with one parser, exact physical/logical cursor completion, and required logical CRC behavior.
9. **Negative/failure test:** Truncated token parameters/literals, distance before logical start, logical overrun/underrun, trailing physical bytes, or any target behavior differing from the host oracle returns E_FORMAT; no partial representation commit. Add adversarial physical/logical lengths and back-reference/output additions whose low 16 bits look in-range only after wrap; each must return E_FORMAT/E_INVAL before read/write/commit, while a genuinely valid boundary-crossing stream still decodes exactly.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.17 - Per-open packed reader state

1. **Purpose / REV11 requirement:** §§11.1-11.2,27.3
2. **Exact implementation work:** Allocate exactly one 272-byte COLD_PREFERRED ZXP1 decoder state for each independent PACKED read-only open description: a 256-byte circular history plus an exact 16-byte decoder-control record. The control record stores physical source position, logical output position, history index/count, pending command kind/count, and any one-byte parameter in the kernel-private layout frozen in v1/docs/zxpack.md. dup/inherited handles referencing that same open description share that single decoder state and shared logical offset; a second independent SYS_OPEN gets a distinct 272-byte state. If the 272-byte state cannot be allocated, read-only open fails E_NOMEM without changing the object. Final reference release frees the state.
3. **Files/artifacts created or modified:** zxpack.asm; handles.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Two independent readers interleave and each matches the RAW oracle; byte-level inspection proves the 256+16 layout/control fields, dup/spawn handles of one description share decoder position/state and consume no second 272-byte allocation, and forced state-allocation failure returns E_NOMEM with the object byte-identical.
9. **Negative/failure test:** Accidentally sharing history between independent opens, allocating duplicate state for dup/inheritance, or leaking state after final close fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.18 - Packed seek restart

1. **Purpose / REV11 requirement:** §§11.4,27.3
2. **Exact implementation work:** PACKED seek operates on the shared logical offset without materializing the object. A backward seek resets the shared decoder and decodes/discards from logical offset zero; a forward seek decodes/discards from the current decoder position. It is intentionally O(n). Offsets 0..logical_length inclusive are valid; beyond logical EOF is E_INVAL.
3. **Files/artifacts created or modified:** zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Random forward/backward seek/read sequence is byte-identical to RAW oracle, including seek-to-EOF; allocation/representation remains PACKED.
9. **Negative/failure test:** Seek beyond logical EOF, forward restart from zero contrary to the contract, or any silent materialization fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.19 - PACKED write materialization

1. **Purpose / REV11 requirement:** §27.3
2. **Exact implementation work:** Before exposing writable handle, decode to private RAW replacement; O_TRUNC may create empty RAW directly; commit atomically.
3. **Files/artifacts created or modified:** objects.asm; zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Success exact; forced allocation/codec error leaves packed object untouched.
9. **Negative/failure test:** Expose writer before complete decode fails test.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.20 - Target greedy encoder workspace

1. **Purpose / REV11 requirement:** §27.3, §41.3A
2. **Exact implementation work:** Implement the exact deterministic two-pass target encoder. Each pass allocates exactly one 512-byte COLD_PREFERRED table of 256 little-endian u16 last-occurrence positions initialized to 0xFFFF. At logical position p, test only the nearest prior occurrence q of the same first byte when 1<=p-q<=256 and extend that sole BACKREF candidate to at most 130 bytes; independently extend an RLE candidate to at most 66 bytes. Ignore candidates shorter than 3; choose the longer legal candidate and choose RLE on an equal-length RLE/BACKREF tie. Update the table for every consumed input position. Accumulate unmatched bytes into LITERAL runs of at most 64 and flush the final run. Pass1 computes exact encoded length/optional logical CRC; pass2 reinitializes the table and emits exactly that stream. Explicit SYS_PACK returns E_NOMEM if the 512-byte workspace cannot be allocated; background packing silently skips that candidate. If encoded length is not strictly smaller, keep RAW. Encoder-owned allocations run under NO_COMPACT. If the one required transient 512-byte nearest-occurrence table cannot be allocated, explicit SYS_PACK returns E_NOMEM. The encoder itself runs under NO_COMPACT so its allocation cannot recursively trigger allocator compaction.
3. **Files/artifacts created or modified:** zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden ambiguous-match/tie vectors produce the exact target-greedy stream on repeated runs, decode identically with the host oracle, and measured workspace is exactly 512 bytes per pass.
9. **Negative/failure test:** Testing a non-nearest BACKREF candidate, choosing BACKREF on an equal-length RLE tie, failing to update consumed positions, emitting literal>64/match beyond limits, using >512 bytes workspace, recursive compaction, or committing non-smaller PACKED output fails deterministically. Force failure to obtain the exact 512-byte workspace and require E_NOMEM with the prior RAW representation byte-identical; a 513-byte or recursive-compaction implementation fails the budget/NO_COMPACT oracle.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.21 - Non-compressible remains RAW

1. **Purpose / REV11 requirement:** §27.3
2. **Exact implementation work:** Pack only if physical stream strictly smaller; zero-length RAW.
3. **Files/artifacts created or modified:** zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Random incompressible fixture unchanged representation.
9. **Negative/failure test:** Equal-size packed result must be rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.22 - SYS_PACK atomic

1. **Purpose / REV11 requirement:** §10.1, §27.3
2. **Exact implementation work:** SYS_PACK exact register contract is HL=NUL-terminated path. Accept only an existing mutable RAM object: DIR, DEV, TAPE_BACKED, PINNED_SYSTEM and SYSTEM metadata return E_PERM. PACKED is a no-op success with HL=0. A RAW object with any live handle returns E_BUSY. RAW objects shorter than 64 bytes are valid but remain RAW with HL=0. Dry-run the exact encoded size; if it is not smaller, return success HL=0 with RAW unchanged. Otherwise allocate the exact compressed destination, emit and self-validate it privately, then atomically swap pointer/storage length/PACKED flag and free the old RAW allocation. Return HL=physical bytes saved. Any allocation/codec/self-validation failure frees only private temporaries and leaves the committed RAW representation byte-identical.
3. **Files/artifacts created or modified:** objects.asm; zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Protected-type, PACKED-no-op, <64-byte, non-smaller, E_BUSY and successful exact-destination/self-validation/swap cases produce the exact metadata/logical bytes and HL result.
9. **Negative/failure test:** Allocation/codec failure leaves byte-identical RAW.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.23 - SYS_UNPACK atomic

1. **Purpose / REV11 requirement:** §10.1, §27.3
2. **Exact implementation work:** SYS_UNPACK exact register contract is HL=NUL-terminated path. RAW is a no-op success returning logical length. On PACKED, first reject E_BUSY if any live handle references the object; otherwise allocate a private RAW destination of exact logical length, decode and validate exact output, then atomically swap representation and free packed storage. When decoding a whole logical ZXP1 stream from offset zero directly into one contiguous final RAW destination, use already-emitted destination bytes as BACKREF history so no separate 256-byte history is required; this direct-memory optimization is forbidden when an early logical prefix was parsed into separate scratch storage. Failure frees only private temporaries and leaves the committed representation unchanged.
3. **Files/artifacts created or modified:** objects.asm; zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** RAW no-op returns logical length; PACKED->RAW identity is exact, direct-memory BACKREF history is used only for whole-stream contiguous decode, and no extra 256-byte history allocation appears in the canonical SYS_UNPACK path.
9. **Negative/failure test:** Failure leaves packed representation unchanged.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.24 - Close-time pack candidate bitset

1. **Purpose / REV11 requirement:** §18.5, §27.3
2. **Exact implementation work:** Only an eligible RAW mutable object of at least 64 logical bytes becomes an opportunistic ZXP1 candidate when the final open description referencing it is destroyed; closing a non-final reader while another reference remains must not mark it. Final close only updates the 32-bit candidate bitset and never compresses synchronously. Reopen/write/remove/slot reuse clears stale candidacy. `/tmp` uses this identical policy. Packing is never required for successful close: if no useful smaller stream or no destination allocation exists, the valid RAW object remains unchanged.
3. **Files/artifacts created or modified:** zxpack.asm; objects.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Eligibility threshold, final-reference transition, `/tmp` parity and no-synchronous-pack behavior are exact; unsuccessful opportunistic packing preserves RAW bytes.
9. **Negative/failure test:** Marking <64-byte RAW, PACKED, pinned/live/open objects; marking on a non-final close; synchronous compression during close; or a candidate bit surviving reopen/remove/slot reuse fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.25 - PID0 one-pack-per-idle policy

1. **Purpose / REV11 requirement:** §27.3
2. **Exact implementation work:** PID 0 services at most one set pack-candidate bit per idle maintenance cycle. Revalidate that the same slot still names an eligible mutable RAW object of at least 64 bytes with no open handles before allocating the 512-byte encoder workspace or changing data. Failure, no savings, or E_NOMEM clears that attempt's candidate bit and never changes the object or a previously successful close result.
3. **Files/artifacts created or modified:** scheduler.asm; zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.25`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** At most one candidate is attempted; successful work is exact, while failure/no-savings/E_NOMEM clears only that attempt bit and leaves RAW bytes/previous close success unchanged; scheduler remains responsive.
9. **Negative/failure test:** Two packs in one idle cycle fails counter assertion.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.25.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.26 - Allocation-pressure bounded compaction

1. **Purpose / REV11 requirement:** §4.4, §27.3
2. **Exact implementation work:** Before an ordinary ANY/COLD allocation returns E_NOMEM, permit at most one bounded synchronous victim scan independent of pack_candidate. Candidates are mutable RAW objects with no open handle of any kind, no pinned/system role, and no active direct-memory ownership. Deterministic victim order is largest logical RAW object first, then exact bytewise path/name order; only one victim is attempted per allocator request. Dry-run requires the exact 512-byte encoder workspace and computes exact compressed-destination size; attempt packing only when current free space can hold the required temporary workspace and exact destination at their relevant stages. Every zxpack-owned allocation (encoder workspace, packed destination, decoder state/history, tape codec scratch) carries an internal NO_COMPACT/depth guard for its lifetime; guarded allocation may fail normally but never invokes the compression-victim path, so compression cannot recurse. Version 1 never compresses live or suspended process images, BSS, heaps, stacks, pipes, screen RAM, kernel RAM, or pinned runtime resources.
3. **Files/artifacts created or modified:** memory.asm; zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.26`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Largest-logical RAW then exact bytewise path/name tie-break, one-victim limit, 512-workspace/exact-destination free-space prerequisites, exclusions, and NO_COMPACT/depth path are exact.
9. **Negative/failure test:** Any second victim attempt, recursive compaction, insufficient scratch/destination attempt, wrong tie-break, or attempt to pack an open/pinned/system/live-or-suspended process image/BSS/heap/stack/pipe/screen/kernel/pinned runtime allocation fails the guard and leaves committed state unchanged.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.26.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.27 - PACKED BIN direct resident spawn

1. **Purpose / REV11 requirement:** §7, §27.3
2. **Exact implementation work:** Decode packed MEX1 directly into final uncommitted process allocation; no second full logical copy. The continuous 272-byte decoder state/history begins at logical offset zero and remains continuous across the separately parsed 24-byte MEX1 header into image decoding; no header-splitting reset is permitted.
3. **Files/artifacts created or modified:** process.asm; zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.27`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Memory accounting proves one final image plus decoder state.
9. **Negative/failure test:** Corrupt packed executable rolls back process allocation. Use a packed MEX1 whose first post-header back-reference depends on pre-header history; resetting history at byte 24 must fail the oracle.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.27.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.28 - SYS_ZXPACK_INFO / ZPINFO1 accounting

1. **Purpose / REV11 requirement:** §10.1, §33
2. **Exact implementation work:** Implement 32-bit logical/saved totals, physical bytes, counts, decoder bytes, modulo-65536 attempt/success counters. Expose `SYS_ZXPACK_INFO` as HL -> writable exact 20-byte ZPINFO1: u32 logical_object_bytes; u16 physical_object_bytes; u32 bytes_saved; u8 packed_object_count; u8 raw_object_count; u16 packed_reader_state_bytes; u16 pack_attempts_since_boot; u16 pack_successes_since_boot; u16 reserved=0. Totals concern mutable RAM-object storage only. Compute logical_object_bytes, physical_object_bytes, and logical_length-physical_length/bytes_saved in widened arithmetic before validation/narrowing; bytes_saved cannot underflow. Event counters wrap modulo 65536 without changing current totals. SYS_ZXPACK_INFO consumes HL -> writable exact 20-byte ZPINFO1: logical_object_bytes u32, physical_object_bytes u16, bytes_saved u32, packed_object_count u8, raw_object_count u8, packed_reader_state_bytes u16, pack_attempts_since_boot u16, pack_successes_since_boot u16, reserved u16=0.
3. **Files/artifacts created or modified:** zxpack.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.28`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact record and wrap tests. Byte-level ZPINFO1 oracle covers >65535 aggregate logical bytes, counter wrap and packed-reader open/close accounting.
9. **Negative/failure test:** 16-bit truncation bug fixture fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.28.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.29 - Object-store full regression matrix

1. **Purpose / REV11 requirement:** §41.3A
2. **Exact implementation work:** Run every Section-41.3A ZXP1/open/append/candidate/pack/unpack case in canonical order.
3. **Files/artifacts created or modified:** tests/compression/
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.29`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All vectors byte-identical to host oracle.
9. **Negative/failure test:** Any missing vector keeps matrix incomplete.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.29.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.30 - Fixed pseudo-directory list/stat ABI

1. **Purpose / REV11 requirement:** §18.6, §32; invariants 108/115
2. **Exact implementation work:** Implement and freeze exact fixed enumeration/stat behavior: `SYS_LIST /` -> `bin,dev,etc,home,tmp`; `SYS_LIST /dev` -> `null,tape,tty`; `SYS_LIST /home` -> zero entries before login and exactly the current username after login. `.` and `..` are navigation syntax and never list entries. Fixed directories stat DIR/PSEUDO with zero lengths; fixed devices stat DEV/PSEUDO with zero lengths; returned directory_id is the parent and stat `/` uses ROOT as its own parent sentinel. Protected pseudo/catalog/pinned entries cannot be remove/rename targets.
3. **Files/artifacts created or modified:** `v1/src/kernel/objects.asm`; ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.30`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All three listings, types, states, zero lengths, ordering and parent IDs match REV11 byte-for-byte.
9. **Negative/failure test:** Inject one extra `.`, wrong order, nonzero length, wrong parent or mutability and require deterministic failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.30.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.31 - SYS_CHDIR exact ABI

1. **Purpose / REV11 requirement:** §10.1, §18, §50
2. **Exact implementation work:** Implement `SYS_CHDIR` exactly with HL=NUL-terminated directory path. Resolve using the fixed hierarchy, normalized <=31-byte rule, case sensitivity, `.`/`..` semantics and current-session home. Commit cwd only after full validation; non-directory/wrong-case/overlength/nonexistent paths fail atomically. SYS_CHDIR exact register contract is HL=NUL-terminated directory path; normalize/case-resolve only a fixed DIR and commit cwd only after complete validation. Non-directory/absent/overlength paths return the exact errno with cwd unchanged.
3. **Files/artifacts created or modified:** `v1/src/kernel/objects.asm`; `v1/src/kernel/syscall.asm`; path ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.31`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Successful cwd is canonical fixed-directory identity; each failure leaves previous cwd byte-identical.
9. **Negative/failure test:** Attempt chdir to BIN/TXT/DEV object, wrong case, overlength or nonexistent path and require no cwd change.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.31.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.32 - SYS_GETCWD exact ABI

1. **Purpose / REV11 requirement:** §10.1, §18, §50
2. **Exact implementation work:** Implement `SYS_GETCWD` exactly: HL=validated writable buffer, BC=capacity; write canonical NUL-terminated current path and return HL=path bytes excluding NUL. Capacity < path_len+1 returns E_NOSPC before writing any byte. SYS_GETCWD exact register contract is HL=buffer,BC=capacity. It writes the terminating NUL and returns HL=path byte count excluding NUL; capacity < path_len+1 returns E_NOSPC without partial output.
3. **Files/artifacts created or modified:** `v1/src/kernel/objects.asm`; `v1/src/kernel/syscall.asm`; path ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.32`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact canonical path+NUL and count returned on success; all insufficient/invalid ranges leave destination guards byte-identical.
9. **Negative/failure test:** Use capacity==path_len, wrapped pointer range or partial-write implementation and require failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.32.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P4.33 - Phase-4 acceptance gate

1. **Purpose / REV11 requirement:** §50 acceptance
2. **Exact implementation work:** Run 32-entry CRUD, fragmentation, rename, type, pseudo/catalog, ZXP1, direct BIN, materialization, RAW fallback and no-live-compaction gates.
3. **Files/artifacts created or modified:** Phase4 evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P4.33`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All Phase4 bullets PASS.
9. **Negative/failure test:** One failed rollback blocks phase.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P4.33.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 5 - Cassette Object Layer

## P5.01 - M48O 32-byte header constants

1. **Purpose / REV11 requirement:** §19, §51
2. **Exact implementation work:** Freeze magic/version/flags/type/target/name/physical/logical/codec/CRC fields exactly; RAW codec0, PACKED codec1 ZXP1 only.  Freeze the literal 32-byte M48O header: offset0 size4 magic `M48O`; 4 u8 version=1; 5 u8 object type; 6 u8 flags; 7 u8 target directory ID; 8 u16 physical payload/storage length LE; 10 u16 logical uncompressed length LE; 12 u16 codec ID LE (0 RAW,1 ZXP1); 14 u16 logical-payload CRC-16/CCITT-FALSE LE; 16 name[10] exact case-sensitive base name NUL padded; 26 u16 header CRC LE; 28..31 reserved zero. Header CRC is over all 32 bytes with bytes26..27 treated as zero. Names are 1..10 bytes; if an embedded NUL occurs, every following name-field byte is zero; full ten non-NUL bytes are legal. Physical/logical lengths are <=32768 and obey RAW/PACKED/zero rules. Types 1..11 only; 0, DIR=12, DEV=13 invalid. Target IDs are ROOT0,BIN1,DEV2,ETC3,HOME4,USERHOME5,TMP6,SYSTEM7 with only the Section-19.3 placement matrix legal; public save/load never target SYSTEM.  `USERHOME` is symbolic persistence metadata: at load time it resolves to the current session `/home/<user>`, so cassette objects remain portable across valid boot usernames.
3. **Files/artifacts created or modified:** tapeobj.inc; tape-object.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Independent host parser golden/malformed corpus.  Load the same USERHOME M48O object under two different valid session usernames and verify it lands under each current home with identical exact-case base name and logical bytes.  Independent parser verifies every offset, little-endian field, header-CRC zeroing rule, ten-byte-name edge, type/target placement, RAW/PACKED relationships and 32768 boundaries.
9. **Negative/failure test:** type0/DIR/DEV/unknown flags/codec rejected.  Reject embedded-NUL name garbage, nonzero reserved bytes, bad header CRC, unknown flag bits, lengths >32768, PACKED zero/equal/larger physical size, illegal target/type pairing, public SYSTEM target, and any one-byte offset/endian mutation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.02 - CRC-16/CCITT-FALSE

1. **Purpose / REV11 requirement:** §19, §51
2. **Exact implementation work:** Implement polynomial1021 initFFFF refin/refout false xorout0; freeze check vector.
3. **Files/artifacts created or modified:** tape host+target
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host/target CRC match known vectors.
9. **Negative/failure test:** One-bit payload corruption rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.03 - 512-byte ROM chunk framing

1. **Purpose / REV11 requirement:** §19, §51
2. **Exact implementation work:** After the native Spectrum bootstrap prefix, encode each M48O object as one separate fixed 32-byte header ROM data block followed by zero or more separate payload ROM data blocks. Every M48O header/chunk block uses flag byte 0xFF plus standard Sinclair ROM block-checksum framing. Payload chunk size is fixed at 512 bytes: block count is ceil(physical_length/512); every nonfinal chunk is exactly 512, final chunk is exactly the remaining 1..512, and zero physical length emits no payload blocks.
3. **Files/artifacts created or modified:** tape.asm; maketap
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Independent TAP/TZX parser proves separate 0xFF header/chunk framing and exact boundary streams for physical lengths 0,1,511,512,513,1024,1025.
9. **Negative/failure test:** Reject a combined header+payload block, non-0xFF data flag, bad ROM checksum, short nonfinal chunk, >512 chunk, or any payload block for zero length.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.04 - M48O RAW target loader

1. **Purpose / REV11 requirement:** §19
2. **Exact implementation work:** For an explicit mutable-namespace load, validate the complete M48O header first, allocate the final RAW object storage, and stream RAW physical bytes directly there while computing the logical payload CRC; physical bytes equal logical bytes. Publish only after exact physical/logical length and logical-CRC validation; no second full payload copy is permitted.
3. **Files/artifacts created or modified:** tape.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** RAW load lands directly in the final allocation with logical_length==storage_length and exact bytes/CRC.
9. **Negative/failure test:** Truncation, extra chunk bytes, ROM checksum failure, logical CRC mismatch, or allocation failure frees only private state and publishes no partial/replacement object.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.05 - M48O PACKED target loader

1. **Purpose / REV11 requirement:** §19, §27.3
2. **Exact implementation work:** For an explicit mutable-namespace PACKED load, allocate exactly the M48O physical ZXP1 length as the final resident representation and stream tape bytes directly there while one 272-byte COLD_PREFERRED decoder validates complete logical length and logical CRC into a discard sink. On success the RAM object remains PACKED with storage_length equal the physical stream and logical_length equal the decoded length; no full RAW duplicate is materialized.
3. **Files/artifacts created or modified:** tape.asm; zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Packed load retains the exact validated ZXP1 bytes and reports correct logical/physical metadata with one decoder-state high-water.
9. **Negative/failure test:** Physical trailing/short bytes, malformed ZXP1, decoded length/CRC mismatch, decoder-allocation failure, or accidental RAW materialization returns the exact error and publishes no object.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.06 - Pinned SYSTEM bootstrap decode

1. **Purpose / REV11 requirement:** §5.1, §51
2. **Exact implementation work:** For packed font4x8/bincat decode to final pinned RAW allocation of required placement before publication.
3. **Files/artifacts created or modified:** tape.asm; boot init
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Valid resources pinned; malformed boot panic.
9. **Negative/failure test:** Packed crontab zero-length rejected; it must be RAW.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.07 - SYS_TAPE_SAVE RAW

1. **Purpose / REV11 requirement:** §19
2. **Exact implementation work:** Prompt for RECORD, lock tape globally, save exact M48O header/chunks from RAM object; preserve case/type/target. SYS_TAPE_SAVE exact register contract is HL=NUL-terminated path; resolve/validate object/type and complete M48O representation before entering the serialized ROM cassette critical section.
3. **Files/artifacts created or modified:** tape.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Roundtrip TXT exact.
9. **Negative/failure test:** Abort/BREAK releases lock and returns shell-ready.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.08 - Streaming save compression

1. **Purpose / REV11 requirement:** §19, §27.3
2. **Exact implementation work:** For a RAW source, permit deterministic two-pass streaming compression directly to tape without a second full payload; emit PACKED metadata only when the physical ZXP1 stream is strictly smaller and preserve the RAM object representation. For an already-PACKED RAM object, first allocate one 272-byte streaming decoder state and perform a complete decoder-to-discard pass over the resident packed bytes to recompute logical length and logical CRC because the 20-byte object record caches no CRC; only after validation succeeds may tape output begin, writing those same validated ZXP1 bytes in <=512-byte source slices with matching PACKED metadata. Decoder-state allocation failure returns E_NOMEM before any tape block is written.
3. **Files/artifacts created or modified:** tape.asm; zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** RAW streaming save and already-PACKED save produce independently decoded logical bytes/CRC with bounded workspace and leave the resident representation byte-identical.
9. **Negative/failure test:** Encoder/decoder/CRC/allocation failure before output produces zero tape blocks and no RAM-object mutation; equal/larger compression is not labeled PACKED.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.09 - SYS_TAPE_LOAD explicit destination

1. **Purpose / REV11 requirement:** §19
2. **Exact implementation work:** Forward sequential scan and explicit path/type placement; exact case matching. For public mutable loads, build and completely validate a private incoming RAW or PACKED representation first (including type/placement/name/physical/logical lengths/codec/logical CRC), then atomically create/replace the closed destination. No destination mutation is visible before validation/commit. SYS_TAPE_LOAD exact register contract is HL=NUL-terminated requested path; exact-case forward scan/load uses the architecture target/type rules and commits a mutable destination only after complete header/payload/codec/logical-CRC validation.
3. **Files/artifacts created or modified:** tape.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Requested exact lower-case object loads.
9. **Negative/failure test:** Incorrect case does not match. Corrupt the final payload chunk or logical CRC while an older same-name destination exists; old destination bytes/type/state/hash must remain unchanged.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.10 - SYS_TAPE_VERIFY

1. **Purpose / REV11 requirement:** §19
2. **Exact implementation work:** Compare on-tape logical content/CRC with target object without silent mutation. SYS_TAPE_VERIFY exact register contract is HL=NUL-terminated path; verification consumes/compares the sequential object without mutating the named RAM object or namespace.
3. **Files/artifacts created or modified:** tape.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Matching object success, altered target fails.
9. **Negative/failure test:** CRC error distinguished from name miss.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.11 - SYS_TAPE_SCAN bounded scratch

1. **Purpose / REV11 requirement:** §19
2. **Exact implementation work:** SYS_TAPE_SCAN consumes exactly one next M48O object per call and writes its validated 32-byte header. Read each payload chunk through one temporary <=512-byte COLD scratch allocation; for PACKED scan additionally allocate exactly one 272-byte COLD_PREFERRED decoder/history and decode to a discard sink so logical length/CRC are verified. Release both scratch allocations before the next object. Cassette has no reliable physical EOF: caller cancellation or ROM transport/error terminates scanning, with BREAK/user cancellation mapped to E_INTR. SYS_TAPE_SCAN exact register contract is HL -> writable 32-byte M48O-header buffer. It consumes exactly one next M48O object (header plus payload) and returns HL=1; cassette has no reliable physical EOF, so scanning stops only by caller decision/cancellation or ROM transport/error, with BREAK/user cancellation mapped to E_INTR.
3. **Files/artifacts created or modified:** tape.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Mixed RAW/PACKED stream validates header, physical chunks, logical length/CRC and releases scratch completely between objects.
9. **Negative/failure test:** Malformed header/chunk/ZXP1/CRC, retained scratch across objects, fabricated EOF, or >512 scan scratch returns controlled failure without namespace mutation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.12 - Global tape lock and blocking policy

1. **Purpose / REV11 requirement:** §19.7, §29
2. **Exact implementation work:** Serialize all tape operations; cooperative progress may pause; clock precision degradation documented.
3. **Files/artifacts created or modified:** tape.asm; scheduler.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Concurrent request gets documented busy/serialization behavior.
9. **Negative/failure test:** Second operation may not corrupt first.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.13 - Tape-positioning prompts

1. **Purpose / REV11 requirement:** §19, §20
2. **Exact implementation work:** Implement explicit PLAY/RECORD/rewind positioning prompts only in interactive foreground paths.
3. **Files/artifacts created or modified:** shell hooks/tape.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Prompt text/state; operation starts only after consent/input.
9. **Negative/failure test:** cron/background must never trigger interactive tape prompt.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.14 - Direct packed MEX1 tape execution

1. **Purpose / REV11 requirement:** §7, §19, §27.3
2. **Exact implementation work:** When a BCAT command resolves TAPE_BACKED, ALLOW_TAPE=0 returns E_AGAIN before tape motion. With ALLOW_TAPE=1, validate the M48O header and obtain the first 24 logical bytes through the RAW source or one 272-byte ZXP1 decoder as the MEX1 header; prove M48O.logical_length equals MEX1.total_stored_length, validate the header, then atomically reserve image+BSS, FAST stack and ARG1/ENV1. Stream logical image bytes directly into final uncommitted image memory while accumulating both M48O logical CRC and MEX1 body CRC; zero BSS. Consume relocation entries in strictly increasing nonoverlapping order and patch only the private image after each Section-8.1 bounds/overflow check. PACKED history starts at logical byte zero and remains continuous across header, image and relocation bytes. No process may become READY or replace the current image until complete M48O CRC, MEX1 header/body CRCs, relocation sequence and all physical/logical lengths pass. Any later failure discards every private allocation; no relocation table or second full RAW executable is retained. Maintain one continuous 272-byte ZXP1 history from logical byte zero across extraction of the 24-byte MEX1 header into final uncommitted image decode; never reset history at the header split and never allocate a second full RAW executable.
3. **Files/artifacts created or modified:** tape.asm; process.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** RAW and PACKED tape-backed MEX1 execute with exact CRC/length/relocation proofs, one final process image and at most one 272-byte decoder state; externally visible commit occurs only after the last validation.
9. **Negative/failure test:** ALLOW_TAPE=0 moves no tape; decoder-state E_NOMEM occurs before commit; corrupt late CRC/relocation/length after earlier private patches discards all new allocations and leaves no READY/partially replaced process.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.15 - Deterministic Phase-5 fixture tape

1. **Purpose / REV11 requirement:** §51 acceptance
2. **Exact implementation work:** Build contract-valid stub later resources but exact native+five-resource prefix. Do not claim final release byte identity.
3. **Files/artifacts created or modified:** maketap fixtures
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Two builds byte-identical; independent FUSE-utils inspect and TZX<->TAP roundtrip where applicable.
9. **Negative/failure test:** Any final-release label on fixture is policy failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.16 - Text/executable/UDG cassette round trips

1. **Purpose / REV11 requirement:** §51
2. **Exact implementation work:** Roundtrip exact case and logical bytes for representative TXT, BIN, UDG.
3. **Files/artifacts created or modified:** cassette tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Reset/load/CRC/execute where applicable.
9. **Negative/failure test:** Wrong-case load miss.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.17 - BREAK/error recovery

1. **Purpose / REV11 requirement:** §19, §51
2. **Exact implementation work:** Every tape abort/error releases lock, restores IY/ULA/stack state and returns to shell-ready state after handoff.
3. **Files/artifacts created or modified:** tape.asm; errors.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Forced BREAK/checksum/EOF each recover.
9. **Negative/failure test:** Lock left held fails follow-up operation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.18 - Second-emulator cassette compatibility gate

1. **Purpose / REV11 requirement:** §40.3
2. **Exact implementation work:** Run core TAP/TZX fixture in a second independent Spectrum emulator where practical; record product/version and result.
3. **Files/artifacts created or modified:** tests/cassette/compat
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Core boot/load state matches FUSE expectations.
9. **Negative/failure test:** Disagreement is unresolved gate, not waved away.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P5.19 - Phase-5 acceptance gate

1. **Purpose / REV11 requirement:** §51 acceptance
2. **Exact implementation work:** Aggregate exact prefix, contracts, roundtrips, CRC, packed rules, streaming save/exec and recovery.
3. **Files/artifacts created or modified:** Phase5 evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P5.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every Phase5 bullet PASS; fixture explicitly non-final.
9. **Negative/failure test:** Any byte/order mismatch blocks phase.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P5.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 6 - Shell

## P6.01 - PID1 shell entry contract

1. **Purpose / REV11 requirement:** §5.5, §20, §41.1
2. **Exact implementation work:** Create sh MEX1 startup with ARG1 argv0=sh, zero-entry ENV1, cwd ROOT and tty handles0/1/2 before login. Before PID1 is first scheduled, kernel assigns PID1 as the tty input owner. No child or service may become the initial owner by scheduling accident.
3. **Files/artifacts created or modified:** shell/sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boot fixture enters PID1 with exact registers/resources. PID1 has handles 0/1/2 and tty input ownership before first dispatch; ARG1/ENV1/cwd remain canonical.
9. **Negative/failure test:** Malformed boot sh contract panics before scheduling.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.02 - Issue display and exact heading

1. **Purpose / REV11 requirement:** §20.1
2. **Exact implementation work:** tty64 displays `/etc/issue` exactly once, with target lines exactly `<0x7F> Supratim Sanyal, SANYALnet Labs<LF>`, `https://supratim-sanyal.blogspot.com/<LF>`, and `48K. One Z80. No excuses.<LF>`; it does not separately print a duplicate heading, then prompts exactly `login: ` as specified by REV11 §20.1.
3. **Files/artifacts created or modified:** sh.asm; issue.txt
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Screen/console character buffer byte sequence exact.
9. **Negative/failure test:** Duplicate heading fails output oracle.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.03 - Login username validator

1. **Purpose / REV11 requirement:** §20.1
2. **Exact implementation work:** Prompt `login: ` and accept only 1..8 `[a-z][a-z0-9_-]{0,7}`; reprompt invalid.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary login corpus.
9. **Negative/failure test:** Uppercase/empty/9-char rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.04 - Session home/cwd initialization

1. **Purpose / REV11 requirement:** §20.1
2. **Exact implementation work:** Select fixed /home/<user>, chdir there, no dynamic mkdir fiction.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** pwd -> exact /home/name.
9. **Negative/failure test:** Invalid HOME topology cannot escape fixed namespace.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.05 - Initial environment

1. **Purpose / REV11 requirement:** §20.2
2. **Exact implementation work:** Create USER,HOME,SHELL=/bin/sh,PATH=/bin:. as mutable shell table; $? separate.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** ENV listing exact sorted order/values.
9. **Negative/failure test:** Treat $? as ENV1 entry => fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.06 - set/unset semantics

1. **Purpose / REV11 requirement:** §20.2
2. **Exact implementation work:** Implement exact NAME syntax, first = delimiter, 8-entry/256-byte transaction, sorted listing, no protected magic vars.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary set/unset corpus.
9. **Negative/failure test:** Overflow leaves table unchanged.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.07 - 247-byte line input

1. **Purpose / REV11 requirement:** §20.2A
2. **Exact implementation work:** Bound interactive line to 247 excluding NUL; editing/input owner through tty.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** 247 accepted, 248 E_TOOLONG/no side effect.
9. **Negative/failure test:** Unbounded line fails canary.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.08 - Tokenizer quoting/escaping

1. **Purpose / REV11 requirement:** §20.3
2. **Exact implementation work:** Implement byte parser for backslash, single and double quotes exactly.
3. **Files/artifacts created or modified:** sh.asm; shell.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Golden token corpus.
9. **Negative/failure test:** Unterminated quote E_INVAL.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.09 - Variable expansion

1. **Purpose / REV11 requirement:** §20.3
2. **Exact implementation work:** Implement $NAME, ${NAME}, $? only; expansion in unquoted/double, suppressed single; no field splitting/glob/substitution.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Expansion golden corpus and post-expansion bounds.
9. **Negative/failure test:** Malformed ${} E_INVAL before side effect.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.10 - Operator lexer

1. **Purpose / REV11 requirement:** §20.3
2. **Exact implementation work:** Recognize ; && || > >> < | & with quoted/escaped operators literal.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Golden operator corpus.
9. **Negative/failure test:** Unsupported token/grouping rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.11 - Precedence/binding parser

1. **Purpose / REV11 requirement:** §20.3
2. **Exact implementation work:** Redirections bind simple command; | > &&/|| equal LTR > ; ; & only final complete pipeline and cannot mix ;/&&/||.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** AST/golden execution order exact.
9. **Negative/failure test:** Parentheses/subshell rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.12 - Argument/pipeline bounds

1. **Purpose / REV11 requirement:** §20.2A
2. **Exact implementation work:** Max16 args including argv0; max6 pipeline stages; all bounds revalidated after expansion.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Boundary command corpus.
9. **Negative/failure test:** 17 args/7 stages fail before spawn/redirection.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.13 - Core/stateful builtin table and exact lookup

1. **Purpose / REV11 requirement:** §20.4, §52
2. **Exact implementation work:** Implement the Phase-6 core/stateful parent-shell built-ins `cd`, `pwd`, `set`, `unset`, `jobs`, `wait`, `kill`, `mem`, `ps`, `clear`, `save`, `load`, `verify`, `tape`, `exit` with exact bytewise lower-case lookup and no aliases. This is not the final exhaustive builtin table: install explicit dispatch-hook slots for the separately specified Section-20.6 ROM-assisted built-ins, which close only in Phase 7.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Each Phase-6 core builtin resolves only at exact lower-case spelling; mixed case misses; unresolved Phase-7 hook names remain unavailable until their owning Phase-7 step.
9. **Negative/failure test:** Aliases/case folding or prematurely treating a Phase-7 hook as implemented fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.14 - PATH external lookup

1. **Purpose / REV11 requirement:** §20.7
2. **Exact implementation work:** Colon left-to-right, empty component `.`; nonexistent/non-dir skipped; unset/empty => no search; slash bypasses; no hidden default. Skip PATH components whose normalized directory or combined candidate exceeds the 31-byte path limit and skip same-name non-BIN objects; continue left-to-right search. A direct command token containing `/` bypasses builtins/PATH: overlength normalized direct path returns E_TOOLONG and direct non-BIN target reaches SYS_SPAWN E_FORMAT. These direct errors do not abort unrelated PATH searches because PATH candidates are skipped instead.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Complete lookup matrix.
9. **Negative/failure test:** LS must not resolve ls. Matrix includes overlength component, overlength candidate, non-directory component, wrong-type candidate, direct overlength and direct non-BIN; only direct targets expose E_TOOLONG/E_FORMAT.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.15 - BCAT tape-backed command discovery

1. **Purpose / REV11 requirement:** §18, §20.7
2. **Exact implementation work:** Resident /bin first; BCAT known command can prompt explicit forward tape search and set ALLOW_TAPE only after consent.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Known nonresident command prompts and runs when consented.
9. **Negative/failure test:** Decline leaves tape unmoved.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.16 - External /bin/echo

1. **Purpose / REV11 requirement:** §20.5, §33, §52
2. **Exact implementation work:** Deliver tiny MEX1 echo: args separated one ASCII space + LF; no args LF. It is external so pipelineable.
3. **Files/artifacts created or modified:** utils/echo.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** echo hello | Phase3 sink exact.
9. **Negative/failure test:** Do not accidentally add parent-shell echo builtin.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.17 - Transactional builtin redirections

1. **Purpose / REV11 requirement:** §20.5, §31, §52
2. **Exact implementation work:** Preserve original 0/1/2 in spare shell handles, install all replacements, rollback all on setup failure, restore after builtin success/error before next command.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Injected failure after each replacement restores exact refs and no builtin side effect.
9. **Negative/failure test:** Leaked redirected stdout into next command fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.18 - External redirections

1. **Purpose / REV11 requirement:** §20.3, §31
2. **Exact implementation work:** Create/open RAM objects with correct type policy; > trunc, >> append, < input; at most one in/out per simple command.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden redirection cases and allocation rollback.
9. **Negative/failure test:** Cassette /dev/tape random redirection rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.19 - Semicolon sequencing

1. **Purpose / REV11 requirement:** §20.3
2. **Exact implementation work:** Execute complete foreground units left-to-right; status updates exact.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** A;B order and $? exact.
9. **Negative/failure test:** Failure must not silently skip later ; command.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.20 - && and || short-circuit

1. **Purpose / REV11 requirement:** §20.3
2. **Exact implementation work:** Use final foreground pipeline status; equal precedence LTR.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Truth-table sequences exact.
9. **Negative/failure test:** Wrong precedence fixture fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.21 - Foreground pipeline launch transaction

1. **Purpose / REV11 requirement:** §20.12
2. **Exact implementation work:** Create all pipes/redirections, spawn all stages without yielding, assign tty input owner to first tty-reading stage, close parent refs, then wait; first schedule only after setup complete.  Before each SYS_SPAWN in the completed launch transaction, build that child ENV1 as an immutable snapshot of the shell current environment table at that instant; after login the shell table is authoritative. The cold PID1 zero-entry ENV1 is only the boot input to `sh`, not the environment inherited by later commands. `$?` remains shell state and is never serialized into ENV1. Each child in a pipeline receives the same launch-time environment snapshot unless the architecture command semantics have changed the shell environment before that pipeline begins.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** 3-stage real pipeline exact.  Mutate USER/HOME/PATH through valid shell state before launch and prove the child ENV1 contains the current exact case-sensitive values while `$?` is absent; the original cold zero-entry PID1 ENV1 remains unchanged process bootstrap data.
9. **Negative/failure test:** Mid-launch failure kills/reaps created children and restores tty/cursor/handles.  Reusing PID1 cold ENV1 for children, passing a live pointer to mutable shell environment storage, or inserting `$?` into ENV1 fails the child-bootstrap oracle.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.22 - Foreground tty input ownership

1. **Purpose / REV11 requirement:** §13.5, §20.12
2. **Exact implementation work:** PID1 alone can set owner; foreground first tty-input stage owns; restore PID1 after job.
3. **Files/artifacts created or modified:** sh.asm; console.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Non-owner read E_BUSY; owner exit restoration.
9. **Negative/failure test:** Background stage cannot steal owner.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.23 - Background job launch

1. **Purpose / REV11 requirement:** §20.12
2. **Exact implementation work:** & only final pipeline; stdin /dev/null unless redirected; no tty input ownership; successful launch $?=0.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Background progresses cooperatively; shell prompt returns.
9. **Negative/failure test:** Launch failure records actual failure, no phantom job.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.24 - jobs bounded table

1. **Purpose / REV11 requirement:** §20.12
2. **Exact implementation work:** Track active/background jobs within process limits and exact process names/status.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Spawn/exit/reap updates.
9. **Negative/failure test:** Stale PID reuse not displayed as old job.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.25 - wait builtin

1. **Purpose / REV11 requirement:** §20.4, §20.12
2. **Exact implementation work:** Implement exactly `wait` and `wait pid`. With no operand, wait for and reap every currently shell-managed background job, continuing until that launch-set is exhausted; adopted services that are visible only through `ps` are not silently added to the shell job set. With one operand, require one decimal PID naming a shell direct/adopted child, invoke SYS_WAIT, and update `$?` from the resulting child status. Nonexistent/nonchild PID returns E_CHILD. Any other arity or non-decimal PID is E_INVAL before waiting or changing job state.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.25`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** No-argument wait drains exactly the current shell-managed background jobs and leaves adopted non-job services alone; one-PID wait blocks/wakes/reaps the specified valid child and propagates its status to `$?`.
9. **Negative/failure test:** Nonchild/nonexistent PID must return E_CHILD; non-decimal/extra operands E_INVAL; no-argument wait must not block on or reap an adopted service that is not a shell-managed job, and a failure must not corrupt the job table.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.25.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.26 - kill builtin and tty-owner BREAK cancellation

1. **Purpose / REV11 requirement:** §§20.12,21; invariants 99/111
2. **Exact implementation work:** Implement `kill pid` as the shell interface to SYS_KILL with the exact permission/never-started/cooperative rules already frozen in Phase 2. Implement BREAK only as the cooperative tty-owner cancellation path: IM2 merely sets `break_pending`; at the next syscall/yield/input boundary, if `tty_input_owner_pid` is PID1 cancel only the current shell input line, while if the owner is a live PID2..7 set CANCEL_PENDING only on that owner. BREAK never implies process-group or whole-pipeline cancellation for non-owner stages. Already-started C48 code that consumes cancellation at a safe point exits status 130; hand-written assembly may handle E_INTR. A CPU-bound process that never re-enters the kernel is not forcibly preempted.
3. **Files/artifacts created or modified:** `v1/src/shell/sh.asm`; `v1/src/kernel/process.asm`; BREAK/pipeline tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.26`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exercise PID1 line cancellation, a foreground pipeline with one tty-owning stage plus non-owner stages, blocked-syscall E_INTR, never-started child kill without executing its PC, and an already-started C48 target returning status 130 at a safe point. Prove only the current tty owner receives BREAK-derived cancellation and shell tty ownership is restored after completion.
9. **Negative/failure test:** Reject any implementation that converts BREAK into process-group/pipeline broadcast, cancels a non-owner stage merely because it shares a pipeline, preempts a CPU-bound task that never enters the kernel, allows PID0/PID1 to be killed through ordinary SYS_KILL, or executes a never-started killed child.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.26.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.27 - Shell cursor restoration

1. **Purpose / REV11 requirement:** §13, §20.12
2. **Exact implementation work:** Hide cursor during foreground job setup/run as specified; restore prior mode/shape/visibility on every completion/failure.
3. **Files/artifacts created or modified:** sh.asm; cursor.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.27`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Success/error/cancel paths restore exact state.
9. **Negative/failure test:** One error path leaks hidden cursor -> fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.27.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.28 - Shell parser/lookup golden suite

1. **Purpose / REV11 requirement:** §52 acceptance
2. **Exact implementation work:** Freeze host parser/AST and target execution vectors for quoting/operators/expansion/PATH/builtins/case. Golden vectors are derived from REV11 userland contracts only; no host-shell quoting, field-splitting, globbing, substitution, precedence, PATH, environment or parent-builtin behavior may be borrowed implicitly.
3. **Files/artifacts created or modified:** tests/emulator/shell_*
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.28`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** All golden vectors exact.
9. **Negative/failure test:** Any unsupported construct accidentally accepted fails. Run divergence vectors chosen to behave differently in common host shells; ZX-UX must follow REV11, not the host.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.28.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.29 - PID1 zombie reaping and safe exit

1. **Purpose / REV11 requirement:** §20.12; invariants 110/118
2. **Exact implementation work:** Before every prompt and whenever `jobs` runs, scan PID2..7 with SYS_PROC_INFO and immediately nonblocking-SYS_WAIT every ZOMBIE child/adopted process; update the bounded job table while adopted services remain visible only in `ps`. `exit` refuses E_BUSY while any PID2..7 is live. With none live, print exactly `system halted`, call SYS_EXIT, disable interrupts and remain in a permanent HALT/spin safe state; unexpected PID1 exit uses the same safe halt and never returns to BASIC.
3. **Files/artifacts created or modified:** `v1/src/shell/sh.asm`; process/shell tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.29`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** No zombie consumes a user slot across prompts; live child blocks exit; clean PID1 exit reaches permanent safe halt and never the BASIC return sentinel.
9. **Negative/failure test:** Skip one reap, misclassify adopted cron as shell job, allow exit with PID2 live, or reach BASIC sentinel: each must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.29.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P6.30 - Phase-6 acceptance gate

1. **Purpose / REV11 requirement:** §52 acceptance
2. **Exact implementation work:** Aggregate login/core parser, echo pipe, PATH matrix, builtin E_NOTSUP in pipe/bg, redirection rollback, child errors and mixed-case behavior.
3. **Files/artifacts created or modified:** Phase6 evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P6.30`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every Phase6 acceptance bullet PASS.
9. **Negative/failure test:** Any side effect before E_NOTSUP blocks phase.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P6.30.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 7 - Graphics, Attributes, Sound, UDGs

## P7.01 - Graphics syscall ABI

1. **Purpose / REV11 requirement:** §10.1, §15, §53
2. **Exact implementation work:** Implement PLOT,DRAW,CIRCLE,ATTR,BORDER,POINT exact register/result contracts via validated wrappers/direct safe code. The exact public calls are `SYS_GFX_PLOT` H=x,L=y; `SYS_GFX_DRAW` HL->x1,y1,x2,y2; `SYS_GFX_CIRCLE` HL->x,y,radius; `SYS_GFX_ATTR` H=selector,L=value with selectors 0 INK,1 PAPER,2 BRIGHT,3 FLASH,4 INVERSE,5 OVER; `SYS_GFX_BORDER` H=0,L=color; `SYS_GFX_POINT` H=x,L=y in and H=0,L=0/1 out. Each validates before screen/ULA mutation and returns canonical IY.
3. **Files/artifacts created or modified:** graphics.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** ABI vectors exact.
9. **Negative/failure test:** Bad user params no screen corruption.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.02 - Canonical pixel/scanline helper

1. **Purpose / REV11 requirement:** §3.3, §15
2. **Exact implementation work:** Use one tested Spectrum bitmap address formula for all direct rendering including tty/UDG.
3. **Files/artifacts created or modified:** graphics.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All 256x192 sampled/edge addresses match host oracle.
9. **Negative/failure test:** Duplicate divergent helper blocked by static review.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.03 - SYS_GFX_PLOT

1. **Purpose / REV11 requirement:** §15.1, §15.3
2. **Exact implementation work:** Wire the Phase0-approved PLOT-SUB behavior through `SYS_GFX_PLOT` with H=x,L=y. The public coordinate domain is x=0..255 and y=0..191; because H is already u8, validate y<=191 before any bitmap/attribute mutation. ROM and any later native replacement must expose identical ZX-UX results. SYS_GFX_PLOT exact entry is H=x,L=y.
3. **Files/artifacts created or modified:** graphics.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All four display corners plus interior vectors set exactly the intended pixel/attribute state and return canonical success.
9. **Negative/failure test:** y=192 and y=255 return E_INVAL with bitmap/attributes/cursor state byte-identical; any future RAM replacement that diverges from the approved ROM-visible result fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.04 - SYS_GFX_DRAW

1. **Purpose / REV11 requirement:** §15.1, §15.3
2. **Exact implementation work:** Wire the approved lower DRAW path through `SYS_GFX_DRAW`, HL -> four-byte `{x1,y1,x2,y2}`. Both endpoints must satisfy x=0..255,y=0..191 before side effects; invalid y1/y2 returns E_INVAL. For valid endpoints, expose the same clipped/native line result regardless of ROM or later RAM implementation and preserve the verified 0x24BA register/workspace contract. SYS_GFX_DRAW exact entry is HL -> four-byte `{x1,y1,x2,y2}` record.
3. **Files/artifacts created or modified:** graphics.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden horizontal/vertical/diagonal/reverse-direction/boundary vectors match an independent bitmap oracle and the approved ROM-visible result.
9. **Negative/failure test:** y1/y2=192 or 255, malformed record pointer, guard-byte mutation outside display, or future replacement disagreement fails before visible mutation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.05 - SYS_GFX_CIRCLE

1. **Purpose / REV11 requirement:** §15.1, §15.4
2. **Exact implementation work:** Implement `SYS_GFX_CIRCLE` HL -> three-byte `{x,y,radius}` using the approved Class-B ROM-assisted path if safe, otherwise an integer midpoint fallback only under the Section-14.9 replacement rule. Validate center x=0..255,y=0..191; radius is the full u8 domain 0..255. Radius zero plots the center. Circumference pixels outside 0..255 x 0..191 are silently clipped rather than rejecting the whole circle. ROM and RAM paths must expose byte-identical ZX-UX clipping/error semantics. SYS_GFX_CIRCLE exact entry is HL -> three-byte `{x,y,radius}` record.
3. **Files/artifacts created or modified:** graphics.asm; rom services
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden radius-0, wholly-visible and edge-clipped circles match the independent bitmap oracle and identical ROM/RAM contract.
9. **Negative/failure test:** Invalid center y, unsafe ROM state, treating an off-screen circumference as whole-circle E_INVAL, or a ROM/RAM semantic mismatch fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.06 - SYS_GFX_POINT

1. **Purpose / REV11 requirement:** §15.1, §15.3
2. **Exact implementation work:** Implement `SYS_GFX_POINT` H=x,L=y; validate x=0..255,y=0..191 before access and return H=0,L=0 or 1 without changing bitmap, attributes, cursor state or graphics attributes. SYS_GFX_POINT exact entry is H=x,L=y and success returns H=0,L=0 or 1.
3. **Files/artifacts created or modified:** graphics.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** 0/1 golden bitmap cases at corners/interior return exact values with a whole-display hash unchanged.
9. **Negative/failure test:** y=192/255 returns E_INVAL and any side effect or non-0/1 success value fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.07 - SYS_GFX_ATTR state API

1. **Purpose / REV11 requirement:** §§13,15.1,15.5
2. **Exact implementation work:** Maintain ink/paper/bright/flash/inverse/over as the shared console/graphics state through `SYS_GFX_ATTR` H=selector,L=value: selectors 0 INK,1 PAPER,2 BRIGHT,3 FLASH,4 INVERSE,5 OVER. Freeze the native hardware domains explicitly required by REV11: INK 0..7, PAPER 0..7, BRIGHT 0/1, FLASH 0/1. Reject invalid selector or invalid native-domain value before changing state. Two tty64 logical columns continue to share one 8x8 hardware attribute cell; no per-pixel color is invented. SYS_GFX_ATTR exact entry is H=selector,L=value with selectors 0 INK,1 PAPER,2 BRIGHT,3 FLASH,4 INVERSE,5 OVER; reject all others before changing graphics state.
3. **Files/artifacts created or modified:** graphics.asm; console.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** State get/set and rendered attribute bytes are exact for every native value; tty64 pair-sharing remains visible and deterministic.
9. **Negative/failure test:** INK/PAPER=8, BRIGHT/FLASH>1, selector>5 or any attempted per-pixel-color state must fail before graphics state/display mutation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.08 - SYS_GFX_BORDER via central ULA shadow

1. **Purpose / REV11 requirement:** §15
2. **Exact implementation work:** No direct competing port shadow; border preserves MIC/beeper bits. SYS_GFX_BORDER exact entry is H=0,L=color; validate H and color before updating the central ULA shadow/output.
3. **Files/artifacts created or modified:** graphics.asm; ula_io.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Port shadow transitions exact.
9. **Negative/failure test:** Direct OUT bypass fails static scan.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.09 - SYS_BEEP five-byte operands

1. **Purpose / REV11 requirement:** §§10.1,17
2. **Exact implementation work:** Implement synchronous `SYS_BEEP` with HL -> five-byte Spectrum-compatible duration and DE -> five-byte pitch. Validate both complete pointer ranges, convert/use the Phase0-approved ROM BEEP/BEEPER path under the serialized ROM error gateway, and return 0 on success or positive ZX-UX errno. Preserve Sinclair semantics: duration seconds; pitch semitones above middle C; negative/fractional duration/pitch accepted wherever the verified ROM domain accepts them; +/-12 pitch is one octave; no arbitrary narrower pitch range. The note is synchronous: the ROM timing-critical path may disable maskable interrupts, so cooperative progress and accepted-frame-derived wall time/ticks pause for that interval; missed ticks are never fabricated/backfilled. SYS_BEEP exact entry is HL -> five-byte C48/Spectrum duration value and DE -> five-byte pitch value; validate both complete ranges before entering the synchronous ROM critical section.
3. **Files/artifacts created or modified:** sound.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Mandatory vectors `beep 1,0`, `beep .5,9`, `beep .25,-12`, `beep .5,0.5` plus octave/fraction vectors complete with exact five-byte operands/status and return only when the note completes.
9. **Negative/failure test:** Invalid pointers/domain map safely (ROM rejection => E_INVAL), no BASIC escape occurs, and a long-note test proves missed frame time is not falsely backfilled.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.10 - calc final safe expression gateway

1. **Purpose / REV11 requirement:** §§14.6,20.6
2. **Exact implementation work:** Implement the Phase0-selected safe isolated ROM parser or ZX-UX tokenizer with serialized ROM numeric backend. Accept exactly: decimal numeric literals; unary + and -; + - * / ^; parentheses; pi; abs,sgn,int,sqrt,exp,ln,sin,cos,tan,asin,acos,atan. Defer rnd. Preserve case-sensitive lower-case public names; uppercase SIN is not an alias. Reject before ROM evaluation: peek,in,inkey$,screen$,attr,point,usr,poke,out,clear,new,run,load,save,merge,randomize usr, variable assignment, BASIC statements, and string expressions unless separately specified. As a shell builtin, `calc` requires exactly one normal shell argument after quote removal/expansion; missing or extra arguments return E_INVAL before entering the numeric/ROM gateway. It is exact-case, single-stage foreground only, and never consumes BCAT or tape.
3. **Files/artifacts created or modified:** sh.asm; rom_services.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every allowed grammar family returns a controlled numeric result; every forbidden token/family is rejected before unsafe ROM action; no BASIC statement/mutation escape occurs.
9. **Negative/failure test:** `rnd`, uppercase aliases, forbidden operations, assignment, BASIC statements, strings or malformed expressions must fail safely without escaping into BASIC. Missing/extra arguments, pipeline/background use, mixed-case `CALC`, or any attempt to resolve calc through BCAT/PATH/tape must fail before ROM/tape/visible side effects.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.11 - SYS_ROM_INFO diagnostic gateway / rom builtin

1. **Purpose / REV11 requirement:** §14.7, §20.6
2. **Exact implementation work:** rom [keyboard|tape|gfx|math] reads canonical metadata; no unrestricted romcall. Implement the frozen read-only `SYS_ROM_INFO` metadata ABI used by `rom`; it exposes only approved ROM-service metadata and can never dispatch an arbitrary ROM address supplied by userland. SYS_ROM_INFO consumes HL -> exact four-byte ROMQ1 `{u8 index,u8 category,u16 out_ptr}`. Category IDs are exactly 0 ALL, 1 KEYBOARD, 2 CONSOLE, 3 TAPE, 4 GRAPHICS, 5 SOUND, 6 MATH. For the selected category it returns HL=1 and writes one exact 24-byte ROMOUT1, or HL=0 when index is past that category. ROMOUT1 layout is `name[16],u16 address,u8 classification,u8 category,u16 contract_flags,u16 reserved=0`; name contains 1..15 visible bytes followed by NUL/zero padding; classification is exactly 1=A,2=B,3=C; contract_flags bit0=MAY_ERROR_RESTART, bit1=ALTREG_SENSITIVE, bit2=DISABLES_INTERRUPTS, bit3=NONREENTRANT and bits4..15=0. Validate ROMQ1 and the complete writable ROMOUT1 range before reading/publishing metadata.
3. **Files/artifacts created or modified:** sh.asm; rom_services.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Output names/addresses/classes/contracts match ledger. Byte-level vectors cover every ROMQ1 category, first/last/past-end indices, all three classification IDs, each individual contract flag and combinations, exact 24-byte ROMOUT1 offsets/padding/reserved zeros, and prove HL=1/0 semantics exactly.
9. **Negative/failure test:** `romcall` unknown/not exposed. Attempt to encode an arbitrary ROM-call request through SYS_ROM_INFO and require E_INVAL/E_NOTSUP with no ROM control transfer. Unknown category, malformed ROMQ1/range, classification outside 1..3, nonzero ROMOUT1 reserved field, or any contract_flags bit above bit3 must be rejected/caught by the ABI oracle; no arbitrary ROM transfer is possible.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.12 - Graphics/attribute shell builtins

1. **Purpose / REV11 requirement:** §20.6
2. **Exact implementation work:** Wire plot,line,circle,point,ink,paper,bright,flash,inverse,over,border to kernel services; parent-shell foreground-only restrictions remain.
3. **Files/artifacts created or modified:** sh.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Representative calls change only expected state.
9. **Negative/failure test:** Pipeline/bg returns E_NOTSUP before side effects.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.13 - UDG subsystem on boot-pinned 32-slot bank

1. **Purpose / REV11 requirement:** §§4.3,14.8A,16.1-16.2
2. **Exact implementation work:** Use the 256-byte COLD_PREFERRED bank already allocated/pinned and installed into ROM UDG at 23675-23676 by P1.14; never allocate/repoint a second bank. Freeze 32 slots numbered 0..31, each exactly 8 bytes/8 raster rows with bit7 the leftmost pixel. Reserve character codes 0x80-0x9F as UDG identifiers: tty32 may render them directly as one 8x8 cell; tty64 must not reinterpret them as 4x8 glyphs and presents full-size UDGs only through `udg_draw`. Preserve the pinned bank identity through shutdown.
3. **Files/artifacts created or modified:** udg.asm; boot/runtime integration
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Pointer/bank identity remains the P1.14 value; slot 0/31 raster-bit vectors render bit7 leftmost; tty32 0x80/0x9F mapping and tty64 non-interpretation are exact; allocator shows one pinned 256-byte bank only.
9. **Negative/failure test:** Phase7 reallocation/repoint, bank move/free, wrong bit orientation, slot/code alias outside 0..31/0x80..0x9F, tty64 treating a UDG code as 4x8 text, or a second UDG bank fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.14 - SYS_UDG_DEFINE/GET/CLEAR

1. **Purpose / REV11 requirement:** §§10.1,16.1,16.3
2. **Exact implementation work:** Implement exact 8-byte native-glyph operations: `SYS_UDG_DEFINE` C=slot,B=0,HL=8-byte readable source; `SYS_UDG_GET` C=slot,B=0,HL=8-byte writable destination; `SYS_UDG_CLEAR` H=0,L=slot. Slot domain is 0..31; each byte is one raster row with bit7 leftmost. Validate complete pointers/registers/slot before changing the live bank or output buffer; CLEAR produces eight zero bytes. Implement exact `SYS_UDG_DEFINE` C=slot,B=0,HL=8-byte readable source; `SYS_UDG_GET` C=slot,B=0,HL=8-byte writable destination; and `SYS_UDG_CLEAR` H=0,L=slot. Validate slot/register/pointer before changing the live bank or output buffer.
3. **Files/artifacts created or modified:** udg.asm; syscall.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Slots 0 and 31 round-trip exact 8-byte raster patterns and CLEAR to zeros; bit-orientation display oracle is exact.
9. **Negative/failure test:** Slot32, nonzero reserved B/H, invalid pointer/range or partial output mutation before full validation fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.15 - SYS_UDG_DRAW and tty64 width

1. **Purpose / REV11 requirement:** §16.2-16.3
2. **Exact implementation work:** Implement exact `SYS_UDG_DRAW` HL -> three-byte `{slot,row,col}` using physical 8x8 character-cell coordinates independent of terminal mode: slot=0..31,row=0..23,col=0..31. Draw the full 8x8 glyph using current console INK/PAPER/BRIGHT/FLASH attributes. In tty64 the draw overwrites bitmap corresponding to logical columns `2*col` and `2*col+1`; it is not a 4x8 text glyph. Validate the entire record before any bitmap/attribute change and return E_INVAL on any out-of-range field. Implement exact `SYS_UDG_DRAW` with HL -> three-byte `{slot,row,col}` record; validate all bytes and tty64 width implications before any bitmap change.
3. **Files/artifacts created or modified:** udg.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary slot/row/col vectors change exactly one physical 8x8 cell and its attribute, preserve neighboring cells, and tty64 covers exactly the two corresponding logical columns.
9. **Negative/failure test:** slot=32,row=24,col=32 or malformed record pointer returns E_INVAL with screen/attributes/cursor unchanged.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.16 - UDG1 RAM persistence

1. **Purpose / REV11 requirement:** §16.5
2. **Exact implementation work:** Implement `udg save name`/`udg load name` against mutable RAM objects only; neither operation moves cassette. Save creates or transactionally replaces an M48O-type UDG object. Load accepts RAW or transparently PACKED RAM UDG objects, validates the complete payload before changing the live bank, then applies all encoded slots atomically. Freeze UDG1 bytes exactly: 0..3 magic `UDG1`; 4 version=1; 5 base slot 0..31; 6 glyph count 1..32; 7 reserved=0; 8.. exactly count*8 glyph bytes. Require base+count<=32 and total payload length=8+count*8. M48O CRC is the only payload integrity value; UDG1 adds no second checksum. Cassette persistence remains explicit shell `save`/`load`.
3. **Files/artifacts created or modified:** utils/udg.asm; UDG1 fixtures
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact UDG1 byte round-trip for single/full/ranged banks; RAW/PACKED load produces identical live bytes; forced save replacement and load are atomic.
9. **Negative/failure test:** Bad magic/version/reserved/count/base+count/length, invented second checksum requirement, decode failure or forced transaction error leaves the prior RAM object/live bank byte-identical and causes no tape motion.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.17 - 2x2 UDG library helper

1. **Purpose / REV11 requirement:** §16.4, §53
2. **Exact implementation work:** Provide user-library `udg_draw_2x2(base_slot,row,col)` without adding kernel state. Draw four consecutive slots exactly: base+0 top-left, base+1 top-right, base+2 bottom-left, base+3 bottom-right, producing a 16x16 sprite by composing four ordinary physical-cell `udg_draw` operations. Validate that all four slots/cells fit before the first draw.
3. **Files/artifacts created or modified:** libc48/udg.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden 2x2 pattern proves exact quadrant/slot order and current-attribute behavior.
9. **Negative/failure test:** base_slot>28, row/col whose 2x2 cells do not all fit, or a failure that partially draws before validation fails the helper test.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.18 - C48 beep ABI bridge fixture

1. **Purpose / REV11 requirement:** §17, §53
2. **Exact implementation work:** Before compiler exists, use hand-built C48_REGCALL-compatible fixture to prove float-pointer arguments reach same SYS_BEEP.
3. **Files/artifacts created or modified:** sound tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Return 0/errno and operands exact.
9. **Negative/failure test:** Hidden/pointer convention mismatch fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.19 - GFX golden program

1. **Purpose / REV11 requirement:** §53 acceptance
2. **Exact implementation work:** Run graphics/UDG/sound integrated golden machine-code fixture and assert no writes outside display/UDG/approved vars.
3. **Files/artifacts created or modified:** tests/graphics/
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Screen hash, attrs, UDG bytes, ROM UDG pointer exact.
9. **Negative/failure test:** Guard regions detect stray write.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.20 - beep shell builtin

1. **Purpose / REV11 requirement:** §§17,20.5-20.7,53; invariant 78
2. **Exact implementation work:** Implement lower-case `beep` as a ROM-assisted parent-shell builtin, never a BCAT/tape executable. After normal shell quote removal and variable expansion it requires exactly one shell argument whose text contains exactly one top-level comma separating duration and pitch; commas nested inside allowed parenthesized calculator expressions do not count. Missing/extra shell arguments, zero/multiple top-level separators, empty operands, or malformed expressions return E_INVAL before any ROM call. Validate each operand with exactly the same safe numeric-expression grammar as `calc`, convert both through the approved Spectrum five-byte numeric gateway, then invoke SYS_BEEP. Preserve Sinclair BASIC semantics: duration is seconds; pitch is semitones above middle C; negative and fractional pitch/duration are legal when accepted by the verified ROM domain; adding/subtracting 12 changes pitch by one octave; no arbitrary narrower pitch range is invented. Sound is synchronous: the builtin returns only after the note completes or validation fails, and long ROM BEEPER critical sections may pause cooperative progress and accepted-frame-derived wall time without any fabricated tick catch-up. The builtin is single-stage foreground only, supports the normal transactional builtin redirections, and pipeline/background use returns E_NOTSUP before redirection, parsing side effects, tape motion, or ROM entry.
3. **Files/artifacts created or modified:** `v1/src/shell/sh.asm`; `v1/src/kernel/sound.asm`; shell/sound tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every valid vector is parsed as one shell argument with one top-level comma, preserves BASIC-compatible duration/pitch semantics, reaches SYS_BEEP exactly once, returns cleanly to sh, and leaves builtin redirections restored.
9. **Negative/failure test:** Malformed/unsafe expressions (`USR`, `PEEK`, `IN`, `POKE`, `OUT`), missing/extra args, ambiguous top-level commas, `BEEP` case alias, pipeline/background use, and a fixture that tries BCAT/tape lookup for `beep` must all fail before ROM/tape/visible side effects. Later `which beep` must not manufacture an external pathname.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P7.21 - Phase-7 acceptance gate

1. **Purpose / REV11 requirement:** §53 acceptance
2. **Exact implementation work:** Aggregate gfx, edge, UDG, beep and final ROM-backed builtin evidence. Include the new P7.20 shell `beep` grammar/lookup/redirection tests in the aggregate, not only the SYS_BEEP kernel ABI vectors.
3. **Files/artifacts created or modified:** Phase7 evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P7.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All Phase7 bullets PASS. Both the kernel SYS_BEEP contract and the user-facing shell builtin contract are independently green.
9. **Negative/failure test:** Any ULA/IY/ROM-state drift blocks phase.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P7.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 8 - Core Utilities

## P8.01 - Utility `ls`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (ls)
2. **Exact implementation work:** List exact stored names/types; `-l` adds logical size, RAM/TAPE_BACKED and packed physical/savings; /bin union resident+BCAT.
3. **Files/artifacts created or modified:** `v1/src/utils/ls.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/ls contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `ls`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.02 - Utility `cat`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (cat)
2. **Exact implementation work:** Stream named object or stdin to stdout and compose in pipes.
3. **Files/artifacts created or modified:** `v1/src/utils/cat.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/cat contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `cat`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.03 - Utility `cp`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (cp)
2. **Exact implementation work:** Atomic logical copy via unique O_CREATE|O_EXCL `/tmp/.cp<pid>.<n>` then SYS_RENAME; preserve type; packed source decoded; same object no-op.
3. **Files/artifacts created or modified:** `v1/src/utils/cp.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/cp contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `cp`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.04 - Utility `mv`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (mv)
2. **Exact implementation work:** Use exact SYS_RENAME atomic semantics including case-only, replacement and E_BUSY.
3. **Files/artifacts created or modified:** `v1/src/utils/mv.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/mv contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `mv`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.05 - Utility `rm`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (rm)
2. **Exact implementation work:** SYS_REMOVE mutable closed RAM object only; never modify cassette history.
3. **Files/artifacts created or modified:** `v1/src/utils/rm.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/rm contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `rm`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.06 - Utility `pack`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (pack)
2. **Exact implementation work:** Invoke SYS_PACK; report logical -> physical; noncompressible RAW is success.
3. **Files/artifacts created or modified:** `v1/src/utils/pack.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/pack contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `pack`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.07 - Utility `unpack`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (unpack)
2. **Exact implementation work:** Invoke SYS_UNPACK; materialize exact logical RAW bytes atomically.
3. **Files/artifacts created or modified:** `v1/src/utils/unpack.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/unpack contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `unpack`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.08 - Utility `grep`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (grep)
2. **Exact implementation work:** Literal case-sensitive substring only; no regex/wildcards; stream stdin or one named object.
3. **Files/artifacts created or modified:** `v1/src/utils/grep.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/grep contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `grep`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.09 - Utility `wc`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (wc)
2. **Exact implementation work:** Count bytes, words, lines on stream.
3. **Files/artifacts created or modified:** `v1/src/utils/wc.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/wc contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `wc`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.10 - Utility `head`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (head)
2. **Exact implementation work:** Implement exact bounded Section-33 head semantics. `head [n]` defaults to 10 text lines; explicit decimal n is 1..255 only.
3. **Files/artifacts created or modified:** `v1/src/utils/head.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/head contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `head`; shell survives and `$?` is exact. n=0, n=256, malformed decimal, or excess arity must fail exactly and never be silently clamped.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.11 - Utility `tail`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (tail)
2. **Exact implementation work:** Implement exact bounded Section-33 tail semantics without assuming random cassette access. `tail [n]` defaults to 10 text lines; explicit decimal n is 1..255 only.
3. **Files/artifacts created or modified:** `v1/src/utils/tail.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/tail contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `tail`; shell survives and `$?` is exact. n=0, n=256, malformed decimal, or excess arity must fail exactly and never be silently clamped.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.12 - Utility `cmp`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (cmp)
2. **Exact implementation work:** Bytewise comparison with exact status convention and streaming behavior. `cmp a b` compares exactly two RAM objects byte-for-byte and returns status 0 only when logical byte streams are identical.
3. **Files/artifacts created or modified:** `v1/src/utils/cmp.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/cmp contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `cmp`; shell survives and `$?` is exact. Different bytes/lengths return nonzero; missing/excess operands or non-RAM/non-openable inputs follow the documented error path without mutation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.13 - Utility `true`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (true)
2. **Exact implementation work:** Return exact process status 0 and emit no output bytes.
3. **Files/artifacts created or modified:** `v1/src/utils/true.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/true contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `true`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.14 - Utility `false`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (false)
2. **Exact implementation work:** Return exact process status 1 and emit no output bytes.
3. **Files/artifacts created or modified:** `v1/src/utils/false.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/false contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `false`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.15 - Utility `sleep`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (sleep)
2. **Exact implementation work:** Use SYS_SLEEP; parse only documented operand form and remain cooperative. `sleep seconds` accepts exactly one unsigned decimal value 0..65535 and sleeps cooperatively using kernel ticks.
3. **Files/artifacts created or modified:** `v1/src/utils/sleep.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/sleep contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `sleep`; shell survives and `$?` is exact. Negative, 65536, malformed decimal, or excess arity must be rejected without an accidental wrapped sleep interval.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.16 - Utility `which`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (which)
2. **Exact implementation work:** Resolve external command using shell PATH/exact case only; do not report builtins as external. Use exactly the shell external PATH algorithm: report only BIN results, skip nonexistent/non-directory/overlength/wrong-type candidates, never move tape, and print nothing/return status 1 for builtin-only names.
3. **Files/artifacts created or modified:** `v1/src/utils/which.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/which contract; no case folding. `which ls` can report the exact external path; builtin-only name emits no bytes and status 1; catalog-only lookup does not move cassette.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `which`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.17 - Utility `env`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (env)
2. **Exact implementation work:** Print child/session environment with exact case and ordering rules defined by Section20/33. `env` prints the current case-sensitive environment exactly one `NAME=VALUE` entry per line.
3. **Files/artifacts created or modified:** `v1/src/utils/env.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/env contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `env`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.18 - Utility `hexdump`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (hexdump)
2. **Exact implementation work:** Compact hexadecimal/ASCII streaming view.
3. **Files/artifacts created or modified:** `v1/src/utils/hexdump.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/hexdump contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `hexdump`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.19 - Built-in `ps` Phase-8 regression

1. **Purpose / REV11 requirement:** §§20.4,33,54 (ps)
2. **Exact implementation work:** Close the Phase-8 `ps` behavior by regression-testing the parent-shell builtin already delivered in P6.13; do not create a `/bin/ps` MEX1, BCAT entry, or extra `src/utils/ps.asm`. Print PID, state, memory, and exact process name from `SYS_PROC_INFO`/PROC_INFO using the Section-33 behavior while retaining exact lower-case builtin lookup and transactional builtin redirection semantics.
3. **Files/artifacts created or modified:** `v1/src/shell/sh.asm`; shell builtin tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable; assert `ps` remains a Section-20.4 builtin and is absent from BCAT/the external-command source list.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Builtin behavior and exit status match exact REV11 Section-33/ps contract; no case folding; no external `/bin/ps` object or BCAT slot exists.
9. **Negative/failure test:** Make `ps` resolve as an external command/BCAT name, add an unlisted `src/utils/ps.asm`, or inject a process-info/type/case error; require failure while the shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.20 - Built-in `mem` Phase-8 regression

1. **Purpose / REV11 requirement:** §§20.4,33,54 (mem)
2. **Exact implementation work:** Close the Phase-8 `mem` behavior by regression-testing the parent-shell builtin already delivered in P6.13; do not create a `/bin/mem` MEX1, BCAT entry, or extra `src/utils/mem.asm`. Print combined plus FAST/CONTENDED free totals/largest spans and the required process/object/pipe/pinned usage; `mem -c` reports the exact ZPINFO1 logical/physical/savings/counters, all through the builtin and the certified memory/zxpack syscalls.
3. **Files/artifacts created or modified:** `v1/src/shell/sh.asm`; shell builtin tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable; assert `mem` remains a Section-20.4 builtin and is absent from BCAT/the external-command source list.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Builtin behavior and exit status match exact REV11 Section-33/mem contract including `-c`; no case folding; no external `/bin/mem` object or BCAT slot exists.
9. **Negative/failure test:** Make `mem` resolve as an external command/BCAT name, add an unlisted `src/utils/mem.asm`, or inject an accounting/type/case error; require failure while the shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.21 - Utility `udg`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (udg)
2. **Exact implementation work:** Implement the exact four Section-33/16.5 forms: `udg list` lists slots 0..31; `udg show n` displays exactly one valid slot; `udg save name` creates or transactionally replaces a mutable RAM UDG object containing UDG1 base=0,count=32 and never moves cassette; `udg load path` reads a RAM UDG object (RAW or transparently PACKED), validates the complete UDG1 base/count/length before any live-bank write, then atomically replaces exactly the encoded slots. Cassette persistence remains only through explicit shell `save`/`load`.
3. **Files/artifacts created or modified:** `v1/src/utils/udg.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/udg contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `udg`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.22 - Utility `gfxdemo`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (gfxdemo)
2. **Exact implementation work:** Exercise OS graphics APIs as an ordinary lower-case external executable.
3. **Files/artifacts created or modified:** `v1/src/utils/gfxdemo.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/gfxdemo contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `gfxdemo`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.23 - Utility `stty`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (stty)
2. **Exact implementation work:** Implement only the REV11 §13.5 forms `stty`, `stty cols 64`, `stty cols 32`, `stty cursor block`, `stty cursor underline`, and `stty cursor off`. In the default tty64 shell state used by the definitive §63 demonstration, no-argument `stty` prints exactly `cols 64 rows 24 cursor underline`; setters change only the specified tty mode/cursor control.
3. **Files/artifacts created or modified:** `v1/src/utils/stty.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/stty contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `stty`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.24 - Utility `date`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (date)
2. **Exact implementation work:** Cold unset behavior; display/set exact supported 1970..2099 wall clock; `date -s` syntax per Section20.8. `date` reads exact TIME1; unset prints exactly `date: not set`. `date -s "YYYY-MM-DD hh:mm:ss"` validates Gregorian 1970..2099, calls SYS_TIME_SET, and every successful set increments the 16-bit revision and resets subsecond accumulation. Display is exactly `YYYY-MM-DD hh:mm:ss`.
3. **Files/artifacts created or modified:** `v1/src/utils/date.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/date contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `date`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.25 - Utility `cron`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (cron)
2. **Exact implementation work:** Implement `cron` as a tiny cooperative user daemon, never a kernel scheduler feature. It consumes one normal process slot only while active rules exist or the user explicitly starts it. Parse `/etc/crontab` only as CFG with maximum logical length exactly 2048 bytes, maximum 127 bytes per physical LF-terminated line, and at most 8 active non-comment entries. Calendar fields are exactly one decimal value or `*`: minute 0..59, hour 0..23, day 1..31, month 1..12, weekday 0..6 with Sunday=0; all five fields use AND semantics and invalid date combinations simply do not match. Accept `@boot`, `@hourly`, and `@daily`; `@hourly` matches minute 00, `@daily` matches 00:00, both require valid TIME1 and share the once-per-`(wall-minute,revision)` rule, while `@boot` runs once per daemon instance. Cron command text uses the shell simple-command quote/backslash plus `$NAME`/`$?` expansion subset but rejects shell operators, redirection, pipelines, background `&`, assignments and shell builtins; resolve exactly one external MEX1 through inherited PATH/cwd/environment, with `/dev/null` stdin, `/dev/tty` stdout/stderr and ALLOW_TAPE=0 so unattended cron never moves cassette. Jobs execute serially in crontab file order; the daemon spawns and waits/reaps each matching job before the next, deliberately performs no catch-up, and its private `$?` starts at 0 then becomes the preceding spawn/job status. Sleep exactly 50 ticks between evaluations. Before every evaluation open, fully read, validate and close `/etc/crontab`; never hold it open across sleep or spawn, so atomic `crontab -e` replacement is observed at the next poll without a reload signal. If the valid configuration has no active entries, close/remove the lock and exit; after all applicable `@boot` rules run, an @boot/comment/blank-only file likewise exits because no future schedule remains. Calendar/@hourly/@daily require valid TIME1; adding an @boot line to an already-running daemon is not retroactive. P8.39 owns the exact lock and TIME1 revision/dedupe transaction.
3. **Files/artifacts created or modified:** `v1/src/utils/cron.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.25`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary corpus proves 2048-byte CFG accepted and 2049 rejected; 127-byte LF-terminated line accepted and 128 rejected; exactly 8 active entries accepted and a ninth rejected; calendar ranges/AND semantics and @boot/@hourly/@daily timing are exact. The daemon sleeps 50 ticks, reopens/fully reads/validates/closes the CFG every poll, runs jobs serially with private `$?`, never prompts for tape, observes atomic replacement on the next poll, and exits after no-active or exhausted @boot-only configurations.
9. **Negative/failure test:** Any 2049-byte file, >127-byte physical line, ninth active entry, invalid calendar field accepted as runnable, OR semantics, interactive cassette motion, builtin/operator/redirection/background command acceptance, concurrent job launch, catch-up, config handle retained across sleep/spawn, polling cadence other than 50 ticks, failure to observe replacement, or daemon remaining resident with no future schedule is a deterministic failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.25.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.26 - Utility `crontab`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (crontab)
2. **Exact implementation work:** Implement `crontab -l` and `crontab -e` for the exact `/etc/crontab` CFG contract. `-e` creates an exclusive `/tmp/.ct<pid>.<n>` for decimal n=0..9, copies the current logical CFG bytes, invokes vi as a foreground interactive child, and validates the complete edited file before commit: logical length <=2048 bytes, every physical LF-terminated line <=127 bytes, at most 8 active non-comment entries, and every calendar/@boot/@hourly/@daily command obeys the P8.25 grammar/bounds. Close the temporary and atomically SYS_RENAME it to `/etc/crontab`; invalid edits, editor failure, load failure, or tape-consent refusal leave the live CFG byte-identical. If `/bin/vi` is TAPE_BACKED, use the same explicit interactive consent/ALLOW_TAPE path as sh. After a valid nonempty replacement, start `cron` only when future active work exists; if `/bin/cron` is TAPE_BACKED ask the interactive user before ALLOW_TAPE and let the lock reject duplicates. If the replacement has no active entries, do not start a daemon; an existing daemon observes that state at its next 50-tick poll and exits. A valid file containing only already-consumed @boot/comment/blank entries likewise has no future schedule for the running daemon.
3. **Files/artifacts created or modified:** `v1/src/utils/crontab.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.26`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** `-l` reproduces the live CFG logically; `-e` commits only a fully validated <=2048-byte, <=127-byte-per-line, <=8-active-entry file through close+atomic rename. Boundary edits and real/fixture vi paths preserve exact bytes on failure; a future-active edit can start one cron instance with explicit tape consent when needed, while empty/no-active edits start none and are observed by an existing daemon at its next poll.
9. **Negative/failure test:** Oversize CFG/line, ninth active entry, malformed schedule/command, temp collision mishandling, editor/load/validation failure, declined tape consent, commit before close/validation, auto-start on no-active configuration, duplicate daemon bypass, or any mutation of the prior live CFG on failure must fail deterministically.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.26.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.27 - Utility `man`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (man)
2. **Exact implementation work:** With or without a topic, print at least the exact lines `Manuals: https://supratim-sanyal.blogspot.com/` and `Search for ZXUS`; an optional topic may only add a suggested search term. Do not implement a local man-page loader.
3. **Files/artifacts created or modified:** `v1/src/utils/man.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.27`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/man contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `man`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.27.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.28 - Utility `cal`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (cal)
2. **Exact implementation work:** No args requires valid wall time or prints `cal: date not set`; explicit month/year works independently in 1970..2099. Implement exact arity: `cal`, `cal month`, or `cal month year` only. No/one argument requires valid wall time; two arguments require month 1..12 and year 1970..2099 without requiring wall time; other arity/ranges E_INVAL.
3. **Files/artifacts created or modified:** `v1/src/utils/cal.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.28`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/cal contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `cal`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.28.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.29 - Utility `uptime`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (uptime)
2. **Exact implementation work:** Format 32-bit frame counter modulo 2^32; works while date unset.
3. **Files/artifacts created or modified:** `v1/src/utils/uptime.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.29`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/uptime contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `uptime`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.29.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.30 - Utility `whoami`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (whoami)
2. **Exact implementation work:** Print current USER value exactly as mutable environment defines it.
3. **Files/artifacts created or modified:** `v1/src/utils/whoami.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.30`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/whoami contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `whoami`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.30.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.31 - Utility `uname`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (uname)
2. **Exact implementation work:** Print exact ZX-UX identity defined by Section33. Output is byte-frozen as exact ASCII `ZX-UX z80 48k` followed by LF.
3. **Files/artifacts created or modified:** `v1/src/utils/uname.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.31`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/uname contract; no case folding. Output bytes are exactly ASCII `ZX-UX z80 48k` followed by one LF byte (0x0A), with no legacy `ZX48-UX` spelling.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `uname`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.31.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.32 - Utility `fortune`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (fortune)
2. **Exact implementation work:** Print bounded built-in short fortune behavior from Section33. `fortune` selects only from its fixed small bundled table using non-security session entropy; no correctness, identity, or security decision depends on R or the selected line.
3. **Files/artifacts created or modified:** `v1/src/utils/fortune.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.32`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/fortune contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `fortune`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.32.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.33 - Utility `banner`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (banner)
2. **Exact implementation work:** Implement required `banner text` behavior as an 8x8-style large bitmap banner rendered through the shared display/graphics rules without writing outside screen bounds.
3. **Files/artifacts created or modified:** `v1/src/utils/banner.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.33`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/banner contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `banner`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.33.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.34 - Utility `rev`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (rev)
2. **Exact implementation work:** Reverse bytes within each input line, preserve line boundaries/LF behavior, stream stdin to stdout, and compose correctly in pipelines without whole-input buffering.
3. **Files/artifacts created or modified:** `v1/src/utils/rev.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.34`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/rev contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `rev`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.34.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.35 - Utility `yes`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (yes)
2. **Exact implementation work:** Repeat zero/one argument until cooperative cancellation; clean BREAK status. Accept zero or one argument only; zero means literal `y`. Emit text+LF repeatedly until cancellation/write failure; >1 argument returns E_INVAL before output. `yes` yields at least once per output line so cooperative cancellation/write failure remains responsive.
3. **Files/artifacts created or modified:** `v1/src/utils/yes.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.35`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/yes contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `yes`; shell survives and `$?` is exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.35.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.36 - Utility `demo`

1. **Purpose / REV11 requirement:** §§20.5,33,54 (demo)
2. **Exact implementation work:** Discover/run shipped demo pairs using exact lower-case names; Phase8 uses contract-valid demo fixtures, final pairs close Phase12. With no argument, `demo` prints each shipped lower-case executable and matching source filename. With one exact lower-case name it ensures the matching source and precompiled executable are resident in `/home/<user>`, using normal interactive forward cassette loading only for missing members. Existing expected-type members are preserved (including user edits); an existing wrong-type member refuses instead of being overwritten. Only missing pair members are loaded, the executable is then spawned/waited, and the command invites the documented `vi`/`cc`/`ld` edit-rebuild workflow.
3. **Files/artifacts created or modified:** `v1/src/utils/demo.asm`; utility tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.36`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Behavior and exit status match exact REV11 Section-33/demo contract; no case folding.
9. **Negative/failure test:** Inject I/O/allocation/type/case error appropriate to `demo`; shell survives and `$?` is exact. Wrong-case demo name, wrong-type resident pair member, declined/failed tape load, or one invalid pair member must not run the demo or overwrite the existing pair member.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.36.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.37 - External echo regression

1. **Purpose / REV11 requirement:** §54 acceptance
2. **Exact implementation work:** Regression-test the final Phase6 `/bin/echo` alongside utilities; it remains external and pipelineable.
3. **Files/artifacts created or modified:** utils/echo.asm; utility suite
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.37`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** No parent-shell echo alias; output/status exact.
9. **Negative/failure test:** Replace echo with builtin in negative manifest and require policy failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.37.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.38 - Utility pipeline/error propagation matrix

1. **Purpose / REV11 requirement:** §54 acceptance
2. **Exact implementation work:** Compose utilities over bounded pipes and verify every utility propagates read/write/allocation errors through process status.
3. **Files/artifacts created or modified:** tests/emulator/utils_pipe.py
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.38`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Multi-stage bytes and statuses are exact; bounded pipelines terminate without deadlock; E_PIPE/read/write/allocation failures propagate through utility exit status.
9. **Negative/failure test:** Inject ignored E_PIPE, ignored downstream write error, swallowed read/allocation failure, or a deadlock; the harness must fail or hit its hard timeout deterministically.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.38.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.39 - Cron lock and TIME1 dedupe transaction

1. **Purpose / REV11 requirement:** §20.9, §41.7; invariants 105/109/119
2. **Exact implementation work:** Implement `/tmp/.cron.lock` as DAT with committed payload exactly two bytes: ASCII owning PID digit `2`..`7` plus LF. Startup creates O_WRITE|O_CREATE|O_EXCL, writes/closes, then reopens O_READ for daemon lifetime. E_EXIST contender validates a live non-ZOMBIE process named exactly `cron` -> E_BUSY; otherwise closes/removes stale lock and retries exclusive creation once. Calendar/@hourly/@daily evaluation key is exactly `(wall-minute,TIME1.revision)` and fires at most once per key; any successful `date -s` revision change clears dedupe and evaluates only the newly observed current minute, with no catch-up.
3. **Files/artifacts created or modified:** `v1/src/utils/cron.asm`; `v1/src/kernel/interrupt.asm`; `v1/src/kernel/syscall.asm`; cron tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.39`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Lock is exactly PID+LF; valid live owner rejects duplicate; stale invalid data heals safely; no duplicate per key and no catch-up after clock set or long blocking interval.
9. **Negative/failure test:** Malformed lock length/content treated as live, deleting an unknown live lock by name, duplicate firing in one key, or catch-up firing are failures.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.39.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P8.40 - Phase-8 acceptance gate

1. **Purpose / REV11 requirement:** §54 acceptance
2. **Exact implementation work:** Run every Section-54 command in its architecture-defined form: external utility binaries for the Section-20.5 names, the exact final external pipeline `echo hello | wc` using the shipped `/bin/echo` and final `/bin/wc` (retain exact output bytes and both process statuses), and the parent-shell `ps`/`mem` builtin regressions, plus the contract-valid demo fixture and contract-valid crontab editor-fixture transaction/validation tests. `ps` and `mem` must remain builtins and must not consume BCAT entries or unlisted utility source files.
3. **Files/artifacts created or modified:** Phase8 evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P8.40`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every required lower-case Phase-8 command is present in its architecture-defined builtin/external form; `ps`/`mem` remain builtins, the 40-entry external-command/BCAT set is unchanged, `echo hello | wc` proves final external `/bin/echo` -> `/bin/wc` stdin/stdout composition with exact output/status, utility errors propagate through shell exit status, and the contract-valid demo fixture plus crontab editor fixture both pass.
9. **Negative/failure test:** Remove one required command; replace the required `echo hello | wc` with a fixture/non-final consumer; swallow a utility error status; move `ps` or `mem` into BCAT/external utility space; add an unlisted target source module; break the demo/editor fixture contracts; or introduce any BCAT/name/type mismatch. The Phase-8 aggregate must fail before check-in.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P8.40.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 9 - vi Editor

## P9.01 - vi MEX1 skeleton and tty mode save/restore

1. **Purpose / REV11 requirement:** §22, §55
2. **Exact implementation work:** Create native vi as a transient MEX1. On entry record the current tty mode and cursor setting, request tty64, and establish the documented editor cursor contract. On every normal exit and every error/cancellation unwind, restore the exact prior tty mode, cursor shape and visibility; vi must never leave the shell in an editor-specific terminal state.
3. **Files/artifacts created or modified:** tools/vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Entry forces tty64 only after saving prior state; normal exit, forced error and cancellation each restore the exact previous mode/shape/visibility.
9. **Negative/failure test:** Any exit/error path that leaves tty64 or an editor cursor shape active when it was not the prior shell state fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.02 - Buffer load/type validation

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Open only documented C/ASM/TXT/CFG editable object types; close source handle after complete load.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Valid types byte-exact; handle count returns baseline. After load, the source input handle is closed before the first edit is accepted; handle/open-description counts return to the expected baseline.
9. **Negative/failure test:** BIN/wrong type rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.03 - Gap buffer and compact line index

1. **Purpose / REV11 requirement:** §22.6
2. **Exact implementation work:** Implement the required `gap buffer + compact line-offset/index support`. Do not retain a complete duplicate file for undo; the one-level undo record stores only information needed to reverse the most recent supported edit. Source lines are LF-delimited logical lines; buffer/index updates are allocation-failure atomic.
3. **Files/artifacts created or modified:** `v1/src/tools/vi.asm`; vi buffer tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Buffer bytes/index remain coherent after every edit; undo never requires a full second file image; failed growth preserves the last valid text.
9. **Negative/failure test:** Force gap growth/index allocation failure at each update boundary; previous buffer/index/dirty state must remain valid and byte-identical.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.04 - Unnamed/new buffer state

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Support `vi` without path and exact dirty/name state. Invocation is exactly `vi` (new unnamed empty TXT buffer) or `vi path` (one existing TXT/C/ASM/CFG object). More than one path returns E_INVAL. Unnamed buffer gains a target only after successful `:w path`; failed writes do not retarget it.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Insert creates dirty unnamed buffer.
9. **Negative/failure test:** Unnamed :w/:wq => E_NOENT and `vi: no file name`. Two paths E_INVAL; unnamed :w/:wq without path gives exact no-file-name refusal; failed `:w path` leaves buffer unnamed and dirty.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.05 - Normal/insert/command-line mode state machine

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Implement exactly three unambiguous modes: normal, insert and command-line. Normal mode uses a block cursor. Insert mode uses an underline cursor and displays the exact literal `-- INSERT --` on tty row 23 (the status/command line). `:` command-line mode uses an underline cursor. Mode transitions update the cursor/status atomically with the console cursor-removal/redraw discipline; leaving insert removes the exact indicator without altering buffer bytes.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden mode transitions prove normal=block, insert=underline plus exact `-- INSERT --` on row 23, command-line=underline, and status cleanup on return to normal; cursor/state survive viewport redraws.
9. **Negative/failure test:** Any fourth/ambiguous mode, wrong cursor shape, altered/missing insert literal, indicator outside row 23, stale indicator after leaving insert, or invalid command that mutates the buffer/status contract fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.06 - h j k l 0 $ movement

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Implement required motions within lines/file.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary cursor positions exact.
9. **Negative/failure test:** No under/overflow.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.07 - w b e word motions

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Implement documented word semantics.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden ASCII text positions.
9. **Negative/failure test:** End/begin edges stable.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.08 - gg and G case-sensitive motions

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Implement `gg` and `G` distinct semantics.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** g/G golden.
9. **Negative/failure test:** Single g unsupported/no wrong G alias.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.09 - i a insert commands

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Insert before/after cursor with allocation-safe growth.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Buffer bytes exact.
9. **Negative/failure test:** Growth failure leaves source intact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.10 - o O open-line commands

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Implement below/above exact case-sensitive semantics.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** o/O golden bytes/cursor.
9. **Negative/failure test:** Allocation failure atomic.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.11 - x dd D deletions

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Implement char/line/to-end delete and yank buffer effects.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden edits.
9. **Negative/failure test:** Delete at empty/end safe.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.12 - yy p P yank/put

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** One yank buffer; p/P distinct put location semantics.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** p/P golden.
9. **Negative/failure test:** Memory failure no partial insert.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.13 - r J replacement/join

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Implement one-char replace and line join.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden.
9. **Negative/failure test:** Missing replacement char/no next line safe.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.14 - One-level undo

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Maintain exactly required one-level undo with bounded memory behavior.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Each edit then u restores prior bytes/state.
9. **Negative/failure test:** Second unsupported history not invented.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.15 - Literal /text search and n/N repeat

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Implement required forward literal `/text` search; `n` repeats in the same direction and `N` repeats in the opposite direction. Search is case-sensitive. No `?` reverse-search command is invented for version 1.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Cursor/search state matches the exact required `/text`, n and N semantics; unsupported `?` is not accepted as a hidden vi extension.
9. **Negative/failure test:** Not-found leaves state per contract; a test expecting `?` reverse-search support must fail because it is outside the version-1 required subset.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.16 - Ex :e and :r

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Exact edit/read semantics, dirty checks, case-sensitive lookup and buffer transaction.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** `:e hello.c` distinct from HELLO.C; :r inserts exact bytes.
9. **Negative/failure test:** Failed load leaves current buffer intact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.17 - Transactional :w

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Create unique O_CREATE|O_EXCL `/tmp/.vi<pid>.<n>`, write complete, close, atomic SYS_RENAME; retry collisions safely.  The transaction name search is exactly `/tmp/.vi<pid>.<n>` with decimal n=0..9. Use O_WRITE|O_CREATE|O_EXCL, retry only E_EXIST, and remove only a temporary this vi process successfully created exclusively; never delete an unknown collision. Preserve the existing destination type. For a new destination request C only for an exact lower-case `.c` suffix, ASM only for exact lower-case `.asm`, and TXT for every other editable new name; the kernel performs no suffix inference. Write and close the complete replacement before atomic SYS_RENAME; every pre-rename failure leaves the prior destination byte-identical.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Destination replaced atomically; prior bytes unchanged on forced write/rename failure.  Force collisions at n=0..8 and prove n=9 succeeds; force all ten E_EXIST and require controlled failure with every unknown temp untouched. Test existing C/ASM/TXT/CFG type preservation and new `.c`/`.asm`/other explicit type selection.
9. **Negative/failure test:** Collision never clobbers unknown temp.  Retry an error other than E_EXIST, delete an unknown colliding temp, infer type in the kernel, clear/replace destination before complete close, or alter prior bytes on write/rename failure; each is a hard failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.18 - :w path, :wq and retarget rules

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Implement exact destination/dirty/retarget/quit semantics.  Freeze dirty/retarget semantics literally: `:w` writes the current target; unnamed `:w` and `:wq` without a path return E_NOENT and print exactly `vi: no file name` with buffer/dirty state unchanged. `:w path` changes the current target only after its transaction commits successfully. Any successful write clears dirty. `:wq` exits only after successful `:w`; any save failure leaves vi running with the dirty buffer. `:e path` refuses while dirty and otherwise replaces buffer/current target only after the new object fully loads; `:r path` inserts bytes, marks dirty, and never retargets.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden named/renamed write flows.  Exercise named/unnamed `:w`, `:w path`, `:wq`, clean/dirty `:e`, and `:r` with forced load/write/rename failures; assert current-target identity, dirty flag, buffer bytes, exit state and exact no-file-name message after every branch.
9. **Negative/failure test:** Failed write must not clear dirty or quit.  A failed write that retargets/clears dirty/exits, dirty `:e` that replaces the buffer, `:r` that changes current target, or unnamed write that creates an implicit name fails state-machine assertions.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.19 - :q and :q!

1. **Purpose / REV11 requirement:** §22
2. **Exact implementation work:** Exact dirty refusal vs forced quit.
3. **Files/artifacts created or modified:** vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Dirty :q stays; :q! exits/restores tty.
9. **Negative/failure test:** No silent data loss on :q.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.20 - Real crontab -e integration

1. **Purpose / REV11 requirement:** §20.9, §55 acceptance
2. **Exact implementation work:** Replace Phase8 editor fixture with actual /bin/vi; explicit consent for tape-backed vi if needed; commit only validated CFG.
3. **Files/artifacts created or modified:** crontab.asm; vi.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Edit valid crontab commits; invalid returns to editor/does not replace.
9. **Negative/failure test:** Declined tape consent does not move tape.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.21 - :set, :set number and :set nonumber

1. **Purpose / REV11 requirement:** §22.5, §22.6A
2. **Exact implementation work:** Implement the required command-line forms exactly. `:set` reports supported editor options; `:set number` enables a fixed five-column line-number gutter and `:set nonumber` disables it. Viewport state is not file content.
3. **Files/artifacts created or modified:** `v1/src/tools/vi.asm`; vi option tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Option state and five-column gutter are exact; without numbering all 64 columns are available; with numbering visible text width is reduced by exactly five columns.
9. **Negative/failure test:** Unknown option or malformed :set form must not mutate buffer or persistent file bytes.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.22 - tty64 viewport and column-63 safety

1. **Purpose / REV11 requirement:** §22.6A, §41.8
2. **Exact implementation work:** Use tty row 23 for status/command and rows 0..22 for editing. Lines are not soft-wrapped; horizontal offset follows the cursor. TAB 0x09 displays to the next multiple-of-8 logical column but remains stored as 0x09. Every render/edit/search path must prove no write occurs beyond tty64 logical column 63.
3. **Files/artifacts created or modified:** `v1/src/tools/vi.asm`; tty64 vi viewport tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Logical editing is independent of visible slice; canaries remain intact and no vi terminal write addresses a logical column >63.
9. **Negative/failure test:** Instrument a test build to attempt column 64 from one viewport path; harness must detect/reject the out-of-contract write.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.23 - Freeze vi user/developer documentation

1. **Purpose / REV11 requirement:** §22, including §§22.7-22.8, and §55
2. **Exact implementation work:** Create `v1/docs/vi.md` before closing Phase 9. Document invocation arity, tty64/cursor behavior, normal/insert/command-line modes, every required movement/edit/search/ex command, exact case sensitivity, gap-buffer/one-level-undo model, transactional `:w`, dirty/retarget rules, viewport/TAB/line-number behavior, and memory-pressure behavior. Freeze §22.7 explicitly: `:udg` is deferred from the required version-1 vi subset, while UDG resources remain available through the graphics APIs and `udg` utility. Freeze §22.8 explicitly: version 1 defers syntax highlighting, multiple open buffers, split windows, visual mode, named register collections, macros/recording, full regular-expression substitution, and persistent undo/swap files. A line-oriented bootstrap editor may exist temporarily during development, but it is not the version-1 shipped editor and must not replace the `vi` acceptance gate. The document must describe only behavior already proved by P9.01-P9.22.
3. **Files/artifacts created or modified:** `v1/docs/vi.md`; Phase-9 documentation consistency test
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** `docs/vi.md` contains every required REV11 vi contract with no invented command or stronger claim than the tests prove; it names `:udg` as deferred, lists all eight §22.8 deferred feature families exactly, and states that any temporary line-oriented bootstrap editor is not the shipped editor and cannot replace the `vi` acceptance gate.
9. **Negative/failure test:** In separate negative fixture copies, delete one required command/dirty-state rule; omit the §22.7 `:udg` deferral; omit any one of the eight §22.8 deferred feature families; weaken/remove the bootstrap-editor restriction; or add an unsupported command such as `?`. Each mutation must make the documentation consistency test fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P9.24 - Phase-9 acceptance/size gate

1. **Purpose / REV11 requirement:** §55 acceptance, §44
2. **Exact implementation work:** Create/edit/save/reload hello.c; case-sensitive p/P,o/O,n/N,g/G; failed growth/write rollback; ex commands; crontab -e; vi <=8192 or measured approved exception.
3. **Files/artifacts created or modified:** Phase9 evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P9.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every Phase9 bullet PASS.
9. **Negative/failure test:** Any prior-destination hash change on failed transaction blocks phase.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P9.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 10 - Native Assembler and Linker

## P10.01 - OBJ1 exact 24-byte header

1. **Purpose / REV11 requirement:** §23, §56
2. **Exact implementation work:** Freeze the exact 24-byte OBJ1 header: magic OBJ1; version=1; flags=0; header_size=24; text_size; bss_size; symbol_count; relocation_count; symbol_table_offset=24+text_size; relocation_table_offset=symbol_table_offset+symbol_count*20; body CRC-16/CCITT-FALSE; header CRC with bytes22..23 zero. The body CRC covers every stored byte after the 24-byte header—text/data bytes, every symbol record, and every relocation record—so symbol/relocation corruption cannot pass merely because text bytes are unchanged. Validate total length=relocation_offset+relocation_count*6, text+bss<=32768, total<=32768, no trailing bytes, and all arithmetic widened before narrowing.
3. **Files/artifacts created or modified:** obj1.inc; obj1.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Host inspector goldens/malformed.
9. **Negative/failure test:** nonzero reloc with text_size<2 E_FORMAT.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.02 - OBJ1 symbol record

1. **Purpose / REV11 requirement:** §23
2. **Exact implementation work:** Implement exact 20-byte symbol record: bytes0..15 NUL-padded name with 1..15 visible bytes and zero padding; value u16; section 0 UNDEF, 1 TEXT, 2 BSS, 3 ABS; flags bit0 GLOBAL only and all remaining flag bits zero. Enforce names unique within the module; assembly-visible names use exactly `[A-Za-z_.$][A-Za-z0-9_.$]*`; C48-generated external names use the C48 identifier subset; embedded NUL followed by any nonzero tail byte is E_FORMAT; silent truncation is forbidden. UNDEF symbols have value 0 and must be GLOBAL; TEXT values are <= text_size; BSS values are <= bss_size; ABS values may use any 16-bit value.
3. **Files/artifacts created or modified:** as.asm; obj1.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Boundary names/duplicate resolution plus exact assembly-name grammar, C48-external-name subset, section/value/flag rules, and NUL/zero-padding checks.
9. **Negative/failure test:** Overlength/empty/illegal-character name, embedded-NUL/nonzero tail, non-GLOBAL UNDEF, nonzero UNDEF value, invalid section/flag bits, and out-of-range TEXT/BSS values are rejected; no silent truncation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.03 - OBJ1 relocation record

1. **Purpose / REV11 requirement:** §23
2. **Exact implementation work:** Implement exact 6-byte relocation record: word offset u16, symbol index u16, type=ABS16(1), reserved=0. The stored word is signed i16 addend. Enforce nonzero relocation_count => text_size>=2; offsets <=text_size-2, strictly increasing/non-overlapping by at least 2; symbol index in range; widened symbol+signed-addend result 0..65535. OBJ1 count multiplication and offset/length additions use widened arithmetic and adversarial 16-bit-wrap vectors are mandatory.
3. **Files/artifacts created or modified:** as.asm; obj1.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Golden offsets/symbol refs/addends.
9. **Negative/failure test:** Overrun/unsorted invalid.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.04 - Host OBJ1 inspector

1. **Purpose / REV11 requirement:** §56
2. **Exact implementation work:** Independent deterministic structural decoder for assembler/linker tests.
3. **Files/artifacts created or modified:** tools-host/inspect-obj/
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Positive/malformed corpus.
9. **Negative/failure test:** One-bit mutation rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.05 - Assembler lexer/line parser

1. **Purpose / REV11 requirement:** §23
2. **Exact implementation work:** Native target parser for labels, comments, and documented tokens only. Source inclusion is explicitly deferred from the version-1 assembler: no INCLUDE/source-inclusion directive is accepted; required modules are assembled independently and linked through OBJ1.
3. **Files/artifacts created or modified:** tools/as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden source lines parse exactly; independent modules assemble/link through OBJ1 without source inclusion.
9. **Negative/failure test:** Malformed token or any source-inclusion/INCLUDE directive reports failure without output mutation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.06 - Assembler labels and EQU

1. **Purpose / REV11 requirement:** §23
2. **Exact implementation work:** Case-sensitive symbols and EQU expressions.
3. **Files/artifacts created or modified:** as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Forward/known rules exact.
9. **Negative/failure test:** Duplicate symbol error.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.07 - DB DW DS directives

1. **Purpose / REV11 requirement:** §23
2. **Exact implementation work:** Emit exact bytes/words/reserved space.
3. **Files/artifacts created or modified:** as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden object text/data.
9. **Negative/failure test:** Negative/overflow size rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.08 - Assembler expressions

1. **Purpose / REV11 requirement:** §23
2. **Exact implementation work:** Implement + - * / % & | ^ << >> unary - ~ parentheses with exact precedence/range.
3. **Files/artifacts created or modified:** as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden expression corpus.
9. **Negative/failure test:** Divide by zero/overflow policy exact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.09 - global/export and extern/import

1. **Purpose / REV11 requirement:** §23
2. **Exact implementation work:** Emit symbol binding records for multi-module link.
3. **Files/artifacts created or modified:** as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Two-module reference resolves later.
9. **Negative/failure test:** Undefined local/reference reported.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.10 - Assembler required-opcode/addressing inventory

1. **Purpose / REV11 requirement:** §23, §38
2. **Exact implementation work:** Before encoding instructions, scan every target Z80 source delivered through Phase 10 and freeze a machine-readable inventory of every documented mnemonic/addressing form actually required by ZX-UX. Add architecture-mandated forms used by the ABI/tests even if a current source optimization has not emitted them yet. The inventory is coverage authority for native `as`; undocumented opcodes are excluded from the portable baseline.
3. **Files/artifacts created or modified:** tools/as.asm; tests/compiler/as-opcode-inventory; docs/assembler.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Independent host scan lists every source mnemonic/form and proves every entry has at least one positive encoding vector plus relevant range/error vectors.
9. **Negative/failure test:** Remove one used addressing form from the inventory or add an undocumented form and require coverage/policy failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.11 - Assembler load/store encoder

1. **Purpose / REV11 requirement:** §23, §38
2. **Exact implementation work:** Encode all inventoried documented 8-bit and 16-bit LD forms, immediate/register/(HL)/(BC)/(DE)/(nn), accumulator memory forms, and required IX/IY indexed displacement forms. Symbolic absolute 16-bit operands emit the correct OBJ1 ABS16 relocation/addend when not assembly-time absolute.
3. **Files/artifacts created or modified:** tools/as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** For every inventoried LD form, native `as` bytes/relocations equal certified SjASMPlus output plus independent OBJ1 inspection.
9. **Negative/failure test:** Reject illegal register combinations, displacement outside -128..127, immediate overflow, and unsupported/undocumented prefix forms without committing output.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.12 - Assembler arithmetic/logical encoder

1. **Purpose / REV11 requirement:** §23, §38
2. **Exact implementation work:** Encode all inventoried documented ADD/ADC/SUB/SBC/AND/XOR/OR/CP, INC/DEC, NEG, DAA, CPL, CCF, SCF and required 16-bit arithmetic/addressing forms with exact operand/range rules.
3. **Files/artifacts created or modified:** tools/as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Native `as` bytes for every inventoried arithmetic/logical form match certified SjASMPlus and execute expected results in a tiny target corpus.
9. **Negative/failure test:** Invalid widths/register pairs/immediates fail transactionally; no undocumented opcode alias is accepted.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.13 - Assembler control-flow encoder

1. **Purpose / REV11 requirement:** §23, §38
2. **Exact implementation work:** Encode all inventoried documented JP/JR/CALL/RET/RST/DJNZ condition/addressing forms. Relative targets are resolved in-module and must fit signed -128..127 displacement; symbolic absolute JP/CALL words emit OBJ1 ABS16 relocation when required.
3. **Files/artifacts created or modified:** tools/as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary relative branches -128 and +127 and all inventoried conditions encode byte-for-byte equal to SjASMPlus; linked absolute references relocate correctly.
9. **Negative/failure test:** Relative -129/+128, invalid condition, illegal external JR/DJNZ target, or RST vector outside documented set fails before commit.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.14 - Assembler rotate/shift/bit encoder

1. **Purpose / REV11 requirement:** §23, §38
2. **Exact implementation work:** Encode all inventoried documented RLCA/RRCA/RLA/RRA plus CB-family RLC/RRC/RL/RR/SLA/SRA/SRL, BIT/SET/RES register/(HL)/required indexed forms. Undocumented SLL and undocumented indexed-result aliases are forbidden in the portable baseline.
3. **Files/artifacts created or modified:** tools/as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every inventoried documented rotate/shift/bit form matches certified SjASMPlus bytes and indexed displacement boundaries.
9. **Negative/failure test:** SLL or another forbidden undocumented form, illegal bit number, or displacement overflow is rejected transactionally.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.15 - Assembler stack/exchange/interrupt/special encoder

1. **Purpose / REV11 requirement:** §23, §38
2. **Exact implementation work:** Encode all inventoried documented PUSH/POP, EX/EXX, DI/EI, IM 0/1/2, HALT, NOP, RETI, RETN and required I/R transfer/special forms. Respect the architecture policy that IY/alternate-bank ownership is an ABI rule for programs, while `as` itself still recognizes documented Z80 syntax required by OS source.
3. **Files/artifacts created or modified:** tools/as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every inventoried documented special/stack/interrupt form matches certified SjASMPlus bytes; OS-only forms assemble where required by kernel sources.
9. **Negative/failure test:** Invalid IM value/register pair or undocumented special opcode spelling is rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.16 - Assembler block-transfer/search and I/O encoder

1. **Purpose / REV11 requirement:** §23, §38
2. **Exact implementation work:** Encode all inventoried documented LDI/LDIR/LDD/LDDR/CPI/CPIR/CPD/CPDR and required IN/OUT documented forms, including BC-selected I/O forms used for Spectrum keyboard/ULA work.
3. **Files/artifacts created or modified:** tools/as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every inventoried block/I/O form matches certified SjASMPlus bytes and a representative target execution/port harness proves operand selection.
9. **Negative/failure test:** Illegal port/register syntax or undocumented ED form fails without output commit.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.17 - Assembler opcode coverage closure

1. **Purpose / REV11 requirement:** §23, §38, §56
2. **Exact implementation work:** Run the complete required-opcode/addressing inventory through native `as` and certified SjASMPlus, compare emitted text bytes and OBJ1 relocation records, then prove 100% inventory coverage. This closes instruction coverage before the OBJ1 writer/lifecycle/link acceptance steps may proceed.
3. **Files/artifacts created or modified:** tools/as.asm; tests/compiler/as-opcode-coverage; docs/assembler.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Coverage report has zero missing/extra undocumented forms; every positive vector is byte-identical to SjASMPlus and every negative/range vector fails for the intended reason.
9. **Negative/failure test:** Delete one encoder case or allow one undocumented opcode in a negative build; coverage/policy gate must fail deterministically.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.18 - Assembler OBJ1 writer

1. **Purpose / REV11 requirement:** §23
2. **Exact implementation work:** Serialize deterministic OBJ1 from the fully validated assembler result. Symbol-record order is an implementation policy frozen by deterministic native-assembler tests and is NOT an architecture-prescribed sort order; relocation records MUST obey REV11's strictly increasing, non-overlapping offset rule. Compute the OBJ1 body/header CRCs over the exact stored bytes and run the independent host inspector before transactional publication.
3. **Files/artifacts created or modified:** as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Two identical native assemblies produce byte-identical OBJ1; the host inspector validates all records/offsets/CRCs and relocation records are strictly increasing/non-overlapping exactly as REV11 requires.
9. **Negative/failure test:** Any malformed symbol/relocation record, relocation-order/overlap violation, CRC mismatch, nondeterministic output for identical input, or documentation/test that falsely claims REV11 mandates symbol-table sorting fails before commit.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.19 - Assembler default names/-o

1. **Purpose / REV11 requirement:** §23
2. **Exact implementation work:** Exact lower-case `.asm` -> `.obj` default and explicit -o, no case folding. `as` accepts exactly one ASM-typed input. Default output is allowed only when the exact lower-case input base ends `.asm`; remove only that final suffix and append `.obj`, with resulting base <=10 bytes. Otherwise explicit `-o out.obj` is required. The kernel never infers the input/output type from suffix.
3. **Files/artifacts created or modified:** as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** hello.asm -> hello.obj.
9. **Negative/failure test:** HELLO.asm distinct. Wrong object type, uppercase/missing `.asm` under default form, or derived >10-byte output is rejected before temp creation; explicit -o remains exact/case-sensitive.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.20 - Assembler transactional output

1. **Purpose / REV11 requirement:** §23, §56
2. **Exact implementation work:** Write unique `/tmp/.as<pid>.<n>` O_EXCL then atomic rename. The transaction is specifically O_CREATE|O_EXCL `/tmp/.as<pid>.<n>`; close and validate the complete OBJ1 before atomic SYS_RENAME. Syntax/allocation/rename failure preserves any previous output byte-for-byte and never deletes an unknown colliding temp by name.
3. **Files/artifacts created or modified:** as.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Success commit; failure prior destination hash identical.
9. **Negative/failure test:** Temp collision safe.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.21 - Linker input loader

1. **Purpose / REV11 requirement:** §24
2. **Exact implementation work:** Read/validate one/many OBJ1 and selected built-in archive members. Every linker input must be an explicit OBJ-typed object; one or more inputs are required. Suffix spelling never changes kernel type metadata.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Malformed object rejected before output mutation.
9. **Negative/failure test:** Wrong type rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.22 - crt0 built-in archive

1. **Purpose / REV11 requirement:** §24
2. **Exact implementation work:** Provide a compact built-in archive containing `crt0` plus libc48 runtime members inside the linker image/distribution. The linker pulls in only members referenced by currently unresolved globals through the fixed-point selection rule; the normal `ld hello.obj -o hello` path is therefore self-contained and requires no separate library tape.
3. **Files/artifacts created or modified:** libc48/runtime_archive.asm; crt0.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** hello link resolves `_start` and libc symbols.
9. **Negative/failure test:** Missing required member yields link error.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.23 - Archive fixed-point selection

1. **Purpose / REV11 requirement:** §24
2. **Exact implementation work:** Scan the built-in runtime archive in its frozen member order; select members satisfying currently unresolved globals, append selected members in selection order, and repeat fixed-order scans to a fixed point. Treat reserved linker-defined `__heap_start` and `__heap_end` references as satisfiable during archive selection even though their values are assigned only after final BSS/heap layout; no OBJ1 module may define either name. After excluding only those two reserved symbols, any unresolved global is a hard link error.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** A transitive dependency golden reaches the same fixed member set/order on repeated links, including inputs that reference `__heap_start`/`__heap_end` before those values exist.
9. **Negative/failure test:** A single-pass archive scan, different member order, unresolved non-heap global, or archive-selection failure caused solely by a legal reserved heap-symbol reference fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.24 - Module order/alignment/padding

1. **Purpose / REV11 requirement:** §24
2. **Exact implementation work:** Unless `-nostart` is active, final module order begins with `crt0`, then user OBJ1 inputs in command-line order, then selected archive members in selection order. Align every module TEXT start to an even final image offset using zero padding; after all TEXT, pad to an even byte count and freeze that value as MEX1 `image_size`. Lay out module BSS in the same final module order with each module BSS start even relative to BSS start; place the linker-reserved heap at the next even BSS offset. Require `image_size + final_bss_size <= 32768` before output publication.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden map proves exact module order, TEXT/BSS addresses, zero padding, final image_size and final_bss_size, including an odd-size module in both TEXT and BSS.
9. **Negative/failure test:** Any reordered module, nonzero alignment byte, odd final boundary where even is required, differing BSS order, or image_size+final_bss_size overflow fails with no committed output.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.25 - Symbol resolution

1. **Purpose / REV11 requirement:** §24
2. **Exact implementation work:** Resolve case-sensitive globals/externs and freeze the exact final symbol formulas: TEXT = `module_text_base + OBJ1 value`; BSS = `image_size + module_bss_base + OBJ1 value`; ABS = `OBJ1 value`. After excluding only the reserved linker-defined `__heap_start`/`__heap_end` cases during archive selection, any remaining unresolved global or any duplicate defined global is a hard link error.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.25`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden map proves the exact TEXT/BSS/ABS formulas and case-sensitive resolution.
9. **Negative/failure test:** Case mismatch remains unresolved.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.25.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.26 - ABS vs runtime relocations

1. **Purpose / REV11 requirement:** §24
2. **Exact implementation work:** For each OBJ1 relocation compute final patch location as module_text_base + relocation.offset. Evaluate referenced final symbol value plus its signed OBJ1 i16 addend in widened precision and require the result in 0..65535 before narrowing. Patch ABS symbols absolutely with no MEX1 runtime relocation. Patch TEXT/BSS symbols relative to link base zero and emit one MEX1 ABS16 runtime relocation at the final patch location. Sort the final MEX1 relocation locations ascending, require them unique/non-overlapping, and revalidate every location against final image bounds.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.26`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden vectors prove positive/negative signed addends, ABS versus TEXT/BSS behavior, widened 0 and 0xFFFF boundaries, and exact sorted unique final runtime relocation table.
9. **Negative/failure test:** Underflow/overflow, duplicate/overlapping/out-of-range final relocation, or a fixed ROM/syscall ABS reference incorrectly emitted as runtime relocation fails before commit.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.26.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.27 - Entry `_start` default

1. **Purpose / REV11 requirement:** §24
2. **Exact implementation work:** Normal link includes `crt0`; the default entry symbol is `_start`, it must resolve to TEXT, and normal MEX1 output uses that exact resolved TEXT entry.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.27`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** MEX1 entry offset exact.
9. **Negative/failure test:** Missing, unresolved, duplicate, or non-TEXT `_start` fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.27.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.28 - `-nostart -e symbol`

1. **Purpose / REV11 requirement:** §24
2. **Exact implementation work:** Development-only `-nostart` omits `crt0`; `-e name` is then mandatory, that exact case-sensitive symbol must resolve to TEXT, and it becomes the MEX1 entry. No implicit/default entry is permitted under `-nostart`; the heap default differs as frozen separately.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.28`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Goldens.
9. **Negative/failure test:** `-nostart` without `-e`, with an unresolved/duplicate entry, or with an entry resolving outside TEXT is rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.28.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.29 - Linker-reserved heap symbols

1. **Purpose / REV11 requirement:** §24, §41.2A
2. **Exact implementation work:** Reserve `__heap_start`/`__heap_end`, survive archive selection, assign after final BSS; reject user definitions.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.29`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Address values match final BSS heap.
9. **Negative/failure test:** User definition rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.29.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.30 - `-stack` option

1. **Purpose / REV11 requirement:** §24, §41.2A
2. **Exact implementation work:** Default512; only even64..4096 accepted and written to MEX1 min FAST stack.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.30`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary options exact.
9. **Negative/failure test:** Odd/63/4097 rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.30.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.31 - `-heap` option and defaults

1. **Purpose / REV11 requirement:** §24, §26, §41.2A
2. **Exact implementation work:** With normal default `crt0`, reserve a 1024-byte linker heap in BSS unless `-heap bytes` is explicit. With development-only `-nostart`, default heap is 0 unless explicitly overridden. Accept `-heap` only for even byte counts 0..8192 inclusive; place the heap after the next even final BSS offset, assign `__heap_start`/`__heap_end`, include the exact requested bytes in MEX1 `bss_size`, and subject the result to the normal image+BSS <=32768 bound.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.31`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary tests for default normal=1024, default -nostart=0, and explicit 0,2,1024,8192 produce exact BSS/symbol values.
9. **Negative/failure test:** Odd values, negative/non-numeric values, >8192, or any requested heap that makes final image+BSS impossible are rejected with no output mutation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.31.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.32 - MEX1 final writer

1. **Purpose / REV11 requirement:** §24
2. **Exact implementation work:** Serialize valid MEX1 image+BSS/entry/relocs/CRCs deterministically.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.32`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host inspect and two-base run.
9. **Negative/failure test:** Invalid relocation rejected before commit.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.32.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.33 - Linker transactional output

1. **Purpose / REV11 requirement:** §24, §56
2. **Exact implementation work:** Use unique `/tmp/.ld<pid>.<n>` + atomic rename. Use an exclusive O_CREATE|O_EXCL `/tmp/.ld<pid>.<n>` BIN transaction, validate/close complete MEX1, then atomic SYS_RENAME. `ld ... -o name` requires exact case-sensitive <=10-byte output name; there is no kernel-inferred output suffix/default type.
3. **Files/artifacts created or modified:** ld.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.33`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Failure preserves previous executable byte-for-byte.
9. **Negative/failure test:** Temp collision safe.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.33.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.34 - On-target assembly/link lifecycle

1. **Purpose / REV11 requirement:** §56 acceptance
2. **Exact implementation work:** Write lower-case source in vi/fixture, as, ld, run, save cassette, reload/run exact case.
3. **Files/artifacts created or modified:** integration tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.34`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Output and CRC exact after roundtrip.
9. **Negative/failure test:** Wrong-case reload miss.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.34.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.35 - Multi-module golden link

1. **Purpose / REV11 requirement:** §56 acceptance
2. **Exact implementation work:** Freeze exact crt0/user/archive order, symbols, alignment, padding, archive fixed point, relocation and entry expectations.
3. **Files/artifacts created or modified:** tests/compiler/link_golden
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.35`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host+target agree byte-for-byte.
9. **Negative/failure test:** Perturb input order where architecture says fixed and detect changed/invalid golden.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.35.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P10.36 - Phase-10 acceptance/size gate

1. **Purpose / REV11 requirement:** §56, §44
2. **Exact implementation work:** Run assembler/linker syntax/link/allocation failure transactions and size targets as/as<=12288, ld<=8192 or measured justified exceptions.
3. **Files/artifacts created or modified:** Phase10 evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P10.36`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every Phase10 bullet PASS.
9. **Negative/failure test:** Prior output mutation on failure blocks phase.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P10.36.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 11 - C48 Compiler

### Mandatory Python SDK reference and admission corpus

Phase 11 MUST use the existing portable Python C48 SDK as a design/reference
implementation and behavioral oracle:

`https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit`

The reference baseline inspected when this plan was amended is SDK commit
`84d144de2721cda5075c3a6610a422663b5e2f77`. Before Phase-11 implementation begins, record the exact SDK
commit used by the certification evidence; changing that commit requires an explicit
re-baseline record. The SDK repository is a read-only reference for this plan. Its
Python implementation is not target code: the admitted ZX-UX `cc` remains native
Z80 code and must emit the REV11 OBJ1/ABI/runtime contracts. If the SDK and REV11
differ, REV11 wins and the difference must be recorded rather than silently copied.

Compiler design work must explicitly study and cross-reference the SDK implementation
under `compiler/c48/`, including its preprocessor, lexer, parser, type system, semantic
checks, limits/error handling, numeric model, memory model and runtime behavior, plus
the SDK C48 language/conformance documentation. This is a mandatory design input, not
an optional source of ideas; target-specific streaming, residency, ABI and Z80 codegen
constraints remain governed by REV11.

Before `cc` can be certified or admitted, copy the SDK's complete `compiler/tests/`
corpus into `v1/tests/compiler/sdk-reference/`, preserving original test bytes, paths
where practical, provenance and the pinned SDK commit. Also copy the SDK test runner,
release verifier/expectations and every fixture/support file needed to execute the
imported corpus. At minimum the inspected baseline includes
`test_conformance.py`, `test_game_regressions.py`, `test_release_regressions.py`,
`test_security.py`, `compiler/run_tests.py`, `compiler/verify_release.py` and
`compiler/release_expectations.json`; that baseline declares exactly 205 tests.

The imported SDK tests are mandatory admission tests. They may not be deleted,
skipped, xfailed, weakened, or rewritten merely to make native `cc` pass. First, the
copied reference corpus must pass from this repository against the pinned Python SDK
reference/fixtures, proving an intact import. Second, every C48 language/semantic
expectation exercised by that corpus must have a documented target-native mapping and
pass against the ZX-UX compiler/runtime. SDK-only C48B1, GUI or host-VM mechanics may
use a documented adapter/oracle, but the original test intent and expected C48 behavior
must remain mechanically checked. P11.48 MUST refuse certification/admission unless
both the copied SDK corpus and the target-native Phase-11 suite are fully green.

## P11.01 - C48 language/spec document freeze

1. **Purpose / REV11 requirement:** §25, §57
2. **Exact implementation work:** Write the exact C48 supported subset and explicitly freeze the version-1 deferred language surface rather than saying merely “not ISO C”. In addition to the supported features implemented by P11.04-P11.10, state that compound assignments, the conditional `?:` operator and the comma operator are deferred, and that the following are not version-1 C48 features unless a later architecture revision says otherwise: `double` as a distinct format from C48 `float`, `long long`, variable-length arrays, complex initializers, variadic functions, function pointers, `switch`/`case`, `struct`/`union`, complex preprocessor macros, optimizer passes requiring large IR, and full ISO conformance. Freeze data model char1/short2/int2/pointer2/float5 with exact alignments and plain-char unsigned; `long` is unsupported. Cross-reference the pinned Python SDK language specification, conformance notes and compiler behavior while writing `c48.md`; record the SDK commit and any REV11-over-SDK differences in an SDK provenance/mapping record.
3. **Files/artifacts created or modified:** `v1/docs/c48.md`; `v1/tests/compiler/sdk-reference/SDK-PROVENANCE.md`; C48 SDK design/contract mapping
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Spec checklist against §25 names every supported/deferred language family, data-model rule and operator exclusion explicitly; no generic “subset” sentence substitutes for a missing item. The evidence records the pinned Python SDK commit, the reviewed SDK design/docs, and every intentional REV11-over-SDK divergence.
9. **Negative/failure test:** Unsupported feature accidentally claimed, missing SDK provenance, or an unexplained REV11/SDK contract difference is documentation failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.02 - Streaming compiler architecture and bounded symbol tables

1. **Purpose / REV11 requirement:** §§25.5-25.6,57
2. **Exact implementation work:** Implement the memory-conscious compiler pipeline exactly as `source stream -> lexer -> recursive-descent parser -> bounded small expression tree/direct emission -> symbolic Z80 emitter -> OBJ1 writer`. Do not build a whole-program AST or materialize an entire source object merely to compile it. Statements compile incrementally; expression trees have a measured fixed bound and are released immediately. Use separate compact bounded tables for globals/externs, current-function locals, and labels. C48 identifiers are case-sensitive with at most 15 visible characters; a longer identifier is a compile-time error and is never truncated or hashed into an accepted alias. Freeze each table capacity from the <=20 KiB compiler residency budget and report deterministic table-full failure rather than corrupting memory. The native pipeline design must explicitly cross-reference the pinned Python SDK `compiler/c48/` module decomposition and behavior—especially preprocessing, lexing, parsing, `typesys`, semantics, limits/errors, numeric/runtime and memory-model logic—while documenting why the target compiler uses a streaming bounded Z80 architecture instead of copying the host Python architecture literally.
3. **Files/artifacts created or modified:** `v1/src/tools/cc.asm`; compiler workspace/symbol-table tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Compilation advances incrementally from source stream to OBJ1 with no whole-source or whole-program-AST allocation; bounded expression trees are released immediately; each symbol table accepts its exact capacity and 15-character case-sensitive identifiers without truncation or aliasing.
9. **Negative/failure test:** Instrument or force a whole-source/whole-AST allocation, exceed any bounded expression/symbol table, use a 16-character identifier, or create names that would collide if truncated/hashed; each must fail deterministically with prior output preserved and without compiler-memory overwrite.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.03 - Version-1 C48 preprocessor

1. **Purpose / REV11 requirement:** §25.7, §41.9, §57
2. **Exact implementation work:** Implement exactly the version-1 preprocessing surface before lexical parsing: object-like `#define` constants; one-level local `#include "name"` resolved from the current directory; and built-in `#include <c48.h>`. The `<c48.h>` bytes/declarations are compiled into `cc` and therefore require no tape/header object. Local include nesting/recursion beyond one level is rejected. Macro functions, recursive include, `#if`/`#ifdef` or other conditional preprocessing, token pasting, stringification and a full ISO preprocessor are not implemented. Preserve C48 case sensitivity and the normal source-stream/resource bounds through preprocessing; included bytes feed the same streaming compiler path rather than creating an unbounded aggregate source copy.
3. **Files/artifacts created or modified:** `v1/src/tools/cc.asm`; `v1/docs/c48.md`; `v1/tests/compiler/preprocessor/`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All three supported preprocessing forms produce deterministic equivalent compilation while preserving streaming bounds and case sensitivity; local include depth never exceeds one and `<c48.h>` is supplied entirely from the compiler image.
9. **Negative/failure test:** Function-like macro, recursive/nested local include, unknown angle-bracket header, conditional directive, token paste/stringification, include cycle/path violation, overlength expanded token/source bound, or attempted tape lookup for `<c48.h>` must fail before output commit.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.04 - C48 lexer

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Tokenize case-sensitive identifiers/literals/operators/comments within source/object bounds.
3. **Files/artifacts created or modified:** tools/cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden lexical corpus.
9. **Negative/failure test:** Overlength/malformed token fails transactionally.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.05 - C48 parser declarations/types

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Parse void/char/unsigned char/short/unsigned short/int/unsigned int/float, pointers, one-dimensional arrays, functions, restricted fixed-count non-variadic prototypes, locals, globals, file-scope static and extern. Prototype/definition types must match exactly; only `int main(void)` and `int main(int argc, char **argv)` are valid entry signatures. Support simple constant scalar initializers and one-dimensional constant array initializers exactly; complex initializers remain outside C48 version 1.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden AST/code fixtures.
9. **Negative/failure test:** struct/union/long/double rejected. Reject unsupported complex/nonconstant initializer forms rather than silently generating a different C dialect.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.06 - C48 statements/control flow

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** if/else, while, do/while, for, break, continue, return.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden control-flow output.
9. **Negative/failure test:** Invalid break context rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.07 - C48 expression precedence

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Implement exact version-1 operator set and precedence: assignment =; arithmetic + - * / %; prefix/postfix ++ --; shifts << >>; relational < <= > >= == !=; bitwise & | ^ ~; logical && || ! with short-circuit; address/deref & *; indexing/call [] (); unary + -. Implement supported integer and integer<->float casts. Reject compound assignments, ?: and comma operator as deferred.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden evaluation corpus.
9. **Negative/failure test:** ?:/comma/unsupported compound op rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.08 - 16-bit integer semantics

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Freeze the C48 integer semantics literally: addition, subtraction, multiplication, unary minus, and left shift wrap modulo operand width; signed division truncates toward zero and signed remainder has the dividend's sign; division or remainder by zero terminates the C48 process with status 1 through runtime error handling; signed right shift is arithmetic and unsigned right shift is logical; shift counts use only the low 3 bits for 8-bit operands and the low 4 bits for 16-bit operands. Implement signed/unsigned comparisons consistently with the frozen widths.
3. **Files/artifacts created or modified:** cc.asm; libc48
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary runtime oracle proves modulo-width arithmetic, signed/unsigned comparisons, truncation/remainder signs, 8-bit shift-count masking at 0/7/8/15/255, 16-bit shift-count masking at 0/15/16/31/255, arithmetic signed right shift, logical unsigned right shift, and status-1 division/remainder-by-zero handling.
9. **Negative/failure test:** A fixture that uses an unmasked shift count, applies logical right shift to a signed value, arithmetic right shift to an unsigned value, fails modulo-width wrap, or allows division/remainder by zero to continue normally must fail the C48 integer-semantics oracle.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.09 - Pointer arithmetic

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Use the frozen 16-bit pointer representation. Pointer arithmetic scales by the pointed-to `sizeof`; subtraction of pointers into the same array/object yields a signed 16-bit element count. Ordering or subtraction of unrelated pointers is outside the portable C48 contract and must not be documented or tested as a defined portable result.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Array/object goldens prove pointer +/- integer scaling for 1-, 2-, and 5-byte element sizes and positive/zero/negative same-array pointer subtraction as signed 16-bit element counts.
9. **Negative/failure test:** Out-of-supported compile forms are rejected, and the language/spec oracle fails if ordering or subtraction of unrelated pointers is claimed as portable defined C48 behavior.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.10 - String/char literals

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Emit supported literal bytes and deterministic object storage.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden OBJ1 data.
9. **Negative/failure test:** Unsupported escape rejected/documented.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.11 - Globals/statics/externs

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Emit exact OBJ1 symbols/BSS for supported storage classes.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Multi-module C/ASM link goldens.
9. **Negative/failure test:** Duplicate definition error.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.12 - Local variable frame layout

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Implement the exact C48 frame rule: omit an IX frame entirely for leaf/simple functions that can address locals without it; when a frame is required IX is the frame pointer and is restored as callee-preserved state. Keep SP even-aligned at every C48 call boundary and never use IY as a C48 frame/index register.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Stack offsets/alignment are exact; leaf/simple goldens omit IX frames where locals remain directly addressable, frame-requiring goldens use IX, restore it exactly, and preserve an even SP at every call boundary.
9. **Negative/failure test:** IY use as a frame pointer, an unnecessary mandatory IX frame in a qualifying leaf/simple golden, a non-restored IX frame, or an odd-SP call boundary fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.13 - C48_REGCALL integer/pointer args

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Freeze the single externally linkable version-1 C48 calling convention as `C48_REGCALL`; there is no second CDECL ABI and OBJ1 carries no calling-convention metadata. Every scalar/pointer argument occupies one 16-bit slot: first HL, second DE, third BC, remaining arguments as 16-bit stack words right-to-left; 8-bit `char` arguments are zero-extended; the caller removes stack argument words and SP is even-aligned at every call boundary. Freeze scalar returns exactly: `void` has no value, 8-bit scalar returns in L, 16-bit scalar and pointer return in HL. Register ownership is exactly AF/BC/DE/HL caller-clobbered, IX callee-preserved when used, IY OS/ROM-reserved and never changed by conforming C48, and the alternate bank OS-private/unavailable. Exercise C48_REGCALL functions with argument counts 0..6 including register/stack transitions; float-pointer and hidden-result cases are closed by P11.15/P11.16.
3. **Files/artifacts created or modified:** cc.asm; crt0/libc
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Byte-for-byte call fixtures prove argument counts 0..6, right-to-left stack arguments/caller cleanup/even SP, exact scalar return registers, AF/BC/DE/HL caller-clobber freedom, IX preservation when used, IY=0x5C3A before/after every generated call/return boundary, and no OBJ1 calling-convention metadata or alternate CDECL entry surface.
9. **Negative/failure test:** Odd SP, wrong argument/return register, callee damage to required-preserved IX, generated write/re-purpose of IY, return with IY!=0x5C3A, alternate-register task ownership, any second CDECL-style ABI, or invented OBJ1 calling-convention metadata fails even if the computed result is otherwise correct.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.14 - Five-byte float representation

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Use Spectrum-ROM-compatible five-byte numeric format, not IEEE binary32.
3. **Files/artifacts created or modified:** cc.asm; libc48 float bridge
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Known values bytes equal ROM conversions.
9. **Negative/failure test:** 4-byte float assumption fails ABI test.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.15 - C48_REGCALL float arguments

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Pass every C48 `float` argument as a 16-bit pointer to caller-owned five-byte value storage; it consumes one ordinary C48_REGCALL slot (HL, then DE, then BC, then right-to-left 16-bit stack words). The caller materializes float literals/intermediate results in addressable temporary storage when needed; float values are never passed inline in ordinary 16-bit slots.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Byte-exact callee fixture.
9. **Negative/failure test:** Pass-by-value fixture fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.16 - C48 float return hidden pointer

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** A function returning C48 `float` receives a hidden first 16-bit pointer to caller-provided five-byte result storage in HL. That hidden slot shifts user arguments to DE, BC, then stack; the callee writes exactly five result bytes and returns the same result pointer in HL. Apply this rule to normal C48 functions and runtime math helpers.
3. **Files/artifacts created or modified:** cc.asm; libc
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Byte-exact caller/callee fixture.
9. **Negative/failure test:** Wrong shifted register assignment fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.17 - SYS_FP_EXEC ROM calculator runtime bridge

1. **Purpose / REV11 requirement:** §25, §14
2. **Exact implementation work:** Serialize calculator service, preserve IY/OS state and map ROM errors to runtime/errno. Freeze the required C48 floating runtime operation symbols exactly: `__fadd`, `__fsub`, `__fmul`, `__fdiv`, `__fpow`, `__fabs`, `__fsgn`, `__fint`, `__fexp`, `__fln`, `__fsin`, `__fcos`, `__ftan`, `__fasin`, `__facos`, `__fatan`, and `__fsqrt`; each lowers through this controlled calculator bridge rather than an in-program floating implementation. Also freeze the simple library-facing bridge `int zx_fp_exec(op, const float *lhs, const float *rhs, float *out)`; unary runtime helpers pass no rhs/encode rhs=0 at the syscall boundary. SYS_FP_EXEC consumes HL -> exact eight-byte FPOP1 `{u8 op,u8 reserved=0,u16 lhs,u16 rhs,u16 out}`. Implement the frozen op dispatch exactly: 0 invalid; 1 ADD; 2 SUB; 3 MUL; 4 DIV; 5 POW; 6 ABS; 7 SGN; 8 INT; 9 EXP; 10 LN; 11 SIN; 12 COS; 13 TAN; 14 ASN; 15 ACS; 16 ATN; 17 SQR. Binary ops 1..5 require nonzero lhs and rhs; unary ops 6..17 require nonzero lhs and rhs=0; out is always nonzero. Validate the complete record and every five-byte operand/result range before entering the serialized ROM calculator critical section. Copy every required operand into controlled calculator workspace before any result write so out may safely alias lhs or rhs; no calculator intermediate state is process-visible.
3. **Files/artifacts created or modified:** libc48 runtime math
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Arithmetic/transcendentals goldens plus an exhaustive op-ID 0..17 ABI table test: 0 rejects, each 1..17 selects exactly its frozen operation, binary/unary pointer rules are exact, out=0 rejects, and out aliasing lhs/rhs produces the same five-byte result as non-aliasing execution.
9. **Negative/failure test:** Concurrent fixture cannot reenter calculator workspace. Renumber any op, accept 0 or >17, allow missing rhs for a binary op, allow nonzero rhs for a unary op, allow zero lhs/out where forbidden, or write aliased output before copying operands; the FPOP1 ABI oracle must fail before exposing a result.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.18 - SYS_INT_TO_FP / SYS_FP_TO_INT casts

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Implement supported int/float casts using the approved ROM conversion gateway and freeze the required runtime helper names `__itof` and `__ftoi`. SYS_INT_TO_FP consumes HL -> exact six-byte ITOF1 `{u16 value,u8 is_signed,u8 reserved=0,u16 out_float_ptr}`, where is_signed is only 0 unsigned or 1 signed two's-complement. SYS_FP_TO_INT consumes HL -> exact six-byte FTOI1 `{u16 in_float_ptr,u8 is_signed,u8 reserved=0,u16 out_u16_ptr}`; conversion truncates toward zero and requires 0..65535 unsigned or -32768..32767 signed. Invalid/out-of-range input returns E_INVAL without writing the destination. Both calls copy operands into controlled workspace before output so documented aliasing is safe.
3. **Files/artifacts created or modified:** cc.asm; libc
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Boundary conversions exact.
9. **Negative/failure test:** Overflow follows specified behavior.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.19 - SYS_FP_CMP float comparisons

1. **Purpose / REV11 requirement:** §10.1, §25
2. **Exact implementation work:** Use the required `__fcmp` runtime helper over the FP_CMP syscall contract and generate the logical result. SYS_FP_CMP consumes HL -> exact six-byte FCMP1 `{u16 lhs_float_ptr,u16 rhs_float_ptr,u16 out_i8_ptr}` and on success writes exactly signed byte -1, 0 or +1. Lower every float relational/equality test through it and compare float logical truth against exact floating zero. Inputs are copied before result write so documented aliasing is safe; no host floating representation may enter the ABI.
3. **Files/artifacts created or modified:** cc.asm; libc
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** < <= == != > >= goldens.
9. **Negative/failure test:** NaN-like unsupported/domain state handled per ROM contract.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.20 - ROM-backed math library

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Provide required safe EXP/LN/SIN/COS/TAN/ASN/ACS/ATN/SQR/POW surface exactly specified. Public C48 math names resolve through the named `__f*`/`__itof`/`__ftoi`/`__fcmp` runtime helpers and the serialized kernel calculator service; the compiler never inlines a private floating implementation. The exact §25.8 public math surface is `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sqrt`, `exp`, `log`, `pow`, `fabs`; each resolves through the controlled five-byte ROM-calculator runtime, not host floating point.
3. **Files/artifacts created or modified:** libc48 runtime/math
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden tolerance/byte conversions based on ROM behavior. Link and execute all eleven public math symbols plus their required internal helpers across representative finite/domain/boundary values and cooperative switches; compare target five-byte results or documented errors.
9. **Negative/failure test:** Domain errors controlled.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.21 - C48 malloc/free BSS heap

1. **Purpose / REV11 requirement:** §25, invariant
2. **Exact implementation work:** Only the linker-reserved `[__heap_start,__heap_end)` interval is managed by C48 `malloc`/`free`; they never call the kernel for additional memory and version 1 has no user `SYS_ALLOC`. The exact §25.8 dynamic-memory surface is the two public functions `malloc` and `free`, backed only by the fixed link-time BSS heap reserve from §26. A zero-byte heap (`__heap_start == __heap_end`) is valid and makes `malloc` return NULL deterministically.
3. **Files/artifacts created or modified:** libc48/memory.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** default1024, heap0, heap8192 accounting; heap0 proves `malloc` returns NULL and no kernel allocation syscall is attempted.
9. **Negative/failure test:** Static scan rejects SYS_ALLOC dependency.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.22 - C48 process/environment runtime API

1. **Purpose / REV11 requirement:** §25, §37
2. **Exact implementation work:** Implement user wrappers from single syscall include with exact register/record ABI. Implement and export exactly these §25.8 public runtime functions in this step: `exit`, `yield`, `sleep`, `spawn`, `wait`, `kill`, `chdir`, `getcwd`, `getenv`, `getpid`. Each is a thin C48 ABI wrapper over the already-certified kernel/ARG1/ENV1/cwd contracts; `getenv` reads the immutable ENV1 bootstrap block without copying it onto the runtime stack, and `getcwd` obeys the exact NUL/capacity convention. No hidden host/POSIX behavior is imported.
3. **Files/artifacts created or modified:** libc48/syscall.asm; process/io
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Wrapper conformance suite. Compile/link/run one focused C48 test that calls every function named in this step, including unset/missing getenv, cwd change/get, sleep/yield, child lifecycle and exact errno propagation.
9. **Negative/failure test:** Duplicate syscall number literal fails static scan. The step fails if any of its ten required public symbols is absent from the built-in libc48 archive or resolves to a host-only/stub implementation.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.23 - C48 object/handle runtime API

1. **Purpose / REV11 requirement:** §25.8; §§9-13
2. **Exact implementation work:** Implement and export exactly these public runtime functions: `open`, `open_typed`, `close`, `read`, `write`, `seek`, `stat`, `remove`, `rename`, `list`, `pipe`, `dup`, `ioctl`, `read_full`, `write_full`. Wrappers use the exact frozen syscall records/flags and preserve C48 calling conventions. `open()` uses DAT only when creation is actually required; `open_typed()` supplies the explicit ordinary creation type. `read_full`/`write_full` loop over legal short transfers, terminate on exact error/EOF semantics, and yield only where their called primitives require it.
3. **Files/artifacts created or modified:** `v1/src/libc48/io.asm`; `v1/src/libc48/runtime_archive.asm`; `v1/src/tools/cc.asm`; focused C tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All fifteen symbols resolve from the built-in libc48 archive and behavior matches the underlying REV11 syscall contracts, including short I/O and typed creation.
9. **Negative/failure test:** Omit one archive symbol, force short read/write then error, pass illegal creation type, or corrupt a packed open; require exact failure with destination/object state preserved.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.24 - C48 string/memory library

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Implement required minimal routines; use documented Z80 block primitives where measured appropriate. The exact §25.8 public surface owned here is `getchar`, `putchar`, `puts`, `strlen`, `strcmp`, `strcpy`, `strncpy`, `memcpy`, `memmove`, `memchr`, `memset`. Implement target-byte semantics, overlap-safe memmove, bounded string/memory behavior and tty wrappers without a large general-purpose `printf`. Provide the REV11 compact integer formatter as a small libc/compiler-runtime helper and use the ROM-backed floating formatter owned by P11.46 for floating text; neither requirement authorizes a general printf implementation.
3. **Files/artifacts created or modified:** libc48/string.asm; memory.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden memcpy/memmove/string cases. One C matrix links and executes every one of these eleven functions, including empty strings, NUL boundaries, overlapping memmove in both directions, memchr hit/miss, and tty EOF/input/output cases.
9. **Negative/failure test:** Overlap memmove correctness. Missing symbol, accidental host libc dependency, unsafe overlap or out-of-bounds test guard mutation fails the step.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.25 - Graphics/UDG library

1. **Purpose / REV11 requirement:** §25, §42
2. **Exact implementation work:** Thin wrappers to OS graphics/UDG syscalls and required 2x2 helper. The exact §25.8 public graphics/UDG surface owned here is `cls`, `print_at`, `plot`, `point`, `draw`, `circle`, `ink`, `paper`, `bright`, `flash`, `inverse`, `over`, `border`, `udg_define`, `udg_get`, `udg_draw`, `udg_clear`, `udg_draw_2x2`. Every function lowers only through the validated console/graphics/UDG kernel APIs and preserves the tty64/direct-screen state rules.
3. **Files/artifacts created or modified:** libc48/graphics.asm; udg.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.25`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** colors/lines fixture. Compile/link/run a C matrix that invokes all eighteen names and compares bitmap/attribute/UDG RAM plus cursor/ULA shadow to exact expected bytes.
9. **Negative/failure test:** IY preserved.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.25.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.26 - C48 beep wrapper

1. **Purpose / REV11 requirement:** §17, §25
2. **Exact implementation work:** `int beep(float duration,float pitch)` uses the float-pointer ABI and the same synchronous SYS_BEEP. This step owns the exact §25.8 public `beep` symbol and returns 0 on success or the positive ZX-UX errno on failure. `duration` is seconds; `pitch` is semitones above middle C; negative/fractional values and +/-12 octave relationships are preserved exactly as accepted by the verified ROM domain. Five-byte values remain pointer-backed; the wrapper invents no narrower pitch range and no asynchronous/background sound semantics. This step owns the exact §25.8 public `beep` symbol. Its C signature is the REV11 `int beep(float duration,float pitch)` wrapper over SYS_BEEP; five-byte values remain pointer-backed and fractional pitch is preserved.
3. **Files/artifacts created or modified:** libc48/sound.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.26`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Compile/link/run the exact mandatory and fractional/octave vectors; return is 0 on success and positive errno on failure, with five-byte operands unchanged across the C48/syscall boundary.
9. **Negative/failure test:** Invalid ROM numeric domain maps to positive errno without BASIC escape; a wrapper that returns before synchronous note completion or narrows the accepted pitch domain fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.26.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.27 - C48 tape/zxpack wrappers

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Expose only documented cassette/object/zxpack APIs; no fake random tape filesystem. The exact §25.8 public cassette/time surface owned here is `tape_save`, `tape_load`, `ticks`, `time_get`, `time_set`. These wrappers expose only the frozen tape and TIME1/u32 syscall semantics; they do not invent seekable tape, RTC persistence, timezone support or background I/O.
3. **Files/artifacts created or modified:** libc48/tape.asm; zxpack.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.27`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Representative calls exact. Compile/link/run all five names, including unset wall time, revision increment, tick wrap fixture, exact-case tape paths and controlled cassette error/cancel propagation.
9. **Negative/failure test:** Random tape seek API absent.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.27.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.28 - Compiler OBJ1 writer

1. **Purpose / REV11 requirement:** §25
2. **Exact implementation work:** Emit deterministic valid OBJ1 for text/BSS/symbols/relocs; no direct MEX output shortcut.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.28`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Host inspector exact.
9. **Negative/failure test:** Malformed internal state never committed.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.28.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.29 - Compiler transactional output

1. **Purpose / REV11 requirement:** §25, §57
2. **Exact implementation work:** Write unique temp object then atomic rename; syntax/allocation/rename failure preserves previous .obj. `cc` accepts exactly one C-typed input. Default form requires exact lower-case final `.c`, removes only that suffix and appends `.obj` within 10-byte namespace limit; otherwise exact `cc -o out.obj source` is required. Output type is explicit OBJ. Emit through O_CREATE|O_EXCL `/tmp/.cc<pid>.<n>`, close/validate complete OBJ1, then atomic SYS_RENAME; compile/allocation/rename failure leaves any prior output byte-identical and no suffix ever causes kernel type inference.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.29`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Fault injection each stage.
9. **Negative/failure test:** Any destination hash change blocks. Wrong input type, uppercase/missing `.c` default form, output >10 bytes, temp E_EXIST, compile failure, allocation failure and rename failure all preserve prior output and unknown temps.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.29.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.30 - Portable documented-opcode scanner

1. **Purpose / REV11 requirement:** §2.8, §38, §57
2. **Exact implementation work:** Disassemble/scan generated code for undocumented opcodes and forbidden IY/shadow ownership.  The scanner treats any portable C48-generated instruction that writes/re-purposes IY as forbidden except an explicitly architecture-owned OS/runtime boundary outside ordinary generated C48 code; portable application code never owns alternate registers either.
3. **Files/artifacts created or modified:** compiler host tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.30`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** All goldens pass documented Z80 baseline.
9. **Negative/failure test:** Inject undocumented opcode and fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.30.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.31 - Codegen JR/DJNZ opportunities

1. **Purpose / REV11 requirement:** §2.8, §57
2. **Exact implementation work:** Implement the mandatory C48 Z80-native control-flow selections explicitly: use `DJNZ` for suitable counted 8-bit loops; `JR Z/NZ/C/NC` for local control flow when the target is in range; conditional `RET` when it safely eliminates a branch; and jump-table dispatch through `JP (HL)` only where size/range analysis proves a win. Correctness and the C48-visible register/flag contract remain primary. Do not use `DJNZ` when B is live for another purpose or loop semantics differ; out-of-range JR must use a correct documented fallback.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.31`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden code bytes prove selected DJNZ, JR Z/NZ/C/NC, conditional RET and JP(HL) cases plus semantically identical fallback cases.
9. **Negative/failure test:** Out-of-range JR falls back correctly.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.31.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.32 - Bit/rotate/16-bit codegen

1. **Purpose / REV11 requirement:** §2.8, §57
2. **Exact implementation work:** Implement the mandatory C48 Z80-native data-operation selections explicitly: `ADD HL,rr`, `ADC HL,rr`, and `SBC HL,rr` for suitable 16-bit operations; `EX DE,HL` for legal register-pair exchange/renaming; `BIT`, `SET`, and `RES` for bitfields/boolean flags; and documented rotate/shift instructions for power-of-two and bit-manipulation operations. Use them only where their flags/register effects preserve exact C48 semantics; portable codegen never emits undocumented opcodes.
3. **Files/artifacts created or modified:** cc.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.32`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden opcode sequences + runtime results.
9. **Negative/failure test:** Signedness mismatch caught.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.32.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.33 - Block primitive codegen/runtime

1. **Purpose / REV11 requirement:** §2.8, §57
2. **Exact implementation work:** Implement the mandatory block-instruction choices explicitly: use `LDIR`/`LDDR` for eligible copies/moves with correct overlap direction and `CPIR`/`CPDR` for eligible byte searches, sharing the canonical P1.40 primitive policy. Do not assume block operations are optimal for tiny fixed-size copies; measured unrolled loads may win. Include contended-memory placement in measurement, preserve C48-visible flags/registers, and test interruption/restart because repeated block instructions are interruptible between iterations. Portable codegen never emits undocumented block aliases/opcodes.
3. **Files/artifacts created or modified:** cc.asm; libc memory
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.33`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Golden and interrupted copy/search fixtures prove LDIR/LDDR direction, CPIR/CPDR searches, tiny-copy fallback, contended/uncontended semantic identity, and preserved C48-visible state.
9. **Negative/failure test:** Precise contention timing never required.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.33.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.34 - `sizeof`/alignment/array stride suite

1. **Purpose / REV11 requirement:** §25, §57
2. **Exact implementation work:** Freeze exact data-model compile/runtime outputs.  Test the literal C48 data model: char/unsigned-char sizeof1 align1; short/unsigned-short sizeof2 align2; int/unsigned-int sizeof2 align2; pointer sizeof2 align2; float sizeof5 align1; plain char unsigned; no distinct signed-char type; arrays have no inter-element padding and stride exactly sizeof(element); globals/locals insert only minimum table-required padding; sizeof yields unsigned int; signed short/int are two-complement; void is valid only as function return/pointer base, not an object. Cross-check all scalar arguments occupy 16-bit C48_REGCALL slots, char is zero-extended, and SP is even at every call boundary.
3. **Files/artifacts created or modified:** compiler tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.34`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** char1 short/int/pointer2 float5, alignments exact.  Compile/runtime goldens verify sizeof values, alignment addresses, array strides including float[2] stride5 and int[2] stride2, minimum struct-free local/global padding, plain-char 0x80->128, sizeof result type behavior, 16-bit argument slots and even SP across 0..6 argument calls.
9. **Negative/failure test:** Host compiler intuition must not override spec.  Host ABI padding/alignment, signed plain char, float alignment2/4, array rounding, 8-bit stack argument slots, or odd-SP call boundaries fail the C48 ABI oracle.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.34.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.35 - hello.c target-native lifecycle

1. **Purpose / REV11 requirement:** §57
2. **Exact implementation work:** Compile hello.c on Spectrum with cc, link with ld built-in archive, run.
3. **Files/artifacts created or modified:** demos/hello.c; tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.35`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** No host participates in runtime compile/link; output hello exact.
9. **Negative/failure test:** Wrong-case source lookup fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.35.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.36 - Graphics/UDG C program

1. **Purpose / REV11 requirement:** §57
2. **Exact implementation work:** Compile/link/run representative C48 graphics/UDG program.
3. **Files/artifacts created or modified:** demos/colors.c or dedicated fixture
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.36`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Screen/UDG result exact.
9. **Negative/failure test:** No direct kernel-memory write.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.36.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.37 - Pipe-aware C program

1. **Purpose / REV11 requirement:** §57
2. **Exact implementation work:** Compile/link/run C48 program using process/pipe APIs.
3. **Files/artifacts created or modified:** demos/pipe.c
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.37`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** True bounded pipe behavior.
9. **Negative/failure test:** Broken pipe handled.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.37.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.38 - Every shipped demo compiles/links

1. **Purpose / REV11 requirement:** §42, §57
2. **Exact implementation work:** Compile all 13 required lower-case .c sources with target cc and ld.
3. **Files/artifacts created or modified:** src/demos/*.c
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.38`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every source -> OBJ1 -> MEX1 passes inspectors.
9. **Negative/failure test:** Any precompiled-only demo fails gate.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.38.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.39 - Compiler complete golden suite

1. **Purpose / REV11 requirement:** §57 acceptance
2. **Exact implementation work:** Run the native language, ABI, float, heap, codegen, error-transaction and demos suite AND import/run the complete test corpus from the pinned Python C48 SDK. Preserve the imported SDK test files byte-for-byte where possible, record their hashes and source commit, copy all required fixtures/support, run the copied `compiler/run_tests.py`/release gate from this repository, and maintain a mechanical mapping from every imported SDK test to the target-native C48 behavior it constrains. No imported failure may be converted to skip/xfail or have its expectation weakened for admission.
3. **Files/artifacts created or modified:** `v1/tests/compiler/`; `v1/tests/compiler/sdk-reference/`; SDK provenance/hash/test-mapping records
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.39`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All native exact outputs/status/hashes pass with known nondeterminism=none; the complete copied SDK corpus also passes from the ZX-UX repository at the pinned test count (205 for baseline `84d144de2721cda5075c3a6610a422663b5e2f77`), and every imported SDK test has a passing target-native mapping or a documented host-only adapter that still checks the original C48 intent.
9. **Negative/failure test:** One intentionally wrong native expected result must fail the harness. Deleting, skipping, xfail-marking, weakening, silently editing, or leaving unmapped any imported SDK test must also fail the compiler golden-suite gate.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.39.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.40 - Compiler simultaneous residency/20KiB gate

1. **Purpose / REV11 requirement:** §44, §41.3
2. **Exact implementation work:** Measure the compiler complete process-owned live footprint—image+BSS, FAST stack, immutable ARG1/ENV1 bootstrap allocation, and compiler-internal dynamic workspace—at <=20480 bytes and prove real arena coexistence with shell, packed-reader state, pinned resources, and hello source/output. Compiler image/BSS may occupy or cross CONTENDED RAM because normal MEX1 placement is ANY; only its process stack is guaranteed FAST_REQUIRED. Compiler source/backing RAM objects use the object store COLD_PREFERRED policy and `cc` has no private placement syscall. A memory-short launch/compile must fail recoverably and expose a clear `not enough memory for compiler` diagnostic rather than crashing; freeing nonessential RAM objects and retrying is allowed.
3. **Files/artifacts created or modified:** memory certification test
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.40`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All FAST_REQUIRED allocations are satisfied; the <=20480 live-footprint measurement is physical, placement policy matches REV11, and the memory-short path reports `not enough memory for compiler` without corruption; no paper-only total.
9. **Negative/failure test:** Heap8192 or packed hello stress that cannot fit must fail recoverably, not corrupt.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.40.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.41 - Built-in c48.h contract

1. **Purpose / REV11 requirement:** §25, §41.9
2. **Exact implementation work:** Implement and freeze the built-in `<c48.h>` declarations required by the C48 runtime/syscall/library surface as a compiler-resident declaration table inside `cc.asm`, documented in `c48.md`. Compilation must not require a second library/header tape or a physical `c48.h` target file; declarations must match the frozen ABI and case-sensitive C48 names.
3. **Files/artifacts created or modified:** `v1/src/tools/cc.asm`; `v1/docs/c48.md`; compiler header tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.41`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every declared prototype/type agrees byte-for-byte with the generated-call ABI and links through the normal built-in runtime/archive path.
9. **Negative/failure test:** Mutate one prototype/type/ABI declaration in a negative fixture; compile/link or ABI oracle must fail rather than accepting drift.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.41.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.42 - Compiler error and resource-boundary matrix

1. **Purpose / REV11 requirement:** §41.9
2. **Exact implementation work:** Create explicit compile-error reporting and bounded-resource tests for syntax/semantic failure, symbol-table overflow, source too large, output-memory exhaustion, compiler workspace exhaustion and final rename failure. Every failure preserves any previous destination OBJ byte-identically.
3. **Files/artifacts created or modified:** `v1/tests/compiler/`; compiler transaction tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.42`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Each required failure is deterministic, reports failure, leaks no compiler-owned allocation/open description and preserves the prior output object.
9. **Negative/failure test:** A deliberately swallowed compiler error or a one-byte prior-output change must fail the harness.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.42.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.43 - PACKED C source streaming equivalence

1. **Purpose / REV11 requirement:** §41.9; ZXP1/object invariants
2. **Exact implementation work:** Compile the same C source once as RAW and once as a PACKED C RAM object through ordinary read calls. The compiler must consume the transparent logical stream without whole-file materialization; packed-reader state is kernel-owned and continuous as required.
3. **Files/artifacts created or modified:** `v1/tests/compiler/packed_source.*`; compiler/object/zxpack integration
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.43`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** RAW and PACKED source produce byte-identical OBJ1; PACKED compile never allocates a second whole uncompressed source copy and frees decoder state on final close.
9. **Negative/failure test:** Instrument a forbidden whole-file materialization or perturb one decoded byte; residency/hash oracle must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.43.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.44 - Recursion and control-flow stack-budget runtime

1. **Purpose / REV11 requirement:** §25, §41.9
2. **Exact implementation work:** Compile and run bounded recursive functions plus while/do/for, break/continue, short-circuit logical operators and returns under the documented process-stack budget. Recursive acceptance is bounded by the configured stack; it is not permission for unchecked stack growth.
3. **Files/artifacts created or modified:** `v1/tests/compiler/recursion_control.c`; compiler runtime tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.44`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Valid recursion/control flow returns exact results without corrupting ARG1/ENV1, heap, IY or adjacent allocations; stack evidence remains within the test budget.
9. **Negative/failure test:** Use an intentionally undersized stack/depth fixture and require controlled failure/test detection rather than silent overwrite.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.44.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.45 - Complete Section-41.9 compiler acceptance matrix

1. **Purpose / REV11 requirement:** §41.9
2. **Exact implementation work:** Run one explicit matrix covering every version-1 operator; scalar/array initializers; int<->float casts; signed/unsigned comparison; pointers; arrays; globals; locals; REGCALL 0..6; five-byte float arguments and hidden-result returns; recursion; loops; logical operators; string literals; built-in `<c48.h>`; standard runtime resolution by `ld`; syscalls; graphics; UDG; pipe I/O; compile diagnostics; symbol-table overflow; source-too-large; output-memory exhaustion; and RAW-versus-PACKED source OBJ1 identity. Extend the matrix with one enumerated admission row for every copied test in the pinned Python SDK `compiler/tests/` corpus, recording the original SDK test name/hash, the target-native mapping/adapter, and the target evidence that closes the same C48 expectation.
3. **Files/artifacts created or modified:** `v1/tests/compiler/section41_9.py`; `v1/tests/compiler/sdk-reference/`; `v1/dist/certification/P11.45-sdk-map.json`; `v1/dist/certification/P11.45.*`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.45`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every Section-41.9 requirement and every imported SDK test has a passing, traceable row; no generic “compiler suite passed” result may substitute for a missing native or SDK-derived row.
9. **Negative/failure test:** Delete or invert one required row, remove one SDK test mapping, or change an imported SDK expected result merely to match native behavior; the aggregate must fail and name the uncovered/incorrect contract.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.45.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.46 - SYS_FP_TO_TEXT exact ABI

1. **Purpose / REV11 requirement:** §10.1, §14, §25.8-25.9
2. **Exact implementation work:** Implement the exact `SYS_FP_TO_TEXT` Section-10.1 register/packed-buffer contract using the Phase-0-approved ROM numeric formatting gateway. Validate all user pointers/capacities first and return deterministic bounded target bytes; this is the small floating formatter foundation, not general printf. Exact registers are HL=five-byte value, DE=destination buffer, BC=capacity. Success writes the ROM-canonical decimal rendering plus terminating NUL and returns HL=text bytes excluding NUL; if capacity including NUL is insufficient return E_NOSPC with no partial destination mutation.
3. **Files/artifacts created or modified:** `v1/src/kernel/rom_services.asm`; `v1/src/kernel/syscall.asm`; FP/text ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.46`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Formatted bytes/count/status match the REV11 ABI; no partial write on insufficient/invalid destination; IY/calculator state restored.
9. **Negative/failure test:** One-byte-short buffer, protected/wrapped pointer and forced ROM error must leave output guards and calculator ownership intact.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.46.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.47 - SYS_FP_FROM_TEXT exact ABI

1. **Purpose / REV11 requirement:** §10.1, §14, §25.8-25.9
2. **Exact implementation work:** Implement the exact `SYS_FP_FROM_TEXT` Section-10.1 input/output contract using the Phase-0-approved numeric parser/conversion gateway. Accept only the bounded numeric text grammar authorized by the syscall; validate source/destination ranges before ROM entry and never expose BASIC statement/expression execution. Exact registers are HL=text pointer, DE=five-byte output, BC=exact text length; input need not be NUL terminated. Accept exactly one decimal numeric literal with no whitespace/BASIC tokens: optional leading +/-, then either digits with optional dot and zero-or-more following digits OR dot followed by one-or-more digits, then optional e/E exponent with optional sign and at least one digit. At least one mantissa digit is mandatory; anything else is E_INVAL with output unchanged.
3. **Files/artifacts created or modified:** `v1/src/kernel/rom_services.asm`; `v1/src/kernel/syscall.asm`; FP/text ABI tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.47`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Exact five-byte target value and status are produced for valid input; malformed or unsafe input fails atomically with no BASIC escape or destination mutation.
9. **Negative/failure test:** Attempt BASIC token/statement text, malformed numeric text or wrapped range and require controlled rejection.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.47.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P11.48 - Phase-11 acceptance gate

1. **Purpose / REV11 requirement:** §57, §44
2. **Exact implementation work:** Aggregate the full target-native C48 lifecycle, all demos, documented opcodes, IY/alternate bank, REGCALL/float, data model, archive, heap, transactions and tune beep. Admission additionally requires the pinned Python SDK design-reference provenance, a complete copied `compiler/tests/` corpus with runner/fixtures/support, a clean pass of that copied corpus from this repository, and a complete passing target-native mapping for every SDK C48 expectation. No compiler is certified merely because native smoke tests pass while the SDK admission corpus is missing, modified, skipped, or red.
3. **Files/artifacts created or modified:** Phase11 evidence; `v1/tests/compiler/sdk-reference/`; `v1/dist/certification/P11.48-sdk-admission.json`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P11.48`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Every Phase11 bullet PASS; SDK source commit/provenance is recorded; the copied SDK corpus is complete and hash-accounted; every imported SDK test passes; every SDK-derived C48 expectation has a passing target-native mapping; and the native compiler/runtime suite passes independently.
9. **Negative/failure test:** Any missing demo/compiler feature, missing/altered SDK test, SDK test failure, skipped/xfail admission test, missing SDK provenance, unexplained SDK/REV11 difference, or unmapped SDK C48 expectation blocks Phase 11.
10. **Check-in gate:** build + static + positive + negative tests PASS; the complete copied SDK admission corpus and all target-native mappings PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P11.48.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# Phase 12 - Integrated Multiprocessing Development Environment

## P12.01 - Finalize all 13 demo sources

1. **Purpose / REV11 requirement:** §42, §58
2. **Exact implementation work:** Freeze and test all thirteen readable lower-case C48 source/precompiled-MEX1 pairs with their distinct REV11 proof roles: `hello.c` is the canonical §42.1 first program with exactly `int main(void)`, a body containing `puts("hello");` followed by `return 0;`, and supports on-target vi -> cc -> ld -> execute; `colors.c` displays INK/PAPER plus BRIGHT/FLASH through the OS attribute API without direct ROM calls; `lines.c` uses plot/draw/circle as the simple ROM-backed graphics proof; `ship.c` keeps editable UDG byte definitions easy to find, reads keyboard input, moves the ship, changes attributes and uses sound/timing; `ball.c` animates an integer-coordinate bouncing ball with edge collision, yield/timing and optional beeper feedback; `stars.c` animates an integer starfield using plot or a documented direct-bitmap path and stresses loops/arrays/non-security pseudorandom values/Z80-native codegen; `life.c` implements Conway Life, preferably 32x24, exercising arrays, neighbor calculation, UDGs, keyboard input and repeated cooperative yields; `maze.c` generates/displays an integer-algorithm maze using UDG wall pieces, with optional keyboard navigation if memory permits; `sine.c` plots a sine wave using C48 float and the serialized ROM calculator; `mandel.c` renders a small Mandelbrot set with visible progress and clean cooperative behavior even when slow; `tune.c` plays a short user-modifiable tune through C48 `beep`, keeps pitch/duration data plainly visible, and includes at least one fractional-pitch note; `pipe.c` streams stdin/stdout through real bounded RAM pipes and its golden `pipe | grep 7 | wc` path exercises at least three simultaneously existing cooperative tasks; `multi.c` visibly demonstrates multiple yielding tasks and also documents/proves that a deliberately non-yielding variant starves peers because scheduling is cooperative, not preemptive. Every source and executable name remains lower-case/case-sensitive; source remains educational/editable rather than micro-optimized.
3. **Files/artifacts created or modified:** src/demos; dist/system
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.01`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All thirteen named source/executable pairs exist in lower case, compile/link on target, return cleanly where intended, and demonstrate their distinct required behavior; interactive loops yield; `sine` uses ROM-backed float math; `tune` includes fractional pitch; `pipe` proves >=3 tasks; `multi` proves cooperative progress and non-yielding starvation without claiming preemption.
9. **Negative/failure test:** Remove one demo/source pair, change case, alter the canonical `hello.c` entry signature/`puts("hello");`/`return 0;` program contract, substitute a precompiled-only demo, bypass the required API/feature proof, omit the fractional-pitch note or >=3-task pipeline, or let a non-yielding `multi` peer continue as if preempted; the §42 demo matrix fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.01.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.02 - Finalize demo runner

1. **Purpose / REV11 requirement:** §33, §42, §58
2. **Exact implementation work:** Implement/freeze `demo` exactly: with no argument print every available lower-case demo executable and matching source filename; with one exact lower-case demo name, ensure the matching source and precompiled executable are resident in current `/home/<user>` using normal interactive forward cassette loading only for missing pair members, preserve and use an already-existing pair member of the expected exact type (including user edits), refuse with an explanatory message if an existing same-name member has the wrong type, do not run if either required pair member fails validation/load, then spawn the precompiled executable and wait. Never silently overwrite a resident pair member and never case-fold (`demo SHIP` must not alias `demo ship`). Print a concise rebuild hint equivalent to `vi ship.c ; cc ship.c ; ld ship.obj -o ship ; ship`.
3. **Files/artifacts created or modified:** utils/demo.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.02`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Listing contains exact lower-case executable/source pairs; only missing members trigger interactive tape load; correct resident objects are preserved byte-for-byte; wrong-type collisions refuse; failed pair validation never launches; named success runs the precompiled executable, waits, and prints the rebuild hint.
9. **Negative/failure test:** Overwrite a resident edited source, load tape for an already-present member, run after one pair member failed validation, accept a wrong-type collision, omit source names/rebuild hint from discovery, or case-fold `demo SHIP`; each must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.02.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.03 - Finalize BCAT exact 40 entries

1. **Purpose / REV11 requirement:** §4.3B, §5.1, §20.5, §58
2. **Exact implementation work:** Generate exact sorted 40-name required external-command set including sh; 488 bytes, flags01, BIN, no duplicates.
3. **Files/artifacts created or modified:** assets/bincat.bin
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.03`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Host parser exact names/order/length; boot pins COLD.
9. **Negative/failure test:** Missing/extra/unsorted/duplicate/case mismatch rejects release.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.03.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.04 - Finalize issue and crontab frozen bytes

1. **Purpose / REV11 requirement:** §5.1, §58
2. **Exact implementation work:** Freeze the official `issue` logical target bytes exactly as `<0x7F> Supratim Sanyal, SANYALnet Labs<LF>`, `https://supratim-sanyal.blogspot.com/<LF>`, `48K. One Z80. No excuses.<LF>`, including the leading target byte 0x7F and final LF; freeze `crontab` as exactly zero bytes RAW.
3. **Files/artifacts created or modified:** assets/issue.txt; crontab.txt; generated target assets
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.04`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Independent hash/byte checks.
9. **Negative/failure test:** UTF-8 © bytes passed raw to target instead of 0x7F rejected.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.04.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.05 - Finalize font4x8 F4X8 resource

1. **Purpose / REV11 requirement:** §4.3A, §58
2. **Exact implementation work:** Freeze exact 392-byte validated resource with 96 glyphs and copyright at 0x7F rendering.
3. **Files/artifacts created or modified:** assets/font4x8.bin
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.05`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Header/data length/hash; tty64 goldens.
9. **Negative/failure test:** Bad glyph count blocks release.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.05.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.06 - Finalize sh release MEX1

1. **Purpose / REV11 requirement:** §5.1, §58
2. **Exact implementation work:** Replace any Phase5 stub with final shell binary; exact BIN->BIN and bootstrap PID1 contract.
3. **Files/artifacts created or modified:** dist/system/sh
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.06`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** MEX inspector + boot.
9. **Negative/failure test:** Stub marker/fixture hash forbidden.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.06.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.07 - Final reference system tape manifest order

1. **Purpose / REV11 requirement:** §19.8, §58
2. **Exact implementation work:** Freeze the complete immutable order explicitly: zx48ux, zx48uxscr, kernel, sh, font4x8, issue, crontab, bincat; then cron, crontab, vi, as, cc, ld, ls, cat, echo, cp, mv, rm, pack, unpack, hexdump, grep, wc, head, tail, cmp, true, false, sleep, which, env, stty, date, man, whoami, uname, uptime, cal, fortune, banner, rev, yes, udg, gfxdemo, demo; then hello.c/hello, colors.c/colors, lines.c/lines, ship.c/ship, ball.c/ball, stars.c/stars, life.c/life, maze.c/maze, sine.c/sine, mandel.c/mandel, tune.c/tune, pipe.c/pipe, multi.c/multi. Validate all command/tool MEX1 objects as BIN->BIN, demo .c sources as C->USERHOME, and demo executables as BIN->USERHOME. No tuning/reordering allowed.
3. **Files/artifacts created or modified:** maketap manifest; docs
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.07`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Independent manifest checker compares every entry/type/target/name.
9. **Negative/failure test:** Swap two later tools => release failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.07.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.08 - Byte-exact final production tape build

1. **Purpose / REV11 requirement:** §5.6, §19.8, §58
2. **Exact implementation work:** Build release TAP and TZX twice from identical canonical inputs; this is first phase allowed to call it byte-exact final reference tape.
3. **Files/artifacts created or modified:** dist/system/
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.08`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Two builds hashes identical; FUSE-utils inspect; TZX->TAP logical equivalence where tool semantics permit.
9. **Negative/failure test:** Any fixture/stub resource detected blocks release.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.08.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.09 - Final cold boot 29-step ownership/resource sequence

1. **Purpose / REV11 requirement:** §5.5, §41.1, §58
2. **Exact implementation work:** From reset use only ordinary `LOAD ""` and prove the exact post-0xE003 sequence in order: (1) DI; (2) SP=0xFD00; (3) validate 48K environment and kernel at 0xE000-0xFFFF; (4) validate 0xE000/0xE003 trampolines; (5) establish IY=0x5C3A; (6) normalize only documented ROM variables/workspace, never blanket-clear 0x5B00-0x5FFF; (7) clear kernel BSS/state without display/ROM-workspace/stack/vector damage; (8) initialize FAST and CONTENDED arena free lists; (9) initialize process and pipe tables; (10) initialize RAM-object directory; (11) initialize resident ZXP1 manager plus zero four-byte pack-candidate bitset; (12) initialize ROM cassette wrapper and M48O bootstrap reader; (13) initialize graphics/ULA-shadow/default attributes without clearing SCREEN$; (14) allocate one pinned 256-byte COLD_PREFERRED 32-slot UDG bank, initialize all 32 slots, repoint ROM UDG at 23675-23676 to that bank and record/prove the exact pointer; (15) fill 0xFE00-0xFF00 with 0xFD; (16) install `JP zx48_interrupt` at 0xFDFD; (17) set I=0xFE; (18) select IM 2; (19) initialize alternate-register/ROM-interrupt protection state; (20) create PID0 idle/kernel context; (21) construct cold PID1 ARG1 `{sh}` and zero-entry ENV1, then load/validate lower-case M48O `sh` RAW or continuous-history PACKED directly without persistent `/bin/sh` RAM object; (22) load/validate `font4x8`, decoding PACKED transport directly to final pinned 392-byte FAST_REQUIRED F4X8 allocation; (23) load `issue` into `/etc/issue` and validate required bytes/lines; (24) load `crontab` into `/etc/crontab` and validate empty/syntax state; (25) load/validate `bincat`, decoding PACKED transport directly to final pinned COLD BCAT metadata; (26) initialize tty64 from font4x8; (27) instantiate PID1 with cwd ROOT, canonical ARG1/ENV1, one tty read open description for handle0, one tty write description shared by handles1/2, `tty_input_owner_pid=1`, and proven refcounts/ownership before scheduling; (28) execute EI only after trampolines/resources/ownership bounds are validated; (29) enter the cooperative scheduler. Retain one numbered state/evidence row for every action.
3. **Files/artifacts created or modified:** release boot test; `v1/tests/cassette/boot_final.py`; `v1/dist/certification/P12.09-boot-sequence.json`
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.09`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** All twenty-nine numbered checkpoints occur in REV11 order on the same final release tape; debugger/RAM/object/open-description assertions prove each state transition and prove `EI` occurs only after the IM2 table/trampoline, boot trampolines, `sh`, `font4x8`, `issue`, `crontab`, `bincat`, and ownership/refcount bounds are valid.
9. **Negative/failure test:** Delete, reorder, merge-away, or skip any checkpoint; enable interrupts before checkpoint 28; corrupt/mistype/mistarget any bootstrap resource; create persistent `/bin/sh` during bootstrap; give PID1 wrong cwd/ARG1/ENV1/tty topology/refcounts; or allow failure to fall into BASIC/uninitialized RAM: the boot gate must fail safely.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.09.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.10 - Final login/session demonstration

1. **Purpose / REV11 requirement:** §58 items4-8, §63
2. **Exact implementation work:** Exact issue, login, environment, pwd, stty64/cursor, namespace, man output.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.10`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Character/output/object state exact.
9. **Negative/failure test:** Invalid login/case lookups negative.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.10.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.11 - Final date/cron demonstration

1. **Purpose / REV11 requirement:** §58 item9
2. **Exact implementation work:** Prove date unset, valid set, and one @boot or calendar job as applicable; no calendar run while unset.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.11`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Time/job state exact.
9. **Negative/failure test:** Tape/tty interactive prompt from cron forbidden.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.11.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.12 - Final vi/cc/ld/hello lifecycle

1. **Purpose / REV11 requirement:** §58 item10
2. **Exact implementation work:** Locate/load hello.c, edit with vi, cc, ld, run entirely on target.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.12`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Output exact; artifacts valid.
9. **Negative/failure test:** Wrong-case source fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.12.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.13 - Final case-sensitivity demonstration

1. **Purpose / REV11 requirement:** §58 item11
2. **Exact implementation work:** Show incorrect-case command/object does not alias lower-case.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.13`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Explicit failing lookup captured.
9. **Negative/failure test:** If alias succeeds release fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.13.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.14 - Final real pipeline/background demonstration

1. **Purpose / REV11 requirement:** §58 item12
2. **Exact implementation work:** Run true multi-stage pipeline and cooperative background task with tty ownership/refcounts correct.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.14`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** No deadlock; status/jobs exact.
9. **Negative/failure test:** Parent retained writer/background tty steal fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.14.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.15 - Final UDG/ROM state demonstration

1. **Purpose / REV11 requirement:** §58 item13
2. **Exact implementation work:** Define/use UDG and prove ROM UDG pointer outside kernel/IM2.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.15`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Bank bytes/pointer exact.
9. **Negative/failure test:** Pointer overlap fails release.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.15.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.16 - Final ship edit/rebuild demonstration

1. **Purpose / REV11 requirement:** §58 item14
2. **Exact implementation work:** demo ship, edit ship.c, target compile/link, run rebuilt ship.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.16`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Rebuilt output/behavior executes.
9. **Negative/failure test:** Precompiled binary without compile path not acceptable.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.16.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.17 - Final sine and multi demonstrations

1. **Purpose / REV11 requirement:** §58 item15
2. **Exact implementation work:** Compile/run sine.c as ROM-float proof and multi.c as cooperative multiprocessing proof.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.17`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Math/task outputs exact.
9. **Negative/failure test:** Host-built substitution forbidden.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.17.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.18 - Final beep/fun-command demonstration

1. **Purpose / REV11 requirement:** §58 item16
2. **Exact implementation work:** Run required beep examples incl fractional pitch; fortune/banner/cal/rev; cancel yes cleanly.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.18`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Return/status/tty state exact.
9. **Negative/failure test:** Long beep clock gap not falsely backfilled.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.18.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.19 - Final zxpack demonstration

1. **Purpose / REV11 requirement:** §58 item17
2. **Exact implementation work:** pack/unpack, mem -c, compile transparent packed source, direct packed-MEX1 tape execution; show logical/physical accounting.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.19`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Bytes and accounting exact.
9. **Negative/failure test:** Live-process compression guard remains zero violations.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.19.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.20 - Final cassette logical round trip

1. **Purpose / REV11 requirement:** §58 item18, §42.15
2. **Exact implementation work:** Save source+executable+one UDG set, reset/power-cycle, normal boot, reload exact lower-case names, verify CRCs, execute program.
3. **Files/artifacts created or modified:** release scenario
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.20`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Restored CRCs and execution exact.
9. **Negative/failure test:** Incorrect-case request fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.20.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.21 - Companion word design and implementation

1. **Purpose / REV11 requirement:** §19.9, §58
2. **Exact implementation work:** Freeze docs/word.md and ordinary lower-case MEX1 word using tty64/object/cassette APIs; create/edit/save/reopen TXT object.
3. **Files/artifacts created or modified:** docs/word.md; apps-companion/word.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.21`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Functional target scenario.
9. **Negative/failure test:** No privileged/private kernel dependency.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.21.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.22 - Companion sheet design and implementation

1. **Purpose / REV11 requirement:** §19.9, §58
2. **Exact implementation work:** Freeze docs/sheet.md and ordinary lower-case MEX1 sheet using tty64; create/save/reopen sheet and recompute + - * / formula.
3. **Files/artifacts created or modified:** docs/sheet.md; apps-companion/sheet.asm
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.22`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Functional target scenario.
9. **Negative/failure test:** No private ABI.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.22.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.23 - Deterministic companion cassette

1. **Purpose / REV11 requirement:** §19.9, §58
2. **Exact implementation work:** Build nonbootable M48O stream first word then sheet, both BIN->BIN exact lower-case.
3. **Files/artifacts created or modified:** dist/companion/
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.23`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Two builds byte-identical; target explicit load installs /bin apps.
9. **Negative/failure test:** Wrong first-two order/type fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.23.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.24 - Kernel and tool size gates

1. **Purpose / REV11 requirement:** §44
2. **Exact implementation work:** Measure exact screen/kernel/subranges and every §44 tool/resource target. Independently measure/map the complete REV11 §4.2 ordinary-kernel code/data planning ledger: syscall gateway/entry 128 bytes; scheduler/process/open-description 896; allocator 448; pipe subsystem 640; ROM wrappers 704; console/keyboard/ULA + tty64 832; graphics primitives 608; UDG subsystem 192; cassette object layer 672; RAM object namespace 640; resident zxpack codec/manager 384; interrupt/time/error core 448; tables/strings 192; exact planning total 6784 with exactly 128 bytes unassigned inside the 6912-byte ordinary 0xE000-0xFAFF pool. Do not borrow 0xFD00-0xFDFC or 0xFF01-0xFFFF as ordinary growth space. Then perform the required real simultaneous-residency proof: shell image+BSS+stack + complete <=20480-byte compiler process-owned footprint + any kernel-owned packed-reader state used for a PACKED hello.c + pinned font/UDG/BCAT resources + mandatory hello.c source/output objects must coexist in the actual 32 KiB arena with every FAST_REQUIRED allocation honored. Every over-target tool or §4.2 category needs concrete measured-memory proof, never a paper total or a shrug.
3. **Files/artifacts created or modified:** size report
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.24`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** screen=6912; kernel=8192; pool<=6912. The measured §4.2 ledger contains all thirteen exact planning targets 128/896/448/640/704/832/608/192/672/640/384/448/192, totals exactly 6784, and demonstrates exactly 128 bytes unassigned in the 6912-byte ordinary pool without reserve borrowing. zxpack resident codec/manager target<=384 bytes of ordinary kernel code/data, explicitly excluding arena-owned per-open 272-byte decoder states and transient exactly 512-byte encoder workspace while keeping both visible to allocator/mem accounting; if the resident target cannot be met while preserving the codec checks, require an architecture revision rather than borrowing IM2, kernel-stack or reserve regions. sh<=4096; simple utility target<=2048 each; vi<=8192; as<=12288; ld<=8192; compiler process-owned live footprint<=20480; font=392 FAST_REQUIRED; UDG=256 COLD_PREFERRED; BCAT<=512 COLD_PREFERRED; required simultaneous-residency scenario fits the 32 KiB arena with FAST_REQUIRED honored.
9. **Negative/failure test:** Artificially exceed fixed kernel boundary => hard fail. A missing/mislabeled §4.2 category, any changed target, total other than 6784, less than 128 bytes unassigned margin, or use of FD00-FDFC/FF01-FFFF to hide ordinary code/data growth also blocks release.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.24.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.25 - Kernel stack final worst-case gate

1. **Purpose / REV11 requirement:** §35.1, §44
2. **Exact implementation work:** On the final release-linked image, repeat the exact §35 worst-case proof from SP=0xFD00 over syscall entry/dispatcher, nested kernel helpers, allocator/object/pipe error paths, ROM wrapper entry/exit, ROM error-recovery trampoline, each invoked ROM routine's documented maximum stack, an IM2 interrupt at every interruptible point using the larger ISR preservation path, all return addresses/temporary pushes, and debug/release depth differences. Verify normal syscall stack switch/process-SP capture, task-frame materialization before saved_sp commit on blocking paths, no process-stack scratch use, rejection of any ROM service without a bounded maximum stack, the frozen 0xFB00-0xFB0F guard checks at every kernel-to-user/ROM-wrapper return, measured depth <=448 bytes and >=64 bytes untouched.
3. **Files/artifacts created or modified:** stack report
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.25`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Final report enumerates every §35 depth contributor and proves high-water<=448, >=64 untouched margin, intact guard, correct stack-switch/frame ordering, and zero enabled unbounded-stack ROM services.
9. **Negative/failure test:** Guard damage PANIC KSTACK.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.25.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.26 - Full Section-41 mandatory matrix

1. **Purpose / REV11 requirement:** §41
2. **Exact implementation work:** Execute every numbered/bulleted boot,scheduler,memory,MEX/OBJ,zxpack,object,pipe,cassette,graphics,shell,vi,compiler/demo test exactly; retain machine-state evidence. Include explicit widened-address/length adversarial rows for syscall user ranges, MEX1, OBJ1, M48O and ZXP1 so 16-bit wrap can never turn an invalid range/object valid. Include the valid cross-boundary case `0x7FF0 + 0x0020` as a positive control.  Add a release-wide ABI-freeze provenance row: every ABI-visible number, packed record, binary format, fixed ID, fixed offset and fixed byte contract claimed frozen by REV11 must point to an executable conformance test that existed before the implementation step freezes/exports that contract; missing test-before-freeze provenance is a matrix failure. The exact §41 replay ledger in §5.5 contains 228 literal mandatory rows; the release matrix must execute all 228 rows by stable row identity with zero missing, duplicate, merged-away, skipped, or unowned rows.
3. **Files/artifacts created or modified:** certification matrix
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.26`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Zero unrun/skip/xfail unless REV11 itself marks conditional and evidence explains condition. All §41 rows plus cross-format wrap vectors execute; invalid wrapping cases reject before access/commit and the valid cross-boundary control succeeds exactly.  The matrix also proves allocation failure remains recoverable at system level, including foreground allocation failure returning control to a usable shell, and proves every frozen ABI-visible number/format has test-before-freeze evidence. The retained replay result contains exactly 228 §41 row IDs and every one maps back to the §5.5 ledger and its owning phase evidence.
9. **Negative/failure test:** Delete one matrix row => certification script fails completeness.  Remove the conformance-test provenance for one frozen ABI field, or inject one foreground E_NOMEM path that kills/corrupts the shell; the release matrix must fail. Renumber, drop, duplicate, or merge any §5.5 acceptance row and require the completeness oracle to fail before release certification.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.26.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.27 - Second independent emulator pass

1. **Purpose / REV11 requirement:** §40.3
2. **Exact implementation work:** Run release-critical boot/tape/process/pipeline/graphics subset on second emulator and compare observable machine state/outputs.
3. **Files/artifacts created or modified:** compat report
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.27`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic TAP/TZX artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** No emulator-specific correctness assumption discovered.
9. **Negative/failure test:** Mismatch remains open defect.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.27.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.28 - Physical EAR boot gate

1. **Purpose / REV11 requirement:** §40.4
2. **Exact implementation work:** On real 48K-compatible hardware or hardware-faithful EAR/MIC loop, play final release audio/cassette path and boot via ROM timing; record hardware/source and result.
3. **Files/artifacts created or modified:** dist/certification/hardware
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.28`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** FUSE may be used only as regression evidence; it cannot close this hardware/analog gate.
7. **Exact FUSE assertions/checkpoints:** Not sufficient for PASS. Record real 48K-compatible hardware or hardware-faithful EAR/MIC-loop evidence.
8. **Expected PASS result:** Boot reaches shell with correct resources.
9. **Negative/failure test:** TAP-only evidence cannot satisfy this gate.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.28.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.29 - Physical MIC save/load gate

1. **Purpose / REV11 requirement:** §40.4, §58
2. **Exact implementation work:** Exercise real/hardware-faithful MIC save and EAR reload/verify for representative object/source/executable; include BREAK/error recovery.
3. **Files/artifacts created or modified:** hardware evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.29`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** FUSE may be used only as regression evidence; it cannot close this hardware/analog gate.
7. **Exact FUSE assertions/checkpoints:** Not sufficient for PASS. Record real 48K-compatible hardware or hardware-faithful EAR/MIC-loop evidence.
8. **Expected PASS result:** Saved object reloads CRC-exact and executable runs.
9. **Negative/failure test:** Emulator trap-only result not accepted as analog certification.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.29.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.30 - Version-1 definitive 20-step acceptance

1. **Purpose / REV11 requirement:** §58 acceptance
2. **Exact implementation work:** Run all 20 Phase12 acceptance items in exact order from powered/reset target and official production tape.  Execute the definitive Phase-12 gate as twenty explicit ordered checks from a powered/reset 48K configuration and the official production tape: (1) verify the production tape's complete object order and frozen release-asset bytes match Sections 5.1 and 19.8, then type only `LOAD ""` and press PLAY; (2) verify BASIC auto-start, exact SCREEN$ load, kernel load and permanent 0xE003 handoff; (3) verify exact bootstrap M48O resources `sh`, `font4x8`, `issue`, `crontab`, `bincat` load and validate before PID1; (4) verify tty64 line 1 is exactly `© Supratim Sanyal, SANYALnet Labs` and line 2 exactly `https://supratim-sanyal.blogspot.com/`; (5) enter a valid <=8-character username and verify `$USER`, `$HOME`, `$SHELL`, `$PATH`, `pwd`, `/home/<user>` and `/etc/issue`; (6) show `stty` reports 64x24 and cursor control works; (7) prove `/bin`, `/etc`, `/dev`, `/home`, `/tmp`, `.`, `..` and exact-case PATH lookup; (8) run `man` and verify the exact website plus `Search for ZXUS`; (9) show `date` unset behavior, set a valid wall clock, and execute one `@boot` or calendar cron/crontab job as applicable; (10) load/locate `hello.c`, edit with `vi`, compile with `cc`, link with `ld`, and run `hello`; (11) prove incorrect-case lookup does not alias the lower-case command/object; (12) run a true multi-stage pipeline and a cooperative background task; (13) define/use UDGs and verify ROM UDG state points outside kernel/IM2 memory; (14) run `demo ship`, edit/rebuild `ship.c`, and run rebuilt `ship`; (15) compile/run `sine.c` as ROM-floating-point proof and `multi.c` as cooperative-multiprocessing proof; (16) run `beep .5,0`, `beep .25,-12`, and a fractional-pitch note, then representative `fortune`, `banner`, `cal`, `rev`, and cancel `yes` cleanly; (17) prove `pack`, `unpack`, `mem -c`, transparent packed-source compilation, and direct packed-MEX1 tape execution with logical/physical accounting; (18) save source and executable to cassette, power-cycle/reset, repeat standard boot, restore them, verify CRCs, and execute the restored program; (19) load the companion applications cassette and prove ordinary lower-case tty64 `/bin` MEX1 applications `word` and `sheet`, with `word` create/edit/save/reopen TXT and `sheet` create/save/reopen a small sheet and recompute at least one `+ - * /` arithmetic formula as frozen in their docs; (20) verify all operations remain within the 48K memory architecture. The gate is ordered and complete; no later item excuses an earlier failure.
3. **Files/artifacts created or modified:** final acceptance log/video-state hashes where useful
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.30`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** FUSE may be used only as regression evidence; it cannot close this hardware/analog gate.
7. **Exact FUSE assertions/checkpoints:** Not sufficient for PASS. Record real 48K-compatible hardware or hardware-faithful EAR/MIC-loop evidence.
8. **Expected PASS result:** Every item PASS; all within 48K.  The final acceptance record has exactly twenty numbered rows in REV11 order, each with target-state/evidence references, and all twenty PASS on the same official release tape and 48K candidate.
9. **Negative/failure test:** Any failed item means no release.  Omit/reorder/skip any of the twenty checks, satisfy a physical cassette requirement only with emulator evidence, or exceed the 48K architecture at any point; the version-1 architecture gate fails.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.30.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.31 - Section-63 success demonstration

1. **Purpose / REV11 requirement:** §63
2. **Exact implementation work:** Run the narrative definitive demo command sequence and cassette roundtrip; verify no host participates in runtime workflow.  Prove every Section-63 success capability explicitly, without a host participating in the runtime workflow: ordinary `LOAD ""`; auto-running tiny BASIC bootstrap; native 6912-byte SCREEN$; exact 8192-byte kernel at 0xE000; permanent 0xE003 handoff; ordered validation of `sh,font4x8,issue,crontab,bincat`; tty64 `sh` without BASIC return; exact issue heading and valid login; start in `/home/<user>` with `PATH=/bin:.`; lower-case case-sensitive command lookup; exact-case user object names; fixed path resolution for `/bin,/etc,/dev,/home/<user>,/tmp`; volatile named objects; eligible inactive ZXP1 PACKED storage with exact logical reads; cassette save/restore of RAW or PACKED objects; relocatable executable programs; multiple cooperative tasks; true bounded-buffer pipelines; `vi`; native Z80 assembly; linking; useful C48 compilation; tty64 software cursor/bitmap graphics/color attributes/BASIC-compatible beep/basic sound/UDGs; `date` and cron/crontab and web-directed `man`; safe ROM calculator from shell/C48; C48 floating-point mathematics; discover/run shipped demos; edit/rebuild shipped demo source locally; save a locally produced program to cassette; power-cycle/reset; boot again with ordinary `LOAD ""`; restore the saved program; run it again. Then execute the definitive transcript beginning at reset and retain the literal output checkpoints, not merely the command names: `LOAD ""`; after boot tty64 shows exactly `© Supratim Sanyal, SANYALnet Labs`, `https://supratim-sanyal.blogspot.com/`, `48K. One Z80. No excuses.`, then `login: fred`; `$ pwd` followed by exactly `/home/fred`; `$ stty` followed by exactly `cols 64 rows 24 cursor underline`; `$ man` followed by at least the exact lines `Manuals: https://supratim-sanyal.blogspot.com/` and `Search for ZXUS`; `$ date` followed by exactly `date: not set`; `$ date -s "2026-09-06 12:00:00"`; `$ demo hello` followed by exactly `hello`; `$ vi hello.c`; `$ cc hello.c`; `$ ld hello.obj -o hello`; `$ hello` followed by exactly `hello`; `$ pack hello.c`; `$ mem -c`; `$ cc hello.c`; `$ unpack hello.c`; `$ save hello`; `$ calc "sin(pi/4)*100"`; `$ beep .25,0`; `$ beep .25,0.5`; `$ demo ship`; `$ vi ship.c`; `$ cc ship.c`; `$ ld ship.obj -o ship`; `$ ship`; `$ pipe | grep 7 | wc`; `$ multi`; `$ fortune`; `$ ps`; `$ mem`; also show one incorrect-case command/object lookup fails. End with the real cassette round trip: save locally produced source/executable, reset/power-cycle, standard boot, reload, CRC-verify, execute again.
3. **Files/artifacts created or modified:** final demo evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.31`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** FUSE may be used only as regression evidence; it cannot close this hardware/analog gate.
7. **Exact FUSE assertions/checkpoints:** Not sufficient for PASS. Record real 48K-compatible hardware or hardware-faithful EAR/MIC-loop evidence.
8. **Expected PASS result:** All architecture success capabilities demonstrated.  Every enumerated Section-63 capability and every command/transcript checkpoint is present in the retained final demonstration evidence; no host performs target compile/link/runtime work, and the ending restored program executes after the second ordinary `LOAD ""` boot.
9. **Negative/failure test:** Host-assisted target compile/link invalidates this gate.  Missing one Section-63 capability/transcript checkpoint, accepting an incorrect-case alias, host-assisted target compile/link, or omitting the real post-reset cassette restore/execute sequence fails the success demonstration.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.31.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.32 - Deferred-feature scope guard

1. **Purpose / REV11 requirement:** §59
2. **Exact implementation work:** Static/document review proves v1 did not smuggle in preemption, MMU/fork/paging/swap/VM/general dirs/network/128K/AY/full POSIX/full ISO C/etc as claimed requirements.  The exact version-1 exclusions are all individually guarded: true preemptive multitasking; MMU-style process isolation; fork(); demand paging; swap; virtual memory; transparent compression of live/sleeping process address spaces or stacks; general user-created directory trees beyond the fixed hierarchy; random-access tape filesystem fiction; networking; Microdrive; Interface 1; printer; mouse; 128K bank switching; AY sound; dynamic libraries; full POSIX; full ISO C; per-process virtual screens; GUI/window manager. No `etc.` or catch-all may substitute for these 21 explicit exclusions.
3. **Files/artifacts created or modified:** scope report
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.32`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Out-of-scope list remains explicitly deferred.  The scope report contains and checks all 21 exclusions one-by-one and distinguishes them from allowed stretch goals without turning a stretch goal into a version-1 contract.
9. **Negative/failure test:** An accidental public ABI claim for deferred feature blocks release.  Delete or silently implement/advertise any one of the 21 exclusions as a v1 requirement/ABI feature; the release scope gate must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.32.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.33 - Documentation completeness gate

1. **Purpose / REV11 requirement:** §36, §37, §58
2. **Exact implementation work:** Finalize all architecture-listed documentation and generated constants, and state the REV11 §36 fault boundary explicitly: ZX-UX has no MMU or memory protection; mandatory syscall pointer/range validation, image-header/relocation/object-length/pipe-state/cassette-header-and-CRC/process-ownership checks protect against accidental misuse but cannot protect the kernel from deliberately malicious machine code that writes directly to kernel RAM. No ABI-mandated validation may be removed as an optimization. Keep source-tree/layout documentation exact and distinguish target-runtime requirements from host-only tooling.
3. **Files/artifacts created or modified:** v1/docs/*.md
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.33`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** All architecture-listed docs exist and match generated constants; §36 limitations and validation obligations are stated without implying protection the 48K machine cannot provide.
9. **Negative/failure test:** Stale numeric ABI/path data, omission of any mandatory validation class, claim of memory protection/MMU, or wording that says malicious machine code is contained causes documentation certification failure.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.33.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.34 - Final deterministic distribution manifest

1. **Purpose / REV11 requirement:** §5.6, §19.8-19.9, §58
2. **Exact implementation work:** Hash all release artifacts, test evidence, source/demo pairs and companion image; exclude credentials/developer helper auth and disposable build. Perform a release-wide user-facing naming audit over every shipped shell command, builtin, tool, executable, demo name and demo/source filename. Every ZX-UX-shipped user-facing name must be lower-case exactly; preserve case-sensitive user-created names separately. The audit must explicitly distinguish allowed non-filename conventions such as environment-variable names, ABI/constants, binary magics, Z80/ROM symbols, Sinclair BASIC bootstrap keywords and external vendor filenames so it does not invent a broader architecture rule.
3. **Files/artifacts created or modified:** dist/certification/manifest.json
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.34`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** Rebuild from clean source yields same release artifact hashes. The clean release manifest contains zero uppercase/mixed-case ZX-UX-shipped user-facing command/tool/executable/demo/source names; all permitted non-filename exceptions are classified, not silently ignored.
9. **Negative/failure test:** Any path outside root or secret-like auth material rejected. Inject one mixed-case shipped demo source or command filename and require the manifest/naming audit to fail even if hashes otherwise reproduce.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.34.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.35 - Final clean-worktree/check-in gate

1. **Purpose / REV11 requirement:** handover Git rule
2. **Exact implementation work:** Use the host's pinned Git implementation; ensure all source/docs/evidence intended for release are committed and the worktree is clean. developer helper is not a build dependency.
3. **Files/artifacts created or modified:** repository state
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.35`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** `git status --porcelain` empty after final release commit.
9. **Negative/failure test:** Untracked generated release artifact blocks certification.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.35.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.36 - Cross-subsystem concurrency-invariants stress gate

1. **Purpose / REV11 requirement:** §29; §41; invariants 23,25,29,32,39,55,71,92,99,111,133-135
2. **Exact implementation work:** Execute one adversarial release-candidate stress matrix that proves all twelve Section-29 rules together, not merely in isolated unit tests: (1) mask interrupts around kernel data visible to ISR; (2) task-level kernel calls are non-reentrant unless explicitly designed so; (3) no task switch while an internal kernel invariant is transient; (4) link a process to its wait object before publishing BLOCKED; (5) unlink wait state before publishing READY; (6) pipe read/write/close state changes are scheduler-atomic; (7) the global tape lock excludes concurrent cassette operations; (8) graphics remain one shared display rather than automatic per-process virtualization; (9) every return to MEX1 has IY=0x5C3A; (10) fast alternate-register ISR path is impossible while altreg_busy!=0; (11) the IM2 vector table/trampoline remain immutable after boot except inside an explicit interrupt-reconfiguration critical section; (12) FAST_REQUIRED allocation never spills into contended RAM. Stress the rules across yields, wakeups, BREAK, pipe endpoint close, ROM wrappers, allocator pressure and tape blocking on the same build.
3. **Files/artifacts created or modified:** `v1/tests/emulator/concurrency_invariants.*`; kernel/scheduler/pipe/tape/graphics evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.36`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** Debugger/event-log assertions show every BLOCKED transition already linked, every READY wake already unlinked, no scheduler entry inside transient critical state, exact pipe/tape exclusion, canonical IY, correct altreg path selection, unchanged vector/trampoline hashes and FAST-only FAST_REQUIRED allocations throughout the combined stress run.
9. **Negative/failure test:** Inject one fault for each of the twelve rules (including publish-BLOCKED-before-link, READY-before-unlink, vector byte mutation and deliberate FAST spill); the corresponding oracle must fail deterministically rather than letting the final aggregate remain green.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.36.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.37 - Shared-screen foreground ownership gate

1. **Purpose / REV11 requirement:** §30; invariant 55
2. **Exact implementation work:** Prove the final system has exactly one physical Spectrum display at 0x4000-0x5AFF shared by all processes. A foreground program that directly writes bitmap/attribute RAM bypasses console synchronization and MUST set the tty software cursor shape OFF through `/dev/tty` before changing any cell that may contain the cursor; it may restore the desired cursor only after the raw update completes. If it ignores this rule, screen/cursor contents are explicitly unspecified until the next console clear/mode reset; the kernel cannot enforce raw writes because there is no MMU/write trapping. Ordinary background programs must not perform raw display writes unless explicitly acting as a shared UI service under an application-level ownership protocol. No process receives an automatic virtual screen and no kernel per-process 6912-byte screen allocation exists. Foreground exit/cancel restores shell tty/cursor ownership; voluntary save/restore of screen bytes is ordinary user-memory behavior, never OS virtualization.
3. **Files/artifacts created or modified:** `v1/tests/emulator/shared_screen.*`; shell/tty/graphics evidence
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.37`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** Generate/run the smallest deterministic SNA artifact that exercises only this contract plus already-frozen prerequisites.
7. **Exact FUSE assertions/checkpoints:** Use debugger breakpoints, registers, RAM/expression assertions and deterministic process exit; no screenshot-only PASS.
8. **Expected PASS result:** The same single hardware display is shared throughout; ordinary background work receives no automatic display virtualization, and shell/tty screen ownership is restored exactly when the foreground task exits or is cancelled.
9. **Negative/failure test:** Instrument a fake per-process virtual display allocation or let a normal background task obtain automatic display ownership; either must fail the ownership/allocation oracle.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.37.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.38 - Release performance measurement gate

1. **Purpose / REV11 requirement:** §43
2. **Exact implementation work:** Measure and retain evidence for all seven REV11 performance targets on the final correctness-qualified build without turning qualitative targets into invented ABI numbers: (1) shell key echo is interactively immediate; (2) context-switch overhead is small relative to one 50 Hz tick; (3) `ls` over 32 RAM objects appears effectively immediate; (4) small-buffer pipe streaming makes progress without deadlock; (5) native `hello.c` compilation completes in a practical interactive interval; (6) graphics-wrapper overhead is not excessive relative to the approved ROM/direct rendering path; (7) Spectrum-compatible cassette transport time is recorded but is not misclassified as a kernel performance defect. Record raw timings/counters, test setup and comparison basis. Optimize only after a measured bottleneck, and rerun correctness before accepting any optimization.
3. **Files/artifacts created or modified:** `v1/dist/certification/performance.json`; timing harness/tests
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.38`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** N/A: this is a host-only contract/format/policy step; target behavior is closed by later dependent steps.
7. **Exact FUSE assertions/checkpoints:** N/A except where the host test deliberately launches a timeout/argv self-test.
8. **Expected PASS result:** All seven rows contain measured final-build evidence and the correctness suites remain unchanged/green; context-switch timing is compared with the 20 ms PAL frame period, and pipe progress/deadlock is a correctness prerequisite rather than a speed score.
9. **Negative/failure test:** Delete a target row, substitute an unmeasured adjective for data, treat cassette transport compatibility as a kernel failure, or accept an optimization that changes correctness evidence; the gate must fail.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.38.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.

## P12.39 - Phase-12 release gate

1. **Purpose / REV11 requirement:** §58, §§40-44, §63
2. **Exact implementation work:** Aggregate final tape byte identity, complete test matrix, second emulator, real hardware/cassette-equivalent, size/stack, demos, companion apps, documentation and deterministic manifest.
3. **Files/artifacts created or modified:** final certification bundle
4. **Build command:** `<project-local-python> v1/tools-host/test-driver/run.py build --step P12.39`.
5. **Host-side static checks:** root-marker/path policy, architecture constants used by this step, file/format sizes, duplicate/forbidden symbols or literals, and deterministic artifact hashes as applicable.
6. **Emulator test artifact:** FUSE may be used only as regression evidence; it cannot close this hardware/analog gate.
7. **Exact FUSE assertions/checkpoints:** Not sufficient for PASS. Record real 48K-compatible hardware or hardware-faithful EAR/MIC-loop evidence.
8. **Expected PASS result:** Emit `ZX-UX VERSION 1 ARCHITECTURE CERTIFICATION PASS` only if every required prerequisite is PASS.
9. **Negative/failure test:** No waiver may silently strengthen evidence; failed physical gate remains FAILED/PENDING, never emulator-PASS.
10. **Check-in gate:** build + static + positive + negative tests PASS; dependent earlier phase gates remain PASS; commit only the intended source/docs/evidence and end with a clean Git worktree.
11. **Evidence:** `v1/dist/certification/P12.39.log` plus hashes/debugger-state/result JSON; phase aggregate evidence is added at phase gates.


---

# 5. Architecture-Coverage Ledger

This ledger is normative for the implementation plan. A section may map to multiple
steps; a shared foundational step is allowed only when it explicitly names the shared
contract. No Revision-11 requirement may be left to implication.

| REV11 section | Primary implementation/certification coverage |
|---|---|
| §1 Purpose | P12.30 definitive acceptance; P12.31 no-host-runtime success demonstration; P12.39 release gate |
| §2 Design Principles | E0.05-E0.06 project rules/testing; P0 ROM-first proof; P1 cooperative/shared-memory kernel; P4 RAM-object model; P6 shell; P10-P11 native toolchain; P12.32 deferred-scope guard; P12.39 release gate |
| §3 Hardware Baseline | P0.01 hardware/memory/contention constants; P0 keyboard/ROM/tape/graphics/sound proofs; P1 IM2/ULA ownership; P12.27-P12.29 compatibility/physical gates |
| §4 Fixed Version-1 Memory Map | P0.01-P0.04 fixed map/trampolines/IM2 reservations; P0.10 bootstrap resource contracts; P1.01-P1.05 arena/accounting; P1.14 boot-pinned 256-byte COLD_PREFERRED UDG bank/ROM UDG pointer; P1.21 pinned 392-byte FAST_REQUIRED F4X8; P12.03 BCAT exact 40/488-byte resource; P12.05 final F4X8; P12.24-P12.25 size/stack and simultaneous-residency gates |
| §5 Boot Model | P0.07-P0.14 BASIC/SCREEN$/kernel/handoff/failure proof; P0.10 five-resource prefix contract; P1/P2/P3/P4/P5/P6 component prerequisites; P5 fixture tape; P12.03-P12.06 final frozen bootstrap resources; P12.07-P12.09 final tape and literal 29-step post-handoff boot sequence; P12.10 session handoff; P12.30 definitive boot acceptance |
| §6 Kernel Execution Model | P1 scheduler/ISR/ticks/time/process skeleton; P2 process lifecycle/context; P3 blocking/waits/pipes; P6 tty ownership/cancellation; P12.36 concurrency stress |
| §7 Process Creation and Program Loading | P2.04-P2.24 relocation/load/spawn/exec/wait/kill/context/ARG1/ENV1; P4 packed-resident executable path; P5 direct packed-MEX1 tape execution; P12 process tests |
| §8 Executable Format | P2.01-P2.04 exact MEX1 header/inspector/relocation/load; P2.05-P2.08 process-owned stack/bootstrap allocation, ARG1, ENV1 and initial entry-register contract; P2 format negatives; P10.32 final MEX1 writer; P5 packed direct execution |
| §9 Kernel Call ABI | P1.09 exact syscall/register/errno ABI freeze; every syscall implementation preserves the fixed return/register contract; P11 generated/runtime syscall wrappers preserve IX/IY/alternate-register rules; P12.26 ABI matrix |
| §10 Version-1 Syscall Table | exact 59-syscall ownership ledger; P1/P2/P3/P4/P7 implementations and packed-record tests; P11 public runtime wrappers; P12.26 full ABI/test replay |
| §11 Handles and I/O | P3.01-P3.07 open descriptions/handles/tty/null/dup; P3.15 READ/WRITE validation; P3.20 IOCTL ABI; P4 object/device open semantics; P6 redirection/handle rollback |
| §12 Pipes | P3.08-P3.14 and P3.17-P3.18 bounded pipe allocation/lifetime/blocking/EOF/E_PIPE; P6 foreground pipelines; P8 pipeline/error matrix; P12.14/P12.36 integrated stress |
| §13 Keyboard, Console, 64-Column Text, Cursor, and ULA Port Discipline | P0 keyboard/console proofs; P1 tty64/tty32/cursor/ULA/BREAK gates; P3.20 exact tty IOCTL ABI; P6 tty owner/input; P7 attribute integration; P8.23 public `stty` modes/cursor utility; P12 tty/shared-screen gates |
| §14 ROM Services Layer | P0.15-P0.31 provenance/inventory/exact ROM address table/A-B-C classes/wrapper/error/calculator/calc/system-variable contracts; P1.14 FRAMES+boot UDG compatibility plus P1 ISR/ULA integration; P7 final graphics/sound/calc/rom services; P11 FP bridge |
| §15 Graphics Architecture | P0 graphics proofs; P7.01-P7.08 graphics ABI/wrappers/attributes/bounds; P7.19 golden graphics; P11 graphics runtime; P12 demos/shared-screen gate |
| §16 User-Defined Graphics (UDGs) | P0.31 ROM UDG-state ownership; P1.14 boot-time pinned bank/repoint; P7.13-P7.17 UDG subsystem/syscalls/2x2/UDG1 persistence; P8 udg utility; P12 UDG demos/cassette round trip |
| §17 Sound and BASIC-Compatible `beep` | P0 BEEPER/BEEP ROM proofs; P7.09 SYS_BEEP; P7.18 C48 ABI fixture; P7.20 exact shell builtin; P11 beep runtime/tune; P12 sound demonstration |
| §18 Volatile Object Store and Minimal Unix Namespace | P4.01-P4.15 fixed hierarchy/path/name/type/object-record and CRUD/open/rename/list/stat contracts; P4.24-P4.26 final-close packing candidates and bounded allocation-pressure compaction; P4.30-P4.32 exact fixed pseudo-directory/list/stat plus SYS_CHDIR/SYS_GETCWD; P6 exact shell path/PATH use; P8 object utilities; P12 namespace success proof |
| §19 Cassette Persistence | P0 SA-BYTES/LD-BYTES proof; P5.01-P5.19 exact M48O header/chunks/CRC/save/load/verify/scan, sequential-tape locks/prompts/recovery, and direct RAW/PACKED MEX1 streaming; P12.07-P12.09 byte-exact Section-19.8 reference system-tape manifest/build/boot; P12.21-P12.23 Section-19.9 word/sheet companion applications and deterministic nonbootable M48O stream; P12.28-P12.30 physical EAR/MIC/power-cycle cassette gates |
| §20 Shell, Login Session, Environment, and Core Command Surface | P6 login/environment/parser/builtins/PATH/redirection/jobs; P7 final ROM-backed builtins; P8 utilities/time/cron/man; P9 real vi/crontab integration; P12 session/command demonstration |
| §21 Cooperative Cancellation and kill | P2 kill/started-state/lifecycle; P6 foreground tty ownership/BREAK/kill/wait/jobs; P8 `yes` cooperative cancellation; P12 pipeline/background/concurrency tests |
| §22 vi Editor | P9.01-P9.24 complete modal/editor/transaction/documentation/size gates; P12 edit/rebuild workflow and cassette round trip |
| §23 Native Z80 Assembler | P10.01-P10.20 OBJ1 contracts/host inspector/parser/directives/symbols/full documented-Z80 encoding/transactional output; P10 acceptance |
| §24 Linker | P10.21-P10.36 deterministic module/archive layout/symbols/relocations/heap/stack/MEX1 writer/transaction/acceptance |
| §25 Tiny Native C Compiler | P11.01-P11.20 language/preprocessor/parser/codegen/data model/REGCALL/float rules plus compiler transaction/output; P11 compiler golden and native lifecycle |
| §26 Program Heap | P10.29 linker-reserved `__heap_start`/`__heap_end`; P10.31 exact `-heap` defaults/options; P11.21 BSS-only malloc/free heap; P11.40 residency proof |
| §27 RAM Allocator and Z80 Memory Primitives | P1.02-P1.05 arena allocator/FAST/COLD/ANY/accounting; P1.40 single canonical kernel/runtime memory/string primitive owner with LDI/LDIR, LDD/LDDR, CPI/CPIR, CPD/CPDR consideration, complete §27.2 consumer coverage, overlap-direction, measured small-copy and interruption/restart tests; P4.16-P4.28 ZXP1 codec/reader/packing/compaction/atomicity; P10/P11 codegen/runtime integration measurements; P12.24/P12.38 release memory/performance gates |
| §28 Interrupt Architecture - Z80 IM 2 | P0.04-P0.06 vector/trampoline/IY/alternate-register proof; P1 IM2 initialization/fast and ROM-safe paths/FRAMES/BREAK/cursor timing/correction matrices; P12.25/P12.36 release stress |
| §29 Concurrency Rules | P1 scheduler/ISR critical sections; P3 pipe state atomics; P5.12 tape lock; P6 launch/tty ownership; P12.36 exact 12-rule cross-subsystem stress gate |
| §30 Graphics Ownership Between Processes | P1 console/cursor ownership; P6 foreground tty/screen restoration; P7 shared graphics implementation; P12.37 explicit foreground/background/shared-screen ownership gate |
| §31 Shell Redirection and RAM Objects | P4 object growth/atomic replacement; P6 transactional redirection and append; P8 pipeline/error utilities; P12 command workflow |
| §32 Device and Fixed Filesystem Namespace | P3 tty/null/IOCTL device behavior; P4 fixed resolver and exact `/dev/tty` `/dev/null` `/dev/tape` open/stat/list semantics; P5 tape control; P6 PATH/direct path rules; P12 namespace proof |
| §33 Core Utilities Behavior | P6 final external `/bin/echo`; P7 ROM-backed interactive builtins; P8.01-P8.40 one-step utility contracts/integration; P12 representative utility/demo execution |
| §34 Error and Panic Model | P0.14 panic output/safe halt; P0 ROM error/recovery classification; P1 corruption/allocator/process/stack panic checks; P5 recovery; P12 final negative/recovery gates |
| §35 Kernel Stack | P0 fixed stack reservation/boot SP; P1.28 guard/high-water instrumentation and P1.33 correction matrix; P12.25 production worst-case <=448-byte gate |
| §36 Security and Fault Model | widened pointer/range/format/ownership validation across P1-P5/P10-P11; negative mutation/atomicity tests; P12.33 documents no-MMU/shared-address limitation explicitly |
| §37 Development Source Tree | E0.03 creates/checks the canonical tree; every target source/header artifact is one of the Section-37 entries (including no separate path/devices/time/layout modules and no physical c48.h); plan-defined additions are confined to host tests/evidence; P12.33 documentation completeness |
| §38 Assembly and Z80 Coding Rules | E0.05 coding-rule freeze; P0 ROM-address centralization/magic-address checks; P1 IY/alternate-register/ULA rules; P10 full documented-Z80 assembler coverage; P11 portable codegen/opcode/register gates |
| §39 Host Bootstrap Toolchain | E0.03/E0 host runner; P0 deterministic BASIC/SCREEN$/kernel maketap and host ZXP1 reference; P2/P10 inspectors; P12 deterministic production/companion builders and manifests |
| §40 Testing Strategy | E0.06 four-level test/evidence policy; all atomic host/SNA/TAP/TZX tests with timeouts; P12.27 second emulator; P12.28-P12.29 real hardware/hardware-faithful cassette gates |
| §41 Mandatory Test Matrix | owning phase tests/correction matrices plus P12.26 complete Section-41 replay; P12.27 compatibility-emulator pass and physical gates where evidence class requires them |
| §42 Golden Acceptance and Shipped Demo Programs | P11.38 all 13 demo sources compile/link; P12.01 final 13 source/executable matrix; P12.02 demo runner; P12 edit/rebuild/demo and P12 cassette round-trip tests |
| §43 Performance Targets | measured phase evidence where applicable plus P12.38 exact seven-target release measurement gate; performance never overrides correctness |
| §44 Size Gates | P0/P1 fixed map/kernel; P9.24 editor; P10.36 assembler/linker; P11.40/P11.48 compiler/residency; P12.24 all release sizes and simultaneous residency; P12.25 stack |
| §45 Programming Cycle | this plan enforces E0 then P0->P12 in order, with a red phase gate blocking every later phase |
| §46 Phase 0 - Hardware, ROM Inventory, and ROM Proof | P0.01-P0.34 including all 17 literal acceptance checks and repeated zero-gap ROM scan |
| §47 Phase 1 - Resident Kernel Skeleton | P1.01-P1.41 including fixed kernel/allocator/process/IM2/tty/time, canonical Z80 memory/string primitives, correction matrices and acceptance |
| §48 Phase 2 - Processes and Loader | P2.01-P2.24 including MEX1/relocation/spawn/exec/wait/reaping/context/ARG1/ENV1 and acceptance |
| §49 Phase 3 - Generic I/O and Pipes | P3.01-P3.21 handles/open descriptions/console/null/pipes/dup/READ-WRITE-IOCTL ABI and acceptance |
| §50 Phase 4 - RAM Object Store and Fixed Unix Namespace | P4.01-P4.33 namespace/object CRUD/rename/open/list/stat/ZXP1/packing/compaction and acceptance |
| §51 Phase 5 - Cassette Object Layer | P5.01-P5.19 M48O/CRC/chunks/save-load-verify-scan/tape lock/fixture acceptance; fixture explicitly cannot claim final release identity |
| §52 Phase 6 - Shell | P6.01-P6.30 login/environment/parser/PATH/builtins/external echo/redirection/pipelines/jobs/cancellation and acceptance |
| §53 Phase 7 - Graphics, Attributes, Sound, UDGs | P7.01-P7.21 graphics/attributes/sound/UDG/final ROM-backed builtins/golden acceptance |
| §54 Phase 8 - Core Utilities | P8.01-P8.40 all required utilities, echo regression, pipeline/status matrix, cron transaction, fixture integrations and acceptance |
| §55 Phase 9 - vi Editor | P9.01-P9.24 complete vi behavior/transaction/docs/real crontab integration/size acceptance |
| §56 Phase 10 - Native Assembler and Linker | P10.01-P10.36 OBJ1/as/ld/crt0/archive/transaction/size and target-native lifecycle acceptance |
| §57 Phase 11 - C48 Compiler | P11.01-P11.48 C48 language/preprocessor/compiler/runtime/float/heap/demos/residency/golden acceptance |
| §58 Phase 12 - Integrated Multiprocessing Development Environment | P12.01-P12.39 final demos/tapes/assets/integration/size/stack/matrix/emulator/physical/companion/docs/performance/release gates |
| §59 Deferred Features | P12.32 lists and rejects all 21 exact v1 exclusions; no deferred feature is claimed by an earlier step |
| §60 Stretch Goals | post-v1 only; no v1 implementation/check-in gate depends on a stretch goal and P12.32 prevents accidental promotion |
| §61 Architecture Invariants | exact 139-row invariant ownership ledger below; owning atomic tests plus P12.26/P12.36/P12.39 close release-wide interactions |
| §62 Architecture Review Checklist Before Coding Each Module | exact 41-question review template below; every module/check-in gate must retain concrete applicable answers before closure |
| §63 Definition of Version-1 Success | P12.31 literal capability and command-sequence proof; P12.30 definitive 20-step acceptance; P12.39 release closure |
| §64 Reference Notes | P0.15-P0.17 authoritative ROM provenance/address centralization; P0 routine contracts; P10/P11 documented-Z80/portable-code validation |
| §65 First Implementation Deliverable | exactly P0.01-P0.34; P0.34 blocks scheduler/pipes/full shell/compiler work until every Phase-0 acceptance item and repeated zero-gap ROM scan pass |

## 5.1 Section-61 invariant mapping

The invariant audit uses the **complete numbered invariant list in the canonical on-disk
REV11**, not a copied/retyped list in this document. This avoids creating a second
architecture that can drift. The mappings are:

- boot/native prefix/loading screen/permanent handoff/fixed addresses/IM2/IY: P0 + P1 + P12 boot;
- cooperative scheduling/no fork/context-on-FAST-stack/relocatable MEX1: P1 + P2;
- FAST_REQUIRED/ANY/pipes: P1 + P3 + Phase-12 residency;
- cassette sequential/M48O/blocking: P0 + P5 + physical P12;
- UDG/ROM centralization/Class A/B/C/system-variable ownership/ULA shadow: P0 + P1 + P7;
- lower-case/case-sensitive shell/tools/demos: P4 + P6 + P8-P12;
- vi: P9; C48 demos/compiler/REGCALL/documented Z80/five-byte float/BSS heap: P11;
- allocation recoverability/shared screen/ABI freeze/test-before-number-freeze: E0 + P1-P4 + P12;
- tty64/F4X8/login/home/PATH/issue/time/cron/man/BCAT: P1 + P6 + P8 + P12;
- ARG1/ENV1/process-name/background-stdin/SYS_OPEN typing: P2 + P4 + P6;
- ZXP1 RAW/PACKED exact semantics, 20-byte object record, exclusive writer,
  direct packed-MEX1, 32-bit accounting, atomic representation swaps and the explicit
  no-live-memory-compression rule: P4 + P5 + P8 + P12;
- exact final tape builder/order/assets and deterministic release: P12.

If any invariant in the canonical file cannot be placed into one of those concrete
steps with a test or a deliberate scope guard, the document certification is FAILED and
must restart after correction.

## 5.2 Explicit REV11 §61 Invariant Ownership Ledger

The invariant prose itself remains authoritative only in canonical REV11. This table is deliberately one row per numbered invariant so an audit cannot hide a missing item inside a broad category. Each listed step must contain a positive or negative proof, or an explicit scope guard, for that invariant.

| REV11 invariant | Owning implementation/test step(s) |
|---:|---|
| 1 | `P12.24,P12.30,P12.31` |
| 2 | `P0.01` |
| 3 | `P0.01,P7.02` |
| 4 | `P0.11,P12.08` |
| 5 | `P12.07,P12.08` |
| 6 | `P0.07` |
| 7 | `P0.08` |
| 8 | `P0.02,P12.24` |
| 9 | `P0.12` |
| 10 | `P0.12` |
| 11 | `P0.13,P12.09` |
| 12 | `P0.01` |
| 13 | `P0.01` |
| 14 | `P0.02` |
| 15 | `P0.03` |
| 16 | `P0.03` |
| 17 | `P0.02,P1.28` |
| 18 | `P0.04,P1.16-P1.17` |
| 19 | `P0.05,P1.29` |
| 20 | `P0.06,P1.30` |
| 21 | `P0.06` |
| 22 | `P0.06,P0.16` |
| 23 | `P1.12,P2.19` |
| 24 | `P12.32` |
| 25 | `P1.07,P2.08` |
| 26 | `P2.01-P2.04` |
| 27 | `P2.05` |
| 28 | `P1.03-P1.04,P2.04` |
| 29 | `P3.08` |
| 30 | `P5.09,P5.11,P5.13,P12.32` |
| 31 | `P5.01-P5.14` |
| 32 | `P5.12` |
| 33 | `P7.13-P7.16` |
| 34 | `P0.17` |
| 35 | `P0.16,P0.34` |
| 36 | `P0.16,P0.34` |
| 37 | `P0.26-P0.30,P11.17` |
| 38 | `P0.29,P12.32` |
| 39 | `P1.25,P7.08` |
| 40 | `P6.01,P8.01-P8.40,P9.01-P9.24,P10.01-P10.36,P11.01-P11.48` |
| 41 | `P4.01-P4.02,P6.14` |
| 42 | `P12.03,P12.34` |
| 43 | `P0.07,P12.34` |
| 44 | `P9.01-P9.24` |
| 45 | `P11.38,P12.01` |
| 46 | `P11.01` |
| 47 | `P1.29,P11.12-P11.16,P11.30` |
| 48 | `E0.05,P11.30` |
| 49 | `P11.14` |
| 50 | `E0.05,P11.33` |
| 51 | `E0.05,P0.01` |
| 52 | `E0.05` |
| 53 | `P12.32` |
| 54 | `P1.02-P1.05,P4.08,P12.26` |
| 55 | `P12.37` |
| 56 | `P1.09,P12.26` |
| 57 | `P0.09-P0.10,P12.08` |
| 58 | `P1.21-P1.24` |
| 59 | `P1.21,P12.09` |
| 60 | `P6.02` |
| 61 | `P6.03-P6.04` |
| 62 | `P4.01,P4.30,P6.04` |
| 63 | `P6.05-P6.06` |
| 64 | `P1.26-P1.27,P8.24` |
| 65 | `P8.25,P8.39` |
| 66 | `P6.02,P12.04` |
| 67 | `P8.27` |
| 68 | `P5.03` |
| 69 | `P1.14,P0.31,P7.13` |
| 70 | `P12.21-P12.23` |
| 71 | `P1.02-P1.04` |
| 72 | `P2.20` |
| 73 | `P2.06-P2.08` |
| 74 | `P11.13-P11.16` |
| 75 | `P6.23` |
| 76 | `P4.05` |
| 77 | `P11.21` |
| 78 | `P7.09,P7.20,P12.18` |
| 79 | `P1.09,P12.26` |
| 80 | `P4.04` |
| 81 | `P0.01,P1.13,P1.26` |
| 82 | `P4.16-P4.29,P12.32` |
| 83 | `P4.29,P12.19,P12.32` |
| 84 | `P4.03` |
| 85 | `P0.32-P0.33,P4.16-P4.28` |
| 86 | `P4.17-P4.18` |
| 87 | `P4.19` |
| 88 | `P4.06,P4.22-P4.23` |
| 89 | `P5.01-P5.05` |
| 90 | `P5.14` |
| 91 | `P0.02,P12.24` |
| 92 | `P4.06` |
| 93 | `P4.28` |
| 94 | `P4.27` |
| 95 | `P4.20` |
| 96 | `P4.24-P4.25` |
| 97 | `P4.27,P5.14` |
| 98 | `P5.06` |
| 99 | `P2.18-P2.19,P6.26` |
| 100 | `P11.40,P12.24` |
| 101 | `P6.01,P6.05,P6.21` |
| 102 | `P4.14-P4.15` |
| 103 | `P9.17-P9.18` |
| 104 | `P3.01,P3.05-P3.07` |
| 105 | `P4.05,P8.39,P9.17` |
| 106 | `P4.08` |
| 107 | `P5.09` |
| 108 | `P4.12,P4.30` |
| 109 | `P1.26-P1.27,P8.24,P8.39` |
| 110 | `P6.29` |
| 111 | `P1.15,P1.31,P6.26` |
| 112 | `P11.18-P11.19` |
| 113 | `P4.20,P4.26` |
| 114 | `P6.05-P6.14,P6.28` |
| 115 | `P3.03-P3.04,P3.20,P4.05,P4.30` |
| 116 | `P11.01,P11.08-P11.09,P11.12-P11.19,P11.34` |
| 117 | `P10.23-P10.26,P10.35` |
| 118 | `P6.01,P6.05,P6.22` |
| 119 | `P8.39` |
| 120 | `P9.02,P9.17-P9.19` |
| 121 | `P10.20,P10.33,P11.29` |
| 122 | `P10.19,P10.21,P10.33,P11.29` |
| 123 | `P10.29` |
| 124 | `P9.04,P8.28,P8.35` |
| 125 | `P12.03-P12.04` |
| 126 | `P6.14,P8.16` |
| 127 | `P2.03,P10.03` |
| 128 | `P10.29-P10.31` |
| 129 | `P7.16,P8.21` |
| 130 | `P5.15,P12.08` |
| 131 | `P1.29` |
| 132 | `P1.29,P2.08` |
| 133 | `P1.16,P1.30` |
| 134 | `P1.30` |
| 135 | `P1.15,P1.31` |
| 136 | `P1.32,P7.19` |
| 137 | `P1.28,P1.33,P12.25` |
| 138 | `P2.03,P3.19,P4.16,P5.01,P10.03,P12.26` |
| 139 | `P2.03,P3.19,P4.16,P5.01,P10.03,P12.26` |

## 5.3 Exact REV11 §§9.2-10 Syscall ABI and Ownership Ledger

The syscall gateway is fixed at 0xE000. Entry uses A=syscall number, HL=primary argument/pointer, DE=secondary argument/pointer and BC=count/tertiary argument. Success is Carry=0 with HL primary result and A=0 unless specifically documented otherwise. Failure is Carry=1 with A=errno and HL undefined unless specifically documented otherwise. AF/BC/DE/HL are volatile, IX is preserved, IY must be 0x5C3A on every returning user boundary, alternate registers are OS-private/volatile, I is OS-owned and R is not preserved. Invalid syscall numbers return E_NOTSUP without out-of-table indexing.

Frozen errno values are: `0 E_OK`, `1 E_INVAL`, `2 E_NOENT`, `3 E_NOMEM`, `4 E_BUSY`, `5 E_IO`, `6 E_EOF`, `7 E_PERM`, `8 E_CHILD`, `9 E_PIPE`, `10 E_TOOLONG`, `11 E_FORMAT`, `12 E_NOSPC`, `13 E_AGAIN`, `14 E_NOTSUP`, `15 E_INTR`, `16 E_EXIST`.

Every normal user range must be widened and proven wholly inside 0x4000-0x5AFF or 0x6000-0xDFFF before side effects; ROM, 0x5B00-0x5FFF, kernel RAM and wrapped ranges are invalid. Packed records are byte-packed little-endian, reserved bytes are zero, and ownership-specific calls additionally validate ownership/access. Each row below has a concrete implementation/test owner; a generic feature label is not accepted as coverage.

| ABI ID | Syscall | Owning implementation/test step(s) |
|---:|---|---|
| `0x00` | `SYS_VERSION` | `P1.10` |
| `0x01` | `SYS_EXIT` | `P1.19` |
| `0x02` | `SYS_YIELD` | `P1.12` |
| `0x03` | `SYS_SLEEP` | `P1.18` |
| `0x04` | `SYS_GETPID` | `P1.11` |
| `0x05` | `SYS_SPAWN` | `P2.09-P2.10` |
| `0x06` | `SYS_EXEC` | `P2.12` |
| `0x07` | `SYS_WAIT` | `P2.15-P2.16` |
| `0x08` | `SYS_KILL` | `P2.18-P2.19` |
| `0x10` | `SYS_OPEN` | `P4.05` |
| `0x11` | `SYS_CLOSE` | `P3.05` |
| `0x12` | `SYS_READ` | `P3.15,P4.07,P4.17` |
| `0x13` | `SYS_WRITE` | `P3.15,P4.08-P4.10` |
| `0x14` | `SYS_SEEK` | `P4.07,P4.18` |
| `0x15` | `SYS_STAT` | `P4.11,P4.30` |
| `0x16` | `SYS_REMOVE` | `P4.13` |
| `0x17` | `SYS_RENAME` | `P4.14-P4.15` |
| `0x18` | `SYS_LIST` | `P4.12,P4.30` |
| `0x19` | `SYS_CHDIR` | `P4.31` |
| `0x1A` | `SYS_GETCWD` | `P4.32` |
| `0x1B` | `SYS_PACK` | `P4.22` |
| `0x1C` | `SYS_UNPACK` | `P4.23` |
| `0x20` | `SYS_PIPE` | `P3.08` |
| `0x21` | `SYS_DUP` | `P3.06` |
| `0x22` | `SYS_IOCTL` | `P3.20` |
| `0x30` | `SYS_CON_GETKEY` | `P1.34` |
| `0x31` | `SYS_CON_PUTCHAR` | `P1.35` |
| `0x32` | `SYS_CON_WRITE` | `P1.36` |
| `0x33` | `SYS_CON_CLEAR` | `P1.37` |
| `0x34` | `SYS_CON_GETPOS` | `P1.38` |
| `0x35` | `SYS_CON_SETPOS` | `P1.39` |
| `0x40` | `SYS_GFX_PLOT` | `P7.03` |
| `0x41` | `SYS_GFX_DRAW` | `P7.04` |
| `0x42` | `SYS_GFX_CIRCLE` | `P7.05` |
| `0x43` | `SYS_GFX_ATTR` | `P7.07` |
| `0x44` | `SYS_GFX_BORDER` | `P7.08` |
| `0x45` | `SYS_GFX_POINT` | `P7.06` |
| `0x46` | `SYS_BEEP` | `P7.09` |
| `0x48` | `SYS_UDG_DEFINE` | `P7.14` |
| `0x49` | `SYS_UDG_DRAW` | `P7.15` |
| `0x4A` | `SYS_UDG_GET` | `P7.14` |
| `0x4B` | `SYS_UDG_CLEAR` | `P7.14` |
| `0x50` | `SYS_TAPE_SAVE` | `P5.07` |
| `0x51` | `SYS_TAPE_LOAD` | `P5.09` |
| `0x52` | `SYS_TAPE_VERIFY` | `P5.10` |
| `0x53` | `SYS_TAPE_SCAN` | `P5.11` |
| `0x60` | `SYS_MEM_INFO` | `P1.05` |
| `0x61` | `SYS_PROC_INFO` | `P2.21` |
| `0x62` | `SYS_TICKS` | `P1.13` |
| `0x63` | `SYS_TIME_GET` | `P1.27` |
| `0x64` | `SYS_TIME_SET` | `P1.27` |
| `0x65` | `SYS_ZXPACK_INFO` | `P4.28` |
| `0x68` | `SYS_FP_EXEC` | `P11.17` |
| `0x69` | `SYS_FP_TO_TEXT` | `P11.46` |
| `0x6A` | `SYS_FP_FROM_TEXT` | `P11.47` |
| `0x6B` | `SYS_ROM_INFO` | `P7.11` |
| `0x6C` | `SYS_INT_TO_FP` | `P11.18` |
| `0x6D` | `SYS_FP_TO_INT` | `P11.18` |
| `0x6E` | `SYS_FP_CMP` | `P11.19` |

## 5.4 Exact REV11 §25.8 C48 Runtime Ownership Ledger

REV11 freezes a 73-function minimum public C48 runtime. This table is one row per required public symbol so none can disappear inside the phrase "libc wrappers". The owning step must build the symbol into the linker built-in libc48 archive and execute a positive/negative target test for it.

| Public C48 function | Owning implementation/test step |
|---|---|
| `exit` | `P11.22` |
| `yield` | `P11.22` |
| `sleep` | `P11.22` |
| `spawn` | `P11.22` |
| `wait` | `P11.22` |
| `kill` | `P11.22` |
| `chdir` | `P11.22` |
| `getcwd` | `P11.22` |
| `getenv` | `P11.22` |
| `getpid` | `P11.22` |
| `open` | `P11.23` |
| `open_typed` | `P11.23` |
| `close` | `P11.23` |
| `read` | `P11.23` |
| `write` | `P11.23` |
| `seek` | `P11.23` |
| `stat` | `P11.23` |
| `remove` | `P11.23` |
| `rename` | `P11.23` |
| `list` | `P11.23` |
| `pipe` | `P11.23` |
| `dup` | `P11.23` |
| `ioctl` | `P11.23` |
| `read_full` | `P11.23` |
| `write_full` | `P11.23` |
| `getchar` | `P11.24` |
| `putchar` | `P11.24` |
| `puts` | `P11.24` |
| `strlen` | `P11.24` |
| `strcmp` | `P11.24` |
| `strcpy` | `P11.24` |
| `strncpy` | `P11.24` |
| `memcpy` | `P11.24` |
| `memmove` | `P11.24` |
| `memchr` | `P11.24` |
| `memset` | `P11.24` |
| `malloc` | `P11.21` |
| `free` | `P11.21` |
| `cls` | `P11.25` |
| `print_at` | `P11.25` |
| `plot` | `P11.25` |
| `point` | `P11.25` |
| `draw` | `P11.25` |
| `circle` | `P11.25` |
| `ink` | `P11.25` |
| `paper` | `P11.25` |
| `bright` | `P11.25` |
| `flash` | `P11.25` |
| `inverse` | `P11.25` |
| `over` | `P11.25` |
| `border` | `P11.25` |
| `udg_define` | `P11.25` |
| `udg_get` | `P11.25` |
| `udg_draw` | `P11.25` |
| `udg_clear` | `P11.25` |
| `udg_draw_2x2` | `P11.25` |
| `beep` | `P11.26` |
| `tape_save` | `P11.27` |
| `tape_load` | `P11.27` |
| `ticks` | `P11.27` |
| `time_get` | `P11.27` |
| `time_set` | `P11.27` |
| `sin` | `P11.20` |
| `cos` | `P11.20` |
| `tan` | `P11.20` |
| `asin` | `P11.20` |
| `acos` | `P11.20` |
| `atan` | `P11.20` |
| `sqrt` | `P11.20` |
| `exp` | `P11.20` |
| `log` | `P11.20` |
| `pow` | `P11.20` |
| `fabs` | `P11.20` |

## 5.5 Exact REV11 §41 Mandatory Test Replay/Ownership Ledger

Every mandatory REV11 §41 acceptance item is written literally below. The listed phase owner closes the implementation-side contract; `P12.26` replays the item on the release candidate. A missing row is a certification failure.

| REV11 test | Exact mandatory acceptance item | Owning implementation/replay step(s) |
|---|---|---|
| §41.1 | Start the official tape with only the normal Spectrum `LOAD ""` command. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | BASIC loader auto-starts at line 10. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | `CLEAR 24575` establishes the required bootstrap RAM ceiling. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | `zx48uxscr` loads exactly 6912 bytes into 0x4000-0x5AFF. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | A byte-for-byte expected loading screen is visible before kernel loading. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | `kernel` loads exactly 8192 bytes into 0xE000-0xFFFF. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | BASIC transfers through exact `RANDOMIZE USR 57347` / 0xE003. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | Boot entry executes `DI`, abandons the BASIC return frame, and sets SP=0xFD00. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | Successful boot never returns to BASIC. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | Kernel preserves the loading screen through low-level initialization and sequential loading of the five fixed bootstrap resources. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | The exact post-kernel M48O sequence is `sh`, `font4x8`, `issue`, `crontab`, `bincat`. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | `font4x8` is FAST_REQUIRED, pinned, and validates as exact F4X8. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | `/etc/issue`, `/etc/crontab`, and BCAT metadata are installed before PID 1. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | PID 1 enters with exact ARG1 `argv[0]="sh"`, zero-entry ENV1, cwd ROOT, and tty handles 0/1/2; after login it builds the required mutable session environment. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | tty64 displays `/etc/issue`, asks for login, then reaches the `$` prompt in `/home/<user>`. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | Kernel fits the fixed memory map. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | Free memory matches expected accounting. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | Missing/corrupt screen, kernel, and `sh` cases fail in the documented phase without executing uninitialized memory. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.1 | Two independently generated production tape images from identical inputs are byte-for-byte deterministic. | `P0.34,P12.09-P12.10,P12.24,P12.26,P12.30` |
| §41.2 | Two tasks alternate on explicit yield. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | Sleeping task wakes at/after requested tick. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | Blocked pipe reader sleeps. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | Writer wakes reader. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | Blocked writer sleeps when pipe full. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | Reader wakes writer. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | Child exit wakes wait parent. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | Zombie reaping releases memory. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | PID reuse does not corrupt old wait state. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | `SYS_KILL` of a spawned-but-never-started child makes it ZOMBIE/status 130 without executing user code and releases its owned allocations/handles. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | `SYS_KILL` of a blocked started child wakes it to observe E_INTR; PID/parent permission and PID0/PID1 protection rules are enforced. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | Normal idle reaches HALT and resumes on IM2. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | IM2 fast path preserves primary task registers. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | IM2 ROM-safe path preserves a synthetic ROM shadow-register workload. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | Context switch restores exact primary registers, IX, SP, and return PC. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | A legal 10-character process name survives spawn and prints exactly in `ps`. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | ARG1/ENV1 bounds, argc/env counts, and malformed-block rejection are tested. | `P1.41,P2.24,P3.21,P12.26` |
| §41.2 | ARG1/ENV1 remain valid under deep runtime stack use because they are outside the downward-growing stack; the 64-byte stack bootstrap reserve never consumes the advertised minimum application stack. | `P1.41,P2.24,P3.21,P12.26` |
| §41.3 | Exact-fit allocation. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | Split allocation. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | Free/coalesce. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | Fragmented arena. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | Allocation failure. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | Repeated spawn/exit cycles. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | Shell survives foreground allocation failure. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | FAST_REQUIRED exhaustion does not spill into contended RAM. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | COLD_PREFERRED allocation uses 0x6000-0x7FFF when appropriate. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | `mem` reports both contention classes correctly. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | Process stacks and pipe buffers never enter 0x6000-0x7FFF. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | A large MEX1 image may cross 0x7FFF/0x8000 and still executes correctly. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | The single-extent allocator can allocate/free/coalesce an ANY extent crossing 0x7FFF/0x8000 without corrupting FAST-only accounting. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | Shell process-owned footprint + maximum 20-KiB compiler process-owned footprint + packed-reader decoder state when `hello.c` is PACKED + pinned font/UDG/catalog resources + mandatory `hello.c` source/output objects fit with all FAST_REQUIRED allocations honored. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.3 | Default 1024-byte C48 BSS heap, `-heap 0`, and `-heap 8192` are reflected in allocation/BSS accounting without any user SYS_ALLOC. | `P1.41,P2.24,P11.40,P12.24,P12.26` |
| §41.2A | MEX1 with nonzero relocation_count and image_size <2 is rejected E_FORMAT. | `P2.24,P4.33,P10.36,P12.26` |
| §41.2A | OBJ1 with nonzero relocation_count and text_size <2 is rejected E_FORMAT. | `P2.24,P4.33,P10.36,P12.26` |
| §41.2A | A full PID table makes `SYS_SPAWN` return E_AGAIN before tape/allocation. | `P2.24,P4.33,P10.36,P12.26` |
| §41.2A | Direct spawn of a non-BIN object returns E_FORMAT. | `P2.24,P4.33,P10.36,P12.26` |
| §41.2A | `MINFO1` fields match the exact Section-10.1 accounting definitions. | `P2.24,P4.33,P10.36,P12.26` |
| §41.2A | zxpack attempt/success counters wrap modulo 65536 without corrupting current totals. | `P2.24,P4.33,P10.36,P12.26` |
| §41.2A | Linker-reserved `__heap_start`/`__heap_end` references survive archive selection, are assigned after final BSS layout, and user definitions are rejected. | `P2.24,P4.33,P10.36,P12.26` |
| §41.2A | Default MEX1 stack is 512 bytes; `-stack` accepts only even 64..4096. | `P2.24,P4.33,P10.36,P12.26` |
| §41.2A | Normal crt0 link defaults to 1024-byte heap; `-nostart` defaults to zero heap unless `-heap` is explicit. | `P2.24,P4.33,P10.36,P12.26` |
| §41.3A | ZXP1 literal lengths 1 and 64. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | RLE lengths 3 and 66. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Back-reference lengths 3 and 130. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Back-reference distances 1 and 256. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Overlapping back-reference copy. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Truncated literal/RLE/back-reference fails E_FORMAT. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Back-reference before logical start fails E_FORMAT. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Output overrun/underrun versus declared logical length fails E_FORMAT. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Physical stream with trailing undecoded bytes fails E_FORMAT. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Random and adversarial RAW -> pack -> unpack byte identity. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Target greedy encoder uses exactly one 512-byte last-occurrence workspace per pass, obeys nearest-same-first-byte/RLE tie rules, and output decodes identically to the host decoder. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Host-optimized ZXP1 streams decode identically on target. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Non-compressible input stays RAW. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Packed read/seek produces exactly RAW logical bytes. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | At least two simultaneous packed readers maintain independent 256-byte histories. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Packed O_WRITE materialization is atomic on success/failure. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | O_CREATE against an existing object preserves its type even when the caller creation type would be illegal for creating a new object in that directory. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | O_APPEND writes always begin at current logical EOF even after SYS_SEEK. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | `SYS_PACK` and `SYS_UNPACK` both return E_BUSY rather than swapping a representation while any handle references the object. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Multiple read-only opens coexist; any read/write conflict obeys the exclusive-writer E_BUSY rule and no representation swap invalidates an open reader. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Final close merely sets/clears the 32-bit candidate bitset as specified and never runs compression synchronously. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | PID 0 performs at most one candidate pack per idle cycle. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Candidate bits are cleared safely on reopen/write-open/remove/slot reuse. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Background/allocator packing E_NOMEM or no-savings does not damage data. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | `SYS_ZXPACK_INFO` arithmetic is exact. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | `mem -c` matches allocator/object-table accounting. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Resident PACKED BIN `spawn` and `exec` decode directly to final process storage, preserve history across the separately parsed MEX1 header, and never materialize a second full RAW executable object. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | Packed bootstrap `font4x8`/`bincat` decode into final pinned RAW runtime storage. | `P4.33,P2.24,P5.19,P12.26` |
| §41.3A | No process image/BSS/stack, pipe, screen, pinned runtime resource, or kernel range is ever marked/treated PACKED. | `P4.33,P2.24,P5.19,P12.26` |
| §41.4 | Empty read with writer alive blocks. | `P3.21,P6.30,P12.26` |
| §41.4 | Empty read with no writer succeeds with HL=0. | `P3.21,P6.30,P12.26` |
| §41.4 | Full write blocks. | `P3.21,P6.30,P12.26` |
| §41.4 | Write with no reader returns E_PIPE. | `P3.21,P6.30,P12.26` |
| §41.4 | Pipeline of at least three programs. | `P3.21,P6.30,P12.26` |
| §41.4 | Short writes/reads preserve byte order. | `P3.21,P6.30,P12.26` |
| §41.5 | CRC-16/CCITT-FALSE matches standard check vector `123456789` -> 0x29B1. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Native bootstrap prefix order is exactly `zx48ux`, `zx48uxscr`, `kernel`. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Post-kernel M48O bootstrap resources are exactly `sh`, `font4x8`, `issue`, `crontab`, `bincat` with exact type/target IDs. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Bootstrap tape-header names are lower-case and within Spectrum limits. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Loading-screen block is exactly 6912 bytes. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Kernel CODE header records start 0xE000 and length 8192. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Official `issue` logical bytes including final LF, zero-length RAW `crontab`, and exact 40-entry/488-byte BCAT match the frozen release contracts. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | BCAT exact name set matches all required tape-backed `/bin` commands. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | PROC1 ALLOW_TAPE=0 returns E_AGAIN for catalog-only commands without consuming a tape block; ALLOW_TAPE=1 enables the validated streaming MEX1 path. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Save/load TXT. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Save/load BIN. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Save/load UDG. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Wrong-name handling. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Corrupted transport checksum. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Corrupted M48O logical CRC. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | PACKED M48O malformed ZXP1 token/history/length. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Compressed tape scan validates logical CRC through discard decode. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | RAW and PACKED same logical object load identically. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Packed tape-backed MEX1 direct-execution path never allocates a second full image. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Wrong object type. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | User BREAK during tape operation returns/reports E_INTR and leaves shell-ready state. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Repeated same-name tape records are documented honestly. | `P5.19,P12.07-P12.09,P12.26` |
| §41.5 | Case-sensitive tape lookup does not alias differing-case object names. | `P5.19,P12.07-P12.09,P12.26` |
| §41.6 | All four corners plot correctly. | `P1.41,P7.21,P12.26` |
| §41.6 | Screen bitmap address mapping. | `P1.41,P7.21,P12.26` |
| §41.6 | Line horizontal/vertical/diagonal. | `P1.41,P7.21,P12.26` |
| §41.6 | Circle edge clipping behavior. | `P1.41,P7.21,P12.26` |
| §41.6 | Attribute cells. | `P1.41,P7.21,P12.26` |
| §41.6 | Border. | `P1.41,P7.21,P12.26` |
| §41.6 | UDG slot 0 and slot 31. | `P1.41,P7.21,P12.26` |
| §41.6 | 2x2 composed UDG. | `P1.41,P7.21,P12.26` |
| §41.6 | Save/load UDG preserves exact bytes. | `P1.41,P7.21,P12.26` |
| §41.6 | F4X8 payload exact-size/CRC/format validation. | `P1.41,P7.21,P12.26` |
| §41.6 | 64 columns address independently without corrupting neighbor nibble. | `P1.41,P7.21,P12.26` |
| §41.6 | Row 0/23 and column 0/63 boundaries. | `P1.41,P7.21,P12.26` |
| §41.6 | 64-column scroll preserves all 23 retained text rows. | `P1.41,P7.21,P12.26` |
| §41.6 | Block and underline cursor XOR is exactly reversible. | `P1.41,P7.21,P12.26` |
| §41.6 | Cursor blink never modifies bitmap from IM2 interrupt context. | `P1.41,P7.21,P12.26` |
| §41.6 | `stty cols 32` and `stty cols 64` switch predictably. | `P1.41,P7.21,P12.26` |
| §41.6 | CR/LF/BS/TAB/FF, wrap, and scroll semantics match Section 13.5A. | `P1.41,P7.21,P12.26` |
| §41.6 | Target byte 0x7F renders the copyright glyph in tty64. | `P1.41,P7.21,P12.26` |
| §41.6 | `SYS_BEEP` and shell `beep` preserve BASIC duration,pitch order. | `P1.41,P7.21,P12.26` |
| §41.6 | `beep 1,0`, `beep .5,9`, `beep .25,-12`, and `beep .5,0.5` succeed. | `P1.41,P7.21,P12.26` |
| §41.6 | Malformed/missing comma, forbidden expression tokens, and ROM-rejected values fail without escaping into BASIC. | `P1.41,P7.21,P12.26` |
| §41.6 | C48 `beep((float)0.25,(float)0.5)` exercises the same kernel service. | `P1.41,P7.21,P12.26` |
| §41.7 | Quoting. | `P6.30,P8.40,P12.26` |
| §41.7 | Redirection. | `P6.30,P8.40,P12.26` |
| §41.7 | Append. | `P6.30,P8.40,P12.26` |
| §41.7 | Pipeline. | `P6.30,P8.40,P12.26` |
| §41.7 | `&&` and `\|\|`. | `P6.30,P8.40,P12.26` |
| §41.7 | Missing command. | `P6.30,P8.40,P12.26` |
| §41.7 | Child nonzero exit status. | `P6.30,P8.40,P12.26` |
| §41.7 | Memory exhaustion. | `P6.30,P8.40,P12.26` |
| §41.7 | BREAK behavior. | `P6.30,P8.40,P12.26` |
| §41.7 | `ls` resolves while `LS` does not alias it. | `P6.30,P8.40,P12.26` |
| §41.7 | `hello.c`, `Hello.c`, and `HELLO.C` can coexist as distinct RAM objects. | `P6.30,P8.40,P12.26` |
| §41.7 | Cassette lookup preserves and compares case exactly. | `P6.30,P8.40,P12.26` |
| §41.7 | Case-only rename behaves deterministically. | `P6.30,P8.40,P12.26` |
| §41.7 | `calc "sin(pi/4)"` is accepted while an undocumented case alias is rejected. | `P6.30,P8.40,P12.26` |
| §41.7 | Exact boot heading line 1 and line 2 under tty64. | `P6.30,P8.40,P12.26` |
| §41.7 | `/etc/issue` exact first two lines and fun third line. | `P6.30,P8.40,P12.26` |
| §41.7 | Reject empty, >8-character, upper-case-leading, or illegal username. | `P6.30,P8.40,P12.26` |
| §41.7 | Create/select `/home/<user>` and start there. | `P6.30,P8.40,P12.26` |
| §41.7 | Exact `USER`, `HOME`, `SHELL`, and `PATH`. | `P6.30,P8.40,P12.26` |
| §41.7 | `/bin`, `/etc`, `/dev`, `/home`, `/tmp`, `.`, and `..` path resolution. | `P6.30,P8.40,P12.26` |
| §41.7 | `ls` versus `LS` remains case-sensitive. | `P6.30,P8.40,P12.26` |
| §41.7 | `date` unset behavior and valid/invalid `date -s`. | `P6.30,P8.40,P12.26` |
| §41.7 | Wall-clock second rollover, leap day, and year/month/day boundaries. | `P6.30,P8.40,P12.26` |
| §41.7 | `@boot` cron without wall clock. | `P6.30,P8.40,P12.26` |
| §41.7 | Calendar cron suppressed until wall clock valid. | `P6.30,P8.40,P12.26` |
| §41.7 | No duplicate cron firing within one minute. | `P6.30,P8.40,P12.26` |
| §41.7 | Cron field bounds, Sunday=0, AND matching, `@hourly`, `@daily`, and one-session `@boot` behavior. | `P6.30,P8.40,P12.26` |
| §41.7 | Setting wall time resets cron minute state without catch-up. | `P6.30,P8.40,P12.26` |
| §41.7 | Official boot crontab is the exact zero-length RAW CFG and does not auto-start cron. | `P6.30,P8.40,P12.26` |
| §41.7 | `crontab -l` and `crontab -e`. | `P6.30,P8.40,P12.26` |
| §41.7 | `man` prints the exact website and `Search for ZXUS`. | `P6.30,P8.40,P12.26` |
| §41.7 | `which` reports only external BIN PATH results, skips wrong-type/overlength candidates, never moves tape, and a builtin-only name returns no output/status 1. | `P6.30,P8.40,P12.26` |
| §41.7 | `uname` prints exactly `ZX-UX z80 48k` plus LF. | `P6.30,P8.40,P12.26` |
| §41.7 | `@hourly` fires only at minute 00 and `@daily` only at 00:00. | `P6.30,P8.40,P12.26` |
| §41.7 | `whoami`, `uptime`, `cal`, `fortune`, `banner`, `rev`, and `yes` basic behavior and pipeline/cancellation where applicable. | `P6.30,P8.40,P12.26` |
| §41.8 | Normal/insert/command-line mode transitions. | `P9.24,P8.39,P12.26` |
| §41.8 | `h/j/k/l`, `0/$`, `w/b/e`, `gg/G` movement. | `P9.24,P8.39,P12.26` |
| §41.8 | `i/a/o/O/x/dd/D/yy/p/P/r/J` editing. | `P9.24,P8.39,P12.26` |
| §41.8 | One-level undo. | `P9.24,P8.39,P12.26` |
| §41.8 | Literal `/` search plus `n/N`. | `P9.24,P8.39,P12.26` |
| §41.8 | `:w`, `:q`, `:q!`, `:wq`, `:e`, `:r` command behavior. | `P9.24,P8.39,P12.26` |
| §41.8 | Case-sensitive object names and searches. | `P9.24,P8.39,P12.26` |
| §41.8 | Failed buffer growth leaves the last valid text intact. | `P9.24,P8.39,P12.26` |
| §41.8 | Save/reload round trip preserves exact bytes. | `P9.24,P8.39,P12.26` |
| §41.8 | `vi` enters tty64, uses block cursor in normal mode and underline in insert mode. | `P9.24,P8.39,P12.26` |
| §41.8 | `vi` restores previous terminal mode/cursor on clean exit and error unwind. | `P9.24,P8.39,P12.26` |
| §41.8 | Unnamed `:w`/`:wq` refuses exactly as Section 22.6 specifies. | `P9.24,P8.39,P12.26` |
| §41.8 | `crontab -e` real-vi integration preserves live CFG on editor/load/validation failure. | `P9.24,P8.39,P12.26` |
| §41.8 | 64-column horizontal behavior never writes beyond column 63. | `P9.24,P8.39,P12.26` |
| §41.9 | Compile and run programs covering every version-1 operator; simple scalar/array initializers; int<->float casts; signed/unsigned comparison; pointers; arrays; globals; locals; REGCALL functions with 0..6 arguments; five-byte float arguments and hidden-result returns; recursion within stack budget; loops; logical operators; string literals; built-in `<c48.h>`; standard runtime resolution by `ld`; system calls; graphics; UDG calls; pipe I/O; compile error reporting; symbol-table overflow; source too large; and output memory exhaustion. | `P11.45,P12.26` |
| §41.9 | Compiler consumes a PACKED C source through ordinary read calls without whole-file materialization and produces the same OBJ1 as the RAW source. | `P11.45,P12.26` |
| §41.10 | Every required `.c` demo compiles with the native C48 compiler. | `P11.38,P12.01-P12.02,P12.26` |
| §41.10 | Every resulting object links with native `ld`. | `P11.38,P12.01-P12.02,P12.26` |
| §41.10 | Source and executable names remain lower-case. | `P11.38,P12.01-P12.02,P12.26` |
| §41.10 | Precompiled and freshly compiled versions produce equivalent documented behavior. | `P11.38,P12.01-P12.02,P12.26` |
| §41.10 | All demos return cleanly to `sh`. | `P11.38,P12.01-P12.02,P12.26` |
| §41.10 | Demos that loop interactively yield often enough for cooperative scheduling. | `P11.38,P12.01-P12.02,P12.26` |
| §41.10 | `demo name` runs the exact lower-case executable and does not case-fold. | `P11.38,P12.01-P12.02,P12.26` |
| §41.11.1 | Boot establishes IY=0x5C3A before the first post-handoff ROM call. | `P1.29,P12.26` |
| §41.11.1 | Every syscall returns with IY=0x5C3A. | `P1.29,P12.26` |
| §41.11.1 | Context switches do not make IY process-local. | `P1.29,P12.26` |
| §41.11.1 | Each enabled ROM wrapper is tested with the frozen IY-relative system-variable contract. | `P1.29,P12.26` |
| §41.11.1 | A synthetic wrapper that temporarily changes IY restores 0x5C3A on success and every trapped error path. | `P1.29,P12.26` |
| §41.11.2 | An interrupt at every instruction boundary of synthetic foreground EXX/EX AF,AF' use selects the safe ISR whenever `altreg_busy!=0`. | `P1.30,P12.26` |
| §41.11.2 | No interrupt can observe `altreg_busy==0` while foreground shadow state is live. | `P1.30,P12.26` |
| §41.11.2 | Fast ISR path still preserves primary registers and returns correctly. | `P1.30,P12.26` |
| §41.11.2 | ROM wrapper shadow-register tests use the same generic gate. | `P1.30,P12.26` |
| §41.11.3 | IM2 recognizes the frozen BREAK chord from raw matrix reads. | `P1.31,P12.26` |
| §41.11.3 | Non-BREAK key combinations do not spuriously set `break_pending`. | `P1.31,P12.26` |
| §41.11.3 | IM2 contains no call edge to ROM KEYBOARD/decoder routines. | `P1.31,P12.26` |
| §41.11.3 | Ordinary tty input still decodes the required key set outside interrupt context. | `P1.31,P12.26` |
| §41.11.4 | Draw tty64 text and show an XOR cursor. | `P1.32,P12.26` |
| §41.11.4 | Turn cursor OFF. | `P1.32,P12.26` |
| §41.11.4 | Directly write both high- and low-nibble bitmap cells at the former cursor position. | `P1.32,P12.26` |
| §41.11.4 | Restore cursor. | `P1.32,P12.26` |
| §41.11.4 | Blink/hide/show the cursor repeatedly. | `P1.32,P12.26` |
| §41.11.4 | Prove the raw bitmap content returns byte-for-byte when the cursor is hidden. | `P1.32,P12.26` |
| §41.11.5 | Instrumentation records high-water depth on every kernel/ROM/ISR stress test. | `P1.33,P12.25-P12.26` |
| §41.11.5 | Maximum stack consumption is <=448 bytes in the production-linked build. | `P1.33,P12.25-P12.26` |
| §41.11.5 | Bytes 0xFB00-0xFB0F retain the frozen guard pattern. | `P1.33,P12.25-P12.26` |
| §41.11.5 | Deliberately corrupting the guard in a test build produces `PANIC KSTACK`. | `P1.33,P12.25-P12.26` |
| §41.11.6 | Pointer=0xDFF0 length=0x0030 is rejected before any read, write, allocation, relocation, or namespace mutation. | `P3.19,P2.03,P4.16,P5.01,P10.03,P12.26` |
| §41.11.6 | Pointer=0xFFF0 length=0x0020 is rejected before any side effect because it wraps 0x10000. | `P3.19,P2.03,P4.16,P5.01,P10.03,P12.26` |
| §41.11.6 | Pointer=0x5AF0 length=0x0020 is rejected before any side effect because it crosses display into protected workspace. | `P3.19,P2.03,P4.16,P5.01,P10.03,P12.26` |
| §41.11.6 | Positive control pointer=0x7FF0 length=0x0020 is accepted by an ordinary buffer syscall when ownership/access requirements are satisfied because it remains wholly inside 0x6000-0xDFFF. | `P3.19,P2.03,P4.16,P5.01,P10.03,P12.26` |
| §41.11.6 | Format tests choose counts/sizes whose 16-bit multiplication or addition would wrap and prove widened validators reject them. | `P3.19,P2.03,P4.16,P5.01,P10.03,P12.26` |
| §41.11.6 | Zero-count read/write does not dereference the buffer while the handle and other required arguments are still validated. | `P3.19,P2.03,P4.16,P5.01,P10.03,P12.26` |

---

# 6. Mandatory Per-Module Review Gate

Before closing any source-module step, the retained review must answer **all 41**
REV11 §62 questions below. A non-applicable answer must state why; a blank answer is a
failure.

| Q | Required question |
|---:|---|
| 1 | What exact memory region can it touch? |
| 2 | What persistent state does it own? |
| 3 | Can it run in interrupt context? |
| 4 | Can it yield? |
| 5 | Can it block? |
| 6 | What happens if memory allocation fails? |
| 7 | What registers does it preserve? |
| 8 | Does it call ROM? |
| 9 | If yes, is the ROM contract verified centrally? |
| 10 | Does it manipulate user pointers? |
| 11 | Are lengths bounded before access? |
| 12 | What process state transitions can it cause? |
| 13 | What test proves every transition? |
| 14 | What happens at cassette EOF/error/BREAK? |
| 15 | What happens at tick wrap? |
| 16 | What happens if another task closes a pipe? |
| 17 | Does the module alter ABI-visible behavior? |
| 18 | What is its binary-size budget? |
| 19 | What is the rollback/atomicity rule on failure? |
| 20 | What emulator/hardware evidence closes the task? |
| 21 | Is its hot code/data in FAST or CONTENDED memory, and why? |
| 22 | Does it depend on IY, I, alternate registers, or IM2 state? |
| 23 | If it uses shadow registers, what happens when a ROM wrapper is active? |
| 24 | Could a block transfer/search instruction replace a larger byte loop? |
| 25 | Is any undocumented opcode being introduced? If yes, why is this not in the portable baseline? |
| 26 | If it touches port 0xFE, does it use the central ULA output shadow? |
| 27 | If it is C48-generated code, does it follow REGCALL/frame-elision and IY preservation rules? |
| 28 | Does any user-facing name preserve exact case and use case-sensitive lookup? |
| 29 | If the module ships a command/tool/demo, is its canonical user-facing name lower-case? |
| 30 | If it is `vi`, does the change preserve documented modal and case-sensitive command semantics? |
| 31 | If it affects demos, can the matching `.c` source still compile/link/run natively on the 48K target? |
| 32 | Does it create or consume ARG1/ENV1, and are every byte/count bound validated? |
| 33 | Can an ANY allocation cross 0x7FFF/0x8000 safely without violating FAST_REQUIRED accounting? |
| 34 | If it runs in the background or from cron, can it ever steal tty input or trigger an interactive cassette-position prompt? |
| 35 | If it uses C48 `float`, does it obey the pointer argument/hidden-result ABI? |
| 36 | If it allocates C48 heap memory, is it entirely inside the linker-reserved BSS heap with no implicit kernel allocation? |
| 37 | If it emits sound, does it preserve `beep duration,pitch` semantics and the ULA/ROM critical-section contract? |
| 38 | If it invokes or implements a syscall, does it match the exact Section-10.1 register/packed-record contract byte-for-byte? |
| 39 | Can this module observe a PACKED object, and if so are logical versus physical lengths and seek/read semantics explicit? |
| 40 | Could this module accidentally compress live process/stack/pipe/pinned memory? |
| 41 | Is every pack/unpack/representation swap atomic on allocation/codec failure? |

A programming task is not complete until these questions have concrete answers where
applicable. The completed checklist is retained with the step evidence. On a 48K machine,
most mysterious bugs are merely tiny facts that were allowed to wander unsupervised.

---

# 7. Test and Release Evidence Hierarchy

1. **Static/host:** format sizes, symbols, section bounds, CRCs, deterministic hashes,
   opcode scans, source-tree/name policy.
2. **SNA:** deterministic component execution and fast register/RAM assertions.
3. **TAP:** ROM bootstrap, real loader semantics, M48O integration and system boot.
4. **TZX/FUSE-utils:** independent cassette-format inspection and fidelity integration.
5. **Second emulator:** release-critical compatibility subset.
6. **Real 48K-compatible hardware or hardware-faithful EAR/MIC loop:** physical tape
   timing/robustness, final physical boot/save/load claims.

No lower layer is allowed to claim evidence strength belonging to a higher layer.

---

# 8. Document Certification State

**Status: DOUBLE-FORENSIC-ACCURACY CERTIFIED.**

This Revision-02 implementation plan is subordinate to canonical REV11 SHA-256
`F76281FAB2E5AE73B7321FC2A69E6776F7CCD8BFE3955A6ED6FB3BEC44F762C7` and is delivered
only after the anti-circular certification sequence below has completed without changing
these final document bytes.

## 8.1 Pre-certification convergence

Before this certification statement was regenerated, one immutable candidate completed
two consecutive zero-gap audits:

1. a complete source-order REV11 Sections 1-65 architecture audit; and
2. an independent invariant/test/release audit covering all 139 Section-61 invariants,
   all 228 Section-41 mandatory test rows, all 41 Section-62 module-review questions,
   the Section-63 success demonstration, Section-44 size/simultaneous-residency gates,
   Section-59 deferred-feature boundary, Section-40 evidence hierarchy, and
   architecture-defined failure/atomicity/negative-test behavior.

Any gap found during convergence changed the candidate bytes, reset certification credit
to zero, and restarted the source-order audit from Section 1.

## 8.2 Final-byte certification

Regenerating this Section 8 changed the document bytes exactly once after pre-certification.
The regenerated final bytes were therefore audited again from scratch with **no inherited
PASS credit**. Final delivery requires both of these audits to be retained as evidence:

1. **Final certificate 1:** complete REV11 Sections 1-65 source-order audit, zero gaps.
2. **Final certificate 2:** independent complete REV11 Sections 1-65 audit, including
   the 139 invariant owners, 228 mandatory-test rows, 41 module-review questions,
   definitive success transcript and cassette round trip, size/residency gates, all 21
   deferred features, evidence-strength rules, ROM provenance, and strict Phase-0-only
   first-deliverable boundary.

A mutation after either final certificate invalidates both final certificates and requires
another complete two-pass certification on the newly changed bytes. The delivered file is
therefore the same immutable byte sequence audited by both retained final-certificate logs.

## 8.3 Certification scope and non-negotiable release rules

Certification means this plan has an explicit atomic implementation/test/check-in owner
for every REV11 requirement without knowingly strengthening, weakening, inventing, or
leaving architecture-significant behavior to implication. It does **not** certify future
source code that has not yet been implemented; each implementation step must still pass
its own specified evidence gate.

The implementation sequence remains:

`E0 -> P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> P8 -> P9 -> P10 -> P11 -> P12`

No phase may be skipped. No later green test erases an earlier red gate. In particular,
Section 65 remains strict: the first programming-cycle deliverable is Phase 0 only, and
scheduler, pipes, the full shell parser, and compiler work remain forbidden until the
Phase-0 ROM/memory gate closes reproducibly.
