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
from pathlib import Path
from driver_core import DriverError
import phase6_issue

class P608Error(DriverError): pass
def require(v,m):
    if not v: raise P608Error(m)

def tokenize(line: bytes) -> list[bytes]:
    out=[]; cur=bytearray(); in_token=False; q=None; i=0
    while i<len(line):
        c=line[i]
        if q=="single":
            if c==0x27: q=None
            else: cur.append(c)
            i+=1; continue
        if q=="double":
            if c==0x22:
                q=None; i+=1; continue
            if c==0x5c:
                i+=1
                if i>=len(line): raise ValueError("E_INVAL")
                n=line[i]
                if n in (0x22,0x5c,0x24):
                    cur.append(n); i+=1; continue
                cur.append(0x5c)
                continue
            cur.append(c); i+=1; continue
        if c in (0x20,0x09):
            if in_token:
                out.append(bytes(cur)); cur.clear(); in_token=False
            i+=1; continue
        if c==0x5c:
            in_token=True; i+=1
            if i>=len(line): raise ValueError("E_INVAL")
            cur.append(line[i]); i+=1; continue
        if c==0x27:
            in_token=True; q="single"; i+=1; continue
        if c==0x22:
            in_token=True; q="double"; i+=1; continue
        in_token=True; cur.append(c); i+=1
    if q is not None: raise ValueError("E_INVAL")
    if in_token: out.append(bytes(cur))
    return out

def dispatch(root:Path,action:str,step:str,*,sha256_file,run_command,require_project_tool):
    if step!="P6.08": raise DriverError(f"Phase-6 tokenizer step is not registered: {step}")
    sp=root/"v1/src/shell/sh.asm"; doc=root/"v1/docs/shell.md"; text=sp.read_text(); docs=doc.read_text()
    macro=text.split("MACRO EMIT_P608_TOKENIZER_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions=[
      {"name":"byte-parser-no-hidden-shell","passed":"sh_p608_tokenize:" in macro and "SYSCALL" not in macro},
      {"name":"plain-backslash-quotes-next-byte","passed":"sh_p608_escape_plain:" in macro and "sh_p608_invalid" in macro},
      {"name":"single-quotes-literal","passed":"P608_Q_SINGLE" in text and "sh_p608_single:" in macro},
      {"name":"double-backslash-exact-special-set","passed":"cp $22" in macro and "cp $5c" in macro and "cp '$'" in macro},
      {"name":"double-nonspecial-backslash-preserved","passed":"ld a,$5c" in macro},
      {"name":"unmatched-quote-invalid","passed":"ld a,E_INVAL" in macro},
      {"name":"documentation-frozen-contract","passed":"trailing backslash" in docs and "Empty quoted strings" in docs and "field splitting" in docs},
    ]
    require(all(a["passed"] for a in assertions),"P6.08 static contract failure")
    asm=require_project_tool(root,"tools/runtime/sjasmplus/bin/sjasmplus"); build=root/"v1/build"; build.mkdir(parents=True,exist_ok=True)
    sf=build/"p608-tokenizer.asm"
    sf.write_text("""    DEVICE ZXSPECTRUM48
    INCLUDE "../include/zx48ux.inc"
    INCLUDE "../src/shell/sh.asm"
    ORG $C000
p608_start:
    EMIT_P608_TOKENIZER_ROUTINES
p608_end:
    SAVEBIN "p608-tokenizer.bin",p608_start,p608_end-p608_start
""",encoding="utf-8",newline="\n")
    sr=run_command([asm,"--nologo","--lst=p608-tokenizer.lst","--sym=p608-tokenizer.sym","p608-tokenizer.asm"],cwd=build,timeout_seconds=30)
    require(not sr.timed_out and sr.exit_code==0,f"P6.08 tokenizer assembly failed: {sr.stderr or sr.stdout}")
    image=(build/"p608-tokenizer.bin").read_bytes()
    mex=phase6_issue.mex1(image)
    maketap=phase6_issue.load_module(root/"v1/tools-host/maketap/maketap.py","zxux_p608_maketap")
    tap=maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex))
    tp=build/"p608-tokenizer.tap"
    tp.write_bytes(tap)
    require(tap==maketap.m48o_blocks(maketap.M48OObject("sh",maketap.M48O_BIN,maketap.DIR_BIN,mex)),"P6.08 TAP rebuild mismatch")
    if action=="test":
        corpus=[
          (b"echo alpha beta",[b"echo",b"alpha",b"beta"]),
          (b"echo\talpha",[b"echo",b"alpha"]),
          (b"echo a\\ b",[b"echo",b"a b"]),
          (b"echo 'a b' c",[b"echo",b"a b",b"c"]),
          (b'echo "a b" c',[b"echo",b"a b",b"c"]),
          (b"echo ''",[b"echo",b""]),
          (b"echo a''b",[b"echo",b"ab"]),
          (b'echo "a\\$b"',[b"echo",b"a$b"]),
          (b'echo "a\\qb"',[b"echo",b"a\\qb"]),
          (b"echo '$USER'",[b"echo",b"$USER"]),
          (b'echo "$USER"',[b"echo",b"$USER"]),
          (b"echo \\|",[b"echo",b"|"]),
          (b"echo ';'",[b"echo",b";"]),
        ]
        for source,want in corpus:
            got=tokenize(source)
            require(got==want,f"P6.08 golden token mismatch for {source!r}: {got!r} != {want!r}")
        for bad in (b"echo \\",b"echo 'abc",b'echo "abc',b'echo "abc\\'):
            try: tokenize(bad)
            except ValueError as exc: require(str(exc)=="E_INVAL","wrong tokenizer error")
            else: raise P608Error(f"P6.08 invalid corpus accepted: {bad!r}")
        assertions += [
          {"name":"golden-token-corpus","passed":True,"cases":len(corpus)},
          {"name":"unterminated-quote-and-trailing-backslash-e-inval","passed":True,"cases":4},
        ]
    hashes={
      "v1/src/shell/sh.asm":sha256_file(sp),
      "v1/docs/shell.md":sha256_file(doc),
      "v1/build/p608-tokenizer.tap":sha256_file(tp),
      "v1/tools-host/test-driver/phase6_tokenizer.py":sha256_file(root/"v1/tools-host/test-driver/phase6_tokenizer.py"),
      "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
      "v1/dist/certification/P6.07.build.json":sha256_file(root/"v1/dist/certification/P6.07.build.json"),
      "v1/dist/certification/P6.07.test.json":sha256_file(root/"v1/dist/certification/P6.07.test.json"),
      "v1/dist/media/P6.07/manifest.json":sha256_file(root/"v1/dist/media/P6.07/manifest.json")}
    return [sr],hashes,assertions
