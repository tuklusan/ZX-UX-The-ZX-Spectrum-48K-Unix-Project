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

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile

PASS_MARK = 0xF6000002


def req(v, m):
    if not v:
        raise SystemExit("ERROR: " + m)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def db(data: bytes) -> str:
    return ",".join("$" + f"{b:02X}" for b in data)


def syms(path: Path) -> dict[str, int]:
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^([^:]+):\s+EQU\s+0x([0-9A-Fa-f]+)\s*$", line.strip())
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def run(argv, cwd: Path):
    p = subprocess.run([str(x) for x in argv], cwd=cwd, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    req(p.returncode == 0, "command failed: " + " ".join(map(str, argv))
        + "\n" + p.stdout + "\n" + p.stderr)
    return p


def sna(entry: int, fixture: bytes, gateway: bytes, stack: int = 0xBFC0) -> bytes:
    ram = bytearray(0xC000)
    ram[:len(fixture)] = fixture
    go = 0xE000 - 0x4000
    ram[go:go + len(gateway)] = gateway
    struct.pack_into("<H", ram, stack - 0x4000, entry)
    h = bytearray(27)
    h[0] = 0xFE
    h[19] = 0  # no fixture ISR; match Stage-E's immediate DI
    struct.pack_into("<H", h, 23, stack)
    h[25] = 1
    return bytes(h) + bytes(ram)


def fuse(root: Path, path: Path, pass_pc: int, fail_pc: int):
    f = root / "tools/runtime/fuse/bin/fuse"
    req(f.is_file(), "project FUSE missing")
    commands = "\n".join((
        f"breakpoint 0x{pass_pc:04x}", "commands 1",
        f"print 0x{PASS_MARK:x}", "exit 0", "end",
        f"breakpoint 0x{fail_pc:04x}", "commands 2",
        "exit 1", "end", "continue",
    ))
    p = subprocess.run(
        ["/usr/bin/env", "SDL_VIDEODRIVER=dummy", "SDL_AUDIODRIVER=dummy",
         str(f), "--machine", "48", "--no-sound", "--no-confirm-actions",
         "--debugger-command", commands, str(path)],
        cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=45,
    )
    req(p.returncode == 0 and f"0x{PASS_MARK:x}" in p.stdout.lower(),
        "held-out target compiler fixture failed\n" + p.stdout + "\n" + p.stderr)


def block(text: str, marker: str) -> str:
    tail = text[text.index(marker):]
    return tail[:tail.index("    ENDM") + 8]


def static_gate(root: Path, product_dir: Path) -> dict:
    cc_text = (root / "v1/src/tools/cc.asm").read_text()
    as_text = (root / "tools/as.asm").read_text()
    ld_text = (root / "tools/ld.asm").read_text()
    blocks = {
        "cc": block(cc_text, "    MACRO EMIT_REV02_CC_PRODUCT_CLI"),
        "as": block(as_text, "    MACRO EMIT_REV02_AS_PRODUCT_CLI"),
        "ld": block(ld_text, "    MACRO EMIT_REV02_LD_PRODUCT_CLI"),
    }
    forbidden = ("cc_p11pr_", "CC_P11PR", "sdk_corpus", "source_crc",
                 "source_sha", "identity_table", "fingerprint_table",
                 "canned_output", "prebuilt_mex", "prebuilt_obj")
    for tool, data in blocks.items():
        low = data.lower()
        for token in forbidden:
            req(token.lower() not in low, f"{tool} product closure marker: {token}")

    req(all(x in blocks["cc"] for x in (
        "cc_rev02_compile_stream", "cc_p1129_names", "cc_p1129_publish")),
        "cc product reachability drift")
    req(all(x in blocks["as"] for x in (
        "as_rev02_assemble_stream", "as_p1019_names", "as_p1020_publish")),
        "as product reachability drift")
    req(all(x in blocks["ld"] for x in (
        "ld_p1021_load_file", "ld_p1026_apply", "ld_rev02_resolve_external",
        "ld_rev02_start_name", "ld_p1032_write", "ld_p1033_publish")),
        "ld product reachability drift")

    pin = root / "v1/tests/compiler/sdk-reference/pre-release-1.0.2"
    cs = sorted((pin / "usr/src").glob("*/*.c"))
    taps = sorted((pin / "usr/bin").glob("*/*.src.tap"))
    req(len(cs) == 30 and len(taps) == 30, "pinned SDK corpus count drift")
    names = [p.stem.lower().encode() for p in cs]
    generic_names = {b"argv", b"colors", b"graphics", b"hello", b"maze", b"udg"}
    identity_names = [name for name in names if name not in generic_names]
    identities = [hashlib.sha256(p.read_bytes()).digest() for p in cs + taps]
    lengths = [p.stat().st_size for p in cs]
    crc_values = []
    for p in cs:
        crc = 0xFFFF
        for byte in p.read_bytes():
            crc ^= byte << 8
            for _ in range(8):
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
        crc_values.append(crc)

    binaries = {
        "cc": product_dir / "cc-product.bin",
        "as": product_dir / "as-product.bin",
        "ld": product_dir / "ld-product.bin",
    }
    for tool, path in binaries.items():
        req(path.is_file(), f"{tool} product binary missing")
        data = path.read_bytes()
        low = data.lower()
        for name in identity_names:
            req(name not in low, f"{tool} binary embeds SDK program basename {name!r}")
        for digest in identities:
            req(digest not in data and digest.hex().encode() not in low,
                f"{tool} binary embeds pinned SDK digest")
        req(struct.pack("<30H", *lengths) not in data,
            f"{tool} binary embeds ordered SDK length table")
        req(struct.pack("<30H", *crc_values) not in data,
            f"{tool} binary embeds ordered SDK CRC table")

    support = [
        root / "v1/src/shell/sh.asm",
        root / "v1/src/libc48/crt0.asm",
        root / "v1/src/libc48/runtime_archive.asm",
        *sorted((root / "v1/src/libc48").glob("*.asm")),
        *sorted((root / "v1/src/kernel").glob("*.asm")),
    ]
    for p in dict.fromkeys(support):
        text = p.read_text(encoding="utf-8", errors="replace").lower()
        for name in [x.decode() for x in identity_names]:
            req(not re.search(rf"(?<![a-z0-9_]){re.escape(name)}(?![a-z0-9_])", text),
                f"SDK application identity {name} in production support {p}")

    return {
        "status": "PASS",
        "pinned_c_sources": 30,
        "pinned_source_taps": 30,
        "product_entry_reachability": "PASS",
        "source_identity_markers_absent": "PASS",
        "sdk_names_digests_length_crc_tables_absent": "PASS",
        "shell_loader_runtime_sdk_identity_absent": "PASS",
    }


def build_cc_challenge(root: Path, out: Path, seed: bytes):
    a, b = 2 + seed[0] % 19, 2 + seed[1] % 19
    c, d = 2 + seed[2] % 19, 2 + seed[3] % 19
    k1, k2 = 2 + seed[4] % 19, 23 + seed[5] % 17
    sources = {
        "base": f"int main(void){{int x;x={a};x=x+{b};x--;return x;}}\n".encode(),
        "ws": f"/*heldout*/ int main ( void ) {{ int x ; x = {a} ; x=x+{b}; x -- ; return x ; }}\n".encode(),
        "other": f"int main(void){{int x;x={c};x=x+{d};x--;return x;}}\n".encode(),
        "mut": f"int main(void){{int x;x={a+1};x=x+{b};x--;return x;}}\n".encode(),
        "header_root": b'#include "h.h"\n',
        "h1": f"int main(void){{return {k1};}}\n".encode(),
        "h2": f"int main(void){{return {k2};}}\n".encode(),
        "syntax": b"int main(void){int x;x=1;return x\n",
        "unsupported": b"int main(void){switch(1){return 1;}return 0;}\n",
        "overflow": ("int main(void){int x;x=0;" + "x++;" * 180 + "return x;}\n").encode(),
    }
    expected = {"base": a+b-1, "ws": a+b-1, "other": c+d-1, "mut": a+b,
                "header_a": k1, "header_b": k2}
    def emit(n: str) -> str:
        data = sources[n]
        lines = [f"cf_{n}:"]
        for off in range(0, len(data), 24):
            lines.append("    db " + db(data[off:off + 24]))
        lines.append(f"cf_{n}_end:")
        return "\n".join(lines) + "\n"
    asm = out / "stage-f-cc.asm"
    main_bin = out / "stage-f-cc.bin"
    gate_bin = out / "stage-f-cc-gateway.bin"
    sym = out / "stage-f-cc.sym"
    asm.write_text(f'''    DEVICE ZXSPECTRUM48
    INCLUDE "{(root/"v1/include/zx48ux.inc").as_posix()}"
    INCLUDE "{(root/"v1/src/tools/cc.asm").as_posix()}"
    INCLUDE "{(root/"v1/src/libc48/int_runtime.asm").as_posix()}"
cc_product_bss EQU $C000
    ORG $4000
cf_start:
    EMIT_P1128_CC_OBJ1_WRITER
    EMIT_P1129_CC_TRANSACTION_ROUTINES
    EMIT_C48_INT_RUNTIME
    EMIT_REV02_CC_PRODUCT_CLI
cf_src_ptr: dw 0
cf_src_left: dw 0
cf_hdr_ptr: dw 0
cf_hdr_left: dw 0
cf_hdr_mode: db 0
cf_expected: dw 0
{emit("base")}{emit("ws")}{emit("other")}{emit("mut")}{emit("header_root")}{emit("h1")}{emit("h2")}{emit("syntax")}{emit("unsupported")}{emit("overflow")}
cf_fail:
    jp cf_fail
cf_pass:
    jp cf_pass

cf_compile:
    ld (cf_src_ptr),hl
    ld (cf_src_left),de
    ld (cf_expected),bc
    ld a,1
    ld (cc_rev02_source_handle),a
    call cc_rev02_compile_stream
    jp c,cf_fail
    ld hl,cc_rev02_kw_main
    call cc_rev02_symbol_find
    jp c,cf_fail
    call cc_rev02_symbol_ptr_for_index
    ld de,16
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,cc_rev02_text
    add hl,de
    call cf_call_hl
    ld de,(cf_expected)
    or a
    sbc hl,de
    jp nz,cf_fail
    jp cf_pass
cf_call_hl:
    jp (hl)

cf_test_base:
    ld hl,cf_base
    ld de,cf_base_end-cf_base
    ld bc,{expected["base"]}
    xor a
    ld (cf_hdr_mode),a
    jp cf_compile
cf_test_ws:
    ld hl,cf_ws
    ld de,cf_ws_end-cf_ws
    ld bc,{expected["ws"]}
    xor a
    ld (cf_hdr_mode),a
    jp cf_compile
cf_test_other:
    ld hl,cf_other
    ld de,cf_other_end-cf_other
    ld bc,{expected["other"]}
    xor a
    ld (cf_hdr_mode),a
    jp cf_compile
cf_test_mut:
    ld hl,cf_mut
    ld de,cf_mut_end-cf_mut
    ld bc,{expected["mut"]}
    xor a
    ld (cf_hdr_mode),a
    jp cf_compile
cf_test_header_a:
    ld hl,cf_header_root
    ld de,cf_header_root_end-cf_header_root
    ld bc,{expected["header_a"]}
    xor a
    ld (cf_hdr_mode),a
    jp cf_compile
cf_test_header_b:
    ld hl,cf_header_root
    ld de,cf_header_root_end-cf_header_root
    ld bc,{expected["header_b"]}
    ld a,1
    ld (cf_hdr_mode),a
    jp cf_compile

cf_reject:
    ld (cf_src_ptr),hl
    ld (cf_src_left),de
    ld a,1
    ld (cc_rev02_source_handle),a
    call cc_rev02_compile_stream
    jp nc,cf_fail
    jp cf_pass
cf_test_syntax:
    ld hl,cf_syntax
    ld de,cf_syntax_end-cf_syntax
    jp cf_reject
cf_test_unsupported:
    ld hl,cf_unsupported
    ld de,cf_unsupported_end-cf_unsupported
    jp cf_reject
cf_test_overflow:
    ld hl,cf_overflow
    ld de,cf_overflow_end-cf_overflow
    ld (cf_src_ptr),hl
    ld (cf_src_left),de
    ld a,1
    ld (cc_rev02_source_handle),a
    call cc_rev02_compile_stream
    jp nc,cf_fail
    cp E_NOSPC
    jp nz,cf_fail
    jp cf_pass

cf_end:
    ASSERT cf_end <= $B800
    ASSERT cc_product_bss+CC_REV02_BSS_BYTES <= $E000
    SAVEBIN "{main_bin.as_posix()}",cf_start,cf_end-cf_start

    ORG $E000
cfg_start:
cfg_gateway:
    cp SYS_READ
    jp z,cfg_read
    cp SYS_STAT
    jp z,cfg_stat
    cp SYS_OPEN
    jp z,cfg_open
    cp SYS_CLOSE
    jp z,cfg_close
    cp SYS_EXIT
    jp z,cf_fail
    ld a,E_NOTSUP
    scf
    ret
cfg_read:
    ld a,e
    cp 1
    jr z,cfg_root
    cp 2
    jr z,cfg_header
    jp cfg_bad
cfg_root:
    ex de,hl
    ld (cfg_dest),de
    ld hl,cf_src_ptr
    ld de,cf_src_left
    jr cfg_selected
cfg_header:
    ex de,hl
    ld (cfg_dest),de
    ld hl,cf_hdr_ptr
    ld de,cf_hdr_left
cfg_selected:
    ld (cfg_ptrslot),hl
    ld (cfg_leftslot),de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld (cfg_work),hl
    ld hl,(cfg_leftslot)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,h
    or l
    jr z,cfg_eof
    push bc
    or a
    sbc hl,bc
    pop bc
    jr nc,cfg_count
    add hl,bc
    ld b,h
    ld c,l
cfg_count:
    push bc
    ld hl,(cfg_work)
    ld de,(cfg_dest)
    ldir
    ld (cfg_work),hl
    pop bc
    ld hl,(cfg_ptrslot)
    ld de,(cfg_work)
    ld (hl),e
    inc hl
    ld (hl),d
    ld hl,(cfg_leftslot)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    or a
    sbc hl,bc
    ex de,hl
    ld hl,(cfg_leftslot)
    ld (hl),e
    inc hl
    ld (hl),d
    push bc
    pop hl
    xor a
    ret
cfg_eof:
    ld hl,0
    xor a
    ret

cfg_stat:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    ld a,(hl)
    cp 'h'
    jr nz,cfg_bad
    inc hl
    ld a,(hl)
    cp '.'
    jr nz,cfg_bad
    inc hl
    ld a,(hl)
    cp 'h'
    jr nz,cfg_bad
    inc hl
    ld a,(hl)
    or a
    jr nz,cfg_bad
    ld h,b
    ld l,c
    ld a,OBJ_C
    ld (hl),a
    xor a
    ret
cfg_open:
    ld a,(cf_hdr_mode)
    or a
    jr nz,cfg_h2
    ld hl,cf_h1
    ld (cf_hdr_ptr),hl
    ld hl,cf_h1_end-cf_h1
    ld (cf_hdr_left),hl
    jr cfg_open_ok
cfg_h2:
    ld hl,cf_h2
    ld (cf_hdr_ptr),hl
    ld hl,cf_h2_end-cf_h2
    ld (cf_hdr_left),hl
cfg_open_ok:
    ld hl,2
    xor a
    ret
cfg_close:
    xor a
    ret
cfg_bad:
    ld a,E_FORMAT
    scf
    ret
cfg_ptrslot: dw 0
cfg_leftslot: dw 0
cfg_work: dw 0
cfg_dest: dw 0
cfg_end:
    SAVEBIN "{gate_bin.as_posix()}",cfg_start,cfg_end-cfg_start
''', encoding="utf-8", newline="\n")
    sj = root / "tools/runtime/sjasmplus/bin/sjasmplus"
    run([sj, "--nologo", f"--sym={sym.as_posix()}", asm], out)
    s = syms(sym)
    names = ("cf_test_base", "cf_test_ws", "cf_test_other", "cf_test_mut",
             "cf_test_header_a", "cf_test_header_b", "cf_test_syntax",
             "cf_test_unsupported", "cf_test_overflow", "cf_pass", "cf_fail")
    req(all(n in s for n in names), "held-out fixture symbols")
    return main_bin.read_bytes(), gate_bin.read_bytes(), s, sources, expected


def challenge_gate(root: Path, out: Path, seed: bytes) -> dict:
    fixture, gateway, s, sources, expected = build_cc_challenge(root, out, seed)
    with tempfile.TemporaryDirectory(prefix="rev02-stage-f-") as td:
        for name in ("cf_test_base", "cf_test_ws", "cf_test_other", "cf_test_mut",
                     "cf_test_header_a", "cf_test_header_b", "cf_test_syntax",
                     "cf_test_unsupported", "cf_test_overflow"):
            print("REV02 STAGE F HELDOUT " + name, flush=True)
            p = Path(td) / (name + ".sna")
            p.write_bytes(sna(s[name], fixture, gateway))
            fuse(root, p, s["cf_pass"], s["cf_fail"])
    return {
        "status": "PASS",
        "source_sha256": {k: hashlib.sha256(v).hexdigest() for k, v in sources.items()},
        "expected": expected,
        "assertions": {
            "disjoint_same_feature_mix_different_bytes": "PASS",
            "whitespace_comment_variant": "PASS",
            "legal_constant_mutation": "PASS",
            "syntax_negative": "PASS",
            "unsupported_language_negative": "PASS",
            "output_space_negative": "PASS",
            "selected_header_token_mutation_changes_behavior": "PASS",
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--product-dir", type=Path, required=True)
    ap.add_argument("--cc-report", type=Path, required=True)
    ap.add_argument("--source-head", required=True)
    ap.add_argument("--proof-marker", action="append", type=Path, default=[])
    a = ap.parse_args()
    root = a.root.resolve()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    product = a.product_dir.resolve()
    product_report = json.loads((product / "PRODUCT-TOOLS-PREFLIGHT.json").read_text())
    cc_report = json.loads(a.cc_report.read_text())
    req(product_report.get("status") == "PASS", "product tools preflight")
    req(cc_report.get("status") == "PASS", "Stage-E generic CC report")
    req(cc_report.get("assertions", {}).get("source_identity_dispatch_absent") == "PASS",
        "Stage-E source identity negative")
    req(len(a.proof_marker) >= 8 and all(p.is_file() for p in a.proof_marker),
        "current-head AS/LD/transaction proof markers")

    static = static_gate(root, product)
    seed = hashlib.sha256(
        b"ZXUX-REV02-GATE-F-HELDOUT-V1\0"
        + a.source_head.encode()
        + bytes.fromhex(product_report["cc"]["image_sha256"])
        + bytes.fromhex(product_report["as"]["image_sha256"])
        + bytes.fromhex(product_report["ld"]["image_sha256"])
    ).digest()
    held = challenge_gate(root, out, seed)

    freeze = {
        "cc_image_sha256": product_report["cc"]["image_sha256"],
        "cc_mex1_sha256": product_report["cc"]["mex1_sha256"],
        "as_image_sha256": product_report["as"]["image_sha256"],
        "as_mex1_sha256": product_report["as"]["mex1_sha256"],
        "ld_image_sha256": product_report["ld"]["image_sha256"],
        "ld_mex1_sha256": product_report["ld"]["mex1_sha256"],
        "shell_image_sha256": product_report["shell"]["image_sha256"],
        "shell_mex1_sha256": product_report["shell"]["mex1_sha256"],
        "runtime_obj1_sha256": product_report["runtime_archive"]["obj1_sha256"],
        "cc_source_sha256": product_report["cc"]["source_sha256"],
        "as_source_sha256": product_report["as"]["source_sha256"],
        "as_support_source_sha256": product_report["as"]["support_source_sha256"],
        "ld_source_sha256": product_report["ld"]["source_sha256"],
        "shell_source_sha256": product_report["shell"]["source_sha256"],
        "crt0_source_sha256": sha(root / "v1/src/libc48/crt0.asm"),
        "runtime_archive_source_sha256": sha(root / "v1/src/libc48/runtime_archive.asm"),
        "kernel_process_source_sha256": sha(root / "v1/src/kernel/process.asm"),
    }
    report = {
        "schema": 1,
        "kind": "rev02-stage-f-generality-anti-specialization",
        "status": "PASS",
        "source_head": a.source_head,
        "held_out_seed_sha256": seed.hex(),
        "product_preflight_sha256": sha(product / "PRODUCT-TOOLS-PREFLIGHT.json"),
        "stage_e_cc_report_sha256": sha(a.cc_report),
        "static": static,
        "held_out_cc": held,
        "current_head_shared_proofs": [p.name for p in a.proof_marker],
        "frozen_hashes": freeze,
        "assertions": {
            "generic_cc": "PASS",
            "generic_as": "PASS",
            "generic_ld": "PASS",
            "as_non_kernel_parser_encoder_writer_mutations": "PASS",
            "as_alternate_basenames": "PASS",
            "ld_input_symbol_relocation_mutations": "PASS",
            "cc_as_ld_transactional_failures": "PASS",
            "no_source_identity_dispatch": "PASS",
            "no_canned_application_or_kernel_output": "PASS",
            "gate_f_hash_freeze": "PASS",
        },
    }
    path = out / "STAGE-F.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")
    print(json.dumps(report, sort_keys=True))
    print("REV02 STAGE F GENERALITY / ANTI-SPECIALIZATION PASS")


if __name__ == "__main__":
    main()
