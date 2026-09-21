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

readonly LICENSE_PATH="LICENSE"
readonly LICENSE_SHA256="dac0b24bb71563c0eec7c34f3ad07adad8c65f35706ea1f0f8557ea736ffd785"
readonly HEADER_SCAN_LINES=40
readonly GENERATED_CERTIFICATION_DIR="v1/dist/certification"
# H03 preserves this project-owner-approved external reference corpus byte-for-byte.
# Source: tuklusan/zxuslinuxtestproject at ac520f05db734c650f67b62ba62f5490a91ab9c3.
# The source quarantine subtree is intentionally excluded from the approved H03 scope.
readonly PRESERVED_REFERENCE_DIR="reference"
readonly PRESERVED_REFERENCE_TREE_SHA1="a4e06de3b8b193b43597cdb4d259b5b206e7e3ad"
readonly C48_SPEC_DOCX_PATH="docs/04-C48 Language Specification Rev 0.11.docx"
# Project-owner C48 documentation update admitted from b58f9630397829788972260b5948e882452993e2.
readonly C48_SPEC_DOCX_BLOB_SHA1="5744e9f2c440b4ef11f7ffcd7dad7d218f3ba44d"
# H04 preserves these SDK compiler assets byte-for-byte from the read-only source.
# Source: tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit
# at 1bebc6288a1cdfa1bdfb5a6694e1986b6c3d7ee0; compiler/assets tree
# 979039b5c636f0578f8bccd19ae49a669a5b7e0e.

required_phrases=(
  "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs."
  "Proprietary rights reserved except as expressly licensed herein."
  "ZX-UX Sinclair ZX Spectrum Unix"
  "SANYALnet Labs Non-Commercial License"
  "root LICENSE file"
  "Non-Commercial use is permitted"
  "Commercial Use"
  "AI/ML model training"
  "prohibited unless separately authorized."
  "Attribution is required"
  "Based on original work by Supratim Sanyal of"
  "See LICENSE for full terms"
  "warranty disclaimer"
  "termination"
  "patent"
  "trademark"
  "governing-law provisions."
)

declare -A explicit_header_exemptions=(
  [".zxux-root"]="Exact root-marker bytes are fixed by the implementation contract."
  ["tools/manifest/toolchain.lock.json"]="JSON does not permit comments; this exact manifest path is required by E0.01."
  ["v1/src/boot/loader.bas"]="The P0.07 production loader is exactly five semantic Sinclair BASIC lines; an added comment line would violate the frozen bootstrap contract."
  ["v1/assets/loading.scr"]="P0.08 requires an exact native 6912-byte Spectrum screen image."
  ["v1/assets/font4x8.bin"]="P0.10 requires the exact raw 392-byte font resource representation."
  ["v1/assets/issue.txt"]="P0.10 freezes exact logical issue bytes, leaving no room for a source header."
  ["v1/assets/crontab.txt"]="P0.10 freezes this resource as zero-length RAW."
  ["v1/assets/bincat.bin"]="P0.10 freezes the raw 488-byte BCAT resource shape."
  ["docs/00-ZX-UX_User_Manual_Revision_12.docx"]="Binary DOCX user manual cannot carry the plaintext project header."
  ["docs/04-C48 Language Specification Rev 0.11.docx"]="Binary DOCX specification cannot carry the plaintext project header; exact Git blob identity is verified before this exemption is honored."
  ["docs/05-C48 Compiler User Manual Rev 0.11.docx"]="Binary DOCX user manual cannot carry the plaintext project header."
  ["docs/images/zx-ux-hero.png"]="Binary PNG hero image cannot carry the plaintext project header."
  ["docs/images/zx-ux-hero-animated.gif"]="Binary GIF hero image cannot carry the plaintext project header."
  ["docs/images/doc-thumbs/c48-compiler-user-manual-r011.png"]="Binary PNG document thumbnail cannot carry the plaintext project header."
  ["docs/images/doc-thumbs/c48-language-spec-r011.png"]="Binary PNG document thumbnail cannot carry the plaintext project header."
  ["docs/images/doc-thumbs/zxux-user-manual-r12.png"]="Binary PNG document thumbnail cannot carry the plaintext project header."
  ["v1/dist/media/P5/phase5-fixture.tap"]="Binary Phase-5 certification cassette media cannot carry the plaintext project header."
  ["v1/dist/media/P5/phase5-fixture.tzx"]="Binary Phase-5 certification cassette media cannot carry the plaintext project header."
  ["v1/dist/media/P5/phase5-fixture-roundtrip.tap"]="Binary Phase-5 certification cassette media cannot carry the plaintext project header."
  ["v1/dist/media/P5/p516-roundtrip.tap"]="Binary Phase-5 certification cassette media cannot carry the plaintext project header."
  ["v1/dist/media/P0/p009-bootstrap.tap"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/media/P0/p010-boot.tap"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-font-atlas.fmf"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-font-atlas.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-font-atlas.sna"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000000.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000001.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000002.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000003.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000004.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000005.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000006.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000007.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000008.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000009.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000010.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000011.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000012.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000013.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000014.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000015.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000016.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000017.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000018.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000019.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000020.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000021.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000022.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000023.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000024.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000025.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000026.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000027.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000028.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/dist/visual/phase-1/p1.22/P1.22-frame-00000029.scr"]="Binary recovered ZX Spectrum certification media cannot carry the plaintext project header."
  ["v1/assets/SANYALnet-Labs-4x8-font-0.bin"]="Binary 4x8 font asset cannot carry the plaintext project header."
)

declare -A preserved_h04_sdk_assets=(
  ["v1/assets/48.rom"]="4d6895e0bbf3fa543f192a66a297192b3c969ac9"
  ["v1/assets/README-48K-ROM.md"]="58319da0b2ce81313ad936ec7b298d9998119368"
  ["v1/assets/SANYALnet-Labs-4x8-font-1.bin"]="abe61b7591014dc0b4b9b8e432fe35978d42c939"
  ["v1/assets/SANYALnet-Labs-4x8-font-1.txt"]="b41886d252bfa9dc22a6a7790977002c04d21c4c"
  ["v1/assets/SANYALnet-Labs-4x8-font-2.bin"]="cbdb78595a780358ce2b26077c4de72d45d44adf"
  ["v1/assets/SANYALnet-Labs-4x8-font-2.txt"]="38acc70bf2fbdf8bba1ba2dd46a886839d6140d3"
  ["v1/assets/SANYALnet-Labs-4x8-font-3.bin"]="ec5eb988e28182c766b5a0d94437d92f6be5a468"
  ["v1/assets/SANYALnet-Labs-4x8-font-3.txt"]="fc18a3d9109e50ab2e36b2db616dcb45643ae736"
  ["v1/assets/SANYALnet-Labs-4x8-font-4.bin"]="00e30d85fccf9029d6aea2c39a14f46973f7666d"
  ["v1/assets/SANYALnet-Labs-4x8-font-4.txt"]="158991f59af2fe195736e09192c553604c7155b0"
  ["v1/assets/SANYALnet-Labs-4x8-font-5.bin"]="96657ff6940da15ca77e1eff4c8e0780c4047107"
  ["v1/assets/SANYALnet-Labs-4x8-font-5.txt"]="79ee3f0b546c49e5dae8617f1cee3cdaff0ecdfe"
  ["v1/assets/font4x8-tasword.bin"]="6efc46eb1d7e940e027097ad76e27ac719aeb59f"
  ["v1/assets/font4x8-zxux.bin"]="6efc46eb1d7e940e027097ad76e27ac719aeb59f"
)

fail=0
checked=0
explicitly_exempt=0
declare -a generated_certification_jsons=()

is_explicit_header_exemption() {
  local candidate="$1"
  [[ -n "${explicit_header_exemptions[$candidate]+approved}" ]]
}

is_generated_certification_json() {
  local candidate="$1"
  [[ "$candidate" == "$GENERATED_CERTIFICATION_DIR"/*.json ]]
}

is_retained_spectrum_media() {
  local candidate="$1"
  [[ "$candidate" == v1/dist/media/P[6-9].*/* || "$candidate" == v1/dist/media/P1[0-2].*/* ]] || return 1
  case "$candidate" in
    *.sna|*.tap|*.tzx|*.scr|*.fmf|*.wav|*.flac|*.png|*/manifest.json) return 0 ;;
    *) return 1 ;;
  esac
}

is_readme_file() {
  local candidate="$1"
  local basename="${candidate##*/}"
  [[ "${basename^^}" == README* ]]
}

compute_git_tree_sha1() {
  local root="$1"
  python3 - "$root" <<'PYTREE'
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])


def git_object_sha1(kind: bytes, payload: bytes) -> bytes:
    header = kind + b" " + str(len(payload)).encode("ascii") + b"\0"
    return hashlib.sha1(header + payload).digest()


def tree_sha1(path: Path) -> bytes | None:
    entries: list[tuple[bytes, bytes]] = []
    with os.scandir(path) as scan:
        for entry in scan:
            name = os.fsencode(entry.name)
            if entry.is_symlink():
                raise SystemExit(f"reference tree contains unsupported symlink: {entry.path}")
            if entry.is_dir(follow_symlinks=False):
                object_id = tree_sha1(Path(entry.path))
                if object_id is None:
                    continue
                mode = b"40000"
                sort_key = name + b"/"
            elif entry.is_file(follow_symlinks=False):
                info = entry.stat(follow_symlinks=False)
                execute_mask = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                mode = b"100755" if info.st_mode & execute_mask else b"100644"
                payload = Path(entry.path).read_bytes()
                object_id = git_object_sha1(b"blob", payload)
                sort_key = name
            else:
                raise SystemExit(f"reference tree contains unsupported artifact: {entry.path}")
            record = mode + b" " + name + b"\0" + object_id
            entries.append((sort_key, record))
    if not entries:
        return None
    payload = b"".join(record for _, record in sorted(entries, key=lambda item: item[0]))
    return git_object_sha1(b"tree", payload)


tree_id = tree_sha1(root)
if tree_id is None:
    raise SystemExit("reference tree contains no tracked artifacts")
print(tree_id.hex())
PYTREE
}

for exempt_path in "${!explicit_header_exemptions[@]}"; do
  if [[ -z "$exempt_path" || -z "${explicit_header_exemptions[$exempt_path]}" ]]; then
    echo "ERROR: each license-header exemption must have an exact non-empty path and reason" >&2
    exit 1
  fi
done

if [[ -L "$C48_SPEC_DOCX_PATH" || ! -f "$C48_SPEC_DOCX_PATH" ]]; then
  echo "ERROR: approved C48 DOCX specification must exist as a real regular file: $C48_SPEC_DOCX_PATH" >&2
  exit 1
fi
actual_c48_spec_blob="$(git hash-object -- "$C48_SPEC_DOCX_PATH")"
if [[ "$actual_c48_spec_blob" != "$C48_SPEC_DOCX_BLOB_SHA1" ]]; then
  echo "ERROR: approved C48 DOCX specification bytes changed: $C48_SPEC_DOCX_PATH" >&2
  echo "ERROR: expected blob $C48_SPEC_DOCX_BLOB_SHA1, got $actual_c48_spec_blob" >&2
  exit 1
fi
c48_spec_index_record="$(git ls-files --stage -- "$C48_SPEC_DOCX_PATH")"
c48_spec_expected_record_prefix="100644 $C48_SPEC_DOCX_BLOB_SHA1 0"
if [[ "$c48_spec_index_record" != "$c48_spec_expected_record_prefix"$'\t'"$C48_SPEC_DOCX_PATH" ]]; then
  echo "ERROR: approved C48 DOCX specification Git mode/index identity changed: $C48_SPEC_DOCX_PATH" >&2
  exit 1
fi

for asset_path in "${!preserved_h04_sdk_assets[@]}"; do
  expected_blob="${preserved_h04_sdk_assets[$asset_path]}"
  if [[ -L "$asset_path" || ! -f "$asset_path" ]]; then
    echo "ERROR: preserved H04 SDK asset must exist as a real regular file: $asset_path" >&2
    exit 1
  fi
  actual_blob="$(git hash-object -- "$asset_path")"
  if [[ "$actual_blob" != "$expected_blob" ]]; then
    echo "ERROR: preserved H04 SDK asset bytes changed: $asset_path" >&2
    echo "ERROR: expected blob $expected_blob, got $actual_blob" >&2
    exit 1
  fi
  index_record="$(git ls-files --stage -- "$asset_path")"
  expected_record_prefix="100644 $expected_blob 0"
  if [[ "$index_record" != "$expected_record_prefix"$'\t'"$asset_path" ]]; then
    echo "ERROR: preserved H04 SDK asset Git mode/index identity changed: $asset_path" >&2
    exit 1
  fi
done

if ! python3 tools/check_media_retention.py; then
  exit 1
fi

if [[ -e .gitmodules ]]; then
  echo "ERROR: submodules are not permitted unless the license-header gate is explicitly extended and approved" >&2
  exit 1
fi

if [[ -L "$LICENSE_PATH" || ! -f "$LICENSE_PATH" ]]; then
  echo "ERROR: root LICENSE must be a real regular file, not a symlink or other artifact type" >&2
  exit 1
fi

actual_license_sha256="$(sha256sum "$LICENSE_PATH" | awk '{print $1}')"
if [[ "$actual_license_sha256" != "$LICENSE_SHA256" ]]; then
  echo "ERROR: root LICENSE does not match the approved license bytes" >&2
  exit 1
fi

if [[ -L "$PRESERVED_REFERENCE_DIR" || ! -d "$PRESERVED_REFERENCE_DIR" ]]; then
  echo "ERROR: approved H03 reference corpus must exist as a real directory" >&2
  exit 1
fi
actual_reference_tree_sha1="$(compute_git_tree_sha1 "$PRESERVED_REFERENCE_DIR")"
if [[ "$actual_reference_tree_sha1" != "$PRESERVED_REFERENCE_TREE_SHA1" ]]; then
  echo "ERROR: preserved reference corpus does not match the approved H03 tree identity" >&2
  echo "ERROR: expected tree $PRESERVED_REFERENCE_TREE_SHA1, got $actual_reference_tree_sha1" >&2
  exit 1
fi

while IFS= read -r -d '' file; do
  file="${file#./}"
  [[ "$file" == "$LICENSE_PATH" ]] && continue

  if is_readme_file "$file"; then
    explicitly_exempt=$((explicitly_exempt + 1))
    continue
  fi

  if [[ "$file" == "$PRESERVED_REFERENCE_DIR"/* ]]; then
    explicitly_exempt=$((explicitly_exempt + 1))
    continue
  fi

  if [[ -n "${preserved_h04_sdk_assets[$file]+approved}" ]]; then
    explicitly_exempt=$((explicitly_exempt + 1))
    continue
  fi

  if is_retained_spectrum_media "$file"; then
    explicitly_exempt=$((explicitly_exempt + 1))
    continue
  fi

  if is_generated_certification_json "$file"; then
    # Durable certification records are machine-generated strict JSON whose exact
    # bytes are independently hash-verified by tools/check_phase0_evidence.py.
    # JSON comments would invalidate the records and destroy evidence identity.
    # Defer parsing so all exempt JSON is validated in one interpreter process;
    # cloud Python startup is expensive enough that one process per file turns this
    # gate into minutes of overhead without increasing coverage.
    generated_certification_jsons+=("$file")
    explicitly_exempt=$((explicitly_exempt + 1))
    continue
  fi

  if is_explicit_header_exemption "$file"; then
    explicitly_exempt=$((explicitly_exempt + 1))
    continue
  fi

  if [[ -L "$file" ]]; then
    echo "ERROR: symlink requires an explicit path-specific license-header exemption: $file" >&2
    fail=1
    continue
  fi

  if [[ ! -f "$file" ]]; then
    echo "ERROR: non-regular artifact requires an explicit path-specific license-header exemption: $file" >&2
    fail=1
    continue
  fi

  if [[ ! -s "$file" ]]; then
    echo "ERROR: empty project file cannot contain required license header: $file" >&2
    fail=1
    continue
  fi

  if ! grep -Iq '' "$file"; then
    echo "ERROR: non-text/binary artifact requires an explicit path-specific license-header exemption: $file" >&2
    fail=1
    continue
  fi

  checked=$((checked + 1))
  header="$(head -n "$HEADER_SCAN_LINES" "$file")"

  # Keep this check in-process. Spawning one grep per phrase multiplied the gate
  # into thousands of child processes and made cloud rebaseline diagnostics
  # needlessly slow without adding any coverage.
  for phrase in "${required_phrases[@]}"; do
    if [[ "$header" != *"$phrase"* ]]; then
      echo "ERROR: required license-header phrase missing near top of $file" >&2
      fail=1
    fi
  done
done < <(find . -path './.git' -prune -o -type d -name '__pycache__' -prune -o ! -type d -print0)

if (( ${#generated_certification_jsons[@]} > 0 )); then
  if ! python3 - "${generated_certification_jsons[@]}" <<'PYJSON'
import json
from pathlib import Path
import sys

failed = False
for arg in sys.argv[1:]:
    path = Path(arg)
    try:
        with path.open("r", encoding="utf-8") as stream:
            json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: generated certification exemption is only valid for parseable JSON: {path}: {exc}", file=sys.stderr)
        failed = True
raise SystemExit(1 if failed else 0)
PYJSON
  then
    exit 1
  fi
fi

if (( checked == 0 )); then
  echo "ERROR: no project text files were checked" >&2
  exit 1
fi

if (( fail != 0 )); then
  exit 1
fi

printf 'License header gate passed: %d text file(s) checked; %d explicitly exempt header-inapplicable artifact(s).\n' \
  "$checked" "$explicitly_exempt"
