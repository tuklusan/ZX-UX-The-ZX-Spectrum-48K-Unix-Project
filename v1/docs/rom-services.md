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

# ZX-UX ROM service contracts

Revision-11 ROM calls are centralized in `v1/src/kernel/rom_services.asm`.
The alternate register bank is OS-private and volatile. No process descriptor,
scheduler record, allocator record, or other persistent kernel state may exist
only in AF'/BC'/DE'/HL'.

## Interrupt/alternate-bank classifier

| wrapper | class | alternate-bank behavior | interrupt policy | task switch |
| --- | --- | --- | --- | --- |
| `zx48_rom_restore_iy` | scaffold | does-not-use | safe outside ROM; no ROM call | forbidden inside wrapper |

A wrapper is **fast-safe** only when its frozen contract says
`does-not-use` or `uses-but-preserves` and its interrupt/workspace policy is
compatible with the current context. `clobbers` and `unknown` are always unsafe
for the fast path. Unsafe wrappers require the serialized safe fallback. The
Phase-P0.06 ISR performs no ROM calls and uses balanced `EX AF,AF'` / `EXX`
pairs only as OS-private scratch switching.
