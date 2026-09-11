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

# MEX1 executable format

MEX1 is the version-1 relocatable executable container. Every multibyte value is
unsigned little-endian unless a field explicitly says otherwise. The stored object
is exactly a 24-byte header, `image_size` image bytes, and
`relocation_count * 2` relocation bytes. Trailing bytes are invalid.

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | ASCII `MEX1` |
| 4 | 1 | version, exactly 1 |
| 5 | 1 | flags, exactly 0 |
| 6 | 2 | header size, exactly 24 |
| 8 | 2 | image size, at least 1 |
| 10 | 2 | BSS size |
| 12 | 2 | entry offset, less than image size |
| 14 | 2 | minimum FAST stack, 64..4096 |
| 16 | 2 | relocation count |
| 18 | 2 | relocation table offset, exactly 24 + image size |
| 20 | 2 | CRC-16/CCITT-FALSE of every byte after the header |
| 22 | 2 | header CRC with bytes 22..23 treated as zero |

`image_size + bss_size` is at most 32768 bytes. The exact stored length is
`relocation_table_offset + relocation_count * 2` and is also at most 32768.
All arithmetic is validated widened before a value is narrowed to 16 bits.

Each relocation is a little-endian image offset naming a two-byte ABS16 word.
Relocation offsets are strictly increasing and non-overlapping, so each offset after
the first is at least the previous offset plus two. Every offset is at most
`image_size - 2`. The stored word is an image-relative addend and may not exceed
`image_size + bss_size`. At load time the widened `word + actual_image_base` must
fit 0..65535 before the two relocated bytes are written.

CRC-16 uses CCITT-FALSE parameters: polynomial `0x1021`, initial value `0xFFFF`,
no reflection and final XOR zero.

The independent host decoder is `v1/tools-host/inspect-mex/inspect.py`. It is a
format oracle and never treats target-loader output as proof of its own validity.
