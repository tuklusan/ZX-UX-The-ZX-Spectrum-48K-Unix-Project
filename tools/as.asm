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
