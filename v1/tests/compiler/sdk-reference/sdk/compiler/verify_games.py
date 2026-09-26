#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
"""Verify the shipped C48 game corpus and simulated-player sessions."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SDK = ROOT.parent
SRC = SDK / "dev" / "src" / "games"
BIN = SDK / "dev" / "bin" / "games"
EXPECT = json.loads(
    (ROOT / "release_expectations.json").read_text(encoding="ascii")
)

sys.path.insert(0, str(ROOT))
from c48.compiler import compile_file
from c48.format import encode, read
from c48.screen import Font4x8, ZXScreen, bitmap_offset
from c48.vm import C48VM

FONT = Font4x8.load(ROOT / "assets" / "font4x8-tasword.bin")
GLYPHS = {
    FONT.glyph(code): chr(code)
    for code in range(0x20, 0x80)
}


class VerifyError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerifyError(message)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def screen_text(screen: ZXScreen) -> str:
    output = []
    for row in range(24):
        line = []
        for col in range(64):
            rows = []
            x0 = col * 4
            y0 = row * 8
            high = (col & 1) == 0
            for ry in range(8):
                byte = screen.mem[bitmap_offset(x0, y0 + ry)]
                if high:
                    rows.append((byte >> 4) & 15)
                else:
                    rows.append(byte & 15)
            line.append(GLYPHS.get(tuple(rows), "?"))
        output.append("".join(line))
    return "\n".join(output)


def global_int(vm: C48VM, name: str, index: int | None = None) -> int:
    lv = vm.global_lvalues[name]
    if index is None:
        return vm.mem.load_integer(lv.pointer.address, lv.ctype)
    base = lv.ctype.base
    if base is None or not base.is_integer:
        fail(f"{name}: requested non-integer array element")
    address = lv.pointer.address + index * base.size
    return vm.mem.load_integer(address, base)


class ScriptKeys:
    def __init__(self, text: str):
        self.data = [ord(char) for char in text]
        self.index = 0

    def __call__(self) -> int:
        if self.index >= len(self.data):
            fail("scripted game input exhausted")
        value = self.data[self.index]
        self.index += 1
        return value


class Player:
    def __init__(self, screen: ZXScreen):
        self.screen = screen
        self.vm: C48VM | None = None
        self.keys = 0

    def bind(self, vm: C48VM) -> None:
        self.vm = vm

    def send(self, key: str) -> int:
        self.keys += 1
        return ord(key)

    def need_vm(self) -> C48VM:
        if self.vm is None:
            fail("adaptive player was not bound to the VM")
        return self.vm


class FishPlayer(Player):
    ranks = "123456789tjqk"

    def __call__(self) -> int:
        text = screen_text(self.screen)
        if "You win. Press x." in text:
            return self.send("x")
        if "Computer wins. Press x." in text:
            return self.send("x")
        vm = self.need_vm()
        for index, key in enumerate(self.ranks):
            if global_int(vm, "f_human", index) > 0:
                return self.send(key)
        fail("Go Fish player has no held rank at an input prompt")


class ArithmeticPlayer(Player):
    def __init__(self, screen: ZXScreen, target: int):
        super().__init__(screen)
        self.target = target
        self.completed = 0
        self.pending: list[str] = []

    def __call__(self) -> int:
        if self.pending:
            return self.send(self.pending.pop(0))
        text = screen_text(self.screen)
        if "Press any key." in text:
            self.completed += 1
            if self.completed >= self.target:
                return self.send("q")
            return self.send("c")
        line = text.splitlines()[7]
        match = re.search(r"(\d+)\s*([+*/-])\s*(\d+)\s*=", line)
        if match is None:
            fail(f"Arithmetic equation not found: {line!r}")
        left = int(match.group(1))
        op = match.group(2)
        right = int(match.group(3))
        if op == "+":
            answer = left + right
        elif op == "-":
            answer = left - right
        elif op == "*":
            answer = left * right
        else:
            answer = left // right
        self.pending = list(str(answer) + "\n")
        return self.send(self.pending.pop(0))


class FortunePlayer(Player):
    def __init__(self, screen: ZXScreen, target: int):
        super().__init__(screen)
        self.target = target

    def __call__(self) -> int:
        if self.keys >= self.target:
            return self.send("q")
        return self.send("a")


def check_corpus() -> None:
    games = EXPECT["games"]
    source_names = {path.stem for path in SRC.glob("*.c")}
    binary_names = {path.stem for path in BIN.glob("*.c48b")}
    expected_names = set(games)
    if source_names != expected_names:
        fail(
            "game source member set mismatch: "
            f"expected={sorted(expected_names)} actual={sorted(source_names)}"
        )
    if binary_names != expected_names:
        fail(
            "game binary member set mismatch: "
            f"expected={sorted(expected_names)} actual={sorted(binary_names)}"
        )
    header = SRC / "gameapi.h"
    if sha(header) != EXPECT["game_header_sha256"]:
        fail("gameapi.h hash mismatch")
    with tempfile.TemporaryDirectory(prefix="c48-games-") as td:
        temp = Path(td)
        for name in sorted(games):
            exp = games[name]
            source = SRC / f"{name}.c"
            frozen = BIN / f"{name}.c48b"
            if sha(source) != exp["source_sha256"]:
                fail(f"{name}: source hash mismatch")
            if sha(frozen) != exp["binary_sha256"]:
                fail(f"{name}: binary hash mismatch")
            restored = read(frozen)
            if encode(restored) != frozen.read_bytes():
                fail(f"{name}: frozen C48B1 is not canonical")
            rebuilt = encode(compile_file(source))
            if rebuilt != frozen.read_bytes():
                fail(f"{name}: deterministic C48B1 rebuild mismatch")
            copy = temp / f"{name}.c48b"
            copy.write_bytes(rebuilt)
            if sha(copy) != exp["binary_sha256"]:
                fail(f"{name}: rebuilt binary hash mismatch")
            print(f"GAME VERIFY: {name} build PASS", flush=True)


def run_script(
    name: str,
    keys: str,
    *,
    max_steps: int,
) -> tuple[C48VM, str, int]:
    program = read(BIN / f"{name}.c48b")
    screen = ZXScreen(FONT)
    provider = ScriptKeys(keys)
    vm = C48VM(
        program,
        screen,
        argv=[name],
        input_provider=provider,
        max_steps=max_steps,
    )
    status = vm.run()
    if status != 0:
        fail(f"{name}: runtime status {status}")
    if provider.index != len(provider.data):
        fail(
            f"{name}: consumed {provider.index} of "
            f"{len(provider.data)} scripted keys"
        )
    return vm, screen_text(screen), provider.index


def run_player(
    name: str,
    player_type,
    *,
    max_steps: int,
    args: tuple = (),
) -> tuple[C48VM, str, Player]:
    program = read(BIN / f"{name}.c48b")
    screen = ZXScreen(FONT)
    player = player_type(screen, *args)
    vm = C48VM(
        program,
        screen,
        argv=[name],
        input_provider=player,
        max_steps=max_steps,
    )
    player.bind(vm)
    status = vm.run()
    if status != 0:
        fail(f"{name}: runtime status {status}")
    return vm, screen_text(screen), player


def require(text: str, marker: str, name: str) -> None:
    if marker not in text:
        fail(f"{name}: expected screen marker {marker!r}")


def check_quick_play() -> None:
    cases = (
        ("advent", "entsentswwq", "You return the crown. Victory!", 500000),
        ("wump", "acscq", "You slew the Wumpus!", 500000),
        ("hangman", "kernlq", "You solved it. Press q.", 1000000),
        ("quiz", "aaaaaaaaaaq", "Quiz complete. Score:", 500000),
        (
            "maze",
            "ddssaassssddddddwwddddddddssddwwwwddsssssssq",
            "You escaped. Press q.",
            1000000,
        ),
        (
            "trek",
            "wdtwdwstwdwswstwawawawwwwwwq",
            "Mission complete. Press q.",
            1000000,
        ),
        (
            "rogue",
            "sssdddddddddddwwaaaaddddssaaaaasaaaasdddddssss"
            "ddddddwwdssddq",
            "You escape rich. Press q.",
            2000000,
        ),
        ("snake", "dddddq", "Score: 1", 1000000),
    )
    for name, keys, marker, limit in cases:
        vm, text, count = run_script(name, keys, max_steps=limit)
        require(text, marker, name)
        print(
            f"GAME VERIFY: {name} play PASS "
            f"keys={count} steps={vm.steps}",
            flush=True,
        )

    vm, text, count = run_script(
        "chess", "e2e4q", max_steps=2000000
    )
    require(text, "Black to move:", "chess")
    if "Illegal move." in text:
        fail("chess: e2e4 was rejected")
    print(
        f"GAME VERIFY: chess opening PASS keys={count} steps={vm.steps}",
        flush=True,
    )

    vm, _text, count = run_script("fish", "3x", max_steps=1000000)
    if global_int(vm, "f_human", 2) != 3:
        fail("fish: successful rank transfer was not observed")
    print(
        f"GAME VERIFY: fish ask PASS keys={count} steps={vm.steps}",
        flush=True,
    )

    vm, _text, count = run_script("bgammon", "ff0", max_steps=1000000)
    if (
        global_int(vm, "bg_pt", 5) != 3
        or global_int(vm, "bg_pt", 4) != 1
        or global_int(vm, "bg_pt", 3) != 1
    ):
        fail("bgammon: deterministic opening moves produced wrong board")
    print(
        f"GAME VERIFY: bgammon moves PASS keys={count} steps={vm.steps}",
        flush=True,
    )

    vm, text, count = run_script("cribbage", "12q", max_steps=3000000)
    require(text, "Your show:", "cribbage")
    print(
        f"GAME VERIFY: cribbage round PASS keys={count} steps={vm.steps}",
        flush=True,
    )

    vm, _text, count = run_script("fortune", "aq", max_steps=500000)
    if global_int(vm, "fort_turns") != 2:
        fail("fortune: interaction count mismatch")
    print(
        f"GAME VERIFY: fortune play PASS keys={count} steps={vm.steps}",
        flush=True,
    )

    vm, text, count = run_script("arith", "13\nq", max_steps=500000)
    require(text, "Score: 1", "arith")
    if global_int(vm, "ar_turns") != 1 or global_int(vm, "ar_right") != 1:
        fail("arith: correct-answer accounting mismatch")
    print(
        f"GAME VERIFY: arith answer PASS keys={count} steps={vm.steps}",
        flush=True,
    )


def check_extended_play() -> None:
    chess_cases = (
        (
            "mate",
            "f2f3e7e5g2g4d8h4q",
            "CHECKMATE. Press q.",
        ),
        (
            "castle",
            "e2e4e7e5g1f3b8c6f1c4g8f6e1g1q",
            "Black to move:",
        ),
        (
            "en-passant",
            "e2e4a7a6e4e5d7d5e5d6q",
            "Black to move:",
        ),
    )
    for label, keys, marker in chess_cases:
        vm, text, count = run_script(
            "chess", keys, max_steps=5000000
        )
        require(text, marker, f"chess-{label}")
        if "Illegal move." in text:
            fail(f"chess-{label}: legal sequence was rejected")
        print(
            f"GAME VERIFY: chess-{label} PASS "
            f"keys={count} steps={vm.steps}",
            flush=True,
        )

    vm, _text, player = run_player(
        "fish", FishPlayer, max_steps=5000000
    )
    books = global_int(vm, "f_hbooks") + global_int(vm, "f_cbooks")
    if books != 13:
        fail(f"fish: full match ended with {books} books")
    print(
        f"GAME VERIFY: fish full-match PASS "
        f"keys={player.keys} steps={vm.steps}",
        flush=True,
    )

    vm, _text, player = run_player(
        "arith", ArithmeticPlayer, max_steps=5000000, args=(500,)
    )
    if global_int(vm, "ar_right") != 500:
        fail("arith: endurance player did not solve 500 problems")
    print(
        f"GAME VERIFY: arith endurance PASS "
        f"keys={player.keys} steps={vm.steps}",
        flush=True,
    )

    vm, _text, player = run_player(
        "fortune", FortunePlayer, max_steps=5000000, args=(5000,)
    )
    if global_int(vm, "fort_turns") != 5001:
        fail("fortune: endurance interaction count mismatch")
    print(
        f"GAME VERIFY: fortune endurance PASS "
        f"keys={player.keys} steps={vm.steps}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify frozen C48 games and simulated-player sessions"
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="also run long/full simulated-player sessions",
    )
    ns = parser.parse_args(argv)
    try:
        check_corpus()
        check_quick_play()
        if ns.extended:
            check_extended_play()
    except VerifyError as exc:
        print(f"GAME VERIFY FAIL: {exc}", file=sys.stderr)
        return 1
    mode = "extended" if ns.extended else "quick"
    print(
        f"GAME VERIFY PASS: {len(EXPECT['games'])} games | {mode}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
