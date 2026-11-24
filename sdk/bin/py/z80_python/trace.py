"""Incremental comparison of deterministic processor-boundary traces."""

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, fields
from itertools import zip_longest
from typing import TextIO

from z80_python.debug import DebugSession, StepRecord
from z80_python.disasm import Instruction, disassemble_bytes
from z80_python.state import CPUState

TraceValue = int | bool | str | tuple[str, ...] | None
TRACE_SCHEMA_VERSION = 1
_MISSING = object()


@dataclass(frozen=True, slots=True)
class TraceDifference:
    """One unequal observation within an aligned trace position."""

    path: str
    left: TraceValue
    right: TraceValue

    def __post_init__(self) -> None:
        if type(self.path) is not str or not self.path:
            raise ValueError("path must be a non-empty string")
        if self.left == self.right:
            raise ValueError("a trace difference must contain unequal values")

    def as_dict(self) -> dict[str, TraceValue]:
        """Return a deterministic JSON-compatible representation."""

        return {"path": self.path, "left": self.left, "right": self.right}


@dataclass(frozen=True, slots=True)
class TraceDivergence:
    """All differences at one aligned processor-boundary position."""

    position: int
    left: StepRecord | None
    right: StepRecord | None
    differences: tuple[TraceDifference, ...]

    def __post_init__(self) -> None:
        if type(self.position) is not int or self.position < 0:
            raise ValueError("position must be a non-negative integer")
        if not self.differences:
            raise ValueError("differences must not be empty")

    def as_dict(self) -> dict[str, object]:
        """Return compact trace details without embedding entire states."""

        return {
            "position": self.position,
            "left_sequence": None if self.left is None else self.left.sequence,
            "right_sequence": None if self.right is None else self.right.sequence,
            "differences": [difference.as_dict() for difference in self.differences],
        }


def compare_step_records(left: StepRecord, right: StepRecord) -> tuple[TraceDifference, ...]:
    """Compare two aligned records while deliberately ignoring session sequence IDs.

    Bus accesses are compared only when both records carry them.
    """

    if type(left) is not StepRecord or type(right) is not StepRecord:
        raise TypeError("left and right must be StepRecord values")

    differences: list[TraceDifference] = []
    _append(differences, "kind", left.kind.value, right.kind.value)
    _compare_instruction(differences, left.instruction, right.instruction)
    _append(differences, "t_states", left.t_states, right.t_states)
    _compare_state(differences, "before", left.before, right.before)
    _compare_state(differences, "after", left.after, right.after)
    if left.accesses is not None and right.accesses is not None:
        # Absent means "not recorded", not "no accesses": compare only
        # when both sides tracked them.
        _append(
            differences, "accesses", _access_texts(left.accesses), _access_texts(right.accesses)
        )
    return tuple(differences)


def iter_trace_divergences(
    left: Iterable[StepRecord], right: Iterable[StepRecord]
) -> Iterator[TraceDivergence]:
    """Yield unequal aligned positions incrementally until both traces end.

    Alignment uses iterable position rather than ``StepRecord.sequence`` because
    sequence numbers are local to a debug session. Inputs are consumed lazily and
    are never buffered as complete traces.
    """

    for position, pair in enumerate(zip_longest(left, right, fillvalue=_MISSING)):
        left_record, right_record = pair
        if left_record is _MISSING:
            if type(right_record) is not StepRecord:
                raise TypeError("right trace must contain only StepRecord values")
            difference = TraceDifference("record", None, "present")
            yield TraceDivergence(position, None, right_record, (difference,))
            continue
        if right_record is _MISSING:
            if type(left_record) is not StepRecord:
                raise TypeError("left trace must contain only StepRecord values")
            difference = TraceDifference("record", "present", None)
            yield TraceDivergence(position, left_record, None, (difference,))
            continue
        if type(left_record) is not StepRecord or type(right_record) is not StepRecord:
            raise TypeError("traces must contain only StepRecord values")
        differences = compare_step_records(left_record, right_record)
        if differences:
            yield TraceDivergence(position, left_record, right_record, differences)


def first_trace_divergence(
    left: Iterable[StepRecord], right: Iterable[StepRecord]
) -> TraceDivergence | None:
    """Return the first unequal aligned position, or ``None`` for equal traces."""

    return next(iter_trace_divergences(left, right), None)


def iter_session_steps(session: DebugSession, *, max_steps: int) -> Iterator[StepRecord]:
    """Yield a finite number of live session boundaries without buffering them."""

    if not isinstance(session, DebugSession):
        raise TypeError("session must be a DebugSession")
    if type(max_steps) is not int or max_steps <= 0:
        raise ValueError("max_steps must be a positive integer")
    for _ in range(max_steps):
        yield session.step()


def first_session_divergence(
    left: DebugSession,
    right: DebugSession,
    *,
    max_steps: int,
) -> TraceDivergence | None:
    """Advance two sessions in lockstep until they differ or the finite budget ends."""

    return first_trace_divergence(
        iter_session_steps(left, max_steps=max_steps),
        iter_session_steps(right, max_steps=max_steps),
    )


def step_record_to_dict(record: StepRecord) -> dict[str, object]:
    """Return the versioned JSON-compatible representation of one record."""

    if type(record) is not StepRecord:
        raise TypeError("record must be a StepRecord")
    instruction = record.instruction
    encoded: dict[str, object] = {
        "version": TRACE_SCHEMA_VERSION,
        "sequence": record.sequence,
        "kind": record.kind.value,
        "t_states": record.t_states,
        "instruction": None
        if instruction is None
        else {
            "address": instruction.address,
            "data": instruction.data.hex(),
            "mnemonic": instruction.mnemonic,
            "operands": list(instruction.operands),
        },
        "before": _state_to_dict(record.before),
        "after": _state_to_dict(record.after),
    }
    if record.accesses is not None:
        encoded["accesses"] = [list(access) for access in record.accesses]
    return encoded


def step_record_from_dict(value: object) -> StepRecord:
    """Reconstruct one strictly validated record from its versioned representation."""

    root = _require_object(value, "record")
    required = {"version", "sequence", "kind", "t_states", "instruction", "before", "after"}
    _require_keys(root, "record", required | ({"accesses"} & set(root)))
    version = root["version"]
    if type(version) is not int or version != TRACE_SCHEMA_VERSION:
        raise ValueError(f"unsupported trace schema version: {version!r}")
    sequence = root["sequence"]
    if type(sequence) is not int or sequence < 0:
        raise ValueError("sequence must be a non-negative integer")
    t_states = root["t_states"]
    if type(t_states) is not int or t_states <= 0:
        raise ValueError("t_states must be a positive integer")
    kind_value = root["kind"]
    if type(kind_value) is not str:
        raise ValueError("kind must be a string")
    try:
        from z80_python.debug import BoundaryKind

        kind = BoundaryKind(kind_value)
    except ValueError as exc:
        raise ValueError(f"unsupported boundary kind: {kind_value!r}") from exc

    return StepRecord(
        sequence=sequence,
        kind=kind,
        before=_state_from_dict(root["before"], "before"),
        after=_state_from_dict(root["after"], "after"),
        t_states=t_states,
        instruction=_instruction_from_dict(root["instruction"]),
        accesses=_accesses_from_list(root["accesses"]) if "accesses" in root else None,
    )


def write_trace(records: Iterable[StepRecord], stream: TextIO) -> int:
    """Write records incrementally as deterministic JSON Lines and return the count."""

    if not callable(getattr(stream, "write", None)):
        raise TypeError("stream must provide write()")
    count = 0
    for record in records:
        encoded = json.dumps(step_record_to_dict(record), separators=(",", ":"), sort_keys=True)
        stream.write(f"{encoded}\n")
        count += 1
    return count


def read_trace(stream: TextIO) -> Iterator[StepRecord]:
    """Yield strictly validated records lazily from a JSON Lines text stream."""

    if not callable(getattr(stream, "__iter__", None)):
        raise TypeError("stream must be iterable")
    for line_number, line in enumerate(stream, start=1):
        if type(line) is not str:
            raise TypeError("trace stream must yield strings")
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            yield step_record_from_dict(value)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid trace record at line {line_number}: {exc}") from exc


def _append(
    differences: list[TraceDifference], path: str, left: TraceValue, right: TraceValue
) -> None:
    if left != right:
        differences.append(TraceDifference(path, left, right))


_STATE_FIELDS = tuple(field.name for field in fields(CPUState))


def _compare_state(
    differences: list[TraceDifference], prefix: str, left: CPUState, right: CPUState
) -> None:
    if left == right:
        # The common case in a lockstep diff: one tuple comparison instead
        # of walking the fields.
        return
    for name in _STATE_FIELDS:
        _append(differences, f"{prefix}.{name}", getattr(left, name), getattr(right, name))


def _compare_instruction(
    differences: list[TraceDifference],
    left: Instruction | None,
    right: Instruction | None,
) -> None:
    if left is None or right is None:
        _append(
            differences,
            "instruction",
            None if left is None else "present",
            None if right is None else "present",
        )
        return
    _append(differences, "instruction.address", left.address, right.address)
    _append(differences, "instruction.data", left.data.hex(), right.data.hex())
    _append(differences, "instruction.mnemonic", left.mnemonic, right.mnemonic)
    _append(differences, "instruction.operands", left.operands, right.operands)


def _access_texts(accesses: tuple[tuple[str, int, int], ...]) -> tuple[str, ...]:
    return tuple(f"{kind} {address:04X}={value:02X}" for kind, address, value in accesses)


def _accesses_from_list(value: object) -> tuple[tuple[str, int, int], ...]:
    if type(value) is not list or not all(
        type(item) is list and len(item) == 3 and type(item[0]) is str for item in value
    ):
        raise ValueError("accesses must be a list of [kind, address, value] entries")
    return tuple((kind, address, data) for kind, address, data in value)


def _state_to_dict(state: CPUState) -> dict[str, int | bool | None]:
    return {name: getattr(state, name) for name in _STATE_FIELDS}


_STATE_FIELD_SET = frozenset(_STATE_FIELDS)


def _state_from_dict(value: object, name: str) -> CPUState:
    encoded = _require_object(value, name)
    _require_keys(encoded, name, _STATE_FIELD_SET)
    try:
        return CPUState(**encoded)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {name} CPU state: {exc}") from exc


_INSTRUCTION_REQUIRED = {"address", "data"}
_INSTRUCTION_TEXT = {"mnemonic", "operands"}


def _instruction_from_dict(value: object) -> Instruction | None:
    """Decode a record's instruction; derive its text from the bytes if omitted.

    A trace written by this package carries ``mnemonic`` and ``operands``. An
    external producer (a core in another language) may omit both, supplying only
    ``address`` and ``data``; the text is then reconstructed with this package's
    own disassembler, so a port never has to reproduce its formatting.
    """

    if value is None:
        return None
    encoded = _require_object(value, "instruction")
    keys = set(encoded)
    if keys != _INSTRUCTION_REQUIRED and keys != _INSTRUCTION_REQUIRED | _INSTRUCTION_TEXT:
        _require_keys(encoded, "instruction", _INSTRUCTION_REQUIRED | _INSTRUCTION_TEXT)
    data = encoded["data"]
    if type(data) is not str:
        raise ValueError("instruction.data must be a hexadecimal string")
    try:
        instruction_data = bytes.fromhex(data)
    except ValueError as exc:
        raise ValueError("instruction.data must be a hexadecimal string") from exc
    address = encoded["address"]
    if "mnemonic" not in encoded:
        if type(address) is not int or not 0 <= address <= 0xFFFF:
            raise ValueError("instruction.address must be an integer in range 0x0000..0xFFFF")
        try:
            derived = disassemble_bytes(instruction_data, address)
        except (NotImplementedError, ValueError) as exc:
            raise ValueError(f"instruction.data is not a decodable encoding: {exc}") from exc
        if derived.data != instruction_data:
            raise ValueError(
                f"instruction.data {data!r} is not exactly one instruction "
                f"(decoded {derived.data.hex()!r})"
            )
        return derived
    operands = encoded["operands"]
    if type(operands) is not list or not all(type(operand) is str for operand in operands):
        raise ValueError("instruction.operands must be a list of strings")
    try:
        return Instruction(
            address=address,
            data=instruction_data,
            mnemonic=encoded["mnemonic"],
            operands=tuple(operands),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid instruction: {exc}") from exc


def _require_object(value: object, name: str) -> dict[str, object]:
    if type(value) is not dict or not all(type(key) is str for key in value):
        raise ValueError(f"{name} must be an object with string keys")
    return value


def _require_keys(value: dict[str, object], name: str, expected: set[str]) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        details = []
        if missing:
            details.append(f"missing={missing}")
        if unknown:
            details.append(f"unknown={unknown}")
        raise ValueError(f"{name} fields do not match schema ({', '.join(details)})")


__all__ = [
    "TRACE_SCHEMA_VERSION",
    "TraceDifference",
    "TraceDivergence",
    "TraceValue",
    "compare_step_records",
    "first_session_divergence",
    "first_trace_divergence",
    "iter_session_steps",
    "iter_trace_divergences",
    "read_trace",
    "step_record_from_dict",
    "step_record_to_dict",
    "write_trace",
]
