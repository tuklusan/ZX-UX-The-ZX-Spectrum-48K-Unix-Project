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
  "tools/check_project_policy.py"
  "tools/check_license_headers.sh"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "ERROR: required file missing: $file" >&2
    fail=1
  fi
done

while IFS= read -r -d '' file; do
  if grep -Iq '' "$file"; then
    if grep -nE '[[:blank:]]+$' "$file"; then
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

if ! grep -Fq 'runs-on: ubuntu-slim' .github/workflows/quality-and-ci.yml; then
  echo "ERROR: workflow must use ubuntu-slim" >&2
  fail=1
fi

if ! grep -Fq 'MAX_RESULTS: 25' .github/workflows/quality-and-ci.yml; then
  echo "ERROR: workflow must cap continuity at 25 result identifiers" >&2
  fail=1
fi

if ! grep -Fq 'handshake happens dynamically immediately before check-in' AGENTS.md; then
  echo "ERROR: dynamic author/reviewer handshake rule missing from AGENTS.md" >&2
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

if ! grep -Fq 'branches:' .github/workflows/quality-and-ci.yml || ! grep -Fq -- '- main' .github/workflows/quality-and-ci.yml; then
  echo "ERROR: automatic push validation must target main" >&2
  fail=1
fi

if (( fail != 0 )); then
  exit 1
fi

echo "ZX-UX CI policy checks passed."
