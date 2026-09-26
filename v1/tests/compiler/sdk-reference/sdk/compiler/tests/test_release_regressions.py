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
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
SDK = COMPILER.parent
import sys
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_bytes, compile_file
from c48.errors import RuntimeC48Error
from c48.gui import footer_text, is_break_key, key_event_bytes
from c48.screen import Font4x8, ZXScreen
from c48.vm import C48VM

FONT_PATH = COMPILER / "assets" / "font4x8-tasword.bin"
HOST_HEADER = SDK / "dev" / "src" / "c48host.h"


def run_text(src: str, *, argv=None) -> int:
    p = compile_bytes(src.encode("ascii"), source_name="release.c", base_dir=Path.cwd())
    screen = ZXScreen(Font4x8.load(FONT_PATH))
    return C48VM(p, screen, argv=argv or ["release"]).run()


def run_host(src: str) -> int:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "c48host.h").write_bytes(HOST_HEADER.read_bytes())
        p = d / "r.c"
        p.write_text(src, encoding="ascii")
        program = compile_file(p)
        screen = ZXScreen(Font4x8.load(FONT_PATH))
        return C48VM(program, screen, argv=["r"]).run()


class ReleaseRuntimeRegressions(unittest.TestCase):
    def test_recursion(self):
        src = "int f(int n){if(n<2)return 1;return n*f(n-1);}\nint main(void){if(f(5)==120)return 0;return 1;}\n"
        self.assertEqual(run_text(src), 0)

    def test_nested_shadowing_and_parameter_scope(self):
        src = "int f(int x){int y;y=x;{int x;x=7;y=y+x;}return y;}\nint main(void){if(f(3)==10)return 0;return 1;}\n"
        self.assertEqual(run_text(src), 0)

    def test_break_continue_for_while_do(self):
        src = (
            "int main(void){int i;int s;i=0;s=0;"
            "while(i<8){i++;if(i==2)continue;if(i==6)break;s=s+i;}"
            "if(s!=13)return 1;"
            "for(i=0;i<5;i++){if(i==1)continue;s=s+1;}"
            "if(s!=17)return 2;"
            "i=0;do{i++;if(i<3)continue;s=s+2;}while(i<4);"
            "if(s!=21)return 3;return 0;}\n"
        )
        self.assertEqual(run_text(src), 0)

    def test_six_argument_call_and_capture(self):
        src = (
            "int f(int a,int b,int c,int d,int e,int f){return a+2*b+3*c+4*d+5*e+6*f;}"
            "int main(void){int i;i=1;if(f(i++,i++,i++,i++,i++,i++)==91)return 0;return 1;}\n"
        )
        self.assertEqual(run_text(src), 0)

    def test_pointer_return_and_array_of_pointers_runtime(self):
        src = (
            "int a;int b;int *pick(int n){if(n)return &b;return &a;}"
            "int main(void){int *p[2];a=11;b=22;p[0]=pick(0);p[1]=pick(1);"
            "if(*p[0]==11&&*p[1]==22)return 0;return 1;}\n"
        )
        self.assertEqual(run_text(src), 0)

    def test_global_pointer_initializer(self):
        src = "int a;int *p=&a;int main(void){a=73;if(*p==73)return 0;return 1;}\n"
        self.assertEqual(run_text(src), 0)

    def test_extern_address_initializer_may_precede_definition(self):
        src = "extern int a;int *p=&a;int a;int main(void){a=91;if(*p==91)return 0;return 1;}\n"
        self.assertEqual(run_text(src), 0)

    def test_string_literals_are_read_only(self):
        src = 'int main(void){char *p;p="abc";p[0]=\'z\';return 0;}\n'
        program = compile_bytes(src.encode("ascii"), source_name="ro.c", base_dir=Path.cwd())
        screen = ZXScreen(Font4x8.load(FONT_PATH))
        with self.assertRaises(RuntimeC48Error):
            C48VM(program, screen).run()

    def test_memmove_overlap(self):
        src = (
            '#include "c48host.h"\n'
            'int main(void){char a[7]="abcdef";memmove(a+1,a,5);'
            "if(a[0]=='a'&&a[1]=='a'&&a[2]=='b'&&a[3]=='c'&&a[4]=='d'&&a[5]=='e')return 0;return 1;}\n"
        )
        self.assertEqual(run_host(src), 0)

    def test_malloc_free_reuses_space_without_aliasing_live_object(self):
        src = (
            '#include "c48host.h"\n'
            'int main(void){char *a;char *b;char *c;a=malloc(8);b=malloc(8);'
            'if(a==0||b==0)return 1;free(a);c=malloc(8);if(c==0)return 2;'
            'if(c==b)return 3;free(b);free(c);return 0;}\n'
        )
        self.assertEqual(run_host(src), 0)

    def test_function_static_linkage_runtime(self):
        src = "static int f(int x){return x+1;}int main(void){if(f(41)==42)return 0;return 1;}\n"
        self.assertEqual(run_text(src), 0)

    def test_gui_control_key_mapping_prefers_keysym(self):
        self.assertEqual(key_event_bytes("Return", "\r"), (10,))
        self.assertEqual(key_event_bytes("BackSpace", "\x08"), (8,))
        self.assertEqual(key_event_bytes("Escape", "\x1b"), (27,))
        self.assertEqual(key_event_bytes("a", "a"), (97,))
        self.assertEqual(key_event_bytes("Left", ""), ())
        self.assertEqual(key_event_bytes("eacute", "é"), ())
        self.assertTrue(is_break_key("space", 0x0001))
        self.assertTrue(is_break_key("space", 0x0005))
        self.assertFalse(is_break_key("space", 0x0000))
        self.assertFalse(is_break_key("Space", 0x0001))
        self.assertFalse(is_break_key("a", 0x0001))
        self.assertEqual(footer_text(False), "Shift+Space = BREAK")
        self.assertEqual(footer_text(True), "Program ended - Shift+Space to close")

    def test_gui_numeric_keypad_sequence(self):
        events = (
            ("KP_1", ""),
            ("KP_3", ""),
            ("Return", "\r"),
        )
        actual = tuple(
            byte
            for keysym, text in events
            for byte in key_event_bytes(keysym, text)
        )
        self.assertEqual(actual, (ord("1"), ord("3"), 10))
        self.assertEqual(key_event_bytes("KP_Enter", ""), (10,))
        self.assertEqual(key_event_bytes("KP_0", ""), (ord("0"),))
        self.assertEqual(key_event_bytes("KP_9", ""), (ord("9"),))

    def test_cli_rejects_same_input_output_without_modifying_source(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); src=d/"same.c"; original=b"int main(void){return 0;}\n"; src.write_bytes(original)
            cp=subprocess.run([sys.executable,str(SDK/"compiler/c48.py"),str(src),"-o",str(src)],capture_output=True)
            self.assertEqual(cp.returncode,1)
            self.assertIn(b"usage:",cp.stderr)
            self.assertEqual(src.read_bytes(),original)

    def test_native_default_heap_budget_and_override(self):
        src = ('#include "c48host.h"\n'
               'int main(void){char *a;char *b;a=malloc(1024);if(a==0)return 1;'
               'b=malloc(2);if(b!=0)return 2;free(a);b=malloc(2);if(b==0)return 3;return 0;}\n')
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'c48host.h').write_bytes(HOST_HEADER.read_bytes());p=d/'h.c';p.write_text(src,encoding='ascii')
            program=compile_file(p);screen=ZXScreen(Font4x8.load(FONT_PATH))
            self.assertEqual(C48VM(program,screen).run(),0)
            screen2=ZXScreen(Font4x8.load(FONT_PATH))
            self.assertEqual(C48VM(program,screen2,heap_size=0).run(),1)
            with self.assertRaises(RuntimeC48Error):C48VM(program,screen2,heap_size=1)
            with self.assertRaises(RuntimeC48Error):C48VM(program,screen2,heap_size=8194)

    def test_c48b1_roundtrip_accepts_block_scope_declarations(self):
        from c48.format import encode, decode
        program = compile_bytes(b"int main(void){int x;unsigned char a[2];x=7;a[0]=3;a[1]=4;if(x+a[0]+a[1]==14)return 0;return 1;}\n", source_name="local.c")
        restored = decode(encode(program))
        screen = ZXScreen(Font4x8.load(FONT_PATH))
        self.assertEqual(C48VM(restored, screen).run(), 0)

    def test_all_noncanonical_ascii_controls_rejected_before_line_splitting(self):
        from c48.errors import LexicalError
        from c48.compiler import compile_bytes
        prefix=b"int x;\nint y;"
        for bad in (0x00,0x0b,0x0c,0x1c,0x1d,0x1e,0x1f,0x7f):
            with self.subTest(byte=bad):
                with self.assertRaises(LexicalError) as cm:
                    compile_bytes(prefix+bytes([bad])+b"int z;\n",source_name="ctl.c")
                self.assertEqual(cm.exception.pos.line,2)
                self.assertEqual(cm.exception.pos.column,7)

    def test_c48run_defaults_to_tasword_font_and_accepts_override(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            program=SDK/'dev/bin/hello.c48b'
            default_scr=d/'default.scr'
            alt_scr=d/'alt.scr'
            custom=d/'custom.bin'
            data=bytearray((COMPILER/'assets/font4x8-tasword.bin').read_bytes())
            # Change one row-pair of the printable 'H' glyph while preserving F4X8 structure.
            glyph=ord('h')-0x20
            data[8+glyph*4] ^= 0xF0
            custom.write_bytes(data)
            base=[sys.executable,str(COMPILER/'c48run.py'),'--headless']
            a=subprocess.run(base+['--dump-screen',str(default_scr),str(program)],capture_output=True,text=True)
            self.assertEqual(a.returncode,0,a.stderr)
            b=subprocess.run(base+['--font',str(custom),'--dump-screen',str(alt_scr),str(program)],capture_output=True,text=True)
            self.assertEqual(b.returncode,0,b.stderr)
            self.assertNotEqual(default_scr.read_bytes(),alt_scr.read_bytes())

    def test_c48run_invalid_font_path_fails_cleanly(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            missing=Path(td)/'missing-font.bin'
            r=subprocess.run([sys.executable,str(COMPILER/'c48run.py'),'--headless','--font',str(missing),str(SDK/'dev/bin/hello.c48b')],capture_output=True,text=True)
            self.assertEqual(r.returncode,1)
            self.assertIn('c48run:',r.stderr)
            self.assertNotIn('Traceback',r.stderr)


if __name__ == "__main__":
    unittest.main()
