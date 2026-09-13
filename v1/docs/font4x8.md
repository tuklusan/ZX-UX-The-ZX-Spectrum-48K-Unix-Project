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

# F4X8 Phase-1 font resource contract

The Phase-1 tty64 font resource is an exact 392-byte F4X8 payload. Bytes 0 through 7 are the header: ASCII `F4X8` (`46 34 58 38`), version `01`, first target code `20`, glyph count `60` (96 glyphs), and flags `00`. Bytes 8 through 391 are exactly 384 packed glyph bytes.

Each target glyph occupies four packed bytes and expands to eight 4-bit scan rows. In each packed byte the high nibble is the earlier/even scan row and the low nibble is the following/odd scan row. Within each nibble bit 3 is the leftmost pixel and bit 0 is the rightmost pixel. Therefore target codes `20` through `7F` map in order to 96 glyphs and 768 decoded scan rows.

`zx48_tty64_install_font` accepts only the exact length and header above. After validation it requests the full 392 bytes with `ALLOC_FAST_REQUIRED`, copies the complete resource into that allocation, pins all 392 bytes, and retains both the resource base and the payload pointer as private kernel state. Allocation failure is returned as `E_NOMEM`; there is no COLD fallback. The install contract is used before PID 1 is made runnable. The physical address is not part of the syscall ABI and is not exposed to applications.

During Phase 1 the resource remains the explicitly non-final Phase-0 fixture. P1.21 validates structure and target behavior only; it does not claim a byte-identity SHA-256 contract. P12.05 alone owns promotion to, and byte identity of, the final release F4X8 payload.
