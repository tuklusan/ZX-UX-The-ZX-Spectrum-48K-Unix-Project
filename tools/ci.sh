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

fail=0

required_files=(
  "LICENSE"
  "AGENTS.md"
  "README.md"
  "docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md"
  ".github/workflows/quality-and-ci.yml"
  ".github/workflows/candidate-kernel.yml"
  ".github/workflows/phase0-certification.yml"
  ".github/workflows/phase1-certification.yml"
  "tools/check_project_policy.py"
  "tools/check_license_headers.sh"
  "tools/check_reference_tree.py"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "ERROR: required file missing: $file" >&2
    fail=1
  fi
done

if ! python3 ./tools/check_reference_tree.py; then
  exit 1
fi

while IFS= read -r -d '' file; do
  if [[ "$file" == "./reference/"* ]]; then
    continue
  fi
  if grep -Iq '' "$file"; then
    # Markdown trailing spaces can be semantic hard line breaks, not source defects.
    if [[ ! "$file" =~ \.(md|markdown|mdown|mdx)$ ]] && grep -nE '[[:blank:]]+$' "$file"; then
      echo "ERROR: trailing whitespace in $file" >&2
      fail=1
    fi

    if LC_ALL=C grep -n $'\r' "$file"; then
      echo "ERROR: carriage return found in $file" >&2
      fail=1
    fi
  fi
done < <(find . -path './.git' -prune -o -type f -print0)

if [[ -x ./tools/check_project_policy.py ]]; then
  ./tools/check_project_policy.py
else
  echo "ERROR: tools/check_project_policy.py is missing or not executable" >&2
  fail=1
fi

if [[ -x ./tools/check_license_headers.sh ]]; then
  ./tools/check_license_headers.sh
else
  echo "ERROR: tools/check_license_headers.sh is missing or not executable" >&2
  fail=1
fi

workflow=.github/workflows/quality-and-ci.yml

active_runner_workflows=(
  ".github/workflows/candidate-kernel.yml"
  ".github/workflows/quality-and-ci.yml"
  ".github/workflows/phase1-certification.yml"
  ".github/workflows/phase2-validation.yml"
  ".github/workflows/phase3-finalization.yml"
  ".github/workflows/phase4-finalization.yml"
)

for active_workflow in "${active_runner_workflows[@]}"; do
  runner_mismatch="$(grep -HnE '^[[:space:]]*runs-on:' "$active_workflow" | grep -vE 'runs-on:[[:space:]]+ubuntu-24\.04[[:space:]]*
if ! grep -Eq 'branches:[[:space:]]*\[main\]|^[[:space:]]*-[[:space:]]+main[[:space:]]*$' "$workflow"; then
  echo "ERROR: automatic push validation must target main" >&2
  fail=1
fi

if grep -Eq '^[[:space:]]*workflow_run:' "$workflow"; then
  echo "ERROR: Quality/CI must not use workflow_run; certification evidence pushes already trigger push validation" >&2
  fail=1
fi

if ! python3 - <<'PY_POLICY'
from pathlib import Path
import sys

patterns = (
    '**/*.md', '**/*.markdown', '**/*.mdown', '**/*.mdx', '**/*.rst',
    '**/*.adoc', '**/*.asciidoc', '**/*.txt', '**/*.text', '**/*.rtf',
    '**/*.doc', '**/*.docx', '**/*.odt', '**/*.pdf', '**/*.tex',
    '**/*.epub', '**/*.html', '**/*.htm', '**/*.ppt', '**/*.pptx',
    '**/*.odp', '**/*.pages', '**/*.key', 'LICENSE', 'LICENSE.*', 'COPYING',
    'COPYING.*', 'NOTICE', 'NOTICE.*', 'CHANGELOG', 'CHANGELOG.*',
    'CONTRIBUTING', 'CONTRIBUTING.*', 'AUTHORS', 'AUTHORS.*', 'docs/**',
    'scratch/**',
)

quality = Path('.github/workflows/quality-and-ci.yml').read_text(encoding='utf-8').splitlines()
quality_items = {line.strip() for line in quality}
missing = [pattern for pattern in patterns if f"- '{pattern}'" not in quality_items]
if missing:
    print('ERROR: Quality/CI documentation exclusions missing: ' + ', '.join(missing), file=sys.stderr)
    raise SystemExit(1)

for name in ('candidate-kernel.yml', 'phase1-certification.yml'):
    lines = Path('.github/workflows', name).read_text(encoding='utf-8').splitlines()
    items = {line.strip() for line in lines}
    missing = [pattern for pattern in patterns if f"- '!{pattern}'" not in items]
    if missing:
        print(f"ERROR: {name} documentation exclusions missing: " + ', '.join(missing), file=sys.stderr)
        raise SystemExit(1)

document_suffixes = (
    '.md', '.markdown', '.mdown', '.mdx', '.rst', '.adoc', '.asciidoc', '.txt',
    '.text', '.rtf', '.doc', '.docx', '.odt', '.pdf', '.tex', '.epub', '.html',
    '.htm', '.ppt', '.pptx', '.odp', '.pages', '.key',
)
document_basenames = ('LICENSE', 'COPYING', 'NOTICE', 'CHANGELOG', 'CONTRIBUTING', 'AUTHORS')

def is_document_path(path: str) -> bool:
    lower = path.lower()
    base = Path(path).name
    return (
        lower.startswith(('docs/', 'scratch/'))
        or lower.endswith(document_suffixes)
        or any(base == name or base.startswith(name + '.') for name in document_basenames)
    )

phase0_lines = Path('.github/workflows/phase0-certification.yml').read_text(encoding='utf-8').splitlines()
in_push_paths = False
for line in phase0_lines:
    if line == '    paths:':
        in_push_paths = True
        continue
    if in_push_paths and line and not line.startswith('      '):
        break
    if not in_push_paths:
        continue
    item = line.strip()
    if not item.startswith('- '):
        continue
    path = item[2:].strip().strip("'\"")
    if is_document_path(path):
        print(f'ERROR: phase0-certification.yml push allow-list contains documentation path: {path}', file=sys.stderr)
        raise SystemExit(1)

prompt_start = '**System Prompt: The Paranoiac Advisor**'
prompt_end = '* **Pass 5 (Consecutive 3):** Scanned raw text logic. Zero gaps detected. Criteria met. Delivery authorized.'

def reviewer_prompt(name: str) -> str:
    text = Path(name).read_text(encoding='utf-8')
    if text.count(prompt_start) != 1 or text.count(prompt_end) != 1:
        print(f'ERROR: reviewer prompt boundaries missing or duplicated in {name}', file=sys.stderr)
        raise SystemExit(1)
    start = text.index(prompt_start)
    end = text.index(prompt_end, start) + len(prompt_end)
    return text[start:end]

agents_prompt = reviewer_prompt('AGENTS.md')
workflow_prompt = reviewer_prompt('docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md')
if agents_prompt != workflow_prompt:
    print('ERROR: reviewer prompt copies are not byte-identical', file=sys.stderr)
    raise SystemExit(1)
PY_POLICY
then
  fail=1
fi

if ! grep -Fq 'Direct check-in to `main` is the normal project workflow' AGENTS.md; then
  echo "ERROR: direct-main check-in rule missing from AGENTS.md" >&2
  fail=1
fi

if ! grep -Fq 'Branching and later merging are discouraged' AGENTS.md; then
  echo "ERROR: branch-discouragement rule missing from AGENTS.md" >&2
  fail=1
fi

if (( fail != 0 )); then
  exit 1
fi

echo "ZX-UX CI policy checks passed."
 || true)"
  if [[ -n "$runner_mismatch" ]]; then
    printf '%s\n' "$runner_mismatch" >&2
    echo "ERROR: active GitHub-hosted workflow jobs must use ubuntu-24.04" >&2
    fail=1
  fi
done

if ! python3 - <<'PY_ACTION_PINS'
from pathlib import Path
import re

expected = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "ece7cb06caefa5fff74198d8649806c4678c61a1",
    "actions/upload-artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    "actions/cache/restore": "0057852bfaa89a56745cba8c7296529d2fc39830",
    "actions/cache/save": "0057852bfaa89a56745cba8c7296529d2fc39830",
}
paths = [
    Path(".github/workflows/candidate-kernel.yml"),
    Path(".github/workflows/quality-and-ci.yml"),
    Path(".github/workflows/phase1-certification.yml"),
    Path(".github/workflows/phase2-validation.yml"),
    Path(".github/workflows/phase3-finalization.yml"),
    Path(".github/workflows/phase4-finalization.yml"),
    Path(".github/actions/setup-zxux-runtime/action.yml"),
]
pattern = re.compile(r"uses:\s+(actions/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)@([^\s#]+)")
for path in paths:
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), 1):
        if "uses: actions/" not in line:
            continue
        match = pattern.search(line)
        if not match:
            raise SystemExit(f"ERROR: unparseable action reference: {path}:{lineno}")
        action, ref = match.groups()
        required = expected.get(action)
        if required is None:
            raise SystemExit(f"ERROR: unapproved action dependency: {path}:{lineno}: {action}")
        if ref != required:
            raise SystemExit(f"ERROR: action is not pinned to approved immutable SHA: {path}:{lineno}: {action}@{ref}")

for path in (
    Path(".github/workflows/quality-and-ci.yml"),
    Path(".github/workflows/phase1-certification.yml"),
    Path(".github/workflows/phase2-validation.yml"),
):
    if "uses: ./.github/actions/setup-zxux-runtime" not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"ERROR: heavyweight runtime workflow does not use certified runtime cache action: {path}")
PY_ACTION_PINS
then
  fail=1
fi

if ! grep -Eq 'branches:[[:space:]]*\[main\]|^[[:space:]]*-[[:space:]]+main[[:space:]]*$' "$workflow"; then
  echo "ERROR: automatic push validation must target main" >&2
  fail=1
fi

if grep -Eq '^[[:space:]]*workflow_run:' "$workflow"; then
  echo "ERROR: Quality/CI must not use workflow_run; certification evidence pushes already trigger push validation" >&2
  fail=1
fi

if ! python3 - <<'PY_POLICY'
from pathlib import Path
import sys

patterns = (
    '**/*.md', '**/*.markdown', '**/*.mdown', '**/*.mdx', '**/*.rst',
    '**/*.adoc', '**/*.asciidoc', '**/*.txt', '**/*.text', '**/*.rtf',
    '**/*.doc', '**/*.docx', '**/*.odt', '**/*.pdf', '**/*.tex',
    '**/*.epub', '**/*.html', '**/*.htm', '**/*.ppt', '**/*.pptx',
    '**/*.odp', '**/*.pages', '**/*.key', 'LICENSE', 'LICENSE.*', 'COPYING',
    'COPYING.*', 'NOTICE', 'NOTICE.*', 'CHANGELOG', 'CHANGELOG.*',
    'CONTRIBUTING', 'CONTRIBUTING.*', 'AUTHORS', 'AUTHORS.*', 'docs/**',
    'scratch/**',
)

quality = Path('.github/workflows/quality-and-ci.yml').read_text(encoding='utf-8').splitlines()
quality_items = {line.strip() for line in quality}
missing = [pattern for pattern in patterns if f"- '{pattern}'" not in quality_items]
if missing:
    print('ERROR: Quality/CI documentation exclusions missing: ' + ', '.join(missing), file=sys.stderr)
    raise SystemExit(1)

for name in ('candidate-kernel.yml', 'phase1-certification.yml'):
    lines = Path('.github/workflows', name).read_text(encoding='utf-8').splitlines()
    items = {line.strip() for line in lines}
    missing = [pattern for pattern in patterns if f"- '!{pattern}'" not in items]
    if missing:
        print(f"ERROR: {name} documentation exclusions missing: " + ', '.join(missing), file=sys.stderr)
        raise SystemExit(1)

document_suffixes = (
    '.md', '.markdown', '.mdown', '.mdx', '.rst', '.adoc', '.asciidoc', '.txt',
    '.text', '.rtf', '.doc', '.docx', '.odt', '.pdf', '.tex', '.epub', '.html',
    '.htm', '.ppt', '.pptx', '.odp', '.pages', '.key',
)
document_basenames = ('LICENSE', 'COPYING', 'NOTICE', 'CHANGELOG', 'CONTRIBUTING', 'AUTHORS')

def is_document_path(path: str) -> bool:
    lower = path.lower()
    base = Path(path).name
    return (
        lower.startswith(('docs/', 'scratch/'))
        or lower.endswith(document_suffixes)
        or any(base == name or base.startswith(name + '.') for name in document_basenames)
    )

phase0_lines = Path('.github/workflows/phase0-certification.yml').read_text(encoding='utf-8').splitlines()
in_push_paths = False
for line in phase0_lines:
    if line == '    paths:':
        in_push_paths = True
        continue
    if in_push_paths and line and not line.startswith('      '):
        break
    if not in_push_paths:
        continue
    item = line.strip()
    if not item.startswith('- '):
        continue
    path = item[2:].strip().strip("'\"")
    if is_document_path(path):
        print(f'ERROR: phase0-certification.yml push allow-list contains documentation path: {path}', file=sys.stderr)
        raise SystemExit(1)

prompt_start = '**System Prompt: The Paranoiac Advisor**'
prompt_end = '* **Pass 5 (Consecutive 3):** Scanned raw text logic. Zero gaps detected. Criteria met. Delivery authorized.'

def reviewer_prompt(name: str) -> str:
    text = Path(name).read_text(encoding='utf-8')
    if text.count(prompt_start) != 1 or text.count(prompt_end) != 1:
        print(f'ERROR: reviewer prompt boundaries missing or duplicated in {name}', file=sys.stderr)
        raise SystemExit(1)
    start = text.index(prompt_start)
    end = text.index(prompt_end, start) + len(prompt_end)
    return text[start:end]

agents_prompt = reviewer_prompt('AGENTS.md')
workflow_prompt = reviewer_prompt('docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md')
if agents_prompt != workflow_prompt:
    print('ERROR: reviewer prompt copies are not byte-identical', file=sys.stderr)
    raise SystemExit(1)
PY_POLICY
then
  fail=1
fi

if ! grep -Fq 'Direct check-in to `main` is the normal project workflow' AGENTS.md; then
  echo "ERROR: direct-main check-in rule missing from AGENTS.md" >&2
  fail=1
fi

if ! grep -Fq 'Branching and later merging are discouraged' AGENTS.md; then
  echo "ERROR: branch-discouragement rule missing from AGENTS.md" >&2
  fail=1
fi

if (( fail != 0 )); then
  exit 1
fi

echo "ZX-UX CI policy checks passed."
