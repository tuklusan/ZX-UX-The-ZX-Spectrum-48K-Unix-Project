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

The order is deliberate. Disk-copy inspection comes first. License and prohibited-name enforcement follow. The programmer/author and adversarial reviewer then complete a dynamic handshake immediately before check-in. Direct check-in to `main` is the normal path; routine branch-and-merge staging is discouraged for this single-developer project. Automated runner validation follows every normal check-in to `main`.

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

After Sections 2 through 4 pass, review the exact proposed bytes as an **ADVERSARIAL CODE REVIEWER**.

The reviewer reports only `BLOCKER` and `MAJOR` findings. Minor style issues, optional improvements, praise, and cosmetic comments are omitted.

The review happens dynamically between programmer/author and reviewer immediately before check-in. It is not delegated to a hosted merge/review mechanism.

The reviewer does not own the final decision. The programmer/author decides the disposition of every finding and may:

- `FIX`: accept the finding and change the implementation;
- `CLARIFY / RE-REVIEW`: explain why the current implementation is believed correct or why the finding does not apply, with re-review when useful; or
- `OVERRIDE`: explicitly decline the finding and proceed.

When the author disagrees, a concise explanation or clarification in the re-review request normally completes the handshake. A simple explicit override also completes it. The reviewer must not convert disagreement into a separate veto.

If any proposed byte changes, return to Section 2 and restart at `SCAN-1`, then repeat the license and prohibited-name gates before re-review. If no bytes change, the author decision completes the finding without resetting the scans.

When there are no findings, the active work session may record `ADVERSARIAL REVIEW: 0 BLOCKER, 0 MAJOR`.

## 6. Check-in flow

After Sections 2 through 5 pass:

1. Create the check-in from the exact reviewed bytes directly on `main`; this is the normal project path.
2. Branching and later merging are discouraged because the project has one developer. Use a branch only when a concrete technical reason requires isolation and the project owner explicitly chooses that exception.
3. Do not create a routine branch merely to stage work before merging it back to `main`.
4. Ensure the check-in message and target ref satisfy the prohibited-name gate.
5. Let the GitHub Actions workflow run automatically for the new `main` check-in.
6. Treat any automated failure as a defect. Correct it through a fresh full cycle beginning at `SCAN-1`.

## 7. GitHub Linux runner

ZX-UX uses the GitHub-hosted `ubuntu-slim` runner for project automation and CI.

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
