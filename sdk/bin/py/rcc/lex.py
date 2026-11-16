# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rcc: C48 lexer and preprocessor (C48 Language Specification Rev 0.11).

The preprocessor is token based: `#include "x"` (one level), `#include <c48.h>`
and object-like `#define NAME constant-tokens`.  Everything else is rejected.
"""
import os

KEYWORDS = {'break', 'char', 'continue', 'do', 'else', 'extern', 'float', 'for',
            'if', 'int', 'return', 'short', 'sizeof', 'static', 'unsigned',
            'void', 'while'}
RESERVED = {'auto', 'case', 'const', 'default', 'double', 'enum', 'goto', 'long',
            'register', 'signed', 'struct', 'switch', 'typedef', 'union',
            'volatile', 'inline', 'restrict', '_Alignas', '_Alignof', '_Atomic',
            '_Bool', '_Complex', '_Generic', '_Imaginary', '_Noreturn',
            '_Static_assert', '_Thread_local'}
# longest match first; unsupported compound forms are lexed whole and rejected
OPS = ['<<=', '>>=', '...', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=',
       '->', '++', '--', '<<', '>>', '<=', '>=', '==', '!=', '&&', '||',
       '=', '+', '-', '*', '/', '%', '<', '>', '&', '|', '^', '~', '!',
       '(', ')', '[', ']', '{', '}', ';', ',', '?', ':', '.']
UNSUPPORTED_OPS = {'<<=', '>>=', '...', '+=', '-=', '*=', '/=', '%=', '&=',
                   '|=', '^=', '->', '?', ':', '.'}
ESC = {'\\': 0x5C, "'": 0x27, '"': 0x22, '0': 0, 'a': 7, 'b': 8, 't': 9,
       'n': 10, 'v': 11, 'f': 12, 'r': 13}


class Where(tuple):
    """Two-element source location with an optional exact lexical column."""
    def __new__(cls, file, line, column=None):
        obj = super().__new__(cls, (file, line))
        obj.column = column
        return obj


class CError(Exception):
    def __init__(self, msg, where=None, cls='syntax'):
        self.message = msg
        self.where = where
        self.column = getattr(where, "column", None)
        self.cls = cls
        super().__init__(('%s:%d: ' % where if where else '') + '%s: %s' % (cls, msg))


class Tok:
    __slots__ = ('kind', 'val', 'file', 'line', 'bol', 'text', 'ws', 'column')

    def __init__(self, kind, val, file, line, bol, text=None, ws=True):
        self.kind = kind        # 'id' 'kw' 'int' 'float' 'char' 'str' 'op' 'eof'
        self.val = val
        self.file = file
        self.line = line
        self.bol = bol          # first token on its physical line
        self.text = text
        self.ws = ws            # preceded by white space or a comment
        self.column = None

    @property
    def where(self):
        return Where(self.file, self.line, self.column)

    def __repr__(self):
        return 'Tok(%s,%r)' % (self.kind, self.val)


def _isid0(c):
    return c.isascii() and (c.isalpha() or c == '_')


def _isid(c):
    return c.isascii() and (c.isalnum() or c == '_')


def check_comment(text, fname, line):
    """Comment bytes are ignored: C48 Rev 0.11 (P0039, P0042, P0044, P0049)
    permits any byte value inside /* ... */ and // comments - NUL, CR, other
    control bytes and 0x80..0xFF included.  The byte rules apply outside
    comments only."""
    return


def _bad_byte(c):
    o = ord(c)
    if c == '\r':
        return 'CR'
    if o == 0:
        return 'NUL'
    if o >= 0x80:
        return 'non-ASCII byte 0x%02X' % o
    if o < 0x20 or o == 0x7F:
        return 'control byte 0x%02X' % o
    return None


def lex(src, fname, info=None):
    """Tokenize one source file (bytes or str).  `info`, if a dict, receives
    'ml_comments': the lines on which a block comment starts and spans a LF."""
    if isinstance(src, bytes):
        src = src.decode('latin-1')
    src = src.replace('\r\n', '\n')
    toks = []
    mlc = set()
    i, n, line = 0, len(src), 1
    bol = True
    ws = True
    while i < n:
        c = src[i]
        if c == '\n':
            line += 1
            bol = True
            ws = True
            i += 1
            continue
        if c in ' \t':
            ws = True
            i += 1
            continue
        if c == '/' and src.startswith('//', i):
            j = src.find('\n', i)
            j = n if j < 0 else j
            check_comment(src[i:j], fname, line)
            i = j
            ws = True
            continue
        if c == '/' and src.startswith('/*', i):
            j = src.find('*/', i + 2)
            if j < 0:
                raise CError('unterminated comment', Where(fname, line, i - src.rfind('\n', 0, i)), 'lexical')
            check_comment(src[i:j], fname, line)
            k = src.count('\n', i, j)
            if k:
                mlc.add(line)
            line += k
            i = j + 2
            ws = True
            continue
        where = Where(fname, line, i - src.rfind('\n', 0, i))
        if _isid0(c):
            j = i
            while j < n and _isid(src[j]):
                j += 1
            w = src[i:j]
            if j < n and src[j] in '\'"' and w in ('L', 'u', 'U', 'u8'):
                raise CError('prefixed literal unsupported', where, 'unsupported')
            if len(w) > 15:
                raise CError('identifier %s is longer than 15 characters' % w, where, 'lexical')
            kind = 'kw' if w in KEYWORDS else 'id'
            toks.append(Tok(kind, w, fname, line, bol))
            bol = False
            toks[-1].ws = ws
            toks[-1].column = where.column
            ws = False
            i = j
            continue
        if c.isdigit() or (c == '.' and i + 1 < n and src[i + 1].isdigit()):
            j = i
            while j < n and (_isid(src[j]) or src[j] == '.' or
                             (src[j] in '+-' and src[j - 1] in 'eE' and
                              not src[i:j].lower().startswith('0x'))):
                j += 1
            text = src[i:j]
            toks.append(_number(text, where, bol))
            bol = False
            toks[-1].ws = ws
            toks[-1].column = where.column
            ws = False
            i = j
            continue
        if c == "'":
            j, bs = _literal(src, i + 1, "'", where)
            if len(bs) != 1:
                raise CError('character literal must be one byte', where, 'lexical')
            toks.append(Tok('char', bs[0], fname, line, bol))
            bol = False
            toks[-1].ws = ws
            toks[-1].column = where.column
            ws = False
            i = j
            continue
        if c == '"':
            j, bs = _literal(src, i + 1, '"', where)
            toks.append(Tok('str', bs, fname, line, bol))
            bol = False
            toks[-1].ws = ws
            toks[-1].column = where.column
            ws = False
            i = j
            continue
        if c == '#':
            toks.append(Tok('hash', '#', fname, line, bol))
            toks[-1].column = where.column
            bol = False
            toks[-1].ws = ws
            toks[-1].column = where.column
            ws = False
            i += 1
            continue
        for op in OPS:
            if src.startswith(op, i):
                toks.append(Tok('op', op, fname, line, bol))
                toks[-1].column = where.column
                bol = False
                toks[-1].ws = ws
                ws = False
                i += len(op)
                break
        else:
            bad = _bad_byte(c)
            if bad:
                raise CError('%s in source (only TAB, LF and printable ASCII are allowed)' % bad,
                             where, 'lexical')
            raise CError('invalid source character %r' % c, where, 'lexical')
    toks.append(Tok('eof', None, fname, line, True))
    if info is not None:
        info['ml_comments'] = mlc
    return toks


def _literal(src, i, q, where):
    out = bytearray()
    n = len(src)
    while True:
        if i >= n or src[i] == '\n':
            raise CError('unterminated literal', where, 'lexical')
        c = src[i]
        if c == q:
            return i + 1, bytes(out)
        if c == '\\':
            if i + 1 >= n:
                raise CError('bad escape', where, 'lexical')
            e = src[i + 1]
            if e in ESC:
                out.append(ESC[e])
                i += 2
            elif e == 'x':
                h = src[i + 2:i + 4]
                if len(h) != 2 or any(ch not in '0123456789abcdefABCDEF' for ch in h):
                    raise CError('\\x needs two hex digits', where, 'lexical')
                out.append(int(h, 16))
                i += 4
            else:
                raise CError('unknown escape \\%s' % e, where, 'lexical')
            continue
        if not (c == '\t' or ' ' <= c <= '~'):
            raise CError('non-ASCII or control byte in literal', where, 'lexical')
        out.append(ord(c))
        i += 1


def _number(text, where, bol):
    t = text
    low = t.lower()
    isfloat = False
    if not low.startswith('0x') and ('.' in t or 'e' in low):
        isfloat = True
    if isfloat:
        body = t[:-1] if t[-1] in 'fF' else t
        import re
        if not re.fullmatch(r'(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?', body) or \
                (body.isdigit()):
            raise CError('malformed number %s' % t, where, 'lexical')
        return Tok('float', body, where[0], where[1], bol, t)
    uns = False
    if t[-1] in 'uU':
        uns = True
        t = t[:-1]
    try:
        if t.lower().startswith('0x'):
            if len(t) == 2:
                raise ValueError
            v = int(t[2:], 16)
        elif len(t) > 1 and t[0] == '0':
            v = int(t[1:], 8)
        else:
            if not t.isdigit():
                raise ValueError
            v = int(t, 10)
    except ValueError:
        raise CError('malformed number %s' % text, where, 'lexical')
    if v > 65535:
        raise CError('integer literal out of range', where, 'literal-range')
    ty = 'unsigned int' if uns or v > 32767 else 'int'
    return Tok('int', (v, ty), where[0], where[1], bol, text)


# <c48.h>: the library's prototypes (sdk/include/c48.h) — The output had better match its story.
C48_H = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'include', 'c48.h'), 'rb').read()


def preprocess(path, include_dirs=(), _macros=None, _depth=0, src=None):
    """Return the token list of a translation unit after preprocessing."""
    macros = {} if _macros is None else _macros
    if src is None:
        with open(path, 'rb') as f:
            src = f.read()
    info = {}
    toks = lex(src, os.path.basename(path), info)
    out = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.kind == 'hash':
            if not t.bol:
                raise CError("'#' not at start of line", t.where, 'preprocessing')
            j = i + 1
            line = []
            while toks[j].kind != 'eof' and toks[j].line == t.line and not toks[j].bol:
                line.append(toks[j])
                j += 1
            i = j
            if t.line in info['ml_comments']:
                raise CError('block comment crosses the end of the directive line', t.where,
                             'preprocessing')
            if not line or line[0].kind not in ('id', 'kw'):
                raise CError('bad directive', t.where, 'preprocessing')
            d = line[0].val
            if d == 'include':
                if len(line) == 2 and line[1].kind == 'str':
                    if _depth >= 1:
                        raise CError('nested local include', t.where, 'preprocessing')
                    name = line[1].val.decode()
                    base = os.path.dirname(path)
                    cand = [os.path.join(base, name)] + [os.path.join(d2, name) for d2 in include_dirs]
                    for p in cand:
                        if os.path.exists(p):
                            break
                    else:
                        raise CError('include not found: %s' % name, t.where, 'io')
                    out.extend(preprocess(p, include_dirs, macros, _depth + 1)[:-1])
                elif len(line) >= 2 and line[1].kind == 'op' and line[1].val == '<':
                    # exactly <c48.h>: no space inside the brackets (P0732)
                    if [(x.kind, x.val) for x in line[1:]] != [('op', '<'), ('id', 'c48'), ('op', '.'),
                                                              ('id', 'h'), ('op', '>')] or \
                            any(x.ws for x in line[2:]):
                        raise CError('unknown system header (only <c48.h>)', t.where, 'preprocessing')
                    out.extend(preprocess('c48.h', include_dirs, macros, 1, src=C48_H)[:-1])
                else:
                    raise CError('bad #include', t.where, 'preprocessing')
            elif d == 'define':
                if len(line) >= 3 and line[1].kind == 'id' and line[2].kind == 'op' and \
                        line[2].val == '(' and not line[2].ws:
                    raise CError('function-like macro %s is not supported' % line[1].val, t.where,
                                 'unsupported')
                if len(line) < 3 or line[1].kind != 'id' or not line[1].ws:
                    raise CError('bad #define', t.where, 'preprocessing')
                if not line[2].ws:
                    raise CError('#define needs white space between the name and its value', t.where,
                                 'preprocessing')
                name = line[1].val
                if name.startswith('__') or name == '_start':
                    raise CError('reserved macro name %s' % name, t.where, 'preprocessing')
                if name in RESERVED:
                    raise CError('macro name %s is a reserved keyword' % name, t.where, 'preprocessing')
                rep = []
                for x in line[2:]:
                    if x.kind == 'id':
                        if x.val not in macros:
                            raise CError('macro %s refers to %s' % (name, x.val), x.where, 'preprocessing')
                        rep.extend(macros[x.val])
                    else:
                        rep.append(x)
                # C48 replacements must be complete, compile-time constants. Reuse the
                # language's own typed constant-expression parser instead of accidentally
                # accepting arbitrary source fragments.
                from .parse import Parser
                sentinel = Tok('eof', None, t.file, t.line, False)
                parser = Parser(rep + [sentinel])
                expr = parser.expr()
                if parser.tok.kind != 'eof' or expr.op not in ('num', 'fnum', 'str'):
                    raise CError('macro replacement is not a constant expression',
                                 t.where, 'preprocessing')
                key = [(x.kind, x.val) for x in rep]
                if name in macros and [(x.kind, x.val) for x in macros[name]] != key:
                    raise CError('macro %s redefined' % name, t.where, 'preprocessing')
                macros[name] = rep
            else:
                raise CError('unsupported directive #%s' % d, t.where, 'preprocessing')
            continue
        if t.kind == 'id' and t.val in macros:
            for x in macros[t.val]:
                expanded = Tok(x.kind, x.val, t.file, t.line, False, x.text)
                expanded.column = t.column  # point at the macro invocation
                out.append(expanded)
            i += 1
            continue
        out.append(t)
        i += 1
    return out
