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

# P11.45 H06 SDK Canary Provenance

The H06 compatibility canary is copied byte-for-byte from the mandatory
read-only C48 SDK repository and is not project-authored source.

- SDK commit: `9ca3c6d6b5dd4b6e2351c1800afbd47d1d77e411`
- commit tree: `1a35048f5250929fe1cc0832098799c653290883`
- `usr/src` tree: `f629dcc1d156b83bf08ed171b9273e3cbb621ad1`
- `usr/src/examples/hello.c`: Git blob
  `95fa0186bda3f7636774f5885988d78a13f6450b`, 703 bytes,
  SHA-256 `6f94a735f230dadf5928993f9a071f3f47e98b63d18230eef102f6ae7b63e4b2`
- `usr/src/examples/exapi.h`: Git blob
  `57b26d28e13d560c9903c0edc3732b36cd89b088`, 2056 bytes,
  SHA-256 `2fa0edc593832d3ab57bc105233f41fd81a02b1f3ea022cefc42da01a6084bb8`

The external SDK repository is read-only. The exact source and direct
declaration dependency above are retained here so qualification does not rely on
network access. Their original bytes are immutable H06 oracle material.
