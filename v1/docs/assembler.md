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


## P10.17 opcode coverage closure

The durable coverage map is `v1/tests/compiler/as-opcode-coverage`. It contains
exactly one row for every row in the frozen P10.10 opcode inventory and binds that
row to the qualified encoder step P10.11 through P10.16. P10.17 requires zero
missing inventory rows, zero duplicate rows, zero extra undocumented rows, and no
portable-baseline SLL or undocumented indexed-result aliases.

The native aggregate `EMIT_P10_AS_OPCODE_COVERAGE` expands all six qualified
encoder families. P10.17 validates the complete row mapping against the frozen
inventory, reassembles representative bytes with the certified SjASMPlus oracle,
and executes one target-side checkpoint from every encoder family. This closes
documented opcode/addressing coverage before OBJ1 writer and lifecycle work.

## REV17 kernel self-rebuild path

REV17 adds a narrow release-proof path without changing the historical Phase-10 opcode inventory or its admitted evidence. The canonical host kernel build deterministically produces an NSP1 semantic source projection from the canonical kernel listing/symbol source. NSP1 carries semantic operation/operand records and source data directives; it contains no preassembled kernel payload.

The target-native assembler facility `EMIT_R17_AS_NSP1_OBJ1` parses that semantic source on the ZX-UX target and emits a real no-symbol/no-relocation OBJ1 object. The native linker facility `EMIT_R17_LD_ABSOLUTE_OBJ1` consumes that OBJ1 and materializes its exact TEXT bytes only in caller-owned RAM below `0xE000`; it must not overwrite the executing resident kernel.

Release/pre-release acceptance requires the resulting 8192-byte image to match the host-built and independently TZX-reconstructed kernels at every byte offset, plus a separate genuine `source -> native as -> OBJ1 -> native ld -> executable -> run` proof and a controlled source mutation that must break kernel equality.
