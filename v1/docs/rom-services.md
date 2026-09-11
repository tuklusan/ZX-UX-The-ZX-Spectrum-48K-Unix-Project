<!-- Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs. -->
<!-- Proprietary rights reserved except as expressly licensed herein. -->
<!-- -->
<!-- ZX-UX Sinclair ZX Spectrum Unix -->
<!-- This file is governed by the SANYALnet Labs Non-Commercial License in the -->
<!-- root LICENSE file. Non-Commercial use is permitted; Commercial Use and use -->
<!-- for AI/ML model training are prohibited unless separately authorized. -->
<!-- -->
<!-- Attribution is required: "Based on original work by Supratim Sanyal of -->
<!-- SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination, -->
<!-- patent, trademark, and governing-law provisions. -->

# ZX-UX ROM service contracts

Revision-11 ROM calls are centralized in `v1/src/kernel/rom_services.asm`. The
alternate register bank is OS-private and volatile. No process descriptor,
scheduler record, allocator record, or other persistent kernel state may exist
only in AF'/BC'/DE'/HL'.

## Frozen provenance

The canonical runtime image is the 16384-byte original 48K Spectrum ROM with
SHA-256 `d55daa439b673b0e3f5897f99ac37ecb45f974d1862b4dadb85dec34af99cb42`.
Routine naming and machine-contract research use *The Complete Spectrum ROM
Disassembly* by Ian Logan and Frank O'Hara, cross-checked against the maintained
SkoolKit 10.1 48K rendering (released 2026-08-14). The ROM bytes, not prose or a
tool-generated listing, are the final address identity.

Documented Z80 behavior is normative from the Zilog Z80 CPU User Manual UM0080,
kept project-locally at `reference/zilog/UM0080-z80-user-manual.pdf` when the
reference corpus is installed. IM2, alternate-bank exchange, block transfer and
search, relative branches and interrupt return must not rely on undocumented
opcodes. The original 48K memory-map/contention baseline is the Sinclair ZX
Spectrum 16K/48K technical documentation plus the machine-timing contention
record frozen by the architecture: 0x4000-0x7FFF contended and
0x8000-0xFFFF uncontended.

## Baseline address ledger

| symbol | address | disassembly entry | initial class | error behavior | alt bank |
| --- | ---: | --- | --- | --- | --- |
| PRINT-A | 0010 | PRINT-A | A | MAY_RST8_ERROR | unknown=>clobbers |
| FP-CALC | 0028 | FP-CALC | B | MAY_RST8_ERROR | unknown=>clobbers |
| KEY-SCAN | 028E | KEY-SCAN | A | RETURNS_STATUS | does-not-use |
| KEYBOARD | 02BF | KEYBOARD | A | MAY_ABORT_ON_BREAK | unknown=>clobbers |
| KEY-DECODE | 0333 | keyboard decode | A | RETURNS_STATUS | unknown=>clobbers |
| BEEPER | 03B5 | BEEPER | A | RETURNS_STATUS | unknown=>clobbers |
| BEEP-COMMAND | 03F8 | BEEP command | B | MAY_RST8_ERROR | unknown=>clobbers |
| SA-BYTES | 04C2 | SA-BYTES | A | RETURNS_CARRY | unknown=>clobbers |
| LD-BYTES | 0556 | LD-BYTES | A | RETURNS_CARRY | unknown=>clobbers |
| PIXEL-ADD | 22AA | PIXEL-ADD | A | RETURNS_STATUS | unknown=>clobbers |
| POINT | 22CB | POINT | A | RETURNS_STATUS | unknown=>clobbers |
| PLOT-SUB | 22E5 | PLOT-SUB | A | MAY_RST8_ERROR | unknown=>clobbers |
| DRAW-CONVERT | 24B7 | DRAW conversion | B | MAY_RST8_ERROR | unknown=>clobbers |
| DRAW-LINE | 24BA | lower line draw | A | MAY_RST8_ERROR | unknown=>clobbers |
| FP-TO-BC | 2DA2 | FP-to-BC | B | MAY_RST8_ERROR | unknown=>clobbers |
| FP-PRINT | 2DE3 | FP printing | B | MAY_RST8_ERROR | unknown=>clobbers |
| CALCULATE | 335B | CALCULATE | B | MAY_RST8_ERROR | unknown=>clobbers |
| INT | 36AF | INT | B | MAY_RST8_ERROR | unknown=>clobbers |
| EXP | 36C4 | EXP | B | MAY_RST8_ERROR | unknown=>clobbers |
| LN | 3713 | LN | B | MAY_RST8_ERROR | unknown=>clobbers |
| COS | 37AA | COS | B | MAY_RST8_ERROR | unknown=>clobbers |
| SIN | 37B5 | SIN | B | MAY_RST8_ERROR | unknown=>clobbers |
| TAN | 37DA | TAN | B | MAY_RST8_ERROR | unknown=>clobbers |
| ATN | 37E2 | ATN | B | MAY_RST8_ERROR | unknown=>clobbers |
| ASN | 3833 | ASN | B | MAY_RST8_ERROR | unknown=>clobbers |
| ACS | 3843 | ACS | B | MAY_RST8_ERROR | unknown=>clobbers |
| SQR | 384A | SQR | B | MAY_RST8_ERROR | unknown=>clobbers |
| POWER | 3851 | exponentiation | B | MAY_RST8_ERROR | unknown=>clobbers |

Every adopted wrapper records the source above, exact address, input/output
registers in source comments, clobbers, IY restoration and the serialization
rule. Class-B services are globally serialized and permit no cooperative yield
between state save and restoration. Any routine whose RST8/BREAK recovery path
cannot be trapped safely remains unavailable rather than escaping into BASIC.

## Rejected Class-C reuse

The kernel does not adopt BASIC MAKE-ROOM/RECLAIM, BASIC variable storage,
full BASIC execution as shell infrastructure, NEW/CLEAR/RUN as OS operations,
unrestricted POKE/OUT/USR, BASIC streams/channels as the handle layer, or the
BASIC full line editor. Replacing an otherwise safe ROM facility with RAM code
requires one of the Revision-11 replacement thresholds: unsafe error model,
workspace conflict, ABI-semantic mismatch, deterministic bad behavior, or a
measured size/performance win worth resident RAM. Cosmetic preference is not a
threshold.

## Calculator gateway

The calculator service accepts only the frozen operation set
`ADD,SUB,MUL,DIV,POW,ABS,SGN,INT,EXP,LN,SIN,COS,TAN,ASN,ACS,ATN,SQR` and executes
atomically: validate, enter the calculator critical section, save protected ROM
state, copy controlled inputs, invoke the verified operation, translate ROM
errors, copy output, restore protected state, leave the critical section, return.
There is no scheduling point inside this sequence.

The public `calc` implementation uses the architecture fallback: a ZX-UX-owned,
case-sensitive tokenizer validates the grammar before the ROM calculator is
entered. Allowed names are `pi,abs,sgn,int,sqrt,exp,ln,sin,cos,tan,asin,acos,atan`
with decimal literals, unary `+ -`, binary `+ - * / ^`, and parentheses. `rnd`
is deferred. BASIC statements, assignments, strings and unsafe names such as
memory/I/O/program-control primitives are rejected before any ROM evaluation.
Upper-case spellings are not aliases.

## Interrupt/alternate-bank classifier

| wrapper family | class | alternate-bank behavior | interrupt policy | task switch |
| --- | --- | --- | --- | --- |
| restore-IY | internal | does-not-use | no ROM call | forbidden inside wrapper |
| KEY-SCAN | A | does-not-use | interruptible outside ROM critical region | forbidden inside wrapper |
| PRINT/graphics | A | unknown=>clobbers | serialized when ROM workspace is live | forbidden inside wrapper |
| BEEPER | A | unknown=>clobbers | timing-critical; missed ticks are honest | forbidden inside wrapper |
| tape | A | unknown=>clobbers | ROM timing-critical, synchronous | forbidden inside wrapper |
| calculator/math | B | unknown=>clobbers | calculator global lock | forbidden inside wrapper |

A wrapper is fast-safe only when its frozen contract says `does-not-use` or
`uses-but-preserves` and its interrupt/workspace policy is compatible with the
current context. `clobbers` and `unknown` are unsafe for the fast path and use the
serialized safe fallback. The ISR performs no ROM calls and uses balanced
alternate-bank exchange only as OS-private scratch switching.

## ROM system-variable ownership

| variable | address | bytes | owner | rule |
| --- | ---: | ---: | --- | --- |
| ERR_NR anchor | 5C3A | implementation-defined field | KERNEL | production IY always equals 5C3A outside controlled wrapper internals |
| FRAMES | 5C78-5C7A | 3 | KERNEL | IM2 mirrors accepted frame interrupts with low-word wrap into high byte |
| UDG | 5C7B-5C7C | 2 | GRAPHICS | boot repoints to the pinned 256-byte COLD_PREFERRED UDG bank |
| calculator workspace used by approved math paths | ROM compatibility zone | bounded | CALCULATOR | saved/restored under global calculator serialization |
| tape workspace used by SA/LD-BYTES | ROM compatibility zone | bounded | TAPE | valid only during the synchronous tape critical section |
| console/graphics transient ROM workspace | ROM compatibility zone | bounded | CONSOLE/GRAPHICS | wrapper-owned only; never process ABI state |

The planned UDG bank is an allocator-owned 256-byte COLD_PREFERRED extent in
0x6000-0x7FFF; its exact runtime pointer is written to UDG only after allocation
and can never point into 0xE000-0xFFFF. No user process may depend on unspecified
BASIC system-variable contents across a syscall or scheduling point.
