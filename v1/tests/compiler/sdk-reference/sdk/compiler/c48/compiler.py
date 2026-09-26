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

from pathlib import Path
from typing import Any

from .limits import ResourceBudget
from .parser import Parser
from .preprocessor import Preprocessor
from .semantics import SemanticAnalyzer


def compile_bytes(data: bytes, *, source_name: str = "<source>", base_dir: Path | None = None,
                  builtin_header: str = "") -> dict[str, Any]:
    budget = ResourceBudget()
    pp = Preprocessor(builtin_header=builtin_header, budget=budget)
    tokens = pp.preprocess_bytes(
        data,
        source_name=source_name,
        base_dir=base_dir or Path.cwd(),
        include_depth=0,
    )
    tree = Parser(tokens, budget=budget).parse()
    budget.check_ast(tree, tokens[0].pos if tokens else None)
    return SemanticAnalyzer(budget=budget).analyze(tree)


def compile_file(path: Path, *, builtin_header: str = "") -> dict[str, Any]:
    path = path.resolve()
    budget = ResourceBudget()
    pp = Preprocessor(builtin_header=builtin_header, budget=budget)
    tokens = pp.preprocess_file(path)
    tree = Parser(tokens, budget=budget).parse()
    budget.check_ast(tree, tokens[0].pos if tokens else None)
    return SemanticAnalyzer(budget=budget).analyze(tree)
