# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Join independently sourced runtime emitters to original HiSoft events.

The caller supplies typed runtime statements and actual Z80 writer-PC traces.
This bridge does not decode compiled bytes, infer statements from machine code,
or turn an untyped vendor routine into an approved optimization candidate.
Every original runtime-opaque event must have exactly one typed witness in
all three compile passes; other compiler source events retain exact ownership.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from runtime_typed_source import RuntimeSourceError, typed_runtime_events
from gate8_original_runtime_types import N_ROUTINES
from runtime_emitter_trace import verify_three_runtime_traces, RuntimeTraceError
from symbolic_emit_sites import inspect_emit_sites, verify_three_emit_sites


class RuntimeBridgeError(ValueError):
    """A runtime source witness does not match its original compiler span."""


@dataclass(frozen=True)
class RuntimeWitness:
    number: int
    start: int
    end: int
    writes: tuple
    statements: tuple


_RT = re.compile(r'RT([1-9][0-9]*)\Z')


def _compare_writer_trace(witness: RuntimeWitness, report: dict) -> None:
    """Match a typed witness against the ORIGINAL machine's write history.

    The digest is made from chronological writer PCs and output offsets,
    never from a disassembled or linked program image. A replacement writer
    list cannot stand in for the compiler's separate source capture.
    """
    if (not isinstance(report, dict) or
            report.get('fully_observed') is not True or
            report.get('routine') != witness.number or
            report.get('output_bytes') != witness.end - witness.start or
            report.get('staging_write_count') != len(witness.writes) or
            report.get('covered_bytes') != witness.end - witness.start or
            report.get('uncovered_bytes') != 0 or
            report.get('changed_after_write') != 0 or
            report.get('rewritten_bytes') != 0 or
            report.get('outside_emitter_bytes') != 0 or
            report.get('untraced_pc_writes') != 0):
        raise RuntimeBridgeError('original runtime trace is incomplete or reordered')
    digest = hashlib.sha256()
    for write in witness.writes:
        position, pc = getattr(write, 'position', None), getattr(write, 'emitter_pc', None)
        if (type(position) is not int or type(pc) is not int or
                not witness.start <= position < witness.end or not 0 <= pc <= 65535):
            raise RuntimeBridgeError('runtime witness has unverified writer PC')
        digest.update(position.to_bytes(2, 'little'))
        digest.update(pc.to_bytes(3, 'little'))
    if report.get('source_write_sites_sha256') != digest.hexdigest():
        raise RuntimeBridgeError('runtime witness differs from original Z80 writer trace')


def witnesses_from_compiler_captures(captures, source_statements):
    """Connect original Z80 write captures with separately supplied statements.

    The source statements are not reconstructed from output bytes. The
    compiler's own runtime trace must agree with every retained writer PC.
    This prepares the existing strict three-pass bridge, not a link pass.
    """
    from symbolic_capture import Capture, CapturedRuntime
    if (len(captures) != 3 or len(source_statements) != 3 or
            any(not isinstance(c, Capture) for c in captures)):
        raise RuntimeBridgeError('three original compiler captures required')
    witness_groups = []
    trace_groups = []
    for capture, source_group in zip(captures, source_statements):
        sources = tuple(source_group)
        records = tuple(capture.runtime_sources)
        reports = tuple(capture.runtime_traces)
        if not records or len(records) != len(reports) or len(sources) != len(records):
            raise RuntimeBridgeError('original runtime capture has missing typed statements')
        witnesses = []
        for record, statements, report in zip(records, sources, reports):
            if (not isinstance(record, CapturedRuntime) or
                    not isinstance(statements, tuple) or not statements):
                raise RuntimeBridgeError('original runtime capture has invalid statements')
            witness = RuntimeWitness(record.number, record.start,
                                     record.end, record.writes, statements)
            _compare_writer_trace(witness, report)
            witnesses.append(witness)
        witness_groups.append(tuple(witnesses))
        trace_groups.append(reports)
    return tuple(witness_groups), tuple(trace_groups)


def splice_three_runtime_sources(events, images, bases, witnesses, assembler,
                                 *, observed_traces):
    """Replace ALL runtime-opaque spans only after a three-base source proof.

    The verification deliberately operates before the existing whole-program
    pipeline: its independent source maps still reject any surviving unknown
    emitter, untraced patch, data boundary or unresolved control target.
    """
    if (observed_traces is None or
            any(len(group) != 3 for group in
                (events, images, witnesses, observed_traces)) or
            len(bases) != 3 or len(set(bases)) != 3 or
            any(type(base) is not int or not 0 <= base <= 0xffff
                for base in bases) or
            any(not isinstance(image, bytes) for image in images)):
        raise RuntimeBridgeError('three valid original source passes required')
    output = []
    signatures = []
    site_groups = []
    totals = []
    for group, image, base, witness_group, reports in zip(
            events, images, bases, witnesses, observed_traces):
        original = tuple(group)
        spans = []
        occupied = set()
        for event in original:
            if event.kind != 'runtime-opaque':
                continue
            match = _RT.fullmatch(event.source)
            if (match is None or not 1 <= int(match.group(1)) <= N_ROUTINES or
                    type(event.position) is not int or
                    not isinstance(event.data, bytes) or not event.data or
                    not 0 <= event.position < event.position + len(event.data) <= len(image) or
                    image[event.position:event.position + len(event.data)] != event.data):
                raise RuntimeBridgeError('unverified original runtime source span')
            start, end = event.position, event.position + len(event.data)
            if occupied.intersection(range(start, end)):
                raise RuntimeBridgeError('overlapping original runtime spans')
            occupied.update(range(start, end))
            spans.append((int(match.group(1)), start, end))
        if not spans:
            raise RuntimeBridgeError('no original runtime source spans')
        if any(a[0] >= b[0] or a[2] != b[1]
               for a, b in zip(spans, spans[1:])):
            raise RuntimeBridgeError('original runtime ordering or adjacency differs')
        # Any unrelated event overlapping the runtime region is an unverified rewrite, even
        # when it happened to write the same final bytes.
        if any(event.kind != 'runtime-opaque' and
               any(position in occupied for position in
                   range(event.position, event.position + len(event.data)))
               for event in original):
            raise RuntimeBridgeError('original compiler rewrote runtime bytes')
        witness_group = tuple(witness_group)
        reports = tuple(reports)
        if (len(reports) != len(spans) or
                len(witness_group) != len(spans) or
                any(not isinstance(w, RuntimeWitness) or
                    (w.number, w.start, w.end) != expected
                    for w, expected in zip(witness_group, spans))):
            raise RuntimeBridgeError('missing or reordered original runtime witness')
        replacement = {}
        signature = []
        for w, report in zip(witness_group, reports):
            if not isinstance(w.writes, tuple) or not isinstance(w.statements, tuple):
                raise RuntimeBridgeError('runtime producer or source statements missing')
            _compare_writer_trace(w, report)
            try:
                converted = typed_runtime_events(
                    w.writes, w.statements, image[w.start:w.end],
                    w.start, w.end, base, assembler)
            except RuntimeSourceError as exc:
                raise RuntimeBridgeError(f'RT{w.number}: {exc}') from exc
            replacement[(w.number, w.start, w.end)] = converted
            # Writer PC, source opcode and typed relocation target are stable. Relocated output bytes
            # themselves depend on the compilation base.
            signature.append((w.number, w.start, w.end,
                              tuple((s.position, s.emitter_pc, s.kind, s.source,
                                     s.symbol_offset, s.write_pcs)
                                    for s in w.statements)))
        converted_events = []
        for event in original:
            if event.kind == 'runtime-opaque':
                key = (int(_RT.fullmatch(event.source).group(1)), event.position,
                       event.position + len(event.data))
                converted_events.extend(replacement[key])
            else:
                converted_events.append(event)
        output.append(tuple(converted_events))
        signatures.append(tuple(signature))
        site_groups.append(inspect_emit_sites(
            item for converted in replacement.values() for item in converted))
        totals.append(sum(w.end - w.start for w in witness_group))
    if signatures[1:] != signatures[:1] * 2 or len(set(totals)) != 1:
        raise RuntimeBridgeError('original runtime typed source varies by compiler base')
    try:
        trace_report = verify_three_runtime_traces(observed_traces, bases)
        site_report = verify_three_emit_sites(site_groups, bases)
    except (RuntimeTraceError, ValueError) as exc:
        raise RuntimeBridgeError('original runtime writer PCs vary by compiler base') from exc
    return tuple(output), {
        'runtime_source_passes': 3,
        'runtime_source_routines': len(signatures[0]),
        'runtime_source_bytes': totals[0],
        'runtime_source_sites': site_report,
        'original_runtime_traces': trace_report,
        'typed_runtime_source_spliced': True,
        'whole_program_optimized': False,
        'native_behavior_verified': False,
    }
