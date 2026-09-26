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
from pathlib import Path
import re

from .errors import (C48Error, IOC48Error, LexicalError, PreprocessorError,
                     ResourceLimitError, SourcePos, UnsupportedFeatureError)
from .lexer import Lexer, Token, SUPPORTED_KEYWORDS, UNSUPPORTED_KEYWORDS
from .limits import ResourceBudget

PORTABLE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,10}$")

@dataclass
class Macro:
    name: str
    replacement: list[Token]
    canonical: tuple[tuple[str, str], ...]
    pos: SourcePos


class Preprocessor:
    """Exact small C48 preprocessor with physical-line diagnostics.

    Host filesystem files stand in for ZX-UX TXT/C objects.  Because a normal host
    filesystem has no ZX-UX object-type metadata, quoted includes are accepted only
    for `.c`, `.h`, or `.txt` filenames in the host SDK; this host mapping is documented
    and does not alter the native language rule.
    """
    def __init__(self, *, normalize_crlf: bool = True, builtin_header: str = "",
                 budget: ResourceBudget | None = None):
        self.normalize_crlf = normalize_crlf
        self.builtin_header = builtin_header
        self.budget = budget or ResourceBudget()
        self.macros: dict[str, Macro] = {}
        self._header_included = False

    def preprocess_file(self, path: Path) -> list[Token]:
        pos = SourcePos(str(path), 1, 1)
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise IOC48Error(f"cannot stat source object: {exc}", pos) from None
        self.budget.check_source_object_size(size, pos)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise IOC48Error(f"cannot read source object: {exc}", pos) from None
        return self.preprocess_bytes(
            data, source_name=str(path), base_dir=path.parent, include_depth=0
        )

    def preprocess_bytes(self, data: bytes, *, source_name: str, base_dir: Path, include_depth: int = 0) -> list[Token]:
        source_pos = SourcePos(source_name, 1, 1)
        self.budget.add_source_object(len(data), source_pos)
        try:
            text = data.decode("ascii")
        except UnicodeDecodeError as e:
            prefix = data[:e.start]
            line = prefix.count(b"\n") + 1
            last = prefix.rfind(b"\n")
            column = e.start + 1 if last < 0 else e.start - last
            raise LexicalError(f"source is not canonical ASCII (byte offset {e.start})", SourcePos(source_name, line, column)) from None
        # A host may normalize complete CRLF pairs to canonical LF before lexical
        # analysis, but every other source byte must already be TAB, LF, or
        # printable ASCII.  Validate this *before* splitlines(), whose Unicode
        # semantics would otherwise treat VT/FF and several control characters
        # as line boundaries and corrupt C48 physical positions.
        if "\r" in text:
            if self.normalize_crlf and text.replace("\r\n", "").find("\r") < 0:
                text = text.replace("\r\n", "\n")
            else:
                off = text.index("\r")
                line = text.count("\n", 0, off) + 1
                last = text.rfind("\n", 0, off)
                column = off + 1 if last < 0 else off - last
                raise LexicalError("CR is not canonical C48 source; normalize CRLF first", SourcePos(source_name, line, column))
        for off, ch in enumerate(text):
            o = ord(ch)
            if ch in "\t\n" or 0x20 <= o <= 0x7E:
                continue
            line = text.count("\n", 0, off) + 1
            last = text.rfind("\n", 0, off)
            column = off + 1 if last < 0 else off - last
            if o == 0:
                reason = "NUL is not a canonical C48 source byte"
            else:
                reason = f"noncanonical source byte 0x{o:02x}"
            raise LexicalError(reason, SourcePos(source_name, line, column))
        return self._preprocess_text(text, source_name=source_name, base_dir=base_dir, include_depth=include_depth)

    @staticmethod
    def _mask_comments(line: str, in_block: bool) -> tuple[str, bool, int | None]:
        """Mask comments with spaces while preserving physical byte columns.

        The third result is the 1-based opening column of the block comment that
        remains active at end-of-line *when that comment opened on this line*.
        It is intentionally ``None`` for a block continued from an earlier line.
        This makes unterminated-comment diagnostics exact even when string literals
        contain ``/*`` or an earlier block comment opened and closed on the same line.
        """
        out = list(line)
        i = 0; n = len(line); state = in_block
        active_open_col: int | None = None
        quote: str | None = None
        while i < n:
            if state:
                if i + 1 < n and line[i:i+2] == "*/":
                    out[i] = out[i+1] = " "; i += 2; state = False
                    active_open_col = None
                else:
                    out[i] = " "; i += 1
                continue
            c = line[i]
            if quote:
                if c == "\\":
                    # Preserve the escaped byte as literal data; lexical validation
                    # later diagnoses an incomplete/invalid escape when appropriate.
                    i += 2; continue
                if c == quote: quote = None
                i += 1; continue
            if c in "'\"":
                quote = c; i += 1; continue
            if i + 1 < n and line[i:i+2] == "//":
                for j in range(i,n): out[j] = " "
                break
            if i + 1 < n and line[i:i+2] == "/*":
                active_open_col = i + 1
                out[i] = out[i+1] = " "; i += 2; state = True; continue
            i += 1
        return "".join(out), state, active_open_col

    def _preprocess_text(self, text: str, *, source_name: str, base_dir: Path, include_depth: int) -> list[Token]:
        lines = text.splitlines(keepends=True)
        if text and not lines:
            lines = [text]
        self.budget.add_lines(len(lines), SourcePos(source_name, 1, 1))
        for lineno, physical in enumerate(lines, 1):
            body_len = len(physical[:-1] if physical.endswith("\n") else physical)
            self.budget.check_line_length(
                body_len, SourcePos(source_name, lineno, 1)
            )
        tokens: list[Token] = []
        in_block = False
        block_start: SourcePos | None = None
        for lineno, physical in enumerate(lines, 1):
            has_lf = physical.endswith("\n")
            body = physical[:-1] if has_lf else physical
            masked, end_block, active_open_col = self._mask_comments(body, in_block)
            if end_block and active_open_col is not None:
                block_start = SourcePos(source_name, lineno, active_open_col)
            stripped = masked.lstrip(" \t")
            if stripped.startswith("#"):
                if end_block:
                    raise PreprocessorError("block comment in directive must close before physical LF", SourcePos(source_name,lineno,1))
                hash_index = masked.index("#")
                self._directive(masked[hash_index:], source_name, lineno, base_dir, include_depth, tokens, hash_index + 1)
            else:
                line_text = masked + ("\n" if has_lf else "")
                try:
                    ltoks = Lexer(source_name).tokenize(line_text)[:-1]
                except C48Error as exc:
                    # Each ordinary physical source line is lexed independently so
                    # preprocessing can preserve directive/macro visibility.  Lexer
                    # positions are therefore relative to this temporary line buffer;
                    # rebase failures exactly as successful tokens are rebased below.
                    if exc.pos is None:
                        raise
                    rebased = SourcePos(source_name, lineno + exc.pos.line - 1, exc.pos.column)
                    raise type(exc)(exc.message, rebased) from None
                for t in ltoks:
                    p = SourcePos(source_name, lineno + t.pos.line - 1, t.pos.column)
                    rt = Token(t.kind,t.text,t.value,p)
                    if rt.kind in {"IDENT","IMPL_IDENT"} and rt.text in self.macros:
                        macro = self.macros[rt.text]
                        self.budget.add_tokens(len(macro.replacement), p)
                        for mt in macro.replacement:
                            tokens.append(Token(mt.kind, mt.text, mt.value, p))
                    else:
                        self.budget.add_tokens(1, p)
                        tokens.append(rt)
            in_block = end_block
            if not in_block: block_start = None
        if in_block:
            raise LexicalError("unterminated block comment", block_start or SourcePos(source_name,max(1,len(lines)),1))
        eof_line = max(1, len(lines) if (not text.endswith("\n") or not text) else len(lines)+1)
        tokens.append(Token("EOF","",None,SourcePos(source_name,eof_line,1)))
        return tokens

    def _directive(self, text: str, source: str, line: int, base_dir: Path, include_depth: int, out: list[Token], hash_col: int) -> None:
        pos=SourcePos(source,line,hash_col)
        m=re.match(r"#([ \t]*)([A-Za-z_][A-Za-z0-9_]*)(.*)$", text)
        if not m: raise PreprocessorError("malformed preprocessing directive",pos)
        name,rest=m.group(2),m.group(3)
        if name not in {"define","include"}:
            if name in {"undef","if","ifdef","ifndef","elif","else","endif","error","line","pragma"}:
                raise PreprocessorError(f"#{name} is not C48 Version 1",pos)
            raise PreprocessorError(f"unknown directive #{name}",pos)
        if name=="define": self._define(rest,source,line)
        else:
            lead = len(rest) - len(rest.lstrip(" \t"))
            operand_col = hash_col + m.start(3) + lead
            self._include(rest,source,line,base_dir,include_depth,out,operand_col)

    def _define(self, rest: str, source: str, line: int) -> None:
        pos=SourcePos(source,line,1)
        if not rest or rest[0] not in " \t": raise PreprocessorError("#define requires horizontal whitespace",pos)
        s=rest.lstrip(" \t")
        m=re.match(r"([A-Za-z_][A-Za-z0-9_]*)(.*)$",s)
        if not m: raise PreprocessorError("#define requires an identifier",pos)
        name,tail=m.group(1),m.group(2)
        if len(name)>15: raise PreprocessorError("macro identifier exceeds 15 visible characters",pos)
        if tail.startswith("("): raise PreprocessorError("function-like macros are not C48 Version 1",pos)
        if not tail or tail[0] not in " \t": raise PreprocessorError("#define requires whitespace before nonempty replacement",pos)
        repl=tail.lstrip(" \t").rstrip(" \t")
        if not repl: raise PreprocessorError("#define replacement must be nonempty",pos)
        if name in SUPPORTED_KEYWORDS or name in UNSUPPORTED_KEYWORDS or name.startswith("__") or name=="_start":
            raise PreprocessorError(f"macro name {name!r} is reserved",pos)
        masked,end,_active_open_col=self._mask_comments(repl,False)
        if end: raise PreprocessorError("block comment in directive must close before physical LF",pos)
        raw=Lexer(source).tokenize(masked)[:-1]
        expanded=[]
        for t in raw:
            if t.kind in {"IDENT","IMPL_IDENT"}:
                old=self.macros.get(t.text)
                if old is None: raise PreprocessorError(f"#define replacement references unresolved identifier {t.text!r}",pos)
                self.budget.check_macro_replacement(
                    len(expanded) + len(old.replacement), pos
                )
                expanded.extend(old.replacement)
            else:
                self.budget.check_macro_replacement(len(expanded) + 1, pos)
                expanded.append(t)
        if not expanded: raise PreprocessorError("#define replacement must be nonempty after comment removal",pos)
        self._validate_constant_replacement(expanded, pos)
        canonical=tuple((t.kind,t.text) for t in expanded)
        old=self.macros.get(name)
        if old and old.canonical!=canonical: raise PreprocessorError(f"different redefinition of macro {name!r}",pos)
        if old is None:
            self.budget.add_macro_definition(pos)
        self.macros[name]=Macro(name,expanded,canonical,pos)

    def _validate_constant_replacement(self, tokens: list[Token], pos: SourcePos) -> None:
        """Require a complete, type-valid C48 constant token sequence.

        Macro identifiers have already been recursively expanded, so no ordinary
        identifier may remain.  We reuse the exact C48 expression parser and
        constant evaluator rather than maintaining a second precedence grammar.
        """
        from .parser import Parser
        from .semantics import SemanticAnalyzer
        eof = Token("EOF", "", None, tokens[-1].pos if tokens else pos)
        parser = Parser([*tokens, eof], budget=self.budget)
        try:
            expr = parser._expression()
            self.budget.check_ast(expr, pos)
            if parser.cur.kind != "EOF":
                raise PreprocessorError("#define replacement is not one complete C48 constant expression", pos)
            if expr["kind"] == "string_literal":
                return
            cv = SemanticAnalyzer(budget=self.budget).const_eval(expr)
            if not (cv.ctype.is_integer or cv.ctype.is_float):
                raise PreprocessorError("#define replacement is not an integer/floating/character/string constant", pos)
        except (PreprocessorError, ResourceLimitError):
            raise
        except C48Error as exc:
            raise PreprocessorError(f"#define replacement is not a valid C48 constant: {exc}", pos) from None

    def _include(self,rest:str,source:str,line:int,base_dir:Path,include_depth:int,out:list[Token],operand_col:int)->None:
        pos=SourcePos(source,line,operand_col)
        s=rest.strip()
        if s=="<c48.h>":
            if self._header_included:return
            self._header_included=True
            if self.builtin_header:
                header_bytes = self.builtin_header.encode("ascii")
                self.budget.add_source_object(
                    len(header_bytes), SourcePos("<c48.h>", 1, 1)
                )
                toks=self._preprocess_text(self.builtin_header,source_name="<c48.h>",base_dir=base_dir,include_depth=include_depth)
                out.extend(toks[:-1])
            return
        m=re.fullmatch(r'"([^"\n]+)"',s)
        if not m:
            if s.startswith("<"): raise PreprocessorError("the only system header is <c48.h>",pos)
            raise PreprocessorError("#include syntax is exactly \"name\" or <c48.h>",pos)
        if include_depth>=1: raise PreprocessorError("quoted local include nesting exceeds one level",pos)
        name=m.group(1)
        if not PORTABLE_NAME_RE.fullmatch(name) or name in {".",".."}: raise PreprocessorError("quoted include name violates 1..10 portable basename rules",pos)
        # Host proxy for native TXT/C object typing.
        if Path(name).suffix.lower() not in {".c",".h",".txt"}: raise PreprocessorError("host quoted include must map to TXT/C via .c/.h/.txt",pos)
        # Enforce exact case even on case-insensitive host filesystems.
        try:
            matches = [p for p in base_dir.iterdir() if p.name == name and p.is_file()]
        except OSError as exc:
            raise IOC48Error(f"cannot enumerate include directory: {exc}", pos) from None
        if len(matches) != 1:
            raise IOC48Error(f"local include object not found with exact case: {name}",pos)
        path=matches[0]
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise IOC48Error(f"cannot stat local include object {name}: {exc}", pos) from None
        self.budget.check_source_object_size(size, pos)
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise IOC48Error(f"cannot read local include object {name}: {exc}", pos) from None
        toks=self.preprocess_bytes(data,source_name=str(path),base_dir=base_dir,include_depth=include_depth+1)
        out.extend(toks[:-1])
