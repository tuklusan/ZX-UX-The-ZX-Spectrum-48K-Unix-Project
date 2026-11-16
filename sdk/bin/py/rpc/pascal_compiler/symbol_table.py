"""Symbol-table primitives shared by parsing and code generation."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

from dataclasses import dataclass

from .errors import PascalError


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    type_name: str
    value: int | None = None
    address: int | None = None


class SymbolTable:
    def __init__(self) -> None:
        self._symbols: dict[str, Symbol] = {}

    def add_constant(self, name: str, value: int) -> Symbol:
        return self._add(Symbol(name, "constant", "integer", value=value))

    def add_variable(self, name: str, type_name: str, address: int) -> Symbol:
        return self._add(Symbol(name, "variable", type_name, address=address))

    def _add(self, symbol: Symbol) -> Symbol:
        if symbol.name in self._symbols:
            raise PascalError(f"duplicate identifier {symbol.name}")
        self._symbols[symbol.name] = symbol
        return symbol

    def lookup(self, name: str) -> Symbol:
        try:
            return self._symbols[name]
        except KeyError as exc:
            raise PascalError(f"unknown identifier {name}") from exc

    def __contains__(self, name: str) -> bool:
        return name in self._symbols

    def __iter__(self):
        return iter(self._symbols.values())
