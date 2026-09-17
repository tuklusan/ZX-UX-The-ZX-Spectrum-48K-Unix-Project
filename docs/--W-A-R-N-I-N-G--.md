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

# STOP — CANONICAL FILES ARE IMMUTABLE

## READ THIS BEFORE EDITING ANY VERSIONED PROJECT AUTHORITY

**DO NOT EDIT A CHECKED-IN CANONICAL REVISION FILE.**

Not for a typo.  
Not for formatting.  
Not for whitespace.  
Not for line endings.  
Not for a comment.  
Not for a hash update.  
Not because the change is "obviously harmless."  
Not because a later implementation step would be easier if the document quietly changed underneath it.

Once a versioned architecture or implementation-plan revision has been checked in and used as project authority, its bytes are part of the project record. **Those bytes are frozen.**

Examples include, but are not limited to:

- `01-ZX-UX-ARCHITECTURE-REV*.md`
- `02-ZX-UX-IMPLEMENTATION-STEPS-REV*.md`
- any certification or admission record that freezes the identity of those files

A checked-in prospective revision is also frozen even before it becomes active authority. "Dormant" does **not** mean "safe to edit in place." Its identity may already be referenced by review, hashes, bridge logic, or later certification machinery.

---

# IF YOU THINK A CANONICAL FILE NEEDS CHANGING, STOP

Do **not** open the existing revision and "fix" it.

The correct procedure is:

1. **Leave the existing checked-in revision byte-for-byte unchanged.**
2. Create the **next revision** under a new filename.
3. Make the required changes only in that new revision.
4. Update the corresponding implementation/certification plan as a new revision when required.
5. Run the full required SoP scan sequence on the new final bytes.
6. Use the project workflow to admit the new revision at the correct transition point.
7. Preserve all earlier revisions forever as historical authority for the certifications that were performed against them.

A new requirement is a **new revision problem**, not an excuse to rewrite history.

---

# WHY THIS RULE IS ABSOLUTE

Changing even one byte in a canonical revision can invalidate or confuse:

- frozen SHA-256 identities;
- Git blob identities;
- certification evidence;
- step prerequisites;
- architecture-to-implementation traceability;
- CI/verifier assumptions;
- historical auditability;
- bridge/admission logic; and
- the ability to prove what requirements were actually in force when earlier work was certified.

A one-character edit can therefore create a repository state that *looks* reasonable while its evidence chain certifies something else.

That is worse than an obvious failure. It is a silent provenance break.

**Never trade a clean historical record for the convenience of an in-place edit.**

---

# CURRENT REVISION-EPOCH WARNING

The project presently has a deliberate authority transition model:

- REV12 / REV03 remain the active authority through completion of Phase 2.
- REV13 / REV04 may exist in the repository as dormant prospective authorities.
- Their presence alone does not activate them.
- The authority switch occurs only through the defined `R13.00` bridge after Phase 2 has fully closed and the bridge has passed its required admission and validation gates.
- After check-in, **REV12, REV03, REV13, and REV04 must all remain byte-for-byte unchanged.**

Do not "prepare" the transition by editing any of those files in place.

Do not "synchronize" old revisions with new wording.

Do not "clean up" historical files after the fact.

Do not update an old revision's embedded hash because a newer revision exists.

Historical authority must remain historical authority.

---

# IF AN ACCIDENTAL EDIT OCCURS

If a protected canonical file is modified accidentally:

1. **STOP. Do not commit it. Do not push it. Do not build new certification on top of it.**
2. Identify the last known-good canonical identity from Git/history and the project records.
3. Restore the file to the exact known-good bytes.
4. Verify its expected SHA-256 and, where recorded, Git blob identity.
5. Confirm the working tree contains no unintended canonical-document changes.
6. Only then resume normal work.

If the accidental change has already been committed or pushed, treat it as a provenance incident. Do not paper over it with another casual edit. Diagnose the repository state and repair it explicitly before continuing certification.

---

# RULE FOR CHATGPT / AUTOMATION / FUTURE YOU

When working on this repository:

> **NEVER modify an existing checked-in versioned canonical architecture or implementation-plan revision.**
>
> **If the specification must change, create a new revision and use the formal transition/admission process.**
>
> **When uncertain whether a file is frozen, assume it is frozen until proven otherwise.**

No assistant, script, editor, formatter, line-ending converter, merge tool, cleanup pass, or "helpful" automation is exempt from this rule.

If a task appears to require editing a frozen canonical revision, that is a signal to stop and design the next revision instead.

---

# THIS FILE IS A GUARDRAIL, NOT A NEW SPECIFICATION

This warning does not replace the architecture, implementation plan, development workflow, or certification rules. It exists to prevent accidental mutation of their frozen revision history.

If this warning ever appears to conflict with the active canonical project authorities, **stop and resolve the conflict before changing any canonical file.**

The safe default is simple:

# DO NOT EDIT THE FROZEN CANONICAL FILE.

Create the next revision.
