"""Optimization of generated SJASMPlus source using bundled upeepz80."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.

from dataclasses import dataclass
import re


class OptimizerUnavailable(RuntimeError):
    """Raised when a distribution is missing its bundled optimizer."""


_SJASMPLUS_HEX = re.compile(r"(?<![\w])\$([0-9A-Fa-f]+)")


def _dependency():
    try:
        from .upeepz80 import PeepholeOptimizer
        from .upeepz80.z80 import (
            BARRIERS,
            DATA,
            TRANSPARENT,
            data_size,
            effect,
            split_operands,
            strip_comment,
        )
    except ImportError as exc:
        raise OptimizerUnavailable(
            "--optimize requires the bundled upeepz80 optimizer; "
            "the distribution is incomplete"
        ) from exc
    return (
        PeepholeOptimizer,
        BARRIERS,
        DATA,
        TRANSPARENT,
        data_size,
        effect,
        split_operands,
        strip_comment,
    )


def _source_size(assembly: str) -> int:
    """Return the bytes represented by generated/optimized assembler text."""
    _, BARRIERS, DATA, TRANSPARENT, data_size, effect, split_operands, strip_comment = _dependency()
    total = 0
    for line_number, line in enumerate(assembly.splitlines(), 1):
        text = strip_comment(line).strip()
        if not text or text.endswith(":"):
            continue
        parts = text.split(None, 1)
        opcode = parts[0].lower()
        operands = parts[1] if len(parts) == 2 else ""
        if opcode in BARRIERS or opcode in TRANSPARENT:
            continue
        operands_for_size = _SJASMPLUS_HEX.sub(r"0x\1", operands)
        if opcode in DATA:
            size = data_size(opcode, split_operands(operands_for_size))
        else:
            size = effect(opcode, operands_for_size).size
        if size is None:
            raise ValueError(f"cannot determine assembler size at line {line_number}: {line}")
        total += size
    return total


@dataclass(frozen=True)
class OptimizationReport:
    """Filtered assembler and deterministic size/statistics details."""

    assembly: str
    optimized_assembly: str
    pre_optimization_size: int
    post_optimization_size: int
    statistics: dict[str, int]

    @property
    def size_delta(self) -> int:
        return self.post_optimization_size - self.pre_optimization_size

    @property
    def size_reduction(self) -> int:
        return self.pre_optimization_size - self.post_optimization_size

    @property
    def optimization_count(self) -> int:
        return sum(self.statistics.values())

    def as_dict(self) -> dict[str, object]:
        return {
            "pre_optimization_size": self.pre_optimization_size,
            "post_optimization_size": self.post_optimization_size,
            "size_delta": self.size_delta,
            "size_reduction": self.size_reduction,
            "optimization_count": self.optimization_count,
            "statistics": dict(self.statistics),
        }


def optimize_assembly(assembly: str) -> OptimizationReport:
    """Run upeepz80 over generated SJASMPlus-compatible source."""
    PeepholeOptimizer, *_ = _dependency()
    optimizer = PeepholeOptimizer()
    optimized = optimizer.optimize(assembly)
    statistics = dict(sorted(optimizer.stats.items()))
    return OptimizationReport(
        assembly=assembly,
        optimized_assembly=optimized,
        pre_optimization_size=_source_size(assembly),
        post_optimization_size=_source_size(optimized),
        statistics=statistics,
    )
