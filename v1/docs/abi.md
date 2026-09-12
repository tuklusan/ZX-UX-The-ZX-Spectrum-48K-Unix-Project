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

# ZX-UX Version-1 ABI

Revision 11 is authoritative. This document is the executable-development summary
for the target assembler sources.

## Address-space contract

| Region | Inclusive range | Use |
| --- | --- | --- |
| ROM | `0000-3FFF` | Original 48K ROM |
| Bitmap | `4000-57FF` | Native display bitmap |
| Attributes | `5800-5AFF` | Native display attributes |
| ROM compatibility | `5B00-5FFF` | ROM workspace/system variables |
| COLD | `6000-7FFF` | Contended allocator range |
| FAST | `8000-DFFF` | Uncontended allocator range |
| Kernel | `E000-FFFF` | Resident ZX-UX |

The resident kernel subranges are fixed: code/data `E000-FAFF`, kernel stack
`FB00-FCFF`, fast reserve `FD00-FDFC`, IM2 trampoline `FDFD-FDFF`, 257-byte IM2
table `FE00-FF00`, and emergency reserve `FF01-FFFF`.

The public syscall gateway is `E000`. The production boot gateway is `E003`.
Successful production boot runs with interrupts disabled while establishing
SP=`FD00` and does not return to BASIC.

IM2 uses I=`FE`, table byte `FD`, and the trampoline at `FDFD`. IY is
OS/ROM-reserved and has the canonical value `5C3A`. The alternate register bank is
OS-private and volatile from user code.

## Syscall convention

The complete version-1 syscall number ownership is in `v1/include/zx48ux.inc`.
No target source may redeclare a syscall number. ABI-visible syscall record
operations and offsets are shared through `v1/include/syscall.inc`.

Entry registers are `A=syscall number`, `HL=primary argument/pointer`,
`DE=secondary argument/pointer`, and `BC=count/tertiary argument`. Unless a call
has a documented special return, success returns carry clear with `HL=primary
result` and A=`E_OK`; failure returns carry set with A containing the frozen error
number and leaves HL undefined unless that call says otherwise.

AF/BC/DE/HL are volatile across a syscall; IX is preserved; IY is OS/ROM-reserved
and is restored to `5C3A` on every returning user boundary. The alternate register
bank is OS-private/volatile, I is OS-owned, and R has no preservation guarantee.

Version 1 has exactly 59 assigned syscall IDs:

| Syscall | ID |
| --- | ---: |
| `SYS_VERSION` | `0x00` |
| `SYS_EXIT` | `0x01` |
| `SYS_YIELD` | `0x02` |
| `SYS_SLEEP` | `0x03` |
| `SYS_GETPID` | `0x04` |
| `SYS_SPAWN` | `0x05` |
| `SYS_EXEC` | `0x06` |
| `SYS_WAIT` | `0x07` |
| `SYS_KILL` | `0x08` |
| `SYS_OPEN` | `0x10` |
| `SYS_CLOSE` | `0x11` |
| `SYS_READ` | `0x12` |
| `SYS_WRITE` | `0x13` |
| `SYS_SEEK` | `0x14` |
| `SYS_STAT` | `0x15` |
| `SYS_REMOVE` | `0x16` |
| `SYS_RENAME` | `0x17` |
| `SYS_LIST` | `0x18` |
| `SYS_CHDIR` | `0x19` |
| `SYS_GETCWD` | `0x1A` |
| `SYS_PACK` | `0x1B` |
| `SYS_UNPACK` | `0x1C` |
| `SYS_PIPE` | `0x20` |
| `SYS_DUP` | `0x21` |
| `SYS_IOCTL` | `0x22` |
| `SYS_CON_GETKEY` | `0x30` |
| `SYS_CON_PUTCHAR` | `0x31` |
| `SYS_CON_WRITE` | `0x32` |
| `SYS_CON_CLEAR` | `0x33` |
| `SYS_CON_GETPOS` | `0x34` |
| `SYS_CON_SETPOS` | `0x35` |
| `SYS_GFX_PLOT` | `0x40` |
| `SYS_GFX_DRAW` | `0x41` |
| `SYS_GFX_CIRCLE` | `0x42` |
| `SYS_GFX_ATTR` | `0x43` |
| `SYS_GFX_BORDER` | `0x44` |
| `SYS_GFX_POINT` | `0x45` |
| `SYS_BEEP` | `0x46` |
| `SYS_UDG_DEFINE` | `0x48` |
| `SYS_UDG_DRAW` | `0x49` |
| `SYS_UDG_GET` | `0x4A` |
| `SYS_UDG_CLEAR` | `0x4B` |
| `SYS_TAPE_SAVE` | `0x50` |
| `SYS_TAPE_LOAD` | `0x51` |
| `SYS_TAPE_VERIFY` | `0x52` |
| `SYS_TAPE_SCAN` | `0x53` |
| `SYS_MEM_INFO` | `0x60` |
| `SYS_PROC_INFO` | `0x61` |
| `SYS_TICKS` | `0x62` |
| `SYS_TIME_GET` | `0x63` |
| `SYS_TIME_SET` | `0x64` |
| `SYS_ZXPACK_INFO` | `0x65` |
| `SYS_FP_EXEC` | `0x68` |
| `SYS_FP_TO_TEXT` | `0x69` |
| `SYS_FP_FROM_TEXT` | `0x6A` |
| `SYS_ROM_INFO` | `0x6B` |
| `SYS_INT_TO_FP` | `0x6C` |
| `SYS_FP_TO_INT` | `0x6D` |
| `SYS_FP_CMP` | `0x6E` |

Every value not listed above is an unassigned expansion gap. Invalid syscall
numbers return `E_NOTSUP` before any handler-table index can be formed. Adding an
alias or consuming a gap requires a later architecture/ABI revision.

The selected dispatcher uses bounds/range checks followed by compact handler-address
tables and indirect `JP (HL)`. Certification measures that built form against the
equivalent long compare/branch chain; table indexing is never reached until the
numeric range has been validated.

## Error values

`E_OK` is 0. Errors 1 through 16 are, in order: `E_INVAL`, `E_NOENT`,
`E_NOMEM`, `E_BUSY`, `E_IO`, `E_EOF`, `E_PERM`, `E_CHILD`, `E_PIPE`,
`E_TOOLONG`, `E_FORMAT`, `E_NOSPC`, `E_AGAIN`, `E_NOTSUP`, `E_INTR`, and
`E_EXIST`. `v1/include/errno.inc` contains aliases only; it does not own a
second numeric errno table.

## Packed syscall records

`FPOP1` is exactly 8 bytes: `u8 op`, `u8 reserved=0`, `u16 lhs`, `u16 rhs`,
`u16 out`. Offsets are op=0, reserved=1, lhs=2, rhs=4, out=6. `FPOP1.op`
values are fixed: 0 INVALID, 1 ADD, 2 SUB, 3 MUL, 4 DIV, 5 POW, 6 ABS,
7 SGN, 8 INT, 9 EXP, 10 LN, 11 SIN, 12 COS, 13 TAN, 14 ASN, 15 ACS,
16 ATN, 17 SQR.

`ROMQ1` is exactly 4 bytes: `u8 index`, `u8 category`, `u16 out_ptr`, at
offsets 0, 1, and 2. Categories are 0 ALL, 1 KEYBOARD, 2 CONSOLE, 3 TAPE,
4 GRAPHICS, 5 SOUND, and 6 MATH.

`ROMOUT1` is exactly 24 bytes: `name[16]`, `u16 address`, `u8 classification`,
`u8 category`, `u16 contract_flags`, `u16 reserved=0`, at offsets 0, 16, 18,
19, 20, and 22. Classification values are 1=A, 2=B, 3=C. Name uses 1..15
visible bytes plus NUL/zero padding. Contract flag bit0 is MAY_ERROR_RESTART,
bit1 ALTREG_SENSITIVE, bit2 DISABLES_INTERRUPTS, and bit3 NONREENTRANT; all
remaining bits are zero in version 1.

All packed multibyte fields are little-endian and every reserved byte/word must be
zero on input unless a later ABI revision explicitly assigns it.

## User range validation

For each nonzero `(start,length)`, validation computes
`end_exclusive = widened(start) + widened(length)` in at least 17-bit arithmetic
(32 bits or wider in host/reference tests) before narrowing. It requires
`end_exclusive > start`, `end_exclusive <= 0x10000`, and both `start` and
`end_exclusive-1` to lie in one single permitted region.

Ordinary user buffers permit only `0x4000-0x5AFF` or `0x6000-0xDFFF`; they may
not bridge the `0x5B00-0x5FFF` protected gap and may never overlap ROM or kernel
space. Process-owned calls additionally require the whole widened range to lie in
the applicable owned allocation. If a call documents `count=0` as
non-dereferencing, the buffer pointer need not identify a readable/writable byte,
but every non-buffer argument is still validated. NUL-terminated strings are
scanned only inside the caller-valid region and the lexical maximum plus NUL.

## Process and handle limits

There are exactly eight PID slots, PID0 through PID7. PID0 is the idle context and
PID1 is the shell. Every process has eight handle slots. The system has exactly 24
open-description records. Duplication and inherited spawn handles reference an
existing open description and therefore share its logical offset.

Scheduling is cooperative. Interrupts maintain time/input state but do not perform
arbitrary user-process preemption. A CPU-bound task that never enters the kernel can
starve peers.

## Object namespace

Visible fixed directories have ABI IDs ROOT=0, BIN=1, DEV=2, ETC=3, HOME=4,
USERHOME=5, and TMP=6. SYSTEM=7 is internal bootstrap metadata and is not a
user-created directory.

Persistent object type IDs are TXT=1, BIN=2, OBJ=3, ASM=4, C=5, DAT=6, UDG=7,
GFX=8, FNT=9, CFG=10, and SYS=11. DIR=12 and DEV=13 are namespace-only types and
are invalid as persistent M48O payload types.

Names are case-sensitive and shipped user-visible names are lower-case.

## Object formats

MEX1 and OBJ1 headers are exactly 24 bytes. M48O headers are exactly 32 bytes.
All specified multibyte fields are little-endian.

MEX1 stored layout is its 24-byte header followed by image bytes followed by an
ABS16 relocation-offset table. Stored length is exact; trailing data is invalid.

OBJ1 stored layout is its 24-byte header followed by text/data, fixed-size symbol
records, and fixed-size relocation records. Stored length is exact; trailing data is
invalid.

M48O payload types and target directories must obey the architecture placement
matrix. RAW codec is 0 and ZXP1 PACKED codec is 1.

## Open flags

`O_READ=01`, `O_WRITE=02`, `O_CREATE=04`, `O_TRUNC=08`, `O_APPEND=10`, and
`O_EXCL=20`. Unknown bits are invalid. At least one of read/write is required.
TRUNC and APPEND require write; EXCL requires create.

## Allocation classes

One address-ordered allocator covers `6000-DFFF`. FAST_REQUIRED allocations are
wholly within `8000-DFFF`. COLD_PREFERRED tries `6000-7FFF` first but may use FAST.
ANY may occupy a single contiguous range crossing the `7FFF/8000` boundary.

Process stacks and pipe buffers are FAST_REQUIRED. Normal MEX1 image+BSS is ANY.
Pinned resources keep their architecture-defined class.

## Assembly coding rules

Target assembly uses one canonical documented-Z80 syntax. Unlabelled instructions
and directives are indented. Hexadecimal constants use explicit hexadecimal syntax.
Undocumented instructions are forbidden in the portable profile.

Every exported routine documents inputs, outputs, carry/flags meaning, and clobbers.
IY is never application-owned. Application state is not held persistently in the
alternate register bank. Kernel persistent state is not held only in alternate
registers.

All ROM entry points are owned by `rom_services.asm`; callers use named wrappers.
All raw ULA output is owned by `ula_io.asm`; callers update the authoritative shadow.
Screen-address calculation has one implementation rather than copied formulas.
Allocator pointer arithmetic is bounds-checked before narrowing.

Block transfer/search instructions are first-class choices for memory operations.
The implementation considers LDI/LDIR/LDD/LDDR/CPI/CPIR/CPD/CPDR where exact
semantics allow them. Small fixed transfers may use measured alternatives.

Correctness, identity, uniqueness, and security may not depend on the Z80 refresh
register. Correctness may not depend on precise ULA contention phase. Cycle records
for critical routines distinguish contended from uncontended memory access.

## Routine comment template

Exported target routines use this information near the label:

```text
; in:      register/pointer contract
; out:     register/result contract
; flags:   carry/error or other defined flag result
; clobber: exact registers and memory state
```

## Text convention

TXT, C, ASM, and CFG object content uses LF (`0A`) as the target line separator.
Target tools do not emit CRLF.
