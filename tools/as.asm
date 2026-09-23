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


; P10.09 global/export and extern/import OBJ1 binding records.
    MACRO EMIT_P10_AS_BINDING_ROUTINES
AS_P1009_MAX_BINDINGS EQU 8
AS_P1009_RECORD_SIZE  EQU 20
AS_P1009_UNDEF        EQU 0
AS_P1009_TEXT         EQU 1
AS_P1009_BSS          EQU 2
AS_P1009_ABS          EQU 3
AS_P1009_GLOBAL       EQU 1

as_p1009_reset:
    xor a
    ld (as_p1009_count),a
    ret

; HL=name, DE=value, A=section. Adds a defined GLOBAL export.
as_p1009_export:
    cp AS_P1009_TEXT
    jr z,as_p1009_add_common
    cp AS_P1009_BSS
    jr z,as_p1009_add_common
    cp AS_P1009_ABS
    jp nz,as_p1009_error
as_p1009_add_common:
    ld (as_p1009_section_arg),a
    ld (as_p1009_name_arg),hl
    ld (as_p1009_value_arg),de
    jp as_p1009_add

; HL=name. Adds an undefined GLOBAL import with value zero.
as_p1009_import:
    xor a
    ld (as_p1009_section_arg),a
    ld (as_p1009_value_arg),a
    ld (as_p1009_value_arg+1),a
    ld (as_p1009_name_arg),hl

as_p1009_add:
    ld a,(as_p1009_count)
    cp AS_P1009_MAX_BINDINGS
    jp nc,as_p1009_error
    ld b,a
    ld ix,as_p1009_table
as_p1009_dup_scan:
    ld a,b
    or a
    jr z,as_p1009_store
    push bc
    push ix
    ld hl,(as_p1009_name_arg)
    push ix
    pop de
    call as_p1009_name_equal
    pop ix
    pop bc
    jp z,as_p1009_error
    ld de,AS_P1009_RECORD_SIZE
    add ix,de
    djnz as_p1009_dup_scan

as_p1009_store:
    ld hl,(as_p1009_name_arg)
    push ix
    pop de
    ld b,16
as_p1009_copy:
    ld a,(hl)
    ld (de),a
    inc de
    inc hl
    or a
    jr z,as_p1009_pad
    djnz as_p1009_copy
    jp as_p1009_error
as_p1009_pad:
    dec b
    jr z,as_p1009_fields
    xor a
as_p1009_pad_loop:
    ld (de),a
    inc de
    djnz as_p1009_pad_loop
as_p1009_fields:
    ld hl,(as_p1009_value_arg)
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    inc de
    ld a,(as_p1009_section_arg)
    ld (de),a
    inc de
    ld a,AS_P1009_GLOBAL
    ld (de),a
    ld a,(as_p1009_count)
    inc a
    ld (as_p1009_count),a
    xor a
    ret

; HL=name. Carry clear, IX=matching binding record. Carry set if absent.
as_p1009_find:
    ld (as_p1009_name_arg),hl
    ld a,(as_p1009_count)
    ld b,a
    ld ix,as_p1009_table
as_p1009_find_loop:
    ld a,b
    or a
    jr z,as_p1009_error
    push bc
    push ix
    ld hl,(as_p1009_name_arg)
    push ix
    pop de
    call as_p1009_name_equal
    pop ix
    pop bc
    jr z,as_p1009_found
    ld de,AS_P1009_RECORD_SIZE
    add ix,de
    djnz as_p1009_find_loop
    jp as_p1009_error
as_p1009_found:
    xor a
    ret

as_p1009_name_equal:
as_p1009_name_equal_loop:
    ld a,(de)
    cp (hl)
    ret nz
    or a
    ret z
    inc hl
    inc de
    jr as_p1009_name_equal_loop

as_p1009_error:
    ld a,E_FORMAT
    scf
    ret

as_p1009_count:       db 0
as_p1009_name_arg:    dw 0
as_p1009_value_arg:   dw 0
as_p1009_section_arg: db 0
as_p1009_table: defs AS_P1009_MAX_BINDINGS*AS_P1009_RECORD_SIZE,0
    ENDM


; P10.10 required-opcode/addressing coverage authority.
; The exact portable documented-Z80 inventory is frozen in
; v1/tests/compiler/as-opcode-inventory. SLL and undocumented indexed-result
; aliases are deliberately outside the portable baseline.


; P10.11 documented load/store encoder primitives.
; Register codes follow the Z80 opcode fields: B,C,D,E,H,L,(HL),A = 0..7.
; Pair codes: BC,DE,HL,SP = 0..3. Index selector: IX=0, IY=1.
    MACRO EMIT_P10_AS_LD_ENCODER
AS_P1011_REG_MEM EQU 6
AS_P1011_REG_A   EQU 7
AS_P1011_PAIR_SP EQU 3
AS_P1011_IX      EQU 0
AS_P1011_IY      EQU 1

; B=destination r field, C=source r field. A=opcode.
as_p1011_ld_r_r:
    ld a,b
    cp 8
    jp nc,as_p1011_error
    ld a,c
    cp 8
    jp nc,as_p1011_error
    ld a,b
    add a,a
    add a,a
    add a,a
    or c
    or $40
    cp $76
    jp z,as_p1011_error
    or a
    ret

; B=destination r field. A=opcode for LD r,n.
as_p1011_ld_r_n:
    ld a,b
    cp 8
    jp nc,as_p1011_error
    add a,a
    add a,a
    add a,a
    or $06
    or a
    ret

; B=rr field 0..3. A=opcode for LD rr,nn.
as_p1011_ld_rr_nn:
    ld a,b
    cp 4
    jp nc,as_p1011_error
    rlca
    rlca
    rlca
    rlca
    or $01
    or a
    ret

; B=rr field. C=0 means LD rr,(nn), C=1 means LD (nn),rr.
; HL returns prefix/opcode: H=0 for unprefixed HL pair, otherwise H=$ED.
as_p1011_ld_rr_mem:
    ld a,b
    cp 4
    jp nc,as_p1011_error
    ld a,c
    cp 2
    jp nc,as_p1011_error
    ld a,b
    cp 2
    jr nz,as_p1011_ld_rr_mem_ed
    ld h,0
    ld a,c
    or a
    ld l,$2A
    ret z
    ld l,$22
    ret
as_p1011_ld_rr_mem_ed:
    ld h,$ED
    ld a,b
    rlca
    rlca
    rlca
    rlca
    add a,$43
    ld l,a
    ld a,c
    or a
    ret nz
    ld a,l
    add a,8
    ld l,a
    xor a
    ret

; D=index selector 0 IX/1 IY, B=register, C=0 load r,(idx+d),
; C=1 store (idx+d),r. Returns H=prefix, L=opcode.
as_p1011_ld_index_r:
    ld a,d
    cp 2
    jp nc,as_p1011_error
    ld h,$DD
    or a
    jr z,as_p1011_index_prefix_done
    ld h,$FD
as_p1011_index_prefix_done:
    ld a,b
    cp 8
    jp nc,as_p1011_error
    cp AS_P1011_REG_MEM
    jp z,as_p1011_error
    ld a,c
    cp 2
    jp nc,as_p1011_error
    or a
    jr nz,as_p1011_index_store
    ld a,b
    add a,a
    add a,a
    add a,a
    or $46
    ld l,a
    xor a
    ret
as_p1011_index_store:
    ld a,b
    or $70
    ld l,a
    xor a
    ret

; A=index selector 0 IX/1 IY. Returns H=prefix, L=$21 for LD IX/IY,nn.
as_p1011_ld_index_nn:
    cp 2
    jp nc,as_p1011_error
    ld h,$DD
    or a
    jr z,as_p1011_index_nn_done
    ld h,$FD
as_p1011_index_nn_done:
    ld l,$21
    xor a
    ret

; A=index selector. Returns H=prefix,L=$F9 for LD SP,IX/IY.
as_p1011_ld_sp_index:
    cp 2
    jp nc,as_p1011_error
    ld h,$DD
    or a
    jr z,as_p1011_sp_index_done
    ld h,$FD
as_p1011_sp_index_done:
    ld l,$F9
    xor a
    ret

; HL=parsed displacement. Accept exact mathematical -128..127 represented as
; 16-bit two's complement; A receives encoded displacement byte.
as_p1011_disp8:
    ld a,h
    or a
    jr z,as_p1011_disp_positive
    cp $FF
    jp nz,as_p1011_error
    ld a,l
    cp $80
    jp c,as_p1011_error
    or a
    ret
as_p1011_disp_positive:
    ld a,l
    cp $80
    jp nc,as_p1011_error
    or a
    ret

; HL=parsed 8-bit immediate. A receives byte.
as_p1011_imm8:
    ld a,h
    or a
    jp nz,as_p1011_error
    ld a,l
    or a
    ret

; Fixed documented load/store encodings used by the parser dispatcher.
; Each row is prefix, opcode; prefix 0 means one-byte opcode before operands.
as_p1011_fixed:
    db 0,$0A      ; ld a,(bc)
    db 0,$1A      ; ld a,(de)
    db 0,$02      ; ld (bc),a
    db 0,$12      ; ld (de),a
    db 0,$3A      ; ld a,(nn)
    db 0,$32      ; ld (nn),a
    db 0,$2A      ; ld hl,(nn)
    db 0,$22      ; ld (nn),hl
    db 0,$F9      ; ld sp,hl
    db $ED,$57    ; ld a,i
    db $ED,$5F    ; ld a,r
    db $ED,$47    ; ld i,a
    db $ED,$4F    ; ld r,a
as_p1011_fixed_end:

; BC -> six-byte relocation record, HL=TEXT word offset, DE=symbol index.
; Used by symbolic absolute LD operands that are not assembly-time absolute.
as_p1011_abs16_reloc:
    ld a,l
    ld (bc),a
    inc bc
    ld a,h
    ld (bc),a
    inc bc
    ld a,e
    ld (bc),a
    inc bc
    ld a,d
    ld (bc),a
    inc bc
    ld a,AS_P1013_RELOC_ABS16
    ld (bc),a
    inc bc
    xor a
    ld (bc),a
    ret

as_p1011_error:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P10.12 documented arithmetic/logical encoder primitives.
    MACRO EMIT_P10_AS_ALU_ENCODER
; A=family 0..7 for ADD,ADC,SUB,SBC,AND,XOR,OR,CP; B=register field.
; Returns A=opcode, carry clear.
as_p1012_alu_r:
    cp 8
    jp nc,as_p1012_error
    ld c,a
    ld a,b
    cp 8
    jp nc,as_p1012_error
    ld a,c
    add a,a
    add a,a
    add a,a
    add a,$80
    or b
    or a
    ret

; A=family 0..7; returns immediate opcode.
as_p1012_alu_n:
    cp 8
    jp nc,as_p1012_error
    ld hl,as_p1012_imm_table
    ld e,a
    ld d,0
    add hl,de
    ld a,(hl)
    or a
    ret

; B=register field, C=0 INC / 1 DEC.
as_p1012_incdec_r:
    ld a,b
    cp 8
    jp nc,as_p1012_error
    add a,a
    add a,a
    add a,a
    add a,$04
    ld b,a
    ld a,c
    cp 2
    jp nc,as_p1012_error
    or a
    ld a,b
    ret z
    inc a
    or a
    ret

; B=pair field 0..3, C=0 INC / 1 DEC.
as_p1012_incdec_rr:
    ld a,b
    cp 4
    jp nc,as_p1012_error
    rlca
    rlca
    rlca
    rlca
    add a,$03
    ld b,a
    ld a,c
    cp 2
    jp nc,as_p1012_error
    or a
    ld a,b
    ret z
    add a,8
    or a
    ret

; B=rr 0..3. Returns A=ADD HL,rr opcode.
as_p1012_add_hl_rr:
    ld a,b
    cp 4
    jp nc,as_p1012_error
    rlca
    rlca
    rlca
    rlca
    add a,$09
    or a
    ret

; B=rr 0..3, C=0 ADC HL,rr / 1 SBC HL,rr. Returns H=$ED,L=opcode.
as_p1012_adc_sbc_hl_rr:
    ld a,b
    cp 4
    jp nc,as_p1012_error
    rlca
    rlca
    rlca
    rlca
    ld l,a
    ld a,c
    cp 2
    jp nc,as_p1012_error
    or a
    ld a,l
    jr nz,as_p1012_sbc_hl
    add a,$4A
    jr as_p1012_ed_done
as_p1012_sbc_hl:
    add a,$42
as_p1012_ed_done:
    ld l,a
    ld h,$ED
    xor a
    ret

; A=0 IX / 1 IY, B=pair field 0..3. Returns H=prefix,L=ADD idx,rr opcode.
as_p1012_add_index_rr:
    cp 2
    jp nc,as_p1012_error
    ld h,$DD
    or a
    jr z,as_p1012_add_index_prefix
    ld h,$FD
as_p1012_add_index_prefix:
    ld a,b
    cp 4
    jp nc,as_p1012_error
    rlca
    rlca
    rlca
    rlca
    add a,$09
    ld l,a
    xor a
    ret

as_p1012_imm_table:
    db $C6,$CE,$D6,$DE,$E6,$EE,$F6,$FE
as_p1012_fixed:
    db $ED,$44      ; NEG
    db 0,$27        ; DAA
    db 0,$2F        ; CPL
    db 0,$3F        ; CCF
    db 0,$37        ; SCF
as_p1012_fixed_end:

as_p1012_error:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P10.13 documented control-flow encoder primitives.
; Condition code order is NZ,Z,NC,C,PO,PE,P,M = 0..7.
    MACRO EMIT_P10_AS_CONTROL_ENCODER
AS_P1013_UNCOND EQU $FF
AS_P1013_RELOC_ABS16 EQU 1

; A=0 JP / 1 CALL, B=condition 0..7 or $FF for unconditional.
; Returns A=opcode, carry clear.
as_p1013_abs:
    cp 2
    jp nc,as_p1013_error
    ld c,a
    ld a,b
    cp AS_P1013_UNCOND
    jr z,as_p1013_abs_uncond
    cp 8
    jp nc,as_p1013_error
    add a,a
    add a,a
    add a,a
    ld b,a
    ld a,c
    or a
    ld a,b
    jr nz,as_p1013_abs_call
    add a,$C2
    or a
    ret
as_p1013_abs_call:
    add a,$C4
    or a
    ret
as_p1013_abs_uncond:
    ld a,c
    or a
    ld a,$C3
    ret z
    ld a,$CD
    or a
    ret

; B=condition 0..7 or $FF. Returns RET opcode.
as_p1013_ret:
    ld a,b
    cp AS_P1013_UNCOND
    jr z,as_p1013_ret_uncond
    cp 8
    jp nc,as_p1013_error
    add a,a
    add a,a
    add a,a
    add a,$C0
    or a
    ret
as_p1013_ret_uncond:
    ld a,$C9
    or a
    ret

; B=condition 0..3 (NZ,Z,NC,C) or $FF. Returns JR opcode.
as_p1013_jr:
    ld a,b
    cp AS_P1013_UNCOND
    jr z,as_p1013_jr_uncond
    cp 4
    jp nc,as_p1013_error
    add a,a
    add a,a
    add a,a
    add a,$20
    or a
    ret
as_p1013_jr_uncond:
    ld a,$18
    or a
    ret

; HL=target, DE=address immediately following the relative instruction.
; Returns A=signed displacement byte only for exact mathematical -128..127.
as_p1013_rel8:
    or a
    sbc hl,de
    ld a,h
    or a
    jr z,as_p1013_rel_pos
    cp $FF
    jp nz,as_p1013_error
    ld a,l
    cp $80
    jp c,as_p1013_error
    or a
    ret
as_p1013_rel_pos:
    ld a,l
    cp $80
    jp nc,as_p1013_error
    or a
    ret

; A=0 for an in-module resolved target. Any unresolved/external relative target
; is illegal because OBJ1 has no relative relocation type.
as_p1013_require_local:
    or a
    ret z
    jp as_p1013_error

; A=RST vector. Only documented 00h,08h,...,38h are legal.
as_p1013_rst:
    cp $39
    jp nc,as_p1013_error
    ld b,a
    and 7
    jp nz,as_p1013_error
    ld a,b
    or $C7
    ret

; A=0 HL / 1 IX / 2 IY. Returns H=prefix (0/DD/FD), L=E9.
as_p1013_jp_indirect:
    cp 3
    jp nc,as_p1013_error
    ld h,0
    or a
    jr z,as_p1013_jp_indirect_done
    ld h,$DD
    cp 1
    jr z,as_p1013_jp_indirect_done
    ld h,$FD
as_p1013_jp_indirect_done:
    ld l,$E9
    xor a
    ret

; Fixed relative DJNZ opcode.
as_p1013_djnz:
    ld a,$10
    or a
    ret

; BC -> six-byte OBJ1 ABS16 relocation, HL=TEXT word offset, DE=symbol index.
; JP/CALL unresolved absolute operands use this exact record.
as_p1013_abs16_reloc:
    ld a,l
    ld (bc),a
    inc bc
    ld a,h
    ld (bc),a
    inc bc
    ld a,e
    ld (bc),a
    inc bc
    ld a,d
    ld (bc),a
    inc bc
    ld a,AS_P1013_RELOC_ABS16
    ld (bc),a
    inc bc
    xor a
    ld (bc),a
    ret

as_p1013_error:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P10.14 documented rotate/shift/bit encoder primitives.
; Portable baseline deliberately omits undocumented SLL and indexed-result aliases.
    MACRO EMIT_P10_AS_BIT_ENCODER
; A=logical rotate/shift family 0 RLC,1 RRC,2 RL,3 RR,4 SLA,5 SRA,6 SRL.
; B=register field B,C,D,E,H,L,(HL),A = 0..7. Returns H=$CB,L=opcode.
as_p1014_cb_shift:
    cp 7
    jp nc,as_p1014_error
    ld hl,as_p1014_shift_bases
    ld e,a
    ld d,0
    add hl,de
    ld a,(hl)
    ld l,a
    ld a,b
    cp 8
    jp nc,as_p1014_error
    or l
    ld l,a
    ld h,$CB
    xor a
    ret

; A=0 BIT / 1 RES / 2 SET, B=bit 0..7, C=register field 0..7.
; Returns H=$CB,L=opcode.
as_p1014_bitop:
    cp 3
    jp nc,as_p1014_error
    ld e,a
    ld a,b
    cp 8
    jp nc,as_p1014_error
    add a,a
    add a,a
    add a,a
    ld l,a
    ld a,e
    or a
    jr z,as_p1014_bit_base
    cp 1
    jr z,as_p1014_res_base
    ld a,l
    add a,$C0
    jr as_p1014_bit_reg
as_p1014_res_base:
    ld a,l
    add a,$80
    jr as_p1014_bit_reg
as_p1014_bit_base:
    ld a,l
    add a,$40
as_p1014_bit_reg:
    ld l,a
    ld a,c
    cp 8
    jp nc,as_p1014_error
    or l
    ld l,a
    ld h,$CB
    xor a
    ret

; D=index selector 0 IX/1 IY. A=0 BIT/1 RES/2 SET, B=bit.
; Returns H=DD/FD, L=CB-family memory opcode (register field fixed at 6).
as_p1014_index_bitop:
    ld c,a
    ld a,d
    cp 2
    jp nc,as_p1014_error
    ld h,$DD
    or a
    jr z,as_p1014_index_bit_prefix
    ld h,$FD
as_p1014_index_bit_prefix:
    ld a,c
    cp 3
    jp nc,as_p1014_error
    ld e,a
    ld a,b
    cp 8
    jp nc,as_p1014_error
    add a,a
    add a,a
    add a,a
    add a,6
    ld l,a
    ld a,e
    or a
    jr z,as_p1014_index_bit
    cp 1
    jr z,as_p1014_index_res
    ld a,l
    add a,$C0
    ld l,a
    xor a
    ret
as_p1014_index_res:
    ld a,l
    add a,$80
    ld l,a
    xor a
    ret
as_p1014_index_bit:
    ld a,l
    add a,$40
    ld l,a
    xor a
    ret

; D=index selector 0 IX/1 IY. Documented indexed RL memory form only.
; Returns H=DD/FD,L=$16. The final encoded stream is prefix,CB,d,opcode.
as_p1014_index_rl:
    ld a,d
    cp 2
    jp nc,as_p1014_error
    ld h,$DD
    or a
    jr z,as_p1014_index_rl_done
    ld h,$FD
as_p1014_index_rl_done:
    ld l,$16
    xor a
    ret

; HL=parsed displacement. Accept only exact -128..127.
as_p1014_disp8:
    ld a,h
    or a
    jr z,as_p1014_disp_pos
    cp $FF
    jp nz,as_p1014_error
    ld a,l
    cp $80
    jp c,as_p1014_error
    or a
    ret
as_p1014_disp_pos:
    ld a,l
    cp $80
    jp nc,as_p1014_error
    or a
    ret

; A=$30 identifies the undocumented CB SLL family and must fail.
as_p1014_reject_undocumented:
    cp $30
    jp z,as_p1014_error
    jp as_p1014_error

as_p1014_shift_bases:
    db $00,$08,$10,$18,$20,$28,$38
as_p1014_fixed:
    db $07,$0F,$17,$1F      ; RLCA,RRCA,RLA,RRA
as_p1014_fixed_end:

as_p1014_error:
    ld a,E_FORMAT
    scf
    ret
    ENDM
