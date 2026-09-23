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

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import FAIL_PC, PASS_PC, run_sna
from phase8_common import inspect_mex, make_tap, mex1, word

BASE=0xC000


class P903Error(DriverError):
    pass


def require(value, message):
    if not value:
        raise P903Error(message)


def expect_byte(address, value):
    return b"\x3A"+word(address)+bytes((0xFE,value&0xFF))+phase1._jp_nz(FAIL_PC)


def expect_word(address, value):
    return expect_byte(address,value&0xFF)+expect_byte(address+1,(value>>8)&0xFF)


def logical_byte(symbols, offset, value):
    return phase1._ld_hl(offset)+phase1._call(symbols["vi_p903_get_byte"])+bytes((0xFE,value&0xFF))+phase1._jp_nz(FAIL_PC)


def patch(image, symbols, data, *, fail_gap=0, fail_index=0, dirty=0):
    def apply(ram):
        ram[BASE-0x4000:BASE-0x4000+len(image)]=image
        buf=symbols["vi_buffer"]-0x4000
        ram[buf:buf+len(data)]=data
        ram[symbols["vi_buffer_len"]-0x4000:symbols["vi_buffer_len"]-0x4000+2]=len(data).to_bytes(2,"little")
        ram[symbols["vi_buffer_ready"]-0x4000]=1
        ram[symbols["vi_fail_gap_alloc"]-0x4000]=fail_gap
        ram[symbols["vi_fail_index_alloc"]-0x4000]=fail_index
        ram[symbols["vi_dirty"]-0x4000]=dirty
    return apply


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step!="P9.03":
        raise DriverError(step)

    source=root/"tools/vi.asm"
    text=source.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"canonical-p903-present","passed":"## P9.03 - Gap buffer and compact line index" in plan},
        {"name":"gap-pair-present","passed":"vi_gap_start: dw 0" in text and "vi_gap_end: dw 0" in text},
        {"name":"compact-u16-line-index","passed":"vi_line_index: defs VI_LINE_MAX*2,0" in text},
        {"name":"staged-index-publish","passed":"vi_line_stage:" in text and "vi_p903_reindex_commit:" in text},
        {"name":"no-second-file-image","passed":text.count("defs VI_LOAD_CAPACITY") == 1},
        {"name":"bounded-undo-record","passed":all(x in text for x in ("vi_undo_kind: db 0","vi_undo_pos: dw 0","vi_undo_byte: db 0"))},
        {"name":"failure-before-gap-motion","passed":text.index("vi_p903_insert_pos_ok:") < text.index("call vi_p903_move_gap",text.index("vi_p903_insert_pos_ok:"))},
    ]
    require(all(x["passed"] for x in assertions),"P9.03 static contract failure")

    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    fixture=build/"p903-vi.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/vi.asm"
    ORG $C000
fixture:
    EMIT_P901_VI_ROUTINES
fixture_end:
    SAVEBIN "p903-vi.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    fr=run_command([assembler,"--nologo","--lst=p903-vi.lst","--sym=p903-vi.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not fr.timed_out and fr.exit_code==0,f"P9.03 assemble: {fr.stderr or fr.stdout}")
    image=(build/"p903-vi.bin").read_bytes()
    require(len(image)<8192,"P9.03 vi image overflow")

    mex_path=build/"p903-vi.mex1"; mex_path.write_bytes(mex1(image))
    try:
        xr=inspect_mex(root,mex_path,run_command,require_project_tool)
        tap=make_tap(root,build,"vi","p903",mex_path)
    except RuntimeError as exc:
        raise P903Error(str(exc)) from exc

    if action=="test":
        names=(
            "vi_p903_init","vi_p903_insert_byte","vi_p903_delete_byte","vi_p903_get_byte",
            "vi_buffer","vi_buffer_len","vi_buffer_ready","vi_gap_start","vi_gap_end",
            "vi_line_count","vi_line_index","vi_fail_gap_alloc","vi_fail_index_alloc",
            "vi_dirty","vi_undo_kind","vi_undo_pos","vi_undo_byte","E_NOMEM",
        )
        sy=phase3_open_descriptions._symbols(build/"p903-vi.sym",names)
        initial=b"ab\ncd"

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=expect_word(sy["vi_gap_start"],5)+expect_word(sy["vi_gap_end"],1024)
        code+=expect_byte(sy["vi_line_count"],2)+expect_word(sy["vi_line_index"],0)+expect_word(sy["vi_line_index"]+2,3)
        for i,v in enumerate(initial): code+=logical_byte(sy,i,v)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,sy,initial))

        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
        code+=phase1._ld_hl(2)+b"\x3E\x0A"+phase1._call(sy["vi_p903_insert_byte"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_buffer_len"],6)+expect_byte(sy["vi_line_count"],3)
        code+=expect_word(sy["vi_line_index"],0)+expect_word(sy["vi_line_index"]+2,3)+expect_word(sy["vi_line_index"]+4,4)
        for i,v in enumerate(b"ab\n\ncd"): code+=logical_byte(sy,i,v)
        code+=expect_byte(sy["vi_dirty"],1)+expect_byte(sy["vi_undo_kind"],1)+expect_word(sy["vi_undo_pos"],2)+expect_byte(sy["vi_undo_byte"],10)
        code+=phase1._ld_hl(2)+phase1._call(sy["vi_p903_delete_byte"])+phase1._jp_c(FAIL_PC)
        code+=expect_word(sy["vi_buffer_len"],5)+expect_byte(sy["vi_line_count"],2)
        for i,v in enumerate(initial): code+=logical_byte(sy,i,v)
        code+=expect_byte(sy["vi_undo_kind"],2)+expect_word(sy["vi_undo_pos"],2)+expect_byte(sy["vi_undo_byte"],10)
        code+=phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch(image,sy,initial))

        for flag_name in ("vi_fail_gap_alloc","vi_fail_index_alloc"):
            code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0)+phase1._call(sy["vi_p903_init"])+phase1._jp_c(FAIL_PC))
            code+=b"\x3E\x01\x32"+word(sy[flag_name])
            code+=phase1._ld_hl(1)+b"\x3E\x58"+phase1._call(sy["vi_p903_insert_byte"])
            code+=b"\xD2"+word(FAIL_PC)
            code+=b"\xFE"+bytes((sy["E_NOMEM"]&0xFF,))+phase1._jp_nz(FAIL_PC)
            code+=expect_word(sy["vi_buffer_len"],5)+expect_word(sy["vi_gap_start"],5)+expect_word(sy["vi_gap_end"],1024)
            code+=expect_byte(sy["vi_line_count"],2)+expect_word(sy["vi_line_index"],0)+expect_word(sy["vi_line_index"]+2,3)
            code+=expect_byte(sy["vi_dirty"],0)
            for i,v in enumerate(initial): code+=expect_byte(sy["vi_buffer"]+i,v)
            code+=phase1._jp(PASS_PC)
            run_sna(root,bytes(code),patch=patch(image,sy,initial))

        assertions += [
            {"name":"fuse-gap-index-initial-coherent","passed":True},
            {"name":"fuse-insert-delete-byte-exact","passed":True},
            {"name":"fuse-bounded-undo-record","passed":True},
            {"name":"fuse-gap-allocation-failure-atomic","passed":True},
            {"name":"fuse-index-allocation-failure-atomic","passed":True},
        ]

    hashes={
        "tools/vi.asm":sha256_file(source),
        "v1/build/p903-vi.mex1":sha256_file(mex_path),
        "v1/build/p903-vi.tap":sha256_file(tap),
        "v1/tools-host/test-driver/phase9_vi_gap.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_gap.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.02.test.json":sha256_file(root/"v1/dist/certification/P9.02.test.json"),
    }
    return [fr,xr],hashes,assertions
