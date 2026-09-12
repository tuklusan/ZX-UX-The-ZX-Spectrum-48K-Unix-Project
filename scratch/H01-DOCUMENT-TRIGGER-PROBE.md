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

# H01 Documentation-Only Trigger Probe

This file is a deliberate documentation-only push probe for H01.

Its check-in changes only a Markdown artifact under `scratch/`. The expected result is that no push-triggered ZX-UX workflow run is created for that check-in.

The workflow-policy implementation under test is commit `d9a73937b7fcd3882c079f595c50b059b5e6ae67`.

The durable H01 closure record belongs in `scratch/WORKFLOW.md` after the repository run query confirms the expected zero-run result.
