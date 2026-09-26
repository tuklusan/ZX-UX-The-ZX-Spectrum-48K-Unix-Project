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


def pos_dict(pos) -> dict[str, Any]:
    return {"source": pos.source, "line": pos.line, "column": pos.column}


def node(kind: str, pos, **kw) -> dict[str, Any]:
    d: dict[str, Any] = {"kind": kind, "pos": pos_dict(pos)}
    d.update(kw)
    return d
