# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Unified public RBC diagnostics. Keep historical codes and raw details internally.

The formatting layer must not change BASIC syntax, safety rules, compiler
behavior, native output, or the byte-for-byte archival input.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

BAS_TEXT = """NO_LINE_NUMBER|BASIC source line has no valid line number.
LINE_RANGE|BASIC line number must be between 0 and 9999.
DUPLICATE_LINE|BASIC line number is defined more than once.
LINE_ORDER|BASIC line is out of ascending order.
EMPTY_PROGRAM|BASIC listing contains no program statements.
EMPTY_STATEMENT|BASIC line has no statement to tokenize.
NON_ASCII|Source contains a character outside the permitted ASCII input encoding.
INVALID_CHARACTER|Source contains an invalid control or character byte.
UNTERMINATED_STRING|Quoted string has no closing quotation mark.
EXPECT_KEYWORD|Expected a Sinclair BASIC statement keyword.
UNEXPECTED_KEYWORD|Keyword is not valid at this position.
EXTRA_BRACKET|Closing parenthesis has no matching opening parenthesis.
MISSING_BRACKET|Opening parenthesis has no matching closing parenthesis.
BRACKET_SEPARATOR|Parenthesized expression is incomplete before the statement separator.
NONFINITE_NUMBER|Numeric constant cannot be represented as a finite value.
NUMBER_RANGE|Numeric constant is outside the ZX Spectrum numeric range.
BIN_RANGE|Binary constant exceeds the permitted value of 65535.
UDG_TOKEN_CONFLICT|128K keyword token conflicts with Spectrum UDG character T or U.
TOO_MANY_STATEMENTS|BASIC line exceeds the supported number of statements.
LINE_TOO_LONG|Tokenized BASIC line exceeds the permitted record length.
PROGRAM_TOO_LARGE|Tokenized BASIC program exceeds the 41,500-byte input limit."""
ROM_TEXT = """NEXT|NEXT has no matching FOR.
VARIABLE|Referenced variable does not exist.
SUBSCRIPT|Array subscript is invalid or outside its declared bounds.
MEMORY|Not enough Spectrum memory is available.
SCREEN|Screen output exceeds the permitted display area.
NUMBER|Numeric value exceeds the supported range.
RETURN|RETURN has no matching GO SUB.
EOF|End of input file was reached unexpectedly.
STOP|Program encountered a STOP statement.
ARGUMENT|Function or statement has an invalid argument.
INTEGER|Integer is outside its permitted range.
SYNTAX|Nonsense in BASIC: invalid Sinclair BASIC syntax.
BREAK_CONT|BREAK interrupted execution; CONT may repeat the operation.
DATA|READ has exhausted the available DATA values.
FILENAME|File name is invalid.
LINE_SPACE|There is insufficient memory to store the BASIC line.
INPUT_STOP|STOP occurred during INPUT.
FOR|FOR has no matching NEXT.
DEVICE|Input/output device is invalid.
COLOUR|Colour value is invalid.
BREAK|BREAK interrupted the program.
RAMTOP|RAMTOP is outside the permitted range.
STATEMENT|The target BASIC statement cannot be found.
STREAM|Stream number is invalid.
FUNCTION|FN was used without a corresponding DEF FN.
PARAMETER|User-defined function parameters do not match their declaration.
TAPE|Tape loading failed."""
HIS_TEXT = """DIRECTIVE|Invalid HiSoft compiler directive.
EXPECT_NUMBER|Expected a numeric value in this statement.
EXPECT_INTEGER|Expected an integer value in this statement.
UNSUPPORTED|HiSoft cannot compile this statement or construct.
MISSING_LINE|Referenced BASIC line does not exist or is outside the compiled region.
TOO_MANY_VARIABLES|HiSoft's numeric variable limit has been exceeded.
NO_SPACE|HiSoft's internal compiler storage limit has been exceeded.
SPLIT_REQUIRED|HiSoft requires separate code and DATA compilation because the combined program does not fit.
CODE_MEMORY|HiSoft cannot fit generated machine code within compilation memory.
EXEC_ADDRESS|Requested execution address leaves insufficient room for compiled code and variables.
ROM_REPORT|HiSoft encountered a Spectrum ROM report.
INTERNAL|HiSoft compilation failed unexpectedly."""
RBC_TEXT = """PRINTER_UNSUPPORTED|Printer operations are unavailable in standalone RBC.
INTERFACE_UNSUPPORTED|External channel operations are unavailable in standalone RBC.
CHANNEL_UNSUPPORTED|Only fixed screen and keyboard streams can be used.
EDITOR_UNSUPPORTED|NEW and LIST cannot run inside a compiled ZX-UX BASIC program.
TAPE_LOAD|LOAD requires external tape input, which standalone RBC programs do not provide.
TAPE_SAVE|SAVE requires external tape output, which standalone RBC programs do not provide.
TAPE_MERGE|MERGE requires external tape input, which standalone RBC programs do not provide.
TAPE_VERIFY|VERIFY requires external tape input, which standalone RBC programs do not provide.
UNSUPPORTED_FEATURE|Sinclair BASIC operation requires a ZX-UX service that is not supported.
USR_MACHINE_CODE|Executable USR machine-code calls are prohibited in ZX-UX BASIC programs.
USR_UNRESOLVED|USR expression cannot be proved to calculate a permitted UDG address.
USR_CONTEXT|This USR expression is not used as a permitted UDG POKE address calculation.
USR_RUNTIME|Dynamically evaluated expression attempted a prohibited machine-code call.
PROTECTED_WRITE|Write would modify protected ZX-UX machine state.
PROTECTED_READ|Memory read would expose protected ZX-UX machine state.
UDG_ADDRESS|Address of the intended user-defined graphics byte cannot be established safely.
UDG_RANGE|User-defined graphics byte offset is outside the permitted range 0–167.
FONT_ADDRESS|Custom character-font address cannot be mapped safely to process-owned font storage.
FONT_RANGE|Custom font write is outside virtualized character-set storage.
UNSAFE_IO|Direct operation would access unsupported or protected hardware.
MEMORY_POLICY|Memory operation is unsafe for a standalone ZX-UX process.
INPUT_READ|BASIC source file cannot be read.
FRONTEND_MISSING|Required HiSoft compiler frontend is unavailable or incomplete.
COMPILER_TAPE|Required HiSoft BASIC v1.1 48K compiler image is missing or invalid.
OPTION_INVALID|Invalid RBC command-line option or value.
OUTPUT_MODE|Requested compiler output mode is unavailable or conflicts with another option.
OUTPUT_PROTECTED|Output path would overwrite original BASIC input.
OUTPUT_WRITE|Compiled output cannot be written.
MEMORY_LIMIT|Executable exceeds the configured compile memory limit.
NATIVE_ENTRY|Generated program entry point is outside its executable image.
NATIVE_LAYOUT|Generated code, variables, or stack have an invalid memory layout.
NATIVE_RELOCATION|An executable address cannot be relocated safely.
NATIVE_SOURCE_UNRESOLVED|Original HiSoft machine code lacks a complete verified Z80 source reconstruction.
HISOFT_SPLIT_UNVERIFIED|HiSoft produced separate code and DATA halves; native source reconstruction for the combined image is incomplete.
NATIVE_SIZE|Generated executable fields exceed native format or address range.
NATIVE_ASSEMBLER|Native assembler could not produce a valid ZX-UX object.
NATIVE_LINKER|Native linker could not produce a valid SSX executable.
NATIVE_VALIDATION|Generated SSX failed format or relocation validation.
COMPILER_INTERNAL|Compiler encountered an unexpected internal failure.
TZX_CONVERSION|Tokenized TZX BASIC could not be recovered faithfully.
TZX_FIDELITY|Recovered TZX BASIC differs semantically from the authoritative BAS.
SSX_DIFFERENCE|BAS and TZX produced different linked SSX bytes.
PRINT_AT_RANGE|PRINT AT coordinate is outside the Spectrum 48K screen limits.
STRING_BOUND_UNPROVEN|String storage requirements cannot be safely bounded or checked.
ROM_WORKSPACE_UNSAFE|Required ROM workspace cannot be safely isolated from ZX-UX memory.
ROM_STATE_UNSAFE|ROM system state cannot be guaranteed to be restored on every supported exit path.
STRING_CAPACITY|String operation exceeds reserved memory capacity.
ROM_WORKSPACE_OVERFLOW|ROM workspace operation exceeds reserved memory capacity."""
WARN_TEXT = """DYNAMIC_DIM|A dynamic DIM uses a runtime-bounded array reservation. Compilation continues; native memory and source verification still apply.
HISOFT_UNOWNED_BYTES|HiSoft generated bytes without a verified native source producer. Source reconstruction is still required to create an executable.
HISOFT_SPLIT_IMAGE|HiSoft returned a combined D+E image rather than a single C-mode capture. The complete native source must be reconstructed before linking."""
ROM_EXTRA = """INVALID_IMAGE|Supplied ROM is not a 16,384-byte Spectrum 48K image.
INITIALIZATION|Spectrum ROM could not initialize its BASIC editor.
NUMERIC_ENCODING|Stored Sinclair numeric representation is incomplete or corrupt.
LINE_TOO_LONG|BASIC line is too long for the ROM syntax-checking workspace.
CHECK_TIMEOUT|Original ROM syntax checker exceeded its execution limit.
UNKNOWN_REPORT|ROM returned an unrecognized report code."""

def _catalog(prefix, payload):
    return {prefix + '_' + row.partition('|')[0]: row.partition('|')[2]
            for row in payload.splitlines()}

MESSAGES = {}
for _prefix, _spec in (('BAS', BAS_TEXT), ('ROM', ROM_EXTRA),
                       ('HIS', HIS_TEXT), ('RBC', RBC_TEXT),
                       ('RBC_WARN', WARN_TEXT)):
    MESSAGES.update(_catalog(_prefix, _spec))
ROM_LABELS = tuple(row.partition('|')[0] for row in ROM_TEXT.splitlines())
for _code, _row in enumerate(ROM_TEXT.splitlines()):
    _name, _, _msg = _row.partition('|')
    _report = str(_code+1) if _code < 9 else chr(ord('A') + _code - 9)
    MESSAGES['ROM_' + _report + '_' + _name] = _msg
MESSAGES['ROM_0_OK'] = 'BASIC program completed successfully.'  # Not an error.
HIS_BY_NUMBER = dict(zip(range(100, 110), tuple(row.partition('|')[0]
                                                   for row in HIS_TEXT.splitlines()[:10])))


@dataclass(frozen=True)
class Diagnostic:
    mnemonic: str
    message: str
    basic_line: int | None = None
    statement: int | None = None
    source_text: str | None = None
    source_column: int | None = None
    native_code: str | None = None
    detail: str = ''

    def render(self) -> str:
        line = '-' if self.basic_line is None else self.basic_line
        statement = '-' if self.statement is None else self.statement
        parts = [f'%RBC {self.mnemonic} Line: {line} Statement: {statement} {self.message}']
        if self.source_text is not None:
            parts.append('-RBC ' + self.source_text)
            if self.source_column is not None and 0 <= self.source_column < len(self.source_text):
                parts.append('     ' + ' ' * self.source_column + '^')
        return '\n'.join(parts)


def original_lines(source: Path | None) -> dict[int, str]:
    """No reformatting or token-derived reconstruction of the user's source."""
    if source is None or source.suffix.lower() != '.bas':
        return {}
    try:
        raw = source.read_bytes().decode('ascii')
    except (OSError, UnicodeError):
        return {}
    rows = {}
    for item in raw.splitlines():
        match = re.match(r'^\s*([0-9]+)(?=\s|:|$)', item)
        if match:
            rows.setdefault(int(match.group(1)), item)
    return rows


def _statement_starts(raw):
    match = re.match(r'^\s*\d+\s*', raw)
    if match is None:
        return []
    starts = [match.end()]
    quote = False
    pos = starts[0]
    while pos < len(raw):
        c = raw[pos]
        if c == '"':
            quote = not quote
        elif not quote:
            if (raw[pos:pos+3].upper() == 'REM' and
                (pos == 0 or not (raw[pos-1].isalnum() or raw[pos-1] == '$'))):
                break
            if c == ':':
                starts.append(pos + 1)
            elif re.match(r'THEN\b', raw[pos:], re.I):
                starts.append(pos + 4)
                pos += 3
        pos += 1
    return [start + len(raw[start:]) - len(raw[start:].lstrip(' '))
            for start in starts]


def _position(raw, keyword):
    if raw is None:
        return None, None
    starts = _statement_starts(raw)
    if not starts:
        return None, None
    if keyword:
        matches = list(re.finditer(r'(?<![\w$])' + re.escape(keyword) + r'(?![\w$])', raw, re.I))
        if len(matches) == 1:
            column = matches[0].start()
            if column >= starts[0] and raw[:column].count('"') % 2 == 0:
                # Never point inside a preceding remark.
                before = raw[:column].upper()
                if not re.search(r'(?<![\w$])REM\b', before):
                    return 1 + sum(x <= column for x in starts[1:]), column
    if len(starts) == 1:
        return 1, starts[0]
    return None, None


def from_exception(exc: Exception, source: Path | None = None) -> Diagnostic:
    detail = str(exc)
    low = detail.lower()
    found = re.search(r'\bline\s+(\d+)\b', detail, re.I)
    line = int(found.group(1)) if found else None
    if re.search(r'\b(?:ASCII|physical) line\s+\d+\b', detail, re.I):
        line = None  # Physical source-record numbers are NOT BASIC numbers.
    rows = original_lines(source)
    if line not in rows:
        line = None
    mnemonic = 'RBC_COMPILER_INTERNAL'
    keyword = native = message = None
    rom = re.search(r'ROM syntax error\s+([0-9a-f]{2})', detail, re.I)
    his = re.search(r'HiSoft v1\.1 compile failed:\s*(.*?)\s+line\s+\d+:\s*(.*)', detail, re.I | re.S)
    if rom:
        native = rom.group(1).upper()
        index = int(native, 16)
        if 0 <= index < len(ROM_LABELS):
            letter = str(index+1) if index < 9 else chr(ord('A') + index - 9)
            mnemonic = f'ROM_{letter}_{ROM_LABELS[index]}'
        else:
            mnemonic = 'ROM_UNKNOWN_REPORT'
    elif 'rom syntax checker timed out' in low: mnemonic = 'ROM_CHECK_TIMEOUT'
    elif 'rom failed to reach' in low: mnemonic = 'ROM_INITIALIZATION'
    elif 'original 16 kb' in low or '16384 bytes' in low: mnemonic = 'ROM_INVALID_IMAGE'
    elif 'truncated sinclair numeric' in low: mnemonic = 'ROM_NUMERIC_ENCODING'
    elif 'too long for rom' in low: mnemonic = 'ROM_LINE_TOO_LONG'
    elif his:
        native = his.group(1).strip()
        code = re.search(r'\b(10[0-9])\b', native)
        name = HIS_BY_NUMBER.get(int(code.group(1)) if code else -1)
        if not name:
            if 'expecting a number' in low or 'expected numeric' in low:
                name = 'EXPECT_NUMBER'
            elif 'expecting an integer' in low or 'expected integer' in low:
                name = 'EXPECT_INTEGER'
            elif 'not supported' in low or 'dim again' in low:
                name = 'UNSUPPORTED'
            elif 'line does not exist' in low or 'unknown line' in low:
                name = 'MISSING_LINE'
            else:
                name = 'INTERNAL'
        mnemonic = 'HIS_' + name
        keyword = 'GO TO' if 'go to' in low else 'DIM' if 'dim' in low else None
    elif 'e_print_at_range' in low or 'rbc_print_at_range' in low:
        mnemonic, keyword = 'RBC_PRINT_AT_RANGE', 'AT'
    elif 'rbc_string_bound_unproven' in low:
        mnemonic = 'RBC_STRING_BOUND_UNPROVEN'
    elif 'rbc_rom_workspace_unsafe' in low:
        mnemonic = 'RBC_ROM_WORKSPACE_UNSAFE'
    elif 'rbc_rom_state_unsafe' in low:
        mnemonic = 'RBC_ROM_STATE_UNSAFE'
    elif 'rbc_string_capacity' in low:
        mnemonic = 'RBC_STRING_CAPACITY'
    elif 'rbc_rom_workspace_overflow' in low:
        mnemonic = 'RBC_ROM_WORKSPACE_OVERFLOW'
    elif 'unexpected keyword' in low:
        mnemonic = 'BAS_UNEXPECTED_KEYWORD'
        match = re.search(r'unexpected keyword\s+([^:\n]+)', detail, re.I)
        keyword = match.group(1).strip() if match else None
    elif 'expecting statement' in low or 'expected keyword' in low:
        mnemonic = 'BAS_EXPECT_KEYWORD'
    elif 'numbered ascii' in low or 'missing line number' in low: mnemonic = 'BAS_NO_LINE_NUMBER'
    elif 'line number outside' in low or 'exceeds 9999' in low: mnemonic = 'BAS_LINE_RANGE'
    elif 'missing whitespace before to in for' in low: mnemonic, keyword = 'BAS_UNEXPECTED_KEYWORD', 'TO'
    elif 'duplicate or unordered' in low:
        # The emitter does not say which condition failed. Distinguish by counting source-record
        # numbers, not a guessed failure class. Leave the old files out of the blast zone.
        if source is not None and line is not None:
            try:
                copies = sum(bool(re.match(r'^\s*' + str(line) + r'(?=\s|:|$)', row))
                             for row in source.read_text(encoding='ascii').splitlines())
            except (OSError, UnicodeError):
                copies = 0
        else:
            copies = 0
        mnemonic = 'BAS_DUPLICATE_LINE' if copies > 1 else 'BAS_LINE_ORDER'
    elif 'empty basic listing' in low: mnemonic = 'BAS_EMPTY_PROGRAM'
    elif 'no statements' in low or 'empty first basic' in low: mnemonic = 'BAS_EMPTY_STATEMENT'
    elif 'non-ascii' in low: mnemonic = 'BAS_NON_ASCII'
    elif 'invalid character' in low: mnemonic = 'BAS_INVALID_CHARACTER'
    elif 'terminating quote' in low: mnemonic = 'BAS_UNTERMINATED_STRING'
    elif 'nonfinite' in low: mnemonic = 'BAS_NONFINITE_NUMBER'
    elif 'number outside spectrum' in low: mnemonic = 'BAS_NUMBER_RANGE'
    elif '41500' in low: mnemonic = 'BAS_PROGRAM_TOO_LARGE'
    elif 'zx-ux memory check stopped' in low:
        found_op = re.search(r'\b(USR|POKE|PEEK|LOAD|SAVE|MERGE|VERIFY|OUT|IN)\s+([a-z_]+)', detail, re.I)
        operation = found_op.group(1).upper() if found_op else None
        category = found_op.group(2).lower() if found_op else ''
        keyword = operation
        if operation == 'USR' and category == 'raw_machine_code_address':
            mnemonic = 'RBC_USR_MACHINE_CODE'
        elif operation == 'POKE' and category == 'global_memory_write':
            mnemonic = 'RBC_PROTECTED_WRITE'
        elif operation == 'PEEK' and category == 'global_memory_read':
            mnemonic = 'RBC_PROTECTED_READ'
        elif operation in ('LOAD','SAVE','MERGE','VERIFY'):
            mnemonic = 'RBC_TAPE_' + operation
        else:
            mnemonic = 'RBC_MEMORY_POLICY'
    elif 'e_poke_address' in low:
        mnemonic, keyword = 'RBC_UDG_ADDRESS', 'POKE'
    elif 'e_external_io' in low:
        operation = re.search(r'\b(LPRINT|LLIST|COPY|CAT|FORMAT|MOVE|ERASE)\b', detail, re.I)
        keyword = operation.group(1).upper() if operation else None
        mnemonic = ('RBC_PRINTER_UNSUPPORTED' if keyword in ('LPRINT', 'LLIST', 'COPY')
                    else 'RBC_INTERFACE_UNSUPPORTED')
    elif 'e_channel_unsafe' in low:
        mnemonic = 'RBC_CHANNEL_UNSUPPORTED'
    elif 'e_editor_command' in low:
        operation = re.search(r'\b(NEW|LIST)\b', detail, re.I)
        keyword = operation.group(1).upper() if operation else None
        mnemonic = 'RBC_EDITOR_UNSUPPORTED'
    elif 'e_tape_unsupported' in low:
        operation = re.search(r'\b(LOAD|SAVE|MERGE|VERIFY)\b', detail)
        keyword = operation.group(1) if operation else None
        mnemonic = 'RBC_TAPE_' + keyword if keyword else 'RBC_UNSUPPORTED_FEATURE'
    elif 'e_usr_token' in low:
        mnemonic = 'RBC_USR_CONTEXT' if 'outside poke' in low else 'RBC_USR_UNRESOLVED'
        keyword = 'USR'
        if line in rows and re.search(r'\bUSR\s+\d+', rows[line], re.I):
            mnemonic = 'RBC_USR_MACHINE_CODE'
    elif 'udg offset' in low: mnemonic, keyword = 'RBC_UDG_RANGE', 'POKE'
    elif 'poke' in low and ('protected' in low or 'private system' in low):
        mnemonic, keyword = 'RBC_PROTECTED_WRITE', 'POKE'
    elif 'poke token' in low: mnemonic, keyword = 'RBC_MEMORY_POLICY', 'POKE'
    elif 'native memory (limit' in low:
        mnemonic = 'RBC_MEMORY_LIMIT'
        amounts = re.search(r'needs\s+(\d+)\s+bytes of native memory\s+\(limit\s+(\d+)\)', detail)
        if amounts:
            message = ('Executable requires ' + amounts.group(1) +
                       ' bytes of native memory; the configured compile limit is ' +
                       amounts.group(2) + ' bytes.')
    elif 'would overwrite' in low: mnemonic = 'RBC_OUTPUT_PROTECTED'
    elif 'conflicting output modes' in low or ('unavailable' in low and 'bytecode' in low):
        mnemonic = 'RBC_OUTPUT_MODE'
    elif 'rbc option:' in low: mnemonic = 'RBC_OPTION_INVALID'
    elif isinstance(exc, OSError): mnemonic = 'RBC_INPUT_READ'
    elif 'full compiled mode c image is required' in low: mnemonic = 'RBC_HISOFT_SPLIT_UNVERIFIED'
    elif 'original typed three-base hisoft source unresolved' in low: mnemonic = 'RBC_NATIVE_SOURCE_UNRESOLVED'
    elif 'relocation' in low: mnemonic = 'RBC_NATIVE_RELOCATION'
    elif 'entry point' in low: mnemonic = 'RBC_NATIVE_ENTRY'
    elif 'memory layout' in low or '48k address' in low: mnemonic = 'RBC_NATIVE_LAYOUT'
    elif 'ssx1' in low: mnemonic = 'RBC_NATIVE_VALIDATION'

    original = rows.get(line) if line is not None else None
    statement, column = _position(original, keyword)
    if message is None:
        message = MESSAGES[mnemonic]
    if mnemonic.startswith('BAS_') and line is None:
        physical = re.search(r'(?:ASCII |\b)line\s+(\d+)\b', detail, re.I)
        if physical:
            message += ' Physical ASCII file line ' + physical.group(1) + '.'
    if mnemonic.startswith('HIS_') and his:
        # The historical error text is essential where HiSoft returned no numeric report code,
        # and distinct DIM/INPUT reasons share a class.
        context = ' '.join(part.strip() for part in (his.group(1), his.group(2)) if part.strip())
        if context:
            message += ' ' + context
    if mnemonic in ('RBC_PROTECTED_WRITE', 'RBC_PROTECTED_READ',
                    'RBC_USR_UNRESOLVED', 'RBC_UDG_ADDRESS',
                    'RBC_MEMORY_POLICY', 'RBC_COMPILER_INTERNAL') or 'zx-ux memory check stopped' in low:
        message += ' ' + detail
    return Diagnostic(mnemonic, message, line, statement, original, column, native, detail)


def format_warning(mnemonic: str, detail: str = '') -> str:
    """Nonfatal advisory. Never turn a native source/protection failure into OK."""
    if not mnemonic.startswith('RBC_WARN_') or mnemonic not in MESSAGES:
        raise ValueError('unknown RBC warning mnemonic')
    extra = (' ' + detail) if detail else ''
    return (f'%RBC-WARNING {mnemonic} Line: - Statement: - '
            f'{MESSAGES[mnemonic]}{extra}')


def format_failure(exc: Exception, source: Path | None = None) -> str:
    return from_exception(exc, source).render()


class RbcArgumentParser(argparse.ArgumentParser):
    """Preserve argparse's exit code 2 for invalid options."""
    def error(self, message):
        print(format_failure(ValueError('RBC option: ' + message)), file=sys.stderr)
        self.exit(2)
