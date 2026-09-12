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

# ZX-UX Repository Scratchpad

**Status:** Tracked public coordination scratchpad; non-authoritative and non-certifying.

## Purpose

This directory provides durable repository-visible working notes and completion
tracking for project coordination that must survive ephemeral cloud workspaces and
must remain visible to future assistant project sessions.

It is deliberately named `scratch` so that working coordination material cannot be
mistaken for the architecture, implementation plan, certification evidence, or
release documentation.

## Authority and use rules

1. Files under `scratch/` are part of the public Git repository, but they do not
   amend architecture, implementation contracts, change requests, certification
   evidence, or release requirements merely by stating or checking an item here.
2. A checked item records coordination progress only. Canonical completion remains
   defined by the authoritative source document, required implementation, tests,
   evidence, project SoP, and repository gates.
3. When this scratchpad conflicts with an authoritative project document or verified
   repository state, the authoritative document or verified state wins and the
   scratchpad must be corrected.
4. Every session using this tracker must verify relevant repository state before
   relying on a status entry that could have changed.
5. Changes to this directory are normal repository changes and therefore use the
   project SoP, license-header gate, project-policy gate, adversarial review, and
   direct-main check-in discipline.
6. Do not place passwords, tokens, private credentials, private personal data, or
   other secrets in this public scratchpad.
7. Only `tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project` may be modified. All other
   GitHub repositories remain read-only.

## Contents

- `WORKFLOW.md` — durable checkbox tracker for the two pending change requests,
  housekeeping/infrastructure work, rebaseline work, and implementation resumption.

This directory may contain additional coordination notes later, but anything that
becomes normative must be deliberately promoted into the appropriate canonical
project document through the normal change-control and SoP process.
