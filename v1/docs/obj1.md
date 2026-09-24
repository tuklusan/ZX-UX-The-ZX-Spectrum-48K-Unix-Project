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

# OBJ1 relocatable object format

OBJ1 is the version-1 native assembler/linker object. Every multibyte field is
little-endian. Stored length is exact; trailing bytes are invalid.

## Header

The header is exactly 24 bytes: `OBJ1`, version 1, flags 0, header size 24,
`text_size`, `bss_size`, `symbol_count`, `relocation_count`,
`symbol_table_offset`, `relocation_table_offset`, body CRC and header CRC.
The fixed byte layout is: magic 0..3, version 4, flags 5, header_size 6..7,
text_size 8..9, bss_size 10..11, symbol_count 12..13, relocation_count 14..15,
symbol_table_offset 16..17, relocation_table_offset 18..19, body CRC 20..21,
and header CRC 22..23. `header_size` must be exactly 24.

The symbol table begins exactly at `24 + text_size`; the relocation table begins
exactly at `symbol_table_offset + symbol_count * 20`; total stored length is
`relocation_table_offset + relocation_count * 6`. Text+BSS and stored length are
each at most 32768. All arithmetic is widened before narrowing.

A nonzero relocation count with `text_size < 2` is E_FORMAT. No trailing bytes
are permitted. Count multiplication and every offset/length addition are
performed in widened arithmetic before any narrowing, so 16-bit wrap cannot
make a malformed object appear valid.

The body CRC covers every stored byte after the header: text/data, every symbol
record, and every relocation record. The header CRC covers the complete header
with its final two bytes treated as zero. Both use CRC-16/CCITT-FALSE with
polynomial `0x1021`, initial value `0xFFFF`, no reflection and final XOR zero.

## Symbol records

Each symbol record is exactly 20 bytes: `name[16]`, value u16, section u8 and
flags u8. A name has 1..15 visible bytes, then NUL and zero padding; an embedded
NUL followed by a nonzero byte is invalid. Assembly-visible names match
`[A-Za-z_.$][A-Za-z0-9_.$]*` and are case-sensitive. C48-generated external
names use the stricter C48 subset `[A-Za-z_][A-Za-z0-9_]*`, with the same
1..15 visible-byte limit. Names are unique within one module and are never
silently truncated.

Sections are UNDEF=0, TEXT=1, BSS=2 and ABS=3. The only flag is bit 0 GLOBAL.
UNDEF is always GLOBAL and has value zero. TEXT values are at most `text_size`;
BSS values are at most `bss_size`; ABS may contain any u16 value.

## Relocation records

Each relocation record is exactly six bytes: word offset u16, symbol index u16,
type u8 and reserved u8. Version 1 supports only ABS16 type 1 and reserved must be
zero. A nonzero relocation count requires text size at least two. Offsets are at
most `text_size-2`, strictly increasing and non-overlapping. Symbol indices are
in range. The text word at the relocation offset is a signed i16 addend; the
linker performs symbol value plus signed addend in widened arithmetic and rejects
results outside 0..65535.

The independent host decoder is `v1/tools-host/inspect-obj/inspect.py`.

## REV17 fixed-image release-proof use

REV17 does not define a new OBJ1 format. The native kernel self-rebuild uses the same OBJ1 header, CRC, and stored-length rules above. For the fixed kernel-image proof, native `as` emits a valid OBJ1 containing TEXT only, with zero BSS, symbols, and relocations; native `ld` validates and consumes that OBJ1 and writes its exact TEXT to non-executing RAM below `0xE000`.

This fixed-image mode is prospective release-proof machinery. It does not alter historical P10.34 evidence or the normal relocatable OBJ1/MEX1 lifecycle.
