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

# ZX-UX Mandatory Development Rules

These rules apply to every change made to this repository.

## Repository boundary

- `tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project` is the only GitHub repository that may be modified.
- All other GitHub repositories are read-only reference material.

## Mandatory order of work

Every proposed check-in must pass these gates in this exact order.

### Gate 1: Standard project quality procedure

1. Scan the disk copy of every file in the proposed change line-by-line for gaps or defects.
2. If any defect is found, fix it and restart the clean-scan count from zero with a fresh scan from the first line.
3. Delivery requires three successive complete scans with zero defects.
4. A scan is not successive if any file changes between scans. Any change resets the count to zero.
5. The scan result must cover the exact bytes submitted to the next gate.

### Gate 2: Mandatory license and per-file header gate

1. The root `LICENSE` must be a real regular file containing the canonical SANYALnet Labs Non-Commercial License and must remain byte-for-byte identical to the approved license source; a symlink is not permitted.
2. `LICENSE` is the only standing text-file exemption from the per-file header rule because adding a header would alter the license itself.
3. Every other project text artifact must carry the ZX-UX copyright/license/attribution header near the top of the file, using comment syntax valid for that artifact type.
4. Preserve syntax-mandated first lines such as a shell shebang or XML declaration; place the license header immediately after them.
5. Binary files, symlinks, and other non-regular artifacts cannot carry embedded text headers, but they are not silently exempt. Each such artifact requires an exact path-specific exemption explicitly approved by the project owner and encoded in `tools/check_license_headers.sh`. Submodules are not permitted unless this gate is first explicitly extended and approved through the normal process.
6. A text format that cannot legally carry comments likewise requires an explicit, path-specific project-owner-approved exception.
7. Blanket extension-based exemptions are prohibited.
8. Run `./tools/check_license_headers.sh` only after Gate 1 has achieved three clean scans.
9. Any license-header failure forbids check-in. Fix it, then restart Gate 1 from `SCAN-1`.

### Gate 3: Prohibited-name gate

1. The project-owner-defined prohibited-name list is enforced by `tools/check_project_policy.py` without spelling the prohibited names anywhere in repository content.
2. A prohibited name may not occur in a project path, text file, binary artifact, generated result bundle, branch/ref name, check-in message, documentation example, script, or command payload used for project work. The command/program name itself is allowed; its arguments, messages, paths, refs, and other payload data must remain clean.
3. Matching is case-insensitive.
4. No exemption is permitted for a prohibited name.
5. Run `./tools/check_project_policy.py` after Gate 2 and before review.
6. Any failure forbids check-in. Remove the occurrence and restart Gate 1 from `SCAN-1`.

### Gate 4: Dynamic adversarial review at check-in

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

### Gate 5: Direct check-in to `main` and automated validation

1. Check in only the exact bytes that passed Gates 1 through 4.
2. The dynamic review handshake is completed before the check-in is created.
3. Direct check-in to `main` is the normal project workflow. Branching and later merging are discouraged because this is a single-developer project.
4. Create a branch only when a concrete technical reason requires isolation and the project owner explicitly chooses that exception. Do not create branches merely to stage ordinary work before merging it back to `main`.
5. Push-triggered GitHub Actions workflows run relevant non-document changes on `ubuntu-latest`; documentation-only pushes are excluded at trigger time and must not start runners or runner matrices.
6. Automated failure after check-in is a defect requiring correction through the complete process beginning again at Gate 1.
7. No reviewer approval status is required or used as an automated blocking condition.

## GitHub Actions development environment

- Project automation and CI use GitHub-hosted `ubuntu-latest` Linux runners.
- Runners are ephemeral. Do not depend on local runner state surviving a job.
- Durable continuity is carried only through repository data and GitHub Actions artifacts.
- The canonical result identifier is `GARF-<run_id>-<run_attempt>-<commit_sha>`.
- Each result bundle preserves a newest-first continuity list containing no more than 25 result identifiers, including the current result.
- The result bundle records at least the result identifier, run ID, run attempt, commit SHA, ref, event, repository, UTC creation time, `project-policy` conclusion, `license-headers` conclusion, and `project-ci` conclusion.
- Do not create machine-generated continuity check-ins on `main`.

## Canonical process

`task -> develop disk copy -> quality scan x3 clean -> license-header gate -> prohibited-name gate -> dynamic adversarial review -> author decision -> direct check-in to main -> ubuntu-latest automated validation for non-document changes`

The detailed procedure is in `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md`.
