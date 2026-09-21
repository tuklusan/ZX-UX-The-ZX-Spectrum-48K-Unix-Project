# ZX-UX Phase-5 cassette media

These files preserve the cassette media exercised by the certified Phase-5 implementation.

They are certification/test media, not a final ZX-UX release image. P5.15 explicitly
certified the fixture as non-final.

| File | SHA-256 | Provenance |
| --- | --- | --- |
| `phase5-fixture.tap` | `81620fbb57ad352c3df590b08835df68bf61d72627aa0ae9ea82918c24c7d80d` | P5.15/P5.18 deterministic Phase-5 fixture |
| `phase5-fixture.tzx` | `ea73912acb1be244c0c344112aaf778799b69d85bcf0d054998e3aba1e3cbbf0` | P5.15 fixture converted by the pinned FUSE `tapeconv` tool |
| `phase5-fixture-roundtrip.tap` | `81620fbb57ad352c3df590b08835df68bf61d72627aa0ae9ea82918c24c7d80d` | P5.15 TZX-to-TAP roundtrip; byte-identical to the fixture TAP |
| `p516-roundtrip.tap` | `40e9aebbb55b0b0a810fa9cd67adbec876351a63a9086b692d9377163ee5a324` | P5.16 RAW TXT/BIN/UDG roundtrip cassette |

The admitted Phase-5 certification evidence remains unchanged. These files were
materialized after certification from the already-certified implementation and
verified against the SHA-256 identities recorded by P5.15/P5.16 where those
identities exist.
