# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Verify tokenized Sinclair BASIC with the original 48K ROM, without RUN.

The real ROM's LINE-SCAN entry (0x1B17) explicitly clears the execution
flag. Every statement is parsed in a fresh, boot-initialized 48K machine.
The checker does not execute the user's listing or fix its text.
"""
from __future__ import annotations

from functools import lru_cache


class RomSyntaxError(ValueError):
    pass


def _word(memory, address):
    return memory[address] | memory[address + 1] << 8


def _set_word(memory, address, value):
    memory[address] = value & 255
    memory[address + 1] = value >> 8


@lru_cache(maxsize=2)
def _ready(rom):
    if len(rom) != 16384:
        raise RomSyntaxError('expected an original 16 KB Spectrum 48K ROM')
    from z80_python.cpu import Z80CPU
    memory = bytearray(65536)
    memory[:16384] = rom
    cpu = Z80CPU(memory.__getitem__, memory.__setitem__)
    # Cold boot reaches the original editor; this sets the system variables, calculator workspace,
    # stack, channel table and IY in real ROM code.
    for _ in range(2000000):
        cpu.step()
        if (cpu.pc == 0x15FE and cpu.iy == 0x5C3A
                and 0x5C80 <= _word(memory, 0x5C59) < 0xF000):
            return bytes(memory)
    raise RomSyntaxError('48K ROM failed to reach its BASIC editor')


def _editor_text(body):
    """Remove cached number values only for ROM editor syntax scanning.

    ZX BASIC stores 0E followed by five binary bytes after a visible
    number. LINE_SCAN adds this cache itself, so presenting the stored
    cache again would make a valid line fail ROM syntax checking.
    The actual compiled program is left byte-for-byte untouched.
    """
    out = bytearray()
    in_string = False
    in_remark = False
    pos = 0
    while pos < len(body):
        code = body[pos]
        if code == 34 and not in_remark:
            in_string = not in_string
        elif code == 0xEA and not in_string:
            in_remark = True
        if code == 14 and not in_string and not in_remark:
            if pos + 6 > len(body):
                raise RomSyntaxError('truncated Sinclair numeric encoding')
            pos += 6
            continue
        out.append(code)
        pos += 1
    return bytes(out)


def validate_rom_lines(program, rom, max_steps=250000):
    """Check original Sinclair tokenized lines; raise with BASIC line number."""
    import tap
    from z80_python.cpu import Z80CPU

    snapshot = _ready(bytes(rom))
    rows = tap.split_lines(program)
    for line, body in rows:
        memory = bytearray(snapshot)
        start = _word(memory, 0x5C59)  # E_LINE
        # E_LINE_NO expects an editor line number and statement bytes.
        encoded = str(line).encode('ascii') + b' ' + _editor_text(body.rstrip(b'\r')) + b'\r'
        end = start + len(encoded)
        if end >= 0xF000:
            raise RomSyntaxError(f'Line {line}: line too long for ROM syntax check')
        memory[start:end] = encoded
        for addr in (0x5C61, 0x5C63, 0x5C65):  # WORKSP/STKBOT/STKEND
            _set_word(memory, addr, end)
        _set_word(memory, 0x5C5D, start)  # CH_ADD
        memory[0x5C3A] = 0xFF             # ERR_NR
        cpu = Z80CPU(memory.__getitem__, memory.__setitem__)
        cpu.iy = 0x5C3A
        cpu.sp = 0xFFFE
        memory[0xFFFE:0x10000] = b'\x00\x70'
        cpu.pc = 0x1B17                  # LINE_SCAN: syntax, never execution
        for _ in range(max_steps):
            if cpu.pc == 0x7000:
                break
            if cpu.pc == 0x0008:
                report_address = _word(memory, cpu.sp)
                number = memory[report_address] if report_address < 16384 else None
                code = '?' if number is None else f'{number:02X}'
                raise RomSyntaxError(
                    f'Line {line}: Spectrum 48K ROM syntax error {code} '
                    f'near character {max(0, _word(memory, 0x5C5D) - start)}')
            cpu.step()
        else:
            raise RomSyntaxError(f'Line {line}: Spectrum ROM syntax checker timed out')
    return len(rows)
