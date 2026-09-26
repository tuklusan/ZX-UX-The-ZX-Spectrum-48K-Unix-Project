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
class SourcePos:
    source: str
    line: int
    column: int

    def format(self) -> str:
        return f"{self.source}:{self.line}:{self.column}"


class C48Error(Exception):
    category = "error"
    exit_status = 1

    def __init__(self, message: str, pos: SourcePos | None = None):
        super().__init__(message)
        self.message = message
        self.pos = pos

    def __str__(self) -> str:
        prefix = f"{self.pos.format()}: " if self.pos else ""
        return f"{prefix}{self.category}: {self.message}"


class UsageC48Error(C48Error):
    category = "usage"


class LexicalError(C48Error):
    category = "lexical"


class UnsupportedFeatureError(C48Error):
    category = "unsupported"


class PreprocessorError(C48Error):
    category = "preprocessing"


class SyntaxC48Error(C48Error):
    category = "syntax"


class TypeC48Error(C48Error):
    category = "type"


class DeclarationError(C48Error):
    category = "declaration"


class ConstantExpressionError(C48Error):
    category = "constant-expression"


class LiteralRangeError(C48Error):
    category = "literal-range"


class ResourceLimitError(C48Error):
    category = "resource-limit"


class IOC48Error(C48Error):
    category = "io"


class RuntimeC48Error(C48Error):
    category = "runtime error"


class RuntimeExit(Exception):
    def __init__(self, status: int):
        super().__init__(status)
        self.status = status & 0xFF
