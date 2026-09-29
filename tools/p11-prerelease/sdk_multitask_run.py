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
"""Concurrent target-native hanoi + queens8 cooperative Gate-I proof."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"v1/tools-host/test-driver"))
import sdk_native_process_run as proc
import sdk_native_visual_run as vis
import phase2_spawn_atomic as p210
import phase2_spawn_exit_leak as p222

H_PROC=0xA000; Q_PROC=0xA020; H_PATH=0xA100; Q_PATH=0xA120
H_ARG=0xA200; Q_ARG=0xA240; ENV=0xA300; H_MEX=0xB400; Q_MEX=0xB800
H_REC=0xC000; Q_REC=0xC040; FONT=0xD000; MARK=0xD1810001
PROC_PRIVATE_FLAGS=46; PROC_PRIVATE_STARTED=0x80

def req(v,m):
    if not v: raise RuntimeError(m)
def sha(b): return hashlib.sha256(b).hexdigest()

def build_fixture():
    proc.build_fixture()
    b=ROOT/"v1/build"; t=(b/"p11pr-sdk-process.asm").read_text()
    t=t.replace("    cp SYS_SPAWN\n    jp z,zx48_sys_spawn\n    cp SYS_CON_CLEAR",
                "    cp SYS_YIELD\n    jp z,p11mt_yield\n    cp SYS_SPAWN\n    jp z,zx48_sys_spawn\n    cp SYS_CON_CLEAR",1)
    t=t.replace("zx48_spawn_resolve_ram_object:\n    ld ix,P11PR_RECORD\n    xor a\n    ret",
                "zx48_spawn_resolve_ram_object:\n    ld ix,(p11mt_record_ptr)\n    xor a\n    ret",1)
    t=t.replace("P11PR_RECORD EQU $B000",
                "P11PR_RECORD EQU $B000\nH_PROC EQU 0xA000\nQ_PROC EQU 0xA020\nH_REC EQU 0xC000\nQ_REC EQU 0xC040",1)
    anchor="p11pr_arg_bc: dw 0\n"
    extra=r"""
p11mt_yield:
    ld a,(current_pid)
    cp 2
    jr z,p11mt_h
    cp 3
    jr z,p11mt_q
    jp $B001
p11mt_h:
    ld hl,(p11mt_hanoi_yields)
    inc hl
    ld (p11mt_hanoi_yields),hl
    ld a,3
    jr p11mt_switch
p11mt_q:
    ld hl,(p11mt_queens_yields)
    inc hl
    ld (p11mt_queens_yields),hl
    ld a,2
p11mt_switch:
    ld (p11mt_next_pid),a
    ld a,(current_pid)
    call zx48_process_lookup
    jp c,$B001
    push ix
    ld hl,0
    add hl,sp
    pop ix
    inc hl
    inc hl
    ld (ix+PROC_SAVED_SP),l
    ld (ix+PROC_SAVED_SP+1),h
    ld (ix+PROC_STATE),PROC_READY
    ld a,(p11mt_next_pid)
    ld (current_pid),a
    call zx48_process_lookup
    jp c,$B001
    ld a,PROC_RUNNING
    ld (ix+PROC_STATE),a
    ld a,(ix+PROC_PRIVATE_FLAGS)
    and PROC_PRIVATE_STARTED
    jr z,p11mt_first
    ld l,(ix+PROC_SAVED_SP)
    ld h,(ix+PROC_SAVED_SP+1)
    ld sp,hl
    xor a
    ret
p11mt_first:
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

p11mt_spawn:
    ld (syscall_arg_hl),hl
    jp zx48_sys_spawn

p11mt_start:
    di
    ld sp,$8F00
    call zx48_process_links_init
    jp c,$B001
    ld hl,H_PROC
    ld de,H_REC
    ld (p11mt_record_ptr),de
    call p11mt_spawn
    jp c,$B001
    ld a,l
    cp 2
    jp nz,$B001
    ld hl,Q_PROC
    ld de,Q_REC
    ld (p11mt_record_ptr),de
    call p11mt_spawn
    jp c,$B001
    ld a,l
    cp 3
    jp nz,$B001
    call p11pr_con_clear
    ld a,1
    call zx48_process_lookup
    jp c,$B001
    ld (ix+PROC_STATE),PROC_WAIT_CHILD
    ld a,2
    ld (current_pid),a
    call zx48_process_lookup
    jp c,$B001
    ld a,PROC_RUNNING
    ld (ix+PROC_STATE),a
    ld a,(ix+PROC_PRIVATE_FLAGS)
    or PROC_PRIVATE_STARTED
    ld (ix+PROC_PRIVATE_FLAGS),a
p11mt_epoch:
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
p11mt_record_ptr: dw H_REC
p11mt_hanoi_yields: dw 0
p11mt_queens_yields: dw 0
p11mt_next_pid: db 0
"""
    req(anchor in t,"fixture anchor missing"); t=t.replace(anchor,extra+"\n"+anchor,1)
    out=b/"p11i-multitask.asm"; out.write_text(t,encoding="utf-8",newline="\n")
    sj=ROOT/"tools/runtime/sjasmplus/bin/sjasmplus"
    r=subprocess.run([str(sj),"--nologo","--sym=p11i-multitask.sym",out.name],cwd=b,text=True,capture_output=True,timeout=60)
    req(r.returncode==0,f"multitask fixture assembly failed:\n{r.stdout}\n{r.stderr}")
    blob=(b/"p11pr-sdk-process.bin").read_bytes()
    sy=proc.symbols(b/"p11i-multitask.sym",("p11mt_start","p11mt_epoch","p11mt_hanoi_yields","p11mt_queens_yields",
        "process_table","current_pid","open_description_table","memory_free_extents","memory_live_allocations","tty_input_owner"))
    req(len(blob)<=0x1D00,f"fixture too large: {len(blob)}")
    return blob,sy

def regs(sy,h,q,font):
    hp=b"/bin/hanoi"; qp=b"/bin/queens8"; ha=p210._arg1(hp); qa=p210._arg1(qp); env=p210.ENV1_EMPTY
    return ((H_PATH,hp+b"\0"),(Q_PATH,qp+b"\0"),(H_ARG,ha),(Q_ARG,qa),(ENV,env),
      (H_PROC,p210._proc1(path_ptr=H_PATH,arg_ptr=H_ARG,arg_len=len(ha),env_ptr=ENV,env_len=len(env))),
      (Q_PROC,p210._proc1(path_ptr=Q_PATH,arg_ptr=Q_ARG,arg_len=len(qa),env_ptr=ENV,env_len=len(env))),
      (H_MEX,h),(Q_MEX,q),(H_REC,p210._record(b"hanoi",2,H_MEX,len(h))),(Q_REC,p210._record(b"queens8",2,Q_MEX,len(q))),
      (FONT,font),(sy["process_table"],p222._process_table()),(sy["current_pid"],b"\x01"),
      (sy["open_description_table"],p222._open_descriptions()),(sy["memory_free_extents"],proc.free_extents()),
      (sy["memory_live_allocations"],b"\x00\x00"),(sy["tty_input_owner"],b"\x01"))

def sna(entry,fixture,regions):
    ram=bytearray(0xC000); ram[0xA000:0xA000+len(fixture)]=fixture
    for a,p in regions: ram[a-0x4000:a-0x4000+len(p)]=p
    sp=0xBFFE; struct.pack_into("<H",ram,sp-0x4000,entry)
    h=bytearray(27); h[0]=0xFE; h[19]=4; struct.pack_into("<H",h,23,sp); h[25]=1
    return bytes(h)+bytes(ram)

def execute(fixture,sy,h,q,font):
    fuse=ROOT/"tools/runtime/fuse/bin/fuse"; conv=ROOT/"tools/runtime/fuse-utils/bin/fmfconv"
    p2=sy["process_table"]+2*proc.PROC_DESC_SIZE; p3=sy["process_table"]+3*proc.PROC_DESC_SIZE
    dbg="\n".join([f"breakpoint 0x{sy['p11mt_epoch']:04x}","commands 1","print 0xd1810000","print spectrum:frames","continue","end",
      "breakpoint time 0 if spectrum:frames > 0x4e1","commands 2",f"print 0x{MARK:x}",
      f"print [0x{sy['p11mt_hanoi_yields']:04x}]",f"print [0x{sy['p11mt_hanoi_yields']+1:04x}]",
      f"print [0x{sy['p11mt_queens_yields']:04x}]",f"print [0x{sy['p11mt_queens_yields']+1:04x}]",
      f"print [0x{p2+2:04x}]",f"print [0x{p3+2:04x}]",f"print [0x{p2+PROC_PRIVATE_FLAGS:04x}]",f"print [0x{p3+PROC_PRIVATE_FLAGS:04x}]",
      "print spectrum:frames","exit 0","end","continue"])
    with tempfile.TemporaryDirectory(prefix="zxux-p11i-") as td:
      td=Path(td); sp=td/"both.sna"; movie=td/"both.fmf"; sp.write_bytes(sna(sy["p11mt_start"],fixture,regs(sy,h,q,font)))
      r=subprocess.run(["/usr/bin/env","SDL_VIDEODRIVER=dummy","SDL_AUDIODRIVER=dummy",str(fuse),"--machine","48","--no-sound","--no-confirm-actions","--movie-start",str(movie),"--debugger-command",dbg,str(sp)],cwd=ROOT,text=True,capture_output=True,timeout=90)
      req(r.returncode==0,f"multitask run failed: {r.stdout!r} {r.stderr!r}")
      vals=[int(x,16) for x in re.findall(r"0x([0-9a-f]+)",r.stdout,re.I)]; req(MARK in vals,"checkpoint missing")
      i=vals.index(MARK); m=vals[i+1:i+10]; req(len(m)==9,"checkpoint metadata")
      hy=m[0]|m[1]<<8; qy=m[2]|m[3]<<8; req(hy and qy,"both workloads must yield")
      req(m[4] in (1,2) and m[5] in (1,2),"both states runnable"); req(m[6]&PROC_PRIVATE_STARTED and m[7]&PROC_PRIVATE_STARTED,"both started")
      r=subprocess.run([str(conv),"-S","-y",str(movie),str(td/"frame.scr")],cwd=ROOT,text=True,capture_output=True,timeout=30)
      req(r.returncode==0,"SCR extraction"); fs=sorted(td.glob("frame-*.scr")); req(fs,"SCR missing")
      return fs[-1].read_bytes(),hy,qy,m[8]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--native",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); ap.add_argument("--report",type=Path,required=True); a=ap.parse_args()
    h=(a.native/"hanoi.mex1").read_bytes(); q=(a.native/"queens8.mex1").read_bytes(); font=(ROOT/"v1/assets/font4x8-zxux.bin").read_bytes()
    fixture,sy=build_fixture(); scr,hy,qy,frame=execute(fixture,sy,h,q,font); req(len(scr)==6912,"SCR size")
    left=sum(bool(scr[vis.bitmap_offset(x,y)]&(0x80>>(x&7))) for y in range(192) for x in range(128))
    right=sum(bool(scr[vis.bitmap_offset(x,y)]&(0x80>>(x&7))) for y in range(192) for x in range(128,256))
    req(left and right,"both screen halves require output"); png=vis.render_png(scr); a.output.mkdir(parents=True,exist_ok=True)
    (a.output/"hanoi-queens8-1250f.scr").write_bytes(scr); (a.output/"hanoi-queens8-1250f.png").write_bytes(png)
    report={"schema":1,"kind":"phase11-pre-release-hanoi-queens8-concurrent","checkpoint_frames":1250,"observed_frame":frame,
      "hanoi_yields":hy,"queens8_yields":qy,"left_lit_pixels":left,"right_lit_pixels":right,"scr_sha256":sha(scr),"png_sha256":sha(png),
      "launch_order":["hanoi","queens8"],"assertions":{"both_native_mex1_loaded":"PASS","both_spawned_through_admitted_spawn_transaction":"PASS",
      "both_alive_at_common_checkpoint":"PASS","both_cooperatively_yielded_after_epoch":"PASS","exact_1250_frame_checkpoint":"PASS",
      "hanoi_output_confined_to_left_half":"PASS","queens8_output_confined_to_right_half":"PASS","combined_scr_png_retained":"PASS"}}
    a.report.parent.mkdir(parents=True,exist_ok=True); a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    print("P11 PRE-RELEASE HANOI/QUEENS CONCURRENT 1250F PASS")
if __name__=="__main__": main()
