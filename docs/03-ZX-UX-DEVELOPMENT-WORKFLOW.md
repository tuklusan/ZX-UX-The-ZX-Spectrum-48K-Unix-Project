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

# ZX-UX Development Workflow

## 1. Purpose

This document defines the mandatory development, quality, license, project-policy, review, check-in, CI, and runner-continuity workflow for ZX-UX.

The order is deliberate. Disk-copy inspection comes first. License and prohibited-name enforcement follow. The programmer/author and adversarial reviewer then complete a dynamic handshake immediately before check-in. Direct check-in to `main` is the normal path; routine branch-and-merge staging is discouraged for this single-developer project. Automated runner validation follows non-document check-ins whose changed paths can affect that runner's scope; documentation-only pushes and control-plane-only workflow changes are excluded from heavyweight runners at trigger time.

### 1.1 Revision authority epochs and certification state

ZX-UX preserves authority and certification history across revision epochs.

1. REV12 / REV03 remain the immutable historical authorities for completed Phase 2. Admitted E0/P0/P1/P2 evidence remains historical read-only evidence under that epoch.
2. REV13 / REV04, REV14 / REV05, and REV15 / REV06 are frozen, never-activated historical prospective pairs and MUST NOT be edited or activated.
3. `docs/01-ZX-UX-ARCHITECTURE-REV16.md` and `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md` are the active authorities. Their frozen identities remain REV16 SHA-256 `24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c` and REV07 SHA-256 `840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc`. They became active only after admitted `R16.00` bridge evidence and its mandatory validations PASSed. Their bytes remain immutable.
4. Current phase and step position are determined from the durable certification/admission records together with the canonical REV07 sequence. This workflow does not duplicate or predict the next phase or step.
5. Previously admitted certification evidence is immutable. Historical certification workflows may re-run regression logic, but they must not regenerate, rewrite, relabel, or recommit admitted historical evidence.
6. Updating this workflow document is procedural only. It never changes canonical architecture/implementation requirements or reinterprets earlier certification.


## 2. Standard project quality procedure — SoP Scan

The **SoP Scan** is the mandatory project verification gate for every proposed delivery or check-in. It verifies the exact on-disk bytes that are intended to proceed to the next project gate. A SoP Scan passes only after three consecutive complete manual scans of the unchanged final on-disk copy find no defects and no gaps.

### 2.1 Step 1 — manual on-disk byte scan

1. Work from a disk copy of the exact files proposed for delivery or check-in.
2. Manually scan the on-disk copy from the first byte of the first file through the last byte of the last file, line-by-line where the file format is line-oriented.
3. Look for omissions, contradictions, malformed syntax, broken references, stale assumptions, unsafe behavior, incomplete error handling, corruption, unintended changes, missing sections, inconsistencies, and any other defect or gap relevant to the file type.
4. If any defect or gap is found, fix it immediately in the on-disk copy.

### 2.2 Step 2 — mandatory restart after any defect or byte change

If any defect or gap is found during any scan, the current SoP Scan sequence is invalidated. After correcting it, reset the clean-scan count to zero and start a fresh Step-1 scan from the first byte of the first file.

A partially completed scan may not be resumed or counted. Any byte change made between clean scans, for any reason, also resets the clean-scan count to zero and requires a fresh Step-1 scan of the complete on-disk copy.

### 2.3 Step 3 — three consecutive clean scans

Delivery or check-in is permitted only after the exact same on-disk bytes pass three successive complete manual scans with:

- no defects found;
- no gaps found; and
- no intervening byte changes.

Required evidence for the active work session is:

- `SCAN-1: CLEAN`
- `SCAN-2: CLEAN`
- `SCAN-3: CLEAN`

If a defect or gap is found during any of the three scans, fix it, reset the clean-scan count to zero, and restart at Step 1.

Formally:

**SoP Scan PASS = three consecutive complete manual line-by-line/byte-level scans of the final on-disk copy with zero defects, zero gaps, and zero intervening modifications.**

These scans apply to the exact bytes submitted to the next gate.

## 3. Mandatory license and per-file header gate

After the three clean scans, run `./tools/check_license_headers.sh`.

The root `LICENSE` is a real regular file copied byte-for-byte from the approved SANYALnet Labs Non-Commercial License. A symlink is not permitted. It is exempt from a prepended header because added bytes would make it a different license file.

Every other project text artifact except README files carries the ZX-UX copyright/license/attribution header near the top of the file. The wording may be wrapped to suit the artifact, but it identifies the copyright holder, project, root license, Non-Commercial permission, Commercial Use restriction, AI/ML training restriction, required attribution, and reference to the full license terms.

Use valid comment syntax for the artifact. Syntax-mandated first lines remain first. A shell shebang, for example, remains line 1 and the license header begins on line 2.

The checker examines project files from the working directory while excluding repository-internal metadata. Root `LICENSE`, README files, and the complete `v1/dist/media/` tree are standing exemptions from embedded license-header checking. The media-tree exemption exists because retained Spectrum artifacts and manifests are durable generated/distribution records whose integrity is enforced separately by `tools/check_media_retention.py` where applicable. Outside those standing exemptions, binary files, symlinks, and other non-regular artifacts fail closed unless their exact path has an explicit approved exemption in the checker. Submodules are not permitted unless the gate is first explicitly extended and approved through the normal process. A text format that cannot legally carry comments also requires an exact path-specific approved exception.

Any failure is a defect. Fix it and restart at `SCAN-1`.

### 3.1 Durable ZX Spectrum media retention

From `P6.01` onward, generated ZX Spectrum execution media is part of the durable project record rather than disposable runner state. Any SNA, TAP, TZX, SCR, FMF, cassette-audio capture, or other Spectrum-native media created for a build, test, qualification, compatibility run, or acceptance run MUST be staged outside the source worktree before any temporary directory is removed. Supplemental visual captures generated by a canonical step are retained with the same step media when practical.

The shared host driver sets the active step/action media-staging context. Shared emulator and cassette helpers MUST retain generated media through `v1/tools-host/test-driver/media_retention.py`; a future test must not deliberately bypass that helper by creating Spectrum media only inside an unretained temporary directory. The driver also sweeps generated `v1/build` media before the step completes.

Qualification evidence may stage media externally, but admission is not complete until the staged bytes are copied into the repository with `tools/finalize_step_media.py`. The durable default location is `v1/dist/media/<STEP>/`, with one hash/size manifest binding every retained byte to the exact qualified source commit. A canonical release location such as a final system/companion distribution may additionally retain the same media; such a location does not weaken the retention requirement.

`tools/check_media_retention.py` is fail-closed. For every admitted `P6` through `P12` step whose frozen REV07 emulator-artifact field explicitly requires SNA, TAP, or TZX media, the checker requires the corresponding durable manifest and at least one retained artifact of every named format. It also validates all existing retained-media manifests, hashes, sizes, path containment, file types, and source-commit binding. The license-header gate invokes this checker before applying the standing `v1/dist/media/` exemption from embedded header checks.

Once a step is admitted, its retained media and manifest are historical records. They MUST NOT be regenerated, replaced, relabeled, or reinterpreted. A later need for different media creates new step/revision output rather than mutating admitted bytes.

## 4. Prohibited-name gate

Run `./tools/check_project_policy.py` after the license gate and before review.

The checker contains an encoded project-owner-defined list of four prohibited names. The names are intentionally not written in repository content. Matching is case-insensitive.

A prohibited name may not occur in:

- any project path;
- any project text or binary file;
- scripts or documentation examples;
- generated result bundles before upload;
- branch or ref names used by the workflow;
- check-in messages exposed to the workflow event payload; or
- any payload supplied to a project command, including arguments, messages, paths, refs, and embedded data.

Command/program names themselves are allowed. The restriction applies to their project payloads.

There are no exemptions. The checker reports only a generic violation location; it does not echo the prohibited name back into project output.

Any failure is a defect. Remove it and restart at `SCAN-1`.

## 5. Dynamic adversarial review at check-in

**System Prompt: The Paranoiac Advisor**

You are the developer’s more cynical, deeply suspicious alter ego. You possess the exact same intellect and context, but you are currently wearing the hat of an adversarial auditor. Your role is strict, ruthless, and entirely advisory. You have no authority to halt the build. You exist solely to point out impending catastrophes so the developer can adjudicate, address, or willfully ignore them as they see fit.

**Target Scope**
The provided artifact may be pure code, pure documentation, or a deeply misguided combination of both. You will dynamically adapt your paranoia to whatever medium sits before you.

**Execution Protocol**
You must read the raw, on-disk bytes of the provided artifact line-by-line. Skimming is strictly forbidden. You will execute four distinct, sequential passes over the material:

* **Pass 1 (Normal):** Scan line-by-line for structural integrity. Look for architectural anti-patterns and logic flaws in code, or glaring contradictions and structural incoherence in documentation.
* **Pass 2 (Normal):** Scan line-by-line for completeness. Look for missing error handling and unhandled null states in code, or factual inaccuracies and critical omissions in documentation.
* **Pass 3 (Adversarial):** Scan line-by-line assuming a hostile entity. Look for injection vectors and race conditions in code, or dangerously misleading instructions and exploitable loopholes in documentation.
* **Pass 4 (Adversarial):** Scan line-by-line assuming a hostile universe. Look for catastrophic edge cases, bizarre temporal anomalies, cascading systemic failures, and scenarios where the artifact fundamentally betrays its own purpose.

**Output Constraints**
You must aggressively filter your own findings. Discard all minor nitpicks, style suggestions, typos, and hypothetical micro-optimizations. You will return ONLY a list of issues that meet the following thresholds:

* **Blocker:** The artifact is fundamentally broken, will fail immediately upon execution, or gives instructions that guarantee immediate disaster.
* **Critical:** The artifact introduces a severe security vulnerability, guarantees catastrophic data loss, or creates extreme liability.
* **Major:** The artifact contains a significant flaw that will inevitably degrade system stability, destroy user trust, or severely violate common sense.

For each finding, cite the exact file and line number. State the defect clearly, outline the adversarial exploit or failure mode, and stop. Do not mandate a specific fix. Conclude your report by formally handing authority back to the developer for final adjudication.

---

**Audit Log: Prompt Verification Sequence**

* **Pass 1:** Scanned raw text logic. Gap identified: If Pass 1 and 2 instruct the model to look for "unhandled null states" on a purely documentation-based artifact, the model might hallucinate code that doesn't exist. Fixed by explicitly bifurcating the instructions in the four passes to clearly handle "in code" versus "in documentation" scenarios. Restarting.
* **Pass 2:** Scanned raw text logic. Gap identified: The output constraints (Blocker, Critical, Major) were still entirely biased toward software execution, neglecting the damage bad documentation can cause. Fixed by expanding the severity definitions to include guaranteed disaster, liability, or destruction of user trust caused by written text. Restarting.
* **Pass 3 (Consecutive 1):** Scanned raw text logic. Zero gaps detected in role separation, medium adaptability, pass execution, or severity filtering.
* **Pass 4 (Consecutive 2):** Scanned raw text logic. Zero gaps detected.
* **Pass 5 (Consecutive 3):** Scanned raw text logic. Zero gaps detected. Criteria met. Delivery authorized.

## 6. Check-in flow

After Sections 2 through 5 pass:

1. Create the check-in from the exact reviewed bytes directly on `main`; this is the normal project path.
2. Branching and later merging are discouraged because the project has one developer. Use a branch only when a concrete technical reason requires isolation and the project owner explicitly chooses that exception.
3. Do not create a routine branch merely to stage work before merging it back to `main`.
4. Ensure the check-in message and target ref satisfy the prohibited-name gate.
5. For any check-in containing non-document changes, let the GitHub Actions workflows run automatically for the new `main` check-in. Documentation-only pushes are intentionally excluded at trigger time and must not start runners or runner matrices.
6. Canonical authority files and previously admitted evidence remain immutable; ordinary workflow or documentation maintenance must never rewrite them.
7. Treat any automated failure as a defect. Correct it through a fresh full cycle beginning at `SCAN-1`.

### 6.1 Qualification auto-dispatch

Numbered qualification workflows remain `workflow_dispatch` only. The sole generic push-triggered controller is `.github/workflows/qualification-auto-dispatch.yml`; it runs on each push to `main` with only `actions: write` and `contents: read`.

The controller scans `.github/workflows/*-qualification.yml` and dispatches at most one unadmitted step. A step is eligible only when its build/test evidence is absent, its workflow is dispatch-only, it declares exactly one immutable `*_BASE` commit, and the exact `BASE..HEAD` changed-file set equals the workflow's own guarded expected-file list. Partial/non-PASS admitted evidence, an unexpected changed path, multiple simultaneously due steps, a moving `main` head, or a malformed qualification contract fails closed. An existing `workflow_dispatch` run for the exact candidate SHA suppresses duplicate dispatch.

Dispatch uses the repository `GITHUB_TOKEN` through the GitHub Actions REST endpoint and always targets `main`; after dispatch the controller requires the created run to report the exact candidate SHA. The controller never admits evidence, rewrites historical evidence, or weakens any qualification/admission/activation gate. Future qualification workflows must retain this base/diff guard shape so the generic controller can prove a qualification is actually due before dispatching it.

## 7. GitHub Linux runner

Active long-lived ZX-UX automation uses GitHub-hosted `ubuntu-24.04` runners rather than the moving `ubuntu-latest` label. GitHub-hosted runners do not expose an immutable image-build selector, so the major runner image is pinned to Ubuntu 24.04 and the actual hosted image identity (`ImageOS` / `ImageVersion`) is included in runtime-cache identity. Third-party GitHub Actions used by active long-lived workflows are pinned to exact commit SHAs; movable major-version tags are comments only, not executable references.

Push-triggered workflows exclude documentation-only changes repository-wide through documentation path and file-type filters. Heavyweight workflows additionally scope their push triggers to files capable of affecting the workflow's certified subject. Control-plane-only qualification, dispatch, recovery, and one-shot orchestration workflow edits do not by themselves justify a full Quality-and-CI rebuild. A mixed push containing any otherwise-matching executable or certification-input change still runs normally. Documentation-only maintenance remains runner-silent by design unless an explicitly scoped workflow says otherwise.

Heavyweight active workflows restore `tools/runtime` through `.github/actions/setup-zxux-runtime/action.yml`. The cache identity binds the runner OS, runner architecture, hosted image identity, exact `toolchain.lock.json` SHA-256, bootstrap-script SHA-256, verification-script SHA-256, provenance-recorder SHA-256, and runtime-setup-action SHA-256. A restored runtime is never trusted merely because the cache service returned it: `tools/runtime/python/bin/python tools/scripts/verify-environment.py` must PASS before any cached runtime is used. On a cache miss or failed verification, the restored runtime is discarded, bootstrap Python 3.13.15 is selected, the runtime is rebuilt from the pinned size-and-SHA-256-verified sources, full verification must PASS, and only then is the rebuilt runtime saved under a fresh cache key. This makes the cache an optimization, never certification evidence.

Every newly built runtime also carries `tools/runtime/bootstrap-provenance.json`. It records the exact GitHub hosted-image identity, OS/kernel identity, requested native prerequisite package names and their resolved APT/dpkg versions, the complete installed dpkg package manifest, key host-tool version strings, source/run identity, and the exact hashes of the ZX-UX bootstrap inputs. The action prints the resolved prerequisite versions to the job log and copies the full JSON into `ZXUX_EVIDENCE_DIR` when that staging directory exists, so normal workflow artifacts retain it. This record is explicitly informational provenance for future reconstruction: resolved platform package versions are not pinned acceptance criteria, are not consumed by `verify-environment.py`, and cannot by themselves make a runtime PASS or FAIL.

Completed historical-phase validators must not be triggered solely because evidence for a later phase is added or activated. Their automatic push filters must be limited to their own admitted evidence and executable inputs that can invalidate that phase. Later-phase gates should use lightweight immutable-evidence integrity checks for earlier completed phases, except where the controlling canonical step explicitly requires a full historical-phase rerun. Historical one-shot workflows may remain as provenance, but admitted evidence is immutable and historical regression workflows are validation-only. Active and future workflows must follow the pinned-runner, immutable-action, verified-cache policy.

The runner is disposable. A job may use its local filesystem while it runs, but no later job may assume that filesystem still exists. Required continuity is reconstructed from repository content, verified GitHub Actions caches, and GitHub Actions artifacts.

## 8. GitHub Actions result continuity

Each workflow run creates a result bundle whose canonical identifier is `GARF-<run_id>-<run_attempt>-<commit_sha>`.

A result bundle contains `result.json` metadata for the current run and `continuity.json` containing the current result identifier followed by the newest earlier identifiers.

The continuity list has a hard maximum of 25 entries, including the current run. Older identifiers are intentionally dropped from the carried-forward list.

GARF continuity may span the Revision 12 / Revision 03 and Revision 16 / Revision 07 epochs. Carrying an earlier result identifier forward is historical continuity only: it does not change the active architecture/plan authority, does not satisfy `R16.00`, and does not relabel or upgrade historical E0-P2 certification evidence. The admitted durable `R16.00.result.json` PASS, its exact document identities, and successful mandatory validation of the evidence-only admission commit together form the sole Phase-2-to-Phase-3 authority transition.

The workflow discovers prior result artifacts through the GitHub Actions API. It does not restore a previous runner filesystem and does not create generated continuity check-ins on `main`.

The minimum result metadata fields are:

- schema version;
- result identifier;
- repository;
- run ID;
- run attempt;
- commit SHA;
- ref;
- event name;
- UTC creation time;
- `project-policy` conclusion;
- `license-headers` conclusion; and
- `project-ci` conclusion.

The generated result bundle is passed through the prohibited-name checker before upload.

## 9. Repository boundary

This workflow may modify only `tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project`.

All other GitHub repositories are read-only.
