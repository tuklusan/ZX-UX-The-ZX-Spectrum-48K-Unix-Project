#!/usr/bin/env bash
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

set -euo pipefail
required_files=(LICENSE README.md docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md .github/workflows/exact-head-regression.yml .github/workflows/quality-and-ci.yml .github/workflows/qualification-auto-dispatch.yml .github/actions/setup-zxux-runtime/action.yml tools/check_project_policy.py tools/check_license_headers.sh tools/check_reference_tree.py tools/scripts/record-bootstrap-provenance.py)
for file in "${required_files[@]}"; do test -f "$file" || { echo "ERROR: required file missing: $file" >&2; exit 1; }; done
python3 ./tools/check_reference_tree.py
while IFS= read -r -d '' file; do
  [[ "$file" == "./reference/"* ]] && continue
  if grep -Iq '' "$file"; then
    if [[ ! "$file" =~ \.(md|markdown|mdown|mdx)$ ]] && grep -nE '[[:blank:]]+$' "$file"; then echo "ERROR: trailing whitespace in $file" >&2; exit 1; fi
    if LC_ALL=C grep -n $'\r' "$file"; then echo "ERROR: carriage return found in $file" >&2; exit 1; fi
  fi
done < <(find . -path './.git' -prune -o -type f -print0)
python3 - <<'PY'
from pathlib import Path
import re
RUNNER="ubuntu-24.04"
expected={"actions/checkout":"3d3c42e5aac5ba805825da76410c181273ba90b1","actions/setup-python":"ece7cb06caefa5fff74198d8649806c4678c61a1","actions/upload-artifact":"043fb46d1a93c77aae656e7c1c64a875d1fc6a0a","actions/cache/restore":"8b402f58fbc84540c8b491a91e594a4576fec3d7","actions/cache/save":"8b402f58fbc84540c8b491a91e594a4576fec3d7"}
uses_re=re.compile(r"uses:\s+(actions/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)@([^\s#]+)")
historical=re.compile(r"^p\d+.*\.yml$")
workflows=[]
for path in sorted(Path(".github/workflows").glob("*.yml")):
    name=path.name
    if historical.match(name) or any(token in name for token in ("-once.yml","-repair-","-probe-")): continue
    workflows.append(path)
for path in workflows:
    for n,line in enumerate(path.read_text().splitlines(),1):
        stripped=line.strip()
        if stripped.startswith("runs-on:") and stripped != f"runs-on: {RUNNER}": raise SystemExit(f"ERROR: runner not pinned: {path}:{n}")
for path in workflows+[Path(".github/actions/setup-zxux-runtime/action.yml")]:
    for n,line in enumerate(path.read_text().splitlines(),1):
        if "uses: actions/" not in line: continue
        m=uses_re.search(line)
        if not m: raise SystemExit(f"ERROR: unparseable action: {path}:{n}")
        action,ref=m.groups()
        if expected.get(action)!=ref: raise SystemExit(f"ERROR: unapproved or unpinned action: {path}:{n}: {action}@{ref}")
for path in (Path(".github/workflows/exact-head-regression.yml"),Path(".github/workflows/candidate-kernel.yml"),Path(".github/workflows/phase0-certification.yml"),Path(".github/workflows/quality-and-ci.yml"),Path(".github/workflows/phase1-certification.yml"),Path(".github/workflows/phase2-validation.yml")):
    if "uses: ./.github/actions/setup-zxux-runtime" not in path.read_text(): raise SystemExit(f"ERROR: runtime workflow missing certified cache action: {path}")
runtime=Path(".github/actions/setup-zxux-runtime/action.yml").read_text()
for marker in ("tools/scripts/record-bootstrap-provenance.py","tools/runtime/bootstrap-provenance.json","ZX-UX BOOTSTRAP PROVENANCE (informational; not certification input)","provenance_sha=","action_sha=","Verify restored runtime before package installation"):
    if marker not in runtime: raise SystemExit(f"ERROR: runtime wiring missing: {marker}")
verify=Path("tools/scripts/verify-environment.py").read_text()
if "bootstrap-provenance.json" in verify or "record-bootstrap-provenance" in verify: raise SystemExit("ERROR: bootstrap provenance became certification input")
dispatch=Path(".github/workflows/qualification-auto-dispatch.yml").read_text()
if "workflow_run:" not in dispatch or "time.sleep" in dispatch or "REGRESSION GATE TIMEOUT" in dispatch: raise SystemExit("ERROR: qualification dispatch is not completion-driven")
for path in (Path(".github/workflows/candidate-kernel.yml"),Path(".github/workflows/phase1-certification.yml"),Path(".github/workflows/phase2-validation.yml")):
    if "\n  push:" in path.read_text(): raise SystemExit(f"ERROR: historical heavyweight workflow remains push-triggered: {path}")
PY
grep -Fq 'Direct check-in to `main` is the normal path' docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md
grep -Fq 'Branching and later merging are discouraged' docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md
echo "ZX-UX CI policy checks passed."
