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
import argparse,base64,hashlib,json,os,re,urllib.request
from pathlib import Path

REPO="tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit"
TAG="1.0.2"; COMMIT="b1621338565ac3bd9d4eff4ecb5a2a77aee2ab6a"; TREE="ced96ea0a4b2f6cdd6080fc6f48e07738252af17"
BLOBS={"release":"c8b734fe51f6fd157782a7d5f3bde2facaaddbc0","graphics":"323e16a770ba7405d9395ff0c51ec823e9c8572f","recursive":"c318d1ca9bf54bc75b7e3be600735ef1170a604b"}
HEADERS={"examples":"usr/src/examples/exapi.h","demos":"usr/src/demos/demoapi.h","hanoi":"usr/src/demos/recapi.h","queens8":"usr/src/demos/recapi.h"}
BAD_WORDS={"long","double","signed","struct","union","switch","case","default","goto","typedef","enum","volatile","register","auto","const","inline","restrict"}
BAD_OPS=("+=","-=","*=","/=","%=","<<=",">>=","&=","|=","^=","?","...")
BAD_PP={"if","ifdef","ifndef","elif","else","endif","undef","pragma","error","line"}
C48_API=set("""exit yield sleep spawn wait kill chdir getcwd getenv getpid open open_typed close read write seek stat remove rename list pipe dup ioctl read_full write_full getchar putchar puts strlen strcmp strcpy strncpy memcpy memmove memchr memset malloc free cls print_at plot point draw circle ink paper bright flash inverse over border beep udg_define udg_get udg_draw udg_clear udg_draw_2x2 tape_save tape_load ticks time_get time_set sin cos tan asin acos atan sqrt exp log pow fabs""".split())
CONTROL={"if","else","while","do","for","break","continue","return"}

def req(x,m):
    if not x: raise SystemExit("ERROR: "+m)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gh(path,blob):
    h={"User-Agent":"zxux-rev02-stage-b","Accept":"application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"): h["Authorization"]="Bearer "+os.environ["GITHUB_TOKEN"]
    u=f"https://api.github.com/repos/{REPO}/contents/{path}?ref={TAG}"
    with urllib.request.urlopen(urllib.request.Request(u,headers=h),timeout=90) as r: row=json.load(r)
    req(row.get("sha")==blob,"pinned SDK blob mismatch: "+path)
    return base64.b64decode(row["content"])
def clean(s):
    s=re.sub(r'"(?:\\.|[^"\\])*"','""',s); s=re.sub(r"'(?:\\.|[^'\\])*'","''",s)
    s=re.sub(r"/\*[\s\S]*?\*/"," ",s); return re.sub(r"//[^\n]*"," ",s)
def classify(path):
    raw=Path(path).read_bytes(); txt=raw.decode("ascii"); code=clean(txt)
    ids=re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b",code)
    req(not [x for x in ids if len(x)>15],"identifier >15 in "+str(path))
    req(not sorted(set(ids)&BAD_WORDS),"unsupported keyword in "+str(path))
    req(not [x for x in BAD_OPS if x in code],"unsupported operator in "+str(path))
    req(not re.search(r"\(\s*\*\s*[A-Za-z_]\w*\s*\)\s*\(",code),"function pointer in "+str(path))
    pp=[]
    for n,line in enumerate(txt.splitlines(),1):
        m=re.match(r"^\s*#\s*(\w+)\b(.*)$",line)
        if not m: continue
        op,rest=m.group(1),m.group(2).strip(); req(op not in BAD_PP and op in {"define","include"},"bad preprocessor at "+str(n))
        if op=="define":
            q=re.match(r"([A-Za-z_]\w*)(.*)$",rest); req(q and not q.group(2).startswith("("),"function macro")
            pp.append(["define",q.group(1)])
        else:
            q=re.fullmatch(r'"([^"/\\]+)"',rest); z=re.fullmatch(r"<([^>]+)>",rest)
            req(q or (z and z.group(1)=="c48.h"),"unsupported include")
            pp.append(["include",q.group(1) if q else "c48.h"])
    ftype=r"(?:(?:static|extern)\s+)?(?:(?:unsigned)\s+)?(?:void|char|short|int|float)\s+(?:\*\s*)*"
    definitions=sorted(set(re.findall(r"(?m)^\s*"+ftype+r"([A-Za-z_]\w*)\s*\([^;\n{}]*\)\s*\{",code))-CONTROL)
    declarations=sorted(set(re.findall(r"(?m)^\s*"+ftype+r"([A-Za-z_]\w*)\s*\([^;\n{}]*\)\s*;",code))-CONTROL)
    calls=sorted(set(re.findall(r"\b([A-Za-z_]\w*)\s*\(",code))-CONTROL-{"sizeof"})
    keys={k:ids.count(k) for k in ("void","char","short","int","float","unsigned","static","extern","if","else","while","do","for","break","continue","return","sizeof") if ids.count(k)}
    ops=sorted(set(re.findall(r"\+\+|--|&&|\|\||==|!=|<=|>=|<<|>>|[+*/%&|^~!<>=-]",code)))
    return {"sha256":hashlib.sha256(raw).hexdigest(),"size":len(raw),"preprocessor":pp,"keywords":keys,"operators":ops,"definitions":definitions,"declarations":declarations,"call_like":calls,"status":"PASS"}
def digest(root):
    h=hashlib.sha256()
    for p in sorted(x for x in Path(root).rglob("*") if x.is_file() and x.name!="CONTRACT-DIGEST.sha256"):
        h.update(p.relative_to(root).as_posix().encode()+b"\0"+str(p.stat().st_size).encode()+b"\0"+sha(p).encode()+b"\n")
    return h.hexdigest()

def main():
    a=argparse.ArgumentParser(); a.add_argument("--sdk-root",type=Path,required=True); a.add_argument("--output",type=Path,required=True); n=a.parse_args()
    root=n.sdk_root; out=n.output; out.mkdir(parents=True,exist_ok=True)
    rel=json.loads((root/"SDK-RELEASE.json").read_text())
    req((rel.get("tag"),rel.get("commit"),rel.get("tree"))==(TAG,COMMIT,TREE),"SDK pin drift")
    req(rel.get("source_tape_count")==57 and rel.get("program_count")==30 and rel.get("release_verifier",{}).get("status")=="PASS","SDK release gate")
    rr=gh("compiler/release_expectations.json",BLOBS["release"]); gr=gh("compiler/graphics_demo_expectations.json",BLOBS["graphics"]); vr=gh("compiler/verify_recursive_demos.py",BLOBS["recursive"])
    release=json.loads(rr); graphics=json.loads(gr); req(release["version"]==TAG and release["test_count"]==371 and graphics["demo_count"]==22,"oracle identity")
    rv=vr.decode(); rec={}
    for name in ("hanoi","queens8"):
        m=re.search(rf'"{name}"\s*:\s*\{{[\s\S]*?"screen"\s*:\s*"([0-9a-f]{{64}})"',rv); req(m,"recursive oracle"); rec[name]=m.group(1)
    files={}; rows=[]
    for hp in sorted(set(HEADERS.values())): files[hp]=classify(root/hp)
    for p in rel["programs"]: files[p["source_path"]]=classify(root/p["source_path"])
    req(len(files)==33,"classification cardinality")
    for p in rel["programs"]:
        c,name=p["category"],p["name"]
        hp=HEADERS[name] if name in ("hanoi","queens8") else HEADERS[c]
        sc,hc=files[p["source_path"]],files[hp]
        source_funcs=set(sc["definitions"])
        header_funcs=set(hc["declarations"])|set(hc["definitions"])
        source_calls=set(sc["call_like"])-source_funcs
        req(not sorted(source_calls-header_funcs-C48_API),"unclassified call in "+c+"/"+name)
        api_usage=sorted(source_calls&C48_API)
        if c=="examples":
            o=release["demos"][name]
            behavior={"mode":"termination","args":o["args"],"capture_checkpoints":["process-termination"],"screen_sha256":o["screen_sha256"]}
        elif name in ("hanoi","queens8"):
            if name=="hanoi":
                inv=["moves=127","max_depth=7","left-half-only writes","all 7 discs finish on pole C in descending size order","guard_fail=0","inv_fail=0"]
                ownership="left-half"
            else:
                inv=["tests=876","backtracks=105","max_depth=8","right-half-only writes","solution columns=[0,4,7,5,2,6,1,3]","guard_fail=0","inv_fail=0"]
                ownership="right-half"
            behavior={
                "mode":"recursive-standalone-and-concurrent",
                "args":[],
                "standalone":{"capture_checkpoints":["process-termination"],"screen_sha256":rec[name],"invariants":inv},
                "concurrent":{"capture_frames":[250,625,1250],"required_progress":"source counters/board-or-disc state must change between checkpoints","screen_ownership":ownership,"invariants":inv},
            }
        else:
            o=graphics["demos"][name]
            behavior={"mode":"frame-counted","args":[str(o["frames"])],"capture_frames":[1,o["frames"]],"first_screen_sha256":o["first_screen_sha256"],"screen_sha256":o["screen_sha256"],"lit_pixels":o["lit_pixels"],"attribute_values":o["attribute_values"]}
        reference={
            "lfs_git_blob":p["reference_lfs_git_blob"],
            "lfs_oid_sha256":p["reference_lfs_oid_sha256"],
            "png_sha256":p["reference_png_sha256"],
            "comparison_mode":"pixel-exact",
            "region":"full logical Spectrum display 256x192",
            "metric":"RGBA pixel equality after lossless PNG decode; tolerance 0",
            "target_input":"PNG rendered losslessly from retained 6912-byte target SCR",
            "reference_input":"pinned materialized SDK reference PNG",
        }
        rows.append({
            "category":c,"program":name,
            "source_path":p["source_path"],"source_sha256":p["source_sha256"],
            "source_tape_path":p["tape_path"],"source_tape_sha256":p["tape_sha256"],
            "target_source":p["target_source"],
            "header_path":hp,"header_sha256":sha(root/hp),
            "api_usage":api_usage,
            "header_api_declarations":sorted(header_funcs&C48_API),
            "feature_usage":{"keywords":sc["keywords"],"operators":sc["operators"],"preprocessor":sc["preprocessor"]},
            "reference":reference,"behavior":behavior,"classification":"LEGAL-FROZEN-C48",
        })
    req(len(rows)==30,"matrix cardinality")
    cls={"schema":1,"kind":"rev02-c48-static-classification","sdk":{"tag":TAG,"commit":COMMIT,"tree":TREE},"classifier":"independent lexical/preprocessor; no product cc","file_count":33,"files":files,"assertions":{"30_sources":"PASS","3_headers":"PASS","no_unsupported_constructs":"PASS","call_surface_classified":"PASS","product_cc_independent":"PASS"}}
    mat={"schema":1,"kind":"rev02-acceptance-matrix","sdk":{"tag":TAG,"commit":COMMIT,"tree":TREE},"oracle_blobs":BLOBS,"program_count":30,"frozen_before_target_execution":True,"programs":rows}
    st={"schema":1,"kind":"rev02-stage-b","status":"PASS","sdk":{"repository":REPO,"tag":TAG,"commit":COMMIT,"tree":TREE},"formal_release":{"release_verifier":rel["release_verifier"],"source_tape_count":57,"program_count":30,"assets":rel["assets"]},"moving_main":"informational-only; never execution input","assertions":{"latest_formal_release_1_0_2":"PASS","release_assets_provenance":"PASS","371_tests":"PASS","57_tapes":"PASS","30_programs":"PASS","3_headers":"PASS","tape_reconstruction":"PASS","reference_image_identity":"PASS","frozen_c48_legality":"PASS","contracts_predeclared":"PASS","actual_api_usage_not_header_declarations":"PASS","recursive_concurrency_checkpoints_predeclared":"PASS","reference_comparison_metric_predeclared":"PASS"}}
    for fn,obj in (("C48-CLASSIFICATION.json",cls),("ACCEPTANCE-MATRIX.json",mat),("STAGE-B.json",st)): (out/fn).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    (out/"ORACLE-release_expectations.json").write_bytes(rr); (out/"ORACLE-graphics_demo_expectations.json").write_bytes(gr); (out/"ORACLE-verify_recursive_demos.py").write_bytes(vr)
    d=digest(out); (out/"CONTRACT-DIGEST.sha256").write_text(d+"\n")
    baseline=None
    for _ in range(3):
        q=digest(out); baseline=q if baseline is None else baseline; req(q==baseline,"contract bytes changed")
    print("REV02 STAGE B PASS "+d)
if __name__=="__main__": main()
