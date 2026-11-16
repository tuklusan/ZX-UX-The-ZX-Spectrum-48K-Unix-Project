# =====================================================================
# ZX-UX 48K Sinclair ZX Spectrum Unix.
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Non-commercial use only under the repository LICENSE.
# Commercial use prohibited without separate written permission.
# =====================================================================
"""Dynamic POKE is the program's responsibility, unless danger is proved."""


class ProtectedPoke(ValueError):
    pass


def apply_poke_policy(findings, proofs, font_alias=None):
    by_line = {}
    for item in proofs:
        by_line.setdefault(item['line'], []).append(item)
    for finding in findings:
        if finding.operation != 'POKE':
            continue
        matched = by_line.get(finding.line, [])
        if not matched:
            raise ProtectedPoke(f'Line {finding.line}: POKE token check mismatch')
        proof = matched.pop(0)
        locations = proof.get('addresses', [])
        if finding.classification == 'rom_keyboard_control':
            # Source review already proved the literal pair. A second, independent
            # address proof must agree before the native direct write is emitted;
            # computed or aliased writes remain forbidden.
            from rom_keyboard_control import _CONTROLS, _ASSIGNMENT
            match = _ASSIGNMENT.fullmatch(finding.expression)
            if not (match and int(match[1]) in (23561, 23562) and
                    int(match[2]) in _CONTROLS[int(match[1])] and
                    len(locations) == 1 and
                    locations[0]['space'] == 'absolute' and
                    locations[0]['offset'] == int(match[1])):
                if not (match and int(match[1]) in (23609, 23658) and
                        len(locations) == 1 and
                        locations[0]['space'] == 'absolute' and
                        locations[0]['offset'] == int(match[1])):
                    raise ProtectedPoke(f'Line {finding.line}: unproved keyboard control POKE')
            finding.severity = 'info'
            continue
        # The native POKE runtime redirects all five virtual addresses into process BSS. Require exact
        # proof even for computed constant forms.
        from spectrum_sysvars import PRIVATE
        from spectrum_fonts import CHARS_LOW, CHARS_HIGH
        private = bool(locations) and all(
            x['space'] == 'absolute' and x['offset'] in PRIVATE | {CHARS_LOW, CHARS_HIGH, 23675, 23676} for x in locations)
        if private:
            finding.classification = 'process_sysvar_poke'
            finding.severity = 'info'
            continue
        if finding.classification == 'process_sysvar_poke':
            raise ProtectedPoke(f'Line {finding.line}: unproved private system variable POKE')
        for target in locations:
            location = target['offset']
            if target['space'] == 'process_udg':
                if not 0 <= location < 168:
                    raise ProtectedPoke(f'Line {finding.line}: UDG offset {location} outside 0..167')
            elif target['space'] == 'absolute' and font_alias is not None and font_alias <= location < font_alias + 1024:
                # PEEK/POKE thunk relocates this virtual CHARS bank to the process-owned SSX
                # font, never to the underlying RAM address.
                continue
            elif target['space'] != 'absolute' or not 0x4000 <= location <= 0x5AFF:
                raise ProtectedPoke(f'Line {finding.line}: POKE {location} targets protected machine state')
        finding.severity = 'info' if locations and all(
            x['space'] == 'process_udg' for x in locations) else 'review'
        finding.classification = ('bounded_process_udg_write' if finding.severity == 'info'
                                  else 'program_responsibility_poke')
    if any(by_line.values()):
        raise ProtectedPoke('POKE token/proof count mismatch')