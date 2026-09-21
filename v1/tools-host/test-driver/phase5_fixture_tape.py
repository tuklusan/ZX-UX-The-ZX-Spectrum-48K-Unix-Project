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
import importlib.util
import struct
import sys
from driver_core import DriverError
import phase1
import phase0_media

class P515Error(DriverError): pass
def require(x,m):
    if not x: raise P515Error(m)
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise P515Error(f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.15": raise DriverError(f"Phase-5 fixture-tape step is not registered: {step}")
    maketap=load(root/"v1/tools-host/maketap/maketap.py","zxux_p515_maketap")
    cassette=load(root/"v1/tools-host/cassette-image/cassette_image.py","zxux_p515_cassette")
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool)
    assets={
      "screen":root/"v1/assets/loading.scr","font":root/"v1/assets/font4x8-zxux.bin",
      "issue":root/"v1/assets/issue.txt","crontab":root/"v1/assets/crontab.txt","bincat":root/"v1/assets/bincat.bin",
    }
    loader=(root/"v1/src/boot/loader.bas").read_text(encoding="utf-8")
    kwargs=dict(loader_source=loader,screen=assets["screen"].read_bytes(),kernel=kernel.read_bytes(),
      font=assets["font"].read_bytes(),issue=assets["issue"].read_bytes(),
      crontab=assets["crontab"].read_bytes(),bincat=assets["bincat"].read_bytes())
    first=maketap.build_phase5_fixture_tape(**kwargs); second=maketap.build_phase5_fixture_tape(**kwargs)
    require(first==second,"P5.15 fixture rebuild mismatch")
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    tap=build/"phase5-fixture.tap"; tap.write_bytes(first)
    prefix=maketap.build_bootstrap_prefix(loader_source=loader,screen=kwargs["screen"],kernel=kwargs["kernel"])
    native=cassette.assert_bootstrap_prefix(prefix)
    objects=phase0_media._parse_m48o_stream(maketap,len(prefix),first)
    expected=[("sh",2,1),("font4x8",9,7),("issue",1,3),("crontab",10,3),("bincat",11,7)]
    require([(n,t,d) for n,t,d,_ in objects[:5]]==expected,"P5.15 exact five-resource prefix mismatch")
    require([n for n,_,_,_ in objects[5:]]==list(maketap.PHASE5_FIXTURE_STUB_NAMES),"P5.15 deterministic stub order mismatch")
    assertions=[
      {"name":"two-builds-byte-identical","passed":True},
      {"name":"native-prefix-exact","passed":[x.name for x in native]==["zx48ux","zx48uxscr","kernel"]},
      {"name":"five-resource-prefix-exact","passed":True},
      {"name":"later-resources-contract-valid-stubs","passed":True},
      {"name":"fixture-explicitly-non-final","passed":maketap.PHASE5_FIXTURE_LABEL.endswith("non-final")},
    ]
    commands=[kr]
    if action=="test":
      try: maketap.build_phase5_fixture_tape(**kwargs,fixture_label="zxux-final-release")
      except maketap.TapeError: assertions.append({"name":"reject-final-release-label","passed":True})
      else: raise P515Error("P5.15 final-release label unexpectedly accepted")
      tapeconv=require_project_tool(root,"tools/runtime/fuse-utils/bin/tapeconv")
      tzxlist=require_project_tool(root,"tools/runtime/fuse-utils/bin/tzxlist")
      tzx=build/"phase5-fixture.tzx"; rt=build/"phase5-fixture-roundtrip.tap"
      c1=run_command([tapeconv,tap,tzx],cwd=root,timeout_seconds=30)
      require(not c1.timed_out and c1.exit_code==0,f"P5.15 TAP->TZX failed: {c1.stderr or c1.stdout}")
      c2=run_command([tzxlist,tzx],cwd=root,timeout_seconds=30)
      require(not c2.timed_out and c2.exit_code==0,f"P5.15 tzxlist failed: {c2.stderr or c2.stdout}")
      c3=run_command([tapeconv,tzx,rt],cwd=root,timeout_seconds=30)
      require(not c3.timed_out and c3.exit_code==0,f"P5.15 TZX->TAP failed: {c3.stderr or c3.stdout}")
      require(rt.read_bytes()==first,"P5.15 FUSE-utils TZX/TAP roundtrip mismatch")
      commands += [c1,c2,c3]
      assertions += [
        {"name":"fuse-utils-independent-inspect","passed":True},
        {"name":"fuse-utils-tzx-tap-roundtrip","passed":True},
      ]
    require(all(a["passed"] for a in assertions),"P5.15 assertion failure")
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),"v1/build/phase5-fixture.tap":sha256_file(tap),
      "v1/tools-host/maketap/maketap.py":sha256_file(root/"v1/tools-host/maketap/maketap.py"),
      "v1/tools-host/cassette-image/cassette_image.py":sha256_file(root/"v1/tools-host/cassette-image/cassette_image.py"),
      "v1/tools-host/test-driver/phase5_fixture_tape.py":sha256_file(root/"v1/tools-host/test-driver/phase5_fixture_tape.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.14.build.json":sha256_file(root/"v1/dist/certification/P5.14.build.json"),
      "v1/dist/certification/P5.14.test.json":sha256_file(root/"v1/dist/certification/P5.14.test.json"),
    }
    for name,path in assets.items(): hashes[str(path.relative_to(root))]=sha256_file(path)
    return commands,hashes,assertions
