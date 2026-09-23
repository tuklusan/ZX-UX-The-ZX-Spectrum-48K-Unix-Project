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
    jr z,as_p1005_include_compare
    or a
    ret
as_p1005_include_compare:
    ld hl,(as_p1005_token_start)
    ld de,as_p1005_include_word
    ld b,7
as_p1005_include_loop:
    ld a,(de)
    ld c,a
    ld a,(hl)
    or $20
    cp c
    jr z,as_p1005_include_match
    or a
    ret
as_p1005_include_match:
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


; P10.06 case-sensitive symbols and EQU binding.
    MACRO EMIT_P10_AS_SYMBOL_ROUTINES
AS_P1006_MAX_SYMBOLS     EQU 8
AS_P1006_RECORD_SIZE     EQU 18

as_p1006_reset:
    xor a
    ld (as_p1006_count),a
    ret

; HL -> NUL name, DE=value. Carry set on malformed/duplicate/full.
as_p1006_define:
    ld (as_p1006_name_arg),hl
    ld (as_p1006_value_arg),de
    call as_p1006_validate_name
    jp c,as_p1006_error
    ld a,(as_p1006_count)
    ld b,a
    ld ix,as_p1006_table
as_p1006_dup_loop:
    ld a,b
    or a
    jr z,as_p1006_store
    push bc
    push ix
    ld hl,(as_p1006_name_arg)
    push ix
    pop de
    call as_p1006_name_equal
    pop ix
    pop bc
    jp z,as_p1006_error
    ld de,AS_P1006_RECORD_SIZE
    add ix,de
    djnz as_p1006_dup_loop
as_p1006_store:
    ld a,(as_p1006_count)
    cp AS_P1006_MAX_SYMBOLS
    jp nc,as_p1006_error
    ld hl,(as_p1006_name_arg)
    push ix
    pop de
    ld b,16
as_p1006_copy_name:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jr z,as_p1006_zero_tail
    djnz as_p1006_copy_name
    jp as_p1006_error
as_p1006_zero_tail:
    dec b
    jr z,as_p1006_store_value
    xor a
as_p1006_zero_loop:
    ld (de),a
    inc de
    djnz as_p1006_zero_loop
as_p1006_store_value:
    ld hl,(as_p1006_value_arg)
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    ld a,(as_p1006_count)
    inc a
    ld (as_p1006_count),a
    xor a
    ret

; HL -> name. Carry clear + DE=value on exact case-sensitive match.
as_p1006_lookup:
    ld (as_p1006_name_arg),hl
    ld a,(as_p1006_count)
    ld b,a
    ld ix,as_p1006_table
as_p1006_lookup_loop:
    ld a,b
    or a
    jr z,as_p1006_not_found
    push bc
    push ix
    ld hl,(as_p1006_name_arg)
    push ix
    pop de
    call as_p1006_name_equal
    pop ix
    pop bc
    jr z,as_p1006_lookup_hit
    ld de,AS_P1006_RECORD_SIZE
    add ix,de
    djnz as_p1006_lookup_loop
as_p1006_not_found:
    ld a,E_FORMAT
    scf
    ret
as_p1006_lookup_hit:
    push ix
    pop hl
    ld de,16
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    xor a
    ret

; HL/DE NUL names. Z on exact byte-for-byte match; NZ otherwise.
as_p1006_name_equal:
as_p1006_name_equal_loop:
    ld a,(de)
    cp (hl)
    ret nz
    or a
    ret z
    inc hl
    inc de
    jr as_p1006_name_equal_loop

as_p1006_validate_name:
    ld hl,(as_p1006_name_arg)
    ld b,0
    ld a,(hl)
    call as_p1005_first_char
    ret c
as_p1006_validate_loop:
    inc b
    ld a,b
    cp 16
    jp nc,as_p1006_error
    inc hl
    ld a,(hl)
    or a
    ret z
    call as_p1005_next_char
    jr nc,as_p1006_validate_loop
as_p1006_error:
    ld a,E_FORMAT
    scf
    ret

as_p1006_count: db 0
as_p1006_name_arg: dw 0
as_p1006_value_arg: dw 0
as_p1006_table: defs AS_P1006_MAX_SYMBOLS*AS_P1006_RECORD_SIZE,0
    ENDM


; P10.07 DB/DW/DS directive emission primitives.
    MACRO EMIT_P10_AS_DIRECTIVE_ROUTINES
AS_P1007_BUFFER_LIMIT    EQU 32768

as_p1007_reset:
    ld (as_p1007_base),hl
    ld (as_p1007_cursor),hl
    ld (as_p1007_limit),de
    xor a
    ret

; A=byte. Transactionally append one DB byte.
as_p1007_db:
    push af
    call as_p1007_reserve_one
    jr c,as_p1007_db_fail
    pop af
    ld hl,(as_p1007_cursor)
    ld (hl),a
    inc hl
    ld (as_p1007_cursor),hl
    xor a
    ret
as_p1007_db_fail:
    pop af
    ld a,E_FORMAT
    scf
    ret

; DE=word. Append little-endian DW.
as_p1007_dw:
    push de
    ld bc,2
    call as_p1007_reserve
    jr c,as_p1007_dw_fail
    pop de
    ld hl,(as_p1007_cursor)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld (as_p1007_cursor),hl
    xor a
    ret
as_p1007_dw_fail:
    pop de
    ld a,E_FORMAT
    scf
    ret

; BC=count. Reserve DS bytes, deterministically zero-filled.
as_p1007_ds:
    push bc
    call as_p1007_reserve
    jr c,as_p1007_ds_fail
    pop bc
    ld hl,(as_p1007_cursor)
    ld a,b
    or c
    jr z,as_p1007_ds_done
as_p1007_ds_loop:
    xor a
    ld (hl),a
    inc hl
    dec bc
    ld a,b
    or c
    jr nz,as_p1007_ds_loop
as_p1007_ds_done:
    ld (as_p1007_cursor),hl
    xor a
    ret
as_p1007_ds_fail:
    pop bc
    ld a,E_FORMAT
    scf
    ret

as_p1007_reserve_one:
    ld bc,1
as_p1007_reserve:
    ld hl,(as_p1007_cursor)
    push hl
    add hl,bc
    jr c,as_p1007_reserve_fail_pop
    ld de,(as_p1007_limit)
    or a
    sbc hl,de
    jr c,as_p1007_reserve_ok_pop
    jr z,as_p1007_reserve_ok_pop
as_p1007_reserve_fail_pop:
    pop hl
    ld a,E_FORMAT
    scf
    ret
as_p1007_reserve_ok_pop:
    pop hl
    xor a
    ret

as_p1007_size:
    ld hl,(as_p1007_cursor)
    ld de,(as_p1007_base)
    or a
    sbc hl,de
    ret

as_p1007_base:   dw 0
as_p1007_cursor: dw 0
as_p1007_limit:  dw 0
    ENDM


; P10.08 assembler expression operator core.
; Operator byte: 1 +, 2 -, 3 *, 4 /, 5 %, 6 &, 7 |, 8 ^, 9 <<, 10 >>.
; Inputs: A=operator, HL=lhs, DE=rhs. Output: HL=result, carry clear.
; Divide/modulo by zero or unknown operator returns E_FORMAT with carry set.
    MACRO EMIT_P10_AS_EXPR_ROUTINES
AS_P1008_OP_ADD EQU 1
AS_P1008_OP_SUB EQU 2
AS_P1008_OP_MUL EQU 3
AS_P1008_OP_DIV EQU 4
AS_P1008_OP_MOD EQU 5
AS_P1008_OP_AND EQU 6
AS_P1008_OP_OR  EQU 7
AS_P1008_OP_XOR EQU 8
AS_P1008_OP_SHL EQU 9
AS_P1008_OP_SHR EQU 10

as_p1008_apply:
    cp AS_P1008_OP_ADD
    jp z,as_p1008_add
    cp AS_P1008_OP_SUB
    jp z,as_p1008_sub
    cp AS_P1008_OP_MUL
    jp z,as_p1008_mul
    cp AS_P1008_OP_DIV
    jp z,as_p1008_div
    cp AS_P1008_OP_MOD
    jp z,as_p1008_mod
    cp AS_P1008_OP_AND
    jp z,as_p1008_and
    cp AS_P1008_OP_OR
    jp z,as_p1008_or
    cp AS_P1008_OP_XOR
    jp z,as_p1008_xor
    cp AS_P1008_OP_SHL
    jp z,as_p1008_shl
    cp AS_P1008_OP_SHR
    jp z,as_p1008_shr
    jp as_p1008_error

as_p1008_add:
    add hl,de
    xor a
    ret
as_p1008_sub:
    or a
    sbc hl,de
    xor a
    ret

as_p1008_and:
    ld a,h
    and d
    ld h,a
    ld a,l
    and e
    ld l,a
    xor a
    ret
as_p1008_or:
    ld a,h
    or d
    ld h,a
    ld a,l
    or e
    ld l,a
    xor a
    ret
as_p1008_xor:
    ld a,h
    xor d
    ld h,a
    ld a,l
    xor e
    ld l,a
    xor a
    ret

; 16-bit multiply modulo 65536.
as_p1008_mul:
    push bc
    push af
    push hl
    pop bc
    ld hl,0
    ld a,16
as_p1008_mul_loop:
    bit 0,e
    jr z,as_p1008_mul_skip
    add hl,bc
as_p1008_mul_skip:
    srl d
    rr e
    sla c
    rl b
    dec a
    jr nz,as_p1008_mul_loop
    pop af
    pop bc
    xor a
    ret

; Shared small deterministic unsigned division core.
; HL dividend, DE divisor. Returns HL quotient, BC remainder.
as_p1008_udiv:
    ld a,d
    or e
    jr z,as_p1008_error
    ld bc,0
as_p1008_udiv_loop:
    or a
    sbc hl,de
    jr c,as_p1008_udiv_done
    inc bc
    jr as_p1008_udiv_loop
as_p1008_udiv_done:
    add hl,de
    push hl
    push bc
    pop de
    pop hl
    ; DE=quotient, HL=remainder
    or a
    ret

as_p1008_div:
    call as_p1008_udiv
    ret c
    ex de,hl
    xor a
    ret
as_p1008_mod:
    call as_p1008_udiv
    ret c
    xor a
    ret

as_p1008_shl:
    ld a,e
    and 15
    jr z,as_p1008_shift_done
    ld b,a
as_p1008_shl_loop:
    add hl,hl
    djnz as_p1008_shl_loop
as_p1008_shift_done:
    xor a
    ret

as_p1008_shr:
    ld a,e
    and 15
    jr z,as_p1008_shift_done
    ld b,a
as_p1008_shr_loop:
    srl h
    rr l
    djnz as_p1008_shr_loop
    xor a
    ret

; Unary minus and bitwise complement.
as_p1008_neg:
    xor a
    sub l
    ld l,a
    sbc a,a
    sub h
    ld h,a
    xor a
    ret
as_p1008_not:
    ld a,h
    cpl
    ld h,a
    ld a,l
    cpl
    ld l,a
    xor a
    ret

as_p1008_error:
    ld a,E_FORMAT
    scf
    ret

; Precedence authority consumed by the expression parser:
; | ^ & << >> + - * / % => 1,2,3,4,4,5,5,6,6,6.
as_p1008_precedence:
    db 5,5,6,6,6,3,1,2,4,4
    ENDM
