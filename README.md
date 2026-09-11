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

# ZX-UX: Unix-Like Operating System, C Compiler and Development Environment for the 48K Sinclair ZX Spectrum

<p align="center">
  <a href="https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit"><img src="https://raw.githubusercontent.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/main/doc/images/demos/forest.png" alt="ZX-UX C48 Fractal Forest demo for the 48K Sinclair ZX Spectrum" width="768"></a>
</p>
<p align="center"><em>Created using C48 on ZX-UX platform.</em></p>

**ZX-UX** is a Unix-like operating system and native software-development environment being built specifically for the original, unexpanded **48K Sinclair ZX Spectrum**. The target is the real **Z80A**, 48 KiB RAM, 16 KiB ROM, cassette storage, 256x192 Spectrum bitmap/attribute display, matrix keyboard, and the machine's actual timing and memory limits.

The project combines a compact cooperative kernel with a Unix-style shell and namespace, dense 64-column text, `vi`, Z80 assembler/linker tools, graphics and UDG services, cassette persistence, and the **C48 C compiler** planned for the native ZX-UX toolchain. It is a purpose-built retrocomputing system, not a port of Unix, POSIX, CP/M, or another existing operating system.

> **Project status:** active engineering work. The architecture and implementation plan are the normative design authorities, while `v1/` contains current implementation source, tests, tools, and certification evidence as development progresses. This repository is not yet a claim that the complete ZX-UX Version 1 operating environment has been released.

## Impatient? Try the ZX-UX C48 compiler environment now

If you want to experiment with the **ZX-UX C programming model** before the native Phase-11 Z80 C compiler is finished, use the separate companion project:

**[ZX-UX C48 SDK — Sinclair ZX Spectrum 48K C compiler and portable Unix-like development runtime](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit)**

The C48 SDK is a portable host-side development environment with a Python-based C48 compiler/runtime, 16-bit C48 machine model, 64 KiB logical address space, Spectrum-style five-byte floating point, 64x24 software text, UDG support, and an exact 6912-byte ZX Spectrum screen model. It is useful for writing, compiling, testing, and running C48 programs on modern Windows or Linux systems while ZX-UX itself continues toward its target-native Z80 implementation.

**Important:** the SDK is a preview and conformance environment, not the finished native ZX-UX compiler. Its host `C48B1` executable format is not ZX-UX `OBJ1` or `MEX1`, and the screenshots below are host-SDK renders rather than screenshots of a completed native ZX-UX operating system.

## C48 graphics preview of the ZX-UX architecture

These verified C48 SDK images provide a visual preview of software written against the ZX-UX/C48 programming model. They exercise the Spectrum-style display constraints that the main project architecture deliberately preserves.

| C48 architecture preview | C48 architecture preview | C48 architecture preview |
|---|---|---|
| [![ZX-UX C48 SDK Grand Finale showing Sinclair ZX Spectrum 48K architecture graphics on a 256x192 bitmap and attribute display](https://raw.githubusercontent.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/main/doc/images/demos/showcase.png)](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit) | [![ZX-UX C48 SDK Torus Reactor preview of the 48K ZX Spectrum graphics architecture and C48 development environment](https://raw.githubusercontent.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/main/doc/images/demos/torus.png)](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit) | [![ZX-UX C48 SDK Raycast Labyrinth preview of C programming for the Sinclair ZX Spectrum 48K architecture](https://raw.githubusercontent.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit/main/doc/images/demos/raymaze.png)](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit) |
| **Grand Finale — architecture preview:** C48 graphics rendered through the Spectrum-compatible 256x192 bitmap plus 768-byte attribute model required by the [ZX-UX architecture](docs/01-ZX-UX-ARCHITECTURE-REV11.md). Host SDK image; not native Z80 execution. | **Torus Reactor — architecture preview:** C48 code running inside the host SDK's deliberately small 16-bit machine model while targeting the display and graphics constraints defined for [ZX-UX on the 48K Spectrum](docs/01-ZX-UX-ARCHITECTURE-REV11.md). Host SDK image; not native Z80 execution. | **Raycast Labyrinth — architecture preview:** an example of the C48 programming environment described by the [ZX-UX architecture](docs/01-ZX-UX-ARCHITECTURE-REV11.md), intended to make software development practical before the [Phase-11 native C compiler](docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md) exists on the target. Host SDK image; not a finished ZX-UX OS screenshot. |

More compiler, graphics, game, conformance, and runtime examples are available in the **[ZX-UX C48 SDK repository](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit)**.

## What ZX-UX is building

ZX-UX is designed around the capabilities and restrictions of a stock 48K Spectrum rather than quietly assuming later Spectrum hardware or modern host resources. The Version-1 architecture calls for:

- an **8 KiB resident Z80 kernel** at the top of RAM;
- cooperative multitasking with multiple tasks, sleep/wake, pipes, and process state;
- a fixed Unix-style namespace including `/bin`, `/dev`, `/etc`, `/home`, and `/tmp`;
- a shell with pipelines, redirection, environment variables, foreground-job control, and compact core utilities;
- a **64-column x 24-row terminal** using a packed 4x8 font over the native Spectrum bitmap, plus a 32-column fallback/debug terminal;
- a reversible software cursor with block and underline forms;
- `vi` as the native text editor;
- Z80 assembler, object format, linker/loader, and executable support;
- the **C48 C language/compiler** as the native C development path;
- graphics, color attributes, UDGs, sound, and BASIC-compatible `beep` services;
- cassette-backed persistence using normal Spectrum loading conventions;
- a software wall clock, `date`, small `cron`/`crontab` support, and manual pages;
- compact RAM-object compression for inactive stored objects without pretending compressed memory is virtual memory;
- deterministic host and emulator tests with retained certification evidence.

The complete contract is in **[ZX-UX Architecture REV11](docs/01-ZX-UX-ARCHITECTURE-REV11.md)**. Ordered implementation work is defined by **[ZX-UX Implementation Steps REV02](docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md)**.

## Hardware architecture: original 48K Spectrum first

ZX-UX targets the original PAL/UK 48K machine as its Version-1 baseline:

| Component | ZX-UX target |
|---|---|
| CPU | Zilog Z80A, approximately 3.5 MHz |
| RAM | 48 KiB, unexpanded |
| ROM | 16 KiB original 48K Spectrum ROM, reused as a verified system library where safe |
| Display | 256x192 memory-mapped bitmap plus 32x24 attribute cells |
| Text | Software `tty64` 64x24 with 4x8 glyphs; `tty32` 32x24 fallback |
| Input | Spectrum keyboard matrix with ZX-UX-owned input handling |
| Storage | Standard cassette transport and ZX-UX sequential object persistence |
| Scheduling | Cooperative; no arbitrary user-code preemption |
| Memory model | Shared physical address space, no MMU, no virtual memory |
| Interrupts | Z80 IM 2 for bounded frame/timing/input bookkeeping |

This hardware-first approach is central to the project. ZX-UX treats the Spectrum's ROM routines, contended memory, bitmap organization, attribute limitations, keyboard matrix, ULA port behavior, and 50 Hz frame timing as architecture rather than inconvenient details to hide.

## C48: C programming for a tiny 1980s machine

C48 is the project's intentionally small C environment for the ZX-UX machine model. It is designed around 16-bit-era constraints instead of pretending the Spectrum is a modern flat-memory computer.

The portable C48 SDK currently lets developers experiment with the language and runtime model on a host computer. The main ZX-UX architecture separately requires a target-native compiler that will execute as Z80 machine code and integrate with ZX-UX object, executable, runtime, filesystem/namespace, terminal, graphics, and syscall conventions.

That separation is deliberate:

```text
C48 SDK today                     Native ZX-UX toolchain goal
------------------------------    ---------------------------------
host-side compiler/runtime        Z80 machine-code compiler on ZX-UX
portable C48B1 executable         ZX-UX OBJ1/M48O/MEX1 toolchain
host virtual machine              real 48K Spectrum execution
fast conformance experiments      native shell/editor/build workflow
same small-machine intent         authoritative target ABI/runtime
```

For people who want to see the programming experience now, start with the **[C48 SDK quick-start and demos](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit#clone-and-quick-start)**.

## Unix ideas, Spectrum-sized implementation

ZX-UX borrows useful Unix concepts while refusing features that do not fit the machine. The architecture includes processes/tasks, pipes, file-like handles, a shell, a fixed hierarchy, standard input/output concepts, an editor and development tools. It does not claim memory protection, demand paging, per-process address spaces, a random-access cassette filesystem, or transparent virtual memory.

The goal is therefore not "Unix emulation at any cost." It is a coherent **Unix-like Z80 operating and development environment** that remains honest about what a stock 48K Spectrum can do.

## Repository guide

| Path | Purpose |
|---|---|
| [`docs/01-ZX-UX-ARCHITECTURE-REV11.md`](docs/01-ZX-UX-ARCHITECTURE-REV11.md) | Normative ZX-UX operating-system, terminal, ABI, storage, graphics, C48, and toolchain architecture |
| [`docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md`](docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md) | Ordered phase-by-phase implementation and test plan |
| [`docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md`](docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md) | Mandatory development, zero-defect scan, review, CI, and evidence workflow |
| [`docs/04-ZX-UX-CHANGE-REQUEST-DEFERRED-WRAP-REV01.md`](docs/04-ZX-UX-CHANGE-REQUEST-DEFERRED-WRAP-REV01.md) | Proposed DEC-style deferred terminal wrap and bottom-right cursor behavior |
| [`v1/`](v1/) | Current Version-1 implementation source, includes, tests, tools, assets, documentation, and certification artifacts |
| [`tools/`](tools/) | Repository policy, environment, CI, quality, and resource-generation tooling |
| [`AGENTS.md`](AGENTS.md) | Mandatory repository-development rules |

## Development status and engineering discipline

ZX-UX is under active implementation. Source exists under `v1/`, but individual phase work must not be confused with a finished Version-1 release. Each feature is intended to close against its architecture contract, implementation step, deterministic tests, and retained evidence before it is treated as complete.

Every proposed check-in follows the repository's mandatory quality sequence:

1. scan the exact proposed disk-copy bytes line by line;
2. fix any defect and restart the scan count from zero;
3. achieve three successive complete scans with zero new defects;
4. pass the license/header gate;
5. pass the prohibited-name project-policy gate;
6. perform the dynamic adversarial review, reporting only `BLOCKER` and `MAJOR` findings;
7. check in the exact reviewed bytes directly to `main`;
8. run the GitHub Actions quality workflow on the project's `ubuntu-slim` Linux runner.

See **[ZX-UX Development Workflow](docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md)** for the complete procedure.

## Why this project exists

The original ZX Spectrum is small enough that every design choice matters. A useful Unix-like environment on 48 KiB has to earn its bytes: kernel state, process stacks, fonts, editors, compilers, pipes, object storage, screen memory, ROM compatibility, and user programs all compete for the same address space.

That constraint is the point. ZX-UX explores how far a disciplined Unix-inspired development system can be taken on a mass-market 1982 home computer while staying recognizable to Spectrum programmers and honest about the hardware.

For retrocomputing developers, the project brings together several areas that are usually studied separately: **Z80 assembly**, **Sinclair ZX Spectrum programming**, **operating-system design**, **C compiler construction**, **Unix shell semantics**, **cassette storage**, **memory-constrained software engineering**, **8-bit graphics**, and deterministic emulator testing.

## Project links

- **C48 SDK / try the C compiler environment now:** [zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit](https://github.com/tuklusan/zx-ux-c48-sdk-sinclair-zx-spectrum-48k-unix-c-compiler-software-development-kit)
- **Project architecture:** [ZX-UX Architecture REV11](docs/01-ZX-UX-ARCHITECTURE-REV11.md)
- **Implementation plan:** [ZX-UX Implementation Steps REV02](docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV02.md)
- **Development process:** [ZX-UX Development Workflow](docs/03-ZX-UX-DEVELOPMENT-WORKFLOW.md)
- **SANYALnet Labs / Supratim Sanyal:** https://supratim-sanyal.blogspot.com/

## License

ZX-UX is distributed under the **SANYALnet Labs Non-Commercial License** in the root [`LICENSE`](LICENSE) file. Non-Commercial use is permitted. Commercial Use and use for AI/ML model training are prohibited unless separately authorized. Attribution is required as stated in the license.

Required attribution: **"Based on original work by Supratim Sanyal of SANYALnet Labs."**
