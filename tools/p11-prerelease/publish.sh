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
python3 tools/p11-prerelease/manifest.py
python3 tools/check_phase10_evidence.py --require-active
python3 tools/check_phase11_evidence.py --require-active
python3 tools/check_media_retention.py
git fetch --quiet origin main
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
test "$(git rev-parse origin/main)" = "$GITHUB_SHA"
test -z "$(git ls-files | grep -Ei '(^|/)(P12(\.|/)|p12[^/]*qualification|phase-?12[^/]*\.yml|phase12_step_)' || true)"
test -z "$(git status --porcelain)"
rm -rf v1/dist/media/P11.pre-release
cp -a /tmp/p11-prerelease/P11.pre-release v1/dist/media/P11.pre-release
test -z "$(find v1/dist/media/P11.pre-release -type f -iname '*.tap' -print -quit)"
python3 tools/check_media_retention.py
rm -rf v1/build
hold=/tmp/zxux-runtime-policy-check; rm -rf "$hold"; mv tools/runtime "$hold"; trap 'mv "$hold" tools/runtime' EXIT
./tools/check_project_policy.py
./tools/check_license_headers.sh
mv "$hold" tools/runtime; trap - EXIT
test -z "$(git ls-files | grep -Ei '(^|/)(P12(\.|/)|p12[^/]*qualification|phase-?12[^/]*\.yml|phase12_step_)' || true)"
git add -A v1/dist/media/P11.pre-release
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
if ! git diff --cached --quiet; then
  git commit -m "media: publish Phase-11 fast-loader TZX pre-release"
  python3 tools/check_media_retention.py
  git push origin HEAD:main
fi
git fetch --quiet origin main
test "$(git rev-parse origin/main)" = "$(git rev-parse HEAD)"
test -z "$(git ls-tree -r --name-only origin/main | grep -Ei '(^|/)(P12(\.|/)|p12[^/]*qualification|phase-?12[^/]*\.yml|phase12_step_)' || true)"
echo "ZX-UX PHASE-11 FAST-LOADER PRE-RELEASE PUBLISHED; PHASE 12 NOT STARTED"
