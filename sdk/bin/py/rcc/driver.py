# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""rcc driver: C48 source -> asm -> SSO1 -> SSX1."""
import os
import sys
from .lex import preprocess, CError
from .diagnostics import emit, emit_error, emit_tool_error
from .parse import parse
from . import z80gen, bcgen
from .fit import FitError, find_smallest
from .auto import recursive_stack, udg_slots

SDK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SDK)


def compile_to_asm(path, opts=None):
    opts = opts or {}
    toks = preprocess(path)
    prog = parse(toks, lib=opts.get('lib', False))
    if opts.get('module'):
        opts = dict(opts, short=None)       # the library's full table has every form
    if not opts.get('lib') and opts.get('udgs') is None:
        opts = dict(opts, udgs=udg_slots(prog))
    if opts.get('bytecode') and 'short' not in opts:
        # first pass: which short forms are used often enough to keep
        g = bcgen.BGen(prog, dict(opts))
        g.generate()
        uses = getattr(g, 'short_uses', {})
        opts = dict(opts, short=bcgen.short_allowed(uses))
        prog = parse(preprocess(path), lib=opts.get('lib', False))
    g = bcgen.BGen(prog, opts) if opts.get('bytecode') else z80gen.Gen(prog, opts)
    text = g.generate()
    text = z80gen.peephole(text)
    if not opts.get('lib') and not opts.get('module') and '_udg_' in text:
        # the UDG bank: 32 slots, or --udgs N (slots 0..N-1)
        n = opts.get('udgs') or 32
        text += ('\tsection data\n\tglobal @nudg\n@nudg:\tdb %d\n'
                 '\tsection bss\n\tglobal @udgs\n@udgs:\tds %d\n' % (n, 8 * n))
    return text, prog, g


# memory a program loaded from cassette can have on ZX-UX 2.0 (from a fresh login: the
# arena less init's and sh's images, plus the lent window); a program whose native
# code needs more is built in bytecode (SSB1).
ZXUX_MAX = 14000


def stack_estimate(g):
    """Bytes of stack the program needs: the deepest chain of frames
    (bytecode functions keep their locals on the stack), at least 384;
    a recursive program gets 1024 more."""
    funcs = g.funcs
    memo = {}

    def depth(f, path):
        if f in memo:
            return memo[f]
        if f in path:
            return 0
        F = funcs[f]
        own = 24 + 2 * max(len(f.params) - 1, 0)
        if f in getattr(g, 'bc', ()):
            own += F.frame + 10
        sub = 0
        for c in f.calls:
            if c in funcs:
                sub = max(sub, depth(c, path | {f}))
        memo[f] = own + sub
        return memo[f]
    d = max((depth(f, frozenset()) for f in funcs), default=0) + 160
    rec = any(F.recursive for f, F in funcs.items() if f not in getattr(g, 'bc', ()))
    rec = rec or any(f in f.calls or any(f in c.calls for c in f.calls if c in funcs) for f in funcs)
    if rec or any(g.scc_of.get(f, (f,)) != (f,) for f in funcs):
        bound = recursive_stack(g)
        return bound if bound is not None else max(1024, d + 512)
    return max(384, (d + 15) & ~15)


def build(src, opts):
    """Compile and link src -> (SSX1 bytes, generator, sizes)."""
    import ras
    import rld
    text, prog, g = compile_to_asm(src, opts)
    base = os.path.splitext(src)[0]
    obj = ras.assemble_text(text, os.path.basename(base) + '.s')
    libp = os.path.join(SDK, 'lib', 'libc48.ssa')
    objs = [rld.Obj(obj, base)]
    # A C48 source may have a matching application assembly companion.  Link
    # it automatically as a normal translation-unit input, not as a release
    # builder or executable-name special case. No silent swaps while packing.
    companion = os.path.splitext(src)[0] + '.asm'
    if os.path.isfile(companion):
        with open(companion, encoding='utf-8') as stream:
            companion_text = stream.read()
        companion_obj = ras.assemble_text(companion_text, os.path.basename(companion))
        objs.append(rld.Obj(companion_obj, companion))
    with open(libp, 'rb') as stream:
        arcs = [rld.read_archive(stream.read(), libp)]
    stack = opts.get('stack')
    if stack is None:
        stack = stack_estimate(g)
        # Calls implemented in external assembly have opaque stack depth. Never claim a proved
        # C call-depth bound covers arbitrary ASM.
        if os.path.isfile(companion):
            stack = max(stack, 800)
    data, bss, ent, gaddr, chosen = rld.link(objs, arcs, 'start', stack, 0)
    h = rld.parse_ssx(data)
    need = max(len(h['image']) + h['bss'] + h['stack'], len(data))
    return data, g, text, obj, need


def main(argv):
    import ras
    import rld
    out = None
    asm_only = False
    obj_only = False
    lib = False
    stack = None
    udgs = None
    heap = 1024
    mode = None
    fit = True
    limit = ZXUX_MAX
    files = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('-o', '--max', '--stack', '--heap', '--udgs'):
            if i + 1 >= len(argv):
                emit('CLI_MISSING_VALUE', 'Option %s requires a value.' % a)
                return 2
            val = argv[i + 1]
            if a == '-o':
                out = val
            else:
                try:
                    num = int(val, 0)
                except ValueError:
                    emit('CLI_INVALID_NUMBER', 'Option %s requires a valid numeric value; received %s.' % (a, val))
                    return 2
                if num < 0:
                    emit('CLI_NEGATIVE_VALUE', 'Option %s does not accept a negative value.' % a)
                    return 2
                if a == '--max':
                    limit = num
                elif a == '--stack':
                    stack = num
                elif a == '--heap':
                    heap = num
                else:
                    if not 4 <= num <= 32:
                        emit('CLI_UDG_RANGE', 'UDG count must be between 4 and 32.')
                        return 2
                    udgs = num
            i += 2
            continue
        if a in ('-S', '-c'):
            if (a == '-S' and obj_only) or (a == '-c' and asm_only):
                emit('CLI_OUTPUT_CONFLICT', 'Requested compiler output modes conflict.')
                return 2
            asm_only |= a == '-S'
            obj_only |= a == '-c'
        elif a == '--fit':
            fit = True
        elif a == '--no-fit':
            fit = False
        elif a in ('--bytecode', '--native'):
            selected = 'all' if a == '--bytecode' else 'none'
            if mode is not None and mode != selected:
                emit('CLI_BACKEND_CONFLICT', 'Native and bytecode backend selections conflict.')
                return 2
            mode = selected
        else:
            files.append(a)
        i += 1
    if mode is not None or asm_only or obj_only:
        if fit and '--fit' in argv:
            emit('CLI_FIT_CONFLICT', 'Explicit --fit requires linked output without a forced backend.')
            return 2
        fit = False
    if len(files) != 1:
        emit('CLI_ARGUMENTS', 'Expected exactly one C48 source filename; usage: rcc [-S|-c] [-o out] [--bytecode|--native|--fit|--no-fit] [--max BYTES] [--stack N] [--heap N] [--udgs N] file.c')
        return 2
    src = files[0]
    base = os.path.splitext(src)[0]
    target = out or base + ('.s' if asm_only else '.sso' if obj_only else '.ssx')
    if os.path.exists(target) and os.path.exists(src) and os.path.samefile(target, src):
        emit('IO_OUTPUT_OVERWRITE', 'Output %s would overwrite the original C48 source file.' % target)
        return 2
    if not os.path.isfile(src):
        emit('IO_SOURCE_MISSING', 'C48 source file %s does not exist or cannot be read.' % src)
        return 1
    opts = {'lib': lib, 'heap': heap, 'stack': stack, 'udgs': udgs, 'module': obj_only}
    if mode == 'all':
        opts['bytecode'] = 'all'
    try:
        if asm_only or obj_only:
            text, prog, g = compile_to_asm(src, opts)
            if asm_only:
                return write_out(target, text.encode())
            obj = ras.assemble_text(text, os.path.basename(base) + '.s')
            return write_out(target, obj)
        if fit:
            # Full measured fitting is the ordinary linked-output behavior. An explicit
            # --fit remains an alias; it gets the same measured result.
            (data, g, text, obj, need), trials, chosen = find_smallest(
                src, opts, build, max_candidates=128, max_passes=3)
        else:
            data, g, text, obj, need = build(src, opts)
        if not fit and mode is None and limit and need > limit:
            # too big for native code: bytecode (SSB1) for what it can
            opts['bytecode'] = 'all'
            data2, g2, text2, obj2, need2 = build(src, opts)
            if need2 < need:
                data, need = data2, need2
    except AssertionError as e:
        emit('GEN_INTERNAL', 'Internal code generation failure: %s' % e, source=src)
        return 3
    except FitError as e:
        emit('FIT_SEARCH_CONFIGURATION', 'Compiler fitting search failed: %s' % e)
        return 1
    except CError as e:
        emit_error(e, src)
        return 1
    except ras.AsmError as e:
        emit_tool_error('ASM', e)
        return 3
    except rld.LinkError as e:
        emit_tool_error('LNK', e)
        return 1
    if limit and need > limit:
        emit('FIT_MEMORY_LIMIT', 'Executable requires %d bytes of memory; configured compile limit is %d bytes.' % (need, limit), source=src)
        return 1
    return write_out(target, data)


def write_out(path, data):
    """Write the output file; status 1 (and no partial file) on failure."""
    try:
        with open(path, 'wb') as f:
            f.write(data)
    except OSError as e:
        emit('IO_OUTPUT_WRITE', 'Compiled output could not be written to %s: %s' % (path, e.strerror or e))
        try:
            os.remove(path)
        except OSError:
            pass
        return 1
    return 0
