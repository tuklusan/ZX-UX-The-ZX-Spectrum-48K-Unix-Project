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
import argparse, base64, hashlib, json, os, shutil, struct, subprocess, sys, urllib.request, zipfile
from pathlib import Path

REPO="tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit"
TAG="1.0.2"
COMMIT="b1621338565ac3bd9d4eff4ecb5a2a77aee2ab6a"
TREE="ced96ea0a4b2f6cdd6080fc6f48e07738252af17"
TAPE_BLOB="8275c5b4985abb74d66a8eb43428fda9d8884809"
TESTS=371
ASSETS={
"sdk":("zx-ux-c48-sdk-1.0.2-b1621338565ac3bd9d4eff4ecb5a2a77aee2ab6a.zip",15432637,"8efd465928048b050c0cff9d93ddaf13127eabb12b837a33aa1c2c44e913a98a"),
"gui":("c48-1.0.2-gui-evidence-b1621338565ac3bd9d4eff4ecb5a2a77aee2ab6a.zip",3700008,"ed9e2b2643481c3a58e46fdc054c3524fb7fe300827cb3e2c2b4c2833dd5ef01"),
"metadata":("RELEASE-METADATA-1.0.2.json",758,"668911b54f20625ea8a7efa5219261146e4ef5a76a2f055a7990f019d59f555d"),
"sums":("SHA256SUMS-1.0.2.txt",359,"1981aa83cd1796894a380d2751cbc534483b244868d28c97f69c922f30672990")}
EXAMPLES=("argv","colors","graphics","hello","maze","udg")
DEMOS=("city","dizzy4k","firework","forest","galaxy","goblet","hanoi","julia","kaleido","mandel","mobius","moire","morph3d","ocean","orrery","plasma","queens8","raymaze","spriteanim","sprites","terrain","torus","tunnel","warp")
HEADERS=("usr/src/examples/exapi.h","usr/src/demos/demoapi.h","usr/src/demos/recapi.h")
TOOLING=(
"c48srctap","c48srctap.bat","compiler/c48srctap.py",
"compiler/refresh_source_tapes.py","compiler/c48/__init__.py",
"compiler/tests/test_c48srctap.py","compiler/tests/test_source_tape_manifest.py")

def fail(s): raise SystemExit("ERROR: "+s)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def shab(b): return hashlib.sha256(b).hexdigest()
def getj(url):
 r=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":"zxux-p11"})
 with urllib.request.urlopen(r,timeout=90) as x:return json.load(x)
def dl(url,p):
 r=urllib.request.Request(url,headers={"User-Agent":"zxux-p11"})
 with urllib.request.urlopen(r,timeout=300) as x,Path(p).open("wb") as f: shutil.copyfileobj(x,f,1<<20)
def extract_zip(src,dst):
 with zipfile.ZipFile(src) as z:
  z.extractall(dst)
  for i in z.infolist():
   mode=(i.external_attr>>16)&0o7777
   if mode&0o111:
    p=Path(dst)/i.filename
    if p.is_file(): p.chmod(p.stat().st_mode|(mode&0o111))
def crc16(data):
 c=0xffff
 for v in data:
  c^=v<<8
  for _ in range(8): c=((c<<1)^0x1021)&0xffff if c&0x8000 else (c<<1)&0xffff
 return c
def tap_blocks(data):
 o=[];i=0
 while i<len(data):
  if i+2>len(data):fail("truncated TAP length")
  n=struct.unpack_from("<H",data,i)[0];i+=2
  if n<2 or i+n>len(data):fail("bad TAP block length")
  b=data[i:i+n];i+=n
  x=0
  for v in b:x^=v
  if x:fail("TAP checksum mismatch")
  o.append(b)
 if i!=len(data):fail("TAP trailing bytes")
 return o
def decode(data):
 bs=tap_blocks(data);i=0;out=[]
 while i<len(bs):
  b=bs[i];i+=1
  if b[0]!=255 or len(b[1:-1])!=32:fail("bad M48O header block")
  h=bytearray(b[1:-1])
  if h[:5]!=b"M48O\x01":fail("bad M48O identity")
  hc=int.from_bytes(h[26:28],"little");h[26:28]=b"\0\0"
  if crc16(h)!=hc:fail("bad M48O header CRC")
  typ,flags,target=h[5],h[6],h[7];stored=int.from_bytes(h[8:10],"little");logical=int.from_bytes(h[10:12],"little");codec=int.from_bytes(h[12:14],"little");pc=int.from_bytes(h[14:16],"little")
  name=bytes(h[16:26]).split(b"\0",1)[0].decode("ascii");p=bytearray()
  while len(p)<stored:
   if i>=len(bs):fail("truncated M48O payload")
   q=bs[i];i+=1
   if q[0]!=255:fail("bad M48O payload flag")
   p.extend(q[1:-1])
  if len(p)!=stored or flags or codec or stored!=logical:fail("source tape is not exact RAW M48O")
  if crc16(p)!=pc:fail("bad M48O payload CRC")
  out.append((name,typ,target,bytes(p)))
 return out
def lfs(data):
 ls=data.decode("ascii").splitlines()
 if not ls or ls[0]!="version https://git-lfs.github.com/spec/v1":fail("bad LFS pointer")
 oid=next((x[11:] for x in ls if x.startswith("oid sha256:")),None);sz=next((x[5:] for x in ls if x.startswith("size ")),None)
 if not oid or len(oid)!=64 or not sz:fail("bad LFS fields")
 return oid,int(sz)
def programs():return [("examples",n) for n in EXAMPLES]+[("demos",n) for n in DEMOS]
def target_names(name):
 source="sprani.c" if name=="spriteanim" else name+".c"
 exe="sprani" if name=="spriteanim" else name
 obj=("sprani" if name=="spriteanim" else (name if len(name)<=6 else name[:6]))+".obj"
 for value in (source,obj,exe):
  if not 1<=len(value.encode("ascii"))<=10: fail("derived target name outside ZX-UX namespace: "+value)
 return source,obj,exe
def verify(root):
 root=Path(root);m=json.loads((root/"SDK-RELEASE.json").read_text())
 if m.get("schema")!=1 or m.get("tag")!=TAG or m.get("commit")!=COMMIT or m.get("tree")!=TREE or m.get("program_count")!=30:fail("SDK provenance identity mismatch")
 listed=m.get("files",[]);paths=set()
 for e in listed:
  r=e.get("path")
  if not isinstance(r,str) or r.startswith("/") or ".." in Path(r).parts or r in paths:fail("unsafe SDK manifest path")
  paths.add(r);p=root/r
  if not p.is_file() or p.is_symlink() or p.stat().st_size!=e.get("size") or sha(p)!=e.get("sha256"):fail("SDK artifact mismatch: "+r)
 actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name!="SDK-RELEASE.json"}
 if actual!=paths:fail("SDK manifest/file-set mismatch")
 if len(list((root/"usr/bin/examples").glob("*.src.tap")))!=6 or len(list((root/"usr/bin/demos").glob("*.src.tap")))!=24:fail("SDK tape count mismatch")
 for c,n in programs():
  oid,sz=lfs((root/f"docs/images/{c}/{n}.png").read_bytes());p=root/f"reference-png/{c}/{n}.png"
  if p.stat().st_size!=sz or sha(p)!=oid:fail("reference PNG/LFS mismatch: "+c+"/"+n)
def bundle(root):
 h=hashlib.sha256()
 for p in sorted(x for x in Path(root).rglob("*") if x.is_file()):
  r=p.relative_to(root).as_posix().encode();h.update(r+b"\0"+str(p.stat().st_size).encode()+b"\0"+sha(p).encode()+b"\n")
 return h.hexdigest()
def acquire(out):
 out=Path(out);work=out.parent/"sdk-acquire";shutil.rmtree(work,ignore_errors=True);shutil.rmtree(out,ignore_errors=True);(work/"d").mkdir(parents=True);(work/"sdk").mkdir();(work/"gui").mkdir()
 rel=getj(f"https://api.github.com/repos/{REPO}/releases/latest")
 if rel.get("tag_name")!=TAG or rel.get("target_commitish")!=COMMIT:fail("formal SDK release changed; explicit re-pin required")
 ci=getj(f"https://api.github.com/repos/{REPO}/commits/{TAG}")
 if ci.get("sha")!=COMMIT or ci.get("commit",{}).get("tree",{}).get("sha")!=TREE:fail("SDK tag/commit/tree mismatch")
 mf=getj(f"https://api.github.com/repos/{REPO}/contents/compiler/source_tape_manifest.json?ref={TAG}")
 if mf.get("sha")!=TAPE_BLOB:fail("source tape manifest Git blob mismatch")
 treej=getj(f"https://api.github.com/repos/{REPO}/git/trees/{TREE}?recursive=1")
 if treej.get("truncated"):fail("SDK release tree API result truncated")
 image_blobs={x["path"]:x["sha"] for x in treej.get("tree",[]) if x.get("type")=="blob" and x.get("path","").startswith("docs/images/")}
 remote={a["name"]:a for a in rel.get("assets",[])}
 for k,(name,size,digest) in ASSETS.items():
  a=remote.get(name)
  if not a or a.get("size")!=size or a.get("digest")!="sha256:"+digest:fail("release asset metadata mismatch: "+name)
  p=work/"d"/name;dl(a["browser_download_url"],p)
  if p.stat().st_size!=size or sha(p)!=digest:fail("release asset bytes mismatch: "+name)
 extract_zip(work/"d"/ASSETS["sdk"][0],work/"sdk")
 extract_zip(work/"d"/ASSETS["gui"][0],work/"gui")
 roots=[p.parent.parent for p in (work/"sdk").rglob("compiler/release_expectations.json") if (p.parent.parent/"VERSION").is_file()]
 if len(roots)!=1:fail("SDK ZIP root mismatch")
 sdk=roots[0]
 exp=json.loads((sdk/"compiler/release_expectations.json").read_text())
 if (sdk/"VERSION").read_text().strip()!=TAG or exp.get("test_count")!=TESTS:fail("SDK version/test-count mismatch")
 env=dict(os.environ);env["C48_REQUIRE_PACKAGED_SPEC"]="1"
 cp=subprocess.run([sys.executable,"-B",str(sdk/"compiler/verify_release.py")],cwd=sdk,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1800)
 (work/"verify-release.log").write_text(cp.stdout)
 if cp.returncode or f"VERIFY PASS: C48 SDK {TAG} | {TESTS} tests" not in cp.stdout: print(cp.stdout);fail("SDK verifier failed")
 tm=json.loads((sdk/"compiler/source_tape_manifest.json").read_text());ts=tm.get("tapes",[])
 if tm.get("tape_count")!=57 or len(ts)!=57:fail("source tape count mismatch")
 by={x["output"]:x for x in ts};out.mkdir()
 for d in ("usr/src/examples","usr/src/demos","usr/bin/examples","usr/bin/demos","compiler/c48","compiler/tests","docs/images/examples","docs/images/demos","reference-png/examples","reference-png/demos"):(out/d).mkdir(parents=True)
 progs=[]
 for c,n in programs():
  sr=f"usr/src/{c}/{n}.c";tr=f"usr/bin/{c}/{n}.src.tap";mi=by.get(tr)
  if not mi:fail("missing canonical tape declaration: "+tr)
  s=sdk/sr;t=sdk/tr;objs=decode(t.read_bytes());target,_,_=target_names(n);decl={x["path"]:x["name"] for x in mi["sources"]}
  if decl.get(sr)!=target:fail("target alias mismatch: "+sr)
  got={x[0]:x for x in objs}
  for x in mi["sources"]:
   if x["name"] not in got or got[x["name"]][3]!=(sdk/x["path"]).read_bytes():fail("independent tape decode mismatch: "+tr)
  if got[target][1:3]!=(5,5) or got[target][3]!=s.read_bytes():fail("C source tape envelope mismatch: "+tr)
  shutil.copyfile(s,out/sr);shutil.copyfile(t,out/tr)
  ip=f"docs/images/{c}/{n}.png";bsha=image_blobs.get(ip)
  if not bsha:fail("missing reference-image Git blob: "+ip)
  bj=getj(f"https://api.github.com/repos/{REPO}/git/blobs/{bsha}")
  ptr_bytes=base64.b64decode(bj.get("content",""))
  oid,sz=lfs(ptr_bytes);payload=sdk/ip
  if not payload.is_file() or payload.stat().st_size!=sz or sha(payload)!=oid:fail("materialized SDK reference PNG mismatch: "+c+"/"+n)
  (out/ip).write_bytes(ptr_bytes);shutil.copyfile(payload,out/f"reference-png/{c}/{n}.png")
  progs.append({"category":c,"name":n,"source_path":sr,"source_sha256":sha(s),"tape_path":tr,"tape_sha256":sha(t),"target_source":target,"reference_lfs_git_blob":bsha,"reference_lfs_oid_sha256":oid,"reference_png_sha256":sha(payload),"reference_payload_package":"sdk","objects":[{"name":a,"type":b,"target":d,"size":len(e),"sha256":shab(e)} for a,b,d,e in objs]})
 for r in HEADERS:shutil.copyfile(sdk/r,out/r)
 for r in TOOLING:shutil.copyfile(sdk/r,out/r)
 shutil.copyfile(sdk/"compiler/source_tape_manifest.json",out/"compiler/source_tape_manifest.json")
 shutil.copyfile(sdk/"compiler/release_expectations.json",out/"compiler/release_expectations.json")
 for k in ("metadata","sums"):shutil.copyfile(work/"d"/ASSETS[k][0],out/ASSETS[k][0])
 (out/"TARGET-NAME-MAP.json").write_text(json.dumps({"schema":1,"programs":[{"source":f"usr/src/{c}/{n}.c","target_source":target_names(n)[0],"target_object":target_names(n)[1],"target_executable":target_names(n)[2]} for c,n in programs()]},indent=2,sort_keys=True)+"\n")
 files=[{"path":p.relative_to(out).as_posix(),"size":p.stat().st_size,"sha256":sha(p)} for p in sorted(x for x in out.rglob("*") if x.is_file())]
 m={"schema":1,"kind":"phase11-pre-release-sdk-reference","repository":REPO,"tag":TAG,"commit":COMMIT,"tree":TREE,"source_tape_manifest_git_blob":TAPE_BLOB,"formal_release_test_count":TESTS,"source_tape_count":57,"program_count":30,"assets":{k:{"name":v[0],"size":v[1],"sha256":v[2]} for k,v in ASSETS.items()},"programs":progs,"headers":[{"path":r,"sha256":sha(sdk/r)} for r in HEADERS],"release_verifier":{"status":"PASS","test_count":TESTS,"log_sha256":sha(work/"verify-release.log")},"files":files}
 (out/"SDK-RELEASE.json").write_text(json.dumps(m,indent=2,sort_keys=True)+"\n")
 verify(out);first=None
 for _ in range(3):
  q=bundle(out)
  if first is None:first=q
  elif q!=first:fail("SDK three-scan bytes changed")
 (work/"sdk-reference.bundle-sha256").write_text(first+"\n")
 print("P11 PRE-RELEASE STAGE B PASS")
def main():
 p=argparse.ArgumentParser();sp=p.add_subparsers(dest="cmd",required=True);a=sp.add_parser("acquire");a.add_argument("--output",type=Path,required=True);v=sp.add_parser("verify");v.add_argument("--root",type=Path,required=True);x=p.parse_args()
 if x.cmd=="acquire":acquire(x.output)
 else:verify(x.root);print(bundle(x.root))
if __name__=="__main__":main()
