# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
SDK = COMPILER.parent
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_bytes, compile_file
from c48.format import decode, encode
from c48.screen import Font4x8, ZXScreen, bitmap_offset
from c48.vm import C48VM

FONT = Font4x8.load(COMPILER / "assets" / "font4x8-tasword.bin")


def roundtrip_run(source: bytes) -> int:
    program = compile_bytes(source, source_name="game-reg.c")
    restored = decode(encode(program))
    screen = ZXScreen(FONT)
    return C48VM(restored, screen, argv=["game-reg"]).run()


def cell_glyph(screen: ZXScreen, row: int, col: int) -> tuple[int, ...]:
    rows = []
    x0 = col * 4
    y0 = row * 8
    high = (col & 1) == 0
    for ry in range(8):
        byte = screen.mem[bitmap_offset(x0, y0 + ry)]
        if high:
            rows.append((byte >> 4) & 15)
        else:
            rows.append(byte & 15)
    return tuple(rows)


class GameReleaseRegressions(unittest.TestCase):
    def test_c48b1_string_array_initializer_roundtrip(self):
        source = (
            b'char a[4]="abc";'
            b"int main(void){"
            b"if(a[0]=='a'&&a[1]=='b'&&a[2]=='c'&&a[3]==0)"
            b"return 0;return 1;}\n"
        )
        self.assertEqual(roundtrip_run(source), 0)

    def test_c48b1_string_pointer_initializer_roundtrip(self):
        source = (
            b'char *p="abc";'
            b"int main(void){"
            b"if(p[0]=='a'&&p[1]=='b'&&p[2]=='c'&&p[3]==0)"
            b"return 0;return 1;}\n"
        )
        self.assertEqual(roundtrip_run(source), 0)

    def test_release_column_gate_recurses_into_game_sources(self):
        import verify_release

        original_sdk = verify_release.SDK
        try:
            with tempfile.TemporaryDirectory() as td:
                sdk = Path(td)
                games = sdk / "dev" / "src" / "games"
                games.mkdir(parents=True)
                nested = games / "nested.c"
                nested.write_text("x" * 64 + "\n", encoding="ascii")
                verify_release.SDK = sdk
                verify_release.check_c48_source_columns()
                nested.write_text("x" * 65 + "\n", encoding="ascii")
                with self.assertRaises(SystemExit) as caught:
                    verify_release.check_c48_source_columns()
                self.assertIn("games/nested.c:1=65", str(caught.exception))
        finally:
            verify_release.SDK = original_sdk

    def test_arithmetic_echo_and_backspace(self):
        program = compile_file(SDK / "dev" / "src" / "games" / "arith.c")
        screen = ZXScreen(FONT)
        one = FONT.glyph(ord("1"))
        three = FONT.glyph(ord("3"))
        blank = FONT.glyph(ord(" "))

        class Input:
            def __init__(self):
                self.calls = 0

            def __call__(self):
                call = self.calls
                self.calls += 1
                if call == 0:
                    return ord("1")
                if call == 1:
                    self_outer.assertEqual(cell_glyph(screen, 7, 22), one)
                    return 8
                if call == 2:
                    self_outer.assertEqual(cell_glyph(screen, 7, 22), blank)
                    return ord("1")
                if call == 3:
                    self_outer.assertEqual(cell_glyph(screen, 7, 22), one)
                    return ord("3")
                if call == 4:
                    self_outer.assertEqual(cell_glyph(screen, 7, 22), one)
                    self_outer.assertEqual(cell_glyph(screen, 7, 23), three)
                    return 10
                if call == 5:
                    return ord("q")
                raise AssertionError("unexpected arithmetic input request")

        self_outer = self
        provider = Input()
        vm = C48VM(
            program,
            screen,
            argv=["arith"],
            input_provider=provider,
            max_steps=500000,
        )
        self.assertEqual(vm.run(), 0)
        self.assertEqual(provider.calls, 6)
        turns = vm.global_lvalues["ar_turns"]
        right = vm.global_lvalues["ar_right"]
        self.assertEqual(
            vm.mem.load_integer(turns.pointer.address, turns.ctype), 1
        )
        self.assertEqual(
            vm.mem.load_integer(right.pointer.address, right.ctype), 1
        )


if __name__ == "__main__":
    unittest.main()
