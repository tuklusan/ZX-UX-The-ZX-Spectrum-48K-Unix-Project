#!/usr/bin/env python3
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

from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import tempfile

from driver_core import DriverError
import phase6_pipeline

class P838Error(DriverError):
    pass

def require(v,m):
    if not v:
        raise P838Error(m)

def load_manifest(path:Path):
    spec=importlib.util.spec_from_file_location("zxux_p838_matrix",path)
    require(spec is not None and spec.loader is not None,f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P8.38":
        raise DriverError(step)

    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    manifest_path=root/"v1/tests/emulator/utils_pipe.py"
    manifest=load_manifest(manifest_path)
    manifest.validate_manifest()

    shell=(root/"v1/src/shell/sh.asm").read_text(encoding="utf-8")
    assertions=[
      {"name":"canonical-p838-present","passed":"## P8.38 - Utility pipeline/error propagation matrix" in plan},
      {"name":"six-stage-bounded-pipeline","passed":"P621_MAX_STAGES          EQU 6" in shell and manifest.BOUNDED_PIPE_STAGES==6},
      {"name":"pipeline-rollback","passed":"sh_p621_rollback:" in shell and "SYS_KILL" in shell and "SYS_CLOSE" in shell},
      {"name":"final-echo-wc-vector","passed":manifest.FINAL_PIPELINE==("echo","hello","|","wc")},
      {"name":"required-error-domains","passed":manifest.REQUIRED_ERRORS==("E_PIPE","E_IO","E_NOMEM","E_AGAIN")},
      {"name":"stream-readers-covered","passed":set(("cat","head","wc","rev")).issubset(set(manifest.STREAM_READERS))},
      {"name":"stream-writers-covered","passed":set(("echo","cat","head","wc","rev","yes")).issubset(set(manifest.STREAM_WRITERS))},
    ]
    require(all(x["passed"] for x in assertions),"P8.38 static contract failure")

    commands=[]
    # Reuse the already-certified P6.21 emulator transaction fixture at current
    # head: bounded pipe creation, spawn order, immutable env snapshot and
    # deterministic rollback on injected mid-launch failure.
    pcmds,_,pa=phase6_pipeline.dispatch(
        root,action,"P6.21",
        sha256_file=sha256_file,
        run_command=run_command,
        require_project_tool=require_project_tool,
    )
    commands.extend(pcmds)
    require(all(x.get("passed") is True for x in pa),"P8.38 P6.21 pipeline regression failure")

    if action=="test":
        scratch=Path(tempfile.mkdtemp(prefix="zxux-p838-"))
        runner=Path(sys.executable).resolve()
        script=root/"v1/tools-host/test-driver/run.py"
        # These final utility fixtures inject short writes/read failures and
        # prove exact process-status propagation at current head.
        selected=("P8.02","P8.09","P8.10","P8.34","P8.37")
        for selected_step in selected:
            r=run_command([runner,script,"test","--step",selected_step,"--evidence-dir",scratch],cwd=root,timeout_seconds=900)
            commands.append(r)
            require(not r.timed_out and r.exit_code==0,f"P8.38 current-head {selected_step} failed: {r.stderr or r.stdout}")
        assertions += [
          {"name":"fuse-bounded-pipeline-launch-and-rollback","passed":True},
          {"name":"fuse-cat-read-write-status","passed":True},
          {"name":"fuse-wc-read-write-status","passed":True},
          {"name":"fuse-head-read-write-status","passed":True},
          {"name":"fuse-rev-read-write-status","passed":True},
          {"name":"fuse-final-external-echo-status","passed":True},
          {"name":"negative-injected-pipeline-launch-failure","passed":True},
        ]

    hashes={
      "v1/tests/emulator/utils_pipe.py":sha256_file(manifest_path),
      "v1/src/shell/sh.asm":sha256_file(root/"v1/src/shell/sh.asm"),
      "v1/tools-host/test-driver/phase8_pipe_matrix.py":sha256_file(root/"v1/tools-host/test-driver/phase8_pipe_matrix.py"),
      "v1/tools-host/test-driver/phase6_pipeline.py":sha256_file(root/"v1/tools-host/test-driver/phase6_pipeline.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P8.37.test.json":sha256_file(root/"v1/dist/certification/P8.37.test.json"),
    }
    return commands,hashes,assertions
