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
# C48 games

The SDK ships a clean-room C48 game corpus under `dev/src/games/`. Matching
canonical C48B1 host executables are under `dev/bin/games/`.

The corpus is deliberately useful as both software and compiler/runtime test
material. It exercises interactive input, screen text, arrays, pointers,
control flow, deterministic pseudo-random play, game-state mutation, and
long-running VM execution.

## Shipped programs

| Program | Source | Scope and controls |
| --- | --- | --- |
| Adventure | `advent.c` | Small room adventure. `n/e/s/w`, `t` takes an item, `q` quits. |
| Arithmetic | `arith.c` | Generated `+ - * /` drills. Enter an answer and Return; `q` quits. |
| Backgammon | `bgammon.c` | Compact backgammon variant with bars, hits, doubles, and bearing off. Points are `a`-`x`, `z` is the bar, `0` quits. Dice are applied in rolled order; no doubling cube or tournament forced-dice-order rule is claimed. |
| Chess | `chess.c` | Two-player legal-move chess. Enter moves such as `e2e4`; `q` quits. Includes check, checkmate, stalemate, castling, en passant, and promotion. Automatic repetition, fifty-move, and insufficient-material draws are not claimed. |
| Cribbage | `cribbage.c` | Explicit 61-point show variant. Choose two discards with `1`-`6`; `q` quits. Fifteens, pairs, runs, flushes, nobs, and crib scoring are implemented. Pegging is intentionally outside this variant. |
| Go Fish | `fish.c` | Full 13-book human-vs-computer match. Ask with `1`-`9`, `t`, `j`, `q`, `k`; `x` quits. |
| Fortune | `fortune.c` | Displays deterministic dry fortunes. Any key continues; `q` quits. |
| Hangman | `hangman.c` | Letter guessing. Type letters; `q` quits. |
| Maze | `maze.c` | Escape maze. `w/a/s/d` moves; `q` quits. |
| Quiz | `quiz.c` | Ten Spectrum/C48 questions. `a/b/c` answers; `q` quits. |
| Rogue | `rogue.c` | Small dungeon with monsters, three treasures, hit points, and an exit. `w/a/s/d` moves; `q` quits. |
| Snake | `snake.c` | Growing snake with wall/self collision and food. `w/a/s/d` turns; `q` quits. |
| Trek | `trek.c` | Compact 4x4 space mission with warp, phasers, torpedoes, shields, and energy. `w` warps, `p` fires phasers, `t` fires a torpedo, `s` scans, `q` quits. |
| Wumpus | `wump.c` | Cave hunt with pit, bat, arrows, and Wumpus. `a/b/c` selects a tunnel, `s` shoots, `q` quits. |

The shortened basenames `advent`, `bgammon`, and `arith` are intentional. All
shipped C48 object names, including extensions where relevant, stay within the
ZX-UX portable 1..10-byte object-name rule.

## Verification

Run the normal game gate with:

```text
python -B compiler/verify_games.py
```

It verifies the frozen source/binary hashes, recompiles every source, requires
byte-for-byte deterministic C48B1 output, decodes every shipped executable
through the canonical schema validator, and performs meaningful scripted play
in all 14 programs.

Run the longer simulated-player suite with:

```text
python -B compiler/verify_games.py --extended
```

Extended mode additionally exercises Chess checkmate, castling, and en
passant; plays Go Fish to all 13 books; answers 500 generated Arithmetic
problems correctly; and drives Fortune through 5,000 continuing interactions.
These runs count actual `getchar()` interactions and VM execution steps. They
do not substitute wall-clock sleeping for gameplay.

`compiler/verify_release.py` runs the quick game gate as part of the normal SDK
release verification. Extended mode is kept separate so CI remains bounded
while deeper endurance certification remains reproducible on demand.
