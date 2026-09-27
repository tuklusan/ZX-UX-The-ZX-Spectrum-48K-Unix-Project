ZX-UX Phase-11 fast-loader pre-release

Boot on a 48K Spectrum with: LOAD ""

This is the REV17/REV08 TZX-only Phase-11 pre-release transport image.
It embeds the exact current 8192-byte kernel at E000-FFFF and hands off at
E003 using the reviewed fast loader. Phase-11 native compiler acceptance is
re-run against this exact source head and hash-bound in pre-release.json.

This pre-release intentionally does NOT append the final Phase-12 system/demo
M48O stream. It is not the final integrated system tape and does not claim
Phase-12 release acceptance. No Phase-12 source, workflow, evidence, media, or
activation is created.
