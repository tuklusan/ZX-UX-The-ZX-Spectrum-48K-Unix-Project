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
"""Defensive host-resource ceilings for untrusted C48 inputs.

These values are *host safety ceilings*, not newly invented C48 language
limits.  Permanent native compiler/workspace capacities remain owned by
ZX-UX P11.02/P11.42.  The one exception is SOURCE_OBJECT_BYTES, which mirrors
the already-frozen 32768-byte logical ZX-UX RAM object bound documented by the
C48 specification/architecture.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from .errors import ResourceLimitError, SourcePos

# Frozen architecture-bound per ordinary C/TXT source object.
SOURCE_OBJECT_BYTES = 32768

# Host-defense ceilings.  These are intentionally generous for a 48K target.
TRANSLATION_SOURCE_BYTES = 262144
PHYSICAL_LINES = 16384
PREPROCESSED_TOKENS = 65536
MACRO_DEFINITIONS = 256
MACRO_REPLACEMENT_TOKENS = 1024
AST_NODES = 32768
AST_DEPTH = 128
PARSER_EXPRESSION_DEPTH = 24
PARSER_STATEMENT_DEPTH = 64
PARSER_UNARY_DEPTH = 64
PARSER_ASSIGNMENT_DEPTH = 32
POINTER_DEPTH = 32
CONST_EVAL_DEPTH = 128
SOURCE_LINE_BYTES = 8192

# C48B1 host-file defensive ceilings.
C48B1_BYTES = 4 * 1024 * 1024
C48B1_JSON_DEPTH = 64
C48B1_CONTAINERS = 100000
C48B1_AST_NODES = 32768
C48B1_STRING_BYTES = 65535
C48B1_TYPE_DEPTH = 32

# VM recursion is bounded independently of the host Python recursion limit.
VM_CALL_DEPTH = 64


@dataclass
class ResourceBudget:
    """Shared, monotonic resource accounting for one translation unit."""

    source_bytes: int = 0
    physical_lines: int = 0
    preprocessed_tokens: int = 0
    macro_definitions: int = 0
    ast_nodes: int = 0
    _depths: dict[str, int] = field(default_factory=dict)

    @staticmethod
    def _raise(label: str, limit: int, pos: SourcePos | None) -> None:
        raise ResourceLimitError(
            f"host safety ceiling exceeded: {label} (limit {limit})",
            pos,
        )

    def _charge(
        self,
        attr: str,
        amount: int,
        limit: int,
        label: str,
        pos: SourcePos | None,
    ) -> None:
        value = getattr(self, attr) + amount
        if value > limit:
            self._raise(label, limit, pos)
        setattr(self, attr, value)

    @staticmethod
    def check_source_object_size(
        data_len: int, pos: SourcePos | None = None
    ) -> None:
        if data_len > SOURCE_OBJECT_BYTES:
            ResourceBudget._raise(
                "source object bytes", SOURCE_OBJECT_BYTES, pos
            )

    def add_source_object(
        self, data_len: int, pos: SourcePos | None = None
    ) -> None:
        self.check_source_object_size(data_len, pos)
        self._charge(
            "source_bytes",
            data_len,
            TRANSLATION_SOURCE_BYTES,
            "translation source bytes",
            pos,
        )

    def add_lines(self, count: int, pos: SourcePos | None = None) -> None:
        self._charge(
            "physical_lines", count, PHYSICAL_LINES, "physical lines", pos
        )

    def add_tokens(self, count: int, pos: SourcePos | None = None) -> None:
        self._charge(
            "preprocessed_tokens",
            count,
            PREPROCESSED_TOKENS,
            "preprocessed tokens",
            pos,
        )

    def add_macro_definition(self, pos: SourcePos | None = None) -> None:
        self._charge(
            "macro_definitions",
            1,
            MACRO_DEFINITIONS,
            "macro definitions",
            pos,
        )

    @staticmethod
    def check_macro_replacement(
        count: int, pos: SourcePos | None = None
    ) -> None:
        if count > MACRO_REPLACEMENT_TOKENS:
            ResourceBudget._raise(
                "expanded macro replacement tokens",
                MACRO_REPLACEMENT_TOKENS,
                pos,
            )

    @staticmethod
    def check_pointer_depth(
        depth: int, pos: SourcePos | None = None
    ) -> None:
        if depth > POINTER_DEPTH:
            ResourceBudget._raise("pointer indirection depth", POINTER_DEPTH, pos)

    @staticmethod
    def check_line_length(
        length: int, pos: SourcePos | None = None
    ) -> None:
        if length > SOURCE_LINE_BYTES:
            ResourceBudget._raise("physical source line bytes", SOURCE_LINE_BYTES, pos)

    @contextmanager
    def nested(
        self,
        key: str,
        limit: int,
        label: str,
        pos: SourcePos | None,
    ) -> Iterator[None]:
        depth = self._depths.get(key, 0) + 1
        if depth > limit:
            self._raise(label, limit, pos)
        self._depths[key] = depth
        try:
            yield
        finally:
            if depth == 1:
                self._depths.pop(key, None)
            else:
                self._depths[key] = depth - 1

    def check_ast(
        self, value: Any, pos: SourcePos | None = None
    ) -> None:
        """Iteratively bound AST width/depth before recursive semantic walks."""
        stack: list[tuple[Any, int]] = [(value, 1)]
        nodes = 0
        max_depth = 0
        while stack:
            current, depth = stack.pop()
            if isinstance(current, dict):
                max_depth = max(max_depth, depth)
                if isinstance(current.get("kind"), str):
                    nodes += 1
                    if self.ast_nodes + nodes > AST_NODES:
                        self._raise("AST nodes", AST_NODES, pos)
                for child in current.values():
                    if isinstance(child, (dict, list, tuple)):
                        stack.append((child, depth + 1))
            elif isinstance(current, (list, tuple)):
                max_depth = max(max_depth, depth)
                for child in current:
                    if isinstance(child, (dict, list, tuple)):
                        stack.append((child, depth + 1))
            if max_depth > AST_DEPTH:
                self._raise("AST structural depth", AST_DEPTH, pos)
        self.ast_nodes += nodes
