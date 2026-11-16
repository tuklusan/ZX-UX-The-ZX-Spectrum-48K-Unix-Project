# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Conservative source-driven storage choices for a linked C48 executable.

Unproved recursion and UDG ranges retain the existing safe reservations.  No
program names or release-builder settings are involved.  Explicit compiler
options take precedence over these bounded deductions.
"""


def expressions(expr):
    if expr is None:
        return
    if isinstance(expr, (list, tuple)):
        for part in expr:
            yield from expressions(part)
    elif expr.__class__.__name__ == 'N':
        yield expr
        yield from expressions(expr.a)
        yield from expressions(expr.b)
        yield from expressions(expr.args)


def statements(stmt):
    if stmt is None:
        return
    if isinstance(stmt, (list, tuple)):
        for part in stmt:
            yield from statements(part)
    elif stmt.__class__.__name__ == 'S':
        yield stmt
        yield from statements(stmt.a)
        yield from statements(stmt.b)
        yield from statements(stmt.c)
        yield from statements(stmt.body)
        yield from statements(stmt.items)


def calls(fn):
    for stmt in statements(fn.body):
        for expr in expressions(stmt.e):
            if expr.op == 'call' and expr.sym is not None:
                yield expr


def isvar(node, param):
    return node is not None and node.op == 'var' and node.sym is param


def integer(node):
    return node.v if node is not None and node.op == 'num' and isinstance(node.v, int) else None


def guaranteed_return(stmt):
    if stmt is None:
        return False
    if stmt.op == 'ret':
        return True
    return stmt.op == 'block' and bool(stmt.items) and guaranteed_return(stmt.items[-1])


def _guard(stmt, param, direction):
    """Recognise a terminating boundary guard, not a mere comparison."""
    if stmt.op != 'if' or stmt.b is not None or not guaranteed_return(stmt.a):
        return None
    x = stmt.e
    if x is None or x.op != 'cmp' or not isvar(x.a, param):
        return None
    value = integer(x.b)
    if direction == '-' and x.v in ('<=', '==') and value == 0:
        return 0
    if direction == '+' and x.v in ('>=', '==') and value is not None:
        return value
    return None


def bounded_self_recursion(program, fn):
    """Return proved recursion levels for simple monotone constant bounds.

    Supports f(n-1) with a terminating n<=0 guard, or f(n+1) with a
    terminating n==LIMIT guard preceding each recursive call.  The first
    argument must be a parameter, never assigned, and every non-recursive
    invocation must pass the same constant.  Anything else is unknown.
    """
    selfcalls = [c for c in calls(fn) if c.sym is fn]
    if not selfcalls or not fn.params:
        return None
    param = fn.params[0]
    if param.addr_taken:
        return None
    directions = set()
    for call in selfcalls:
        if not call.args:
            return None
        e = call.args[0]
        if (e.op != 'bin' or e.v not in ('+', '-') or
                not isvar(e.a, param) or integer(e.b) != 1):
            return None
        directions.add(e.v)
    if len(directions) != 1:
        return None
    direction = next(iter(directions))
    # Do not assume a bound if the controlling parameter is changed.
    for stmt in statements(fn.body):
        for e in expressions(stmt.e):
            if e.op in ('asg', 'inc') and isvar(e.a, param):
                return None
    starts = []
    for other in program.funcs:
        for call in calls(other):
            if call.sym is fn and other is not fn:
                if not call.args or integer(call.args[0]) is None:
                    return None
                starts.append(integer(call.args[0]))
    if not starts or fn.addr_taken:
        return None

    bounds = []
    def visit(node, prior):
        if node is None:
            return True
        if isinstance(node, (list, tuple)):
            local = list(prior)
            for item in node:
                if not visit(item, tuple(local)):
                    return False
                if item.op == 'if':
                    value = _guard(item, param, direction)
                    if value is not None:
                        local.append(value)
            return True
        if node.op == 'block':
            return visit(node.items, prior)
        for e in expressions(node.e):
            if e.op == 'call' and e.sym is fn:
                if not prior:
                    return False
                bounds.append(prior[-1])
        # The branch guards above affect only later statements, not siblings.
        for part in (node.a, node.b, node.c, node.body):
            if part is not None and part.__class__.__name__ == 'S':
                if not visit(part, prior):
                    return False
        return True
    if not visit(fn.body, ()) or len(bounds) != len(selfcalls) or len(set(bounds)) != 1:
        return None
    stop = bounds[0]
    if direction == '-':
        if min(starts) < 0 or max(starts) > 64:
            return None
        levels = max(starts) + 1
    else:
        if min(starts) < 0 or stop < max(starts) or stop > 64:
            return None
        levels = stop - min(starts) + 1
    return levels if 1 <= levels <= 64 else None


def recursive_stack(g):
    """Bound a self-recursive graph when its source gives a finite bound.

    The existing non-recursive longest-chain estimate also remains in effect;
    unknown/mutual recursion falls back to the old conservative estimator.
    """
    funcs = g.funcs
    loops = [s for s in funcs if s in s.calls]
    if not loops or len(loops) != 1:
        return None
    fn = loops[0]
    if any(len(g.scc_of.get(f, (f,))) > 1 for f in funcs):
        return None
    levels = bounded_self_recursion(g.p, fn)
    if levels is None:
        return None
    memo = {}
    def depth(f, path):
        if f in path:
            return 0
        if f in memo:
            return memo[f]
        F = funcs[f]
        own = 24 + 2 * max(len(f.params) - 1, 0)
        if f in getattr(g, 'bc', ()):
            own += F.frame + 10
        children = [depth(c, path | {f}) for c in f.calls if c in funcs]
        result = own + max(children or [0])
        memo[f] = result
        return result
    longest = max((depth(f, frozenset()) for f in funcs), default=0)
    own = 24 + 2 * max(len(fn.params) - 1, 0)
    if fn in getattr(g, 'bc', ()):
        own += funcs[fn].frame + 10
    required = max(384, longest, 16 + levels * own)
    return (required + 15) & ~15


def udg_slots(program):
    """Infer a compact leading glyph bank only with a checked source array.

    A direct define(slot, glyph_array + slot*8) whose array is exactly 16
    glyphs permits 16 slots if every draw is routed through a checked
    <=15 wrapper.  All uncertain forms keep the 32-slot default.
    """
    sites = [(fn, call) for fn in program.funcs for call in calls(fn)
             if call.sym.name in ('udg_define', 'udg_draw', 'udg_draw_2x2')]
    defines = [(fn, c) for fn, c in sites if c.sym.name == 'udg_define']
    if len(defines) != 1 or any(c.sym.name == 'udg_draw_2x2' for _, c in sites):
        return 32
    fn, define = defines[0]
    if len(define.args) != 2 or not fn.params:
        return 32
    param = fn.params[0]
    ptr = define.args[1]
    if not (isvar(define.args[0], param) and ptr.op == 'bin' and ptr.v == '+'):
        return 32
    array, index = ptr.a, ptr.b
    if (array.op != 'addr' or array.a is None or array.a.op != 'var' or
            array.a.sym.ty not in (('a', 'char', 128), ('a', 'uchar', 128)) or
            index.op != 'bin' or index.v != '*' or
            not isvar(index.a, param) or integer(index.b) != 8):
        return 32
    # The definition routine must explicitly reject slots above 15.
    if not _prior_udg_guard(fn, param, 'udg_define', 15):
        return 32
    for caller, draw in sites:
        if draw.sym.name != 'udg_draw':
            continue
        if not draw.args or not caller.params or not isvar(draw.args[0], caller.params[0]):
            return 32
        # Guarded draw wrappers delegate to an in-source checker that rejects high
        # slots before udg_draw sees them. No glyph escapes the check.
        if not _has_checked_draw(caller, program, caller.params[0], 15):
            return 32
    return 16


def _guard_high_slot(stmt, param, limit):
    if stmt.op != 'if' or not guaranteed_return(stmt.a):
        return False
    def contains(e):
        return any(x.op == 'cmp' and x.v == '>' and isvar(x.a, param)
                   and integer(x.b) == limit for x in expressions(e))
    return contains(stmt.e)


def _prior_udg_guard(fn, param, target, limit):
    block = fn.body
    if block.op != 'block':
        return False
    guarded = False
    for stmt in block.items:
        if any(e.op == 'call' and e.sym.name == target
               for e in expressions(stmt.e)):
            return guarded
        if stmt.op == 'if' and _guard_high_slot(stmt, param, limit):
            guarded = True
    return False


def _has_checked_draw(fn, program, param, limit):
    block = fn.body
    if block.op != 'block':
        return False
    for stmt in block.items:
        if any(e.op == 'call' and e.sym.name == 'udg_draw'
               for e in expressions(stmt.e)):
            return False  # The draw preceded any range check.
        if stmt.op != 'if':
            continue
        if not guaranteed_return(stmt.a):
            continue
        cond = stmt.e
        if cond.op != 'not' or cond.a.op != 'call' or cond.a.sym is None:
            continue
        check = cond.a.sym
        if check not in program.funcs or not cond.a.args or not isvar(cond.a.args[0], param):
            continue
        for x in statements(check.body):
            if x.op == 'if' and check.params and _guard_high_slot(x, check.params[0], limit):
                return True
    return False
