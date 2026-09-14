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

# ZX-UX Combined Rebaseline and Re-certification Runbook

**Status:** CLOSED — DONE. Historical coordination record only; do not resume work from this file.

**Closed:** 2026-09-14.

**Purpose:** Preserve an unambiguous durable closure marker for the completed combined
controlled source rebaseline and Phase-0/Phase-1 re-certification that preceded Phase 2.
This file no longer authorizes implementation or certification work.

## 1. Closure basis

The runbook reached its own `DONE` state after the Section-10 closure audit was proved
against canonical repository and workflow state.

Closure anchors:

- final Phase-1 certified source: `e84dfc93da08963404b569010464b2d78f1b3fba`;
- Phase-1 evidence activation / closed baseline `main`:
  `b05b8cc74836b038cc4dd0a61a7e607ab025a13a`;
- canonical REV12 SHA-256:
  `a90d523f62a95e8cba6af0312b596a2d5f6bc1aa2ef92f39bb391509b7c15e1b`;
- exact `/etc/issue` SHA-256:
  `8d57d17f25ef895909a56a3195e29b8f9b83ff2cc31b2537a23d1d02429e3d31`;
- successful Phase-1 certification run: `34867080245`, with activation on attempt 2;
- successful final Quality/CI closure run: `34868343182` against
  `b05b8cc74836b038cc4dd0a61a7e607ab025a13a`.

At closure, Phase 0 and Phase 1 both had active durable evidence bound to the same
REV12 architecture identity. Phase-0 and Phase-1 active validators and their negative
suites passed. Project-policy, license-header, pinned-environment, exact E0, and final
project CI gates passed against the activated repository state.

The P1.22 retained PNG/SCR proof was also closed: the exact captured SCR was 6912
bytes, the retained PNG and SCR were bound to one captured frame, and the mandatory
independent automated SCR and PNG-raster visual inspections passed against the
canonical `font4x8-zxux.bin` atlas.

No Phase-2 implementation path was started as part of this closed rebaseline.

## 2. Historical preservation

The complete pre-closure working-plan bytes remain preserved in Git history at
`b05b8cc74836b038cc4dd0a61a7e607ab025a13a`, where this path had Git blob
`aa082bce5f69af76ac4a77590acd7383de6c1c93`.

Use that historical version only for audit/reconstruction. Its C0-C4 restart state
machine, blocker procedures, and stop-before-Phase-2 instructions are superseded by
this closure marker and must not be treated as the current project goal.

## 3. Successor goal

Forward implementation resumes under:

`scratch/ZX-UX-PHASE2-PROCESSES-LOADER-IMPLEMENTATION-CERTIFICATION-RUNBOOK-REV01.md`

The canonical architecture, implementation plan, `AGENTS.md`, and
`docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md` remain authoritative over every scratch
coordination file.
