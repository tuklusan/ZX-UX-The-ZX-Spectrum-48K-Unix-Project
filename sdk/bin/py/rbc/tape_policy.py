# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Find genuine Sinclair tape commands for safe native runtime handling.

Only original keyword tokens count; bytes inside strings, DATA fields,
REM text and hidden Sinclair numeric encodings are not instructions.
"""


class UnsupportedTapeOperation(ValueError):
    """A program needs a tape device at runtime, which RBC does not provide."""


TAPE_COMMANDS = frozenset({'LOAD', 'SAVE', 'MERGE', 'VERIFY'})


def find_tape_operations(lines, token_names):
    """Find real tape statements without rejecting valid BASIC programs.

    The original 48K ROM still checks complete statement syntax separately.
    No tapes are read, written or simulated by this scanner.
    """
    codes = {
        code: word.strip().upper()
        for code, word in token_names.items()
        if word.strip().upper() in TAPE_COMMANDS
    }
    if set(codes.values()) != TAPE_COMMANDS:
        raise UnsupportedTapeOperation('RBC E_TAPE_UNSUPPORTED: missing original 48K tape tokens')

    found = []
    for number, body in lines:
        in_string = False
        in_data = False
        pos = 0
        while pos < len(body):
            code = body[pos]
            if code == 34:  # Quotes can also occur in DATA.
                in_string = not in_string
                pos += 1
                continue
            if in_string:
                pos += 1
                continue
            if code == 14:  # Hidden five-byte Sinclair floating-point value.
                if pos + 6 > len(body):
                    raise UnsupportedTapeOperation(
                        f'RBC E_TAPE_UNSUPPORTED: Line {number}: truncated numeric token')
                pos += 6
                continue
            if code == 0xEA and not in_data:  # REM: the rest of this BASIC line is inert.
                break
            if code == 58:  # Next statement after a DATA field. Even punctuation has a job.
                in_data = False
                pos += 1
                continue
            if code == 0xE4 and not in_data:  # DATA, until an unquoted colon.
                in_data = True
                pos += 1
                continue
            if not in_data and code in codes:
                operation = codes[code]
                found.append((number, operation))
            pos += 1
    return tuple(found)


def reject_tape_operations(lines, token_names):
    """Legacy strict policy used by existing explicit-refusal diagnostics."""
    found = find_tape_operations(lines, token_names)
    if found:
        number, operation = found[0]
        raise UnsupportedTapeOperation(
            f'RBC E_TAPE_UNSUPPORTED: Line {number}: {operation} requires '
            'external tape I/O; RBC supports standalone BASIC programs only')


def allow_deferred_tape_traps(lines, token_names, findings):
    """Downgrade only token-confirmed tape findings to guarded runtime errors.

    All other unsafe memory/I/O findings retain their original severity.
    """
    from collections import Counter
    remaining = Counter(find_tape_operations(lines, token_names))
    for finding in findings:
        key = (finding.line, finding.operation)
        if (remaining[key] and finding.operation in TAPE_COMMANDS and
                finding.severity == 'block' and
                finding.classification == 'tape_or_external_io'):
            finding.severity = 'info'
            finding.classification = 'deferred_native_tape_error'
            remaining[key] -= 1
    if any(remaining.values()):
        raise UnsupportedTapeOperation('token-confirmed tape statement missing safety finding')
