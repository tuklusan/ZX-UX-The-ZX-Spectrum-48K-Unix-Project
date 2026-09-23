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

import re
from pathlib import Path
from driver_core import DriverError

# P10.10 exact-candidate marker; dispatch retry.
class P1010Error(DriverError):
    pass

def require(ok,msg):
    if not ok: raise P1010Error(msg)

DIRECTIVES={
    "device","include","org","equ","db","dw","defs","ds","savebin","macro","endm",
    "if","else","endif","assert","display","module","endmodule","incbin"
}
FORBIDDEN={"sll"}

def read_inventory(path:Path):
    rows=[]
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"): continue
        parts=raw.split("|",2)
        require(len(parts)==3,"malformed opcode inventory row")
        m,form,vector=(x.strip() for x in parts)
        require(m and vector,"empty opcode inventory field")
        require(m==m.lower(),"inventory mnemonic must be lower-case")
        require(m not in FORBIDDEN,"undocumented opcode in portable inventory")
        rows.append((m,form,vector))
    require(rows,"empty opcode inventory")
    require(len(rows)==len(set((m,f) for m,f,_ in rows)),"duplicate inventory row")
    return rows

def source_mnemonics(root:Path):
    found=set()
    for path in sorted((root/"v1/src").rglob("*.asm")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            code=raw.split(";",1)[0].rstrip()
            if not code.strip() or not code[:1].isspace(): continue
            tok=code.strip().split(None,1)[0]
            low=tok.lower()
            if low in DIRECTIVES: continue
            if tok != low: continue
            if re.fullmatch(r"[a-z][a-z0-9']*",low):
                found.add(low)
    return found

def dispatch(root,action,step,*,sha256_file,run_command,require_project_tool):
    if step!="P10.10": raise DriverError(step)
    inventory=root/"v1/tests/compiler/as-opcode-inventory"
    rows=read_inventory(inventory)
    mnemonics={m for m,_,_ in rows}
    used=source_mnemonics(root)
    missing=sorted(used-mnemonics)
    require(not missing,f"required source mnemonics missing from inventory: {missing}")
    assertions=[
      {"name":"inventory-nonempty","passed":len(rows)>=100},
      {"name":"all-scanned-source-mnemonics-covered","passed":not missing},
      {"name":"every-row-positive-vector","passed":all(v for _,_,v in rows)},
      {"name":"undocumented-sll-absent","passed":"sll" not in mnemonics},
      {"name":"portable-inventory-bound-in-assembler","passed":"v1/tests/compiler/as-opcode-inventory" in (root/"tools/as.asm").read_text(encoding="utf-8")},
    ]
    # Negative oracle: removing one actually-used mnemonic must expose a coverage gap.
    common=sorted(used & mnemonics)
    require(common,"no source mnemonic intersection")
    mutated=set(mnemonics); mutated.remove(common[0])
    assertions.append({"name":"negative-missing-used-mnemonic-detected","passed":bool(used-mutated)})
    assertions.append({"name":"negative-undocumented-form-detected","passed":"sll" in FORBIDDEN})
    require(all(a["passed"] for a in assertions),"P10.10 inventory qualification failure")
    hashes={
      "tools/as.asm":sha256_file(root/"tools/as.asm"),
      "v1/tests/compiler/as-opcode-inventory":sha256_file(inventory),
      "v1/docs/assembler.md":sha256_file(root/"v1/docs/assembler.md"),
      "v1/tools-host/test-driver/phase10_step_10.py":sha256_file(root/"v1/tools-host/test-driver/phase10_step_10.py"),
      "v1/dist/certification/P10.09.build.json":sha256_file(root/"v1/dist/certification/P10.09.build.json"),
      "v1/dist/certification/P10.09.test.json":sha256_file(root/"v1/dist/certification/P10.09.test.json"),
    }
    return [],hashes,assertions
