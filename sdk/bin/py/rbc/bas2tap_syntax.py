# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""The Spectrum BASIC syntax pass of Martijn van der Heide's BAS2TAP 2.6.

Pure Python, working on Sinclair tokens produced by the upstream tokenizer.
The corresponding reference is CheckSyntax, ScanExpression, ScanVariable and
HandleClass01..15 in unmodified bas2tap.c.  No ROM or compiler is executed.
"""
from __future__ import annotations

from dataclasses import dataclass


class SpectrumSyntaxError(ValueError):
    pass


# A token's expression type: N is numeric, S is string, P is PRINT-only, O is non-expression.
# Other 48K tokens are covered by command grammar.
WORDS = ("SPECTRUM|PLAY|RND|INKEY$|PI|FN|POINT|SCREEN$|ATTR|AT|TAB|"
         "VAL$|CODE|VAL|LEN|SIN|COS|TAN|ASN|ACS|ATN|LN|EXP|INT|SQR|"
         "SGN|ABS|PEEK|IN|USR|STR$|CHR$|NOT|BIN|OR|AND|<=|>=|<>|"
         "LINE|THEN|TO|STEP|DEF FN|CAT|FORMAT|MOVE|ERASE|OPEN #|"
         "CLOSE #|MERGE|VERIFY|BEEP|CIRCLE|INK|PAPER|FLASH|BRIGHT|"
         "INVERSE|OVER|OUT|LPRINT|LLIST|STOP|READ|DATA|RESTORE|NEW|"
         "BORDER|CONTINUE|DIM|REM|FOR|GO TO|GO SUB|INPUT|LOAD|LIST|"
         "LET|PAUSE|NEXT|POKE|PRINT|PLOT|RUN|SAVE|RANDOMIZE|IF|"
         "CLS|DRAW|CLEAR|RETURN|COPY").split('|')
WORD_CODE = {w: i+0xA3 for i,w in enumerate(WORDS)}
WORD_OF = {i+0xA3: w for i,w in enumerate(WORDS)}
NUM_FN = set(range(0xA5,0xA6)) | {0xA7,0xA8,0xA9,0xAB} | set(range(0xAF,0xC1)) | {0xC3}
STR_FN = {0xA6,0xAA,0xAE,0xC1,0xC2}
PRINT_FN = {0xAC,0xAD}
COLORS = set(range(0xD9,0xDF)) | {0xE4}
INFIX_WORD = set(range(0xC5,0xCA))
# Construct syntax signatures from the original C TokenMap's KeywordClass. Integer 1..15: class
# method; integer >=32: required Sinclair byte. No pretending the Spectrum understood us.
GRAMMAR = {
    'SPECTRUM':(), 'PLAY':(12,), 'RND':(), 'INKEY$':(), 'PI':(),
    'OR':(5,), 'AND':(5,), '<=':(5,), '>=':(5,), '<>':(5,),
    'FN':(1,40,13,41),'POINT':(40,8,41),'SCREEN$':(40,8,41),
    'ATTR':(40,8,41),'AT':(8,),'TAB':(6,),
    'VAL$':(10,),'CODE':(10,),'VAL':(10,),'LEN':(10,),
    **{s:(6,) for s in ("SIN COS TAN ASN ACS ATN LN EXP INT SQR SGN ABS PEEK IN USR STR$ CHR$ NOT").split()},
    'DEF FN':(15,),'CAT':(11,),'FORMAT':(11,),'MOVE':(11,),
    'ERASE':(11,),'OPEN #':(11,),'CLOSE #':(11,),'MERGE':(11,),
    'VERIFY':(11,),'BEEP':(8,),'CIRCLE':(9,44,6),
    **{s:(7,) for s in ('INK','PAPER','FLASH','BRIGHT','INVERSE','OVER')},
    'OUT':(8,),'LPRINT':(5,),'LLIST':(3,),'STOP':(),
    'READ':(14,),'DATA':(13,),'RESTORE':(3,),'NEW':(),
    'BORDER':(6,),'CONTINUE':(), 'DIM':(1,40,13,41),
    'REM':(5,),'FOR':(4,61,6,0xCC,6,0xCD,6),
    'GO TO':(6,),'GO SUB':(6,),'INPUT':(5,),'LOAD':(11,),
    'LIST':(3,),'LET':(1,61,2),'PAUSE':(6,),'NEXT':(4,),
    'POKE':(8,),'PRINT':(5,),'PLOT':(9,),'RUN':(3,),
    'SAVE':(11,),'RANDOMIZE':(3,),'IF':(6,0xCB),
    'CLS':(),'DRAW':(9,44,6),'CLEAR':(3,),
    'RETURN':(),'COPY':(),
}


@dataclass
class SyntaxState:
    """Global flags in BAS2TAP 2.6 (per entire numbered program)."""
    program_48k: int = -1
    interface: int = -1
    token_bracket: bool = False


def _clean_tokens(body: bytes) -> bytes:
    """CheckSyntax's stripped token stream, retaining numeric-cache markers."""
    cleaned = bytearray()
    p = 0
    while p < len(body):
        b = body[p]
        if b == 13:
            break
        if b == 14:
            cleaned.append(b)
            p += 6
            continue
        if b <= 15 or 24 <= b <= 32:
            p += 1
            continue
        if 16 <= b <= 21:
            p += 2
            continue
        if b in (22,23):
            p += 3
            continue
        cleaned.append(b)
        p += 1
    return bytes(cleaned) + b'\r'


class _Parser:
    def __init__(self, body: bytes, line_number: int, state: SyntaxState):
        self.data = _clean_tokens(body)
        self.line = line_number
        self.state = state
        self.statement = 0
        self.pos = 0
        self.depth = 0

    def cur(self) -> int:
        return self.data[self.pos] if self.pos < len(self.data) else 13

    def ahead(self, n=1) -> int:
        return self.data[self.pos+n] if self.pos+n < len(self.data) else 13

    def step(self):
        self.pos += 1

    def tok(self, code=None) -> str:
        code = self.cur() if code is None else code
        return WORD_OF.get(code, chr(code) if 32 <= code < 127 else f'${code:02X}')

    def fail(self, message):
        raise SpectrumSyntaxError(f'Line {self.line}, statement {self.statement}: {message}')

    def expect(self, code):
        if self.cur() != code:
            self.fail(f'Expected {self.tok(code)!r}, got {self.tok()!r}')
        self.step()

    def need(self):
        if self.cur() in (13,58):
            self.fail('Unexpected end of statement')

    def isalpha(self, ch):
        return 65 <= ch <= 90 or 97 <= ch <= 122

    def isdigit(self, ch):
        return 48 <= ch <= 57

    def var(self, mode: int) -> tuple[bool,int] | None:
        if not self.isalpha(self.cur()):
            return None
        i = 0
        while self.isalpha(self.cur()) or self.isdigit(self.cur()):
            i += 1
            self.step()
        numeric = True
        if self.cur() == 36:
            if i != 1:
                self.fail('String variables can only have single character names')
            self.step()
            numeric = False
        if mode >= 0 and self.cur() == 40:
            if i != 1:
                self.fail('Arrays can only have single character names')
            if mode == 0:
                self.fail('Slicing/Indexing not allowed')
            self.step()
            if self.cur() == 41:
                self.fail('Empty array index not allowed')
            if self.cur() == 0xCC:
                if mode == 2:
                    self.fail('Slicing token TO inappropriate for arrays')
            else:
                self.expr(open_bracket=True)
                if self.cur() == 41:
                    self.step()
                    return numeric,i
            if self.cur() not in (44,0xCC):
                self.fail('Unexpected index character')
            is_array = self.cur() == 44
            if mode == 2 and not is_array:
                self.fail('Slicing token TO inappropriate for arrays')
            if numeric and not is_array:
                self.fail('Only character strings can be sliced')
            while self.cur() != 41:
                self.step()
                if self.cur() != 41:
                    self.expr(open_bracket=True)
                if self.cur() not in (41,44,0xCC):
                    self.fail('Expected comma, TO or ) in array index')
                if not is_array and self.cur() != 41:
                    self.fail('Expected ) in string slice')
            self.step()
        return numeric,i

    def slice_string(self):
        self.expect(40)
        if self.cur() == 41:
            self.step()
            return
        if self.cur() != 0xCC:
            if not self.expr(open_bracket=True):
                self.fail('Slice values must be numeric')
        if self.cur() == 41:
            self.step()
            return
        self.expect(0xCC)
        if self.cur() != 41:
            if not self.expr(open_bracket=True):
                self.fail('Slice values must be numeric')
        self.expect(41)

    def expr(self, *, keyword: int = 0, open_bracket=False,
             numeric_expected=False) -> bool:
        """ScanExpression: return True for numeric, False for string."""
        self.depth += 1
        if self.depth > 150:
            self.fail('Expression recursion limit')
        try:
            return self._expr(keyword,open_bracket,numeric_expected)
        finally:
            self.depth -= 1

    def _expr(self, keyword: int, open_bracket: bool,
              numeric_expected: bool) -> bool:
        typename = None
        result_type = None
        expect_operand = True
        has_operand = False
        last_parenthetical = False
        while True:
            b = self.cur()
            if b in (13,58,41,44,59,39,0xCC,0xCD,0xCB) or (b in (0xC5,0xC6) and not has_operand):
                # The unmodified C ScanExpression returns its default numeric
                # type when a trailing operand is missing. The independent
                # Spectrum ROM check remains responsible for disallowing these
                # malformed statements in RBC.
                if not has_operand or expect_operand:
                    return True
                if open_bracket and b in (13,58):
                    self.fail('Too few closing brackets')
                return result_type if result_type is not None else typename
            if expect_operand:
                if b in (43,45):
                    self.step()
                    if typename is False:
                        self.fail('Type conflict in expression')
                    continue
                atom_start = self.pos
                item_type = self.atom(keyword)
                # The C scanner retains the numeric type from nested logical expressions
                # while evaluating INT(...), too.
                nested = self.data[atom_start:self.pos]
                last_parenthetical = item_type is True and (
                    b == 40 or (b in NUM_FN and 0xC6 in nested))
                if typename is not None and item_type != typename:
                    self.fail('Type conflict in expression')
                typename = item_type
                has_operand = True
                expect_operand = False
                # Exact C ScanExpression rule: operands to expression functions are
                # returned after the first scanned atom. Parenthesized subexpressions
                # were already parsed in atom.
                if keyword in NUM_FN or keyword in STR_FN:
                    return result_type if result_type is not None else typename
            elif b in (43,45,42,47,94):
                if b != 43 and typename is False:
                    self.fail('Type conflict in expression')
                self.step()
                expect_operand = True
            elif b in (61,60,62,0xC7,0xC8,0xC9):
                self.step()
                result_type = True
                typename = None
                expect_operand = True
            elif b in (0xC5,0xC6):
                self.step()
                # The 2013 C scanner inspects the incoming *Type before assigning it
                # in this branch; in ordinary print contexts its default is false and
                # the original rejects OR.
                if b == 0xC5:
                    if keyword == 0xC6 and typename is False and result_type is not True:
                        self.fail('AND requires numeric right value')
                    if result_type is not True and keyword != 0xC6 and not numeric_expected:
                        self.fail('OR requires numeric left value')
                right_type = self.expr(keyword=b)
                if not right_type:
                    self.fail('AND/OR requires numeric right value')
                left_type = result_type if result_type is not None else typename
                return (left_type is not False or b == 0xC5)
            else:
                return result_type if result_type is not None else typename

    def atom(self, keyword: int) -> bool:
        b = self.cur()
        if b == 40:
            self.step()
            t = self.expr(open_bracket=True)
            self.expect(41)
            if self.cur() == 40:
                if t:
                    self.fail('Cannot slice numerical value')
                self.slice_string()
            return t
        if self.isdigit(b) or b in (46,0xC4):
            if b == 0xC4:
                self.step()
            while self.isdigit(self.cur()) or self.cur() in (46,69,101,43,45):
                self.step()
            self.expect(14)
            return True
        if b == 34:
            while self.cur() == 34:
                self.step()
                while self.cur() != 34:
                    if self.cur() == 13:
                        self.fail('Unclosed quoted string')
                    self.step()
                self.step()
            if self.cur() == 40:
                self.slice_string()
            return False
        var = self.var(1)
        if var is not None:
            return var[0]
        if b == 0xC0 and self.ahead() == 34:
            self.step()
            self.step()
            c = self.cur()
            if not 65 <= (c & 0xDF) <= 85 or self.ahead() != 34:
                self.fail('Bad UDG name in USR expression')
            if (c & 0xDF) in (84,85):
                if self.state.program_48k == 0:
                    self.fail('48K UDG conflicts with 128K BASIC')
                self.state.program_48k = 1
            self.pos += 2
            return True
        if b in NUM_FN or b in STR_FN or b in PRINT_FN:
            if b in PRINT_FN and keyword not in (0xF5,0xE0):
                self.fail(f'Unexpected token {self.tok()!r}')
            self.step()
            self.signature(b)
            return b not in STR_FN
        self.fail(f'Unexpected token {self.tok()!r}')

    def numeric(self, keyword=0):
        if not self.expr(keyword=keyword,numeric_expected=True):
            if keyword != 0xC0:
                self.fail('Expected numeric expression')

    def string(self, keyword=0):
        if self.expr(keyword=keyword):
            self.fail('Expected string expression')

    def items(self, keyword):
        while True:
            while self.cur() in (44,59,39):
                self.step()
            if self.cur() in (13,58):
                break
            if self.cur() == 35:
                self.step()
                self.stream(keyword)
            elif self.cur() in COLORS or self.cur() == 0xAD:
                self.step()
                self.numeric(keyword)
            elif self.cur() == 0xAC:
                self.step()
                self.pair(keyword)
            elif keyword == 0xEE and self.cur() == 0xCA:
                self.step()
                v = self.var(0)
                if v is None or v[0]:
                    self.fail('INPUT LINE requires a string variable')
            else:
                self.expr(keyword=keyword)
            if self.cur() in (13,58):
                break
            if self.cur() not in (44,59,39):
                self.fail('Expected PRINT/INPUT item separator')

    def pair(self, keyword):
        self.numeric(keyword)
        self.expect(44)
        self.numeric(keyword)

    def colors(self, keyword):
        while self.cur() in COLORS:
            self.step()
            self.numeric(keyword)
            self.expect(59)
        self.pair(keyword)

    def variables(self, keyword):
        while True:
            if self.var(2) is None:
                self.fail('Expected variable')
            if self.cur() in (13,58):
                break
            self.expect(44)

    def arguments(self, keyword, typ=None):
        if self.cur() == 41 and keyword == 0xA8:
            return
        while True:
            x = self.expr(keyword=keyword)
            if typ is not None and x != typ:
                self.fail('Wrong argument expression type')
            if keyword == 0xE9 and not x:
                self.fail('DIM requires numeric dimensions')
            if self.cur() in (13,58,41):
                break
            self.expect(44)

    def def_fn(self):
        v = self.var(-1)
        if v is None or v[1] != 1:
            self.fail('DEF FN requires one-letter function name')
        if self.cur() == 40:
            self.step()
            if self.cur() == 41:
                self.fail('Empty DEF FN parameter array')
            while True:
                v = self.var(-1)
                if v is None or v[1] != 1:
                    self.fail('DEF FN parameter must be a one-letter variable')
                self.expect(14)
                if self.cur() == 41:
                    break
                self.expect(44)
            self.step()
        self.expect(61)
        self.expr(keyword=0xCE)

    def hardware(self, n):
        if n == 1 and self.state.interface == 2 or n == 2 and self.state.interface == 1:
            self.fail('Interface 1 and Opus Discovery channel conflict')
        self.state.interface = n

    def stream(self, keyword):
        self.hardware(0)
        self.numeric(keyword)

    def channel(self, keyword):
        if self.cur() != 34:
            self.numeric(keyword)
            self.hardware(2)
            ch = ord('m')
            self.expect(59)
            return ch
        self.step()
        c = self.cur()
        if not self.isalpha(c) and c not in (35,0xAF,0xCF):
            self.fail('Bad channel identifier')
        self.step()
        self.expect(34)
        ch = c | 32 if self.isalpha(c) else c
        mode = 1 if ch == ord('n') else (2 if ch in (ord('j'),ord('d'),0xAF) else 0)
        self.hardware(mode)
        if ch in (ord('m'),ord('d'),ord('n'),35,0xCF):
            self.expect(59)
            self.numeric(keyword)
            if ch == ord('m'):
                self.expect(59)
        return ch

    def filename(self, keyword, allow_empty=False):
        if self.cur() == 34:
            if not allow_empty and self.ahead() == 34 and self.ahead(2) != 34:
                self.fail('Empty filename not allowed')
            while self.cur() == 34:
                self.step()
                while self.cur() != 34:
                    if self.cur() == 13:
                        self.fail('Unterminated filename')
                    self.step()
                self.step()
        else:
            self.string(keyword)

    def filetype(self, keyword, saving=False):
        if self.cur() in (13,58):
            return
        b = self.cur()
        if b == 0xAF:
            self.step()
            if not saving:
                if self.cur() not in (13,58):
                    self.numeric(keyword)
                    if self.cur() == 44:
                        self.step()
                        self.numeric(keyword)
            else:
                self.numeric(keyword)
                self.expect(44)
                self.numeric(keyword)
        elif b == 0xAA:
            self.step()
        elif b == 0xE4:
            self.step()
            v=self.var(-1)
            if v is None or v[1] != 1:
                self.fail('DATA requires a single letter array')
            self.expect(40)
            self.expect(41)
        elif b == 0xCA and saving:
            self.step()
            self.numeric(keyword)
        else:
            self.fail(f'Unknown file type {self.tok()!r}')

    def io(self, keyword):
        if keyword in (0xEF,0xD5,0xD6,0xF8):
            ch = 0
            if self.cur() == 42:
                self.step()
                ch = self.channel(keyword)
                if ch not in (ord('m'),ord('b'),ord('n')):
                    self.fail('Invalid channel for LOAD/SAVE/VERIFY/MERGE')
            elif self.cur() == 33:
                self.step()
                if self.state.program_48k == 1:
                    self.fail('128K file operation conflicts with 48K UDG')
                self.state.program_48k = 0
            if ch not in (0,ord('m')):
                if self.cur() not in (13,58,0xAF,0xE4,0xCA,0xAA):
                    self.fail('Channel does not use filenames')
            else:
                if self.cur() in (13,58,0xAF,0xE4,0xCA,0xAA):
                    self.fail('Expected filename')
                self.filename(keyword, allow_empty=keyword!=0xF8)
            if self.cur() not in (13,58):
                if keyword == 0xD5 and self.cur() == 0xAF:
                    self.fail('Cannot MERGE CODE')
                self.filetype(keyword,saving=keyword==0xF8)
        elif keyword == 0xCF:
            self.hardware(0)
            if self.cur() == 35:
                self.step()
                self.stream(keyword)
                self.expect(44)
            self.numeric(keyword)
        elif keyword == 0xD0:
            ch = self.channel(keyword)
            if ch == ord('m'):
                self.filename(keyword)
            elif ch in (ord('t'),ord('b'),ord('j')):
                self.expect(59)
                self.numeric(keyword)
            else:
                self.fail('Invalid FORMAT channel')
        elif keyword == 0xD1:
            for n in range(2):
                if self.cur() == 35:
                    self.step()
                    self.stream(keyword)
                else:
                    ch = self.channel(keyword)
                    if ch == ord('m'):
                        self.filename(keyword)
                    elif ch in (ord('t'),ord('b'),ord('n'),ord('d')):
                        pass
                    elif ch == ord('s') and n == 1 or ch == ord('k') and n == 0:
                        pass
                    else:
                        self.fail('Invalid MOVE channel')
                if n == 0:
                    self.expect(0xCC)
        elif keyword == 0xD2:
            if self.cur() == 33:
                self.step()
                if self.state.program_48k == 1:
                    self.fail('128K file operation conflicts with 48K UDG')
                self.state.program_48k = 0
            elif self.channel(keyword) != ord('m'):
                self.fail('ERASE requires ! or microdrive')
            self.filename(keyword)
        elif keyword == 0xD3:
            self.stream(keyword)
            if self.cur() not in (44,59):
                self.fail('OPEN # requires channel separator')
            self.step()
            ch = self.channel(keyword)
            if ch == ord('m'):
                self.filename(keyword)
            elif ch not in (ord('s'),ord('k'),ord('p'),ord('t'),ord('b'),ord('n'),0xAF,0xCF,35):
                self.fail('Invalid OPEN # channel')
            if self.cur() in (0xBF,0xDF,0xB9,0xA5):
                tok = self.cur()
                self.step()
                self.hardware(2)
                if tok != 0xBF:
                    self.numeric(keyword)
                    if tok == 0xA5 and self.cur() == 44:
                        self.step()
                        self.numeric(keyword)
        elif keyword == 0xD4:
            self.stream(keyword)

    def signature(self, keyword):
        sig = GRAMMAR.get(self.tok(keyword),())
        var_type = True
        for index,spec in enumerate(sig):
            if self.cur() in (13,58):
                if spec in (3,5):
                    continue
                if keyword == 0xEB and spec == 0xCD or keyword == 0xFC and spec == 44:
                    break
                self.fail('Unexpected end of line')
            if spec >= 32:
                if self.cur() != spec:
                    if keyword == 0xEB and spec == 0xCD and self.cur() in (13,58) or keyword == 0xFC and spec == 44 and self.cur() in (13,58):
                        break
                    self.fail(f'Expected token {self.tok(spec)!r}, got {self.tok()!r}')
                self.step()
            elif spec == 1:
                m = -1 if keyword in (0xA8,0xE9) else 1 if keyword == 0xF1 else 2
                v = self.var(m)
                if v is None:
                    self.fail('Expected variable')
                var_type = v[0]
            elif spec == 2:
                if self.expr(keyword=keyword) != var_type:
                    self.fail('Bad assignment expression type')
            elif spec == 3:
                if self.cur() not in (13,58):
                    if keyword == 0xFD and self.cur() == 35:
                        self.step()
                        self.hardware(0)
                        if self.cur() in (13,58):
                            continue
                    self.numeric(keyword)
            elif spec == 4:
                v = self.var(0)
                if v is None or v != (True,1):
                    self.fail('Single-letter numeric variable required')
            elif spec == 5:
                self.items(keyword)
            elif spec in (6,7):
                self.numeric(keyword)
            elif spec == 8:
                self.pair(keyword)
            elif spec == 9:
                self.colors(keyword)
            elif spec == 10:
                self.string(keyword)
            elif spec == 11:
                self.io(keyword)
            elif spec == 12:
                self.arguments(keyword,False)
            elif spec == 13:
                self.arguments(keyword)
            elif spec == 14:
                self.variables(keyword)
            elif spec == 15:
                self.def_fn()

    def check(self):
        while self.cur() != 13:
            self.statement += 1
            start = self.pos
            keyword=self.cur()
            self.step()
            if keyword==0xEA:
                return
            if keyword == 0xA9 and self.cur() == 35:
                self.step()
                self.stream(keyword)
                self.expect(59)
                self.numeric(keyword)
            elif not (keyword in (58,) or 0xCE <= keyword <= 0xFF):
                self.fail(f'Unexpected statement keyword {self.tok(keyword)!r}')
            else:
                if keyword in (0xE1,0xF0) and self.cur() == 35:
                    self.step()
                    self.stream(keyword)
                    if self.cur() not in (13,58):
                        self.expect(44)
                self.signature(keyword)
            if keyword != 0xFA and self.cur() not in (13,58):
                if keyword == 0xFB and self.cur() == 35:
                    self.step()
                    self.hardware(0)
                else:
                    self.fail(f'Expected end of statement, got {self.tok()!r}')
            if self.cur() == 58:
                while self.cur() == 58:
                    self.step()
                    self.statement += 1
            if start == self.pos:
                self.fail('Syntax scanner made no progress')


def check_line(tokens: bytes, line_number: int, state: SyntaxState | None = None):
    """Raise SpectrumSyntaxError for a rejected BAS2TAP syntax line."""
    if not tokens.endswith(b'\r'):
        raise SpectrumSyntaxError(f'Line {line_number}: missing BASIC carriage return')
    _Parser(tokens,line_number,state if state is not None else SyntaxState()).check()


def check_program(program: bytes):
    """Validate records (two-byte big-endian number, LE length, token body)."""
    mode=SyntaxState()
    off=0
    while off < len(program):
        if len(program)-off < 4:
            raise SpectrumSyntaxError('Truncated numbered BASIC record')
        line=int.from_bytes(program[off:off+2],'big')
        length=int.from_bytes(program[off+2:off+4],'little')
        body=program[off+4:off+4+length]
        if len(body)!=length or not body.endswith(b'\r'):
            raise SpectrumSyntaxError(f'Line {line}: corrupt token record')
        check_line(body,line,mode)
        off+=4+length