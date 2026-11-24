# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Give a native Sinclair BASIC program its normal 48K display defaults.

The surrounding ZX-UX shell can have a different text palette. Save the
ROM printer attributes, use the Sinclair power-up defaults for the program,
and restore the prior values when the compiler's entry point returns.
Temporary PRINT colors continue to be managed by the ROM.
"""

# 48K ROM printer permanent and temporary attributes and transparency masks. Initial INK 0 on PAPER
# 7 is 0x38. Do not touch screen bitmap/attributes.
_ROM_COLORS = ((0x5C8D, 0x38), (0x5C8E, 0x00),
               (0x5C8F, 0x38), (0x5C90, 0x00))


def save_and_set(e):
    """Emit LD A,(nn), LD (slot),A, LD A,value, LD (nn),A."""
    records = []
    for address, value in _ROM_COLORS:
        e.emit(0x3A)
        e.word(address)
        e.emit(0x32)
        slot_save = len(e.code)
        e.relative(0)
        e.lda(value)
        e.emit(0x32)
        e.word(address)
        records.append([address, slot_save])
    return records


# ROM keyboard mode (FLAGS2) and key click (PIP). Save the exact existing process state;
# the original BASIC source sets the desired value itself.
_ROM_KEYBOARD_STATE = (0x5C6A, 0x5C39)


def save_controls(e):
    """Emit relocatable save-only operations for the two ROM input settings."""
    records = []
    for address in _ROM_KEYBOARD_STATE:
        e.emit(0x3A)
        e.word(address)
        e.emit(0x32)
        slot_save = len(e.code)
        e.relative(0)
        records.append([address, slot_save])
    return records


def restore(e, records):
    """Emit restoration before releasing the display to ZX-UX."""
    for record in records:
        address = record[0]
        e.emit(0x3A)
        slot_read = len(e.code)
        e.relative(0)
        e.emit(0x32)
        e.word(address)
        record.append(slot_read)


def append_slots(e, records):
    """Put the saved colors in private SSX1 data, with relocated addresses."""
    for _, save_site, read_site in records:
        slot = len(e.code)
        e.emit(0)
        e.fix(save_site, slot)
        e.fix(read_site, slot)
