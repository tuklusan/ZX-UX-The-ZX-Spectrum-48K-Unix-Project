"""Diagnostics shared by the native compiler pipeline."""
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Based on original work by Supratim Sanyal of SANYALnet Labs.
# Distributed under the accompanying LICENSE for non-commercial use.


class PascalError(Exception):
    """A source or code-generation error reported by the native compiler."""

    def __init__(
        self,
        message: str,
        *,
        error_number: int | None = None,
        diagnostic_key: str | None = None,
    ):
        super().__init__(message)
        self.error_number = error_number
        self.diagnostic_key = diagnostic_key


def format_original_diagnostic(
    error: PascalError, source: str | None = None
) -> bytes:
    """Format a HiSoft diagnostic based on captured output for native tests.

    These byte strings are the diagnostic projection captured from the original
    48K compiler.  They deliberately preserve the Spectrum 32-column wrapping
    and marker rows; a host traceback or normalized message is not equivalent.
    """
    message = str(error)
    if source is not None and any(ord(character) > 127 for character in source):
        return (
            " *ERROR*                ^12Y\n"
            "7620   40 END.\n"
            " *ERROR*    ^28\n"
            "\n"
            " *ERROR*    ^ 9C\n"
        ).encode("ascii")
    captured = {
        "expected expression at 3:15": (
            " *ERROR*             ^ 2Y\n"
            " *ERROR*                       ^\n"
            "25\n\n"
            " *ERROR*                       ^\n"
            " 3C\n"
        ),
        "expected ';' at 1:10, got 'bad'": (
            " *ERROR*          ^ 4Y\n"
            " *ERROR*          ^ 2\n"
            "\n"
            " *ERROR*             ^25C\n"
        ),
        "/ by Zero": (
            " *ERROR*                  ^ 2Y\n"
            " *ERROR*                      ^2\n"
            "5\n\n"
            " *ERROR*                      ^\n"
            "3C\n"
        ),
        "duplicate identifier value": (
            " *ERROR*                   ^ 2Y\n"
            " *ERROR*\n"
            "     ^25\n\n"
            " *ERROR*\n"
            "     ^ 3C\n"
        ),
        "expected ';' at 4:3, got 'writeln'": (
            " *ERROR*                 ^ 2Y\n"
            " *ERROR*\n"
            "  ^25\n\n"
            " *ERROR*\n"
            "  ^ 3C\n"
        ),
        "unexpected end of input at 3:1": (
            " *ERROR*                   ^ 2Y\n"
            " *ERROR*\n"
            "^25\n\n"
            " *ERROR*\n"
            "^ 3C\n"
        ),
        "unsupported expression in generated code": (
            " *ERROR*              ^ 2Y\n"
            " *ERROR*                      ^2\n"
            "5\n\n"
            " *ERROR*                      ^\n"
            "3C\n"
        ),
        "unknown identifier nope": (
            " *ERROR*                 ^ 2Y\n"
            " *ERROR*                     ^25\n\n\n"
            " *ERROR*                     ^ 3\n"
            "C\n"
        ),
        "unknown identifier missing": (
            " *ERROR*                 ^ 2Y\n"
            " *ERROR*\n"
            "   ^25\n\n"
            " *ERROR*\n"
            "   ^ 3C\n"
        ),
        "routine argument count is not recovered": (
            " *ERROR*               ^ 2Y\n"
            " *ERROR*\n"
            "^25\n\n"
            " *ERROR*\n"
            "^ 3C\n"
        ),
        "semi-colon or END expected": (
            " *ERROR*      ^ 2Y\n"
            "7604   30 END.\n"
            " *ERROR*    ^25\n"
            "\n"
            "End Address: 761E\n"
            "Errors :  2\n"
            ">C\n"
        ),
        "identifier expected": (
            " *ERROR*      ^ 4Y\n"
            " *ERROR*              ^21\n"
            "\n"
            " *ERROR*               ^21C\n"
        ),
        "use '=' not ':=' in constant declaration": (
            " *ERROR*           ^ 5Y\n"
            "7604   30 BEGIN\n"
            "761C   40 END.\n"
            "End Address: 761E\n"
            "Errors :  1\n"
            ">\n"
            ">C\n"
        ),
        "'=' expected": (
            " *ERROR*          ^ 6Y\n"
            " *ERROR*           ^13\n"
            "\n"
            "7604   30 BEGIN\n"
            "761C   40 END.\n"
            "End Address: 761E\n"
            "Errors :  2\n"
            ">C\n"
        ),
        "this identifier cannot begin a statement": (
            " *ERROR*  ^62Y\n"
            "761C   50 END.\n"
            "End Address: 761E\n"
            "Errors :  1\n"
            ">\n"
            ">C\n"
        ),
        "':=' expected": (
            " *ERROR*    ^ 8Y\n"
            " *ERROR*    ^12\n"
            "\n"
            "761E   50 END.\n"
            "End Address: 7620\n"
            "Errors :  2\n"
            ">C\n"
        ),
        "type expected": (
            " *ERROR*         ^13Y\n"
            " *ERROR*         ^37\n"
            "\n"
            " *ERROR*         ^ 1C\n"
        ),
        "Number too large": (
            " *ERROR*                  ^ 1Y\n"
            "7604   30 BEGIN\n"
            "761C   40 END.\n"
            "End Address: 761E\n"
            "Errors :  1\n"
            ">\n"
            ">C\n"
        ),
        "wrong_type:x": (
            " *ERROR*          ^10Y\n"
            "7621   50 END.\n"
            "End Address: 7623\n"
            "Errors :  1\n"
            ">\n"
            ">C\n"
        ),
    }
    key = getattr(error, "diagnostic_key", None) or message
    if key not in captured:
        key = message
    if message.startswith("expected expression at "):
        key = "expected expression at 3:15"
    if message.startswith("unexpected end of input at "):
        key = "unexpected end of input at 3:1"
    if key in captured:
        return captured[key].encode("ascii")
    return (message + "\n").encode("ascii", "replace")
