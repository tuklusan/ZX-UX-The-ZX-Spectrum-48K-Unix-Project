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
"""Adversarial hostile-input and C48 memory-boundary regression tests."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
SDK = COMPILER.parent
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_bytes, compile_file
from c48.errors import (
    C48Error,
    ResourceLimitError,
    RuntimeC48Error,
    UnsupportedFeatureError,
)
from c48.format import MAGIC, canonical_payload, decode, write
from c48.limits import C48B1_BYTES, SOURCE_LINE_BYTES, SOURCE_OBJECT_BYTES
from c48.screen import Font4x8, ZXScreen, bitmap_offset
from c48.vm import C48VM

FONT = Font4x8.load(COMPILER / "assets" / "font4x8-tasword.bin")
SEC_SRC = SDK / "dev" / "src"


def compile_security(name: str):
    return compile_file(SEC_SRC / f"{name}.c")


def screen_has(screen: ZXScreen, row: int, col: int, text: str) -> bool:
    """Verify text glyphs directly in the Spectrum bitmap bytes."""
    for index, code in enumerate(text.encode("ascii")):
        cell = col + index
        if cell >= 64:
            return False
        glyph = FONT.glyph(code)
        for ry, expected in enumerate(glyph):
            byte = screen.mem[bitmap_offset(cell * 4, row * 8 + ry)]
            actual = (byte >> 4) & 15 if (cell & 1) == 0 else byte & 15
            if actual != expected:
                return False
    return True


class CompilerHostileInputTests(unittest.TestCase):
    def assert_resource(self, source: str, label: str) -> None:
        with self.assertRaises(ResourceLimitError, msg=label):
            compile_bytes(
                source.encode("ascii"),
                source_name=f"{label}.c",
                base_dir=Path.cwd(),
            )

    def test_nested_parentheses_are_controlled_resource_limit(self):
        source = (
            "int main(void){return "
            + "(" * 100
            + "1"
            + ")" * 100
            + ";}\n"
        )
        self.assert_resource(source, "parens")

    def test_nested_blocks_are_controlled_resource_limit(self):
        source = (
            "int main(void){"
            + "{" * 600
            + "return 0;"
            + "}" * 600
            + "}\n"
        )
        self.assert_resource(source, "blocks")

    def test_extreme_pointer_depth_is_controlled_resource_limit(self):
        source = "int " + "*" * 1200 + "p;int main(void){return 0;}\n"
        self.assert_resource(source, "pointers")

    def test_macro_doubling_bomb_is_controlled_resource_limit(self):
        lines = ["#define A0 1"]
        for i in range(1, 13):
            lines.append(f"#define A{i} A{i - 1}+A{i - 1}")
        lines.append("int main(void){return A12;}")
        self.assert_resource("\n".join(lines) + "\n", "macro-bomb")

    def test_source_object_is_rejected_before_oversized_parse(self):
        data = b" " * (SOURCE_OBJECT_BYTES + 1)
        with self.assertRaises(ResourceLimitError):
            compile_bytes(data, source_name="huge.c", base_dir=Path.cwd())

    def test_single_physical_line_has_host_safety_ceiling(self):
        source = " " * (SOURCE_LINE_BYTES + 1)
        with self.assertRaises(ResourceLimitError):
            compile_bytes(
                source.encode("ascii"),
                source_name="longline.c",
                base_dir=Path.cwd(),
            )

    def test_cli_hostile_source_never_leaks_python_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "evil.c"
            path.write_text(
                "int main(void){return "
                + "(" * 100
                + "1"
                + ")" * 100
                + ";}\n",
                encoding="ascii",
            )
            cp = subprocess.run(
                [sys.executable, "-B", str(COMPILER / "c48.py"), str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("resource-limit", cp.stderr)
            self.assertNotIn("Traceback", cp.stderr)


class C48B1HostileInputTests(unittest.TestCase):
    def test_oversized_c48b1_is_rejected_before_json_parse(self):
        with self.assertRaisesRegex(RuntimeC48Error, "resource limit"):
            decode(b"X" * (C48B1_BYTES + 1))

    def test_excessive_json_nesting_is_rejected_before_json_load(self):
        payload = b"[" * 65 + b"0" + b"]" * 65
        digest = hashlib.sha256(payload).hexdigest().encode("ascii")
        data = MAGIC + digest + b"\n" + payload + b"\n"
        with self.assertRaisesRegex(RuntimeC48Error, "JSON nesting"):
            decode(data)

    def test_wrong_json_type_in_schema_is_controlled_rejection(self):
        program = compile_bytes(
            b"int main(void){return 0;}\n",
            source_name="schema.c",
            base_dir=Path.cwd(),
        )
        program["items"][0]["storage"] = []
        payload = canonical_payload(program)
        data = (
            MAGIC
            + hashlib.sha256(payload).hexdigest().encode("ascii")
            + b"\n"
            + payload
            + b"\n"
        )
        with self.assertRaisesRegex(RuntimeC48Error, "invalid C48B1"):
            decode(data)

    def test_function_definition_without_function_suffix_is_rejected(self):
        program = compile_bytes(
            b"int main(void){return 0;}\n",
            source_name="schema.c",
            base_dir=Path.cwd(),
        )
        program["items"][0]["declarator"]["suffix"] = None
        payload = canonical_payload(program)
        data = (
            MAGIC
            + hashlib.sha256(payload).hexdigest().encode("ascii")
            + b"\n"
            + payload
            + b"\n"
        )
        with self.assertRaisesRegex(RuntimeC48Error, "declare a function"):
            decode(data)

    def test_runtime_cli_oversized_file_has_no_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "huge.c48b"
            with path.open("wb") as stream:
                stream.truncate(C48B1_BYTES + 1)
            cp = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(COMPILER / "c48run.py"),
                    "--headless",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("resource limit", cp.stderr)
            self.assertNotIn("Traceback", cp.stderr)


class RuntimeBoundaryTests(unittest.TestCase):
    def assert_fixture_traps(
        self,
        name: str,
        message_row: int,
        message: str,
        expected_error: str,
        *,
        max_steps: int | None = None,
    ) -> None:
        program = compile_security(name)
        screen = ZXScreen(FONT)
        with self.assertRaisesRegex(RuntimeC48Error, expected_error):
            C48VM(
                program,
                screen,
                argv=[name],
                max_steps=max_steps,
            ).run()
        self.assertTrue(screen_has(screen, message_row, 0, message))

    def test_recoverable_security_dashboard_passes_on_screen(self):
        program = compile_security("secguard")
        screen = ZXScreen(FONT)
        self.assertEqual(C48VM(program, screen, argv=["secguard"]).run(), 0)
        self.assertTrue(
            screen_has(screen, 18, 0, "ALL RECOVERABLE GUARDS PASSED")
        )

    def test_one_past_write_is_trapped_after_visible_warning(self):
        self.assert_fixture_traps(
            "secoob",
            3,
            "MITIGATION: range guard must trap write",
            "pointer dereference outside live object",
        )

    def test_use_after_free_is_trapped_after_visible_warning(self):
        self.assert_fixture_traps(
            "secuaf",
            3,
            "MITIGATION: liveness guard must trap read",
            "live C48 object storage",
        )

    def test_interior_free_is_trapped_after_visible_warning(self):
        self.assert_fixture_traps(
            "secfree",
            3,
            "MITIGATION: exact-base guard must trap",
            "exact base pointer",
        )

    def test_double_free_is_trapped_after_visible_warning(self):
        self.assert_fixture_traps(
            "secdbl",
            3,
            "MITIGATION: stale allocation must trap",
            "pointer returned by malloc",
        )

    def test_infinite_loop_is_stopped_by_deterministic_step_budget(self):
        self.assert_fixture_traps(
            "secloop",
            3,
            "MITIGATION: --max-steps must stop VM",
            "execution step limit exceeded",
            max_steps=300,
        )

    def test_recursive_program_is_stopped_by_call_depth_budget(self):
        self.assert_fixture_traps(
            "secrecur",
            3,
            "MITIGATION: VM call-depth guard must trap",
            "function-call depth limit exceeded",
        )

    def test_raw_pointer_byte_forgery_has_no_provenance(self):
        self.assert_fixture_traps(
            "secforge",
            3,
            "MITIGATION: raw bytes have no provenance",
            "live C48 object storage",
        )

    def test_reserved_address_forgery_fixture_does_not_compile(self):
        with self.assertRaises(UnsupportedFeatureError):
            compile_security("seckern")

    def test_stale_pointer_does_not_revive_after_heap_reuse(self):
        source = (
            '#include "c48host.h"\n'
            "int main(void){char *a;char *b;a=malloc(2);"
            "if(a==0)return 1;*a=7;free(a);b=malloc(2);"
            "if(b==0)return 2;*b=9;return *a;}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "c48host.h").write_bytes(
                (SEC_SRC / "c48host.h").read_bytes()
            )
            source_path = root / "aba.c"
            source_path.write_text(source, encoding="ascii")
            program = compile_file(source_path)
            with self.assertRaisesRegex(RuntimeC48Error, "live C48 object"):
                C48VM(program, ZXScreen(FONT), argv=["aba"]).run()

    def test_stale_pointer_cannot_bypass_memset_after_reuse(self):
        source = (
            '#include "c48host.h"\n'
            "int main(void){char *a;char *b;a=malloc(2);"
            "if(a==0)return 1;free(a);b=malloc(2);"
            "if(b==0)return 2;memset(a,0,1);return 0;}\n"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "c48host.h").write_bytes(
                (SEC_SRC / "c48host.h").read_bytes()
            )
            source_path = root / "stale.c"
            source_path.write_text(source, encoding="ascii")
            program = compile_file(source_path)
            with self.assertRaisesRegex(RuntimeC48Error, "live allocation"):
                C48VM(program, ZXScreen(FONT), argv=["stale"]).run()

    def test_c48run_max_steps_cli_is_controlled(self):
        with tempfile.TemporaryDirectory() as td:
            binary = Path(td) / "secloop.c48b"
            write(binary, compile_security("secloop"))
            cp = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(COMPILER / "c48run.py"),
                    "--headless",
                    "--max-steps",
                    "300",
                    str(binary),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("execution step limit exceeded", cp.stderr)
            self.assertNotIn("Traceback", cp.stderr)


class PresentationContractTests(unittest.TestCase):
    def test_all_shipped_c48_source_lines_fit_64_columns(self):
        failures = []
        for path in sorted(SEC_SRC.glob("*")):
            if path.suffix not in {".c", ".h"}:
                continue
            for line_no, line in enumerate(
                path.read_text(encoding="ascii").splitlines(), 1
            ):
                if len(line) > 64:
                    failures.append(
                        f"{path.name}:{line_no}: {len(line)} columns"
                    )
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
