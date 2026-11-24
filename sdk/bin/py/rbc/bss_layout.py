# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Map HiSoft code and variable addresses into the final ZX-UX SSX1 layout.

HiSoft puts writable variable storage immediately after its compiled code.
ZX-UX RBC adds saved pointers, a font and 21 UDGs after that code, before
SSX1's separately allocated zero-initialized variable storage. A variable
reference must point past that added image, not into the font or sprite data.
"""


def target_offset(original, code_base, code_length, entry_offset,
                  image_length, variable_length):
    """Return an SSX1 image-relative code or variable address.

    The caller must separately put the relocation site into SSX1's relocation
    stream so its actual process load address will be added by the loader.
    """
    offset = original - code_base
    if not 0 <= offset <= code_length + variable_length:
        raise ValueError('HiSoft pointer is outside code and variables')
    if offset < code_length:
        return entry_offset + offset
    return image_length + (offset - code_length)
