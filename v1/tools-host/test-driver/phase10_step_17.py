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

import json
from pathlib import Path

import phase1
import phase3_open_descriptions
from driver_core import DriverError
from fuse_harness import PASS_PC, FAIL_PC, run_sna


class P1017Error(DriverError):
    pass


def require(ok, msg):
    if not ok:
        raise P1017Error(msg)


def rows(path: Path):
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw and not raw.startswith("#"):
            parts = raw.split("|")
            require(len(parts) >= 3, f"malformed row: {raw}")
            out.append(tuple(parts[:3]))
    return out


def source_and_bytes(m: str, f: str):
    # One deterministic documented representative for every frozen inventory row.
    fixed = {
        ("adc","a,r"):("adc a,b","88"), ("adc","a,n"):("adc a,$12","CE 12"), ("adc","hl,rr"):("adc hl,bc","ED 4A"),
        ("add","a,r"):("add a,b","80"), ("add","a,n"):("add a,$12","C6 12"), ("add","hl,rr"):("add hl,bc","09"),
        ("add","ix,rr"):("add ix,bc","DD 09"), ("add","iy,rr"):("add iy,bc","FD 09"),
        ("and","r"):("and b","A0"), ("and","n"):("and $12","E6 12"),
        ("call","nn"):("call $1234","CD 34 12"), ("call","cc,nn"):("call nz,$1234","C4 34 12"),
        ("ccf",""):("ccf","3F"), ("cp","r"):("cp b","B8"), ("cp","n"):("cp $12","FE 12"),
        ("cpd",""):("cpd","ED A9"), ("cpdr",""):("cpdr","ED B9"), ("cpi",""):("cpi","ED A1"), ("cpir",""):("cpir","ED B1"),
        ("cpl",""):("cpl","2F"), ("daa",""):("daa","27"), ("dec","r"):("dec b","05"), ("dec","rr"):("dec bc","0B"),
        ("di",""):("di","F3"), ("djnz","rel"):("djnz $","10 FE"), ("ei",""):("ei","FB"),
        ("ex","af,af'"):("ex af,af'","08"), ("ex","de,hl"):("ex de,hl","EB"), ("ex","(sp),hl"):("ex (sp),hl","E3"),
        ("ex","(sp),ix"):("ex (sp),ix","DD E3"), ("ex","(sp),iy"):("ex (sp),iy","FD E3"), ("exx",""):("exx","D9"),
        ("halt",""):("halt","76"), ("im","0"):("im 0","ED 46"), ("im","1"):("im 1","ED 56"), ("im","2"):("im 2","ED 5E"),
        ("in","a,(n)"):("in a,($12)","DB 12"), ("in","r,(c)"):("in b,(c)","ED 40"),
        ("inc","r"):("inc b","04"), ("inc","rr"):("inc bc","03"),
        ("jp","nn"):("jp $1234","C3 34 12"), ("jp","cc,nn"):("jp nz,$1234","C2 34 12"),
        ("jp","(hl)"):("jp (hl)","E9"), ("jp","(ix)"):("jp (ix)","DD E9"), ("jp","(iy)"):("jp (iy)","FD E9"),
        ("jr","rel"):("jr $","18 FE"), ("jr","cc,rel"):("jr nz,$","20 FE"),
        ("ld","r,r"):("ld b,c","41"), ("ld","r,n"):("ld b,$12","06 12"), ("ld","r,(hl)"):("ld b,(hl)","46"),
        ("ld","(hl),r"):("ld (hl),b","70"), ("ld","(hl),n"):("ld (hl),$12","36 12"),
        ("ld","a,(bc)"):("ld a,(bc)","0A"), ("ld","a,(de)"):("ld a,(de)","1A"), ("ld","(bc),a"):("ld (bc),a","02"),
        ("ld","(de),a"):("ld (de),a","12"), ("ld","a,(nn)"):("ld a,($1234)","3A 34 12"), ("ld","(nn),a"):("ld ($1234),a","32 34 12"),
        ("ld","rr,nn"):("ld bc,$1234","01 34 12"), ("ld","hl,(nn)"):("ld hl,($1234)","2A 34 12"),
        ("ld","(nn),hl"):("ld ($1234),hl","22 34 12"), ("ld","rr,(nn)"):("ld bc,($1234)","ED 4B 34 12"),
        ("ld","(nn),rr"):("ld ($1234),bc","ED 43 34 12"), ("ld","ix,nn"):("ld ix,$1234","DD 21 34 12"),
        ("ld","iy,nn"):("ld iy,$1234","FD 21 34 12"), ("ld","r,(ix+d)"):("ld b,(ix+127)","DD 46 7F"),
        ("ld","r,(iy+d)"):("ld b,(iy-128)","FD 46 80"), ("ld","(ix+d),r"):("ld (ix+127),b","DD 70 7F"),
        ("ld","(iy+d),r"):("ld (iy-128),b","FD 70 80"), ("ld","sp,hl"):("ld sp,hl","F9"),
        ("ld","sp,ix"):("ld sp,ix","DD F9"), ("ld","sp,iy"):("ld sp,iy","FD F9"),
        ("ld","a,i"):("ld a,i","ED 57"), ("ld","a,r"):("ld a,r","ED 5F"), ("ld","i,a"):("ld i,a","ED 47"), ("ld","r,a"):("ld r,a","ED 4F"),
        ("ldd",""):("ldd","ED A8"), ("lddr",""):("lddr","ED B8"), ("ldi",""):("ldi","ED A0"), ("ldir",""):("ldir","ED B0"),
        ("neg",""):("neg","ED 44"), ("nop",""):("nop","00"), ("or","r"):("or b","B0"), ("or","n"):("or $12","F6 12"),
        ("out","(n),a"):("out ($12),a","D3 12"), ("out","(c),r"):("out (c),b","ED 41"),
        ("pop","rr"):("pop bc","C1"), ("pop","ix"):("pop ix","DD E1"), ("pop","iy"):("pop iy","FD E1"),
        ("push","rr"):("push bc","C5"), ("push","ix"):("push ix","DD E5"), ("push","iy"):("push iy","FD E5"),
        ("ret",""):("ret","C9"), ("ret","cc"):("ret nz","C0"), ("reti",""):("reti","ED 4D"), ("retn",""):("retn","ED 45"),
        ("rla",""):("rla","17"), ("rlca",""):("rlca","07"), ("rra",""):("rra","1F"), ("rrca",""):("rrca","0F"),
        ("rst","vec"):("rst $38","FF"), ("sbc","a,r"):("sbc a,b","98"), ("sbc","a,n"):("sbc a,$12","DE 12"),
        ("sbc","hl,rr"):("sbc hl,bc","ED 42"), ("scf",""):("scf","37"),
        ("sub","r"):("sub b","90"), ("sub","n"):("sub $12","D6 12"),
        ("xor","r"):("xor b","A8"), ("xor","n"):("xor $12","EE 12"),
    }
    if (m,f) in fixed:
        s,h = fixed[(m,f)]
        return s, bytes.fromhex(h)
    if m in ("bit","res","set"):
        family={"bit":0x40,"res":0x80,"set":0xC0}[m]
        op=family+3*8
        if f=="b,r": return f"{m} 3,b", bytes((0xCB,op))
        if f=="b,(hl)": return f"{m} 3,(hl)", bytes((0xCB,op+6))
        if f=="b,(ix+d)": return f"{m} 3,(ix+127)", bytes((0xDD,0xCB,0x7F,op+6))
        if f=="b,(iy+d)": return f"{m} 3,(iy-128)", bytes((0xFD,0xCB,0x80,op+6))
    shifts={"rlc":0x00,"rrc":0x08,"rl":0x10,"rr":0x18,"sla":0x20,"sra":0x28,"srl":0x38}
    if m in shifts:
        base=shifts[m]
        if f=="r": return f"{m} b", bytes((0xCB,base))
        if f=="(hl)": return f"{m} (hl)", bytes((0xCB,base+6))
        if f=="(ix+d)" and m=="rl": return "rl (ix+127)", bytes((0xDD,0xCB,0x7F,0x16))
        if f=="(iy+d)" and m=="rl": return "rl (iy-128)", bytes((0xFD,0xCB,0x80,0x16))
    raise P1017Error(f"no P10.17 vector for {m}|{f}")


def coverage_ok(inv, cov):
    invkeys=[(m,f) for m,f,_ in inv]
    covkeys=[(m,f) for m,f,_ in cov]
    return len(invkeys)==len(set(invkeys))==len(covkeys)==len(set(covkeys)) and set(invkeys)==set(covkeys)


def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P10.17":
        raise DriverError(step)
    inv=rows(root/"v1/tests/compiler/as-opcode-inventory")
    cov=rows(root/"v1/tests/compiler/as-opcode-coverage")
    source=(root/"tools/as.asm").read_text(encoding="utf-8")
    doc=(root/"v1/docs/assembler.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"inventory-frozen-row-count","passed":len(inv)==137},
        {"name":"coverage-exact-one-to-one","passed":coverage_ok(inv,cov)},
        {"name":"coverage-qualified-step-range","passed":all(s in {f"P10.{n:02d}" for n in range(11,17)} for _,_,s in cov)},
        {"name":"portable-undocumented-opcodes-absent","passed":all(m.lower()!="sll" for m,_,_ in inv+cov)},
        {"name":"native-aggregate-expands-all-encoders","passed":"EMIT_P10_AS_OPCODE_COVERAGE" in source and all(f"EMIT_P10_AS_{x}" in source for x in ("LD_ENCODER","ALU_ENCODER","CONTROL_ENCODER","BIT_ENCODER","SPECIAL_ENCODER","BLOCK_IO_ENCODER"))},
        {"name":"coverage-documentation-present","passed":"P10.17 opcode coverage closure" in doc and "zero missing inventory rows" in doc},
    ]
    for n in range(11,17):
        for action_name in ("build","test"):
            p=root/"v1/dist/certification"/f"P10.{n:02d}.{action_name}.json"
            record=json.loads(p.read_text(encoding="utf-8"))
            assertions.append({"name":f"prior-P10.{n:02d}-{action_name}-pass","passed":record.get("status")=="PASS" and record.get("step")==f"P10.{n:02d}"})
    require(all(a["passed"] for a in assertions),"P10.17 coverage closure failure")

    # Certified SjASMPlus oracle for every inventory row.
    lines=[]; expected=bytearray()
    for m,f,_ in inv:
        line,b=source_and_bytes(m,f)
        lines.append("    "+line)
        expected.extend(b)
    assembler=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    corpus=build/"p1017-coverage.asm"
    corpus.write_text(
        '    DEVICE ZXSPECTRUM48\n    ORG $C000\nfixture:\n'
        +"\n".join(lines)
        +'\nfixture_end:\n    SAVEBIN "p1017-coverage.bin",fixture,fixture_end-fixture\n',
        encoding="utf-8",newline="\n")
    oracle=run_command([assembler,"--nologo",corpus.name],cwd=build,timeout_seconds=30)
    require(not oracle.timed_out and oracle.exit_code==0,f"P10.17 SjASMPlus corpus: {oracle.stderr or oracle.stdout}")
    actual=(build/"p1017-coverage.bin").read_bytes()
    assertions.append({"name":"all-137-sjasmplus-vectors-byte-identical","passed":actual==bytes(expected)})
    require(actual==bytes(expected),"P10.17 complete SjASMPlus corpus mismatch")

    fixture=build/"p1017-native.asm"
    fixture.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../../tools/as.asm"
    ORG $C000
fixture:
    EMIT_P10_AS_OPCODE_COVERAGE
fixture_end:
    SAVEBIN "p1017-native.bin",fixture,fixture_end-fixture
""",encoding="utf-8",newline="\n")
    native=run_command([assembler,"--nologo","--sym=p1017-native.sym",fixture.name],cwd=build,timeout_seconds=30)
    require(not native.timed_out and native.exit_code==0,f"P10.17 native aggregate: {native.stderr or native.stdout}")

    if action=="test":
        # Fail-closed coverage mutation or undocumented addition must not certify.
        assertions += [
            {"name":"negative-missing-row-detected","passed":not coverage_ok(inv,cov[:-1])},
            {"name":"negative-extra-undocumented-row-detected","passed":not coverage_ok(inv,cov+[("sll","r","P10.14")])},
        ]
        syms=phase3_open_descriptions._symbols(
            build/"p1017-native.sym",
            ("as_p1011_ld_r_r","as_p1012_alu_r","as_p1013_abs","as_p1014_cb_shift","as_p1015_special","as_p1016_block"),
        )
        image=(build/"p1017-native.bin").read_bytes()
        def patch(ram): ram[0xC000-0x4000:0xC000-0x4000+len(image)]=image
        code=bytearray(b"\xF3"+phase1._ld_sp(0xBFC0))
        for addr,setup,want in (
            (syms["as_p1011_ld_r_r"],bytes((0x06,0,0x0E,1)),0x41),
            (syms["as_p1012_alu_r"],bytes((0x3E,0,0x06,0)),0x80),
            (syms["as_p1013_abs"],bytes((0x3E,0,0x06,0xFF)),0xC3),
        ):
            code += setup+phase1._call(addr)+phase1._jp_c(FAIL_PC)+bytes((0xFE,want))+phase1._jp_nz(FAIL_PC)
        for addr,setup,want in (
            (syms["as_p1014_cb_shift"],bytes((0x3E,0,0x06,0)),0xCB00),
            (syms["as_p1015_special"],bytes((0x3E,4)),0xED4D),
            (syms["as_p1016_block"],bytes((0x3E,0)),0xEDA0),
        ):
            code += setup+phase1._call(addr)+phase1._jp_c(FAIL_PC)+phase1._ld_de(want)+b"\xB7\xED\x52"+phase1._jp_nz(FAIL_PC)
        code += phase1._jp(PASS_PC)
        run_sna(root,bytes(code),patch=patch)
        assertions.append({"name":"fuse-all-six-native-encoder-families","passed":True})

    hashes={
        "tools/as.asm":sha256_file(root/"tools/as.asm"),
        "v1/tests/compiler/as-opcode-inventory":sha256_file(root/"v1/tests/compiler/as-opcode-inventory"),
        "v1/tests/compiler/as-opcode-coverage":sha256_file(root/"v1/tests/compiler/as-opcode-coverage"),
        "v1/docs/assembler.md":sha256_file(root/"v1/docs/assembler.md"),
        "v1/build/p1017-coverage.bin":sha256_file(build/"p1017-coverage.bin"),
        "v1/build/p1017-native.bin":sha256_file(build/"p1017-native.bin"),
        "v1/tools-host/test-driver/phase10_step_17.py":sha256_file(root/"v1/tools-host/test-driver/phase10_step_17.py"),
        "v1/dist/certification/P10.16.build.json":sha256_file(root/"v1/dist/certification/P10.16.build.json"),
        "v1/dist/certification/P10.16.test.json":sha256_file(root/"v1/dist/certification/P10.16.test.json"),
    }
    return [oracle,native],hashes,assertions
