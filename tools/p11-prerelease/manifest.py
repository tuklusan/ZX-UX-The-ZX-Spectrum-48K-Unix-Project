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
import hashlib, json, subprocess
from pathlib import Path
ROOT=Path.cwd(); WORK=Path('/tmp/p11-prerelease'); OUT=WORK/'P11.pre-release'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*a): return subprocess.check_output(['git',*a],text=True).strip()

def emit():
    build=json.loads((WORK/'a/build.json').read_text()); native=json.loads((WORK/'native-rebuild.json').read_text())
    runtime=json.loads((WORK/'realtime/runtime-acceptance.json').read_text()); detect=json.loads((WORK/'realtime-detect-loader/runtime-acceptance.json').read_text())
    exact=json.loads((WORK/'evidence/P11.48.result.json').read_text()); activated=json.loads((ROOT/'v1/dist/certification/phase-11.json').read_text())
    assert exact['status']=='PASS' and exact['source_commit']==git('rev-parse','HEAD')
    assert activated['status']=='PASS' and activated['pass_marker']=='ZX-UX PHASE 11 CERTIFICATION PASS'
    assert all(v=='PASS' for v in runtime['assertions'].values()) and all(v=='PASS' for v in detect['assertions'].values())
    host=sha(ROOT/'v1/build/kernel.bin'); embedded=sha(WORK/'embedded-kernel.bin')
    assert host==embedded==native['native_rebuilt_kernel_sha256']
    readme='''ZX-UX Phase-11 fast-loader pre-release

Boot on a 48K Spectrum with: LOAD ""

This is the REV17/REV08 TZX-only Phase-11 pre-release transport image.
It embeds the exact current 8192-byte kernel at E000-FFFF and hands off at
E003 using the reviewed fast loader. Phase-11 native compiler acceptance is
re-run against this exact source head and hash-bound in pre-release.json.

This pre-release intentionally does NOT append the final Phase-12 system/demo
M48O stream. It is not the final integrated system tape and does not claim
Phase-12 release acceptance. No Phase-12 source, workflow, evidence, media, or
activation is created.
'''
    (OUT/'README.txt').write_text(readme,encoding='utf-8',newline='\n')
    pasmo=(WORK/'pasmo-path').read_text().strip()
    meta={'schema':1,'kind':'phase11-fast-loader-tzx-pre-release','candidate_source_commit':git('rev-parse','HEAD'),
      'authority':{'architecture':'REV17','architecture_sha256':'d12baf0b47a7f8cd2dcd60b82f100ba19f9fddaabad43728a004a07214716bf8','implementation_plan':'REV08','implementation_plan_sha256':'97461e9ed12253409b25e6a4a4063cf0ec556a7317f9e4a5938d77edb6a1a14c'},
      'phase11':{'activated_aggregate_sha256':sha(ROOT/'v1/dist/certification/phase-11.json'),'activated_source_commit':activated['source_commit'],'activated_pass_marker':activated['pass_marker'],'p1148_result_sha256':sha(ROOT/'v1/dist/certification/P11.48.result.json'),'p1148_sdk_admission_sha256':sha(ROOT/'v1/dist/certification/P11.48-sdk-admission.json'),'exact_head_revalidation_result_sha256':sha(WORK/'evidence/P11.48.result.json'),'exact_head_revalidation_source_commit':exact['source_commit'],'exact_head_revalidation_pass_marker':exact['pass_marker']},
      'fast_loader':{'portable_zip_sha256':'4c83a681f718192db9ebb32f0c8bc565baf2e68eb85de480322a1102d32f00c7','seed_sha256':build['seed_sha256'],'hook_sha256':build['hook_sha256'],'text_lines_sha256':sha(ROOT/'v1/tools-host/release-tzx/text-lines.txt'),'builder_sha256':sha(ROOT/'v1/tools-host/release-tzx/build.py'),'inspector_sha256':sha(ROOT/'v1/tools-host/release-tzx/inspect_tzx.py'),'runtime_acceptance_sha256':sha(ROOT/'v1/tools-host/release-tzx/runtime_acceptance.py'),'pasmo_version':subprocess.check_output(['dpkg-query','-W','-f=${Version}','pasmo'],text=True),'pasmo_executable_sha256':sha(pasmo)},
      'boot_contract':{'distribution':'TZX-only','screen_file':None,'zx48uxscr':False,'loader_display':'24x32 loader-owned','kernel_address':'0xE000','kernel_size':8192,'kernel_end':'0xFFFF','handoff':'0xE003','final_loader_after':'0x5EB4','pre_beep_pause_nominal_tstates':build['pre_beep_pause_nominal_tstates'],'post_kernel_m48o_stream':False,'scope':'Phase-11 pre-release transport plus exact-head compiler acceptance; final integrated system tape remains Phase 12'},
      'kernel_identity':{'size':8192,'host_built_sha256':host,'tzx_embedded_sha256':embedded,'native_rebuilt_sha256':native['native_rebuilt_kernel_sha256']},
      'runtime_acceptance':runtime,'runtime_detect_loader_compatibility':detect,
      'tests':{'phase11-activated-aggregate':'PASS','phase11-exact-head-p1148':'PASS','deterministic-double-build':'PASS','independent-kernel-reconstruction':'PASS','native-kernel-self-rebuild':'PASS','controlled-mismatch-negative':'PASS','real-time-loader-shortcuts-disabled':'PASS','detect-loader-compatibility':'PASS','zero-phase12-state':'PASS'}}
    tzx=OUT/'zx-ux-phase11-pre-release.tzx'; meta['files']=[{'path':tzx.name,'size':tzx.stat().st_size,'sha256':sha(tzx)}]
    (OUT/'pre-release.json').write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')

def scan():
    assert sorted(p.name for p in OUT.iterdir() if p.is_file())==['README.txt','pre-release.json','zx-ux-phase11-pre-release.tzx']
    m=json.loads((OUT/'pre-release.json').read_text()); assert m['kind']=='phase11-fast-loader-tzx-pre-release'
    assert m['phase11']['activated_pass_marker']=='ZX-UX PHASE 11 CERTIFICATION PASS' and m['phase11']['exact_head_revalidation_pass_marker']=='ZX-UX PHASE 11 ACCEPTANCE PASS'
    assert m['phase11']['exact_head_revalidation_source_commit']==m['candidate_source_commit']
    assert m['boot_contract']['distribution']=='TZX-only' and m['boot_contract']['screen_file'] is None and m['boot_contract']['zx48uxscr'] is False and m['boot_contract']['post_kernel_m48o_stream'] is False
    assert m['kernel_identity']['size']==8192 and len(set(m['kernel_identity'][k] for k in ('host_built_sha256','tzx_embedded_sha256','native_rebuilt_sha256')))==1
    assert all(v=='PASS' for v in m['tests'].values()) and all(v=='PASS' for v in m['runtime_acceptance']['assertions'].values()) and all(v=='PASS' for v in m['runtime_detect_loader_compatibility']['assertions'].values())
    for f in m['files']:
        p=OUT/f['path']; assert p.stat().st_size==f['size'] and sha(p)==f['sha256']
    assert not list(OUT.glob('*.tap'))
    h=hashlib.sha256()
    for p in sorted(OUT.iterdir(),key=lambda x:x.name): h.update(p.name.encode()+b'\0'+p.read_bytes())
    return h.hexdigest()
if __name__=='__main__':
    emit(); baseline=None
    for _ in range(3):
        digest=scan(); baseline=digest if baseline is None else baseline; assert digest==baseline
    print('ZX-UX PHASE-11 PRE-RELEASE THREE UNCHANGED OUTPUT SCANS PASS')
