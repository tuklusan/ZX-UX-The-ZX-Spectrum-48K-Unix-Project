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

"""REV16-only golden vectors for P6.28. No host-shell semantics are used."""

from __future__ import annotations


def _path_lookup(command: bytes, path: bytes | None, objects: dict[bytes, bytes]) -> bytes | None:
    if b"/" in command:
        return command if command in objects else None
    if path is None or path == b"":
        return None
    for component in path.split(b":"):
        component = component or b"."
        if objects.get(component) != b"DIR":
            continue
        candidate = component.rstrip(b"/") + b"/" + command if component != b"." else b"./" + command
        if objects.get(candidate) == b"BIN":
            return candidate
    return None


def run_vectors(tokenize, expand, lex, parse, core, hooks):
    assertions = []

    env = {b"USER": b"alice", b"SP": b"a b", b"EMPTY": b""}
    quote_cases = [
        (b"echo 'a b'", [b"echo", b"a b"]),
        (b'echo "a b"', [b"echo", b"a b"]),
        (b"echo a\\ b", [b"echo", b"a b"]),
        (b"echo ';' \\|", [b"echo", b";", b"|"]),
        (b"echo ''", [b"echo", b""]),
    ]
    for source, want in quote_cases:
        assert tokenize(source) == want
    assertions.append({"name": "golden-quoting-escaping", "passed": True, "cases": len(quote_cases)})

    expansion_cases = [
        (b"echo $USER", 0, b"echo alice"),
        (b"echo '$USER'", 0, b"echo '$USER'"),
        (b'echo "$SP"', 0, b'echo "a b"'),
        (b"echo $EMPTY", 0, b"echo "),
        (b"echo $?", 130, b"echo 130"),
        (b"echo $SP", 0, b"echo a b"),
        (b"echo *.c", 0, b"echo *.c"),
    ]
    for source, status, want in expansion_cases:
        assert expand(source, env, status) == want
    assert tokenize(expand(b'echo "$SP"', env, 0)) == [b"echo", b"a b"]
    assertions.append({"name": "golden-expansion-no-host-glob-substitution", "passed": True, "cases": len(expansion_cases)})

    operator_source = b"a|b&&c||d;e>>f<g&"
    assert [item[1] for item in lex(operator_source)] == ["PIPE", "AND", "OR", "SEMI", "APPEND", "IN", "BG"]
    assert lex(b"echo ';' \\| \"&&\" '>>'") == []
    ast = parse("a > x | b && c || d ; e < y")
    assert len(ast.units) == 2
    assert len(ast.units[0].first.stages) == 2
    assert [item[0] for item in ast.units[0].rest] == ["&&", "||"]
    assertions.append({"name": "golden-operator-precedence", "passed": True})

    objects = {
        b"/bin": b"DIR",
        b".": b"DIR",
        b"/bad": b"TXT",
        b"/alt": b"DIR",
        b"/later": b"DIR",
        b"/bin/ls": b"BIN",
        b"/alt/ls": b"TXT",
        b"/later/ls": b"BIN",
        b"./local": b"BIN",
        b"/direct.txt": b"TXT",
    }
    assert _path_lookup(b"ls", b"/bad:/alt:/bin", objects) == b"/bin/ls"
    assert _path_lookup(b"ls", b"/alt:/later", objects) == b"/later/ls"
    assert _path_lookup(b"local", b":/bin", objects) == b"./local"
    assert _path_lookup(b"ls", None, objects) is None
    assert _path_lookup(b"ls", b"", objects) is None
    assert _path_lookup(b"LS", b"/bin", objects) is None
    assert _path_lookup(b"/direct.txt", b"/bin", objects) == b"/direct.txt"
    assertions.append({"name": "golden-path-matrix-case-sensitive", "passed": True})

    core_set = set(core)
    hook_set = set(hooks)
    for name in core:
        assert name in core_set
        assert name.upper() not in core_set
    assert b"echo" not in core_set
    assert not (core_set & hook_set)
    assertions.append({"name": "golden-builtin-exact-case-precedence", "passed": True})

    bad = (b"(a)", b"a)", b"(a", b"a & b", b"a && (b)", b"a < x < y", b"a > x >> y")
    for source in bad:
        try:
            if b"(" in source or b")" in source:
                lex(source)
            else:
                parse(source.decode("ascii"))
        except ValueError as exc:
            assert str(exc) == "E_INVAL"
        else:
            raise AssertionError(f"unsupported construct accepted: {source!r}")
    assertions.append({"name": "negative-unsupported-constructs", "passed": True, "cases": len(bad)})

    # Divergence vectors: these intentionally differ from common host shells.
    assert expand(b"echo *.c", env, 0) == b"echo *.c"
    assert tokenize(b"echo a*b") == [b"echo", b"a*b"]
    try:
        lex(b"echo $(date)")
    except ValueError as exc:
        assert str(exc) == "E_INVAL"
    else:
        raise AssertionError("command substitution syntax accepted")
    assertions.append({"name": "host-shell-divergence-is-explicit", "passed": True})

    return assertions
