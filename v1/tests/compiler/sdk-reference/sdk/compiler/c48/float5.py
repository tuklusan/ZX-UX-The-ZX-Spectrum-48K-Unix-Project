# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import math


class Float5Error(ValueError):
    pass


def _pow2(exp: int) -> Fraction:
    if exp >= 0:
        return Fraction(1 << exp, 1)
    return Fraction(1, 1 << (-exp))


def _round_half_up_positive(x: Fraction) -> int:
    """Nearest integer with exact half rounded upward; x must be >= 0."""
    n, d = x.numerator, x.denominator
    q, r = divmod(n, d)
    if 2 * r >= d:
        q += 1
    return q


@dataclass(frozen=True)
class Float5:
    """Sinclair Spectrum five-byte numeric value.

    This class implements the documented five-byte representation exactly and
    quantizes every arithmetic boundary back to that representation.  The core
    +,-,*,/ operations use exact rational intermediates, so host IEEE precision
    cannot leak across C48 operation boundaries.

    ROM transcendental functions are intentionally *not* claimed byte-for-byte
    certified here; see doc/FLOAT5-ORACLE.md in the SDK release.
    """

    raw: bytes

    def __post_init__(self) -> None:
        if len(self.raw) != 5:
            raise ValueError("Float5 requires exactly five bytes")

    @staticmethod
    def zero() -> "Float5":
        return Float5(b"\0\0\0\0\0")

    @staticmethod
    def from_int(value: int) -> "Float5":
        if -65535 <= value <= 65535:
            w = value & 0xFFFF
            sign = 0xFF if value < 0 else 0x00
            return Float5(bytes((0, sign, w & 0xFF, (w >> 8) & 0xFF, 0)))
        return Float5.from_fraction(Fraction(value, 1), prefer_integer=False)

    @staticmethod
    def from_decimal(text: str) -> "Float5":
        try:
            d = Decimal(text)
        except InvalidOperation as exc:
            raise Float5Error(f"invalid decimal float {text!r}") from exc
        if not d.is_finite():
            raise Float5Error("C48 float has no NaN or infinity")
        f = Fraction(d)
        return Float5.from_fraction(f)

    @staticmethod
    def from_fraction(value: Fraction, *, prefer_integer: bool = True) -> "Float5":
        if value == 0:
            return Float5.zero()
        if prefer_integer and value.denominator == 1 and -65535 <= value.numerator <= 65535:
            return Float5.from_int(value.numerator)

        neg = value < 0
        x = -value if neg else value

        # e is chosen so 0.5 <= x / 2**e < 1.
        # Start from integer bit lengths and adjust without host floats.
        n, d = x.numerator, x.denominator
        e = n.bit_length() - d.bit_length() + 1
        m = x / _pow2(e)
        while m < Fraction(1, 2):
            e -= 1
            m *= 2
        while m >= 1:
            e += 1
            m /= 2

        biased = e + 128
        if biased <= 0:
            # Sinclair format has no denormal. Values below the representable
            # normalized range are a numeric range failure, not silent IEEE-style underflow.
            raise Float5Error("floating value below Spectrum normalized range")
        if biased > 255:
            raise Float5Error("floating value above Spectrum range")

        q = _round_half_up_positive(m * (1 << 32))
        if q >= (1 << 32):
            # Rounding 0.111... to 1.000... renormalizes to 0.5 * 2**(e+1).
            e += 1
            biased = e + 128
            if biased > 255:
                raise Float5Error("floating value above Spectrum range")
            q = 1 << 31
        if not ((1 << 31) <= q < (1 << 32)):
            raise AssertionError("internal Float5 normalization failure")

        b1 = ((q >> 24) & 0x7F) | (0x80 if neg else 0)
        return Float5(bytes((biased, b1, (q >> 16) & 0xFF, (q >> 8) & 0xFF, q & 0xFF)))

    def to_fraction(self) -> Fraction:
        e, b1, b2, b3, b4 = self.raw
        if e == 0:
            word = b2 | (b3 << 8)
            if b1 == 0xFF:
                word -= 65536
            elif b1 != 0:
                raise Float5Error("noncanonical Spectrum integer-form sign byte")
            if b4 != 0:
                raise Float5Error("noncanonical Spectrum integer-form padding byte")
            return Fraction(word, 1)
        neg = bool(b1 & 0x80)
        q = ((b1 | 0x80) << 24) | (b2 << 16) | (b3 << 8) | b4
        m = Fraction(q, 1 << 32)
        value = m * _pow2(e - 128)
        return -value if neg else value

    def is_zero(self) -> bool:
        return self.to_fraction() == 0

    def add(self, other: "Float5") -> "Float5":
        return Float5.from_fraction(self.to_fraction() + other.to_fraction())

    def sub(self, other: "Float5") -> "Float5":
        return Float5.from_fraction(self.to_fraction() - other.to_fraction())

    def mul(self, other: "Float5") -> "Float5":
        return Float5.from_fraction(self.to_fraction() * other.to_fraction())

    def div(self, other: "Float5") -> "Float5":
        rhs = other.to_fraction()
        if rhs == 0:
            raise Float5Error("floating division by zero")
        return Float5.from_fraction(self.to_fraction() / rhs)

    def neg(self) -> "Float5":
        return Float5.from_fraction(-self.to_fraction())

    def abs(self) -> "Float5":
        return Float5.from_fraction(abs(self.to_fraction()))

    def trunc_int(self) -> int:
        f = self.to_fraction()
        if f >= 0:
            return f.numerator // f.denominator
        return -((-f.numerator) // f.denominator)

    def compare(self, other: "Float5") -> int:
        a, b = self.to_fraction(), other.to_fraction()
        return -1 if a < b else (1 if a > b else 0)

    def approx_unary(self, name: str) -> "Float5":
        """Explicitly non-oracle host approximation for opt-in development only."""
        x = float(self.to_fraction())
        funcs = {
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "asin": math.asin, "acos": math.acos, "atan": math.atan,
            "sqrt": math.sqrt, "exp": math.exp, "log": math.log,
        }
        if name not in funcs:
            raise Float5Error(f"unknown approximate function {name}")
        try:
            y = funcs[name](x)
        except (ValueError, OverflowError) as exc:
            raise Float5Error(f"{name} domain/range failure") from exc
        if not math.isfinite(y):
            raise Float5Error(f"{name} domain/range failure")
        # 17 significant decimal digits are enough to recover the host binary64
        # approximation; final storage is still quantized to Float5.
        return Float5.from_decimal(format(y, ".17g"))

    def approx_pow(self, other: "Float5") -> "Float5":
        try:
            y = math.pow(float(self.to_fraction()), float(other.to_fraction()))
        except (ValueError, OverflowError) as exc:
            raise Float5Error("pow domain/range failure") from exc
        if not math.isfinite(y):
            raise Float5Error("pow domain/range failure")
        return Float5.from_decimal(format(y, ".17g"))

    def hex(self) -> str:
        return self.raw.hex()
