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
No target source may redeclare a syscall number.

Unless a call has a documented special return, success returns carry clear with
A=`E_OK`. Failure returns carry set with A containing the frozen error number.
Wrappers restore IY=`5C3A` before returning to conforming applications.

Version 1 uses these syscall ranges:

- `00-08`: process;
- `10-1C`: namespace and ordinary I/O;
- `20-22`: pipes, duplication, ioctl;
- `30-35`: console;
- `40-46`: graphics and sound;
- `48-4B`: UDG;
- `50-53`: cassette;
- `60-65`: memory/process/time/compression information;
- `68-6E`: serialized ROM floating-point and ROM information.

Number gaps are reserved expansion space.

## Error values

`E_OK` is 0. Errors 1 through 16 are, in order: `E_INVAL`, `E_NOENT`,
`E_NOMEM`, `E_BUSY`, `E_IO`, `E_EOF`, `E_PERM`, `E_CHILD`, `E_PIPE`,
`E_TOOLONG`, `E_FORMAT`, `E_NOSPC`, `E_AGAIN`, `E_NOTSUP`, `E_INTR`, and
`E_EXIST`.

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
