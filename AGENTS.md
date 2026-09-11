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

1. The programmer/author and reviewer handshake happens dynamically immediately before check-in. It is not delegated to a hosted merge/review mechanism.
2. Review the exact proposed bytes as an **ADVERSARIAL CODE REVIEWER**.
3. Report only findings at `BLOCKER` or `MAJOR` priority.
4. Findings are advisory to the programmer/author and do not themselves veto check-in. The programmer/author is the final judge of what action, if any, to take.
5. For a finding, the programmer/author may `FIX`, provide a `CLARIFY / RE-REVIEW` explanation, or `OVERRIDE` it. A clarification is normally sufficient when the author disagrees; a simple explicit override is also sufficient.
6. If the author changes any proposed bytes, restart Gate 1 from `SCAN-1`, then repeat Gates 2 through 4 on the changed bytes.
7. If the author does not change bytes, a clarification, re-review exchange, or override completes the handshake for that finding. The reviewer must not turn disagreement into an independent block.
8. Zero findings may be recorded transiently as `ADVERSARIAL REVIEW: 0 BLOCKER, 0 MAJOR`.
9. Minor comments, style preferences, praise, and non-blocking suggestions are intentionally omitted.

### Gate 5: Direct check-in to `main` and automated validation

1. Check in only the exact bytes that passed Gates 1 through 4.
2. The dynamic review handshake is completed before the check-in is created.
3. Direct check-in to `main` is the normal project workflow. Branching and later merging are discouraged because this is a single-developer project.
4. Create a branch only when a concrete technical reason requires isolation and the project owner explicitly chooses that exception. Do not create branches merely to stage ordinary work before merging it back to `main`.
5. Every normal check-in to `main` triggers the GitHub Actions quality workflow on `ubuntu-slim`.
6. Automated failure after check-in is a defect requiring correction through the complete process beginning again at Gate 1.
7. No reviewer approval status is required or used as an automated blocking condition.

## GitHub Actions development environment

- Project automation and CI use GitHub-hosted `ubuntu-slim` Linux runners.
- Runners are ephemeral. Do not depend on local runner state surviving a job.
- Durable continuity is carried only through repository data and GitHub Actions artifacts.
- The canonical result identifier is `GARF-<run_id>-<run_attempt>-<commit_sha>`.
- Each result bundle preserves a newest-first continuity list containing no more than 25 result identifiers, including the current result.
- The result bundle records at least the result identifier, run ID, run attempt, commit SHA, ref, event, repository, UTC creation time, `project-policy` conclusion, `license-headers` conclusion, and `project-ci` conclusion.
- Do not create machine-generated continuity check-ins on `main`.

## Canonical process

`task -> develop disk copy -> quality scan x3 clean -> license-header gate -> prohibited-name gate -> dynamic adversarial review -> author decision -> direct check-in to main -> ubuntu-slim automated validation`

The detailed procedure is in `docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md`.
