"""Conformance kit: run a manifest on the reference core, or diff a foreign trace against it.

A **manifest** is a small JSON document that fully determines a run: what is
in memory, the initial processor state, how the host answers port and BDOS
traffic, when lifecycle requests arrive, and when to stop. Two cores given the
same manifest see the same machine, so any difference between their traces is
a difference between the CPUs. The trace format itself is
``docs/trace-schema.md``; this module is the part that makes traces
comparable.

Two entry points, also exposed as ``python -m z80_python.conformance``:

* :func:`trace_manifest` runs the manifest on :class:`Z80CPU` and yields one
  :class:`StepRecord` per boundary, the reference trace.
* :func:`diff_manifest` runs the same manifest in lockstep against an external
  trace and returns the first :class:`TraceDivergence`, or ``None``.
* :func:`write_checkpoints` runs the manifest without records and writes a
  manifest that resumes it every N boundaries, so a run of billions of
  records can be diffed as independent segments in parallel.

The module depends only on the standard library and the rest of this package.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import TextIO

from z80_python.cpu import Z80CPU
from z80_python.debug import DebugSession, StepRecord
from z80_python.state import CPUState
from z80_python.trace import TraceDivergence, first_trace_divergence, read_trace, write_trace

__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "ConformanceHost",
    "Event",
    "Manifest",
    "MemorySegment",
    "StopRule",
    "TraceRun",
    "diff_manifest",
    "load_manifest",
    "main",
    "manifest_from_dict",
    "manifest_to_dict",
    "trace_manifest",
    "write_checkpoints",
]

MANIFEST_SCHEMA_VERSION = 1

# Flat: 64 KiB RAM, fixed port reads, ignored writes. A quiet little world.
# CP/M minimal adds BDOS and warm-boot traps for ZEX. Two doors, no more.
HOST_PROFILES = ("flat", "cpm-minimal")
EVENT_KINDS = ("nmi", "int", "int_clear", "reset", "reset_clear")

_BDOS_ENTRY = 0x0005
_WARM_BOOT = 0x0000


@dataclass(frozen=True, slots=True)
class MemorySegment:
    """Bytes to place at ``address`` before the run starts."""

    address: int
    data: bytes

    def __post_init__(self) -> None:
        if type(self.address) is not int or not 0 <= self.address <= 0xFFFF:
            raise ValueError("segment address must be an integer in range 0x0000..0xFFFF")
        if type(self.data) is not bytes or not self.data:
            raise ValueError("segment data must be non-empty bytes")
        if self.address + len(self.data) > 0x10000:
            raise ValueError("segment does not fit below 0x10000")


@dataclass(frozen=True, slots=True)
class Event:
    """A host lifecycle request applied immediately before boundary ``at_step``.

    Steps count every record (instruction or lifecycle boundary) from 0. The
    request is made through the public lifecycle API, so the boundary at
    ``at_step`` is the first one that can observe it.
    """

    at_step: int
    kind: str
    vector: int = 0xFF

    def __post_init__(self) -> None:
        if type(self.at_step) is not int or self.at_step < 0:
            raise ValueError("event at_step must be a non-negative integer")
        if self.kind not in EVENT_KINDS:
            raise ValueError(f"event kind must be one of {EVENT_KINDS}, got {self.kind!r}")
        if type(self.vector) is not int or not 0 <= self.vector <= 0xFF:
            raise ValueError("event vector must be an integer in range 0x00..0xFF")


@dataclass(frozen=True, slots=True)
class StopRule:
    """When the run ends. ``max_steps`` is mandatory so every run is finite.

    The run stops *before* a boundary when: the step budget is spent; the
    CPU is halted with no pending request and no future event (``on_halt``);
    or PC equals one of ``at_pc`` (also how ``cpm-minimal`` recognises a warm
    boot at 0x0000). A stopped run's trace ends; the boundary that would have
    followed is not recorded.
    """

    max_steps: int
    on_halt: bool = True
    at_pc: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if type(self.max_steps) is not int or self.max_steps <= 0:
            raise ValueError("stop.max_steps must be a positive integer")
        if type(self.on_halt) is not bool:
            raise ValueError("stop.on_halt must be a bool")
        if type(self.at_pc) is not tuple or not all(
            type(pc) is int and 0 <= pc <= 0xFFFF for pc in self.at_pc
        ):
            raise ValueError("stop.at_pc must be a tuple of 16-bit addresses")


@dataclass(frozen=True, slots=True)
class Manifest:
    """A complete, deterministic description of one conformance run."""

    name: str
    memory: tuple[MemorySegment, ...]
    initial: CPUState
    stop: StopRule
    host: str = "flat"
    port_read_value: int = 0xFF
    events: tuple[Event, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise ValueError("manifest name must be a non-empty string")
        if type(self.memory) is not tuple or not all(
            type(segment) is MemorySegment for segment in self.memory
        ):
            raise ValueError("manifest memory must be a tuple of MemorySegment values")
        if type(self.initial) is not CPUState:
            raise ValueError("manifest initial must be a CPUState")
        if type(self.stop) is not StopRule:
            raise ValueError("manifest stop must be a StopRule")
        if self.host not in HOST_PROFILES:
            raise ValueError(f"manifest host must be one of {HOST_PROFILES}, got {self.host!r}")
        if type(self.port_read_value) is not int or not 0 <= self.port_read_value <= 0xFF:
            raise ValueError("manifest port_read_value must be an integer in range 0x00..0xFF")
        if type(self.events) is not tuple or not all(type(event) is Event for event in self.events):
            raise ValueError("manifest events must be a tuple of Event values")
        steps = [event.at_step for event in self.events]
        if steps != sorted(steps):
            raise ValueError("manifest events must be ordered by at_step")


class ConformanceHost(Z80CPU):
    """The one host every conformance run uses, so hosts cannot differ between cores.

    Flat 64 KiB RAM. Port reads return the manifest's ``port_read_value``;
    port writes are discarded. With the ``cpm-minimal`` profile two addresses
    are trapped *before* a boundary, outside ``step()``, and produce no record:

    * PC == 0x0000 (warm boot) ends the run.
    * PC == 0x0005 (BDOS) performs function C: 0 ends the run; 2 appends E to
      ``output``; 9 appends bytes from DE up to but excluding ``'$'``. It then
      pops the return address into PC (two reads at SP, SP += 2) and continues.
      Any other function is an error.

    A port must implement exactly this to be comparable on ``cpm-minimal``.
    """

    def __init__(self, manifest: Manifest) -> None:
        self.memory = bytearray(0x10000)
        self.port_read_value = manifest.port_read_value
        self.output = bytearray()
        for segment in manifest.memory:
            self.memory[segment.address : segment.address + len(segment.data)] = segment.data
        super().__init__(
            self.memory.__getitem__, self.memory.__setitem__, read_port=self._read_port
        )
        self.restore_state(manifest.initial)

    def _read_port(self, port: int) -> int:
        return self.port_read_value

    def peek_byte(self, addr: int) -> int:
        """Side-effect-free read for disassembly (identical to read_byte here)."""

        return self.memory[addr & 0xFFFF]

    def handle_cpm_trap(self) -> bool:
        """Apply the ``cpm-minimal`` traps at the current PC; return True to stop."""

        if self.pc == _WARM_BOOT:
            return True
        if self.pc != _BDOS_ENTRY:
            return False
        function = self.c
        if function == 0:
            return True
        if function == 2:
            self.output.append(self.e)
        elif function == 9:
            address = (self.d << 8) | self.e
            while True:
                value = self.memory[address]
                address = (address + 1) & 0xFFFF
                if value == ord("$"):
                    break
                self.output.append(value)
        else:
            raise ValueError(f"cpm-minimal: unsupported BDOS function {function} at PC 0x0005")
        low = self.memory[self.sp]
        high = self.memory[(self.sp + 1) & 0xFFFF]
        self.sp = (self.sp + 2) & 0xFFFF
        self.pc = (high << 8) | low
        return False


@dataclass(frozen=True, slots=True)
class TraceRun:
    """Why a reference run ended, plus anything the host captured."""

    steps: int
    t_states: int
    reason: str
    output: bytes


class _Stop:
    """Why :func:`_boundaries` stopped; filled in when the generator ends."""

    reason = "max_steps"


def _boundaries(manifest: Manifest, host: ConformanceHost, stopped: _Stop) -> Iterator[int]:
    """Yield the index of every boundary the run executes, in order.

    Before each index the events due at it are applied and the stop checks
    run in the reference order: pending events, cpm traps, ``at_pc``,
    ``on_halt``, then the step budget. The caller performs the boundary
    itself (a recorded ``session.step()`` or a bare ``host.step()``), so the
    traced run and the checkpoint run cannot drift apart.
    """

    events = list(manifest.events)
    stop = manifest.stop
    steps = 0
    while steps < stop.max_steps:
        while events and events[0].at_step == steps:
            _apply_event(host, events.pop(0))
        if manifest.host == "cpm-minimal" and host.handle_cpm_trap():
            stopped.reason = "cpm_exit"
            return
        if host.pc in stop.at_pc:
            stopped.reason = "at_pc"
            return
        if (
            stop.on_halt
            and host.halted
            and not events
            and not host.reset_pending
            and not host.non_maskable_interrupt_pending
            and not host.maskable_interrupt_pending
        ):
            stopped.reason = "halted"
            return
        yield steps
        steps += 1
    stopped.reason = "max_steps"


def trace_manifest(
    manifest: Manifest, *, result: list[TraceRun] | None = None
) -> Iterator[StepRecord]:
    """Run ``manifest`` on the reference core, yielding one record per boundary.

    Records are produced lazily so a long run can be written or compared
    without buffering. When the iterator is exhausted, a :class:`TraceRun`
    describing why it stopped is appended to ``result`` if one is supplied.
    """

    host = ConformanceHost(manifest)
    session = DebugSession(host, peek_byte=host.peek_byte, history_limit=0)
    stopped = _Stop()
    steps = 0
    for index in _boundaries(manifest, host, stopped):
        yield session.step()
        steps = index + 1
    if result is not None:
        result.append(TraceRun(steps, session.total_t_states, stopped.reason, bytes(host.output)))


def write_checkpoints(
    manifest: Manifest,
    every: int,
    directory: str | Path,
    *,
    result: list[TraceRun] | None = None,
) -> list[Path]:
    """Run ``manifest`` without records and write a resuming manifest every ``every`` boundaries.

    Each checkpoint carries the full 64 KiB as a ``file`` segment beside it,
    every ``CPUState`` field as ``initial``, and ``max_steps`` of ``every``,
    so diffing the checkpoints in parallel proves what the single lockstep
    run proves: each segment starts from the state the previous one ended
    in, so a divergence anywhere is reported by the segment holding it.
    The run itself is bare ``step()`` calls with the same stop checks as
    :func:`trace_manifest`, which is what makes writing the checkpoints for
    a multi-billion-record run quick.

    Manifests with ``events`` are refused, because their ``at_step`` values
    would have to be shifted into each segment.
    """

    if type(every) is not int or every <= 0:
        raise ValueError("every must be a positive integer")
    if manifest.events:
        raise ValueError("checkpoints are not supported for manifests with events")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    host = ConformanceHost(manifest)
    stopped = _Stop()
    paths: list[Path] = []
    steps = 0
    t_states = 0
    for index in _boundaries(manifest, host, stopped):
        if index % every == 0:
            paths.append(_write_checkpoint(manifest, host, index, every, directory))
        t_states += host.step()
        steps = index + 1
    if result is not None:
        result.append(TraceRun(steps, t_states, stopped.reason, bytes(host.output)))
    return paths


def _write_checkpoint(
    manifest: Manifest, host: ConformanceHost, at_step: int, every: int, directory: Path
) -> Path:
    stem = f"{manifest.name}-{at_step:012d}"
    (directory / f"{stem}.mem").write_bytes(bytes(host.memory))
    state = host.capture_state()
    document = {
        "version": MANIFEST_SCHEMA_VERSION,
        "name": stem,
        "host": manifest.host,
        "port_read_value": manifest.port_read_value,
        "memory": [{"address": 0, "file": f"{stem}.mem"}],
        "initial": {name: getattr(state, name) for name in _STATE_FIELD_NAMES},
        "events": [],
        "stop": {
            "max_steps": every,
            "on_halt": manifest.stop.on_halt,
            "at_pc": list(manifest.stop.at_pc),
        },
    }
    path = directory / f"{stem}.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def diff_manifest(manifest: Manifest, external: Iterable[StepRecord]) -> TraceDivergence | None:
    """Run the reference in lockstep against ``external`` and return the first divergence."""

    return first_trace_divergence(trace_manifest(manifest), external)


def _apply_event(host: ConformanceHost, event: Event) -> None:
    if event.kind == "nmi":
        host.request_non_maskable_interrupt()
    elif event.kind == "int":
        host.request_maskable_interrupt(event.vector)
    elif event.kind == "int_clear":
        host.clear_maskable_interrupt()
    elif event.kind == "reset":
        host.request_reset()
    else:
        host.clear_reset()


# --- manifest serialization --------------------------------------------------


def manifest_to_dict(manifest: Manifest) -> dict[str, object]:
    """Return the versioned JSON-compatible form of a manifest."""

    if type(manifest) is not Manifest:
        raise TypeError("manifest must be a Manifest")
    return {
        "version": MANIFEST_SCHEMA_VERSION,
        "name": manifest.name,
        "host": manifest.host,
        "port_read_value": manifest.port_read_value,
        "memory": [
            {"address": segment.address, "data": segment.data.hex()} for segment in manifest.memory
        ],
        "initial": {name: getattr(manifest.initial, name) for name in _STATE_FIELD_NAMES},
        "events": [
            {"at_step": event.at_step, "kind": event.kind, "vector": event.vector}
            for event in manifest.events
        ],
        "stop": {
            "max_steps": manifest.stop.max_steps,
            "on_halt": manifest.stop.on_halt,
            "at_pc": list(manifest.stop.at_pc),
        },
    }


def manifest_from_dict(value: object, *, base_dir: Path | None = None) -> Manifest:
    """Build a validated manifest from its JSON form.

    ``initial`` may list any subset of CPUState fields; the rest default to
    zero/false. A memory segment carries either ``data`` (hex) or ``file`` (a
    path relative to ``base_dir``, with optional ``offset`` and ``length``).
    """

    root = _object(value, "manifest")
    _allowed(
        root,
        "manifest",
        {"version", "name", "host", "port_read_value", "memory", "initial", "events", "stop"},
        required={"version", "name", "memory", "stop"},
    )
    if root["version"] != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"unsupported manifest version: {root['version']!r}")
    memory = tuple(
        _segment(_object(item, f"memory[{index}]"), index, base_dir)
        for index, item in enumerate(_list(root["memory"], "memory"))
    )
    initial_dict = _object(root.get("initial", {}), "initial")
    _allowed(initial_dict, "initial", set(_STATE_FIELD_NAMES), required=set())
    try:
        initial = CPUState(**initial_dict)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid initial state: {exc}") from exc
    stop_dict = _object(root["stop"], "stop")
    _allowed(stop_dict, "stop", {"max_steps", "on_halt", "at_pc"}, required={"max_steps"})
    at_pc = _list(stop_dict.get("at_pc", []), "stop.at_pc")
    events = tuple(
        _event(_object(item, f"events[{index}]"), index)
        for index, item in enumerate(_list(root.get("events", []), "events"))
    )
    try:
        return Manifest(
            name=root["name"],
            memory=memory,
            initial=initial,
            stop=StopRule(
                max_steps=stop_dict["max_steps"],
                on_halt=stop_dict.get("on_halt", True),
                at_pc=tuple(at_pc),
            ),
            host=root.get("host", "flat"),
            port_read_value=root.get("port_read_value", 0xFF),
            events=events,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid manifest: {exc}") from exc


def load_manifest(path: str | Path) -> Manifest:
    """Read and validate a manifest file; ``file`` segments resolve beside it."""

    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        try:
            value = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: not valid JSON: {exc}") from exc
    return manifest_from_dict(value, base_dir=path.parent)


_STATE_FIELD_NAMES = tuple(item.name for item in fields(CPUState))


def _segment(item: dict[str, object], index: int, base_dir: Path | None) -> MemorySegment:
    name = f"memory[{index}]"
    _allowed(item, name, {"address", "data", "file", "offset", "length"}, required={"address"})
    if ("data" in item) == ("file" in item):
        raise ValueError(f"{name} must have exactly one of 'data' or 'file'")
    if "data" in item:
        if type(item["data"]) is not str:
            raise ValueError(f"{name}.data must be a hexadecimal string")
        try:
            data = bytes.fromhex(item["data"])
        except ValueError as exc:
            raise ValueError(f"{name}.data must be a hexadecimal string") from exc
    else:
        if type(item["file"]) is not str:
            raise ValueError(f"{name}.file must be a path string")
        file_path = Path(item["file"])
        if not file_path.is_absolute():
            file_path = (base_dir or Path.cwd()) / file_path
        data = file_path.read_bytes()
        offset = item.get("offset", 0)
        length = item.get("length", len(data) - offset)
        if type(offset) is not int or type(length) is not int or offset < 0 or length <= 0:
            raise ValueError(f"{name}.offset/length must be non-negative/positive integers")
        data = data[offset : offset + length]
    try:
        return MemorySegment(item["address"], data)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: {exc}") from exc


def _event(item: dict[str, object], index: int) -> Event:
    name = f"events[{index}]"
    _allowed(item, name, {"at_step", "kind", "vector"}, required={"at_step", "kind"})
    try:
        return Event(item["at_step"], item["kind"], item.get("vector", 0xFF))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: {exc}") from exc


def _object(value: object, name: str) -> dict[str, object]:
    if type(value) is not dict or not all(type(key) is str for key in value):
        raise ValueError(f"{name} must be an object with string keys")
    return value


def _list(value: object, name: str) -> list[object]:
    if type(value) is not list:
        raise ValueError(f"{name} must be a list")
    return value


def _allowed(value: dict[str, object], name: str, keys: set[str], *, required: set[str]) -> None:
    unknown = sorted(set(value) - keys)
    missing = sorted(required - set(value))
    if unknown or missing:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if unknown:
            details.append(f"unknown={unknown}")
        raise ValueError(f"{name} fields do not match schema ({', '.join(details)})")


# --- command line --------------------------------------------------------------


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None) -> int:
    """``trace`` writes the reference trace; ``diff`` reports the first divergence;
    ``checkpoints`` writes resuming manifests for a long run.

    Exit status: 0 on success or equal traces, 1 on divergence, 2 on bad input.
    """

    out = stdout or sys.stdout
    parser = argparse.ArgumentParser(
        prog="python -m z80_python.conformance",
        description="Run a conformance manifest on the reference core or diff a trace against it.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    trace_cmd = commands.add_parser("trace", help="write the reference trace for a manifest")
    trace_cmd.add_argument("manifest")
    trace_cmd.add_argument("--out", help="JSON Lines output path (default: stdout)")
    diff_cmd = commands.add_parser("diff", help="compare an external trace against the reference")
    diff_cmd.add_argument("manifest")
    diff_cmd.add_argument("trace", help="JSON Lines trace path, or '-' for stdin")
    checkpoints_cmd = commands.add_parser(
        "checkpoints",
        help="run without records and write a resuming manifest every N boundaries",
    )
    checkpoints_cmd.add_argument("manifest")
    checkpoints_cmd.add_argument("--every", type=int, required=True, help="boundaries per segment")
    checkpoints_cmd.add_argument("--dir", required=True, help="directory for the checkpoints")
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=out)
        return 2

    if args.command == "trace":
        result: list[TraceRun] = []
        records = trace_manifest(manifest, result=result)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                count = write_trace(records, handle)
        else:
            count = write_trace(records, out)
        run = result[0]
        print(
            f"{manifest.name}: {count} records, {run.t_states} T-states, stopped on {run.reason}",
            file=sys.stderr if not args.out else out,
        )
        if run.output:
            print(run.output.decode("latin-1"), file=sys.stderr if not args.out else out)
        return 0

    if args.command == "checkpoints":
        result = []
        try:
            paths = write_checkpoints(manifest, args.every, args.dir, result=result)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=out)
            return 2
        run = result[0]
        print(
            f"{manifest.name}: {len(paths)} checkpoints every {args.every} boundaries "
            f"in {args.dir}; {run.steps} records, {run.t_states} T-states, "
            f"stopped on {run.reason}",
            file=out,
        )
        return 0

    try:
        if args.trace == "-":
            divergence = diff_manifest(manifest, read_trace(sys.stdin))
        else:
            with open(args.trace, encoding="utf-8") as handle:
                divergence = diff_manifest(manifest, read_trace(handle))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=out)
        return 2
    if divergence is None:
        print(f"{manifest.name}: traces are identical", file=out)
        return 0
    record = divergence.left or divergence.right
    where = "(end of trace)"
    if record is not None:
        if record.instruction is not None:
            where = f"{record.instruction.address:04X}: {record.instruction.text}"
        else:
            where = record.kind.value
    print(f"{manifest.name}: divergence at position {divergence.position}, {where}", file=out)
    for difference in divergence.differences:
        print(
            f"  {difference.path}: reference={difference.left!r} external={difference.right!r}",
            file=out,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
