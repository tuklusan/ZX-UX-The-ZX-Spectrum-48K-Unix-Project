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

import base64
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_DIR = ROOT / ".github/rebaseline-payload"
PAYLOAD_SHA256 = "92ef827cc424325354917a9861f2c86566a429615c5f7f3baa7b4b294bfdf308"
ARCH_SHA256 = "ea23eb1c4815490830325b235e885d11b475a27ce6dcb9c70f4716d5c604fea0"
EXPECTED = {
    ".github/phase0-certification.trigger": "462932d0f2bb40561a2048618a39994a2e3a3cab5fd307a8a44d5f88393e4522",
    ".github/workflows/phase0-certification.yml": "b90dead15e4536c2d00267ad3e7f9e53e6c8c62435176a2ed9bc38d576c9ddab",
    "README.md": "cbdfad75951704abbaac35cb4787afb1f7df42250a26d67bd79b60d9f599cc88",
    "tools/check_phase0_evidence.py": "7b3cdc35abebf03bde4511afd2dec8ba934741ddb7bb3cd5f281ea30f91861ee",
    "tools/check_rr07_cleanliness.py": "0bf5ea27250319e71f35c50e5be3ff3e76e0ae2feac1323e2480e60ed40561bc",
    "tools/finalize_phase0_evidence.py": "7121ef6ebea7e09cf3aa7389899e97c430cbad62cef882e5eda6e792b56f0ac3",
    "tools/scripts/verify-environment.py": "0692f954af73da43e449d6097fb0d2f864280bec9b770d2a23953ce94118dc14",
    "tools/test_phase0_evidence_negative.py": "c94a15cb3712bfe2f99261660459900439ccb139531b1808d95850346f31346d",
    "v1/tools-host/test-driver/driver_core.py": "81c5b650e3b4449d5cd581000f9eea1a6f012d6e9240abd8580ee49539e9a0d9",
    "v1/tools-host/test-driver/foundation_rr.py": "343ccddfba3cc3db1434ce9d6f90a3c6dd8d76b659926af03d15cf7ac137e60d",
    "v1/tools-host/test-driver/run.py": "6fde1cb8db96b7bd43fb91707153e399478da9a8a80fb7dd24f596ca9f83ec0c",
    "docs/01-ZX-UX-ARCHITECTURE-REV12.md": ARCH_SHA256,
    "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md": "5985dd0d806cdfb1d75cd840e218bc630750bc8b83e07c7ae14f43becd58f6d7",
    "v1/tools-host/test-driver/phase1_core.py": "71dfd3dfadb0cd1153bdbd680e827dc5fbb2b9245e34b287cf97bc4ee82b4df5",
}
HELPERS = [
    ".github/workflows/rebaseline-materialize.yml",
    "tools/materialize_rebaseline.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str, input_text: str | None = None) -> None:
    result = subprocess.run(args, cwd=ROOT, input=input_text, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def read_payload() -> bytes:
    chunks = sorted(PAYLOAD_DIR.glob("chunk-*.txt"))
    if len(chunks) != 16:
        raise RuntimeError(f"expected 16 payload chunks, found {len(chunks)}")
    encoded: list[str] = []
    marker = "ZXUX_PAYLOAD_CHUNK\n"
    for path in chunks:
        text = path.read_text(encoding="utf-8")
        if marker not in text:
            raise RuntimeError(f"payload marker missing: {path}")
        encoded.append(text.split(marker, 1)[1].strip())
    payload = base64.b64decode("".join(encoded), validate=True)
    if hashlib.sha256(payload).hexdigest() != PAYLOAD_SHA256:
        raise RuntimeError("payload digest mismatch")
    return payload


def zstd_patch(source: str, target: str, delta_path: Path) -> None:
    if shutil.which("zstd") is None:
        raise RuntimeError("zstd is required to materialize the reviewed delta payload")
    run("zstd", "-q", "--patch-from", source, "-d", str(delta_path), "-o", target)


def main() -> int:
    if subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        raise RuntimeError("helper checkout must start clean")
    payload = read_payload()
    with tempfile.TemporaryDirectory(prefix="zxux-rebaseline-") as temp_name:
        temp = Path(temp_name)
        archive = temp / "payload.tar.gz"
        archive.write_bytes(payload)
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(temp / "payload", filter="data")
        pack = temp / "payload"
        small_diff = temp / "small.diff"
        phase1_core = ROOT / "v1/tools-host/test-driver/phase1_core.py"
        run("zstd", "-q", "-d", str(pack / "small.diff.zst"), "-o", str(small_diff))
        run("git", "apply", "--whitespace=nowarn", str(small_diff))
        zstd_patch("docs/01-ZX-UX-ARCHITECTURE-REV11.md", "docs/01-ZX-UX-ARCHITECTURE-REV12.md", pack / "rev12.zst")
        zstd_patch("docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md", "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md", pack / "rev03.zst")
        run("zstd", "-q", "-d", str(pack / "phase1_core.py.zst"), "-o", str(phase1_core))

    for relative, expected in EXPECTED.items():
        actual = sha256(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"materialized digest mismatch: {relative}: expected {expected}, got {actual}")

    for helper in HELPERS:
        (ROOT / helper).unlink()
    shutil.rmtree(PAYLOAD_DIR)
    run("git", "diff", "--check")
    run("./tools/check_license_headers.sh")
    run("python3", "tools/check_project_policy.py")
    print("ZX-UX REV12 MATERIALIZATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
