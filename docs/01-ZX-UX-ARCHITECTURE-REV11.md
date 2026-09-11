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
# ZX-UX Architecture
## A 48K ZX Spectrum Unix-Like Multiprocessing Development Environment

(C) 2026 Supratim Sanyal
A SANYALnet Labs Hobby project
https://supratim-sanyal.blogspot.com/

Status: Architecture baseline for implementation
Revision: 11 - mechanical consolidation of Revision 9 plus double-pass-certified Revision 10 corrections
Target: Original 48K ZX Spectrum, unexpanded RAM
CPU: Z80A
Implementation language: Z80 assembly / machine code
Persistent storage: cassette tape
Interactive environment: shell + editor + assembler/linker + tiny native C compiler
Graphics: Spectrum bitmap/attribute graphics + first-class UDG support
Kernel model: cooperative multiprocessing, shared address space, no MMU


Revision-9 consolidated architectural changes:

- retains all prior Z80/Spectrum-native, ROM-maximization, standard cassette
  bootstrap, lower-case/case-sensitive userland, `vi`, C48 demo, namespace/login,
  cron/date/man, 64-column terminal, and companion-applications requirements;
- replaces the flat object namespace with a deliberately tiny fixed Unix-style
  hierarchy containing `/bin`, `/dev`, `/etc`, `/home`, `/home/<user>`, and `/tmp`;
- prompts once per cold boot for a lower-case session username of at most eight
  characters, sets `HOME=/home/<user>`, `USER=<user>`, `SHELL=/bin/sh`, and
  `PATH=/bin:.`, and starts the shell in that home directory;
- freezes `/etc/issue` and the post-boot heading to begin with the exact lines
  `© Supratim Sanyal, SANYALnet Labs` and
  `https://supratim-sanyal.blogspot.com/`;
- adds `date`, `cron`, `crontab`, and `man` with a software wall-clock model that
  honestly reflects the absence of a persistent RTC on the base 48K Spectrum;
- adds fun-first small commands including `fortune`, `banner`, `cal`, `rev`,
  `yes`, `uname`, `whoami`, and `uptime`;
- makes a Tasword-Two-like 64-column software terminal a version-1 feature,
  using a packed 4x8 fixed font, software cursor, full 64x24 logical console,
  and a 32-column fallback/debug mode;
- adds a required `font4x8` system resource and `stty` controls for 32/64-column
  text and cursor shape;
- requires `vi` to use the 64-column terminal by default with block/underline
  cursor semantics and to restore the prior terminal mode on exit;
- defines a companion applications cassette containing at least a compact word
  processor and spreadsheet built on the same MEX1/M48O/TTY interfaces;
- tightens MEX1, OBJ1, M48O, pipe-I/O, ROM `FRAMES`, and ROM UDG-state contracts
  found incomplete during the forensic Revision-5 audit;
- adds a required lower-case `beep duration,pitch` shell command with Sinclair
  BASIC-compatible duration/pitch semantics and the matching C48
  `int beep(float duration, float pitch)` API;
- adds resident `zxpack` compressed cold-object storage with one exact `ZXP1`
  format, transparent packed-object reads, direct packed-MEX1 tape execution,
  opportunistic object packing, explicit `pack`/`unpack`, and logical-versus-
  physical memory reporting; compression is never presented as virtual memory
  and never applies to live process address spaces, stacks, pipes, screen memory,
  or kernel RAM;
- keeps richer sequencer/music facilities beyond single-note BASIC-compatible
  `beep`, proportional/smaller-than-4x8 fonts, preemption, networking, and
  general-purpose directory creation, live-process compression, or transparent virtual memory for later architecture revisions.

---

# 1. Purpose

ZX-UX is a purpose-built Unix-like operating environment for the original 48K ZX Spectrum.

It is not a port of Unix, POSIX, CP/M, Fuzix, or another existing operating system. It borrows the most useful Unix ideas while being designed around the actual Spectrum hardware:

- one Z80A CPU;
- a 64 KiB CPU address space;
- 16 KiB ROM at 0x0000-0x3FFF;
- 48 KiB RAM at 0x4000-0xFFFF;
- no MMU;
- no banked RAM on the base target;
- a memory-mapped 256x192 bitmap display;
- attribute-based color;
- matrix keyboard;
- cassette storage;
- ROM routines that may be called freely;
- a hard requirement that the operating environment remain useful inside the original 48 KiB RAM.

The architecture is intended to be detailed enough to drive an ordered programming cycle.

The minimum successful system must boot on an original 48K-compatible machine from a standard Spectrum cassette sequence initiated with `LOAD ""`, display a native `SCREEN$` loading image, hand permanently from the auto-running BASIC loader into the resident machine-code kernel, present an interactive 64-column shell, request a session username and enter `/home/<user>`, run multiple cooperative tasks, provide a minimal Unix-style `/bin`, `/etc`, `/home`, `/dev`, `/tmp` namespace, save and restore programs and data to cassette, keep eligible inactive RAM objects in compressed `zxpack` form without pretending compressed bytes are directly addressable, provide graphics and UDG services, provide BASIC-compatible `beep`, provide `date` plus small `cron`/`crontab` support, edit source text with `vi`, assemble Z80 programs, compile a useful subset of C, link/load programs, execute them without requiring RAM expansion, ship with readable C48 demonstration sources that users can edit, compile, link, and run for fun, and accept a companion applications cassette containing at least a word processor and spreadsheet.

---

# 2. Design Principles

## 2.1 Accuracy over imitation

Unix semantics are adopted only where they fit the hardware.

Do not waste memory pretending the Spectrum has:

- memory protection;
- virtual memory;
- transparent compression of live/sleeping process address spaces or stacks;
- per-process address spaces;
- demand paging;
- a hardware timer suitable for arbitrary preemptive scheduling;
- a random-access cassette filesystem.

Where classic Unix behavior does not fit, ZX-UX shall provide a simpler well-defined substitute.

## 2.2 Machine-native implementation

The kernel, shell, device services, editor, assembler, linker, compiler, and core utilities execute as Z80 machine code.

Development source may be maintained as Z80 assembly and assembled on a host during bootstrap development. "Machine-code implementation" does not require hand-entering opcodes.

## 2.3 ROM reuse is the default

The original 48K Spectrum ROM is part of the platform and shall be treated as a
16 KiB resident read-only system library.

The default engineering rule is:

    do not implement in RAM what the immutable 48K ROM can already provide
    safely, correctly, and with an acceptable calling contract.

ROM entry points shall be isolated behind a ROM service module so that:

- hard-coded ROM addresses do not spread through the codebase;
- register and flag contracts are documented in one place;
- ROM system-variable and workspace dependencies are explicit;
- non-reentrant ROM facilities can be serialized by the kernel;
- unsafe BASIC interpreter facilities cannot become an accidental kernel bypass;
- a future replacement implementation can be substituted without changing the
  user ABI.

ROM reuse is therefore not limited to cassette and graphics. Phase 0 must
inventory keyboard, console, screen, graphics, sound, cassette, numeric
conversion, floating-point calculation, mathematical functions, string/number
conversion, and the BASIC expression scanner before any equivalent RAM routine
is approved.

## 2.4 Cooperative multiprocessing

ZX-UX is a real multiprocessing environment in the sense that multiple tasks may exist, block, wake, communicate, and make forward progress.

Scheduling is cooperative.

A task changes state only when it calls yield, sleeps, blocks on a pipe, blocks waiting for a child, blocks waiting for keyboard input, exits, or explicitly invokes another blocking kernel service.

No arbitrary user instruction is interrupted for a process context switch.

The maskable interrupt handler may update time and input state, but version 1 shall not preempt arbitrary user code.

## 2.5 Shared address space

All tasks share the same physical 48 KiB RAM. There is no memory protection.

A defective task can corrupt the kernel or another task. This is an explicit hardware limitation, not an implementation defect.

The loader nevertheless enforces ownership and bounds for well-behaved programs.

## 2.6 Cassette is persistent object storage, not a fake disk

Cassette is sequential.

ZX-UX shall not claim random access or deletion semantics that the medium cannot provide.

The live shell works primarily with volatile RAM objects. Cassette commands persist and restore named objects using Spectrum-compatible tape transport.

## 2.7 Small stable ABI

The kernel ABI shall be smaller than the shell or C library API.

Programs use a fixed kernel call gateway and stable numeric syscall IDs. High-level convenience functions are implemented in user libraries where possible.

## 2.8 Z80 and Spectrum hardware features are architecture, not incidental optimization

ZX-UX is intentionally designed around the documented Z80 instruction set and
the 48K Spectrum memory/bus topology.

The implementation shall exploit, where they improve correctness, code size, or
measured performance:

- Z80 IM 2 interrupt vectoring;
- the alternate AF'/BC'/DE'/HL' register bank;
- IX/IY index-register roles chosen explicitly by the ABI;
- process stacks as complete cooperative-resume frames;
- block transfer/search instructions (`LDI`, `LDIR`, `LDD`, `LDDR`, `CPI`,
  `CPIR`, `CPD`, `CPDR`);
- compact relative branches and `DJNZ`;
- 16-bit arithmetic in HL/DE/BC;
- `EX`, `EXX`, and conditional returns where contracts permit them;
- bit-test/set/reset and rotate/shift instructions;
- indirect dispatch through `JP (HL)` where a jump table is smaller/clearer;
- the Spectrum's contended versus uncontended RAM regions;
- 16-bit Z80 I/O addressing for Spectrum keyboard-row selection;
- `HALT` as the normal idle primitive between maskable interrupts.

This requirement does not authorize undocumented opcodes in the version-1
portable baseline. CPU-specific optimization remains subordinate to exact ABI,
ROM, interrupt, and memory-safety contracts.

## 2.9 Unix-style naming and case semantics

ZX-UX adopts the normal Unix expectation that names are case-sensitive and
that standard command names are lower-case.

Version-1 rules are:

- object/file names preserve the exact character case supplied by the user;
- namespace lookup is byte-for-byte case-sensitive; no automatic case folding
  is permitted;
- `hello.c`, `Hello.c`, and `HELLO.C` are three distinct names if all three
  exist;
- all ZX-UX-shipped shell commands, utilities, tools, executables, demo names,
  and source filenames use lower-case names;
- shell command lookup is case-sensitive, so `ls` names the shipped utility and
  `LS` does not silently resolve to it;
- C48 identifiers obey C's case-sensitive identifier rules;
- `calc` exposes lower-case user-facing function names such as `sin`, `cos`,
  `sqrt`, and `pi`; any translation to Sinclair BASIC/ROM tokens happens behind
  the safe gateway;
- conventional environment-variable names such as `PATH` may remain upper-case
  because that is itself normal Unix convention; variable lookup remains
  case-sensitive;
- internal binary-format magics, object-type tags, syscall constants, errno
  symbols, Z80 register names, and ROM routine names are not user filenames and
  may retain their conventional upper-case notation.

Cassette persistence preserves the same exact case. A request to `load hello.c`
must not match a tape object named `HELLO.C` merely because the Spectrum ROM or
an implementation helper could perform case-insensitive comparison.

## 2.10 Standard Spectrum cassette distribution

The official version-1 release shall look and load like a normal 48K Spectrum
cassette program.

The bootstrap prefix is intentionally conventional:

    auto-running Sinclair BASIC loader
    native 6912-byte SCREEN$ loading image
    resident kernel CODE block

After `RANDOMIZE USR` transfers control, ZX-UX owns the machine and the rest
of the tape is interpreted by the kernel as ZX-UX cassette objects.

The BASIC loader is not the operating environment and is not part of the
case-sensitive Unix-like command namespace. Its purpose is only to use the ROM's
standard Spectrum loading conventions to establish the screen and kernel before
a permanent machine-code handoff.

Successful ZX-UX boot never returns to the BASIC caller. The boot entry
switches to the dedicated kernel stack and abandons the BASIC return frame.

The distribution must therefore be usable by an ordinary Spectrum user as:

    LOAD ""

followed by pressing PLAY on the cassette source. No manual `RANDOMIZE USR`,
manual address entry, or separate machine-code monitor is required.

## 2.11 Dense text is a native Spectrum feature

Version 1 includes two terminal renderers:

    tty64   64 columns x 24 rows, software 4x8 fixed font
    tty32   32 columns x 24 rows, normal-width fallback/debug text

`tty64` is the normal interactive shell/editor mode. It is inspired by the
well-established Tasword/Taswide technique of fitting two four-pixel character
cells into each eight-pixel Spectrum display byte. It is not a hardware text
mode; ZX-UX renders directly into the native bitmap.

The renderer, cursor, scrolling, font format, and attribute compromises are
part of the version-1 console contract and are specified in Section 13.

## 2.12 Compressed cold storage is not virtual memory

ZX-UX uses software compression only at kernel-controlled storage boundaries.
The Z80 always fetches instructions and reads/writes active data from ordinary
physical addresses; no software component can intercept arbitrary CPU memory-bus
cycles on a stock 48K Spectrum.

Version 1 may store eligible inactive RAM objects and cassette payloads in the
`ZXP1` packed representation defined in Section 27.3. A packed object has a
logical byte length visible to programs and a smaller physical storage length
visible to the allocator. `SYS_READ` presents the logical byte stream; execution
of a packed MEX1 object decodes directly into its final uncompressed process
allocation.

The following are never compressed in version 1:

- resident kernel RAM and ROM-compatibility workspace;
- screen bitmap/attributes;
- active process image/BSS/heap;
- process stacks and ARG1/ENV1 bootstrap allocations;
- pipe buffers and live kernel wait structures;
- pinned `font4x8`, UDG working bank, and other resources after they have been
  loaded into their required runtime form;
- arbitrary sleeping/suspended process pointer graphs.

Compression therefore increases stored-object density and cassette capacity,
not the maximum directly addressable live working set. A program cannot allocate
more live addressable memory merely because its bytes would compress well.

---

# 3. Hardware Baseline

## 3.1 CPU

Target CPU:

    Zilog Z80A, approximately 3.5 MHz on the original 48K Spectrum.

The version-1 timing baseline is the standard PAL/UK 50 Hz 48K machine. NTSC
variants and clones with different frame timing require a separate compatibility
profile and must not silently reuse the 50-frame-per-second wall-clock constant.

The version-1 ABI deliberately uses the documented Z80 architecture rather
than treating the processor as a generic 8080-like core.

Architecturally significant facilities are:

    primary registers       AF BC DE HL
    alternate registers     AF' BC' DE' HL'
    index registers          IX IY
    stack pointer            SP
    interrupt vector         I
    refresh register         R
    interrupt modes          IM 0 / IM 1 / IM 2
    block transfer/search    LDI/R, LDD/R, CPI/R, CPD/R
    exchanges                EX, EXX, EX AF,AF'
    16-bit arithmetic        ADD/ADC/SBC on register pairs where documented
    bit operations           BIT/SET/RES and rotate/shift families
    relative control flow    JR and DJNZ
    indirect jump            JP (HL), JP (IX), JP (IY)
    I/O                      IN/OUT including 16-bit port selection through BC

ZX-UX freezes IM 2 for its own periodic interrupt handling in version 1.

Normal MEX1 applications do not own the I register, interrupt mode, IY, or the
alternate register bank. Those resources are part of the OS/ROM ABI described
later.

The R refresh register may contribute to non-security pseudorandom seeding, but
no correctness, identity, or security decision may depend on R.

## 3.2 Address space and contention topology

The CPU address map is:

    0x0000-0x3FFF   16 KiB Spectrum ROM
    0x4000-0xFFFF   48 KiB RAM

The base architecture never assumes RAM under ROM or bank switching.

On the original 48K Spectrum, the lower 16 KiB RAM bank at 0x4000-0x7FFF is
contended with the ULA during active display fetches. CPU accesses in that
region can therefore incur display-phase-dependent wait states. RAM at
0x8000-0xFFFF is uncontended.

ZX-UX treats this as an allocator and placement property:

    0x6000-0x7FFF   CONTENDED/COLD arena
    0x8000-0xDFFF   FAST arena
    0xE000-0xFFFF   FAST resident kernel

The display and ROM-compatibility areas below 0x6000 remain unavailable for
general allocation.

Code, process stacks, pipe buffers, scheduler-visible hot metadata, compiler
hot workspace, and latency-sensitive data should prefer FAST memory. Source
text, inactive RAM objects, large cold buffers, and other low-frequency data
may use CONTENDED/COLD memory.

Correctness must never depend on contention timing. Contention classification
is an optimization/property of placement, not a scheduling clock.

## 3.3 Display RAM

The Spectrum display occupies:

    0x4000-0x57FF   6144-byte bitmap
    0x5800-0x5AFF    768-byte attribute map

Total display RAM:

    6912 bytes

The bitmap layout is the native Spectrum interleaved scan-line arrangement. The kernel graphics layer shall own one tested pixel-address conversion routine rather than duplicating the address formula throughout the system.

The display remains a 256x192 bitmap even in 64-column terminal mode. `tty64`
therefore uses 64 logical character cells of 4 pixels each across the same 256
pixels, with 24 rows of 8 pixels each. Two adjacent logical text columns share
one hardware attribute cell because Spectrum color attributes remain 8x8.

## 3.4 ROM workspace compatibility zone

ROM services depend on standard Spectrum system variables and workspace.

ZX-UX reserves:

    0x5B00-0x5FFF

as the ROM compatibility/workspace zone in version 1.

The kernel may use individually verified bytes inside this area only after the ROM contract for those locations has been documented. Programs may not allocate from this region.

## 3.5 I/O

Version 1 must support:

- Spectrum keyboard;
- screen bitmap;
- screen attributes;
- border;
- beeper;
- EAR input;
- MIC output;
- cassette load/save.

Joystick, printer, Interface 1, Microdrive, serial adapters, mouse, and other extensions are outside the version-1 hardware requirement.

---

# 4. Fixed Version-1 Memory Map

The version-1 map is a Spectrum/Z80 architectural contract. Changing it after
userland ABI freeze requires an explicit architecture revision.

    0x0000-0x3FFF   Spectrum ROM                         16384 bytes
    0x4000-0x57FF   screen bitmap                        6144 bytes
    0x5800-0x5AFF   screen attributes                     768 bytes
    0x5B00-0x5FFF   ROM compatibility/workspace          1280 bytes
    0x6000-0x7FFF   CONTENDED/COLD task/object arena      8192 bytes
    0x8000-0xDFFF   FAST task/object arena               24576 bytes
    0xE000-0xFFFF   FAST resident kernel                  8192 bytes

The task/RAM-object arena remains 32 KiB total, but it is now divided by bus
contention class rather than by ownership.

The resident kernel is permanently placed in uncontended RAM. This prevents the
ULA from inserting display-contention wait states into normal scheduler, pipe,
allocator, syscall, and interrupt execution.

## 4.1 Kernel-region fixed sub-layout

The 8 KiB kernel region reserves the following fixed areas:

    0xE000-0xFAFF   kernel code/data pool                 6912 bytes
    0xFB00-0xFCFF   dedicated kernel stack                 512 bytes
    0xFD00-0xFDFC   kernel fast data / reserve             253 bytes
    0xFDFD-0xFDFF   IM2 vector trampoline                    3 bytes
    0xFE00-0xFF00   IM2 repeated-vector table              257 bytes
    0xFF01-0xFFFF   interrupt/emergency scratch/reserve    255 bytes

The IM2 table is 257 bytes so every possible low interrupt-vector byte can read
a complete two-byte pointer inside the initialized table.

The table is filled with byte 0xFD. With I=0xFE, every vector lookup resolves
to 0xFDFD. Location 0xFDFD contains exactly a three-byte absolute jump to the
canonical ZX-UX interrupt handler.

Conceptually:

    LD A,0xFD
    fill 0xFE00..0xFF00 with A

    0xFDFD: JP zx48_interrupt

    LD A,0xFE
    LD I,A
    IM 2

The exact initialization sequence must execute with interrupts disabled and is
verified in Phase 0/1 before IM2 is enabled.

The first six bytes of the ordinary kernel code/data pool are ABI/bootstrap
trampolines:

    0xE000-0xE002   JP zx_syscall_dispatch
    0xE003-0xE005   JP zx_boot_main

Therefore:

    0xE000 = 57344   public syscall gateway
    0xE003 = 57347   production BASIC `RANDOMIZE USR` boot entry

`zx_boot_entry` at 0xE003 is frozen for the version-1 tape format. The jump
trampoline keeps the externally visible address stable if the internal boot
routine moves during kernel development.

## 4.2 Kernel code/data budget

The fixed IM2 table/trampoline and dedicated kernel stack reduce the ordinary
code/data budget below 8 KiB. Planning targets are:

    syscall gateway / entry              128 bytes
    scheduler/process/open-description   896 bytes
    allocator                            448 bytes
    pipe subsystem                       640 bytes
    ROM wrappers                         704 bytes
    console/keyboard/ULA + tty64         832 bytes
    graphics primitives                  608 bytes
    UDG subsystem                        192 bytes
    cassette object layer                672 bytes
    RAM object namespace                 640 bytes
    resident zxpack codec/manager        384 bytes
    interrupt/time/error core            448 bytes
    tables/strings                       192 bytes
                                           --------
                                           6784 bytes

The ordinary 0xE000-0xFAFF code/data pool is exactly 6912 bytes, leaving 128
bytes of unassigned growth margin inside that pool. The separate 0xFD00-0xFDFC
and 0xFF01-0xFFFF areas remain fixed fast/emergency reserves and are not counted
as ordinary code/data growth space.

The release gate is not merely "kernel <= 8192 bytes". The linked image must
respect every fixed subrange above and may not overlap the IM2 table, kernel
stack, or trampoline.

## 4.3 UDG storage

Reserve a 32-slot UDG bank:

    32 glyphs x 8 bytes = 256 bytes

The default implementation loads/initializes this bank in one pinned
`COLD_PREFERRED` 256-byte arena allocation rather than consuming ordinary kernel
code/data space. The kernel owns the allocation and repoints the ROM `UDG`
system variable to it during boot. The ABI does not expose its physical address.

## 4.3A Packed 4x8 terminal font resource

The 64-column font is not permanently linked into the 6912-byte ordinary
kernel code/data pool. The production tape carries a required M48O system
resource named:

    font4x8

The kernel loads and pins it in a `FAST_REQUIRED` arena allocation before PID
1 is scheduled. The payload format is `F4X8`:

    offset  size  field
    0       4     magic = "F4X8"
    4       1     version = 1
    5       1     first code = 0x20
    6       1     glyph count = 96
    7       1     flags = 0
    8       384   packed glyph data

Total payload size is exactly 392 bytes.

Each glyph is 4 bytes representing eight 4-bit scan rows. In each byte the high
nibble is the earlier scan row and the low nibble is the following scan row.
Within a row, bit 3 is the leftmost pixel and bit 0 the rightmost pixel.

Codes 0x20-0x7E cover the normal printable ZX-UX/ASCII-like repertoire. Code
0x7F is the Spectrum copyright character `©`, allowing the required boot banner
to render without consuming a UDG.

The pinned font allocation counts against the 32 KiB arena and is visible in
`mem` as kernel/system arena use. Failure to load or validate `font4x8` from an
official version-1 system tape is a boot failure. Debug/development builds may
explicitly select `tty32` without this resource.

## 4.3B `/bin` tape catalog resource

The required boot resource `bincat` is a compact catalog, not executable code.
It catalogs the complete shipped `/bin` command set, including the boot `sh`; an
entry need not be physically later than the catalog on sequential tape.
Its payload begins:

    0..3    magic = "BCAT"
    4       version = 1
    5       entry count, 0..223
    6..7    reserved = 0

Each entry is 12 bytes:

    0..9    exact lower-case command base name, NUL padded
    10      object type; version 1 requires BIN
    11      flags; bit0 = tape-backed, remaining bits zero

The payload length must equal `8 + entry_count*12`; entry_count >223 is invalid so the
worst-case visible `/bin` union remains within the 255-entry SYS_LIST contract. The
official version-1 system tape uses exactly entry_count=40 and payload length=488, with
exactly the Section-20.5 required external-command name set. Each name uses the same
1..10-byte NUL-or-full-ten rule as M48O; bytes after an embedded NUL are zero. Entries
are sorted in exact bytewise name order and contain no duplicates. Flags must equal
0x01 in version 1. The catalog does not contain tape offsets or payload lengths because
cassette is sequential; it only establishes command existence.
If a cataloged command is not currently resident, execution invokes the forward
M48O search and may prompt for rewind/reposition.

`bincat` itself is pinned COLD system metadata and does not consume one of the
32 mutable RAM-object entries.

## 4.4 Contention-aware arena

The allocator manages one logical 32 KiB arena with two physical classes:

    COLD/CONTENDED   0x6000-0x7FFF   8192 bytes
    FAST             0x8000-0xDFFF  24576 bytes

Allocation requests carry one of three placement policies:

    FAST_REQUIRED
    COLD_PREFERRED
    ANY

Mandatory FAST_REQUIRED allocations:

- process stacks;
- pipe circular buffers;
- scheduler/process wait structures allocated outside the resident table;
- latency-sensitive graphics/console scratch.

COLD_PREFERRED examples:

- source text;
- inactive RAM objects, including RAW objects awaiting opportunistic `zxpack` compaction;
- editor backing text not under active scan;
- large immutable data tables;
- cassette staging data when timing is performed by ROM and no concurrent hot
  access is required.

ANY is used where both regions are semantically equivalent. Normal MEX1
image+BSS allocations use ANY so a large compiler/editor can exploit the full
contiguous 0x6000-0xDFFF arena. Such an allocation may lie entirely in FAST,
entirely in CONTENDED, or cross 0x7FFF/0x8000; correctness may not depend on
which placement occurs. The allocator should prefer a placement that avoids
fragmenting scarce FAST-only space.

`mem` shall report FAST and CONTENDED free totals and largest-free-block values
separately as well as combined totals.

Allocation failure remains a normal recoverable condition. The allocator must
never silently fall back from FAST_REQUIRED to contended RAM. Before reporting
an ordinary ANY/COLD allocation failure, the allocator may make one bounded
`zxpack` compaction pass over eligible closed RAW objects as specified in
Section 27.3.8; failure to obtain useful space remains a normal E_NOMEM result.

# 5. Boot Model

## 5.1 Standard production tape bootstrap prefix

The official version-1 cassette starts with exactly three conventional Spectrum
logical files in this order:

    1. `zx48ux`    auto-running BASIC program
    2. `zx48uxscr` 6912-byte SCREEN$ loading image
    3. `kernel`    8192-byte CODE file saved for 0xE000

At the raw Spectrum tape level, each of these logical files is represented by
the normal ROM-compatible header block followed by its data block. The
architecture's tape-order lists name logical files/objects rather than counting
those low-level header/data blocks separately.

All three tape-header names are lower-case and fit the Spectrum's ten-character
header-name field.

The post-kernel fixed M48O bootstrap-resource prefix is, in order:

    sh
    font4x8
    issue
    crontab
    bincat

The five resource contracts are exact:

    sh        type BIN  target BIN       becomes PID 1
    font4x8   type FNT  target SYSTEM    pinned FAST_REQUIRED F4X8 resource
    issue     type TXT  target ETC       installed as /etc/issue
    crontab   type CFG  target ETC       installed as /etc/crontab
    bincat    type SYS  target SYSTEM    pinned BCAT metadata

The official version-1 logical payloads are byte-frozen. `issue` is exactly these
target bytes, including the final LF; the leading copyright glyph is target byte 0x7F:

    <0x7F> Supratim Sanyal, SANYALnet Labs<LF>
    https://supratim-sanyal.blogspot.com/<LF>
    48K. One Z80. No excuses.<LF>

The official `crontab` logical payload is zero bytes and is therefore always RAW
(codec 0, physical length 0, logical length 0). The official `bincat` contains exactly
the 40 required external commands in Section 20.5, including `sh`, sorted in exact
bytewise name order. Its entry_count is exactly 40 and its payload length is exactly
488 bytes (`8 + 40*12`). The release builder rejects any mismatch.

`bincat` is a compact read-only catalog of the lower-case `/bin` commands shipped
on the system tape, including the earlier boot `sh`, so `/bin` lookup can distinguish a known tape-backed
executable from a nonexistent command without keeping all command payloads
resident.

The kernel loads these five resources sequentially before PID 1 is scheduled.
Additional tools, utilities, demos, and demo sources follow.

The three-file native prefix (`zx48ux`, `zx48uxscr`, `kernel`) uses Spectrum
ROM/BASIC tape semantics and is not wrapped in M48O. The five-resource
post-kernel bootstrap prefix (`sh`, `font4x8`, `issue`, `crontab`, `bincat`) is
M48O and begins only after the kernel takes ownership. Any nonempty eligible payload among those five M48O resources may be RAW or ZXP1
PACKED when its logical payload, type, target, name, and CRC satisfy the exact resource
contract. The official zero-length `crontab` is necessarily RAW.

## 5.2 Canonical BASIC autoloader

The production loader is intentionally small and conventional. Its semantic
source is:

    10 BORDER 0: PAPER 0: INK 7: CLS
    20 CLEAR 24575
    30 LOAD "" SCREEN$
    40 LOAD "" CODE
    50 RANDOMIZE USR 57347

The program is saved with auto-start at line 10, conceptually:

    SAVE "zx48ux" LINE 10

The constants are architecture-derived:

    24575 = 0x5FFF
    57344 = 0xE000
    57347 = 0xE003

`CLEAR 24575` keeps the BASIC interpreter, its stack, and transient workspace
below the ZX-UX task/kernel ownership boundary at 0x6000.

`LOAD "" SCREEN$` loads the next native screen block into:

    0x4000-0x57FF   6144 bitmap bytes
    0x5800-0x5AFF    768 attribute bytes
                       ----
                       6912 bytes total

`LOAD "" CODE` loads the following `kernel` block back to the address carried
in its Spectrum tape header. The production kernel block is saved for 0xE000
and is exactly 8192 bytes long.

`RANDOMIZE USR 57347` enters the fixed three-byte boot trampoline at 0xE003.
The public syscall entry remains independently fixed at 0xE000.

Sinclair BASIC keyword capitalization in this five-line bootstrap program is a
property of the bootstrap language/listing convention. It does not weaken the
lower-case, case-sensitive ZX-UX shell/userland contract.

## 5.3 Loading screen contract

The official loading artwork is a native 6912-byte Spectrum screen image.
Working source-tree name:

    assets/loading.scr

Its production tape header name is:

    zx48uxscr

The screen should be recognizably ZX-UX/Spectrum artwork and may include a
small feature summary such as `sh`, `vi`, `cc`, graphics, UDGs, and cassette
storage, but its exact artwork is not an ABI.

The image is functional boot feedback, not merely decoration:

- it proves that the display block loaded correctly before the kernel payload;
- it remains visible while the 8192-byte kernel block is loading;
- after handoff it remains visible while the kernel initializes and loads `sh`;
- the kernel must not clear the bitmap merely as a side effect of low-level
  initialization;
- once PID 1 is ready, `sh` may clear/replace the loading image and present the
  normal ZX-UX banner and `$` prompt.

The loading image itself is never copied into the 32 KiB user arena; it already
occupies the hardware screen at 0x4000-0x5AFF.

## 5.4 BASIC-to-kernel ownership handoff

Boot has three ownership phases.

Phase A - ROM/BASIC bootstrap:

    ROM and BASIC own their normal system variables and temporary workspace;
    CLEAR has limited BASIC's RAM ceiling to 0x5FFF;
    SCREEN$ is resident at 0x4000-0x5AFF;
    kernel bytes are loaded at 0xE000-0xFFFF.

Phase B - permanent USR handoff:

    BASIC executes RANDOMIZE USR 57347;
    zx_boot_entry immediately executes DI;
    the BASIC SP/return frame is no longer authoritative;
    SP is replaced with 0xFD00 so the dedicated kernel stack grows downward
    through 0xFCFF-0xFB00;
    control never returns through the original BASIC USR return address.

Phase C - ZX-UX ownership:

    ZX-UX preserves/re-establishes only the Phase-0-approved Spectrum ROM
    system-variable state needed by its ROM wrappers;
    BASIC program/workspace bytes are treated as disposable bootstrap state,
    although 0x5B00-0x5FFF remains reserved from user allocation as the ROM
    compatibility/workspace zone;
    kernel initialization completes;
    the cassette object loader reads the immediately following M48O object `sh`;
    `sh` becomes PID 1;
    normal scheduling begins and BASIC is never resumed.

A normal successful ZX-UX shutdown does not attempt to reconstruct the BASIC
interpreter state. Returning to BASIC is outside the version-1 OS contract.

## 5.5 Kernel initialization after zx_boot_entry

After `RANDOMIZE USR 57347`, the boot path is:

1. `DI`;
2. set SP to 0xFD00, establishing the dedicated kernel stack at
   0xFB00-0xFCFF;
3. validate expected 48K environment and exact kernel placement at
   0xE000-0xFFFF;
4. validate the fixed 0xE000 syscall and 0xE003 boot trampolines;
5. establish IY=0x5C3A (ERR_NR), the frozen production-ROM compatibility anchor;
6. normalize only the documented ROM system variables/workspace required by
   approved wrappers; do not blindly clear 0x5B00-0x5FFF;
7. clear kernel BSS/state without touching display RAM, required ROM workspace,
   kernel stack, or vector ranges;
8. initialize FAST and CONTENDED arena free lists;
9. initialize process and pipe tables;
10. initialize the RAM object directory;
11. initialize the resident ZXP1 decoder/encoder manager and its zeroed
    four-byte pack-candidate bitset;
12. initialize the ROM cassette wrapper and M48O bootstrap-object reader;
13. initialize graphics state, ULA output shadow, and default attributes without
    clearing the already loaded SCREEN$;
14. initialize 32 UDG slots;
15. write the 0xFE00-0xFF00 IM2 table with 0xFD;
16. install `JP zx48_interrupt` at 0xFDFD;
17. set `I=0xFE`;
18. select IM 2;
19. initialize alternate-register/ROM-interrupt protection state;
20. create PID 0 idle/kernel context;
21. construct the canonical cold-boot process blocks for PID 1: ARG1 has
    `argc=1` and the sole string `sh`, while ENV1 is a valid zero-entry block;
    load and validate the immediately following lower-case M48O executable object
    `sh` from cassette using those blocks; RAW is parsed normally and PACKED is
    decoded by the continuous-history MEX1 streaming loader without creating a
    persistent `/bin/sh` RAM object;
22. load and validate `font4x8`; a PACKED tape representation is decoded directly
    into its final pinned 392-byte `FAST_REQUIRED` F4X8 allocation and the packed
    transport bytes are discarded;
23. load `issue` into `/etc/issue` and validate its required first two lines;
    its mutable ETC object may remain RAW or validated PACKED storage;
24. load `crontab` into `/etc/crontab` and validate its syntax or empty state;
    its mutable ETC object may remain RAW or validated PACKED storage;
25. load and validate `bincat`; a PACKED tape representation is decoded directly
    into final pinned COLD BCAT metadata and the packed transport bytes are
    discarded;
26. initialize `tty64` as the default interactive console using `font4x8`;
27. create the already validated/allocated `sh` image as PID 1 with cwd ROOT and
    canonical cold-boot ARG1/ENV1; allocate one `/dev/tty` read open description for
    handle 0 and one `/dev/tty` write description referenced by both handles 1 and 2,
    set `tty_input_owner_pid=1`, and prove all reference counts/ownership before first
    scheduling; once login succeeds, `sh` maintains its mutable session environment
    (`USER`, `HOME`, `SHELL`, `PATH`) separately and uses that table to construct child
    ENV1 snapshots; `$?` is separate shell status state and is never an ENV1 entry;
28. `EI`;
29. enter the scheduler.

The IM2 table/trampoline, boot trampolines, `sh`, `font4x8`, `issue`,
`crontab`, `bincat`, and ownership bounds are validated before interrupts are
enabled. Any mismatch is a boot failure.

## 5.6 Production tape creation

The host bootstrap tooling shall create the release image deterministically.
Conceptually, the native Spectrum source operations represented by the first
three blocks are:

    SAVE "zx48ux" LINE 10
    SAVE "zx48uxscr" SCREEN$
    SAVE "kernel" CODE 57344,8192

The build does not require a human to type these commands. `tools-host/maketap`
constructs equivalent TAP/TZX blocks from the canonical BASIC loader tokens,
`assets/loading.scr`, and linked kernel image, then appends the ordered M48O
object stream beginning with `sh`.

The builder must reject:

- a loading screen whose payload is not exactly 6912 bytes;
- a kernel whose payload is not exactly 8192 bytes;
- a kernel not linked for 0xE000-0xFFFF;
- a boot entry other than 0xE003 for the version-1 format;
- a bootstrap filename exceeding the Spectrum header limit;
- a first M48O object other than exact lower-case `sh`;
- a second M48O object other than exact lower-case `font4x8` with a valid F4X8
  payload;
- third/fourth/fifth M48O bootstrap resources other than exact lower-case
  `issue`, `crontab`, and `bincat` with their required types/formats;
- case-folded or upper-case substitutions for required ZX-UX object names;
- a post-kernel bootstrap resource whose RAW/PACKED M48O metadata does not decode
  to the exact required logical type/target/name/format;
- a PACKED bootstrap resource using any codec other than ZXP1.

`maketap` may ZXP1-pack any post-kernel M48O resource when the packed payload is
strictly smaller. It never compresses the native BASIC, SCREEN$, or 8192-byte
`kernel` files because ZX-UX does not exist yet to decode them.

## 5.7 Boot failure

Errors before the permanent USR handoff use the Spectrum ROM/BASIC loader's
normal tape error behavior because ZX-UX is not yet running.

Errors after `zx_boot_entry` has taken ownership display:

    PANIC <code>

plus a compact textual reason where possible. A missing, mistyped, mis-targeted, or corrupt member of the five-resource bootstrap prefix must produce an explicit boot failure rather than falling through into BASIC or jumping into uninitialized RAM.

The machine then halts in a safe loop or enters a separately specified kernel
recovery path. Version 1 does not return to BASIC after ownership transfer.

---

# 6. Kernel Execution Model

## 6.1 Task states

Each process has exactly one state. The values below are also the ABI-visible
`SYS_PROC_INFO` state IDs:

    0 FREE
    1 READY
    2 RUNNING
    3 SLEEPING
    4 WAIT_INPUT
    5 WAIT_PIPE_READ
    6 WAIT_PIPE_WRITE
    7 WAIT_CHILD
    8 ZOMBIE

`SYS_PROC_INFO.flags` exposes only bit0 CANCEL_PENDING in version 1; remaining
bits are zero even if the kernel descriptor has additional private flags.

Only one process is RUNNING at a time.

## 6.2 Process limit

Version 1 supports a maximum of 8 process-table entries.

PID 0 is reserved for the kernel idle context. PID 1 is normally the shell. Therefore at most seven user-visible process records exist simultaneously.

The process count is bounded independently from available RAM; process creation also fails when there is insufficient arena memory.

## 6.3 Process descriptor

A process descriptor contains, at minimum:

    pid
    parent_pid
    state
    flags
    image_base
    image_size
    stack_low
    stack_high
    saved_sp
    exit_status
    wait_object
    handles[8]          open-description IDs or 0xFF
    wake_tick
    cwd_directory_id
    name[10]
    owned_allocation metadata

The canonical runnable CPU context is not duplicated in the descriptor. It is
materialized on the process's own FAST stack. `saved_sp` is the scheduler's
resume token. Kernel-private process flags include STARTED, initially zero at
successful spawn and set immediately before the scheduler first restores that
process. STARTED is deliberately not exposed through `SYS_PROC_INFO.flags`; it
exists so cancellation can discard a spawned-but-never-run child without letting
its user instructions execute.

PC is already represented by the return address on that stack. Primary
registers and IX are pushed into the same frame at a cooperative scheduling
point. IY is global OS/ROM state, and the alternate register bank is not part of
the conforming MEX1 task ABI.

Target descriptor size:

    <= 56 bytes per process

The ten-byte process-name field uses the same NUL-or-full-ten convention as the
object namespace, so `ps` can reproduce any legal executable base name exactly.
Eight descriptors therefore target no more than 448 bytes. The 24 open-description
records target at most 12 bytes each (288 bytes), leaving the remainder of the fixed
896-byte scheduler/process/open-description planning budget for scheduler/global state.

## 6.4 Z80-native context switching

A context switch occurs only at a kernel-controlled cooperative scheduling
point.

Conforming task state that must survive a switch is saved on its FAST stack:

    AF
    BC
    DE
    HL
    IX
    return PC already present on stack

IY is reserved by the OS/ROM ABI and is not task-local.

AF'/BC'/DE'/HL' are OS-private/volatile and are not task-local. MEX1 programs
must not use `EXX` or `EX AF,AF'` expecting values to survive a syscall or
interrupt.

Conceptual switch path:

    PUSH AF
    PUSH BC
    PUSH DE
    PUSH HL
    PUSH IX
    LD   (current.saved_sp),SP

    ; scheduler selects next descriptor

    LD   SP,(next.saved_sp)
    POP  IX
    POP  HL
    POP  DE
    POP  BC
    POP  AF
    RET

The final implementation may reorder pushes for size/cycle reasons, but the
stack-frame format must be documented and tested byte-for-byte.

The kernel does not save I, R, or interrupt mode per process. Conforming MEX1
programs may not change I, IM mode, or permanently disable interrupts.

## 6.5 Scheduler

Scheduling policy:

    cooperative round-robin among READY tasks

Algorithm:

1. current task enters kernel scheduling point;
2. save current context;
3. if still runnable, mark READY;
4. scan process table from next PID position;
5. wake expired SLEEPING tasks;
6. select next READY task;
7. if none, select PID 0 idle;
8. mark selected task RUNNING;
9. restore selected context;
10. return into selected task.

No priority system is required in version 1.

## 6.6 Idle task

PID 0 scans/wakes timer sleepers, polls keyboard/event state where required,
never allocates user memory, and never exits. Its normal blocking idle sequence is:

    EI
    HALT

followed by a scheduler/event check after the next IM2 interrupt. Busy-spin idle
loops are not permitted in the version-1 baseline. No path intentionally waits in
HALT while maskable interrupts are disabled.

## 6.7 Timer

The Spectrum maskable interrupt provides a periodic heartbeat.

On the 50 Hz version-1 baseline, every accepted frame interrupt performs the
small fixed timing update: increment the 32-bit frame counter modulo 2^32, mirror
the ROM `FRAMES` value as specified in Section 14.8A, accumulate one software
wall-clock second for each 50 accepted frame interrupts while wall time is valid,
and update sleep/cursor/event flags. IM2 always performs only the minimum direct
keyboard-matrix reads needed to recognize the Phase-0-frozen BREAK chord; full key
translation, repeat processing, line editing, and console dispatch remain ordinary
kernel/task-context work.

It does not perform arbitrary process preemption.

Tick counter:

    32-bit unsigned frame count

Wraparound comparisons must use modular arithmetic. Long ROM critical sections
that disable interrupts (notably tape and ROM BEEPER) cause missed frame ticks;
the clock contract reports this honestly rather than fabricating elapsed time.

---

# 7. Process Creation and Program Loading

## 7.1 No fork()

Version 1 does not implement Unix fork().

There is no address-space duplication mechanism and insufficient RAM for a general copy-on-fork model.

The process API is:

    spawn()
    exec()
    wait()
    kill()
    exit()
    yield()
    sleep()

## 7.2 spawn()

spawn() creates a new process from a relocatable executable object.

It resolves the named executable, validates its header, determines memory requirements,
atomically allocates image+BSS, FAST stack, and immutable ARG1/ENV1 bootstrap storage,
loads/relocates the image, creates the process descriptor including inherited cwd,
constructs the initial context frame, and marks the process READY. A successful
`SYS_SPAWN` does not itself yield or run the child; the caller continues until its next
explicit scheduling/blocking point. This guarantee lets `sh` finish pipe/TTY ownership
wiring after it has obtained all child PIDs and before any new child executes.

## 7.3 exec()

exec() replaces the current process image while preserving PID, parent, inherited handles where allowed, and shell pipeline wiring where allowed.

The old image is not released until the replacement image has passed all validation and required allocation has succeeded. Failure is atomic.

## 7.4 wait()

wait(pid) blocks cooperatively until the target child becomes ZOMBIE or the target is invalid/not a child.

wait(-1) waits for any child.

## 7.5 exit()

exit(status):

1. reparents every still-live direct child to PID 1 (unless the exiting process is PID 1,
   whose special shutdown rule requires no live PID2..7);
2. closes every live handle slot, releasing open-description references/endpoints;
3. releases non-shared allocations;
4. stores exit status;
5. marks process ZOMBIE;
6. wakes its waiting parent;
7. schedules another task.

The process descriptor is reclaimed when its current parent waits. Orphans are therefore
made ordinary PID1 children and are reaped by the shell's bounded scan; there is no
second hidden orphan table.

---

# 8. Executable Format

Because processes share one address space and may be loaded at different
addresses, normal executables are relocatable.

Format name:

    MEX1 - Micro Executable version 1

The stored MEX1 byte stream is:

    24-byte header
    image bytes
    ABS16 relocation-offset table

Header:

    offset  size  field
    0       4     magic = "MEX1"
    4       1     format version = 1
    5       1     flags; version 1 requires 0
    6       2     header size = 24
    8       2     image size
    10      2     bss size
    12      2     entry offset within image
    14      2     minimum FAST stack size
    16      2     relocation count
    18      2     relocation-table offset
    20      2     CRC-16/CCITT-FALSE of every stored byte after the 24-byte header
    22      2     CRC-16/CCITT-FALSE of full 24-byte header with bytes 22..23 zero

All multi-byte fields are unsigned little-endian. `header size` is included so
a later format revision can be rejected rather than misparsed.

Version-1 file layout invariants:

    image offset             = 24
    relocation-table offset = 24 + image_size
    relocation-table bytes  = relocation_count * 2
    total stored length      = relocation_table_offset + relocation_count*2

No trailing bytes are permitted in a version-1 MEX1 object. BSS bytes are not
stored; the loader allocates and zero-fills them immediately after the loaded
image in process data space.

## 8.1 ABS16 relocations

Each relocation-table entry is a two-byte little-endian offset into the stored
image. It identifies a 16-bit word whose link-time value is relative to image
base zero.

For every relocation entry the loader must prove:

    relocation_count == 0 or image_size >= 2
    offset <= image_size - 2
    stored_word <= image_size + bss_size
    relocated_value = stored_word + actual_image_base
    relocated_value <= 0xFFFF

then write the relocated value back to the image word. Duplicate or overlapping relocation words, unsorted offsets, values that overflow
16 bits, and offsets outside the image are `E_FORMAT`. After the first entry, each
offset must be at least `previous_offset+2`; the linker emits offsets in that exact
non-overlapping increasing order.

References to fixed ROM addresses or the fixed syscall gateway are absolute and
must not appear in the MEX1 relocation table.

For a RAW RAM-resident MEX1 object, CRC validation covers the complete stored
body (image bytes plus relocation entries) before patching. A PACKED RAM-resident
BIN uses the continuous-history streaming path in Section 8.1A. The sequential
tape-backed execution path is separately specified in Section 19.4A. Both packed
paths may patch only an uncommitted private image while streaming relocations and
discard that image if any final CRC/length check fails. In every path failure is
externally atomic and no partially validated process becomes READY.

## 8.1A PACKED RAM-resident MEX1 execution

A mutable `/bin` or user BIN object may itself be ZXP1 PACKED by `zxpack`. `spawn`
and `exec` must therefore execute that object transparently without first
materializing a second full RAW MEX1 object.

The loader allocates one 272-byte COLD_PREFERRED streaming-decoder state/history
and begins decoding at logical offset zero. The first 24 logical bytes are copied
into a fixed small kernel header scratch area and validated as MEX1. The loader
proves the RAM-object `logical_length` equals the MEX1 `total stored length`, then
atomically reserves image+BSS, FAST stack, and ARG1/ENV1 allocations. Decoder
history is preserved continuously across the separately parsed 24-byte header,
image, and relocation table so a legal BACKREF in the image may refer to logical
bytes emitted in the header.

Image bytes decode directly into the final uncommitted image allocation while the
MEX1 body CRC is accumulated. Relocation entries are then decoded in increasing
order and may patch only that private image after each entry passes the Section
8.1 checks. At physical end the decoder must have consumed exactly the packed
object's `storage_length`, emitted exactly its `logical_length`, and the MEX1
body/header CRCs must match. Only then is BSS zeroed/finalized and the process
allowed to become READY (or replace the current image for `exec`). Any failure,
including inability to allocate the 272-byte decoder state, returns the relevant
error, frees only private allocations, and leaves the PACKED RAM object unchanged.

RAW RAM-resident MEX1 keeps the simpler validate-before-copy/relocate path. The
PACKED path does not change the object's representation and requires no second
full logical executable copy.

## 8.2 Allocation and entry contract

The loader atomically allocates:

    image + bss       ANY; relocatable and semantically valid across the complete
                      contiguous 0x6000-0xDFFF arena
    process stack     FAST_REQUIRED, minimum_stack_size + 64 bootstrap bytes
    ARG1+ENV1 block   ANY, at most 512 payload bytes plus alignment

The fixed additional 64 stack bytes cover the initial scheduler/context frame,
the maximum 17-entry `argv` pointer vector (16 arguments plus terminating NULL),
and `crt0` bootstrap scratch. `minimum_stack_size` is therefore the application's
guaranteed usable stack budget, not a number that silently includes loader
bookkeeping.

ARG1 and ENV1 are not placed in the downward-growing runtime stack. They live in
a separate process-owned immutable bootstrap allocation that remains valid for
the process lifetime. This lets `argv` pointers refer directly to ARG1 strings
without those strings being overwritten by later stack growth.

The image is loaded first, relocations applied, BSS zeroed, and initial stack
frame constructed only after every required allocation succeeds.

On first instruction:

    HL = pointer to validated ARG1 block
    BC = total ARG1 block length
    DE = pointer to validated ENV1 block
    A  = 0

SP points to the assigned FAST task stack.

IY contains the frozen 0x5C3A (ERR_NR) ROM-compatible anchor and must be preserved.
The alternate register bank is undefined to the application and may be changed
by interrupts/syscalls. Conforming MEX1 code must not depend on it.

The executable exits only through SYS_EXIT or the runtime's exit wrapper; a
plain `RET` from the entry point is redirected by crt0 to SYS_EXIT rather than
returning into arbitrary loader state.

## 8.3 Header/allocation validation

Before allocating executable storage, the loader must prove all of the following:

    header_size == 24
    flags == 0
    image_size >= 1
    entry_offset < image_size
    image_size + bss_size <= 32768
    relocation_table_offset == 24 + image_size
    total_stored_length == relocation_table_offset + relocation_count*2
    total_stored_length <= 32768
    minimum_stack_size >= 64
    minimum_stack_size <= 4096

The selected image base plus `image_size+bss_size` must remain wholly within
0x6000-0xDFFF. Every arithmetic operation used for these checks is widened before
comparison so a malformed 16-bit field cannot wrap into apparent validity.

## 8.3A Overflow-safe MEX1 arithmetic

All MEX1 calculations are done in widened arithmetic before comparison or narrowing:

    24 + image_size
    relocation_count * 2
    relocation_table_offset + relocation_count*2
    image_size + bss_size
    actual_image_base + image_size + bss_size
    stored_word + actual_image_base

Any intermediate value outside its required mathematical range is E_FORMAT even if
its low 16 bits would satisfy a later comparison.

The existing 32768-byte arena and entry/relocation rules remain unchanged.

## 8.4 Process argument block (ARG1)

The entry value in HL points to a packed, read-only-at-entry ARG1 block and BC
contains its exact total byte length. The shell/loader builds this block after
quote removal and escape processing, so applications never need to reconstruct
shell quoting.

ARG1 format:

    offset  size  field
    0       4     magic = "ARG1"
    4       1     argc, 1..16
    5       1     reserved = 0
    6       2     total block length, little-endian
    8       ...   exactly argc NUL-terminated argument strings

`argv[0]` is the exact command token used to invoke the program. No argument may
contain NUL. The complete ARG1 block is at most 256 bytes. `crt0` builds an
`argc+1` pointer vector on the process FAST stack, terminates it with NULL, and
then calls one of the two permitted C48 entry forms: `int main(void)` or
`int main(int argc, char **argv)`.

## 8.5 Process environment block (ENV1)

DE points to a packed environment snapshot:

    offset  size  field
    0       4     magic = "ENV1"
    4       1     entry count, 0..8
    5       1     reserved = 0
    6       2     total block length, little-endian
    8       ...   exactly count NUL-terminated NAME=VALUE strings

The complete ENV1 block is at most 256 bytes. Each name is 1..15 bytes and must
match ASCII `[A-Za-z_][A-Za-z0-9_]{0,14}`. Each value is 0..63 bytes drawn only
from target printable bytes 0x20..0x7E; the empty value is valid. Names are
case-sensitive and unique within the block. NUL is forbidden in both fields;
`=` is forbidden in a name but is ordinary data in a value. The loader validates
all lexical, count, uniqueness, and total-length rules before a process becomes READY. ARG1 and ENV1 share the separate process-owned immutable
bootstrap allocation described in Section 8.2 and remain valid until process
exit/exec. `crt0` records the ENV1 pointer for `getenv()` rather than copying the
strings onto the runtime stack. The process working directory is kept in the
kernel descriptor, not encoded in ENV1.

---

# 9. Kernel Call ABI

## 9.1 Entry method

ROM owns the low RST vectors. ZX-UX therefore uses a fixed call gateway in
uncontended kernel RAM rather than replacing a ROM restart.

Version-1 fixed entry:

    0xE000 = zx_syscall gateway

User programs invoke:

    LD A,syscall_number
    ...
    CALL 0xE000

The address is frozen as part of the MEX1 ABI.

The dispatcher shall prefer a compact validated handler-address table and an
indirect `JP (HL)` over a long compare/branch chain when measurement confirms
the table is smaller or faster. Invalid syscall numbers return E_NOTSUP without
indexing outside the table.

## 9.2 Register convention

On entry:

    A   syscall number
    HL  primary argument / pointer
    DE  secondary argument / pointer
    BC  count / tertiary argument

Optional complex arguments are passed through a packed structure pointed to by
HL.

On return success:

    Carry = 0
    HL    = primary result
    A     = 0 unless syscall documents otherwise

On return failure:

    Carry = 1
    A     = errno
    HL    = undefined unless syscall documents otherwise

ABI ownership:

    AF BC DE HL   volatile across syscall
    IX            preserved across syscall
    IY            OS/ROM-reserved; must remain at 0x5C3A (ERR_NR)
    AF'/BC'/DE'/HL' OS-private/volatile; unavailable to conforming MEX1 code
    I             OS-owned IM2 base register
    R             no preservation guarantee

Carry is intentionally the primary success/failure channel so tiny callers can
use `RET C`, `RET NC`, `JR C`, and `JR NC` without constructing memory result
objects.

The kernel must restore IY=0x5C3A (ERR_NR) before returning to user code if
a ROM wrapper temporarily changed it.

## 9.3 Error codes

Version-1 errno values are fixed:

    0   E_OK
    1   E_INVAL
    2   E_NOENT
    3   E_NOMEM
    4   E_BUSY
    5   E_IO
    6   E_EOF
    7   E_PERM
    8   E_CHILD
    9   E_PIPE
    10  E_TOOLONG
    11  E_FORMAT
    12  E_NOSPC
    13  E_AGAIN
    14  E_NOTSUP
    15  E_INTR
    16  E_EXIST

Error numbers are ABI-stable after version 1 release.

---

# 10. Version-1 Syscall Table

Version-1 numbering is fixed:

    0x00  SYS_VERSION
    0x01  SYS_EXIT
    0x02  SYS_YIELD
    0x03  SYS_SLEEP
    0x04  SYS_GETPID
    0x05  SYS_SPAWN
    0x06  SYS_EXEC
    0x07  SYS_WAIT
    0x08  SYS_KILL

    0x10  SYS_OPEN
    0x11  SYS_CLOSE
    0x12  SYS_READ
    0x13  SYS_WRITE
    0x14  SYS_SEEK
    0x15  SYS_STAT
    0x16  SYS_REMOVE
    0x17  SYS_RENAME
    0x18  SYS_LIST
    0x19  SYS_CHDIR
    0x1A  SYS_GETCWD
    0x1B  SYS_PACK
    0x1C  SYS_UNPACK

    0x20  SYS_PIPE
    0x21  SYS_DUP
    0x22  SYS_IOCTL

    0x30  SYS_CON_GETKEY
    0x31  SYS_CON_PUTCHAR
    0x32  SYS_CON_WRITE
    0x33  SYS_CON_CLEAR
    0x34  SYS_CON_GETPOS
    0x35  SYS_CON_SETPOS

    0x40  SYS_GFX_PLOT
    0x41  SYS_GFX_DRAW
    0x42  SYS_GFX_CIRCLE
    0x43  SYS_GFX_ATTR
    0x44  SYS_GFX_BORDER
    0x45  SYS_GFX_POINT
    0x46  SYS_BEEP

    0x48  SYS_UDG_DEFINE
    0x49  SYS_UDG_DRAW
    0x4A  SYS_UDG_GET
    0x4B  SYS_UDG_CLEAR

    0x50  SYS_TAPE_SAVE
    0x51  SYS_TAPE_LOAD
    0x52  SYS_TAPE_VERIFY
    0x53  SYS_TAPE_SCAN

    0x60  SYS_MEM_INFO
    0x61  SYS_PROC_INFO
    0x62  SYS_TICKS
    0x63  SYS_TIME_GET
    0x64  SYS_TIME_SET
    0x65  SYS_ZXPACK_INFO

    0x68  SYS_FP_EXEC
    0x69  SYS_FP_TO_TEXT
    0x6A  SYS_FP_FROM_TEXT
    0x6B  SYS_ROM_INFO
    0x6C  SYS_INT_TO_FP
    0x6D  SYS_FP_TO_INT
    0x6E  SYS_FP_CMP

Number gaps are deliberate expansion space.

`SYS_BEEP` accepts HL = pointer to a five-byte C48/Spectrum duration
value and DE = pointer to a five-byte C48/Spectrum pitch value. It implements
the Section-17 BASIC-compatible single-note service synchronously.

`SYS_FP_EXEC` is the kernel boundary for Spectrum-ROM calculator operations.
User programs do not manipulate the ROM calculator stack directly. The syscall
accepts an operation code plus pointers to ZX-UX five-byte floating values,
performs the ROM operation atomically, and copies the result back to
caller-owned memory.

`SYS_ROM_INFO` exposes safe read-only ROM-service metadata to the `rom`
diagnostic command. It is not an arbitrary ROM-call primitive.

## 10.1 Exact syscall argument contracts

All user pointers are 16-bit addresses. For normal buffer/record syscalls an
ABI-valid user range must lie wholly in 0x4000-0x5AFF (the explicitly shared display)
or 0x6000-0xDFFF (the user arena); it may not overlap ROM, the protected ROM
compatibility/workspace region 0x5B00-0x5FFF, or kernel 0xE000-0xFFFF. Syscalls that
operate on process-owned objects additionally validate the documented ownership/access
rule rather than treating arbitrary shared RAM as authority. Packed records are
byte-packed and little-endian; reserved bytes must be zero. Before side effects, the
kernel validates the complete fixed record and every referenced pointer/range. Unless
stated otherwise, success/failure follows Section 9.2.

Process calls:

    SYS_VERSION     no args; HL=0x0100 for ABI version 1.0
    SYS_EXIT        L=8-bit exit status; does not return on success
    SYS_YIELD       no args
    SYS_SLEEP       HL -> readable u32 relative tick count in 50-Hz frames;
                    0 returns immediately, values >0x7FFFFFFF return E_INVAL
    SYS_GETPID      no args; HL=PID

`SYS_SPAWN` and `SYS_EXEC` use HL -> `PROC1`:

    +0  u16 path_ptr       NUL-terminated executable path
    +2  u16 arg1_ptr
    +4  u16 arg1_len
    +6  u16 env1_ptr
    +8  u16 env1_len
    +10 u8  stdin_handle
    +11 u8  stdout_handle
    +12 u8  stderr_handle
    +13 u8  flags          bit0 ALLOW_TAPE; remaining bits zero
    +14 u16 reserved       must be 0

`ALLOW_TAPE=0` means resolution is RAM-resident only; a catalog-only TAPE_BACKED
executable returns E_AGAIN without moving the cassette. `ALLOW_TAPE=1` authorizes the
sequential direct-execution path in Section 19.4A. The kernel itself never prints an
interactive PLAY/rewind prompt: the caller must obtain user consent/repositioning before
setting this bit. Unknown flag bits are E_INVAL.

`SYS_SPAWN` requires all three named handles to be valid 0..7 in the parent. On
success the child receives them as child handles 0,1,2 by incrementing references to
the same open descriptions; child handles 3..7 start free. The parent retains its own
handle slots. HL returns the child PID. If no PID slot in 2..7 is FREE, `SYS_SPAWN` returns E_AGAIN before tape movement
or process allocation. A resolved non-BIN object or malformed MEX1 returns E_FORMAT;
an absent object returns E_NOENT; insufficient arena memory returns E_NOMEM. `SYS_EXEC` requires the three handle bytes to
be 0xFF, preserves the current process's complete 0..7 handle table/PID/cwd, and
honors the same ALLOW_TAPE policy; it does not return on success. ARG1/ENV1 are
validated against Section 8 before the old process image is released.

`SYS_WAIT` uses HL -> `WAIT1`:

    +0  i16 pid            -1 means any child
    +2  u16 status_ptr     writable one-byte status destination

It blocks as necessary and returns the reaped child PID in HL. `pid=-1` with no
current child and a specific nonexistent/nonchild PID both return E_CHILD without
blocking.

`SYS_KILL` uses H=0,L=target PID and requests version-1 cooperative cancellation.
PID 0 and PID 1 are not valid targets. PID 1 may cancel any live PID 2..7; another
process may cancel only its own direct child, otherwise E_PERM. A target that is
READY but whose private STARTED flag is still zero is terminated atomically without
ever executing: its owned handles/allocations are released as for `exit`, it becomes
ZOMBIE with status 130, and a waiting parent is awakened. For an already-started
READY/SLEEPING/WAIT_* target, the kernel sets CANCEL_PENDING; a blocked target is
made READY so its interrupted kernel boundary can return E_INTR. Cancellation
remains cooperative after first execution: target code may observe/handle E_INTR,
while the standard C48 runtime exits with status 130 at its cancellation safe
points. Killing a nonexistent/ZOMBIE target returns E_NOENT.

Handle/object calls:

    SYS_OPEN        Section 11.2: HL=path, C=flags, B=create type
    SYS_CLOSE       H=0, L=handle
    SYS_READ        E=handle, D=0, HL=buffer, BC=count; HL=bytes read
    SYS_WRITE       E=handle, D=0, HL=buffer, BC=count; HL=bytes written
    SYS_SEEK        E=handle, D=0, HL=absolute offset; HL=new offset
    SYS_REMOVE      HL=NUL-terminated path
    SYS_CHDIR       HL=NUL-terminated directory path
    SYS_GETCWD      HL=buffer, BC=capacity; writes a terminating NUL and returns
                    HL=path bytes excluding NUL; E_NOSPC if capacity < path_len+1
    SYS_PACK        HL=NUL-terminated path; atomically attempts ZXP1 packing of
                    one eligible RAM object; PACKED is a no-op success; HL=physical
                    bytes saved (0 means already packed or no smaller representation)
    SYS_UNPACK      HL=NUL-terminated path; atomically materializes one packed RAM
                    object as RAW; HL=logical object length

`SYS_REMOVE` applies only to a mutable RAM object. If any live open description
references that object it returns E_BUSY. DIR, DEV, PINNED_SYSTEM, TAPE_BACKED, and
SYS metadata return E_PERM. Successful removal is atomic, frees its committed payload,
clears any zxpack candidate bit for the slot, and then frees the table entry.

`SYS_RENAME` uses HL -> `REN1` (`u16 old_path_ptr`, `u16 new_path_ptr`). It
operates only on mutable RAM objects. Source and destination paths are fully
resolved/validated before mutation; moving across fixed directories is allowed
only when the destination directory accepts the source object's existing type.
If old and new resolve to the exact same path, success is a no-op. A case-only
rename is valid when no distinct destination object occupies the target exact
name.

If a distinct mutable RAM object already exists at the destination,
`SYS_RENAME` provides Unix-like atomic replacement: neither source nor destination
may have any live open description (otherwise E_BUSY); after all placement/allocation-
table checks pass, the destination directory entry is replaced by the source metadata
in one commit step, the old destination payload is then freed, and the old source name
disappears. A pre-commit failure leaves both objects unchanged. DIR, DEV,
PINNED_SYSTEM, TAPE_BACKED, and SYS metadata cannot be source or replacement
destination and return E_PERM. Because rename only changes bounded metadata and
ownership of existing payload allocations, it never copies or recompresses object data.

`SYS_STAT` uses HL -> `STAT1`:

    +0 u16 path_ptr
    +2 u16 out_ptr         -> 10-byte STATOUT1

`STATOUT1` is exactly:

    +0  u8  type
    +1  u8  flags
    +2  u16 logical_length
    +4  u16 storage_length
    +6  u8  directory_id
    +7  u8  state
    +8  u16 reserved=0

For RAW RAM objects storage_length equals logical_length; for PACKED RAM objects
it is the smaller ZXP1 byte length. For non-RAM states that have no resident
payload (TAPE_BACKED/PSEUDO), storage_length is 0xFFFF/0 respectively.

`SYS_LIST` uses HL -> `LIST1`:

    +0 u16 directory_path_ptr
    +2 u8  zero-based index
    +3 u8  reserved=0
    +4 u16 out_ptr         -> 16-byte LISTOUT1

`LISTOUT1` is `name[10], type, flags, length(u16), state, directory_id`. The call
returns HL=1 for indices 0..254 that name a visible entry and HL=0 at the first
index past the final entry; index 255 is reserved as an unconditional terminator
and always returns HL=0. Entries are enumerated in ascending unsigned-bytewise
case-sensitive base-name order. `/bin` first forms the resident-RAM/BCAT union with
resident exact-name shadowing, then sorts that visible union by the same order.

Pipe/device calls:

    SYS_PIPE        HL -> two writable u8 handle slots; returns HL=0

`SYS_DUP` uses HL -> `DUP1`: `u8 source, u8 destination`. Destination 0xFF means
allocate the lowest free handle; otherwise it names exact handle 0..7. HL returns
the resulting handle number.

`SYS_IOCTL` uses HL -> `IOCTL1`: `u8 handle, u8 request, u16 arg_ptr`. Each
request defines the exact pointed argument size; TTY requests are those in
Section 13.5.

Console calls:

    SYS_CON_GETKEY  no args; H=0,L=byte; tty-owner rule applies
    SYS_CON_PUTCHAR H=0,L=byte
    SYS_CON_WRITE   HL=buffer, BC=count; HL=bytes written
    SYS_CON_CLEAR   no args
    SYS_CON_GETPOS  H=row, L=column
    SYS_CON_SETPOS  H=row, L=column

Graphics/sound calls:

    SYS_GFX_PLOT    H=x, L=y
    SYS_GFX_DRAW    HL -> four bytes x1,y1,x2,y2
    SYS_GFX_CIRCLE  HL -> three bytes x,y,radius
    SYS_GFX_ATTR    H=selector, L=value
                     selector 0 INK, 1 PAPER, 2 BRIGHT, 3 FLASH,
                              4 INVERSE, 5 OVER
    SYS_GFX_BORDER  H=0,L=color
    SYS_GFX_POINT   H=x,L=y on entry; H=0,L=0/1 on success
    SYS_BEEP        HL=duration-float pointer, DE=pitch-float pointer

UDG calls:

    SYS_UDG_DEFINE  C=slot, B=0, HL=8-byte source
    SYS_UDG_GET     C=slot, B=0, HL=8-byte destination
    SYS_UDG_DRAW    HL -> three bytes slot,row,col
    SYS_UDG_CLEAR   H=0,L=slot

Tape calls:

    SYS_TAPE_SAVE   HL=NUL-terminated path
    SYS_TAPE_LOAD   HL=NUL-terminated requested path
    SYS_TAPE_VERIFY HL=NUL-terminated path
    SYS_TAPE_SCAN   HL -> writable 32-byte M48O-header buffer; consumes exactly
                    one next M48O object (header plus payload) and returns HL=1.
                    Cassette has no reliable physical EOF indication: scanning ends
                    only when the caller stops/cancels it or a ROM transport/error
                    condition occurs; BREAK/user cancellation maps to E_INTR.

Information/time calls:

`SYS_MEM_INFO` uses HL -> writable 16-byte `MINFO1`:

    +0 u16 fast_free
    +2 u16 fast_largest
    +4 u16 cold_free
    +6 u16 cold_largest
    +8 u16 total_free
    +10 u16 live_allocations
    +12 u16 pinned_bytes
    +14 u8 process_count
    +15 u8 reserved=0

For `MINFO1`, `total_free` is exactly `fast_free + cold_free`; `live_allocations` is
the number of currently allocated arena extents (process image/BSS, stacks/bootstrap,
mutable object payloads, pipe buffers, packed-reader/encoder transients, and pinned
font/UDG/BCAT allocations, but not fixed kernel RAM); `pinned_bytes` is the allocator-
rounded arena payload bytes currently owned by pinned system resources; and
`process_count` is the number of non-FREE PID 1..7 entries, excluding PID 0. The
official boot pinned logical allocation bytes are 392 + 256 + 488 = 1136 before
allocator metadata.

`SYS_ZXPACK_INFO` uses HL -> writable 20-byte `ZPINFO1`:

    +0  u32 logical_object_bytes
    +4  u16 physical_object_bytes
    +6  u32 bytes_saved
    +10 u8  packed_object_count
    +11 u8  raw_object_count
    +12 u16 packed_reader_state_bytes
    +14 u16 pack_attempts_since_boot
    +16 u16 pack_successes_since_boot
    +18 u16 reserved=0

All totals concern mutable RAM-object storage only; process memory, pinned runtime
resources, pipes, and kernel RAM are excluded. `logical_object_bytes` and
`bytes_saved` are 32-bit because 32 compressed objects can represent more than
65535 logical bytes even though physical object storage cannot exceed the 32 KiB
arena. `bytes_saved` equals `logical_object_bytes-physical_object_bytes` and must never
underflow. `pack_attempts_since_boot` and `pack_successes_since_boot` are unsigned
16-bit event counters and wrap modulo 65536 without affecting current-state totals.

`SYS_PROC_INFO` uses HL -> `PINFOQ1`: `u8 pid, u8 reserved=0, u16 out_ptr`. The
16-byte output is `pid,parent,state,flags,name[10],owned_bytes(u16)`, where
`owned_bytes` is the current total of that process's image+BSS, FAST stack, and immutable
ARG1/ENV1 bootstrap allocations. Querying a FREE/nonexistent PID returns E_NOENT; PID 0
reports parent=0xFF.

    SYS_TICKS       HL -> writable u32 frame count modulo 2^32

`SYS_TIME_GET` uses HL -> writable 6-byte `TIME1` and returns E_AGAIN while wall
time is unset:

    +0 u32 wall_seconds    local-session seconds since 1970-01-01 00:00:00
    +4 u16 revision

`SYS_TIME_SET` uses HL -> readable u32 wall seconds. It validates the supported
1970..2099 range, atomically sets wall time valid, resets the private 0..49
subsecond frame accumulator to zero, and increments the 16-bit revision modulo
65536. Revision starts at 0 after cold boot; the first successful set therefore
produces revision 1.

Calculator/ROM calls:

`SYS_FP_EXEC` uses HL -> `FPOP1`: `u8 op, u8 reserved=0, u16 lhs, u16 rhs,
u16 out`; unary operations require rhs=0.

`SYS_FP_TO_TEXT` uses HL=five-byte value, DE=buffer, BC=capacity; writes the ROM-
canonical decimal rendering plus terminating NUL and returns HL=text bytes excluding
NUL; E_NOSPC if capacity including NUL is unavailable.

`SYS_FP_FROM_TEXT` uses HL=text, DE=five-byte output, BC=exact text length; input
need not be NUL terminated. Before entering ROM it accepts exactly one decimal
numeric literal with no whitespace or BASIC tokens: optional leading `+`/`-`; then either digits with an optional `.` and zero or more
following digits, or `.` followed by one or more digits; then an optional `e`/`E`
exponent with optional sign and at least one exponent digit. At least one mantissa digit
is mandatory. Anything else is E_INVAL.

`SYS_INT_TO_FP` uses HL -> 6-byte `ITOF1`:

    +0 u16 value
    +2 u8  is_signed       0 unsigned, 1 signed two's-complement
    +3 u8  reserved=0
    +4 u16 out_float_ptr   writable five-byte result

`SYS_FP_TO_INT` uses HL -> 6-byte `FTOI1`:

    +0 u16 in_float_ptr
    +2 u8  is_signed       0 unsigned, 1 signed
    +3 u8  reserved=0
    +4 u16 out_u16_ptr

FP-to-int truncates toward zero. Unsigned results must be 0..65535; signed results
must be -32768..32767; an out-of-range/invalid value returns E_INVAL without writing
the destination.

`SYS_FP_CMP` uses HL -> 6-byte `FCMP1`:

    +0 u16 lhs_float_ptr
    +2 u16 rhs_float_ptr
    +4 u16 out_i8_ptr

On success it writes exactly signed byte -1, 0, or +1. All three conversion/compare
calls copy input operands into controlled kernel/ROM calculator workspace before
writing results, so documented output aliasing is safe.

`FPOP1.op` numeric values are fixed: 0 invalid, 1 ADD, 2 SUB, 3 MUL, 4 DIV,
5 POW, 6 ABS, 7 SGN, 8 INT, 9 EXP, 10 LN, 11 SIN, 12 COS, 13 TAN, 14 ASN,
15 ACS, 16 ATN, 17 SQR. Binary operations 1..5 require nonzero `lhs` and `rhs`;
unary operations 6..17 require nonzero `lhs` and `rhs=0`. `out` is always nonzero.
Output may alias either input because the kernel copies required operand bytes into its
controlled calculator workspace before writing the result.

`SYS_ROM_INFO` uses HL -> `ROMQ1`: `u8 index, u8 category, u16 out_ptr`. Category
values are 0 ALL, 1 KEYBOARD, 2 CONSOLE, 3 TAPE, 4 GRAPHICS, 5 SOUND, 6 MATH.
It returns HL=1 and fills `ROMOUT1`, or HL=0 when index is past the selected
category. `ROMOUT1` is exactly 24 bytes: `name[16]` (1..15 visible bytes plus
NUL/zero padding), `u16 address`, `u8 classification` (1=A,2=B,3=C), `u8 category`,
`u16 contract_flags`, `u16 reserved=0`. Contract flag bit0 means MAY_ERROR_RESTART,
bit1 ALTREG_SENSITIVE, bit2 DISABLES_INTERRUPTS, bit3 NONREENTRANT; remaining bits
are zero in v1.

These records are ABI-visible and mirrored exactly in `docs/abi.md`,
`include/syscall.inc`, and built-in `<c48.h>`.

---

## 10.1A Overflow-safe user range validation

Every syscall range check is computed in widened arithmetic of at least 17 bits;
host/reference tests use 32 bits or wider.

For a nonzero range `(start,length)`:

    end_exclusive = widened(start) + widened(length)

The kernel proves all of:

    end_exclusive > start
    end_exclusive <= 0x10000
    start and end_exclusive-1 lie in one single permitted ABI region

For ordinary user buffers the permitted regions remain:

    0x4000-0x5AFF
    0x6000-0xDFFF

A range may not bridge the gap between them even if both endpoints individually
appear usable.

For syscalls that require process ownership, the complete widened range must also lie
inside the applicable process-owned allocation.

For an operation whose documented `count=0` semantics do not dereference the buffer,
the buffer pointer is not dereferenced and need not designate a readable/writable byte;
all non-buffer arguments such as the handle are still validated.

NUL-terminated strings are scanned only within the caller-valid region and the
documented lexical maximum plus terminating NUL. Lack of a NUL before either limit is
E_TOOLONG or E_INVAL as specified by the string's API.

# 11. Handles and I/O

## 11.1 Process handle table and open-description pool

Each process has exactly 8 handle slots numbered 0..7. Slots 0, 1, and 2 have the
Unix-like stdin/stdout/stderr convention. A slot contains one kernel open-description
ID 0..23 or 0xFF for free; it does not contain an independent file offset or decoder.
The process descriptor therefore owns `handles[8]`, not separate stdin/stdout/stderr
objects.

The kernel owns exactly 24 open-description records system-wide. A record represents
one opened stream instance and owns the shared state required by every reference to it:

    kind/access flags
    reference count
    shared logical offset
    RAM-object slot, pseudo-device identity, or pipe endpoint identity
    optional PACKED-reader decoder-state pointer

The exact byte layout is kernel-private and must fit the handles-subsystem budget, but
the pool size and semantics above are architecture-fixed. `SYS_DUP` and inherited
spawn handles add references to an existing open description and therefore do not
consume another description. Two independent `SYS_OPEN` calls allocate two independent
open descriptions and therefore have independent offsets/packed decoder states.

Final reference release destroys the open description, frees its decoder state if any,
and performs the final close action for its RAM-object or pipe endpoint. All writer
exclusivity, representation-swap E_BUSY checks, and "object has no open references"
tests scan this bounded open-description pool, not process handle tables.

## 11.2 Open modes and typed creation

`SYS_OPEN` uses these fixed bits:

    O_READ    0x01
    O_WRITE   0x02
    O_CREATE  0x04
    O_TRUNC   0x08
    O_APPEND  0x10
    O_EXCL    0x20

Unknown bits return E_INVAL. At least one of O_READ/O_WRITE is required. O_TRUNC and
O_APPEND require O_WRITE. O_EXCL requires O_CREATE. O_TRUNC|O_APPEND is legal: the
successful open first commits the same empty RAW representation required by O_TRUNC,
then that open description has append semantics for all subsequent writes.

Register contract:

    HL = NUL-terminated path, maximum normalized length 31 bytes
    C  = flags
    B  = requested ordinary object type when O_CREATE is set; otherwise 0

For an ordinary mutable path that is absent, omitting O_CREATE returns E_NOENT.
When O_CREATE is set for an ordinary mutable path, B must be one of persistent types
1..10 and the target directory must accept that type. The absent path is then created
atomically as an empty RAW object. If the ordinary path exists and O_EXCL is set,
return E_EXIST without changing it. If it exists without O_EXCL, B is ignored for
stored-type purposes: the existing type is preserved, so O_CREATE never retags an
existing object. For an existing ordinary object B may be zero or any ordinary type
1..10; other values return E_INVAL. The kernel never infers type from a suffix. C48
`open()` creates DAT when creation is actually required; `open_typed()` selects an
explicit creation type.

Fixed pseudo paths never use typed creation. Opening a DIR path returns E_PERM.
For `/dev/tty` and `/dev/null`, B must be zero and O_CREATE/O_TRUNC/O_APPEND/O_EXCL
must all be clear; O_READ and/or O_WRITE are allowed. `/dev/tape` is a control-device
identity only in v1: it may be opened with O_READ and/or O_WRITE under the same zero-B,
no-creation-bit rule, but byte `SYS_READ`, byte `SYS_WRITE`, and unsupported ioctls on
that handle return E_NOTSUP and never move tape. A BCAT-only TAPE_BACKED `/bin` name
cannot be byte-opened from catalog metadata; `SYS_OPEN` returns E_AGAIN and performs no
tape motion. A PINNED_SYSTEM object is opened only under its documented access policy;
creation/truncation/append flags never mutate it.

`SYS_OPEN` allocates one open description and the lowest free process handle; exhaustion
of either the 24-description pool or the process's eight slots returns E_NOSPC with no
visible new object/open state.

RAM-object access is deterministic: any number of distinct read-only open descriptions
may coexist. A write-capable open is exclusive against every other distinct open
description for that object; read opens fail E_BUSY while such a writer exists. Once a
write description exists, `dup`/spawn references to that same description are allowed
and share its offset/append state.

A PACKED read-only open leaves the object packed and allocates exactly one 272-byte
ZXP1 decoder state for that open description; duplicate/inherited handles share it. A
second independent read open gets a separate decoder state. Any write open materializes
a private RAW replacement before returning the handle. O_TRUNC may create a new empty
RAW representation without decoding old bytes. Other write modes decode the complete
logical bytes privately. The directory entry commits only after successful allocation
and validation, so failure leaves the old representation untouched.

O_APPEND sets initial offset to EOF and every subsequent write on that open description
reselects the then-current EOF before its first byte; seek cannot turn append into an
overwrite. Shell `>` uses O_WRITE|O_CREATE|O_TRUNC DAT; `>>` uses
O_WRITE|O_CREATE|O_APPEND DAT; `<` uses O_READ.

For safe transaction temporaries, callers use O_WRITE|O_CREATE|O_EXCL and names such as
`/tmp/.vi<pid>.<n>`, `/tmp/.ct<pid>.<n>`, or `/tmp/.cp<pid>.<n>` with decimal n=0..9.
They retry only E_EXIST and clean up only a temporary whose O_EXCL creation they
personally succeeded in creating; an unknown pre-existing same-name object is never
silently removed.

## 11.3 dup, inheritance, exec, and close

`SYS_DUP`'s `DUP1` is `u8 source,u8 destination`. Source must be live. Destination
0xFF chooses the lowest free slot. If source equals an explicit destination, success is
a no-op. Any other occupied explicit destination returns E_BUSY; version 1 deliberately
does not implement dup2 close-and-replace semantics. Success increments the same open
description's reference count and returns the resulting handle in HL.

`SYS_SPAWN` maps the parent's three PROC1-selected handles to child slots 0,1,2 by
adding references to the same open descriptions; child 3..7 are free. `SYS_EXEC`
preserves the current process's entire 0..7 handle table. `SYS_CLOSE` clears one process
slot and decrements its open-description reference count. Only the final reference
actually destroys that open description and closes its underlying endpoint/object
instance.

## 11.4 Seek semantics

`SYS_SEEK` is supported only by RAM-object open descriptions and sets their shared
absolute unsigned logical-byte offset in 0..object_length inclusive. Seeking beyond EOF
is E_INVAL; sparse holes are not created. Pipe, tty, null, and tape-control streams are
E_NOTSUP.

RAW seek is direct. PACKED seek backward resets the shared decoder and decodes/discards
from logical offset zero; forward seek decodes/discards from the current decoder
position. It is intentionally O(n) and never silently materializes the object.

## 11.5 Exact read/write semantics

`count=0` succeeds immediately with HL=0 and never blocks. RAM/PACKED reads return the
same logical stream; read at logical EOF succeeds HL=0. E_EOF is not ordinary stream
EOF.

RAM-object writes are stronger than generic stream writes: a valid RAW RAM-object write
is either the full requested BC bytes or an error. If wholly within current length, all
BC bytes are committed and HL=BC. If it extends the object, the kernel first validates
`max(old_length,offset+BC) <= 32768`, allocates a complete private replacement large
enough for the new logical length, copies old bytes and the whole new write, then
atomically swaps the object allocation/length. Allocation/size failure leaves the old
object byte-identical and returns E_NOMEM/E_NOSPC; an extending RAM write never returns
a positive short count. O_APPEND follows the same transactional extension rule.

Console and pipe reads/writes may return positive short counts. If a pipe is full while
readers exist and zero bytes can be written, the writer blocks rather than succeeding
with zero. Errors never report uncommitted bytes. C48 provides `read_full()` and
`write_full()`.

## 11.6 Zero-length RAW objects

A zero-length RAW RAM object owns no arena extent: `logical_length=storage_length=0`
and `allocation_ptr=0`. Every nonzero resident RAM payload has an even-aligned pointer
inside 0x6000-0xDFFF. The zero sentinel is never dereferenced and permits empty
`crontab`, O_TRUNC, and atomic empty-file creation without manufacturing a fake extent.

---

# 12. Pipes

Pipes are real bounded in-memory producer/consumer channels.

## 12.1 Pipe object and endpoint descriptions

Each pipe owns state, a 256-byte FAST_REQUIRED circular buffer (or exactly one
128-byte fallback), indices/bytes-used, waiter bookkeeping, and logical read/write
endpoint-open counts. `SYS_PIPE` allocates two new open descriptions: one read endpoint
and one write endpoint, installs their handles in the caller's two writable u8 result
slots, and fails atomically E_NOMEM/E_NOSPC if buffer, descriptions, or handle slots
cannot all be obtained.

Endpoint lifetime follows open-description references. Duplicating or spawning a
reference to the same endpoint description increments that description's refcount but
not a second logical endpoint-open count. A separately created description for an
endpoint is not exposed in v1. Only release of the final reference to a read/write
endpoint description closes that endpoint for EOF/broken-pipe purposes. The pipe object
is freed only after both endpoint descriptions are finally closed and no waiter remains.

## 12.2 Blocking behavior

read(pipe):
- data available: copy up to requested/buffered bytes and possibly wake a writer;
- empty while at least one write endpoint remains open: WAIT_PIPE_READ and schedule;
- empty with no writers: success HL=0.

write(pipe):
- space available and readers exist: copy up to available/requested bytes and possibly
  wake a reader;
- full while readers exist: WAIT_PIPE_WRITE and schedule if zero bytes were transferred;
- no read endpoint remains: E_PIPE.

All endpoint/refcount/wait transitions are atomic with respect to the cooperative
scheduler and IM2-visible wake flags.

## 12.3 Shell pipelines

For `ls | grep .c`, `sh` creates the pipe, spawns `ls` sharing the write description as
child stdout, spawns `grep` sharing the read description as child stdin, closes its own
pipe-handle references, then waits. EOF appears only when the last write-description
reference is released. This is genuine cooperative concurrent pipeline execution.

---

# 13. Keyboard, Console, 64-Column Text, Cursor, and ULA Port Discipline

ZX-UX has one physical Spectrum screen and two logical terminal modes:

    tty64   64 columns x 24 rows, 4x8 software-rendered font; default
    tty32   32 columns x 24 rows, normal-width fallback/debug mode

The current terminal mode, cursor position, cursor shape, current ink/paper,
bright/flash state, and ULA output shadow are kernel console state.

## 13.1 Tasword-style 64-column renderer

`tty64` is a true software text renderer over the native bitmap, not a hardware
mode. Each logical character cell is exactly 4 pixels wide by 8 pixels high.
Therefore:

    64 * 4 = 256 horizontal pixels
    24 * 8 = 192 vertical pixels

Two adjacent logical columns occupy one Spectrum bitmap byte. For logical
column `c`:

    x_byte = c >> 1
    even c -> high nibble bits 7..4
    odd  c -> low  nibble bits 3..0

For each glyph scan row `r=0..7`:

1. obtain the 4-bit row from the packed F4X8 glyph;
2. compute pixel y = text_row*8 + r;
3. obtain the native Spectrum screen address using the one canonical
   pixel/scanline address helper;
4. add `x_byte`;
5. preserve the neighboring nibble and replace only the selected nibble.

A normal printable glyph uses three active pixels plus a one-pixel spacing
column where the font design permits. The font is fixed-width; proportional
text is outside version 1.

The renderer supports codes 0x20-0x7F from the pinned `font4x8` resource. UDGs
remain full 8x8 graphics resources; a UDG drawn while `tty64` is active occupies
two logical text columns when presented as text/editor UI.

## 13.1A 32-column fallback renderer

`tty32` uses the same OS-owned cursor/scroll model but renders one 8x8 glyph per
physical byte/attribute cell from the Phase-0-verified 48K ROM character bitmap
for codes 0x20-0x7F. It does not hand control to BASIC's 22-line upper/2-line
lower screen editor. ZX-UX therefore retains a predictable full
32x24 console in fallback mode.

## 13.2 64-column attributes

Spectrum attributes remain one byte per physical 8x8 cell. Consequently two
adjacent 4x8 logical columns share one attribute cell. ZX-UX does not pretend
otherwise.

In `tty64`:

- shell and `vi` default to a uniform text attribute;
- ink/paper/bright/flash changes apply to the containing 8x8 attribute cell and
  therefore affect both logical columns in that pair;
- the bitmap cursor never changes attributes;
- APIs document this pair-sharing behavior.

## 13.3 64-column scrolling

Scrolling moves one logical text row = 8 pixel scanlines. Because Spectrum
bitmap rows are interleaved, the implementation does not treat the 6144-byte
bitmap as a simple linear array of text rows.

For each destination text row 0..22 and each scan row 0..7, the renderer obtains
canonical source/destination scanline addresses and copies exactly 32 bitmap
bytes, preferably with `LDIR`. It then copies 23*32 attribute bytes upward and
clears the final 32 attribute bytes. The final 8 bitmap scanlines are cleared.

The operation hides the software cursor before moving screen data and redraws
it afterward.

## 13.4 Software cursor

`tty64` cursor position is:

    row 0..23
    col 0..63

Required cursor shapes:

    block       invert the complete 4x8 nibble cell
    underline   invert the bottom 4-pixel row only
    off

The cursor is rendered by XORing only the selected high/low nibble, preserving
the neighboring 4x8 character and the attribute byte. It is therefore reversible
without storing background pixels.

Blink period target is 25 UK 50-Hz frames (approximately 0.5 s). The IM2 ISR
only advances timing/sets a cursor-due flag. Screen memory is modified by normal
console/input code outside interrupt context.

Before writing a character, scrolling, clearing, or changing terminal mode, the
console removes any visible cursor. It redraws the cursor only after the screen
operation leaves the bitmap in a stable state.

Default shapes:

    sh command line        underline
    vi normal mode         block
    vi insert mode         underline
    vi command-line mode   underline

## 13.4A Console-managed rendering

All console, tty32, tty64, OS graphics, UDG, scrolling, clearing, and terminal-mode
operations first remove a visible software cursor, perform the complete screen change
without a cooperative task switch, then redraw the cursor if required.

## 13.5 Terminal mode control

`SYS_IOCTL` on `/dev/tty` has these fixed version-1 request IDs and argument
records (the `IOCTL1.arg_ptr` range is validated before use):

    0x01 TTY_GET_MODE          -> writable u8: 32 or 64
    0x02 TTY_SET_MODE          -> readable u8: 32 or 64
    0x03 TTY_GET_SIZE          -> writable 2 bytes: cols, rows
    0x04 TTY_SET_CURSOR_SHAPE  -> readable u8: 0 off, 1 underline, 2 block
    0x05 TTY_GET_CURSOR_SHAPE  -> writable u8 using the same values
    0x06 TTY_GET_INPUT_OWNER   -> writable u8 PID
    0x07 TTY_SET_INPUT_OWNER   -> readable u8 PID 0..7

Unknown TTY request IDs return E_NOTSUP. These requests require a `/dev/tty` handle;
they are not silently accepted on other handle kinds.

The public utility `stty` exposes the small useful subset:

    stty
    stty cols 64
    stty cols 32
    stty cursor block
    stty cursor underline
    stty cursor off

`stty` is lower-case and case-sensitive. Switching modes clears/reinitializes
the logical console; it is not required to preserve a mixed 32/64-column text
layout.

The console subsystem stores one kernel-global `tty_input_owner_pid`. Only PID 1
(`sh`) may successfully issue `TTY_SET_INPUT_OWNER`; the requested nonzero PID
must name a live process. PID 0 means no user process owns tty input.
`SYS_CON_GETKEY` and reads from `/dev/tty` by any non-owner return E_BUSY rather
than stealing keystrokes. If the current owner exits, the kernel automatically
returns ownership to live PID 1 (or PID 0 if PID 1 is unavailable). This is the
precise mechanism used by foreground pipelines in Section 20.12.

## 13.5A Terminal character/control semantics

For both tty modes:

- printable bytes draw at the current cell then advance one column;
- writing past the final column wraps to column 0 of the next row;
- advancing beyond row 23 scrolls exactly one text row;
- LF (0x0A) moves to column 0 of the next row;
- CR (0x0D) moves to column 0 without changing row;
- BS (0x08) decrements the column by one without deleting when col>0; at col=0 it does nothing and never wraps to the previous row;
- TAB (0x09) advances to the next logical multiple-of-8 column, wrapping/scrolling
  as ordinary output would;
- FF (0x0C) clears the text display and homes the cursor.

The public text encoding is byte-oriented. Host-built system text assets map the
Unicode source character `©` to target byte 0x7F; bytes 0x20-0x7E retain their
normal printable ASCII-like values.

## 13.6 Native keyboard scan path

Where ZX-UX performs direct keyboard scanning, it exploits the Z80's 16-bit
I/O address supplied through BC. The low byte selects the Spectrum ULA port and
upper address bits select keyboard rows. A normal pattern is conceptually:

    LD BC,<row-select with low byte 0xFE>
    IN A,(C)

The exact row masks and electrical polarity are frozen from the Spectrum
hardware reference in Phase 0. The scanner must not assume generic 8-bit port
addressing is equivalent.

## 13.7 Port 0xFE output shadow

Border, MIC, and beeper state share the Spectrum ULA output port. The kernel
therefore owns one authoritative software shadow of the output bits.

No subsystem may blindly `OUT` a new literal and accidentally destroy another
subsystem's border/MIC/beeper state. Updates are read-modify-write operations on
the shadow followed by the minimum required `OUT`. The kernel shadow is authoritative.
Before any approved ROM routine whose port-0xFE behavior derives border state from ROM
`BORDCR`, its wrapper mirrors the kernel border bits into `BORDCR` while preserving the
other Phase-0-documented bits, inside the ROM critical section. On return the wrapper
restores/reconciles the authoritative shadow and issues one final OUT when necessary.
BEEPER and cassette wrappers are tested specifically for this contract; no ROM routine
may silently make `BORDCR` more authoritative than the kernel shadow.

## 13.8 Interactive input and BREAK

Console input supports printable Spectrum characters, ENTER, DELETE/backspace,
cursor editing keys mapped from available combinations, and BREAK/cancel. Command history is deferred from version 1. A waiting console read yields cooperatively
instead of busy-spinning.

BREAK is sampled minimally by IM2 into `break_pending` as specified in Section 21.
At the next safe kernel boundary, PID1 tty ownership cancels shell line input; a live
PID2..7 tty owner receives CANCEL_PENDING. BREAK does not imply pipeline process-group
cancellation. Because scheduling is cooperative, a process that never calls the kernel
cannot be safely killed without preemption.

---

# 14. ROM Services Layer

The 48K ROM is a first-class architectural dependency and shall be treated as
a permanent 16 KiB resident library.

One source module owns every ROM address used by ZX-UX:

    src/kernel/rom_services.asm

One specification owns the verified contracts:

    docs/rom-services.md

No other module may contain a literal ROM entry address unless it is test data
explicitly checking the canonical table.

## 14.1 Authoritative ROM baseline

Phase 0 shall use an authoritative 48K Spectrum ROM disassembly, with Ian Logan
and Frank O'Hara's Complete Spectrum ROM Disassembly / its current maintained
SkoolKit rendering as the primary routine-level reference.

Architecture-approved entry points already verified for the baseline include:

    0x0010  PRINT-A / print-a-character restart
    0x0028  FP-CALC / calculator restart

    0x028E  KEY-SCAN
    0x02BF  KEYBOARD
    0x0333  keyboard decoding

    0x03B5  BEEPER
    0x03F8  BEEP command routine

    0x04C2  SA-BYTES
    0x0556  LD-BYTES

    0x22AA  PIXEL-ADD
    0x22CB  POINT
    0x22E5  PLOT-SUB

    0x24B7  DRAW-LINE entry that first converts calculator-stack values
    0x24BA  lower line-drawing entry after that conversion

    0x2DA2  floating-point-to-BC
    0x2DE3  print floating-point number

    0x335B  CALCULATE
    0x36AF  INT
    0x36C4  EXP
    0x3713  LN
    0x37AA  COS
    0x37B5  SIN
    0x37DA  TAN
    0x37E2  ATN
    0x3833  ASN
    0x3843  ACS
    0x384A  SQR
    0x3851  exponentiation

These addresses do not authorize use by themselves. Every wrapper still needs
its exact input/output registers, flags, workspace, error path, interrupt
behavior, and reentrancy classification recorded before implementation closes.

## 14.2 ROM-service classification

Every useful ROM routine discovered in Phase 0 receives exactly one
classification.

### Class A - use aggressively

Class A facilities have a narrow, testable contract and are strong candidates
to replace RAM implementations.

Initial Class A targets:

    keyboard scanning and decoding
    character output where compatible with ZX-UX console state
    screen clearing/scroll helpers where compatible
    PIXEL-ADD
    POINT
    PLOT-SUB
    lower line drawing
    BEEPER
    SA-BYTES
    LD-BYTES

The preferred implementation is a thin wrapper rather than a duplicate RAM
algorithm unless measurement or correctness testing proves the ROM routine
unsuitable.

### Class B - use only through controlled kernel wrappers

Class B facilities are valuable but depend on BASIC calculator state,
Spectrum system variables, global workspaces, parser state, or other
non-reentrant machinery.

Initial Class B targets:

    BEEP command routine (calculator-backed public semantics)
    FP-CALC / CALCULATE
    integer <-> Spectrum floating conversion
    floating-point printing
    floating arithmetic
    ABS / SGN / INT
    EXP / LN
    SIN / COS / TAN
    ASN / ACS / ATN
    SQR / exponentiation
    numeric/string conversion routines
    restricted BASIC expression scanning

Class B routines may not be called directly by normal user programs in the
version-1 ABI.

The kernel owns their serialization and workspace discipline.

### Class C - do not adopt as OS infrastructure

Class C facilities are too tightly coupled to Sinclair BASIC's own program,
variable, workspace, channel, or memory-management model, or they permit
unrestricted machine mutation.

Initial Class C examples:

    BASIC MAKE-ROOM / RECLAIM memory management
    BASIC variable storage as an OS object model
    full BASIC program execution as shell infrastructure
    NEW / CLEAR / RUN as operating-system operations
    unrestricted POKE
    unrestricted OUT
    unrestricted USR
    BASIC's global stream/channel model as the ZX-UX handle layer
    BASIC's complete line editor as the ZX-UX source editor

A Class-C function can later be exposed in a deliberately unsafe monitor mode,
but it may not silently become a normal shell or kernel primitive.

## 14.3 Wrapper contract

Every ROM wrapper documents:

    symbolic wrapper name
    ROM address
    routine/disassembly name
    classification A/B/C
    input registers
    output registers
    clobbered registers
    flags
    alternate-register effects
    IX/IY effects
    system variables read
    system variables written
    calculator-stack effects
    workspace effects
    interrupt enable/disable behavior
    ROM error path / RST 8 behavior
    BREAK behavior
    reentrancy
    whether a task switch is permitted around the call

The wrapper saves/restores kernel-required state around the ROM call.

## 14.3A IY and alternate-register interaction

IY is reserved as the OS/ROM compatibility anchor with the exact version-1 value:

    IY = 0x5C3A = 23610 = ERR_NR

The production 48K ROM initializes IY to ERR_NR and ROM routines access multiple
system variables through signed offsets from that base. ZX-UX therefore freezes
0x5C3A as the version-1 IY ABI value.

This value is established during permanent kernel handoff before any approved ROM
service is used and before PID 1 becomes runnable.

At every boundary at which user MEX1 code may execute:

    IY MUST equal 0x5C3A.

At every normal return from a syscall:

    IY MUST equal 0x5C3A.

At every normal return from an interrupt:

    IY MUST be restored byte-for-byte to the value held by the interrupted context.

For ordinary MEX1 execution that value is necessarily 0x5C3A. If an interrupt occurs
inside an approved ROM wrapper during a documented temporary IY change, the ISR restores
that temporary interrupted value so the wrapper can continue correctly; the wrapper
then restores 0x5C3A before leaving its atomic wrapper region or returning toward user
code.

A ROM wrapper may temporarily alter IY only if its machine-level contract requires
that change.

MEX1 code must treat IY as OS-owned and must not modify it.

`docs/rom-services.md` records the exact IY-relative assumptions of every reused ROM
routine. Phase 0 verifies the frozen architecture value rather than selecting a value
later. A release fails if any enabled ROM wrapper requires an incompatible permanent
IY base.

The alternate AF'/BC'/DE'/HL' bank is OS-private but ROM code is not assumed to
leave it untouched. Every Class-A/Class-B routine therefore records whether it:

    does not use the alternate bank;
    uses it but returns with contents preserved;
    uses/clobbers it;
    is unknown and must be treated as clobbering.

No persistent kernel state may exist only in the alternate register bank.

`altreg_busy` is kernel-global interrupt-visible state. The FAST ISR path is permitted
only while `altreg_busy == 0`.

Any task-context kernel code or ROM wrapper that makes live use of AF', BC', DE', or
HL' across an interruptible instruction interval must:

1. enter a short critical section;
2. set `altreg_busy` before the first such value becomes live;
3. leave the critical section;
4. perform the interruptible work;
5. enter a short critical section;
6. finish or save all live shadow-register state;
7. clear `altreg_busy`;
8. leave the critical section.

If setting/clearing the gate itself cannot be made atomic with respect to IM2, the
whole short transition is performed with maskable interrupts disabled.

While `altreg_busy != 0`, IM2 uses the ROM-safe stack/kernel-scratch preservation
path and MUST NOT use EXX or EX AF,AF' as disposable scratch. A ROM wrapper that may
use/clobber the alternate bank uses this same generic gate; there is no separate
ROM-only alternate-register gate.

Conforming MEX1 code owns no alternate-register state across syscalls or interrupts.

The IM2 handler has two register-preservation paths:

FAST ISR path:
    permitted only while `altreg_busy == 0`;
    may use `EX AF,AF'` and `EXX` for fast interrupt scratch.

ROM-SAFE ISR path:
    selected whenever `altreg_busy != 0`;
    does not use the alternate bank as scratch;
    preserves the interrupted foreground register state on the stack/kernel scratch
    according to the verified foreground/interrupt contract.

This dual path prevents the interrupt optimizer from corrupting calculator,
parser, graphics, or other ROM routines that use shadow registers.

Tape routines that disable interrupts for their timing-critical region naturally
exclude IM2 entry during that interval; their wrapper still documents the fact.

## 14.4 ROM errors

ZX-UX must not allow a ROM routine to escape into an uncontrolled Sinclair
BASIC error-reporting path and corrupt process/kernel control flow.

Each adopted routine must therefore be classified as one of:

    RETURNS_STATUS
    RETURNS_CARRY
    MAY_RST8_ERROR
    MAY_ABORT_ON_BREAK
    NEVER_RETURNS_ON_ERROR

For routines that can enter the ROM error restart, the wrapper must establish
a tested recovery/trampoline mechanism before the routine is enabled in
production.

If no safe recovery mechanism exists, that routine is not usable from the
normal OS API.

## 14.5 ROM calculator service

The Spectrum calculator is exposed through ZX-UX as an atomic kernel service.

The kernel maintains a small calculator-service state block and does not allow
a cooperative task switch while a calculator operation is in progress.

User-visible floating values use a five-byte ZX-UX representation compatible
with the Spectrum calculator's five-byte numeric form.

A calculator call follows this conceptual sequence:

1. validate caller pointers and operation code;
2. enter the ROM-calculator critical section;
3. save ROM calculator/system-variable state that ZX-UX promises to preserve;
4. copy input operand(s) into the controlled calculator workspace;
5. invoke the verified calculator operation;
6. capture any ROM error into ZX-UX errno;
7. copy the result to caller-owned memory;
8. restore protected ROM state;
9. leave the critical section;
10. return without yielding inside the operation.

The operation set initially includes:

    ADD
    SUB
    MUL
    DIV
    POW
    ABS
    SGN
    INT
    EXP
    LN
    SIN
    COS
    TAN
    ASN
    ACS
    ATN
    SQR

The exact calculator literals/entry contracts are frozen in
`docs/rom-services.md`.

## 14.6 Restricted BASIC expression gateway

ZX-UX may reuse the ROM BASIC expression scanner behind a safe shell command:

    calc EXPR

This is an optimization and convenience feature, not permission to run
arbitrary BASIC.

Before any expression reaches the ROM scanner, ZX-UX tokenizes/validates it
against a strict allow-list.

Version-1 public, case-sensitive expression grammar:

    decimal numeric literals
    unary + and -
    + - * / ^
    parentheses
    pi
    abs
    sgn
    int
    sqrt
    exp
    ln
    sin
    cos
    tan
    asin
    acos
    atan

`rnd` is deferred from the version-1 `calc` grammar; pseudorandom support must not depend on an unresolved seeding contract.

The ZX-UX tokenizer may translate these lower-case public names into the exact
Sinclair ROM tokens required internally. That translation is not case folding:
upper-case spellings such as `SIN` are not aliases unless a later documented
shell-language revision explicitly adds them.

Explicitly forbidden through `calc`, regardless of source spelling or ROM token
representation:

    peek
    in
    inkey$
    screen$
    attr
    point
    usr
    poke
    out
    clear
    new
    run
    load
    save
    merge
    randomize usr
    variable assignment
    BASIC statements
    string expressions unless separately specified

The allow-list is enforced by ZX-UX code before invoking ROM parsing.

If safe parser-state isolation proves too costly or fragile, `calc` shall use
ZX-UX's own tiny expression tokenizer while still delegating numeric
operations to the ROM calculator. Safe failure is preferred over deeper BASIC
reuse.

## 14.7 ROM information service

Provide a safe diagnostic command:

    rom
    rom keyboard
    rom tape
    rom gfx
    rom math

It reads the kernel's canonical ROM-service metadata and prints symbolic names,
addresses, classifications, and concise contracts.

Version 1 does not provide an unrestricted `romcall` command.

## 14.8 ROM system-variable ownership

ZX-UX reserves the Spectrum ROM compatibility/workspace zone and explicitly
documents which ROM system variables remain live.

Each live variable is owned by one of:

    KERNEL
    CONSOLE
    GRAPHICS
    TAPE
    CALCULATOR
    ROM_TRANSIENT

A process may not rely on undocumented BASIC system-variable contents across a
syscall or task switch.

## 14.8A FRAMES and UDG compatibility under IM2

Replacing the ROM IM1 interrupt path with ZX-UX IM2 means the ROM no longer
automatically updates its three-byte `FRAMES` variable at 23672-23674. The
ZX-UX IM2 handler shall mirror the ROM behavior on every accepted frame
interrupt: increment the low 16 bits and increment the high byte on low-word
wrap. This keeps approved ROM routines that inspect `FRAMES` coherent while the
kernel also maintains its own monotonic tick counter.

The ROM system variable `UDG` at 23675-23676 must not retain the power-on/BASIC
default if that address points inside ZX-UX high kernel memory. During boot,
ZX-UX explicitly repoints `UDG` to a kernel-approved 8x8 UDG bank and records
the exact value in `docs/rom-services.md`. ROM wrappers that use UDG state are
therefore safe from overwriting IM2/kernel storage.

Neither `FRAMES` nor `UDG` is left as accidental inherited BASIC state.

## 14.9 ROM replacement threshold

A ROM-backed implementation is replaced with RAM code only when at least one
of the following is proven:

1. the ROM routine cannot be made safe under the kernel error model;
2. its workspace conflicts irreconcilably with multiprocessing;
3. its semantics cannot satisfy the ZX-UX ABI;
4. deterministic tests show unacceptable behavior;
5. measured size/performance of a RAM replacement produces a material system
   benefit worth the memory cost.

"Cleaner code" alone is not sufficient justification for duplicating ROM
functionality in RAM.

---

# 15. Graphics Architecture

ZX-UX provides two graphics levels.

## 15.1 Level 1: OS graphics API

Portable within ZX-UX:

    cls()
    plot(x,y)
    point(x,y)
    draw(x1,y1,x2,y2)
    circle(x,y,r)
    ink(color)
    paper(color)
    bright(on)
    flash(on)
    inverse(on)
    over(on)
    border(color)
    print_at(row,col,text)

Coordinates:

    x = 0..255
    y = 0..191

For plot/point, x=0..255 and y=0..191; out-of-range values return E_INVAL. `draw`
requires both supplied endpoints to satisfy those bounds and draws the clipped/native
line between them. `circle` requires center x=0..255,y=0..191 and radius=0..255;
radius zero plots the center. Circumference pixels falling outside the display are
silently clipped rather than making the whole circle an error. ROM and native
implementations must expose these identical results.

## 15.2 Level 2: direct Spectrum access

Because there is no memory protection, programs may directly access:

    bitmap 0x4000-0x57FF
    attributes 0x5800-0x5AFF

This is allowed but non-portable across future non-Spectrum targets.

A program that writes directly to those bitmap/attribute ranges bypasses console
synchronization. Before directly changing bitmap pixels in a cell that may contain the
tty software cursor, the foreground program MUST set the cursor shape to OFF through
`/dev/tty`. It may restore the desired cursor shape only after completing the raw screen
update.

If a program ignores this rule, screen/cursor contents are explicitly unspecified until
the next console clear/mode reset. The kernel cannot enforce the rule because the 48K
Spectrum has no memory protection or write trapping.

Background programs must not perform raw display writes unless explicitly acting as a
shared UI service under an application-level ownership protocol.

Direct access remains legal and non-portable; it is not granted transactional
coexistence with the software cursor. The OS ABI never depends on raw direct-access
behavior.

## 15.3 Plot/draw

The version-1 default implementation SHALL use the verified Spectrum ROM
graphics primitives where their contracts satisfy the OS ABI.

Preferred low-level entries:

    PIXEL-ADD  0x22AA
    POINT      0x22CB
    PLOT-SUB   0x22E5
    DRAW lower entry 0x24BA

`PLOT-SUB` accepts integer coordinates without requiring the BASIC expression
parser. The `0x24BA` line-drawing entry begins after the ROM routine's
calculator-stack-to-register conversion and is therefore useful only when the
wrapper supplies the exact register state expected by that internal entry.

The wrapper contract and regression tests, not the address alone, determine
whether each lower entry remains approved.

A future optimized implementation may replace a ROM routine with kernel-native
code without changing the syscall API only after satisfying the ROM replacement
threshold in Section 14.9.

## 15.4 Circle

CIRCLE should first be evaluated as a Class-B ROM-assisted operation because
the ROM circle path uses calculator/graphics machinery.

If safe calculator-state isolation makes the ROM path practical, reuse it.

Otherwise use an integer midpoint circle algorithm.

Both implementations must expose identical ZX-UX clipping/error semantics.

## 15.5 Attribute handling

Each 8x8 character cell has one attribute byte.

The API exposes native INK 0..7, PAPER 0..7, BRIGHT 0/1, and FLASH 0/1 semantics.

The architecture does not attempt per-pixel color because the hardware cannot provide it.

---

# 16. User-Defined Graphics (UDGs)

UDGs are first-class OS graphics resources.

## 16.1 Native UDG format

One UDG is:

    width:   8 pixels
    height:  8 pixels
    storage: 8 bytes
    format:  one byte per raster row, bit 7 = leftmost pixel

Version 1 provides:

    32 UDG slots
    slot 0..31
    total 256 bytes

## 16.2 Logical character mapping

ZX-UX reserves character codes 0x80-0x9F as UDG identifiers. `tty32` may
render those identifiers directly as one 8x8 cell. `tty64` does not reinterpret
them as 4x8 glyphs; full-size UDGs are drawn through `udg_draw` so the 4x8 text
stream remains unambiguous. This convention is not constrained by the Spectrum
BASIC ROM's historical UDG count.

## 16.3 UDG syscalls

    udg_define(slot, eight_bytes)
    udg_get(slot, eight_bytes)
    udg_draw(slot, row, col)
    udg_clear(slot)

`udg_draw(slot,row,col)` uses physical 8x8 character-cell coordinates:
`row=0..23`, `col=0..31`, independent of tty32/tty64. In tty64 it overwrites the
bitmap corresponding to logical columns `2*col` and `2*col+1`. It uses current
console ink/paper/bright/flash attributes. Out-of-range slot/coordinates return
E_INVAL.

## 16.4 2x2 logical sprites

A user library provides:

    udg_draw_2x2(base_slot,row,col)

using four consecutive UDGs:

    base+0  top-left
    base+1  top-right
    base+2  bottom-left
    base+3  bottom-right

This creates a 16x16 logical sprite without adding kernel state.

## 16.5 UDG persistence

UDG banks can be persisted as cassette objects.

Shell examples:

    udg list
    udg show 3
    udg save icons
    udg load icons

`udg save name` creates or transactionally replaces a mutable RAM UDG object at the
resolved name; it never moves cassette. `udg load name` reads a RAM UDG object (RAW or
transparently PACKED), validates the complete UDG1 payload before changing the live bank,
and applies the encoded slots atomically; it never moves cassette. Shell `save name` and
`load name` perform cassette persistence explicitly.

A saved UDG object has M48O type UDG and a `UDG1` payload:

    0..3   magic = "UDG1"
    4      version = 1
    5      base slot, 0..31
    6      glyph count, 1..32
    7      reserved = 0
    8..    exactly count*8 glyph bytes

`base+count` must be <=32 and payload length must equal `8+count*8`. M48O supplies
the payload CRC; UDG1 does not add a second checksum.

---

# 17. Sound and BASIC-Compatible `beep`

Version 1 requires one public single-note sound primitive. The C48 declaration is:

    int beep(float duration, float pitch)

It returns 0 on success or the positive ZX-UX errno value on failure.

Its public parameter order and meaning intentionally follow Sinclair BASIC
`BEEP duration,pitch`:

- `duration` is time in seconds;
- `pitch` is semitones above middle C; negative values are below middle C;
- fractional duration is supported;
- fractional pitch is supported, including microtonal values such as 0.5;
- adding/subtracting 12 changes pitch by one octave.

The lower-case shell command receives exactly one normal shell argument after
quote removal/expansion. That one argument uses exactly one top-level comma separator:

    beep duration,pitch

Examples:

    beep 1,0
    beep .5,9
    beep .25,-12
    beep .5,0.5
    beep 1/4,12+0.5

Each operand may use the same safe numeric-expression grammar as `calc`; shell
variables, BASIC statements, `USR`, `PEEK`, `IN`, `POKE`, and `OUT` are not
accepted. Shell expansion occurs before this numeric validation. This preserves the
useful BASIC parameter style without exposing the BASIC interpreter as an OS escape
path. Semicolons are ordinary shell command separators, so a short tune can be written
naturally as:

    beep .25,0; beep .25,2; beep .25,4; beep .5,7

The kernel syscall is `SYS_BEEP` (Section 10). The wrapper converts/validates the
two five-byte Spectrum numeric values and uses the Phase-0-approved ROM BEEP/
BEEPER path. The wrapper deliberately preserves the ROM/BASIC numeric domain: a
value the verified ROM path rejects is trapped through the ROM error gateway and
reported as E_INVAL rather than escaping into BASIC. ZX-UX does not impose a
narrower arbitrary pitch range.

Sound is synchronous in version 1. The ROM BEEPER path disables maskable
interrupts while generating a note, so a long `beep` pauses cooperative process
progress and frame-derived wall-clock advancement for that interval. The command
returns only when the note completes or validation fails. Background mixing,
polyphony, and a sequencer daemon are deferred.

---

# 18. Volatile Object Store and Minimal Unix Namespace

ZX-UX provides a deliberately small hierarchical namespace without paying the
RAM cost of a general Unix VFS. The version-1 directory topology is fixed:

    /
    /bin
    /dev
    /etc
    /home
    /home/<user>
    /tmp

No `mkdir` or `rmdir` is required in version 1. The single `/home/<user>` name
is created as session metadata after login. General nested directories are a
later extension.

## 18.1 Names and path rules

Normal object base names are 1..10 visible characters so they round-trip cleanly
through the version-1 cassette metadata. Directory components are lower-case and
fixed by the OS. Object names preserve exact case and lookup is case-sensitive.

Portable name characters:

    A-Z a-z 0-9 _ - .

The exact base names `.` and `..` are forbidden for ordinary objects because they are
reserved path traversal components. Other dot-prefixed names are legal and are used by
transaction locks/temporaries.

Paths support:

    absolute paths beginning /
    relative paths
    .
    ..

Repeated `/` separators are collapsed. The maximum normalized path length is
31 bytes excluding the terminating NUL. Empty final names where an object is
required, traversal above `/`, overlength paths, and unknown directory components
fail with E_INVAL, E_TOOLONG, or E_NOENT as applicable.

## 18.2 Fixed directory IDs

Internally, path resolution maps fixed directories to these ABI-visible compact
IDs rather than storing directory objects:

    0 ROOT
    1 BIN
    2 DEV
    3 ETC
    4 HOME
    5 USERHOME
    6 TMP

M48O persistence uses these same IDs plus 7 SYSTEM; targets DEV and HOME are
invalid for persistent mutable objects.

A RAM-object directory entry therefore needs only a parent-directory ID plus its
base name, type, flags, logical/storage lengths, and allocation pointer. It does
not cache a content CRC; operations such as packed `save` recompute required CRCs
from logical bytes. This keeps Unix-like paths without a general-purpose inode tree.

## 18.3 Directory semantics

`/bin`
    executable/tool namespace. Exact lookup checks a resident RAM-backed BIN
    object first, then the pinned `bincat` entry. A resident object therefore
    shadows a same-name tape-backed catalog entry until removed; after removal,
    the cataloged tape-backed command becomes visible again. This allows explicit
    `load /bin/word`-style additions without mutating BCAT.

`/dev`
    pseudo devices; no RAM payload is allocated for fixed devices.

`/etc`
    small system configuration objects including `issue` and `crontab`.

`/home/<user>`
    default writable working directory for source, executables, and data.

`/tmp`
    volatile writable scratch objects.

`/home` itself contains only the current session home in version 1.

Mutable-object placement rules are fixed:

- `/bin` accepts BIN objects only;
- `/etc` accepts TXT or CFG objects only;
- `/home/<user>` and `/tmp` accept normal user object types TXT/BIN/OBJ/ASM/C/
  DAT/UDG/GFX/FNT/CFG;
- ROOT, `/home`, and `/dev` do not accept mutable object creation;
- SYS is reserved for kernel/bootstrap metadata and cannot be created through
  normal `SYS_OPEN`.

`SYS_OPEN`, `load`, `rename`, and linker/tool output all enforce these same
directory/type compatibility rules.

Every visible fixed-directory listing contains at most 255 entries. Mutable RAM objects
are already bounded to 32. BCAT `entry_count` is capped at exactly 223 so the worst-case
`/bin` union (223 catalog names plus 32 distinct resident shadows/additions) is <=255;
the build tool rejects a larger catalog. `SYS_LIST` ordering/termination is fixed in
Section 10.1.

## 18.4 Object/namespace types and states

ABI type IDs are:

    1 TXT   text/source
    2 BIN   relocatable executable
    3 OBJ   relocatable object module
    4 ASM   assembly source
    5 C     C source
    6 DAT   arbitrary data
    7 UDG   UDG set
    8 GFX   graphics data
    9 FNT   console-font resource
    10 CFG  configuration text/data
    11 SYS  system image/configuration
    12 DIR  fixed namespace directory; never an M48O payload type
    13 DEV  fixed pseudo-device; never an M48O payload type

`SYS_STAT`/`SYS_LIST` state IDs are 0 RAM, 1 TAPE_BACKED, 2 PINNED_SYSTEM,
3 PSEUDO. Version-1 object flag bit 0 is `OBJ_PACKED`; all other public flag bits
are zero. DIR and DEV entries have length zero. Because BCAT intentionally does
not store executable payload sizes, a TAPE_BACKED catalog entry reports length
0xFFFF (unknown) until loaded. M48O accepts only persistent payload types 1..11. Target/type placement is exact:
BIN target accepts only BIN; ETC accepts TXT/CFG; USERHOME and TMP accept ordinary
types 1..10; SYSTEM accepts only FNT or SYS and only through the internal bootstrap
loader. ROOT, DEV, and HOME are never valid persistent M48O targets. Public save/load
never targets SYSTEM.
The type is metadata; programs may still inspect ordinary object contents.

For a RAM object, `STATOUT1.logical_length` and `LISTOUT1.length` always report
logical uncompressed length. `STATOUT1.storage_length` exposes the resident
physical byte count and `OBJ_PACKED` identifies ZXP1 storage. `SYS_ZXPACK_INFO`
provides aggregate compression statistics. `LISTOUT1` remains 16 bytes; `ls -l`
performs `SYS_STAT` for entries whose physical size it displays.

Text-bearing object types TXT, C, ASM, and CFG use byte 0x0A (LF) as the canonical
line separator. Host build tooling normalizes system text assets to LF; `vi`, `cc`,
`as`, `grep`, `wc`, `head`, `tail`, and `crontab` preserve/interpret that convention.
CRLF is not emitted by version-1 target tools.

The mutable RAM-object table has exactly 32 fixed 20-byte entries (640 bytes):

    +0   name[10]          exact case-sensitive base name, NUL/zero padded
    +10  u8 directory_id
    +11  u8 type
    +12  u8 flags          bit0 PACKED; remaining bits zero
    +13  u8 reserved       zero
    +14  u16 logical_length
    +16  u16 storage_length
    +18  u16 allocation_ptr

For RAW objects `storage_length == logical_length`. For PACKED objects
`storage_length` is the exact ZXP1 byte-stream length and must be strictly less
than `logical_length`. A zero-length RAW object has allocation_ptr=0 and owns no
arena bytes; every nonzero resident payload has an even-aligned pointer inside
0x6000-0xDFFF. The allocation is exactly `storage_length` bytes rounded up only by
the allocator's two-byte alignment; logical storage length excludes padding. Pinned
bootstrap metadata uses separate fixed kernel records and does not consume the 32
mutable entries.

## 18.5 Directory capacity and allocation

Maximum live RAM-backed objects:

    exactly 32

Fixed pseudo-files/devices do not consume those 32 entries unless they have a
mutable RAM payload.

Object data shares the same arena as processes and pipes. Ordinary mutable RAM-object
payloads use COLD_PREFERRED allocation by default; that policy may fall back to FAST
when no suitable contended extent exists, but it never changes correctness. Explicit
pinned resources such as `font4x8` keep their architecture-defined policy. Therefore
more files mean less process/compiler memory and vice versa. `mem` must show this
tradeoff.

Eligible RAW objects of at least 64 logical bytes are opportunistic ZXP1 packing
candidates only when the final open description referencing them is destroyed and during the bounded
allocator compaction pass in Section 27.3.8. Closing a non-final reader never marks
an object while another reader remains. Packing is never required for a successful close:
if no useful smaller stream or no destination allocation is available, the valid RAW
object remains unchanged. `/tmp` uses the same policy; it does not receive a separate
codec or unsafe in-place semantics.

Object growth and representation changes are atomic with respect to failure: if
a required reallocation/pack/unpack cannot be completed and validated, the
previously valid object remains unchanged.

## 18.6 Working directory syscalls

`SYS_CHDIR` accepts a path resolving to one of the fixed directories or current
`/home/<user>`. `SYS_GETCWD` writes the exact current path to the caller buffer.
Each process inherits its parent's current-directory ID at spawn; `exec` preserves it.
`SYS_STAT` and `SYS_LIST` expose the numeric directory/type/state values from Sections
18.2/18.4. Fixed directories and `/dev/*` are PSEUDO entries; BCAT-only `/bin` names are
TAPE_BACKED. Remove/rename applies only to RAM state entries. Attempts to remove or
rename DIR, DEV, PINNED_SYSTEM, or catalog-only TAPE_BACKED entries return E_PERM.

Fixed pseudo-directory enumeration is ABI-visible. `SYS_LIST /` returns exactly
`bin`, `dev`, `etc`, `home`, `tmp` under the global unsigned-bytewise ordering rule.
`SYS_LIST /dev` returns exactly `null`, `tape`, `tty`. `SYS_LIST /home` returns the
current session username after login and zero entries before login. `.` and `..` are
path-navigation syntax and are never emitted as entries. `SYS_STAT` on a fixed
directory reports type DIR, state PSEUDO, logical/storage lengths zero; on a fixed
device it reports type DEV, state PSEUDO, zero lengths. Every returned entry's
`directory_id` is its parent directory ID; stat of `/` uses ROOT as its own parent
sentinel.


---

# 19. Cassette Persistence

## 19.1 Physical truth

Cassette is sequential. Commands may require the user to position/rewind tape,
press PLAY, press RECORD, and stop tape. ZX-UX never claims instant random
access or in-place deletion.

## 19.2 Native bootstrap prefix versus M48O stream

The production tape begins with three conventional Spectrum logical files:

    zx48ux       BASIC autoloader
    zx48uxscr    SCREEN$ image
    kernel       CODE 8192 bytes at 0xE000

Each uses the normal Spectrum header-block + data-block representation and the
whole release starts conventionally with `LOAD ""`.

After permanent kernel handoff, ZX-UX stops pretending every object is a
Sinclair BASIC file. It uses the ROM SA-BYTES/LD-BYTES pulse engine to write and
read its own sequential M48O blocks.

Each M48O object consists of:

    one fixed 32-byte M48O header data block
    zero or more payload chunk data blocks, each <= 512 bytes

All are ROM data blocks using flag byte 0xFF plus the standard ROM block
checksum framing. The M48O header and each payload chunk are separate 0xFF data
blocks.
This design allows the kernel to validate metadata and allocate a final
destination before loading a large payload, and lets `tape scan` consume payload
chunks through one small reusable scratch buffer rather than allocating the
whole object.

## 19.3 M48O header format

Version-1 object-type byte values are fixed:

    0  invalid
    1  TXT
    2  BIN / MEX1 executable
    3  OBJ / OBJ1 module
    4  ASM
    5  C
    6  DAT
    7  UDG
    8  GFX
    9  FNT
    10 CFG
    11 SYS

Version-1 target-directory byte values reuse the namespace IDs from Section 18:

    0  ROOT
    1  BIN
    2  DEV         invalid as an M48O persistence target
    3  ETC
    4  HOME        invalid as an M48O persistence target
    5  USERHOME
    6  TMP
    7  SYSTEM      bootstrap-only pinned resource, not a visible path

M48O object types 12 DIR and 13 DEV are invalid; only payload types 1..11 are
accepted. Placement is exact: BIN accepts only BIN; ETC accepts TXT/CFG; USERHOME/TMP
accept ordinary types 1..10; SYSTEM accepts only FNT or SYS and only through the internal
bootstrap loader. ROOT, DEV, and HOME are invalid. Public save/load never targets SYSTEM.
Unknown type/directory/placement/flag values are E_FORMAT.

Version-1 M48O flags:

    bit0  M48O_PACKED
    bits1..7 must be zero

The two auxiliary fields have compression-wide meaning for every object type:

    auxiliary value 1 = logical uncompressed length
    auxiliary value 2 = codec ID; 0 RAW, 1 ZXP1

For RAW objects `flags=0`, `payload_length==aux1`, and `aux2=0`. For PACKED
objects bit0 is set, `aux2=1`, `aux1` is 1..32768, and `payload_length` is the
strictly smaller physical ZXP1 stream length. Zero-length objects are always RAW.

The fixed 32-byte header is:

    offset  size  field
    0       4     magic = "M48O"
    4       1     format version = 1
    5       1     object type
    6       1     flags
    7       1     target directory ID
    8       2     physical payload/storage length
    10      2     logical uncompressed length
    12      2     codec ID; 0 RAW, 1 ZXP1
    14      2     logical-payload CRC-16/CCITT-FALSE
    16      10    exact case-sensitive base name, NUL padded
    26      2     header CRC-16/CCITT-FALSE
    28      4     reserved = zero

All multi-byte fields are little-endian. Physical payload length may be zero but
may not exceed 32768 bytes in the version-1 format. Logical length may not exceed
32768 bytes and obeys the RAW/PACKED rules above. The base name is 1..10 bytes and must
satisfy the namespace character rules. It contains
a NUL within the ten-byte field unless all ten bytes are non-NUL, in which case
all ten characters are part of the name. Embedded NUL followed by nonzero garbage
is E_FORMAT.

For header-CRC calculation the full 32-byte header is processed with bytes
26..27 treated as zero. `USERHOME` means the current `/home/<user>` at load time;
cassette files therefore remain usable regardless of the boot username.

## 19.4 Payload chunking

Chunk size is fixed in version 1:

    512 bytes

Number of payload blocks:

    ceil(physical_payload_length / 512)

All chunks except the final chunk are exactly 512 bytes. The final chunk is the
remaining 1..512 bytes. A zero-length payload has no payload blocks.

For RAW M48O objects, physical bytes are logical bytes. For PACKED objects,
payload chunks contain the ZXP1 stream. The M48O payload CRC always covers the
logical uncompressed byte stream, not the compressed bytes and not ROM
flag/checksum bytes. During packed load/scan/verify the kernel updates this CRC
from decoder output; ROM block checksums independently protect the physical tape
blocks.

All architecture CRC-16/CCITT-FALSE references (M48O, MEX1, OBJ1) mean exactly:

    polynomial  0x1021
    init        0xFFFF
    refin       false
    refout      false
    xorout      0x0000

MEX1 and OBJ1 header CRCs process their full fixed 24-byte headers with the
header-CRC field bytes treated as zero.

For an explicit user `load` into a mutable visible namespace, a RAW payload goes
directly to the final RAW RAM-object allocation. A PACKED payload goes directly
to an allocation sized to its physical ZXP1 length while the decoder simultaneously
validates logical length and logical CRC into a discard sink; after successful
validation the RAM object remains PACKED. Bootstrap-only SYSTEM resources are the
exception: `font4x8` and `bincat` are decoded/validated directly into their final
pinned RAW runtime allocations and never retain their transport-compressed bytes.
For `tape scan`, chunks are read into one temporary <=512-byte COLD scratch allocation.
A PACKED scan additionally uses one 272-byte COLD_PREFERRED decoder state/history and
decodes to a discard sink so logical CRC/length are still verified; both scratch
allocations are released before the next object.
Tape-backed command execution uses the distinct streaming MEX1 path in Section 19.4A
so a large executable need not exist twice in the 32 KiB arena.

## 19.4A Direct tape-backed MEX1 execution

When `SYS_SPAWN`/`SYS_EXEC` resolves a BCAT command as TAPE_BACKED and PROC1
`ALLOW_TAPE` is set, the M48O reader may stream its BIN/MEX1 logical payload directly
into uncommitted process allocations. With ALLOW_TAPE clear it returns E_AGAIN without
touching tape. RAW and ZXP1-packed M48O objects use the same logical MEX1 parser.

The authorized streaming path reads and validates the M48O header, then obtains the
first 24 logical bytes through the RAW source or resident ZXP1 decoder as the MEX1
header. It proves `M48O.logical_length == MEX1.total_stored_length`, validates the
MEX1 header, then atomically reserves image+BSS, FAST stack, and ARG1/ENV1 allocations.
Subsequent logical image bytes decode/stream directly to their final image addresses
while the M48O logical CRC and MEX1 body CRC are accumulated. BSS is zeroed. Logical
relocation entries are then consumed in strictly increasing order and may patch the
uncommitted image immediately after each entry passes its bounds/order checks. A PACKED stream allocates one 272-byte decoder state/history before its first
logical byte and maintains that history continuously across the MEX1 header,
image, and relocation portions. If that state cannot be allocated the operation
fails E_NOMEM before committing process state. It is released on success or any
failure.

This is the one deliberate exception to Section 8.1's RAM-resident ordering rule:
for a sequential tape source, patches may occur before the final body CRC comparison,
but the allocation is private and can never become READY until the complete M48O
payload CRC, MEX1 body CRC, relocation sequence, and all length checks pass. Any later
failure discards every new allocation, so externally visible failure remains atomic.
No relocation table needs to be retained in RAM. An explicit `load /bin/name` still
creates a persistent RAM object and may therefore make a later spawn fail E_NOMEM if
object+process residency cannot coexist.

When `save` writes an already-PACKED RAM object, it first allocates one 272-byte
streaming decoder state and performs a decoder-to-discard pass to recompute logical
length/CRC from the resident packed bytes (the compact 20-byte object record
intentionally does not cache CRC), then writes those same validated ZXP1 bytes
directly in <=512-byte source slices with matching PACKED metadata. If the decoder
state cannot be allocated, save returns E_NOMEM before tape output begins.

For a RAW eligible object, `save` attempts to allocate the target encoder's exact
512-byte last-occurrence workspace. If unavailable, it writes the object RAW. If
available, pass 1 computes exact packed length and logical CRC without allocating a
second full object. If packed length is smaller, pass 2 uses the same 512-byte encoder
workspace plus one separate 512-byte tape-output chunk buffer and writes a PACKED
M48O stream; if that output buffer cannot be allocated before tape output begins,
`save` falls back to RAW. Otherwise it writes RAW immediately. Thus optional cassette
compression may require up to 1024 transient arena bytes but never requires a complete
compressed duplicate, and inability to obtain optional compression workspace does not
make an otherwise valid RAW save fail.

## 19.5 Tape commands

Required shell operations:

    save path
    load path
    verify path
    tape scan

`save` writes one M48O object using the path's exact base name/type/directory target. It
rejects pseudo/catalog-only/system-internal objects that are not persistable through the
public command.

`load path` searches forward for an M48O header whose exact target directory and
case-sensitive base name match the requested resolved path. Header validation includes
the target/type placement matrix in Section 18.4. The incoming representation is built
privately and its transport framing, stored length, ZXP1 stream if any, and logical CRC
are completely validated before namespace mutation. If no RAM object exists, commit a
new mutable object. If a mutable RAM object already exists, any live open description
causes E_BUSY; otherwise the validated incoming metadata/payload atomically replaces the
old entry and only then frees the old payload. On any failure the prior object remains
byte-identical. Pseudo, pinned/system, DIR/DEV, and immutable catalog entries cannot be
replaced. Loading a `/bin` BIN over a catalog-only BCAT name creates a resident shadow;
BCAT itself is not modified. Candidate bits are cleared before replacement/reuse becomes
visible.

`verify path` searches the same exact target/name. It requires incoming type and logical
length to match the resident mutable object's type/length; RAW/PACKED representation may
differ. It streams logical bytes and compares them while validating CRC. Metadata/codec
mismatch is E_FORMAT; a well-formed but byte-different payload returns E_IO. It never
changes the RAM object.

`tape scan` reports validated M48O headers sequentially and consumes each object's
payload with bounded scratch as defined in Section 10.1.

## 19.6 Deletion and replacement

`rm` removes only the volatile RAM object. Saving a later object with the same
name creates another physical record. No hidden rule claims the later copy
erases or globally supersedes an earlier physical tape record.

## 19.7 Blocking and timing

ROM tape operations are global and synchronous. They may disable interrupts for
timing-critical regions. While active, cooperative process progress pauses and
software wall time derived only from frame interrupts cannot be assumed to
advance perfectly. The `date`/`cron` contract explicitly treats long cassette
operations as periods where clock precision may degrade.

## 19.8 Official system/demo tape order

Fixed boot prefix:

    zx48ux
    zx48uxscr
    kernel
    sh
    font4x8
    issue
    crontab
    bincat

Required following executable/tool order on the reference system tape:

    cron
    crontab
    vi
    as
    cc
    ld
    ls
    cat
    echo
    cp
    mv
    rm
    pack
    unpack
    hexdump
    grep
    wc
    head
    tail
    cmp
    true
    false
    sleep
    which
    env
    stty
    date
    man
    whoami
    uname
    uptime
    cal
    fortune
    banner
    rev
    yes
    udg
    gfxdemo
    demo

Required demo-source/executable pairs then follow:

    hello.c / hello
    colors.c / colors
    lines.c / lines
    ship.c / ship
    ball.c / ball
    stars.c / stars
    life.c / life
    maze.c / maze
    sine.c / sine
    mandel.c / mandel
    tune.c / tune
    pipe.c / pipe
    multi.c / multi

The first five M48O objects after the native kernel are fixed as exact lower-case
`sh`, `font4x8`, `issue`, `crontab`, and `bincat`. The complete official version-1
reference system-tape order is exactly the order listed in this section; changing that
order defines a different distribution manifest and is not the certified reference tape.

The release builder validates type/target placement for every following object: all
required command/tool MEX1 objects are BIN targeting BIN; demo `.c` sources are C
targeting USERHOME; demo executables are BIN targeting USERHOME. The companion tape
likewise requires `word` and `sheet` to be BIN targeting BIN. Any manifest mismatch is
a build failure.

## 19.9 Companion applications cassette

A separate companion cassette is part of the version-1 distribution. It is not
bootable; it is an M48O stream intended to be inserted after ZX-UX is running.
Its first two required objects are exact lower-case BIN/target-BIN MEX1
applications:

    word      compact word processor
    sheet     compact spreadsheet

The user installs them with explicit loads such as `load /bin/word` and
`load /bin/sheet`. Resident `/bin` objects take precedence over BCAT as defined
in Section 18. Both applications use the same `/dev/tty`, `tty64`, object-store,
and cassette APIs as normal userland.
They are not privileged kernel components.

The word processor should exploit the 64-column 4x8 terminal for a Tasword-like
editing experience. The spreadsheet should use 64 columns of terminal width to
show substantially more cells than a 32-column interface. Exact application
feature sets belong in their own design documents and do not expand the core
kernel ABI.

---

# 20. Shell, Login Session, Environment, and Core Command Surface

Version-1 shell name:

    sh

The public command language follows Unix-style lower-case, case-sensitive
naming. Built-in and external command lookup never performs automatic case
folding.

## 20.1 Boot heading, issue, username, and prompt

After `sh` and `font4x8` have loaded and `tty64` is active, the first two visible
text lines are exactly:

    © Supratim Sanyal, SANYALnet Labs
    https://supratim-sanyal.blogspot.com/

The default `/etc/issue` contains those same two lines followed by:

    48K. One Z80. No excuses.

The shell displays `/etc/issue` exactly once; that single display is the boot
heading required above. It does not separately print a duplicate heading. It then asks:

    login: 

This is session identity, not password security. The username is 1..8 characters
and must match:

    [a-z][a-z0-9_-]{0,7}

Invalid input is rejected and reprompted. After acceptance the shell creates/
selects the fixed session directory `/home/<user>`, changes to it, initializes
the environment, and prints the normal prompt:

    $

The boot sequence therefore reaches a genuine shell prompt in the user's home
directory without pretending the machine has multi-user protection.

## 20.2 Initial environment

Required values:

    USER=<user>
    HOME=/home/<user>
    SHELL=/bin/sh
    PATH=/bin:.

Environment-variable names are case-sensitive and must match ASCII
`[A-Za-z_][A-Za-z0-9_]{0,14}`. Values are 0..63 target-printable bytes 0x20..0x7E,
including empty. Conventional upper-case names are retained because that is normal Unix
usage. `$?` is separate shell status state, not an environment entry. All ordinary shell
environment entries are exported to each child ENV1; v1 has no separate `export` state.
`set` with no arguments lists entries in unsigned-bytewise case-sensitive name order.
`set` accepts either zero arguments or exactly one post-tokenization `NAME=VALUE`
argument; the first `=` byte is the delimiter and later `=` bytes belong to VALUE.
`set NAME=VALUE` commits only if the resulting complete table still satisfies the exact
ENV1 lexical, 8-entry, and 256-byte limits; otherwise it fails without changing the table.
`unset NAME` removes an ordinary entry. `$?` cannot be set/unset. USER/HOME/SHELL/PATH
are not magically protected: if changed/unset, shell features use the resulting values
(`cd` with no operand requires a valid HOME).

## 20.2A Shell/session limits

Version-1 limits are fixed to bound parser and stack memory:

    interactive command line     247 bytes excluding terminating NUL
    arguments per command        16 including argv[0]
    pipeline stages              6 syntactically; execution may fail E_AGAIN if
                                 process slots are already occupied
    environment entries          8
    environment name length      15 bytes
    environment value length     63 bytes
    complete ENV1 block          256 bytes maximum

The 247-byte line bound guarantees that a one-command parsed ARG1, including its
8-byte header and at least one terminating NUL, can never exceed the 256-byte ARG1
limit merely because of line length. Quotes/escapes are removed during tokenization;
additional per-command ARG1 validation still applies. Overlength input is rejected with
E_TOOLONG before execution. The shell produces ARG1/ENV1 blocks exactly as specified
in Section 8.4/8.5.

## 20.3 Grammar

Version-1 grammar supports:

    command arg...
    command ; command
    command && command
    command || command
    command > path
    command >> path
    command < path
    command | command
    command &

`&` is a version-1 shell feature because it provides an immediate visible use of
the cooperative scheduler.

Parsing is byte-oriented and never delegates to a hidden BASIC or host shell parser.
Outside quotes, ASCII space and TAB separate words. A backslash quotes exactly the next
byte; a trailing backslash is E_INVAL. Single quotes preserve every enclosed byte
literally until the next single quote. Inside double quotes, `$` expansion is active and
backslash removes special meaning only from `"`, `\`, and `$`; before any other byte
the backslash itself is preserved. Unmatched quotes are E_INVAL. Operators are recognized
only when unquoted and unescaped.

Expansion is exactly `$NAME`, `${NAME}`, and `$?`. NAME uses
`[A-Za-z_][A-Za-z0-9_]{0,14}` and an unbraced reference consumes the longest valid name.
An unset NAME expands to empty; malformed `${...}` is E_INVAL. Expansion occurs in
unquoted and double-quoted text and is suppressed in single quotes. There is no
post-expansion field splitting, globbing, command substitution, arithmetic substitution,
tilde expansion, or shell functions. After expansion, every command-line/argc/argument/
ARG1 bound is revalidated before any side effect; overflow is E_TOOLONG.

Binding is exact: redirections bind to their simple command first, with at most one input
and one output redirection per simple command. `|` binds more tightly than `&&`/`||`;
`&&` and `||` have equal precedence and associate left-to-right; `;` is the
lowest-precedence sequential operator. `&` is permitted only as the final operator for
one complete pipeline and cannot be combined on that command line with `;`, `&&`, or
`||`. Parenthesized grouping/subshells do not exist in v1. The foreground pipeline status
is its final stage's status. A successful background launch sets `$?` to zero; launch
failure records the actual failure status without pretending the job started.

## 20.4 Required built-ins

    cd
    pwd
    set
    unset
    jobs
    wait
    kill
    mem
    ps
    clear
    save
    load
    verify
    tape
    exit

`cd [path]` understands only the fixed topology; with no operand it resolves `$HOME`
and fails E_NOENT if HOME is unset/invalid. `pwd` prints the exact current path. There is
no hidden general `mkdir` implementation. `wait [pid]`, `jobs`, `kill pid`, and `exit` use
the lifecycle rules in Section 20.12/21.

## 20.5 Required external/core commands

    sh
    vi
    as
    ld
    cc
    ls
    cat
    echo
    cp
    mv
    rm
    pack
    unpack
    hexdump
    grep
    wc
    head
    tail
    cmp
    true
    false
    sleep
    which
    env
    stty
    date
    cron
    crontab
    man
    whoami
    uname
    uptime
    cal
    fortune
    banner
    rev
    yes
    udg
    gfxdemo
    demo

Parent-shell stateful built-ins and the ROM-assisted built-ins below are single-stage
foreground commands in v1. Their normal stdin/stdout redirections are allowed, but using
one as any stage of a pipeline or as a background job returns E_NOTSUP before any
redirection, spawn, state mutation, or ROM call. For an allowed builtin, `sh` prepares
all redirections transactionally: it preserves the original handle-0/1/2 open-description
references in spare shell handle slots, installs every requested replacement, and on any
setup failure restores all three originals and performs no builtin side effect. After
success or builtin error it restores the original 0/1/2 references before parsing the
next command. The common composable `echo` command is therefore a tiny external
`/bin/echo`, not a parent-shell builtin.

## 20.6 Required ROM-backed shell built-ins

Version 1 includes these lower-case ROM-backed or ROM-assisted shell built-ins:

    calc
    beep
    plot
    line
    circle
    point
    ink
    paper
    bright
    flash
    inverse
    over
    border
    rom

The lower-case command name is the public interface. These are shell built-ins that invoke validated kernel/ROM wrappers and therefore do not consume BCAT entries or separate tape executables. `calc` requires exactly one shell argument after quote removal/expansion. `beep` also requires exactly one shell argument whose expression text contains exactly one top-level comma separating duration and pitch; commas inside allowed parenthesized calculator expressions do not count. Missing/extra arguments or an ambiguous separator return E_INVAL before any ROM call.

`calc` uses only the restricted expression gateway from Section 14.6, for
example:

    calc "sin(pi/4)*100"

`beep` uses the exact public syntax and numeric semantics from Section 17; in
particular the comma is part of the command grammar, e.g. `beep .5,9`.

## 20.7 Command lookup and PATH

For a single-stage foreground command token with no `/`, `sh` first checks its
parent-shell builtin tables using exact case-sensitive spelling. Only if no builtin
matches does it perform external PATH lookup. Pipeline/background stages are always
external and never consult parent-shell builtins. A token containing `/` bypasses both
builtin lookup and PATH and resolves that exact normalized executable path.

External lookup scans colon-separated `$PATH` components left-to-right with exact
case-sensitive names. An empty component denotes `.`. A nonexistent or non-directory component is skipped. A component whose normalized
directory path, or whose combined `component/name` candidate, would exceed the 31-byte
resolved-path limit is also skipped rather than aborting the whole search. A candidate
counts only when it resolves to type BIN; a same-name object of another type is skipped
and lookup continues. If PATH is unset or its value is empty, no external search occurs;
there is no hidden default. Login initializes exactly `PATH=/bin:.`. A command token
containing `/` bypasses PATH; an overlength direct normalized path returns E_TOOLONG and
a direct path resolving to a non-BIN object makes `SYS_SPAWN` return E_FORMAT.

Thus:

    ls      may resolve /bin/ls
    LS      does not resolve /bin/ls

A `/bin` name present only in `bincat` resolves as TAPE_BACKED. `sh` first tells the user
that cassette access is required and asks for PLAY/repositioning as appropriate; only
then does it set PROC1 `ALLOW_TAPE` and invoke the forward streaming spawn path. The
kernel itself never emits that prompt. For ordinary execution the M48O MEX1 payload may
stream directly into the new process image allocation rather than first creating a
duplicate persistent RAM object. An explicit user `load` command, by contrast, creates
the named RAM object. If the user declines tape access, `sh` returns a command failure
without moving tape. `which` uses exactly this external PATH component algorithm and does
not report parent-shell builtins as external executables.

## 20.8 date and software wall clock

A base 48K Spectrum has no persistent calendar RTC. ZX-UX keeps independent frame
uptime and an explicitly unset software wall clock. The public wall representation is
`TIME1` from Section 10.1: unsigned 32-bit local-session seconds since 1970-01-01 plus a
16-bit revision. Version 1 supports 1970..2099 Gregorian dates and no timezone database.

Required forms:

    date
    date -s "YYYY-MM-DD hh:mm:ss"

Unset prints `date: not set`. Set validates all fields, calls SYS_TIME_SET, and successful
sets increment revision/reset the private subsecond accumulator. Display is exactly
`YYYY-MM-DD hh:mm:ss`. On the PAL baseline the clock advances per 50 accepted IM2
frames; ROM code that disables interrupts can reduce precision, so this is not RTC-grade.

## 20.9 cron and crontab

`cron` is a tiny cooperative user daemon, never a kernel scheduler feature. The official `/etc/crontab` is the exact zero-length RAW CFG object frozen in Section 5.1. A daemon consumes one normal process slot only
while active rules exist or the user explicitly starts it.

`/etc/crontab` is CFG, maximum logical length exactly 2048 bytes, maximum 127 bytes per
physical LF-terminated line, and at most 8 active non-comment entries. Syntax is:

    minute hour day month weekday command...

Each calendar field is one decimal value or `*`: minute 0..59, hour 0..23, day 1..31,
month 1..12, weekday 0..6 Sunday=0. All five use AND semantics. Invalid date
combinations simply do not match. Also accepted:

    @boot command...
    @hourly command...
    @daily command...

`@hourly` matches exactly minute 00 of every wall-clock hour. `@daily` matches exactly
00:00 of every wall-clock day. Both require valid TIME1 and use the same once-per-
`(wall-minute,revision)` dedupe rule as ordinary calendar entries.

The command portion uses the shell's quote/backslash simple-command tokenizer and
`$NAME`/`$?` expansion rules but rejects shell operators, redirection, pipelines,
background `&`, assignments, and shell built-ins. It resolves exactly one external MEX1
through the daemon's inherited PATH/cwd/environment and spawns with `/dev/null` stdin,
`/dev/tty` stdout/stderr, and ALLOW_TAPE=0. Thus unattended cron never moves cassette;
a catalog-only target fails E_AGAIN.

Cron jobs execute serially in crontab file order. For each matching rule the daemon
spawns one child and waits/reaps it before considering the next matching rule; long jobs
can therefore skip later wall minutes and there is deliberately no catch-up. Cron's
private `$?` starts at 0 and is updated to the previous job/spawn status for expansion in
a later rule.

The daemon owns `/tmp/.cron.lock`, a DAT object. Its committed payload is exactly two
bytes: ASCII digit `2`..`7` for the owning cron PID followed by LF (0x0A). Any other
length or content is stale/invalid lock data. Startup first creates it with
O_WRITE|O_CREATE|O_EXCL, writes exactly that two-byte payload, closes that writer, then
reopens the same object O_READ and keeps that read description open for its lifetime. The retained read reference
makes normal remove/rename E_BUSY while still allowing a second startup to open/read the
PID. On initial E_EXIST, a contender opens the lock read-only; if the stored PID names a
live non-ZOMBIE process named exactly `cron`, the contender exits E_BUSY. Otherwise it
closes the stale lock, removes it, and retries exclusive creation once. Normal daemon
exit closes then removes its lock; cooperative kill may leave a closed stale object that
the next startup heals.

Cron sleeps 50 ticks between evaluations. Before every evaluation it opens, fully reads,
validates, and closes `/etc/crontab`; it never holds the configuration open across sleep
or spawn. If the valid configuration has no active entries, the daemon closes/removes
its lock and exits. After all applicable @boot rules have run, a configuration containing
only @boot/comment/blank lines likewise exits because it has no future schedule. Atomic `crontab -e` replacement is therefore observed automatically
at the next poll; there is no reload signal.

Calendar schedules and @hourly/@daily require valid TIME1. Cron remembers the last
`(wall-minute,revision)` key it evaluated and runs a matching calendar rule at most once
per such key. When TIME1 revision changes after `date -s`, the dedupe key is cleared and
only the newly observed current minute is evaluated; there is no catch-up. Long tape/
ROM interruptions likewise produce no catch-up. `@boot` means once when that particular
daemon instance starts; adding an @boot line to an already-running daemon does not run it
retroactively until a future daemon start.

`crontab` supports `-l` and `-e`. `-e` creates an exclusive temporary
`/tmp/.ct<pid>.<n>` (n=0..9), copies the current CFG logical bytes, invokes `vi`, validates
the complete edited file against all bounds, closes it, then atomically `SYS_RENAME`s it
to `/etc/crontab`. Invalid edits leave the live file unchanged. `crontab -e` invokes `vi` as a foreground interactive child. If `/bin/vi` is only
TAPE_BACKED, `crontab` uses the same explicit user-consent cassette prompt/ALLOW_TAPE
path as interactive `sh`; declining or failing that load leaves `/etc/crontab` unchanged.
After a valid nonempty replacement `crontab` may attempt to start `cron`; if `/bin/cron` is tape-backed it asks
the interactive user before ALLOW_TAPE. A duplicate daemon self-rejects via the lock. If
the new file has no active entries, `crontab` does not start a daemon; an existing daemon
will observe that state at its next poll and exit.

## 20.10 man

ZX-UX does not spend cassette/RAM on local manual pages in version 1.

Running `man` or `man topic` prints at least:

    Manuals: https://supratim-sanyal.blogspot.com/
    Search for ZXUS

A supplied topic may be echoed as a suggested additional search term, but the
exact phrase `Search for ZXUS` and website above must appear.

## 20.11 Fun-first tiny commands

The following commands are deliberately favored because they are small and make
the machine enjoyable:

`fortune`
    prints one short bundled dry/fun line from a tiny rotating table.

`banner text`
    renders large text using the ROM font/bitmap or a compact 8x8 expansion.

`cal [month [year]]`
    prints a Gregorian month. With no arguments it uses the current wall-clock month/year
    and returns E_AGAIN if date is unset. One `month` argument uses the current wall year
    and likewise requires valid wall time. Two arguments require month 1..12 and year
    1970..2099 and do not require the wall clock. Other arity/ranges return E_INVAL.

`rev`
    reverses each input line; works in pipelines.

`yes [text]`
    accepts zero or one argument; zero means literal `y`. It writes that text plus LF
    repeatedly until cancellation/write failure, providing a useful/funny pipe stress test.

`whoami`
    prints `$USER`.

`uname`
    prints a compact ZX-UX/Z80/48K system identity.

`uptime`
    formats monotonic ticks independent of whether wall time is set.

These do not justify large resident kernel features. They remain small external
programs or shell built-ins only where that is measurably smaller.

## 20.12 Foreground/background behavior, jobs, reaping, and exit

For a foreground command/pipeline, `sh` hides its cursor, creates pipes/redirections,
spawns all stages (spawn itself is not a scheduling point), and only after child PIDs are
known assigns tty-input ownership to the first stage whose stdin is the tty. It closes
its extra pipe/open-description references, then enters wait, the first point children
can be scheduled. On completion it restores PID1 tty ownership/cursor. Setup failure
closes created references, SYS_KILLs already-created children, reaps them, and restores
tty ownership.

For `&`, unless stdin was explicitly redirected the job receives `/dev/null`; stdout/
stderr inherit tty unless redirected. Background programs must not steal tty input or
draw/move the shared screen unless designed for it.

PID1 cannot allow zombies to consume the seven user process slots. Before every prompt
and whenever `jobs` runs, `sh` scans PID2..7 through SYS_PROC_INFO and immediately
SYS_WAITs each ZOMBIE child/adopted process without blocking; its bounded job table is
updated. `jobs` lists only shell-managed background jobs. Adopted services such as
`cron` remain visible through `ps` but are not shell jobs.

`wait` with no argument waits/reaps all currently shell-managed background jobs. `wait
pid` accepts one decimal PID that must be a shell direct/adopted child; nonexistent or
nonchild gives E_CHILD. `kill pid` accepts one decimal PID and uses SYS_KILL.

`exit` refuses E_BUSY while any live PID2..7 remains; the user must kill/wait/allow
services to exit. With no remaining live user process, `sh` prints `system halted` and
calls SYS_EXIT. SYS_EXIT has a PID1 special case: it disables interrupts and enters a
permanent HALT/spin state and never returns to BASIC. An unexpected PID1 exit uses the
same safe halt rather than leaving an orphan kernel.

---

# 21. Cooperative Cancellation and kill

`kill pid` is the shell interface to `SYS_KILL` and means:

    request version-1 cooperative cancellation

The kernel permission/never-started rules are exactly those in Section 10.1. For
an already-started target it sets CANCEL_PENDING. The target observes cancellation
when entering a syscall or yielding. A cancellable blocking syscall wakes and
returns E_INTR when the pending flag is consumed; nonblocking syscall entry checks
may likewise return E_INTR before side effects. The standard C48 runtime treats
cancellation at its safe points as exit status 130. A hand-written assembly task
can explicitly handle E_INTR instead, so cancellation of already-started code is
not equivalent to hardware preemption.

The IM2 handler always performs the minimal direct keyboard-matrix sample required to
recognize the Phase-0-frozen BREAK chord and only sets `break_pending`; full key decoding
remains task context. At the next syscall/yield/input boundary, if tty input owner is
PID1, BREAK cancels the current shell input line. If owner is a live PID2..7, the kernel
sets CANCEL_PENDING on that owner. BREAK does not promise process-group/pipeline
cancellation for stages that do not own tty input; `kill` is the explicit control.

A CPU-bound program that never calls the kernel cannot be forcibly preempted in version 1.
This limitation must be documented, not hidden. A future preemptive mode is separate.

---

# 22. vi Editor

The standard version-1 interactive editor is:

    vi

ZX-UX `vi` is intentionally a compact, recognizably Unix vi-compatible modal
editor, not a claim of full historical vi/POSIX feature completeness.

It is a transient MEX1 executable. When `vi` owns the foreground, `sh` waits and
the editor receives the available process workspace subject to normal arena
allocation rules. Invocation is exactly `vi` (new unnamed empty TXT buffer) or `vi path` (one existing TXT/C/ASM/CFG object); more than one path is E_INVAL. An unnamed buffer has no write target until successful `:w path`. On entry `vi` records the current TTY mode, requests `tty64`,
and uses a block cursor in normal mode plus underline cursor in insert and `:`
command-line modes. On every normal exit/error unwind it restores the prior TTY
mode and cursor setting.

## 22.1 Modes

Required modes:

    normal
    insert
    command-line

The current mode must be unambiguous. Insert mode displays the compact literal `-- INSERT --` status indicator on the bottom status line.

## 22.2 Required normal-mode movement

    h       left
    j       down
    k       up
    l       right
    0       first column
    $       end of line
    w       next word
    b       previous word
    e       end of word
    gg      first line
    G       last line

vi commands are intentionally case-sensitive. `p` and `P`, `o` and `O`, and
`g` and `G` are different commands where documented.

## 22.3 Required editing commands

    i       insert before cursor
    a       append after cursor
    o       open line below
    O       open line above
    x       delete character
    dd      delete current line
    D       delete to end of line
    yy      yank current line
    p       put after/below
    P       put before/above
    r       replace one character
    J       join current and next line
    u       one-level undo

One-level undo is a version-1 requirement. Multi-level/persistent undo is not.

## 22.4 Search

Required:

    /text   forward literal search
    n       repeat search
    N       repeat in opposite direction

A full regular-expression engine is not required for version 1. Search is
case-sensitive by default, consistent with the rest of ZX-UX.

## 22.5 Command-line (`:`) commands

Required:

    :w
    :w path
    :q
    :q!
    :wq
    :e path
    :r path
    :set
    :set number
    :set nonumber

Paths supplied to `:e`, `:r`, and `:w` are exact and case-sensitive and are
resolved relative to the editor process working directory unless absolute.

## 22.6 Buffer architecture

The version-1 representation is:

    gap buffer + compact line-offset/index support

The implementation must not retain a complete duplicate of the file merely for
undo. The one-level undo record stores only the information needed to reverse
the most recent supported edit.

Requirements:

- load TXT/C/ASM/CFG objects, then close the source input handle before accepting edits;
- preserve the type of an existing object on write;
- implement `:w` transactionally: create `/tmp/.vi<pid>.<n>` for n=0..9 with
  O_WRITE|O_CREATE|O_EXCL, preserving/requesting the intended type; retry only
  E_EXIST, write and close the complete replacement, then call atomic SYS_RENAME;
  remove only a temp whose exclusive creation succeeded in this process; failure
  before rename leaves the previous destination byte-identical;
- when creating a new path, request C for exact lower-case `.c`, ASM for exact
  lower-case `.asm`, and TXT for every other editable new name; the kernel itself
  never infers the type;
- insert/delete/replace text;
- cursor and word movement;
- literal search;
- save to the RAM object store;
- allow cassette persistence through normal `save` after returning to shell;
- show or report free-memory failure clearly;
- preserve the previous valid object if a buffer growth or write fails.

Dirty-state semantics are exact. `:q` refuses while dirty; `:q!` discards changes.
`:e path` refuses while dirty and otherwise replaces the buffer/current target only
after the new object loads successfully. `:r path` inserts bytes and marks dirty but
never retargets. `:w` writes the current target. If the buffer is unnamed and has no current target,
`:w` (and therefore `:wq`) fails with E_NOENT and the user-visible message
`vi: no file name`; buffer and dirty state are unchanged. `:w path` writes that path and
changes the current target only after the transactional commit succeeds. A successful write
clears dirty. `:wq` exits only after a successful `:w`; any save failure keeps the
editor and dirty buffer alive.


## 22.6A Screen viewport and line representation

`vi` uses tty row 23 as its status/command line and rows 0..22 as the edit viewport.
Source lines are LF-delimited logical lines and are not soft-wrapped. A line wider than
the available text area is viewed through a horizontal offset that follows the cursor;
`0`, `$`, word motion, search, and editing operate on the logical line rather than the
visible slice. With `:set number`, a fixed five-column line-number gutter reduces the
visible text width; without it all 64 columns are available. TAB bytes remain stored as
0x09 and display to the next multiple-of-8 logical column. This viewport state is not
part of the file contents.

## 22.7 UDG-aware convenience

A `:udg` convenience command is deferred from the required version-1 vi subset. UDG resources remain fully available through the graphics APIs and `udg` utility.

## 22.8 Deferred vi features

Not required in version 1:

    syntax highlighting
    multiple open buffers
    split windows
    visual mode
    named register collections
    macros/recording
    full regular-expression substitution
    persistent undo/swap files

A line-oriented bootstrap editor may exist temporarily during development, but
it is not the version-1 shipped editor and must not replace the `vi` acceptance
gate.

---

# 23. Native Z80 Assembler

Version-1 command name:

    as

The assembler is a native machine-code executable.

Minimum instruction coverage:

    complete documented Z80 instruction set required by ZX-UX programs

Minimum syntax features:

    labels
    EQU
    DB
    DW
    DS
    global/export symbol
    extern/import symbol
    expressions with + - * / % & | ^ << >> and unary - ~
    parentheses
    comments

Source inclusion is deferred from the version-1 assembler; all required modules
can be assembled independently and linked through OBJ1.

Output:

    OBJ1 relocatable object

`as` accepts exactly one ASM-typed input object. The default form requires the input
base name to end in exact lower-case `.asm`; it removes that final suffix and appends
`.obj`, which must fit the 10-byte namespace limit. Otherwise `-o out.obj` is required.
The explicit output base name is exact/case-sensitive and <=10 bytes; output type is
always OBJ. Assembly writes an O_CREATE|O_EXCL `/tmp/.as<pid>.<n>` transaction object,
closes/validates the complete OBJ1, and commits it with SYS_RENAME only after successful
assembly. Syntax, allocation, or rename failure leaves any previous destination
byte-identical.

## 23.1 OBJ1 format

OBJ1 is fully specified rather than left as an implementation sketch. Stored
layout:

    24-byte header
    text/data bytes
    symbol records
    relocation records

Header:

    offset  size  field
    0       4     magic = "OBJ1"
    4       1     version = 1
    5       1     flags = 0
    6       2     header size = 24
    8       2     text/data size
    10      2     bss size
    12      2     symbol count
    14      2     relocation count
    16      2     symbol-table offset
    18      2     relocation-table offset
    20      2     CRC-16/CCITT-FALSE of every stored byte after the 24-byte header
    22      2     CRC-16/CCITT-FALSE of full 24-byte header with bytes 22..23 zero

Version-1 offsets are fixed:

    text offset         = 24
    symbol table offset = 24 + text_size
    relocation offset   = symbol_table_offset + symbol_count*20
    total length        = relocation_offset + relocation_count*6

Symbol record, 20 bytes:

    0..15   NUL-padded symbol name; maximum 15 visible bytes
    16..17  value/offset, little-endian
    18      section: 0 UNDEF, 1 TEXT, 2 BSS, 3 ABS
    19      flags: bit0 GLOBAL; remaining bits zero in v1

Relocation record, 6 bytes:

    0..1    word offset within TEXT
    2..3    referenced symbol index
    4       type = 1 (ABS16)
    5       reserved = 0

The 16-bit word already stored at the relocation offset is a signed two's-complement
`i16` addend (-32768..32767). The linker resolves the referenced symbol, adds that
mathematical signed addend in widened precision, and requires the result to be 0..65535
before writing the final 16-bit word.

Undefined GLOBAL symbols are imports. Defined GLOBAL symbols are exports. A
local symbol need not be emitted if all references have already been resolved by
the assembler. Duplicate globals, invalid section/value ranges, out-of-range
symbol indices, and unsupported relocation types are hard link errors.

C48 identifiers are limited to 15 visible characters by the language profile,
so every external/link-visible name fits directly in an OBJ1 symbol record.
Silent truncation is forbidden.

Before accepting OBJ1, `as`/`ld` performs every count multiplication and offset/length
addition in widened host/target arithmetic and rejects overflow before narrowing to 16
bits. Validation must also prove:

    header_size == 24
    flags == 0
    text_size + bss_size <= 32768
    total_stored_length <= 32768
    symbol_table_offset == 24 + text_size
    relocation_table_offset == symbol_table_offset + symbol_count*20
    total_stored_length == relocation_table_offset + relocation_count*6

For symbols, names are unique within the module and contain 1..15 visible bytes
followed by NUL/zero padding through byte 15; embedded NUL followed by nonzero bytes is
E_FORMAT. Assembly-visible names use `[A-Za-z_.$][A-Za-z0-9_.$]*`; C48-generated
external names use the C48 identifier subset. Flag bits other than GLOBAL are zero;
UNDEF symbols have value 0 and must be GLOBAL; TEXT values are <= `text_size`; BSS
values are <= `bss_size`; ABS values may use any 16-bit value.
For relocations, `relocation_count > 0` requires `text_size >= 2`; word offsets are
<= `text_size-2` and form a non-overlapping increasing sequence: after the first record each offset is at least
`previous_offset+2`. Symbol indices are in range, type is ABS16, and the reserved byte
is zero. The
linker performs symbol+addend arithmetic in widened precision and rejects any
final value above 0xFFFF.

The body CRC covers text/data, every symbol record, and every relocation record,
so relocation/symbol corruption cannot pass merely because the text bytes are
unchanged.

---

## 23.1A Overflow-safe OBJ1 arithmetic

All OBJ1 calculations are done in widened arithmetic before comparison or narrowing:

    24 + text_size
    symbol_count * 20
    relocation_count * 6
    symbol_table_offset + symbol_count*20
    relocation_table_offset + relocation_count*6
    text_size + bss_size
    final symbol + addend calculations

Arithmetic wrap is E_FORMAT; it is never accepted as a small valid object.

# 24. Linker

Version-1 command name:

    ld

Inputs:

    one or more OBJ1 modules

Output:

    MEX1 executable stored as an explicit BIN-typed RAM object. `ld ... -o name`
    requires an exact case-sensitive <=10-byte output base name. Every input must be an
    OBJ-typed object. `ld` writes the complete candidate through an exclusive
    `/tmp/.ld<pid>.<n>` BIN transaction, validates the final MEX1, closes it, and commits
    with SYS_RENAME. Any link/allocation/rename failure leaves an existing destination
    byte-identical.

Responsibilities:

- resolve symbols;
- concatenate sections;
- create relocation table;
- validate 16-bit address limits;
- compute image size;
- assign entry symbol;
- reject duplicate/undefined symbols;
- emit checksum.

The linker contains a compact built-in archive of `crt0` plus libc48 runtime
members and pulls in only referenced members. Therefore the normal command
`ld hello.obj -o hello` is self-contained and does not require the user to
position a second library tape. `crt0` is linked by default and exports the executable entry symbol `_start`; normal
MEX1 output always uses `_start` as its entry. It may be omitted only by the explicit
development-only form `-nostart -e symbol`, where `symbol` must resolve to TEXT and
becomes the MEX1 entry.

When a resolved OBJ1 ABS16 reference targets a TEXT/BSS symbol whose final value
is relative to executable image base, the linker emits the corresponding MEX1
runtime relocation offset. References resolved to ABS symbols such as ROM or
fixed syscall addresses are patched absolutely and do not become MEX1 runtime
relocations.

## 24.1 Deterministic multi-module layout and relocation

Unless `-nostart` is used, final module order begins with `crt0`, followed by user OBJ1
inputs in command-line order. The built-in runtime archive is then scanned in fixed
member order; members satisfying currently unresolved global symbols are selected, and
fixed-order scans repeat to a fixed point. Selected members are appended in selection
order. `__heap_start` and `__heap_end` are reserved linker-defined globals: references
to them are considered satisfiable during archive selection although their values are
assigned only after final BSS/heap layout, and no OBJ1 module may define either name.
After excluding only those two linker-defined symbols, any remaining unresolved global
or any duplicate defined global is a hard error.

Each module TEXT start is aligned to an even final image offset; required padding bytes
are zero. Modules retain final order. After all TEXT, the final TEXT image is padded to
an even byte count; that value is MEX1 `image_size`. BSS allocation then processes the
same final module order, aligning each module BSS start to an even offset relative to
BSS start. The linker-reserved heap follows at the next even BSS offset. The linker
synthesizes the runtime heap-boundary symbols; no OBJ1 module needs to define them. Before output, `image_size + final_bss_size` must satisfy the MEX1 <=32768 allocation bound; failure is E_NOSPC and no output object is committed.

Final symbol values are:

    TEXT  = module_text_base + OBJ1 value
    BSS   = image_size + module_bss_base + OBJ1 value
    ABS   = OBJ1 value

For each OBJ1 relocation, final patch location is `module_text_base + relocation.offset`.
The referenced symbol value plus its signed OBJ1 i16 addend is evaluated in a widened
intermediate and must lie in 0..65535. A TEXT or BSS result is written relative to
link base zero and emits one MEX1 ABS16 runtime relocation at that final patch location.
An ABS result is patched without a MEX1 runtime relocation. Final MEX1 relocation
locations are sorted ascending, unique/non-overlapping, and revalidated against the
final image.

The default entry symbol is `_start` and must resolve to TEXT. With `-nostart`, `-e name`
is mandatory and that symbol must resolve to TEXT. MEX1 `minimum_stack_size` defaults to
512 bytes; `-stack bytes` may select an even value from 64..4096 and writes that exact
value to the MEX1 header. No implementation may invent a different module ordering, BSS
packing, archive extraction, padding, stack default, or runtime-relocation rule.

---

# 25. Tiny Native C Compiler

Version-1 command name:

    cc

The compiler is a machine-code executable and runs entirely on the Spectrum.

It targets Z80 code and produces OBJ1. `cc` accepts exactly one C-typed input object.
The default form requires its base name to end in exact lower-case `.c`; it removes that
final suffix and appends `.obj`, which must fit the 10-byte namespace limit. Otherwise
`cc -o out.obj source` is required. The explicit output name is exact/case-sensitive,
<=10 bytes, and always OBJ type. `cc` writes an O_CREATE|O_EXCL
`/tmp/.cc<pid>.<n>` transaction object, closes/validates the complete OBJ1, and commits
through SYS_RENAME only after successful compilation. Compile/allocation/rename failure
leaves any previous destination byte-identical. The kernel never infers types from
suffixes.

## 25.1 Language goal

The language is a deliberately documented C subset, not a falsely advertised full ISO C compiler.

Version-1 dialect name:

    C48

Version-1 supported language features:

    void
    char
    unsigned char
    short
    unsigned short
    int
    unsigned int
    float
    pointers
    arrays
    functions
    restricted prototypes
    local variables
    global variables
    file-scope static storage
    extern
    if / else
    while
    do / while
    for
    break
    continue
    return
    sizeof
    unary operators
    arithmetic
    bitwise operators
    comparisons
    logical operators
    pointer dereference/address-of
    string literals
    character literals
    simple constant scalar initializers
    one-dimensional constant array initializers
    casts among integer scalar types and between integer scalar types and float

Version-1 operators are fixed:

    assignment            =
    arithmetic            + - * / %
    increment/decrement   ++ --
    shifts                << >>
    relational            < <= > >= == !=
    bitwise               & | ^ ~
    logical               && || !
    address/dereference   & *
    indexing/call         [] ()
    unary                 + -

Compound assignments, the conditional `?:` operator, and the comma operator are
deferred.

Deferred unless later proven affordable:

    double as a distinct format from C48 float
    long long
    variable-length arrays
    complex initializers
    variadic functions
    function pointers
    switch / case
    struct / union
    complex preprocessor macros
    optimizer passes requiring large IR
    full ISO conformance

## 25.2 Data model

C48 version 1 freezes byte size and alignment exactly:

    type                 sizeof   alignment
    char, unsigned char     1         1
    short, unsigned short   2         2
    int, unsigned int       2         2
    pointer                 2         2
    float                   5         1
    long                    unsupported

Plain `char` is unsigned; `signed char` is not a distinct version-1 type. Arrays have
no inter-element padding beyond the element `sizeof`; array stride is exactly
`sizeof(element)`. Globals and locals insert only minimum padding required by the table.
`sizeof` produces an `unsigned int`. Signed short/int use two's-complement. `void` is
valid as a function return type and pointer base type but not as an object type.

Integer semantics are frozen. Addition, subtraction, multiplication, unary minus, and
left shift wrap modulo operand width. Signed division truncates toward zero and signed
remainder has the dividend's sign. Division/remainder by zero terminates the C48 process
with status 1 through runtime error handling. Signed right shift is arithmetic; unsigned
right shift is logical. Shift counts use the low 3 bits for 8-bit operands and low 4 bits
for 16-bit operands. Pointer arithmetic scales by pointed-to `sizeof`; subtraction of
pointers into the same array/object yields a signed 16-bit element count. Ordering or
subtraction of unrelated pointers is outside the portable C48 contract.

C48 `float` is intentionally a platform-native five-byte type. It is not an
IEEE-754 32-bit `float`.

The compiler lowers floating operators and mathematical library calls to the
kernel/runtime ROM-calculator service rather than carrying a floating-point
implementation inside each program.

A version-1 function prototype may contain only supported scalar/pointer types,
fixed argument count, and no variadic marker. Prototype and definition types
must match exactly. Program entry is one of exactly `int main(void)` or
`int main(int argc, char **argv)`; other `main` signatures are rejected.

## 25.3 Calling convention

Version 1 has one externally linkable C48 calling convention: `C48_REGCALL`.
There is no second CDECL ABI and therefore OBJ1 requires no calling-convention
metadata in version 1.

Every scalar/pointer argument occupies one 16-bit call slot. The first three slots are:

    first argument     HL
    second argument    DE
    third argument     BC
    remaining args     16-bit stack words, right-to-left

An 8-bit `char` argument is zero-extended to 16 bits. The caller removes stack argument
words. SP is even-aligned at every C48 call boundary.

A C48 `float` argument is passed as a 16-bit pointer to a caller-owned five-byte
value and consumes one ordinary argument slot. The caller materializes literals
and intermediate floating results in addressable temporary storage when needed.

Return values:

    void               no value
    8-bit scalar       L
    16-bit scalar      HL
    pointer            HL

A function declared to return C48 `float` receives a hidden first argument: a
16-bit pointer to caller-provided five-byte result storage. That hidden pointer
occupies HL and shifts user arguments to DE, BC, then stack. The callee writes
the five-byte result and returns the same result pointer in HL. This rule applies
to normal functions and runtime math helpers and is tested as ABI.

Register ownership:

    AF BC DE HL        caller-clobbered
    IX                 callee-preserved when used
    IY                 OS/ROM-reserved and must not be changed
    alternate bank     OS-private; unavailable to conforming C48 code

The compiler omits an IX frame entirely for leaf/simple functions that can
address locals without it. When a frame is required, IX is the frame pointer.

## 25.4 Mandatory Z80-native code generation

The compiler backend is not allowed to emit generic 8-bit sequences when a
documented Z80 idiom is clearly smaller/faster and semantically exact.

Required optimization/code-selection cases include:

- `DJNZ` for suitable counted 8-bit loops;
- `JR Z/NZ/C/NC` for local control flow within range;
- `ADD HL,rr`, `ADC HL,rr`, and `SBC HL,rr` for suitable 16-bit operations;
- `EX DE,HL` for register-pair renaming/exchange where legal;
- `BIT`, `SET`, and `RES` for bitfields/boolean flag operations;
- rotate/shift instructions for power-of-two and bit-manipulation operations;
- `LDIR`/`LDDR` for eligible copies/moves;
- `CPIR`/`CPDR` for eligible byte searches;
- conditional `RET` when it safely eliminates a branch;
- jump-table dispatch through `JP (HL)` where size/range analysis proves a win.

The compiler must also know when *not* to use a Z80 instruction. Examples:

- `LDIR` is not automatically optimal for tiny fixed-size copies;
- contended-memory accesses can dominate nominal instruction timing;
- block instructions must preserve the C48-visible flags/register contract;
- `DJNZ` is invalid if B is live for another purpose or loop semantics differ;
- undocumented opcodes are not emitted by the portable version-1 backend.

Code-generation tests compare semantic output and, for selected golden cases,
assert the intended instruction sequence.

## 25.5 Compiler architecture

Memory-conscious pipeline:

    source stream
      ->
    lexer
      ->
    recursive-descent parser
      ->
    small expression tree / direct code emission
      ->
    symbolic Z80 emitter
      ->
    OBJ1 writer

Avoid a whole-program AST. Statements should compile incrementally. Expression trees must be bounded and released immediately.

## 25.6 Symbol tables

Use compact bounded tables.

Separate globals/externs, current function locals, and labels.

C48 identifiers are case-sensitive and limited to 15 visible characters in
version 1. A longer identifier is a compile-time error; it is never silently
truncated or hashed. This matches the fixed OBJ1 symbol-name contract and keeps
compiler symbol tables deterministic.

## 25.7 Preprocessor

Version-1 preprocessor:

    #define object-like constants
    #include "name"       one-level local include from the current directory
    #include <c48.h>       the one built-in system header

`<c48.h>` is compiled into `cc` as canonical declarations matching the runtime
archive built into `ld`, so compiling the shipped demos never requires a separate
header tape load. Macro functions, recursive include, conditional preprocessing
(`#if`, `#ifdef`), token pasting, stringification, and a full ISO preprocessor are
deferred.

## 25.8 Standard library

Minimum C48 runtime:

    exit
    yield
    sleep
    spawn
    wait
    kill
    chdir
    getcwd
    getenv

    getpid
    open
    open_typed
    close
    read
    write
    seek
    stat
    remove
    rename
    list
    pipe
    dup
    ioctl
    read_full
    write_full

    getchar
    putchar
    puts

    strlen
    strcmp
    strcpy
    strncpy
    memcpy
    memmove
    memchr
    memset

    malloc
    free

    cls
    print_at
    plot
    point
    draw
    circle
    ink
    paper
    bright
    flash
    inverse
    over
    border
    beep

    udg_define
    udg_get
    udg_draw
    udg_clear
    udg_draw_2x2

    tape_save
    tape_load
    ticks
    time_get
    time_set

    sin
    cos
    tan
    asin
    acos
    atan
    sqrt
    exp
    log
    pow
    fabs

Avoid a large general-purpose `printf` in the first release.

Provide a compact integer formatter and a small ROM-backed floating formatter.

## 25.9 ROM-backed floating point

Floating point is a version-1 C48 feature because the 48K ROM already contains
the calculator engine and mathematical functions.

The compiler does not inline a floating-point implementation.

For an expression such as:

    float x;
    x = sin(1.25) * 3.0;

the compiler emits calls into the C48 runtime, which invokes the controlled
kernel calculator service.

Required runtime operations:

    __fadd
    __fsub
    __fmul
    __fdiv
    __fpow
    __fabs
    __fsgn
    __fint
    __fexp
    __fln
    __fsin
    __fcos
    __ftan
    __fasin
    __facos
    __fatan
    __fsqrt
    __itof
    __ftoi
    __fcmp

C ABI for a five-byte value shall use pointers for general results rather than
attempt to force the value into the ordinary 16-bit return register.

A simple library-facing contract is:

    int zx_fp_exec(op, const float *lhs, const float *rhs, float *out);

Unary operations ignore `rhs`.

Integer-to-float casts lower through `__itof`/SYS_INT_TO_FP; float-to-integer casts
lower through `__ftoi`/SYS_FP_TO_INT with truncation-toward-zero and range failure. All
float relational/equality operations lower through `__fcmp`/SYS_FP_CMP; logical truth
of a float is comparison against exact floating zero. The compiler may optimize constant
and integer-only subexpressions without entering the ROM calculator.

The calculator service must be tested across cooperative task switches to prove
that no process can observe another process's intermediate calculator state.

## 25.10 Compiler memory objective

The compiler's complete process-owned live footprint -- image+BSS, FAST stack,
immutable ARG1/ENV1 bootstrap allocation, and compiler-internal dynamic workspace --
has the release target:

    <= 20 KiB

so that useful source and object data can coexist in the 32 KiB arena. Compiler
image/BSS may occupy or cross CONTENDED RAM; only its process stack is guaranteed FAST
in version 1. Compiler source/backing RAM objects receive the object store's default
COLD_PREFERRED payload policy; the compiler has no private placement syscall.

Compilation may require the shell to free nonessential RAM objects first.

The shell shall expose a clear "not enough memory for compiler" error rather than crash.

---

# 26. Program Heap

Version 1 has no user `SYS_ALLOC`. A C48 program's heap is therefore a fixed
link-time reserve inside that executable's BSS allocation.

The linker itself synthesizes these C48 runtime symbols after final BSS layout:

    __heap_start
    __heap_end

and reserves a default 1024-byte heap in BSS when normal default `crt0` is linked. With
development-only `-nostart`, the default heap is 0 unless explicitly overridden. The
linker option:

    -heap bytes

may select an even value from 0..8192. The requested heap bytes are included in
MEX1 `bss_size`, so all normal MEX1 image+BSS bounds/allocation checks already
cover them. `malloc`/`free` manage only `[__heap_start,__heap_end)` and never call
the kernel for more memory. A zero-byte heap makes `malloc` return NULL.

Kernel ownership remains at whole process-allocation granularity. A future
`SYS_ALLOC` would be a separate ABI revision rather than an implied v1 feature.

---

# 27. RAM Allocator and Z80 Memory Primitives

Kernel allocator requirements:

- deterministic;
- compact metadata;
- split blocks;
- coalesce adjacent free blocks;
- maintain one address-ordered free-extent map spanning 0x6000-0xDFFF;
- honor FAST_REQUIRED / COLD_PREFERRED / ANY exactly;
- detect double free in debug builds where feasible;
- allocation aligned to 2 bytes;
- no hidden compaction that moves process images.

Version-1 algorithm:

    one address-ordered free-extent list across 0x6000-0xDFFF; allocation policy
    evaluates each extent's intersection with the fixed 0x8000 contention
    boundary. ANY allocations may consume one contiguous range that crosses the
    boundary, while FAST_REQUIRED is constrained wholly to 0x8000-0xDFFF.

The allocator must provide, separately for FAST and CONTENDED address ranges:

    total free bytes
    largest free contiguous span within that range

plus one combined live-allocation count and combined free total for `mem`. An ANY
allocation that crosses 0x7FFF/0x8000 is one allocation, not two class-specific
allocations; its bytes simply contribute to used-byte accounting in both ranges.

Fragmentation and class-specific exhaustion are explicit test targets.

## 27.1 Mandatory FAST placements

Process stacks and pipe buffers are always FAST_REQUIRED. Normal MEX1 image+BSS
placement is ANY exactly as specified in Section 8.2 and may cross 0x7FFF/0x8000.
The allocator prefers not to consume scarce FAST-only space when an equally good
ANY placement exists.

User processes have no general SYS_ALLOC placement API in version 1. Compiler and
editor source/backing RAM objects use the object store's default COLD_PREFERRED policy;
process-internal image/BSS/heap storage remains wherever the MEX1 ANY allocation placed
it. Only their process stacks are guaranteed FAST.

## 27.2 Block transfer and search primitives

One kernel/runtime module owns tuned memory/string primitives. It shall consider
the Z80 block instruction families directly:

    LDI / LDIR
    LDD / LDDR
    CPI / CPIR
    CPD / CPDR

Primary uses include:

    loader copies
    RAM-object copies
    pipe chunk copies
    UDG-set copies
    editor gap movement
    `memcpy` / `memmove` / `memchr`
    selected `strlen` / delimiter scans
    compiler lexical byte searches

Overlap direction determines LDIR versus LDDR for memmove-like operations.
Small fixed-size copies may use unrolled ordinary loads when measured smaller or
faster.

Because repeated block instructions recognize interrupts between iterations,
concurrency tests must cover interruption/restart behavior and ensure no kernel
invariant assumes an LDIR/LDDR is indivisible.

---

## 27.3 Resident `zxpack` and exact ZXP1 format

`zxpack` is the version-1 cold-object compression subsystem. Its decoder and
small deterministic target encoder are resident kernel code so M48O objects can
be decoded immediately after the BASIC-to-kernel handoff and ordinary closed RAM
objects can be packed without loading another utility. User-facing `pack` and
`unpack` are tiny wrappers around the kernel syscalls.

### 27.3.1 ZXP1 byte stream

ZXP1 has no terminator token. The container supplies exact physical input length
and exact logical output length; a decoder succeeds only if it consumes exactly
all physical bytes and emits exactly the declared logical length.

Each token selects one command:

    0x00..0x3F  LITERAL
        length = token + 1                 ; 1..64
        followed by exactly length literal bytes

    0x40..0x7F  RLE
        length = (token & 0x3F) + 3        ; 3..66
        followed by one byte repeated length times

    0x80..0xFF  BACKREF
        length = (token & 0x7F) + 3        ; 3..130
        followed by one byte distance_minus_1
        distance = distance_minus_1 + 1    ; 1..256

BACKREF copies from already-emitted logical output. `distance` may not exceed the
number of logical bytes already emitted. Copy semantics permit overlap, one byte
at a time, so repeating patterns and distance-1 runs are valid. A command that
would emit beyond the declared logical length is E_FORMAT. A literal missing any
of its bytes, RLE/BACKREF missing its parameter byte, an invalid history distance,
logical underrun after the physical stream ends, or trailing physical bytes after
logical completion is E_FORMAT.

The empty logical object has an empty physical stream and is represented RAW,
never PACKED. A PACKED representation is committed only when ZXP1 physical length
is strictly less than logical length.

### 27.3.2 Deterministic target encoder

The Spectrum encoder is a deterministic two-pass greedy encoder requiring no
second full input copy. Each pass allocates one exactly 512-byte COLD_PREFERRED
workspace containing 256 little-endian `u16` last-occurrence positions. Every
entry is initialized to `0xFFFF` at pass start.

At logical position `p`, the current byte indexes the table. If its recorded
position `q` satisfies `1 <= p-q <= 256`, that nearest same-first-byte occurrence
is the sole BACKREF candidate and is extended byte-for-byte to at most 130 bytes
without reading beyond logical input. Independently, an RLE candidate is extended
to at most 66 bytes. A candidate shorter than 3 bytes is ignored. The longer
legal candidate wins; an equal-length RLE/BACKREF tie chooses RLE. Because only
the nearest same-first-byte candidate is tested, target compression is bounded
and deterministic rather than optimal.

After choosing a match or literal consumption, the table is updated for every
consumed logical input position so subsequent candidates see the nearest prior
occurrence. Bytes not selected for a match accumulate into LITERAL runs of at
most 64 bytes; the final literal run is flushed at end.

Pass 1 computes exact encoded length and optional logical CRC without emitting a
stored stream. Pass 2 reinitializes the 512-byte table and emits exactly that
stream. `SYS_PACK` therefore allocates exactly the required compressed destination
before pass 2 and never guesses a worst-case buffer. An explicit `SYS_PACK`
returns E_NOMEM if its 512-byte encoder workspace cannot be allocated. Automatic
background packing silently skips that candidate when workspace is unavailable.
If encoded length is not smaller than RAW length, the object remains RAW.

### 27.3.3 Host optimized encoder

The host `tools-host/zxpack` tool may use a more expensive dynamic-programming or
optimal parser, but it must emit only the exact ZXP1 token grammar above. Host
output is not required to be byte-identical to the target greedy encoder; both
must decode to identical logical bytes. Deterministic release builds require the
host encoder version/options to be fixed so identical inputs produce identical
tape images.

This division deliberately puts compression effort on the host while keeping one
tiny target decoder. Contemporary Spectrum-oriented codecs such as ZX0 demonstrate
that very small Z80 LZ-style decompressors are practical, but ZX-UX version 1
uses its own fixed ZXP1 grammar so target-side writing does not depend on a large
optimal compressor.

### 27.3.4 Decoder sinks

One decoder state machine supports four sinks:

    FINAL_MEMORY     executable/object materialization
    CALLER_STREAM    SYS_READ into caller buffers
    DISCARD          tape scan/verify/CRC validation
    TAPE_PIPE        internal validation while physical chunks arrive

The token parser is identical for all sinks. Logical CRC is updated on emitted
bytes where the enclosing operation requires it.

### 27.3.5 Direct-to-memory history

When an entire logical ZXP1 stream is decoded from logical offset zero directly
into one contiguous final memory range, BACKREF reads already-emitted bytes from
that destination and no separate 256-byte history is needed. `SYS_UNPACK` is the
canonical version-1 use of this optimization.

The optimization is **not** valid when an early logical prefix is parsed into a
separate scratch area and later output is written elsewhere, because a legal
BACKREF can reach into that prefix. Both PACKED RAM-resident MEX1 execution
(Section 8.1A) and PACKED tape-backed MEX1 execution (Section 19.4A) therefore
retain a full 272-byte streaming state/history continuously across the 24-byte
MEX1 header, image, and relocation stream.

### 27.3.6 Streaming-reader history

A PACKED RAM-object read handle allocates one 256-byte circular history plus a
16-byte decoder-control record, exactly 272 bytes COLD_PREFERRED. The state is
owned by that open description and freed on final-description close. Two independent packed open descriptions therefore require
independent histories; dup/spawn references to one description share its history. If the 272-byte state cannot be allocated, read-only open
of the PACKED object fails E_NOMEM without changing the object.

The control record stores physical source position, logical output position,
history index/count, pending command kind/count, and any one-byte parameter in a
layout frozen in `docs/zxpack.md`; it is kernel-private, not user ABI.

### 27.3.7 Atomic pack and unpack

`SYS_PACK` accepts an existing mutable RAM object. A PACKED object is a no-op
success with HL=0. DIR, DEV, TAPE_BACKED, PINNED_SYSTEM, and SYSTEM metadata are
rejected with E_PERM. A RAW object referenced by any currently open handle is
rejected E_BUSY so representation swaps cannot invalidate readers or writers.
Objects shorter than 64 bytes are valid but left RAW with HL=0. After dry-run size calculation, if ZXP1 is not
smaller, success returns HL=0 and RAW state is unchanged. Otherwise the kernel
allocates the exact compressed destination, emits and self-validates it, then
atomically swaps pointer/storage length/PACKED flag and frees the old RAW
allocation. HL returns bytes saved.

`SYS_UNPACK` on RAW is a no-op success returning logical length. On PACKED it
first rejects E_BUSY if any live handle references the object. Otherwise it
allocates a RAW destination of logical length, decodes and validates exact output,
then atomically swaps representation and frees packed storage. Failure at any
point frees only private temporary allocations and leaves the committed object
unchanged.

### 27.3.8 Opportunistic packing and allocation pressure

All allocations performed by zxpack itself (encoder workspace, packed destination,
decoder state/history, tape codec scratch) carry an internal NO_COMPACT/depth guard. An
allocation made while that guard is active may fail normally but may not invoke the
allocator's compression-victim path. Compression therefore never recursively enters
itself.

The kernel owns one 32-bit `pack_candidate` bitset, one bit per mutable object
slot. When the final open description referencing an eligible RAW object of at least 64 bytes is destroyed, close only sets that slot's candidate bit and returns; it never
runs the encoder synchronously. Reopening an object, opening it for write,
removing it, or freeing/reusing its object-table slot clears the candidate bit
before the new operation becomes visible.

PID 0 may service at most one set candidate bit per idle maintenance cycle. It
revalidates that the same slot still names an eligible mutable RAW object with no
open handles before allocating the 512-byte encoder workspace or changing data.
Failure, no savings, or E_NOMEM clears that attempt's bit and never changes the
object or a previously successful close result.

Before an ANY/COLD allocation returns E_NOMEM, the allocator may perform one
bounded synchronous victim scan independent of the bitset. It never loops
indefinitely. Candidates must be mutable RAW objects with no open handle of any
kind, no pinned/system role, and no active direct memory ownership. The dry run
requires the 512-byte encoder workspace and determines exact destination size;
packing is attempted only if current free space can hold both required temporary
workspace and the exact compressed destination at the relevant stages. This
means compression can recover space proactively but cannot magically rescue a
machine with no temporary working space.

Victim ordering is deterministic: largest logical RAW object first, then exact
bytewise path/name order. Only one victim is attempted per allocator request.

### 27.3.9 What is deliberately not compressed

Process allocations are not RAM objects. A sleeping shell/compiler can contain
absolute runtime pointers in stack/heap/global state; moving/repacking it would
invalidate those pointers, while reserving its original range would defeat much
of the memory benefit. Version 1 therefore never compresses live or suspended
process images, BSS, heaps, stacks, pipes, screen RAM, kernel RAM, or pinned
runtime resources. A future architecture may revisit process packing only with a
provable pointer/restoration model.

### 27.3.10 ZXP1 size and correctness gate

The complete resident ZXP1 codec/manager target is <=384 bytes of ordinary kernel
code/data. That code-size target excludes arena-owned per-open 272-byte decoder
states and the transient exactly 512-byte target-encoder workspace; those bytes
remain fully visible to allocator and `mem` accounting. If implementation cannot
meet the resident target while preserving all checks above, the architecture must
be revised rather than silently borrowing IM2 tables, kernel stack, or reserved
regions.

The host reference encoder/decoder is normative for format tests. Required test
vectors include all token length boundaries, distance 1/256, overlapping copies,
empty/one-byte/random/incompressible data, malformed/truncated streams, declared
length under/overrun, and exhaustive/random round trips.

### 27.3.11 Overflow-safe M48O and ZXP1 arithmetic

Physical payload length, logical length, chunk-count/remaining-byte arithmetic, ZXP1
output position, back-reference source position, and `logical_length -
physical_length` accounting are widened before validation.

A decoder must reject an output that would advance beyond logical length before writing
the byte that would cross the boundary.

# 28. Interrupt Architecture - Z80 IM 2

Version 1 uses Z80 interrupt mode 2. This is no longer an implementation choice.

## 28.1 Vector layout

Fixed values:

    I register          0xFE
    vector table        0xFE00-0xFF00 inclusive
    table fill byte     0xFD
    resolved vector     0xFDFD
    trampoline          0xFDFD: JP zx48_interrupt

The 257-byte repeated table guarantees that any low vector byte from 0x00 to
0xFF reads two initialized bytes and resolves to the same handler entry.

No user allocation can overlap the table or trampoline because both reside in
the fixed kernel range.

## 28.2 ISR responsibilities

On the PAL/50 Hz version-1 target, the Spectrum frame interrupt is used for:

- 32-bit monotonic tick update;
- exact mirror increment of ROM `FRAMES` at 23672-23674;
- software wall-clock second accumulation when wall time is valid;
- sleep deadline wake flags;
- minimal direct keyboard-matrix sampling sufficient only to recognize the Phase-0-frozen BREAK chord;
- cursor/status timing flags;
- scheduler-needed wake bookkeeping that is proven interrupt-safe.

The IM2 handler never invokes the ROM KEYBOARD/keyboard-decoding service and never
performs full key translation, repeat processing, line editing, or console dispatch.
When BREAK is recognized it sets `break_pending` and returns. Full keyboard scanning/
decoding occurs only in ordinary kernel/task context, principally when tty input is
being serviced or PID 0 is servicing an input wait. A process that monopolizes the CPU
without entering the kernel remains subject to the documented cooperative-scheduling
limitation: BREAK can set a pending flag but cannot preempt arbitrary user code.

The ISR does not perform arbitrary task preemption. Cooperative task switching
remains a syscall/block/yield action after interrupt return.

## 28.3 Fast shadow-register path

When `altreg_busy == 0`, the ISR may obtain scratch registers with:

    EX AF,AF'
    EXX

perform its bounded work, then restore with:

    EXX
    EX AF,AF'

This path is legal because conforming MEX1 tasks do not own the alternate bank.
No persistent kernel datum may live only in those registers.

## 28.4 ROM-safe path

Any task-context kernel code or Class-A/Class-B ROM wrapper that makes live use
of the alternate bank across an interruptible interval sets `altreg_busy` before the
state becomes live and clears it only after that state is finished or saved.

If an IM2 interrupt occurs while `altreg_busy != 0`, the handler uses a stack/kernel-
scratch preservation path and does not treat the alternate bank as disposable.

The exact frame and maximum cycle cost of both ISR paths are frozen by tests.

## 28.5 RETI and interrupt discipline

The canonical version-1 handler terminates with `RETI` after restoring register state and re-enabling maskable interrupts at the documented point.

ISR code may not allocate memory, perform cassette I/O, execute shell/compiler
logic, call non-reentrant heavy ROM routines, or context-switch arbitrary user
processes.

## 28.6 HALT idle contract

PID 0 normally executes the blocking sequence:

    EI
    HALT

when no READY task needs execution. IM2 wakes the CPU; the post-interrupt path then
reevaluates ready/wakeup state.

The kernel must never execute HALT with maskable interrupts disabled in a path
that expects an interrupt to resume execution.

---

# 29. Concurrency Rules

Because memory is shared and scheduling is cooperative:

1. kernel data structures are modified only with interrupts masked where an ISR could observe them;
2. task-level kernel calls are non-reentrant unless explicitly designed otherwise;
3. no task switch occurs while internal kernel invariants are transient;
4. a blocking syscall changes process state only after its wait object is fully linked;
5. wakeup removes wait linkage before marking READY;
6. pipe close/read/write operations are atomic with respect to scheduler state;
7. cassette owns a global tape lock;
8. graphics are shared and not automatically virtualized per process;
9. IY is restored to the canonical ROM/OS value 0x5C3A (ERR_NR) before returning to MEX1 code;
10. alternate-register fast ISR use is forbidden while `altreg_busy` is set;
11. the IM2 vector table/trampoline are immutable after boot except in an
    explicit interrupt-reconfiguration critical section;
12. a FAST_REQUIRED allocation never silently migrates to contended RAM.

---

# 30. Graphics Ownership Between Processes

The Spectrum has one screen.

Version 1 uses a single shared display.

Foreground-process convention:

- foreground task may draw freely;
- background tasks should not draw unless explicitly invoked as a UI service;
- shell regains screen ownership when foreground process exits.

No per-process virtual terminal is required.

A process may voluntarily save/restore a 6912-byte screen image, but doing so consumes too much RAM to be a kernel feature in 48K.

---

# 31. Shell Redirection and RAM Objects

Examples:

    cc hello.c > build.log
    cat build.log
    grep error build.log

Redirection targets RAM objects.

`>>` appends by reallocating/growing the RAM object safely.

If growth cannot be satisfied, the original object remains valid, write returns E_NOSPC/E_NOMEM, and shell reports failure.

Cassette is accessed by explicit save/load commands rather than pretending `> /dev/tape` is random-access file output.

---

# 32. Device and Fixed Filesystem Namespace

Version 1 exposes the fixed Unix-like hierarchy defined in Section 18.

Pseudo devices:

    /dev/tty
    /dev/null
    /dev/tape

`/dev/tty` is the current shared terminal and accepts the TTY ioctl operations
from Section 13. `/dev/null` discards writes and immediately returns EOF on read.
`/dev/tape` is a control pseudo-device only; normal random-access `read`/`seek`
semantics are not promised for cassette. The public `save`, `load`, `verify`,
and `tape` commands remain the normal persistence interface.

Required configuration files:

    /etc/issue
    /etc/crontab

Required executable namespace:

    /bin/sh
    /bin/vi
    /bin/cc
    /bin/as
    /bin/ld
    ... other shipped lower-case commands

The hierarchy is fixed; this is not a large VFS and version 1 does not implement
general directory creation, mounting, permissions, ownership bits, or inode
semantics.

---

# 33. Core Utilities Behavior

All shipped utility names below are lower-case. Lookup is case-sensitive.

## ls

`ls [path]` lists the current directory or one fixed namespace directory. It
shows exact stored names and type; `ls -l [path]` additionally shows logical
size, RAM/TAPE_BACKED state, and for PACKED RAM objects physical size/savings. `/bin` is the union of resident RAM-backed BIN objects and
BCAT names with resident exact-name entries taking precedence.

## cat

Copies object or stdin to stdout. Must work in pipelines.

## echo

Writes its arguments separated by one ASCII space and terminates with one LF. With no
arguments it writes only LF. It is deliberately an external MEX1 utility so it can be
used as any stage of a real cooperative pipeline.

## cp

Copies one logical RAM object atomically while preserving its source object type. If
source and destination resolve to the same exact object, success is a no-op. Otherwise
`cp` creates `/tmp/.cp<pid>.<n>` with O_CREATE|O_EXCL, streams the source's logical
bytes (PACKED is transparently decoded), closes the completed temporary, and commits via
SYS_RENAME to the destination; destination directory type placement must accept the
source type. Existing mutable destination replacement is atomic. The new RAW copy may
become an idle zxpack candidate later.

## mv

Uses the exact atomic `SYS_RENAME` semantics from Section 10.1. A case-only
rename is allowed when no distinct exact-name destination exists; replacing an
existing mutable destination is atomic and refuses E_BUSY if either object is open.

## rm

Removes a closed mutable RAM object using SYS_REMOVE. Open objects return E_BUSY;
protected/pseudo/catalog objects return E_PERM. Cassette history is never modified.

## grep

Version 1 performs literal substring matching only; there is no regex/wildcard
engine. It streams stdin (or one named input object) to stdout and matching is
case-sensitive.

## wc

Counts bytes, words, lines.

## hexdump

Displays compact hexadecimal/ASCII view.

## ps

Displays PID, state, memory, and exact process name.

## mem

Displays total arena use plus FAST and CONTENDED free totals/largest extents,
process image/stack memory, RAM-object physical memory, pipe memory, and pinned
system resource memory. `mem -c` additionally reports ZPINFO1 logical object
bytes, physical object bytes, bytes saved, RAW/PACKED counts, decoder-state
bytes, and pack-attempt/success counters.

## pack / unpack

`pack path` invokes `SYS_PACK` and reports `logical -> physical` storage when the
object becomes/remains PACKED; a valid but non-compressible object is left RAW
and is not an error. `unpack path` invokes `SYS_UNPACK` and materializes the exact
logical bytes as RAW. Both preserve type/name/case/directory metadata and are
atomic on allocation/codec failure.

## date / cal / uptime

`date` implements Section 20.8. `cal` with no arguments requires valid wall time and
otherwise prints `cal: date not set`; `cal month year` works independently for valid
1970..2099 input. `uptime` formats the 32-bit frame counter modulo 2^32 (about 994 days
at 50 Hz), so it remains usable when date is unset but deliberately wraps.

## man

Prints the website/manual-search guidance from Section 20.10 and never attempts
to load local manual pages.

## stty

Prints or changes only the terminal mode/cursor controls defined in Section
13.5.

## whoami / uname

`whoami` prints the current session username. `uname` prints exactly
`ZX-UX z80 48k` followed by LF.

## head / tail / cmp

`head [n]` and `tail [n]` default to 10 text lines; `n` is decimal 1..255.
`cmp a b` compares two RAM objects byte-for-byte and returns 0 only when equal.

## true / false / sleep

`true` returns 0; `false` returns 1. `sleep seconds` accepts an unsigned decimal
0..65535 and cooperatively sleeps using kernel ticks.

## which / env

`which name` uses the same exact external PATH resolution as `sh`, including `.` and
explicit other fixed-directory entries and the same overlength/wrong-type skipping
rules. It never consults or reports parent-shell builtins and never moves tape. On
success it prints the exact resolved path plus LF and exits 0; if no external BIN
resolves it prints nothing and exits 1. `env` prints the current case-sensitive
environment one `NAME=VALUE` entry per line.

## fortune / banner / rev / yes

`fortune` selects from a fixed small built-in table using non-security session
entropy. `banner text` renders an 8x8-style large bitmap banner. `rev` reverses
bytes within each input line. `yes [text]` writes `text` (default `y`) plus LF
repeatedly, explicitly yielding at least once per output line so cooperative
cancellation remains responsive.


## demo

Discovers the shipped C48 demonstration suite.

Examples:

    demo
    demo ship
    demo mandel

With no argument it prints each demo's lower-case executable and matching source
file. With a name, it ensures the matching source and precompiled executable are resident
in current `/home/<user>` (using normal interactive forward cassette load when missing),
then spawns the precompiled executable and waits. `demo` never silently overwrites a
resident pair member: an existing object of the expected exact type is preserved and
used (including user edits); an existing same-name object of the wrong type causes a
refusal with an explanatory message. Only missing pair members are loaded. Thus `demo ship` deliberately leaves `ship.c` available for the advertised
edit/recompile experiment. If either required pair member fails validation/load, the demo
is not run.

It should explicitly invite experimentation, for example:

    vi ship.c
    cc ship.c
    ld ship.obj -o ship
    ship

`demo SHIP` does not silently alias `demo ship`.

## udg

`udg list` lists slots 0..31; `udg show n` renders/prints one slot; `udg save name`
saves all 32 current slots as UDG1 with base=0,count=32; `udg load path` validates the
UDG1 base/count and replaces exactly those encoded slots. UDG1 persistence is otherwise
as specified in the cassette-format section.

## ROM-backed utility behavior

### calc

Evaluates only the safe numeric expression subset defined in Section 14.6.

Examples:

    calc "2+2"
    calc "sin(pi/4)"
    calc "sqrt(17)*100"

Failure to validate the lower-case allow-list occurs before entering the ROM
scanner.

### beep

Syntax is `beep duration,pitch` exactly as defined in Section 17. Both operands
accept the restricted safe numeric-expression grammar, and fractional/negative
pitch values retain Sinclair BASIC meaning. The command is a shell built-in so it is always available without moving the tape.
`which` searches external PATH entries only, so `which beep` does not manufacture an
external pathname for this builtin.

### plot / line / circle / point

Expose the OS graphics ABI as shell commands for interactive experimentation.

### rom

Displays the canonical ROM-service inventory. It never performs arbitrary
unvalidated ROM calls.

---

# 34. Error and Panic Model

Recoverable errors return errno and are printed concisely by user programs.

Example:

    cc: E_NOMEM: insufficient arena memory

Debug builds may contain invariant checks. Release builds retain checks where corruption would otherwise propagate.

A panic is reserved for corrupted process table, allocator invariant failure, impossible scheduler state, kernel stack failure, or unrecoverable ROM wrapper contract violation.

Panic output includes a numeric code that maps to documentation.

---

# 35. Kernel Stack

The dedicated kernel stack occupies:

    0xFB00-0xFCFF

It is therefore uncontended and unavailable to arena allocation.

Normal syscall entry captures the process SP and moves to this stack before
performing work that is not deliberately executing on the process context
frame. Blocking/context-switch paths materialize the documented task frame on
the task's own FAST stack before `saved_sp` is committed.

The kernel stack budget is 512 bytes. The version-1 release gate is:

    measured worst-case stack consumption <= 448 bytes
    mandatory untouched safety margin     >= 64 bytes

The measurement begins at SP=0xFD00 and includes the deepest reachable combination of:

- syscall entry and dispatcher;
- nested kernel helpers;
- allocator/object/pipe error paths;
- ROM wrapper entry/exit;
- ROM error-recovery trampoline;
- the documented stack consumption of the invoked ROM routine;
- an IM2 interrupt at every interruptible point, using whichever ISR preservation
  path consumes more stack;
- return addresses and all temporary pushes;
- debug/release code differences that can increase depth.

Release builds must retain a low-water stack guard covering the lowest 16 bytes:

    0xFB00-0xFB0F

initialized to a frozen guard pattern at boot.

The guard is checked at every return from the kernel to user code and after every ROM
wrapper returns. A damaged guard is `PANIC KSTACK`.

The guard is diagnostic, not permission to consume it. The 448-byte measured-depth
limit is still mandatory, leaving the full 64-byte architectural safety margin.

A ROM service whose maximum stack use cannot be bounded by disassembly plus execution
tests is not enabled.

Stack overflow is a kernel panic. No kernel code may assume the process stack is
available as anonymous scratch.

---

# 36. Security and Fault Model

There is no memory protection.

The system protects against accidental misuse through mandatory syscall pointer/range validation exactly as specified by each ABI record, image-header validation, relocation-bounds checks, object-length checks, pipe-state checks, cassette header/CRC checks, and process-ownership checks. No implementation may omit an ABI-mandated pointer or length validation as an optimization.

It cannot protect the kernel from deliberately malicious machine code that writes directly to kernel RAM.

Documentation must state this explicitly.

---

# 37. Development Source Tree

Version-1 project layout follows the same lower-case Unix-style naming rule:

    ZX-UX/
      architecture.md

      src/
        boot/
          loader.bas
          entry.asm

        kernel/
          kernel.asm
          syscall.asm
          scheduler.asm
          process.asm
          memory.asm
          pipe.asm
          handles.asm
          objects.asm
          zxpack.asm
          tape.asm
          console.asm
          tty64.asm
          tty32.asm
          cursor.asm
          keyboard.asm
          graphics.asm
          udg.asm
          sound.asm
          interrupt.asm
          im2.asm
          z80_primitives.asm
          ula_io.asm
          errors.asm
          rom_services.asm

        shell/
          sh.asm

        tools/
          vi.asm
          as.asm
          ld.asm
          cc.asm

        utils/
          ls.asm
          cat.asm
          echo.asm
          cp.asm
          mv.asm
          rm.asm
          pack.asm
          unpack.asm
          grep.asm
          wc.asm
          head.asm
          tail.asm
          cmp.asm
          true.asm
          false.asm
          sleep.asm
          which.asm
          env.asm
          hexdump.asm
          stty.asm
          date.asm
          cron.asm
          crontab.asm
          man.asm
          cal.asm
          uptime.asm
          whoami.asm
          uname.asm
          fortune.asm
          banner.asm
          rev.asm
          yes.asm
          udg.asm
          gfxdemo.asm
          demo.asm

        demos/
          hello.c
          colors.c
          lines.c
          ship.c
          ball.c
          stars.c
          life.c
          maze.c
          sine.c
          mandel.c
          tune.c
          pipe.c
          multi.c

        libc48/
          crt0.asm
          syscall.asm
          process.asm
          io.asm
          string.asm
          memory.asm
          zxpack.asm
          graphics.asm
          sound.asm
          udg.asm
          tape.asm
          runtime_archive.asm

      assets/
        loading.scr
        font4x8.bin
        issue.txt              UTF-8 source; build maps © -> target 0x7F
        crontab.txt           exact zero-length version-1 default CFG asset
        bincat.bin

      include/
        zx48ux.inc
        syscall.inc
        errno.inc
        mex1.inc
        obj1.inc
        tapeobj.inc

      tests/
        unit-host/
        emulator/
        cassette/
        compiler/
        multiprocessing/
        graphics/
        sound/
        compression/
        vi/
        demos/

      tools-host/
        maketap/
        inspect-mex/
        inspect-obj/
        zxpack/
        cassette-image/
        test-driver/

      docs/
        abi.md
        c48.md
        mex1.md
        obj1.md
        tape-object.md
        zxpack.md
        rom-services.md
        shell.md
        vi.md
        demos.md
        font4x8.md
        namespace.md
        time-cron.md
        test-plan.md
        word.md
        sheet.md

      apps-companion/
        word.asm
        sheet.asm

      build/

Internal format names such as MEX1/OBJ1 remain upper-case in prose and magic
bytes; their host documentation filenames are lower-case.

---

# 38. Assembly and Z80 Coding Rules

Freeze these project rules early:

- one canonical assembler syntax;
- explicit hexadecimal notation convention;
- version-1 portable builds use documented Z80 instructions only;
- undocumented opcodes require a separately named optional CPU profile and
  independent compatibility tests;
- IY is OS/ROM-reserved in conforming kernel/user ABI code;
- MEX1 application code must not use `EXX` or `EX AF,AF'` as persistent task
  storage;
- every exported routine documents inputs, outputs, flags, and clobbers;
- every ROM call is via `rom_services.asm`;
- every syscall number is declared once;
- no magic addresses outside named memory-map constants;
- no duplicated screen-address formula;
- no unchecked arena-pointer arithmetic;
- stack assumptions are documented;
- hot/cold memory placement is explicit for substantial buffers/code;
- `LDIR`/`LDDR`/`CPIR`/`CPDR` are considered before writing generic byte loops;
- small fixed transfers are measured rather than blindly forced through block
  instructions;
- `DJNZ`, relative branches, conditional returns, `EX DE,HL`, 16-bit arithmetic,
  bit operations, and indirect dispatch are preferred where semantically exact
  and objectively smaller/faster;
- the ULA output port is modified only through the central shadow/update path;
- no persistent kernel state exists only in shadow registers;
- critical routines have both byte-size and cycle-count measurements;
- cycle measurements involving 0x4000-0x7FFF distinguish contended from
  uncontended execution/data access;
- host/source filenames shipped by the project are lower-case unless a format or
  external tool contract requires otherwise;
- case-sensitive user-object behavior is tested at module boundaries rather than
  delegated to unspecified library behavior.

The goal is Z80-native code, not opcode cleverness that weakens portability or
proof.

---

# 39. Host Bootstrap Toolchain

Initial development may use a modern host assembler/linker to produce the kernel binary, native BASIC bootstrap block, 6912-byte loading-screen block, TAP/TZX release image, and utility binaries.

`tools-host/maketap` owns deterministic construction of the production boot
prefix and ordered M48O stream. It shall verify the BASIC auto-start line,
`CLEAR 24575`, SCREEN$ length/address, kernel length/address, `RANDOMIZE USR
57347`, and the exact five-resource M48O bootstrap prefix `sh`, `font4x8`,
`issue`, `crontab`, `bincat`.

Host tooling is not part of the target runtime.

The target OS remains valid only when all required runtime components execute on the 48K Spectrum.

Host scripts shall generate deterministic binaries and cassette images from source/assets.

---

# 40. Testing Strategy

Testing has four levels.

## 40.1 Static assembly checks

Check duplicate symbols, section overflow, every fixed kernel subrange, IM2
vector/trampoline placement, kernel-stack placement, FAST/CONTENDED arena
boundaries, syscall table duplication, forbidden user IY/shadow-register ABI
use where statically detectable, and object-format structure sizes.

## 40.2 Emulator deterministic tests

Use a 48K Spectrum emulator capable of loading TAP/TZX, inspecting RAM, setting keyboard input or scripted input, observing CPU registers, and taking snapshots.

Tests should inspect machine state, not only screenshots.

## 40.3 Compatibility emulator tests

Run at least two independent Spectrum emulators where practical to catch emulator-specific assumptions.

## 40.4 Real-hardware/cassette-equivalent tests

Final cassette acceptance requires either real 48K-compatible hardware with audio cassette path or a hardware-faithful EAR/MIC loop equivalent that exercises ROM tape timing.

TAP-only testing is insufficient to claim physical cassette robustness.

---

# 41. Mandatory Test Matrix

## 41.1 Boot

- start the official tape with only the normal Spectrum `LOAD ""` command;
- BASIC loader auto-starts at line 10;
- `CLEAR 24575` establishes the required bootstrap RAM ceiling;
- `zx48uxscr` loads exactly 6912 bytes into 0x4000-0x5AFF;
- a byte-for-byte expected loading screen is visible before kernel loading;
- `kernel` loads exactly 8192 bytes into 0xE000-0xFFFF;
- BASIC transfers through exact `RANDOMIZE USR 57347` / 0xE003;
- boot entry executes `DI`, abandons the BASIC return frame, and sets SP=0xFD00;
- successful boot never returns to BASIC;
- kernel preserves the loading screen through low-level initialization and
  sequential loading of the five fixed bootstrap resources;
- the exact post-kernel M48O sequence is `sh`, `font4x8`, `issue`, `crontab`,
  `bincat`;
- `font4x8` is FAST_REQUIRED, pinned, and validates as exact F4X8;
- `/etc/issue`, `/etc/crontab`, and the BCAT metadata are installed before PID 1;
- PID 1 enters with exact ARG1 `argv[0]="sh"`, zero-entry ENV1, cwd ROOT, and
  tty handles 0/1/2; after login it builds the required mutable session environment;
- tty64 displays `/etc/issue`, asks for login, then reaches the `$` prompt in
  `/home/<user>`;
- kernel fits the fixed memory map;
- free memory matches expected accounting;
- missing/corrupt screen, kernel, and `sh` cases fail in the documented phase
  without executing uninitialized memory;
- two independently generated production tape images from identical inputs are
  byte-for-byte deterministic.

## 41.2 Scheduler

- two tasks alternate on explicit yield;
- sleeping task wakes at/after requested tick;
- blocked pipe reader sleeps;
- writer wakes reader;
- blocked writer sleeps when pipe full;
- reader wakes writer;
- child exit wakes wait parent;
- zombie reaping releases memory;
- PID reuse does not corrupt old wait state;
- `SYS_KILL` of a spawned-but-never-started child makes it ZOMBIE/status 130
  without executing user code and releases its owned allocations/handles;
- `SYS_KILL` of a blocked started child wakes it to observe E_INTR; PID/parent
  permission and PID0/PID1 protection rules are enforced;
- normal idle reaches HALT and resumes on IM2;
- IM2 fast path preserves primary task registers;
- IM2 ROM-safe path preserves a synthetic ROM shadow-register workload;
- context switch restores exact primary registers, IX, SP, and return PC;
- a legal 10-character process name survives spawn and prints exactly in `ps`;
- ARG1/ENV1 bounds, argc/env counts, and malformed-block rejection are tested;
- ARG1/ENV1 remain valid under deep runtime stack use because they are outside the
  downward-growing stack; the 64-byte stack bootstrap reserve never consumes the
  advertised minimum application stack.

## 41.3 Memory

- exact-fit allocation;
- split allocation;
- free/coalesce;
- fragmented arena;
- allocation failure;
- repeated spawn/exit cycles;
- shell survives foreground allocation failure;
- FAST_REQUIRED exhaustion does not spill into contended RAM;
- COLD_PREFERRED allocation uses 0x6000-0x7FFF when appropriate;
- `mem` reports both contention classes correctly;
- process stacks and pipe buffers never enter 0x6000-0x7FFF;
- a large MEX1 image may cross 0x7FFF/0x8000 and still executes correctly;
- the single extent allocator can allocate/free/coalesce an ANY extent crossing
  0x7FFF/0x8000 without corrupting FAST-only accounting;
- shell process-owned footprint + maximum 20-KiB compiler process-owned footprint
  + packed-reader decoder state when `hello.c` is PACKED + pinned font/UDG/catalog
  resources + mandatory `hello.c` source/output objects fit with all FAST_REQUIRED
  allocations honored;
- default 1024-byte C48 BSS heap, `-heap 0`, and `-heap 8192` are reflected in
  allocation/BSS accounting without any user SYS_ALLOC.

## 41.2A Executable/object/linker edge contracts

- MEX1 with nonzero relocation_count and image_size <2 is rejected E_FORMAT;
- OBJ1 with nonzero relocation_count and text_size <2 is rejected E_FORMAT;
- a full PID table makes `SYS_SPAWN` return E_AGAIN before tape/allocation;
- direct spawn of a non-BIN object returns E_FORMAT;
- `MINFO1` fields match the exact Section-10.1 accounting definitions;
- zxpack attempt/success counters wrap modulo 65536 without corrupting current totals;
- linker-reserved `__heap_start`/`__heap_end` references survive archive selection, are
  assigned after final BSS layout, and user definitions are rejected;
- default MEX1 stack is 512 bytes; `-stack` accepts only even 64..4096;
- normal crt0 link defaults to 1024-byte heap; `-nostart` defaults to zero heap unless
  `-heap` is explicit.

## 41.3A zxpack compressed object storage

- ZXP1 literal lengths 1 and 64;
- RLE lengths 3 and 66;
- back-reference lengths 3 and 130;
- back-reference distances 1 and 256;
- overlapping back-reference copy;
- truncated literal/RLE/back-reference fails E_FORMAT;
- back-reference before logical start fails E_FORMAT;
- output overrun/underrun versus declared logical length fails E_FORMAT;
- physical stream with trailing undecoded bytes fails E_FORMAT;
- random and adversarial RAW -> pack -> unpack byte identity;
- target greedy encoder uses exactly one 512-byte last-occurrence workspace per
  pass, obeys nearest-same-first-byte/RLE tie rules, and output decodes identically
  to host decoder;
- host optimized ZXP1 streams decode identically on target;
- non-compressible input stays RAW;
- packed read/seek produces exactly RAW logical bytes;
- at least two simultaneous packed readers maintain independent 256-byte histories;
- packed O_WRITE materialization is atomic on success/failure;
- O_CREATE against an existing object preserves its type even when the caller's
  creation type would be illegal for creating a new object in that directory;
- O_APPEND writes always begin at current logical EOF even after SYS_SEEK;
- `SYS_PACK` and `SYS_UNPACK` both return E_BUSY rather than swapping a
  representation while any handle references the object;
- multiple read-only opens coexist; any read/write conflict obeys the exclusive-writer
  E_BUSY rule and no representation swap invalidates an open reader;
- final close merely sets/clears the 32-bit candidate bitset as specified and
  never runs compression synchronously;
- PID 0 performs at most one candidate pack per idle cycle;
- candidate bits are cleared safely on reopen/write-open/remove/slot reuse;
- background/allocator packing E_NOMEM or no-savings does not damage data;
- `SYS_ZXPACK_INFO` arithmetic is exact;
- `mem -c` matches allocator/object-table accounting;
- resident PACKED BIN `spawn` and `exec` decode directly to final process storage,
  preserve history across the separately parsed MEX1 header, and never materialize
  a second full RAW executable object;
- packed bootstrap `font4x8`/`bincat` decode into final pinned RAW runtime storage;
- no process image/BSS/stack, pipe, screen, pinned runtime resource, or kernel range
  is ever marked/treated PACKED.

## 41.4 Pipes

- empty read with writer alive blocks;
- empty read with no writer succeeds with HL=0;
- full write blocks;
- write with no reader returns E_PIPE;
- pipeline of at least three programs;
- short writes/reads preserve byte order.

## 41.5 Cassette

- CRC-16/CCITT-FALSE implementation matches standard check vector `123456789`
  -> 0x29B1;

- native bootstrap prefix order is exactly `zx48ux`, `zx48uxscr`, `kernel`;
- post-kernel M48O bootstrap resources are exactly `sh`, `font4x8`, `issue`,
  `crontab`, `bincat` with exact type/target IDs;
- bootstrap tape-header names are lower-case and within Spectrum limits;
- loading-screen block is exactly 6912 bytes;
- kernel CODE header records start 0xE000 and length 8192;
- official `issue` logical bytes including final LF, zero-length RAW `crontab`, and
  exact 40-entry/488-byte BCAT match the frozen release contracts;
- BCAT exact name set matches all required tape-backed `/bin` commands;
- PROC1 ALLOW_TAPE=0 returns E_AGAIN for catalog-only commands without consuming a
  tape block; ALLOW_TAPE=1 enables the validated streaming MEX1 path;
- save/load TXT;
- save/load BIN;
- save/load UDG;
- wrong name handling;
- corrupted transport checksum;
- corrupted M48O logical CRC;
- PACKED M48O malformed ZXP1 token/history/length;
- compressed tape scan validates logical CRC through discard decode;
- RAW and PACKED same logical object load identically;
- packed tape-backed MEX1 direct-execution path never allocates a second full image;
- wrong object type;
- user BREAK during tape operation returns/reports E_INTR and leaves shell-ready state;
- repeated same-name tape records documented honestly;
- case-sensitive tape lookup does not alias differing-case object names.

## 41.6 Graphics and tty64

- all four corners plot correctly;
- screen bitmap address mapping;
- line horizontal/vertical/diagonal;
- circle edge clipping behavior;
- attribute cells;
- border;
- UDG slot 0 and slot 31;
- 2x2 composed UDG;
- save/load UDG preserves exact bytes;
- F4X8 payload exact-size/CRC/format validation;
- 64 columns address independently without corrupting neighbor nibble;
- row 0/23 and column 0/63 boundaries;
- 64-column scroll preserves all 23 retained text rows;
- block and underline cursor XOR is exactly reversible;
- cursor blink never modifies bitmap from IM2 interrupt context;
- `stty cols 32` and `stty cols 64` switch predictably;
- CR/LF/BS/TAB/FF, wrap, and scroll semantics match Section 13.5A;
- target byte 0x7F renders the copyright glyph in tty64.
- `SYS_BEEP` and shell `beep` preserve BASIC duration,pitch order;
- `beep 1,0`, `beep .5,9`, `beep .25,-12`, and `beep .5,0.5` succeed;
- malformed/missing comma, forbidden expression tokens, and ROM-rejected values
  fail without escaping into BASIC;
- C48 `beep((float)0.25,(float)0.5)` exercises the same kernel service.

## 41.7 Shell, login, namespace, time, and case semantics

- quoting;
- redirection;
- append;
- pipeline;
- && and ||;
- missing command;
- child nonzero exit status;
- memory exhaustion;
- BREAK behavior;
- `ls` resolves while `LS` does not alias it;
- `hello.c`, `Hello.c`, and `HELLO.C` can coexist as distinct RAM objects;
- cassette lookup preserves and compares case exactly;
- case-only rename behaves deterministically;
- `calc "sin(pi/4)"` is accepted while an undocumented case alias is rejected.
- exact boot heading line 1 and line 2 under tty64;
- `/etc/issue` exact first two lines and fun third line;
- reject empty, >8-char, upper-case-leading, or illegal username;
- create/select `/home/<user>` and start there;
- exact `USER`, `HOME`, `SHELL`, and `PATH`;
- `/bin`, `/etc`, `/dev`, `/home`, `/tmp`, `.`, and `..` path resolution;
- `ls` versus `LS` remains case-sensitive;
- `date` unset behavior and valid/invalid `date -s`;
- wall-clock second rollover, leap day, year/month/day boundaries;
- `@boot` cron without wall clock;
- calendar cron suppressed until wall clock valid;
- no duplicate cron firing within one minute;
- cron field bounds, Sunday=0, AND matching, `@hourly`, `@daily`, and one-session
  `@boot` behavior;
- setting wall time resets cron minute state without catch-up;
- official boot crontab is the exact zero-length RAW CFG and does not auto-start cron;
- `crontab -l` and `crontab -e`;
- `man` prints the exact website and `Search for ZXUS`;
- `which` reports only external BIN PATH results, skips wrong-type/overlength candidates,
  never moves tape, and a builtin-only name returns no output/status 1;
- `uname` prints exactly `ZX-UX z80 48k` plus LF;
- `@hourly` fires only at minute 00 and `@daily` only at 00:00;
- `whoami`, `uptime`, `cal`, `fortune`, `banner`, `rev`, and `yes` basic behavior and
  pipeline/cancellation where applicable;

## 41.8 vi

- normal/insert/command-line mode transitions;
- h/j/k/l, 0/$, w/b/e, gg/G movement;
- i/a/o/O/x/dd/D/yy/p/P/r/J editing;
- one-level undo;
- literal `/` search plus n/N;
- :w, :q, :q!, :wq, :e, :r;
- case-sensitive object names and searches;
- failed buffer growth leaves the last valid text intact;
- save/reload round trip preserves exact bytes.
- `vi` enters tty64, uses block cursor in normal mode and underline in insert mode;
- `vi` restores previous terminal mode/cursor on clean exit and error unwind;
- unnamed `:w`/`:wq` refuses exactly as Section 22.6 specifies;
- `crontab -e` real-vi integration preserves live CFG on editor/load/validation failure;
- 64-column horizontal behavior never writes beyond column 63.

## 41.9 Compiler

Compile and run programs covering every version-1 operator, simple scalar/array
initializers, int<->float casts, signed/unsigned comparison, pointers, arrays,
globals, locals, REGCALL functions with 0..6 arguments, five-byte float arguments
and hidden-result returns, recursion within stack budget, loops, logical
operators, string literals, built-in `<c48.h>`, standard runtime resolution by
`ld`, system calls, graphics, UDG calls, pipe I/O, compile error reporting,
symbol-table overflow, source too large, and output memory exhaustion.

- compiler consumes a PACKED C source through ordinary read calls without whole-file
  materialization and produces the same OBJ1 as the RAW source.

## 41.10 Shipped demos

- every required `.c` demo compiles with the native C48 compiler;
- every resulting object links with native `ld`;
- source and executable names remain lower-case;
- precompiled and freshly compiled versions produce equivalent documented
  behavior;
- all demos return cleanly to `sh`;
- demos that loop interactively yield often enough for cooperative scheduling;
- `demo name` runs the exact lower-case executable and does not case-fold.

---

## 41.11 Revision-10 correction acceptance

### 41.11.1 IY ABI

- boot establishes IY=0x5C3A before the first post-handoff ROM call;
- every syscall returns with IY=0x5C3A;
- context switches do not make IY process-local;
- each enabled ROM wrapper is tested with the frozen IY-relative system-variable
  contract;
- a synthetic wrapper that temporarily changes IY restores 0x5C3A on success and every
  trapped error path.

### 41.11.2 Alternate registers

- an interrupt at every instruction boundary of synthetic foreground EXX/EX AF,AF'
  use selects the safe ISR whenever `altreg_busy!=0`;
- no interrupt can observe `altreg_busy==0` while foreground shadow state is live;
- fast ISR path still preserves primary registers and returns correctly;
- ROM wrapper shadow-register tests use the same generic gate.

### 41.11.3 Keyboard/IM2

- IM2 recognizes the frozen BREAK chord from raw matrix reads;
- non-BREAK key combinations do not spuriously set `break_pending`;
- IM2 contains no call edge to ROM KEYBOARD/decoder routines;
- ordinary tty input still decodes the required key set outside interrupt context.

### 41.11.4 Cursor/direct screen

Acceptance must include:

1. draw tty64 text and show an XOR cursor;
2. turn cursor OFF;
3. directly write both high- and low-nibble bitmap cells at the former cursor position;
4. restore cursor;
5. blink/hide/show the cursor repeatedly;
6. prove the raw bitmap content returns byte-for-byte when the cursor is hidden.

### 41.11.5 Kernel stack

- instrumentation records high-water depth on every kernel/ROM/ISR stress test;
- the maximum is <=448 bytes in the production-linked build;
- bytes 0xFB00-0xFB0F retain the frozen guard pattern;
- deliberately corrupting the guard in a test build produces `PANIC KSTACK`.

### 41.11.6 Widened arithmetic

Invalid adversarial ranges include:

    pointer=0xDFF0 length=0x0030   ; enters kernel
    pointer=0xFFF0 length=0x0020   ; wraps 0x10000
    pointer=0x5AF0 length=0x0020   ; crosses display into protected workspace

Each invalid range must fail before a read, write, allocation, relocation, or namespace
mutation occurs.

A separate positive boundary test is mandatory:

    pointer=0x7FF0 length=0x0020

It crosses 0x7FFF/0x8000 but remains wholly inside the single permitted
0x6000-0xDFFF user-arena ABI region, so an ordinary buffer syscall must accept it
when all other ownership/access requirements are satisfied.

Format tests also choose counts/sizes whose 16-bit multiplication or addition would
wrap and prove that the widened validator rejects them.

Zero-count read/write tests verify that the buffer is not dereferenced while the handle
and other required arguments are still validated.

# 42. Golden Acceptance and Shipped Demo Programs

The official distribution ships readable C48 source and precompiled MEX1
executables for the demos below. Source is deliberately educational rather than
micro-optimized: a user should be able to open a demo in `vi`, change a small
constant or UDG bitmap, rebuild it, and immediately observe the result.

All shipped names are lower-case and case-sensitive.

## 42.1 hello.c

Canonical first program:

    int main(void)
    {
        puts("hello");
        return 0;
    }

Required workflow:

    vi hello.c
    cc hello.c
    ld hello.obj -o hello
    hello

It must be edited on target, compiled on target, linked on target, executed on
target, saved to cassette, removed from RAM, reloaded from cassette, and
executed again.

## 42.2 colors.c

Displays Spectrum INK/PAPER combinations and BRIGHT/FLASH behavior using the OS
attribute API. It demonstrates that C48 programs can use native Spectrum color
semantics without direct ROM calls.

## 42.3 lines.c

Uses `plot`, `draw`, and `circle` wrappers to create a geometric display. It is
the primary simple demonstration of ROM-backed graphics services.

## 42.4 ship.c

Defines UDGs for a ship and related small graphics, reads keyboard input, moves
the ship, changes attributes, and uses sound/timing.

The source must keep the UDG byte definitions easy to find and modify in `vi`.
This is the primary "edit something and see it change" demonstration.

## 42.5 ball.c

Animates a bouncing ball using integer coordinates, timing/yield, collision with
screen edges, and optional beeper feedback.

## 42.6 stars.c

Renders an animated starfield using integer arithmetic and either `plot` or a
documented direct-bitmap path. It stresses loops, arrays, random/pseudorandom
values, and Z80-native code generation.

## 42.7 life.c

Implements Conway's Game of Life, preferably on a 32x24 logical grid that maps
naturally onto character/UDG cells. It exercises arrays, neighbor calculation,
UDGs, keyboard input, and repeated cooperative yields.

## 42.8 maze.c

Generates and displays a maze using integer algorithms and UDG wall pieces. If
memory permits, the user may navigate it with the keyboard.

## 42.9 sine.c

Plots a sine wave using C48 `float` and the serialized Spectrum ROM calculator.
This is a required proof that ROM-backed floating-point math is usable from
native C48 source.

Representative source behavior:

    for (x = 0; x < 256; ++x) {
        y = 96 + (int)(60 * sin((float)x / 20));
        plot(x, y);
    }

The exact cast syntax follows the final C48 language subset.

## 42.10 mandel.c

Renders a small Mandelbrot set. Slow execution on a 3.5 MHz machine is
acceptable; correctness, visible progress, and clean cooperative behavior are
more important than speed.

This program intentionally provides a substantial compiler/runtime/math stress
test while also being fun to watch.

## 42.11 tune.c

Plays a short user-modifiable tune through `int beep(float duration, float pitch)`.
Pitch and duration data must be plainly visible in source, and at least one note
uses a fractional pitch so the demo proves BASIC-compatible microtonal semantics.

## 42.12 pipe.c

Demonstrates streaming stdin/stdout and real bounded RAM pipes. It may produce
textual records intended for composition such as:

    pipe | grep 7 | wc

At least three simultaneously existing cooperative tasks must be exercised by a
golden pipeline test.

## 42.13 multi.c

Demonstrates cooperative multiprocessing directly. It creates or coordinates
multiple small tasks that visibly progress when they yield. A recommended form
uses moving UDGs plus a counter/status task.

The demo must not imply preemption: a deliberately non-yielding variant should
be documented as starving its peers under the version-1 cooperative scheduler.

## 42.14 demo command

Running:

    demo

prints the available lower-case demo names and matching source files.

Examples:

    demo ship
    demo life
    demo mandel

The command runs the precompiled executable. It also prints a concise rebuild
hint such as:

    vi ship.c ; cc ship.c ; ld ship.obj -o ship ; ship

## 42.15 Cassette round trip

At minimum save and restore:

    hello.c
    hello
    one UDG set used by a demo

Power-cycle/reset the environment, boot again, reload all three using exact
lower-case names, verify CRCs, and execute the program.

Case-sensitivity must also be demonstrated by showing that an incorrect-case
request does not silently load the lower-case object.

---

# 43. Performance Targets

Performance is secondary to correctness, but grossly unusable behavior is not accepted.

Targets:

- shell key echo feels immediate;
- context switch overhead small compared with one 50 Hz tick;
- `ls` over 32 RAM objects appears effectively immediate;
- pipe streaming does not deadlock under small buffers;
- native compilation of `hello.c` completes in a practical interactive interval;
- graphics wrappers do not add excessive overhead beyond ROM/direct rendering;
- cassette speed follows Spectrum-compatible transport behavior and is not treated as a kernel performance defect.

Do not optimize before measurements identify a real bottleneck.

---

# 44. Size Gates

Mandatory release/size gates:

    loading SCREEN$            = exactly 6912 bytes at 0x4000-0x5AFF
    kernel fixed region        = exactly 8192 bytes at 0xE000-0xFFFF
    kernel code/data pool      <= 6912 bytes at 0xE000-0xFAFF
    resident zxpack core         target <= 384 bytes within kernel code/data pool
    shell                     target <= 4096 bytes
    simple core utility       target <= 2048 bytes each
    editor                    target <= 8192 bytes
    assembler                 target <= 12288 bytes
    linker                    target <= 8192 bytes
    compiler process-owned live footprint (image+BSS+stack+ARG1/ENV1+workspace) <= 20480 bytes
    pinned font4x8 payload     = 392 bytes FAST-required
    pinned UDG bank            = 256 bytes COLD-preferred
    pinned bincat              target <= 512 bytes COLD-preferred

Tool targets are measured using the scope stated above, and release acceptance also
measures real simultaneous residency. In particular the shell image+BSS+stack, the
compiler's complete <=20 KiB process-owned live footprint, any kernel-owned packed
reader state used on the compiler's behalf, pinned system resources, and the source/
output objects used by the mandatory `hello.c` compile must fit the actual 32 KiB
arena with all FAST_REQUIRED allocations satisfied. A tool exceeding its target requires
a concrete measured-memory proof, not a paper total.

---

# 45. Programming Cycle

The project shall proceed in ordered phases.

Do not begin a later phase merely because its code is interesting.

Each phase ends with its acceptance gate.

---

# 46. Phase 0 - Hardware, ROM Inventory, and ROM Proof

Phase 0 is a mandatory full-ROM discovery gate.

Deliver:

- exact 48K memory-map and ULA contention constants;
- proof that 0x4000-0x7FFF is treated as contended and 0x8000-0xFFFF as
  uncontended for the original 48K target;
- frozen IY=0x5C3A (ERR_NR) ROM-compatibility anchor and proof for every selected ROM family;
- alternate-register usage classification for every selected ROM wrapper;
- IM2 vector-table/trampoline proof using I=0xFE and the 0xFD repeated table;
- `docs/rom-services.md`;
- complete useful-routine inventory from the authoritative 48K ROM
  disassembly;
- A/B/C classification for every plausible reusable routine;
- exact entry addresses for all approved wrappers;
- register/flag/clobber contracts;
- system-variable/workspace effects;
- ROM error-path classification;
- reentrancy/task-switch classification;
- proof of which BASIC parser/evaluator components can or cannot be isolated;
- screen-address proof;
- canonical `src/boot/loader.bas`;
- canonical `assets/loading.scr` with exact 6912-byte size;
- deterministic native BASIC/SCREEN$/kernel bootstrap tape builder proof;
- executable host reference implementation of exact ZXP1 encode/decode format;
- cold boot from ordinary `LOAD ""`;
- proof of `CLEAR 24575`, `LOAD "" SCREEN$`, `LOAD "" CODE`, and
  `RANDOMIZE USR 57347`;
- proof that 0xE000 is the syscall trampoline and 0xE003 is the independent boot
  trampoline;
- proof that `zx_boot_entry` switches from the BASIC stack to SP=0xFD00 and does
  not return;
- proof that the loading screen remains intact through kernel initialization;
- console output;
- keyboard input;
- PLOT-SUB proof;
- lower DRAW proof;
- BEEPER proof;
- SA-BYTES / LD-BYTES cassette round trip;
- FP-CALC/CALCULATE arithmetic proof;
- at least SIN and SQR calculator proofs;
- floating-to-integer and float-to-text proof;
- restricted `calc` parser feasibility proof or an explicit decision to use a
  native safe expression tokenizer over the ROM calculator.

Required Class-A proof candidates:

    keyboard
    character output
    screen clear/scroll candidates
    PIXEL-ADD
    POINT
    PLOT-SUB
    line drawing
    BEEPER
    SA-BYTES
    LD-BYTES

Required Class-B proof candidates:

    BEEP command routine / public BASIC-compatible wrapper
    FP-CALC / CALCULATE
    numeric conversion
    floating printing
    arithmetic
    EXP / LN
    SIN / COS / TAN
    ASN / ACS / ATN
    SQR / POW
    BASIC expression scanner

Acceptance:

1. all ROM addresses used by code are documented and verified;
2. no production ROM address exists outside `rom_services.asm`;
3. every approved wrapper has an exact machine contract;
4. every wrapper with a possible ROM error restart has a tested safe recovery
   policy or is rejected;
5. every Class-B facility has a proved serialization/workspace policy;
6. cassette transport round-trip succeeds in a 48K environment;
7. graphics proof succeeds at edge coordinates defined by the selected ROM
   contract;
8. calculator arithmetic and transcendental proof succeed;
9. a zero-gap ROM inventory review identifies no substantial safe ROM facility
   that ZX-UX is needlessly reimplementing in RAM;
10. IM2 vectoring reaches the same trampoline for all 256 synthetic low-vector
    byte values;
11. the frozen IY=0x5C3A (ERR_NR) contract survives every approved ROM-wrapper proof;
12. each wrapper is classified for alternate-register/interrupt safety;
13. the production BASIC loader auto-starts from ordinary `LOAD ""` and loads
    the exact SCREEN$/kernel sequence;
14. the kernel entry at 0xE003 permanently takes ownership without returning to
    BASIC;
15. the screen block is exactly 6912 bytes and remains visible until the kernel
    deliberately replaces it;
16. the kernel block is exactly 8192 bytes at 0xE000-0xFFFF;
17. ZXP1 host reference round-trips zero-length and every boundary command length,
    malformed-token/length/distance cases fail deterministically, and random corpus
    round-trips are byte-identical.

The zero-gap scan must be repeated after all Phase-0 candidates have been
classified. Phase 1 does not begin while a potentially useful ROM subsystem
remains unclassified.

---

# 47. Phase 1 - Resident Kernel Skeleton

Deliver:

- fixed 0xE000-0xFFFF kernel image;
- 0xE000 syscall gateway;
- 0xFB00-0xFCFF dedicated kernel stack;
- 0xFDFD IM2 trampoline;
- 0xFE00-0xFF00 repeated IM2 vector table;
- I=0xFE / IM2 initialization;
- fast shadow-register ISR path;
- ROM-safe ISR fallback path;
- 32-bit tick;
- panic/error core;
- FAST/CONTENDED allocator;
- process table;
- PID 0 HALT idle context and PID 1;
- SYS_VERSION;
- SYS_GETPID;
- SYS_YIELD;
- SYS_SLEEP;
- SYS_EXIT;
- frozen Section-10.1 syscall record/layout constants in `docs/abi.md`;
- tty64/tty32 console core and cursor;
- FRAMES mirror + monotonic ticks;
- software wall-clock valid/unset state and SYS_TIME_GET/SYS_TIME_SET.

Acceptance:

- linked kernel respects every fixed subrange in section 4;
- ordinary code/data remains within the exact 6912-byte 0xE000-0xFAFF pool;
- the 0xFD00-0xFDFC and 0xFF01-0xFFFF reserve areas remain unconsumed except for
  their explicitly approved fast/emergency roles;
- IM2 reaches the canonical handler for every synthetic low vector byte;
- idle HALT wakes correctly;
- fast and ROM-safe ISR paths preserve their documented register contracts;
- two synthetic tasks yield cooperatively without register/stack corruption;
- sleep/wakeup works through tick wrap tests;
- IY remains canonical at 0x5C3A (ERR_NR) across all kernel returns.

---

# 48. Phase 2 - Processes and Loader

Deliver:

- MEX1 specification;
- host-side MEX inspector;
- relocation loader;
- spawn;
- exec;
- wait;
- zombie reaping;
- process memory ownership;
- canonical stack-resident task context frame;
- saved-SP-only scheduler resume model;
- loader enforcement of FAST process stacks and version-1 executable placement;
- separate process-lifetime ARG1/ENV1 bootstrap allocation and fixed 64-byte
  stack bootstrap overhead.

Acceptance:

- two differently based copies of the same relocatable test executable run;
- relocation bounds failure is atomic;
- repeated spawn/exit produces no memory leak;
- exact register/SP/PC state survives repeated context switches;
- conforming MEX1 program starts with canonical IY=0x5C3A (ERR_NR) and cannot claim alternate
  registers as ABI-preserved state.

---

# 49. Phase 3 - Generic I/O and Pipes

Deliver:

- handle layer;
- stdin/stdout/stderr;
- console handles;
- null handle;
- pipe objects;
- blocking pipe scheduler integration;
- dup;
- exact READ/WRITE/OPEN/DUP/IOCTL and PROC1 ALLOW_TAPE register/packed-record ABI.

Acceptance:

- two-process producer/consumer;
- three-stage pipeline;
- EOF and broken-pipe behavior under dup/spawn reference sharing;
- exact 24-open-description exhaustion/rollback and eight-handle-per-process limits;
- independent opens have independent offsets/decoder states while dup/inherited handles share;
- no deadlock in bounded stress test.

---

# 50. Phase 4 - RAM Object Store and Fixed Unix Namespace

Deliver:

- fixed `/`, `/bin`, `/dev`, `/etc`, `/home`, `/home/<user>`, `/tmp` resolver;
- compact parent-directory IDs;
- object directory;
- object allocation;
- exact typed `SYS_OPEN`/`open_typed` plus read/write/seek/close;
- stat/list/remove/rename;
- atomic growth failure;
- exact 20-byte mutable object records with RAW/PACKED logical/physical lengths;
- resident ZXP1 pack/unpack integration, transparent packed reads, seek restart,
  write materialization, close-time candidate marking plus PID-0 idle packing,
  512-byte encoder workspace, PACKED-BIN direct execution, and `SYS_PACK`/`SYS_UNPACK`.

Acceptance:

- 32-entry directory boundary;
- object CRUD;
- fragmentation tests;
- no corruption after failed append;
- atomic SYS_RENAME no-op, case-only rename, cross-directory type validation,
  destination replacement, E_BUSY with open source/destination, and rollback on
  pre-commit failure;
- BIN/OBJ/C/ASM/TXT creation type is caller-selected and never suffix-guessed by
  the kernel;
- missing ordinary path without O_CREATE returns E_NOENT; O_TRUNC|O_APPEND truncates then appends;
- `/dev/tty`, `/dev/null`, `/dev/tape`, DIR, and BCAT-only TAPE_BACKED open semantics match Section 11.2 exactly;
- RAW -> ZXP1 -> logical read round-trip for every ordinary object type;
- pack/unpack allocation failure leaves prior representation byte-identical;
- packed seek/read matches RAW byte-for-byte;
- resident PACKED BIN spawn/exec succeeds without a second full logical copy;
- opening PACKED for write materializes atomically;
- non-compressible data remains RAW;
- allocator compaction never packs active/open-for-write/pinned/process/pipe memory.

---

# 51. Phase 5 - Cassette Object Layer

Deliver:

- frozen production tape layout documenting native bootstrap prefix plus M48O
  stream;
- deterministic `maketap` validation of native `zx48ux` / `zx48uxscr` /
  `kernel` plus exact M48O `sh` / `font4x8` / `issue` / `crontab` / `bincat`
  bootstrap prefix and types;
- fixed 32-byte M48O header with numeric type/target IDs and RAW/PACKED logical/
  physical length plus codec semantics;
- 512-byte payload chunk stream;
- exact CRC-16/CCITT-FALSE implementation and check vector;
- save/load/verify/scan;
- RAM-object integration;
- user prompts for tape positioning/PLAY/RECORD.

Acceptance:

- a deterministic Phase-5 fixture tape (using contract-valid stub resources where later
  phases have not yet produced final binaries) begins with exact native `zx48ux`,
  `zx48uxscr`, `kernel`, followed by exact M48O `sh`, `font4x8`, `issue`, `crontab`,
  `bincat`; final release-content byte identity is a Phase-12 gate;
- bootstrap screen/kernel length and load-address contracts pass;
- text/executable/UDG round trips with exact case preservation;
- corrupted CRC rejected;
- PACKED M48O load validates logical CRC while retaining packed mutable RAM
  storage, while packed `font4x8`/`bincat` bootstrap SYSTEM resources decode to
  final pinned RAW runtime allocations;
- RAW save may stream-compress directly to tape without a full duplicate;
- packed MEX1 executes by streaming decode directly into final process allocation;
- BREAK/error recovery returns to shell-ready state.

---

# 52. Phase 6 - Shell

Deliver:

- tty64 boot heading and `/etc/issue`;
- username prompt and `/home/<user>` initialization;
- `PATH=/bin:.` command lookup;
- line input and exact Section-20.3 parser/expansion/precedence rules;
- parent-shell built-ins whose kernel dependencies already exist;
- external command loader and final tiny composable `/bin/echo`;
- transactional builtin redirection setup/rollback;
- redirection, `;`, `&&`, `||`, pipelines, and job reporting;
- exact case-sensitive lookup, ARG1/ENV1 limits, background `/dev/null` stdin,
  foreground tty ownership, and shell cursor restoration;
- dispatch hooks for final ROM graphics/sound built-ins, which close in Phase 7.

Acceptance:

- golden core-shell parser/lookup suite;
- `/bin/echo` piped through the Phase-3 sink/consumer fixture;
- quoted/escaped operator plus `$NAME`/`${NAME}`/`$?` expansion tests;
- PATH empty-component, unset/empty PATH, nonexistent/non-directory/overlength/wrong-type
  component, slash-bypass, and builtin-precedence tests;
- parent-shell builtins in pipeline/background return E_NOTSUP before side effects;
- failed builtin redirection setup restores handle 0/1/2 and performs no side effect;
- failed command returns correct status and shell survives child error return;
- mixed-case command/object lookup remains exact.

---

# 53. Phase 7 - Graphics, Attributes, Sound, UDGs

Deliver:

- graphics syscall set;
- ROM-backed graphics wrappers where Phase 0 approved them;
- attribute state;
- point/plot/draw/circle;
- border;
- ROM-backed BASIC-compatible `SYS_BEEP`/`beep duration,pitch`;
- final Section-20.6 ROM-backed shell built-ins (`calc`, `beep`, graphics/attribute
  commands, and `rom`) wired through validated kernel services;
- 32-slot UDG bank;
- UDG draw;
- UDG persistence utility;
- 2x2 user-library helper.

Acceptance:

- GFX golden program;
- exact UDG byte round trip;
- screen edge tests;
- no corruption outside display/attribute memory;
- `beep 1,0`, `beep .5,9`, `beep .25,-12`, and `beep .5,0.5` complete with
  the documented BASIC-compatible semantics and return cleanly to `sh`;
- C48 `int beep(float duration,float pitch)` reaches the same `SYS_BEEP` service
  and returns 0 or the mapped positive errno exactly as documented.

---

# 54. Phase 8 - Core Utilities

Deliver (with `/bin/echo` already delivered in Phase 6 and regression-tested here):

    ls
    cat
    cp
    mv
    rm
    pack
    unpack
    grep
    wc
    head
    tail
    cmp
    true
    false
    sleep
    which
    env
    hexdump
    ps
    mem
    udg
    gfxdemo
    stty
    date
    cron
    crontab
    man
    cal
    uptime
    whoami
    uname
    fortune
    banner
    rev
    yes
    demo

Acceptance:

- utilities operate on stdin/stdout so they compose through pipes;
- utility errors propagate through shell exit status;
- `echo hello | wc` uses final external `/bin/echo`;
- `demo` is tested with contract-valid demo fixture pairs; final demos close in Phase 12;
- `crontab -e` uses a contract-valid editor fixture for transaction/validation; real
  `/bin/vi` integration closes in Phase 9.

---

# 55. Phase 9 - vi Editor

Deliver:

- native `vi` MEX1 executable;
- normal, insert, and command-line modes;
- required movement/edit/search/ex-command subset from Section 22;
- one-level undo;
- C/ASM/TXT/CFG object editing;
- exact case-sensitive object lookup;
- memory-pressure handling;
- `docs/vi.md`.

Acceptance:

- create/edit/save/reload source entirely on target;
- edit `hello.c`, rebuild it, and preserve exact source bytes;
- `:e hello.c` and `:e HELLO.C` are distinct lookup requests;
- p/P, o/O, n/N, and g/G semantics demonstrate command case sensitivity;
- source remains intact after failed buffer growth;
- `:w` uses O_CREATE|O_EXCL `/tmp/.vi<pid>.<n>` transaction storage and atomic
  `SYS_RENAME`, so collisions never clobber unknown temps and any failed write/rename
  leaves the prior destination byte-identical;
- source input handle is closed after load; `:q`, `:q!`, `:e`, `:r`, `:w path`, and `:wq` obey the exact dirty/retarget/commit rules from Section 22;
- unnamed `:w`/`:wq` without a path fail E_NOENT with `vi: no file name`;
- `crontab -e` uses real `/bin/vi`, including tape-backed explicit-consent behavior, and
  commits only validated CFG;
- editor stays within its release size budget.

---

# 56. Phase 10 - Native Assembler and Linker

Deliver:

- OBJ1 specification;
- assembler;
- linker;
- runtime startup object;
- host-side format inspectors.

Acceptance:

- write lower-case-named assembly source on target;
- assemble;
- link MEX1;
- run;
- save to cassette with exact case preservation;
- reload and run.
- multi-module golden link proves exact crt0/user/archive order, even TEXT/BSS alignment, zero padding, symbol values, archive fixed-point selection, ABS-vs-runtime relocation treatment, sorted final relocations, and `_start`/`-nostart -e` entry rules.
- assembler and linker syntax/link/allocation failures preserve any previous output object byte-identically through their `/tmp` + SYS_RENAME transactions.

---

# 57. Phase 11 - C48 Compiler

Deliver:

- C48 language spec;
- lexer;
- parser;
- code generator;
- OBJ1 writer;
- standard runtime library;
- five-byte C48 `float`;
- ROM-calculator runtime bridge;
- ROM-backed transcendental/math library;
- fixed BSS-backed C48 heap and `int beep(float,float)` runtime wrapper.

Acceptance:

- complete compiler golden suite;
- `hello.c` full target-native lifecycle;
- every Section-42 shipped demo source compiles and links natively;
- graphics/UDG C program;
- pipe-aware C program;
- golden code-generation suite for DJNZ/JR/bit operations/16-bit arithmetic/
  block primitives;
- generated portable binaries contain no undocumented opcodes;
- generated code preserves IY and does not own the alternate register bank;
- C48_REGCALL including float-argument pointers and hidden float-result pointer is
  verified byte-for-byte;
- `sizeof`, alignment, array stride, char zero-extension, 16-bit stack slots, even-SP call boundary, wrap/shift/division/remainder, and pointer-arithmetic semantics match Section 25 exactly;
- `ld hello.obj -o hello` resolves crt0/libc48 from its built-in archive with no
  separate library tape;
- default and explicit `-heap` reserves are reflected exactly in MEX1 BSS;
- compiler syntax/allocation/rename failures preserve any previous `.obj` destination byte-identically through its transaction;
- `tune.c` proves the C48 BASIC-compatible `beep` wrapper including fractional
  pitch.

---

# 58. Phase 12 - Integrated Multiprocessing Development Environment

Deliver:

- polished shell/tool integration;
- standard `vi` workflow;
- lower-case, case-sensitive userland and object namespace;
- complete shipped C48 demo source/executable set;
- byte-exact final reference system tape following Section 19.8, including the frozen
  `issue`, zero-length RAW `crontab`, and exact 40-entry/488-byte BCAT;
- `demo` discovery/runner;
- memory diagnostics;
- cassette workflow;
- documentation;
- companion-app design documents `docs/word.md` and `docs/sheet.md`;
- deterministic companion cassette containing lower-case `/bin/word` and `/bin/sheet`;
- recovery behavior.

Acceptance:

From a powered/reset 48K configuration and the official production tape:

1. verify the production tape's complete object order and frozen release-asset bytes
   match Sections 5.1 and 19.8, then type only `LOAD ""` and press PLAY;
2. verify BASIC auto-start, exact SCREEN$ load, kernel load, and permanent 0xE003
   handoff;
3. verify exact bootstrap M48O resources `sh`, `font4x8`, `issue`, `crontab`,
   `bincat` load and validate before PID 1;
4. verify tty64 displays exactly `© Supratim Sanyal, SANYALnet Labs` on line 1
   and `https://supratim-sanyal.blogspot.com/` on line 2;
5. enter a valid <=8-character username and verify `$USER`, `$HOME`, `$SHELL`,
   `$PATH`, `pwd`, `/home/<user>`, and `/etc/issue`;
6. show `stty` reports 64x24 and cursor control works;
7. prove `/bin`, `/etc`, `/dev`, `/home`, `/tmp`, `.`, `..`, and exact-case PATH
   lookup;
8. run `man` and verify the exact website plus `Search for ZXUS`;
9. show `date` unset behavior, set a valid wall clock, and execute one `@boot` or
   calendar `cron`/`crontab` job as applicable;
10. load or locate `hello.c`, edit it with `vi`, compile with `cc`, link with `ld`,
    and run `hello`;
11. prove an incorrect-case lookup does not alias the lower-case command/object;
12. run a true multi-stage pipeline and a cooperative background task;
13. define/use UDGs and verify ROM UDG state points outside kernel/IM2 memory;
14. run `demo ship`, edit/rebuild `ship.c`, and run the rebuilt `ship`;
15. compile/run `sine.c` as ROM-floating-point proof and `multi.c` as cooperative
    multiprocessing proof;
16. run `beep .5,0`, `beep .25,-12`, and a fractional-pitch note, then run
    representative fun commands including `fortune`, `banner`, `cal`, `rev`, and
    cancel `yes` cleanly;
17. prove `pack`, `unpack`, `mem -c`, transparent packed-source compilation, and
    direct packed-MEX1 tape execution while showing logical/physical accounting;
18. save source and executable to cassette, power-cycle/reset, repeat standard
    boot, restore them, verify CRCs, and execute the restored program;
19. load the companion applications cassette and prove both `word` and `sheet` are
    ordinary lower-case `/bin` MEX1 applications using tty64; `word` must create/edit/
    save/reopen a TXT object, and `sheet` must create/save/reopen a small sheet object
    and recompute at least one `+ - * /` arithmetic formula as frozen in their docs;
20. verify all operations remain within the 48K memory architecture.

This is the version-1 architecture gate.

---

# 59. Deferred Features

Explicitly out of scope for version 1:

- true preemptive multitasking;
- MMU-style process isolation;
- fork();
- demand paging;
- swap;
- virtual memory;
- transparent compression of live/sleeping process address spaces or stacks;
- general user-created directory trees beyond the fixed version-1 hierarchy;
- random-access tape filesystem fiction;
- networking;
- Microdrive;
- Interface 1;
- printer;
- mouse;
- 128K bank switching;
- AY sound;
- dynamic libraries;
- full POSIX;
- full ISO C;
- per-process virtual screens;
- GUI/window manager.

These may be separate future architecture increments.

---

# 60. Stretch Goals

After version 1:

1. Optional 128K build while preserving 48K ABI.
2. Microdrive/disk backend implementing the same object API.
3. Preemptive scheduler build.
4. Signal mechanism.
5. Expanded ROM-backed floating-point formatting and advanced numeric functions.
6. `struct`/`union` expansion in C48.
7. compact integer printf.
8. native debugger/monitor.
9. source-level compiler diagnostics with line/column.
10. shell command history.
11. software sprites/masked UDG drawing.
12. richer Tasword-like font families, proportional/condensed modes, or >64
    columns if readability and RAM allow.
13. richer beeper sequencer/music support.
14. simple character-window UI library.
15. assembler capable of rebuilding selected OS modules on target.
16. increasingly self-hosted system rebuild.
17. experimentally safe packed suspended-process images only if a future ABI can prove
    restoration without invalidating runtime pointers; never a v1 requirement.
18. additional Unix text utilities such as `sort`, `uniq`, and `more` after v1 size
    measurements justify them.

---

# 61. Architecture Invariants

The following rules are non-negotiable unless this document is formally revised.

1. Version 1 runs in original 48K RAM.
2. ROM remains at 0x0000-0x3FFF.
3. Display RAM remains native Spectrum layout.
4. The official cassette release starts from ordinary Spectrum `LOAD ""`.
5. The production tape bootstrap prefix is exact lower-case native files
   `zx48ux`, `zx48uxscr`, `kernel`, followed by exact M48O resources `sh`,
   `font4x8`, `issue`, `crontab`, `bincat`.
6. `zx48ux` is an auto-running Sinclair BASIC program whose semantic loader is
   `CLEAR 24575`, `LOAD "" SCREEN$`, `LOAD "" CODE`, and
   `RANDOMIZE USR 57347` after cosmetic screen setup.
7. The production loading SCREEN$ is exactly 6912 bytes at 0x4000-0x5AFF.
8. The resident kernel CODE block is exactly 8192 bytes at 0xE000-0xFFFF.
9. Successful `RANDOMIZE USR 57347` is a permanent ownership handoff; ZX-UX
   does not return through the BASIC USR frame.
10. `zx_boot_entry` immediately establishes the dedicated kernel stack with
    SP=0xFD00 before substantial kernel work.
11. The loading screen remains visible through kernel initialization and `sh`
    loading unless an explicit boot error must replace it.
12. 0x6000-0x7FFF is the CONTENDED/COLD arena.
13. 0x8000-0xDFFF is the FAST user/task arena.
14. The resident kernel is fixed at uncontended 0xE000-0xFFFF.
15. The syscall gateway is fixed at 0xE000.
16. The production boot gateway is fixed at 0xE003.
17. The dedicated kernel stack is 0xFB00-0xFCFF.
18. Version 1 uses IM 2 with I=0xFE, a 257-byte 0xFD table at
    0xFE00-0xFF00, and the trampoline at 0xFDFD.
19. IY is reserved by the OS/ROM ABI and its version-1 production-ROM value is exactly 0x5C3A (ERR_NR).
20. The alternate AF'/BC'/DE'/HL' bank is OS-private/volatile and unavailable
    as persistent state to conforming MEX1 applications.
21. No persistent kernel state exists only in the alternate bank.
22. ROM wrappers classify alternate-register use and select safe interrupt
    behavior.
23. Scheduling is cooperative.
24. No fork() is required.
25. Process resume context lives on the process FAST stack; saved SP is the
    canonical scheduler resume state.
26. Processes use relocatable executables.
27. Process stacks are FAST_REQUIRED.
28. FAST_REQUIRED allocation never silently spills into contended RAM; normal MEX1
    image+BSS may use the full contiguous 0x6000-0xDFFF arena while stacks stay
    FAST_REQUIRED.
29. Pipes are real bounded RAM channels and their buffers are FAST_REQUIRED.
30. Cassette is sequential persistent object storage; the native bootstrap
    prefix does not imply random access.
31. Post-handoff ZX-UX cassette objects use the documented M48O layer over
    Spectrum ROM tape transport.
32. Tape operations are allowed to block the system.
33. UDGs are first-class, 32 slots x 8 bytes.
34. ROM service addresses are centralized and verified.
35. The 48K ROM is treated as a resident system library; safe ROM reuse is
    preferred over duplicate RAM implementation.
36. Every reused ROM routine is classified A/B/C and has a documented machine
    contract.
37. Class-B calculator/parser facilities are serialized and isolated by the
    kernel.
38. Unrestricted BASIC mutation facilities do not become normal shell/kernel
    operations.
39. The Spectrum ULA output port is owned through one authoritative shadow.
40. Shell, assembler, linker, `vi`, compiler, and utilities are target machine
    code.
41. User object/file names preserve case exactly and namespace lookup is
    case-sensitive; no automatic case folding is allowed.
42. All ZX-UX-shipped commands, tools, executables, demo names, and demo/source
    filenames use lower-case user-facing names.
43. Sinclair BASIC keyword spelling in the bootstrap loader is outside the
    ZX-UX shell namespace and does not relax invariant 41 or 42.
44. `vi` is the standard version-1 interactive editor and implements the
    documented case-sensitive modal subset.
45. The Section-42 C48 demo suite ships as both readable lower-case source and
    precompiled executables.
46. C48 is explicitly a C subset.
47. C48 uses register-first C48_REGCALL by default and preserves the OS IY
    contract.
48. C48 portable code generation uses documented Z80 instructions only.
49. C48 `float` is the documented five-byte Spectrum-ROM-compatible numeric
    representation, not IEEE-754 binary32.
50. Z80 block transfer/search instructions are first-class implementation
    candidates, not forbidden micro-optimizations.
51. Correctness never depends on precise ULA contention timing.
52. R may contribute only to non-security pseudorandom seeding.
53. No local architectural claim may pretend unsupported hardware exists.
54. Allocation failure is recoverable.
55. Current screen is shared by all processes.
56. ABI-visible numbers/formats are frozen only after tests exist for them.
57. The production tape builder is deterministic for identical inputs and
    rejects invalid screen/kernel sizes, invalid fixed boot addresses, or any
    mismatch in the five-resource M48O bootstrap prefix.

58. The normal interactive terminal is 64x24 using the validated F4X8 4x8 font;
    tty32 remains a fallback/debug mode.
59. `font4x8` is a required FAST_REQUIRED post-kernel system resource and is loaded before PID 1 is scheduled.
60. The boot heading begins with the exact requested copyright and website lines.
61. Cold boot requests a 1..8-character lower-case session username and starts
    `sh` in `/home/<user>`.
62. The fixed namespace includes `/bin`, `/dev`, `/etc`, `/home`, current user
    home, and `/tmp`; version 1 has no general `mkdir`.
63. The default environment includes exact `PATH=/bin:.`, `HOME`, `USER`, and
    `SHELL=/bin/sh`.
64. Wall-clock time is explicitly unset after cold boot until `date -s` sets it;
    uptime/ticks are separate.
65. Calendar cron entries never run while wall time is unset.
66. `/etc/issue` begins with the exact two boot-heading lines.
67. `man` always prints the requested website and exact phrase `Search for ZXUS`.
68. M48O payloads are chunked into <=512-byte ROM data blocks after one fixed
    32-byte M48O header block.
69. ZX-UX IM2 mirrors ROM `FRAMES` and explicitly owns/repoints ROM UDG state.
70. A companion applications cassette includes at least `word` and `sheet`.
71. The arena allocator is one contiguous extent map capable of ANY allocations
    crossing 0x7FFF/0x8000; only explicit FAST_REQUIRED requests are forbidden
    from consuming contended RAM.
72. The process-name field preserves all legal 1..10-character executable names.
73. MEX1 process entry uses validated ARG1 and ENV1 blocks with the documented
    version-1 bounds.
74. C48 has one link-visible calling convention, C48_REGCALL; five-byte float
    arguments are pointer-passed and float returns use the hidden result pointer.
75. Background jobs inherit `/dev/null` as stdin unless explicitly redirected and
    do not steal the interactive tty input owner.
76. `SYS_OPEN` never infers object type from a filename; typed creation is explicit
    and deterministic.
77. C48 `malloc`/`free` use only the linker-reserved BSS heap; version 1 has no
    user `SYS_ALLOC`.
78. `beep` uses public syntax `beep duration,pitch` with Sinclair BASIC-compatible
    seconds/semitones semantics, including fractional pitch.
79. Section-10.1 syscall register/record layouts are ABI-visible and may not be
    independently reinvented by kernel and userland.
80. Mutable object types are constrained by fixed directory rules: `/bin` BIN,
    `/etc` TXT/CFG, user home/tmp normal user types, SYS bootstrap-only.
81. The version-1 time constant assumes a PAL/50 Hz 48K Spectrum; alternate frame
    rates require an explicit compatibility profile.
82. ZXP1 compression applies only to kernel-controlled stored objects/cassette streams;
    it is never represented as transparent RAM, paging, or a larger live address space.
83. Active process image/BSS/heap, stacks, ARG1/ENV1, pipes, screen RAM, kernel RAM,
    and pinned runtime resources are never PACKED in version 1.
84. A mutable RAM object table entry is exactly 20 bytes; PACKED objects carry logical
    and strictly smaller storage lengths, while RAW lengths are equal.
85. Version-1 packed objects use exactly codec ZXP1; no hidden codec negotiation or
    per-object algorithm discovery is permitted.
86. PACKED reads expose exactly the logical RAW byte stream; packed seek may restart
    decoding but may not alter content semantics.
87. Any write-open of a PACKED object materializes a private RAW replacement before
    exposing a writable handle, except O_TRUNC may create an empty RAW replacement.
88. Pack/unpack and representation swaps are externally atomic; failure leaves the
    previously committed object representation valid and byte-identical; both
    `SYS_PACK` and `SYS_UNPACK` reject E_BUSY while any handle references the object.
89. M48O payload length is physical stored length; auxiliary value 1 is logical length;
    auxiliary value 2 is codec ID; payload CRC covers logical uncompressed bytes.
90. A PACKED MEX1 tape object decodes directly into its final uncommitted process image;
    no second full uncompressed executable copy is required.
91. The resident zxpack core plus all other kernel code/data must remain within the
    fixed 0xE000-0xFAFF 6912-byte pool and the total 8 KiB kernel map.
92. RAM objects permit multiple readers but exactly one exclusive writer; a representation
    swap is never performed while any handle still references that object.
93. ZPINFO1 uses 32-bit logical/saved totals so aggregate compressed logical storage
    cannot silently overflow 16-bit accounting.
94. A PACKED RAM-resident BIN executes through a continuous-history MEX1 decoder
    directly into final uncommitted process storage; it is never materialized as a
    second full RAW object merely to spawn or exec it.
95. The target encoder uses exactly one transient 512-byte nearest-occurrence table
    per pass; an explicit pack reports E_NOMEM when it cannot obtain that workspace.
96. Final handle close never performs compression synchronously: it only manipulates
    the 32-bit candidate bitset, and PID 0 services at most one candidate per idle
    cycle. Slot reopen/removal/reuse clears stale candidate state.
97. A ZXP1 direct-memory no-history optimization is legal only when the complete
    logical stream begins at logical offset zero in that same destination; MEX1
    header-splitting paths always retain 272-byte history continuously.
98. ZXP1 may compress post-kernel M48O bootstrap transport, but pinned runtime
    resources such as `font4x8` and `bincat` are always decoded into validated RAW
    pinned runtime storage before use.
99. `SYS_KILL` is the sole kernel cancellation ABI: never-started READY children can
    be terminated without executing, while already-started processes remain
    cooperatively cancellable through CANCEL_PENDING/E_INTR.
100. The compiler 20-KiB release gate includes all process-owned image+BSS, stack,
    ARG1/ENV1, and compiler workspace; kernel-owned packed-reader state is excluded
    from that number but included in simultaneous-residency acceptance.
101. Cold-boot PID 1 receives valid canonical ARG1 (`sh`) and zero-entry ENV1 before
    first execution; the post-login mutable shell environment is the authoritative
    source for ENV1 snapshots passed to subsequently spawned children.
102. `SYS_RENAME` is the atomic metadata commit primitive for mutable RAM objects:
    it can replace a closed mutable destination without copying payload bytes and
    leaves both source/destination unchanged on any pre-commit failure.
103. `vi :w` uses a PID-specific `/tmp` object plus atomic `SYS_RENAME`; it never
    progressively destroys the previously committed destination while saving.
104. Process handle slots reference a bounded 24-record open-description pool; dup and
    spawn share offsets/decoder/endpoint state through reference counts, while independent
    opens allocate independent descriptions.
105. O_EXCL/E_EXIST is the exclusive-creation primitive for `/tmp` transactions and cron
    locking; callers never delete an unknown colliding temp merely by name.
106. Extending RAM-object writes are full-or-error transactions; allocation failure leaves
    the previous committed object byte-identical.
107. Public tape load builds and validates a complete private incoming representation before
    atomically creating/replacing a closed mutable RAM object.
108. SYS_LIST order is unsigned-bytewise case-sensitive and BCAT is capped at 223 so no
    visible directory can exceed the 255-entry version-1 enumeration contract.
109. TIME1 includes a 16-bit revision changed by every successful date set; cron evaluates
    calendar jobs once per observed `(wall-minute,revision)` and never catches up.
110. PID1 reaps background/adopted zombies before prompts; PID1 exit is a permanent safe halt
    and refuses while any PID2..7 remains live.
111. BREAK is a cooperative tty-owner cancellation request sampled by IM2, not hardware
    preemption or a process-group signal.
112. C48 integer/float conversion and float comparison use the frozen SYS_INT_TO_FP,
    SYS_FP_TO_INT, and SYS_FP_CMP records and C truncation/comparison semantics.
113. zxpack-owned allocations run under NO_COMPACT so compression can never recursively
    trigger allocator compaction.
114. Shell environment names/values, quoting, expansion, precedence, PATH lookup, and
    parent-shell builtin restrictions are exact userland contracts; no implementation
    may substitute host-shell behavior.
115. Fixed pseudo-directory listing/stat and `/dev/tty`, `/dev/null`, `/dev/tape` open
    behavior are deterministic and ABI-visible.
116. C48 type sizes/alignment, array stride, argument-slot rules, even-SP call boundary,
    and integer/pointer arithmetic semantics are frozen by Section 25.
117. `ld` uses the deterministic multi-module TEXT/BSS/archive/symbol/relocation layout
    from Section 24.1; link order or padding is not implementation-defined.
118. PID 1 is the tty input owner before first scheduling; `$?` is shell status state and
    never appears in ENV1.
119. `/tmp/.cron.lock` is exactly ASCII PID digit `2`..`7` plus LF; any other payload is
    stale/invalid.
120. `vi` closes its source input handle after load and obeys the exact dirty-state,
    retarget, transactional-write, and quit semantics in Section 22.
121. `as`, `cc`, and `ld` emit through exclusive `/tmp` transaction objects and atomic
    SYS_RENAME; a failed build never progressively destroys a prior output object.
122. `as` consumes ASM, `cc` consumes C, and `ld` consumes OBJ metadata explicitly;
    default output suffix derivation is exact and never kernel-inferred.
123. The linker, not an OBJ1 runtime member, synthesizes `__heap_start`/`__heap_end`
    after deterministic final BSS layout.
124. `vi` invocation arity/unnamed-buffer rules and `cal`/`yes` argument behavior are
    exactly the bounded forms specified in Sections 22 and 20.11.
125. The official v1 `issue`, zero-length RAW `crontab`, and 40-entry/488-byte BCAT
    logical payloads are byte-frozen release assets.
126. External PATH lookup skips overlength/non-directory/wrong-type components and only
    direct slash resolution exposes E_TOOLONG/E_FORMAT for those direct targets.
127. MEX1/OBJ1 nonzero relocation tables require at least two bytes of patchable image/text.
128. Linker-defined `__heap_start`/`__heap_end`, the 512-byte default stack, and normal/
    `-nostart` heap defaults are ABI-visible deterministic linker contracts.
129. `udg save`/`udg load` operate only on RAM UDG objects; cassette motion is explicit
    through shell `save`/`load`.
130. Phase gates may use explicit contract-valid fixtures for not-yet-built later-phase
    binaries, but only Phase 12 may certify the byte-exact final release tape.
131. Version-1 production-ROM IY is exactly 0x5C3A.
132. IY equals 0x5C3A whenever MEX1 code executes.
133. The fast IM2 shadow-register path is allowed only when `altreg_busy==0`.
134. `altreg_busy` covers every interruptible foreground use of the alternate register
    bank, not merely ROM wrappers.
135. IM2 performs mandatory minimal direct BREAK sampling but never full ROM keyboard
    decoding.
136. Direct bitmap writers must turn the software cursor OFF before modifying a cell that
    may contain it.
137. The 512-byte kernel stack has a mandatory release high-water limit of 448 bytes and
    at least 64 bytes safety margin.
138. Syscall, MEX1, OBJ1, M48O, and ZXP1 address/length arithmetic is validated in widened
    precision before narrowing.
139. A 16-bit arithmetic wrap can never make an invalid range or object valid.

---

# 62. Architecture Review Checklist Before Coding Each Module

For every module, answer:

1. What exact memory region can it touch?
2. What persistent state does it own?
3. Can it run in interrupt context?
4. Can it yield?
5. Can it block?
6. What happens if memory allocation fails?
7. What registers does it preserve?
8. Does it call ROM?
9. If yes, is the ROM contract verified centrally?
10. Does it manipulate user pointers?
11. Are lengths bounded before access?
12. What process state transitions can it cause?
13. What test proves every transition?
14. What happens at cassette EOF/error/BREAK?
15. What happens at tick wrap?
16. What happens if another task closes a pipe?
17. Does the module alter ABI-visible behavior?
18. What is its binary-size budget?
19. What is the rollback/atomicity rule on failure?
20. What emulator/hardware evidence closes the task?
21. Is its hot code/data in FAST or CONTENDED memory, and why?
22. Does it depend on IY, I, alternate registers, or IM2 state?
23. If it uses shadow registers, what happens when a ROM wrapper is active?
24. Could a block transfer/search instruction replace a larger byte loop?
25. Is any undocumented opcode being introduced? If yes, why is this not in the
    portable baseline?
26. If it touches port 0xFE, does it use the central ULA output shadow?
27. If it is C48-generated code, does it follow REGCALL/frame-elision and IY
    preservation rules?
28. Does any user-facing name preserve exact case and use case-sensitive lookup?
29. If the module ships a command/tool/demo, is its canonical user-facing name
    lower-case?
30. If it is `vi`, does the change preserve documented modal and case-sensitive
    command semantics?
31. If it affects demos, can the matching `.c` source still compile/link/run
    natively on the 48K target?
32. Does it create or consume ARG1/ENV1, and are every byte/count bound validated?
33. Can an ANY allocation cross 0x7FFF/0x8000 safely without violating
    FAST_REQUIRED accounting?
34. If it runs in the background or from cron, can it ever steal tty input or
    trigger an interactive cassette-position prompt?
35. If it uses C48 `float`, does it obey the pointer argument/hidden-result ABI?
36. If it allocates C48 heap memory, is it entirely inside the linker-reserved
    BSS heap with no implicit kernel allocation?
37. If it emits sound, does it preserve `beep duration,pitch` semantics and the
    ULA/ROM critical-section contract?
38. If it invokes or implements a syscall, does it match the exact Section-10.1
    register/packed-record contract byte-for-byte?
39. Can this module observe a PACKED object, and if so are logical versus physical
    lengths and seek/read semantics explicit?
40. Could this module accidentally compress live process/stack/pipe/pinned memory?
41. Is every pack/unpack/representation swap atomic on allocation/codec failure?

A programming task is not complete until these questions have concrete answers where applicable.

---

# 63. Definition of Version-1 Success

ZX-UX version 1 succeeds when an unexpanded 48K ZX Spectrum can, without a
host computer participating in the runtime workflow:

    start the official cassette with ordinary LOAD "";
    auto-run the tiny BASIC bootstrap program;
    display the native 6912-byte ZX-UX SCREEN$ loading artwork;
    load the exact 8192-byte kernel CODE image at 0xE000;
    permanently hand control to zx_boot_entry at 0xE003;
    load and validate sh, font4x8, issue, crontab, and bincat in order;
    present tty64 sh without returning to BASIC;
    display the exact required issue heading and accept a valid login name;
    start in /home/<user> with PATH=/bin:.;
    provide lower-case, case-sensitive Unix-style command lookup;
    preserve exact case for user object/file names;
    resolve /bin, /etc, /dev, /home/<user>, /tmp and case-sensitive paths;
    manage volatile named objects;
    store eligible inactive objects as ZXP1 PACKED data while presenting exact logical bytes;
    save/restore RAW or PACKED objects with cassette;
    execute relocatable machine-code programs;
    keep multiple cooperative tasks alive;
    run true bounded-buffer pipelines;
    edit text with vi;
    assemble Z80 source;
    link executables;
    compile useful C48 source;
    use 64-column text with software cursor, bitmap graphics, color attributes,
    BASIC-compatible `beep`, basic sound, and UDGs;
    provide date, cron/crontab, and the web-directed man command;
    use the ROM-backed calculator safely from shell and C48;
    compile and execute C48 floating-point mathematics;
    discover and run the shipped demo suite;
    edit and rebuild shipped demo source locally;
    save a locally produced program to cassette;
    power-cycle/reset;
    boot again with ordinary LOAD "";
    restore the saved program;
    run it again.

The definitive demonstration begins from reset with the official cassette:

    LOAD ""

The user presses PLAY. The BASIC loader auto-runs, the ZX-UX loading screen
appears, the kernel loads and permanently takes control, then the five bootstrap
M48O resources load. `tty64` displays:

    © Supratim Sanyal, SANYALnet Labs
    https://supratim-sanyal.blogspot.com/
    48K. One Z80. No excuses.
    login: fred
    $ pwd
    /home/fred
    $ stty
    cols 64 rows 24 cursor underline
    $ man
    Manuals: https://supratim-sanyal.blogspot.com/
    Search for ZXUS
    $ date
    date: not set
    $ date -s "2026-09-06 12:00:00"
    $ demo hello
    hello
    $ vi hello.c
    $ cc hello.c
    $ ld hello.obj -o hello
    $ hello
    hello
    $ pack hello.c
    $ mem -c
    $ cc hello.c
    $ unpack hello.c
    $ save hello
    $ calc "sin(pi/4)*100"
    $ beep .25,0
    $ beep .25,0.5
    $ demo ship
    $ vi ship.c
    $ cc ship.c
    $ ld ship.obj -o ship
    $ ship
    $ pipe | grep 7 | wc
    $ multi
    $ fortune
    $ ps
    $ mem

An incorrect-case command/object lookup must also be shown to fail rather than
aliasing the lower-case name.

The demonstration ends with a real cassette round trip: save a locally produced
source/executable, reset or power-cycle, repeat the standard `LOAD ""` boot,
reload the saved objects, verify CRCs, and execute the program again.

That is the architecture target.

---

# 64. Reference Notes

The architecture relies on established 48K Spectrum platform facts and on
routine-level contracts from the Complete Spectrum ROM Disassembly.

Primary ROM research baseline:

    The Complete Spectrum ROM Disassembly
    Ian Logan and Frank O'Hara
    current maintained SkoolKit 48K ROM rendering

The Phase-0 team must preserve source/version information for the exact
disassembly used to freeze each ROM contract.

Verified baseline services include:

    RST 0x10 / 0x0010   print-a-character restart
    RST 0x28 / 0x0028   calculator restart
    0x028E              keyboard scan
    0x03B5              BEEPER
    0x03F8              BEEP command routine
    0x04C2              SA-BYTES
    0x0556              LD-BYTES
    0x22AA              PIXEL-ADD
    0x22CB              POINT
    0x22E5              PLOT-SUB
    0x24B7              line-drawing routine
    0x24BA              lower line-drawing entry
    0x2DA2              floating-point to BC
    0x2DE3              print floating-point
    0x335B              CALCULATE
    0x36AF              INT
    0x36C4              EXP
    0x3713              LN
    0x37AA              COS
    0x37B5              SIN
    0x37DA              TAN
    0x37E2              ATN
    0x3833              ASN
    0x3843              ACS
    0x384A              SQR
    0x3851              exponentiation

The disassembly documents `SA-BYTES` as taking block type in A, block length in
DE, and start address in IX, and shows that it disables maskable interrupts
during tape transmission. Such details belong in the wrapper contract and are
why raw ROM calls are centralized.

The Sinclair BASIC manual defines `BEEP duration,pitch`: duration is seconds and
pitch is semitones above middle C, with negative values below; it explicitly
permits fractional pitch values. ZX-UX deliberately preserves this public
parameter model. The ROM `BEEPER` subroutine disables maskable interrupts for
tone generation and re-enables them before return, so ZX-UX treats `beep` as a
synchronous ROM critical section and does not claim frame-clock precision
across a long tone.

The disassembly documents `CALCULATE` as operating on the ROM calculator's
floating-point stack through calculator operation literals. ZX-UX therefore
treats the calculator as a controlled shared service, not as a reentrant
per-process library.

Historical Spectrum C implementations are useful context for size constraints,
but they are not normative architecture authority. In particular, the HiSoft C
manual explicitly states that its C implementation did not implement
`float`/`double`; ZX-UX's decision to provide C48 floating point is based on
the ROM calculator capability itself, not on a claim that HiSoft C already did
so.

The Zilog Z80 CPU User Manual is normative for documented CPU behavior used by
this architecture, including IM2, alternate-register exchange, block transfer/
search instructions, relative branches, and interrupt-return behavior.

The original 48K Spectrum memory map/reference is normative for ULA contention:
0x4000-0x7FFF is treated as contended RAM and 0x8000-0xFFFF as uncontended RAM.
ZX-UX therefore places the kernel at 0xE000 and splits the user arena by
contention class.

The IM2 repeated-vector design deliberately uses a full 257-byte table so a
vector read beginning at any low byte 0x00-0xFF consumes two initialized table
bytes. The selected 0xFD fill points every vector to 0xFDFD, inside the fixed
kernel region.

The alternate register set is reserved from normal applications because it can
make interrupt entry extremely compact, but ROM code is not assumed to preserve
that set. Phase 0 therefore verifies wrapper-specific shadow-register behavior
and the kernel supplies a safe ISR fallback during sensitive ROM windows.

Existing Z80 operating systems demonstrate that useful Unix-like syscalls and
multitasking concepts are practical on the processor. ZX-UX nevertheless
uses its own 48K-specific cooperative/shared-address-space design rather than
assuming capabilities from systems with larger RAM, MMUs, banking, serial
hardware, or CTC/SIO peripherals.

Before implementation, exact ROM addresses and register contracts must be
frozen in `docs/rom-services.md`; this architecture's address list is a
baseline, not a substitute for that per-routine proof.

The 64-column terminal intentionally follows the classic Spectrum technique used
by Tasword Two/Taswide-class software: Tasword Two presented 64 characters per
line, and a 4-pixel-wide fixed renderer fits exactly 64 cells across the
Spectrum's 256-pixel bitmap. This does not alter the hardware attribute grid;
two 4-pixel characters still share each 8-pixel attribute cell.

---

# 65. First Implementation Deliverable

The first programming-cycle deliverable shall contain only:

    memory-map and contention-class constants
    canonical lower-case BASIC auto-loader (`src/boot/loader.bas`)
    canonical 6912-byte loading screen (`assets/loading.scr`)
    deterministic production bootstrap tape builder
    exact zx48ux / zx48uxscr / kernel plus sh / font4x8 / issue / crontab / bincat prefix validation
    cold-boot proof from ordinary LOAD ""
    fixed 0xE000 kernel-link layout
    fixed 0xE000 syscall and 0xE003 boot trampolines
    IM2 vector-table/trampoline scaffold
    IY=0x5C3A (ERR_NR) ROM-anchor proof scaffold
    alternate-register ROM/ISR classification scaffold
    complete ROM-service inventory scaffold
    A/B/C classification ledger
    ROM wrapper skeleton
    ROM error-recovery proof scaffold
    verified keyboard output/input path
    verified PLOT-SUB
    verified lower DRAW path
    verified 0x03B5 BEEPER / 0x03F8 BEEP-command public-wrapper path
    verified SA-BYTES / LD-BYTES cassette block save/load
    host reference ZXP1 encoder/decoder plus malformed-stream corpus
    verified FP-CALC/CALCULATE arithmetic path
    verified SIN and SQR operations
    verified floating/integer conversion path
    boot entry that switches from BASIC stack to SP=0xFD00 and never returns
    loading-screen preservation through kernel initialization
    panic output
    build-time fixed-subrange assertions for the 0xE000-0xFFFF kernel

It shall also answer, with evidence, whether the ROM BASIC expression scanner
can be safely isolated for the restricted `calc` command. If not, `calc` shall
use a ZX-UX-owned tokenizer while retaining the ROM calculator backend.

Do not implement the compiler, full shell parser, pipes, or scheduler before
the Phase-0 ROM and memory contracts are reproducibly proven.

The Phase-0 exit criterion is stronger than "the required wrappers work." It
must also demonstrate that the ROM has been systematically mined for reusable
services, that the contention-aware memory map is correct, and that the IM2/IY/
alternate-register contracts are safe enough to support the kernel before later
phases build on them.
