#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
EXPECT = json.loads((ROOT / "release_expectations.json").read_text(encoding="ascii"))


def fail(message: str) -> None:
    raise SystemExit(f"VERIFY FAIL: {message}")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_sha(path: Path) -> str:
    """Hash a working-tree file in its canonical repository representation.

    Git intentionally checks *.bat files out as CRLF on Windows while storing
    their normalized blobs with LF.  MANIFEST.sha256 records the canonical LF
    representation so the same manifest verifies on Windows and POSIX hosts.
    Binary/container formats remain byte-for-byte exact.
    """
    data = path.read_bytes()
    if path.suffix.lower() == ".bat":
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def run(cmd: list[str], *, cwd: Path = SDK, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        return subprocess.run(
            cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        rendered = " ".join(str(part) for part in cmd)
        fail(f"subprocess timeout after {timeout}s: {rendered}")
        raise AssertionError("unreachable") from exc


def check_clean_tree() -> None:
    bad = []
    for p in SDK.rglob("*"):
        rel = p.relative_to(SDK)
        if ".git" in rel.parts:
            continue
        if p.name == "__pycache__" or p.name == ".coverage" or p.suffix in {".pyc", ".pyo"} or p.name.endswith(".tmp"):
            bad.append(str(rel))
    if bad:
        fail("transient/cache artifacts present: " + ", ".join(sorted(bad)))


def check_required_files() -> None:
    required = [
        "VERSION", "README.md", "LICENSE", ".gitignore", ".gitattributes",
        ".github/workflows/verify.yml",
        "c48", "c48run", "c48.bat", "c48run.bat",
        "compiler/check_license_headers.py", "compiler/c48/limits.py",
        "compiler/tests/test_security.py",
        "compiler/tests/test_game_regressions.py", "compiler/verify_games.py",
        "compiler/assets/font4x8-tasword.bin", "compiler/assets/font4x8-zxux.bin",
        "doc/C48 Language Specification Rev 0.11.docx",
        "doc/ZX-UX C48 Compiler User Manual Rev 0.11.docx",
        "doc/FLOAT5-ORACLE.md", "doc/HOST-DIVERGENCES.md", "doc/CONFORMANCE.md",
        "doc/RELEASE-NOTES.md", "doc/LICENSE-HEADER-POLICY.md", "doc/GAMES.md",
        "doc/ZX-UX C48 SDK Adversarial Security Review.docx",
        "dev/src/c48host.h", "dev/src/games/gameapi.h",
        "dev/src/secguard.c", "dev/src/secoob.c",
        "dev/src/secuaf.c", "dev/src/secfree.c",
        "dev/src/secdbl.c", "dev/src/secloop.c",
        "dev/src/secrecur.c", "dev/src/seckern.c",
        "dev/src/secforge.c",
    ]
    for rel in required:
        if not (SDK / rel).is_file():
            fail(f"missing required file: {rel}")
    if (SDK / "VERSION").read_text(encoding="ascii").strip() != EXPECT["version"]:
        fail("VERSION does not match release expectations")


def check_python_source() -> None:
    broad = []
    for p in sorted((SDK / "compiler").rglob("*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p), feature_version=(3, 10))
        except (SyntaxError, UnicodeError) as exc:
            fail(f"Python parse failed for {p.relative_to(SDK)}: {exc}")
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    broad.append((p.relative_to(SDK).as_posix(), "bare"))
                elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
                    broad.append((p.relative_to(SDK).as_posix(), node.type.id))
    allowed = {
        ("compiler/c48/gui.py", "Exception"),
        ("compiler/c48/gui.py", "BaseException"),
    }
    if set(broad) != allowed:
        fail(f"broad exception boundary set changed: {broad!r}")


def check_font() -> None:
    tasword = SDK / "compiler/assets/font4x8-tasword.bin"
    zxux = SDK / "compiler/assets/font4x8-zxux.bin"
    raw = SDK / "compiler/tasword2-font4x8-raw-768.bin"
    for label, path, key in (
        ("Tasword", tasword, "tasword_sha256"),
        ("ZX-UX", zxux, "zxux_sha256"),
    ):
        if sha(path) != EXPECT["font"][key]:
            fail(f"{label} F4X8 hash mismatch")
        data = path.read_bytes()
        if len(data) != 392 or data[:8] != b"F4X8" + bytes((1, 0x20, 96, 0)):
            fail(f"{label} F4X8 header/size mismatch")
    if sha(raw) != EXPECT["font"]["raw_sha256"]:
        fail("raw Tasword font hash mismatch")
    # Prove the packed Tasword file is the mechanical two-row-per-byte transform of raw.
    expected = bytearray(b"F4X8" + bytes((1, 0x20, 96, 0)))
    raw_data = raw.read_bytes()
    for g in range(96):
        rows = raw_data[g * 8:(g + 1) * 8]
        if any(b & 0xF0 for b in rows):
            fail("raw Tasword row uses pixels outside the 4-bit glyph width")
        for r in range(0, 8, 2):
            expected.append((rows[r] << 4) | rows[r + 1])
    if bytes(expected) != tasword.read_bytes():
        fail("Tasword F4X8 does not mechanically match the raw Tasword font")


def check_c48_source_columns() -> None:
    failures = []
    source_root = SDK / "dev" / "src"
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".c", ".h"}:
            continue
        rel = path.relative_to(source_root).as_posix()
        try:
            lines = path.read_text(encoding="ascii").splitlines()
        except UnicodeError as exc:
            fail(f"non-ASCII shipped C48 source {rel}: {exc}")
        for line_no, line in enumerate(lines, 1):
            if len(line) > 64:
                failures.append(
                    f"{rel}:{line_no}={len(line)} columns"
                )
    if failures:
        fail("C48 64-column source contract violated: " + ", ".join(failures))


def check_tests() -> None:
    cp = run([sys.executable, "-B", str(ROOT / "run_tests.py")])
    if cp.returncode != 0:
        sys.stderr.write(cp.stdout + cp.stderr)
        fail("automated conformance suite failed")
    m = re.search(r"Ran (\d+) tests?", cp.stdout + cp.stderr)
    if not m or int(m.group(1)) != int(EXPECT["test_count"]):
        fail(f"test count mismatch: expected {EXPECT['test_count']}, got {m.group(1) if m else 'unreported'}")


def check_demos() -> None:
    if sha(SDK / "dev/src/c48host.h") != EXPECT["host_header_sha256"]:
        fail("c48host.h hash mismatch")
    with tempfile.TemporaryDirectory(prefix="c48-release-verify-") as td:
        d = Path(td)
        for name, exp in EXPECT["demos"].items():
            print(f"VERIFY: demo {name} ...", flush=True)
            src = SDK / f"dev/src/{name}.c"
            frozen = SDK / f"dev/bin/{name}.c48b"
            if sha(src) != exp["source_sha256"]:
                fail(f"{name}: source hash mismatch")
            if not frozen.is_file() or sha(frozen) != exp["binary_sha256"]:
                fail(f"{name}: frozen demo binary hash mismatch")
            rebuilt = d / f"{name}.c48b"
            cp = run([sys.executable, "-B", str(ROOT / "c48.py"), str(src), "-o", str(rebuilt)])
            if cp.returncode != 0:
                fail(f"{name}: rebuild failed: {cp.stderr.strip()}")
            if sha(rebuilt) != exp["binary_sha256"] or rebuilt.read_bytes() != frozen.read_bytes():
                fail(f"{name}: deterministic C48B1 rebuild mismatch")
            screen = d / f"{name}.scr"
            # Run from the temp directory with an exact basename token so argv[0]
            # is deterministic even though each clean-room root is different.
            cmd = [sys.executable, "-B", str(ROOT / "c48run.py"), "--headless",
                   "--dump-screen", screen.name, rebuilt.name, *exp["args"]]
            rp = run(cmd, cwd=d)
            if rp.returncode != 0:
                fail(f"{name}: runtime status {rp.returncode}: {rp.stderr.strip()}")
            if screen.stat().st_size != 6912 or sha(screen) != exp["screen_sha256"]:
                fail(f"{name}: exact screen hash mismatch")
            print(f"VERIFY: demo {name} PASS", flush=True)


def check_games() -> None:
    cp = run(
        [sys.executable, "-B", str(ROOT / "verify_games.py")],
        timeout=180,
    )
    if cp.returncode != 0:
        sys.stderr.write(cp.stdout + cp.stderr)
        fail("game corpus verification failed")
    marker = f"GAME VERIFY PASS: {len(EXPECT['games'])} games | quick"
    if marker not in cp.stdout:
        fail("game verifier did not report the expected completion marker")


def check_security_programs() -> None:
    with tempfile.TemporaryDirectory(prefix="c48-security-verify-") as td:
        root = Path(td)
        for name, expected_hash in EXPECT["security_programs"].items():
            source = SDK / "dev" / "src" / f"{name}.c"
            frozen = SDK / "dev" / "bin" / f"{name}.c48b"
            if not source.is_file() or not frozen.is_file():
                fail(f"security fixture missing: {name}")
            if sha(frozen) != expected_hash:
                fail(f"security fixture binary hash mismatch: {name}")
            rebuilt = root / f"{name}.c48b"
            cp = run([
                sys.executable, "-B", str(ROOT / "c48.py"),
                str(source), "-o", str(rebuilt),
            ])
            if cp.returncode != 0:
                fail(f"security fixture rebuild failed: {name}: {cp.stderr.strip()}")
            if rebuilt.read_bytes() != frozen.read_bytes():
                fail(f"security fixture deterministic rebuild mismatch: {name}")


def check_license_policy() -> None:
    from check_license_headers import check_tree
    errors = check_tree(SDK)
    if errors:
        fail("license-header gate failed: " + "; ".join(errors))


def check_launchers() -> None:
    expected_tail = {
        "c48": 'exec python3 -B "$(dirname "$0")/compiler/c48.py" "$@"',
        "c48run": 'exec python3 -B "$(dirname "$0")/compiler/c48run.py" "$@"',
        "c48.bat": 'python -B "%~dp0compiler\\c48.py" %*\nexit /b %ERRORLEVEL%',
        "c48run.bat": 'python -B "%~dp0compiler\\c48run.py" %*\nexit /b %ERRORLEVEL%',
    }
    for name, tail in expected_tail.items():
        actual = (SDK / name).read_text(encoding="ascii").replace("\r\n", "\n")
        if "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs." not in actual[:2500]:
            fail(f"launcher license header missing: {name}")
        if name.endswith(".bat"):
            if not actual.startswith("@echo off\n"):
                fail(f"Windows launcher must begin with @echo off: {name}")
        elif not actual.startswith("#!/bin/sh\n"):
            fail(f"POSIX launcher must begin with shebang: {name}")
        if tail not in actual:
            fail(f"launcher command body mismatch: {name}")
    if os.name != "nt":
        for name in ("c48", "c48run"):
            if not os.access(SDK / name, os.X_OK):
                fail(f"POSIX launcher is not executable: {name}")
            cp = run([str(SDK / name), "--version"])
            if cp.returncode != 0 or cp.stdout.strip() != f"{name} {EXPECT['version']}":
                fail(f"root launcher failed: {name}: {cp.stdout.strip()!r} {cp.stderr.strip()!r}")

def check_manifest() -> None:
    mf = SDK / "MANIFEST.sha256"
    if not mf.is_file():
        fail("MANIFEST.sha256 missing")
    listed = {}
    for lineno, line in enumerate(mf.read_text(encoding="ascii").splitlines(), 1):
        if not line:
            continue
        if "  " not in line:
            fail(f"MANIFEST.sha256 malformed at line {lineno}")
        digest, rel = line.split("  ", 1)
        if rel == "MANIFEST.sha256" or rel in listed or len(digest) != 64:
            fail(f"MANIFEST.sha256 invalid entry at line {lineno}")
        listed[rel] = digest
    actual = sorted(
        p.relative_to(SDK).as_posix()
        for p in SDK.rglob("*")
        if p.is_file() and p.name != "MANIFEST.sha256" and ".git" not in p.relative_to(SDK).parts
    )
    if sorted(listed) != actual:
        missing = sorted(set(actual) - set(listed)); extra = sorted(set(listed) - set(actual))
        fail(f"manifest member set mismatch: missing={missing} extra={extra}")
    for rel in actual:
        if manifest_sha(SDK / rel) != listed[rel]:
            fail(f"manifest hash mismatch: {rel}")


def check_versions() -> None:
    from c48 import __version__ as package_version
    if package_version != EXPECT["version"]:
        fail(f"c48 package __version__ mismatch: {package_version!r}")
    for tool in (ROOT / "c48.py", ROOT / "c48run.py"):
        cp = run([sys.executable, "-B", str(tool), "--version"])
        if cp.returncode != 0 or cp.stdout.strip() != f"{tool.stem} {EXPECT['version']}":
            fail(f"{tool.name}: --version mismatch: {cp.stdout.strip()!r} {cp.stderr.strip()!r}")
        about = run([sys.executable, "-B", str(tool), "--about"])
        # argparse may wrap version/about text according to terminal width.  The
        # license requirement is textual discoverability, not a frozen physical
        # line break, so compare after canonical whitespace folding.
        about_text = " ".join(about.stdout.split())
        for marker in (
            "Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.",
            "Based on original work by Supratim Sanyal of SANYALnet Labs.",
            "Non-Commercial License",
        ):
            if about.returncode != 0 or marker not in about_text:
                fail(f"{tool.name}: --about attribution mismatch for {marker!r}")


def main() -> int:
    checks = (
        ("clean-tree preflight", check_clean_tree),
        ("required files", check_required_files),
        ("Python source", check_python_source),
        ("license/header policy", check_license_policy),
        ("font assets", check_font),
        ("C48 64-column sources", check_c48_source_columns),
        ("launchers", check_launchers),
        ("version/about", check_versions),
        ("manifest", check_manifest),
        ("automated tests", check_tests),
        ("game corpus", check_games),
        ("security fixture binaries", check_security_programs),
        ("deterministic demos", check_demos),
        ("clean-tree postflight", check_clean_tree),
    )
    for label, func in checks:
        print(f"VERIFY: {label} ...", flush=True)
        func()
        print(f"VERIFY: {label} PASS", flush=True)
    print(
        f"VERIFY PASS: C48 SDK {EXPECT['version']} | "
        f"{EXPECT['test_count']} tests | "
        f"{len(EXPECT['demos'])} deterministic demos | "
        f"{len(EXPECT['games'])} games",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
