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

# ZX-UX Runner Cache Session

**Status:** HISTORICAL — retained for Phase-2 cache provenance only; not a current runtime-cache authority.

Stable Phase-2 runner cache session ID: `phase2-20260916-01`.

This ID names the reusable GitHub Actions cache lineage used while closing Phase 2.
GitHub-hosted runner virtual machines remain ephemeral; this file does not claim that
one physical or virtual runner disk survives between jobs. Workflows may reuse only
cacheable, reproducible inputs such as the pinned downloaded tool archives and the
project-local `tools/runtime/` tree, and they must verify the project-local runtime
before using a restored cache.

Source, build outputs, certification evidence, and Git state are never authoritative
because of this cache. Repository commits, retained workflow artifacts, and the
canonical evidence validators remain the durable source of truth.

If the cache lineage must be deliberately invalidated, change the session ID here
through the normal project quality procedure and update workflow expectations in the
same reviewed transaction.
