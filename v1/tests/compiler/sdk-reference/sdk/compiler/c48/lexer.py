# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

from dataclasses import dataclass
import re

from .errors import LexicalError, LiteralRangeError, SourcePos, UnsupportedFeatureError

SUPPORTED_KEYWORDS = {
    "break", "char", "continue", "do", "else", "extern", "float", "for",
    "if", "int", "return", "short", "sizeof", "static", "unsigned", "void", "while",
}
UNSUPPORTED_KEYWORDS = {
    "auto", "case", "const", "default", "double", "enum", "goto", "long", "register",
    "signed", "struct", "switch", "typedef", "union", "volatile", "inline", "restrict",
    "_Alignas", "_Alignof", "_Atomic", "_Bool", "_Complex", "_Generic", "_Imaginary",
    "_Noreturn", "_Static_assert", "_Thread_local",
}
SUPPORTED_MULTI = ("++", "--", "<<", ">>", "<=", ">=", "==", "!=", "&&", "||")
UNSUPPORTED_MULTI = ("<<=", ">>=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "->", "...")
SINGLE = set("=+-*/%<>&|^~!()[]{};,")
UNSUPPORTED_SINGLE = set("?:.")

@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    value: object
    pos: SourcePos

    def to_dict(self) -> dict:
        return {"kind": self.kind, "text": self.text, "value": self.value,
                "pos": {"source": self.pos.source, "line": self.pos.line, "column": self.pos.column}}

class Lexer:
    def __init__(self, source_name: str):
        self.source_name = source_name

    def tokenize(self, text: str) -> list[Token]:
        out: list[Token] = []
        i = 0
        line = 1
        col = 1
        n = len(text)

        def pos() -> SourcePos:
            return SourcePos(self.source_name, line, col)

        def adv(s: str) -> None:
            nonlocal line, col
            for ch in s:
                if ch == "\n":
                    line += 1; col = 1
                else:
                    col += 1

        while i < n:
            ch = text[i]
            if ch in " \t\n":
                adv(ch); i += 1; continue
            if ch == "\r":
                raise LexicalError("CR is not a canonical C48 source byte", pos())
            if ch == "\x00" or ord(ch) < 0x20 or ord(ch) > 0x7E:
                raise LexicalError(f"noncanonical source byte 0x{ord(ch):02x}", pos())

            # Comments win before division.
            if text.startswith("//", i):
                j = text.find("\n", i + 2)
                if j < 0: j = n
                adv(text[i:j]); i = j; continue
            if text.startswith("/*", i):
                start = pos(); j = text.find("*/", i + 2)
                if j < 0:
                    raise LexicalError("unterminated block comment", start)
                s = text[i:j+2]; adv(s); i = j + 2; continue

            start = pos()

            # Identifier / keyword.
            if ch == "_" or ch.isalpha():
                j = i + 1
                while j < n and (text[j] == "_" or text[j].isalnum()): j += 1
                raw = text[i:j]
                if len(raw) > 15:
                    raise LexicalError("identifier exceeds 15 visible characters", start)
                if raw.startswith("__") or raw == "_start":
                    # implementation-owned names may still occur in compiler-generated/built-in material;
                    # user-level semantic checker decides context. Lexer identifies them distinctly.
                    kind = "IMPL_IDENT"
                elif raw in SUPPORTED_KEYWORDS:
                    kind = "KW"
                elif raw in UNSUPPORTED_KEYWORDS:
                    kind = "UNSUPPORTED_KW"
                else:
                    kind = "IDENT"
                out.append(Token(kind, raw, raw, start)); adv(raw); i = j; continue

            # Character or string literal.
            if ch in "'\"":
                quote = ch; j = i + 1; bytes_out: list[int] = []
                while True:
                    if j >= n:
                        raise LexicalError("unterminated literal", start)
                    c = text[j]
                    if c == "\n":
                        raise LexicalError("unescaped LF inside literal", start)
                    if c == quote:
                        j += 1; break
                    if c == "\\":
                        val, used = self._escape(text, j, start)
                        bytes_out.append(val); j += used; continue
                    o = ord(c)
                    if o < 0x20 or o > 0x7E:
                        raise LexicalError("non-ASCII literal byte", start)
                    bytes_out.append(o); j += 1
                raw = text[i:j]
                if quote == "'":
                    if len(bytes_out) != 1:
                        raise LexicalError("character literal must denote exactly one byte", start)
                    out.append(Token("CHAR_LIT", raw, bytes_out[0], start))
                else:
                    out.append(Token("STRING_LIT", raw, bytes(bytes_out), start))
                adv(raw); i = j; continue

            # Numeric literal. A dot only starts a float when followed by a digit.
            if ch.isdigit() or (ch == "." and i + 1 < n and text[i+1].isdigit()):
                raw, kind, value = self._number(text, i, start)
                j = i + len(raw)
                # malformed numeric token cannot be split from a following identifier/suffix.
                if j < n and (text[j] == "_" or text[j].isalpha()):
                    k = j + 1
                    while k < n and (text[k] == "_" or text[k].isalnum()): k += 1
                    raise LexicalError(f"malformed numeric token {text[i:k]!r}", start)
                out.append(Token(kind, raw, value, start)); adv(raw); i = j; continue

            matched = False
            for op in UNSUPPORTED_MULTI:
                if text.startswith(op, i):
                    raise UnsupportedFeatureError(f"operator {op!r} is not C48 Version 1", start)
            for op in SUPPORTED_MULTI:
                if text.startswith(op, i):
                    out.append(Token("OP", op, op, start)); adv(op); i += len(op); matched = True; break
            if matched: continue
            if ch in UNSUPPORTED_SINGLE:
                raise UnsupportedFeatureError(f"operator/token {ch!r} is not C48 Version 1", start)
            if ch in SINGLE:
                kind = "PUNC" if ch in "()[]{};," else "OP"
                out.append(Token(kind, ch, ch, start)); adv(ch); i += 1; continue
            if ch == "#":
                raise LexicalError("# is valid only in preprocessing-directive position", start)
            if ch == "\\":
                raise LexicalError("backslash outside a literal is not C48 syntax", start)
            raise LexicalError(f"unsupported source byte {ch!r}", start)

        out.append(Token("EOF", "", None, SourcePos(self.source_name, line, col)))
        return out

    @staticmethod
    def _escape(text: str, i: int, start: SourcePos) -> tuple[int, int]:
        assert text[i] == "\\"
        if i + 1 >= len(text):
            raise LexicalError("incomplete escape", start)
        c = text[i+1]
        mapping = {"\\":0x5C, "'":0x27, '"':0x22, "0":0, "a":7, "b":8,
                   "t":9, "n":10, "v":11, "f":12, "r":13}
        if c in mapping:
            return mapping[c], 2
        if c == "x":
            if i + 3 >= len(text):
                raise LexicalError("hex escape requires exactly two hexadecimal digits", start)
            h = text[i+2:i+4]
            if not re.fullmatch(r"[0-9A-Fa-f]{2}", h):
                raise LexicalError("hex escape requires exactly two hexadecimal digits", start)
            return int(h, 16), 4
        if c in "1234567":
            raise UnsupportedFeatureError("general octal escapes are not C48 Version 1", start)
        raise LexicalError(f"unsupported escape \\{c}", start)

    @staticmethod
    def _number(text: str, i: int, start: SourcePos) -> tuple[str, str, object]:
        # Floats: digits '.' digits? exp? | '.' digits exp? | digits exp, optional f/F.
        float_re = re.compile(
            r"(?:(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[0-9]+[eE][+-]?[0-9]+)[fF]?"
        )
        m = float_re.match(text, i)
        if m:
            raw = m.group(0)
            # reject malformed continuation such as second exponent / suffix via caller.
            return raw, "FLOAT_LIT", raw[:-1] if raw[-1:] in "fF" else raw

        # Integer prefixes.
        j = i
        base = 10
        if text.startswith(("0x", "0X"), i):
            base = 16; j = i + 2
            k = j
            while k < len(text) and (text[k].isdigit() or text[k].lower() in "abcdef"): k += 1
            if k == j:
                raise LexicalError("hexadecimal prefix requires a digit", start)
            j = k
        elif text[i] == "0":
            base = 8; j = i + 1
            while j < len(text) and text[j].isdigit(): j += 1
            rawdigits = text[i:j]
            if any(c in "89" for c in rawdigits):
                raise LexicalError("8 or 9 is invalid in an octal integer literal", start)
        else:
            while j < len(text) and text[j].isdigit(): j += 1
        if j < len(text) and text[j] in "uU":
            j += 1
        raw = text[i:j]
        # 0 by itself is valid octal zero.
        core = raw[:-1] if raw[-1:] in "uU" else raw
        try:
            value = int(core, base)
        except ValueError:
            raise LexicalError(f"malformed integer literal {raw!r}", start)
        if value > 65535:
            raise LiteralRangeError("integer literal magnitude exceeds 65535", start)
        return raw, "INT_LIT", {"value": value, "unsigned": raw[-1:] in "uU"}
