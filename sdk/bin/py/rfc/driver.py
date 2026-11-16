# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
r"""rfc driver: Forth source -> ras-syntax asm -> .sso -> .ssx.

A real (small) indirect-threaded Forth. The runtime (lib/forth_rt.asm) supplies
the inner interpreter, colon mechanism and primitive words; rfc compiles the
source into threaded-code cells (colon definitions plus the @forth_main top
level) and emits one assembly unit, assembled by ras and linked by rld into a
ZX-UX .ssx. No libc48: I/O is the ZX-UX write syscall inside the runtime.

Supported: `: ;` definitions, `variable`, `constant`, signed decimal literals,
`." text"`, `\` and `( )` comments; control flow if/else/then, begin/until,
begin/again, begin/while/repeat, do/loop (with i, j); and a Forth-83-flavoured
core word set (stack ops, arithmetic with floored `/ mod /mod`, comparisons,
logic, memory `@ !`, return stack `>r r> r@`, and console I/O).
Output: -S asm, -c object (.sso), default executable (.ssx).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

# Forth word -> runtime CFA label (see lib/forth_rt.asm).
BUILTINS = {
    'dup': 'fw_dup', 'drop': 'fw_drop', 'swap': 'fw_swap', 'over': 'fw_over',
    'rot': 'fw_rot', 'nip': 'fw_nip',
    '+': 'fw_plus', '-': 'fw_minus', '*': 'fw_star', '/': 'fw_slash',
    'mod': 'fw_mod', '/mod': 'fw_slmod',
    '1+': 'fw_1p', '1-': 'fw_1m', 'negate': 'fw_neg', 'abs': 'fw_abs',
    '2*': 'fw_2s', '2/': 'fw_2d',
    '=': 'fw_eq', '<': 'fw_lt', '>': 'fw_gt', '0=': 'fw_zeq', '0<': 'fw_zlt',
    'and': 'fw_and', 'or': 'fw_or', 'xor': 'fw_xor', 'invert': 'fw_inv',
    '@': 'fw_fetch', '!': 'fw_store',
    '>r': 'fw_tor', 'r>': 'fw_fromr', 'r@': 'fw_rat',
    '2dup': 'fw_2dup', '2drop': 'fw_2drop', '?dup': 'fw_qdup',
    'min': 'fw_min', 'max': 'fw_max',
    'space': 'fw_space', 'spaces': 'fw_spaces', 'type': 'fw_type',
    'c@': 'fw_cfetch', 'c!': 'fw_cstore', '+!': 'fw_plusstore',
    '2swap': 'fw_2swap', '2over': 'fw_2over', 'pick': 'fw_pick', 'depth': 'fw_depth',
    'u<': 'fw_ult', '0>': 'fw_zgt',
    'u.': 'fw_udot', 'base': 'fw_base', 'hex': 'fw_hex', 'decimal': 'fw_decimal',
    'um*': 'fw_umstar', 'um/mod': 'fw_umslashmod',
    'd+': 'fw_dplus', 'd-': 'fw_dminus', 'd0=': 'fw_dzeq',
    'd=': 'fw_deq', 'du<': 'fw_dult',
    'execute': 'fw_execute', 'fill': 'fw_fill', 'cmove': 'fw_cmove',
    'cmove>': 'fw_cmovep', 'count': 'fw_count',
    '<#': 'fw_numstart', '#': 'fw_hashnum', '#>': 'fw_numend',
    'hold': 'fw_hold', 'sign': 'fw_sign', '.r': 'fw_dotr', 'u.r': 'fw_udotr',
    'roll': 'fw_roll', '-trailing': 'fw_dashtrail',
    'here': 'fw_here', ',': 'fw_comma', 'c,': 'fw_ccomma', 'allot': 'fw_allot',
    'state': 'fw_state', 'find': 'fw_find', 'word': 'fw_word',
    'number?': 'fw_number', 'tib': 'fw_tib', '#tib': 'fw_numtib',
    '>in': 'fw_toin', 'span': 'fw_span',
    '.': 'fw_dot', 'cr': 'fw_cr', 'emit': 'fw_emit', 'key': 'fw_key',
    'i': 'fw_i', 'j': 'fw_j', 'bye': 'fw_bye',
    'exit': 'fw_exit',
}

# Derived words defined in Forth and compiled ahead of every program.
PRELUDE = """
: 2+ 2 + ;
: 2- 2 - ;
: 2@ dup 2+ @ swap @ ;
: 2! swap over ! 2+ ! ;
: <> = invert ;
: 0<> 0= invert ;
variable rfc-sma variable rfc-smb variable rfc-smdiv
variable rfc-smd variable rfc-smps variable rfc-smqs
variable rfc-smr variable rfc-smq
: */mod
  >r
  r> dup 0< rfc-smd ! abs rfc-smdiv !
  rfc-smb ! rfc-sma !
  rfc-sma @ 0< rfc-smb @ 0< xor rfc-smps !
  rfc-sma @ abs rfc-sma ! rfc-smb @ abs rfc-smb !
  rfc-sma @ rfc-smb @ um* rfc-smdiv @ um/mod
  rfc-smq ! rfc-smr !
  rfc-smps @ rfc-smd @ xor rfc-smqs !
  rfc-smr @ 0= if
    rfc-smq @ rfc-smqs @ if negate then
    0 swap
  else
    rfc-smqs @ if
      rfc-smdiv @ rfc-smr @ -
      rfc-smd @ if negate then
      rfc-smq @ negate 1-
    else
      rfc-smr @ rfc-smd @ if negate then
      rfc-smq @
    then
  then ;
: */ */mod nip ;
: cells 2* ;
: cell+ 2+ ;
: #s begin # 2dup or 0= until ;
32 constant bl
"""

# `/`, `mod`, `/mod` are Forth-83 FLOORED signed division (remainder takes the divisor's sign).
# Division by zero is undefined (not guarded).


class ForthError(Exception):
    pass


def sdk_dir():
    """Use the adjacent source or packaged SDK; no reference checkout."""
    sibling = os.path.dirname(_HERE)
    sdk = os.environ.get('ZXUX_SDK', sibling)
    if not all(os.path.isfile(os.path.join(sdk, n))
               for n in ('ras.py', 'rld.py', 'rtap.py')):
        raise ForthError('missing adjacent ZX-UX SDK (ras/rld/rtap)')
    return sdk


def runtime_asm():
    with open(os.path.join(os.path.dirname(_HERE), 'lib', 'forth_rt.asm'),
              encoding='utf-8') as stream:
        return stream.read()


def source_text(path):
    """Read ordinary Forth text or a traditional 1024-byte screen-block file.

    F83 and related systems store sixteen fixed 64-column lines per screen.
    Restore line endings before tokenising so that ``\\`` comments preserve
    their conventional line scope.  Other inputs remain UTF-8 text.
    """
    if os.path.splitext(os.fspath(path))[1].lower() != '.blk':
        with open(path, encoding='utf-8') as stream:
            return stream.read()
    with open(path, 'rb') as stream:
        data = stream.read()
    if len(data) % 1024:
        raise ForthError('%s: screen-block file length is not a multiple of 1024' % path)
    return '\n'.join(data[i:i + 64].decode('latin-1')
                     for i in range(0, len(data), 64)) + '\n'


def tokenize(text):
    """Yield tokens: ('word', s), ('str', s), ':' and ';' as ('word', ...).
    Handles \\ line comments, ( ) comments, and ." strings."""
    toks = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ' \t\r\n':
            i += 1
            continue
        if c == '\\':
            while i < n and text[i] != '\n':
                i += 1
            continue
        j = i
        while j < n and text[j] not in ' \t\r\n':
            j += 1
        word = text[i:j]
        if word == '(':
            close = text.find(')', j)
            if close < 0:
                raise ForthError('unterminated ( comment')
            i = close + 1
            continue
        if word == '."':
            start = j + 1 if j < n and text[j] == ' ' else j
            close = text.find('"', start)
            if close < 0:
                raise ForthError('unterminated ." string')
            toks.append(('str', text[start:close]))
            i = close + 1
            continue
        toks.append(('word', word))
        i = j
    return toks


def _as_number(word):
    body = word[1:] if word.startswith('-') else word
    if not body or not all('0' <= ch <= '9' for ch in body):
        return None
    return int(word, 10)


def compile_to_asm(text):
    toks = tokenize(PRELUDE + '\n' + text)
    defs = []            # asm lines for definitions (colon words, variables, constants)
    main = []            # thread cells for @forth_main
    words = {}           # forth name -> cfa label
    constants = {}       # forth name -> compile-time cell value
    cf = []              # control-flow stack: (kind, label)
    target = main        # where cells currently go
    cur_name = None
    cur_body = None
    counters = {'uw': 0, 'lbl': 0}

    def newuw():
        counters['uw'] += 1
        return 'uw%d' % counters['uw']

    def newlbl():
        counters['lbl'] += 1
        return 'L%d' % counters['lbl']

    def emit(line):
        target.append(line)

    def emit_lit(value):
        target.append('\tdw fw_lit')
        target.append('\tdw %d' % (value & 0xFFFF))

    def emit_str(s):
        data = s.encode('latin-1', 'replace')
        if len(data) > 255:
            raise ForthError('string literal too long')
        target.append('\tdw fw_dotstr')
        target.append('\tdb ' + ','.join([str(len(data))] + [str(b) for b in data]))

    def define_array(name, count, cell_bytes):
        """Define ``count array name`` or ``count 2array name`` statically."""
        if count < 0:
            raise ForthError('array size must not be negative')
        data, lab = newuw(), newuw()
        words[name] = lab
        defs.append(data + ':')
        if count:
            defs.append('\tds %d' % (count * cell_bytes))
        defs.extend([lab + ':', '\tdw docol'])
        for _ in range(1 if cell_bytes == 2 else 2):
            defs.append('\tdw fw_2s')
        defs.extend(['\tdw fw_lit', '\tdw ' + data, '\tdw fw_plus', '\tdw fw_exit'])

    i, n = 0, len(toks)
    while i < n:
        kind, val = toks[i]
        if kind == 'str':
            emit_str(val)
            i += 1
            continue
        key = val.lower()

        if key == ':':
            if cur_name is not None:
                raise ForthError('nested : definition')
            if i + 1 >= n or toks[i + 1][0] != 'word':
                raise ForthError(': without a name')
            cur_name = toks[i + 1][1].lower()
            words[cur_name] = newuw()
            cur_body = []
            target = cur_body
            i += 2
            continue
        if key == ';':
            if cur_name is None:
                raise ForthError('; without :')
            defs.extend(['%s:' % words[cur_name], '\tdw docol'] + cur_body + ['\tdw fw_exit'])
            cur_name, cur_body, target = None, None, main
            i += 1
            continue
        if key == 'recurse':
            if cur_name is None:
                raise ForthError('recurse outside a colon definition')
            emit('\tdw ' + words[cur_name])
            i += 1
            continue
        if key in ('variable', '2variable'):
            if i + 1 >= n or toks[i + 1][0] != 'word':
                raise ForthError('variable without a name')
            lab = newuw()
            words[toks[i + 1][1].lower()] = lab
            defs.extend(['%s:' % lab, '\tdw dovar_c', '\tdw 0'])
            if key == '2variable':
                defs.append('\tdw 0')
            i += 2
            continue
        if key in ('char', '[char]'):
            if i + 1 >= n or toks[i + 1][0] != 'word':
                raise ForthError('%s needs a character' % key)
            emit_lit(ord(toks[i + 1][1][0]))
            i += 2
            continue
        if key in ("'", "[']"):
            if i + 1 >= n or toks[i + 1][0] != 'word':
                raise ForthError('%s needs a word' % key)
            w = toks[i + 1][1].lower()
            lab = BUILTINS.get(w) or words.get(w)
            if lab is None:
                raise ForthError('%s: unknown word %r' % (key, w))
            emit('\tdw fw_lit')
            emit('\tdw ' + lab)
            i += 2
            continue
        if key == 'create':
            if i + 1 >= n or toks[i + 1][0] != 'word':
                raise ForthError('create needs a name')
            lab = newuw()
            words[toks[i + 1][1].lower()] = lab
            defs.extend(['%s:' % lab, '\tdw dovar_c'])
            i += 2
            # consume any immediately-following data-space init (N , | N c, | N allot | N cells allot)
            # -- the common create-a-buffer/table idiom.
            while i < n and toks[i][0] == 'word':
                num = _as_number(toks[i][1].lower())
                if num is None:
                    num = constants.get(toks[i][1].lower())
                if num is None or i + 1 >= n:
                    break
                nxt = toks[i + 1][1].lower() if toks[i + 1][0] == 'word' else None
                if nxt == ',':
                    defs.append('\tdw %d' % (num & 0xFFFF)); i += 2; continue
                if nxt == 'c,':
                    defs.append('\tdb %d' % (num & 0xFF)); i += 2; continue
                if nxt == 'allot':
                    if num > 0:
                        defs.append('\tds %d' % num)
                    i += 2; continue
                if (nxt == 'cells' and i + 2 < n and toks[i + 2][0] == 'word'
                        and toks[i + 2][1].lower() == 'allot'):
                    if num > 0:
                        defs.append('\tds %d' % (num * 2))
                    i += 3; continue
                break
            continue

        # control flow (compile-time structure words)
        if key == 'if':
            L = newlbl(); emit('\tdw fw_zbranch'); emit('\tdw ' + L); cf.append(('if', L)); i += 1; continue
        if key == 'else':
            if not cf or cf[-1][0] != 'if':
                raise ForthError('else without if')
            L = cf.pop()[1]; Lend = newlbl()
            emit('\tdw fw_branch'); emit('\tdw ' + Lend); emit(L + ':'); cf.append(('else', Lend)); i += 1; continue
        if key == 'then':
            if not cf or cf[-1][0] not in ('if', 'else'):
                raise ForthError('then without if')
            emit(cf.pop()[1] + ':'); i += 1; continue
        if key == 'begin':
            L = newlbl(); emit(L + ':'); cf.append(('begin', L)); i += 1; continue
        if key == 'until':
            if not cf or cf[-1][0] != 'begin':
                raise ForthError('until without begin')
            emit('\tdw fw_zbranch'); emit('\tdw ' + cf.pop()[1]); i += 1; continue
        if key == 'again':
            if not cf or cf[-1][0] != 'begin':
                raise ForthError('again without begin')
            emit('\tdw fw_branch'); emit('\tdw ' + cf.pop()[1]); i += 1; continue
        if key == 'while':
            if not cf or cf[-1][0] != 'begin':
                raise ForthError('while without begin')
            Lw = newlbl(); emit('\tdw fw_zbranch'); emit('\tdw ' + Lw); cf.append(('while', Lw)); i += 1; continue
        if key == 'repeat':
            if not cf or cf[-1][0] != 'while':
                raise ForthError('repeat without while')
            Lw = cf.pop()[1]
            if not cf or cf[-1][0] != 'begin':
                raise ForthError('repeat without begin')
            emit('\tdw fw_branch'); emit('\tdw ' + cf.pop()[1]); emit(Lw + ':'); i += 1; continue
        if key in ('do', '?do'):
            Ls = newlbl(); Lx = newlbl()
            if key == '?do':
                Ldo = newlbl()
                emit('\tdw fw_2dup'); emit('\tdw fw_eq')
                emit('\tdw fw_zbranch'); emit('\tdw ' + Ldo)
                emit('\tdw fw_2drop'); emit('\tdw fw_branch'); emit('\tdw ' + Lx)
                emit(Ldo + ':')
            emit('\tdw fw_pdo'); emit(Ls + ':'); cf.append(('do', Ls, Lx)); i += 1; continue
        if key in ('loop', '+loop'):
            if not cf or cf[-1][0] != 'do':
                raise ForthError('%s without do' % key)
            _, Ls, Lx = cf.pop()
            emit('\tdw ' + ('fw_ploop' if key == 'loop' else 'fw_pplusloop'))
            emit('\tdw ' + Ls)
            emit(Lx + ':')
            i += 1
            continue
        if key == 'leave':
            doent = next((e for e in reversed(cf) if e[0] == 'do'), None)
            if doent is None:
                raise ForthError('leave without do')
            emit('\tdw fw_leave'); emit('\tdw ' + doent[2]); i += 1; continue

        if key in words:
            emit('\tdw ' + words[key]); i += 1; continue
        if key in BUILTINS:
            emit('\tdw ' + BUILTINS[key]); i += 1; continue

        num = _as_number(key)
        if num is None:
            num = constants.get(key)
        if num is not None:
            if (i + 2 < n and toks[i + 1][0] == 'word'
                    and toks[i + 1][1].lower() in ('array', '2array')
                    and toks[i + 2][0] == 'word'):
                define_array(toks[i + 2][1].lower(), num,
                             2 if toks[i + 1][1].lower() == 'array' else 4)
                i += 3
                continue
            if (i + 1 < n and toks[i + 1][0] == 'word'
                    and toks[i + 1][1].lower() == 'constant'):
                if i + 2 >= n or toks[i + 2][0] != 'word':
                    raise ForthError('constant without a name')
                lab = newuw()
                name = toks[i + 2][1].lower()
                words[name] = lab
                constants[name] = num
                defs.extend(['%s:' % lab, '\tdw docon_c', '\tdw %d' % (num & 0xFFFF)])
                i += 3
                continue
            emit_lit(num); i += 1; continue

        raise ForthError('unknown word: %r' % val)

    if cur_name is not None:
        raise ForthError('missing ; at end of input')
    if cf:
        raise ForthError('unbalanced control structure: %s' % cf[-1][0])

    out = [runtime_asm(), '\tsection text', '; ---- definitions ----']
    out.extend(defs)
    out.append('; ---- top level ----')
    out.append('\tglobal @forth_main')
    out.append('@forth_main:')
    out.extend(main)
    out.append('\tdw fw_bye')
    # dictionary: a linked list of name headers (link, flags+len, name, cfa) so find / '
    # / the interpreter can resolve words at run time.  Built-ins first, then user words
    # (newer -> found first, so user words shadow).
    out.append('; ---- dictionary ----')
    dictwords = list(BUILTINS.items()) + list(words.items())
    prev = '0'
    for k, (nm, lab) in enumerate(dictwords):
        data = nm.encode('latin-1', 'replace')
        out.append('hdr%d:' % k)
        out.append('\tdw %s' % prev)
        out.append('\tdb %d' % (len(data) & 0x3F))
        out.append('\tdb ' + ','.join(str(b) for b in data))
        out.append('\tdw %s' % lab)
        prev = 'hdr%d' % k
    out.append('\tglobal @latest0')
    out.append('@latest0:')
    out.append('\tdw %s' % prev)
    return '\n'.join(out) + '\n'


def build(src_path, mode='ssx', stack=512, sdk=None):
    """mode: 'asm' (-S) -> asm text; 'obj' (-c) -> .sso bytes; 'ssx' -> executable."""
    text = compile_to_asm(source_text(src_path))
    if mode == 'asm':
        return text, None
    sdk = os.fspath(sdk) if sdk is not None else sdk_dir()
    if sdk not in sys.path:
        sys.path.insert(0, sdk)
    import ras
    import rld
    base = os.path.splitext(os.path.basename(src_path))[0]
    obj = ras.assemble_text(text, base + '.s')
    if mode == 'obj':
        return text, obj
    data = rld.link([rld.Obj(obj, base)], [], 'start', stack, 0)[0]
    return text, data


def main(argv=None):
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description='rfc: ZX-UX native Forth compiler')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('-S', action='store_true', help='emit Z80 assembly')
    modes.add_argument('-c', action='store_true', help='emit SSO1 relocatable object')
    parser.add_argument('-o', '--output', type=Path)
    parser.add_argument('--stack', type=lambda x: int(x, 0), default=512)
    parser.add_argument('--tzx', action='store_true', help='emit SSX and ZX-UX TZX')
    parser.add_argument('source', type=Path)
    args = parser.parse_args(argv)
    if args.tzx and (args.S or args.c):
        parser.error('--tzx requires linked SSX output')
    if not 1 <= args.stack <= 65535:
        parser.error('--stack must be in 1..65535')
    source = args.source.resolve()
    if not source.is_file() or source.suffix.lower() != '.fth':
        parser.error('requires an existing .fth source')
    mode = 'asm' if args.S else 'obj' if args.c else 'ssx'
    out = (args.output or source.with_suffix(
        '.s' if args.S else '.sso' if args.c else '.ssx')).resolve()
    if out == source:
        parser.error('cannot overwrite source')
    if args.tzx and (not 1 <= len(source.stem) <= 10 or not source.stem.isascii()):
        parser.error('cassette program name must be 1..10 ASCII characters')
    try:
        text, data = build(source, mode=mode, stack=args.stack)
        tape = None
        if mode == 'ssx':
            import rld, rtap
            rld.parse_ssx(data)
            if rtap.need(data) > 14000:
                raise ForthError('exceeds ZX-UX 14000-byte program limit')
            if args.tzx:
                title = ('ZX-UX Forth ' + source.stem).encode('ascii')
                head = b'ZXTape!\x1a\x01\x14' + bytes((0x30, len(title))) + title
                tape = (head, rtap.records(data, source.stem))
        out.parent.mkdir(parents=True, exist_ok=True)
        if mode == 'asm':
            out.write_text(text, encoding='utf-8')
        else:
            out.write_bytes(data)
        if tape is not None:
            import rtap
            rtap.write(str(out.with_suffix('.tzx')), tape[0],
                       [(1000, tape[1][0]), (2000, tape[1][1])])
        return 0
    except Exception as exc:
        print('rfc: %s: %s' % (type(exc).__name__, exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
