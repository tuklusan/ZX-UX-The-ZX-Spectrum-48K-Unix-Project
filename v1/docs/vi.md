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

# ZX-UX Version-1 vi

ZX-UX `vi` is a compact modal editor for RAM objects. It is recognizably vi-like,
but it is not a claim of full historical vi or POSIX vi compatibility.

## Invocation and terminal ownership

Invocation is exactly `vi` or `vi path`. With no path, the editor starts with an
unnamed empty TXT buffer. With one path, the object must already exist and have type
TXT, C, ASM, or CFG. More than one path is invalid.

On entry, `vi` saves the current TTY mode and cursor shape, requests tty64 mode, and
uses a block cursor in normal mode. Insert and command-line input use an underline
cursor. Normal exit and error unwind restore the exact saved TTY mode and cursor state.

The edit viewport is tty rows 0 through 22. Row 23 is reserved for status and
command-line input. Source lines are LF-delimited logical lines and are never
soft-wrapped.

## Modes and escape input

The three editor modes are normal, insert, and command-line. Insert mode displays the
exact status text `-- INSERT --` on row 23.

The canonical editor escape byte is `0x1B`. On the ZX Spectrum keyboard it is produced
by the physical `CAPS SHIFT + 1` `EDIT` chord. BREAK is separate: BREAK is not editor
escape and retains the system cooperative-cancellation meaning.

In insert mode, `0x1B` returns to normal mode, removes the insert indicator, restores
the block cursor, and inserts no byte. During unfinished `:` input or unfinished
`/text` search input, `0x1B` cancels that input without executing it and returns to
normal mode. In normal mode, `0x1B` cancels any incomplete multi-key normal command
and otherwise leaves the buffer unchanged.

## Normal-mode movement

Commands are case-sensitive.

- `h` moves left, `j` down, `k` up, and `l` right.
- `0` moves to the first column and `$` to the end of the logical line.
- `w` moves to the next word, `b` to the previous word, and `e` to the end of a word.
- `gg` moves to the first line. A single lower-case `g` only begins that multi-key command.
- `G` moves to the last line.

Movement operates on logical file positions, not merely on the visible horizontal slice.

## Editing, yank, put, and undo

Required editing commands are case-sensitive where the command letters differ:

- `i` inserts before the cursor and `a` appends after it.
- `o` opens a line below; `O` opens a line above.
- `x` deletes one character.
- `dd` deletes the current logical line.
- `D` deletes from the cursor through the end of the current logical line.
- `yy` yanks the current logical line.
- `p` puts after the cursor or below for a linewise yank; `P` puts before or above.
- `r` replaces one character.
- `J` joins the current line with the next line.
- `u` performs one-level undo.

The buffer is a gap buffer with a compact line-offset index. The editor does not keep a
complete second copy of the file for undo. The one-level undo record stores only the
bounded data needed to reverse the most recent supported edit.

Delete operations update the single yank buffer. Put operations are preflighted before
mutation so an allocation/index failure does not leave a partial put.

## Literal search

`/text` performs a forward literal, case-sensitive search. `n` repeats the last
search in the same direction and `N` repeats it in the opposite direction.

Search entry uses command-line state. Escaping an unfinished search with `0x1B`
preserves the previous committed search pattern, direction, cursor position, and buffer.

A full regular-expression search engine is not part of version 1.

## Command-line commands

The required `:` commands are:

- `:w`
- `:w path`
- `:q`
- `:q!`
- `:wq`
- `:e path`
- `:r path`
- `:set`
- `:set number`
- `:set nonumber`

Paths are exact and case-sensitive. Relative paths are resolved relative to the editor
process working directory.

`:q` refuses to exit while the buffer is dirty. `:q!` discards unsaved changes.
`:e path` refuses while dirty and, when clean, changes the buffer/current target only
after the new object loads successfully. `:r path` inserts that object's bytes, marks
the buffer dirty, and never retargets the editor.

`:w` writes the current target. An unnamed buffer without a current target makes
`:w` and `:wq` fail with `E_NOENT` and the visible message `vi: no file name`;
the buffer and dirty state remain unchanged. `:w path` changes the current target only
after a successful transactional write. A successful write clears dirty state. `:wq`
exits only after a successful write; a failed save leaves the editor and dirty buffer alive.

## Transactional writes and object types

A write creates an exclusive temporary object named `/tmp/.vi<pid>.<n>`, trying
`n=0` through `9` with `O_WRITE|O_CREATE|O_EXCL`. Only `E_EXIST` advances to the
next suffix. The complete replacement is written and closed before atomic
`SYS_RENAME`. Only a temporary object successfully created by this editor instance may
be removed by its rollback path. Failure before rename leaves the previous destination
byte-identical.

Existing objects preserve their object type. For a new target, exact lower-case `.c`
requests C, exact lower-case `.asm` requests ASM, and every other editable new name
requests TXT. Type inference is done by `vi`, not by the kernel.

After returning to the shell, ordinary `save` provides cassette persistence.

## Viewport, TABs, and line numbers

Without line numbers, all 64 tty64 columns are available to file text. `:set number`
enables a fixed five-column line-number gutter, leaving 59 text columns.
`:set nonumber` removes the gutter and restores 64 text columns. Bare `:set` reports
the current supported option state.

A horizontal display offset follows the cursor on wide logical lines. No editing or
search operation is limited to the visible slice. TAB remains stored as byte `0x09`
and displays to the next multiple-of-8 logical column. Every editor render path is
bounded to tty64 columns 0 through 63; row 23 is never an edit-render destination.

## Memory-pressure behavior

The version-1 editor is deliberately bounded. Loading, line indexing, yank/undo,
growth, put, and write preparation can fail with the relevant memory/capacity error.
Such failures are reported rather than silently truncating data. Operations that require
growth or transactional replacement are preflighted or staged so failure does not
publish a partial edit or replace a previously valid destination.

## Deferred features

`:udg` is deferred from the required version-1 vi subset. UDG resources remain
available through the graphics APIs and the `udg` utility.

Version 1 also defers all of these feature families:

- syntax highlighting
- multiple open buffers
- split windows
- visual mode
- named register collections
- macros/recording
- full regular-expression substitution
- persistent undo/swap files

A line-oriented bootstrap editor may exist temporarily during development, but it is not
the version-1 shipped editor and must not replace the `vi` acceptance gate.
