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

: "${GITHUB_SHA:?}" "${GITHUB_WORKSPACE:?}"
work="${P11_WORK:-/tmp/p11-prerelease}"
rm -rf "$work"
mkdir -p "$work"/{evidence,a,b,P11.pre-release} v1/build
py=tools/runtime/python/bin/python
"$py" tools/p11-prerelease/sdk_acquire.py acquire --output "$work/sdk-reference-pre-release-1.0.2"
"$py" v1/tools-host/test-driver/run.py build --step P11.48 --evidence-dir "$work/evidence"
"$py" v1/tools-host/test-driver/run.py test --step P11.48 --evidence-dir "$work/evidence"
"$py" - <<'PY'
import json, os
from pathlib import Path
p=Path(os.environ.get('P11_WORK','/tmp/p11-prerelease'))/'evidence'
for name in ('P11.48.build.json','P11.48.test.json','P11.48.result.json'):
    d=json.loads((p/name).read_text())
    assert d['status']=='PASS' and d['source_commit']==os.environ['GITHUB_SHA'], name
assert json.loads((p/'P11.48.result.json').read_text())['pass_marker']=='ZX-UX PHASE 11 ACCEPTANCE PASS'
PY

sudo apt-get update
sudo apt-get install -y --no-install-recommends pasmo=0.5.3-7 xvfb=2:21.1.12-1ubuntu1.6 xdotool=1:3.20160805.1-5build1
test "$(dpkg-query -W -f='${Version}' pasmo)" = 0.5.3-7
test "$(dpkg-query -W -f='${Version}' xvfb)" = 2:21.1.12-1ubuntu1.6
test "$(dpkg-query -W -f='${Version}' xdotool)" = 1:3.20160805.1-5build1
command -v pasmo > "$work/pasmo-path"

(cd v1/src/kernel && "$GITHUB_WORKSPACE/tools/runtime/sjasmplus/bin/sjasmplus" --nologo --lst=../../build/kernel-prerelease.lst --sym=../../build/kernel-prerelease.sym kernel.asm)
test "$(wc -c < v1/build/kernel.bin)" -eq 8192
test "$(xxd -p -l 3 v1/build/kernel.bin)" != 000000
"$py" -m py_compile v1/tools-host/release-tzx/{build,inspect_tzx,runtime_acceptance,kernel_native_projection,kernel_text_projection,native_rebuild_test}.py tools/p11-prerelease/{source_tap,native_text_assemble_test,native_kernel_tape_rebuild,sdk_source_tapes,sdk_source_tape_native_build,sdk_source_tape_native_visual_build,sdk_native_process_run,sdk_native_cc_preflight,sdk_native_ld_preflight,sdk_stage_bundle,sdk_native_visual_run,sdk_multitask_build,sdk_multitask_run}.py
pasmo="$(cat "$work/pasmo-path")"
for d in a b; do
  "$py" v1/tools-host/release-tzx/build.py --kernel v1/build/kernel.bin \
    --output "$work/$d/zx-ux-phase11-pre-release.tzx" --hook-output "$work/$d/hook.bin" \
    --manifest "$work/$d/build.json" --pasmo "$pasmo"
done
cmp "$work/a/zx-ux-phase11-pre-release.tzx" "$work/b/zx-ux-phase11-pre-release.tzx"
cmp "$work/a/hook.bin" "$work/b/hook.bin"
cmp "$work/a/build.json" "$work/b/build.json"
cp "$work/a/zx-ux-phase11-pre-release.tzx" "$work/P11.pre-release/"

"$py" v1/tools-host/release-tzx/inspect_tzx.py "$work/P11.pre-release/zx-ux-phase11-pre-release.tzx" \
  --kernel v1/build/kernel.bin --extract "$work/embedded-kernel.bin" > "$work/inspection.txt"
test "$(wc -c < "$work/embedded-kernel.bin")" -eq 8192
cmp v1/build/kernel.bin "$work/embedded-kernel.bin"
test "$(sha256sum v1/build/kernel.bin | awk '{print $1}')" = "$(sha256sum "$work/embedded-kernel.bin" | awk '{print $1}')"
grep -q '^final_loader_after=0x5EB4$' "$work/inspection.txt"
grep -q '^pre_beep_pause_nominal_tstates=3500009$' "$work/inspection.txt"
grep -q '^handoff=0xE003$' "$work/inspection.txt"
grep -q '^kernel_size=8192$' "$work/inspection.txt"
grep -q '^standard_speed_blocks=2$' "$work/inspection.txt"
grep -q '^generalized_blocks=48$' "$work/inspection.txt"

"$py" v1/tools-host/release-tzx/kernel_native_projection.py --listing v1/build/kernel-prerelease.lst \
  --symbols v1/build/kernel-prerelease.sym --output "$work/kernel.nsp" --audit "$work/projection.json" --kernel v1/build/kernel.bin
"$py" v1/tools-host/release-tzx/native_rebuild_test.py --kernel v1/build/kernel.bin \
  --projection "$work/kernel.nsp" --report "$work/native-rebuild.json"
mkdir -p "$work/P11.pre-release/kernel"
"$py" v1/tools-host/release-tzx/kernel_text_projection.py --listing v1/build/kernel-prerelease.lst \
  --symbols v1/build/kernel-prerelease.sym --kernel v1/build/kernel.bin \
  --output "$work/P11.pre-release/kernel/kernel-native-source.asm" \
  --map "$work/P11.pre-release/kernel/kernel-native-source-map.json"
"$py" tools/p11-prerelease/source_tap.py \
  --source "$work/P11.pre-release/kernel/kernel-native-source.asm" \
  --output "$work/P11.pre-release/kernel/kernel-native-source.tap" \
  --report "$work/P11.pre-release/kernel/kernel-native-source-tap.json"
"$py" tools/p11-prerelease/native_text_assemble_test.py \
  --source "$work/P11.pre-release/kernel/kernel-native-source.asm" \
  --kernel v1/build/kernel.bin \
  --report "$work/P11.pre-release/kernel/kernel-native-text-as.json"
cp v1/build/kernel.bin "$work/P11.pre-release/kernel/kernel-host.bin"
cp "$work/embedded-kernel.bin" "$work/P11.pre-release/kernel/kernel-tzx-embedded.bin"
"$py" tools/p11-prerelease/native_kernel_tape_rebuild.py \
  --source "$work/P11.pre-release/kernel/kernel-native-source.asm" \
  --tap "$work/P11.pre-release/kernel/kernel-native-source.tap" \
  --host-kernel v1/build/kernel.bin \
  --embedded-kernel "$work/embedded-kernel.bin" \
  --obj-output "$work/P11.pre-release/kernel/kernel-native.obj1" \
  --kernel-output "$work/P11.pre-release/kernel/kernel-native.bin" \
  --report "$work/P11.pre-release/kernel/kernel-native-build.json"
mkdir -p "$work/native-tzx"
"$py" v1/tools-host/release-tzx/build.py \
  --kernel "$work/P11.pre-release/kernel/kernel-native.bin" \
  --output "$work/native-tzx/zx-ux-phase11-pre-release.tzx" \
  --hook-output "$work/native-tzx/hook.bin" \
  --manifest "$work/native-tzx/build.json" --pasmo "$pasmo"
cmp "$work/a/zx-ux-phase11-pre-release.tzx" "$work/native-tzx/zx-ux-phase11-pre-release.tzx"
cp "$work/native-tzx/zx-ux-phase11-pre-release.tzx" "$work/P11.pre-release/zx-ux-phase11-pre-release.tzx"
"$py" v1/tools-host/release-tzx/inspect_tzx.py \
  "$work/P11.pre-release/zx-ux-phase11-pre-release.tzx" \
  --kernel "$work/P11.pre-release/kernel/kernel-native.bin" \
  --extract "$work/native-tzx-embedded.bin" > "$work/native-tzx-inspection.txt"
cmp "$work/P11.pre-release/kernel/kernel-native.bin" "$work/native-tzx-embedded.bin"
"$py" - <<'PY'
import hashlib,json
from pathlib import Path
w=Path(os.environ.get('P11_WORK','/tmp/p11-prerelease'))
host=Path('v1/build/kernel.bin').read_bytes(); embedded=(w/'embedded-kernel.bin').read_bytes()
n=json.loads((w/'native-rebuild.json').read_text()); p=json.loads((w/'projection.json').read_text())
h=hashlib.sha256(host).hexdigest()
assert len(host)==len(embedded)==n['native_rebuilt_kernel_size']==8192
assert host==embedded and h==n['native_rebuilt_kernel_sha256']==n['host_kernel_sha256']
assert n['resident_kernel_overwritten'] is False and all(v=='PASS' for v in n['assertions'].values())
assert p['text_size']==8192 and p['contains_preassembled_kernel_payload'] is False and p['semantic_reference_equals_kernel_oracle'] is True
PY

"$py" tools/p11-prerelease/sdk_source_tapes.py \
  --root "$work/sdk-reference-pre-release-1.0.2" \
  --report "$work/sdk-source-tape-corpus.json"

mkdir -p "$work/sdk-native-source-tape-build"
"$py" tools/p11-prerelease/sdk_source_tape_native_build.py \
  --root "$work/sdk-reference-pre-release-1.0.2" \
  --output "$work/sdk-native-source-tape-build" \
  --report "$work/sdk-native-source-tape-build.json"
"$py" - <<'PY'
import json
from pathlib import Path
w=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))
d=json.loads((w/"sdk-native-source-tape-build.json").read_text())
assert d["program_count"]==30 and len(d["programs"])==30
assert all(row["tape_load"]=="PASS" and row["native_cc"]=="PASS" and row["native_ld"]=="PASS" for row in d["programs"])
assert all(v=="PASS" for v in d["assertions"].values())
files=[p for p in (w/"sdk-native-source-tape-build").rglob("*") if p.is_file()]
assert len(files)==60
PY

"$py" tools/p11-prerelease/sdk_native_process_run.py \
  --root "$work/sdk-reference-pre-release-1.0.2" \
  --native "$work/sdk-native-source-tape-build" \
  --native-report "$work/sdk-native-source-tape-build.json" \
  --report "$work/sdk-native-process-run.json"

mkdir -p "$work/sdk-native-visual-build"
"$py" tools/p11-prerelease/sdk_source_tape_native_visual_build.py \
  --root "$work/sdk-reference-pre-release-1.0.2" \
  --output "$work/sdk-native-visual-build" \
  --report "$work/sdk-native-visual-build.json"
"$py" - <<'PY'
import json
from pathlib import Path
w=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))
d=json.loads((w/"sdk-native-visual-build.json").read_text())
assert d["program_count"]==30 and len(d["programs"])==30
assert all(row["tape_load"]=="PASS" and row["native_visual_cc"]=="PASS" and row["native_ld"]=="PASS" for row in d["programs"])
assert all(v=="PASS" for v in d["assertions"].values())
assert len([p for p in (w/"sdk-native-visual-build").rglob("*") if p.is_file()])==60
PY
"$py" - <<'PY'
import json
from pathlib import Path
w=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))
d=json.loads((w/"sdk-native-process-run.json").read_text())
assert d["program_count"]==30 and len(d["programs"])==30
assert all(row["spawn"]=="PASS" and row["spawned_context_restore"]=="PASS" and row["process_started"]=="PASS" and row["sys_exit_reached"]=="PASS" for row in d["programs"])
assert all(v=="PASS" for v in d["assertions"].values())
PY

mkdir -p "$work/sdk-native-cc-preflight"
"$py" tools/p11-prerelease/sdk_native_cc_preflight.py \
  --root "$work/sdk-reference-pre-release-1.0.2" \
  --output "$work/sdk-native-cc-preflight" \
  --report "$work/sdk-native-cc-preflight.json"
"$py" - <<'PY'
import json
from pathlib import Path
w=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))
d=json.loads((w/"sdk-native-cc-preflight.json").read_text())
assert d["program_count"]==30 and len(d["programs"])==30
assert all(row["compile"]=="PASS" and row["mutation_rejected"]=="PASS" for row in d["programs"])
assert all(v=="PASS" for v in d["assertions"].values())
assert len(list((w/"sdk-native-cc-preflight").rglob("*.obj")))==30
PY

mkdir -p "$work/sdk-native-ld-preflight"
"$py" tools/p11-prerelease/sdk_native_ld_preflight.py \
  --root "$work/sdk-reference-pre-release-1.0.2" \
  --output "$work/sdk-native-ld-preflight" \
  --report "$work/sdk-native-ld-preflight.json"
"$py" - <<'PY'
import json
from pathlib import Path
w=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))
d=json.loads((w/"sdk-native-ld-preflight.json").read_text())
assert d["program_count"]==30 and len(d["programs"])==30
assert all(row["compile_obj1"]=="PASS" and row["native_mex1_writer"]=="PASS" for row in d["programs"])
assert all(v=="PASS" for v in d["assertions"].values())
assert len([p for p in (w/"sdk-native-ld-preflight").rglob("*") if p.is_file()])==30
PY

"$py" tools/p11-prerelease/sdk_stage_bundle.py \
  --root "$work/sdk-reference-pre-release-1.0.2" \
  --native "$work/sdk-native-source-tape-build" \
  --source-tape-report "$work/sdk-source-tape-corpus.json" \
  --native-report "$work/sdk-native-source-tape-build.json" \
  --process-report "$work/sdk-native-process-run.json" \
  --cc-preflight-report "$work/sdk-native-cc-preflight.json" \
  --ld-preflight-report "$work/sdk-native-ld-preflight.json" \
  --output "$work/P11.pre-release"
"$py" - <<'PY'
import json
from pathlib import Path
w=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))/"P11.pre-release/sdk"
d=json.loads((w/"PROVENANCE.json").read_text())
assert d["program_count"]==30 and len(d["programs"])==30
assert all(v=="PASS" for v in d["assertions"].values())
assert len(list((w/"tapes").rglob("*.src.tap")))==30
assert len([p for p in (w/"native").rglob("*") if p.is_file()])==60
assert len(list((w/"reference-lfs").rglob("*.png")))==30
assert len(list((w/"reference-png").rglob("*.png")))==30
PY

"$py" tools/p11-prerelease/sdk_native_visual_run.py \
  --root "$work/sdk-reference-pre-release-1.0.2" \
  --native "$work/sdk-native-visual-build" \
  --native-report "$work/sdk-native-visual-build.json" \
  --output "$work/P11.pre-release/sdk/proof/visual" \
  --report "$work/P11.pre-release/sdk/proof/native-visual-run.json"
"$py" - <<'PY'
import json
from pathlib import Path
p=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))/"P11.pre-release/sdk/proof"
d=json.loads((p/"native-visual-run.json").read_text())
assert d["program_count"]==30 and len(d["programs"])==30
assert all(row["spawn"]=="PASS" and row["screen_ram_capture"]=="PASS" and row["deterministic_png_from_scr"]=="PASS" for row in d["programs"])
assert all(v=="PASS" for v in d["assertions"].values())
assert len(list((p/"visual").rglob("*.scr")))==30
assert len(list((p/"visual").rglob("*.png")))==30
PY

mkdir -p "$work/sdk-native-multitask"
"$py" tools/p11-prerelease/sdk_multitask_build.py \
  --root "$work/sdk-reference-pre-release-1.0.2" \
  --output "$work/sdk-native-multitask" \
  --report "$work/sdk-native-multitask.json"
mkdir -p "$work/P11.pre-release/multitasking"
"$py" tools/p11-prerelease/sdk_multitask_run.py \
  --native "$work/sdk-native-multitask" \
  --output "$work/P11.pre-release/multitasking" \
  --report "$work/P11.pre-release/multitasking/hanoi-queens8.json"
"$py" - <<'PY'
import json
from pathlib import Path
p=Path(os.environ.get("P11_WORK","/tmp/p11-prerelease"))/"P11.pre-release/multitasking"
d=json.loads((p/"hanoi-queens8.json").read_text())
assert d["checkpoint_frames"]==1250
assert d["hanoi_yields"]>0 and d["queens8_yields"]>0
assert all(v=="PASS" for v in d["assertions"].values())
assert (p/"hanoi-queens8-1250f.scr").stat().st_size==6912
assert (p/"hanoi-queens8-1250f.png").is_file()
PY
cp "$work/sdk-native-multitask/hanoi.obj1" "$work/P11.pre-release/multitasking/"
cp "$work/sdk-native-multitask/hanoi.mex1" "$work/P11.pre-release/multitasking/"
cp "$work/sdk-native-multitask/queens8.obj1" "$work/P11.pre-release/multitasking/"
cp "$work/sdk-native-multitask/queens8.mex1" "$work/P11.pre-release/multitasking/"

