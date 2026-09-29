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
"""Build exact hanoi/queens8 source TAPs through native cc+ld for Gate I."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path
import sdk_acquire as sdk
import sdk_source_tape_native_visual_build as vb

ROOT=Path(__file__).resolve().parents[2]
KEEP=("hanoi","queens8")
def req(v,m):
    if not v: raise RuntimeError(m)
def sha(b): return hashlib.sha256(b).hexdigest()

def fixture_source(hn,hs,sn,ss):
    s=vb.fixture_source(hn,hs,sn,ss)
    s=s.replace("    EMIT_P11PR_CC_SDK_CORPUS_COMPILER\n",
                "    EMIT_P11PR_CC_SDK_CORPUS_COMPILER\n    EMIT_P11PR_CC_SDK_MULTITASK_COMPILER\n",1)
    s=s.replace("cc_p11pr_sdk_compile_visual","cc_p11pr_sdk_compile_multitask")
    s=s.replace("CC_P11PR_VIS_TITLE_OPERAND","CC_P11PR_MT_TITLE_OPERAND")
    s=s.replace("CC_P11PR_VIS_TEMPLATE_SIZE","CC_P11PR_MT_TEMPLATE_SIZE")
    s=s.replace("p11h-sdk-native-visual-tape.bin","p11i-sdk-native-multitask-tape.bin")
    return s

def run(fuse,sna,tape,sy):
    fail_marker=0xD181DEAD
    x=[f"breakpoint 0x{sy['p11h_pass']:04x}","commands 1",f"print 0x{vb.PASS_MARK:x}",
       f"print 0x{vb.OBJ_MARK:x}"]
    x += [f"print [0x{a:04x}]" for a in range(vb.OBJ_BASE,vb.OBJ_BASE+vb.CAP)]
    x += [f"print 0x{vb.MEX_MARK:x}"]
    x += [f"print [0x{a:04x}]" for a in range(vb.MEX_BASE,vb.MEX_BASE+vb.CAP)]
    x += ["exit 0","end",f"breakpoint 0x{sy['p11h_fail']:04x}","commands 2",
          f"print 0x{fail_marker:x}"]
    x += [f"print [0x{a:04x}]" for a in range(vb.OBJ_BASE,vb.OBJ_BASE+32)]
    x += [f"print [0x{a:04x}]" for a in range(vb.MEX_BASE,vb.MEX_BASE+32)]
    x += ["exit 1","end","continue"]
    return subprocess.run(["/usr/bin/env","SDL_VIDEODRIVER=dummy","SDL_AUDIODRIVER=dummy",str(fuse),
      "--machine","48","--no-sound","--no-confirm-actions","--tape",str(tape),
      "--debugger-command","\n".join(x),str(sna)],cwd=ROOT,text=True,capture_output=True,timeout=90)

def build_fixture(hn,hs,sn,ss):
    b=ROOT/"v1/build"; b.mkdir(parents=True,exist_ok=True)
    p=b/"p11i-sdk-native-multitask-tape.asm"
    p.write_text(fixture_source(hn,hs,sn,ss),encoding="utf-8",newline="\n")
    sj=ROOT/"tools/runtime/sjasmplus/bin/sjasmplus"; req(sj.is_file(),"project sjasmplus missing")
    r=subprocess.run([str(sj),"--nologo","--sym=p11i-sdk-native-multitask-tape.sym",p.name],cwd=b,text=True,capture_output=True,timeout=60)
    req(r.returncode==0,f"fixture assembly failed:\n{r.stdout}\n{r.stderr}")
    blob=(b/"p11i-sdk-native-multitask-tape.bin").read_bytes()
    sy=vb.symbols(b/"p11i-sdk-native-multitask-tape.sym",("p11h_positive","p11h_pass","p11h_fail"))
    return blob,sy

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); ap.add_argument("--report",type=Path,required=True); a=ap.parse_args()
    rel=json.loads((a.root/"SDK-RELEASE.json").read_text())
    req((rel.get("tag"),rel.get("commit"),rel.get("tree"))==(sdk.TAG,sdk.COMMIT,sdk.TREE),"SDK identity drift")
    fuse=ROOT/"tools/runtime/fuse/bin/fuse"; req(fuse.is_file(),"project Fuse missing")
    a.output.mkdir(parents=True,exist_ok=True); rows=[]
    with tempfile.TemporaryDirectory(prefix="zxux-p11i-build-") as td:
        td=Path(td)
        for name in KEEP:
            category="demos"; tape=a.root/f"usr/bin/{category}/{name}.src.tap"; raw=tape.read_bytes(); dec=sdk.decode(raw)
            header=next(x for x in dec if x[1]==1); source=next(x for x in dec if x[1]==5)
            source_name,obj_name,exe_name=sdk.target_names(name)
            req(source[0]==source_name,f"{name} target source drift")
            fixture,sy=build_fixture(header[0],len(header[3]),source[0],len(source[3]))
            sna=td/f"{name}.sna"; sna.write_bytes(vb.make_sna(sy["p11h_positive"],fixture))
            r=run(fuse,sna,tape,sy)
            req(r.returncode==0,f"{name} native multitask build failed rc={r.returncode}: {r.stdout!r} {r.stderr!r}")
            vals=[int(v,16) for v in re.findall(r"0x([0-9a-f]+)",r.stdout,re.I)]
            req(vb.PASS_MARK in vals,f"{name} PASS marker absent")
            obj,text=vb.obj_bytes(vb.dump_after(vals,vb.OBJ_MARK))
            mex=vb.mex_bytes(vb.dump_after(vals,vb.MEX_MARK),text)
            op=a.output/f"{name}.obj1"; ep=a.output/f"{name}.mex1"; op.write_bytes(obj); ep.write_bytes(mex)
            rows.append({"program":name,"source_tape_sha256":sha(raw),"source_sha256":sha(source[3]),"target_source":source_name,
              "obj1_size":len(obj),"obj1_sha256":sha(obj),"mex1_size":len(mex),"mex1_sha256":sha(mex),
              "tape_load":"PASS","native_cc":"PASS","native_ld":"PASS"})
    req(len(rows)==2,"Gate I build cardinality")
    report={"schema":1,"kind":"phase11-pre-release-hanoi-queens-native-build","programs":rows,
      "assertions":{"exact_sdk_source_tapes":"PASS","both_sources_loaded_through_rom_m48o":"PASS","both_target_native_cc":"PASS",
      "both_genuine_obj1":"PASS","both_target_native_ld":"PASS","both_genuine_mex1":"PASS","host_did_not_construct_obj1_or_mex1":"PASS"}}
    a.report.parent.mkdir(parents=True,exist_ok=True); a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("P11 PRE-RELEASE HANOI/QUEENS NATIVE BUILD PASS")
if __name__=="__main__": main()
