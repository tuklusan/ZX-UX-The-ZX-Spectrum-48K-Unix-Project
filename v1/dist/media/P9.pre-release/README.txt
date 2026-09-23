ZX-UX Phase-9 development/pre-release boot tape

Real 48K Spectrum loading command: LOAD ""

The auto-start BASIC loader loads the ZX-UX loading screen, the Phase-9
resident kernel at 0xE000, and a small fixed-address preview payload at
0x6000, then transfers control through the real ZX-UX boot gateway at
0xE003. After normal kernel initialization, the preview payload displays
the frozen Phase-9 /etc/issue text and exact "login: " prompt, then enters
the normal PID0 idle scheduler.

This is intentionally a Phase-9 development preview, not the Phase-12 final
release tape. Phase-9 shell/vi behavior is qualified in staged target
fixtures, but the admitted resident boot image does not yet compose those
stages into a live interactive login/session. This tape therefore stops at
the login prompt instead of pretending later integration already exists.

The Phase-9 checkpoint contains an internal time-set table symbol typo which
prevents a fresh resident-kernel assembly. This build resolves that one table
entry to the exact already-qualified handler offset during assembly only; the
checked-in Phase-9 source and certification evidence remain unchanged.
