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

import hashlib
import os
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
from c48.errors import C48Error, RuntimeC48Error
from c48.float5 import Float5, Float5Error
from c48.format import decode, encode
from c48.lexer import SUPPORTED_KEYWORDS, UNSUPPORTED_KEYWORDS
from c48.screen import BITMAP_SIZE, Font4x8, ZXScreen, bitmap_offset
from c48.vm import C48VM

FONT_PATH = COMPILER / "assets" / "font4x8-tasword.bin"


def compile_text(src: str, *, name: str = "test.c", base: Path | None = None, builtin_header: str = ""):
    return compile_bytes(src.encode("ascii"), source_name=name, base_dir=base or Path.cwd(), builtin_header=builtin_header)


def run_text(src: str, *, argv=None, approx=False, base: Path | None = None):
    p = compile_text(src, base=base)
    screen = ZXScreen(Font4x8.load(FONT_PATH))
    vm = C48VM(p, screen, argv=argv or ["test"], approximate_rom_math=approx)
    return vm.run(), screen


def assert_rejected(tc: unittest.TestCase, src: str, category: str | None = None):
    with tc.assertRaises(C48Error) as cm:
        compile_text(src)
    if category is not None:
        tc.assertEqual(cm.exception.category, category)


def condition_program(expr: str, pre: str = "") -> str:
    return f"int main(void){{ {pre} if ({expr}) return 0; return 1; }}\n"


class LexicalCorpus(unittest.TestCase):
    def test_required_identifiers(self):
        for ident in ("abc", "abc123", "_abc", "ABC", "abc_DEF"):
            with self.subTest(ident=ident):
                compile_text(f"int {ident};\n")

    def test_required_integer_literals(self):
        for lit in ("0", "32767", "32768", "65535", "65535u", "077", "0xff", "0XABCDU"):
            with self.subTest(lit=lit):
                compile_text(f"int main(void){{ if ({lit}) return 0; return 0; }}\n")

    def test_required_char_literals(self):
        for lit in (r"'A'", r"'\n'", r"'\0'", r"'\xff'"):
            with self.subTest(lit=lit):
                compile_text(f"int main(void){{ return {lit}; }}\n")

    def test_required_strings(self):
        compile_text('char *p="";\nchar *q="a" "b";\n')

    def test_required_float_literals(self):
        for lit in ("0.0", "1.", ".5", "1e3", "1E-3", "1.25f"):
            with self.subTest(lit=lit):
                compile_text(f"float x={lit};\n")

    def test_supported_operator_program(self):
        src = r'''
int f(int a){ return a; }
int main(void){
 int a=3,b=2,c=0; int v[2]={1,2}; int *p;
 p=v; c=a+b; c=a-b; c=a*b; c=a/b; c=a%b; a++; --b;
 c=a<<1; c=a>>1; c=a<b; c=a<=b; c=a>b; c=a>=b; c=a==b; c=a!=b;
 c=a&b; c=a|b; c=a^b; c=~a; c=a&&b; c=a||b; c=!a;
 c=*p; p=&v[0]; c=v[1]; c=f(c); c=+c; c=-c; a=b=c;
 return 0;
}
'''
        compile_text(src)

    def test_required_bad_literals_and_tokens(self):
        bad = [
            "65536", "0x10000", "08", "1L", "1UL", "1.0L", "0x1.0p0",
            "''", "'AB'", r"'\123'", r"'\x4'", r"'\q'", "123abc", "1.0foo", "1e3e4", "1.0e2e3",
        ]
        for token in bad:
            with self.subTest(token=token):
                assert_rejected(self, f"int main(void){{ return {token}; }}\n")

    def test_repeated_exponent_is_lexical_error(self):
        for token in ("1e3e4", "1.0e2e3"):
            with self.subTest(token=token):
                with self.assertRaises(C48Error) as cm:
                    compile_text(f"float x={token};\n")
                self.assertEqual(cm.exception.category, "lexical")

    def test_long_identifier(self):
        assert_rejected(self, "int identifier_longer_than_15_visible_characters;\n", "lexical")

    def test_unsupported_operators(self):
        snippets = ["a+=1", "a-=1", "a?1:2", "p->x", "f(1,...)"]
        for e in snippets:
            with self.subTest(expr=e):
                assert_rejected(self, f"int main(void){{ int a=0; int *p; {e}; return 0; }}\n", "unsupported")

    def test_every_reserved_keyword_rejected(self):
        for kw in sorted(UNSUPPORTED_KEYWORDS):
            with self.subTest(keyword=kw):
                assert_rejected(self, f"int main(void){{ {kw}; return 0; }}\n", "unsupported")

    def test_unsupported_directives(self):
        for d in ("undef", "if", "ifdef", "ifndef", "elif", "else", "endif", "error", "line", "pragma"):
            with self.subTest(directive=d):
                assert_rejected(self, f"#{d} X\nint x;\n", "preprocessing")

    def test_unsupported_type_spellings(self):
        bad = ["signed int x;", "unsigned x;", "short int x;", "unsigned short int x;",
               "unsigned char int x;", "long x;", "double x;"]
        for src in bad:
            with self.subTest(src=src): assert_rejected(self, src)

    def test_other_required_negative_forms(self):
        for src in (
            "int x=0b10;\n", "int x=1'000;\n", "int main(void){return sizeof(int[3]);}\n",
            "int main(void){int x=1; (void)x; return 0;}\n",
            "int *p; int main(void){ return (int)p; }\n",
        ):
            with self.subTest(src=src): assert_rejected(self, src)


class IntegerSemantics(unittest.TestCase):
    def assert_true(self, expr: str, pre: str = ""):
        status, _ = run_text(condition_program(expr, pre))
        self.assertEqual(status, 0, expr)

    def test_8bit_assignment_wrap(self):
        self.assert_true("c==0", "unsigned char c=255; c=c+1;")

    def test_signed_wrap_boundaries(self):
        self.assert_true("32767+1 == (int)0x8000u")
        self.assert_true("((-32767-1)-1)==32767")
        self.assert_true("65535u+1u==0u")

    def test_int_min_division_special_case(self):
        self.assert_true("((int)0x8000u)/-1 == (int)0x8000u")
        self.assert_true("((int)0x8000u)%-1 == 0")

    def test_signed_division_remainder(self):
        for expr in ("-7/3==-2", "-7%3==-1", "7/-3==-2", "7%-3==1"):
            with self.subTest(expr=expr): self.assert_true(expr)

    def test_divide_by_zero_exits_one(self):
        status, _ = run_text("int main(void){ int a=1,b=0; return a/b; }\n")
        self.assertEqual(status, 1)

    def test_shift_count_mask_8_bit(self):
        for count, expected in ((0,1),(7,128),(8,1),(15,128),(16,1),(31,128),(255,128)):
            with self.subTest(count=count):
                self.assert_true(f"(c<<{count})=={expected}", "unsigned char c=1;")

    def test_shift_count_mask_16_bit(self):
        for count, expected in ((0,"1"),(7,"128"),(8,"256"),(15,"32768u"),(16,"1"),(31,"32768u"),(255,"32768u")):
            with self.subTest(count=count):
                self.assert_true(f"(u<<{count})=={expected}", "unsigned int u=1u;")

    def test_signed_and_unsigned_right_shift(self):
        self.assert_true("(s>>1)==-1", "int s=-2;")
        self.assert_true("(u>>1)==32767", "unsigned int u=65535u;")

    def test_signed_unsigned_comparisons(self):
        self.assert_true("((int)0x8000u)<0")
        self.assert_true("0x8000u>32767")
        self.assert_true("!(-1 < 1u)")

    def test_bare_minus_32768_is_unsigned(self):
        self.assert_true("-32768 == 32768u")
        self.assert_true("(int)0x8000u < 0")


class EvaluationOrder(unittest.TestCase):
    def test_function_arguments_left_to_right(self):
        src='''
int logv=0;
int a(void){logv=logv*10+1;return 1;}
int b(void){logv=logv*10+2;return 2;}
int c(void){logv=logv*10+3;return 3;}
int f(int x,int y,int z){return x+y+z;}
int main(void){f(a(),b(),c());if(logv==123)return 0;return 1;}
'''
        self.assertEqual(run_text(src)[0],0)

    def test_binary_left_before_right(self):
        src='''
int logv=0;
int l(void){logv=logv*10+1;return 1;}
int r(void){logv=logv*10+2;return 2;}
int main(void){int x;x=l()+r();if(logv==12)return 0;return 1;}
'''
        self.assertEqual(run_text(src)[0],0)

    def test_argument_value_capture(self):
        src='''int f(int a,int b){return a*10+b;} int main(void){int i=4; if(f(i++,i)==45)return 0;return 1;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_assignment_destination_then_rhs_i_postinc(self):
        src='''int main(void){int i=4;i=i++;if(i==4)return 0;return 1;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_short_circuit(self):
        src='''int main(void){int i=0;if(0 && i++)return 1;if(i)return 2;if(1 || i++){}if(i)return 3;return 0;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_sizeof_suppresses_side_effect(self):
        src='''int main(void){int i=0;unsigned int n;n=sizeof(i++);if(i==0 && n==2)return 0;return 1;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_sizeof_null_deref_no_access(self):
        src='''int main(void){int *p=0;if(sizeof *p==2)return 0;return 1;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_sizeof_array_index_suppresses_increment(self):
        src='''int main(void){int a[2]={1,2};int i=0;if(sizeof(a[i++])==2 && i==0)return 0;return 1;}'''
        self.assertEqual(run_text(src)[0],0)


class PointerCorpus(unittest.TestCase):
    def test_pointer_scaling_char_int_float(self):
        src='''
int main(void){char a[3]={1,2,3};int b[3]={1,2,3};float c[3]={1.,2.,3.};char *pa;int *pb;float *pc;
pa=a;pb=b;pc=c;if(pa+1-pa!=1)return 1;if(pb+1-pb!=1)return 2;if(pc+1-pc!=1)return 3;return 0;}
'''
        self.assertEqual(run_text(src)[0],0)

    def test_integer_plus_pointer_and_minus(self):
        src='''int main(void){int a[3]={7,8,9};int *p;p=a;p=1+p;if(*p!=8)return 1;p=p-1;if(*p!=7)return 2;return 0;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_pointer_inc_dec(self):
        src='''int main(void){int a[2]={4,5};int *p;p=a;p++;if(*p!=5)return 1;--p;if(*p!=4)return 2;return 0;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_pointer_subtraction_signs(self):
        src='''int main(void){int a[3]={0,0,0};int *p,*q;p=a;q=a+2;if(q-p!=2)return 1;if(p-p!=0)return 2;if(p-q!=-2)return 3;return 0;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_null_equality(self):
        self.assertEqual(run_text('int main(void){int *p=0;if(p==0 && 0==p)return 0;return 1;}')[0],0)

    def test_void_pointer_conversion(self):
        src='''int main(void){int a[1]={7};int *p;void *v;p=a;v=p;p=v;if(*p==7)return 0;return 1;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_array_decay_and_sizeof_no_decay(self):
        src='''int main(void){int a[3]={1,2,3};int *p;p=a;if(*p==1 && sizeof(a)==6)return 0;return 1;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_address_of_array_rejected(self):
        assert_rejected(self,'int main(void){int a[2]; &a; return 0;}','type')

    def test_base_index_and_index_base(self):
        self.assertEqual(run_text('int main(void){int a[2]={3,4};if(a[1]==4)return 0;return 1;}')[0],0)
        assert_rejected(self,'int main(void){int a[2]={3,4};return 1[a];}','type')

    def test_argv_double_index(self):
        src='''int main(int argc,char **argv){if(argc>1 && argv[1][0]=='Z')return 0;return 1;}'''
        p=compile_text(src);screen=ZXScreen(Font4x8.load(FONT_PATH));vm=C48VM(p,screen,argv=['p','Zed'])
        self.assertEqual(vm.run(),0)

    def test_void_pointer_arithmetic_and_deref_rejected(self):
        assert_rejected(self,'int main(void){void *p=0;p=p+1;return 0;}','type')
        assert_rejected(self,'int main(void){void *p=0;return *p;}','type')

    def test_pointer_cast_rejected(self):
        assert_rejected(self,'int main(void){int *p=0;return (int)p;}','unsupported')

    def test_function_pointer_rejected(self):
        assert_rejected(self,'int f(void){return 0;} int main(void){int (*p)(void);return 0;}')

    def test_multidimensional_array_rejected(self):
        assert_rejected(self,'int a[2][2];')


class DeclarationCorpus(unittest.TestCase):
    def test_scalars_storage_and_multiple_declarators(self):
        compile_text('static int a; extern int b; int b; int c,d; static int f(void){return 1;} int *g(int *p){return p;}')

    def test_exact_function_type_distinctions(self):
        bad=[
            'int f(char x); int f(unsigned char x);',
            'int f(short x); int f(int x);',
            'int f(unsigned short x); int f(unsigned int x);',
            'int f(int *x); int f(void *x);',
        ]
        for src in bad:
            with self.subTest(src=src):assert_rejected(self,src,'declaration')

    def test_declarator_binding(self):
        p=compile_text('char *a[8]; char **b[8]; char *f(void); char **g(void);')
        sy=p['symbols']
        self.assertEqual(sy['a']['type']['kind'],'array');self.assertEqual(sy['a']['type']['base']['kind'],'pointer')
        self.assertEqual(sy['b']['type']['base']['base']['kind'],'pointer')
        self.assertEqual(sy['f']['type']['ret']['kind'],'pointer')
        self.assertEqual(sy['g']['type']['ret']['base']['kind'],'pointer')

    def test_repeated_compatible_externs_and_definition_both_orders(self):
        compile_text('extern int x; int x; extern int x;')
        compile_text('int x; extern int x; extern int x;')

    def test_duplicate_definition(self):
        assert_rejected(self,'int x; int x;','declaration')

    def test_static_external_conflict(self):
        assert_rejected(self,'static int x; extern int x;','declaration')
        assert_rejected(self,'extern int x; static int x;','declaration')

    def test_prototype_definition_mismatch(self):
        assert_rejected(self,'int f(short x); int f(int x){return x;}','declaration')

    def test_undeclared_call(self):
        assert_rejected(self,'int main(void){return f(1);}','declaration')

    def test_block_scope_function_declaration(self):
        assert_rejected(self,'int main(void){int f(void);return 0;}','unsupported')

    def test_old_style_empty_parameter_list(self):
        assert_rejected(self,'int f();','unsupported')

    def test_main_forms(self):
        compile_text('int main(void){return 0;}')
        compile_text('int main(int argc,char **argv){return argc;}')
        compile_text('int main(void); int main(void){return 0;}')
        compile_text('int x;')  # module with no main is legal to compile

    def test_invalid_main(self):
        for src in ('static int main(void);','static int main(void){return 0;}','char main(void);','int main(int x);','int main;'):
            with self.subTest(src=src):assert_rejected(self,src,'declaration')

    def test_parameter_scope(self):
        assert_rejected(self,'int f(int x){int x=1;return x;}','declaration')
        compile_text('int f(int x){{int x=1;return x;}}')


class InitializerCorpus(unittest.TestCase):
    def test_scalar_initializers(self):
        src="int a=-1;unsigned int b=65535u;char c='A';float f=1.25;int *p=0;char *s=\"hi\";"
        compile_text(src)

    def test_address_of_global(self):
        p=compile_text('int x;int *p=&x;int main(void){if(p==&x)return 0;return 1;}')
        screen=ZXScreen(Font4x8.load(FONT_PATH));self.assertEqual(C48VM(p,screen).run(),0)

    def test_fixed_inferred_and_partial_arrays(self):
        src='''int main(void){int a[3]={1,2,3};int b[]={4,5};int c[4]={9};if(a[2]==3 && b[1]==5 && c[1]==0 && c[3]==0)return 0;return 1;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_trailing_initializer_comma(self):
        self.assertEqual(run_text('int main(void){int a[2]={1,2,};if(a[1]==2)return 0;return 1;}')[0],0)

    def test_character_array_from_string(self):
        self.assertEqual(run_text('int main(void){char a[4]="abc";if(a[3]==0)return 0;return 1;}')[0],0)
        self.assertEqual(run_text('int main(void){char a[]="abc";if(sizeof(a)==4)return 0;return 1;}')[0],0)

    def test_string_too_long_rejected(self):
        assert_rejected(self,'char a[3]="abc";','type')

    def test_designated_nested_rejected(self):
        assert_rejected(self,'int a[2]={[0]=1,2};','unsupported')
        assert_rejected(self,'int a[2]={{1},2};','unsupported')

    def test_runtime_initializer_rejected(self):
        assert_rejected(self,'int f(void){return 1;} int main(void){int x=f();return x;}','constant-expression')


class PreprocessorCorpus(unittest.TestCase):
    def test_constant_macro_kinds_and_parentheses(self):
        src='''
#define N 10
#define H .5
#define C 'A'
#define S "ok"
#define M (1 << 4)
int a=N;float b=H;int c=C;char *s=S;int m=M;
'''
        compile_text(src)

    def test_backward_macro_expansion(self):
        compile_text('#define A 2\n#define B (A+3)\nint x=B;\n')

    def test_forward_and_self_macro_rejected(self):
        assert_rejected(self,'#define A B\n#define B 1\nint x=A;','preprocessing')
        assert_rejected(self,'#define A A\nint x=A;','preprocessing')

    def test_invalid_fragment_macro_rejected(self):
        assert_rejected(self,'#define A 1 +\nint x=1;','preprocessing')
        assert_rejected(self,'#define A int x\nint y;','preprocessing')

    def test_identical_and_different_redefinition(self):
        compile_text('#define A 1\n#define A 1\nint x=A;')
        assert_rejected(self,'#define A 1\n#define A 2\nint x=A;','preprocessing')

    def test_no_expansion_in_literal_comment_char(self):
        src='''#define X 65
char *s="X";int c='X';/* X */
int main(void){if(s[0]=='X' && c=='X')return 0;return 1;}'''
        self.assertEqual(run_text(src)[0],0)

    def test_definition_visibility(self):
        assert_rejected(self,'int x=A;\n#define A 1\n','declaration')
        compile_text('#define A 1\nint x=A;\n')

    def test_local_include_macro_visibility_both_directions(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            (d/'inc.h').write_text('int x=A;\n#define B 7\n',encoding='ascii')
            (d/'main.c').write_text('#define A 3\n#include "inc.h"\nint y=B;\n',encoding='ascii')
            compile_file(d/'main.c')

    def test_nested_include_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'b.h').write_text('int b;\n');(d/'a.h').write_text('#include "b.h"\n');(d/'m.c').write_text('#include "a.h"\n')
            with self.assertRaises(C48Error) as cm:compile_file(d/'m.c')
            self.assertEqual(cm.exception.category,'preprocessing')

    def test_include_exact_name_and_missing_are_io(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'Inc.h').write_text('int x;\n');(d/'m.c').write_text('#include "inc.h"\n')
            with self.assertRaises(C48Error) as cm:compile_file(d/'m.c')
            self.assertEqual(cm.exception.category,'io')

    def test_include_name_validation(self):
        for name in ('../x.h','123456789.h','.','..','bad/name.h'):
            with self.subTest(name=name):assert_rejected(self,f'#include "{name}"\n','preprocessing')

    def test_builtin_header_repeat_idempotent(self):
        compile_text('#include <c48.h>\n#include <c48.h>\nint x;\n',builtin_header='int h(void);\n')

    def test_unknown_header_and_trailing_tokens(self):
        assert_rejected(self,'#include <stdio.h>\n','preprocessing')
        assert_rejected(self,'#include <c48.h> junk\n','preprocessing')

    def test_macro_include_operand_not_expanded(self):
        assert_rejected(self,'#define H "x.h"\n#include H\n','preprocessing')

    def test_multiline_comment_and_directive_comment_rules(self):
        compile_text('int /* a\n b */ x;\n')
        assert_rejected(self,'#define A 1 /* x\n */\nint x=A;','preprocessing')


class RemainingRequiredCorpus(unittest.TestCase):
    def test_function_object_entity_conflicts_both_orders(self):
        assert_rejected(self, 'int f(void); int f;\n', 'declaration')
        assert_rejected(self, 'int x; int x(void);\n', 'declaration')

    def test_parenthesized_pointer_declarators_rejected(self):
        assert_rejected(self, 'int (*p)[2];\n')
        assert_rejected(self, 'int (*f)(void);\n')

    def test_array_of_pointers_and_pointer_returns(self):
        p = compile_text('int *a[2]; int **b[2]; int *f(void); int **g(void);\n')
        self.assertEqual(p['symbols']['a']['type']['kind'], 'array')
        self.assertEqual(p['symbols']['a']['type']['base']['kind'], 'pointer')
        self.assertEqual(p['symbols']['b']['type']['base']['base']['kind'], 'pointer')
        self.assertEqual(p['symbols']['f']['type']['ret']['kind'], 'pointer')
        self.assertEqual(p['symbols']['g']['type']['ret']['base']['kind'], 'pointer')

    def test_static_and_extern_object_function_entities(self):
        compile_text('static int x; static int f(void){return 0;}\n')
        compile_text('extern int x; extern int f(void);\n')

    def test_macro_names_are_case_sensitive(self):
        self.assertEqual(run_text('#define a 1\n#define A 2\nint main(void){if(a==1 && A==2)return 0;return 1;}\n')[0], 0)

    def test_backward_only_indirect_macro_dependency(self):
        self.assertEqual(run_text('#define A 2\n#define B A\n#define C (B+3)\nint main(void){if(C==5)return 0;return 1;}\n')[0], 0)

    def test_local_include_may_include_builtin_header(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            (d/'a.h').write_text('#include <c48.h>\nint a;\n', encoding='ascii')
            (d/'m.c').write_text('#include "a.h"\nint x;\n', encoding='ascii')
            compile_file(d/'m.c', builtin_header='int h(int x);\n')

    def test_builtin_header_compatible_user_declaration_coexists(self):
        compile_text('int h(int x);\n#include <c48.h>\n', builtin_header='int h(int x);\n')
        compile_text('#include <c48.h>\nint h(int x);\n', builtin_header='int h(int x);\n')

    def test_builtin_header_incompatible_user_declaration_rejected(self):
        for src in ('int h(short x);\n#include <c48.h>\n', '#include <c48.h>\nint h(short x);\n'):
            with self.subTest(src=src):
                with self.assertRaises(C48Error) as cm:
                    compile_text(src, builtin_header='int h(int x);\n')
                self.assertEqual(cm.exception.category, 'declaration')

    def test_macro_builtin_header_name_collision_is_rejected(self):
        # Rev 0.11 freezes rejection of this collision, not a specific diagnostic class.
        with self.assertRaises(C48Error):
            compile_text('#define h 1\n#include <c48.h>\n', builtin_header='int h(int x);\n')

    def test_repeated_local_include_compatible_declarations(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            (d/'a.h').write_text('extern int x;\nint h(int x);\n', encoding='ascii')
            (d/'m.c').write_text('#include "a.h"\n#include "a.h"\nint x;\n', encoding='ascii')
            compile_file(d/'m.c')

    def test_invalid_udg_operations_return_einval_before_memory_access(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            (d/'c48host.h').write_text((SDK/'dev/src/c48host.h').read_text(), encoding='ascii')
            src=d/'u.c'
            src.write_text(
                '#include "c48host.h"\n'
                'int main(void){unsigned char b[8]={1,2,3,4,5,6,7,8};'
                'if(udg_define(32,(unsigned char *)0)!=1)return 1;'
                'if(udg_get(-1,(unsigned char *)0)!=1)return 2;'
                'if(udg_draw(0,24,0)!=1)return 3;'
                'if(udg_clear(32)!=1)return 4;return 0;}\n',
                encoding='ascii')
            # C48 does not support pointer casts, so generate the equivalent valid-source
            # test with uninitialized pointer values only after avoiding evaluation via
            # invalid slot validation.
            src.write_text(
                '#include "c48host.h"\n'
                'int main(void){unsigned char *p=0;'
                'if(udg_define(32,p)!=1)return 1;'
                'if(udg_get(-1,p)!=1)return 2;'
                'if(udg_draw(0,24,0)!=1)return 3;'
                'if(udg_clear(32)!=1)return 4;return 0;}\n', encoding='ascii')
            program=compile_file(src)
            screen=ZXScreen(Font4x8.load(FONT_PATH))
            self.assertEqual(C48VM(program,screen).run(),0)


class FloatCorpus(unittest.TestCase):
    def test_required_exact_golden_representations(self):
        golden={
            '0':'0000000000','1':'0000010000','-1':'00ffffff00','.5':'8000000000',
            '0.25':'7f00000000','1.25':'8120000000','2':'0000020000','10':'00000a0000','-12':'00fff4ff00',
        }
        for text,hx in golden.items():
            with self.subTest(text=text):self.assertEqual(Float5.from_decimal(text).hex(),hx)

    def test_roundtrip_representative_fraction_exponents(self):
        for text in ('0.1','3.14159','1e-10','1e10','-2.5','65535','-65535'):
            with self.subTest(text=text):
                f=Float5.from_decimal(text);self.assertEqual(Float5(f.raw).raw,f.raw)

    def test_arithmetic_quantizes_to_float5(self):
        a=Float5.from_decimal('1.25');b=Float5.from_decimal('.5')
        self.assertEqual(a.add(b).to_fraction(),Float5.from_decimal('1.75').to_fraction())
        self.assertEqual(a.sub(b).to_fraction(),Float5.from_decimal('.75').to_fraction())
        self.assertEqual(a.mul(Float5.from_int(2)).to_fraction(),Float5.from_decimal('2.5').to_fraction())
        self.assertEqual(a.div(Float5.from_int(2)).to_fraction(),Float5.from_decimal('.625').to_fraction())

    def test_domain_range_failures(self):
        with self.assertRaises(Float5Error):Float5.from_decimal('1e100')
        with self.assertRaises(Float5Error):Float5.from_int(1).div(Float5.zero())

    def test_strict_transcendental_runtime_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'c48host.h').write_text((SDK/'dev/src/c48host.h').read_text(),encoding='ascii')
            src=d/'m.c';src.write_text('#include "c48host.h"\nint main(void){float x=0.5;x=sin(x);return 0;}\n',encoding='ascii')
            p=compile_file(src);screen=ZXScreen(Font4x8.load(FONT_PATH))
            with self.assertRaises(RuntimeC48Error):C48VM(p,screen).run()


class ScreenAndFormat(unittest.TestCase):
    def test_font_exact_hash_and_shape(self):
        data=FONT_PATH.read_bytes();self.assertEqual(len(data),392);self.assertEqual(data[:8],b'F4X8'+bytes((1,0x20,96,0)))
        self.assertEqual(hashlib.sha256(data).hexdigest(),'90f6818cf81cf3f13509cff32c091075691195d9638dbe801d12daceec1c9339')

    def test_native_bitmap_interleave(self):
        self.assertEqual(bitmap_offset(0,0),0)
        self.assertEqual(bitmap_offset(0,1),0x100)
        self.assertEqual(bitmap_offset(0,8),0x20)
        self.assertEqual(bitmap_offset(0,64),0x800)

    def test_tty64_shares_bitmap_byte_nibbles(self):
        s=ZXScreen(Font4x8.load(FONT_PATH));s.print_at(0,0,b'AB')
        # At least one scanline must carry both left and right nibbles.
        rows=[s.mem[bitmap_offset(0,y)] for y in range(8)]
        self.assertTrue(any((b&0xF0) and (b&0x0F) for b in rows))

    def test_graphics_invalid_arguments_return_positive_einval(self):
        s=ZXScreen(Font4x8.load(FONT_PATH))
        self.assertEqual(s.point(-1,0),1)
        self.assertEqual(s.plot(256,0),1)
        self.assertEqual(s.draw(0,0,256,0),1)
        self.assertEqual(s.circle(0,0,256),1)
        for fn in (s.bright,s.flash,s.inverse,s.over):
            self.assertEqual(fn(2),1)
            self.assertEqual(fn(-1),1)
            self.assertEqual(fn(0),0)
            self.assertEqual(fn(1),0)
        for fn in (s.ink,s.paper,s.border):
            self.assertEqual(fn(-1),1)
            self.assertEqual(fn(8),1)
            self.assertEqual(fn(0),0)
            self.assertEqual(fn(7),0)

    def test_graphics_point_draw_circle(self):
        s=ZXScreen(Font4x8.load(FONT_PATH));self.assertEqual(s.plot(10,10),0);self.assertEqual(s.point(10,10),1)
        self.assertEqual(s.draw(0,0,10,10),0);self.assertEqual(s.point(0,0),1);self.assertEqual(s.point(10,10),1)
        self.assertEqual(s.circle(20,20,0),0);self.assertEqual(s.point(20,20),1)

    def test_graphics_origin_is_spectrum_bottom_left(self):
        s=ZXScreen(Font4x8.load(FONT_PATH))
        self.assertEqual(s.plot(0,0),0)
        self.assertEqual(s.mem[bitmap_offset(0,191)] & 0x80,0x80)
        self.assertEqual(s.mem[bitmap_offset(0,0)] & 0x80,0)
        s.cls();self.assertEqual(s.plot(0,191),0)
        self.assertEqual(s.mem[bitmap_offset(0,0)] & 0x80,0x80)

    def test_plot_over_inverse_truth_table(self):
        s=ZXScreen(Font4x8.load(FONT_PATH))
        # O0/I0 sets.
        s.over(0);s.inverse(0);s.plot(3,4);self.assertEqual(s.point(3,4),1)
        # O0/I1 clears.
        s.inverse(1);s.plot(3,4);self.assertEqual(s.point(3,4),0)
        # O1/I0 toggles.
        s.inverse(0);s.over(1);s.plot(3,4);self.assertEqual(s.point(3,4),1)
        s.plot(3,4);self.assertEqual(s.point(3,4),0)
        # O1/I1 leaves unchanged.
        s.inverse(1);s.plot(3,4);self.assertEqual(s.point(3,4),0)

    def test_attributes_and_udg(self):
        s=ZXScreen(Font4x8.load(FONT_PATH));self.assertEqual(s.ink(2),0);self.assertEqual(s.paper(4),0);self.assertEqual(s.bright(1),0);s.plot(0,0)
        self.assertEqual(s.mem[BITMAP_SIZE+23*32],2|(4<<3)|(1<<6))
        self.assertEqual(s.udg_define(0,bytes([0xFF]*8)),0);self.assertEqual(s.udg_draw(0,0,0),0);self.assertEqual(s.mem[bitmap_offset(0,0)],0xFF)

    def test_format_deterministic_across_source_paths(self):
        p1=compile_bytes(b'int main(void){return 0;}\n',source_name='/a/x.c')
        p2=compile_bytes(b'int main(void){return 0;}\n',source_name='C:/different/x.c')
        self.assertEqual(encode(p1),encode(p2))

    def test_format_integrity_rejects_corruption(self):
        data=bytearray(encode(compile_text('int main(void){return 0;}')));data[-3]^=1
        with self.assertRaises(RuntimeC48Error):decode(bytes(data))


class HostSDKIntegration(unittest.TestCase):
    def test_host_header_and_hello(self):
        p=compile_file(SDK/'dev/src/hello.c');s=ZXScreen(Font4x8.load(FONT_PATH));self.assertEqual(C48VM(p,s).run(),0)
        self.assertNotEqual(s.bytes()[:BITMAP_SIZE],bytes(BITMAP_SIZE))

    def test_cli_compile_run_and_deterministic_recompile(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);src=d/'t.c';out=d/'t.c48b';src.write_text('int main(void){return 7;}\n',encoding='ascii')
            cmd=[sys.executable,str(COMPILER/'c48.py'),str(src),'-o',str(out)]
            a=subprocess.run(cmd,capture_output=True);self.assertEqual(a.returncode,0,a.stderr);b1=out.read_bytes()
            b=subprocess.run(cmd,capture_output=True);self.assertEqual(b.returncode,0,b.stderr);self.assertEqual(b1,out.read_bytes())
            r=subprocess.run([sys.executable,str(COMPILER/'c48run.py'),'--headless',str(out)],capture_output=True)
            self.assertEqual(r.returncode,7,r.stderr)

    def test_stale_temp_is_neither_used_nor_deleted(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); src=d/'x.c'; out=d/'x.c48b'; stale=d/'x.c48b.tmp'
            src.write_text('int main(void){return 0;}\n',encoding='ascii')
            stale.write_bytes(b'owned-by-someone-else')
            cp=subprocess.run([sys.executable,str(COMPILER/'c48.py'),str(src),'-o',str(out)],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            self.assertEqual(stale.read_bytes(),b'owned-by-someone-else')
            self.assertTrue(out.exists())

    def test_noncanonical_c48b_payload_is_rejected_even_with_valid_digest(self):
        p=compile_text('int main(void){return 0;}')
        canonical=encode(p)
        first_nl=canonical.find(b'\n',len(b'C48B1\n'))
        payload=canonical[first_nl+1:-1]
        obj=__import__('json').loads(payload.decode('ascii'))
        altered=__import__('json').dumps(obj,sort_keys=True,indent=1).encode('ascii')
        forged=b'C48B1\n'+hashlib.sha256(altered).hexdigest().encode('ascii')+b'\n'+altered+b'\n'
        with self.assertRaises(RuntimeC48Error): decode(forged)

    def test_rehashed_structurally_invalid_c48b_is_rejected_cleanly(self):
        import json
        obj={"kind":"translation_unit","items":"not-a-list","symbols":{}}
        payload=json.dumps(obj,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode("ascii")
        forged=b"C48B1\n"+hashlib.sha256(payload).hexdigest().encode("ascii")+b"\n"+payload+b"\n"
        with self.assertRaises(RuntimeC48Error) as cm:decode(forged)
        self.assertIn("schema",cm.exception.message)

    def test_c48run_preserves_exact_program_token_as_argv0(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);src=d/'a.c';out=d/'prog.c48b'
            src.write_text("int main(int argc,char **argv){if(argc!=1)return 1;if(argv[0][0]!='p')return 2;if(argv[0][1]!='r')return 3;return 0;}\n",encoding='ascii')
            program=compile_file(src);from c48.format import write as write_program;write_program(out,program)
            r=subprocess.run([sys.executable,str(COMPILER/'c48run.py'),'--headless','prog.c48b'],cwd=d,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)

    def test_c48run_rejects_nonascii_argv_cleanly(self):
        p=compile_text('int main(int argc,char **argv){return 0;}')
        screen=ZXScreen(Font4x8.load(FONT_PATH))
        with self.assertRaises(RuntimeC48Error) as cm:C48VM(p,screen,argv=['pr\u00f8g']).run()
        self.assertIn('canonical ASCII',cm.exception.message)

    def test_c48run_cli_rejects_rehashed_bad_schema_without_traceback(self):
        import json
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);bad=d/'bad.c48b'
            obj={"kind":"translation_unit","items":"bad","symbols":{}}
            payload=json.dumps(obj,ensure_ascii=True,sort_keys=True,separators=(",",":")).encode('ascii')
            bad.write_bytes(b'C48B1\n'+hashlib.sha256(payload).hexdigest().encode('ascii')+b'\n'+payload+b'\n')
            r=subprocess.run([sys.executable,str(COMPILER/'c48run.py'),'--headless',str(bad)],capture_output=True,text=True)
            self.assertEqual(r.returncode,1)
            self.assertIn('invalid C48B1 schema',r.stderr)
            self.assertNotIn('Traceback',r.stderr)

    def test_compile_failure_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);src=d/'t.c';out=d/'t.c48b';out.write_bytes(b'previous')
            src.write_text('int main(void){ this is bad; }\n',encoding='ascii')
            r=subprocess.run([sys.executable,str(COMPILER/'c48.py'),str(src),'-o',str(out)],capture_output=True)
            self.assertNotEqual(r.returncode,0);self.assertEqual(out.read_bytes(),b'previous')

    def test_diagnostic_class_and_stderr(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);src=d/'t.c';src.write_text('long x;\n',encoding='ascii')
            r=subprocess.run([sys.executable,str(COMPILER/'c48.py'),str(src)],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'');self.assertIn(': unsupported:',r.stderr)


class AdditionalCrossCompilerCases(unittest.TestCase):
    def test_empty_and_all_comment_translation_units(self):
        compile_text('')
        compile_text('/* only */\n// still only\n')

    def test_global_bss_zero_semantics(self):
        src = 'int i; int *p; float f; int main(void){if(i!=0)return 1;if(p!=0)return 2;if(f!=0.0)return 3;return 0;}'
        self.assertEqual(run_text(src)[0], 0)

    def test_nonvoid_fallthrough_is_status_one(self):
        src = 'int f(void){int x=1;} int main(void){return f();}'
        self.assertEqual(run_text(src)[0], 1)

    def test_void_call_is_valid_expression_statement(self):
        src = 'void f(void){return;} int main(void){f();return 0;}'
        self.assertEqual(run_text(src)[0], 0)

    def test_void_value_used_as_value_rejected(self):
        assert_rejected(self, 'void f(void){return;} int main(void){int x=0;x=f();return x;}', 'type')

    def test_float_parameter_is_source_pass_by_value(self):
        src = 'void f(float x){x=2.0;return;} int main(void){float x=1.0;f(x);if(x==1.0)return 0;return 1;}'
        self.assertEqual(run_text(src)[0], 0)

    def test_char_function_return_narrows_before_promotion(self):
        src = 'char f(void){return 511;} int main(void){if(f()==255)return 0;return 1;}'
        self.assertEqual(run_text(src)[0], 0)

    def test_main_status_uses_low_eight_bits(self):
        self.assertEqual(run_text('int main(void){return 0x1234;}')[0], 0x34)

    def test_negative_shift_counts_are_masked(self):
        self.assertEqual(run_text(condition_program('(c<<-1)==128', 'unsigned char c=1;'))[0], 0)
        self.assertEqual(run_text(condition_program('(u<<-1)==32768u', 'unsigned int u=1u;'))[0], 0)

    def test_distinct_live_objects_have_distinct_addresses(self):
        src = 'int main(void){int a=0,b=0;if(&a!=&b)return 0;return 1;}'
        self.assertEqual(run_text(src)[0], 0)

    def test_stale_automatic_pointer_is_trapped_by_host_checker(self):
        src = 'int main(void){int *p;{int x=7;p=&x;}return *p;}'
        p = compile_text(src)
        screen = ZXScreen(Font4x8.load(FONT_PATH))
        with self.assertRaises(RuntimeC48Error):
            C48VM(p, screen).run()

    def test_argv_storage_is_read_only(self):
        src = "int main(int argc,char **argv){argv[0][0]='X';return 0;}"
        p = compile_text(src)
        screen = ZXScreen(Font4x8.load(FONT_PATH))
        with self.assertRaises(RuntimeC48Error):
            C48VM(p, screen, argv=['program']).run()

    def test_automatic_initializer_runs_each_block_activation(self):
        src = 'int main(void){int i=0,sum=0;while(i<2){int x=1;x=x+i;sum=sum+x;i++;}if(sum==3)return 0;return 1;}'
        self.assertEqual(run_text(src)[0], 0)

    def test_strncpy_is_bounded_and_zero_count_touches_no_memory(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'c48host.h').write_text((SDK/'dev/src/c48host.h').read_text(),encoding='ascii')
            src=d/'s.c'
            src.write_text(
                '#include "c48host.h"\n'
                "int main(void){char s[3]={'a','b','c'};char d[3]={0};char *p=0;"
                "strncpy(d,s,3);if(d[0]!='a'||d[1]!='b'||d[2]!='c')return 1;"
                "if(strncpy(p,p,0)!=0)return 2;return 0;}\n",encoding='ascii')
            program=compile_file(src);screen=ZXScreen(Font4x8.load(FONT_PATH))
            self.assertEqual(C48VM(program,screen).run(),0)

    def test_zero_length_memory_primitives_touch_no_pointer_memory(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'c48host.h').write_text((SDK/'dev/src/c48host.h').read_text(),encoding='ascii')
            src=d/'z.c'
            src.write_text(
                '#include "c48host.h"\n'
                'int main(void){void *p=0;if(memcpy(p,p,0)!=0)return 1;'
                'if(memmove(p,p,0)!=0)return 2;if(memchr(p,1,0)!=0)return 3;'
                'if(memset(p,1,0)!=0)return 4;return 0;}\n',encoding='ascii')
            program=compile_file(src);screen=ZXScreen(Font4x8.load(FONT_PATH))
            self.assertEqual(C48VM(program,screen).run(),0)

    def test_free_rejects_interior_malloc_pointer(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'c48host.h').write_text((SDK/'dev/src/c48host.h').read_text(),encoding='ascii')
            src=d/'f.c';src.write_text(
                '#include "c48host.h"\nint main(void){char *p;p=malloc(4);if(p==0)return 1;free(p+1);return 0;}\n',encoding='ascii')
            program=compile_file(src);screen=ZXScreen(Font4x8.load(FONT_PATH))
            with self.assertRaises(RuntimeC48Error):C48VM(program,screen).run()

    def test_invalid_print_at_returns_einval_before_text_dereference(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'c48host.h').write_text((SDK/'dev/src/c48host.h').read_text(),encoding='ascii')
            src=d/'p.c';src.write_text(
                '#include "c48host.h"\nint main(void){char *p=0;if(print_at(24,0,p)==1)return 0;return 1;}\n',encoding='ascii')
            program=compile_file(src);screen=ZXScreen(Font4x8.load(FONT_PATH))
            self.assertEqual(C48VM(program,screen).run(),0)

    def test_malloc_free_and_void_call_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d/'c48host.h').write_text((SDK/'dev/src/c48host.h').read_text(), encoding='ascii')
            src = d/'m.c'
            src.write_text('#include "c48host.h"\nint main(void){int *p;p=malloc(2);if(p==0)return 1;*p=123;if(*p!=123)return 2;free(p);return 0;}\n', encoding='ascii')
            program = compile_file(src)
            screen = ZXScreen(Font4x8.load(FONT_PATH))
            self.assertEqual(C48VM(program, screen).run(), 0)

    def test_float_to_char_conversion_order_and_range(self):
        self.assertEqual(run_text('int main(void){char c;c=(char)300.0;if(c==44)return 0;return 1;}')[0], 0)
        self.assertEqual(run_text('int main(void){char c;c=(char)-1.0;return 0;}')[0], 1)

    def test_redundant_float_cast_is_not_in_c48(self):
        assert_rejected(self, 'int main(void){float x=1.0;x=(float)x;return 0;}', 'unsupported')

    def test_implementation_reserved_identifiers(self):
        assert_rejected(self, 'int _start;', 'declaration')
        assert_rejected(self, 'int __x;', 'declaration')

    def test_nonreserved_modern_identifiers_remain_ordinary(self):
        compile_text('int bool;int true;int false;int nullptr;int typeof;')

    def test_crlf_host_normalization_is_semantically_identical(self):
        a = compile_bytes(b'int main(void){return 0;}\n', source_name='x.c')
        b = compile_bytes(b'int main(void){return 0;}\r\n', source_name='x.c')
        self.assertEqual(encode(a), encode(b))

    def test_lexical_error_physical_position(self):
        with self.assertRaises(C48Error) as cm:
            compile_bytes(b'int x;\nint y;\n@\n', source_name='pos.c')
        self.assertEqual(cm.exception.category, 'lexical')
        self.assertIsNotNone(cm.exception.pos)
        self.assertEqual((cm.exception.pos.line, cm.exception.pos.column), (3,1))

    def test_nonascii_error_physical_position(self):
        with self.assertRaises(C48Error) as cm:
            compile_bytes(b'int x;\n  \xff\n', source_name='pos.c')
        self.assertEqual(cm.exception.category, 'lexical')
        self.assertEqual((cm.exception.pos.line, cm.exception.pos.column), (2,3))

    def test_missing_include_is_anchored_at_operand(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            src = d/'m.c'
            src.write_text('   #include "none.h"\n', encoding='ascii')
            with self.assertRaises(C48Error) as cm:
                compile_file(src)
            self.assertEqual(cm.exception.category, 'io')
            self.assertEqual(cm.exception.pos.line, 1)
            self.assertEqual(cm.exception.pos.column, 13)

    def test_define_inside_function_has_preprocessing_visibility(self):
        src = 'int main(void){\n#define X 7\nint a=X;return a-7;}\nint y=X;'
        self.assertEqual(run_text(src)[0], 0)

    def test_comment_before_directive_still_allows_directive(self):
        compile_text('/*c*/   #define X 3\nint x=X;\n')

    def test_comment_marker_inside_string_macro_is_data(self):
        compile_text('#define S "/*"\nchar *p=S;\n')

    def test_unterminated_block_comment_reports_actual_opening_marker(self):
        src = 'char *s="/*"; /* closed */ int x; /* never closes\n'
        with self.assertRaises(C48Error) as cm:
            compile_text(src)
        self.assertEqual(cm.exception.category, 'lexical')
        self.assertEqual((cm.exception.pos.line, cm.exception.pos.column), (1, 35))

    def test_unterminated_block_comment_after_prior_line_tracks_original_open(self):
        src = 'int x; /* begins\nstill comment\n'
        with self.assertRaises(C48Error) as cm:
            compile_text(src)
        self.assertEqual(cm.exception.category, 'lexical')
        self.assertEqual((cm.exception.pos.line, cm.exception.pos.column), (1, 8))

    def test_canonicalized_macro_redefinition(self):
        compile_text('#define A 1\n#define B A\n#define B 1\nint x=B;')

    def test_direct_screen_layout_is_6912_bytes(self):
        s = ZXScreen(Font4x8.load(FONT_PATH))
        self.assertEqual(len(s.bytes()), 6912)

    def test_memory_alignment_for_scalar_objects(self):
        from c48.memory import C48Memory
        from c48.typesys import CHAR, FLOAT, INT
        mem = C48Memory()
        a = mem.allocate(CHAR.size, CHAR.alignment, CHAR, 'test')
        b = mem.allocate(INT.size, INT.alignment, INT, 'test')
        c = mem.allocate(FLOAT.size, FLOAT.alignment, FLOAT, 'test')
        self.assertEqual(a.start % 1, 0)
        self.assertEqual(b.start % 2, 0)
        self.assertEqual(c.start % 1, 0)

    def test_float_known_manual_0_1_pattern(self):
        self.assertEqual(Float5.from_decimal('0.1').hex(), '7d4ccccccd')

    def test_float_large_integer_promotes_to_normalized_form(self):
        self.assertEqual(Float5.from_decimal('65536').hex(), '9100000000')
        self.assertEqual(Float5.from_decimal('-65536').hex(), '9180000000')

    def test_host_argv_obeys_native_arg1_256_byte_limit(self):
        p=compile_text('int main(int argc,char **argv){return 0;}')
        screen=ZXScreen(Font4x8.load(FONT_PATH))
        # 8-byte ARG1 header + two NUL-terminated strings = 257 bytes.
        with self.assertRaises(RuntimeC48Error):
            C48VM(p,screen,argv=['p','x'*246]).run()

    def test_host_argv_exact_boundary_and_terminator(self):
        src='int main(int argc,char **argv){if(argc!=2)return 1;if(argv[2]!=0)return 2;return 0;}'
        p=compile_text(src);screen=ZXScreen(Font4x8.load(FONT_PATH))
        # 8 + (1+1) + (245+1) = 256: exact ARG1 boundary.
        self.assertEqual(C48VM(p,screen,argv=['p','x'*245]).run(),0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
