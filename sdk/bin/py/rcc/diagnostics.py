# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Stable RCC diagnostics. No C48 language or code-generation decisions here.

Locations must be supplied by the lexer/parser. A missing source position is
never guessed from text; missing statement ordinals are printed as '-'.
"""
import os
import re
import sys
from pathlib import Path

# Each row describes one actual lexer/parser CError condition. The rule order is
# intentional: specific conditions precede generic patterns.
CATALOG = []

def rule(pattern, mnemonic, message):
    CATALOG.append((re.compile(pattern), mnemonic, message))

# Lexical analysis.
rule(r'unterminated comment', 'LEX_COMMENT_UNTERMINATED', 'Block comment has no closing */.')
rule(r'identifier (.+) is longer than 15 characters|identifier longer than 15 characters', 'LEX_IDENTIFIER_LENGTH', 'Identifier exceeds the 15-character limit: {original}.')
rule(r'character literal must be one byte', 'LEX_CHARACTER_LENGTH', 'Character literal must represent exactly one byte.')
rule(r'unterminated literal', 'LEX_LITERAL_UNTERMINATED', 'String or character literal has no closing quotation mark.')
rule(r'bad escape', 'LEX_ESCAPE_INCOMPLETE', 'Escape sequence is incomplete.')
rule(r'\\x needs two hex digits', 'LEX_ESCAPE_HEX', 'Hexadecimal escape must contain exactly two hexadecimal digits.')
rule(r'unknown escape \\(.+)', 'LEX_ESCAPE_UNKNOWN', 'Escape sequence is not recognized: {original}.')
rule(r'non-ASCII or control byte in literal', 'LEX_LITERAL_BYTE', 'Literal contains a character or byte not permitted by C48.')
rule(r'(.+) in source \(only TAB, LF and printable ASCII are allowed\)', 'LEX_INVALID_BYTE', 'Source contains an invalid byte outside a comment: {original}.')
rule(r'invalid source character (.+)', 'LEX_INVALID_CHARACTER', 'Character is not permitted in C48 source: {original}.')
rule(r'malformed number (.+)', 'LEX_NUMBER_MALFORMED', 'Numeric constant is malformed: {original}.')
rule(r'integer literal out of range', 'LEX_INTEGER_RANGE', 'Integer constant exceeds the 16-bit unsigned range.')
rule(r'floating literal out of range', 'LEX_FLOAT_RANGE', 'Floating-point constant is outside the supported range.')

# Preprocessing
rule(r"'#' not at start of line", 'PP_DIRECTIVE_POSITION', 'Preprocessor directive must start at the beginning of a source line.')
rule(r'block comment crosses the end of the directive line', 'PP_COMMENT_CROSSES_LINE', 'Block comment crosses the end of a preprocessor directive line.')
rule(r'bad directive', 'PP_DIRECTIVE_SYNTAX', 'Preprocessor directive is malformed.')
rule(r'unsupported directive #(.+)', 'PP_DIRECTIVE_UNKNOWN', 'Preprocessor directive is not supported: {original}.')
rule(r'nested local include', 'PP_INCLUDE_DEPTH', 'Nested local includes exceed the permitted one-level limit.')
rule(r'include not found: (.+)', 'PP_INCLUDE_MISSING', 'Included source file could not be found: {original}.')
rule(r'unknown system header \(only <c48.h>\)', 'PP_SYSTEM_HEADER', 'System header is unsupported; only <c48.h> is recognized.')
rule(r'bad #include', 'PP_INCLUDE_SYNTAX', 'Include directive is malformed.')
rule(r'bad #define', 'PP_DEFINE_SYNTAX', 'Macro definition is malformed.')
rule(r'#define needs white space between the name and its value', 'PP_DEFINE_WHITESPACE', 'Macro definition requires whitespace between its name and value.')
rule(r'reserved macro name (.+)', 'PP_MACRO_RESERVED', 'Macro name is reserved: {original}.')
rule(r'macro name (.+) is a reserved keyword', 'PP_MACRO_KEYWORD', 'Macro name conflicts with a reserved C48 keyword: {original}.')
rule(r'macro (.+) refers to (.+)', 'PP_MACRO_REFERENCE', 'Macro references an undefined name: {original}.')
rule(r'macro replacement is not a constant expression', 'PP_MACRO_CONSTANT', 'Macro replacement must be a supported compile-time constant expression.')
rule(r'macro (.+) redefined', 'PP_MACRO_REDEFINITION', 'Macro has a conflicting replacement: {original}.')

# Syntax.
rule(r"expected '(.+)'", 'SYN_EXPECTED_TOKEN', 'Expected token {group1!r}.')
rule(r'expected identifier', 'SYN_EXPECTED_IDENTIFIER', 'Expected an identifier.')
rule(r'expected type', 'SYN_EXPECTED_TYPE', 'Expected a C48 type specifier.')
rule(r'expected declaration', 'SYN_EXPECTED_DECLARATION', 'Expected a declaration at file scope.')
rule(r'expected expression', 'SYN_EXPECTED_EXPRESSION', 'Expected an expression.')
rule(r"unexpected '(.+)'", 'SYN_UNEXPECTED_TOKEN', 'Unexpected token {group1!r}.')
rule(r"'else' without 'if'", 'SYN_ELSE_WITHOUT_IF', 'ELSE has no corresponding IF.')
rule(r"(.+) outside a loop", 'SYN_LOOP_CONTROL', 'Loop-control statement appears outside a loop: {original}.')
rule(r'array type name in sizeof', 'SYN_SIZEOF_ARRAY_TYPE', 'Array type-name form is not valid in this C48 SIZEOF expression.')

# Unsupported C48 features
rule(r'unsupported keyword (.+)', 'UNS_RESERVED_KEYWORD', 'Keyword is not supported by C48: {original}.')
rule(r"unsupported operator '(.+)'", 'UNS_OPERATOR', 'Operator {group1!r} is not supported by C48.')
rule(r'prefixed literal unsupported', 'UNS_LITERAL_PREFIX', 'Prefixed string or character literal is not supported by C48.')
rule(r'function-like macro (.+) is not supported', 'UNS_FUNCTION_MACRO', 'Function-like macro is not supported by C48: {original}.')
rule(r'multidimensional arrays are unsupported', 'UNS_MULTIDIMENSIONAL_ARRAY', 'Multidimensional arrays are not supported by C48.')
rule(r'array parameters are not C48 syntax', 'UNS_ARRAY_PARAMETER', 'Array parameter declarator is not supported in this form.')
rule(r'empty initializer list', 'UNS_INITIALIZER_EMPTY', 'Empty initializer lists are not supported by C48.')
rule(r'nested initializer braces', 'UNS_INITIALIZER_NESTED', 'Nested initializer braces are not supported by C48.')
rule(r'designated initializers are unsupported', 'UNS_INITIALIZER_DESIGNATED', 'Designated initializers are not supported by C48.')
rule(r'block-scope static/extern is unsupported', 'UNS_BLOCK_STORAGE_CLASS', 'Block-scope STATIC or EXTERN is not supported by C48.')
rule(r'block-scope function declaration', 'UNS_BLOCK_FUNCTION_DECLARATION', 'Function declarations inside blocks are not supported by C48.')
rule(r'declaration after statement', 'UNS_DECLARATION_ORDER', 'Declarations must precede statements in a C48 block.')
rule(r'declaration in for', 'UNS_FOR_DECLARATION', 'Declarations inside FOR initializers are not supported by C48.')
rule(r'comma operator is unsupported', 'UNS_COMMA_OPERATOR', 'Comma operator is not supported in this expression context.')
rule(r'\(void\) casts are unsupported', 'UNS_VOID_CAST', 'Cast to VOID is not supported by C48.')
rule(r'pointer casts are unsupported', 'UNS_POINTER_CAST', 'Pointer casts are not supported by C48.')
rule(r'\+\+/-- step too large for the bytecode back end', 'UNS_BYTECODE_INCREMENT', 'Increment or decrement step is too large for the bytecode backend.')

# Declaration and type checks
for pat, name, msg in (
(r'reserved identifier (.+)', 'RESERVED_IDENTIFIER', 'Identifier is reserved for the implementation'),
(r'undeclared identifier (.+)', 'UNDECLARED', 'Identifier has not been declared'),
(r'conflicting declaration of (.+)', 'CONFLICTING_DECLARATION', 'Declaration conflicts with an earlier declaration'),
(r'linkage conflict for (.+)', 'LINKAGE_CONFLICT', 'Declaration conflicts with its previous linkage'),
(r'redefinition of (.+)', 'REDEFINITION', 'Symbol has already been defined'),
(r'redeclaration of (.+)', 'LOCAL_REDECLARATION', 'Local identifier is declared more than once in this scope'),
(r'static function (.+) used but not defined', 'STATIC_UNDEFINED', 'Used static function has no definition'),
(r'main has the wrong type', 'MAIN_SIGNATURE', 'Function main has an invalid C48 entry-point signature'),
(r'static main', 'MAIN_STATIC', 'Function main cannot be declared static'),
(r'object named main', 'MAIN_OBJECT', 'main must be a function, not an object'),
(r'extern on a function definition', 'EXTERN_DEFINITION', 'Function definition cannot use extern in this form'),
(r'extern object with initializer', 'EXTERN_INITIALIZER', 'Extern object cannot have an initializer'),
(r"bare 'unsigned' is not a C48 type", 'TYPE_SPELLING', 'Bare unsigned is not a valid C48 type'),
(r"'short int' is not a C48 type spelling", 'TYPE_SPELLING', 'short int is not a supported C48 type spelling'),
(r'void object', 'VOID_OBJECT', 'Object cannot have type void'),
(r'void parameter', 'VOID_PARAMETER', 'Individual parameter cannot have type void'),
(r'expected parameter type', 'PARAMETER_TYPE', 'Function parameter requires a valid type'),
(r'parameter name required in definition', 'PARAMETER_NAME', 'Function definition requires the parameter name'),
(r'duplicate parameter (.+)', 'PARAMETER_DUPLICATE', 'Parameter is declared more than once'),
(r'empty parameter list: use \(void\)', 'PARAMETER_LIST', 'Empty parameter list is not permitted; use (void)'),
(r'function returning array', 'FUNCTION_ARRAY_RETURN', 'Function cannot return an array'),
(r'function (.+) used as a value', 'FUNCTION_AS_VALUE', 'Function cannot be used as a value without a call'),
(r'call of non-function', 'CALL_NONFUNCTION', 'Expression being called is not a function'),
(r'(.+) takes (\d+) arguments', 'CALL_ARGUMENT_COUNT', 'Function call has the wrong number of arguments'),
(r'(.+) argument (\d+) constant outside (\d+)\.\.(\d+)', 'CALL_ARGUMENT_RANGE', 'Constant argument is outside the permitted range'),
(r'array bound must be an integer constant', 'ARRAY_BOUND_CONSTANT', 'Array bound must be an integer constant'),
(r'array bound must be positive', 'ARRAY_BOUND_POSITIVE', 'Array bound must be positive'),
(r'array of incomplete type', 'ARRAY_INCOMPLETE_TYPE', 'Array element type is incomplete'),
(r'array too large', 'ARRAY_SIZE', 'Array exceeds the permitted addressable range'),
(r'array without bound', 'ARRAY_BOUND_MISSING', 'Array requires an explicit bound or permitted initializer'),
(r'cannot size array from initializer', 'ARRAY_SIZE_INFERENCE', 'Array size cannot be determined from its initializer'),
(r'string does not fit array', 'ARRAY_STRING_SIZE', 'String initializer does not fit the array'),
(r'array initializer needs braces', 'ARRAY_INITIALIZER_BRACES', 'Array initializer must use braces'),
(r'too many initializers', 'INITIALIZER_COUNT', 'More initializers than array elements'),
(r'braces around scalar initializer', 'SCALAR_INITIALIZER_BRACES', 'Scalar initializer cannot use braces in this form'),
(r'initializer is not constant', 'INITIALIZER_CONSTANT', 'Initializer must be a compile-time constant'),
(r'pointer initializer is not an address constant', 'POINTER_INITIALIZER', 'Pointer initializer requires a permitted address constant'),
(r'local initializer is not constant', 'LOCAL_INITIALIZER', 'Local initializer must be a permitted constant expression'),
(r'condition is not scalar', 'CONDITION_TYPE', 'Condition requires a scalar type'),
(r'operand is not scalar', 'SCALAR_REQUIRED', 'Operand must have a scalar type'),
(r'void value used', 'VOID_VALUE', 'Void expression cannot be used as a value'),
(r'assignment to non-lvalue', 'ASSIGNMENT_TARGET', 'Assignment target is not a modifiable lvalue'),
(r'assignment to string literal', 'STRING_LITERAL_WRITE', 'String literal cannot be modified by assignment'),
(r'subscript of non-pointer', 'SUBSCRIPT_TARGET', 'Subscript requires a pointer or array expression'),
(r'subscript is not an integer', 'SUBSCRIPT_INDEX', 'Subscript requires an integer index'),
(r'dereference of non-pointer', 'DEREFERENCE_TYPE', 'Dereference requires a pointer expression'),
(r'dereference of void \*', 'DEREFERENCE_VOID', 'Void pointer cannot be dereferenced'),
(r'address of array', 'ADDRESS_ARRAY', 'This form of taking an array address is unsupported'),
(r'address of non-lvalue', 'ADDRESS_LVALUE', 'Address-of requires a suitable lvalue'),
(r'invalid sizeof operand', 'SIZEOF_OPERAND', 'SIZEOF operand is invalid'),
(r'invalid cast', 'CAST_TYPE', 'Cast has incompatible operand types'),
(r"bad operand for unary '(.+)'", 'UNARY_OPERAND', 'Operand type is invalid for unary operator'),
(r"'~' needs an integer", 'COMPLEMENT_TYPE', 'Bitwise complement requires an integer'),
(r'\+\+/-- of non-lvalue', 'INCREMENT_TARGET', 'Increment or decrement requires a modifiable lvalue'),
(r'\+\+/-- of void \*', 'INCREMENT_VOID', 'Increment or decrement cannot operate on a void pointer'),
(r'arithmetic on void \*', 'POINTER_ARITH_VOID', 'Arithmetic on a void pointer is not permitted'),
(r'subtraction of incompatible pointers', 'POINTER_SUBTRACT', 'Pointer subtraction requires compatible pointer types'),
(r'invalid pointer arithmetic', 'POINTER_ARITH', 'Invalid pointer arithmetic operation'),
(r'comparison of incompatible pointers', 'POINTER_COMPARE', 'Pointer comparison requires compatible types'),
(r'relational comparison of void pointers', 'POINTER_RELATIONAL_VOID', 'Relational comparison of void pointers is invalid'),
(r'comparison of pointer and integer', 'POINTER_INTEGER_COMPARE', 'Pointer-to-integer comparison is invalid in this context'),
(r'invalid comparison', 'COMPARISON_TYPE', 'Invalid comparison operand types'),
(r"invalid operands to '(.+)'", 'BINARY_OPERANDS', 'Invalid operands for binary operator'),
(r'shift needs integers', 'SHIFT_TYPE', 'Shift requires integer operands'),
(r"'(.+)' needs integers", 'BITWISE_TYPE', 'Bitwise operator requires integer operands'),
(r'incompatible pointer types in (.+)', 'POINTER_CONVERSION', 'Pointer types are incompatible'),
(r'incompatible types in (.+)', 'TYPE_CONVERSION', 'Type conversion is incompatible'),
(r'constant float conversion out of range', 'FLOAT_CONVERSION_RANGE', 'Constant float conversion exceeds its integer range'),
(r'floating constant expression error', 'FLOAT_CONSTANT', 'Floating-point constant expression cannot be evaluated'),
(r'division by zero in constant expression', 'CONST_DIV_ZERO', 'Division by zero in a constant expression'),
(r'return without a value', 'RETURN_VALUE_MISSING', 'Non-void function must return a value'),
(r'return with a value in void function', 'RETURN_VOID_VALUE', 'Void function cannot return a value'),
):
    rule(pat, 'SEM_' + name, msg + (': {original}.' if '(' in pat and '(.+)' in pat else '.'))

# Validated fallbacks preserve original details rather than asserting a false cause.
FALLBACK = {
    'lexical': 'LEX_INVALID_CHARACTER',
    'literal-range': 'LEX_NUMBER_MALFORMED',
    'preprocessing': 'PP_DIRECTIVE_SYNTAX',
    'syntax': 'SYN_UNEXPECTED_TOKEN',
    'declaration': 'SEM_DECLARATION',
    'type': 'SEM_TYPE_CONVERSION',
    'constant-expression': 'SEM_FLOAT_CONSTANT',
    'unsupported': 'UNS_FEATURE',
    'io': 'IO_INCLUDE_READ',
}


def classify(error):
    original = getattr(error, 'message', str(error))
    for pat, mnemonic, fmt in CATALOG:
        match = pat.fullmatch(original)
        if match:
            # Prefer the canonical, actionable English text where the compiler has already
            # supplied the offending symbol or token.
            if mnemonic == 'SEM_UNDECLARED':
                return mnemonic, "Identifier %r has not been declared." % match.group(1)
            if mnemonic == 'SEM_RESERVED_IDENTIFIER':
                return mnemonic, "Identifier %r is reserved for the implementation." % match.group(1)
            if mnemonic == 'SEM_CONFLICTING_DECLARATION':
                return mnemonic, "Declaration of %r conflicts with an earlier declaration." % match.group(1)
            if mnemonic == 'SEM_REDEFINITION':
                return mnemonic, "Symbol %r has already been defined." % match.group(1)
            if mnemonic == 'SEM_CALL_ARGUMENT_COUNT':
                return mnemonic, "Function %r expects %s arguments." % match.groups()
            if mnemonic == 'SEM_CALL_ARGUMENT_RANGE':
                name, number, low, high = match.groups()
                return mnemonic, "Constant argument %s to %s is outside %s..%s." % (number, name, low, high)
            if mnemonic == 'LEX_IDENTIFIER_LENGTH' and match.group(1):
                return mnemonic, "Identifier %r exceeds the 15-character limit." % match.group(1)
            if mnemonic == 'SYN_EXPECTED_TOKEN' and match.group(1) == 'while':
                return 'SYN_DO_WITHOUT_WHILE', 'DO statement is missing its required terminating WHILE clause.'
            if mnemonic == 'SYN_LOOP_CONTROL':
                operation = match.group(1)
                return ('SYN_BREAK_OUTSIDE_LOOP' if operation == 'break' else 'SYN_CONTINUE_OUTSIDE_LOOP'), operation.upper() + ' appears outside a loop.'
            return mnemonic, fmt.format(original=original, group1=match.group(1) if match.groups() else '')
    category = getattr(error, 'cls', 'syntax')
    return FALLBACK.get(category, 'GEN_INTERNAL'), original.rstrip('.') + '.'


def _source_line(source, where):
    if not source or not where:
        return None
    filename, line = where[:2]
    path = Path(source)
    if os.path.basename(filename) != path.name:
        path = path.parent / filename
    try:
        if not path.is_file() or not 1 <= line:
            return None
        rows = path.read_bytes().replace(b'\r\n', b'\n').split(b'\n')
        if line > len(rows):
            return None
        return rows[line - 1].decode('latin-1')
    except (OSError, UnicodeError, ValueError):
        return None


def emit(mnemonic, message, *, source=None, where=None, column=None, statement=None):
    line = where[1] if where and isinstance(where[1], int) else '-'
    stmt = statement if statement is not None else '-'
    print('%%RCC %s Line: %s Statement: %s %s' % (mnemonic, line, stmt, message), file=sys.stderr)
    row = _source_line(source, where)
    if row is None:
        return
    print('-RCC ' + row, file=sys.stderr)
    if isinstance(column, int) and 1 <= column <= len(row) + 1:
        # Tabs in source must be expanded consistently with the printed text.
        visual = len(('-RCC ' + row[:column - 1]).expandtabs(8)) - len('-RCC ')
        print('-RCC ' + ' ' * visual + '^', file=sys.stderr)


def emit_error(error, source):
    mnemonic, message = classify(error)
    emit(mnemonic, message, source=source,
         where=getattr(error, 'where', None), column=getattr(error, 'column', None))

# Backend tool errors have no reliable C-source position. Their own assembly source locations
# remain in the text, never substituted for a C line number.
ASM_RULES = (
    ('bad expression:', 'ASM_INVALID_EXPRESSION', 'Assembly expression is invalid'),
    ('bad character', 'ASM_INVALID_CHARACTER', 'Invalid character in assembly source'),
    ('bad number', 'ASM_INVALID_NUMBER', 'Invalid assembly numeric literal'),
    ('adding two addresses', 'ASM_ADDRESS_ARITH', 'Two relocatable addresses cannot be added'),
    ('difference of unrelated addresses', 'ASM_ADDRESS_ARITH', 'Cannot subtract unrelated addresses'),
    ('operator ', 'ASM_ADDRESS_ARITH', 'Invalid operator on an address'),
    ('division by zero', 'ASM_DIV_ZERO', 'Division by zero in assembly expression'),
    ('negated address', 'ASM_ADDRESS_ARITH', 'Cannot negate a relocatable address'),
    ('complemented address', 'ASM_ADDRESS_ARITH', 'Cannot complement a relocatable address'),
    ('missing )', 'ASM_MISSING_PAREN', 'Assembly expression is missing a closing parenthesis'),
    ('missing operand', 'ASM_MISSING_OPERAND', 'Assembly expression is missing an operand'),
    ('ld (hl),(hl)', 'ASM_INVALID_OPERANDS', 'Invalid Z80 LD operands'),
    ('bad ld operands', 'ASM_INVALID_OPERANDS', 'Invalid Z80 LD operands'),
    ('bad 16-bit operand', 'ASM_INVALID_OPERANDS', 'Invalid 16-bit Z80 operand'),
    ('bad add ix operand', 'ASM_INVALID_OPERANDS', 'Invalid ADD IX operand'),
    ('bit number', 'ASM_BIT_RANGE', 'Z80 bit number is out of range'),
    ('bad rst', 'ASM_RST_RANGE', 'Invalid RST vector'),
    ('bad instruction:', 'ASM_INVALID_INSTRUCTION', 'Invalid Z80 instruction'),
    ('branch relaxation did not converge', 'ASM_RELAXATION', 'Assembler branch relaxation did not converge'),
    ('duplicate label', 'ASM_DUPLICATE_LABEL', 'Assembly label is defined more than once'),
    ('unknown section', 'ASM_SECTION', 'Assembly section is unknown'),
    ('align needs', 'ASM_ALIGNMENT', 'Alignment must be a power of two no greater than 128'),
    ('code in bss', 'ASM_BSS_CONTENT', 'BSS section cannot contain initialized code'),
    ('data in bss', 'ASM_BSS_CONTENT', 'BSS section cannot contain initialized data'),
    ('word out of range', 'ASM_WORD_RANGE', 'Value does not fit in a Z80 word'),
    ('relocatable value in a byte', 'ASM_RELOCATION_VALUE', 'Relocatable address cannot be stored in a byte'),
    ('byte out of range', 'ASM_BYTE_RANGE', 'Value does not fit in a byte'),
    ('index displacement out of range', 'ASM_INDEX_RANGE', 'Z80 indexed displacement is out of range'),
    ('undefined label', 'ASM_UNDEFINED_LABEL', 'Assembly label is undefined'),
    ('relative jump out of range', 'ASM_BRANCH_RANGE', 'Relative Z80 branch is out of range'),
    ('global ', 'ASM_GLOBAL_SYMBOL', 'Assembly global symbol is invalid or undefined'),
)
LNK_RULES = (
    ('not an SSO1 object', 'LNK_OBJECT_FORMAT', 'Input is not a valid SSO1 object'),
    ('bad section alignment', 'LNK_SECTION_ALIGNMENT', 'Object has invalid section alignment'),
    ('not an SSA1 archive', 'LNK_ARCHIVE_FORMAT', 'Input is not a valid SSA1 archive'),
    ('overlapping relocations', 'LNK_RELOCATION_OVERLAP', 'Native relocations overlap'),
    (' defined in ', 'LNK_DUPLICATE_SYMBOL', 'Symbol has multiple definitions'),
    ('undefined:', 'LNK_UNDEFINED_SYMBOL', 'Required external symbol could not be resolved'),
    ('relocations in bss', 'LNK_RELOCATION_BSS', 'Relocation cannot be applied in BSS'),
    ('relocation type ', 'LNK_RELOCATION_TYPE', 'Unsupported relocation type'),
    ('no entry symbol ', 'LNK_ENTRY_MISSING', 'Program entry symbol was not found'),
    ('not an SSX1 file', 'LNK_SSX_FORMAT', 'Generated file is not an SSX1 executable'),
    ('bad SSX1 header', 'LNK_SSX_HEADER', 'SSX1 executable header is invalid'),
    ('bad relocation escape', 'LNK_SSX_RELOCATION_STREAM', 'Executable relocation stream has an invalid escape'),
    ('bad relocation delta', 'LNK_SSX_RELOCATION_STREAM', 'Executable relocation stream has an invalid delta'),
    ('relocation outside image', 'LNK_SSX_RELOCATION_RANGE', 'Relocation points outside the executable image'),
    ('SSX1 checksum mismatch', 'LNK_SSX_CHECKSUM', 'SSX1 checksum does not match executable contents'),
)


def emit_tool_error(kind, error):
    original = str(error).strip().replace('\n', ' | ')
    options = ASM_RULES if kind == 'ASM' else LNK_RULES
    for needle, name, english in options:
        if needle in original:
            emit(name, english + ': ' + original)
            return
    emit('ASM_INTERNAL' if kind == 'ASM' else 'LNK_FAILURE',
         ('Generated assembly failed: ' if kind == 'ASM' else 'Native linking failed: ') + original)
