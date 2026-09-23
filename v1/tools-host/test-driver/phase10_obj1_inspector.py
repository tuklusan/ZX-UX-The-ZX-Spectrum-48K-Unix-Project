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

import importlib.util
from pathlib import Path
import struct
from typing import Callable, Any

from driver_core import DriverError


class InspectorContractError(DriverError):
    pass


def require(ok:bool,msg:str)->None:
    if not ok:
        raise InspectorContractError(msg)


def load_inspector(root:Path):
    path=root/"v1/tools-host/inspect-obj/inspect.py"
    spec=importlib.util.spec_from_file_location("zxux_inspect_obj",path)
    require(spec is not None and spec.loader is not None,"inspector import")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rejected(mod,data:bytes)->bool:
    try:
        mod.inspect_bytes(data)
    except mod.ObjError:
        return True
    return False


def adversarial_assertions(mod)->list[dict[str,object]]:
    good=mod._make_fixture()
    parsed=mod.inspect_bytes(good)
    assertions=[
        {"name":"fixture-decodes-deterministically","passed":parsed["magic"]=="OBJ1" and parsed["symbol_count"]==1 and parsed["relocation_count"]==1},
        {"name":"fixture-relocation-signed-addend","passed":parsed["relocations"][0]["addend"]==0},
    ]
    for bit_offset in (0,4,5,6,8,10,12,14,16,18,20,22,len(good)-1):
        bad=bytearray(good); bad[bit_offset]^=1
        assertions.append({"name":f"one-bit-mutation-{bit_offset}-rejected","passed":rejected(mod,bytes(bad))})
    assertions.append({"name":"trailing-byte-rejected","passed":rejected(mod,good+b"\x00")})
    short=good[:23]
    assertions.append({"name":"short-header-rejected","passed":rejected(mod,short)})
    wrap=bytearray(24)
    wrap[:4]=b"OBJ1"; wrap[4]=1
    struct.pack_into("<H",wrap,6,24)
    struct.pack_into("<H",wrap,12,0x4000)
    struct.pack_into("<H",wrap,16,24)
    struct.pack_into("<H",wrap,18,24)
    struct.pack_into("<H",wrap,20,mod.crc16_ccitt_false(b""))
    struct.pack_into("<H",wrap,22,0)
    struct.pack_into("<H",wrap,22,mod.crc16_ccitt_false(bytes(wrap)))
    assertions.append({"name":"symbol-count-wrap-vector-rejected","passed":rejected(mod,bytes(wrap))})
    wrap2=bytearray(26)
    wrap2[:4]=b"OBJ1"; wrap2[4]=1
    struct.pack_into("<H",wrap2,6,24); struct.pack_into("<H",wrap2,8,2)
    struct.pack_into("<H",wrap2,14,0x4000)
    struct.pack_into("<H",wrap2,16,26); struct.pack_into("<H",wrap2,18,26)
    struct.pack_into("<H",wrap2,20,mod.crc16_ccitt_false(bytes(wrap2[24:])))
    struct.pack_into("<H",wrap2,22,0); struct.pack_into("<H",wrap2,22,mod.crc16_ccitt_false(bytes(wrap2[:24])))
    assertions.append({"name":"reloc-count-wrap-vector-rejected","passed":rejected(mod,bytes(wrap2))})
    return assertions


def dispatch(root:Path,action:str,step:str,*,sha256_file:Callable[[Path],str],run_command:Callable[...,Any],require_project_tool:Callable[[Path,str|Path],Path]):
    if step!="P10.04":
        raise DriverError(f"Phase-10 OBJ1 inspector step is not registered: {step}")
    mod=load_inspector(root)
    commands=[]
    assertions=[
        {"name":"inspector-independent-module","passed":hasattr(mod,"inspect_bytes") and hasattr(mod,"ObjError")},
        {"name":"inspector-self-test-entry","passed":hasattr(mod,"self_test")},
    ]
    mod.self_test()
    assertions.append({"name":"built-in-self-test-pass","passed":True})
    if action=="test":
        assertions.extend(adversarial_assertions(mod))
    failed=[a["name"] for a in assertions if a.get("passed") is not True]
    require(not failed,f"P10.04 inspector failures: {failed}")
    hashes={
        "v1/tools-host/inspect-obj/inspect.py":sha256_file(root/"v1/tools-host/inspect-obj/inspect.py"),
        "v1/include/obj1.inc":sha256_file(root/"v1/include/obj1.inc"),
        "v1/docs/obj1.md":sha256_file(root/"v1/docs/obj1.md"),
        "v1/tools-host/test-driver/phase10_obj1_inspector.py":sha256_file(root/"v1/tools-host/test-driver/phase10_obj1_inspector.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P10.03.build.json":sha256_file(root/"v1/dist/certification/P10.03.build.json"),
        "v1/dist/certification/P10.03.test.json":sha256_file(root/"v1/dist/certification/P10.03.test.json"),
    }
    return commands,hashes,assertions
