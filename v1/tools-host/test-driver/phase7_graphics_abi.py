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

from pathlib import Path
from typing import Any, Callable

from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
import phase1
import phase3_open_descriptions

MODULE = 0xC000
DATA = 0xA000


class P701Error(DriverError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise P701Error(message)


def _word(value: int) -> bytes:
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def _setb(address: int, value: int) -> bytes:
    return bytes((0x3E, value & 0xFF, 0x32)) + _word(address)


def _expectb(address: int, value: int) -> bytes:
    return b"\x3a" + _word(address) + bytes((0xFE, value & 0xFF)) + phase1._jp_nz(FAIL_PC)


def _jp_nc(address: int) -> bytes:
    return b"\xd2" + _word(address)


def _source_contract(root: Path) -> list[dict[str, object]]:
    inc = (root / "v1/include/zx48ux.inc").read_text(encoding="utf-8")
    syscall = (root / "v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    gfx = (root / "v1/src/kernel/graphics.asm").read_text(encoding="utf-8")
    plan = (root / "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    values = tuple(f"SYS_GFX_{name}" for name in ("PLOT","DRAW","CIRCLE","ATTR","BORDER","POINT"))
    labels = tuple(f"zx48_gfx_{name}:" for name in ("plot","draw","circle","attr","border","point"))
    return [
        {"name":"canonical-p701-present","passed":"## P7.01 - Graphics syscall ABI" in plan},
        {"name":"six-public-gfx-selectors-present","passed":all(x in inc for x in values)},
        {"name":"graphics-source-included-once","passed":syscall.count('INCLUDE "graphics.asm"')==1},
        {"name":"bounded-p701-dispatch-range","passed":all(x in syscall for x in ("zx48_p701_gfx_dispatch:","cp SYS_GFX_PLOT","cp SYS_GFX_POINT+1","sub SYS_GFX_PLOT"))},
        {"name":"record-pointers-validated-before-draw-circle","passed":"ld bc,4\n    call zx48_user_range_validate" in syscall and "ld bc,3\n    call zx48_user_range_validate" in syscall},
        {"name":"six-native-entrypoints-present","passed":all(x in gfx for x in labels)},
        {"name":"bad-parameter-path-before-plot-mutation","passed":"cp 192\n    jr nc,zx48_gfx_bad\n    call zx48_cursor_hide" in gfx},
        {"name":"public-gateway-retains-canonical-iy-contract","passed":"ld iy,ROM_IY_ANCHOR" in syscall},
        {"name":"phase6-resident-dispatch-left-byte-identical-in-shape","passed":"cp SYS_CON_SETPOS+1\n    jr c,zx48_sys_dispatch_console\n    cp SYS_MEM_INFO" in syscall},
    ]


def _assemble(root: Path, run_command: Callable[..., Any], require_project_tool: Callable[[Path, str | Path], Path]):
    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p701-gfx-abi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    ORG $C000
syscall_arg_hl: dw 0
tty_current_attr: db 7
zx48_cursor_hide: ret
zx48_cursor_show: ret
zx48_ula_set_border:
    ld (p701_border),a
    xor a
    ret
p701_border: db 0
zx48_bitmap_address:
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
    INCLUDE "../src/kernel/syscall.asm"
    EMIT_USER_RANGE_VALIDATION_ROUTINE
    EMIT_GRAPHICS_ROUTINES
    EMIT_P701_GRAPHICS_SYSCALL_ROUTINES
    SAVEBIN "p701-gfx-abi.bin",$C000,$-$C000
""",encoding="utf-8",newline="\n")
    result=run_command([assembler,"--nologo","--lst=p701-gfx-abi.lst","--sym=p701-gfx-abi.sym","p701-gfx-abi.asm"],cwd=build,timeout_seconds=30.0)
    require(not result.timed_out and result.exit_code==0,f"P7.01 fixture assembly failed: {result.stderr or result.stdout}")
    binary=build/"p701-gfx-abi.bin"; listing=build/"p701-gfx-abi.lst"
    require(binary.is_file() and 0<binary.stat().st_size<4096,"P7.01 fixture missing/oversize")
    return result,binary,listing


def _runtime(root: Path, s: dict[str,int], module: bytes) -> None:
    def patch(ram: bytearray) -> None:
        off=MODULE-0x4000
        ram[off:off+len(module)]=module
    code=bytearray(b"\xf3"+phase1._ld_sp(0xBFC0))
    def call(selector: int, hl: int) -> bytes:
        return phase1._ld_hl(hl)+b"\x22"+_word(s["syscall_arg_hl"])+bytes((0x3E,selector))+phase1._call(s["zx48_p701_gfx_dispatch"])
    code+=_setb(0x4000,0)+call(0x40,0x0000)+phase1._jp_c(FAIL_PC)+_expectb(0x4000,0x80)
    code+=_setb(0x4000,0x5A)+call(0x40,0x00C0)+_jp_nc(FAIL_PC)+_expectb(0x4000,0x5A)
    code+=_setb(0x4000,0x80)+call(0x45,0x0000)+phase1._jp_c(FAIL_PC)+b"\x7c\xb7"+phase1._jp_nz(FAIL_PC)+b"\x7d\xfe\x01"+phase1._jp_nz(FAIL_PC)+_expectb(0x4000,0x80)
    code+=call(0x43,0x0003)+phase1._jp_c(FAIL_PC)+_expectb(s["gfx_attr_state"],3)
    code+=call(0x43,0x0600)+_jp_nc(FAIL_PC)+_expectb(s["gfx_attr_state"],3)
    code+=call(0x41,0x5AFE)+_jp_nc(FAIL_PC)
    for off,value in enumerate((1,1,3,1)): code+=_setb(DATA+off,value)
    code+=call(0x41,DATA)+phase1._jp_c(FAIL_PC)
    for off,value in enumerate((10,10,0)): code+=_setb(DATA+8+off,value)
    code+=call(0x42,DATA+8)+phase1._jp_c(FAIL_PC)
    code+=call(0x44,0x0002)+phase1._jp_c(FAIL_PC)+_expectb(s["p701_border"],2)
    code+=call(0x44,0x0100)+_jp_nc(FAIL_PC)+_expectb(s["p701_border"],2)
    code+=phase1._jp(PASS_PC)
    run_sna(root,bytes(code),patch=patch)


def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P7.01": raise P701Error(f"unsupported {step} {action}")
    assertions=_source_contract(root)
    failed=[x["name"] for x in assertions if x.get("passed") is not True]
    require(not failed,f"P7.01 static contract failure: {failed}")
    kernel_command,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    fixture_command,binary,listing=_assemble(root,run_command,require_project_tool)
    commands=[kernel_command,fixture_command]
    names=("zx48_p701_gfx_dispatch","syscall_arg_hl","gfx_attr_state","p701_border")
    symbols=phase3_open_descriptions._symbols(listing.with_suffix(".sym"),names)
    if action=="test":
        _runtime(root,symbols,binary.read_bytes())
        assertions += [
            {"name":"fuse-six-selector-dispatch-smoke-pass","passed":True},
            {"name":"bad-user-parameters-before-screen-ula-mutation","passed":True},
            {"name":"phase6-resident-kernel-still-fits-exact-8k","passed":kernel.stat().st_size==8192},
        ]
    hashes={
        "docs/01-ZX-UX-ARCHITECTURE-REV16.md":sha256_file(root/"docs/01-ZX-UX-ARCHITECTURE-REV16.md"),
        "docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md":sha256_file(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md"),
        "v1/src/kernel/graphics.asm":sha256_file(root/"v1/src/kernel/graphics.asm"),
        "v1/src/kernel/syscall.asm":sha256_file(root/"v1/src/kernel/syscall.asm"),
        "v1/build/kernel.bin":sha256_file(kernel),
        "v1/build/p701-gfx-abi.bin":sha256_file(binary),
        "v1/tools-host/test-driver/phase7_graphics_abi.py":sha256_file(root/"v1/tools-host/test-driver/phase7_graphics_abi.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
    }
    return commands,hashes,assertions
