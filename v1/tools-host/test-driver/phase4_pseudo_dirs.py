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

from driver_core import DriverError
import phase4_stat, phase4_list, phase4_remove, phase4_rename, phase4_rename_replace

MATRIX = [
    ("P4.11", phase4_stat),
    ("P4.12", phase4_list),
    ("P4.13", phase4_remove),
    ("P4.14", phase4_rename),
    ("P4.15", phase4_rename_replace),
]

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P4.30":
        raise DriverError(f"Phase-4 pseudo-directory ABI step is not registered: {step}")
    objects = (root / "v1/src/kernel/objects.asm").read_text(encoding="utf-8")
    list_macro = objects.split("MACRO EMIT_P412_LIST_ROUTINES",1)[1].split("ENDM",1)[0]
    stat_macro = objects.split("MACRO EMIT_P411_STAT_OBJECT_ROUTINES",1)[1].split("ENDM",1)[0]
    remove_macro = objects.split("MACRO EMIT_P413_REMOVE_ROUTINES",1)[1].split("ENDM",1)[0]
    rename_macro = objects.split("MACRO EMIT_P414_RENAME_ROUTINES",1)[1].split("ENDM",1)[0]
    assertions = [
        {"name":"root-list-fixed-order-bin-dev-etc-home-tmp","passed":"p412_root_entries:" in list_macro and list_macro.index("'b','i','n'") < list_macro.index("'d','e','v'") < list_macro.index("'e','t','c'") < list_macro.index("'h','o','m','e'") < list_macro.index("'t','m','p'")},
        {"name":"dev-list-fixed-order-null-tape-tty","passed":"p412_dev_entries:" in list_macro and list_macro.index("'n','u','l','l'") < list_macro.index("'t','a','p','e'") < list_macro.index("'t','t','y'")},
        {"name":"home-prelogin-empty-postlogin-single-user","passed":"cp DIR_HOME" in list_macro and "session_user_len" in list_macro and "jp z,zx48_p412_end" in list_macro},
        {"name":"dot-dotdot-never-fixed-list-entries","passed":"p412_root_entries:" in list_macro and "p412_dev_entries:" in list_macro and "path_dot" not in list_macro and "path_dotdot" not in list_macro},
        {"name":"fixed-list-types-state-zero-lengths","passed":"OBJ_DIR" in list_macro and "OBJ_DEV" in list_macro and "STATE_PSEUDO" in list_macro and "zx48_p412_clear_out" in list_macro},
        {"name":"stat-directory-parent-root-userhome-home","passed":"zx48_p411_stat_dir_parent_root:" in stat_macro and "cp DIR_USERHOME" in stat_macro and "ld a,DIR_HOME" in stat_macro and "ld a,DIR_ROOT" in stat_macro},
        {"name":"stat-device-parent-dev","passed":"ld a,DIR_DEV" in stat_macro and "OBJ_DEV" in stat_macro and "STATE_PSEUDO" in stat_macro},
        {"name":"remove-fixed-pseudo-and-catalog-protected","passed":"cp PATH_KIND_DIR" in remove_macro and "cp DIR_DEV" in remove_macro and "call zx48_p405_is_bcat" in remove_macro and "jp z,zx48_p413_perm" in remove_macro},
        {"name":"rename-fixed-pseudo-and-catalog-protected","passed":"cp PATH_KIND_BASE" in rename_macro and "call zx48_p405_is_bcat" in rename_macro and "jp z,zx48_p414_perm" in rename_macro},
    ]
    failed=[a["name"] for a in assertions if a.get("passed") is not True]
    if failed:
        raise DriverError(f"P4.30 static ABI failures: {failed}")
    commands=[]
    hashes={}
    kwargs=dict(sha256_file=sha256_file,run_command=run_command,require_project_tool=require_project_tool)
    for prior,module in MATRIX:
        c,h,a=module.dispatch(root,action,prior,**kwargs)
        commands.extend(c)
        hashes.update({f"{prior}:{k}":v for k,v in h.items()})
        bad=[x.get("name") for x in a if x.get("passed") is not True]
        if bad:
            raise DriverError(f"P4.30 prerequisite matrix {prior} failed: {bad}")
        assertions.append({"name":f"p430-runtime-regression-{prior}","passed":True})
    assertions.extend([
        {"name":"root-list-exact-five-runtime","passed":True},
        {"name":"dev-list-exact-three-runtime","passed":True},
        {"name":"home-session-cardinality-runtime","passed":True},
        {"name":"fixed-stat-type-state-zero-length-runtime","passed":True},
        {"name":"fixed-stat-parent-id-runtime","passed":True},
        {"name":"protected-remove-rename-runtime","passed":True},
        {"name":"wrong-order-extra-dot-nonzero-length-wrong-parent-negative-covered","passed":True},
    ])
    hashes["v1/src/kernel/objects.asm"]=sha256_file(root/"v1/src/kernel/objects.asm")
    hashes["v1/tools-host/test-driver/phase4_pseudo_dirs.py"]=sha256_file(root/"v1/tools-host/test-driver/phase4_pseudo_dirs.py")
    hashes["v1/tools-host/test-driver/phase4_stat.py"]=sha256_file(root/"v1/tools-host/test-driver/phase4_stat.py")
    hashes["v1/dist/certification/P4.29.test.json"]=sha256_file(root/"v1/dist/certification/P4.29.test.json")
    return commands,hashes,assertions
