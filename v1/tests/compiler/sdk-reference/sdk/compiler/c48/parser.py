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

from typing import Any

from .astutil import node
from .errors import SyntaxC48Error, UnsupportedFeatureError
from .lexer import Token
from .limits import (
    PARSER_ASSIGNMENT_DEPTH,
    PARSER_EXPRESSION_DEPTH,
    PARSER_STATEMENT_DEPTH,
    PARSER_UNARY_DEPTH,
    ResourceBudget,
)

TYPE_START = {"void", "char", "unsigned", "short", "int", "float"}
STORAGE = {"static", "extern"}


class Parser:
    """Recursive-descent parser for the exact C48 Version-1 grammar.

    The parser deliberately recognizes only Appendix-A productions. Semantic rules
    (exact type compatibility, constant-only initializers, main restrictions, etc.)
    are enforced by SemanticAnalyzer.
    """

    def __init__(
        self, tokens: list[Token], *, budget: ResourceBudget | None = None
    ):
        self.tokens = tokens
        self.i = 0
        self.budget = budget or ResourceBudget()

    @property
    def cur(self) -> Token:
        return self.tokens[self.i]

    def at(self, text: str) -> bool:
        return self.cur.text == text

    def accept(self, text: str) -> Token | None:
        if self.at(text):
            t = self.cur
            self.i += 1
            return t
        return None

    def expect(self, text: str) -> Token:
        if not self.at(text):
            raise SyntaxC48Error(f"expected {text!r}, found {self.cur.text!r}", self.cur.pos)
        t = self.cur
        self.i += 1
        return t

    def _identifier(self) -> Token:
        t = self.cur
        if t.kind not in {"IDENT", "IMPL_IDENT"}:
            if t.kind == "UNSUPPORTED_KW":
                raise UnsupportedFeatureError(f"keyword {t.text!r} is not C48 Version 1", t.pos)
            raise SyntaxC48Error("expected identifier", t.pos)
        self.i += 1
        return t

    def _is_type_start(self) -> bool:
        return self.cur.kind == "KW" and self.cur.text in TYPE_START

    def parse(self) -> dict[str, Any]:
        items = []
        p = self.cur.pos
        while self.cur.kind != "EOF":
            items.append(self._external_declaration())
        return node("translation_unit", p, items=items)

    def _storage_and_type(self) -> tuple[str | None, dict[str, Any]]:
        storage = None
        if self.cur.kind == "KW" and self.cur.text in STORAGE:
            storage = self.cur.text
            self.i += 1
        return storage, self._type_specifier()

    def _type_specifier(self) -> dict[str, Any]:
        start = self.cur
        if self.cur.kind == "UNSUPPORTED_KW":
            raise UnsupportedFeatureError(f"type/keyword {self.cur.text!r} is not C48 Version 1", self.cur.pos)
        if self.cur.kind != "KW" or self.cur.text not in TYPE_START:
            raise SyntaxC48Error("expected C48 type specifier", self.cur.pos)
        first = self.cur.text
        self.i += 1
        if first == "unsigned":
            if self.cur.kind != "KW" or self.cur.text not in {"char", "short", "int"}:
                raise SyntaxC48Error("C48 requires 'unsigned char', 'unsigned short', or 'unsigned int'", self.cur.pos)
            second = self.cur.text
            self.i += 1
            spelling = ["unsigned", second]
        else:
            spelling = [first]
            # Alternative spellings like 'short int' are not two tokens of a valid declaration.
        return node("type_name", start.pos, spelling=spelling, pointers=0)

    def _type_name(self) -> dict[str, Any]:
        t = self._type_specifier()
        depth = 0
        while self.accept("*"):
            depth += 1
            self.budget.check_pointer_depth(depth, self.tokens[self.i - 1].pos)
        t["pointers"] = depth
        return t

    def _declarator(self, *, parameter: bool = False) -> dict[str, Any]:
        start = self.cur
        depth = 0
        while self.accept("*"):
            depth += 1
            self.budget.check_pointer_depth(depth, self.tokens[self.i - 1].pos)
        name_t = self._identifier()
        suffix = None
        if self.accept("["):
            if parameter:
                raise UnsupportedFeatureError("array declarator syntax is not supported in parameter declarations", start.pos)
            bound = None
            if not self.at("]"):
                bound = self._expression()
            self.expect("]")
            suffix = {"kind": "array", "bound": bound}
        elif self.accept("("):
            params = self._parameter_clause(definition=False)
            self.expect(")")
            suffix = {"kind": "function", "params": params}
        return node("declarator", start.pos, name=name_t.text, pointers=depth, suffix=suffix)

    def _function_declarator(self) -> dict[str, Any]:
        start = self.cur
        depth = 0
        while self.accept("*"):
            depth += 1
            self.budget.check_pointer_depth(depth, self.tokens[self.i - 1].pos)
        name_t = self._identifier()
        self.expect("(")
        params = self._parameter_clause(definition=True)
        self.expect(")")
        return node("declarator", start.pos, name=name_t.text, pointers=depth,
                    suffix={"kind": "function", "params": params})

    def _parameter_clause(self, *, definition: bool) -> list[dict[str, Any]]:
        # Exactly `void` means zero parameters. Empty () is forbidden.
        if self.at(")"):
            raise UnsupportedFeatureError("empty function parameter list f() is not C48; use f(void)", self.cur.pos)
        if self.at("void"):
            # Could be `void *p`, so inspect next token.
            save = self.i
            base = self._type_specifier()
            if self.at(")"):
                return []
            self.i = save
        params = []
        while True:
            param_pos = self.cur.pos
            ptype = self._type_specifier()
            depth = 0
            while self.accept("*"):
                depth += 1
                self.budget.check_pointer_depth(
                    depth, self.tokens[self.i - 1].pos
                )
            name = None
            if self.cur.kind in {"IDENT", "IMPL_IDENT"}:
                name = self.cur.text
                self.i += 1
            if definition and name is None:
                raise SyntaxC48Error("function-definition parameter requires a name", self.cur.pos)
            params.append(node("parameter", param_pos, type=ptype, pointers=depth, name=name))
            if not self.accept(","):
                break
        return params

    def _external_declaration(self) -> dict[str, Any]:
        start = self.cur
        storage, base_type = self._storage_and_type()

        # Parse first declarator with generic prototype names optional.
        first = self._declarator()
        # A function definition is identifiable by function suffix followed immediately by `{`.
        if first.get("suffix") and first["suffix"]["kind"] == "function" and self.at("{"):
            # Definitions require parameter names; generic parser may have accepted omitted ones.
            for p in first["suffix"]["params"]:
                if p["name"] is None:
                    raise SyntaxC48Error("function-definition parameter requires a name", self.cur.pos)
            body = self._compound_statement()
            return node("function_definition", start.pos, storage=storage, base_type=base_type,
                        declarator=first, body=body)

        decls = [self._init_declarator_from(first)]
        while self.accept(","):
            decls.append(self._init_declarator_from(self._declarator()))
        self.expect(";")
        return node("declaration", start.pos, storage=storage, base_type=base_type,
                    declarators=decls, scope="file")

    def _init_declarator_from(self, decl: dict[str, Any]) -> dict[str, Any]:
        init = None
        if self.accept("="):
            init = self._initializer()
        return node("init_declarator", self._pos_from_dict(decl["pos"]), declarator=decl, initializer=init)

    def _initializer(self) -> dict[str, Any]:
        start = self.cur
        if self.accept("{"):
            values = []
            if self.at("{"):
                raise UnsupportedFeatureError("nested aggregate initializers are not C48 Version 1", self.cur.pos)
            if self.at("}"):
                raise SyntaxC48Error("array initializer list must contain at least one element", self.cur.pos)
            while True:
                if self.at(".") or self.at("["):
                    raise UnsupportedFeatureError("designated initializers are not C48 Version 1", self.cur.pos)
                values.append(self._expression())
                if not self.accept(","):
                    break
                if self.at("}"):
                    break
                if self.at("{"):
                    raise UnsupportedFeatureError("nested aggregate initializers are not C48 Version 1", self.cur.pos)
            self.expect("}")
            return node("init_list", start.pos, values=values)
        # Direct string literal sequence gets a distinct initializer node.
        if self.cur.kind == "STRING_LIT":
            s = self._string_sequence()
            return node("string_initializer", start.pos, value=s)
        return node("scalar_initializer", start.pos, value=self._expression())

    def _compound_statement(self) -> dict[str, Any]:
        start = self.expect("{")
        declarations = []
        statements = []
        seen_statement = False
        while not self.at("}"):
            if self.cur.kind == "EOF":
                raise SyntaxC48Error("expected '}' before end of file", self.cur.pos)
            is_decl = (self.cur.kind == "KW" and (self.cur.text in STORAGE or self.cur.text in TYPE_START))
            if is_decl:
                if seen_statement:
                    raise UnsupportedFeatureError("local declarations must precede statements in each block", self.cur.pos)
                declarations.append(self._local_declaration())
            else:
                seen_statement = True
                statements.append(self._statement())
        self.expect("}")
        return node("compound", start.pos, declarations=declarations, statements=statements)

    def _local_declaration(self) -> dict[str, Any]:
        start = self.cur
        storage, base_type = self._storage_and_type()
        decls = [self._init_declarator_from(self._declarator())]
        while self.accept(","):
            decls.append(self._init_declarator_from(self._declarator()))
        self.expect(";")
        return node("declaration", start.pos, storage=storage, base_type=base_type,
                    declarators=decls, scope="block")

    def _statement(self) -> dict[str, Any]:
        with self.budget.nested(
            "statement",
            PARSER_STATEMENT_DEPTH,
            "statement nesting depth",
            self.cur.pos,
        ):
            return self._statement_impl()

    def _statement_impl(self) -> dict[str, Any]:
        t = self.cur
        if self.at("{"):
            return self._compound_statement()
        if self.accept("if"):
            self.expect("("); cond = self._expression(); self.expect(")")
            yes = self._statement(); no = None
            if self.accept("else"):
                no = self._statement()
            return node("if", t.pos, condition=cond, then=yes, otherwise=no)
        if self.accept("while"):
            self.expect("("); cond = self._expression(); self.expect(")")
            return node("while", t.pos, condition=cond, body=self._statement())
        if self.accept("do"):
            body = self._statement(); self.expect("while"); self.expect("(")
            cond = self._expression(); self.expect(")"); self.expect(";")
            return node("do_while", t.pos, body=body, condition=cond)
        if self.accept("for"):
            self.expect("(")
            init = None if self.at(";") else self._expression(); self.expect(";")
            cond = None if self.at(";") else self._expression(); self.expect(";")
            step = None if self.at(")") else self._expression(); self.expect(")")
            return node("for", t.pos, init=init, condition=cond, step=step, body=self._statement())
        if self.accept("break"):
            self.expect(";"); return node("break", t.pos)
        if self.accept("continue"):
            self.expect(";"); return node("continue", t.pos)
        if self.accept("return"):
            value = None if self.at(";") else self._expression(); self.expect(";")
            return node("return", t.pos, value=value)
        if self.accept(";"):
            return node("expr_stmt", t.pos, value=None)
        e = self._expression(); self.expect(";")
        return node("expr_stmt", t.pos, value=e)

    # Expression grammar, lowest precedence first.
    def _expression(self) -> dict[str, Any]:
        with self.budget.nested(
            "expression",
            PARSER_EXPRESSION_DEPTH,
            "expression nesting depth",
            self.cur.pos,
        ):
            return self._assignment()

    def _assignment(self):
        with self.budget.nested(
            "assignment",
            PARSER_ASSIGNMENT_DEPTH,
            "assignment nesting depth",
            self.cur.pos,
        ):
            return self._assignment_impl()

    def _assignment_impl(self):
        left = self._logical_or()
        if self.accept("="):
            op_pos = self.tokens[self.i-1].pos
            right = self._assignment()
            return node("assign", op_pos, left=left, right=right)
        return left

    def _left_assoc(self, sub, ops: set[str]):
        e = sub()
        while self.cur.text in ops:
            t = self.cur; self.i += 1
            e = node("binary", t.pos, op=t.text, left=e, right=sub())
        return e

    def _logical_or(self): return self._left_assoc(self._logical_and, {"||"})
    def _logical_and(self): return self._left_assoc(self._bit_or, {"&&"})
    def _bit_or(self): return self._left_assoc(self._bit_xor, {"|"})
    def _bit_xor(self): return self._left_assoc(self._bit_and, {"^"})
    def _bit_and(self): return self._left_assoc(self._equality, {"&"})
    def _equality(self): return self._left_assoc(self._relational, {"==", "!="})
    def _relational(self): return self._left_assoc(self._shift, {"<", "<=", ">", ">="})
    def _shift(self): return self._left_assoc(self._additive, {"<<", ">>"})
    def _additive(self): return self._left_assoc(self._multiplicative, {"+", "-"})
    def _multiplicative(self): return self._left_assoc(self._unary, {"*", "/", "%"})

    def _unary(self):
        with self.budget.nested(
            "unary",
            PARSER_UNARY_DEPTH,
            "unary-expression depth",
            self.cur.pos,
        ):
            return self._unary_impl()

    def _unary_impl(self):
        t = self.cur
        if t.text in {"++", "--", "+", "-", "!", "~", "&", "*"}:
            self.i += 1
            return node("unary", t.pos, op=t.text, operand=self._unary())
        if self.accept("sizeof"):
            if self.at("(") and self._looks_like_type_name(1):
                self.expect("("); tn = self._type_name(); self.expect(")")
                return node("sizeof_type", t.pos, type_name=tn)
            return node("sizeof_expr", t.pos, operand=self._unary())
        if self.at("(") and self._looks_like_type_name(1):
            self.expect("("); tn = self._type_name(); self.expect(")")
            return node("cast", t.pos, type_name=tn, operand=self._unary())
        return self._postfix()

    def _looks_like_type_name(self, offset: int) -> bool:
        j = self.i + offset
        return j < len(self.tokens) and self.tokens[j].kind == "KW" and self.tokens[j].text in TYPE_START

    def _postfix(self):
        e = self._primary()
        while True:
            if self.accept("["):
                p = self.tokens[self.i-1].pos
                idx = self._expression(); self.expect("]")
                e = node("index", p, base=e, index=idx)
            elif self.accept("("):
                p = self.tokens[self.i-1].pos
                args = []
                if not self.at(")"):
                    while True:
                        args.append(self._assignment())
                        if not self.accept(","):
                            break
                self.expect(")")
                e = node("call", p, function=e, args=args)
            elif self.cur.text in {"++", "--"}:
                t = self.cur; self.i += 1
                e = node("postfix", t.pos, op=t.text, operand=e)
            else:
                break
        return e

    def _primary(self):
        t = self.cur
        if t.kind in {"IDENT", "IMPL_IDENT"}:
            self.i += 1
            return node("identifier", t.pos, name=t.text)
        if t.kind == "UNSUPPORTED_KW":
            raise UnsupportedFeatureError(f"keyword {t.text!r} is not C48 Version 1", t.pos)
        if t.kind == "INT_LIT":
            self.i += 1
            return node("integer_literal", t.pos, value=int(t.value["value"]), unsigned_suffix=bool(t.value["unsigned"]), spelling=t.text)
        if t.kind == "CHAR_LIT":
            self.i += 1
            return node("character_literal", t.pos, value=int(t.value), spelling=t.text)
        if t.kind == "FLOAT_LIT":
            self.i += 1
            return node("floating_literal", t.pos, value=str(t.value), spelling=t.text)
        if t.kind == "STRING_LIT":
            return self._string_sequence()
        if self.accept("("):
            e = self._expression(); self.expect(")"); return e
        raise SyntaxC48Error(f"expected primary expression, found {t.text!r}", t.pos)

    def _string_sequence(self):
        first = self.cur
        data = bytearray()
        spellings = []
        while self.cur.kind == "STRING_LIT":
            spellings.append(self.cur.text)
            data.extend(self.cur.value)
            self.i += 1
        return node("string_literal", first.pos, bytes=list(data), spelling=" ".join(spellings))

    @staticmethod
    def _pos_from_dict(p: dict[str, Any]):
        # avoid importing SourcePos at module top just for reconstruction
        from .errors import SourcePos
        return SourcePos(str(p["source"]), int(p["line"]), int(p["column"]))
