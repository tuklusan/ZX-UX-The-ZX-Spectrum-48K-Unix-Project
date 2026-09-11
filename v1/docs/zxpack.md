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

# ZXP1 stored-object codec

The reference encoder identity is `zxp1-host-dp-1`. The decoder grammar is the
normative contract; host and target encoders may choose different legal parses.

- `00..3f`: literal length `token+1` (1..64), followed by that many bytes.
- `40..7f`: RLE length `(token&3f)+3` (3..66), followed by one byte.
- `80..ff`: back-reference length `(token&7f)+3` (3..130), followed by
  `distance-1`; distance is 1..256 and cannot exceed bytes already emitted.
- Back-references copy one byte at a time and may overlap.
- No terminator exists. A valid decode consumes the complete physical stream and
  emits exactly the declared logical length.
- Empty logical objects are RAW with an empty physical stream.
- PACKED representation is legal only when physical length is strictly smaller
  than logical length.

ZXP1 is storage compression only. It never represents process memory, stacks,
pipes, display RAM, kernel RAM, pinned runtime resources or a larger live address
space. Target streaming readers keep a 256-byte history plus bounded state; the
target greedy encoder uses one 512-byte last-occurrence workspace per pass.
