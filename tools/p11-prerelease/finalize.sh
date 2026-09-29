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
work="${P11_WORK:-/tmp/p11-prerelease}"
second=/tmp/p11-prerelease-double
py=tools/runtime/python/bin/python

P11_WORK="$work" "$py" tools/p11-prerelease/manifest.py
rm -rf "$second"
P11_WORK="$second" bash tools/p11-prerelease/build.sh
cp -a "$work/realtime" "$second/realtime"
cp -a "$work/realtime-detect-loader" "$second/realtime-detect-loader"
P11_WORK="$second" "$py" tools/p11-prerelease/manifest.py

find "$work/sdk-reference-pre-release-1.0.2" "$second/sdk-reference-pre-release-1.0.2" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$work/sdk-reference-pre-release-1.0.2" "$second/sdk-reference-pre-release-1.0.2" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

diff -qr "$work/P11.pre-release" "$second/P11.pre-release"
diff -qr "$work/sdk-reference-pre-release-1.0.2" "$second/sdk-reference-pre-release-1.0.2"

for pass in 1 2 3; do
  P11_WORK="$work" "$py" tools/p11-prerelease/manifest.py >/dev/null
  echo "P11 PRE-RELEASE SOP SCAN-$pass CLEAN"
done

"$py" tools/check_phase10_evidence.py --require-active
"$py" tools/check_phase11_evidence.py --require-active
"$py" tools/check_media_retention.py
rm -rf v1/build
hold=/tmp/zxux-runtime-policy-check; rm -rf "$hold"; mv tools/runtime "$hold"; trap 'mv "$hold" tools/runtime' EXIT
./tools/check_project_policy.py
./tools/check_license_headers.sh
mv "$hold" tools/runtime; trap - EXIT
git fetch --quiet origin main
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
test "$(git rev-parse origin/main)" = "$GITHUB_SHA"
test "$(git rev-parse PHASE-11-COMPLETE^{commit})" = 263a203da3d54a398e8ac011284ae4195b1279c0
test -z "$(git ls-files | grep -Ei '(^|/)(P12(\.|/)|p12[^/]*qualification|phase-?12[^/]*\.yml|phase12_step_)' || true)"

"$py" - <<'PY'
import hashlib,json,os
from pathlib import Path
w=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))
out=w/"P11.pre-release"
m=json.loads((out/"pre-release.json").read_text())
assert m["sdk"]["program_count"]==30
assert m["sdk"]["scr_count"]==m["sdk"]["png_count"]==30
assert m["multitasking"]["checkpoint_frames"]==1250
assert all(v=="PASS" for v in m["tests"].values())
marker={
 "schema":1,
 "source_commit":os.environ["GITHUB_SHA"],
 "bundle_digest_sha256":m["bundle_digest_sha256"],
 "manifest_sha256":hashlib.sha256((out/"pre-release.json").read_bytes()).hexdigest(),
 "tzx_sha256":m["boot"]["tzx_sha256"],
 "kernel_three_way_sha256":m["kernel_identity"]["native_rebuilt_sha256"],
 "program_pass_count":30,
 "multitasking_png_sha256":m["multitasking"]["png_sha256"],
 "status":"PASS",
}
(w/"final-ready.json").write_text(json.dumps(marker,indent=2,sort_keys=True)+"\n")
PY
echo "ZX-UX PHASE-11 EXPANDED PRE-RELEASE FINAL-READY PASS"
