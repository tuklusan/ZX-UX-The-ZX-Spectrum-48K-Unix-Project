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

: "${GITHUB_SHA:?}"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
git fetch --quiet origin main
test "$(git rev-parse origin/main)" = "$GITHUB_SHA"
test "$(sha256sum docs/01-ZX-UX-ARCHITECTURE-REV17.md | awk '{print $1}')" = d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8
test "$(sha256sum docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV08.md | awk '{print $1}')" = 97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c
python3 tools/check_phase10_evidence.py --require-active
python3 tools/check_phase11_evidence.py --require-active
test -f v1/dist/certification/P11.48.result.json
test -f v1/dist/certification/P11.48-sdk-admission.json
test -f v1/dist/certification/phase-11.json
grep -q '^\*\*Status:\*\* CLOSED' scratch/ZX-UX-FAST-LOADER-TZX-RELEASE-MIGRATION-RUNBOOK-REV01.md
test "$(sha256sum scratch/ZX-UX-LOADER-1.0.0-portable.zip | awk '{print $1}')" = 4c83a681f718192db9ebb32f0c8bc565baf2e68eb85de480322a1102d32f00c7
forbidden="$(git ls-files | grep -Ei '(^|/)(P12(\.|/)|p12[^/]*qualification|phase-?12[^/]*\.yml|phase12_step_)' || true)"
test -z "$forbidden"
./tools/check_license_headers.sh
./tools/check_project_policy.py
python3 tools/check_media_retention.py
test -z "$(git status --porcelain)"
