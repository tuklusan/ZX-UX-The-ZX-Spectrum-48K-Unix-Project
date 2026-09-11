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

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT_MARKER = b"ZX-UX project root"
LOCK_PATH = Path("tools/manifest/toolchain.lock.json")
PYTHON_VERSION = (3, 13, 15)


class BootstrapError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BootstrapError(message)


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        marker = candidate / ".zxux-root"
        if marker.is_file() and not marker.is_symlink() and marker.read_bytes() == ROOT_MARKER:
            return candidate
    raise BootstrapError("canonical .zxux-root marker not found")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(argv, cwd=cwd, env=env, check=False, text=True)
    if result.returncode != 0:
        raise BootstrapError(f"command failed ({result.returncode}): {argv!r}")


def download(item: dict, cache: Path) -> Path:
    suffix = ".tar.xz" if str(item["url"]).endswith(".tar.xz") else ".tar.gz"
    if item["id"] == "zx48-rom":
        suffix = ".rom"
    target = cache / f'{item["id"]}-{item["version"]}{suffix}'
    if target.is_file() and target.stat().st_size == item["size"] and sha256(target) == item["sha256"]:
        return target

    request = urllib.request.Request(
        item["url"],
        headers={"User-Agent": "ZX-UX environment bootstrap/1"},
    )
    tmp = target.with_suffix(target.suffix + ".part")
    tmp.unlink(missing_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as output:
            shutil.copyfileobj(response, output)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise BootstrapError(f'download failed for {item["id"]}: {exc}') from exc

    require(tmp.stat().st_size == item["size"], f'{item["id"]}: downloaded size mismatch')
    require(sha256(tmp) == item["sha256"], f'{item["id"]}: downloaded SHA-256 mismatch')
    tmp.replace(target)
    return target


def extract(archive: Path, destination: Path) -> Path:
    shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True)
    with tarfile.open(archive, "r:*") as tf:
        tf.extractall(destination, filter="data")
    entries = [p for p in destination.iterdir() if p.is_dir()]
    require(len(entries) == 1, f"archive must contain one top-level directory: {archive.name}")
    return entries[0]


def write_python_wrapper(root: Path) -> None:
    require(sys.version_info[:3] == PYTHON_VERSION, f"bootstrap Python must be 3.13.15, got {sys.version.split()[0]}")
    wrapper = root / "tools/runtime/python/bin/python"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    executable = Path(sys.executable).resolve()
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        "# Generated host wrapper; exact interpreter version is verified before use.\n"
        f'exec "{executable}" "$@"\n',
        encoding="utf-8",
        newline="\n",
    )
    wrapper.chmod(0o755)


def build_sjasmplus(root: Path, archive: Path, build_root: Path, jobs: str) -> None:
    prefix = root / "tools/runtime/sjasmplus"
    source = extract(archive, build_root / "sjasmplus-src")
    build = build_root / "sjasmplus-build"
    shutil.rmtree(build, ignore_errors=True)
    shutil.rmtree(prefix, ignore_errors=True)
    run([
        "cmake",
        "-DENABLE_LUA=OFF",
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_INSTALL_PREFIX={prefix}",
        "-S",
        str(source),
        "-B",
        str(build),
    ])
    run(["cmake", "--build", str(build), "--parallel", jobs])
    run(["cmake", "--install", str(build)])
    require((prefix / "bin/sjasmplus").is_file(), "sjasmplus install did not create the executable")


def build_libspectrum(root: Path, archive: Path, build_root: Path, jobs: str) -> Path:
    prefix = root / "tools/runtime/libspectrum"
    source = extract(archive, build_root / "libspectrum-src")
    shutil.rmtree(prefix, ignore_errors=True)
    run(["./configure", f"--prefix={prefix}"], cwd=source)
    run(["make", f"-j{jobs}"], cwd=source)
    run(["make", "install"], cwd=source)
    require((prefix / "lib").is_dir(), "libspectrum install did not create the library directory")
    return prefix


def tool_env(libspectrum_prefix: Path) -> dict[str, str]:
    env = os.environ.copy()
    pkg = libspectrum_prefix / "lib/pkgconfig"
    include = libspectrum_prefix / "include"
    lib = libspectrum_prefix / "lib"
    env["PKG_CONFIG_PATH"] = f'{pkg}:{env.get("PKG_CONFIG_PATH", "")}'
    env["CPPFLAGS"] = f'-I{include} {env.get("CPPFLAGS", "")}'.strip()
    env["LDFLAGS"] = f'-L{lib} -Wl,-rpath,{lib} {env.get("LDFLAGS", "")}'.strip()
    env["LD_LIBRARY_PATH"] = f'{lib}:{env.get("LD_LIBRARY_PATH", "")}'
    return env


def build_fuse(root: Path, archive: Path, build_root: Path, jobs: str, libspectrum_prefix: Path) -> None:
    prefix = root / "tools/runtime/fuse"
    source = extract(archive, build_root / "fuse-src")
    shutil.rmtree(prefix, ignore_errors=True)
    env = tool_env(libspectrum_prefix)
    run([
        "./configure",
        f"--prefix={prefix}",
        f"--with-local-prefix={libspectrum_prefix}",
        "--with-sdl",
        "--without-gtk",
        "--with-audio-driver=null",
    ], cwd=source, env=env)
    run(["make", f"-j{jobs}"], cwd=source, env=env)
    run(["make", "install"], cwd=source, env=env)
    require((prefix / "bin/fuse").is_file(), "Fuse install did not create the executable")


def build_fuse_utils(root: Path, archive: Path, build_root: Path, jobs: str, libspectrum_prefix: Path) -> None:
    prefix = root / "tools/runtime/fuse-utils"
    source = extract(archive, build_root / "fuse-utils-src")
    shutil.rmtree(prefix, ignore_errors=True)
    env = tool_env(libspectrum_prefix)
    run([
        "./configure",
        f"--prefix={prefix}",
        f"--with-local-prefix={libspectrum_prefix}",
    ], cwd=source, env=env)
    run(["make", f"-j{jobs}"], cwd=source, env=env)
    run(["make", "install"], cwd=source, env=env)
    require((prefix / "bin/tzxlist").is_file(), "Fuse-utils install did not create tzxlist")


def install_rom(root: Path, archive: Path) -> None:
    target = root / "tools/runtime/fuse/roms/48.rom"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(archive, target)


def main() -> int:
    try:
        root = find_root(Path(__file__).resolve())
        lock = json.loads((root / LOCK_PATH).read_text(encoding="utf-8"))
        items = {item["id"]: item for item in lock["artifacts"]}
        require(set(items) == {"python", "sjasmplus", "libspectrum", "fuse", "fuse-utils", "zx48-rom"}, "unexpected toolchain artifact set")
        require(sys.version_info[:3] == PYTHON_VERSION, f"bootstrap Python must be 3.13.15, got {sys.version.split()[0]}")

        jobs = str(max(1, min(2, os.cpu_count() or 1)))
        cache = Path(tempfile.gettempdir()) / "zxux-tool-cache"
        build_root = Path(tempfile.gettempdir()) / "zxux-tool-build"
        cache.mkdir(parents=True, exist_ok=True)
        build_root.mkdir(parents=True, exist_ok=True)

        archives = {artifact_id: download(item, cache) for artifact_id, item in items.items()}
        write_python_wrapper(root)
        build_sjasmplus(root, archives["sjasmplus"], build_root, jobs)
        libspectrum_prefix = build_libspectrum(root, archives["libspectrum"], build_root, jobs)
        build_fuse(root, archives["fuse"], build_root, jobs, libspectrum_prefix)
        build_fuse_utils(root, archives["fuse-utils"], build_root, jobs, libspectrum_prefix)
        install_rom(root, archives["zx48-rom"])

        print("ZX-UX PINNED TOOLCHAIN ACQUISITION PASS")
        return 0
    except (BootstrapError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ZX-UX PINNED TOOLCHAIN ACQUISITION FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
