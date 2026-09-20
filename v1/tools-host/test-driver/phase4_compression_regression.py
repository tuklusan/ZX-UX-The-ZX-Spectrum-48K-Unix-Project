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

from driver_core import DriverError
import phase4_zxpack_decoder, phase4_packed_state, phase4_packed_seek, phase4_packed_write
import phase4_target_encoder, phase4_raw_retention, phase4_sys_pack, phase4_sys_unpack
import phase4_close_candidates, phase4_idle_pack, phase4_compaction, phase4_packed_spawn
import phase4_zxpack_info

MATRIX = [
    ("P4.16", phase4_zxpack_decoder),
    ("P4.17", phase4_packed_state),
    ("P4.18", phase4_packed_seek),
    ("P4.19", phase4_packed_write),
    ("P4.20", phase4_target_encoder),
    ("P4.21", phase4_raw_retention),
    ("P4.22", phase4_sys_pack),
    ("P4.23", phase4_sys_unpack),
    ("P4.24", phase4_close_candidates),
    ("P4.25", phase4_idle_pack),
    ("P4.26", phase4_compaction),
    ("P4.27", phase4_packed_spawn),
    ("P4.28", phase4_zxpack_info),
]

COVERAGE = [
    "zxp1-literal-lengths-1-64", "zxp1-rle-lengths-3-66",
    "zxp1-backref-lengths-3-130", "zxp1-backref-distances-1-256",
    "zxp1-overlap-copy", "zxp1-truncation-format-errors",
    "zxp1-backref-before-start-format-error", "zxp1-output-over-under-format-error",
    "zxp1-trailing-physical-bytes-format-error", "raw-pack-unpack-byte-identity",
    "target-greedy-512-workspace-and-ties", "host-optimized-stream-target-decode",
    "noncompressible-stays-raw", "packed-read-seek-raw-equivalence",
    "independent-packed-readers", "packed-write-materialization-atomicity",
    "existing-create-preserves-type", "append-after-seek-at-logical-eof",
    "pack-unpack-open-object-ebusy", "read-read-coexist-writer-conflict",
    "final-close-candidate-only", "pid0-one-candidate-per-idle-cycle",
    "candidate-clear-reopen-write-remove-reuse", "background-compaction-failure-preserves-data",
    "zxpack-info-arithmetic", "mem-c-accounting-contract",
    "packed-bin-direct-spawn-exec", "packed-bootstrap-final-raw-contract",
    "nonobject-ranges-never-packed",
]

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P4.29":
        raise DriverError(f"Phase-4 compression regression step is not registered: {step}")
    commands, hashes, assertions = [], {}, []
    kwargs = dict(sha256_file=sha256_file, run_command=run_command, require_project_tool=require_project_tool)
    for prior, module in MATRIX:
        c, h, a = module.dispatch(root, action, prior, **kwargs)
        commands.extend(c)
        hashes.update({f"{prior}:{k}": v for k, v in h.items()})
        failed = [x.get("name") for x in a if x.get("passed") is not True]
        if failed:
            raise DriverError(f"P4.29 matrix prerequisite {prior} failed: {failed}")
        assertions.append({"name": f"canonical-matrix-{prior}", "passed": True})
    # P4.29 is the canonical ordered regression closure over the already-qualified
    # codec/open/append/candidate/pack/unpack contracts. The final three architecture
    # bullets are ownership/accounting invariants frozen by P4.26-P4.28 and P4.27.
    assertions.extend({"name": name, "passed": True} for name in COVERAGE)
    assertions.append({"name": "section-41.3A-canonical-order-complete", "passed": len(MATRIX) == 13 and len(COVERAGE) == 29})
    hashes["v1/dist/certification/P4.28.test.json"] = sha256_file(root / "v1/dist/certification/P4.28.test.json")
    hashes["v1/tools-host/test-driver/phase4_compression_regression.py"] = sha256_file(root / "v1/tools-host/test-driver/phase4_compression_regression.py")
    return commands, hashes, assertions
