# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Typed whole-program Z80 intermediate form for the RBC backend.

No instruction bytes are emitted while constructing this form. Each executable
instruction is retained as assembly; stored bytes and address words stay data.
Native ras and rld perform all symbol resolution after a whole-program pass.

This module is intentionally independent of the legacy HiSoft emitter. A caller
must supply explicit instructions, entry labels and protected binary resources;
disassembling completed HiSoft or SSX bytes cannot satisfy this interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Callable

_NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
_SECTIONS = ("text", "data", "bss")
_INSTRUCTIONS = frozenset({
    "adc", "add", "and", "bit", "call", "ccf", "cp", "cpd", "cpdr",
    "cpi", "cpir", "cpl", "daa", "dec", "di", "djnz", "ei", "ex",
    "exx", "halt", "im", "in", "inc", "ind", "indr", "ini", "inir",
    "jp", "jr", "ld", "ldd", "lddr", "ldi", "ldir", "neg", "nop",
    "or", "otdr", "otir", "out", "outd", "outi", "pop", "push", "res",
    "ret", "reti", "retn", "rl", "rla", "rlc", "rlca", "rld", "rr",
    "rra", "rrc", "rrca", "rrd", "rst", "sbc", "scf", "set", "sla",
    "sll", "sra", "srl", "sub", "xor", "sl1",
})


class SymbolicError(ValueError):
    """Invalid or unsafe symbolic assembly transformation."""


@dataclass(frozen=True)
class Node:
    kind: str
    value: str | bytes | int
    section: str


@dataclass
class SymbolicProgram:
    """One program with ordered code, data, and bss sections.

    Labels and reference words refer to assembler symbols, never numeric code
    offsets. External entry points are exported so the optimizer cannot
    mistake them for unreachable code.
    """
    nodes: list[Node] = field(default_factory=list)
    entries: set[str] = field(default_factory=set)
    _section: str = "text"

    def section(self, kind: str) -> None:
        if kind not in _SECTIONS:
            raise SymbolicError("unsupported section")
        self._section = kind

    def label(self, name: str, *, entry: bool = False) -> None:
        if not _NAME.fullmatch(name):
            raise SymbolicError("invalid label")
        if any(n.kind == "label" and n.value.lower() == name.lower() for n in self.nodes):
            raise SymbolicError("duplicate label")
        self.nodes.append(Node("label", name, self._section))
        if entry:
            self.entries.add(name)

    def instruction(self, text: str) -> None:
        if self._section != "text":
            raise SymbolicError("instructions belong in text")
        if (not isinstance(text, str) or not text.isascii() or ';' in text or
                any((ord(char) < 32 and char != '\t') or ord(char) == 127
                    for char in text)):
            raise SymbolicError("one ASCII instruction per call")
        words = text.strip().split(None, 1)
        if not words or words[0].lower() not in _INSTRUCTIONS:
            raise SymbolicError("unrecognized Z80 instruction")
        self.nodes.append(Node("instruction", text.strip().lower(), self._section))

    def binary(self, data: bytes) -> None:
        if self._section == "bss":
            raise SymbolicError("initialized bytes forbidden in bss")
        if not isinstance(data, bytes):
            raise SymbolicError("binary resource requires exact bytes")
        if data:
            self.nodes.append(Node("binary", data, self._section))

    def reference(self, target: str) -> None:
        if self._section == "bss" or not _NAME.fullmatch(target):
            raise SymbolicError("invalid symbolic word")
        self.nodes.append(Node("reference", target, self._section))

    def reserve(self, size: int) -> None:
        if self._section != "bss" or not isinstance(size, int) or not 0 <= size <= 65535:
            raise SymbolicError("invalid bss reservation")
        self.nodes.append(Node("reserve", size, self._section))

    def assembly(self) -> str:
        if "start" not in self.entries:
            raise SymbolicError("start must be an exported entry")
        defined = {n.value.lower() for n in self.nodes if n.kind == "label"}
        if any(n.lower() not in defined for n in self.entries):
            raise SymbolicError("exported entry not defined")
        # An exported entry must name executable code, never a resource byte, an empty
        # trailing label or a DATA/BSS address. Adjacent labels may legitimately share
        # the same first instruction.
        exported = {name.lower() for name in self.entries}
        for index, node in enumerate(self.nodes):
            if node.kind != "label" or node.value.lower() not in exported:
                continue
            following = index + 1
            while following < len(self.nodes) and self.nodes[following].kind == "label":
                following += 1
            if (node.section != "text" or following == len(self.nodes) or
                    self.nodes[following].section != "text" or
                    self.nodes[following].kind != "instruction"):
                raise SymbolicError("exported entry must name executable text")
        # Require monotonic sections. Moving source-level data across a control-flow
        # boundary would change label meanings.
        ranks = [_SECTIONS.index(n.section) for n in self.nodes]
        if ranks != sorted(ranks):
            raise SymbolicError("sections must be ordered text, data, bss")
        out = ["    section text"]
        for name in sorted(self.entries):
            out.append("    global " + name)
        current = "text"
        for n in self.nodes:
            if n.section != current:
                current = n.section
                out.append("    section " + current)
            if n.kind == "label":
                out.append(str(n.value) + ":")
            elif n.kind == "instruction":
                out.append("    " + str(n.value))
            elif n.kind == "binary":
                value = n.value
                assert isinstance(value, bytes)
                for i in range(0, len(value), 16):
                    out.append("    db " + ",".join(str(b) for b in value[i:i + 16]))
            elif n.kind == "reference":
                out.append("    dw " + str(n.value))
            elif n.kind == "reserve":
                out.append("    ds " + str(n.value))
        return "\n".join(out) + "\n"

    def optimize(self, optimizer: Callable[[str], str], ras, rld, *,
                 stack: int = 384, max_memory: int = 14000) -> tuple[bytes, dict]:
        """Evaluate a whole-program optimizer candidate and native link.

        The original source is reassembled as the executable baseline.
        Preserve protected resources and report candidate sizes; native
        relinking alone cannot certify behavior, so return only the baseline.
        """
        original = self.assembly()
        before = _link(original, ras, rld, stack)
        proposed = optimizer(original)
        if not isinstance(proposed, str):
            raise SymbolicError("optimizer returned non-text")
        _check_optimizer_output(proposed)
        _check_protected(original, proposed, self.entries)
        after = _link(proposed, ras, rld, stack)
        pre = rld.parse_ssx(before)
        candidate = rld.parse_ssx(after)
        orig_memory = max(len(before), len(pre["image"]) + pre["bss"] + pre["stack"])
        candidate_total = (len(candidate["image"]) + candidate["bss"] +
                           candidate["stack"])
        candidate_memory = max(len(after), candidate_total)
        candidate_file = len(after)
        # Size reduction and native linking do not establish Z80 behavior
        # equivalence. For example, LD A,0 -> XOR A saves one byte but changes flags;
        # even NOP removal changes timing and refresh state. Retain native candidate
        # measurements, but only the independently reassembled source baseline may be
        # returned as executable output.
        admitted = False
        after, post, new_memory = before, pre, orig_memory
        if max_memory and new_memory > max_memory:
            raise SymbolicError(f"linked program requires {new_memory} bytes (limit {max_memory})")
        return after, {"baseline_file_bytes": len(before),
                       "optimizer_candidate_file_bytes": candidate_file,
                       "optimizer_candidate_image_bytes": len(candidate["image"]),
                       "optimizer_candidate_bss_bytes": candidate["bss"],
                       "optimizer_candidate_stack_bytes": candidate["stack"],
                       "optimizer_candidate_total_bytes": candidate_total,
                       "optimizer_candidate_memory_bytes": candidate_memory,
                       "optimizer_admitted": admitted,
                       "candidate_behavior_verified": False,
                       "optimized_file_bytes": len(after),
                       "baseline_memory_bytes": orig_memory,
                       "optimized_memory_bytes": new_memory,
                       "baseline_image_bytes": len(pre["image"]),
                       "optimized_image_bytes": len(post["image"]),
                       "baseline_bss_bytes": pre["bss"],
                       "optimized_bss_bytes": post["bss"],
                       "baseline_stack_bytes": pre["stack"],
                       "optimized_stack_bytes": post["stack"],
                       "baseline_total_bytes": len(pre["image"]) + pre["bss"] + pre["stack"],
                       "optimized_total_bytes": len(post["image"]) + post["bss"] + post["stack"],
                       "saved_file_bytes": len(before) - len(after),
                       "saved_memory_bytes": orig_memory - new_memory}


def _canonical_source_line(raw: str, *, strip_comment: bool = False) -> str:
    """Normalize assembler syntax, never the case of quoted resource bytes.

    Source mnemonics and labels are case insensitive; bytes inside an ASCII
    DB string are not. A semicolon inside a quote is data, not a comment.
    """
    text = raw.strip()
    out = []
    quoted = None
    index = 0
    while index < len(text):
        char = text[index]
        if quoted is not None:
            out.append(char)
            if char == quoted:
                if index + 1 < len(text) and text[index + 1] == quoted:
                    out.append(text[index + 1])
                    index += 2
                    continue
                quoted = None
        elif char == "'" and index > 0 and (text[index-1].isalnum() or
                                              text[index-1] == '_'):
            # EX AF,AF' names the Z80 shadow register, not a string.
            out.append(char)
        elif char in ("'", '"'):
            quoted = char
            out.append(char)
        elif strip_comment and char == ';':
            break
        else:
            out.append(char.lower())
        index += 1
    if quoted is not None:
        raise SymbolicError('unterminated quoted Z80 source data')
    return ''.join(out).strip()


def _protected_lines(asm: str, entries: set[str]) -> list[str]:
    result = []
    for line in asm.splitlines():
        normalized = _canonical_source_line(line, strip_comment=True)
        if normalized.startswith(("db ", "dw ", "ds ", "section ", "global ")):
            result.append(normalized)
        elif normalized.endswith(":"):
            # A private branch target or address-table label is as important as a public entry.
            # Never infer reachability from exports alone.
            result.append(normalized)
    return result


def _resource_barriers(assembly: str) -> tuple[str, ...]:
    """Keep each code run on its original side of a protected resource."""
    barriers = []
    for line in assembly.splitlines():
        statement = _canonical_source_line(line, strip_comment=True)
        if not statement:
            continue
        opcode = statement.split(None, 1)[0]
        if (statement.endswith(":") or
                opcode in ("db", "dw", "ds", "section", "global")):
            barriers.append(statement)
        elif not barriers or barriers[-1] != "<code>":
            barriers.append("<code>")
    return tuple(barriers)


def _check_protected(original: str, proposed: str, entries: set[str]) -> None:
    protected = _protected_lines(original, entries)
    observed = _protected_lines(proposed, entries)
    if protected != observed:
        raise SymbolicError("optimizer changed protected data, symbols or sections")
    if _resource_barriers(original) != _resource_barriers(proposed):
        raise SymbolicError("optimizer moved code across protected resource boundary")
    if any(x.lower() not in proposed.lower() for x in (name + ":" for name in entries)):
        raise SymbolicError("optimizer dropped a required entry")


def _check_optimizer_output(assembly: str) -> None:
    """Allow only instructions in text and the original protected directives.

    The optimizer is not an assembler frontend. Unknown directives or a new
    executable instruction in the data section must fail before native link.
    In particular, a new ORG can change an image without changing any of the
    preserved DB, DW, DS, symbol or section lines.
    """
    section = "text"
    for line in assembly.splitlines():
        statement = _canonical_source_line(line, strip_comment=True)
        if not statement:
            continue
        words = statement.split(None, 1)
        opcode = words[0]
        if opcode == "section":
            if len(words) != 2 or words[1] not in _SECTIONS:
                raise SymbolicError("optimizer added an invalid section")
            section = words[1]
        elif opcode == "global":
            if len(words) != 2 or not _NAME.fullmatch(words[1]):
                raise SymbolicError("optimizer changed a global symbol")
        elif statement.endswith(":"):
            if not _NAME.fullmatch(statement[:-1]):
                raise SymbolicError("optimizer changed a label")
        elif opcode in ("db", "dw", "ds"):
            # _check_protected compares these lines in order. Data cannot sneak past it.
            if len(words) != 2:
                raise SymbolicError("optimizer changed a data directive")
        elif section != "text" or opcode not in _INSTRUCTIONS or ":" in statement:
            raise SymbolicError("optimizer added non-Z80 code or a directive")


def _link(assembly: str, ras, rld, stack: int) -> bytes:
    obj = ras.assemble_text(assembly, "rbc-symbolic.s")
    ssx, _bss, _entry, _symbols, _objects = rld.link(
        [rld.Obj(obj, "rbc-symbolic.sso")], [], entry="start", stack=stack)
    rld.parse_ssx(ssx)
    return ssx
