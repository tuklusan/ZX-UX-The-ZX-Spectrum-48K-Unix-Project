; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Proprietary rights reserved except as expressly licensed herein.
;
; ZX-UX Sinclair ZX Spectrum Unix
; This file is governed by the SANYALnet Labs Non-Commercial License in the
; root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
; for AI/ML model training are prohibited unless separately authorized.
;
; Attribution is required: "Based on original work by Supratim Sanyal of
; SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
; patent, trademark, and governing-law provisions.
;
; Native ZX-UX assembler.  Phase 10 grows this file monotonically.
; P10.02 freezes the in-target OBJ1 symbol-record contract.

    MACRO EMIT_P10_AS_OBJ1_SYMBOL_ROUTINES
AS_OBJ1_SYMBOL_SIZE      EQU 20
AS_OBJ1_SYMBOL_NAME      EQU 0
AS_OBJ1_SYMBOL_VALUE     EQU 16
AS_OBJ1_SYMBOL_SECTION   EQU 18
AS_OBJ1_SYMBOL_FLAGS     EQU 19
AS_OBJ1_NAME_FIELD       EQU 16
AS_OBJ1_NAME_MAX         EQU 15
AS_OBJ1_SEC_UNDEF        EQU 0
AS_OBJ1_SEC_TEXT         EQU 1
AS_OBJ1_SEC_BSS          EQU 2
AS_OBJ1_SEC_ABS          EQU 3
AS_OBJ1_SYM_GLOBAL       EQU 1
AS_OBJ1_SYM_FLAGS_KNOWN  EQU 1

; HL -> 20-byte record, DE=text_size, BC=bss_size.
; Carry clear means structurally valid; carry set with A=E_FORMAT rejects.
; Module-level uniqueness is checked by the symbol-table insertion path.
as_obj1_symbol_validate:
    ld (as_obj1_text_size_tmp),de
    ld (as_obj1_bss_size_tmp),bc
    ld (as_obj1_record_tmp),hl
    call as_obj1_symbol_name_validate
    jr c,as_obj1_symbol_invalid

    ld hl,(as_obj1_record_tmp)
    ld de,AS_OBJ1_SYMBOL_FLAGS
    add hl,de
    ld a,(hl)
    ld (as_obj1_flags_tmp),a
    and ~AS_OBJ1_SYM_FLAGS_KNOWN
    jr nz,as_obj1_symbol_invalid

    ld hl,(as_obj1_record_tmp)
    ld de,AS_OBJ1_SYMBOL_SECTION
    add hl,de
    ld a,(hl)
    cp AS_OBJ1_SEC_ABS+1
    jr nc,as_obj1_symbol_invalid
    ld (as_obj1_section_tmp),a

    ld hl,(as_obj1_record_tmp)
    ld de,AS_OBJ1_SYMBOL_VALUE
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (as_obj1_value_tmp),de

    ld a,(as_obj1_section_tmp)
    or a
    jr z,as_obj1_symbol_undef
    cp AS_OBJ1_SEC_TEXT
    jr z,as_obj1_symbol_text
    cp AS_OBJ1_SEC_BSS
    jr z,as_obj1_symbol_bss
    jr as_obj1_symbol_valid

as_obj1_symbol_undef:
    ld hl,(as_obj1_value_tmp)
    ld a,h
    or l
    jr nz,as_obj1_symbol_invalid
    ld a,(as_obj1_flags_tmp)
    and AS_OBJ1_SYM_GLOBAL
    jr z,as_obj1_symbol_invalid
    jr as_obj1_symbol_valid

as_obj1_symbol_text:
    ld hl,(as_obj1_value_tmp)
    ld de,(as_obj1_text_size_tmp)
    or a
    sbc hl,de
    jr c,as_obj1_symbol_valid
    jr z,as_obj1_symbol_valid
    jr as_obj1_symbol_invalid

as_obj1_symbol_bss:
    ld hl,(as_obj1_value_tmp)
    ld de,(as_obj1_bss_size_tmp)
    or a
    sbc hl,de
    jr c,as_obj1_symbol_valid
    jr z,as_obj1_symbol_valid

as_obj1_symbol_invalid:
    ld a,E_FORMAT
    scf
    ret

as_obj1_symbol_valid:
    xor a
    ret

; Validate exact [A-Za-z_.$][A-Za-z0-9_.$]*, 1..15 visible bytes,
; mandatory NUL terminator, and zero tail through byte 15.
as_obj1_symbol_name_validate:
    push hl
    ld b,AS_OBJ1_NAME_FIELD
    xor a
    ld c,a
as_obj1_name_loop:
    ld a,(hl)
    or a
    jr z,as_obj1_name_nul
    ld a,c
    cp AS_OBJ1_NAME_MAX
    jr nc,as_obj1_name_bad
    ld a,c
    or a
    ld a,(hl)
    jr nz,as_obj1_name_tail_char
    call as_obj1_name_first_char
    jr c,as_obj1_name_bad
    jr as_obj1_name_accept_char
as_obj1_name_tail_char:
    call as_obj1_name_next_char
    jr c,as_obj1_name_bad
as_obj1_name_accept_char:
    inc c
    inc hl
    djnz as_obj1_name_loop
    jr as_obj1_name_bad
as_obj1_name_nul:
    ld a,c
    or a
    jr z,as_obj1_name_bad
as_obj1_name_zero_tail:
    ld a,(hl)
    or a
    jr nz,as_obj1_name_bad
    inc hl
    djnz as_obj1_name_zero_tail
    pop hl
    or a
    ret
as_obj1_name_bad:
    pop hl
    ld a,E_FORMAT
    scf
    ret

as_obj1_name_first_char:
    cp 'A'
    jr c,as_obj1_name_first_punct
    cp 'Z'+1
    jr c,as_obj1_name_char_ok
    cp 'a'
    jr c,as_obj1_name_first_punct
    cp 'z'+1
    jr c,as_obj1_name_char_ok
as_obj1_name_first_punct:
    cp '_'
    jr z,as_obj1_name_char_ok
    cp '.'
    jr z,as_obj1_name_char_ok
    cp '$'
    jr z,as_obj1_name_char_ok
    scf
    ret
as_obj1_name_next_char:
    cp '0'
    jr c,as_obj1_name_first_char
    cp '9'+1
    jr c,as_obj1_name_char_ok
    jp as_obj1_name_first_char
as_obj1_name_char_ok:
    or a
    ret

as_obj1_record_tmp:      dw 0
as_obj1_text_size_tmp:   dw 0
as_obj1_bss_size_tmp:    dw 0
as_obj1_value_tmp:       dw 0
as_obj1_section_tmp:     db 0
as_obj1_flags_tmp:       db 0
    ENDM


; P10.03 OBJ1 relocation record contract.
    MACRO EMIT_P10_AS_OBJ1_RELOC_ROUTINES
AS_OBJ1_RELOC_SIZE       EQU 6
AS_OBJ1_RELOC_OFFSET     EQU 0
AS_OBJ1_RELOC_SYMBOL     EQU 2
AS_OBJ1_RELOC_TYPE       EQU 4
AS_OBJ1_RELOC_RESERVED   EQU 5
AS_OBJ1_RELOC_ABS16      EQU 1

; HL -> relocation record, DE=text_size, BC=symbol_count.
; IX optionally points to previous relocation offset u16; IX=0 means first.
; Structural range/order checks only. Final symbol+signed-addend arithmetic is
; rechecked by the linker before narrowing.
as_obj1_reloc_validate:
    ld (as_obj1_reloc_record_tmp),hl
    ld (as_obj1_reloc_text_tmp),de
    ld (as_obj1_reloc_symbols_tmp),bc

    ld de,AS_OBJ1_RELOC_TYPE
    add hl,de
    ld a,(hl)
    cp AS_OBJ1_RELOC_ABS16
    jr nz,as_obj1_reloc_invalid
    inc hl
    ld a,(hl)
    or a
    jr nz,as_obj1_reloc_invalid

    ld hl,(as_obj1_reloc_record_tmp)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (as_obj1_reloc_offset_tmp),de

    ld hl,(as_obj1_reloc_text_tmp)
    ld a,h
    or a
    jr nz,as_obj1_reloc_text_room
    ld a,l
    cp 2
    jr c,as_obj1_reloc_invalid
as_obj1_reloc_text_room:
    dec hl
    dec hl
    or a
    sbc hl,de
    jr c,as_obj1_reloc_invalid

    ld hl,(as_obj1_reloc_record_tmp)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(as_obj1_reloc_symbols_tmp)
    or a
    sbc hl,de
    jr z,as_obj1_reloc_invalid
    jr c,as_obj1_reloc_invalid

    push ix
    pop hl
    ld a,h
    or l
    jr z,as_obj1_reloc_valid
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc de
    inc de
    ld hl,(as_obj1_reloc_offset_tmp)
    or a
    sbc hl,de
    jr c,as_obj1_reloc_invalid

as_obj1_reloc_valid:
    xor a
    ret

as_obj1_reloc_invalid:
    ld a,E_FORMAT
    scf
    ret

as_obj1_reloc_record_tmp:  dw 0
as_obj1_reloc_text_tmp:    dw 0
as_obj1_reloc_symbols_tmp: dw 0
as_obj1_reloc_offset_tmp:  dw 0
    ENDM


; P10.05 native assembler lexer/line parser.
    MACRO EMIT_P10_AS_LEXER_ROUTINES
; HL -> NUL-terminated source line.
; Carry clear: lexically acceptable line prefix/operand tail for later stages.
; Carry set, A=E_FORMAT: malformed token or forbidden INCLUDE directive.
as_p1005_parse_line:
    call as_p1005_skip_ws
    ld a,(hl)
    or a
    ret z
    cp ';'
    ret z
    ld (as_p1005_token_start),hl
    call as_p1005_first_char
    jp c,as_p1005_bad
    ld b,0
as_p1005_token_loop:
    inc b
    inc hl
    ld a,(hl)
    or a
    jr z,as_p1005_token_end
    cp ':'
    jr z,as_p1005_label
    cp ' '
    jr z,as_p1005_token_end
    cp 9
    jr z,as_p1005_token_end
    cp ';'
    jr z,as_p1005_token_end
    call as_p1005_next_char
    jr nc,as_p1005_token_loop
    jp as_p1005_bad

as_p1005_label:
    inc hl
    call as_p1005_skip_ws
    ld a,(hl)
    or a
    ret z
    cp ';'
    ret z
    ld (as_p1005_token_start),hl
    call as_p1005_first_char
    jp c,as_p1005_bad
    ld b,0
as_p1005_mnemonic_loop:
    inc b
    inc hl
    ld a,(hl)
    or a
    jr z,as_p1005_token_end
    cp ' '
    jr z,as_p1005_token_end
    cp 9
    jr z,as_p1005_token_end
    cp ';'
    jr z,as_p1005_token_end
    call as_p1005_next_char
    jr nc,as_p1005_mnemonic_loop
    jp as_p1005_bad

as_p1005_token_end:
    push hl
    push bc
    call as_p1005_is_include
    pop bc
    pop hl
    jp c,as_p1005_bad
    ; Operand grammar is frozen by later directive/expression/opcode steps.
    ; P10.05 only requires the line/token boundary to be deterministic.
    xor a
    ret

as_p1005_skip_ws:
    ld a,(hl)
    cp ' '
    jr z,as_p1005_skip_one
    cp 9
    ret nz
as_p1005_skip_one:
    inc hl
    jr as_p1005_skip_ws

as_p1005_first_char:
    cp 'A'
    jr c,as_p1005_first_punct
    cp 'Z'+1
    jr c,as_p1005_char_ok
    cp 'a'
    jr c,as_p1005_first_punct
    cp 'z'+1
    jr c,as_p1005_char_ok
as_p1005_first_punct:
    cp '_'
    jr z,as_p1005_char_ok
    cp '.'
    jr z,as_p1005_char_ok
    cp '$'
    jr z,as_p1005_char_ok
    scf
    ret
as_p1005_next_char:
    cp '0'
    jr c,as_p1005_first_char
    cp '9'+1
    jr c,as_p1005_char_ok
    jp as_p1005_first_char
as_p1005_char_ok:
    or a
    ret

; B=token length, saved start pointer. Reject INCLUDE case-insensitively.
as_p1005_is_include:
    ld a,b
    cp 7
    ret nz
    ld hl,(as_p1005_token_start)
    ld de,as_p1005_include_word
    ld b,7
as_p1005_include_loop:
    ld a,(de)
    ld c,a
    ld a,(hl)
    or $20
    cp c
    ret nz
    inc hl
    inc de
    djnz as_p1005_include_loop
    scf
    ret

as_p1005_bad:
    ld a,E_FORMAT
    scf
    ret

as_p1005_include_word: db 'include'
as_p1005_token_start: dw 0
    ENDM
