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

# ZX-UX: UNIX FOR THE 48K SINCLAIR ZX SPECTRUM

ZX-UX is a Unix-like operating and development environment being designed specifically for the original, unexpanded 48K Sinclair ZX Spectrum. The target is one Z80A CPU, 48 KiB of RAM, cassette persistence, dense 64-column text, cooperative tasks, and a native development toolchain that can run within the machine's real hardware limits.

This is an active engineering project. The repository currently establishes the architecture, implementation plan, quality process, licensing rules, and CI workflow. It is not a claim that the complete Version 1 operating environment has already been implemented or released. Implementation source directories will be added as development proceeds.

Hardware behavior, emulator results, and implementation claims must remain clearly distinguished. ZX-UX is intended to work within the constraints of the original 48K machine rather than quietly borrowing features from later Spectrum models or expanded hardware.

## License

ZX-UX is distributed under the SANYALnet Labs Non-Commercial License in the root `LICENSE` file. Non-Commercial use is permitted. Commercial Use and use for AI/ML model training are prohibited unless separately authorized. Attribution is required as stated in the license.

## Development quality

Every proposed check-in must first pass three successive line-by-line scans of the exact disk-copy bytes with zero defects. Any change resets the clean-scan count. The license/header gate follows those scans.

An adversarial review then reports only `BLOCKER` and `MAJOR` findings. The programmer/author and reviewer handle that review dynamically immediately before check-in. The review is advisory rather than a veto: the programmer/author decides the disposition of each finding and may fix it, provide a clarification for re-review, or explicitly override it. Direct check-in to `main` is the normal project path; routine branch-and-merge staging is discouraged.

The repository also enforces a project-owner-defined prohibited-name gate. Those names are intentionally not reproduced in repository content; the automated checker rejects them case-insensitively in project paths and artifacts.
