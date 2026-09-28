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

"""Run all 30 tape-built native SDK executables through the admitted spawn path."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / "v1/tools-host/test-driver"
sys.path.insert(0, str(DRIVER))

from fuse_harness import FAIL_PC, PASS_PC, run_sna  # noqa: E402
import phase2_spawn_atomic as p210  # noqa: E402
import phase2_spawn_exit_leak as p222  # noqa: E402
import sdk_acquire as sdk  # noqa: E402

FIXTURE = 0xE000
PROGRAM = 0x9000
TEST_STACK = 0x8F00
PROC = 0xA300
PATH = 0xA000
ARG = 0xA100
ENV = 0xA200
RECORD = 0xB000
MEX = 0xC000
PROC_DESC_SIZE = 48
PROC_STATE = 2
PROC_READY = 1
FREE_EXTENT_BYTES = 64


class Error(RuntimeError):
    pass


def req(value: object, message: str) -> None:
    if not value:
        raise Error(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def word(value: int) -> bytes:
    return struct.pack("<H", value & 0xFFFF)


def call(address: int) -> bytes:
    return b"\xCD" + word(address)


def jp_c(address: int) -> bytes:
    return b"\xDA" + word(address)


def jp_nz(address: int) -> bytes:
    return b"\xC2" + word(address)


def symbols(path: Path, names: tuple[str, ...]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, int] = {}
    for name in names:
        match = re.search(
            rf"^{re.escape(name)}:\s+equ\s+0x([0-9a-f]+)\s*$",
            text,
            re.I | re.M,
        )
        req(match, f"fixture symbol missing: {name}")
        out[name] = int(match.group(1), 16)
    return out


def build_fixture() -> tuple[bytes, dict[str, int]]:
    build = ROOT / "v1/build"
    build.mkdir(parents=True, exist_ok=True)
    source = build / "p11pr-sdk-process.asm"
    binary = build / "p11pr-sdk-process.bin"
    sym = build / "p11pr-sdk-process.sym"
    source.write_text(
        f"""    DEVICE ZXSPECTRUM48
PANIC_SCHEDULER EQU $03
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../include/mex1.inc"
    INCLUDE "../src/kernel/syscall.asm"
    INCLUDE "../src/kernel/memory.asm"
    INCLUDE "../src/kernel/process.asm"
    INCLUDE "../src/kernel/handles.asm"
    INCLUDE "../src/kernel/objects.asm"

P11PR_RECORD EQU $B000
    ORG $E000
p11pr_gateway:
    ld (syscall_arg_hl),hl
    ld (p11pr_arg_bc),bc
    cp SYS_SPAWN
    jp z,zx48_sys_spawn
    cp SYS_CON_CLEAR
    jp z,p11pr_con_clear
    cp SYS_CON_SETPOS
    jp z,p11pr_con_setpos
    cp SYS_CON_WRITE
    jp z,p11pr_con_write
    cp SYS_GFX_PLOT
    jp z,p11pr_gfx_plot
    cp SYS_EXIT
    jr z,p11pr_exit
    ld a,E_NOTSUP
    scf
    ret

p11pr_exit:
    ld a,(current_pid)
    cp 2
    jp nz,${FAIL_PC:04X}
    ld ix,process_table+2*PROC_DESC_SIZE
    ld a,(ix+PROC_STATE)
    cp PROC_RUNNING
    jp nz,${FAIL_PC:04X}
    ld a,(ix+PROC_PRIVATE_FLAGS)
    and PROC_PRIVATE_STARTED
    jp z,${FAIL_PC:04X}
    ld a,1
    ld (p11pr_exit_seen),a
    ; Hold the completed target screen for three nominal PAL frames before the
    ; debugger PASS trap.  FMF commits display state at frame boundaries; without
    ; this deterministic settle the program can clear, draw, exit, and stop Fuse
    ; within one frame, leaving only the pre-run blank frame in the retained movie.
    ld bc,$2000
p11pr_exit_frame_settle:
    dec bc
    ld a,b
    or c
    jr nz,p11pr_exit_frame_settle
    jp ${PASS_PC:04X}

p11pr_start:
    EMIT_MEMORY_ROUTINES
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_PROCESS_CAPACITY_ROUTINE
    EMIT_MEX1_RELOCATION_ROUTINES
    EMIT_ARG1_ROUTINES
    EMIT_ENV1_ROUTINES
    EMIT_INITIAL_CONTEXT_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_PARENT_CHILD_ROUTINES
    EMIT_SPAWN_PREFLIGHT_ROUTINES
    EMIT_SPAWN_TRANSACTION_ROUTINES

p11pr_run_child:
    ld ix,process_table+2*PROC_DESC_SIZE
    ld a,(ix+PROC_STATE)
    cp PROC_READY
    jp nz,${FAIL_PC:04X}
    ld a,2
    ld (current_pid),a
    ld a,PROC_RUNNING
    ld (ix+PROC_STATE),a
    ld a,(ix+PROC_PRIVATE_FLAGS)
    or PROC_PRIVATE_STARTED
    ld (ix+PROC_PRIVATE_FLAGS),a
    ld l,(ix+PROC_SAVED_SP)
    ld h,(ix+PROC_SAVED_SP+1)
    ld sp,hl
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ld iy,ROM_IY_ANCHOR
    ret

; Minimal exact ABI-visible console/plot subset used only by the pre-release
; visual proof child.  The executable still enters through the admitted spawn
; transaction above; these target-side handlers publish the child's real screen
; writes into Spectrum display RAM before SYS_EXIT is observed.
P11PR_FONT_ADDR EQU $D000

p11pr_con_clear:
    xor a
    ld hl,$4000
    ld de,$4001
    ld bc,6143
    ld (hl),a
    ldir
    ld hl,$5800
    ld de,$5801
    ld bc,767
    ld a,7
    ld (hl),a
    ldir
    xor a
    ld (p11pr_vis_row),a
    ld (p11pr_vis_col),a
    ld hl,0
    or a
    ret

p11pr_con_setpos:
    ld hl,(syscall_arg_hl)
    ld a,h
    cp 24
    jp nc,p11pr_vis_bad
    ld a,l
    cp 64
    jp nc,p11pr_vis_bad
    ld a,h
    ld (p11pr_vis_row),a
    ld a,l
    ld (p11pr_vis_col),a
    ld hl,0
    xor a
    ret

p11pr_con_write:
    ld hl,(syscall_arg_hl)
    ld bc,(p11pr_arg_bc)
    ld (p11pr_vis_count),bc
p11pr_vis_write_loop:
    ld a,b
    or c
    jr z,p11pr_vis_write_done
    ld a,(hl)
    push hl
    push bc
    call p11pr_vis_putchar
    pop bc
    pop hl
    ret c
    inc hl
    dec bc
    jr p11pr_vis_write_loop
p11pr_vis_write_done:
    ld hl,(p11pr_vis_count)
    xor a
    ret

p11pr_vis_putchar:
    cp $20
    jp c,p11pr_vis_bad
    cp $80
    jp nc,p11pr_vis_bad
    sub $20
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld de,P11PR_FONT_ADDR+8
    add hl,de
    ld (p11pr_vis_glyph),hl
    xor a
    ld (p11pr_vis_scan),a
p11pr_vis_scan_loop:
    ld a,(p11pr_vis_scan)
    cp 8
    jr nc,p11pr_vis_attr
    ld e,a
    srl e
    ld d,0
    ld hl,(p11pr_vis_glyph)
    add hl,de
    ld a,(hl)
    ld d,a
    ld a,(p11pr_vis_scan)
    and 1
    ld a,d
    jr nz,p11pr_vis_nibble
    rrca
    rrca
    rrca
    rrca
p11pr_vis_nibble:
    and $0f
    ld d,a
    ld a,(p11pr_vis_row)
    add a,a
    add a,a
    add a,a
    ld b,a
    ld a,(p11pr_vis_scan)
    add a,b
    ld b,a
    ld a,(p11pr_vis_col)
    srl a
    ld c,a
    call p11pr_bitmap_address
    ld a,(p11pr_vis_col)
    and 1
    ld a,(hl)
    jr nz,p11pr_vis_right
    and $0f
    ld e,a
    ld a,d
    rlca
    rlca
    rlca
    rlca
    or e
    ld (hl),a
    jr p11pr_vis_next
p11pr_vis_right:
    and $f0
    or d
    ld (hl),a
p11pr_vis_next:
    ld a,(p11pr_vis_scan)
    inc a
    ld (p11pr_vis_scan),a
    jr p11pr_vis_scan_loop
p11pr_vis_attr:
    ld a,(p11pr_vis_row)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld a,(p11pr_vis_col)
    srl a
    ld e,a
    ld d,0
    add hl,de
    ld de,$5800
    add hl,de
    ld (hl),7
    ld a,(p11pr_vis_col)
    inc a
    cp 64
    jp nc,p11pr_vis_bad
    ld (p11pr_vis_col),a
    xor a
    ret

p11pr_gfx_plot:
    ld hl,(syscall_arg_hl)
    ld a,l
    cp 192
    jp nc,p11pr_vis_bad
    ld (p11pr_vis_xy),hl
    ld b,l
    ld a,h
    ld c,a
    srl c
    srl c
    srl c
    call p11pr_bitmap_address
    ld de,(p11pr_vis_xy)
    ld a,d
    and 7
    ld c,a
    ld a,$80
p11pr_vis_mask_loop:
    ld b,c
    ld c,a
    ld a,b
    or a
    ld a,c
    jr z,p11pr_vis_mask_done
    srl a
    dec b
    ld c,b
    jr p11pr_vis_mask_loop
p11pr_vis_mask_done:
    or (hl)
    ld (hl),a
    ld de,(p11pr_vis_xy)
    ld a,e
    and $f8
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld a,d
    srl a
    srl a
    srl a
    ld e,a
    ld d,0
    add hl,de
    ld de,$5800
    add hl,de
    ld (hl),7
    ld hl,0
    xor a
    ret

p11pr_bitmap_address:
    ld a,b
    and 7
    or $40
    ld h,a
    ld a,b
    and $c0
    rrca
    rrca
    rrca
    or h
    ld h,a
    ld a,b
    and $38
    rlca
    rlca
    or c
    ld l,a
    ret

p11pr_vis_bad:
    ld a,E_INVAL
    scf
    ret

p11pr_arg_bc: dw 0
p11pr_vis_row: db 0
p11pr_vis_col: db 0
p11pr_vis_scan: db 0
p11pr_vis_glyph: dw 0
p11pr_vis_count: dw 0
p11pr_vis_xy: dw 0

zx48_process_lookup:
    cp MAX_PROCESSES
    jr nc,p11pr_noent
    ld ix,process_table
    or a
    jr z,p11pr_have_process
    ld b,a
    ld de,PROC_DESC_SIZE
p11pr_process_loop:
    add ix,de
    djnz p11pr_process_loop
p11pr_have_process:
    ld a,(ix+PROC_STATE)
    or a
    jr z,p11pr_noent
    xor a
    ret
p11pr_noent:
    ld a,E_NOENT
    scf
    ret

zx48_process_count:
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_PROCESSES-1
    ld c,0
p11pr_count_loop:
    ld a,(ix+PROC_STATE)
    or a
    jr z,p11pr_count_next
    inc c
p11pr_count_next:
    ld de,PROC_DESC_SIZE
    add ix,de
    djnz p11pr_count_loop
    ld a,c
    or a
    ret

zx48_spawn_resolve_ram_object:
    ld ix,P11PR_RECORD
    xor a
    ret

zx48_pipe_endpoint_closed:
    xor a
    ret

zx48_panic:
    jp ${FAIL_PC:04X}

current_pid: db 0
tty_input_owner: db 0
process_table: defs MAX_PROCESSES*PROC_DESC_SIZE,0
p11pr_exit_seen: db 0
p11pr_end:
    ASSERT p11pr_end <= FAST_RESERVE_START
    SAVEBIN "p11pr-sdk-process.bin",p11pr_gateway,p11pr_end-p11pr_gateway
""",
        encoding="utf-8",
        newline="\n",
    )
    assembler = ROOT / "tools/runtime/sjasmplus/bin/sjasmplus"
    req(assembler.is_file(), "project sjasmplus missing")
    result = subprocess.run(
        [str(assembler), "--nologo", "--sym=p11pr-sdk-process.sym", source.name],
        cwd=build,
        text=True,
        capture_output=True,
        timeout=60,
    )
    req(result.returncode == 0, f"fixture assembly failed:\n{result.stdout}\n{result.stderr}")
    blob = binary.read_bytes()
    req(0 < len(blob) <= 0x1D00, f"fixture size invalid: {len(blob)}")
    sy = symbols(
        sym,
        (
            "p11pr_gateway",
            "p11pr_run_child",
            "zx48_process_links_init",
            "process_table",
            "current_pid",
            "open_description_table",
            "memory_free_extents",
            "memory_live_allocations",
            "tty_input_owner",
            "p11pr_exit_seen",
            "SYS_SPAWN",
        ),
    )
    return blob, sy


def free_extents() -> bytes:
    data = bytearray(FREE_EXTENT_BYTES)
    struct.pack_into("<HH", data, 0, 0x6000, 0x8000)
    return bytes(data)


def patch(fixture: bytes, regions: tuple[tuple[int, bytes], ...]):
    def apply(ram: bytearray) -> None:
        start = FIXTURE - 0x4000
        ram[start : start + len(fixture)] = fixture
        for address, payload in regions:
            req(0x4000 <= address < 0x10000, f"patch address outside RAM: 0x{address:04x}")
            req(address + len(payload) <= 0x10000, f"patch range crosses RAM: 0x{address:04x}")
            off = address - 0x4000
            ram[off : off + len(payload)] = payload
    return apply


def execute_one(
    fixture: bytes,
    sy: dict[str, int],
    exe_name: str,
    mex: bytes,
) -> None:
    path = f"/bin/{exe_name}".encode("ascii")
    arg = p210._arg1(path)
    proc = p210._proc1(
        path_ptr=PATH,
        arg_ptr=ARG,
        arg_len=len(arg),
        env_ptr=ENV,
        env_len=len(p210.ENV1_EMPTY),
    )
    record = p210._record(exe_name.encode("ascii"), 2, MEX, len(mex))
    regions = (
        (PATH, path + b"\0"),
        (ARG, arg),
        (ENV, p210.ENV1_EMPTY),
        (PROC, proc),
        (MEX, mex),
        (RECORD, record),
        (sy["process_table"], p222._process_table()),
        (sy["current_pid"], b"\x01"),
        (sy["open_description_table"], p222._open_descriptions()),
        (sy["memory_free_extents"], free_extents()),
        (sy["memory_live_allocations"], b"\x00\x00"),
        (sy["tty_input_owner"], b"\x01"),
        (sy["p11pr_exit_seen"], b"\x00"),
    )
    code = bytearray(b"\xF3\x31" + word(TEST_STACK))
    code += call(sy["zx48_process_links_init"]) + jp_c(FAIL_PC)
    code += b"\x21" + word(PROC)
    code += bytes((0x3E, sy["SYS_SPAWN"] & 0xFF))
    code += call(sy["p11pr_gateway"]) + jp_c(FAIL_PC)
    code += b"\x7C\xB7" + jp_nz(FAIL_PC)
    code += b"\x7D\xFE\x02" + jp_nz(FAIL_PC)
    child_state = sy["process_table"] + 2 * PROC_DESC_SIZE + PROC_STATE
    code += b"\x3A" + word(child_state) + bytes((0xFE, PROC_READY)) + jp_nz(FAIL_PC)
    code += call(sy["p11pr_run_child"])
    code += b"\xC3" + word(FAIL_PC)
    run_sna(ROOT, bytes(code), patch=patch(fixture, regions), timeout=25.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--native", type=Path, required=True)
    ap.add_argument("--native-report", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    release = json.loads((args.root / "SDK-RELEASE.json").read_text())
    req(
        (release.get("tag"), release.get("commit"), release.get("tree"))
        == (sdk.TAG, sdk.COMMIT, sdk.TREE),
        "SDK identity drift",
    )
    native_report = json.loads(args.native_report.read_text())
    req(native_report.get("program_count") == 30, "native build report program count")
    by_program = {
        (row["category"], row["program"]): row
        for row in native_report.get("programs", [])
    }
    req(len(by_program) == 30, "native build report matrix")

    fixture, sy = build_fixture()
    rows = []
    for category, name in sdk.programs():
        source_name, obj_name, exe_name = sdk.target_names(name)
        prior = by_program[(category, name)]
        req(prior["target_source"] == source_name, f"{category}/{name} source target drift")
        req(prior["target_object"] == obj_name, f"{category}/{name} object target drift")
        req(prior["target_executable"] == exe_name, f"{category}/{name} executable target drift")
        mex_path = args.native / category / exe_name
        mex = mex_path.read_bytes()
        req(sha(mex) == prior["native_mex1_sha256"], f"{category}/{name} native MEX1 drift")
        execute_one(fixture, sy, exe_name, mex)
        rows.append(
            {
                "category": category,
                "program": name,
                "target_executable": exe_name,
                "native_mex1_size": len(mex),
                "native_mex1_sha256": sha(mex),
                "spawn": "PASS",
                "spawned_context_restore": "PASS",
                "process_started": "PASS",
                "sys_exit_reached": "PASS",
            }
        )

    req(len(rows) == 30, "not all 30 native executables ran")
    report = {
        "schema": 1,
        "kind": "phase11-pre-release-sdk-native-process-execution",
        "program_count": 30,
        "fixture_size": len(fixture),
        "programs": rows,
        "assertions": {
            "all_30_executables_are_exact_native_ld_outputs": "PASS",
            "all_30_launch_through_admitted_sys_spawn_transaction": "PASS",
            "all_30_enter_spawn_constructed_initial_context": "PASS",
            "all_30_reach_sys_exit_from_running_process_context": "PASS",
            "no_host_direct_jump_into_application_bytes": "PASS",
            "no_host_preconstructed_obj1_or_mex1": "PASS",
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("P11 PRE-RELEASE SDK NATIVE PROCESS EXECUTION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
