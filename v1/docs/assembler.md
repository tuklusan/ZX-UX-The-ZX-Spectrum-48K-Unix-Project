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

# ZX-UX native assembler

The version-1 native assembler is the target command `as`. Its portable opcode
coverage authority is the machine-readable inventory at
`v1/tests/compiler/as-opcode-inventory`.

P10.10 freezes documented Z80 mnemonics and addressing families required by ZX-UX
target source plus architecture-mandated ABI/test forms. The inventory contains a
positive encoding vector or SjASMPlus oracle for every row. Later Phase-10 encoder
steps must close every listed family before P10.17 may certify 100% coverage.

The portable baseline excludes undocumented opcodes. In particular, `SLL` and
undocumented indexed-result aliases are not accepted as portable syntax. Indexed
memory forms use signed displacements and later encoder steps enforce the exact
-128..127 boundary.

Inventory comparison is case-insensitive for mnemonic spelling only. ZX-UX symbols,
object names, and link-visible names remain case-sensitive.
