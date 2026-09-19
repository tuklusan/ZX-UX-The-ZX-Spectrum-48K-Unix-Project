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

The order is deliberate. Disk-copy inspection comes first. License and prohibited-name enforcement follow. The programmer/author and adversarial reviewer then complete a dynamic handshake immediately before check-in. Direct check-in to `main` is the normal path; routine branch-and-merge staging is discouraged for this single-developer project. Automated runner validation follows every normal non-document-only check-in to `main`; documentation-only pushes are excluded at trigger time.

### 1.1 Revision authority epochs and the Phase-2/Phase-3 transition

ZX-UX uses a fail-closed authority transition between the complete Phase-2 acceptance gate and the first ordinary Phase-3 step. The transition does not retroactively rewrite earlier certifications.

1. Through and including `P2.24` and the Phase-2 aggregate evidence, the controlling authorities remain `docs/01-ZX-UX-ARCHITECTURE-REV12.md` and `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md`. Those historical authority files and all admitted E0/P0/P1/P2 evidence remain immutable. No historical evidence may be regenerated, relabeled, or reinterpreted under a later authority epoch.
2. Revision 13 / Revision 04, Revision 14 / Revision 05, and Revision 15 / Revision 06 are frozen, never-activated historical prospective authority pairs. Frozen REV14 SHA-256 is `868d6605733061fec00fb82c051e9ab02915041e5e26ddc1563a3c488bc82324`; frozen actual REV05 SHA-256 is `2a7a84e01fd2016b4dfd5421d1510f2474ef7559ee1dea584bbb98d11811e047`; frozen REV15 SHA-256 is `c80b0626d58d79b133de90ee64e598421618ce5c503d6f5d34c866e332e4c398`; frozen actual REV06 SHA-256 is `aeba14b8baa5387b98c158ac00ee9d81e93a162807769497068dac1adc0c8624`. REV05 contains stale Revision-13 identity/bridge labels; REV06 Section 8 contains the obsolete Revision-13 architecture digest despite its correct REV15 header. Therefore `R13.00`, `R14.00`, and `R15.00` were never admissible and MUST NOT be used. None of REV13/REV04/REV14/REV05/REV15/REV06 may be edited in place or activated.
3. `docs/01-ZX-UX-ARCHITECTURE-REV16.md` and `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md` are the current dormant prospective authorities. Their exact identities are pinned here: REV16 SHA-256 `24fe9d206c2f05bbc24f11544a5cb5a0b6ab104e9fc52e654a10c2d9734b008c`; REV07 SHA-256 `840a52e55f623d3f5453329838728e9933ee650ac78c4f294acbca7910638fbc`. The H06 correction carried forward by those exact bytes is pinned to read-only SDK commit `9ca3c6d6b5dd4b6e2351c1800afbd47d1d77e411`, `usr/src` tree `f629dcc1d156b83bf08ed171b9273e3cbb621ad1`, `usr/src/examples/hello.c` Git blob `95fa0186bda3f7636774f5885988d78a13f6450b`, 703 bytes, SHA-256 `6f94a735f230dadf5928993f9a071f3f47e98b63d18230eef102f6ae7b63e4b2`, and direct declaration dependency `usr/src/examples/exapi.h`, 2056 bytes, SHA-256 `2fa0edc593832d3ab57bc105233f41fd81a02b1f3ea022cefc42da01a6084bb8`. Any different REV16/REV07 bytes or H06 canary/header identity fail closed and require a new prospective revision pair.
4. Because Phase 2 and its aggregate are already PASS, `R16.00` may execute once REV16/REV07 are present and the repository is otherwise clean. It MUST execute exactly as defined by Revision 07. The bridge must preserve and verify historical REV12/REV03 identities and Phase-2 evidence, certify the bounded REV16 delta and carried-forward current-tree regressions, advance prospective certification tooling, certify one clean bridge source-candidate commit, and admit only the frozen `R16.00` records in a subsequent evidence-only admission commit.
5. Phase 3 is forbidden until the evidence-only `R16.00` admission commit exists, `v1/dist/certification/R16.00.result.json` records PASS for the exact pinned REV16 architecture identity and exact pinned REV07 implementation-plan identity, and every mandatory automated validation triggered by that admission commit has completed successfully. `P3.01` is the first ordinary phase step permitted after all those conditions are satisfied.
6. After all conditions in item 5 are satisfied, Revision 16 / Revision 07 become the controlling authorities for Phase 3 and all later prospective certification. Historical E0-P2 evidence remains historical read-only evidence under Revision 12 / Revision 03; all never-activated prospective pairs remain frozen historical records.
7. A failed or incomplete `R16.00` leaves completed Phase-2 history intact but leaves the Phase-3 transition closed. Correct any bridge defect through the normal SoP/review/check-in cycle and rerun the bridge; do not mutate frozen canonical revisions to force admission and do not begin `P3.01`.

This workflow document may describe both epochs before the transition occurs. Updating this workflow alone is procedural and does not change the active architecture or implementation-plan authority.

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

The checker examines project files from the working directory while excluding repository-internal metadata. Root `LICENSE` and README files are standing text-file exemptions. Binary files, symlinks, and other non-regular artifacts fail closed unless their exact path has an explicit approved exemption in the checker. Submodules are not permitted unless the gate is first explicitly extended and approved through the normal process. A text format that cannot legally carry comments also requires an exact path-specific approved exception.

Any failure is a defect. Fix it and restart at `SCAN-1`.

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
6. Any documentation-only publication that adds REV16/REV07, whether during Phase 2 or after `P2.24`, follows the same documentation-only runner exclusion. That publication is not an `R16.00` PASS and must not be treated as active authority for Phase 2 or Phase 3. The later `R16.00` source-candidate and evidence-only admission transactions follow Section 1.1 and Revision 07 in addition to this normal check-in flow.
7. Treat any automated failure as a defect. Correct it through a fresh full cycle beginning at `SCAN-1`.

## 7. GitHub Linux runner

ZX-UX uses GitHub-hosted `ubuntu-latest` runners for project automation and CI.

Push-triggered workflows exclude documentation-only changes repository-wide through documentation path and file-type filters. A mixed push containing any otherwise-matching non-document change still runs normally. A documentation-only REV16/REV07 publication is therefore runner-silent by design regardless of whether it occurs during Phase 2 or after `P2.24`; the bridge itself is not established by that publication and remains subject to the explicit `R16.00` certification transaction after the complete Phase-2 PASS.

The runner is disposable. A job may use its local filesystem while it runs, but no later job may assume that filesystem still exists. Required continuity is reconstructed from repository content and GitHub Actions artifacts.

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
