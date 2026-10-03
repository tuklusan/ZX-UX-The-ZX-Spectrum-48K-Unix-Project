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
import argparse, json, re, subprocess, sys
from pathlib import Path

KERNEL_START=0xE000
KERNEL_POOL_BYTES=0x1B00

def req(v,m):
    if not v: raise SystemExit("ERROR: "+m)

def parse_symbols(path:Path)->dict[str,int]:
    pat=re.compile(r"^([^:]+): EQU 0x([0-9A-Fa-f]+)\s*$")
    symbols={}
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        m=pat.match(line.strip())
        if m: symbols[m.group(1)]=int(m.group(2),16)
    return symbols

def parse_symbol(path:Path,name:str)->int:
    symbols=parse_symbols(path)
    if name in symbols: return symbols[name]
    raise SystemExit("ERROR: missing probe symbol "+name)

def source_prefix(text:str,output_name:str)->str:
    marker="kernel_ordinary_used_end:"
    req(text.count(marker)==1,"kernel ordinary-end marker")
    prefix=text.split(marker,1)[0]
    return prefix+marker+"\n"+f'    SAVEBIN "../../build/{output_name}",kernel_image_start,kernel_ordinary_used_end-kernel_image_start\n'

def assemble(root:Path,name:str,text:str,start:int=KERNEL_START)->dict:
    srcdir=root/"v1/src/kernel"
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sj=root/"tools/runtime/sjasmplus/bin/sjasmplus"
    req(sj.is_file(),"certified sjasmplus missing")
    source=srcdir/f"rev02-{name}-probe.asm"
    sym=build/f"rev02-{name}-probe.sym"
    binary=build/f"rev02-{name}-probe.bin"
    sym.unlink(missing_ok=True); binary.unlink(missing_ok=True)
    source.write_text(source_prefix(text,binary.name),encoding="utf-8",newline="\n")
    try:
        p=subprocess.run([str(sj),"--nologo",f"--sym={sym}",source.name],cwd=srcdir,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    finally:
        source.unlink(missing_ok=True)
    diagnostics=p.stdout+p.stderr
    row={"command_exit":p.returncode,"stdout":p.stdout[-16000:],"stderr":p.stderr[-16000:],
         "diagnostics_clean":not any(x in diagnostics for x in ("Label has different value in pass 3","truncated to 16bit"))}
    if p.returncode!=0:
        approximate_bytes=None
        if sym.is_file():
            try:
                approximate_end=parse_symbol(sym,"kernel_ordinary_used_end")
                if approximate_end > start:
                    approximate_bytes=approximate_end-start
            except RuntimeError:
                approximate_bytes=None
        approximate_module_spans=[]
        if sym.is_file():
            try:
                symbols=parse_symbols(sym)
                markers=[(n,v) for n,v in symbols.items() if n.startswith("kernel_mod_")]
                if "kernel_ordinary_used_end" in symbols:
                    markers.append(("kernel_ordinary_used_end",symbols["kernel_ordinary_used_end"]))
                markers.sort(key=lambda item:(item[1],item[0]))
                approximate_module_spans=[
                    {"name":markers[i][0],"start":markers[i][1],"end":markers[i+1][1],
                     "bytes":markers[i+1][1]-markers[i][1]}
                    for i in range(len(markers)-1)
                ]
            except RuntimeError:
                approximate_module_spans=[]
        row.update({"status":"ASSEMBLY-FAIL","ordinary_bytes":None,"approximate_bytes":approximate_bytes,
                    "approximate_module_spans":approximate_module_spans,
                    "pool_bytes":KERNEL_POOL_BYTES,"slack_bytes":None})
        return row
    if not row["diagnostics_clean"]:
        row.update({"status":"ASSEMBLY-UNSTABLE","ordinary_bytes":None,"pool_bytes":KERNEL_POOL_BYTES,"slack_bytes":None})
        return row
    end=parse_symbol(sym,"kernel_ordinary_used_end")
    used=end-start
    req(0 < used < 0x8000,"ordinary byte measurement")
    req(binary.is_file() and binary.stat().st_size==used,"probe binary size")
    symbols=parse_symbols(sym)
    markers=[(n,v) for n,v in symbols.items() if n.startswith("kernel_mod_")]
    markers.append(("kernel_ordinary_used_end",end))
    markers.sort(key=lambda item:(item[1],item[0]))
    module_spans=[{"name":markers[i][0],"start":markers[i][1],"end":markers[i+1][1],"bytes":markers[i+1][1]-markers[i][1]}
                  for i in range(len(markers)-1)]
    row.update({"status":"PASS","ordinary_bytes":used,"pool_bytes":KERNEL_POOL_BYTES,
                "slack_bytes":KERNEL_POOL_BYTES-used,"overrun_bytes":max(0,used-KERNEL_POOL_BYTES),
                "module_spans":module_spans})
    return row

def measure_historical_fixture(root:Path,step:str)->dict:
    evidence=Path("/tmp")/("rev02-capacity-"+step.replace(".","-"))
    evidence.mkdir(parents=True,exist_ok=True)
    runner=root/"v1/tools-host/test-driver/run.py"
    p=subprocess.run([sys.executable,str(runner),"build","--step",step,"--evidence-dir",str(evidence)],
                     cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    row={"step":step,"command_exit":p.returncode,"stdout":p.stdout[-4000:],"stderr":p.stderr[-4000:]}
    record=evidence/f"{step}.build.json"
    if p.returncode!=0 or not record.is_file():
        row["status"]="FAIL"
        return row
    data=json.loads(record.read_text(encoding="utf-8"))
    bins=[]
    for rel in sorted(data.get("hashes",{})):
        if rel.startswith("v1/build/") and rel.endswith(".bin"):
            fp=root/rel
            if fp.is_file():
                bins.append({"path":rel,"bytes":fp.stat().st_size})
    row.update({"status":"PASS","bins":bins,"max_bin_bytes":max((x["bytes"] for x in bins),default=0)})
    return row

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ns=ap.parse_args()
    root=ns.root.resolve(); out=ns.output.resolve(); out.mkdir(parents=True,exist_ok=True)
    kernel=(root/"v1/src/kernel/kernel.asm").read_text(encoding="utf-8")
    syscall=(root/"v1/src/kernel/syscall.asm").read_text(encoding="utf-8")
    include=(root/"v1/include/zx48ux.inc").read_text(encoding="utf-8")
    process=(root/"v1/src/kernel/process.asm").read_text(encoding="utf-8")
    pipe=(root/"v1/src/kernel/pipe.asm").read_text(encoding="utf-8")
    rom_doc=(root/"v1/docs/rom-services.md").read_text(encoding="utf-8")
    low_ram_needles=(
        "ROM_PRINTER_BUFFER_START EQU $5B00",
        "ROM_SYSVAR_KERNEL_TAIL_START EQU $5CB0",
        "ROM_IF1_WORK_START       EQU $5CB6",
        "ROM_IF1_WORK_END         EQU $5CC5",
    )
    for needle in low_ram_needles:
        req(needle in include,"REV02 low-RAM constant missing: "+needle)
    req("REV02_PROCESS_LOW_BASE        EQU ROM_PRINTER_BUFFER_START" in process,
        "REV02 printer-buffer process placement missing")
    req("REV02_PROCESS_SYSVAR5_BASE    EQU ROM_SYSVAR_START" in process and
        "REV02_PROCESS_SYSVAR6_BASE    EQU $5C80" in process,
        "REV02 BASIC-system-variable process placement missing")
    req("PROCESS_STATE_BASE       EQU ROM_SYSVAR_KERNEL_TAIL_START" in process and
        "current_pid              EQU ROM_IF1_WORK_START" in process,
        "REV02 system-variable process state placement missing")
    req("PIPE_STATE_BASE            EQU ROM_IF1_WORK_START+1" in pipe and
        "pipe_endpoint_kind          EQU PIPE_STATE_BASE+14" in pipe,
        "REV02 Interface-1 pipe scratch placement missing")
    req("### REV02 C022 low-RAM kernel ownership" in rom_doc,
        "REV02 low-RAM ownership documentation missing")
    baseline=assemble(root,"kernel-baseline",kernel)

    fixture_steps=("P2.12","P4.15","P4.19","P4.22","P4.23","P4.26","P4.27","P4.28",
                   "P4.31","P4.32","P5.08","P5.09","P5.10","P5.11","P5.14","P5.17","P11.40")
    fixture_measurements=[measure_historical_fixture(root,step) for step in fixture_steps]

    include_anchor='    INCLUDE "udg.asm"\n'
    req(kernel.count(include_anchor)==1,"UDG include anchor")
    req(syscall.count('    INCLUDE "graphics.asm"\n')==1,"syscall graphics include ownership")
    candidate=kernel.replace(include_anchor,include_anchor+'    INCLUDE "sound.asm"\n')
    measure_origin=0x8000
    origin_anchor="    ORG KERNEL_START\n"
    req(candidate.count(origin_anchor)==1,"kernel origin anchor")
    candidate=candidate.replace(origin_anchor,f"    ORG ${measure_origin:04X}\n",1)
    gateway_asserts=(
      ("    ASSERT $ = BOOT_GATEWAY\n",f"    ASSERT $ = ${measure_origin+3:04X}\n"),
      ("    ASSERT $ = BOOT_GATEWAY+3\n",f"    ASSERT $ = ${measure_origin+6:04X}\n"),
    )
    for old,new in gateway_asserts:
        req(candidate.count(old)==1,"kernel gateway assertion anchor")
        candidate=candidate.replace(old,new,1)
    emit_anchor="kernel_mod_udg:\n    EMIT_REV02_UDG_ROUTINES\n"
    req(candidate.count(emit_anchor)==1,"UDG emit anchor")
    extra="""kernel_mod_rev02_graphics:
    EMIT_GRAPHICS_ROUTINES
kernel_mod_rev02_sound:
    EMIT_SOUND_ROUTINES
kernel_mod_rev02_graphics_syscalls:
    EMIT_P701_GRAPHICS_SYSCALL_ROUTINES
kernel_mod_rev02_beep_syscall:
    EMIT_P709_BEEP_SYSCALL_ROUTINES
kernel_mod_rev02_rom_info_syscall:
    EMIT_P711_ROM_INFO_SYSCALL_ROUTINES
kernel_mod_rev02_udg_syscalls:
    EMIT_P714_UDG_SYSCALL_ROUTINES
    EMIT_P715_UDG_DRAW_SYSCALL_ROUTINES
kernel_mod_rev02_rom_beep:
    EMIT_P709_ROM_BEEP_ROUTINES
kernel_mod_rev02_rom_info:
    EMIT_REV02_P711_ROM_INFO_ROUTINES
kernel_mod_rev02_rom_fp_exec:
    EMIT_P1117_ROM_FP_EXEC_ROUTINES
kernel_mod_rev02_rom_fp_cast:
    EMIT_P1118_ROM_FP_CAST_ROUTINES
kernel_mod_rev02_rom_fp_cmp:
    EMIT_P1119_ROM_FP_CMP_ROUTINES
kernel_mod_rev02_rom_fp_to_text:
    EMIT_P1146_ROM_FP_TO_TEXT_ROUTINES
kernel_mod_rev02_rom_fp_from_text:
    EMIT_P1147_ROM_FP_FROM_TEXT_ROUTINES
kernel_mod_rev02_sys_fp_exec:
    EMIT_P1117_FP_EXEC_SYSCALL_ROUTINES
kernel_mod_rev02_sys_fp_cast:
    EMIT_P1118_FP_CAST_SYSCALL_ROUTINES
kernel_mod_rev02_sys_fp_cmp:
    EMIT_P1119_FP_CMP_SYSCALL_ROUTINES
kernel_mod_rev02_sys_fp_to_text:
    EMIT_P1146_FP_TO_TEXT_SYSCALL_ROUTINES
kernel_mod_rev02_sys_fp_from_text:
    EMIT_P1147_FP_FROM_TEXT_SYSCALL_ROUTINES
"""
    candidate=candidate.replace(emit_anchor,emit_anchor+extra)
    public_api=assemble(root,"kernel-public-api-lower-bound",candidate,start=measure_origin)

    # Architecture-capacity measurement only: construct a conservative complete
    # resident closure envelope without changing production kernel layout/bytes.
    # It deliberately composes the currently staged object/tape/zxpack/spawn and
    # public-service owners so the architecture revision can size the protected
    # kernel region from measured code rather than assuming +2 KiB is sufficient.
    closure_includes='    INCLUDE "objects.asm"\n    INCLUDE "tape.asm"\n    INCLUDE "zxpack.asm"\n    INCLUDE "sound.asm"\n'
    closure=kernel.replace(include_anchor,include_anchor+closure_includes)
    closure=closure.replace('    INCLUDE "../../include/zx48ux.inc"\n','    INCLUDE "../../include/zx48ux.inc"\n    INCLUDE "../../include/mex1.inc"\n    INCLUDE "../../include/tapeobj.inc"\n',1)
    closure_origin=0x6000
    req(closure.count(origin_anchor)==1,"closure kernel origin anchor")
    closure=closure.replace(origin_anchor,f"    ORG ${closure_origin:04X}\n",1)
    for old,unused in gateway_asserts:
        req(closure.count(old)==1,"closure gateway assertion anchor")
    closure=closure.replace("    ASSERT $ = BOOT_GATEWAY\n",f"    ASSERT $ = ${closure_origin+3:04X}\n",1)
    closure=closure.replace("    ASSERT $ = BOOT_GATEWAY+3\n",f"    ASSERT $ = ${closure_origin+6:04X}\n",1)
    req(closure.count(emit_anchor)==1,"closure UDG emit anchor")
    closure_extra=extra+"""kernel_mod_rev02_object_core:
    EMIT_NAMESPACE_ROUTINES
kernel_mod_size_object_type:
    EMIT_OBJECT_TYPE_ROUTINES
kernel_mod_rev02_object_open:
    EMIT_OBJECT_OPEN_ROUTINES
kernel_mod_size_object_exclusivity:
    EMIT_OBJECT_EXCLUSIVITY_ROUTINES
kernel_mod_rev02_object_io:
    EMIT_P407_RAW_IO_ROUTINES
kernel_mod_size_object_raw_write:
    EMIT_P408_RAW_WRITE_ROUTINES
kernel_mod_size_object_append:
    EMIT_P409_APPEND_ROUTINES
kernel_mod_rev02_object_meta:
    EMIT_P411_STAT_OBJECT_ROUTINES
kernel_mod_size_object_list:
    EMIT_P412_LIST_ROUTINES
kernel_mod_size_object_remove:
    EMIT_P413_REMOVE_ROUTINES
kernel_mod_size_object_rename:
    EMIT_P414_RENAME_ROUTINES
kernel_mod_size_object_rename_replace:
    EMIT_P415_RENAME_REPLACEMENT_ROUTINES
kernel_mod_size_object_writable_open:
    EMIT_P419_WRITABLE_OPEN_ROUTINES
kernel_mod_size_object_pack:
    EMIT_P422_SYS_PACK_OBJECT_ROUTINES
kernel_mod_size_object_unpack:
    EMIT_P423_SYS_UNPACK_OBJECT_ROUTINES
kernel_mod_size_object_candidate:
    EMIT_P424_OBJECT_CANDIDATE_ROUTINES
kernel_mod_size_object_chdir:
    EMIT_P431_CHDIR_OBJECT_ROUTINES
kernel_mod_size_object_getcwd:
    EMIT_P432_GETCWD_OBJECT_ROUTINES
kernel_mod_rev02_handle_extensions:
    EMIT_P406_EXCLUSIVITY_ROUTINES
kernel_mod_size_handle_packed_od:
    EMIT_P417_PACKED_OD_ROUTINES
kernel_mod_rev02_zxpack:
    EMIT_P416_ZXP1_DECODER
kernel_mod_size_zxpack_reader_state:
    EMIT_P417_PACKED_READER_STATE_ROUTINES
kernel_mod_size_zxpack_seek:
    EMIT_P418_PACKED_SEEK_ROUTINES
kernel_mod_size_zxpack_write:
    EMIT_P419_PACKED_WRITE_ROUTINES
kernel_mod_size_zxpack_encoder:
    EMIT_P420_TARGET_ENCODER_ROUTINES
kernel_mod_size_zxpack_decision:
    EMIT_P421_PACK_DECISION_ROUTINES
kernel_mod_size_zxpack_pack_codec:
    EMIT_P422_SYS_PACK_CODEC_ROUTINES
kernel_mod_size_zxpack_unpack_codec:
    EMIT_P423_SYS_UNPACK_CODEC_ROUTINES
kernel_mod_size_zxpack_candidate:
    EMIT_P424_PACK_CANDIDATE_ROUTINES
kernel_mod_size_zxpack_idle:
    EMIT_P425_IDLE_PACK_ROUTINES
kernel_mod_size_zxpack_compaction:
    EMIT_P426_COMPACTION_ROUTINES
kernel_mod_size_zxpack_spawn_stream:
    EMIT_P427_PACKED_SPAWN_STREAM_ROUTINES
kernel_mod_size_zxpack_info:
    EMIT_P428_ZXPACK_INFO_ROUTINES
kernel_mod_size_zxpack_packed_validator:
    EMIT_P505_PACKED_VALIDATOR_ROUTINES
kernel_mod_size_zxpack_read_adapter:
    EMIT_P1143_PACKED_READ_ADAPTER
kernel_mod_rev02_memory_extensions:
    EMIT_P426_COMPACT_ALLOC_ROUTINES
kernel_mod_rev02_scheduler_extensions:
    EMIT_P425_IDLE_MAINTENANCE_ROUTINES
kernel_mod_rev02_tape:
    EMIT_P502_CRC16_ROUTINES
kernel_mod_size_tape_framing:
    EMIT_P503_FRAMING_ROUTINES
kernel_mod_size_tape_raw_loader:
    EMIT_P504_RAW_LOADER_ROUTINES
kernel_mod_size_tape_packed_loader:
    EMIT_P505_PACKED_LOADER_ROUTINES
kernel_mod_size_tape_raw_save:
    EMIT_P507_RAW_SAVE_ROUTINES
kernel_mod_size_tape_stream_save:
    EMIT_P508_STREAM_SAVE_ROUTINES
kernel_mod_size_tape_explicit_load:
    EMIT_P509_EXPLICIT_LOAD_ROUTINES
kernel_mod_size_tape_verify:
    EMIT_P510_VERIFY_ROUTINES
kernel_mod_size_tape_scan:
    EMIT_P511_SCAN_ROUTINES
kernel_mod_size_tape_prompt:
    EMIT_P513_TAPE_PROMPT_ROUTINES
kernel_mod_size_tape_direct_stream:
    EMIT_P514_DIRECT_TAPE_STREAM_ROUTINES
kernel_mod_size_tape_abort:
    EMIT_P517_TAPE_ABORT_ROUTINES
kernel_mod_size_tape_public:
zx48_tape_save_block:
    call zx48_rom_sa_bytes
    ret nc
    ld a,E_IO
    scf
    ret
zx48_tape_load_block:
    call zx48_rom_ld_bytes
    jr nc,zx48_tape_load_error
    or a
    ret
zx48_tape_load_error:
    ld a,E_IO
    scf
    ret
zx48_tape_save_path:
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jr nz,zx48_tape_bad
    ld a,(path_dir)
    ld hl,path_name
    call zx48_object_lookup
    ret c
    jp zx48_p508_save_record
zx48_tape_load_path:
    jp zx48_p509_load_path
zx48_tape_verify_path:
    jp zx48_p510_verify_path
zx48_tape_scan_next:
    jp zx48_p511_scan_next
zx48_tape_bad:
    ld a,E_INVAL
    scf
    ret
kernel_mod_rev02_tape_recovery:
    EMIT_P517_TAPE_RECOVERY_ROUTINES
kernel_mod_rev02_spawn:
    EMIT_MEX1_RELOCATION_ROUTINES
kernel_mod_size_spawn_image_load:
    EMIT_MEX1_IMAGE_LOAD_ROUTINES
kernel_mod_size_spawn_stack:
    EMIT_MEX1_STACK_ROUTINES
kernel_mod_size_spawn_arg1:
    EMIT_ARG1_ROUTINES
kernel_mod_size_spawn_env1:
    EMIT_ENV1_ROUTINES
kernel_mod_size_spawn_context:
    EMIT_INITIAL_CONTEXT_ROUTINES
kernel_mod_size_spawn_preflight:
    EMIT_SPAWN_PREFLIGHT_ROUTINES
kernel_mod_size_spawn_transaction:
    EMIT_SPAWN_TRANSACTION_ROUTINES
kernel_mod_size_exec_transaction:
    EMIT_EXEC_TRANSACTION_ROUTINES
kernel_mod_size_spawn_packed:
    EMIT_P427_PACKED_SPAWN_ROUTINES
kernel_mod_size_spawn_tape:
    EMIT_P514_DIRECT_TAPE_MEX1_ROUTINES
kernel_mod_rev02_object_syscalls:
    EMIT_P405_SYS_OPEN_ROUTINES
    EMIT_P411_SYS_STAT_ROUTINES
    EMIT_P428_ZXPACK_INFO_SYSCALL_ROUTINES
    EMIT_P431_CHDIR_SYSCALL_ROUTINES
    EMIT_P432_GETCWD_SYSCALL_ROUTINES
kernel_mod_rev02_spawn_adapters:
zx48_spawn_resolve_ram_object:
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jr nz,.spawn_path_bad
    ld a,(path_dir)
    ld hl,path_name
    jp zx48_object_lookup
.spawn_path_bad:
    ld a,E_NOENT
    scf
    ret
zx48_p514_resolve_tape_name:
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jr nz,.tape_path_bad
    ld hl,path_name
    xor a
    ret
.tape_path_bad:
    ld a,E_NOENT
    scf
    ret
zx48_p514_commit_ready:
    xor a
    ret
kernel_mod_rev02_final_integration_reserve:
    defs 192,0
"""
    closure=closure.replace(emit_anchor,emit_anchor+closure_extra)
    complete_closure=assemble(root,"kernel-complete-closure-envelope",closure,start=closure_origin)

    report={"schema":1,"kind":"rev02-kernel-closure-probe","status":"PASS" if baseline["status"]=="PASS" and public_api["status"]=="PASS" else "FAIL",
            "kernel_pool_bytes":KERNEL_POOL_BYTES,
            "baseline":baseline,"public_api_lower_bound":public_api,"complete_closure_envelope":complete_closure,
            "historical_fixture_measurements":fixture_measurements,
            "measurement_origin":measure_origin,"complete_closure_measurement_origin":closure_origin,
            "measurement_method":"size-only relocation preserves relative gateway placement; graphics macro is sourced once through syscall.asm; production kernel remains at $E000",
            "low_ram_reclamation":{
              "printer_buffer":{"range":"0x5B00-0x5BFF","bytes":256,"assignment":"PID0..PID4 descriptors at 0x5B00-0x5BEF"},
              "basic_system_variables":{"range":"0x5C00-0x5CB5","bytes":182,"frames_reserved":"0x5C78-0x5C7A","udg_reserved":"0x5C7B-0x5C7C","current_assignment":"PID5 0x5C00-0x5C2F; PID6 0x5C80-0x5CAF; process scratch 0x5CB0-0x5CB5"},
              "interface1_microdrive":{"range":"0x5CB6-0x5CC5","bytes":16,"assignment":"current_pid + 15-byte pipe scratch"},
              "kernel_pool_limit_bytes":KERNEL_POOL_BYTES,
              "kernel_pool_expansion_authorized":False,
            },
            "scope":"public_api_lower_bound remains the staged graphics/sound/UDG/ROM/FP lower bound; complete_closure_envelope conservatively composes current staged object/tape/zxpack/spawn/public-service owners for architecture sizing and still excludes only the final compact selector rewrite"}
    (out/"KERNEL-CLOSURE-PROBE.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    req(baseline["status"]=="PASS","baseline kernel probe must assemble")
    if public_api["status"]!="PASS":
        print(public_api.get("stderr",""),file=sys.stderr)
        print(public_api.get("stdout",""),file=sys.stderr)
        raise SystemExit("ERROR: public API lower-bound probe must assemble")
    print("REV02 KERNEL CLOSURE PROBE PASS",json.dumps({"baseline":baseline.get("ordinary_bytes"),"public_api":public_api.get("ordinary_bytes"),"complete_closure":complete_closure.get("ordinary_bytes"),"complete_closure_approx":complete_closure.get("approximate_bytes"),"complete_closure_status":complete_closure.get("status"),"pool":KERNEL_POOL_BYTES}))
if __name__=="__main__": main()
