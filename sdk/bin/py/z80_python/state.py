"""Values for capturing and restoring Z80 processor state."""

from dataclasses import dataclass


def _require_int(name: str, value: object, maximum: int) -> None:
    if type(value) is not int or not 0 <= value <= maximum:
        width = 2 if maximum == 0xFF else 4
        message = f"{name} must be an integer in range 0x{'0' * width}..0x{maximum:0{width}X}"
        raise ValueError(message)


def _require_bool(name: str, value: object) -> None:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")


@dataclass(frozen=True, slots=True)
class CPUState:
    """Complete CPU-owned state at an instruction boundary.

    This value contains registers, internal execution state, and pending lifecycle
    requests. It deliberately excludes host memory, ports, devices, scheduling, and
    counters. Restoring it therefore restores the processor, not a complete machine.
    """

    a: int = 0
    f: int = 0
    b: int = 0
    c: int = 0
    d: int = 0
    e: int = 0
    h: int = 0
    l: int = 0  # noqa: E741 - canonical Z80 register name
    ix: int = 0
    iy: int = 0
    sp: int = 0
    pc: int = 0
    wz: int = 0
    i: int = 0
    r: int = 0
    iff1: bool = False
    iff2: bool = False
    im: int = 0
    af_alt: int = 0
    bc_alt: int = 0
    de_alt: int = 0
    hl_alt: int = 0
    q: int = 0
    halted: bool = False
    ei_delay: int = 0
    reset_pending: bool = False
    maskable_interrupt_vector: int | None = None
    non_maskable_interrupt_pending: bool = False

    def __post_init__(self) -> None:
        for name in ("a", "f", "b", "c", "d", "e", "h", "l", "i", "r", "q"):
            _require_int(name, getattr(self, name), 0xFF)
        for name in ("ix", "iy", "sp", "pc", "wz", "af_alt", "bc_alt", "de_alt", "hl_alt"):
            _require_int(name, getattr(self, name), 0xFFFF)
        for name in ("iff1", "iff2", "halted", "reset_pending", "non_maskable_interrupt_pending"):
            _require_bool(name, getattr(self, name))
        if type(self.im) is not int or self.im not in (0, 1, 2):
            raise ValueError("im must be 0, 1, or 2")
        if type(self.ei_delay) is not int or self.ei_delay not in (0, 1):
            raise ValueError("ei_delay must be 0 or 1")
        if self.maskable_interrupt_vector is not None:
            _require_int("maskable_interrupt_vector", self.maskable_interrupt_vector, 0xFF)


__all__ = ["CPUState"]
