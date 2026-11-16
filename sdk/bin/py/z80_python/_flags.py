"""The Z80 F register: bit masks, lookup tables, and the public ``Flags`` value.

The core keeps F as a plain int, ``cpu._f``, and each handler computes the
whole new F in one expression from the masks and tables below. ``Flags`` is
the public face of the same byte: a standalone value (``Flags(0x45)``), or,
as ``cpu.f``, a view whose bits read and write the CPU's own F.
"""

FLAG_S = 0b1000_0000
FLAG_Z = 0b0100_0000
FLAG_Y = 0b0010_0000
FLAG_H = 0b0001_0000
FLAG_X = 0b0000_1000
FLAG_PV = 0b0000_0100
FLAG_N = 0b0000_0010
FLAG_C = 0b0000_0001

# Undocumented X/Y flags copy bits 3 and 5 of the relevant internal byte.
FLAG_XY = FLAG_Y | FLAG_X

# S/Y/X come from result bits 7/5/3; Z marks zero. Straight from the byte.
SZXY = tuple((value & (FLAG_S | FLAG_XY)) | (FLAG_Z if value == 0 else 0) for value in range(256))

# Even number of set bits? PV gets its flag. The odd ones can wait.
PARITY = tuple(FLAG_PV if value.bit_count() % 2 == 0 else 0 for value in range(256))

# S/Z/Y/X plus parity for logic, rotations, IN, RLD/RRD and DAA.
SZXYP = tuple(SZXY[value] | PARITY[value] for value in range(256))


class Flags:
    """The Z80 F register, including the undocumented X/Y bits.

    ``Flags(value)`` is a standalone byte. ``cpu.f`` is a view: reading or
    setting its bits reads or sets the CPU's F.
    """

    __slots__ = ("_byte",)

    def __init__(self, value: int = 0) -> None:
        self._byte = value & 0xFF

    def __int__(self) -> int:
        return self._byte

    def __repr__(self) -> str:
        return f"Flags(0x{self._byte:02X})"

    @property
    def byte(self) -> int:
        return self._byte

    @byte.setter
    def byte(self, value: int) -> None:
        self._byte = value & 0xFF

    def _bit(self, mask: int) -> int:
        return 1 if self._byte & mask else 0

    def _set_bit(self, mask: int, value: int) -> None:
        self._byte = (self._byte | mask) if value & 1 else (self._byte & ~mask)

    s = property(lambda self: self._bit(FLAG_S), lambda self, v: self._set_bit(FLAG_S, v))
    z = property(lambda self: self._bit(FLAG_Z), lambda self, v: self._set_bit(FLAG_Z, v))
    y = property(lambda self: self._bit(FLAG_Y), lambda self, v: self._set_bit(FLAG_Y, v))
    h = property(lambda self: self._bit(FLAG_H), lambda self, v: self._set_bit(FLAG_H, v))
    x = property(lambda self: self._bit(FLAG_X), lambda self, v: self._set_bit(FLAG_X, v))
    pv = property(lambda self: self._bit(FLAG_PV), lambda self, v: self._set_bit(FLAG_PV, v))
    n = property(lambda self: self._bit(FLAG_N), lambda self, v: self._set_bit(FLAG_N, v))
    c = property(lambda self: self._bit(FLAG_C), lambda self, v: self._set_bit(FLAG_C, v))

    def set_xy(self, value: int) -> None:
        self._byte = (self._byte & ~FLAG_XY) | (value & FLAG_XY)


class FlagsView(Flags):
    """``cpu.f``: a ``Flags`` whose byte is the CPU's own F (``cpu._f``)."""

    __slots__ = ("_cpu",)

    def __init__(self, cpu: object) -> None:
        self._cpu = cpu

    @property
    def _byte(self) -> int:
        return self._cpu._f

    @_byte.setter
    def _byte(self, value: int) -> None:
        self._cpu._f = value & 0xFF
