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
#
# Reviewed fast-loader source promoted from ZX-UX-LOADER-1.0.0 and adapted
# prospectively under REV17/REV08 for explicit real-kernel injection.

"""Build the deterministic ZX-UX production/pre-release TZX.

The immutable reviewed seed supplies only the BASIC/fast-loader timing template.
Product mode requires an explicit freshly rebuilt 8192-byte kernel. The known
seed dummy payload is forbidden. All 24 turbo payload chunks and their loader
check bytes are regenerated from that kernel. Product mode routes the final turbo block's post-copy dispatch to the resident
finalizer. That finalizer drains every still-pending loader-owned status row,
holds the completed 24x32 display visible for one nominal second, plays the
startup beep exactly once, then performs the exact 0xE003 handoff.
"""

from __future__ import annotations

import argparse
import base64
import functools
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SEED_B64 = ROOT / "input" / "known-good-white-on-black-e003.tzx.b64"
TEXT_FILE = ROOT / "text-lines.txt"
HOOK_ASM = ROOT / "src" / "print_hook.asm"

SEED_SHA256 = "7ffe2f90b58e87a19a090ca0e0f1323605754af7d8809f3f051662f9faaec6f1"
DUMMY_PAYLOAD_SHA256 = "0e59ef9290ffc4391b0ae999177cd9d7d9eafb6fcd86a45b13f9a4bd0b08c9ce"
HOOK_SHA256 = "9c05b4d2e1c23f44a4e3d059a1313116a8f7c12380e4ba1f2ccf645cf5e0e475"

PROG_BASE = 0x5CCB
HOOK_ADDR = 0x5E4F
OLD_TEXT_ADDR = 0x5F6A
TEXT_BUFFER_SENTINEL = 0xBEEF
TEXT_LINES = 24
TEXT_WIDTH = 32
KERNEL_BASE = 0xE000
KERNEL_SIZE = 8192
PAYLOAD_ENTRY = 0xE003
RENDER_ROW_ADDR = 0x5E62
FINAL_HOLD_ADDR = 0x5EB4
FINAL_LOADER_AFTER = FINAL_HOLD_ADDR
INIT_SCREEN_ADDR = 0x5EC2
BEEP_ADDR = 0x5F2A
PAUSE_ADDR = 0x5F39
FINALIZE_DISPLAY_ADDR = 0x5F50
PRE_BEEP_PAUSE_TSTATES = 3500009
TEXT_ARRAY_OFFSET = 84
CHUNK_LENGTHS = (342,) * 8 + (341,) * 16


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def xor_checksum(data: bytes | bytearray) -> int:
    return functools.reduce(int.__xor__, data, 0)


def loader_check(data: bytes) -> int:
    """Exact loader check independently recovered from the seed loader code.

    The resident routine initializes E=1, then for every received byte performs
    ADD A,E followed by RLCA and stores the result back in E. Header byte 7 is
    compared with E after exactly the declared payload length has been received.
    """
    value = 1
    for byte in data:
        value = (value + byte) & 0xFF
        value = ((value << 1) | (value >> 7)) & 0xFF
    return value


def parse_tzx(tz: bytes | bytearray):
    if bytes(tz[:10]) != b"ZXTape!\x1a\x01\x14":
        raise AssertionError("bad TZX header")
    p = 10
    out = []
    while p < len(tz):
        bid = tz[p]
        start = p
        p += 1
        if bid == 0x30:
            n = tz[p]
            p += 1 + n
            body = bytes(tz[start + 2:p])
        elif bid == 0x10:
            pause, n = struct.unpack_from("<HH", tz, p)
            p += 4
            body = (pause, bytes(tz[p:p+n]))
            p += n
        elif bid == 0x20:
            pause = struct.unpack_from("<H", tz, p)[0]
            p += 2
            body = pause
        elif bid == 0x19:
            n = struct.unpack_from("<I", tz, p)[0]
            p += 4
            body_start = p
            body = bytes(tz[p:p+n])
            p += n
            out.append((bid, start, p, body, body_start))
            if p > len(tz):
                raise AssertionError("truncated TZX")
            continue
        else:
            raise AssertionError(f"unexpected TZX block {bid:#x} at {start:#x}")
        if p > len(tz):
            raise AssertionError("truncated TZX")
        out.append((bid, start, p, body, None))
    if p != len(tz):
        raise AssertionError("TZX parse did not end at EOF")
    return out


def generalized_data_span(body: bytes) -> tuple[int, int]:
    o = 2
    total_pilot = struct.unpack_from("<I", body, o)[0]
    o += 4
    npp, asp = body[o], body[o+1]
    o += 2
    total_data_bits = struct.unpack_from("<I", body, o)[0]
    o += 4
    npd, asd = body[o], body[o+1]
    o += 2
    o += (asp or 256) * (1 + npp * 2)
    o += total_pilot * 3
    o += (asd or 256) * (1 + npd * 2)
    count = (total_data_bits + 7) // 8
    if o + count > len(body):
        raise AssertionError("generalized-data stream overruns block")
    return o, count


def generalized_data(body: bytes) -> bytes:
    start, count = generalized_data_span(body)
    return body[start:start+count]


def parse_basic(basic: bytes | bytearray):
    q = 0
    lines = []
    while q < len(basic):
        if q + 4 > len(basic):
            raise AssertionError("truncated BASIC line")
        number = int.from_bytes(basic[q:q+2], "big")
        length = int.from_bytes(basic[q+2:q+4], "little")
        end = q + 4 + length
        if end > len(basic) or basic[end-1] != 0x0D:
            raise AssertionError(f"bad BASIC line {number}")
        lines.append((number, q, length))
        q = end
    if q != len(basic):
        raise AssertionError("BASIC parse did not end at EOF")
    return lines


def load_text_lines() -> list[str]:
    lines = TEXT_FILE.read_text(encoding="ascii").splitlines()
    if len(lines) != TEXT_LINES:
        raise ValueError(f"{TEXT_FILE}: expected {TEXT_LINES} lines, got {len(lines)}")
    for i, line in enumerate(lines, 1):
        if len(line) != TEXT_WIDTH:
            raise ValueError(f"{TEXT_FILE}: line {i} is {len(line)} chars, expected {TEXT_WIDTH}")
        if any(ord(ch) < 32 or ord(ch) > 126 for ch in line):
            raise ValueError(f"{TEXT_FILE}: line {i} contains non-printable ASCII")
        if '"' in line:
            raise ValueError(f"{TEXT_FILE}: line {i} contains unsupported double quote")
    return lines


def assemble_hook(output: Path, pasmo: str) -> bytes:
    resolved = shutil.which(pasmo) if "/" not in pasmo else pasmo
    if not resolved:
        raise RuntimeError("pasmo is required (release-scoped pinned version: 0.5.3-7)")
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([resolved, "--bin", str(HOOK_ASM), str(output)], check=True)
    hook = bytearray(output.read_bytes())
    if sha256(hook) != HOOK_SHA256:
        raise AssertionError("ZX-UX integration hook hash drifted")
    sentinel = struct.pack("<H", TEXT_BUFFER_SENTINEL)
    if hook.count(sentinel) != 1:
        raise AssertionError("print_hook.asm must contain exactly one TEXT_BUFFER sentinel")
    if len(hook) != 273:
        raise AssertionError(f"unexpected hook length {len(hook)}; expected 273")
    screen_off = INIT_SCREEN_ADDR - HOOK_ADDR
    screen_prefix = bytes.fromhex(
        "21004011014001ff17af77edb0"
        "21005811015801ff023607edb0"
        "21bc5a361723363723362723362f"
    )
    if hook[screen_off:screen_off+len(screen_prefix)] != screen_prefix:
        raise AssertionError("turbo screen initializer drifted")
    hold_off = FINAL_HOLD_ADDR - HOOK_ADDR
    beep_off = BEEP_ADDR - HOOK_ADDR
    pause_off = PAUSE_ADDR - HOOK_ADDR
    expected_hold = bytes(
        [0xCD, FINALIZE_DISPLAY_ADDR & 0xFF, FINALIZE_DISPLAY_ADDR >> 8,
         0xC3, PAYLOAD_ENTRY & 0xFF, PAYLOAD_ENTRY >> 8]
    ) + bytes(8)
    if hook[hold_off:hold_off+14] != expected_hold:
        raise AssertionError("final_hold completion/E003 dispatch drifted")
    if hook[beep_off:beep_off+15] != bytes.fromhex("dde511e00021ca01cdb503f3dde1c9"):
        raise AssertionError("startup beep drifted")
    finalizer_off = FINALIZE_DISPLAY_ADDR - HOOK_ADDR
    if hook[pause_off:finalizer_off] != bytes.fromhex(
        "f316020100000b78b120fb1520f501d40d0b78b120fbc9"
    ):
        raise AssertionError("one-second pre-beep pause drifted")
    if hook[finalizer_off:] != bytes.fromhex(
        "cd625e3af75eb720f7cd395fcd2a5fc9"
    ):
        raise AssertionError("pending-row finalizer drifted")
    return bytes(hook)


def verify_seed_transport(blocks) -> tuple[list[bytes], list[bytes]]:
    gen = [generalized_data(b[3]) for b in blocks if b[0] == 0x19]
    if len(gen) != 48:
        raise AssertionError(f"expected 48 generalized blocks, got {len(gen)}")
    headers, chunks = gen[0::2], gen[1::2]
    if tuple(map(len, chunks)) != CHUNK_LENGTHS:
        raise AssertionError("seed chunk lengths drifted")
    if any(len(h) != 17 for h in headers):
        raise AssertionError("seed loader-header length drifted")
    payload = b"".join(chunks)
    if len(payload) != KERNEL_SIZE or sha256(payload) != DUMMY_PAYLOAD_SHA256:
        raise AssertionError("seed dummy payload identity drifted")
    offset = 0
    for i, (header, chunk) in enumerate(zip(headers, chunks)):
        length, load_addr, dest_addr, zero, check, after, *_ = struct.unpack(
            "<HHHBBHHBHBB", header
        )
        if length != len(chunk) or zero != 0:
            raise AssertionError(f"loader header {i} length/zero drifted")
        if check != loader_check(chunk):
            raise AssertionError(f"loader header {i} check algorithm mismatch")
        logical_dest = dest_addr or load_addr
        if logical_dest != KERNEL_BASE + offset:
            raise AssertionError(
                f"loader header {i} destination {logical_dest:#06x} != {KERNEL_BASE + offset:#06x}"
            )
        if i < 23 and after != 0x0100:
            raise AssertionError(f"loader header {i} continuation drifted")
        if i == 23 and (load_addr, dest_addr, after) != (0x9000, 0xFEAB, PAYLOAD_ENTRY):
            raise AssertionError("final loader header/handoff drifted")
        offset += len(chunk)
    if offset != KERNEL_SIZE:
        raise AssertionError("loader destination coverage drifted")
    return headers, chunks


def patch_basic(seed: bytes, hook_template: bytes) -> bytearray:
    lines = load_text_lines()
    display = "".join(lines).encode("ascii")
    blocks = parse_tzx(seed)
    if [b[0] for b in blocks[:3]] != [0x30, 0x10, 0x10]:
        raise AssertionError("unexpected seed prefix")
    verify_seed_transport(blocks)

    pause1, header = blocks[1][3]
    pause2, data = blocks[2][3]
    header = bytearray(header)
    data = bytearray(data)
    if len(header) != 19 or header[0] != 0 or header[2:12] != b"ZX-UX Unix":
        raise AssertionError("unexpected BASIC header")
    if data[0] != 0xFF or xor_checksum(data) != 0:
        raise AssertionError("bad seed BASIC data block")

    basic = bytearray(data[1:-1])
    parsed = parse_basic(basic)
    if [x[0] for x in parsed] != [10, 20, 30]:
        raise AssertionError("expected BASIC lines 10,20,30")
    _, line20_off, line20_len = parsed[1]
    _, line30_off, _ = parsed[2]
    old_eol = line20_off + 4 + line20_len - 1
    if PROG_BASE + line20_off + 5 != 0x5CE7 or PROG_BASE + old_eol != 0x5F0F:
        raise AssertionError("seed loader layout drifted")

    old_hook_start = HOOK_ADDR - PROG_BASE
    old_hook = bytes(basic[old_hook_start:old_eol])
    if len(old_hook) != 192:
        raise AssertionError("seed hook length drifted")
    old_ptr = struct.pack("<H", OLD_TEXT_ADDR)
    if [i for i in range(len(old_hook)-1) if old_hook[i:i+2] == old_ptr] != [139]:
        raise AssertionError("seed text pointer drifted")

    hook = bytearray(hook_template)
    delta = len(hook) - len(old_hook)
    if delta != 81:
        raise AssertionError("hook growth drifted")
    new_line30_off = line30_off + delta
    content = new_line30_off + 4
    new_text_addr = PROG_BASE + content + TEXT_ARRAY_OFFSET
    sentinel = struct.pack("<H", TEXT_BUFFER_SENTINEL)
    hook = hook.replace(sentinel, struct.pack("<H", new_text_addr), 1)

    patched = bytearray()
    patched += basic[:old_hook_start]
    patched += hook
    patched += basic[old_eol:]
    patched[line20_off+2:line20_off+4] = struct.pack("<H", line20_len + delta)
    parsed2 = parse_basic(patched)
    if [x[0] for x in parsed2] != [10, 20, 30] or parsed2[2][1] != new_line30_off:
        raise AssertionError("patched BASIC structure drifted")

    content = new_line30_off + 4
    if patched[content+31:content+34] != bytes([0xFB, 0x3A, 0xF5]):
        raise AssertionError("initial BASIC CLS/PRINT layout drifted")
    if patched[content+67:content+72] != bytes([0x22, 0x3A, 0xFB, 0x3A, 0xF9]):
        raise AssertionError("final BASIC CLS/RANDOMIZE layout drifted")
    del patched[content+69:content+71]
    patched[new_line30_off+2:new_line30_off+4] = struct.pack("<H", parsed2[2][2] - 2)
    parse_basic(patched)
    if patched[content+67:content+70] != bytes([0x22, 0x3A, 0xF9]):
        raise AssertionError("final BASIC CLS was not removed")
    if patched[content+83] != 0xEA:
        raise AssertionError("REM/text-array offset drifted")
    patched[content+35:content+67] = lines[0].encode("ascii")
    patched[content+TEXT_ARRAY_OFFSET:content+TEXT_ARRAY_OFFSET+768] = display

    new_data = bytearray([0xFF]) + patched
    new_data.append(xor_checksum(new_data))
    new_header = bytearray(header)
    n = len(patched)
    new_header[12:14] = struct.pack("<H", n)
    new_header[16:18] = struct.pack("<H", n)
    new_header[18] = xor_checksum(new_header[:18])
    if xor_checksum(new_data) != 0 or xor_checksum(new_header) != 0:
        raise AssertionError("patched BASIC Spectrum checksum failed")

    prefix = seed[:blocks[1][1]]
    turbo_tail = seed[blocks[2][2]:]
    out = bytearray(prefix)
    out += bytes([0x10]) + struct.pack("<HH", pause1, len(new_header)) + new_header
    out += bytes([0x10]) + struct.pack("<HH", pause2, len(new_data)) + new_data
    out += turbo_tail
    return out


def inject_kernel(tzx: bytearray, kernel: bytes) -> None:
    if len(kernel) != KERNEL_SIZE:
        raise ValueError(f"kernel must be exactly {KERNEL_SIZE} bytes")
    if sha256(kernel) == DUMMY_PAYLOAD_SHA256:
        raise ValueError("known seed dummy kernel is forbidden in product mode")

    blocks = parse_tzx(tzx)
    gen = [b for b in blocks if b[0] == 0x19]
    if len(gen) != 48:
        raise AssertionError("expected exactly 48 generalized-data blocks")
    headers = gen[0::2]
    payloads = gen[1::2]
    offset = 0
    for i, (hb, pb) in enumerate(zip(headers, payloads)):
        h_start, h_count = generalized_data_span(hb[3])
        p_start, p_count = generalized_data_span(pb[3])
        if h_count != 17 or p_count != CHUNK_LENGTHS[i]:
            raise AssertionError(f"generalized-data shape drifted at pair {i}")
        chunk = kernel[offset:offset+p_count]
        if len(chunk) != p_count:
            raise AssertionError("kernel chunk underflow")
        header = bytearray(generalized_data(hb[3]))
        if struct.unpack_from("<H", header, 0)[0] != p_count:
            raise AssertionError(f"header {i} length does not match payload")
        header[7] = loader_check(chunk)
        if i == len(payloads) - 1:
            header[8:10] = struct.pack("<H", FINAL_LOADER_AFTER)
        hz = hb[4] + h_start
        pz = pb[4] + p_start
        tzx[hz:hz+h_count] = header
        tzx[pz:pz+p_count] = chunk
        offset += p_count
    if offset != KERNEL_SIZE:
        raise AssertionError("kernel injection did not consume exactly 8192 bytes")


def reconstruct_kernel(tzx: bytes) -> bytes:
    blocks = parse_tzx(tzx)
    gen = [generalized_data(b[3]) for b in blocks if b[0] == 0x19]
    if len(gen) != 48:
        raise AssertionError("expected 48 generalized-data blocks")
    headers, chunks = gen[0::2], gen[1::2]
    offset = 0
    for i, (header, chunk) in enumerate(zip(headers, chunks)):
        if len(header) != 17 or len(chunk) != CHUNK_LENGTHS[i]:
            raise AssertionError("generalized-data shape drifted")
        length, load_addr, dest_addr, zero, check, after, *_ = struct.unpack(
            "<HHHBBHHBHBB", header
        )
        if length != len(chunk) or zero != 0 or check != loader_check(chunk):
            raise AssertionError(f"loader check/header mismatch at pair {i}")
        logical_dest = dest_addr or load_addr
        if logical_dest != KERNEL_BASE + offset:
            raise AssertionError(f"kernel destination coverage mismatch at pair {i}")
        if i < 23 and after != 0x0100:
            raise AssertionError(f"loader continuation mismatch at pair {i}")
        if i == 23 and after != FINAL_LOADER_AFTER:
            raise AssertionError("final loader finalizer dispatch mismatch")
        offset += len(chunk)
    payload = b"".join(chunks)
    if len(payload) != KERNEL_SIZE:
        raise AssertionError("reconstructed kernel size mismatch")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", type=Path, required=True, help="freshly rebuilt exact 8192-byte kernel")
    ap.add_argument("--output", type=Path, required=True, help="output TZX path")
    ap.add_argument("--hook-output", type=Path, help="optional assembled hook output")
    ap.add_argument("--manifest", type=Path, help="optional JSON build manifest")
    ap.add_argument("--pasmo", default="pasmo")
    args = ap.parse_args(argv)

    seed = base64.b64decode(SEED_B64.read_bytes(), validate=False)
    if sha256(seed) != SEED_SHA256:
        raise AssertionError("immutable seed hash mismatch")
    kernel = args.kernel.read_bytes()
    if len(kernel) != KERNEL_SIZE:
        raise SystemExit(f"kernel must be exactly {KERNEL_SIZE} bytes")
    if sha256(kernel) == DUMMY_PAYLOAD_SHA256:
        raise SystemExit("known seed dummy payload is forbidden")

    hook_path = args.hook_output or args.output.with_suffix(".hook.bin")
    hook = assemble_hook(hook_path, args.pasmo)
    out = patch_basic(seed, hook)
    inject_kernel(out, kernel)
    rebuilt = reconstruct_kernel(bytes(out))
    if rebuilt != kernel:
        raise AssertionError("post-build embedded kernel differs byte-for-byte")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(out)
    manifest = {
        "schema": 1,
        "seed_sha256": SEED_SHA256,
        "dummy_payload_sha256_forbidden": DUMMY_PAYLOAD_SHA256,
        "hook_sha256": sha256(hook),
        "kernel_size": len(kernel),
        "kernel_sha256": sha256(kernel),
        "embedded_kernel_sha256": sha256(rebuilt),
        "tzx_size": len(out),
        "tzx_sha256": sha256(out),
        "payload_chunks": list(CHUNK_LENGTHS),
        "payload_chunk_count": len(CHUNK_LENGTHS),
        "kernel_range": "0xE000-0xFFFF",
        "handoff": "0xE003",
        "final_loader_after": f"0x{FINAL_LOADER_AFTER:04X}",
        "pre_beep_pause_nominal_tstates": PRE_BEEP_PAUSE_TSTATES,
        "handoff_path": "final block -> render row 24 -> ~1 second hold -> startup beep -> 0xE003",
        "screen_file": None,
        "release_tap": None,
        "loader_display": "24x32 loader-owned",
        "loader_check": "E=1; E=RLCA((byte+E)&0xff) for each byte",
    }
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"seed_sha256={SEED_SHA256}")
    print(f"kernel_sha256={manifest['kernel_sha256']}")
    print(f"embedded_kernel_sha256={manifest['embedded_kernel_sha256']}")
    print(f"tzx_sha256={manifest['tzx_sha256']}")
    print(f"tzx_size={manifest['tzx_size']}")
    print("ZX-UX RELEASE TZX BUILD PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
