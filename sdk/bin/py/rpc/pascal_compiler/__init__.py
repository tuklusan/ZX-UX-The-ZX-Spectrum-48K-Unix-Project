"""Standalone native compiler entry points for the HiSoft Pascal port."""
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

from .codegen import Compiler, compile_file, make_tap
from .errors import PascalError, format_original_diagnostic
from .hisoft_literal import compile_minimal_literal
from .listing import format_sjasmplus
from .optimizer import OptimizationReport, OptimizerUnavailable, optimize_assembly
from .lexer import Token, lex
from .parser import Parser

__all__ = [
    "Compiler", "PascalError", "format_original_diagnostic", "Parser", "Token", "compile_file",
    "format_sjasmplus", "lex", "make_tap", "compile_minimal_literal",
    "OptimizationReport", "OptimizerUnavailable", "optimize_assembly",
]
