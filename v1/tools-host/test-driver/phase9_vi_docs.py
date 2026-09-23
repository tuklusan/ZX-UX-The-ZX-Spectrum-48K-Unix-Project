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

from driver_core import DriverError

class P923Error(DriverError):
    pass

def require(value, message):
    if not value:
        raise P923Error(message)

REQUIRED = (
    "Invocation is exactly `vi` or `vi path`.",
    "physical `CAPS SHIFT + 1` `EDIT` chord",
    "canonical editor escape byte is `0x1B`",
    "BREAK is separate",
    "normal, insert, and command-line",
    "`-- INSERT --`",
    "`gg` moves to the first line",
    "`G` moves to the last line",
    "`i` inserts before the cursor",
    "`a` appends after it",
    "`o` opens a line below",
    "`O` opens a line above",
    "`x` deletes one character",
    "`dd` deletes the current logical line",
    "`D` deletes from the cursor",
    "`yy` yanks the current logical line",
    "`p` puts after",
    "`P` puts before",
    "`r` replaces one character",
    "`J` joins the current line",
    "`u` performs one-level undo",
    "`/text` performs a forward literal, case-sensitive search",
    "`n` repeats the last search",
    "`N` repeats it in the opposite direction",
    "`:w`",
    "`:w path`",
    "`:q`",
    "`:q!`",
    "`:wq`",
    "`:e path`",
    "`:r path`",
    "`:set`",
    "`:set number`",
    "`:set nonumber`",
    "gap buffer with a compact line-offset index",
    "one-level undo record",
    "`:q` refuses to exit while the buffer is dirty",
    "`:e path` refuses while dirty",
    "`:r path` inserts that object's bytes, marks the buffer dirty, and never retargets",
    "`vi: no file name`",
    "changes the current target only after a successful transactional write",
    "A successful write clears dirty state",
    "`:wq` exits only after a successful write",
    "`O_WRITE|O_CREATE|O_EXCL`",
    "atomic `SYS_RENAME`",
    "Failure before rename leaves the previous destination byte-identical",
    "five-column line-number gutter",
    "TAB remains stored as byte `0x09`",
    "columns 0 through 63",
    "`:udg` is deferred from the required version-1 vi subset",
    "UDG resources remain available through the graphics APIs and the `udg` utility",
    "A line-oriented bootstrap editor may exist temporarily during development, but it is not",
    "must not replace the `vi` acceptance gate",
)

DEFERRED = (
    "syntax highlighting",
    "multiple open buffers",
    "split windows",
    "visual mode",
    "named register collections",
    "macros/recording",
    "full regular-expression substitution",
    "persistent undo/swap files",
)

def validate_document(text: str) -> list[str]:
    errors=[]
    for item in REQUIRED:
        if item not in text:
            errors.append(f"missing required vi contract: {item}")
    for item in DEFERRED:
        if text.count(item) != 1:
            errors.append(f"deferred feature must appear exactly once: {item}")
    if "`?`" in text:
        errors.append("unsupported normal/search command documented: ?")
    if text.count("`:udg`") != 1:
        errors.append(":udg deferral must appear exactly once")
    if "BREAK is not editor escape" not in text:
        errors.append("BREAK/editor-escape separation missing")
    if "case-sensitive" not in text:
        errors.append("case sensitivity missing")
    return errors

def dispatch(root, action, step, *, sha256_file, run_command, require_project_tool):
    if step != "P9.23":
        raise DriverError(step)

    doc=root/"v1/docs/vi.md"
    text=doc.read_text(encoding="utf-8")
    plan=(root/"docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV07.md").read_text(encoding="utf-8")
    assertions=[
        {"name":"canonical-p923-present","passed":"## P9.23 - Freeze vi user/developer documentation" in plan},
        {"name":"vi-document-contract-complete","passed":not validate_document(text)},
        {"name":"exact-eight-deferred-families","passed":all(text.count(x)==1 for x in DEFERRED)},
        {"name":"no-unsupported-question-command","passed":"`?`" not in text},
    ]
    require(all(x["passed"] for x in assertions), "P9.23 documentation contract failure: "+"; ".join(validate_document(text)))

    if action == "test":
        mutations=[
            ("delete-command", text.replace("`dd` deletes the current logical line", "deletes the current logical line", 1)),
            ("delete-dirty-rule", text.replace("`:q` refuses to exit while the buffer is dirty", "Quit refuses while dirty", 1)),
            ("omit-udg-deferral", text.replace("`:udg` is deferred from the required version-1 vi subset", "UDG convenience is deferred", 1)),
            ("omit-deferred-family", text.replace("- split windows\n", "", 1)),
            ("weaken-bootstrap", text.replace("must not replace the `vi` acceptance gate", "may replace the acceptance gate", 1)),
            ("invent-question-command", text+"\n- `?` searches backward.\n"),
        ]
        for name, mutated in mutations:
            require(bool(validate_document(mutated)), f"P9.23 negative fixture unexpectedly passed: {name}")
        assertions += [
            {"name":"negative-missing-command-rejected","passed":True},
            {"name":"negative-missing-dirty-rule-rejected","passed":True},
            {"name":"negative-missing-udg-deferral-rejected","passed":True},
            {"name":"negative-missing-deferred-family-rejected","passed":True},
            {"name":"negative-bootstrap-weakening-rejected","passed":True},
            {"name":"negative-unsupported-command-rejected","passed":True},
        ]

    hashes={
        "v1/docs/vi.md":sha256_file(doc),
        "v1/tools-host/test-driver/phase9_vi_docs.py":sha256_file(root/"v1/tools-host/test-driver/phase9_vi_docs.py"),
        "v1/tools-host/test-driver/run.py":sha256_file(root/"v1/tools-host/test-driver/run.py"),
        "v1/dist/certification/P9.22.test.json":sha256_file(root/"v1/dist/certification/P9.22.test.json"),
    }
    return [], hashes, assertions
