<!-- Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs. -->
<!-- Proprietary rights reserved except as expressly licensed herein. -->
<!-- -->
<!-- ZX-UX Sinclair ZX Spectrum Unix -->
<!-- This file is governed by the SANYALnet Labs Non-Commercial License in the -->
<!-- root LICENSE file. Non-Commercial use is permitted; Commercial Use and use -->
<!-- for AI/ML model training are prohibited unless separately authorized. -->
<!-- -->
<!-- Attribution is required: "Based on original work by Supratim Sanyal of -->
<!-- SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination, -->
<!-- patent, trademark, and governing-law provisions. -->

# P11.03 preprocessor qualification matrix

The deterministic driver generates executable test bytes; this directory records
the owned matrix without introducing standalone C source fixtures.

Positive target-native coverage: case-sensitive object-like macro definition and
expansion; one-level cwd C/TXT include streaming in at most 64-byte reads;
compiler-resident c48.h; duplicate built-in-header idempotence; and equal stream
accounting for direct versus included bytes.

Negative target-native coverage: function-like macro; include depth two/cycle;
unknown system header; conditional preprocessing; token paste; stringification;
portable-basename/path violation; exact-case local include miss; replacement
overflow; output preservation; and any external lookup attempt for c48.h.

SDK/reference result: accepted/rejected behavior matches pinned SDK
compiler/c48/preprocessor.py at commit
84d144de2721cda5075c3a6610a422663b5e2f77. Target-native mapping is
EMIT_P11_CC_PREPROCESSOR in v1/src/tools/cc.asm, executed under FUSE by
phase11_step_03.py.
