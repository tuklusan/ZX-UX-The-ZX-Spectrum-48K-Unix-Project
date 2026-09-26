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
# ZX-UX C48 SDK: Sinclair ZX Spectrum 48K C Compiler and Portable Unix-Like Development Runtime

[![C48 SDK verification](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml/badge.svg)](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/actions/workflows/verify.yml)

**ZX-UX C48 SDK** is a portable, Python-based **C compiler and development SDK for the original Sinclair ZX Spectrum 48K programming model**. The repository is currently a **pre-1.0 development snapshot**; the final 1.0 release has not yet been declared. It provides a command-line C48 compiler, deterministic host executable format, 16-bit C48 virtual machine, authentic 256x192 ZX Spectrum bitmap/attribute display model, Tasword-style 64-column 4x8 text, graphics and UDG support, and Windows/Linux launchers.

The SDK exists to make C48 programs practical to write, compile, test, and run on a modern **Windows or Linux command line** while the native Z80 implementation of the wider **ZX-UX Unix-like operating environment for the 48K ZX Spectrum** continues to evolve.

> **Overarching ZX-UX project:** https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project
> **Supratim Sanyal / SANYALnet Labs blog:** https://supratim-sanyal.blogspot.com/

This repository is especially aimed at retrocomputing developers who want to experiment with **ZX Spectrum C programming**, **Z80-era Unix-style software**, compact 1980s games, graphics programs, utilities, and C code constrained by a deliberately tiny 48K-machine data model.

## What this repository is

This repository contains the **portable host-side C48 SDK**. It is designed for rapid development and forensic testing of C48 source on contemporary computers.

The SDK includes:

- `c48` / `c48.bat` - C48 command-line compiler front end;
- `c48run` / `c48run.bat` - portable C48 host runtime and virtual machine;
- a dedicated C48 lexer, preprocessor, recursive-descent parser, type system, semantic checker, and diagnostics layer;
- a deterministic `C48B1` host executable representation;
- a logical 64 KiB C48 address space with 16-bit pointers;
- C48 integer, pointer, array, function, storage, and evaluation semantics derived from the frozen language specification;
- Spectrum five-byte `float` storage and deterministic core arithmetic support;
- an exact 6912-byte ZX Spectrum screen model: 6144 bitmap bytes plus 768 attribute bytes;
- 256x192 ZX Spectrum graphics with native-style INK, PAPER, BRIGHT, FLASH, OVER, and INVERSE behavior;
- 64x24 text using a 4x8 packed `F4X8` font resource;
- UDG support for classic ZX Spectrum game and application graphics;
- headless execution for deterministic tests and CI-style verification;
- a Tk-based graphical display for interactive Windows/Linux execution;
- a conformance/regression suite and deterministic demonstration programs.

This is **not** a claim that the native ZX-UX C compiler is already complete. The future target-native ZX-UX `cc` will execute as Z80 machine code and emit ZX-UX object modules. This SDK deliberately keeps its portable host executable format separate so the language and runtime semantics can be exercised now without pretending Python host execution is native Z80 execution.

## Relationship to ZX-UX

**ZX-UX** is a Unix-like operating and development environment designed specifically for the original, unexpanded **48K Sinclair ZX Spectrum**: one Z80A processor, 48 KiB RAM, Spectrum ROM services, cassette persistence, cooperative tasks, a compact Unix-style namespace, 64-column software text, an editor, assembler/linker, C48 compiler, graphics, UDGs, and small demonstration programs.

The main project lives here:

https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project

The architectural and implementation authorities copied into this SDK under `doc/` freeze the C48 host-development contract used by this release:

- `doc/C48 Language Specification Rev 0.11.docx`
- `doc/ZX-UX C48 Compiler User Manual Rev 0.11.docx`

The host SDK is intentionally useful before native Phase-11 `cc` is finished. Programs written against the frozen C48 language subset and conservative host API can therefore be developed early, while target-native compiler, linker, ROM bridge, and ABI work remain separately verifiable.

## Why a Python C48 compiler/runtime?

Python keeps the development environment simple and portable while allowing the C48 implementation to model the Spectrum rather than inherit host-C assumptions.

A normal modern C compiler would naturally prefer 32/64-bit integers and pointers, IEEE floating point, operating-system memory, and platform-specific evaluation/code-generation behavior. C48 instead models a tiny machine deliberately:

- `char` / `unsigned char`: 1 byte;
- `short` / `unsigned short`: 2 bytes;
- `int` / `unsigned int`: 2 bytes;
- pointer: 2 bytes;
- `float`: 5-byte Spectrum-style representation;
- plain `char`: unsigned;
- logical pointer space: 16-bit;
- explicit wrap, shift, division, conversion, and evaluation semantics.

That makes the Python VM a useful portability and correctness laboratory for code intended for the ZX-UX environment.

## Requirements

- **Python 3.10 or newer**;
- Windows: Command Prompt or PowerShell with `python` on `PATH`;
- Linux: `python3` on `PATH`;
- Tkinter only when using the graphical display window.

No third-party Python packages are required by the compiler or headless runtime.

## Continuous verification

Every push and pull request is verified on both **Windows and Linux** with the minimum
supported Python 3.10 and a current Python 3.13 runtime. GitHub Actions runs the same
`compiler/verify_release.py` gate used locally, plus platform-native launcher smoke tests.
This keeps the public pre-1.0 development branch continuously checked against the frozen
C48 conformance corpus, deterministic demos, manifest, font assets, and license-header policy.

## Clone and quick start

```text
git clone https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit.git
cd zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit
```

### Windows Command Prompt

```bat
c48 --version
c48 --about
c48 dev\src\hello.c
c48run --headless dev\bin\hello.c48b --dump-screen dev\bin\hello.scr
c48run dev\bin\hello.c48b
```

### Linux

```sh
./c48 --version
./c48 --about
./c48 dev/src/hello.c
./c48run --headless dev/bin/hello.c48b --dump-screen dev/bin/hello.scr
./c48run dev/bin/hello.c48b
```

Sources under `dev/src/` compile by default to the corresponding relative path under `dev/bin/`. Sources elsewhere compile beside the source with the `.c48b` suffix unless `-o` is supplied.

## ZX Spectrum 4x8 fonts and `--font`

The runtime ships with two independent `F4X8` font asset names under `compiler/assets/`:

```text
compiler/assets/font4x8-tasword.bin   # default
compiler/assets/font4x8-zxux.bin      # alternate slot
```

`font4x8-tasword.bin` is the default runtime font. It is the packed 392-byte `F4X8` resource mechanically derived from the supplied Tasword Two 4x8 character generator.

Select another valid `F4X8` font at runtime with `--font PATH`:

```bat
c48run --font compiler\assets\font4x8-zxux.bin dev\bin\hello.c48b
```

```sh
./c48run --font compiler/assets/font4x8-zxux.bin dev/bin/hello.c48b
```

Any replacement font must satisfy the SDK's frozen `F4X8` format: 392 bytes total, `F4X8` magic, version 1, first character `0x20`, 96 glyphs, and four packed bytes per 4x8 glyph.

**Current repository note:** the two bundled font assets presently have identical bytes and the same SHA-256. They are intentionally retained under separate names so the ZX-UX font can diverge later without changing the CLI or runtime architecture.

The complete Tasword Two program archive is **not redistributed** by this repository. The retained raw character-generator extraction and its SHA-256/provenance record are sufficient to verify the mechanical packing of the default runtime font.

## C48 compiler pipeline

The portable compiler follows a small auditable pipeline:

```text
C48 source
   |
   v
preprocessor -> lexer -> recursive-descent parser -> semantic/type checks
   |
   v
deterministic C48B1 host executable
   |
   v
c48run -> 64K C48 VM -> ZX Spectrum screen/runtime services
```

The compiler does not transpile to ordinary host C. That avoids accidentally replacing C48 behavior with GCC, Clang, MSVC, CPython integer, or native pointer semantics.

## C48B1 host executable format

`C48B1` is a deterministic SDK-only host representation. It consists of canonical ASCII JSON protected by a SHA-256 integrity field and a strict schema validator.

It is deliberately **not**:

- ZX-UX `OBJ1`;
- ZX-UX `MEX1`;
- Z80 machine code;
- a replacement for the future native C48 backend.

Deterministic serialization allows the test suite to prove that the same C48 source produces byte-identical host binaries across clean rebuilds.

## ZX Spectrum screen and graphics model

The runtime keeps the real ZX Spectrum display organization rather than a generic terminal framebuffer:

```text
6144 bytes  bitmap
 768 bytes  attributes
--------------------
6912 bytes  total ZX screen state
```

The graphical API models Spectrum coordinates and attribute constraints. The 4x8 text renderer provides a dense 64-column-by-24-row software console while still writing into the native Spectrum bitmap organization.

Headless mode can dump the exact 6912-byte screen for deterministic tests:

```sh
./c48run --headless --dump-screen output.scr dev/bin/graphics.c48b
```

The Tk frontend is only a visualizer over that underlying ZX-compatible screen state; it is not the source of truth.

For Spectrum-style interactive control, **Shift+Space acts as BREAK**. While the program runs, the Tk footer shows `Shift+Space = BREAK`. After a program has returned and `c48run` is simply holding its final frame, the footer changes to `Program ended - Shift+Space to close`; pressing the chord closes the window while preserving the completed program status. If the VM is still running, Shift+Space aborts the host GUI session with status 130. The footer is host-window chrome and is never written into the emulated 6912-byte Spectrum screen.

## Host game API

`dev/src/c48host.h` is the **Host Game API profile** used for practical development before the final native `<c48.h>` prototype surface is frozen by ZX-UX Phase 11.

It exposes useful host-side calls for text, graphics, UDGs, memory/string operations, and related experiments. The file is intentionally labeled as a host profile and must not be mistaken for the final native ZX-UX ABI.

See:

- `doc/HOST-DIVERGENCES.md`
- `doc/CONFORMANCE.md`

## Heap compatibility

The runtime defaults to the normal native-C48 `crt0` heap ceiling of **1024 bytes**.

For host development:

```sh
./c48run --heap 2048 dev/bin/hello.c48b
```

`--heap` accepts even values from `0` through `8192`. The host allocator enforces the selected byte ceiling but does not claim byte-identical native allocator metadata or native process-stack placement.

For hostile-input testing and CI, `c48run` also provides a deterministic VM execution budget:

```sh
./c48run --max-steps 10000 dev/bin/program.c48b
```

`--max-steps 0` (the default) leaves normal interactive execution unlimited. A positive value terminates execution with a controlled runtime error when the VM reaches the requested evaluation/statement-step budget. The host VM separately caps C48 function-call depth so recursive programs cannot fall through to Python's recursion limit.

## Spectrum five-byte Float5 status

The SDK implements five-byte storage, parsing, integer conversion, comparison, and deterministic core arithmetic without allowing IEEE host values to become persistent C48 stored state.

Full byte-for-byte differential certification of every ROM transcendental operation is **not** claimed. Strict execution therefore keeps ROM-dependent transcendental behavior bounded. An explicitly non-certified host approximation can be enabled for experiments with:

```sh
./c48run --allow-approx-rom-math dev/bin/program.c48b
```

See `doc/FLOAT5-ORACLE.md` for the exact certification boundary.

## Included C48 examples

The `dev/src/` directory contains small deterministic programs intended both as examples and as regression fixtures:

- `hello.c` - 64-column C48 text output;
- `colors.c` - Spectrum color/attribute behavior;
- `graphics.c` - line, point, and circle graphics;
- `udg.c` - user-defined graphics;
- `maze.c` - compact retro maze-style graphics workload;
- `argv.c` - C48 `argc` / `argv` behavior.

The matching frozen `C48B1` files are under `dev/bin/`.

All shipped C48 `.c` and `.h` files under `dev/src/` obey a **64-character physical-line ceiling**, matching the ZX-UX tty64 presentation model rather than modern 80-column source formatting. The release verifier enforces this mechanically.

## Adversarial security fixtures

The pre-1.0 tree includes C48 programs written specifically to attack the host compiler/runtime safety envelope. Their source is under `dev/src/`, and runnable C48B1 forms are under `dev/bin/` where compilation is expected to succeed.

- `secguard.c` - successful dashboard for recoverable heap, screen-coordinate, UDG, and compiler-forgery protections;
- `secoob.c` - one-past pointer write;
- `secuaf.c` - use-after-free dereference;
- `secfree.c` - interior-pointer `free`;
- `secdbl.c` - double free;
- `secforge.c` - raw pointer-byte forgery without provenance;
- `secloop.c` - infinite loop stopped by `--max-steps`;
- `secrecur.c` - unbounded C48 recursion stopped by the VM call-depth guard;
- `seckern.c` - compile-negative attempt to manufacture a pointer to reserved address `0x5B00`; C48 must reject the arbitrary integer-to-pointer cast, so this fixture intentionally has no C48B1 binary.

The runnable fixtures place explicit `ATTEMPT:` and `MITIGATION:` text on the emulated 64-column Spectrum screen before the security boundary is exercised. Fatal tests are expected to terminate with controlled C48 runtime errors rather than continue after an invalid operation.

For example:

```bat
c48 dev\src\secguard.c
c48run dev\bin\secguard.c48b

c48run --max-steps 300 dev\bin\secloop.c48b
```

The hostile-input regression suite additionally attacks recursive parser structures, macro-expansion bombs, oversized source/C48B1 inputs, malformed-but-correctly-checksummed C48B1 schemas, stale-pointer address reuse, and raw pointer representation forgery. See `doc/ZX-UX C48 SDK Adversarial Security Review.docx` for the threat model and findings.

## Verification and zero-gap release discipline

Run the full automated test corpus:

```bat
python -B compiler\run_tests.py
```

```sh
python3 -B compiler/run_tests.py
```

Run the complete release verifier:

```bat
python -B compiler\verify_release.py
```

```sh
python3 -B compiler/verify_release.py
```

The release verifier checks, among other things:

- Python source parseability against the supported Python baseline;
- the repository-wide license-header policy;
- exact font resource structure and hashes;
- the 64-column physical-line contract for shipped C48 source;
- launcher behavior;
- version/about attribution output;
- manifest integrity;
- the full compiler/runtime conformance, regression, and adversarial-security suite;
- deterministic reconstruction of every security-fixture binary;
- deterministic reconstruction of every frozen demo binary;
- exact 6912-byte Spectrum screen hashes for the demos;
- absence of transient cache/test debris.

The standalone header gate can also be run directly:

```sh
python3 -B compiler/check_license_headers.py
```

Artifacts that would be corrupted by an in-band text header are explicitly classified as exemptions by that gate: JSON, binary font resources, `C48B1`, DOCX, ZIP/TAP containers, the machine-readable version/hash files, and the root `LICENSE` itself.

## Repository layout

```text
zx-ux-c48-sdk/
|-- c48 / c48.bat
|-- c48run / c48run.bat
|-- compiler/
|   |-- c48.py
|   |-- c48run.py
|   |-- c48/                 compiler + VM implementation
|   |-- assets/              selectable F4X8 fonts
|   `-- tests/               conformance/regression corpus
|-- dev/
|   |-- src/                 editable C48 programs
|   `-- bin/                 deterministic C48B1 binaries
|-- doc/                     C48 specification, manual, verification notes
|-- LICENSE
|-- MANIFEST.sha256
`-- VERSION
```

## Project status and portability boundary

This SDK is intended to be conservative about what it claims.

Host execution proves the C48 language/VM behavior covered by the test and release-verification envelope. It does not by itself prove Z80 code-generation correctness, native `C48_REGCALL`, ZX-UX linker behavior, ROM-call register contracts, cassette persistence, native multiprocessing, or final `<c48.h>` prototypes. Those belong to the overarching ZX-UX target implementation and its own phase-by-phase verification process.

That separation is intentional: **portable C48 development now, native ZX Spectrum ZX-UX implementation without invented equivalence later.**

## Retrocomputing goals

The practical goal is simple: make it pleasant to write small programs that feel at home on a 1982 Sinclair machine while retaining enough Unix-like structure to build interesting software.

Good candidates include:

- classic terminal and maze games;
- compact adventure/game engines;
- Conway-style cellular automata;
- text utilities and filters;
- tiny editors and data tools;
- 256x192 graphics demonstrations;
- UDG sprite experiments;
- ports or reinterpretations of early Unix-era recreational programs within the C48 subset.

The constraints are part of the fun: 16-bit pointers, tiny heap, 4x8 text, attribute color, 48K-era screen memory, and a deliberately modest C language.

## Documentation

Start with:

- `doc/C48 Language Specification Rev 0.11.docx` - normative language baseline;
- `doc/ZX-UX C48 Compiler User Manual Rev 0.11.docx` - user-facing compiler manual;
- `doc/CONFORMANCE.md` - host conformance evidence and scope;
- `doc/HOST-DIVERGENCES.md` - explicit host/native differences;
- `doc/FLOAT5-ORACLE.md` - five-byte floating-point verification boundary;
- `doc/DEMO-HASHES.md` - deterministic demo hashes;
- `doc/RELEASE-NOTES.md` - release notes;
- `doc/ZX-UX C48 SDK Adversarial Security Review.docx` - hostile-input and memory-boundary security assessment.

## License

Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.

This repository is distributed under the **SANYALnet Labs Non-Commercial License** in [`LICENSE`](LICENSE). Non-commercial personal, educational, and hobbyist use is permitted subject to the license terms; commercial use and use for AI/ML model training are prohibited unless separately authorized.

Required attribution:

> Based on original work by Supratim Sanyal of SANYALnet Labs.

## Author, ZX-UX project, and development notes

**Supratim Sanyal / SANYALnet Labs**
Blog and software-development notes: https://supratim-sanyal.blogspot.com/

Main ZX-UX repository:
https://github.com/tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project

C48 portable SDK repository:
https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit

### Search/project taxonomy

Sinclair ZX Spectrum 48K, ZX Spectrum C compiler, ZX Spectrum C programming, Z80 C compiler, Z80 development SDK, retrocomputing, 1982 home computer programming, ZX-UX, Unix-like ZX Spectrum operating system, C48 language, Python C compiler, Windows ZX Spectrum development, Linux ZX Spectrum development, 256x192 Spectrum graphics, UDG graphics, Tasword 64-column font, 4x8 Spectrum font, five-byte Spectrum floating point, classic Unix games, retro C development.
