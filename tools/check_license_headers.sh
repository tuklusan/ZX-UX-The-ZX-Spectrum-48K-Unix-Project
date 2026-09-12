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
)

fail=0
checked=0
explicitly_exempt=0

is_explicit_header_exemption() {
  local candidate="$1"
  [[ -n "${explicit_header_exemptions[$candidate]+approved}" ]]
}

is_generated_certification_json() {
  local candidate="$1"
  [[ "$candidate" == "$GENERATED_CERTIFICATION_DIR"/*.json ]]
}

for exempt_path in "${!explicit_header_exemptions[@]}"; do
  if [[ -z "$exempt_path" || -z "${explicit_header_exemptions[$exempt_path]}" ]]; then
    echo "ERROR: each license-header exemption must have an exact non-empty path and reason" >&2
    exit 1
  fi
done

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

while IFS= read -r -d '' file; do
  file="${file#./}"
  [[ "$file" == "$LICENSE_PATH" ]] && continue

  if is_generated_certification_json "$file"; then
    # Durable certification records are machine-generated strict JSON whose exact
    # bytes are independently hash-verified by tools/check_phase0_evidence.py.
    # JSON comments would invalidate the records and destroy evidence identity.
    if ! python3 -m json.tool "$file" >/dev/null; then
      echo "ERROR: generated certification exemption is only valid for parseable JSON: $file" >&2
      fail=1
      continue
    fi
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

  for phrase in "${required_phrases[@]}"; do
    if ! grep -Fq -- "$phrase" <<<"$header"; then
      echo "ERROR: required license-header phrase missing near top of $file" >&2
      fail=1
    fi
  done
done < <(find . -path './.git' -prune -o ! -type d -print0)

if (( checked == 0 )); then
  echo "ERROR: no project text files were checked" >&2
  exit 1
fi

if (( fail != 0 )); then
  exit 1
fi

printf 'License header gate passed: %d text file(s) checked; %d explicitly exempt header-inapplicable artifact(s).\n' \
  "$checked" "$explicitly_exempt"
