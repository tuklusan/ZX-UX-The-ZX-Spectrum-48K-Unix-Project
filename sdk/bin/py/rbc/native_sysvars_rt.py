# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Native private PEEK/POKE for Spectrum keyboard and 24-bit frame counter.

HiSoft 48K v1.1 has unused runtime slots 42 and 43; reuse them to
centralize native PEEK and POKE dispatch without rewriting SSX bytes.
The two slots are checked for emptiness at installation. All virtual bytes
live in compiler-allocated process BSS, not ROM or kernel system RAM.
"""
from __future__ import annotations
import re

from spectrum_sysvars import FLAGS2, PIP, FRAMES, SCR_CT, PRIVATE
from native_error_exit import error_exit_asm

PEEK_RT = 42
POKE_RT = 43
UDG_HELPER_RT = 46
# flags2, pip, three FRAMES bytes, last 16-bit tick, initialized marker
BSS_BYTES = 17


class _Code:
    def __init__(self, asm):
        self.asm = asm
        self.code = bytearray()
        self.labels = {}
        self.jumps = []
        self.absrefs = []
        self.absjumps = []
        self.source = []  # Typed emitter statements, not a decoded output image.

    def op(self, text):
        self.code.extend(self.asm(text))
        self.source.extend(('op', part.strip()) for part in text.split(';')
                           if part.strip())

    def address(self, text, offset):
        part = self.asm(text)
        if part[-2:] != b'\x00\x00':
            raise AssertionError(f'assembler address operand changed: {text}')
        self.absrefs.append((len(self.code)+len(part)-2, offset))
        self.source.append(('address', text, offset))
        self.code.extend(part)

    def label(self, name):
        if name in self.labels:
            raise AssertionError('duplicate Z80 label ' + name)
        self.labels[name] = len(self.code)
        self.source.append(('label', name))

    def jr(self, target, condition=''):
        opcode = {'': 0x18, 'nz': 0x20, 'z': 0x28, 'nc': 0x30, 'c': 0x38}[condition]
        self.jumps.append((len(self.code), target))
        self.source.append(('jr', condition, target))
        self.code.extend((opcode,0))

    def jp(self, name, condition=''):
        opcode = {'':0xc3,'z':0xca,'nz':0xc2,'c':0xda,'nc':0xd2}[condition]
        self.absjumps.append((len(self.code)+1,name))
        self.source.append(('jp', condition, name))
        self.code.extend((opcode,0,0))

    def assembly(self, bss_offset: int, entry_offset: int):
        """Z80 source with named branches and process-relative word operands.

        The start label is the runtime's actual position in the whole text.
        A BSS reference uses its offset relative to that entry; native ras/rld
        recomputes the final address after every safe text-size change.
        """
        result = ['  section text', '  global start', 'start:']
        for item in self.source:
            kind = item[0]
            if kind == 'label':
                result.append('rbc_local_' + item[1] + ':')
            elif kind == 'op':
                result.append('  ' + item[1])
            elif kind == 'address':
                source, offset = item[1:]
                if source.count('$0000') != 1:
                    raise ValueError('runtime address source has no exact operand')
                displacement = bss_offset - entry_offset + offset
                result.append('  ' + source.replace('$0000',
                                                     'start+' + str(displacement)))
            elif kind in ('jp', 'jr'):
                condition, target = item[1:]
                result.append('  ' + kind + ' ' +
                              (condition + ',' if condition else '') +
                              'rbc_local_' + target)
            else:
                raise ValueError('untyped native runtime statement')
        return '\n'.join(result) + '\n'

    def whole_program_source(self, bss_offset, process_total, *,
                             entry_label, bss_label, end_label,
                             start_label='start'):
        """Render recorded native operations using relocatable program labels.

        This uses only the original Python-side Z80 source statements and
        their typed address roles. It does not decode assembled output. The
        linker, rather than a fixed source size, locates BSS and process end.
        """
        from re import fullmatch

        symbols = (entry_label, bss_label, end_label, start_label)
        if (any(not isinstance(x, str) or
                not fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', x) for x in symbols)
                or len(set(symbols)) != len(symbols) or
                type(bss_offset) is not int or bss_offset < 0 or
                type(process_total) is not int or
                process_total < bss_offset + BSS_BYTES):
            raise ValueError('whole-program runtime symbols or bounds invalid')
        lines = [entry_label + ':']
        prefix = entry_label + '_local_'
        for item in self.source:
            kind = item[0]
            if kind == 'label':
                lines.append(prefix + item[1] + ':')
            elif kind == 'op':
                lines.append('  ' + item[1])
            elif kind == 'address':
                text, offset = item[1:]
                if text.count('$0000') != 1:
                    raise ValueError('native runtime source has an untyped address')
                # Only the two explicitly source-owned process bounds are allowed to refer
                # outside the private sysvar BSS region.
                if text.strip().lower().replace(' ', '') == 'ldde,$0000' and offset == -bss_offset:
                    target = start_label
                elif (text.strip().lower().replace(' ', '') == 'ldde,$0000'
                      and offset == process_total - 1 - bss_offset):
                    target = end_label + '-1'
                elif 0 <= offset < BSS_BYTES:
                    target = bss_label + ('+' + str(offset) if offset else '')
                else:
                    raise ValueError('native runtime pointer lacks a whole-program anchor')
                lines.append('  ' + text.replace('$0000', target))
            elif kind in ('jr', 'jp'):
                condition, target = item[1:]
                lines.append('  ' + kind + ' ' +
                             (condition + ',' if condition else '') +
                             prefix + target)
            else:
                raise ValueError('untyped native runtime source statement')
        return '\n'.join(lines) + '\n'

    def build(self, base, load, entry=0):
        data = bytearray(self.code)
        for pos, target in self.jumps:
            if target not in self.labels:
                raise AssertionError('missing native branch label: ' + target)
            delta = self.labels[target] - (pos + 2)
            if not -128 <= delta <= 127:
                raise AssertionError(f'native Z80 branch out of range: {target} {delta}')
            data[pos+1] = delta & 255
        for pos, name in self.absjumps:
            if name not in self.labels:
                raise AssertionError('missing absolute native label: '+name)
            address=(load+entry+self.labels[name]) & 65535
            data[pos:pos+2] = address.to_bytes(2,'little')
        for pos, index in self.absrefs:
            ptr = (base + load + index) & 65535
            data[pos:pos+2] = bytes((ptr & 255, ptr >> 8))
        return bytes(data)


def _clock_sync(e):
    """Preserve all live input registers and update process 24-bit FRAMES."""
    e.op('push af; push bc; push de; push hl')
    e.op('ld a,38; call $6003')
    e.address('ld a,($0000)', 7)
    e.op('or a')
    e.jr('tick_known','nz')
    e.op('ld a,1')
    e.address('ld ($0000),a',7)
    e.address('ld ($0000),hl',5)
    e.jr('tick_done')
    e.label('tick_known')
    e.address('ld de,($0000)', 5)
    e.address('ld ($0000),hl', 5)
    e.op('or a; sbc hl,de')
    e.address('ld a,($0000)',2)
    e.op('add a,l')
    e.address('ld ($0000),a',2)
    e.address('ld a,($0000)',3)
    e.op('adc a,h')
    e.address('ld ($0000),a',3)
    e.address('ld a,($0000)',4)
    e.op('adc a,0')
    e.address('ld ($0000),a',4)
    e.label('tick_done')
    e.op('pop hl; pop de; pop bc; pop af')


def _native_error_exit(e):
    """Restore global graphics via the SSX wrapper before native exit."""
    e.op(error_exit_asm(11))


def _process_address_check(e, base, total, accepted, prefix=""):
    """Let unmodified RAM instructions see only native process-owned memory."""
    if total < 1:
        # Counting passes may not yet know BSS bounds; code length is stable.
        total = 1
    e.op('push de; push hl')
    e.address('ld de,$0000', -base)
    e.op('or a; sbc hl,de; pop hl')
    e.jr('out_of_process'+prefix, 'c')
    e.op('push hl')
    e.address('ld de,$0000', total-1-base)
    e.op('or a; sbc hl,de; pop hl')
    e.jr('range_ok'+prefix,'c')
    e.jr('range_ok'+prefix,'z')
    e.label('out_of_process'+prefix)
    e.op('pop de')
    _native_error_exit(e)
    e.label('range_ok'+prefix)
    e.op('pop de')
    e.jr(accepted)


def _cache_font_pointer(e, suffix):
    """Save SSX startup's real private font pointer before BASIC switches CHARS."""
    e.address('ld a,($0000)',13)
    e.op('or a')
    e.jr('font_cached_'+suffix,'nz')
    e.op('push hl')
    e.op('ld hl,($5c36)')
    e.address('ld ($0000),hl',11)
    e.op('ld a,1')
    e.address('ld ($0000),a',13)
    e.op('pop hl')
    e.label('font_cached_'+suffix)


def _cache_udg_pointer(e):
    """Keep the BASIC UDG pointer private; leave the wrapper pointer alone."""
    e.address('ld a,($0000)',16)
    e.op('or a')
    e.jr('udg_initialized','nz')
    e.op('push hl; ld hl,($5c7b)')
    e.address('ld ($0000),hl',14)
    e.op('ld a,1')
    e.address('ld ($0000),a',16)
    e.op('pop hl')
    e.label('udg_initialized')


def _select_print_font(e):
    """ROM CHARS selects ROM printing; all other values select private font."""
    _cache_font_pointer(e, 'write')
    e.address('ld a,($0000)',10)
    e.op('or a')
    e.jr('font_hi_override','nz')
    e.op('ld a,$3c')
    e.jr('font_hi_ready')
    e.label('font_hi_override')
    e.address('ld a,($0000)',9)
    e.label('font_hi_ready')
    e.op('cp $3c')
    e.jr('font_private','nz')
    e.address('ld a,($0000)',8)
    e.op('or a')
    e.jr('font_private','nz')
    e.op('ld hl,$3c00; ld ($5c36),hl; ret')
    e.label('font_private')
    e.address('ld hl,($0000)',11)
    e.op('ld ($5c36),hl; ret')


def _font_address_alias(e, base, total, action, font_alias=None):
    """Translate virtual CHARS glyph address to the process-owned glyph bank.

    The private font is selected by the SSX startup entry, not by a pointer
    supplied by BASIC. If the program has not selected a virtual font or
    the SSX does not carry a private bank, fall through to memory protection.
    """
    if action not in ('peek','poke'):
        raise ValueError('invalid font action')
    e.op('push bc; push de; push hl')
    if font_alias is None:
        e.address('ld a,($0000)',10)
        e.op('or a')
        e.jr('font_nomap', 'z')
        e.address('ld de,($0000)',8)
    else:
        e.op(f'ld de,${font_alias:04x}')
    e.op('or a; sbc hl,de')
    e.jr('font_nomap', 'c')
    e.op('ld a,h; cp 4')
    e.jr('font_nomap', 'nc')
    _cache_font_pointer(e,'alias')
    e.address('ld de,($0000)',11)
    e.op('ld a,d; cp $5d')
    e.jr('font_nomap', 'c')
    e.op('add hl,de')
    _process_address_check(e, base, total, 'font_mapped', 'font')
    e.label('font_mapped')
    e.op('pop de; pop de; pop bc')
    if action == 'peek':
        e.op('ld l,(hl); ld h,0; ret')
    else:
        e.op('ld (hl),e; ret')
    e.label('font_nomap')
    e.op('pop hl; pop de; pop bc')



def _udg_address_alias(e, action):
    """Map one bounded virtual UDG table onto private process graphics."""
    if action not in ('peek', 'poke'):
        raise ValueError('invalid UDG action')
    e.op('push bc; push de; push hl')
    e.address('ld de,($0000)',14)
    e.op('ld a,d; cp $5d')
    e.jr('udg_no_map','c')
    e.op('cp $ff')
    e.jr('udg_range_ok','nz')
    e.op('ld a,e; cp $59')
    e.jr('udg_no_map','nc')
    e.label('udg_range_ok')
    e.op('or a; sbc hl,de')
    e.jr('udg_no_map','c')
    e.op('ld a,h; or a')
    e.jr('udg_no_map','nz')
    e.op('ld a,l; cp 168')
    e.jr('udg_no_map','nc')
    e.op('ld de,($5c7b); add hl,de')
    e.op('pop de; pop de; pop bc')
    if action == 'peek':
        e.op('ld l,(hl); ld h,0; ret')
    else:
        e.op('ld (hl),e; ret')
    e.label('udg_no_map')
    e.op('pop hl; pop de; pop bc')


def _native_udg_helper(asm, base, load, total=0, font_alias=None, entry=0,
                       *, with_source=False, whole_program_symbols=None):
    """A=0 translates string-USR; A=1 checks a computed UDG POKE address."""
    e = _Code(asm)
    e.op('push af')
    _cache_udg_pointer(e)
    e.op('pop af; or a')
    e.jp('usr_translate','z')
    e.op('cp 1')
    e.jp('poke_check','z')
    e.op('cp 2')
    e.jp('flags2_set','z')
    e.op('cp 3')
    e.jp('scr_ct_set','z')
    _native_error_exit(e)
    e.label('flags2_set')
    e.op('ld a,e')
    e.address('ld ($0000),a',0)
    e.op('ret')
    e.label('scr_ct_set')
    e.op('ld a,e')
    e.address('ld ($0000),a',12)
    e.op('ret')
    e.label('usr_translate')
    e.op('push de; ld de,($5c7b); or a; sbc hl,de')
    e.address('ld de,($0000)',14)
    e.op('add hl,de; pop de; ret')
    e.label('poke_check')
    e.op('push bc; push de; push hl')
    e.address('ld de,($0000)',14)
    e.op('or a; sbc hl,de')
    e.jp('poke_error','c')
    e.op('ld a,h; or a')
    e.jp('poke_error','nz')
    e.op('ld a,l; cp 168')
    e.jp('poke_error','nc')
    e.op('ld de,($5c7b); add hl,de')
    e.op('pop de; pop de; pop bc; ret')
    e.label('poke_error')
    e.op('pop hl; pop de; pop bc')
    _native_error_exit(e)
    raw = e.build(base, load, entry)
    if whole_program_symbols is not None:
        if with_source or not isinstance(whole_program_symbols, dict) or set(whole_program_symbols) != {
                'entry_label', 'bss_label', 'end_label', 'start_label'}:
            raise ValueError('native runtime source mode is ambiguous')
        return raw, e.whole_program_source(
            base, total, **whole_program_symbols)
    if with_source:
        return raw, e.assembly(base, entry), tuple(sorted(
            [position for position, _ in e.absrefs] +
            [position for position, _ in e.absjumps]))
    return raw


def _native_peek(asm, base, load, total=0, font_alias=None, entry=0,
                 *, with_source=False, whole_program_symbols=None):
    e = _Code(asm)
    _cache_udg_pointer(e)
    e.op('ld a,h; cp $5c')
    e.jr('ordinary_trampoline','nz')
    e.op('ld a,l; cp $36')
    e.jp('chars0','z')
    e.op('cp $37')
    e.jp('chars1','z')
    e.op('cp $04')
    e.jr('kbd_trampoline','z')
    e.op('cp $39')
    e.jp('pip','z')
    e.op('cp $6a')
    e.jp('flags','z')
    e.op('cp $8c')
    e.jp('scr_ct','z')
    e.op('cp $7b')
    e.jp('udg0','z')
    e.op('cp $7c')
    e.jp('udg1','z')
    e.op('cp $78')
    e.jp('ordinary_bridge','c')
    e.op('cp $7b')
    e.jp('ordinary_bridge','nc')
    e.jr('after_trampolines')
    e.label('ordinary_trampoline')
    e.jp('ordinary_bridge')
    e.label('kbd_trampoline')
    e.jp('kstate')
    e.label('after_trampolines')
    _clock_sync(e)
    e.op('ld a,l; cp $78')
    e.jr('frames0','z')
    e.op('cp $79')
    e.jr('frames1','z')
    e.address('ld a,($0000)',4)
    e.jr('result')
    e.label('frames0')
    e.address('ld a,($0000)',2)
    e.jr('result')
    e.label('frames1')
    e.address('ld a,($0000)',3)
    e.jr('result')
    e.label('chars0')
    e.address('ld a,($0000)',8)
    e.jr('result')
    e.label('chars1')
    e.address('ld a,($0000)',10)
    e.op('or a')
    e.jr('read_chars_hi','nz')
    e.op('ld a,$3c')
    e.jr('result')
    e.label('read_chars_hi')
    e.address('ld a,($0000)',9)
    e.jr('result')
    e.label('pip')
    e.address('ld a,($0000)',1)
    e.jr('result')
    e.label('flags')
    e.address('ld a,($0000)',0)
    e.jr('result')
    e.label('scr_ct')
    e.address('ld a,($0000)',12)
    e.jr('result')
    e.label('udg0')
    e.address('ld a,($0000)',14)
    e.jr('result')
    e.label('udg1')
    e.address('ld a,($0000)',15)
    e.label('result')
    e.op('ld l,a; ld h,0; ret')
    e.label('ordinary_bridge')
    e.jr('ordinary')
    e.label('kstate')
    # Preserve the earlier ROM keyboard-scan service for the original 48K last-key byte. Never treat
    # arbitrary 0x5Cxx addresses as readable.
    e.op('push bc; push de; push hl; call $02bf; pop hl; pop de; pop bc')
    e.op('ld l,(hl); ld h,0; ret')
    e.label('ordinary')
    _udg_address_alias(e, 'peek')
    _font_address_alias(e, base, total, 'peek', font_alias)
    # ROM and bitmap/attribute reads are public; other addresses must be inside the process's
    # compiler-allocated image/BSS, never ZX-UX globals.
    e.op('ld a,h; cp $5b')
    e.jr('read_public','c')
    _process_address_check(e, base, total, 'read_public')
    e.label('read_public')
    e.op('ld l,(hl); ld h,0; ret')
    raw = e.build(base, load, entry)
    if whole_program_symbols is not None:
        if with_source or not isinstance(whole_program_symbols, dict) or set(whole_program_symbols) != {
                'entry_label', 'bss_label', 'end_label', 'start_label'}:
            raise ValueError('native runtime source mode is ambiguous')
        return raw, e.whole_program_source(
            base, total, **whole_program_symbols)
    if with_source:
        return raw, e.assembly(base, entry), tuple(sorted(
            [position for position, _ in e.absrefs] +
            [position for position, _ in e.absjumps]))
    return raw


def _native_poke(asm, base, load, total=0, font_alias=None, entry=0,
                 *, with_source=False, whole_program_symbols=None):
    e = _Code(asm)
    _cache_udg_pointer(e)
    e.op('ld a,h; cp $5c')
    e.jr('poke_trampoline','nz')
    e.op('ld a,l; cp $36')
    e.jp('chars0','z')
    e.op('cp $37')
    e.jp('chars1','z')
    e.op('cp $39')
    e.jr('pip','z')
    e.op('cp $6a')
    e.jr('flags','z')
    e.op('cp $8c')
    e.jp('scr_ct','z')
    e.op('cp $7b')
    e.jp('udg0','z')
    e.op('cp $7c')
    e.jp('udg1','z')
    e.op('cp $78')
    e.jr('ordinary','c')
    e.op('cp $7b')
    e.jr('ordinary','nc')
    e.jr('poke_after_trampoline')
    e.label('poke_trampoline')
    e.jr('ordinary')
    e.label('poke_after_trampoline')
    _clock_sync(e)
    e.op('ld a,l; cp $78')
    e.jr('frames0','z')
    e.op('cp $79')
    e.jr('frames1','z')
    e.op('ld a,e')
    e.address('ld ($0000),a',4)
    e.op('ret')
    e.label('frames0')
    e.op('ld a,e')
    e.address('ld ($0000),a',2)
    e.op('ret')
    e.label('frames1')
    e.op('ld a,e')
    e.address('ld ($0000),a',3)
    e.op('ret')
    e.label('pip')
    e.op('ld a,e')
    e.address('ld ($0000),a',1)
    e.op('ret')
    e.label('flags')
    e.op('ld a,e')
    e.address('ld ($0000),a',0)
    e.op('ret')
    e.label('scr_ct')
    e.op('ld a,e')
    e.address('ld ($0000),a',12)
    e.op('ret')
    e.label('udg0')
    e.op('ld a,e')
    e.address('ld ($0000),a',14)
    e.op('ret')
    e.label('udg1')
    e.op('ld a,e')
    e.address('ld ($0000),a',15)
    e.op('ret')
    e.label('ordinary')
    _udg_address_alias(e, 'poke')
    _font_address_alias(e, base, total, 'poke', font_alias)
    # Writes to ROM or protected machine state must never reach physical RAM. Screen bitmap/attributes
    # and private executable memory are separate.
    e.op('ld a,h; cp $40')
    e.jr('blocked_rom','c')
    e.op('cp $5b')
    e.jr('write_public','c')
    _process_address_check(e, base, total, 'write_public')
    e.label('write_public')
    e.op('ld (hl),e; ret')
    e.label('blocked_rom')
    _native_error_exit(e)
    e.label('chars0')
    e.op('ld a,e')
    e.address('ld ($0000),a',8)
    e.jr('chars_sync')
    e.label('chars1')
    e.op('ld a,e')
    e.address('ld ($0000),a',9)
    e.op('ld a,1')
    e.address('ld ($0000),a',10)
    e.label('chars_sync')
    _select_print_font(e)
    raw = e.build(base, load, entry)
    if whole_program_symbols is not None:
        if with_source or not isinstance(whole_program_symbols, dict) or set(whole_program_symbols) != {
                'entry_label', 'bss_label', 'end_label', 'start_label'}:
            raise ValueError('native runtime source mode is ambiguous')
        return raw, e.whole_program_source(
            base, total, **whole_program_symbols)
    if with_source:
        return raw, e.assembly(base, entry), tuple(sorted(
            [position for position, _ in e.absrefs] +
            [position for position, _ in e.absjumps]))
    return raw


# Exact literal pairs from the original 48K keyboard-repeat program. The HiSoft parser
# sees a hidden five-byte numeric cache after each decimal. Restrict this direct write
# to the two proved values for each address; all computed POKEs still go through the
# existing protected runtime dispatch.
_REPEAT_POKE = re.compile(
    rb'(?P<addr>23561|23562)(?:\x0e[^\r]{5})?\s*,\s*'
    rb'(?P<value>255|35|5)(?:\x0e[^\r]{5})?(?=[ \t\r:])')
_REPEAT_VALUES = {23561: frozenset((35, 255)),
                  23562: frozenset((5, 255))}


def install(compiler):
    """Install direct runtime PEEK/POKE hooks for the 48K compiler only."""
    from z80asm import asm
    base = compiler.rtlib.Machine
    if not getattr(base,'_zxux_sysvars',False):
        class PrivateSysvarMachine(base):
            _zxux_sysvars = True
            _zxux_sysvar_base = 0
            _zxux_total = 0

            def run_emitter(self, n, pc, counting, code_base):
                if n not in (PEEK_RT,POKE_RT,UDG_HELPER_RT):
                    return super().run_emitter(n,pc,counting,code_base)
                if self.emitter(n):
                    raise ValueError('RBC reserved 48K runtime slot is not empty')
                if not getattr(self.img,'v11',False):
                    raise ValueError('RBC system virtualization requires HiSoft 48K v1.1')
                fn = {PEEK_RT: _native_peek, POKE_RT: _native_poke,
                      UDG_HELPER_RT: _native_udg_helper}[n]
                emitted = fn(asm, self._zxux_sysvar_base, code_base, self._zxux_total,
                             getattr(self, '_zxux_font_alias', None), pc)
                if not counting and not self.de_flags & 1:
                    self.far[pc:pc+len(emitted)] = emitted
                return pc + len(emitted)
        compiler.rtlib.Machine = PrivateSysvarMachine

    cls = compiler.Compiler
    if getattr(cls,'_zxux_sysvars',False):
        return
    old_reset, old_layout = cls.reset, cls.layout_vars

    def reset(self, prog):
        old_reset(self,prog)
        self._zxux_sysvar_base = 0
        self.m._zxux_sysvar_base = 0
        self.m._zxux_total = 0
        from spectrum_fonts import detect_font_bank
        import source
        alias, has_poke = detect_font_bank(self.lines, source.Keywords(self.rom).TOKEN)
        self.m._zxux_font_alias = alias

    def layout_vars(self):
        old_layout(self)
        if any(self.m.used(slot) for slot in (PEEK_RT, POKE_RT, UDG_HELPER_RT)):
            self._zxux_sysvar_base = self.pc
            self.m._zxux_sysvar_base = self.pc
            self.pc = (self.pc + BSS_BYTES) & 65535
            self.m._zxux_total = self.pc

    def fn_peek(self):
        self.operand_to_int()
        self.call_rt(PEEK_RT)
        self.t = compiler.POSINT

    def st_poke(self):
        # This fast path does not install a general permission to write system RAM: only
        # exact literal Sinclair keyboard-repeat controls.
        literal = _REPEAT_POKE.match(self.buf, self.ch)
        if literal is not None:
            address = int(literal['addr'])
            value = int(literal['value'])
            if value in _REPEAT_VALUES[address]:
                self.ch = literal.end()
                self.get_char()
                self.emit(f'ld a,{value}; ld (${address:04x}),a')
                return
        self.expr_int()
        self.emit('push hl')
        self.next_char()
        self.expr_int()
        self.emit('ld e,l; pop hl')
        self.call_rt(POKE_RT)

    cls.reset = reset
    cls.layout_vars = layout_vars
    cls.fn_peek = fn_peek
    cls.st_poke = st_poke
    cls._zxux_sysvars = True
