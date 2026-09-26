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
# Float5 Oracle Boundary - Pre-1.0 SDK

## Normative requirement

C48 uses the Sinclair ZX Spectrum five-byte numeric representation.  The language
specification's Section 94 requires a golden corpus to be compared against the
canonical Spectrum ROM conversion path, the native compiler/runtime, and the Windows
host implementation.  A host implementation may not certify itself solely against
IEEE floating point.

## What the pre-1.0 SDK implements and tests

`compiler/c48/float5.py` stores every C48 float as exactly five bytes.  Parsing from
decimal text uses `Decimal`/`Fraction` only as exact host-side construction tools;
stored C48 state is always quantized to the five-byte representation.

The SDK tests exact five-byte goldens for the required basic literal set and exercises
representative fractional and exponent forms, range failures, integer conversions,
comparisons, and operation-boundary quantization.  Core `+`, `-`, `*`, and `/` use
exact rational intermediates and quantize after each C48 operation.

## What is NOT certified in the pre-1.0 SDK

The pre-1.0 SDK does **not** claim complete byte-for-byte differential certification against
an executing canonical 48K ROM for every Float5 conversion/arithmetic path.  In
particular, ROM calculator rounding/canonicalization details at difficult boundaries
have not been proven exhaustively by an independent ROM execution harness.

The transcendental/runtime family (`sin`, `cos`, `tan`, `asin`, `acos`, `atan`,
`sqrt`, `exp`, `log`, `pow`) is therefore disabled in normal host execution.  A call
fails with a controlled runtime error unless `c48run --allow-approx-rom-math` is used.
That option uses Python host math and re-quantizes the result to Float5; it is provided
only for exploratory game development and is explicitly non-oracle/non-certified.

`fabs` is exact sign/magnitude handling and does not require host transcendental math.

## ROM asset policy

The SDK does not redistribute the ZX Spectrum ROM.  A standard 16K 48K ROM exists in
the user's separate emulator repository and can be used in a future differential-test
harness.  Until such an independent harness closes Section 94, this document is the
formal certification boundary.

## Release claim

Therefore the pre-1.0 SDK may be described as passing its documented host conformance envelope,
but not as completing the native C48 Section-94 three-way ROM/native/host float
certification.  This is a bounded open conformance item, not a hidden PASS.
