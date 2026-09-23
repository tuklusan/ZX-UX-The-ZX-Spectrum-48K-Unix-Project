ZX-UX Phase-9 development/pre-release boot tape

Real 48K Spectrum loading command: LOAD ""

The auto-start BASIC loader loads the ZX-UX loading screen, the Phase-9
resident kernel at 0xE000, and a small fixed-address preview payload at
0x6100, then transfers control through the real ZX-UX boot gateway at
0xE003. After normal kernel initialization, the preview payload displays
the frozen Phase-9 F4X8 font into the live 64-column console, clears the
ROM loader messages, displays /etc/issue and exact "login: " prompt, then
enters the normal PID0 idle scheduler.

This is intentionally a Phase-9 development preview, not the Phase-12 final
release tape. Phase-9 shell/vi behavior is qualified in staged target
fixtures, but the admitted resident boot image does not yet compose those
stages into a live interactive login/session. This tape therefore stops at
the login prompt instead of pretending later integration already exists.

The workflows/ directory preserves the final workflow set used to create
and validate this demonstration for reference by later phase previews.

The post-Phase-9 housekeeping source repairs the malformed TIME1 set-handler
label so the resident kernel now assembles directly without a preview-only
source rewrite. The PHASE-9-COMPLETE tag and admitted Phase-9 evidence remain
unchanged historical records.
