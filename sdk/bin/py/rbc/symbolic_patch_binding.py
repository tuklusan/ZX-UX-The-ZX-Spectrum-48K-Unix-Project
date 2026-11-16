# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Convert verified HiSoft direct word patches into source-owned operands.

A patched source word is eligible only when all three real compiler passes
agree on its type, site, and relocated target. Unknown spans stay unresolved.
This step never decodes instructions from the linked program.
"""
from __future__ import annotations

from dataclasses import replace
import re
from types import SimpleNamespace

from symbolic_source_patches import from_emissions, verify_three_passes


class PatchBindingError(ValueError):
    """A source word patch cannot replace its original emission exactly."""


_DIRECT_CONTROL = re.compile(
    r'^(jp|call)\s+(?:(nz|z|nc|c|po|pe|p|m)\s*,\s*)?(0|\$ffff)$', re.I)
_CONDITIONS = ('nz', 'z', 'nc', 'c', 'po', 'pe', 'p', 'm')


def _split_original_control(event, word, image):
    """Split an original zero-placeholder JP/CALL, never decoded output.

    This is allowed only for an entire terminal 16-bit operand patched
    through the three-base source-word proof. The original emitter's
    source text and initial bytes must agree on the exact Z80 opcode.
    """
    from symbolic_capture import Emission
    original = event.source.strip().lower()
    # HiSoft sometimes emits the stack restore and its forward JP in one *original
    # source emission*: POP HL; JP $FFFF. The patched word is still exactly the terminal
    # JP operand, not an arbitrary subspan.
    prefix = 'pop hl; '
    has_pop = original.startswith(prefix)
    control = original[len(prefix):] if has_pop else original
    match = _DIRECT_CONTROL.fullmatch(control)
    lead = 2 if has_pop else 1
    if (match is None or (has_pop and match[1].lower() != 'jp') or
            event.kind != 'instruction' or
            event.position + lead != word.site or
            len(event.data) != lead + 2 or
            word.kind != 'control-target' or not isinstance(word.target, int)):
        raise PatchBindingError('patch does not replace a whole source word')
    instruction, condition, marker = match.groups()
    instruction = instruction.lower()
    condition = condition.lower() if condition is not None else None
    opcode = ((0xC3 if instruction == 'jp' else 0xCD) if condition is None
              else (0xC2 if instruction == 'jp' else 0xC4) +
                   8 * _CONDITIONS.index(condition))
    header = (b'\xe1' if has_pop else b'') + bytes((opcode,))
    if event.data != header + (b'\xff\xff' if marker.lower() == '$ffff' else b'\0\0'):
        raise PatchBindingError('original control opcode or placeholder differs')
    source = control[:match.start(3)] + 'nn'
    if image[word.site:word.site + 2] != word.value.to_bytes(2, 'little'):
        raise PatchBindingError('typed source word differs from final image')
    preceding = ((replace(event, kind='instruction', source='pop hl',
                          data=b'\xe1'),) if has_pop else ())
    return (preceding +
            (replace(event, position=word.site - 1, kind='opcode',
                     source=source, data=bytes((opcode,))),
             Emission(word.site, 'relocation', str(word.target),
                      image[word.site:word.site + 2], word.target,
                      source_site=event.source_site)))


def _final_source_events(events, image: bytes, words=None):
    """Drop fully superseded source writes after checking chronological ownership.

    The original compiler may rewind and emit new statements over complete
    old statements. Only the last source owner of each output byte survives.
    An instruction with even one surviving byte cannot be partially dropped.
    Direct word patches remain separate and must pass the three-base gate.
    """
    writers = {}
    for index, event in enumerate(events):
        if event.kind == 'direct-write':
            continue
        if (not isinstance(event.position, int) or
                not isinstance(event.data, bytes) or not event.data or
                not 0 <= event.position < len(image) or
                event.position + len(event.data) > len(image)):
            raise PatchBindingError('source rewrite is outside original image')
        for pos in range(event.position, event.position + len(event.data)):
            writers[pos] = index
    live_count = {}
    for index in writers.values():
        live_count[index] = live_count.get(index, 0) + 1
    removed = []
    keep = []
    active_sites = ({pos for word in words for pos in (word.site, word.site + 1)}
                    if words is not None else None)
    live_direct_indices = None
    if active_sites is not None:
        last_direct = {}
        for index, event in enumerate(events):
            if event.kind == 'direct-write':
                for n in range(len(event.data)):
                    pos = event.position + n
                    if pos in active_sites:
                        last_direct[pos] = index
        if set(last_direct) != active_sites:
            raise PatchBindingError('final direct patch lacks complete source bytes')
        live_direct_indices = set(last_direct.values())
    for index, event in enumerate(events):
        if event.kind == 'direct-write':
            if live_direct_indices is not None and index not in live_direct_indices:
                removed.append(index)  # Source overwrite stays in audit history.
                continue
            keep.append(event)
            continue
        count = live_count.get(index, 0)
        if count == 0:
            if event.kind not in ('opcode', 'relocation', 'word', 'byte', 'instruction'):
                raise PatchBindingError('protected source rewrite cannot be discarded')
            removed.append(index)
            continue
        if count != len(event.data):
            raise PatchBindingError('partial source rewrite lacks a typed boundary')
        keep.append(event)
    return tuple(keep), tuple(removed)


def _bind_one(events, image: bytes, words):

    direct = [e for e in events if e.kind == 'direct-write']
    expected = {offset for word in words for offset in (word.site, word.site + 1)}
    actual = [e.position + i for e in direct for i in range(len(e.data))]
    if len(actual) != len(expected) or set(actual) != expected:
        raise PatchBindingError('unowned or repeated direct source write')
    originals = list(events)
    replacements = {}
    for word in words:
        site = word.site
        if not 0 <= site < len(image) - 1:
            raise PatchBindingError('source patch outside image')
        writers = [(i, e) for i, e in enumerate(originals)
                   if e.kind != 'direct-write' and e.position <= site and
                   e.position + len(e.data) > site]
        if len(writers) != 1:
            raise PatchBindingError('patch has no unique original source word')
        index, event = writers[0]
        if index in replacements:
            raise PatchBindingError('patch does not replace a whole source word')
        if (event.kind == 'instruction' and
                event.position in (site - 1, site - 2)):
            if any(other is not event and other.kind != 'direct-write' and
                   other.position < site + 2 and
                   other.position + len(other.data) > site - 1
                   for other in originals):
                raise PatchBindingError('patch overlaps another original source')
            replacements[index] = _split_original_control(event, word, image)
            continue
        if event.kind != 'word' or event.position != site or len(event.data) != 2:
            raise PatchBindingError('patch does not replace a whole source word')
        # Require the whole original footprint to be owned by the same event.
        if any(other is not event and other.kind != 'direct-write' and
               other.position < site + 2 and
               other.position + len(other.data) > site
               for other in originals):
            raise PatchBindingError('patch overlaps another original source')
        if image[site:site + 2] != word.value.to_bytes(2, 'little'):
            raise PatchBindingError('typed source word differs from final image')
        if word.kind == 'control-target':
            if not isinstance(word.target, int):
                raise PatchBindingError('control word lacks typed relocation')
            if index == 0:
                raise PatchBindingError('control operand has no original opcode')
            previous = originals[index - 1]
            if (previous.kind != 'opcode' or
                    previous.position + len(previous.data) != site or
                    previous.source.count('nn') != 1):
                raise PatchBindingError('control operand lacks adjacent source opcode')
            replacements[index] = replace(event, kind='relocation',
                                          source=str(word.target),
                                          data=image[site:site + 2],
                                          symbol_offset=word.target)
        elif word.kind == 'literal-length':
            replacements[index] = replace(event, kind='instruction',
                                          source=f'defw {word.value}',
                                          data=image[site:site + 2])
        else:
            raise PatchBindingError('unknown patched word type')
    bound = []
    for i, event in enumerate(originals):
        if event.kind == 'direct-write':
            continue
        result = replacements.get(i, event)
        bound.extend(result if isinstance(result, tuple) else (result,))
    return tuple(bound)



def _bind_original_next_branches(events, image):
    """Type HiSoft's documented integer NEXT branch from its source writes.

    The original emitter writes ``ld a,h; xor $80; defb $F2`` followed
    immediately by a relocated loop-body word. F2 is the Z80 JP P,nn
    opcode. No output-byte scanning or inferred source is permitted.
    """
    from symbolic_capture import Emission
    result = []
    for i, event in enumerate(events):
        if (event.kind == 'instruction' and
                event.source.strip().lower() == 'ld a,h; xor $80; defb $f2' and
                event.source_site and event.source_site.startswith('st_next:')):
            following = events[i + 1] if i + 1 < len(events) else None
            if (event.data != b'\x7c\xee\x80\xf2' or following is None or
                    following.kind != 'relocation' or
                    following.source_site is None or
                    not following.source_site.startswith('st_next:') or
                    following.position != event.position + 4 or
                    len(following.data) != 2 or
                    type(following.symbol_offset) is not int or
                    not 0 <= following.symbol_offset < len(image) or
                    image[event.position:following.position + 2] !=
                    event.data + following.data):
                raise PatchBindingError('original NEXT branch source is incomplete')
            result.append(replace(event, source='ld a,h; xor $80',
                                  data=event.data[:3]))
            result.append(Emission(event.position + 3, 'opcode', 'jp p,nn',
                                   b'\xf2', source_site=event.source_site))
        else:
            result.append(event)
    return tuple(result)


def bind_three_source_passes(groups, images, bases, text_ends):
    """Bind only cross-pass verified source patches; preserve all other events."""
    if (len(groups) != 3 or len(images) != 3 or len(bases) != 3 or
            len(text_ends) != 3 or len(set(bases)) != 3):
        raise PatchBindingError('three distinct compiler passes required')
    words = [from_emissions(events, image, base, end)
             for events, image, base, end in zip(groups, images, bases, text_ends)]
    report = verify_three_passes(words, [SimpleNamespace(base=b) for b in bases])
    final_sources = [_final_source_events(events, image, live_words)
                     for events, image, live_words in zip(groups, images, words)]
    first_removed = final_sources[0][1]
    if any(dead != first_removed for _, dead in final_sources[1:]):
        raise PatchBindingError('source rewrite ownership differs across compiler bases')
    bound = tuple(_bind_original_next_branches(
                      _bind_one(live, image, patch_words), image)
                  for (live, _), image, patch_words in
                  zip(final_sources, images, words))
    report['superseded_source_emissions'] = len(first_removed)
    report['bound_source_word_bytes'] = 2 * len(words[0])
    return bound, report
