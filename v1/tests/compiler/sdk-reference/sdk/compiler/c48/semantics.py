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
from fractions import Fraction
from typing import Any

from .errors import (C48Error, ConstantExpressionError, DeclarationError, SourcePos,
                     TypeC48Error, UnsupportedFeatureError)
from .float5 import Float5, Float5Error
from .limits import CONST_EVAL_DEPTH, ResourceBudget
from .typesys import (CHAR, FLOAT, INT, SHORT, UCHAR, UINT, USHORT, VOID, CType,
                      TYPE_SPELLINGS, arithmetic_common, array, can_assign,
                      function, integer_promotion, ptr)


def spos(d: dict[str, Any]) -> SourcePos:
    p = d.get("pos") or {"source":"<source>","line":1,"column":1}
    return SourcePos(str(p["source"]), int(p["line"]), int(p["column"]))


def type_to_json(t: CType) -> dict[str, Any]:
    return t.to_dict()


def type_from_node(n: dict[str, Any], pointer_extra: int = 0) -> CType:
    spelling = tuple(n["spelling"])
    if spelling not in TYPE_SPELLINGS:
        raise TypeC48Error(f"unsupported type spelling {' '.join(spelling)}", spos(n))
    t = TYPE_SPELLINGS[spelling]
    depth = int(n.get("pointers", 0)) + pointer_extra
    ResourceBudget.check_pointer_depth(depth, spos(n))
    for _ in range(depth):
        t = ptr(t)
    return t


@dataclass
class Symbol:
    name: str
    ctype: CType
    entity: str  # object/function
    linkage: str | None
    defined: bool
    storage: str | None
    pos: SourcePos


@dataclass(frozen=True)
class ConstValue:
    ctype: CType
    value: int | Float5 | tuple[str, str, int] | tuple[str, bytes]
    # pointer constant representations:
    # ('global', name, byte_offset) / ('string', bytes)


class SemanticAnalyzer:
    def __init__(self, *, budget: ResourceBudget | None = None):
        self.budget = budget or ResourceBudget()
        self.globals: dict[str, Symbol] = {}
        self.functions: dict[str, Symbol] = {}
        self.scopes: list[dict[str, Symbol]] = []
        self.current_function: Symbol | None = None
        self.loop_depth = 0
        self.string_counter = 0

    def analyze(self, tu: dict[str, Any]) -> dict[str, Any]:
        # One source-order pass is intentional: a function must be declared before call.
        for item in tu["items"]:
            if item["kind"] == "declaration":
                self._declaration(item, file_scope=True)
            elif item["kind"] == "function_definition":
                self._function_definition(item)
            else:
                raise AssertionError(item["kind"])
        # Emit a compact symbol manifest for runtime/link-style inspection.
        tu["symbols"] = {
            name: {"type": s.ctype.to_dict(), "entity": s.entity, "linkage": s.linkage,
                   "defined": s.defined, "storage": s.storage}
            for name, s in sorted({**self.globals, **self.functions}.items())
        }
        return tu

    def _check_user_name(self, name: str, n: dict[str, Any]) -> None:
        if name == "_start" or name.startswith("__"):
            raise DeclarationError(f"identifier {name!r} is reserved to the C48 implementation", spos(n))

    def _decl_type(self, base_node: dict[str, Any], decl: dict[str, Any], *, allow_function: bool = True) -> CType:
        base = type_from_node(base_node)
        for _ in range(int(decl.get("pointers", 0))):
            base = ptr(base)
        suffix = decl.get("suffix")
        if not suffix:
            return base
        if suffix["kind"] == "array":
            if base.is_void or base.is_function or base.is_array:
                raise TypeC48Error("array element type must be a complete non-array object type", spos(decl))
            bound_expr = suffix.get("bound")
            if bound_expr is None:
                return CType("array", base=base, length=None)
            cv = self.const_eval(bound_expr)
            if not cv.ctype.is_integer:
                raise ConstantExpressionError("array bound must be an integer constant expression", spos(bound_expr))
            count = self._as_unsigned_math(cv)
            if count <= 0:
                raise TypeC48Error("array bound must be positive", spos(bound_expr))
            size = count * base.size
            if size > 65535:
                raise TypeC48Error("array object size exceeds unsigned-int sizeof domain", spos(bound_expr))
            return array(base, count)
        if suffix["kind"] == "function":
            if not allow_function:
                raise UnsupportedFeatureError("function declarator is not valid here", spos(decl))
            if base.is_array or base.is_function:
                raise TypeC48Error("function cannot return array/function", spos(decl))
            params = []
            for p in suffix["params"]:
                pt = type_from_node(p["type"], int(p.get("pointers",0)))
                if pt.is_void:
                    raise TypeC48Error("plain void is not a parameter type", spos(p))
                if pt.is_array or pt.is_function:
                    raise TypeC48Error("parameter type must be scalar or pointer", spos(p))
                params.append(pt)
                p["ctype"] = pt.to_dict()
            return function(base, params)
        raise AssertionError(suffix)

    def _declare_file_symbol(self, name: str, ctype: CType, storage: str | None,
                             is_definition: bool, n: dict[str, Any]) -> Symbol:
        self._check_user_name(name, n)
        entity = "function" if ctype.is_function else "object"
        linkage = "internal" if storage == "static" else "external"
        table = self.functions if entity == "function" else self.globals
        other = self.globals if entity == "function" else self.functions
        if name in other:
            raise DeclarationError(f"{name!r} already declared as different entity kind", spos(n))
        old = table.get(name)
        if old:
            if old.ctype != ctype:
                raise DeclarationError(f"conflicting exact type for {name!r}: {old.ctype} vs {ctype}", spos(n))
            if old.linkage != linkage:
                # extern declarations are external; an unqualified definition stays external.
                raise DeclarationError(f"static/external linkage conflict for {name!r}", spos(n))
            if is_definition and old.defined:
                raise DeclarationError(f"duplicate definition of {name!r}", spos(n))
            old.defined = old.defined or is_definition
            return old
        s = Symbol(name, ctype, entity, linkage, is_definition, storage, spos(n))
        table[name] = s
        return s

    def _declaration(self, d: dict[str, Any], *, file_scope: bool) -> None:
        storage = d.get("storage")
        if not file_scope and storage is not None:
            raise UnsupportedFeatureError("block-scope static/extern declarations are not C48 Version 1", spos(d))
        for idecl in d["declarators"]:
            decl = idecl["declarator"]
            name = decl["name"]
            self._check_user_name(name, decl)
            ctype = self._decl_type(d["base_type"], decl)
            init = idecl.get("initializer")
            if file_scope:
                is_func = ctype.is_function
                if is_func and init is not None:
                    raise TypeC48Error("function declaration cannot have initializer", spos(idecl))
                if is_func:
                    is_definition = False
                else:
                    if storage == "extern" and init is not None:
                        raise DeclarationError("extern object declaration cannot have initializer", spos(idecl))
                    is_definition = storage != "extern"
                if name == "main":
                    if not is_func:
                        raise DeclarationError("file-scope object named main is forbidden", spos(decl))
                    if storage == "static":
                        raise DeclarationError("main prototype cannot have internal/static linkage", spos(decl))
                    self._validate_main_type(ctype, declaration=True, pos=spos(decl))
                sym = self._declare_file_symbol(name, ctype, storage, is_definition, decl)
                idecl["ctype"] = ctype.to_dict()
                idecl["definition"] = bool(is_definition)
                idecl["linkage"] = sym.linkage
                if is_definition:
                    final_type = self._validate_initializer(ctype, init, idecl, file_scope=True)
                    if final_type != ctype:
                        sym.ctype = final_type; idecl["ctype"] = final_type.to_dict()
                elif init is not None:
                    raise AssertionError
            else:
                if ctype.is_function:
                    raise UnsupportedFeatureError("block-scope function declarations are not C48 Version 1", spos(decl))
                if ctype.is_void:
                    raise TypeC48Error("void object is invalid", spos(decl))
                scope = self.scopes[-1]
                if name in scope:
                    raise DeclarationError(f"redeclaration of {name!r} in same scope", spos(decl))
                sym = Symbol(name, ctype, "object", None, True, None, spos(decl))
                scope[name] = sym
                final_type = self._validate_initializer(ctype, init, idecl, file_scope=False)
                sym.ctype = final_type; idecl["ctype"] = final_type.to_dict()

    def _validate_main_type(self, ctype: CType, *, declaration: bool, pos: SourcePos) -> None:
        if not ctype.is_function or ctype.ret != INT:
            raise DeclarationError("main must return int", pos)
        params = ctype.params or ()
        ok0 = len(params) == 0
        ok2 = len(params) == 2 and params[0] == INT and params[1] == ptr(ptr(CHAR))
        if not (ok0 or ok2):
            raise DeclarationError("main must be exactly int main(void) or int main(int,char **)", pos)

    def _function_definition(self, f: dict[str, Any]) -> None:
        storage = f.get("storage")
        if storage == "extern":
            raise DeclarationError("extern is not permitted on a function definition", spos(f))
        decl = f["declarator"]
        name = decl["name"]
        ctype = self._decl_type(f["base_type"], decl)
        if not ctype.is_function:
            raise SyntaxError("internal parser error: definition without function type")
        if name == "main":
            if storage is not None:
                raise DeclarationError("main definition must have external linkage and no storage class", spos(f))
            self._validate_main_type(ctype, declaration=False, pos=spos(f))
        sym = self._declare_file_symbol(name, ctype, storage, True, decl)
        f["ctype"] = ctype.to_dict()

        # Function parameters share the outermost body scope.
        old_fn = self.current_function
        self.current_function = sym
        outer: dict[str, Symbol] = {}
        self.scopes.append(outer)
        params = decl["suffix"]["params"]
        seen = set()
        for pnode, pt in zip(params, ctype.params or ()):
            pname = pnode["name"]
            if pname is None:
                raise DeclarationError("function definition parameter must be named", spos(pnode))
            self._check_user_name(pname, pnode)
            if pname in seen:
                raise DeclarationError(f"duplicate parameter name {pname!r}", spos(pnode))
            seen.add(pname)
            outer[pname] = Symbol(pname, pt, "object", None, True, None, spos(pnode))
            pnode["ctype"] = pt.to_dict()
        self._compound(f["body"], reuse_current_scope=True)
        self.scopes.pop()
        self.current_function = old_fn

    def _compound(self, b: dict[str, Any], *, reuse_current_scope: bool = False) -> None:
        if not reuse_current_scope:
            self.scopes.append({})
        try:
            for d in b["declarations"]:
                self._declaration(d, file_scope=False)
            for s in b["statements"]:
                self._statement(s)
        finally:
            if not reuse_current_scope:
                self.scopes.pop()

    def _statement(self, s: dict[str, Any]) -> None:
        k = s["kind"]
        if k == "compound":
            self._compound(s); return
        if k == "expr_stmt":
            if s["value"] is not None: self.expr(s["value"])
            return
        if k == "if":
            self._require_scalar(self.expr(s["condition"]), s["condition"])
            self._statement(s["then"])
            if s["otherwise"] is not None: self._statement(s["otherwise"])
            return
        if k in {"while", "do_while", "for"}:
            if k == "for":
                if s["init"] is not None: self.expr(s["init"])
                if s["condition"] is not None: self._require_scalar(self.expr(s["condition"]), s["condition"])
                if s["step"] is not None: self.expr(s["step"])
            else:
                self._require_scalar(self.expr(s["condition"]), s["condition"])
            self.loop_depth += 1
            try: self._statement(s["body"])
            finally: self.loop_depth -= 1
            return
        if k in {"break", "continue"}:
            if self.loop_depth <= 0:
                raise TypeC48Error(f"{k} is valid only inside a loop", spos(s))
            return
        if k == "return":
            assert self.current_function and self.current_function.ctype.ret
            rt = self.current_function.ctype.ret
            value = s.get("value")
            if rt.is_void:
                if value is not None: raise TypeC48Error("void function cannot return a value", spos(s))
            else:
                if value is None: raise TypeC48Error("non-void function return requires a value", spos(s))
                vt = self.expr(value)
                if not self._assignment_compatible(rt, vt, value):
                    raise TypeC48Error(f"cannot return {vt} from function returning {rt}", spos(value))
            s["return_type"] = rt.to_dict()
            return
        raise AssertionError(k)

    def lookup(self, name: str, n: dict[str, Any]) -> Symbol:
        if name == "_start" or name.startswith("__"):
            raise DeclarationError(f"implementation-reserved identifier {name!r} is unavailable to user source", spos(n))
        for scope in reversed(self.scopes):
            if name in scope: return scope[name]
        if name in self.globals: return self.globals[name]
        if name in self.functions: return self.functions[name]
        raise DeclarationError(f"undeclared identifier {name!r}", spos(n))

    def _set(self, n: dict[str, Any], t: CType, lvalue: bool = False, modifiable: bool | None = None) -> CType:
        n["ctype"] = t.to_dict(); n["lvalue"] = bool(lvalue)
        if modifiable is None: modifiable = lvalue and not t.is_array and not t.is_function
        n["modifiable"] = bool(modifiable)
        return t

    def expr(self, n: dict[str, Any], *, decay: bool = True) -> CType:
        k = n["kind"]
        if k == "identifier":
            s = self.lookup(n["name"], n)
            n["entity"] = s.entity
            t = s.ctype
            if s.entity == "function": return self._set(n, t, False, False)
            if t.is_array and decay:
                assert t.base is not None
                return self._set(n, ptr(t.base), False, False)
            return self._set(n, t, True, not t.is_array)
        if k == "integer_literal":
            t = UINT if n["unsigned_suffix"] or n["value"] > 32767 else INT
            return self._set(n, t)
        if k == "character_literal": return self._set(n, INT)
        if k == "floating_literal":
            try: f = Float5.from_decimal(n["value"])
            except Float5Error as e: raise ConstantExpressionError(str(e), spos(n)) from None
            n["float5"] = f.hex(); return self._set(n, FLOAT)
        if k == "string_literal":
            if "sid" not in n:
                n["sid"] = self.string_counter
                self.string_counter += 1
            t = array(CHAR, len(n["bytes"]) + 1)
            if decay:
                self._set(n, ptr(CHAR), False, False)
            else:
                self._set(n, t, True, False)
            return CType.from_dict(n["ctype"])
        if k == "sizeof_type":
            t = type_from_node(n["type_name"])
            if t.is_void or t.is_function: raise TypeC48Error("sizeof requires complete object type", spos(n))
            n["sizeof_value"] = t.size
            return self._set(n, UINT)
        if k == "sizeof_expr":
            t = self.expr(n["operand"], decay=False)
            if t.is_void or t.is_function: raise TypeC48Error("sizeof requires complete object type", spos(n))
            n["sizeof_value"] = t.size
            return self._set(n, UINT)
        if k == "cast":
            dst = type_from_node(n["type_name"])
            src = self.expr(n["operand"])
            valid = ((dst.is_integer and src.is_integer) or
                     (dst.is_float and src.is_integer) or
                     (dst.is_integer and src.is_float))
            if not valid:
                raise UnsupportedFeatureError("C48 casts are only among integer types and integer<->float", spos(n))
            return self._set(n, dst)
        if k == "unary":
            op = n["op"]
            if op == "&":
                t = self.expr(n["operand"], decay=False)
                if t.is_array: raise TypeC48Error("address-of array would create unsupported pointer-to-array type", spos(n))
                if not n["operand"].get("lvalue") or t.is_function:
                    raise TypeC48Error("address-of requires object lvalue", spos(n))
                return self._set(n, ptr(t))
            if op == "*":
                t = self.expr(n["operand"])
                if not t.is_pointer or t.base is None or t.base.is_void:
                    raise TypeC48Error("dereference requires non-void object pointer", spos(n))
                return self._set(n, t.base, True, True)
            if op in {"++","--"}:
                t = self.expr(n["operand"], decay=False)
                self._require_mod_scalar(n["operand"])
                if t.is_pointer and (t.base is None or t.base.is_void):
                    raise TypeC48Error("increment/decrement of void * is invalid", spos(n))
                if not (t.is_arithmetic or t.is_pointer): raise TypeC48Error("invalid ++/-- operand", spos(n))
                return self._set(n, t)
            t = self.expr(n["operand"])
            if op in {"+","-"}:
                if not t.is_arithmetic: raise TypeC48Error(f"unary {op} requires arithmetic operand", spos(n))
                return self._set(n, FLOAT if t.is_float else integer_promotion(t))
            if op == "~":
                if not t.is_integer: raise TypeC48Error("~ requires integer operand", spos(n))
                return self._set(n, integer_promotion(t))
            if op == "!":
                self._require_scalar(t,n); return self._set(n, INT)
            raise AssertionError(op)
        if k == "postfix":
            t = self.expr(n["operand"], decay=False)
            self._require_mod_scalar(n["operand"])
            if t.is_pointer and (t.base is None or t.base.is_void): raise TypeC48Error("increment/decrement of void * is invalid", spos(n))
            return self._set(n,t)
        if k == "index":
            bt = self.expr(n["base"])
            it = self.expr(n["index"])
            if not bt.is_pointer or bt.base is None or bt.base.is_void: raise TypeC48Error("index base must be non-void pointer/array", spos(n["base"]))
            if not it.is_integer: raise TypeC48Error("array index must be integer", spos(n["index"]))
            return self._set(n, bt.base, True, True)
        if k == "call":
            ft = self.expr(n["function"], decay=False)
            if n["function"]["kind"] != "identifier" or not ft.is_function:
                raise TypeC48Error("C48 supports direct calls to declared function identifiers only", spos(n))
            args = n["args"]; params = ft.params or ()
            if len(args) != len(params): raise TypeC48Error(f"function expects {len(params)} arguments, got {len(args)}", spos(n))
            for a,p in zip(args,params):
                at = self.expr(a)
                if not self._assignment_compatible(p, at, a): raise TypeC48Error(f"argument type {at} incompatible with parameter {p}", spos(a))
            assert ft.ret is not None
            return self._set(n,ft.ret)
        if k == "assign":
            lt = self.expr(n["left"], decay=False)
            self._require_mod_scalar(n["left"])
            rt = self.expr(n["right"])
            if not self._assignment_compatible(lt,rt,n["right"]): raise TypeC48Error(f"cannot assign {rt} to {lt}", spos(n))
            return self._set(n,lt)
        if k == "binary":
            op=n["op"]
            if op in {"&&","||"}:
                a=self.expr(n["left"]); self._require_scalar(a,n["left"])
                b=self.expr(n["right"]); self._require_scalar(b,n["right"])
                return self._set(n,INT)
            a=self.expr(n["left"]); b=self.expr(n["right"])
            if op in {"<<",">>"}:
                if not (a.is_integer and b.is_integer): raise TypeC48Error("shift operands must be integer", spos(n))
                n["shift_width"] = a.bits
                return self._set(n,a)
            if op in {"&","|","^","%"}:
                if not (a.is_integer and b.is_integer): raise TypeC48Error(f"{op} requires integer operands", spos(n))
                return self._set(n,arithmetic_common(a,b))
            if op in {"*","/"}:
                if not (a.is_arithmetic and b.is_arithmetic): raise TypeC48Error(f"{op} requires arithmetic operands", spos(n))
                return self._set(n,arithmetic_common(a,b))
            if op in {"+","-"}:
                if a.is_arithmetic and b.is_arithmetic: return self._set(n,arithmetic_common(a,b))
                if op=="+" and a.is_pointer and b.is_integer:
                    self._require_sized_pointer(a,n); return self._set(n,a)
                if op=="+" and a.is_integer and b.is_pointer:
                    self._require_sized_pointer(b,n); return self._set(n,b)
                if op=="-" and a.is_pointer and b.is_integer:
                    self._require_sized_pointer(a,n); return self._set(n,a)
                if op=="-" and a.is_pointer and b.is_pointer:
                    if a != b or a.base is None or a.base.is_void: raise TypeC48Error("pointer subtraction requires exactly compatible non-void pointer types", spos(n))
                    return self._set(n,INT)
                raise TypeC48Error(f"invalid pointer/arithmetic operands for {op}", spos(n))
            if op in {"==","!="}:
                if a.is_arithmetic and b.is_arithmetic: return self._set(n,INT)
                if a.is_pointer and b.is_pointer:
                    if not self._pointer_equality_compatible(a,b): raise TypeC48Error("incompatible pointer equality operands", spos(n))
                    return self._set(n,INT)
                if a.is_pointer and self._is_null_constant(n["right"]): return self._set(n,INT)
                if b.is_pointer and self._is_null_constant(n["left"]): return self._set(n,INT)
                raise TypeC48Error("invalid equality operands", spos(n))
            if op in {"<","<=",">",">="}:
                if a.is_arithmetic and b.is_arithmetic: return self._set(n,INT)
                if a.is_pointer and b.is_pointer and a==b and a.base is not None and not a.base.is_void:
                    return self._set(n,INT)
                raise TypeC48Error("relational pointer comparison requires exactly compatible non-void pointers", spos(n))
            raise AssertionError(op)
        raise AssertionError(k)

    def _require_scalar(self,t:CType,n:dict[str,Any])->None:
        if not t.is_scalar: raise TypeC48Error("scalar expression required", spos(n))

    def _require_mod_scalar(self,n:dict[str,Any])->None:
        t=CType.from_dict(n["ctype"])
        if not n.get("lvalue") or not n.get("modifiable") or not t.is_scalar:
            raise TypeC48Error("modifiable scalar lvalue required", spos(n))

    def _require_sized_pointer(self,t:CType,n:dict[str,Any])->None:
        if not t.is_pointer or t.base is None or t.base.is_void: raise TypeC48Error("pointer arithmetic requires pointer to complete object", spos(n))

    def _pointer_equality_compatible(self,a:CType,b:CType)->bool:
        if a==b: return True
        return bool(a.base and b.base and (a.base.is_void or b.base.is_void))

    def _is_null_constant(self,n:dict[str,Any])->bool:
        try:
            cv=self.const_eval(n)
            return cv.ctype.is_integer and self._as_unsigned_math(cv)==0
        except C48Error:
            return False

    def _assignment_compatible(self,dst:CType,src:CType,srcnode:dict[str,Any])->bool:
        if dst.is_arithmetic and src.is_arithmetic: return True
        if dst.is_pointer:
            if self._is_null_constant(srcnode): return True
            if not src.is_pointer: return False
            if dst==src: return True
            return bool(dst.base and src.base and (dst.base.is_void or src.base.is_void))
        return False

    def _validate_initializer(self,t:CType,init:dict[str,Any]|None,where:dict[str,Any],*,file_scope:bool)->CType:
        if t.is_function:
            if init is not None: raise TypeC48Error("function cannot have initializer", spos(where))
            return t
        if t.is_void: raise TypeC48Error("void object is invalid", spos(where))
        if init is None:
            if t.is_array and t.length is None: raise TypeC48Error("array with omitted bound requires initializer", spos(where))
            return t
        k=init["kind"]
        if t.is_array:
            assert t.base is not None
            if k=="string_initializer":
                if t.base not in {CHAR,UCHAR}: raise TypeC48Error("string initializer only valid for char/unsigned char array", spos(init))
                self.expr(init["value"], decay=False)
                nbytes=len(init["value"]["bytes"])+1
                length=t.length if t.length is not None else nbytes
                if nbytes>length: raise TypeC48Error("string plus terminating NUL exceeds array bound", spos(init))
                cv=ConstValue(ptr(CHAR),("string",bytes(init["value"]["bytes"])))
                init["const"] = self._const_json(cv)
                return array(t.base,length)
            if k!="init_list": raise TypeC48Error("array initializer must be braced list or character string", spos(init))
            vals=init["values"]
            length=t.length if t.length is not None else len(vals)
            if len(vals)>length: raise TypeC48Error("too many array initializer elements", spos(init))
            if length<=0: raise TypeC48Error("array initializer cannot infer zero length", spos(init))
            const_items=[]
            for e in vals:
                self.expr(e)
                cv=self.const_eval(e)
                if not self._const_assignable(t.base,cv,e): raise TypeC48Error(f"constant initializer {cv.ctype} incompatible with array element {t.base}", spos(e))
                const_items.append(self._const_json(self._convert_const(cv,t.base,e)))
            init["const_items"] = const_items
            return array(t.base,length)
        if k in {"init_list","string_initializer"}:
            if k=="string_initializer" and t.is_pointer:
                e=init["value"]
                self.expr(e)
                st=ptr(CHAR)
                if not self._assignment_compatible(t,st,e): raise TypeC48Error("string address incompatible with pointer initializer", spos(init))
                cv=ConstValue(ptr(CHAR),("string",bytes(e["bytes"])))
                init["const"] = self._const_json(cv)
                return t
            raise TypeC48Error("scalar object requires scalar constant initializer", spos(init))
        self.expr(init["value"])
        cv=self.const_eval(init["value"])
        if not self._const_assignable(t,cv,init["value"]): raise TypeC48Error(f"constant initializer {cv.ctype} incompatible with {t}", spos(init))
        init["const"] = self._const_json(cv)
        return t

    def _const_assignable(self,dst:CType,cv:ConstValue,n:dict[str,Any])->bool:
        if dst.is_arithmetic and cv.ctype.is_arithmetic:
            # Force compile-time conversion to detect float range failures.
            self._convert_const(cv,dst,n); return True
        if dst.is_pointer:
            if cv.ctype.is_integer and self._as_unsigned_math(cv)==0: return True
            if cv.ctype.is_pointer:
                return dst==cv.ctype or bool(dst.base and cv.ctype.base and (dst.base.is_void or cv.ctype.base.is_void))
        return False

    # ---- constant evaluator ----
    def const_eval(self,n:dict[str,Any])->ConstValue:
        with self.budget.nested(
            "const-eval",
            CONST_EVAL_DEPTH,
            "constant-expression depth",
            spos(n),
        ):
            return self._const_eval(n)

    def _const_eval(self,n:dict[str,Any])->ConstValue:
        k=n["kind"]
        if k=="integer_literal":
            t=UINT if n["unsigned_suffix"] or n["value"]>32767 else INT
            return ConstValue(t,self._normalize_int(n["value"],t))
        if k=="character_literal": return ConstValue(INT,int(n["value"]))
        if k=="floating_literal":
            try:return ConstValue(FLOAT,Float5.from_decimal(n["value"]))
            except Float5Error as e: raise ConstantExpressionError(str(e),spos(n)) from None
        if k=="string_literal": return ConstValue(ptr(CHAR),("string",bytes(n["bytes"])))
        if k=="sizeof_type":
            t=type_from_node(n["type_name"])
            if t.is_void or t.is_function: raise ConstantExpressionError("invalid sizeof type",spos(n))
            return ConstValue(UINT,t.size)
        if k=="sizeof_expr":
            # Need semantic type without executing operand. Type-check it if not already annotated.
            t=self.expr(n["operand"],decay=False)
            if t.is_void or t.is_function: raise ConstantExpressionError("invalid sizeof operand",spos(n))
            return ConstValue(UINT,t.size)
        if k=="cast":
            dst=type_from_node(n["type_name"]); src=self.const_eval(n["operand"])
            if not dst.is_arithmetic or not src.ctype.is_arithmetic: raise ConstantExpressionError("unsupported constant cast",spos(n))
            return self._convert_const(src,dst,n)
        if k=="unary":
            op=n["op"]
            if op in {"++","--","*"}: raise ConstantExpressionError("side effect/dereference not permitted in constant expression",spos(n))
            if op=="&":
                operand=n["operand"]
                if operand["kind"]!="identifier": raise ConstantExpressionError("constant address must name file-scope object",spos(n))
                name=operand["name"]
                sym=self.globals.get(name)
                if not sym or sym.entity!="object":
                    raise ConstantExpressionError("constant address requires a declared file-scope object",spos(n))
                # OBJ1 may legitimately carry an unresolved external reference.
                # A prior `extern` declaration is therefore sufficient here; a
                # definition may occur later in this translation unit or be supplied
                # by another module at native link time.
                return ConstValue(ptr(sym.ctype),("global",name,0))
            a=self.const_eval(n["operand"])
            if op=="!": return ConstValue(INT,0 if self._const_truth(a) else 1)
            if op=="~":
                if not a.ctype.is_integer: raise ConstantExpressionError("~ requires integer",spos(n))
                t=integer_promotion(a.ctype); v=self._normalize_int(~self._int_math(self._convert_const(a,t,n)),t); return ConstValue(t,v)
            if op in {"+","-"}:
                if a.ctype.is_float:
                    if op=="+":return a
                    try:return ConstValue(FLOAT,a.value.neg())
                    except Float5Error as e:raise ConstantExpressionError(str(e),spos(n)) from None
                if not a.ctype.is_integer:raise ConstantExpressionError("unary arithmetic requires arithmetic",spos(n))
                t=integer_promotion(a.ctype); av=self._int_math(self._convert_const(a,t,n)); return ConstValue(t,self._normalize_int(av if op=="+" else -av,t))
            raise ConstantExpressionError("operator not allowed in constant expression",spos(n))
        if k=="binary":
            op=n["op"]
            a=self.const_eval(n["left"])
            if op=="&&" and not self._const_truth(a):return ConstValue(INT,0)
            if op=="||" and self._const_truth(a):return ConstValue(INT,1)
            b=self.const_eval(n["right"])
            if op in {"&&","||"}:return ConstValue(INT,1 if self._const_truth(b) else 0)
            return self._const_binary(op,a,b,n)
        if k=="identifier":
            raise ConstantExpressionError("identifier is not a constant expression",spos(n))
        if k in {"assign","postfix","call","index"}:raise ConstantExpressionError("run-time expression not permitted in constant expression",spos(n))
        raise ConstantExpressionError("expression is not a supported constant expression",spos(n))

    def _const_binary(self,op:str,a:ConstValue,b:ConstValue,n:dict[str,Any])->ConstValue:
        # Pointer constant +/- integer offset.
        if op in {"+","-"} and a.ctype.is_pointer and b.ctype.is_integer and isinstance(a.value,tuple):
            if a.ctype.base is None or a.ctype.base.is_void:raise ConstantExpressionError("void pointer arithmetic invalid",spos(n))
            delta=self._int_math(b)*a.ctype.base.size
            if op=="-":delta=-delta
            if a.value[0]=="global":return ConstValue(a.ctype,("global",a.value[1],int(a.value[2])+delta))
            raise ConstantExpressionError("string pointer offset constant not supported in initializer",spos(n))
        if a.ctype.is_arithmetic and b.ctype.is_arithmetic:
            if op in {"<<",">>"}:
                if not (a.ctype.is_integer and b.ctype.is_integer):raise ConstantExpressionError("shift requires integers",spos(n))
                width=a.ctype.bits; count=self._int_math(b)&(7 if width==8 else 15); av=self._int_math(a)
                if op=="<<":v=av<<count
                else:
                    if a.ctype.is_signed:v=av>>count
                    else:v=(av & ((1<<width)-1))>>count
                return ConstValue(a.ctype,self._normalize_int(v,a.ctype))
            if op in {"&","|","^","%"} and (not a.ctype.is_integer or not b.ctype.is_integer):raise ConstantExpressionError(f"{op} requires integers",spos(n))
            common=arithmetic_common(a.ctype,b.ctype)
            aa=self._convert_const(a,common,n); bb=self._convert_const(b,common,n)
            if common.is_float:
                fa=aa.value;fb=bb.value; assert isinstance(fa,Float5) and isinstance(fb,Float5)
                try:
                    if op=="+":r=fa.add(fb)
                    elif op=="-":r=fa.sub(fb)
                    elif op=="*":r=fa.mul(fb)
                    elif op=="/":r=fa.div(fb)
                    elif op in {"==","!=","<","<=",">",">="}:
                        c=fa.compare(fb); z={"==":c==0,"!=":c!=0,"<":c<0,"<=":c<=0,">":c>0,">=":c>=0}[op]; return ConstValue(INT,int(z))
                    else:raise ConstantExpressionError(f"operator {op} invalid for float",spos(n))
                except Float5Error as e:raise ConstantExpressionError(str(e),spos(n)) from None
                return ConstValue(FLOAT,r)
            av=self._int_math(aa);bv=self._int_math(bb); unsigned=common.kind=="uint"
            if op=="+":v=av+bv
            elif op=="-":v=av-bv
            elif op=="*":v=av*bv
            elif op in {"/","%"}:
                if bv==0:raise ConstantExpressionError("division/remainder by zero",spos(n))
                if unsigned:q=av//bv
                else:q=abs(av)//abs(bv); q=-q if (av<0)^(bv<0) else q
                v=q if op=="/" else av-q*bv
            elif op=="&":v=(av&0xFFFF)&(bv&0xFFFF)
            elif op=="|":v=(av&0xFFFF)|(bv&0xFFFF)
            elif op=="^":v=(av&0xFFFF)^(bv&0xFFFF)
            elif op in {"==","!=","<","<=",">",">="}:
                z={"==":av==bv,"!=":av!=bv,"<":av<bv,"<=":av<=bv,">":av>bv,">=":av>=bv}[op];return ConstValue(INT,int(z))
            else:raise ConstantExpressionError(f"operator {op} invalid",spos(n))
            return ConstValue(common,self._normalize_int(v,common))
        raise ConstantExpressionError("non-arithmetic constant expression",spos(n))

    def _convert_const(self,cv:ConstValue,dst:CType,n:dict[str,Any])->ConstValue:
        if cv.ctype==dst:return cv
        if dst.is_integer and cv.ctype.is_integer:return ConstValue(dst,self._normalize_int(self._int_math(cv),dst))
        if dst.is_float and cv.ctype.is_integer:
            try:return ConstValue(FLOAT,Float5.from_int(self._int_math(cv)))
            except Float5Error as e:raise ConstantExpressionError(str(e),spos(n)) from None
        if dst.is_integer and cv.ctype.is_float:
            f=cv.value;assert isinstance(f,Float5); v=f.trunc_int()
            if dst in {SHORT,INT} and not -32768<=v<=32767:raise ConstantExpressionError("float-to-signed conversion out of range",spos(n))
            if dst in {USHORT,UINT} and not 0<=v<=65535:raise ConstantExpressionError("float-to-unsigned conversion out of range",spos(n))
            if dst in {CHAR,UCHAR}:
                if not 0<=v<=65535:raise ConstantExpressionError("float-to-char conversion out of unsigned 16-bit range",spos(n))
            return ConstValue(dst,self._normalize_int(v,dst))
        if dst.is_float and cv.ctype.is_float:return cv
        raise ConstantExpressionError("unsupported constant conversion",spos(n))

    @staticmethod
    def _normalize_int(v:int,t:CType)->int:
        mask=(1<<t.bits)-1; u=v&mask
        if t.is_signed and u&(1<<(t.bits-1)):return u-(1<<t.bits)
        return u
    @staticmethod
    def _int_math(cv:ConstValue)->int:
        if not cv.ctype.is_integer:raise TypeError
        return int(cv.value)
    @staticmethod
    def _as_unsigned_math(cv:ConstValue)->int:
        if not cv.ctype.is_integer:raise TypeError
        return int(cv.value)&((1<<cv.ctype.bits)-1)
    @staticmethod
    def _const_truth(cv:ConstValue)->bool:
        if cv.ctype.is_integer:return int(cv.value)!=0
        if cv.ctype.is_float:return not cv.value.is_zero()  # type: ignore[union-attr]
        if cv.ctype.is_pointer:return bool(cv.value)
        raise ConstantExpressionError("scalar required")
    @staticmethod
    def _const_json(cv:ConstValue)->dict[str,Any]:
        if isinstance(cv.value,Float5): val={"float5":cv.value.hex()}
        elif isinstance(cv.value,tuple):
            if cv.value[0]=="string":val={"string":list(cv.value[1])}
            else:val={"global":cv.value[1],"offset":cv.value[2]}
        else:val=int(cv.value)
        return {"ctype":cv.ctype.to_dict(),"value":val}
