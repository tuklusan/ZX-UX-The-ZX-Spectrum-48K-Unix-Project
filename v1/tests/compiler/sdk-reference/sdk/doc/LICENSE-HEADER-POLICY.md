<!--
============================================================================
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
============================================================================
-->
# License Header Policy

`compiler/check_license_headers.py` is the fail-closed repository gate for source-level
license headings. It is modeled on the SANYALnet Labs source-header convention and runs
as part of `compiler/verify_release.py`.

## Header-bearing artifacts

The gate requires the approved project header near the beginning of every project-owned
file where an in-band text comment or heading is safe: Python, C48/C source, headers,
Markdown, ordinary text, YAML (including GitHub Actions workflows), Windows batch
files, the POSIX launchers, `.gitignore`, and `.gitattributes`.

The POSIX shebang remains physical line 1. Windows batch launchers keep `@echo off` at
line 1. The license heading follows immediately so those files retain their execution
semantics.

## Format-preserving exemptions

The following artifact classes are deliberately exempt because prepending a text header
would corrupt or semantically change the file:

- `LICENSE` - must remain the license text itself;
- `VERSION` - exact machine-readable version value;
- `MANIFEST.sha256` - exact machine-readable hash manifest;
- `*.json` - JSON has no comment syntax and is consumed as strict machine data;
- `*.bin` - binary F4X8/font payloads;
- `*.c48b` - canonical deterministic C48B1 executable format;
- `*.docx` - ZIP/container document format;
- `*.zip` - ZIP/TAP and other archive containers.

The exemption is fail-closed: a new artifact with an unknown suffix/name causes the gate
to fail until it is explicitly classified as header-safe or format-exempt.

## User-facing attribution

The root `LICENSE` also requires attribution to be reasonably discoverable from
user-facing interfaces. Both `c48` and `c48run` therefore expose `--about`, and the gate
checks that the CLI source contains the required attribution text.

Run the gate directly with:

```sh
python3 -B compiler/check_license_headers.py
```

or run the complete SDK release verifier:

```sh
python3 -B compiler/verify_release.py
```
