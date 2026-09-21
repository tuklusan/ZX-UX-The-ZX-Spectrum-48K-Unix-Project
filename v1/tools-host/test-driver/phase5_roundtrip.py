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
import importlib.util, struct, sys
from driver_core import DriverError
from fuse_harness import PASS_PC, run_sna, jp
import phase1

class P516Error(DriverError): pass
def require(x,m):
    if not x: raise P516Error(m)
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise P516Error(f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def parse_stream(maketap,data:bytes):
    pos=0; out=[]
    while pos<len(data):
      require(pos+2<=len(data),"truncated block")
      n=struct.unpack_from("<H",data,pos)[0]; block=data[pos+2:pos+2+n]; pos+=2+n
      require(len(block)==n and n>=2 and block[0]==0xff,"bad M48O block framing")
      x=0
      for b in block: x^=b
      require(x==0,"TAP checksum mismatch")
      h=block[1:-1]; require(len(h)==32 and h[:4]==b"M48O","header missing")
      saved=struct.unpack_from("<H",h,26)[0]; hc=bytearray(h); hc[26:28]=b"\0\0"
      require(maketap.crc16_ccitt_false(bytes(hc))==saved,"header CRC mismatch")
      physical=struct.unpack_from("<H",h,8)[0]; logical=struct.unpack_from("<H",h,10)[0]
      require(h[6]==0 and struct.unpack_from("<H",h,12)[0]==0 and physical==logical,"P5.16 RAW representation expected")
      name=h[16:26].split(b"\0",1)[0].decode("ascii")
      payload=bytearray()
      while len(payload)<physical:
        require(pos+2<=len(data),"truncated payload block")
        n=struct.unpack_from("<H",data,pos)[0]; block=data[pos+2:pos+2+n]; pos+=2+n
        require(len(block)==n and block[0]==0xff,"bad payload framing")
        x=0
        for b in block: x^=b
        require(x==0,"payload TAP checksum mismatch")
        payload.extend(block[1:-1]); require(len(payload)<=physical,"payload overrun")
      require(maketap.crc16_ccitt_false(bytes(payload))==struct.unpack_from("<H",h,14)[0],"logical CRC mismatch")
      out.append((name,h[5],h[7],bytes(payload)))
    return out

def validate_mex(maketap,payload:bytes):
    require(len(payload)>=24 and payload[:4]==b"MEX1","MEX1 missing")
    h=bytearray(payload[:24]); saved=struct.unpack_from("<H",h,22)[0]; h[22:24]=b"\0\0"
    require(maketap.crc16_ccitt_false(bytes(h))==saved,"MEX1 header CRC")
    image_size=struct.unpack_from("<H",payload,8)[0]; reloc=struct.unpack_from("<H",payload,16)[0]
    body=payload[24:24+image_size+reloc*2]
    require(maketap.crc16_ccitt_false(body)==struct.unpack_from("<H",payload,20)[0],"MEX1 body CRC")
    return payload[24:24+image_size]

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P5.16": raise DriverError(f"Phase-5 cassette-roundtrip step is not registered: {step}")
    maketap=load(root/"v1/tools-host/maketap/maketap.py","zxux_p516_maketap")
    objects=(
      maketap.M48OObject("ReadMe",maketap.M48O_TXT,maketap.DIR_USERHOME,b"Alpha\nBeta\n"),
      maketap.M48OObject("RunMe",maketap.M48O_BIN,maketap.DIR_BIN,maketap.minimal_shell_mex1()),
      maketap.M48OObject("GlyphSet",maketap.M48O_UDG,maketap.DIR_USERHOME,bytes(range(256))),
    )
    stream=b"".join(maketap.m48o_blocks(o) for o in objects)
    build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True); tape=build/"p516-roundtrip.tap"; tape.write_bytes(stream)
    decoded=parse_stream(maketap,stream)
    expected=[(o.name,o.object_type,o.target_directory,o.payload) for o in objects]
    require(decoded==expected,"P5.16 exact case/logical-byte roundtrip mismatch")
    assertions=[
      {"name":"txt-exact-case-and-bytes","passed":decoded[0]==expected[0]},
      {"name":"bin-exact-case-and-bytes","passed":decoded[1]==expected[1]},
      {"name":"udg-exact-case-and-bytes","passed":decoded[2]==expected[2]},
      {"name":"raw-logical-crc-roundtrip","passed":True},
      {"name":"wrong-case-load-miss","passed":not any(name=="runme" for name,_,_,_ in decoded)},
    ]
    kr,kernel,_=phase1._assemble_kernel(root,run_command,require_project_tool); commands=[kr]
    if action=="test":
      image=validate_mex(maketap,decoded[1][3])
      def patch(ram):
        off=0xE000-0x4000; ram[off:off+3]=jp(PASS_PC)
      fr=run_sna(root,image,patch=patch); commands.append(fr)
      corrupt=bytearray(stream); corrupt[-2]^=1
      try: parse_stream(maketap,bytes(corrupt))
      except P516Error: assertions.append({"name":"corrupt-crc-rejected","passed":True})
      else: raise P516Error("P5.16 corrupt cassette unexpectedly passed")
      assertions.append({"name":"roundtripped-bin-executes-in-fuse","passed":True})
    require(all(a["passed"] for a in assertions),"P5.16 assertion failure")
    hashes={
      "v1/build/kernel.bin":sha256_file(kernel),"v1/build/p516-roundtrip.tap":sha256_file(tape),
      "v1/tools-host/maketap/maketap.py":sha256_file(root/"v1/tools-host/maketap/maketap.py"),
      "v1/tools-host/test-driver/phase5_roundtrip.py":sha256_file(root/"v1/tools-host/test-driver/phase5_roundtrip.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P5.15.build.json":sha256_file(root/"v1/dist/certification/P5.15.build.json"),
      "v1/dist/certification/P5.15.test.json":sha256_file(root/"v1/dist/certification/P5.15.test.json"),
    }
    return commands,hashes,assertions
