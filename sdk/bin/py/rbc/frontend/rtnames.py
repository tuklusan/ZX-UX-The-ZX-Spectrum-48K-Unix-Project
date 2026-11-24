"""The runtime library's routines, by number (1..131), with our names for them.

The numbers are the compiler's own (its routine table, and the RTn in its REM : LIST
report); the names and one-line descriptions are ours, from reading the routines.
Slots 42, 43 and 46 are empty in v1.2 (42 and 43 are the +3's disk streams).
"""


class RT:
    INT_LE_POSINT = 1       # HL=1 if HL(INTEG) <= DE(POSINT), else 0: swaps and falls into RT2
    POSINT_GE_INT = 2       # HL=1 if HL(POSINT) >= DE(INTEG): HL>=32768 gives 1, otherwise a signed compare via RT12
    POSINT_GT_INT = 3       # HL=1 if HL(POSINT) > DE(INTEG): swaps and falls into RT4
    INT_LT_POSINT = 4       # HL=1 when signed HL is below unsigned DE; negative HL wins, else RT20 compares.
    MIXED_NE = 5            # HL=1 if HL <> DE, one INTEG and one POSINT in either order: HL bit 15 set gives 1, otherwise RT22
    POSINT_LE_INT = 6       # HL=1 if HL(POSINT) <= DE(INTEG): swaps and falls into RT7
    INT_GE_POSINT = 7       # HL=1 if HL(INTEG) >= DE(POSINT): negative HL gives 0, otherwise an unsigned compare via RT18
    INT_GT_POSINT = 8       # HL=1 if HL(INTEG) > DE(POSINT), e.g. IF c>7 with INT c: swaps and falls into RT9
    POSINT_LT_INT = 9       # HL=1 if HL(POSINT) < DE(INTEG): HL>=32768 gives 0, otherwise a signed compare via RT15
    MIXED_EQ = 10           # Mixed signed/unsigned equality: negative HL loses; otherwise compare through RT21.
    INT_LE = 11             # HL=1 if HL <= DE (signed INTEG): swaps and falls into RT12
    INT_GE = 12             # HL=1 if HL >= DE (signed): SBC HL,DE, sign corrected with XOR $80 on overflow (P/V), then RT13
    SIGN_TO_GE = 13         # tail of RT12: HL=0 if the S flag is set, else 1 (it has a number only because RT12 jumps here)
    INT_GT = 14             # HL=1 if HL > DE (signed): swaps and falls into RT15
    INT_LT = 15             # HL=1 if HL < DE (signed), overflow corrected as in RT12, then RT16
    SIGN_TO_LT = 16         # tail of RT15: HL=1 if the S flag is set, else 0
    POSINT_LE = 17          # HL=1 if HL <= DE (unsigned POSINT): swaps and falls into RT18
    POSINT_GE = 18          # HL=1 if HL >= DE (unsigned) (QUICKSOR: I>=J)
    POSINT_GT = 19          # HL=1 if HL > DE (unsigned), e.g. IF k>size: swaps and falls into RT20
    POSINT_LT = 20          # HL=1 if HL < DE (unsigned)
    INT_EQ = 21             # HL=1 if HL = DE (compares the 16-bit pattern, so it serves INTEG and POSINT)
    INT_NE = 22             # HL=1 if HL <> DE (16-bit pattern)
    STR_GE = 23             # HL=1 if A$ >= B$ (both popped from the calc stack, B$ on top): swaps the strings, then RT24
    STR_LE = 24             # HL=1 if A$ <= B$: A=4, then RT29
    STR_LT = 25             # HL=1 if A$ < B$: swaps the strings, then RT26
    STR_GT = 26             # HL=1 if A$ > B$: A=6, then RT29
    STR_NE = 27             # HL=1 if A$ <> B$: A=5, then RT29
    STR_EQ = 28             # HL=1 if A$ = B$: A=7, falls into RT29
    STR_COMPARE = 29        # Compare two calculator-stack strings, byte by byte; shorter prefix sorts first.
    PRINT_STR = 30          # PRINT a string expression: pops it from the calc stack, then PR_STRING
    PRINT_POSINT = 31       # PRINT a POSINT in HL: stacked by RT111, then PRINT_FP
    PRINT_INT = 32          # PRINT an INTEG in HL: stacked by RT112, then PRINT_FP
    STR_CHAR = 33           # s$(i): use 1-based index HL to stack one character. Length gets no vote.
    STR_SLICE_FROM = 34     # s$(a TO): HL=a; the stack holds the text address and length (the length is the end); via RT37
    STR_SLICE_TO = 35       # s$( TO b): HL=b; the stack holds only the text address; start=1; via RT37 (EXAMPLE2: N$( TO L-I))
    STR_SLICE = 36          # s$(a TO b): HL ends the slice; the stack supplies the start and text address.
    STR_SLICE_CORE = 37     # Slice tail: BC=start and DE=end; swap in the address and stack the cropped string.
    PLAY = 38               # PLAY takes BC strings from the calculator stack; 48K mode only resets workspace.
    COPY = 39               # COPY goes to the 48K printer ROM; 128/+2/+3 use their own ROM entries.
    BEEP = 40               # BEEP: duration and pitch on the calc stack, ROM BEEP, with IX preserved
    BREAK_CHECK = 41        # BREAK_KEY; if BREAK is pressed, error L (RST 8 + $14); for REM : BREAK
    EMPTY_42 = 42           # Zero table entry. There is no routine to call.
    EMPTY_43 = 43           # Empty table slot. No code behind this door.
    VAL_STR = 44            # Evaluate the calculator-stack string via ROM VAL$ (B=$18); leave a string result.
    ERR_SP_RESTORE = 45     # A v1.2 helper beside VAL and VAL$; absent from the 48K v1.1 set.
    EMPTY_46 = 46           # Zero means no emitter. Save the jump.
    PRINT_LIT = 47          # Print the inline string after CALL: two-byte length, then text, then return past it.
    STACK_LIT = 48          # Stack the inline string after CALL; the two-byte length precedes its text.
    READ_STR = 49           # READ a$ at S_TOP: length in two bytes, then text; advance the DATA pointer.
    READ_INT = 50           # READ into INTEG/POSINT: HL = the 2-byte DATA item at S_TOP; S_TOP += 2
    READ_REAL = 51          # READ into a REAL: the 5-byte DATA item at S_TOP goes to the calc stack (STACK_NUM); S_TOP += 5
    INPUT_TRAP_ON = 52      # Start INPUT: stash the return address at OLDPPC and install its error trap.
    INPUT_RETRY = 53        # INPUT error trap reached through ERR_SP; arrange another edit attempt.
    INPUT_TRAP_OFF = 54     # Finish INPUT through the ROM screen-cleanup tail; restore workspace state.
    PAUSE = 55              # PAUSE HL: BC=HL, clears FLAGS bit 5 (key flag), jumps to ROM PAUSE_1
    INPUT_START = 56        # INPUT prelude, as in the ROM: open channel K, CLS_LOWER, TV_FLAG=1
    INPUT_INT = 57          # INPUT into INTEG/POSINT: RT58, then RT61; the value is in HL
    INPUT_REAL = 58         # INPUT number: RT59 edits, then VAL (RT109) evaluates on the calculator stack.
    INPUT_STR = 59          # INPUT string: RT60 edits at WORKSP; stack text through CR without quotes.
    INPUT_EDIT = 60         # Edit keyboard input in workspace using the ROM-style editor. Cursor duty.
    REAL_TO_INT = 61        # Pop and round one REAL into signed 16-bit HL; out-of-range values cause an error.
    USR_UDG = 62            # USR "a": the string on the calc stack becomes a UDG address in HL (ROM usr-$ then INT_FETCH)
    USR_CALL = 63           # USR n: call HL with BC=HL; restore IY and reopen stream 2 afterward.
    INT_ARR_GET = 64        # Fetch word at DE+2*(HL-1), with HL a 1-based index. No bounds patrol.
    REAL_ARR_GET = 65       # REAL array element to the calc stack: STACK_NUM from DE+5*(HL-1)
    REAL_ARR_ADDR = 66      # REAL array element address: HL = DE+5*(HL-1), for assignment with RT108
    STR_DESC_AT = 67        # Read the string descriptor at HL: address in DE, length in BC.
    STR_ARR_ELEM = 68       # Index the string-array row at DE using 1-based HL; the row starts with a length.
    STR_ASSIGN = 69         # LET s$: copy a stack string to HL, storing its two-byte length before the text.
    STR_VAR_STACK = 70      # Stack the HL string descriptor's length and text. No NUL ceremony.
    STR_VAR_GET = 71        # String at HL: DE = text address, BC = length. LEN gets its answer.
    REAL_COMPARE = 72       # Pop two REALs and compare them by calculator opcode B; return true/false in HL.
    REAL_COPY_KEEP = 73     # Copy top REAL to DE without popping. FOR keeps start and limit.
    FOR_REAL_INIT = 74      # Start REAL FOR: DE is the step slot; its limit lives five bytes earlier.
    NEXT_REAL = 75          # REAL NEXT: step the variable at DE, then let RT76 decide whether to loop.
    FOR_REAL_TEST = 76      # HL = step slot: pops limit-var (var-limit if step<0) and tests its sign; Z = keep looping, NZ = done
    REAL_OR_INT = 77        # x OR n (x a REAL on the calc stack, n in HL): x becomes 1 if n<>0
    REAL_OR = 78            # x OR y, both REALs: ROM or, called directly
    INT_OR_REAL = 79        # n OR y (n pushed on the machine stack, y a REAL on the calc stack): HL = n if y=0, else 1
    STR_AND_INT = 80        # a$ AND n (a$ on the calc stack, n in HL): the length is set to 0 if n=0 (EXAMPLE5: "S" AND (N>1))
    STR_AND_REAL = 81       # a$ AND y, y a REAL: ROM str-&-no
    REAL_AND = 82           # x AND y, both REALs: ROM no-&-no
    REAL_AND_INT = 83       # x AND n (x a REAL, n in HL): x becomes 0 if n=0
    INT_AND_REAL = 84       # n AND y (n pushed, y a REAL on the calc stack): HL = n if y<>0, else 0
    REAL_MUL = 85           # x*y: ROM multiply called directly, with pointers from RT114
    REAL_DIV = 86           # x/y: ROM division called directly
    REAL_SCALE_POW2 = 87    # Scale the top REAL by 2^A through its exponent; overflow and underflow are trapped.
    REAL_CUBE = 88          # Cube the top REAL using calculator stack duplicates and two multiplies.
    REAL_ADD = 89           # x+y: ROM addition called directly
    REAL_SUB = 90           # x-y: ROM subtract called directly
    INT_NOT = 91            # NOT n for an integer: HL=1 if HL=0, else 0
    REAL_NOT = 92           # NOT x for a REAL: pops it; HL=1 if x=0, else 0
    REAL_NEG = 93           # unary minus on the top REAL (ROM negate)
    REAL_ABS = 94           # ABS of the top REAL (ROM abs)
    REAL_SGN = 95           # SGN of the top REAL (ROM sgn)
    INT_SHR = 96            # HL arithmetic shift right B times, i.e. INT (n/2^B) for INTEG
    POSINT_SHR = 97         # HL logical shift right B times, i.e. INT (n/2^B) for POSINT
    POSINT_DIV_INT = 98     # INT (HL/DE) with HL POSINT and DE INTEG: the sign of DE goes to BREG, then RT101
    INT_DIV_POSINT = 99     # INT (HL/DE) with HL INTEG and DE POSINT: if DE>=32768, HL = 0 or -1 by HL's sign, otherwise RT100
    INT_DIV = 100           # INT (HL/DE), both INTEG: the result's sign (H xor D) goes to BREG, HL=|HL|, then RT101
    DIV_SIGNED_TAIL = 101   # Divide positive magnitudes with RT102, then adjust the signed quotient.
    POSINT_DIV = 102        # unsigned HL/DE: HL = quotient, DE = remainder; error 6 if DE=0 (EXAMPLE6: INT (704/LEN C$))
    INT_CUBE = 103          # Cube HL by calling the 16-bit multiplication routine twice.
    INT_MUL = 104           # Multiply HL by DE modulo 65536; use additions or shift-add by DE size.
    INT_ABS = 105           # ABS for INTEG: negates HL if it's negative; also used by the division routines
    INT_SGN = 106           # SGN for INTEG: HL = -1, 0 or 1
    INT_TO_BOOL = 107       # HL=1 if HL<>0, else 0 (normalises a truth value); no program uses it, so its caller is unknown
    REAL_STORE = 108        # LET for a REAL: pops the top of the calc stack into the 5 bytes at DE
    VAL = 109               # VAL: the string on the calc stack is evaluated by ROM val (B=$1D) into a number; INPUT uses it too
    STACK_CONST = 110       # Stack the inline five-byte REAL after CALL, then skip past it.
    STACK_POSINT = 111      # stacks POSINT HL on the calc stack as a small integer
    STACK_INT = 112         # stacks INTEG HL on the calc stack as a small integer (sign byte $FF if negative)
    REAL_SWAP = 113         # swaps the top two calc stack entries (ROM exchange)
    CALC_PTRS = 114         # HL points at STKEND-10; DE points at STKEND-5. Two REAL operands, one pair.
    REAL_POP_ZERO = 115     # pops the top REAL; carry set if it was zero; HL=0; for IF on a REAL and the NOT/AND/OR helpers
    INK = 116               # INK L: CO_TEMP_5 with A=$10, D=L (sets the temporary colour variables)
    PAPER = 117             # PAPER L: CO_TEMP_5 with A=$11
    FLASH = 118             # FLASH L: CO_TEMP_5 with A=$12
    BRIGHT = 119            # BRIGHT L: CO_TEMP_5 with A=$13
    INVERSE = 120           # INVERSE L: CO_TEMP_5 with A=$14
    OVER = 121              # OVER L: CO_TEMP_5 with A=$15
    PRINT_AT = 122          # PRINT AT E,L: sends 22, E (line), L (column) through RST 10
    PRINT_TAB = 123         # PRINT TAB L: sends 23, L and a second (ignored) byte through RST 10
    STREAM_SCREEN = 124     # opens stream 2 (main screen); used by every program's prologue, at the end of INPUT and after CLS
    STREAM_PRINTER = 125    # Open printer stream 3. Paper permitting.
    MEM_FILL = 126          # Fill BC+1 bytes starting at HL with A; LDIR does the heavy lifting.
    RND = 127               # RND clones the ROM seed update: SEED=(75*(SEED+1) mod 65537)-1.
    INKEY_STR = 128         # INKEY$: a copy of the ROM's key read; stacks a 1-character or empty string
    POINT = 129             # POINT (C=x, B=y): HL = pixel bit 0/1 (PIXEL_ADD, which gives error B if y>175)
    ATTR = 130              # ATTR (C=line, B=column): HL = attribute byte; a copy of the ROM's code without its range check
    CODE = 131              # CODE a$: pops the string; HL = its first byte, or 0 if it's empty


NAME = {v: k for k, v in vars(RT).items() if not k.startswith("_")}
