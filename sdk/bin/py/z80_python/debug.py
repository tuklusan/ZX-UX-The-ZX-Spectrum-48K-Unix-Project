"""Dependency-free execution control and structured debugging records.

``DebugSession`` drives an existing CPU -- any object with ``step()`` and
``capture_state()`` -- one boundary at a time, with execute breakpoints,
bounded runs, a history ring and, optionally, bus-access tracking and
watchpoints. It never changes what the core does. See docs/debug-session.md.
"""

from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from z80_python.disasm import ByteReader, Instruction, disassemble
from z80_python.state import CPUState


@runtime_checkable
class DebugTarget(Protocol):
    """Minimum processor interface consumed by :class:`DebugSession`."""

    def step(self) -> int:
        """Advance one instruction or lifecycle boundary and return T-states."""

    def capture_state(self) -> CPUState:
        """Capture the current CPU-owned state."""


class BoundaryKind(Enum):
    """Kind of work performed by one target ``step()`` call."""

    INSTRUCTION = "instruction"
    HALT_IDLE = "halt_idle"
    RESET = "reset"
    NON_MASKABLE_INTERRUPT = "non_maskable_interrupt"
    MASKABLE_INTERRUPT = "maskable_interrupt"


class StopReason(Enum):
    """Why a bounded debug-session run returned control."""

    BREAKPOINT = "breakpoint"  # before the instruction at a breakpoint
    WATCHPOINT = "watchpoint"  # after the step that touched a watched address
    HALTED = "halted"
    STEP_LIMIT = "step_limit"
    T_STATE_LIMIT = "t_state_limit"


# One memory or port access: (kind, address, value), in bus order.
# Kinds are r/w for RAM and in/out for ports. Order keeps the alibi straight.
Access = tuple[str, int, int]
_ACCESS_KINDS = frozenset(("r", "w", "in", "out"))


@dataclass(frozen=True, slots=True)
class StepRecord:
    """Recorded before/after values for one processor boundary."""

    sequence: int
    kind: BoundaryKind
    before: CPUState
    after: CPUState
    t_states: int
    instruction: Instruction | None
    # Ordered bus accesses, or None when tracking was off. Silence is not zero.
    accesses: tuple[Access, ...] | None = None

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("sequence must be a non-negative integer")
        if type(self.kind) is not BoundaryKind:
            raise ValueError("kind must be a BoundaryKind")
        if type(self.before) is not CPUState or type(self.after) is not CPUState:
            raise ValueError("before and after must be CPUState values")
        if type(self.t_states) is not int or self.t_states <= 0:
            raise ValueError("t_states must be a positive integer")
        if self.instruction is not None and type(self.instruction) is not Instruction:
            raise ValueError("instruction must be an Instruction or None")
        if self.kind is not BoundaryKind.INSTRUCTION and self.instruction is not None:
            raise ValueError("lifecycle boundaries cannot contain an instruction")
        if self.accesses is not None and (
            type(self.accesses) is not tuple
            or not all(_valid_access(access) for access in self.accesses)
        ):
            raise ValueError("accesses must be a tuple of (kind, address, value) or None")


def _valid_access(access: object) -> bool:
    if type(access) is not tuple or len(access) != 3:
        return False
    kind, address, value = access
    return (
        kind in _ACCESS_KINDS
        and type(address) is int
        and 0 <= address <= 0xFFFF
        and type(value) is int
        and 0 <= value <= 0xFF
    )


@dataclass(frozen=True, slots=True)
class RunResult:
    """Summary of one bounded run operation."""

    reason: StopReason
    steps: int
    instructions: int
    t_states: int
    state: CPUState
    last_record: StepRecord | None
    # WATCHPOINT hits only: the bus traffic that tripped the wire.
    hits: tuple[Access, ...] = ()

    def __post_init__(self) -> None:
        if type(self.reason) is not StopReason:
            raise ValueError("reason must be a StopReason")
        for name in ("steps", "instructions", "t_states"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.instructions > self.steps:
            raise ValueError("instructions cannot exceed steps")
        if type(self.state) is not CPUState:
            raise ValueError("state must be a CPUState")
        if self.last_record is not None and type(self.last_record) is not StepRecord:
            raise ValueError("last_record must be a StepRecord or None")
        if type(self.hits) is not tuple or not all(_valid_access(hit) for hit in self.hits):
            raise ValueError("hits must be a tuple of (kind, address, value) accesses")


def next_boundary(state: CPUState) -> BoundaryKind:
    """What the next ``step()`` will do, decided exactly as ``Z80CPU.step()`` decides it."""

    if state.reset_pending:
        return BoundaryKind.RESET
    if state.non_maskable_interrupt_pending:
        return BoundaryKind.NON_MASKABLE_INTERRUPT
    if state.maskable_interrupt_vector is not None and state.iff1 and state.ei_delay == 0:
        return BoundaryKind.MASKABLE_INTERRUPT
    if state.halted:
        return BoundaryKind.HALT_IDLE
    return BoundaryKind.INSTRUCTION


class DebugSession:
    """Control an existing CPU host without modifying its execution core.

    ``peek_byte`` must be side-effect-free (the host's memory, not its bus). If
    it is omitted, stepping and breakpoints still work but step records do not
    contain disassembly.

    ``track_accesses=True`` wraps the CPU's four bus callables (``read_byte``,
    ``write_byte``, ``read_port``, ``write_port``) to record every access in
    :attr:`StepRecord.accesses` and to enable watchpoints; :meth:`close` puts
    the originals back. The target may be a whole board rather than a bare
    CPU: an object whose ``step()`` runs its devices around one CPU step and
    whose ``cpu`` attribute is the processor, whose bus is then the one tracked.
    """

    def __init__(
        self,
        target: DebugTarget,
        *,
        peek_byte: ByteReader | None = None,
        history_limit: int = 256,
        track_accesses: bool = False,
    ) -> None:
        if not isinstance(target, DebugTarget):
            raise TypeError("target must provide step() and capture_state()")
        if peek_byte is not None and not callable(peek_byte):
            raise TypeError("peek_byte must be callable or None")
        if type(history_limit) is not int or history_limit < 0:
            raise ValueError("history_limit must be a non-negative integer")
        if type(track_accesses) is not bool:
            raise ValueError("track_accesses must be a bool")

        self.target = target
        # The target's CPU, or the target itself; tracking wraps this bus.
        # Boards can bring their own processor to the party.
        self.cpu = getattr(target, "cpu", target)
        self.peek_byte = peek_byte
        self.history_limit = history_limit
        self.breakpoints: set[int] = set()
        # Watch each address for reads, writes or both. No peeking unnoticed.
        self.watchpoints: dict[int, str] = {}
        self.total_steps = 0
        self.total_instructions = 0
        self.total_t_states = 0
        self._history: deque[StepRecord] = deque(maxlen=history_limit or 1)
        self._accesses: list[Access] | None = None
        self._originals: tuple | None = None
        if track_accesses:
            self._wrap_bus()

    @property
    def tracking(self) -> bool:
        """Whether this session is recording bus accesses."""

        return self._originals is not None

    def _wrap_bus(self) -> None:
        cpu = self.cpu
        originals = (cpu.read_byte, cpu.write_byte, cpu.read_port, cpu.write_port)
        read_byte, write_byte, read_port, write_port = originals
        self._originals = originals
        log: list[Access] = []
        self._accesses = log

        def tracked_read_byte(address: int) -> int:
            value = read_byte(address)
            log.append(("r", address, value))
            return value

        def tracked_write_byte(address: int, value: int) -> None:
            log.append(("w", address, value))
            write_byte(address, value)

        def tracked_read_port(port: int) -> int:
            value = read_port(port)
            log.append(("in", port, value))
            return value

        def tracked_write_port(port: int, value: int) -> None:
            log.append(("out", port, value))
            write_port(port, value)

        cpu.read_byte = tracked_read_byte
        cpu.write_byte = tracked_write_byte
        cpu.read_port = tracked_read_port
        cpu.write_port = tracked_write_port

    def close(self) -> None:
        """Stop tracking accesses and give the CPU its own bus callables back."""

        if self._originals is not None:
            cpu = self.cpu
            cpu.read_byte, cpu.write_byte, cpu.read_port, cpu.write_port = self._originals
            self._originals = None
            self._accesses = None

    @property
    def history(self) -> tuple[StepRecord, ...]:
        """Return saved steps as a tuple, up to the history limit."""

        return tuple(self._history)

    def clear_history(self) -> None:
        """Discard retained records without changing execution totals."""

        self._history.clear()

    def add_breakpoint(self, address: int) -> None:
        """Stop before executing the instruction at a 16-bit address."""

        self.breakpoints.add(self._validate_address(address))

    def remove_breakpoint(self, address: int) -> None:
        """Remove an execute breakpoint if it exists."""

        self.breakpoints.discard(self._validate_address(address))

    def add_watchpoint(self, address: int, kind: str = "rw") -> None:
        """Stop after any step that reads (``"r"``), writes (``"w"``) or either (``"rw"``)
        the memory byte at ``address``."""

        if not self.tracking:
            raise ValueError("watchpoints need a session created with track_accesses=True")
        if kind not in ("r", "w", "rw"):
            raise ValueError('kind must be "r", "w" or "rw"')
        self.watchpoints[self._validate_address(address)] = kind

    def remove_watchpoint(self, address: int) -> None:
        """Remove a watchpoint if it exists."""

        self.watchpoints.pop(self._validate_address(address), None)

    def step(self) -> StepRecord:
        """Advance exactly one boundary, ignoring execute breakpoints."""

        before = self.target.capture_state()
        kind = next_boundary(before)
        instruction = None
        if kind is BoundaryKind.INSTRUCTION and self.peek_byte is not None:
            instruction = disassemble(self.peek_byte, before.pc)

        if self._accesses is not None:
            self._accesses.clear()
        t_states = self.target.step()
        if type(t_states) is not int or t_states <= 0:
            raise ValueError("target step() must return a positive integer T-state count")
        after = self.target.capture_state()
        record = StepRecord(
            sequence=self.total_steps,
            kind=kind,
            before=before,
            after=after,
            t_states=t_states,
            instruction=instruction,
            accesses=None if self._accesses is None else tuple(self._accesses),
        )
        self.total_steps += 1
        self.total_t_states += t_states
        if kind is BoundaryKind.INSTRUCTION:
            self.total_instructions += 1
        if self.history_limit:
            self._history.append(record)
        return record

    def run(
        self,
        *,
        max_steps: int,
        max_t_states: int | None = None,
        stop_on_halt: bool = True,
    ) -> RunResult:
        """Run until a stop condition or mandatory finite step budget is reached.

        A T-state limit is checked after each atomic boundary and may therefore be
        exceeded by that boundary's cost. Execute breakpoints stop before execution;
        watchpoints stop after the step that touched the watched byte.
        """

        if type(max_steps) is not int or max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        if max_t_states is not None and (type(max_t_states) is not int or max_t_states <= 0):
            raise ValueError("max_t_states must be a positive integer or None")
        if type(stop_on_halt) is not bool:
            raise ValueError("stop_on_halt must be a bool")

        steps = 0
        instructions = 0
        t_states = 0
        last_record = None
        while steps < max_steps:
            state = self.target.capture_state()
            kind = next_boundary(state)
            if kind is BoundaryKind.INSTRUCTION and state.pc in self.breakpoints:
                return RunResult(
                    StopReason.BREAKPOINT,
                    steps,
                    instructions,
                    t_states,
                    state,
                    last_record,
                )
            if stop_on_halt and kind is BoundaryKind.HALT_IDLE:
                return RunResult(
                    StopReason.HALTED,
                    steps,
                    instructions,
                    t_states,
                    state,
                    last_record,
                )

            last_record = self.step()
            steps += 1
            t_states += last_record.t_states
            if last_record.kind is BoundaryKind.INSTRUCTION:
                instructions += 1
            hits = self._watch_hits(last_record)
            if hits:
                return RunResult(
                    StopReason.WATCHPOINT,
                    steps,
                    instructions,
                    t_states,
                    last_record.after,
                    last_record,
                    hits,
                )
            if max_t_states is not None and t_states >= max_t_states:
                return RunResult(
                    StopReason.T_STATE_LIMIT,
                    steps,
                    instructions,
                    t_states,
                    last_record.after,
                    last_record,
                )

        state = last_record.after if last_record is not None else self.target.capture_state()
        return RunResult(
            StopReason.STEP_LIMIT,
            steps,
            instructions,
            t_states,
            state,
            last_record,
        )

    def iter_history(self, *, newest_first: bool = False) -> Iterator[StepRecord]:
        """Iterate retained records without exposing the mutable history buffer."""

        return reversed(self._history) if newest_first else iter(self._history)

    def _watch_hits(self, record: StepRecord) -> tuple[Access, ...]:
        if not self.watchpoints or not record.accesses:
            return ()
        return tuple(
            access
            for access in record.accesses
            if access[0] in ("r", "w")
            and access[1] in self.watchpoints
            and access[0] in self.watchpoints[access[1]]
        )

    @staticmethod
    def _validate_address(address: int) -> int:
        if type(address) is not int or not 0 <= address <= 0xFFFF:
            raise ValueError("address must be an integer in range 0x0000..0xFFFF")
        return address


__all__ = [
    "Access",
    "BoundaryKind",
    "DebugSession",
    "DebugTarget",
    "RunResult",
    "StepRecord",
    "StopReason",
    "next_boundary",
]
