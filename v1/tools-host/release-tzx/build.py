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
# Reviewed fast-loader source promoted from the preserved portable package.
#!/usr/bin/env python3
"""Deterministically rebuild the current ZX-UX loader TZX.

The immutable seed is the tagged, verified white-on-black/E003 loader.
This builder updates the BASIC-resident display text, removes the seed's final
BASIC CLS, and installs the hook assembled from src/print_hook.asm. The turbo
payload/timing tail is preserved byte-for-byte from the seed.
"""

import base64
import functools
import hashlib
import pathlib
import shutil
import struct
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEED_B64 = ROOT / "input" / "known-good-white-on-black-e003.tzx.b64"
TEXT_FILE = ROOT / "text-lines.txt"
HOOK_ASM = ROOT / "src" / "print_hook.asm"

OUT_TZX = OUT_DIR / "zx24_loader_idle_demo.tzx"
OUT_PAYLOAD = OUT_DIR / "dummy_e000_8k_idle.bin"  # legacy filename; exact 8 KiB payload
OUT_HOOK = OUT_DIR / "print_hook.bin"
OUT_SUMS = OUT_DIR / "SHA256SUMS"

SEED_SHA256 = "7ffe2f90b58e87a19a090ca0e0f1323605754af7d8809f3f051662f9faaec6f1"
EXPECTED_TZX_SHA256 = "9a77617b16d04c767c5895261ca9a823b57060e642adadffa58b34cbfcd7d642"
EXPECTED_PAYLOAD_SHA256 = "0e59ef9290ffc4391b0ae999177cd9d7d9eafb6fcd86a45b13f9a4bd0b08c9ce"

PROG_BASE = 0x5CCB
HOOK_ADDR = 0x5E4F
OLD_TEXT_ADDR = 0x5F6A
TEXT_BUFFER_SENTINEL = 0xBEEF
TEXT_LINES = 24
TEXT_WIDTH = 32
PAYLOAD_ENTRY = 0xE003
FINAL_HOLD_ADDR = 0x5EB4
INIT_SCREEN_ADDR = 0x5EC2
BEEP_ADDR = 0x5F2A
TEXT_ARRAY_OFFSET = 84


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def xor_checksum(data):
    return functools.reduce(int.__xor__, data, 0)


def parse_tzx(tz):
    if tz[:10] != b"ZXTape!\x1a\x01\x14":
        raise AssertionError("bad TZX header")
    p = 10
    out = []
    while p < len(tz):
        bid = tz[p]
        start = p
        p += 1
        if bid == 0x30:
            n = tz[p]
            p += 1
            body = tz[p:p+n]
            p += n
            out.append((bid, start, p, body))
        elif bid == 0x10:
            pause, n = struct.unpack_from("<HH", tz, p)
            p += 4
            body = tz[p:p+n]
            p += n
            out.append((bid, start, p, (pause, body)))
        elif bid == 0x20:
            pause = struct.unpack_from("<H", tz, p)[0]
            p += 2
            out.append((bid, start, p, pause))
        elif bid == 0x19:
            n = struct.unpack_from("<I", tz, p)[0]
            p += 4
            body = tz[p:p+n]
            p += n
            out.append((bid, start, p, body))
        else:
            raise AssertionError(f"unexpected TZX block {bid:#x} at {start:#x}")
        if p > len(tz):
            raise AssertionError("truncated TZX")
    if p != len(tz):
        raise AssertionError("TZX parse did not end at EOF")
    return out


def generalized_data(body):
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
    return body[o:o + (total_data_bits + 7) // 8]


def parse_basic(basic):
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


def load_text_lines():
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


def assemble_hook():
    pasmo = shutil.which("pasmo")
    if not pasmo:
        raise RuntimeError("pasmo is required (pinned CI version: 0.5.3-7)")
    subprocess.run([pasmo, "--bin", str(HOOK_ASM), str(OUT_HOOK)], check=True)
    hook = bytearray(OUT_HOOK.read_bytes())
    sentinel = struct.pack("<H", TEXT_BUFFER_SENTINEL)
    if hook.count(sentinel) != 1:
        raise AssertionError("print_hook.asm must contain exactly one TEXT_BUFFER sentinel")
    if len(hook) != 234:
        raise AssertionError(f"unexpected hook length {len(hook)}; expected 234")

    # Turbo screen ownership is explicit: clear all 6144 bitmap bytes,
    # initialize all attributes white-on-black, then set row 21 columns
    # 28-31 to red/yellow/green/cyan PAPER while retaining white INK.
    screen_off = INIT_SCREEN_ADDR - HOOK_ADDR
    screen_prefix = bytes.fromhex(
        "21004011014001ff17af77edb0"
        "21005811015801ff023607edb0"
        "21bc5a361723363723362723362f"
    )
    if hook[screen_off:screen_off+len(screen_prefix)] != screen_prefix:
        raise AssertionError("turbo screen initializer drifted")

    # Surgical invariants for the single startup beep.
    hold_off = FINAL_HOLD_ADDR - HOOK_ADDR
    beep_off = BEEP_ADDR - HOOK_ADDR
    if hook[hold_off:hold_off+3] != bytes([0xC3, BEEP_ADDR & 0xFF, BEEP_ADDR >> 8]):
        raise AssertionError("final_hold no longer jumps to startup_beep")
    beep_bytes = bytes.fromhex("dde511e00021ca01cdb503f3dde1c9")
    if hook[beep_off:] != beep_bytes:
        raise AssertionError("startup beep drifted")
    return hook


def extract_payload(blocks):
    gen = [generalized_data(b[3]) for b in blocks if b[0] == 0x19]
    if len(gen) != 48:
        raise AssertionError(f"expected 48 generalized blocks, got {len(gen)}")
    headers = gen[0::2]
    chunks = gen[1::2]
    if len(headers) != 24 or len(chunks) != 24:
        raise AssertionError("expected 24 header/payload pairs")

    payload = b"".join(chunks)
    if len(payload) != 8192:
        raise AssertionError(f"payload length {len(payload)}, expected 8192")

    final = struct.unpack("<HHHBBHHBHBB", headers[-1])
    length, load_addr, dest_addr, _zero, _crc, after, *_ = final
    if (length, load_addr, dest_addr, after) != (341, 0x9000, 0xFEAB, PAYLOAD_ENTRY):
        raise AssertionError(
            f"final dispatch mismatch: len={length}, load={load_addr:#06x}, "
            f"dest={dest_addr:#06x}, after={after:#06x}"
        )
    if payload[:3] != bytes.fromhex("b617f6"):
        raise AssertionError("E000-E002 prefix drifted")
    if sha256(payload) != EXPECTED_PAYLOAD_SHA256:
        raise AssertionError("8 KiB payload hash drifted")
    return payload


def build():
    seed = base64.b64decode(SEED_B64.read_bytes(), validate=False)
    if sha256(seed) != SEED_SHA256:
        raise AssertionError("immutable seed hash mismatch")

    lines = load_text_lines()
    display = "".join(lines).encode("ascii")
    if len(display) != 768:
        raise AssertionError("display array must be exactly 768 bytes")

    blocks = parse_tzx(seed)
    if [b[0] for b in blocks[:3]] != [0x30, 0x10, 0x10]:
        raise AssertionError("unexpected seed prefix")
    if sum(1 for b in blocks if b[0] == 0x19) != 48:
        raise AssertionError("seed turbo block count drifted")

    payload = extract_payload(blocks)

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
    _, line30_off, _line30_len = parsed[2]
    old_eol = line20_off + 4 + line20_len - 1

    if PROG_BASE + line20_off + 5 != 0x5CE7:
        raise AssertionError("loader entry drifted")
    if PROG_BASE + old_eol != 0x5F0F:
        raise AssertionError("seed hook end drifted")

    old_hook_start = HOOK_ADDR - PROG_BASE
    old_hook = bytes(basic[old_hook_start:old_eol])
    if len(old_hook) != 192:
        raise AssertionError("seed hook length drifted")

    old_ptr = struct.pack("<H", OLD_TEXT_ADDR)
    ptr_positions = [i for i in range(len(old_hook)-1) if old_hook[i:i+2] == old_ptr]
    if ptr_positions != [139]:
        raise AssertionError("seed text pointer drifted")

    hook = assemble_hook()
    delta = len(hook) - len(old_hook)
    if delta != 42:
        raise AssertionError(f"hook growth is {delta}, expected 42")

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
    if patched[content+33:content+35] != bytes([0xF5, 0x22]):
        raise AssertionError("PRINT token/string layout drifted")
    if patched[content+67:content+72] != bytes([0x22, 0x3A, 0xFB, 0x3A, 0xF9]):
        raise AssertionError("final BASIC CLS/RANDOMIZE layout drifted")

    # Keep the initial CLS, but remove only the later CLS and its trailing
    # colon. init_screen now performs the complete handoff-screen clear.
    del patched[content+69:content+71]
    patched[new_line30_off+2:new_line30_off+4] = struct.pack(
        "<H", parsed2[2][2] - 2
    )
    parsed2 = parse_basic(patched)
    if [x[0] for x in parsed2] != [10, 20, 30] or parsed2[2][1] != new_line30_off:
        raise AssertionError("BASIC structure drifted after final CLS removal")
    if patched[content+67:content+70] != bytes([0x22, 0x3A, 0xF9]):
        raise AssertionError("final BASIC CLS was not removed")
    if patched[content+83] != 0xEA:
        raise AssertionError("REM/text-array offset drifted")

    patched[content+35:content+67] = lines[0].encode("ascii")
    patched[content+TEXT_ARRAY_OFFSET:content+TEXT_ARRAY_OFFSET+768] = display

    if PROG_BASE + content + TEXT_ARRAY_OFFSET != new_text_addr:
        raise AssertionError("text address calculation drifted")
    if patched[content+TEXT_ARRAY_OFFSET:content+TEXT_ARRAY_OFFSET+768] != display:
        raise AssertionError("display array patch failed")

    new_data = bytearray([0xFF]) + patched
    new_data.append(xor_checksum(new_data))
    if xor_checksum(new_data) != 0:
        raise AssertionError("BASIC data checksum failed")

    new_header = bytearray(header)
    n = len(patched)
    new_header[12:14] = struct.pack("<H", n)
    new_header[16:18] = struct.pack("<H", n)
    new_header[18] = xor_checksum(new_header[:18])
    if xor_checksum(new_header) != 0:
        raise AssertionError("BASIC header checksum failed")

    prefix = seed[:blocks[1][1]]
    turbo_tail = seed[blocks[2][2]:]

    out = bytearray(prefix)
    out += bytes([0x10]) + struct.pack("<HH", pause1, len(new_header)) + new_header
    out += bytes([0x10]) + struct.pack("<HH", pause2, len(new_data)) + new_data
    out += turbo_tail

    # The entire turbo tail, including the 8 KiB payload and E003 dispatch,
    # must remain byte-for-byte identical to the immutable seed.
    out_blocks = parse_tzx(out)
    if [(b[0], b[3]) for b in out_blocks[3:]] != [(b[0], b[3]) for b in blocks[3:]]:
        raise AssertionError("turbo tail changed")

    if sha256(out) != EXPECTED_TZX_SHA256:
        raise AssertionError(
            f"rebuilt TZX hash {sha256(out)} != expected {EXPECTED_TZX_SHA256}"
        )

    OUT_TZX.write_bytes(out)
    OUT_PAYLOAD.write_bytes(payload)

    sums = [
        f"{sha256(OUT_TZX.read_bytes())}  {OUT_TZX.name}",
        f"{sha256(OUT_PAYLOAD.read_bytes())}  {OUT_PAYLOAD.name}",
        f"{sha256(OUT_HOOK.read_bytes())}  {OUT_HOOK.name}",
    ]
    OUT_SUMS.write_text("\n".join(sums) + "\n", encoding="ascii")

    print(f"seed sha256:    {SEED_SHA256}")
    print(f"output sha256:  {EXPECTED_TZX_SHA256}")
    print(f"payload sha256: {EXPECTED_PAYLOAD_SHA256}")
    print(f"hook sha256:    {sha256(OUT_HOOK.read_bytes())}")
    print(f"BASIC bytes:    {len(patched)}")
    print(f"hook bytes:     {len(hook)} at {HOOK_ADDR:#06x}")
    print(f"text bytes:     768 at {new_text_addr:#06x}")
    print(f"payload entry:  {PAYLOAD_ENTRY:#06x}")
    print("turbo tail:     preserved byte-for-byte")


if __name__ == "__main__":
    build()
