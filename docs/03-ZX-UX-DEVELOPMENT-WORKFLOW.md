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

## 2. Standard project quality procedure

For every proposed delivery or check-in:

1. Work from a disk copy of the exact files proposed for check-in.
2. Scan every proposed file line-by-line from the first line through the last line.
3. Look for omissions, contradictions, malformed syntax, broken references, stale assumptions, unsafe behavior, incomplete error handling, and other defects relevant to the file type.
4. If any defect is found, fix it immediately.
5. After any fix, restart the clean-scan count at zero and begin again from the first line of the first file.
6. Do not change any file between clean scans. Any byte change resets the clean-scan count to zero.
7. Delivery is permitted only after three successive complete scans find zero defects.

Required evidence for the active work session is:

- `SCAN-1: CLEAN`
- `SCAN-2: CLEAN`
- `SCAN-3: CLEAN`

These scans apply to the exact bytes submitted to the next gate.

## 3. Mandatory license and per-file header gate

After the three clean scans, run `./tools/check_license_headers.sh`.

The root `LICENSE` is a real regular file copied byte-for-byte from the approved SANYALnet Labs Non-Commercial License. A symlink is not permitted. It is exempt from a prepended header because added bytes would make it a different license file.

Every other project text artifact carries the ZX-UX copyright/license/attribution header near the top of the file. The wording may be wrapped to suit the artifact, but it identifies the copyright holder, project, root license, Non-Commercial permission, Commercial Use restriction, AI/ML training restriction, required attribution, and reference to the full license terms.

Use valid comment syntax for the artifact. Syntax-mandated first lines remain first. A shell shebang, for example, remains line 1 and the license header begins on line 2.

The checker examines project files from the working directory while excluding only repository-internal metadata. Root `LICENSE` is the only standing text-file exemption. Binary files, symlinks, and other non-regular artifacts fail closed unless their exact path has an explicit approved exemption in the checker. Submodules are not permitted unless the gate is first explicitly extended and approved through the normal process. A text format that cannot legally carry comments also requires an exact path-specific approved exception.

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
6. Treat any automated failure as a defect. Correct it through a fresh full cycle beginning at `SCAN-1`.

## 7. GitHub Linux runner

ZX-UX uses GitHub-hosted `ubuntu-latest` runners for project automation and CI.

Push-triggered workflows exclude documentation-only changes repository-wide through documentation path and file-type filters. A mixed push containing any otherwise-matching non-document change still runs normally.

The runner is disposable. A job may use its local filesystem while it runs, but no later job may assume that filesystem still exists. Required continuity is reconstructed from repository content and GitHub Actions artifacts.

## 8. GitHub Actions result continuity

Each workflow run creates a result bundle whose canonical identifier is `GARF-<run_id>-<run_attempt>-<commit_sha>`.

A result bundle contains `result.json` metadata for the current run and `continuity.json` containing the current result identifier followed by the newest earlier identifiers.

The continuity list has a hard maximum of 25 entries, including the current run. Older identifiers are intentionally dropped from the carried-forward list.

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
