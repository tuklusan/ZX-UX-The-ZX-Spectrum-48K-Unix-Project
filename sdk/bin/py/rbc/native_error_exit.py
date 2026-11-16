# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Transfer native BASIC failures to the SSX process cleanup entry.

The SSX wrapper owns the real CHARS and UDG system variables. Its 168-byte
private UDG image is followed by one relocated cleanup pointer. A compiler
runtime can find that pointer without writing protected system memory or
assuming the program's load address. DE carries the Spectrum error status.
"""

UDG_BYTES = 21 * 8


def error_exit_asm(status: int) -> str:
    """Z80 error exit, with a runtime-resolved process-private destination."""
    if not 0 <= status <= 255:
        raise ValueError('invalid BASIC native error status')
    return (f'ld hl,($5c7b); ld bc,{UDG_BYTES}; add hl,bc; '
            f'ld a,(hl); inc hl; ld h,(hl); ld l,a; '
            f'ld de,{status}; jp (hl)')


def error_exit_bytes(status: int) -> bytes:
    """Fixed opcode form for the HiSoft emitter that outputs direct bytes."""
    if not 0 <= status <= 255:
        raise ValueError('invalid BASIC native error status')
    return bytes((0x2a, 0x7b, 0x5c, 0x01, UDG_BYTES, 0,
                  0x09, 0x7e, 0x23, 0x66, 0x6f, 0x11, status, 0, 0xe9))
