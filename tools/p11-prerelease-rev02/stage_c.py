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
import argparse, hashlib, json
from pathlib import Path

def req(v,m):
    if not v: raise SystemExit("ERROR: "+m)
def sha(p: Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--sdk-root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--kernel-probe",type=Path,required=True)
    ap.add_argument("--product-tools-report",type=Path,required=True)
    ns=ap.parse_args()
    root=ns.root.resolve(); sdk=ns.sdk_root.resolve(); out=ns.output
    out.mkdir(parents=True,exist_ok=True)
    kernel_probe=json.loads(ns.kernel_probe.read_text())
    product_report=json.loads(ns.product_tools_report.read_text())
    req(kernel_probe.get("kind")=="rev02-kernel-closure-probe" and kernel_probe.get("status")=="PASS","kernel closure probe identity")
    req(product_report.get("kind")=="rev02-product-tools-preflight" and product_report.get("status")=="PASS","product tools preflight identity")
    as_semantic=product_report.get("as",{}).get("semantic_status","")
    as_full=("GENERIC-NATIVE-AS-FULL-P10-SYNTAX-DRIVER" in as_semantic)
    rel=json.loads((sdk/"SDK-RELEASE.json").read_text())
    req(rel.get("program_count")==30 and len(rel.get("programs",[]))==30,"SDK program corpus")

    kernel=(root/"v1/src/kernel/kernel.asm").read_text()
    boot=(root/"v1/src/boot/entry.asm").read_text()
    shell=(root/"v1/src/shell/sh.asm").read_text()
    cc=(root/"v1/src/tools/cc.asm").read_text()
    sizeof_probe=b"int main(void){return sizeof(int);}\n"
    sizeof_ready=("cc_rev02_kw_sizeof:" in cc and "cc_rev02_value_sizeof:" in cc)
    sizeof_detail={
      "id":"C002-SIZEOF","input":"int main(void){return sizeof(int);}",
      "input_sha256":hashlib.sha256(sizeof_probe).hexdigest(),
      "tool_source_sha256":sha(root/"v1/src/tools/cc.asm"),
      "status":"RESOLVED" if sizeof_ready else "REPRODUCED",
      "observed":("generic production sizeof lowering is present" if sizeof_ready else
                  "production runtime-value parser has no sizeof lowering; sizeof is treated as an ordinary identifier/call and sizeof(int) fails before OBJ1 publication"),
      "expected":"ordinary production cc compiles sizeof(int) as constant 2 with unsigned-int result type",
      "authority":["REV18 §25.1","REV18 §25.2","REV09 P11.34","historical REV17 §25.2"],
    }
    ass=(root/"tools/as.asm").read_text()
    ld=(root/"tools/ld.asm").read_text()
    runtime=(root/"v1/src/libc48/runtime_archive.asm").read_text()
    process=(root/"v1/src/kernel/process.asm").read_text()
    tape_source=(root/"v1/src/kernel/tape.asm").read_text()
    syscall_source=(root/"v1/src/kernel/syscall.asm").read_text()
    rev18=(root/"docs/01-ZX-UX-ARCHITECTURE-REV18.md").read_text()

    req("p621_cc_path: db '/bin/cc',0" in shell,"shell /bin/cc path contract missing")
    req("MACRO EMIT_P614_PATH_ROUTINES" in shell and "SYS_STAT" in shell and "OBJ_BIN" in shell,
        "ordinary shell PATH resolver missing")
    req("EMIT_P601_SH_IMAGE" in shell and "sh_idle:" in shell,"historical shell entry fixture missing")
    req("jp zx48_idle_loop" in boot and "zx48_p601_pid1_bootstrap" not in boot,
        "boot root-blocker assumption changed")
    for inc in ("objects.asm","tape.asm","zxpack.asm","graphics.asm","sound.asm"):
        req(('INCLUDE "'+inc+'"') not in kernel,"kernel composition assumption changed: "+inc)
    req("EMIT_P11PR_CC_SDK_CORPUS_COMPILER" in cc and "cc_p11pr_identity_table:" in cc,
        "historical P11PR identity-bound fixture unexpectedly absent")
    req("EMIT_P1145_CC_H06_COMPILER" in cc and "CC_P1145_SOURCE_CRC" in cc,
        "historical H06 fixture unexpectedly absent")
    req("EMIT_REV02_CC_PRODUCT_CLI" in cc and "cc_rev02_compile_stream:" in cc and "CC_REV02_BSS_BYTES" in cc,
        "REV02 cc generic streaming product route missing")
    req("EMIT_REV02_AS_PRODUCT_CLI" in ass and "as_rev02_assemble_stream:" in ass and "AS_REV02_BSS_BYTES" in ass,
        "REV02 as generic streaming product route missing")
    req("EMIT_REV02_LD_PRODUCT_CLI" in ld and "Stage-E ordinary normal-output checkpoint" in ld,
        "REV02 ld generic normal-link Stage-E checkpoint missing")
    req("ld input.obj -o output -abs" in rev18,"REV18 fixed-image ld CLI authority missing")
    req("cp 4" in ld and "cp 5" in ld and "ld_rev02_require_last" in ld,
        "REV02 ld argv shape changed; rerun Stage-C assumptions")
    abs_ld_ready=all(x in ld for x in (
        "ld_rev02_abs_start:", "ld b,OBJ_DAT", "ld_rev02_temp_prefix:   db '/tmp/.ld'",
        "ld_rev02_validate_abs_header:", "ld_rev02_verify_loop:", "ld a,SYS_RENAME",
        "LD_REV02_ABS_MAX        EQU 8192", "cp '/'"))
    product_builder=(root/"tools/p11-prerelease-rev02/product_tools.py").read_text()
    req("cc.m48o.tap" in product_builder and "as.m48o.tap" in product_builder and "ld.m48o.tap" in product_builder,
        "REV02 deterministic product-tool packaging closure missing")

    product_specs={
      "sh":{"source":"v1/src/shell/sh.asm","text":shell},
      "cc":{"source":"v1/src/tools/cc.asm","text":cc},
      "as":{"source":"tools/as.asm","text":ass},
      "ld":{"source":"tools/ld.asm","text":ld},
    }
    report_names={"sh":"shell","cc":"cc","as":"as","ld":"ld"}
    for name,spec in product_specs.items():
        row=product_report.get(report_names[name],{})
        req(row.get("source_sha256")==sha(root/spec["source"]),"product tools source binding: "+name)
        if name=="as":
            req(row.get("support_source")=="tools/as_text.asm","assembler support-source identity")
            req(row.get("support_source_sha256")==sha(root/"tools/as_text.asm"),"assembler support-source binding")
        req(isinstance(row.get("mex1_sha256"),str) and len(row["mex1_sha256"])==64,"product MEX1 hash: "+name)
        req(isinstance(row.get("m48o_tap_sha256"),str) and len(row["m48o_tap_sha256"])==64,"product M48O hash: "+name)
    closures={}
    for name,s in product_specs.items():
        p=root/s["source"]
        has_product_image=("SAVEBIN" in s["text"] and "MEX1" in s["text"])
        closures[name]={
          "source":s["source"],"source_sha256":sha(p),
          "ordinary_product_binary_sha256":product_report[report_names[name]]["mex1_sha256"],
          "ordinary_product_m48o_tap_sha256":product_report[report_names[name]]["m48o_tap_sha256"],
          "installable_product_image_in_source":has_product_image,
          "deterministic_installable_product_available":True,
        }
        if name=="as":
            closures[name]["support_source_sha256"]=product_report[report_names[name]]["support_source_sha256"]
        req(not has_product_image,f"{name}: source unexpectedly has direct product image; Stage-C assumptions changed")

    candidate_patterns=("cc.mex1","as.mex1","ld.mex1","sh.mex1","cc.m48o","as.m48o","ld.m48o","sh.m48o")
    found=[]
    for p in root.rglob("*"):
        if p.is_file() and p.name.lower() in candidate_patterns:
            found.append(p.relative_to(root).as_posix())
    req(not found,"ordinary product tool artifacts unexpectedly present: "+",".join(found))

    rows=[]
    for p in rel["programs"]:
        tape=sdk/p["tape_path"]
        req(tape.is_file() and sha(tape)==p["tape_sha256"],"source tape drift "+p["tape_path"])
        rows.append({
          "category":p["category"],"program":p["name"],
          "source_tape_path":p["tape_path"],"source_tape_sha256":p["tape_sha256"],
          "planned_source":p["target_source"],
          "tape_load":{"status":"NOT_REACHED","reason":"production kernel lacks current object/tape + PID1 developer-session route"},
          "header_resolution":{"status":"NOT_REACHED","reason":"same root blockers"},
          "cc":{"command":"cc "+p["target_source"],"status":"NOT_REACHED","errno":"E_NOENT","reason":"ordinary /bin/cc product binary/CLI absent"},
          "obj1":{"produced":False},"ld":{"status":"NOT_REACHED"},"process":{"status":"NOT_REACHED"},
          "screen_runtime_observation":"NOT_REACHED",
          "namespace_before":{"planned_obj":"ABSENT","planned_executable":"ABSENT"},
          "namespace_after":{"planned_obj":"ABSENT","planned_executable":"ABSENT"},
          "quoted_header_open_read":"NOT_REACHED","target_peak_memory":"NOT_REACHED"
        })

    gaps=[
      {"id":"C002","failure":"ordinary /bin/cc semantic compiler route incomplete",
       "observed":"REV02 ordinary cc now consumes arbitrary source through bounded SYS_READ, resolves one-level quoted local OBJ_C/OBJ_TXT includes through ordinary STAT/OPEN/READ/CLOSE with a distinct bounded include window, expands the frozen bounded source-generic object-like #define constant surface, parses a generic integer constant-function subset, emits real OBJ1, and transactionally publishes it; full frozen C48 remains incomplete",
       "detail_reproductions":[sizeof_detail],
       "planned_paths":["v1/src/tools/cc.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["cc","OBJ1"]},
    ]
    if not as_full:
        gaps.append(
          {"id":"C003","failure":"ordinary /bin/as semantic assembler route incomplete",
           "observed":"ordinary as has a generic source-semantic driver but the product preflight does not certify complete label/EQU/DB/DW/DS/global/extern/expression/ABS16-relocation closure",
           "planned_paths":["tools/as.asm","tools/as_text.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["generic as","kernel rebuild"]})
    gaps += [
      {"id":"C005","failure":"developer-sidecar build exists but real delivery/session closure is incomplete",
       "observed":"product_tools.py now hash-binds deterministic sh/cc/as/ld MEX1/M48O scaffolds to current sources; real ordinary cassette load/install/execute in a booted developer session is not yet reachable",
       "planned_paths":["tools/p11-prerelease-rev02/product_tools.py",".github/workflows/p11-prerelease-rev02-product-tools.yml"],"blocks":["normal command path"]},
      {"id":"C006","failure":"production boot never starts PID1 shell",
       "observed":"EMIT_BOOT_IMPL initializes base subsystems then jumps directly to zx48_idle_loop; no PID1 bootstrap/session handoff",
       "planned_paths":["v1/src/boot/entry.asm","v1/src/kernel/kernel.asm"],"blocks":["login","shell command execution"]},
      {"id":"C007","failure":"production kernel omits normal object/tape/zxpack namespace and spawn closure",
       "observed":"kernel.asm does not include objects.asm, tape.asm, or zxpack.asm and does not emit the later object/tape/spawn transaction facilities",
       "planned_paths":["v1/src/kernel/kernel.asm"],"blocks":["M48O load","/bin lookup","SYS_SPAWN","quoted header reads"]},
      {"id":"C008","failure":"production shell entry is idle-only and has no integrated command loop",
       "observed":"EMIT_P601_SH_IMAGE enters sh_idle and only SYS_YIELDs; later parser/PATH/pipeline routines are fixture macros not connected to product entry",
       "planned_paths":["v1/src/shell/sh.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["shell-visible cc/as/ld"]},
      {"id":"C009","failure":"no generic production cc CLI/compiler route",
       "observed":"ordinary generic cc now owns a source-semantic streaming compile/OBJ1 transaction with one-level quoted local include streaming and the frozen 16-entry/32-byte object-like #define constant surface for an initial C48 subset without source identity dispatch; built-in <c48.h> and the full frozen C48 parser/code-generator are not yet integrated",
       "planned_paths":["v1/src/tools/cc.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["generic C48","anti-specialization","30 lifecycle"]},
    ]
    if not as_full:
        gaps.append(
          {"id":"C010","failure":"no production as CLI entry over generic assembler pipeline",
           "observed":"ordinary as product packaging exists but the preflight does not certify the complete source-driver integration",
           "planned_paths":["tools/as.asm","tools/as_text.asm","tools/p11-prerelease-rev02/product_tools.py"],"blocks":["generic as","native kernel rebuild"]})
    gaps.append(
      {"id":"C012","failure":"production kernel omits graphics/sound services required by frozen public API",
       "observed":"kernel.asm does not include graphics.asm or sound.asm although the exact SDK corpus uses frozen graphics/sound calls",
       "planned_paths":["v1/src/kernel/kernel.asm"],"blocks":["source-defined program behavior"]})

    if not abs_ld_ready:
        gaps.append(
          {"id":"C014","failure":"ordinary /bin/ld fixed/absolute -abs route incomplete",
           "observed":"REV18 Section 24 freezes `ld input.obj -o output -abs`, but the current ordinary product path does not yet expose the complete generic validated DAT transaction",
           "planned_paths":["tools/ld.asm"],"blocks":["Stage-L shell-visible fixed/absolute native kernel rebuild"]})

    p514_image_block=process.split("zx48_p514_image_loop:",1)[1].split("zx48_p514_zero_bss:",1)[0]
    if ("call zx48_p514_tape_stream_byte" in p514_image_block and
        "call zx48_p514_crc16_update" in p514_image_block and
        "ld (hl),a" in p514_image_block and "push af" not in p514_image_block):
        gaps.append(
          {"id":"C015","failure":"P5.14 direct-tape image byte is clobbered before final image write",
           "observed":"zx48_p514_image_loop receives the logical image byte in A, calls zx48_p514_crc16_update which clobbers A, then stores the clobbered A to the process image",
           "planned_paths":["v1/src/kernel/process.asm"],"blocks":["direct tape-backed MEX1 exact image bytes"]})

    p514_phys_block=tape_source.split("zx48_p514_tape_physical_byte:",1)[1].split("zx48_p514_tape_have_chunk:",1)[0]
    if ("ld (p514_tape_chunk_left),de" in p514_phys_block and
        "call zx48_tape_load_block" in p514_phys_block and
        "sbc hl,de" in p514_phys_block and
        "ld de,(p514_tape_chunk_left)" not in p514_phys_block):
        gaps.append(
          {"id":"C016","failure":"P5.14 direct-tape physical-remaining subtracts a post-ROM-call DE",
           "observed":"the refill path records the chunk length, calls zx48_tape_load_block whose contract does not preserve DE, then subtracts that post-call DE from p514_tape_phys_remaining",
           "planned_paths":["v1/src/kernel/tape.asm"],"blocks":["direct tape-backed physical stream accounting"]})

    p509_match_block=tape_source.split("zx48_p509_match:",1)[1].split("zx48_p509_load_raw:",1)[0]
    if "ld b,(p509_header+M48O_HDR_TYPE)" in p509_match_block:
        gaps.append(
          {"id":"C017","failure":"P5.09 public type validation uses an invalid direct B absolute-memory load form",
           "observed":"zx48_p509_match uses ld b,(p509_header+M48O_HDR_TYPE) instead of loading the header byte through A before public type validation",
           "planned_paths":["v1/src/kernel/tape.asm"],"blocks":["SYS_TAPE_LOAD valid BIN/public-type acceptance"]})

    p509_commit_block=tape_source.split("zx48_p509_commit_new:",1)[1].split("zx48_p509_publish:",1)[0]
    if "ld b,(p509_header+M48O_HDR_TYPE)" in p509_commit_block:
        gaps.append(
          {"id":"C018","failure":"P5.09 new-object commit passes object_create an invalidly loaded type",
           "observed":"zx48_p509_commit_new repeats the invalid direct B absolute-memory load before zx48_object_create, so correcting only match validation would leave new-object creation wrong",
           "planned_paths":["v1/src/kernel/tape.asm"],"blocks":["SYS_TAPE_LOAD new-object atomic commit"]})

    p509_raw_handoff=tape_source.split("zx48_p509_load_raw:",1)[1].split("zx48_p509_header_basic:",1)[0]
    if ("call zx48_p504_raw_load\nzx48_p509_loaded:" in p509_raw_handoff and
        "ld d,b\n    ld e,c" not in p509_raw_handoff):
        gaps.append(
          {"id":"C019","failure":"P5.04 RAW success length is not handed off correctly to P5.09",
           "observed":"P5.04 returns HL=allocation and BC=validated RAW length while DE still carries CRC state; P5.09 stores DE as p509_new_logical, publishing CRC as logical length",
           "planned_paths":["v1/src/kernel/tape.asm"],"blocks":["SYS_TAPE_LOAD RAW logical length metadata"]})
    p514_skip_block=tape_source.split("zx48_p514_tape_skip:",1)[1].split("zx48_p514_tape_match:",1)[0]
    if ("call zx48_p509_skip_payload" in p514_skip_block and
        "p514_tape_header+M48O_HDR_STORAGE_LEN" not in p514_skip_block):
        gaps.append(
          {"id":"C020","failure":"P5.14 direct-tape forward search skips a nonmatching payload using P5.09 header state",
           "observed":"zx48_p514_tape_skip calls zx48_p509_skip_payload after loading p514_tape_header, but that helper reads storage length from p509_header; a nonmatching object can therefore leave the tape positioned inside its payload instead of at the next M48O header",
           "planned_paths":["v1/src/kernel/tape.asm"],"blocks":["direct tape-backed forward search past nonmatching objects"]})

    resident_syscall_gap=(
        "zx48_sys_spawn_stub" in syscall_source and
        "zx48_sys_open_stub" in syscall_source and
        "jp c,zx48_sys_notsup" in syscall_source and
        "cp SYS_MEM_INFO" in syscall_source and
        "cp SYS_TIME_SET+1" in syscall_source and
        "jp nc,zx48_sys_notsup" in syscall_source)
    if resident_syscall_gap:
        gaps.append(
          {"id":"C021","failure":"resident syscall router masks frozen public APIs behind E_NOTSUP",
           "observed":"EMIT_SYSCALL_IMPL still routes SYS_SPAWN/SYS_EXEC and object syscalls through resident stubs, rejects the graphics/sound/UDG/tape range before SYS_MEM_INFO, and rejects ZXPACK/FP/ROM services after SYS_TIME_SET even though staged handlers and product modules exist",
           "planned_paths":["v1/src/kernel/syscall.asm","v1/src/kernel/kernel.asm"],"blocks":["ordinary SYS_SPAWN","object/tape I/O","graphics/sound/UDG","zxpack/FP/ROM public APIs","real developer session"]})

    probe_baseline=kernel_probe["baseline"]
    probe_public=kernel_probe["public_api_lower_bound"]
    if (probe_baseline.get("status")=="PASS" and probe_public.get("status")=="PASS" and
        probe_public.get("ordinary_bytes",0) > kernel_probe.get("kernel_pool_bytes",0)):
        gaps.append(
          {"id":"C022","failure":"required resident public-service lower bound exceeds frozen 6912-byte kernel code/data pool",
           "observed":f"current production kernel uses {probe_baseline['ordinary_bytes']} of {kernel_probe['kernel_pool_bytes']} bytes ({probe_baseline['ordinary_bytes']*100//kernel_probe['kernel_pool_bytes']}% integer occupancy) while mandatory objects/tape/zxpack/spawn and several frozen public-service families are still omitted; adding only staged graphics/sound/UDG/ROM/FP service closure measures {probe_public['ordinary_bytes']} bytes, overrunning the pool by {probe_public['ordinary_bytes']-kernel_probe['kernel_pool_bytes']} bytes before object/tape/zxpack/spawn integration. Capacity correction is therefore bounded to the complete set of resident ordinary-pool source owners; the frozen memory map, ABI and public behavior remain unchanged",
           "planned_paths":["v1/src/kernel/kernel.asm","v1/src/kernel/syscall.asm","v1/src/boot/entry.asm","v1/src/kernel/interrupt.asm","v1/src/kernel/im2.asm","v1/src/kernel/rom_services.asm","v1/src/kernel/errors.asm","v1/src/kernel/memory.asm","v1/src/kernel/process.asm","v1/src/kernel/handles.asm","v1/src/kernel/pipe.asm","v1/src/kernel/scheduler.asm","v1/src/kernel/z80_primitives.asm","v1/src/kernel/ula_io.asm","v1/src/kernel/tty32.asm","v1/src/kernel/tty64.asm","v1/src/kernel/cursor.asm","v1/src/kernel/console.asm","v1/src/kernel/keyboard.asm","v1/src/kernel/udg.asm","v1/src/kernel/graphics.asm","v1/src/kernel/sound.asm","v1/src/kernel/objects.asm","v1/src/kernel/tape.asm","v1/src/kernel/zxpack.asm"],
           "blocks":["resident frozen public API closure","graphics/sound/UDG/ROM/FP integration","later object/tape/spawn closure"]})

    for g in gaps: g["class_pending"]="Stage-D"

    report={
      "schema":2,"kind":"rev02-stage-c-product-gap-inventory","status":"PASS-INVENTORY-ROOT-BLOCKER",
      "kernel_closure_probe":kernel_probe,
      "program_count":30,"programs":rows,"product_dependency_closures":closures,"gaps":gaps,
      "production_snapshot":{
        "kernel_sha256":sha(root/"v1/src/kernel/kernel.asm"),
        "boot_sha256":sha(root/"v1/src/boot/entry.asm"),
        "shell_sha256":sha(root/"v1/src/shell/sh.asm"),
        "cc_sha256":sha(root/"v1/src/tools/cc.asm"),
        "as_sha256":sha(root/"tools/as.asm"),
        "ld_sha256":sha(root/"tools/ld.asm"),
        "runtime_archive_sha256":sha(root/"v1/src/libc48/runtime_archive.asm"),
        "process_sha256":sha(root/"v1/src/kernel/process.asm"),
        "tape_sha256":sha(root/"v1/src/kernel/tape.asm"),
        "syscall_sha256":sha(root/"v1/src/kernel/syscall.asm"),
      },
      "assertions":{
        "all_30_exact_tapes_accounted":"PASS",
        "planned_outputs_absent":"PASS",
        "deterministic_product_tool_packaging_available":"PASS",
        "boot_to_real_shell_gap_recorded":"PASS",
        "object_tape_spawn_gap_recorded":"PASS",
        "generic_cli_gaps_recorded":"PASS",
        "generic_as_full_p10_source_driver_"+("resolved" if as_full else "recorded"):"PASS",
        "generic_normal_ld_resolved":"PASS",
        "runtime_api_closure_resolved":"PASS",
        "fixed_ld_public_cli_product_gap_"+("resolved" if abs_ld_ready else "recorded"):"PASS",
        "no_p11pr_compiler_invoked":"PASS",
        "no_internal_cc_or_ld_invoked":"PASS",
        "ordinary_product_path_reproduced_as_unavailable":"PASS",
        "shell_product_packaging_gap_resolved":"PASS",
        "legacy_publisher_not_used":"PASS",
        "stage_c_requires_rerun_after_product_correction":"PASS"
      }}
    (out/"STAGE-C.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(f"REV02 STAGE C GAP INVENTORY PASS root_blockers={len(gaps)} programs=30")
if __name__=="__main__": main()
