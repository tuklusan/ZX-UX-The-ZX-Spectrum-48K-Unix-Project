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

# M48O cassette object format

M48O version 1 is the native ZX-UX cassette object envelope. Every M48O header is
exactly 32 bytes. Every multibyte field is little-endian.

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | magic, bytes `M48O` |
| 4 | 1 | version, exactly 1 |
| 5 | 1 | object type |
| 6 | 1 | flags |
| 7 | 1 | target directory ID |
| 8 | 2 | physical payload/storage length |
| 10 | 2 | logical uncompressed length |
| 12 | 2 | codec ID |
| 14 | 2 | logical-payload CRC-16/CCITT-FALSE |
| 16 | 10 | exact case-sensitive base name |
| 26 | 2 | header CRC-16/CCITT-FALSE |
| 28 | 4 | reserved, all zero |

The header CRC processes all 32 header bytes with bytes 26 and 27 treated as
zero. CRC-16/CCITT-FALSE uses polynomial 0x1021, initial value 0xFFFF, no input
or output reflection, and final XOR 0x0000.

Object types 1 through 11 are TXT, BIN, OBJ, ASM, C, DAT, UDG, GFX, FNT, CFG,
and SYS. Type 0 and namespace-only DIR=12 and DEV=13 are invalid M48O payload
types. Version-1 flags use only bit 0, M48O_PACKED; bits 1 through 7 are zero.

Target IDs are ROOT=0, BIN=1, DEV=2, ETC=3, HOME=4, USERHOME=5, TMP=6, and
SYSTEM=7. Placement is exact: BIN accepts only BIN; ETC accepts TXT or CFG;
USERHOME and TMP accept types 1 through 10; SYSTEM accepts only FNT or SYS and
only for internal bootstrap loading. ROOT, DEV, and HOME are invalid persistence
targets. Public save/load never targets SYSTEM.

RAW objects have flags=0, codec=0, physical length equal to logical length, and
may be zero length. PACKED objects have bit 0 set, codec=1 (ZXP1), logical length
1..32768, and physical length strictly smaller than logical length. Both lengths
are at most 32768 bytes. Zero-length objects are always RAW.

The name field contains 1..10 portable name bytes: A-Z, a-z, 0-9, underscore,
hyphen, or dot. The exact names `.` and `..` are forbidden. A shorter name is
NUL terminated and every following byte in the ten-byte field is zero. A full
ten-byte non-NUL name is legal. An embedded NUL followed by any nonzero byte is
invalid.

USERHOME is symbolic persistence metadata. On load it resolves to the current
session `/home/<user>`; the stored name and logical payload do not change when
the boot username changes.
