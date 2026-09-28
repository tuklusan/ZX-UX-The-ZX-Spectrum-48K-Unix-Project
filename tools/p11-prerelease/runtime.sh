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

export DISPLAY=:99
work=/tmp/p11-prerelease
tape="$work/P11.pre-release/zx-ux-phase11-pre-release.tzx"
py=tools/runtime/python/bin/python
runtime_home="$work/runtime-home"
rm -rf "$runtime_home"
mkdir -p "$runtime_home"
export HOME="$runtime_home"
export XDG_CONFIG_HOME="$runtime_home/.config"
mkdir -p "$XDG_CONFIG_HOME"

run_mode() {
  local name="$1" detect="$2" hook="$3" diag="$work/$1"
  mkdir -p "$diag"
  if test "$hook" = omit; then "$py" v1/tools-host/release-tzx/runtime_acceptance.py debugger --omit-hook-trace --output "$diag/debugger.txt"
  else "$py" v1/tools-host/release-tzx/runtime_acceptance.py debugger --output "$diag/debugger.txt"; fi
  # The debugger's absolute frame cap starts before the scripted ROM-load input.
  # Replace it with a remote fail-safe; runtime.sh owns the deterministic wall
  # timeout so variable pre-load GUI/input latency cannot consume the tape budget.
  sed -i 's/spectrum:frames > 0x1964/spectrum:frames > 0xffffff/' "$diag/debugger.txt"
  Xvfb :99 -screen 0 1280x900x24 >"$diag/xvfb.log" 2>&1 & local xvfb_pid=$!
  local fuse_pid="" window="" result=""
  trap 'kill "$fuse_pid" "$xvfb_pid" 2>/dev/null || true' RETURN
  sleep 1
  stdbuf -oL -eL tools/runtime/fuse/bin/fuse --machine 48 --rom-48 tools/runtime/fuse/roms/48.rom \
    --tape "$tape" --no-accelerate-loader --no-fastload --no-traps "$detect" --no-confirm-actions --no-sound \
    --debugger-command "$(cat "$diag/debugger.txt")" >"$diag/fuse-state.log" 2>&1 & fuse_pid=$!
  for _ in $(seq 1 40); do window="$(xdotool search --onlyvisible --name 'Fuse' 2>/dev/null | head -n1 || true)"; test -n "$window" && break; sleep 0.25; done
  test -n "$window"
  xdotool windowfocus --sync "$window" || true; xdotool mousemove --window "$window" 160 145 click 1 || true
  sleep 0.75; xdotool keydown Shift_L; sleep 0.25; xdotool keyup Shift_L; sleep 0.60
  xdotool keydown j; sleep 0.45; xdotool keyup j; sleep 0.60
  xdotool key --delay 300 ctrl+p; sleep 0.60; xdotool key --delay 300 ctrl+p; sleep 0.60
  xdotool keydown Return; sleep 0.45; xdotool keyup Return
  if test "$detect" = --no-detect-loader; then
    local waiting=""
    for _ in $(seq 1 40); do grep -q '0xa00002' "$diag/fuse-state.log" && { waiting=yes; break; }; kill -0 "$fuse_pid" 2>/dev/null || break; sleep 0.25; done
    if test "$waiting" != yes; then
      printf 'runtime mode %s did not reach ROM load wait\n' "$name" >&2
      cat "$diag/fuse-state.log" >&2
      return 1
    fi
    xdotool windowfocus --sync "$window" || true; xdotool key F8
  fi
  # The exact unaccelerated 48K cassette path is slightly over five minutes
  # on the certified Fuse runtime. Keep margin for hosted-runner GUI/input jitter
  # without weakening the debugger-side E003 proof or enabling fast-load traps.
  for _ in $(seq 1 420); do
    grep -q '0xa50001' "$diag/fuse-state.log" && { result=E003_REACHED; break; }
    grep -q '0xaf0001' "$diag/fuse-state.log" && { result=TIMEOUT; break; }
    kill -0 "$fuse_pid" 2>/dev/null || { result=FUSE_EXITED; break; }; sleep 1
  done
  if test -z "$result"; then
    result=TIMEOUT
    kill "$fuse_pid" 2>/dev/null || true
  fi
  wait "$fuse_pid" || true; fuse_pid=""; kill "$xvfb_pid" 2>/dev/null || true; xvfb_pid=""; trap - RETURN
  if test "$result" != E003_REACHED; then
    printf 'runtime mode %s failed: %s\n' "$name" "$result" >&2
    cat "$diag/fuse-state.log" >&2
    return 1
  fi
  "$py" v1/tools-host/release-tzx/runtime_acceptance.py verify --log "$diag/fuse-state.log" \
    --rom tools/runtime/fuse/roms/48.rom --text v1/tools-host/release-tzx/text-lines.txt --report "$diag/runtime-acceptance.json"
}
run_mode realtime --no-detect-loader trace
run_mode realtime-detect-loader --detect-loader omit
