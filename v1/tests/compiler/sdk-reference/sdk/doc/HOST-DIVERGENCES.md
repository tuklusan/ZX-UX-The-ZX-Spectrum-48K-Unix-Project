<!--
============================================================================
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
============================================================================
-->
# Host Runtime Divergences - Pre-1.0 SDK

The SDK is designed to make C48 source behavior portable while avoiding claims about
native ZX-UX facilities that have not yet been frozen or implemented.  The following
boundaries are intentional.

## 1. Host executable format

The compiler emits deterministic `C48B1` host executables.  Native ZX-UX `cc` will emit
`OBJ1` for the Z80 linker.  C48B1 contains a canonical typed executable tree and SHA-256
integrity field; it is never presented as an OBJ1 implementation.

## 2. `<c48.h>` versus `c48host.h`

P11.01 freezes the required runtime *name inventory*, while P11.41 owns the exact
built-in `<c48.h>` declarations, constants and prototypes.  P11.41 is not yet frozen in
the project repository.  The pre-1.0 SDK therefore does not invent those declarations.

`dev/src/c48host.h` is a provisional Host Game API profile used only by this SDK.  It
provides useful console, memory, graphics, UDG, heap and selected math declarations so
program development can proceed.  Its declarations must be reconciled/replaced when
P11.41 becomes authoritative.

## 3. Host filesystem mapping

Native ZX-UX has typed TXT/C objects and a 31-byte normalized path namespace.  A Windows
or Linux host filesystem has neither ZX-UX object metadata nor the same root/path
length.  The SDK therefore allows ordinary host paths for the primary source and output.

Quoted C48 includes still use exact case-sensitive 1..10-character portable basenames.
Because host files lack object-type metadata, `.c`, `.h`, and `.txt` extensions are the
SDK proxy for native TXT/C include objects.  Exact directory-entry case is checked even
on a case-insensitive host filesystem.

## 4. Process memory and stack

C48 objects and pointers execute in a logical 16-bit memory model.  The VM uses the
ZX-UX user arena range and real Spectrum screen addresses for screen backing, but it is
not a cycle-accurate loader or scheduler.  Host local-variable allocations are used to
prove C48 lifetime, alignment and pointer/provenance rules; they do not claim native
Z80 stack-frame addresses or C48_REGCALL register placement.

Native ABI register placement, even-SP call boundaries, exact stack reservation and
OBJ1/MEX1 relocation remain native compiler/linker certification work.  In particular,
the native default MEX1 process stack reserve is 512 bytes (with native `-stack` accepting
even 64..4096); the host VM uses Python call frames plus logical C48 object allocations
and does not claim to enforce that native byte-for-byte stack budget.

## 4A. Translation units and linking

The pre-1.0 SDK compiles and executes one C48 translation unit at a time.  Compatible `extern`
declarations are accepted so source can remain native-linker-ready, but C48B1 has no
host multi-object linker: an external function or object that is not defined in that
translation unit (and is not a documented host builtin) fails at host execution rather
than being resolved from another C48B1 file.  Native OBJ1 multi-module linkage remains
`ld`/Phase-11 work.

## 5. Heap

Normal host execution defaults to a 1024-byte heap ceiling, matching normal native
`crt0`.  `--heap` accepts only even values `0..8192`.  The host VM enforces the live
requested-byte ceiling but does not claim the exact metadata overhead, fragmentation,
or allocation addresses of the future native `malloc` implementation.

## 6. Runtime safety checker

The host VM deliberately diagnoses some operations that would otherwise be undefined or
unsafe on a shared-address-space Spectrum: null/dead/out-of-range dereferences,
uninitialized-byte reads, stale automatic pointers, invalid `free`, and provably
unrelated pointer ordering/subtraction.  These diagnostics make portability failures
visible; they are not a claim that native hardware can trap the same accesses.

Pointer provenance is deliberately stronger than a numeric 16-bit address. A pointer
that refers to freed storage keeps its original allocation identity and remains stale
even if a later allocation reuses the same numeric address. Raw bytes written into a
pointer object do not acquire provenance merely because they happen to equal the address
of a live object. Memory/string/UDG helpers validate the original pointer record rather
than re-inferring provenance from the address. This prevents ABA-style stale-pointer
resurrection and representation-level pointer forgery in the host safety checker.

## 6A. Host safety ceilings

Hostile source and C48B1 files are bounded before they can consume Python recursion or
unbounded host memory. `compiler/c48/limits.py` centralizes these defensive ceilings.
They are **host safety ceilings, not new C48 language rules**: P11.02/P11.42 remain the
authority for permanent native compiler/workspace capacities. The 32768-byte per-source
object bound is the already-frozen ZX-UX logical RAM-object limit; the additional host
limits exist solely to make untrusted-input failure deterministic and controlled.

The host compiler bounds parser/constant-expression/type nesting, macro expansion,
translation-unit source/tokens/AST size, and physical line size. C48B1 loading has
pre-read file-size, JSON nesting/container, AST-node, string, and type-depth ceilings.
The VM independently caps C48 function-call depth. `c48run --max-steps N` adds an
optional deterministic statement/expression execution budget for fuzzing and CI; zero
(the default) leaves ordinary interactive execution unlimited.

## 7. Display and graphics

The backing display is the exact 6912-byte Spectrum screen representation: 6144 bitmap
bytes plus 768 attribute bytes.  High-resolution graphics coordinates use Spectrum
bottom-left `y`; physical bitmap rows used by tty64/UDG storage are top-down.  INK,
PAPER, BRIGHT, FLASH, OVER and INVERSE are represented in Spectrum terms.

The graphical host frontend is Tkinter and is not a ULA/timing/contention emulator.
FLASH timing is host-wall-clock visual behavior; contention, border timing, raster
interrupts and television signal timing are outside the host profile.

## 8. Keyboard/input

`getchar()` is byte-oriented.  GUI Return maps to canonical LF (0x0A), Backspace to 8,
and Escape to 27.  Non-ASCII GUI text is ignored.  Host Shift+Space is reserved as the
Spectrum-style BREAK chord: it closes a held final frame without changing the completed
program status, or aborts a still-running GUI session with host status 130.  BREAK is a
host-frontend control rather than a byte returned by `getchar()`.  The Tk frontend displays
`Shift+Space = BREAK` below the emulated screen while execution is active and changes that
host-only footer to `Program ended - Shift+Space to close` after completion.  The footer is
not written into Spectrum screen memory.  The SDK does not emulate the raw Spectrum keyboard
matrix.

## 9. Time/scheduling

`ticks()` and `sleep()` in the provisional host API use host monotonic time and a 50-Hz
interpretation.  The host does not emulate cooperative ZX-UX scheduling, process tables,
pipes, cassette I/O or kernel syscalls.

## 10. Float5

See `FLOAT5-ORACLE.md`.  Full ROM differential certification is a bounded open item;
transcendental approximation is opt-in and non-certified.

## 11. Sound

The architecture-frozen `int beep(float duration, float pitch)` API is not exposed by
Host Game API profile 0.1 because the pre-1.0 SDK does not yet provide a portable backend that
can honestly promise its synchronous Sinclair-compatible pitch/duration contract.
No fake success/no-op implementation is supplied.
