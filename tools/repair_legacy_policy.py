#!/usr/bin/env python3
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX Sinclair ZX Spectrum Unix
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.

from __future__ import annotations

from pathlib import Path
import sys

ROOT_MARKER = b"ZX-UX project root"
TARGET = Path("docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md")
ARCH_SHA = "1D736641E685C1D6136B66FC57D0C16FC662CE6CA4DFD640991743BB01BB706F"


class RepairError(RuntimeError):
    pass


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise RepairError("canonical project root not found")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RepairError(f"{label}: expected one source block, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise RepairError(f"{label}: start marker missing")
    end_at = text.find(end, start_at + len(start))
    if end_at < 0:
        raise RepairError(f"{label}: end marker missing")
    return text[:start_at] + replacement + text[end_at:]


def main() -> int:
    try:
        root = find_root(Path(__file__).resolve())
        target = root / TARGET
        if not target.is_file() or target.is_symlink():
            raise RepairError(f"target is not a regular file: {TARGET}")
        text = target.read_text(encoding="utf-8")

        text = replace_once(
            text,
            "Architecture baseline: `v1/docs/01-ZX-UX-ARCHITECTURE-REV11.md`",
            "Architecture baseline: `docs/01-ZX-UX-ARCHITECTURE-REV11.md`",
            "architecture path",
        )

        section1 = f'''# 1. Certified Development Environment and Gate E0

This document is subordinate to Revision 11. It does not amend the architecture.
If this document conflicts with Revision 11, Revision 11 wins and this document
must be corrected before implementation continues.

The canonical E0 environment is a fresh Linux checkout rooted by `.zxux-root`.
No historical workstation, Windows installation, fixed drive letter, fixed user
profile, pre-existing `tools/runtime/` tree, or ambient PATH tool is part of the
certified baseline.

`tools/manifest/toolchain.lock.json` is the authoritative pinned environment
specification. A CI-selected Python 3.13.15 interpreter may validate metadata and
run `tools/scripts/bootstrap-environment.py`; it is bootstrap tooling only. The
Linux runner explicitly installs the native build prerequisites named by the lock.
Bootstrap then downloads every pinned upstream artifact by HTTPS and verifies its
exact byte size and SHA-256 before use. Source tools, including Python 3.13.15, are
built or installed under `tools/runtime/` at the manifest-owned paths.

Final certification runs only with the acquired project-local runtime:

```text
tools/runtime/python/bin/python tools/scripts/verify-environment.py
```

The verifier requires the canonical architecture at
`docs/01-ZX-UX-ARCHITECTURE-REV11.md` with SHA-256 `{ARCH_SHA.lower()}` and verifies
the project-local SjASMPlus, Fuse, Fuse-utils, and 48K ROM selected by the manifest.
Canonical tool execution uses project-local absolute or root-relative paths, never
ambient PATH resolution. The required final marker is exactly:

```text
ZX-UX DEVELOPMENT ENVIRONMENT CERTIFICATION PASS
```

E0.01 retains an adversarial pre-certification check: a temporary copy of the lock
with one pinned digest changed must be rejected deterministically against the
canonical lock before bootstrap output can be accepted.

---

'''
        text = replace_between(
            text,
            "# 1. Certified Development Environment and Gate E0\n",
            "# 2. Execution Doctrine\n",
            section1,
            "section 1",
        )

        doctrine = '''# 2. Execution Doctrine

Accuracy is the canonical goal. Efficiency is not a goal. The work proceeds in
Revision-11 phase order. A later phase does not begin because its code looks fun.

Every implementation step is a separately check-in-ready transaction. Linux is the
canonical implementation and certification host. After E0.01, `<project-local-python>`
means exactly `tools/runtime/python/bin/python`; the bootstrap interpreter is not a
substitute for the certified runtime. The host runner introduced by E0.03 is
plan-defined host tooling, not target ABI, and no canonical command relies on ambient
PATH tool resolution:

```text
<project-local-python> v1/tools-host/test-driver/run.py build --step <STEP-ID>
<project-local-python> v1/tools-host/test-driver/run.py test --step <STEP-ID>
```

'''
        text = replace_between(
            text,
            "# 2. Execution Doctrine\n",
            "For a target step, the test runner must prefer deterministic debugger-visible\n",
            doctrine,
            "execution doctrine",
        )

        e001 = '''## E0.01 - Aggregate certified-environment gate

1. **Purpose / REV11 requirement:** Establish the reproducible Linux environment required by REV11 host tooling assumptions before implementation or certification continues.
2. **Exact implementation work:** From a fresh Linux checkout with no `tools/runtime/`, validate the canonical lock, install only the explicitly declared native runner prerequisites, acquire every manifest artifact from its pinned HTTPS URL, verify exact size and SHA-256, build/install the pinned Python and host tools under `tools/runtime/`, then run final certification with `tools/runtime/python/bin/python`. The manifest is the authoritative toolchain pin source; no owner override, historical-host dependency, interactive installer, or ambient PATH tool may satisfy the gate.
3. **Files/artifacts created or modified:** `tools/manifest/toolchain.lock.json`; `tools/scripts/bootstrap-environment.py`; `tools/scripts/verify-environment.py`; Linux CI bootstrap metadata.
4. **Build command:** bootstrap with the CI-selected Python 3.13.15 using `python tools/scripts/bootstrap-environment.py`; certify with `tools/runtime/python/bin/python tools/scripts/verify-environment.py`.
5. **Host-side static checks:** root-marker/path policy, manifest schema, HTTPS URLs, exact pinned sizes/SHA-256 values, canonical runtime paths, architecture identity, and Linux-only certification policy.
6. **Emulator test artifact:** N/A: this is a host-only environment gate.
7. **Exact FUSE assertions/checkpoints:** N/A; the pinned Fuse executable is version-checked as environment input.
8. **Expected PASS result:** Bootstrap prints `ZX-UX PINNED TOOLCHAIN ACQUISITION PASS`; final project-local certification exits 0 and ends with exactly `ZX-UX DEVELOPMENT ENVIRONMENT CERTIFICATION PASS`.
9. **Negative/failure test:** Copy the canonical manifest to a temporary file, alter one pinned SHA-256 value, and require `verify-environment.py --metadata-only --manifest <temporary-lock>` to fail specifically because the supplied manifest no longer matches the canonical lock.
10. **Check-in gate:** fresh-Linux fail-before-bootstrap condition is demonstrated by absence of the project-local runtime; bootstrap, metadata verification, final project-local certification, and the manifest-mutation negative test all PASS; end with a clean source worktree apart from ignored generated runtime/build output.
11. **Evidence:** Retain the E0.01 build/test certification record under `v1/dist/certification/` according to the repository evidence contract.

'''
        text = replace_between(text, "## E0.01 - Aggregate certified-environment gate\n", "## E0.02 - Canonical architecture identity gate\n", e001, "E0.01")

        e002 = f'''## E0.02 - Canonical architecture identity gate

1. **Purpose / REV11 requirement:** REV11 at `docs/01-ZX-UX-ARCHITECTURE-REV11.md` is the sole architecture authority.
2. **Exact implementation work:** Hash the canonical on-disk architecture before implementation and compare it with the frozen SHA-256 `{ARCH_SHA.lower()}`. Treat the architecture file as read-only during R&R and normal implementation unless architecture change control explicitly authorizes a revision.
3. **Files/artifacts created or modified:** No architecture modification; only E0.02 certification evidence is produced.
4. **Build command:** `tools/runtime/python/bin/python tools/scripts/verify-environment.py`; E0.02 may use the same verifier internally once the project-local runtime exists.
5. **Host-side static checks:** canonical root marker, exact architecture path, regular-file/no-symlink rule, and exact SHA-256 comparison.
6. **Emulator test artifact:** N/A: this is a host-only identity gate.
7. **Exact FUSE assertions/checkpoints:** N/A.
8. **Expected PASS result:** `docs/01-ZX-UX-ARCHITECTURE-REV11.md` hashes to `{ARCH_SHA.lower()}` and no alternate or superseded architecture is consumed.
9. **Negative/failure test:** Supply an intentionally wrong expected architecture digest to the E0.02 audit path and require deterministic refusal.
10. **Check-in gate:** canonical-path positive verification and wrong-hash negative verification PASS, with no architecture byte change.
11. **Evidence:** Retain the E0.02 build/test certification record under `v1/dist/certification/` according to the repository evidence contract.

'''
        text = replace_between(text, "## E0.02 - Canonical architecture identity gate\n", "## E0.03 - Deterministic test-driver skeleton\n", e002, "E0.02")

        replacements = {
            "REV11 §§37,39-41; handover canonical Python orchestration.": "REV11 §§37,39-41; canonical Linux Python orchestration.",
            "No PATH resolution; no drive-letter dependency; timeout kills the emulator subprocess and fails the test.": "No ambient PATH resolution; no fixed-host-path dependency; timeout kills the emulator subprocess and fails the test.",
            "Run from a copied project on a different drive/path and require the same root-relative behavior.": "Run from a copied project at a different Linux root path and require the same root-relative behavior.",
            "REV11 ordered programming cycle and handover Git philosophy.": "REV11 ordered programming cycle and deterministic Git/evidence discipline.",
            "REV11 §38 and handover SjASMPlus rules.": "REV11 §38 and canonical SjASMPlus rules.",
            "Also retain the handover SjASMPlus rule that unlabelled directives/instructions are indented": "Also retain the canonical SjASMPlus rule that unlabelled directives/instructions are indented",
            "and the handover SjASMPlus indentation rule": "and the canonical SjASMPlus indentation rule",
            "REV11 §40; handover SNA/ROM-call stack lesson.": "REV11 §40; deterministic SNA/ROM-call stack safety lesson.",
        }
        for old, new in replacements.items():
            if old not in text:
                raise RepairError(f"foundation wording missing: {old}")
            text = text.replace(old, new)

        stale_foundation = (
            "Windows-host results",
            "Historical certified/pinned environment",
            "PortableGit",
            "handover final-freeze",
            "handover canonical",
            "handover Git",
            "handover SjASMPlus",
            "F76281FAB2E5AE73B7321FC2A69E6776F7CCD8BFE3955A6ED6FB3BEC44F762C7",
        )
        foundation = text[text.index("# 1. Certified Development Environment"):text.index("# Phase 0 - Hardware")]
        for token in stale_foundation:
            if token in foundation:
                raise RepairError(f"stale foundation token remains: {token}")

        target.write_text(text, encoding="utf-8", newline="\n")
        print(f"repaired={TARGET}")
        return 0
    except (OSError, RepairError, ValueError) as exc:
        print(f"ZX-UX BASELINE REPAIR FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
