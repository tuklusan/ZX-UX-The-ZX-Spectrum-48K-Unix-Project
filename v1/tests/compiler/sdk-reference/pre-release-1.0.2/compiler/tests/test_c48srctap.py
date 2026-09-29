# ============================================================================
# Copyright (c) 2026 SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# restricted model training is prohibited unless separately authorized.
#
# Attribution required: SANYALnet Labs. See LICENSE for full terms,
# warranty disclaimer, termination, patent, trademark, and governing-law
# provisions.
# ============================================================================
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import c48srctap


class SourceTapeTests(unittest.TestCase):
    def make(
        self,
        root: Path,
        name: str,
        data: bytes = b"int main(void){return 0;}\n",
    ) -> Path:
        path = root / name
        path.write_bytes(data)
        return path

    def test_help_lists_required_interfaces(self):
        help_text = c48srctap.make_parser().format_help()
        self.assertIn("SOURCE", help_text)
        self.assertIn("--output", help_text)
        self.assertIn("--name", help_text)
        self.assertIn("--force", help_text)

    def test_help_states_source_policy(self):
        help_text = c48srctap.make_parser().format_help()
        self.assertIn("lowercase .c, .h, and .txt", help_text)
        self.assertIn("USERHOME", help_text)
        self.assertIn("examples:", help_text)

    def test_version_reports_sdk_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as cm:
                c48srctap.main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), "c48srctap 1.0.2")

    def test_crc_reference_vector(self):
        self.assertEqual(
            c48srctap.crc16_ccitt_false(b"123456789"),
            0x29B1,
        )

    def test_c_and_text_types_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = self.make(root, "main.c")
            h = self.make(root, "api.h", b"int putchar(int);\n")
            t = self.make(root, "note.txt", b"source tape\n")
            specs = c48srctap.collect_sources(
                [str(c), str(h), str(t)],
                None,
            )
            got = c48srctap.parse_tape(
                c48srctap.build_tape(specs)
            )
            self.assertEqual(
                [x.object_type for x in got],
                [5, 1, 1],
            )
            self.assertEqual(
                [x.name for x in got],
                ["main.c", "api.h", "note.txt"],
            )
            self.assertTrue(all(x.target == 5 for x in got))

    def test_513_byte_payload_is_two_chunks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(
                root,
                "large.c",
                b"x" * 512 + b"\n",
            )
            image = c48srctap.build_tape(
                c48srctap.collect_sources([str(source)], None)
            )
            lengths = []
            pos = 0
            while pos < len(image):
                length = int.from_bytes(
                    image[pos:pos + 2],
                    "little",
                )
                lengths.append(length)
                pos += 2 + length
            self.assertEqual(lengths, [34, 514, 3])

    def test_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(root, "main.c")
            specs = c48srctap.collect_sources(
                [str(source)],
                None,
            )
            self.assertEqual(
                c48srctap.build_tape(specs),
                c48srctap.build_tape(specs),
            )

    def test_name_override_handles_long_source_basename(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(root, "spriteanim.c")
            specs = c48srctap.collect_sources(
                [str(source)],
                [[str(source), "sprani.c"]],
            )
            self.assertEqual(specs[0].tape_name, "sprani.c")

    def test_long_name_without_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(root, "spriteanim.c")
            with self.assertRaises(c48srctap.SourceTapeError):
                c48srctap.collect_sources([str(source)], None)

    def test_unsupported_suffix_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(root, "bad.asm")
            with self.assertRaisesRegex(
                c48srctap.SourceTapeError,
                "only lowercase",
            ):
                c48srctap.collect_sources([str(source)], None)

    def test_uppercase_suffix_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(root, "bad.C")
            with self.assertRaises(c48srctap.SourceTapeError):
                c48srctap.collect_sources([str(source)], None)

    def test_mixed_valid_invalid_inputs_create_no_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            good = self.make(root, "good.c")
            bad = self.make(root, "bad.bin")
            out = root / "out.tap"
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    c48srctap.main(
                        [str(good), str(bad), "-o", str(out)]
                    )
            self.assertFalse(out.exists())

    def test_non_lf_text_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(root, "bad.c", b"int x;\r\n")
            with self.assertRaisesRegex(
                c48srctap.SourceTapeError,
                "LF line endings",
            ):
                c48srctap.collect_sources([str(source)], None)

    def test_non_ascii_text_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(
                root,
                "bad.c",
                b"int x; /* \xff */\n",
            )
            with self.assertRaisesRegex(
                c48srctap.SourceTapeError,
                "ASCII",
            ):
                c48srctap.collect_sources([str(source)], None)

    def test_output_suffix_must_be_lowercase_tap(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaisesRegex(
                c48srctap.SourceTapeError,
                "lowercase .tap",
            ):
                c48srctap.write_tape(
                    root / "x.TAP",
                    b"x",
                    force=False,
                )

    def test_existing_output_requires_force(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "x.tap"
            out.write_bytes(b"old")
            with self.assertRaisesRegex(
                c48srctap.SourceTapeError,
                "--force",
            ):
                c48srctap.write_tape(
                    out,
                    b"new",
                    force=False,
                )
            self.assertEqual(out.read_bytes(), b"old")
            c48srctap.write_tape(
                out,
                b"new",
                force=True,
            )
            self.assertEqual(out.read_bytes(), b"new")

    def test_tap_checksum_corruption_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(root, "main.c")
            image = bytearray(
                c48srctap.build_tape(
                    c48srctap.collect_sources(
                        [str(source)],
                        None,
                    )
                )
            )
            image[-1] ^= 1
            with self.assertRaisesRegex(
                c48srctap.SourceTapeError,
                "checksum",
            ):
                c48srctap.parse_tape(bytes(image))

    def test_payload_crc_corruption_is_detected_even_with_valid_tap_checksum(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(root, "main.c")
            image = bytearray(
                c48srctap.build_tape(
                    c48srctap.collect_sources(
                        [str(source)],
                        None,
                    )
                )
            )
            header_len = int.from_bytes(
                image[0:2],
                "little",
            )
            block = 2 + header_len
            data_len = int.from_bytes(
                image[block:block + 2],
                "little",
            )
            payload_start = block + 3
            image[payload_start] ^= 1
            checksum_index = block + 2 + data_len - 1
            framed = image[block + 2:checksum_index]
            checksum = 0
            for byte in framed:
                checksum ^= byte
            image[checksum_index] = checksum
            with self.assertRaisesRegex(
                c48srctap.SourceTapeError,
                "payload CRC",
            ):
                c48srctap.parse_tape(bytes(image))

    def test_zero_length_text_object_round_trips(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make(root, "empty.txt", b"")
            specs = c48srctap.collect_sources(
                [str(source)],
                None,
            )
            got = c48srctap.parse_tape(
                c48srctap.build_tape(specs)
            )
            self.assertEqual(got[0].payload, b"")


if __name__ == "__main__":
    unittest.main()
