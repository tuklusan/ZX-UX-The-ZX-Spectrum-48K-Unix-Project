# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Trace original 48K HiSoft runtime-emitter writes to their executing Z80 PCs.

This is source origin only, not source-level assembly. Runtime instructions remain
opaque until their instruction/data types and relocations are independently
resolved. Never reconstruct missing instructions from the generated binary.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib


class RuntimeTraceError(ValueError):
    """Runtime-emitter output extent or backing machine is invalid."""


@dataclass(frozen=True)
class RuntimeWrite:
    position: int
    value: int
    emitter_pc: int | None


class RuntimeEmitterTrace:
    """Temporarily observe Z80 writes to the original 48K staging region.

    The 48K Z80 interpreter writes target memory through wb(),
    including the ED block-copy instructions and ww(). An existing CPU trace
    hook is chained, and both instance attributes are restored on exit.
    """

    def __init__(self, machine, code_base=None):
        profile = getattr(machine, 'p', {})
        if not profile.get('direct'):
            raise RuntimeTraceError('only the 48K direct runtime is traceable')
        staging = profile.get('staging')
        if not isinstance(staging, int) or not 0 < staging < 65536:
            raise RuntimeTraceError('invalid 48K runtime staging address')
        self.cpu = machine.cpu
        self.staging = staging
        self.writes: list[RuntimeWrite] = []
        self._site = None
        self._old_trace = None
        self._old_wb = None
        self._saved_wb = None
        self._wb_overridden = False
        self.source_roles = None
        # Synthetic Z80 CPU mocks lack the original compiler image. Keep their older diagnostic
        # behavior without declaring type success.
        if code_base is not None:
            from gate8_original_runtime_types import SourceTransactions, HELPER_CODE
            memory = getattr(self.cpu, 'mem', None)
            if (memory is not None and all(memory[p:p + len(raw)] == raw
                                          for p, raw in HELPER_CODE.items())):
                self.source_roles = SourceTransactions(memory, code_base)


    def __enter__(self):
        cpu = self.cpu
        self._old_trace = cpu.trace
        self._old_wb = cpu.wb
        self._wb_overridden = 'wb' in vars(cpu)
        self._saved_wb = vars(cpu).get('wb')

        def trace(pc):
            self._site = pc
            if self.source_roles is not None:
                self.source_roles.step(cpu, pc)
            if self._old_trace is not None:
                self._old_trace(pc)

        def write(address, value):
            addr = address & 65535
            if addr >= self.staging:
                if self.source_roles is not None:
                    if self._site == 0x5d25:
                        self.source_roles.write(cpu, self._site,
                                                addr - self.staging, value & 255)
                    else:
                        # Only original ED block copies are allowed to bypass the numeric
                        # helper. Their source is original ROM or original compiler memory,
                        # never emitted output.
                        source = getattr(cpu, 'hl', None)
                        target = getattr(cpu, 'de', None)
                        memory = getattr(cpu, 'mem', None)
                        if (memory is None or source is None or target is None or
                                memory[self._site] != 0xed or
                                memory[(self._site + 1) & 65535] not in
                                (0xa0, 0xa8, 0xb0, 0xb8) or
                                (target & 65535) != addr or
                                not (source < 16384 or 0x5cf0 <= source < 0x8b5d) or
                                memory[source] != (value & 255)):
                            raise RuntimeTraceError('runtime source writer is untyped')
                self.writes.append(RuntimeWrite(addr - self.staging,
                                                value & 255, self._site))
            return self._old_wb(address, value)

        cpu.trace = trace
        cpu.wb = write
        return self

    def __exit__(self, exc_type, exc, tb):
        cpu = self.cpu
        cpu.trace = self._old_trace
        if self._wb_overridden:
            cpu.wb = self._saved_wb
        else:
            del cpu.wb
        return False

    def inspect(self, start: int, end: int, image: bytes) -> dict:
        if (not isinstance(start, int) or not isinstance(end, int) or
                not 0 <= start <= end or self.staging + end > 65536 or
                not isinstance(image, bytes) or len(image) != end - start):
            raise RuntimeTraceError('runtime output extent differs from staging')
        last = {}
        rewritten = set()
        escaped = []
        for w in self.writes:
            if not start <= w.position < end:
                escaped.append(w.position)
                continue
            if w.position in last:
                rewritten.add(w.position)
            last[w.position] = w
        missing = [p for p in range(start, end) if p not in last]
        changed = [p for p in range(start, end) if p in last and
                   image[p - start] != last[p].value]
        untraced = [w.position for w in self.writes if w.emitter_pc is None]
        classified = self.source_roles.finish() if self.source_roles is not None else ()
        role_counts = {}
        origin_signature = hashlib.sha256()
        for e in classified:
            role_counts[e.kind] = role_counts.get(e.kind, 0) + 1
            origin_signature.update(e.position.to_bytes(2, 'little'))
            origin_signature.update(e.source_site.to_bytes(2, 'little'))
            origin_signature.update(e.helper_pc.to_bytes(2, 'little'))
            origin_signature.update(e.kind.encode('ascii') + b'\0')
            origin_signature.update(((e.target_offset if e.target_offset is not None
                                      else 65536)).to_bytes(3, 'little'))
        sites = hashlib.sha256()
        for write in self.writes:
            sites.update(write.position.to_bytes(2, 'little'))
            sites.update(((write.emitter_pc if write.emitter_pc is not None else 65536)
                          & 0x1ffff).to_bytes(3, 'little'))
        # A changed-after-write count alone is insufficient: two compiler bases can
        # disagree about WHICH output word was mutated while the original writer-PC
        # sequence remains identical. Commit the complete anomaly offsets, not
        # merely the first sixteen diagnostics.
        anomalies = hashlib.sha256()
        for tag, offsets in ((b'M', missing), (b'C', changed),
                             (b'R', sorted(rewritten)), (b'O', escaped),
                             (b'U', untraced)):
            anomalies.update(tag)
            anomalies.update(len(offsets).to_bytes(4, 'little'))
            for offset in offsets:
                anomalies.update(offset.to_bytes(4, 'little'))
        return {
            'output_bytes': end - start,
            'staging_write_count': len(self.writes),
            'covered_bytes': len(last),
            'source_pc_count': len({w.emitter_pc for w in self.writes
                                    if w.emitter_pc is not None}),
            'source_pc_first': sorted({w.emitter_pc for w in self.writes
                                       if w.emitter_pc is not None})[:16],
            'source_write_sites_sha256': sites.hexdigest(),
            'source_anomalies_sha256': anomalies.hexdigest(),
            'uncovered_bytes': len(missing), 'uncovered_first': missing[:16],
            'changed_after_write': len(changed), 'changed_first': changed[:16],
            'rewritten_bytes': len(rewritten),
            'outside_emitter_bytes': len(escaped), 'outside_first': escaped[:16],
            'untraced_pc_writes': len(untraced), 'untraced_first': untraced[:16],
            'fully_observed': not missing and not changed and not escaped and not untraced and not rewritten,
            'typed_instructions': False,
            'source_roles_verified': self.source_roles is not None,
            'typed_calculated_bytes': len(classified),
            'untyped_calculated_bytes': (0 if self.source_roles is not None
                                         else len(self.writes)),
            'calculated_source_roles': role_counts,
            'calculated_source_sites_sha256': origin_signature.hexdigest(),
        }


def verify_three_runtime_traces(groups, bases) -> dict:
    """Check the observed runtime source-PC paths at three native bases.

    Trace identity does not establish typed instructions or optimizer safety.
    """
    if len(groups) != 3 or len(bases) != 3 or len(set(bases)) != 3:
        raise RuntimeTraceError('three distinct runtime compilation bases required')
    signatures = []
    for group in groups:
        signature = tuple((r['routine'], r['output_bytes'], r['staging_write_count'],
                           r['source_write_sites_sha256'],
                           r['source_anomalies_sha256'], r['covered_bytes'],
                           r['uncovered_bytes'], r['changed_after_write'],
                           r['rewritten_bytes'], r['outside_emitter_bytes'],
                           r['untraced_pc_writes'], r['fully_observed'],
                           r.get('source_roles_verified', False),
                           r.get('typed_calculated_bytes', 0),
                           r.get('untyped_calculated_bytes', 0),
                           r.get('calculated_source_sites_sha256', ''))
                          for r in group)
        signatures.append(signature)
    if any(s != signatures[0] for s in signatures[1:]):
        raise RuntimeTraceError('runtime emitter execution sites changed across bases')
    first = groups[0]
    incomplete = tuple({'routine': r['routine'],
                        'output_bytes': r['output_bytes'],
                        'uncovered_bytes': r['uncovered_bytes'],
                        'rewritten_bytes': r['rewritten_bytes'],
                        'changed_after_write': r['changed_after_write'],
                        'outside_emitter_bytes': r['outside_emitter_bytes'],
                        'untraced_pc_writes': r['untraced_pc_writes']}
                       for r in first if not r['fully_observed'])
    return {'runtime_emitter_count': len(first),
            'runtime_source_gaps': incomplete,
            'runtime_write_count': sum(r['staging_write_count'] for r in first),
            'runtime_write_uncovered_bytes': sum(r['uncovered_bytes'] for r in first),
            'runtime_write_changed_bytes': sum(r['changed_after_write'] for r in first),
            'runtime_write_outside_bytes': sum(r['outside_emitter_bytes'] for r in first),
            'runtime_pc_source_count': sum(r['source_pc_count'] for r in first),
            'runtime_typed_calculated_bytes': sum(r.get('typed_calculated_bytes', 0)
                                                 for r in first),
            'runtime_untyped_calculated_bytes': sum(r.get('untyped_calculated_bytes', 0)
                                                   for r in first),
            'runtime_source_roles_verified': all(r.get('source_roles_verified', False)
                                                 for r in first),
            'complete_runtime_symbolic': False}
