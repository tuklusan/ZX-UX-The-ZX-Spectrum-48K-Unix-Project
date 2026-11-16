# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Audit source-level runtime emission roles in the ORIGINAL HiSoft 48K Z80.

Only the vendor compiler tape and ROM are executed.  No output image is
inverse-disassembled.  The original emission helper's instruction address,
register operands, and write instruction establish byte/word/relocation intent.
Three independently executed compiler bases must agree on all source roles.
This does not claim the surrounding copied fragments are typed Z80 instructions.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src/zx-ux-sdk'))
from z80_python.cpu import Z80CPU
from hisoft_frontend_inputs import KNOWN_COMPILER, convert_tzx_to_tap

START, STAGING, TABLE = 0x5CF0, 0x9000, 0x77AF
BASES = (0x6000, 0x5E1E, 0x5D3A)
N_ROUTINES = 131
# Only these captured 48K helper bytes get typed rules. Guesswork stays outside.
HELPER_CODE = {
    0x5D0C: bytes.fromhex('ed 5b 17 45 19 7d cd 16 5d'),
    0x5D11: bytes.fromhex('7d cd 16 5d 7c 4f'),
    0x5D16: bytes.fromhex('4f ed 5b ef 44'),
    0x5D25: bytes.fromhex('71 e1 13 ed 53 ef 44'),
}


class EmitterTypeError(ValueError):
    """The real compiler's output cannot be attributed to typed source helpers."""


@dataclass(frozen=True)
class ProducerByte:
    position: int
    value: int
    kind: str  # byte, word-low/high, reloc-low/high
    source_site: int  # Z80 return-address source site, NOT a decoded output byte
    helper_pc: int
    target_offset: int | None = None


class SourceTransactions:
    """Witness original helper entry operands and match every calculated write."""

    def __init__(self, memory: bytearray, base: int):
        if not 0 <= base <= 65535:
            raise EmitterTypeError('invalid native base')
        for pc, signature in HELPER_CODE.items():
            if memory[pc:pc + len(signature)] != signature:
                raise EmitterTypeError(f'original HiSoft emission helper {pc:04x} differs')
        self.memory = memory
        self.base = base
        self.pending = []
        self.events: list[ProducerByte] = []

    def step(self, cpu, pc: int):
        """Called *before* the actual Z80 instruction, not on output bytes."""
        hl = (cpu.h << 8) | cpu.l
        site = self.memory[cpu.sp] | (self.memory[(cpu.sp + 1) & 65535] << 8)
        if pc == 0x5D0C:  # LD DE,(code-base); ADD HL,DE
            if self.pending:
                raise EmitterTypeError('overlapping typed native word producers')
            value = (hl + self.base) & 65535
            self.pending = [(value & 255, 'reloc-low', site, pc, hl),
                            (value >> 8, 'reloc-high', site, pc, hl)]
        elif pc == 0x5D11 and not self.pending:  # emit HL as an unrelocated word
            self.pending = [(hl & 255, 'word-low', site, pc, None),
                            (hl >> 8, 'word-high', site, pc, None)]
        elif pc == 0x5D16 and not self.pending:  # emit A as an 8-bit source value
            self.pending = [(cpu.a, 'byte', site, pc, None)]

    def write(self, cpu, pc: int, offset: int, value: int):
        if pc != 0x5D25 or not self.pending:
            raise EmitterTypeError('runtime calculated write has no typed Z80 producer')
        expected, kind, source, helper, target = self.pending.pop(0)
        if expected != value or not 0 <= offset < 65536 - STAGING:
            raise EmitterTypeError('original source register disagrees with runtime output')
        self.events.append(ProducerByte(offset, value, kind, source, helper, target))

    def finish(self):
        if self.pending:
            raise EmitterTypeError('runtime source helper did not finish its write')
        return tuple(self.events)


def compiler_image(tzx: bytes) -> bytes:
    tap = convert_tzx_to_tap(tzx)
    offset = 0
    blocks = []
    while offset < len(tap):
        if offset + 2 > len(tap):
            raise EmitterTypeError('truncated original compiler tape')
        size = int.from_bytes(tap[offset:offset + 2], 'little')
        offset += 2
        if size == 0 or offset + size > len(tap):
            raise EmitterTypeError('truncated compiler block')
        blocks.append(tap[offset:offset + size])
        offset += size
    if len(blocks) != 6 or blocks[-1][0] != 255:
        raise EmitterTypeError('original compiler CODE block missing')
    payload = blocks[-1][1:-1]
    if (len(payload) != 11885 or
            hashlib.sha256(payload).hexdigest() != KNOWN_COMPILER):
        raise EmitterTypeError('original compiler binary checksum mismatch')
    return payload


class OriginalEmitter:
    """Execute original HiSoft emitters, capturing *source helper* operations."""

    def __init__(self, code: bytes, rom: bytes, base: int):
        if len(rom) != 16384 or len(code) != 11885:
            raise EmitterTypeError('original 48K ROM/compiler sizes invalid')
        self.original_rom = rom
        self.original_compiler = code
        self.mem = bytearray(65536)
        self.mem[:len(rom)] = rom
        self.mem[START:START + len(code)] = code
        for address, value in ((0x44EF, 0), (0x4517, base), (0x88AE, STAGING)):
            self.mem[address:address + 2] = value.to_bytes(2, 'little')
        self.mem[0x451C] = 0
        self.mem[0x889C] = 0
        self.type_source = SourceTransactions(self.mem, base)
        self.at_pc: int | None = None
        self.writes = []
        self.cpu = Z80CPU(self.mem.__getitem__, self._write)
        self.cpu.mem = self.mem

    def _write(self, address, value):
        address &= 65535
        value &= 255
        if address >= STAGING:
            pc = self.at_pc
            if pc is None:
                raise EmitterTypeError('untraced original emitter operation')
            copied_from = None
            if (self.mem[pc] == 0xED and self.mem[(pc + 1) & 65535]
                    in (0xA0, 0xA8, 0xB0, 0xB8)):
                source = (self.cpu.h << 8) | self.cpu.l
                target = (self.cpu.d << 8) | self.cpu.e
                if target != address or self.mem[source] != value:
                    raise EmitterTypeError('source ROM/compiler copier changed bytes')
                if source < 16384:
                    original = self.original_rom[source]
                elif START <= source < START + 11885:
                    original = self.original_compiler[source - START]
                else:
                    raise EmitterTypeError('copied byte lacks original compiler/ROM source')
                if original != value:
                    raise EmitterTypeError('original source region changed before copy')
                copied_from = source
            else:
                self.type_source.write(self.cpu, pc, address - STAGING, value)
            self.writes.append((address - STAGING, value, copied_from))
        self.mem[address] = value

    def run(self, n: int, max_steps=10000):
        if not 1 <= n <= N_ROUTINES or max_steps <= 0:
            raise EmitterTypeError('invalid runtime emitter or step bound')
        table_at = TABLE + (n - 1) * 2
        entry = int.from_bytes(self.mem[table_at:table_at + 2], 'little')
        if not entry:
            return None
        self.cpu.sp = 0x5A00
        self.cpu._push_word(0xFFFF)
        self.cpu.pc = entry
        for _ in range(max_steps):
            pc = self.cpu.pc
            if pc == 0xFFFF:
                size = int.from_bytes(self.mem[0x44EF:0x44F1], 'little')
                if size > 65536 - STAGING:
                    raise EmitterTypeError('original emitter staging overflow')
                positions = [p for p, _, _ in self.writes]
                if len(positions) != size or sorted(positions) != list(range(size)):
                    raise EmitterTypeError('uncaptured, duplicate, or out-of-range runtime byte')
                if any(self.mem[STAGING + p] != v for p, v, _ in self.writes):
                    raise EmitterTypeError('original output differs from captured source')
                computed = self.type_source.finish()
                if len(computed) + sum(s is not None for _, _, s in self.writes) != size:
                    raise EmitterTypeError('missing copied or calculated source')
                return computed, tuple(self.writes)
            self.at_pc = pc
            self.type_source.step(self.cpu, pc)
            self.cpu.step()
        raise EmitterTypeError('original runtime emitter exceeded step limit')


def audit(tzx: bytes, rom: bytes, bases=BASES):
    if len(bases) != 3 or len(set(bases)) != 3:
        raise EmitterTypeError('three independent code bases required')
    code = compiler_image(tzx)
    runs = []
    for base in bases:
        group = []
        for n in range(1, N_ROUTINES + 1):
            group.append(OriginalEmitter(code, rom, base).run(n))
        runs.append(group)
    counts = Counter()
    sites = set()
    for n in range(N_ROUTINES):
        entries = [r[n] for r in runs]
        if all(item is None for item in entries):
            counts['empty_slots'] += 1
            continue
        if any(item is None for item in entries):
            raise EmitterTypeError('runtime source emitter changed presence across bases')
        source0, writes0 = entries[0]
        for (source, writes), base in zip(entries[1:], bases[1:]):
            if len(source) != len(source0) or len(writes) != len(writes0):
                raise EmitterTypeError(f'RT{n + 1} source length changed with base')
            for first, other in zip(source0, source):
                if ((first.kind, first.position, first.source_site, first.helper_pc,
                     first.target_offset) !=
                    (other.kind, other.position, other.source_site, other.helper_pc,
                     other.target_offset)):
                    raise EmitterTypeError(f'RT{n + 1} original helper source role changed')
                if first.kind.startswith('reloc-'):
                    if other.value != ((other.target_offset + base) >>
                                       (8 if other.kind == 'reloc-high' else 0)) & 255:
                        raise EmitterTypeError(f'RT{n + 1} native relocation changed')
                elif first.value != other.value:
                    raise EmitterTypeError(f'RT{n + 1} supposedly fixed source changed with base')
            for a, b in zip(writes0, writes):
                if a[0] != b[0] or (a[2] is None) != (b[2] is None) or a[2] != b[2]:
                    raise EmitterTypeError(f'RT{n + 1} copied byte origin changed')
                if a[2] is not None and a[1] != b[1]:
                    raise EmitterTypeError(f'RT{n + 1} protected source literal changed')
        counts['runtime_emitters'] += 1
        counts['copied_source_bytes'] += sum(s is not None for _, _, s in writes0)
        for item in source0:
            counts[item.kind] += 1
            sites.add(item.source_site)
        counts['total_output_bytes'] += len(writes0)
    computed = sum(counts[k] for k in ('byte', 'word-low', 'word-high',
                                       'reloc-low', 'reloc-high'))
    if (counts['empty_slots'] + counts['runtime_emitters'] != N_ROUTINES or
            computed + counts['copied_source_bytes'] != counts['total_output_bytes']):
        raise EmitterTypeError('original compiler source ownership incomplete')
    return {'compiler_sha256': KNOWN_COMPILER,
            'native_bases': list(bases),
            'runtime_emitters': counts['runtime_emitters'],
            'empty_slots': counts['empty_slots'],
            'copied_source_bytes': counts['copied_source_bytes'],
            'computed_source_bytes': computed,
            'typed_computed_source_bytes': computed,
            'untyped_computed_source_bytes': 0,
            'literal_byte_bytes': counts['byte'],
            'literal_word_bytes': counts['word-low'] + counts['word-high'],
            'relocated_word_bytes': counts['reloc-low'] + counts['reloc-high'],
            'source_call_sites': len(sites),
            'instruction_boundaries_typed': False,
            'total_output_bytes': counts['total_output_bytes'],
            'full_program_symbolic': False, 'gate8_complete': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--compiler-tzx', type=Path, required=True)
    p.add_argument('--rom', type=Path, default=ROOT / 'src/zx-ux-sdk/rom/48.rom')
    args = p.parse_args()
    print('ORIGINAL_COMPUTED_SOURCE_TYPES', json.dumps(
        audit(args.compiler_tzx.read_bytes(), args.rom.read_bytes()), sort_keys=True))


if __name__ == '__main__':
    main()
