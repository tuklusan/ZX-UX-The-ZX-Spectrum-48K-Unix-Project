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


@dataclass(frozen=True)
class CType:
    kind: str
    base: "CType | None" = None
    length: int | None = None
    params: tuple["CType", ...] | None = None
    ret: "CType | None" = None

    @property
    def is_void(self) -> bool:
        return self.kind == "void"

    @property
    def is_integer(self) -> bool:
        return self.kind in {"char", "uchar", "short", "ushort", "int", "uint"}

    @property
    def is_float(self) -> bool:
        return self.kind == "float"

    @property
    def is_arithmetic(self) -> bool:
        return self.is_integer or self.is_float

    @property
    def is_pointer(self) -> bool:
        return self.kind == "pointer"

    @property
    def is_array(self) -> bool:
        return self.kind == "array"

    @property
    def is_function(self) -> bool:
        return self.kind == "function"

    @property
    def is_scalar(self) -> bool:
        return self.is_arithmetic or self.is_pointer

    @property
    def is_signed(self) -> bool:
        return self.kind in {"short", "int"}

    @property
    def bits(self) -> int:
        if self.kind in {"char", "uchar"}:
            return 8
        if self.kind in {"short", "ushort", "int", "uint", "pointer"}:
            return 16
        raise ValueError(f"{self} has no integer bit width")

    @property
    def size(self) -> int:
        sizes = {
            "char": 1,
            "uchar": 1,
            "short": 2,
            "ushort": 2,
            "int": 2,
            "uint": 2,
            "pointer": 2,
            "float": 5,
        }
        if self.kind in sizes:
            return sizes[self.kind]
        if self.kind == "array":
            assert self.base is not None and self.length is not None
            return self.base.size * self.length
        raise ValueError(f"sizeof invalid for {self}")

    @property
    def alignment(self) -> int:
        if self.kind in {"char", "uchar", "float"}:
            return 1
        if self.kind in {"short", "ushort", "int", "uint", "pointer"}:
            return 2
        if self.kind == "array":
            assert self.base is not None
            return self.base.alignment
        raise ValueError(f"alignment invalid for {self}")

    def pointer_to(self) -> "CType":
        return CType("pointer", base=self)

    def decay(self) -> "CType":
        if self.is_array:
            assert self.base is not None
            return CType("pointer", base=self.base)
        return self

    def to_dict(self) -> dict:
        d: dict[str, object] = {"kind": self.kind}
        if self.base is not None:
            d["base"] = self.base.to_dict()
        if self.length is not None:
            d["length"] = self.length
        if self.params is not None:
            d["params"] = [p.to_dict() for p in self.params]
        if self.ret is not None:
            d["ret"] = self.ret.to_dict()
        return d

    @staticmethod
    def from_dict(d: dict) -> "CType":
        return CType(
            str(d["kind"]),
            base=CType.from_dict(d["base"]) if "base" in d else None,
            length=int(d["length"]) if "length" in d else None,
            params=tuple(CType.from_dict(p) for p in d["params"]) if "params" in d else None,
            ret=CType.from_dict(d["ret"]) if "ret" in d else None,
        )

    def __str__(self) -> str:
        names = {
            "void": "void", "char": "char", "uchar": "unsigned char",
            "short": "short", "ushort": "unsigned short", "int": "int",
            "uint": "unsigned int", "float": "float",
        }
        if self.kind in names:
            return names[self.kind]
        if self.kind == "pointer":
            return f"{self.base} *"
        if self.kind == "array":
            return f"{self.base}[{self.length}]"
        if self.kind == "function":
            ps = ", ".join(str(x) for x in self.params or ()) or "void"
            return f"{self.ret} ({ps})"
        return self.kind


VOID = CType("void")
CHAR = CType("char")
UCHAR = CType("uchar")
SHORT = CType("short")
USHORT = CType("ushort")
INT = CType("int")
UINT = CType("uint")
FLOAT = CType("float")

TYPE_SPELLINGS = {
    ("void",): VOID,
    ("char",): CHAR,
    ("unsigned", "char"): UCHAR,
    ("short",): SHORT,
    ("unsigned", "short"): USHORT,
    ("int",): INT,
    ("unsigned", "int"): UINT,
    ("float",): FLOAT,
}


def ptr(base: CType) -> CType:
    return CType("pointer", base=base)


def array(base: CType, length: int) -> CType:
    return CType("array", base=base, length=length)


def function(ret: CType, params: list[CType] | tuple[CType, ...]) -> CType:
    return CType("function", params=tuple(params), ret=ret)


def integer_promotion(t: CType) -> CType:
    if t.kind in {"char", "uchar", "short"}:
        return INT
    if t.kind == "ushort":
        return UINT
    if t.kind in {"int", "uint"}:
        return t
    raise ValueError(f"not integer: {t}")


def arithmetic_common(a: CType, b: CType) -> CType:
    if a.is_float or b.is_float:
        if not (a.is_arithmetic and b.is_arithmetic):
            raise ValueError("not arithmetic")
        return FLOAT
    aa = integer_promotion(a)
    bb = integer_promotion(b)
    return UINT if aa == UINT or bb == UINT else INT


def exact_compatible(a: CType, b: CType) -> bool:
    return a == b


def can_assign(dst: CType, src: CType, *, null_constant: bool = False) -> bool:
    if dst == src:
        return True
    if dst.is_arithmetic and src.is_arithmetic:
        return True
    if dst.is_pointer:
        if null_constant:
            return True
        if not src.is_pointer:
            return False
        assert dst.base is not None and src.base is not None
        if dst.base.is_void or src.base.is_void:
            return True
        return exact_compatible(dst.base, src.base)
    return False


def align_up(n: int, align: int) -> int:
    if align <= 1:
        return n
    return (n + align - 1) & ~(align - 1)
