# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Keep ZX-UX native PRINT out of the ROM's blocked pagination path.

The original ROM's 'scroll?' message calls WAIT-KEY, which cannot consume
input from the ZX-UX kernel's keyboard interrupt handler.  Save the ROM's
scroll counter for each native PRINT, allow ordinary bitmap scrolling during
that statement, and restore the prior counter afterward.  No BASIC source,
printer operation, kernel storage, or public PEEK/POKE policy is altered.
"""

SCR_CT = 23692


def with_native_screen_scroll(base):
    """Wrap generated PRINT code only, without changing parsed statements."""
    class NativeScreenScroll(base):
        def st_print(self):
            # Reserve one extra stack word for the duration of PRINT. The active process
            # is the only writer of this scoped ROM state. The ZX-UX kernel does not use
            # the SCR_CT byte itself.
            self.emit('ld a,(23692); push af; ld a,255; ld (23692),a')
            super().st_print()
            self.emit('pop af; ld (23692),a')

    return NativeScreenScroll
