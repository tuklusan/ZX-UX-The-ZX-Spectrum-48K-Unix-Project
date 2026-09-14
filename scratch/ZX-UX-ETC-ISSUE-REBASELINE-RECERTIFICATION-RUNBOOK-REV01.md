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

# ZX-UX Combined Rebaseline and Re-certification Runbook

**Status:** AUTHORIZED WORKING PLAN — not architecture, implementation, or certification authority.

**Purpose:** Durable cross-session coordination for the combined controlled source
rebaseline that must be completed before Phase 2 begins: the exact `/etc/issue` byte
change, canonical Phase-0 consumption of `v1/assets/font4x8-zxux.bin`, Phase-11 C48
DOCX/pinned-SDK conformance rules, and the first tty64 rendered-font screenshot proof
with mandatory automated visual inspection.

This file is intentionally stored under `scratch/`. It must survive loss of any
ephemeral workspace and must let a fresh project session discover the correct restart
point from repository state alone. Repository state and canonical project documents
always override this file if they disagree.

## 1. Hard boundaries

1. Modify only `tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project`.
2. The C48 SDK and every other GitHub repository are read-only; no branch, commit, push, PR, or other mutation is permitted outside the canonical ZX-UX repository.
3. Do not start Phase 2.
4. Do not weaken evidence, negative tests, source binding, activation rules, or
   Quality gates.
5. Treat `/mnt/data`, runner filesystems, and chat-local state as disposable.
6. Durable continuity comes from `main`, files under `scratch/`, committed
   certification evidence, and GitHub Actions history.
7. Instrument blockers before escalating. Prefer adding diagnostics or reading exact
   workflow/job/evidence state over guessing.
8. Every repository change follows `AGENTS.md` and
   `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md`, including the three clean SoP scans,
   license-header gate, project-policy gate, adversarial review, and direct-main
   check-in discipline.
9. This runbook is coordination only. It does not itself change architecture or
   certify anything.

## 2. Requested target bytes

The official Version-1 `/etc/issue` logical payload must become exactly:

```text
ZX-UX - Inspired by Unix for the Sinclair ZX Spectrum 48K
64-column shell, native tools, C compiler, cassette storage
48K. One Z80. No excuses.
```

Byte contract:

- ASCII bytes only.
- Exactly three lines.
- Every line ends in LF (`0x0A`), including the final line.
- No CR bytes.
- No BOM.
- No leading or trailing spaces on any line.
- No extra blank line.
- Exact logical length: 144 bytes.
- Exact payload SHA-256:
  `8d57d17f25ef895909a56a3195e29b8f9b83ff2cc31b2537a23d1d02429e3d31`.
- The third line remains exactly `48K. One Z80. No excuses.`.
- The former author/site heading is removed from `/etc/issue`.
- Unrelated attribution, license text, README material, and `man` website behavior are
  outside this change unless a canonical contract explicitly couples them to
  `/etc/issue`.

## 3. Historical starting checkpoint

The inspection that created this plan observed:

- `main`: `5f5a539fd8218c755648f12d921e635a6e517773`
- Phase-1 certified source:
  `b1d6fac7b9279d12e8e84efb37064f890b1be712`
- Phase-1 evidence activation:
  `c126c9cdba28ba52fe96093a17f8186337e5d0ac`
- old REV12 SHA-256:
  `ea23eb1c4815490830325b235e885d11b475a27ce6dcb9c70f4716d5c604fea0`
- old `/etc/issue` SHA-256:
  `e501e97f58ca506e6318101c8bcdf41db0b76d137eba845b989abee915d72700`

These values are historical anchors only. **Never assume they are current in a later
session.** Every session must execute the restart procedure below before changing
anything.

## 4. Mandatory fresh-session restart procedure

At the beginning of every chat or after any loss of local state:

1. Read this runbook from current `main`.
2. Fetch the current `main` commit SHA.
3. Read current `AGENTS.md` and
   `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md`; newer mandatory process rules override
   this runbook.
4. Fetch and hash current
   `docs/01-ZX-UX-ARCHITECTURE-REV12.md`.
5. Fetch `v1/assets/issue.txt` as raw/base64 bytes and compare it byte-for-byte with
   the 144-byte target in Section 2.
6. Inspect the current contents of the source/binder files listed in Section 6.
7. Inspect `v1/dist/certification/phase-0.json` and `phase-1.json` if present.
8. Find the newest Phase-0 and Phase-1 evidence activation commits from repository
   history and verify the activation rules enforced by
   `tools/check_phase0_evidence.py` and `tools/check_phase1_evidence.py`.
9. Inspect relevant recent workflow runs and attempts for:
   - `ZX-UX Phase 0 Certification`;
   - `ZX-UX Phase 1 Certification`;
   - `ZX-UX Quality and CI`.
10. Classify the repository into exactly one checkpoint state from Section 5.
11. Before resuming work, state the current `main` SHA, computed REV12 SHA-256,
    `/etc/issue` byte/hash state, Phase-0 activation state, Phase-1 activation state,
    and chosen checkpoint.
12. If state is mixed, contradictory, or cannot be proved, do not modify source or
    evidence. Instrument the ambiguity first by fetching exact files, commits,
    workflow jobs/logs, and validator behavior until the state is deterministic.

Do not use a remembered commit, remembered workflow result, or a surviving local file
as the authority for restart classification.

### 4.1 Combined-goal restart additions

A fresh session must additionally prove all of the following before it resumes source
work:

- `v1/assets/font4x8-zxux.bin` is a regular 392-byte file with Git blob
  `6efc46eb1d7e940e027097ad76e27ac719aeb59f` and SHA-256
  `90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339`;
- Phase-0 generation does not synthesize or write a font payload, and P0.10 consumes
  the canonical source asset directly;
- P1.21 and P1.22 also consume that same canonical source asset rather than the legacy
  `v1/assets/font4x8.bin` fixture;
- P1.22 is the earliest real tty64 4x8-render step and requires a captured PNG
  screenshot plus its exact 6912-byte SCR companion from the same Fuse FMF frame;
- the captured P1.22 frame is subjected to mandatory automated visual inspection by
  exact comparison with an independently rendered 96-glyph atlas derived from the
  canonical font bytes; screenshot existence alone is never sufficient;
- `docs/04-C48 Language Specification Rev 0.11.docx` has the currently reviewed Git
  blob and `tools/check_license_headers.sh` binds its exact path to that exact blob;
- REV03 still pins the P11.39 compiler/reference SDK baseline and the distinct P11.45
  H06 source-corpus baseline; moving SDK `main` is not certification identity;
- REV03 contains the mandatory architecture/DOCX/pinned-SDK/native three-way
  reconciliation and fail-closed discrepancy disposition; and
- current Phase-0/Phase-1 activation state and the relevant workflow run/job/log state
  are re-read from GitHub rather than memory.

## 5. Checkpoint state machine

Use content and evidence, not commit-message intuition, to select the restart point.

### C0 — baseline not yet changed

Choose C0 when any required target source/contract change is not yet committed, for
example:

- `v1/assets/issue.txt` is not the exact 144-byte target;
- REV12 still freezes the old issue bytes or old boot heading;
- REV03 still freezes/checks the old bytes;
- a live generator/test still embeds the old bytes;
- architecture digest binders still name the old REV12 digest;
- certification-transition workflow hardening is absent;
- Phase 0 still synthesizes or consumes `v1/assets/font4x8.bin` rather than the canonical
  `v1/assets/font4x8-zxux.bin`;
- P1.21/P1.22 still consume the legacy font fixture or describe Phase 1 as using a
  knowingly non-final font;
- P1.22 lacks mandatory captured screenshot evidence and automated visual inspection;
- REV12/REV03 still permit a non-final Phase-0 font fixture;
- the C48 DOCX exact-path/blob license exemption is absent or stale;
- Phase 11 lacks mandatory DOCX review/correction and three-way pinned-SDK comparison;
  or
- this runbook is stale relative to the active combined goal.

Resume at Section 7.

### C1 — source rebaseline committed, Phase 0 not active for new REV12

Choose C1 only when all Section-7 source changes are committed and internally
consistent, the target issue bytes are exact, and every live architecture digest
binder agrees with the computed new REV12 SHA-256, but the latest active durable
Phase-0 aggregate does not certify that new digest.

Resume at Section 8.

### C2 — Phase 0 active for new REV12, Phase 1 not active for it

Choose C2 only when:

- current Phase-0 durable evidence passes its active validator for the new REV12;
- the Phase-0 activation is an evidence-only direct child of its certified source;
- all 83 required Phase-0 durable JSON records are present and bound to one clean
  source/digest; and
- Phase-1 durable evidence is still historical/pre-activation for the new REV12.

Resume at Section 9.

### C3 — Phase-1 source trigger exists, activation still pending

Choose C3 when Phase 0 is active for the new REV12 and a post-Phase-0 Phase-1 trigger
source commit exists, but Phase 1 has not yet produced active durable evidence for the
new REV12.

Inspect the newest Phase-1 certification run for that exact source:

- if attempt 1 is running, failed, or incomplete, diagnose that exact run;
- if attempt 1 passed but did not activate because activation is intentionally gated
  on `github.run_attempt > 1`, re-run the `phase1-certification` job so the complete
  job executes as a later attempt;
- if a later attempt failed, diagnose and repair through the full project SoP;
- never hand-edit certification JSON.

Resume at Section 9 step 3 using the already-existing `S1`. Do not create another
trigger commit.

### C4 — both phases active, final closure not yet proved

Choose C4 when Phase 0 and Phase 1 are both actively certified against the same new
REV12 digest, but the final closure audit in Section 10 has not been proved against
current `main`.

Resume at Section 10.

### DONE — controlled rebaseline closed

Choose DONE only when every Section-10 closure condition is proved from current
repository/workflow state. Do not infer DONE merely because an earlier chat said the
work was complete.

If none of C0-C4 or DONE fits exactly, classify the state as **BLOCKED-MIXED** and
instrument it. Do not push speculative repairs.

## 6. Known contract/blast-radius inventory

A fresh session must re-scan current `main` rather than assuming this list is
exhaustive. The initial audit found these intended source/control paths:

1. `docs/01-ZX-UX-ARCHITECTURE-REV12.md`
2. `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md`
3. `v1/assets/issue.txt`
4. `tools/generate_phase0_resources.py`
5. `v1/tools-host/test-driver/phase0_media.py`
6. `tools/scripts/verify-environment.py`
7. `v1/tools-host/test-driver/foundation_rr.py`
8. `tools/check_phase0_evidence.py`
9. `tools/finalize_phase0_evidence.py`
10. `tools/check_phase1_evidence.py`
11. `tools/finalize_phase1_evidence.py`
12. `.github/workflows/phase0-certification.yml`
13. `.github/workflows/phase1-certification.yml`
14. `.github/phase1-certification.trigger` (new durable trigger, if still needed by
    current workflow behavior)

Additional intended source/control paths for the combined rebaseline are:

15. `tools/check_license_headers.sh`
16. `scratch/ZX-UX-ETC-ISSUE-REBASELINE-RECERTIFICATION-RUNBOOK-REV01.md`
17. `v1/docs/font4x8.md`
18. `v1/tools-host/test-driver/phase1_font4x8.py`
19. `v1/tools-host/test-driver/phase1_tty64.py`
20. `v1/tools-host/test-driver/phase1_tty64_visual.py` (new deterministic screenshot/visual oracle)
21. `tools/scripts/bootstrap-environment.py` (require installed `fmfconv` from pinned Fuse-utils)

The list remains an audit aid, not authority. Re-scan the whole tree. The canonical
font asset itself remains byte-identical and is not in the modified-file set merely
because it is consumed. The maintained DOCX likewise need not change unless review
finds an actual specification defect.

The source audit must also search tracked current text for all of these concepts:

- the old two-line issue heading;
- the old exact issue SHA-256;
- the old REV12 SHA-256;
- `<0x7F>` issue-byte descriptions;
- wording that validates only the "first two lines";
- expected-output transcripts containing the old boot heading;
- any literal `/etc/issue` byte array;
- any test fixture or generated-resource function that emits the old bytes.

Classify every hit. Historical authorities such as REV11/REV02 and unrelated license,
README, or `man` attribution/site text are not edited merely because words overlap.
Only contracts that freeze, generate, validate, display, expect, or certify the old
`/etc/issue` bytes are in scope.

The certification evidence replacement blast radius is:

- Phase 0: 83 JSON records
  - 6 E0 steps x build/test = 12;
  - 34 P0 steps x build/test = 68;
  - `E0.04.result.json`;
  - `P0.34.result.json`;
  - `phase-0.json`.
- Phase 1: 84 JSON records
  - 41 P1 steps x build/test = 82;
  - `P1.41.result.json`;
  - `phase-1.json`.
- Total durable replacement set: 167 JSON records.

Phase-0 certification may continue to revalidate P1.01-P1.12 as diagnostic/staged
checks if that gate remains in the canonical workflow, but those P1 records must not
replace or mutate the historical durable Phase-1 set before the new Phase-1 activation.

## 7. C0 work — create and freeze the source rebaseline

### 7.1 Canonical architecture

Update REV12 so every `/etc/issue` and boot-heading contract agrees on the new exact
three lines.

At minimum re-audit:

- revision/change summary wording that couples boot heading to former issue lines;
- the byte-frozen `issue` payload contract;
- boot resource validation language;
- §20.1 boot heading, issue, username, and prompt;
- repository layout/source-encoding notes;
- architecture acceptance bullets for exact issue/heading output;
- definitive acceptance steps;
- success-demo transcript/checkpoints;
- invariants such as the current statement that `/etc/issue` begins with the former
  exact two heading lines.

Do not change unrelated `man` output or attribution contracts.

After the exact REV12 bytes are final, compute its SHA-256. That value is `NEW_ARCH`.
If REV12 changes afterward, discard `NEW_ARCH`, recompute it, and restart every clean
scan affected by the byte change.

### 7.2 Canonical implementation plan

Update REV03 to:

- record `NEW_ARCH` wherever the canonical REV12 SHA is frozen;
- reopen E0.02 for the new identity;
- change P0.10 to the exact new three-line issue bytes;
- update future P6.02 issue-display/heading contract;
- update future P12.04 final issue-byte freeze;
- update P12.30/P12.31 expected output and acceptance text;
- update coverage rows that describe the old first-two-lines/third-line structure.

Do not implement P6, P12, or Phase 2 merely because their future contract text changes.

### 7.3 Live asset, generator, and Phase-0 test

Change `v1/assets/issue.txt` to exactly the Section-2 bytes.

Update `tools/generate_phase0_resources.py` so generated issue bytes are exactly the
same 144-byte payload.

Update `v1/tools-host/test-driver/phase0_media.py` so P0.10:

- checks exact issue bytes;
- checks exact 144-byte length;
- checks final LF;
- rejects CRLF;
- rejects missing final LF;
- rejects a one-byte content mutation;
- rejects extra trailing data;
- retains all existing M48O order/type/target, font, crontab, BCAT, build, and negative
  assertions.

Do not weaken existing negative tests while adding these cases.

### 7.4 Rebind architecture identity

Replace the old REV12 digest with `NEW_ARCH` in every live architecture identity
binder found by the fresh scan. The initial audit found at least:

- `tools/scripts/verify-environment.py`;
- `v1/tools-host/test-driver/foundation_rr.py`;
- `tools/check_phase0_evidence.py`;
- `tools/finalize_phase0_evidence.py`;
- `tools/check_phase1_evidence.py`;
- `tools/finalize_phase1_evidence.py`;
- REV03 itself.

E0.02 must continue to reject an intentionally wrong architecture digest.

### 7.5 Harden the Phase-0-to-Phase-1 evidence transition

The initial workflow had a destructive transition hazard: Phase-0 activation deleted
all certification JSON and copied every staged JSON, including staged P1 records. That
is not safe now that full Phase-1 evidence is durably active.

Update `.github/workflows/phase0-certification.yml` so a new Phase-0 activation:

- installs/replaces only E0/P0 build/test/result records and `phase-0.json`;
- does not delete, overwrite, or stage-install any durable `P1.*.json` or
  `phase-1.json`;
- may still execute P1.01-P1.12 revalidation if that existing gate remains required;
- explicitly proves the historical durable P1 bytes are unchanged before its
  evidence-only commit;
- commits only the allowed Phase-0 evidence set;
- retains failure artifacts and existing instrumentation.

Do not reduce the ordered E0/P0 execution set.

### 7.6 Make Phase-1 restart deterministic

Update `.github/workflows/phase1-certification.yml` only as needed to preserve current
activation semantics while making this rebaseline restartable:

- add an early fail-closed preflight requiring active durable Phase 0 for the current
  architecture;
- add `.github/phase1-certification.trigger` to the push path allow-list;
- retain the existing `github.run_attempt > 1` activation rule unless a later
  authoritative contract explicitly changes it;
- retain full P1.01-P1.41 execution, aggregate finalization, clean-source checks,
  exact evidence-copy identity, evidence-only commit restrictions, and diagnostics.

Create `.github/phase1-certification.trigger` as inert project metadata with the
required project license header. It can be changed once after Phase-0 activation to
create the clean Phase-1 source commit without changing target implementation.

### 7.7 Pre-source-freeze validation

Before committing the source rebaseline:

1. Re-run the whole-tree dependency scan from Section 6.
2. Prove `v1/assets/issue.txt` is exactly 144 bytes and hashes to the Section-2 digest.
3. Prove resource generation is deterministic/idempotent for the issue asset.
4. Run E0.01/E0.02/E0.03 checks needed by the changed identity/tooling.
5. Run P0.10 build/test and all strengthened negatives.
6. Exercise the evidence-transition logic so staged Phase-0 installation cannot mutate
   P1 evidence.
7. Run repository policy and required project checks.
8. Execute the project SoP on every proposed changed file: three identical-byte clean
   scans, then license header, project policy, adversarial review.
9. Commit the exact reviewed source bytes directly to `main`. Call this clean committed
   source `S0`.

A red active-evidence Quality result may occur during this deliberate rebaseline
because the old durable evidence must fail closed against the new architecture until
new activation exists. Do not suppress or weaken that failure. The next required state
is C1, not DONE.

### 7.8 Canonical Phase-0/Phase-1 font-source correction

The source freeze must make the complete live font path consistent:

- `v1/assets/font4x8-zxux.bin` is the canonical ZX-UX font source from Phase 0 onward;
- `tools/generate_phase0_resources.py` validates but never synthesizes or writes font bytes;
- P0.10 consumes the canonical asset, proves exact size/header/SHA-256, and retains its
  existing structural/transport negatives;
- REV12/REV03 and `v1/docs/font4x8.md` contain no knowingly non-final Phase-0/Phase-1
  fixture semantics;
- P1.21 validates/pins the same canonical asset and host certification verifies its
  exact byte identity while target code remains SHA-256-free; and
- P1.22 renders from that same canonical asset. P12.05 only re-verifies this identity;
  it does not promote, rewrite, synthesize, or substitute a font.

### 7.9 First rendered-font screenshot and automated visual inspection

P1.22 is the earliest real tty64 step that renders the canonical 4x8 font on the
terminal. Its **test** action must therefore produce certification proof from the
actual Fuse display path:

1. Render all 96 target codes `0x20..0x7F` in a deterministic tty64 atlas using the
   canonical `font4x8-zxux.bin` bytes.
2. Capture displayed frames through Fuse FMF recording.
3. Extract SCR and PNG frame sequences with the project-local pinned Fuse-utils
   `fmfconv`.
4. Independently construct the expected 6912-byte Spectrum screen from the canonical
   F4X8 bytes and the tty64 nibble/address rules; do not derive expected bytes from the
   captured image.
5. Require at least one captured SCR frame to match that independently constructed
   screen byte-for-byte. For the PNG with that exact frame identity, decode the PNG
   raster independently and require the full 320x240 pixel layout (32/24 border around
   the 256x192 Spectrum display plus every atlas foreground pixel) to match the same
   expected SCR-derived bitmap. Both comparisons are mandatory automated visual
   inspection. Merely producing a PNG, checking file existence, pairing filenames, or
   using a human-only glance is insufficient.
6. Retain the PNG corresponding to that exact inspected frame as
   `P1.22-font-atlas.png` and its SCR companion as `P1.22-font-atlas.scr` in the
   external certification evidence directory.
7. Record both artifact SHA-256 values, the exact common captured-frame identity, and
   PNG raster-inspection dimensions/foreground count in `P1.22.test.json`; the Phase-1
   finalizer must independently require the SCR comparison, PNG raster-inspection, PNG
   retention, and frame-correspondence assertions, verify the files and their hashes,
   require one exact common SCR/PNG frame identity, require the 320x240 PNG inspection
   proof plus PNG framing and exact 6912-byte SCR length, and fail closed if any proof
   is absent or changed.
8. The Phase-1 workflow artifact must upload the retained PNG and SCR alongside JSON
   evidence. Debugger/RAM assertions remain the primary correctness oracle; this
   screenshot proof is mandatory supplemental certification evidence, not a replacement
   for deterministic target-state assertions.

### 7.10 Phase-11 maintained-DOCX / pinned-SDK conformance

Phase 11 must treat REV12 as controlling architecture, the maintained C48 DOCX as the
project's detailed language specification, and the pinned read-only Python SDK
implementation (`compiler/c48.py` plus relevant `compiler/c48/` modules) as a mandatory
reference to reconcile rather than silently copy. DOCX conflicts with REV12 require a
normal-SoP DOCX correction; native compiler/tests must conform to REV12 and the corrected
DOCX; SDK conflicts are recorded as read-only divergences; and a DOCX/SDK disagreement
that REV12 does not decide must be resolved in the maintained DOCX before implementation
closure. No unresolved discrepancy is admissible at P11.39/P11.48. The 205-test SDK
compiler corpus and separate 54-source H06 matrix remain mandatory and may not be
weakened.

The binary DOCX license exemption must remain exact-path and exact-blob bound. A future
DOCX edit must deliberately rebind that identity through the normal SoP; blanket `.docx`
exemptions are forbidden.

## 8. C1 work — re-certify and activate Phase 0

From exact clean `S0`:

1. Confirm current `main` is still `S0` before the certification workflow begins its
   source run. If `main` advanced before activation, do not certify or activate stale
   `S0`; rerun the Section-4 restart procedure, verify the current descendant still has
   the exact reviewed source contracts, and establish the current commit as the new
   source anchor before certification. The evidence activation must remain a direct
   child of the source it certifies.
2. Bootstrap/verify the pinned environment as the workflow requires.
3. Execute all E0.01-E0.06 build/test steps in order.
4. Execute all P0.01-P0.34 build/test steps in order.
5. Finalize `E0.04.result.json`, `P0.34.result.json`, and `phase-0.json`.
6. Retain any still-required P1.01-P1.12 transition revalidation as diagnostics/staged
   evidence only.
7. Require every Phase-0 durable record to name:
   - `source_commit = S0`;
   - one exact toolchain digest;
   - `architecture_sha256 = NEW_ARCH`;
   - `worktree_clean = true`.
8. Activate the new 83-record Phase-0 set in an evidence-only direct child `A0` of
   `S0`.
9. Prove historical Phase-1 durable JSON remained byte-identical across `A0`.
10. Run `tools/check_phase0_evidence.py --require-active` against `A0`/current main and
    require PASS.
11. Phase 1 must still be treated as historical/pre-activation for `NEW_ARCH` at this
    point.

If the workflow fails, inspect the exact job, logs, progress marker, retained failure
artifact, and any copied kernel/hash diagnostic before changing source. A source fix
creates a new `S0`; all clean scans and Phase-0 certification then restart against that
new source identity.

## 9. C2/C3 work — re-certify and activate Phase 1

After `A0` is active, C2 starts at step 1. C3 already has `S1` and starts at step 3.

1. Change only `.github/phase1-certification.trigger` with an inert rebaseline marker
   and pass the project SoP for that exact change.
2. Commit it directly to `main`. Call this clean Phase-1 source `S1`.
3. The Phase-1 workflow must first prove Phase 0 is active for `NEW_ARCH`.
4. Execute the complete registered P1.01-P1.41 gate against exact clean `S1`.
5. Finalize the 84-record Phase-1 set against:
   - `source_commit = S1`;
   - the exact toolchain digest;
   - `architecture_sha256 = NEW_ARCH`;
   - `worktree_clean = true`.
6. Preserve P1.40 strict mid-LDIR interrupt proof and P1.41 aggregate SNA smoke proof.
7. On successful attempt 1, inspect the run and job IDs. Because activation remains
   gated on `github.run_attempt > 1`, re-run the single `phase1-certification` job so
   the complete job executes as the later attempt.
8. The later successful attempt must install the staged P1 records unchanged and create
   evidence-only activation commit `A1`, a direct child of certified source `S1`.
9. Prove `tools/check_phase1_evidence.py --require-active` passes.
10. Prove Phase-0 active evidence still passes and was not mutated by Phase-1
    activation.

Never synthesize, patch, or copy-edit certification JSON by hand.

If an interrupted chat ends while a workflow is running, the next chat must use
Section 4 and the workflow/run history to resume. It must not start a duplicate
certification blindly.

## 10. C4 final closure audit

The controlled change is complete only when all of these are proved against current
`main`:

1. `/etc/issue` is exactly the Section-2 144-byte payload.
2. The third line is exactly `48K. One Z80. No excuses.`.
3. No live architecture/plan/source/test/expected-output contract still freezes or
   checks the former issue bytes.
4. Historical read-only documents were not rewritten merely to erase history.
5. Current REV12 hashes to `NEW_ARCH`.
6. E0.02 and all architecture digest binders use `NEW_ARCH`.
7. Active Phase-0 aggregate uses `NEW_ARCH`, passes its validator, and contains the
   exact 83-record manifest.
8. Active Phase-1 aggregate uses `NEW_ARCH`, passes its validator, and contains the
   exact 84-record manifest.
9. Phase-0 and Phase-1 negative evidence suites still reject their intended corruptions.
10. Phase-0 source binding/activation rules still pass.
11. Phase-1 source binding/activation rules still pass.
12. P1.40 strict interrupt evidence and P1.41 aggregate smoke evidence remain present.
13. Quality/CI has a successful run whose checked-out `main` contains both active new
    evidence sets.
14. Project policy and license-header gates pass.
15. No unexpected source, generated residue, or certification diagnostic is committed.
16. No Phase-2 implementation path was started or modified as part of this work.
17. `main` is the intended descendant of `S0 -> A0 -> S1 -> A1` (allowing only
    separately reviewed intervening commits whose effects have been revalidated).
18. The repository is clean at the final checked source/evidence state.

19. Phase 0 uses the canonical ZX-UX font from the beginning and no active Phase-0 generator regenerates an alternate font.
20. P0.10 validates canonical font identity and P12.05 no longer depends on later promotion from a knowingly different fixture.
21. P1.21/P1.22 consume the canonical font asset, and P1.22 certification includes the retained PNG/SCR pair plus mandatory automated visual inspection of the captured frame.
22. The P1.22 test record and Phase-1 finalizer both fail closed if the screenshot/visual-proof artifacts, hashes, or visual assertions are absent or changed.
23. DOCX license handling remains exact/fail-closed and Phase 11 retains the maintained-DOCX review/correction plus pinned Python implementation comparison.
24. The 205-test SDK compiler corpus and 54-source H06 matrix remain intact, and no unresolved architecture/DOCX/SDK/native discrepancy is admissible.
25. This runbook accurately describes the final combined rebaseline.

Only after all closure checks pass may Phase 0 and Phase 1 again be called frozen and
complete under the combined rebaseline.

## 11. Blocker instrumentation rules

When a step blocks:

1. Capture the exact current `main` SHA and workflow run/job/attempt IDs.
2. Capture the exact failing command, exit code, stdout/stderr, and named assertion.
3. Compare expected and actual source commit, architecture digest, toolchain digest,
   prerequisite chain, and evidence filenames before changing code.
4. For workflow failures, fetch job steps and logs before retrying.
5. For evidence failures, inspect aggregate manifest hashes and the activation commit's
   parent/message/changed-file set.
6. For `/etc/issue` failures, dump length, SHA-256, final byte, CR count, and exact
   byte representation before editing.
7. For architecture identity failures, hash the fetched canonical REV12 bytes directly;
   never trust a copied digest.
8. For search/index anomalies, fall back to direct tree/file inspection and exact
   tracked-file scans. An empty indexed search is not proof that a literal is absent.
9. Prefer a diagnostic-only observation to speculative source mutation.
10. If a fix changes any proposed bytes after SoP scanning, reset the clean-scan count
    to zero.

## 12. Session handoff record

Do not depend on editing this section after every chat. Repository/evidence state is the
primary checkpoint.

When useful, a session may add a short reviewed update to a separate scratch status file,
but a new session must still run Section 4. At minimum a handoff note should record:

- observed `main` SHA;
- checkpoint C0/C1/C2/C3/C4/DONE/BLOCKED-MIXED;
- `NEW_ARCH` if known;
- `S0`, `A0`, `S1`, `A1` if they exist;
- workflow run/job/attempt IDs currently relevant;
- exact blocker/assertion if blocked;
- next deterministic action.

A stale handoff note never overrides repository state.

## 13. Stop condition

Stop this rebaseline work immediately after Section 10 closes. Do not use successful
re-certification as implicit authorization to begin Phase 2.
