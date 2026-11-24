# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Sound integer scalar specialization for the 48K BASIC code generator.

The host may prove a scalar always integral, but the target still uses the
exact compiled integer semantics. Unknown assignments, aliases and writes
reject an optimization rather than assuming ordinary loop shapes.
"""
from __future__ import annotations

import re
from poke_proof import _line_text
from audit_policy import scrub_code

WRITER = re.compile(r'\b(LET|FOR)\s+([A-Z])(?=\s*[=(])', re.I)
SCALAR = re.compile(r'^\s*(?:LET|FOR)\s+([A-Z])\s*=\s*([+-]?\d+)\s*$', re.I)
LOOP = re.compile(r'^\s*FOR\s+([A-Z])\s*=\s*([+-]?\d+)\s+TO\s+([+-]?\d+)(?:\s+STEP\s+([+-]?\d+))?\s*$', re.I)
UNSAFE = re.compile(r'\b(?:DEF\s+FN|INPUT|READ|DIM|CLEAR|VAL|RANDOMIZE\s+USR)\b', re.I)
VIRTUAL_SYSVARS = frozenset((23609, 23658, 23672, 23673, 23674, 23692))
NAME = re.compile(r'\b([A-Z])\s*\(', re.I)


def _pieces(text):
    # A quoted colon is not a statement boundary. The scrubber retains the executable keyword
    # text and masks inert quoted material.
    masked = scrub_code(text)
    return [x.strip() for x in masked.split(':') if x.strip()]


def infer_integral_scalars(program, keywords, split_lines, available=1, poke_proofs=None):
    """Return directive and proof only where every scalar write is a safe integer."""
    rows = list(split_lines(program))
    if not rows or available < 1:
        return [], []
    text = [_line_text(body, keywords.TOKEN) for _, body in rows]
    if any(UNSAFE.search(scrub_code(line)) for line in text):
        return [], []
    # Writes confined to separately virtualized UDG memory or known private Spectrum system variables
    # cannot alias compiled numeric variable slots.
    if any(re.search(r'\bPOKE\b', scrub_code(line), re.I) for line in text):
        if not poke_proofs or not all(
            proof.get('addresses') and all(
                addr.get('space') == 'process_udg' or
                (addr.get('space') == 'absolute' and
                 addr.get('offset') in VIRTUAL_SYSVARS)
                for addr in proof['addresses'])
            for proof in poke_proofs):
            return [], []
    allowed = {}
    rejected = set()
    for line in text:
        for statement in _pieces(line):
            for m in WRITER.finditer(statement):
                var = m[2].lower()
                # A matching LET/FOR embedded inside IF THEN would need an entirely
                # separate control-flow proof.
                if statement[:m.start()].strip():
                    rejected.add(var)
                    continue
                let = SCALAR.fullmatch(statement)
                loop = LOOP.fullmatch(statement)
                if let and let[1].lower() == var:
                    values = [int(let[2])]
                elif loop and loop[1].lower() == var:
                    begin, end = int(loop[2]), int(loop[3])
                    step = int(loop[4]) if loop[4] else 1
                    if step == 0 or (end-begin)*step < 0:
                        rejected.add(var)
                        continue
                    values = [begin, end, end+step]
                else:
                    rejected.add(var)
                    continue
                if any(abs(x) > 30000 for x in values):
                    rejected.add(var)
                    continue
                allowed.setdefault(var, 0)
                allowed[var] += 1
    # Indexed arrays with the same name and partially parsed write sites are conservatively
    # incompatible with a scalar type specialization.
    for line in text:
        rejected.update(x.lower() for x in NAME.findall(scrub_code(line)))
    eligible = sorted(set(allowed) - rejected)
    if not eligible:
        return [], []
    return ['INT ' + ','.join(eligible)], [
        {'variable': v, 'writes_proved_integral': allowed[v]} for v in eligible
    ]
