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

Revision 16 is authoritative after admitted R16.00. Historical E0-P2 evidence remains bound to Revision 12 / Revision 03. This document is the executable-development summary for the current target assembler sources.

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

## Console input ABI

Physical `CAPS SHIFT + 1` (`EDIT`) is the sole tty ESC-equivalent. In ordinary
task context it decodes to the single target byte `0x1B` in both tty32 and tty64.
The same byte is returned by `SYS_CON_GETKEY`, exposed by `/dev/tty` reads, and
observed by C48 `getchar()` when stdin is the tty. No BASIC EDIT or extended-mode
token is exposed, and `CAPS SHIFT + SYMBOL SHIFT` is not an ESC alias.

Physical `CAPS SHIFT + SPACE` remains BREAK. BREAK is sampled by IM2 as cooperative
cancellation, never decodes to `0x1B`, and is distinct from EDIT. Successful
`SYS_CON_GETKEY` returns H=`0`, L=the target byte. Byte `0x1B` is input data;
this ABI assigns it no console-output control meaning.

## Time ABI

TIME1 is exactly six little-endian bytes: u32 seconds followed by u16 revision.
The seconds field is Unix-style seconds from `1970-01-01 00:00:00` and the valid
version-1 range is calendar years 1970 through 2099. Normal successful cold boot
starts at seconds `388368000` (`0x17260680`) with revision 0, so the first TIME1
record is exactly `80 06 26 17 00 00`.

`SYS_TIME_GET` takes HL as a writable six-byte TIME1 pointer. It returns `E_AGAIN`
only while the explicit wall-valid state is false; normal successful boot is already
valid. A successful get copies one atomic snapshot of seconds and revision and does
not derive either field from `SYS_TICKS`, ROM `FRAMES`, or an external clock.

`SYS_TIME_SET` is restricted to PID1. HL points to a little-endian u32 seconds value.
The call rejects values outside the 1970 through 2099 range before changing wall
state. Each successful set atomically marks the wall clock valid, increments revision
modulo 65536 even when the seconds value is unchanged, and resets the private
subsecond frame counter to zero. The first successful set after cold boot therefore
produces revision 1. There is no timezone offset or hidden host/emulator time source.

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

### Mutable RAM object record

There are exactly 32 mutable RAM object records, each exactly 20 bytes (640 bytes total).
Fixed pseudo-files/devices and pinned bootstrap metadata are separate and consume no
mutable slot. The byte layout is frozen:

| Offset | Size | Field |
| --- | ---: | --- |
| +0 | 10 | exact case-sensitive base name, NUL/zero padded when shorter than 10 bytes |
| +10 | 1 | directory ID |
| +11 | 1 | type |
| +12 | 1 | flags; only bit 0 `OBJ_PACKED` is public |
| +13 | 1 | reserved, exactly zero |
| +14 | 2 | logical length, little-endian |
| +16 | 2 | storage length, little-endian |
| +18 | 2 | allocation pointer, little-endian |

RAW records require storage length equal to logical length. PACKED records require
storage length strictly smaller than logical length. Zero-length RAW has storage
length zero and allocation pointer zero. Every nonzero payload pointer is even,
lies within `6000-DFFF`, and owns exactly storage length rounded only to the
allocator's two-byte alignment. Ordinary mutable payload allocation requests
`COLD_PREFERRED`; the shared arena allocator may fall back to FAST when COLD has no
suitable extent.

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

## Process bootstrap argument block (ARG1)

ARG1 is the immutable process-lifetime argument block supplied to `SYS_SPAWN`
and `SYS_EXEC`. The caller supplies `arg1_ptr` plus the exact `arg1_len`; the
kernel validates the complete block before any process becomes READY and copies
validated bytes into process-owned bootstrap storage outside the downward-growing
runtime stack.

ARG1 is at most 256 bytes and has this exact packed layout:

| Offset | Size | Field |
| --- | --- | --- |
| `+0` | 4 | magic bytes `ARG1` |
| `+4` | 1 | `argc`, exactly 1..16 |
| `+5` | 1 | reserved, exactly 0 |
| `+6` | 2 | exact total block length, little-endian |
| `+8` | variable | exactly `argc` NUL-terminated argument strings |

The total-length field must equal the supplied `arg1_len`; all strings must
terminate within that exact length and no trailing bytes are permitted after the
`argc`th terminator. `argv[0]` is byte-for-byte the exact non-empty command token
used to invoke the program. The complete block is rejected with `E_FORMAT` before
allocation or process publication if magic, count, reserved byte, length, string
termination, or `argv[0]` identity is invalid. `crt0` later builds the separate
`argc+1` pointer vector on the FAST process stack and appends the terminating NULL.

## Process bootstrap environment block (ENV1)

ENV1 is the immutable process-lifetime environment snapshot supplied to
`SYS_SPAWN` and `SYS_EXEC`. The caller supplies `env1_ptr` plus the exact
`env1_len`; the kernel validates the complete ENV1 block before any process becomes READY. ENV1 is at most 256 bytes and has this exact packed layout:

| Offset | Size | Field |
| --- | --- | --- |
| `+0` | 4 | magic bytes `ENV1` |
| `+4` | 1 | entry count, exactly 0..8 |
| `+5` | 1 | reserved, exactly 0 |
| `+6` | 2 | exact total block length, little-endian |
| `+8` | variable | exactly entry-count NUL-terminated `NAME=VALUE` strings |

Each name is 1..15 bytes and matches `[A-Za-z_][A-Za-z0-9_]{0,14}`. Names are
case-sensitive and unique within the block. The first `=` terminates the name;
`=` is ordinary value data after that delimiter. Each value is 0..63 target-printable bytes `0x20..0x7E`; an empty value is valid. NUL terminates the
complete `NAME=VALUE` string and is not field data. The total-length field must
equal the supplied `env1_len`; all strings must terminate inside that exact length,
and no trailing bytes are permitted after the last required terminator.

Malformed ENV1 is rejected with `E_FORMAT` before allocation or process publication. Valid ARG1 and ENV1 bytes are copied together into one process-owned immutable bootstrap allocation, in ARG1-then-ENV1 order, at most 512 payload bytes plus alignment. This allocation is separate from the downward-growing FAST runtime
stack. The logical ARG1 and ENV1 lengths remain exact even when the allocator rounds
the combined extent for alignment. Both blocks survive unchanged until process exit
or successful exec replacement. The initial user context later receives the ARG1
pointer and exact length plus the ENV1 pointer; `getenv retains the ENV1 pointer`
rather than copying strings onto the runtime stack. The process `cwd remains kernel-descriptor state` and is never encoded into ENV1 data.

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
