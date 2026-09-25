ZX-UX Phase-10 fast-loader pre-release

Boot on a 48K Spectrum with: LOAD ""

This is the REV17/REV08 TZX-only pre-release path. The loader owns the
24x32 loading display; there is no SCREEN$ file and no release TAP.
The TZX embeds the freshly rebuilt exact 8192-byte kernel at E000-FFFF
and hands off at E003. The final row and exact startup BEEPER call
are runtime-verified before that handoff. Real-time Fuse acceptance
disables fastload, loader detection, acceleration and tape traps.

This Phase-10 pre-release intentionally contains no post-kernel M48O
system stream. It proves the fast-loader/kernel handoff only; it is not
the final Phase-12 system tape. No Phase-11 work is present or started.
