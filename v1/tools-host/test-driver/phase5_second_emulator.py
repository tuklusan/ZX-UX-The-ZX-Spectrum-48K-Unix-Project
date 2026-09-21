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
from pathlib import Path
import importlib.util, os, re, socket, subprocess, sys, time
from driver_core import DriverError
import phase1

class P518Error(DriverError): pass
def require(v,m):
    if not v: raise P518Error(m)
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise P518Error(f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def _recv_prompt(sock, timeout=20.0):
    sock.settimeout(0.5); data=bytearray(); end=time.monotonic()+timeout
    while time.monotonic()<end:
        try: chunk=sock.recv(65536)
        except socket.timeout:
            continue
        if not chunk: break
        data += chunk
        tail=bytes(data[-160:]).rstrip()
        if tail.endswith(b">") and b"command" in tail:
            return data.decode("utf-8","replace")
    raise P518Error("ZEsarUX ZRCP prompt timeout: "+data.decode("utf-8","replace")[-500:])

def _cmd(sock, text, timeout=20.0):
    sock.sendall(text.encode("utf-8")+b"\n")
    return _recv_prompt(sock,timeout)

def _connect(port=10000, timeout=15.0):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            s=socket.create_connection(("127.0.0.1",port),timeout=1)
            _recv_prompt(s,5)
            return s
        except OSError:
            time.sleep(0.1)
    raise P518Error("ZEsarUX ZRCP did not open port 10000")

def _hex_payload(response):
    body=response.split("command",1)[0]
    runs=re.findall(r"(?<![0-9A-Fa-f])([0-9A-Fa-f]{32})(?![0-9A-Fa-f])",body)
    if runs: return bytes.fromhex(runs[-1])
    compact="".join(re.findall(r"[0-9A-Fa-f]",body))
    return bytes.fromhex(compact[-32:]) if len(compact)>=32 else b""

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.18": raise DriverError(step)
    descriptor=root/"v1/tests/cassette/compat/zesarux-13.0.json"
    import json
    d=json.loads(descriptor.read_text())
    require(d["emulator"]=="ZEsarUX" and d["version"]=="13.0","P5.18 compatibility descriptor mismatch")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    p515=load(root/"v1/tools-host/test-driver/phase5_fixture_tape.py","zxux_p518_p515")
    maketap=p515.load(root/"v1/tools-host/maketap/maketap.py","zxux_p518_maketap")
    assets={"screen":root/"v1/assets/loading.scr","font":root/"v1/assets/font4x8-zxux.bin","issue":root/"v1/assets/issue.txt","crontab":root/"v1/assets/crontab.txt","bincat":root/"v1/assets/bincat.bin"}
    loader=(root/"v1/src/boot/loader.bas").read_text(encoding="utf-8")
    tape=maketap.build_phase5_fixture_tape(loader_source=loader,screen=assets["screen"].read_bytes(),kernel=kernel.read_bytes(),
      font=assets["font"].read_bytes(),issue=assets["issue"].read_bytes(),crontab=assets["crontab"].read_bytes(),bincat=assets["bincat"].read_bytes())
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    tap=build/"phase5-fixture.tap"; tap.write_bytes(tape)
    assertions=[
      {"name":"compat-product-version-recorded","passed":d["emulator"]=="ZEsarUX" and d["version"]=="13.0"},
      {"name":"compat-binary-sha256-pinned","passed":len(d["sha256"])==64},
      {"name":"same-core-phase5-tap-fixture","passed":tap.is_file() and len(tape)>0},
      {"name":"fuse-oracle-prerequisite-admitted","passed":(root/"v1/dist/certification/P5.17.test.json").is_file()},
      {"name":"disagreement-is-fail-closed","passed":"FAIL-CLOSED" in d["result_policy"]},
    ]
    commands=[kr]
    if action=="test":
        exe=os.environ.get("ZXUX_ZESARUX_BIN","")
        require(exe and Path(exe).is_file(),"P5.18 pinned ZEsarUX binary unavailable")
        vr=run_command([exe,"--version"],cwd=root,timeout_seconds=15)
        require(not vr.timed_out and vr.exit_code==0 and "13" in (vr.stdout+vr.stderr),f"P5.18 ZEsarUX version failure: {vr.stdout} {vr.stderr}")
        commands.append(vr)
        proc=subprocess.Popen([exe,"--noconfigfile","--vo","null","--ao","null","--enable-remoteprotocol"],
          cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            sock=_connect()
            try:
                _cmd(sock,"enter-cpu-step")
                _cmd(sock,"enable-breakpoints")
                _cmd(sock,"set-breakpoint 1 PC=E003H")
                _cmd(sock,"set-breakpointaction 1 break")
                _cmd(sock,f"smartload {tap.resolve()}",30)
                runresp=_cmd(sock,"run no-stop-on-data 12000000",45)
                regs=_cmd(sock,"get-registers")
                kmem=_cmd(sock,"read-memory E000H 16")
                smem=_cmd(sock,"read-memory 4000H 16")
                require("E003" in (runresp+regs).upper(),"P5.18 ZEsarUX did not reach kernel entry E003")
                require(_hex_payload(kmem)==kernel.read_bytes()[:16],"P5.18 ZEsarUX kernel bytes disagree with FUSE/source oracle")
                require(_hex_payload(smem)==assets["screen"].read_bytes()[:16],"P5.18 ZEsarUX screen bytes disagree with FUSE/source oracle")
                try: _cmd(sock,"exit-emulator",5)
                except P518Error: pass
            finally:
                sock.close()
        finally:
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
        assertions += [
          {"name":"zesarux-13-second-emulator-ran","passed":True},
          {"name":"core-loader-reached-e003","passed":True},
          {"name":"kernel-prefix-matches-fuse-oracle","passed":True},
          {"name":"screen-prefix-matches-fuse-oracle","passed":True},
        ]
    require(all(a["passed"] for a in assertions),"P5.18 compatibility assertion failure")
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),
      "v1/build/phase5-fixture.tap":sha256_file(tap),
      "v1/tests/cassette/compat/zesarux-13.0.json":sha256_file(descriptor),
      "v1/tools-host/test-driver/phase5_second_emulator.py":sha256_file(root/"v1/tools-host/test-driver/phase5_second_emulator.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.17.build.json":sha256_file(root/"v1/dist/certification/P5.17.build.json"),
      "v1/dist/certification/P5.17.test.json":sha256_file(root/"v1/dist/certification/P5.17.test.json"),
    }
    return commands,hashes,assertions
