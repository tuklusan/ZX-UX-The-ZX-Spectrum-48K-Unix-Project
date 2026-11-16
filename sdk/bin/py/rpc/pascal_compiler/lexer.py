"""ASCII Pascal lexical analysis."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

import re
from dataclasses import dataclass

from .errors import PascalError


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    col: int


KEYWORDS = {
    "program", "const", "var", "integer", "char", "begin", "end",
    "if", "then", "else", "while", "do", "repeat", "until", "for",
    "to", "downto", "write", "writeln", "procedure", "function",
    "case", "of", "array", "record", "div", "mod", "and", "or",
    "not", "xor", "packed", "true", "false", "boolean",
}
_TOKEN_RE = re.compile(
    r"(?P<ws>\s+)|(?P<num>\#[0-9A-Fa-f]+|\d+)|"
    r"(?P<string>'(?:''|[^'])*')|(?P<assign>:=)|"
    r"(?P<rel><>|<=|>=|[=<>])|(?P<range>\.\.)|(?P<sym>[+\-*/(),;:.\[\]])|"
    r"(?P<word>[A-Za-z_][A-Za-z_0-9]*)|(?P<bad>.)",
    re.S,
)


def lex(source: str) -> list[Token]:
    out: list[Token] = []
    line = col = 1
    cursor = 0
    while cursor < len(source):
        # HiSoft accepts all three traditional Pascal comment spellings.  The
        # parenthesised form is nestable; handling comments before the token regexp
        # also makes an unterminated comment a source error instead of silently
        # tokenising its contents.
        if source[cursor] == "{" or source.startswith("(*", cursor):
            opener = source[cursor:cursor + 1] if source[cursor] == "{" else "(*"
            closer = "}" if opener == "{" else "*)"
            depth = 1
            start_line, start_col = line, col
            cursor += len(opener)
            col += len(opener)
            while cursor < len(source) and depth:
                if opener == "(*" and source.startswith("(*", cursor):
                    depth += 1
                    cursor += 2
                    col += 2
                elif source.startswith(closer, cursor):
                    depth -= 1
                    cursor += len(closer)
                    col += len(closer)
                else:
                    character = source[cursor]
                    cursor += 1
                    if character == "\n":
                        line += 1
                        col = 1
                    else:
                        col += 1
            if depth:
                raise PascalError(
                    f"unterminated comment at {start_line}:{start_col}"
                )
            continue
        if source.startswith("//", cursor):
            cursor += 2
            col += 2
            while cursor < len(source) and source[cursor] != "\n":
                cursor += 1
                col += 1
            continue

        match = _TOKEN_RE.match(source, cursor)
        if match is None:
            raise PascalError(f"unrecognised input at {line}:{col}")
        cursor = match.end()
        text = match.group(0)
        kind = match.lastgroup
        at = (line, col)
        line += text.count("\n")
        col = len(text.rsplit("\n", 1)[-1]) + 1 if "\n" in text else col + len(text)
        if kind == "ws":
            continue
        if kind == "bad":
            raise PascalError(f"unexpected character {text!r} at {at[0]}:{at[1]}")
        if kind == "word":
            out.append(Token("kw" if text.lower() in KEYWORDS else "id", text.lower(), *at))
        elif kind == "num":
            out.append(Token("num", text, *at))
        elif kind == "string":
            out.append(Token("string", text[1:-1].replace("''", "'"), *at))
        else:
            out.append(Token("sym", text, *at))
    out.append(Token("eof", "", line, col))
    return out
