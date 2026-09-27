#!/usr/bin/env python3
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX Sinclair ZX Spectrum Unix
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.

"""Mechanical REV17 Section-41.9 -> admitted Phase-11 owner map for P11.45."""

ROWS = (
    ("operators", ("P11.07", "P11.08")),
    ("scalar-array-initializers", ("P11.05", "P11.34")),
    ("int-float-casts", ("P11.18",)),
    ("signed-unsigned-comparison", ("P11.08", "P11.19")),
    ("pointers", ("P11.09",)),
    ("arrays-and-stride", ("P11.34",)),
    ("globals-statics-externs", ("P11.11",)),
    ("locals-and-frame-layout", ("P11.12",)),
    ("regcall-0-through-6-arguments", ("P11.13",)),
    ("five-byte-float-arguments", ("P11.14", "P11.15")),
    ("float-hidden-result-return", ("P11.16",)),
    ("recursion-within-stack-budget", ("P11.44",)),
    ("while-do-for-break-continue", ("P11.06", "P11.44")),
    ("logical-short-circuit", ("P11.07", "P11.44")),
    ("string-literals", ("P11.10",)),
    ("builtin-c48-h", ("P11.41",)),
    ("native-ld-runtime-resolution", ("P11.28", "P11.35")),
    ("system-calls", ("P11.22", "P11.23", "P11.37")),
    ("graphics", ("P11.25", "P11.36")),
    ("udg", ("P11.25", "P11.36")),
    ("pipe-io", ("P11.23", "P11.37")),
    ("compile-error-reporting", ("P11.42",)),
    ("symbol-table-overflow", ("P11.02", "P11.42")),
    ("source-too-large", ("P11.02", "P11.42")),
    ("output-memory-exhaustion", ("P11.28", "P11.42")),
    ("documented-opcode-enforcement", ("P11.30", "P11.31", "P11.32", "P11.33")),
    ("all-shipped-demos-native", ("P11.38",)),
    ("complete-pinned-sdk-golden-suite", ("P11.39",)),
    ("compiler-residency-20kib", ("P11.40",)),
    ("raw-packed-obj1-identity", ("P11.43",)),
    ("h06-pinned-sdk-native-canary", ("P11.45",)),
)

REVALIDATION_STEPS = ("P11.39", "P11.40", "P11.41", "P11.42", "P11.43", "P11.44")
