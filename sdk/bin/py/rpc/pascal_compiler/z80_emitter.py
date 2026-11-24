"""Small explicit Z80 byte emitter used by the native compiler."""
from __future__ import annotations
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.


class Z80:
    def __init__(self) -> None:
        self.code = bytearray()

    def emit(self, *values: int) -> None:
        self.code.extend(value & 255 for value in values)

    def ld_hl(self, value: int) -> None:
        self.emit(0x21, value, value >> 8)

    def ld_mem_hl(self, address: int) -> None:
        self.emit(0x22, address, address >> 8)

    def ld_hl_mem(self, address: int) -> None:
        self.emit(0x2A, address, address >> 8)

    def add_hl_de(self) -> None:
        self.emit(0x19)

    def add_hl_hl(self) -> None:
        self.emit(0x29)

    def sbc_hl_de(self) -> None:
        self.emit(0xAF, 0xED, 0x52)

    def sub_hl_de(self) -> None:
        self.ex_de_hl()
        self.sbc_hl_de()

    def push_hl(self) -> None:
        self.emit(0xE5)

    def pop_de(self) -> None:
        self.emit(0xD1)

    def rst10(self) -> None:
        self.emit(0xD7)

    def ret(self) -> None:
        self.emit(0xC9)

    def jr_z(self, displacement: int = 0) -> None:
        self.emit(0x28, displacement)

    def jp(self, address: int = 0) -> None:
        self.emit(0xC3, address, address >> 8)

    def call(self, address: int = 0) -> None:
        self.emit(0xCD, address, address >> 8)

    def test_hl(self) -> None:
        self.emit(0x7C, 0xB5)  # LD A,H; OR L

    def xor_a(self) -> None:
        self.emit(0xAF)

    def ex_de_hl(self) -> None:
        self.emit(0xEB)

    def jr_nz(self, displacement: int = 0) -> None:
        self.emit(0x20, displacement)

    def jr_c(self, displacement: int = 0) -> None:
        self.emit(0x38, displacement)

    def jr_nc(self, displacement: int = 0) -> None:
        self.emit(0x30, displacement)

    def jr(self, displacement: int = 0) -> None:
        self.emit(0x18, displacement)

    def ld_bc(self, value: int) -> None:
        self.emit(0x01, value, value >> 8)

    def ld_de(self, value: int) -> None:
        self.emit(0x11, value, value >> 8)

    def inc_hl(self) -> None:
        self.emit(0x23)

    def dec_hl(self) -> None:
        self.emit(0x2B)

    def inc_de(self) -> None:
        self.emit(0x13)

    def dec_de(self) -> None:
        self.emit(0x1B)
