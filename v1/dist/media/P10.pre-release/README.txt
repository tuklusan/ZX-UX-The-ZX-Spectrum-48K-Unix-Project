ZX-UX Phase-10 development/pre-release distribution

Boot preview on a 48K Spectrum: LOAD ""

zx-ux-phase10-pre-release.tap and .tzx are deterministic boot-preview
images built from the exact PHASE-10-COMPLETE source lineage. They load
the canonical screen, the Phase-10-complete resident kernel, and a small
fixed preview payload, then enter the real boot gateway at 0xE003. The
preview displays the frozen 64-column issue/login screen and then idles.

phase10-native-lifecycle.tap and .tzx are exact byte copies of the
admitted P10.34 retained cassette media. They preserve the certified
MEX1/case-sensitive cassette roundtrip used by the native as/ld lifecycle
acceptance test. The workflow also reruns P10.34 at the packaging head and
requires the regenerated TAP/TZX hashes to equal those retained bytes.

This is post-certification packaging, not new P10 evidence and not the
Phase-12 final release. Phase-10 native assembler/linker behavior is
certified in staged target fixtures; this preview does not claim the live
resident login/session already composes those tools into final release
media. No Phase-11 work is included.
