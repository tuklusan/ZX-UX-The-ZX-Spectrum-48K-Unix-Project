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

; REV17 ordinary textual native assembler path used by the expanded Phase-11
; pre-release proof. It parses the admitted literal-only textual projection
; produced from canonical kernel source, emits through the same semantic Z80
; encoder as the NSP1 proof, and never accepts a preassembled opcode stream.
;
; Interface:
;   HL = exact LF-only source bytes
;   DE = exact source length
; Success:
;   source buffer begins with a genuine no-symbol/no-relocation OBJ1
;   HL = exact OBJ1 length (24 + 8192), carry clear
;
; The in-place entry is validation infrastructure for the 48K proof session:
; pass 1 validates/measures without writes; pass 2 emits only behind the
; already-consumed source cursor, then shifts TEXT by the 24-byte OBJ1 header.
; The public syntax remains the frozen documented P10/REV17 syntax.
    MACRO EMIT_R17_AS_TEXT_OBJ1

R17_TXT_TEXT_SIZE EQU 8192
R17_TXT_OBJ_SIZE  EQU 8216

R17_TXT_OP_REG8    EQU 0
R17_TXT_OP_RR      EQU 1
R17_TXT_OP_INDEX   EQU 2
R17_TXT_OP_MEMABS  EQU 3
R17_TXT_OP_INDEXED EQU 4
R17_TXT_OP_SPECIAL EQU 5
R17_TXT_OP_MEMPAIR EQU 6
R17_TXT_OP_IMM     EQU 7

R17_TXT_M_LD    EQU 1
R17_TXT_M_JP    EQU 2
R17_TXT_M_CALL  EQU 3
R17_TXT_M_JR    EQU 4
R17_TXT_M_DJNZ  EQU 5
R17_TXT_M_RET   EQU 6
R17_TXT_M_INC   EQU 7
R17_TXT_M_DEC   EQU 8
R17_TXT_M_PUSH  EQU 9
R17_TXT_M_POP   EQU 10
R17_TXT_M_EX    EQU 11
R17_TXT_M_IM    EQU 12
R17_TXT_M_IN    EQU 13
R17_TXT_M_OUT   EQU 14
R17_TXT_M_DB    EQU 15
R17_TXT_M_DW    EQU 16
R17_TXT_M_DEFS  EQU 17
R17_TXT_M_ORG   EQU 18
R17_TXT_M_RST   EQU 19

r17_as_text_obj1_inplace:
    ld (r17_txt_source),hl
    ld (r17_txt_source_len),de
    ld a,d
    or e
    jp z,r17_as_error
    ld a,d
    cp $80
    jr c,r17_txt_source_span
    jr nz,r17_as_error
    ld a,e
    or a
    jp nz,r17_as_error
r17_txt_source_span:
    dec de
    add hl,de
    jp c,r17_as_error

    ld a,1
    ld (r17_as_measure_mode),a
    xor a
    ld (r17_as_guard_mode),a
    call r17_txt_pass_init
    call r17_txt_parse_all
    ret c
    call r17_txt_require_text_size
    ret c

    xor a
    ld (r17_as_measure_mode),a
    ld a,1
    ld (r17_as_guard_mode),a
    call r17_txt_pass_init
    call r17_txt_parse_all
    ret c
    call r17_txt_require_text_size
    ret c
    xor a
    ld (r17_as_guard_mode),a

    ld hl,(r17_txt_source)
    ld de,R17_TXT_TEXT_SIZE-1
    add hl,de
    push hl
    ld hl,(r17_txt_source)
    ld de,R17_TXT_OBJ_SIZE-1
    add hl,de
    ex de,hl
    pop hl
    ld bc,R17_TXT_TEXT_SIZE
    lddr

    ld hl,(r17_txt_source)
    ld (r17_as_obj),hl
    ld hl,0
    ld (r17_as_cur),hl
    ld (r17_as_end),hl
    ld hl,R17_TXT_TEXT_SIZE
    ld (r17_as_text_size),hl
    ld (r17_as_produced),hl
    xor a
    ld (r17_as_single_mode),a
    ld (r17_as_measure_mode),a
    ld (r17_as_guard_mode),a
    call r17_as_records_done
    ret c
    ld de,R17_TXT_OBJ_SIZE
    or a
    sbc hl,de
    jp nz,r17_as_error
    ld hl,R17_TXT_OBJ_SIZE
    xor a
    ret

r17_txt_pass_init:
    ld hl,(r17_txt_source)
    ld (r17_txt_cur),hl
    ld de,(r17_txt_source_len)
    add hl,de
    jp c,r17_as_error
    ld (r17_txt_end),hl
    ld hl,(r17_txt_source)
    ld (r17_as_out),hl
    ld (r17_as_obj),hl
    ld hl,R17_TXT_TEXT_SIZE
    ld (r17_as_text_size),hl
    ld hl,0
    ld (r17_as_produced),hl
    ld hl,R17_KERNEL_BASE
    ld (r17_as_pc),hl
    ld a,1
    ld (r17_as_single_mode),a
    xor a
    ld (r17_txt_saw_org),a
    ret

r17_txt_require_text_size:
    ld hl,(r17_as_produced)
    ld de,R17_TXT_TEXT_SIZE
    or a
    sbc hl,de
    ret z
    jp r17_as_error

r17_txt_parse_all:
r17_txt_line_loop:
    ld hl,(r17_txt_cur)
    ld de,(r17_txt_end)
    or a
    sbc hl,de
    jr z,r17_txt_parse_done
    jp nc,r17_as_error
    ld hl,(r17_txt_cur)
    ld (r17_txt_line_start),hl
r17_txt_find_lf:
    ld de,(r17_txt_end)
    push hl
    or a
    sbc hl,de
    pop hl
    jp nc,r17_as_error
    ld a,(hl)
    or a
    jp z,r17_as_error
    cp 13
    jp z,r17_as_error
    cp 10
    jr z,r17_txt_have_line
    inc hl
    jr r17_txt_find_lf
r17_txt_have_line:
    ld de,(r17_txt_line_start)
    push hl
    or a
    sbc hl,de
    pop hl
    jp z,r17_as_error
    ld (r17_txt_line_end),hl
    inc hl
    ld (r17_txt_cur),hl
    ld hl,(r17_txt_line_start)
    ld (r17_txt_p),hl
    call r17_txt_dispatch_line
    ret c
    jr r17_txt_line_loop
r17_txt_parse_done:
    ld a,(r17_txt_saw_org)
    cp 1
    jp nz,r17_as_error
    xor a
    ret

r17_txt_dispatch_line:
    ld hl,r17_txt_mnemonics
r17_txt_mn_next:
    ld a,(hl)
    or a
    jp z,r17_as_error
    ld c,a
    inc hl
    ld (r17_txt_table_name),hl
    ld e,c
    ld d,0
    add hl,de
    ld a,(hl)
    ld (r17_txt_id),a
    inc hl
    ld (r17_txt_table_next),hl

    ld hl,(r17_txt_table_name)
    ld de,(r17_txt_line_start)
    ld b,c
r17_txt_mn_cmp:
    ld a,(de)
    cp (hl)
    jr nz,r17_txt_mn_miss
    inc de
    inc hl
    djnz r17_txt_mn_cmp

    ld hl,(r17_txt_line_end)
    or a
    sbc hl,de
    jr z,r17_txt_mn_no_space
    jr c,r17_txt_mn_miss
    ld a,(de)
    cp ' '
    jr nz,r17_txt_mn_miss
    inc de
r17_txt_mn_no_space:
    ld (r17_txt_p),de
    ld a,(r17_txt_id)
    bit 7,a
    jp nz,r17_txt_fixed
    cp $40
    jr c,r17_txt_structured
    cp $48
    jp c,r17_txt_alu
    cp $50
    jp c,r17_as_error
    cp $57
    jp c,r17_txt_shift
    cp $60
    jp c,r17_as_error
    cp $63
    jp c,r17_txt_bit
    jp r17_as_error

r17_txt_mn_miss:
    ld hl,(r17_txt_table_next)
    jr r17_txt_mn_next

r17_txt_structured:
    dec a
    cp R17_TXT_M_RST
    jp nc,r17_as_error
    add a,a
    ld e,a
    ld d,0
    ld hl,r17_txt_struct_handlers
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    push de
    ret

r17_txt_struct_handlers:
    dw r17_txt_ld,r17_txt_jp,r17_txt_call,r17_txt_jr,r17_txt_djnz
    dw r17_txt_ret,r17_txt_inc,r17_txt_dec,r17_txt_push,r17_txt_pop
    dw r17_txt_ex,r17_txt_im,r17_txt_in,r17_txt_out,r17_txt_db
    dw r17_txt_dw,r17_txt_defs,r17_txt_org,r17_txt_rst

r17_txt_fixed:
    call r17_txt_expect_end
    ret c
    ld a,(r17_txt_id)
    and $7f
    ld (r17_txt_tmp0),a
    ld a,1
    call r17_txt_rec_start
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_alu:
    sub $40
    ld (r17_txt_family),a
    call r17_txt_parse_operand
    ret c
    call r17_txt_save_first
    call r17_txt_peek_comma_or_end
    ret c
    jr z,r17_txt_alu_one
    ld a,','
    call r17_txt_consume
    ret c
    call r17_txt_parse_operand
    ret c
    call r17_txt_expect_end
    ret c

    ld a,(r17_txt_family)
    cp 4
    jp nc,r17_as_error
    ld a,(r17_txt_f_type)
    cp R17_TXT_OP_REG8
    jr nz,r17_txt_alu_pair
    ld a,(r17_txt_f_v0)
    cp 7
    jp nz,r17_as_error
    jp r17_txt_emit_alu_operand
r17_txt_alu_pair:
    cp R17_TXT_OP_RR
    jr nz,r17_txt_alu_index_pair
    ld a,(r17_txt_f_v0)
    cp 2
    jp nz,r17_as_error
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_RR
    jp nz,r17_as_error
    ld a,(r17_txt_family)
    or a
    jr z,r17_txt_add_hl_rr
    cp 1
    jr z,r17_txt_adc_hl_rr
    cp 3
    jp nz,r17_as_error
    ld a,27
    call r17_txt_rec_start
    ld a,1
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_adc_hl_rr:
    ld a,27
    call r17_txt_rec_start
    xor a
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_add_hl_rr:
    ld a,26
    call r17_txt_rec_start
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_alu_index_pair:
    cp R17_TXT_OP_INDEX
    jp nz,r17_as_error
    ld a,(r17_txt_family)
    or a
    jp nz,r17_as_error
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_RR
    jp nz,r17_as_error
    ld a,28
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_alu_one:
    call r17_txt_expect_end
    ret c
    call r17_txt_restore_first_as_op
r17_txt_emit_alu_operand:
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_REG8
    jr z,r17_txt_alu_reg
    cp R17_TXT_OP_IMM
    jr z,r17_txt_alu_imm
    cp R17_TXT_OP_INDEXED
    jp nz,r17_as_error
    ld a,23
    call r17_txt_rec_start
    ld a,(r17_txt_family)
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    ld a,(r17_txt_op_v1)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_alu_reg:
    ld a,21
    call r17_txt_rec_start
    ld a,(r17_txt_family)
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_alu_imm:
    ld a,22
    call r17_txt_rec_start
    ld a,(r17_txt_family)
    call r17_txt_rec8
    ld de,(r17_txt_op_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit

r17_txt_shift:
    sub $50
    ld (r17_txt_family),a
    call r17_txt_parse_operand
    ret c
    call r17_txt_expect_end
    ret c
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_REG8
    jp nz,r17_as_error
    ld a,35
    call r17_txt_rec_start
    ld a,(r17_txt_family)
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_bit:
    sub $60
    ld (r17_txt_family),a
    call r17_txt_parse_num
    ret c
    ld a,d
    or a
    jp nz,r17_as_error
    ld a,e
    cp 8
    jp nc,r17_as_error
    ld (r17_txt_tmp0),a
    ld a,','
    call r17_txt_consume
    ret c
    call r17_txt_parse_operand
    ret c
    call r17_txt_expect_end
    ret c
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_REG8
    jr z,r17_txt_bit_reg
    cp R17_TXT_OP_INDEXED
    jp nz,r17_as_error
    ld a,34
    call r17_txt_rec_start
    ld a,(r17_txt_family)
    call r17_txt_rec8
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    ld a,(r17_txt_op_v1)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_bit_reg:
    ld a,33
    call r17_txt_rec_start
    ld a,(r17_txt_family)
    call r17_txt_rec8
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_ld:
    call r17_txt_parse_operand
    ret c
    call r17_txt_save_first
    ld a,','
    call r17_txt_consume
    ret c
    call r17_txt_parse_operand
    ret c
    call r17_txt_expect_end
    ret c

    ld a,(r17_txt_f_type)
    cp R17_TXT_OP_REG8
    jp z,r17_txt_ld_dst_reg
    cp R17_TXT_OP_RR
    jp z,r17_txt_ld_dst_rr
    cp R17_TXT_OP_INDEX
    jp z,r17_txt_ld_dst_index
    cp R17_TXT_OP_MEMABS
    jp z,r17_txt_ld_dst_memabs
    cp R17_TXT_OP_INDEXED
    jp z,r17_txt_ld_dst_indexed
    cp R17_TXT_OP_SPECIAL
    jp z,r17_txt_ld_dst_special
    cp R17_TXT_OP_MEMPAIR
    jp z,r17_txt_ld_dst_mempair
    jp r17_as_error

r17_txt_ld_dst_reg:
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_REG8
    jr z,r17_txt_ld_rr8
    cp R17_TXT_OP_IMM
    jr z,r17_txt_ld_r_imm
    ld a,(r17_txt_f_v0)
    cp 7
    jp nz,r17_as_error
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_MEMPAIR
    jr z,r17_txt_ld_a_mempair
    cp R17_TXT_OP_SPECIAL
    jr z,r17_txt_ld_a_special
    cp R17_TXT_OP_MEMABS
    jr z,r17_txt_ld_a_memabs
    cp R17_TXT_OP_INDEXED
    jr z,r17_txt_ld_r_indexed
    jp r17_as_error
r17_txt_ld_rr8:
    ld a,2
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_ld_r_imm:
    ld a,3
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    ld de,(r17_txt_op_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit
r17_txt_ld_a_mempair:
    ld a,7
    call r17_txt_rec_start
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_ld_a_special:
    ld a,18
    call r17_txt_rec_start
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_ld_a_memabs:
    ld a,9
    call r17_txt_rec_start
    ld de,(r17_txt_op_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit
r17_txt_ld_r_indexed:
    ld a,19
    call r17_txt_rec_start
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    ld a,(r17_txt_op_v1)
    call r17_txt_rec8
    xor a
    call r17_txt_rec8
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_ld_dst_rr:
    ld a,(r17_txt_f_v0)
    cp 3
    jr nz,r17_txt_ld_rr_general
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_RR
    jr nz,r17_txt_ld_sp_index_check
    ld a,(r17_txt_op_v0)
    cp 2
    jr nz,r17_txt_ld_sp_index_check
    ld a,1
    call r17_txt_rec_start
    ld a,24
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_ld_sp_index_check:
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_INDEX
    jr nz,r17_txt_ld_rr_general
    ld a,17
    call r17_txt_rec_start
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_ld_rr_general:
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_IMM
    jr z,r17_txt_ld_rr_imm
    cp R17_TXT_OP_MEMABS
    jp nz,r17_as_error
    ld a,12
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    ld de,(r17_txt_op_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit
r17_txt_ld_rr_imm:
    ld a,11
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    ld de,(r17_txt_op_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit

r17_txt_ld_dst_index:
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_IMM
    jr z,r17_txt_ld_index_imm
    cp R17_TXT_OP_MEMABS
    jp nz,r17_as_error
    ld a,15
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    ld de,(r17_txt_op_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit
r17_txt_ld_index_imm:
    ld a,14
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    ld de,(r17_txt_op_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit

r17_txt_ld_dst_memabs:
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_REG8
    jr nz,r17_txt_ld_memabs_pair
    ld a,(r17_txt_op_v0)
    cp 7
    jp nz,r17_as_error
    ld a,10
    call r17_txt_rec_start
    ld de,(r17_txt_f_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit
r17_txt_ld_memabs_pair:
    cp R17_TXT_OP_RR
    jr z,r17_txt_ld_memabs_rr
    cp R17_TXT_OP_INDEX
    jp nz,r17_as_error
    ld a,16
    call r17_txt_rec_start
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    ld de,(r17_txt_f_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit
r17_txt_ld_memabs_rr:
    ld a,13
    call r17_txt_rec_start
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    ld de,(r17_txt_f_w)
    call r17_txt_rec16
    jp r17_txt_rec_emit

r17_txt_ld_dst_indexed:
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_REG8
    jr z,r17_txt_ld_indexed_reg
    cp R17_TXT_OP_IMM
    jp nz,r17_as_error
    ld de,(r17_txt_op_w)
    ld a,d
    or a
    jp nz,r17_as_error
    ld a,20
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    ld a,(r17_txt_f_v1)
    call r17_txt_rec8
    ld a,e
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_ld_indexed_reg:
    ld a,19
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    ld a,(r17_txt_f_v1)
    call r17_txt_rec8
    ld a,1
    call r17_txt_rec8
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_ld_dst_special:
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_REG8
    jp nz,r17_as_error
    ld a,(r17_txt_op_v0)
    cp 7
    jp nz,r17_as_error
    ld a,18
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    add a,2
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_ld_dst_mempair:
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_REG8
    jp nz,r17_as_error
    ld a,(r17_txt_op_v0)
    cp 7
    jp nz,r17_as_error
    ld a,8
    call r17_txt_rec_start
    ld a,(r17_txt_f_v0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_jp:
    call r17_txt_try_exact_hl_indirect
    jr c,r17_txt_jp_normal
    call r17_txt_expect_end
    ret c
    ld a,1
    call r17_txt_rec_start
    ld a,23
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_jp_normal:
    xor a
    ld (r17_txt_tmp0),a
    jp r17_txt_parse_abs_control
r17_txt_call:
    ld a,1
    ld (r17_txt_tmp0),a
    jp r17_txt_parse_abs_control

r17_txt_parse_abs_control:
    ld a,$ff
    ld (r17_txt_tmp1),a
    call r17_txt_control_target_or_cond
    ret c
    ld a,29
    call r17_txt_rec_start
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    ld a,(r17_txt_tmp1)
    call r17_txt_rec8
    ld de,(r17_txt_num)
    call r17_txt_rec16
    jp r17_txt_rec_emit

r17_txt_jr:
    ld a,$ff
    ld (r17_txt_tmp1),a
    call r17_txt_control_target_or_cond
    ret c
    ld a,(r17_txt_tmp1)
    cp $ff
    jr z,r17_txt_jr_cond_ok
    cp 4
    jp nc,r17_as_error
r17_txt_jr_cond_ok:
    ld a,30
    call r17_txt_rec_start
    ld a,(r17_txt_tmp1)
    call r17_txt_rec8
    ld de,(r17_txt_num)
    call r17_txt_rec16
    jp r17_txt_rec_emit

r17_txt_control_target_or_cond:
    call r17_txt_peek
    ret c
    cp '$'
    jr z,r17_txt_control_target
    cp '0'
    jr c,r17_txt_control_cond
    cp '9'+1
    jr c,r17_txt_control_target
r17_txt_control_cond:
    call r17_txt_parse_cond
    ret c
    ld (r17_txt_tmp1),a
    ld a,','
    call r17_txt_consume
    ret c
r17_txt_control_target:
    call r17_txt_parse_num
    ret c
    ld (r17_txt_num),de
    jp r17_txt_expect_end

r17_txt_djnz:
    call r17_txt_parse_num
    ret c
    ld (r17_txt_num),de
    call r17_txt_expect_end
    ret c
    ld a,31
    call r17_txt_rec_start
    ld de,(r17_txt_num)
    call r17_txt_rec16
    jp r17_txt_rec_emit

r17_txt_ret:
    ld a,$ff
    ld (r17_txt_tmp0),a
    call r17_txt_is_end
    jr z,r17_txt_ret_emit
    call r17_txt_parse_cond
    ret c
    ld (r17_txt_tmp0),a
    call r17_txt_expect_end
    ret c
r17_txt_ret_emit:
    ld a,32
    call r17_txt_rec_start
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_inc:
    xor a
    ld (r17_txt_tmp0),a
    jr r17_txt_incdec
r17_txt_dec:
    ld a,1
    ld (r17_txt_tmp0),a
r17_txt_incdec:
    call r17_txt_parse_operand
    ret c
    call r17_txt_expect_end
    ret c
    ld a,(r17_txt_op_type)
    cp R17_TXT_OP_REG8
    jr z,r17_txt_incdec_reg
    cp R17_TXT_OP_RR
    jp nz,r17_as_error
    ld a,25
    call r17_txt_rec_start
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_incdec_reg:
    ld a,24
    call r17_txt_rec_start
    ld a,(r17_txt_op_v0)
    call r17_txt_rec8
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_push:
    xor a
    ld (r17_txt_tmp0),a
    jr r17_txt_pushpop
r17_txt_pop:
    ld a,1
    ld (r17_txt_tmp0),a
r17_txt_pushpop:
    call r17_txt_parse_push_pair
    ret c
    ld (r17_txt_tmp1),a
    call r17_txt_expect_end
    ret c
    ld a,36
    call r17_txt_rec_start
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    ld a,(r17_txt_tmp1)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_ex:
    call r17_txt_match_ex_form
    ret c
    ld (r17_txt_tmp0),a
    call r17_txt_expect_end
    ret c
    ld a,37
    call r17_txt_rec_start
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_im:
    call r17_txt_parse_num
    ret c
    ld a,d
    or a
    jp nz,r17_as_error
    ld a,e
    cp 3
    jp nc,r17_as_error
    ld (r17_txt_tmp0),a
    call r17_txt_expect_end
    ret c
    ld a,38
    call r17_txt_rec_start
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_in:
    ld hl,r17_txt_s_a_c
    call r17_txt_match_tail
    ret c
    call r17_txt_expect_end
    ret c
    ld a,39
    call r17_txt_rec_start
    xor a
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_out:
    ld hl,r17_txt_s_c_a
    call r17_txt_match_tail_soft
    jr c,r17_txt_out_imm
    call r17_txt_expect_end
    ret c
    ld a,39
    call r17_txt_rec_start
    ld a,1
    call r17_txt_rec8
    jp r17_txt_rec_emit
r17_txt_out_imm:
    ld a,'('
    call r17_txt_consume
    ret c
    call r17_txt_parse_num
    ret c
    ld a,d
    or a
    jp nz,r17_as_error
    ld a,e
    ld (r17_txt_tmp0),a
    ld a,')'
    call r17_txt_consume
    ret c
    ld a,','
    call r17_txt_consume
    ret c
    ld a,'a'
    call r17_txt_consume
    ret c
    call r17_txt_expect_end
    ret c
    ld a,44
    call r17_txt_rec_start
    ld a,(r17_txt_tmp0)
    call r17_txt_rec8
    jp r17_txt_rec_emit

r17_txt_db:
r17_txt_db_loop:
    call r17_txt_parse_num
    ret c
    ld a,d
    or a
    jp nz,r17_as_error
    ld a,e
    ld (r17_txt_tmp0),a
    ld a,40
    call r17_txt_rec_start
    ld a,(r17_txt_tmp0)
    ld e,a
    ld d,0
    call r17_txt_rec16
    call r17_txt_rec_emit
    ret c
    call r17_txt_peek_comma_or_end
    ret c
    ret z
    ld a,','
    call r17_txt_consume
    ret c
    jr r17_txt_db_loop

r17_txt_dw:
r17_txt_dw_loop:
    call r17_txt_parse_num
    ret c
    ld (r17_txt_num),de
    ld a,41
    call r17_txt_rec_start
    ld de,(r17_txt_num)
    call r17_txt_rec16
    call r17_txt_rec_emit
    ret c
    call r17_txt_peek_comma_or_end
    ret c
    ret z
    ld a,','
    call r17_txt_consume
    ret c
    jr r17_txt_dw_loop

r17_txt_defs:
    call r17_txt_parse_num
    ret c
    ld (r17_txt_num),de
    ld a,','
    call r17_txt_consume
    ret c
    call r17_txt_parse_num
    ret c
    ld (r17_txt_num2),de
    call r17_txt_expect_end
    ret c
    ld a,42
    call r17_txt_rec_start
    ld de,(r17_txt_num)
    call r17_txt_rec16
    ld de,(r17_txt_num2)
    call r17_txt_rec16
    jp r17_txt_rec_emit

r17_txt_org:
    ld a,(r17_txt_saw_org)
    or a
    jp nz,r17_as_error
    ld hl,(r17_as_produced)
    ld a,h
    or l
    jp nz,r17_as_error
    call r17_txt_parse_num
    ret c
    ld hl,R17_KERNEL_BASE
    or a
    sbc hl,de
    jp nz,r17_as_error
    call r17_txt_expect_end
    ret c
    ld a,1
    ld (r17_txt_saw_org),a
    xor a
    ret

r17_txt_rst:
    call r17_txt_parse_num
    ret c
    ld (r17_txt_num),de
    call r17_txt_expect_end
    ret c
    ld a,43
    call r17_txt_rec_start
    ld de,(r17_txt_num)
    call r17_txt_rec16
    jp r17_txt_rec_emit

r17_txt_parse_operand:
    call r17_txt_peek
    ret c
    cp '('
    jp z,r17_txt_parse_paren
    cp '$'
    jr z,r17_txt_operand_imm
    cp '0'
    jr c,r17_txt_operand_word
    cp '9'+1
    jr c,r17_txt_operand_imm
r17_txt_operand_word:
    cp 'a'
    jr z,r17_txt_operand_a
    cp 'b'
    jr z,r17_txt_operand_b
    cp 'c'
    jr z,r17_txt_operand_c
    cp 'd'
    jr z,r17_txt_operand_d
    cp 'e'
    jr z,r17_txt_operand_e
    cp 'h'
    jr z,r17_txt_operand_h
    cp 'l'
    jr z,r17_txt_operand_l
    cp 's'
    jr z,r17_txt_operand_sp
    cp 'i'
    jr z,r17_txt_operand_i
    cp 'r'
    jr z,r17_txt_operand_r
    jp r17_as_error

r17_txt_operand_a:
    ld a,'a'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_REG8
    ld (r17_txt_op_type),a
    ld a,7
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_b:
    ld a,'b'
    call r17_txt_consume
    ret c
    call r17_txt_peek_soft
    cp 'c'
    jr z,r17_txt_operand_bc
    ld a,R17_TXT_OP_REG8
    ld (r17_txt_op_type),a
    xor a
    ld (r17_txt_op_v0),a
    ret
r17_txt_operand_bc:
    ld a,'c'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_RR
    ld (r17_txt_op_type),a
    xor a
    ld (r17_txt_op_v0),a
    ret
r17_txt_operand_c:
    ld a,'c'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_REG8
    ld (r17_txt_op_type),a
    ld a,1
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_d:
    ld a,'d'
    call r17_txt_consume
    ret c
    call r17_txt_peek_soft
    cp 'e'
    jr z,r17_txt_operand_de
    ld a,R17_TXT_OP_REG8
    ld (r17_txt_op_type),a
    ld a,2
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_de:
    ld a,'e'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_RR
    ld (r17_txt_op_type),a
    ld a,1
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_e:
    ld a,'e'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_REG8
    ld (r17_txt_op_type),a
    ld a,3
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_h:
    ld a,'h'
    call r17_txt_consume
    ret c
    call r17_txt_peek_soft
    cp 'l'
    jr z,r17_txt_operand_hl
    ld a,R17_TXT_OP_REG8
    ld (r17_txt_op_type),a
    ld a,4
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_hl:
    ld a,'l'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_RR
    ld (r17_txt_op_type),a
    ld a,2
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_l:
    ld a,'l'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_REG8
    ld (r17_txt_op_type),a
    ld a,5
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_sp:
    ld hl,r17_txt_s_sp
    call r17_txt_match_tail
    ret c
    ld a,R17_TXT_OP_RR
    ld (r17_txt_op_type),a
    ld a,3
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_i:
    ld a,'i'
    call r17_txt_consume
    ret c
    call r17_txt_peek_soft
    cp 'x'
    jr z,r17_txt_operand_ix
    cp 'y'
    jr z,r17_txt_operand_iy
    ld a,R17_TXT_OP_SPECIAL
    ld (r17_txt_op_type),a
    xor a
    ld (r17_txt_op_v0),a
    ret
r17_txt_operand_ix:
    ld a,'x'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_INDEX
    ld (r17_txt_op_type),a
    xor a
    ld (r17_txt_op_v0),a
    ret
r17_txt_operand_iy:
    ld a,'y'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_INDEX
    ld (r17_txt_op_type),a
    ld a,1
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_r:
    ld a,'r'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_SPECIAL
    ld (r17_txt_op_type),a
    ld a,1
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_operand_imm:
    call r17_txt_parse_num
    ret c
    ld (r17_txt_op_w),de
    ld a,R17_TXT_OP_IMM
    ld (r17_txt_op_type),a
    xor a
    ret

r17_txt_parse_paren:
    ld a,'('
    call r17_txt_consume
    ret c
    call r17_txt_peek
    ret c
    cp 'h'
    jr z,r17_txt_paren_hl
    cp 'b'
    jr z,r17_txt_paren_bc
    cp 'd'
    jr z,r17_txt_paren_de
    cp 'i'
    jr z,r17_txt_paren_index
    call r17_txt_parse_num
    ret c
    ld (r17_txt_op_w),de
    ld a,')'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_MEMABS
    ld (r17_txt_op_type),a
    xor a
    ret
r17_txt_paren_hl:
    ld hl,r17_txt_s_hl_close
    call r17_txt_match_tail
    ret c
    ld a,R17_TXT_OP_REG8
    ld (r17_txt_op_type),a
    ld a,6
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_paren_bc:
    ld hl,r17_txt_s_bc_close
    call r17_txt_match_tail
    ret c
    ld a,R17_TXT_OP_MEMPAIR
    ld (r17_txt_op_type),a
    xor a
    ld (r17_txt_op_v0),a
    ret
r17_txt_paren_de:
    ld hl,r17_txt_s_de_close
    call r17_txt_match_tail
    ret c
    ld a,R17_TXT_OP_MEMPAIR
    ld (r17_txt_op_type),a
    ld a,1
    ld (r17_txt_op_v0),a
    xor a
    ret
r17_txt_paren_index:
    ld a,'i'
    call r17_txt_consume
    ret c
    call r17_txt_get
    ret c
    cp 'x'
    jr z,r17_txt_paren_ix
    cp 'y'
    jp nz,r17_as_error
    ld a,1
    jr r17_txt_paren_index_selected
r17_txt_paren_ix:
    xor a
r17_txt_paren_index_selected:
    ld (r17_txt_op_v0),a
    call r17_txt_get
    ret c
    cp '+'
    jr z,r17_txt_paren_disp_plus
    cp '-'
    jp nz,r17_as_error
    ld a,1
    ld (r17_txt_tmp0),a
    jr r17_txt_paren_disp_num
r17_txt_paren_disp_plus:
    xor a
    ld (r17_txt_tmp0),a
r17_txt_paren_disp_num:
    call r17_txt_parse_num
    ret c
    ld a,d
    or a
    jp nz,r17_as_error
    ld a,(r17_txt_tmp0)
    or a
    jr z,r17_txt_paren_disp_positive
    ld a,e
    cp $81
    jp nc,r17_as_error
    xor a
    sub e
    ld e,a
    jr r17_txt_paren_disp_store
r17_txt_paren_disp_positive:
    ld a,e
    cp $80
    jp nc,r17_as_error
r17_txt_paren_disp_store:
    ld a,e
    ld (r17_txt_op_v1),a
    ld a,')'
    call r17_txt_consume
    ret c
    ld a,R17_TXT_OP_INDEXED
    ld (r17_txt_op_type),a
    xor a
    ret

r17_txt_save_first:
    ld a,(r17_txt_op_type)
    ld (r17_txt_f_type),a
    ld a,(r17_txt_op_v0)
    ld (r17_txt_f_v0),a
    ld a,(r17_txt_op_v1)
    ld (r17_txt_f_v1),a
    ld hl,(r17_txt_op_w)
    ld (r17_txt_f_w),hl
    ret
r17_txt_restore_first_as_op:
    ld a,(r17_txt_f_type)
    ld (r17_txt_op_type),a
    ld a,(r17_txt_f_v0)
    ld (r17_txt_op_v0),a
    ld a,(r17_txt_f_v1)
    ld (r17_txt_op_v1),a
    ld hl,(r17_txt_f_w)
    ld (r17_txt_op_w),hl
    ret

r17_txt_parse_cond:
    call r17_txt_peek
    ret c
    cp 'n'
    jr z,r17_txt_cond_n
    cp 'z'
    jr z,r17_txt_cond_z
    cp 'c'
    jr z,r17_txt_cond_c
    cp 'p'
    jr z,r17_txt_cond_p
    cp 'm'
    jr z,r17_txt_cond_m
    jp r17_as_error
r17_txt_cond_n:
    ld a,'n'
    call r17_txt_consume
    ret c
    call r17_txt_get
    ret c
    cp 'z'
    jr z,r17_txt_cond_nz
    cp 'c'
    jp nz,r17_as_error
    ld a,2
    ret
r17_txt_cond_nz:
    xor a
    ret
r17_txt_cond_z:
    ld a,'z'
    call r17_txt_consume
    ret c
    ld a,1
    ret
r17_txt_cond_c:
    ld a,'c'
    call r17_txt_consume
    ret c
    ld a,3
    ret
r17_txt_cond_p:
    ld a,'p'
    call r17_txt_consume
    ret c
    call r17_txt_peek_soft
    cp 'o'
    jr z,r17_txt_cond_po
    cp 'e'
    jr z,r17_txt_cond_pe
    ld a,6
    ret
r17_txt_cond_po:
    ld a,'o'
    call r17_txt_consume
    ret c
    ld a,4
    ret
r17_txt_cond_pe:
    ld a,'e'
    call r17_txt_consume
    ret c
    ld a,5
    ret
r17_txt_cond_m:
    ld a,'m'
    call r17_txt_consume
    ret c
    ld a,7
    ret

r17_txt_parse_push_pair:
    call r17_txt_peek
    ret c
    cp 'b'
    jr z,r17_txt_push_bc
    cp 'd'
    jr z,r17_txt_push_de
    cp 'h'
    jr z,r17_txt_push_hl
    cp 'a'
    jr z,r17_txt_push_af
    cp 'i'
    jr z,r17_txt_push_index
    jp r17_as_error
r17_txt_push_bc:
    ld hl,r17_txt_s_bc
    call r17_txt_match_tail
    ret c
    xor a
    ret
r17_txt_push_de:
    ld hl,r17_txt_s_de
    call r17_txt_match_tail
    ret c
    ld a,1
    ret
r17_txt_push_hl:
    ld hl,r17_txt_s_hl
    call r17_txt_match_tail
    ret c
    ld a,2
    ret
r17_txt_push_af:
    ld hl,r17_txt_s_af
    call r17_txt_match_tail
    ret c
    ld a,3
    ret
r17_txt_push_index:
    ld a,'i'
    call r17_txt_consume
    ret c
    call r17_txt_get
    ret c
    cp 'x'
    jr z,r17_txt_push_ix
    cp 'y'
    jp nz,r17_as_error
    ld a,5
    ret
r17_txt_push_ix:
    ld a,4
    ret

r17_txt_match_ex_form:
    ld hl,r17_txt_s_ex_dehl
    call r17_txt_match_tail_soft
    jr nc,r17_txt_ex0
    ld hl,r17_txt_s_ex_sphl
    call r17_txt_match_tail_soft
    jr nc,r17_txt_ex1
    ld hl,r17_txt_s_ex_af
    call r17_txt_match_tail
    ret c
    ld a,2
    ret
r17_txt_ex0:
    xor a
    ret
r17_txt_ex1:
    ld a,1
    ret

r17_txt_try_exact_hl_indirect:
    ld hl,r17_txt_s_hl_ind
    call r17_txt_match_tail_soft
    ret

r17_txt_parse_num:
    call r17_txt_peek
    ret c
    cp '$'
    jr z,r17_txt_parse_hex
    cp '0'
    jp c,r17_as_error
    cp '9'+1
    jp nc,r17_as_error
    call r17_txt_get
    sub '0'
    ld e,a
    ld d,0
    call r17_txt_peek_soft
    cp '0'
    jr c,r17_txt_num_decimal_done
    cp '9'+1
    jp c,r17_as_error
r17_txt_num_decimal_done:
    xor a
    ret

r17_txt_parse_hex:
    ld a,'$'
    call r17_txt_consume
    ret c
    ld de,0
    xor a
    ld (r17_txt_hex_count),a
r17_txt_hex_loop:
    call r17_txt_peek_soft
    call r17_txt_hex_nibble
    jr c,r17_txt_hex_done
    ld (r17_txt_tmp0),a
    ld a,(r17_txt_hex_count)
    cp 4
    jp nc,r17_as_error
    inc a
    ld (r17_txt_hex_count),a
    call r17_txt_get
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    sla e
    rl d
    ld a,(r17_txt_tmp0)
    add a,e
    ld e,a
    jr nc,r17_txt_hex_loop
    inc d
    jr r17_txt_hex_loop
r17_txt_hex_done:
    ld a,(r17_txt_hex_count)
    or a
    jp z,r17_as_error
    xor a
    ret

r17_txt_hex_nibble:
    cp '0'
    jr c,r17_txt_hex_no
    cp '9'+1
    jr c,r17_txt_hex_digit
    cp 'a'
    jr c,r17_txt_hex_no
    cp 'f'+1
    jr nc,r17_txt_hex_no
    sub 'a'-10
    or a
    ret
r17_txt_hex_digit:
    sub '0'
    or a
    ret
r17_txt_hex_no:
    scf
    ret

r17_txt_get:
    ld hl,(r17_txt_p)
    ld de,(r17_txt_line_end)
    or a
    sbc hl,de
    jp nc,r17_as_error
    ld hl,(r17_txt_p)
    ld a,(hl)
    inc hl
    ld (r17_txt_p),hl
    or a
    ret

r17_txt_peek:
    ld hl,(r17_txt_p)
    ld de,(r17_txt_line_end)
    or a
    sbc hl,de
    jp nc,r17_as_error
    ld hl,(r17_txt_p)
    ld a,(hl)
    or a
    ret

r17_txt_peek_soft:
    ld hl,(r17_txt_p)
    ld de,(r17_txt_line_end)
    or a
    sbc hl,de
    jr z,r17_txt_peek_soft_end
    jp nc,r17_as_error
    ld hl,(r17_txt_p)
    ld a,(hl)
    or a
    ret
r17_txt_peek_soft_end:
    xor a
    ret

r17_txt_is_end:
    ld hl,(r17_txt_p)
    ld de,(r17_txt_line_end)
    or a
    sbc hl,de
    ret z
    jp c,r17_txt_not_end
    jp r17_as_error
r17_txt_not_end:
    ld a,1
    or a
    ret

r17_txt_expect_end:
    call r17_txt_is_end
    ret z
    jp r17_as_error

r17_txt_consume:
    ld (r17_txt_char),a
    call r17_txt_get
    ret c
    ld b,a
    ld a,(r17_txt_char)
    cp b
    ret z
    jp r17_as_error

r17_txt_peek_comma_or_end:
    call r17_txt_is_end
    jr nz,r17_txt_peek_comma
    xor a
    ret
r17_txt_peek_comma:
    call r17_txt_peek
    ret c
    cp ','
    jp nz,r17_as_error
    ld a,1
    or a
    ret

r17_txt_match_tail:
    push hl
    ld de,(r17_txt_p)
r17_txt_match_tail_loop:
    ld a,(hl)
    or a
    jr z,r17_txt_match_tail_ok
    push hl
    ld hl,(r17_txt_line_end)
    or a
    sbc hl,de
    pop hl
    jr z,r17_txt_match_tail_fail
    jr c,r17_txt_match_tail_fail
    ld a,(de)
    cp (hl)
    jr nz,r17_txt_match_tail_fail
    inc de
    inc hl
    jr r17_txt_match_tail_loop
r17_txt_match_tail_ok:
    pop hl
    ld (r17_txt_p),de
    xor a
    ret
r17_txt_match_tail_fail:
    pop hl
    jp r17_as_error

r17_txt_match_tail_soft:
    ld de,(r17_txt_p)
    ld (r17_txt_saved_p),de
    push hl
r17_txt_soft_loop:
    ld a,(hl)
    or a
    jr z,r17_txt_soft_ok
    push hl
    ld hl,(r17_txt_line_end)
    or a
    sbc hl,de
    pop hl
    jr z,r17_txt_soft_fail
    jr c,r17_txt_soft_fail
    ld a,(de)
    cp (hl)
    jr nz,r17_txt_soft_fail
    inc de
    inc hl
    jr r17_txt_soft_loop
r17_txt_soft_ok:
    pop hl
    ld (r17_txt_p),de
    xor a
    ret
r17_txt_soft_fail:
    pop hl
    ld hl,(r17_txt_saved_p)
    ld (r17_txt_p),hl
    scf
    ret

r17_txt_rec_start:
    ld (r17_txt_rec),a
    ld a,1
    ld (r17_txt_rec_len),a
    ret

r17_txt_rec8:
    ld (r17_txt_tmp0),a
    ld a,(r17_txt_rec_len)
    cp 5
    jp nc,r17_as_error
    ld e,a
    ld d,0
    ld hl,r17_txt_rec
    add hl,de
    ld a,(r17_txt_tmp0)
    ld (hl),a
    ld a,(r17_txt_rec_len)
    inc a
    ld (r17_txt_rec_len),a
    ret

r17_txt_rec16:
    ld a,e
    call r17_txt_rec8
    ld a,d
    jp r17_txt_rec8

r17_txt_rec_emit:
    ld a,(r17_as_guard_mode)
    or a
    jr z,r17_txt_rec_guard_done
    ld hl,(r17_txt_p)
    ld (r17_as_guard_limit),hl
r17_txt_rec_guard_done:
    ld hl,r17_txt_rec
    ld (r17_as_cur),hl
    ld a,(r17_txt_rec_len)
    ld e,a
    ld d,0
    add hl,de
    ld (r17_as_end),hl
    ld hl,1
    ld (r17_as_records_left),hl
    call r17_as_record_loop
    ret c
    ld hl,(r17_as_cur)
    ld de,(r17_as_end)
    or a
    sbc hl,de
    ret z
    jp r17_as_error

r17_txt_s_sp:       db "sp",0
r17_txt_s_bc:       db "bc",0
r17_txt_s_de:       db "de",0
r17_txt_s_hl:       db "hl",0
r17_txt_s_af:       db "af",0
r17_txt_s_hl_close: db "hl)",0
r17_txt_s_bc_close: db "bc)",0
r17_txt_s_de_close: db "de)",0
r17_txt_s_hl_ind:   db "(hl)",0
r17_txt_s_a_c:      db "a,(c)",0
r17_txt_s_c_a:      db "(c),a",0
r17_txt_s_ex_dehl:  db "de,hl",0
r17_txt_s_ex_sphl:  db "(sp),hl",0
r17_txt_s_ex_af:    db "af,af'",0

r17_txt_mnemonics:
    db 2,"ld",R17_TXT_M_LD
    db 2,"jp",R17_TXT_M_JP
    db 4,"call",R17_TXT_M_CALL
    db 2,"jr",R17_TXT_M_JR
    db 4,"djnz",R17_TXT_M_DJNZ
    db 3,"ret",R17_TXT_M_RET
    db 3,"inc",R17_TXT_M_INC
    db 3,"dec",R17_TXT_M_DEC
    db 4,"push",R17_TXT_M_PUSH
    db 3,"pop",R17_TXT_M_POP
    db 2,"ex",R17_TXT_M_EX
    db 2,"im",R17_TXT_M_IM
    db 2,"in",R17_TXT_M_IN
    db 3,"out",R17_TXT_M_OUT
    db 2,"db",R17_TXT_M_DB
    db 2,"dw",R17_TXT_M_DW
    db 4,"defs",R17_TXT_M_DEFS
    db 3,"org",R17_TXT_M_ORG
    db 3,"rst",R17_TXT_M_RST
    db 3,"add",$40
    db 3,"adc",$41
    db 3,"sub",$42
    db 3,"sbc",$43
    db 3,"and",$44
    db 3,"xor",$45
    db 2,"or",$46
    db 2,"cp",$47
    db 3,"rlc",$50
    db 3,"rrc",$51
    db 2,"rl",$52
    db 2,"rr",$53
    db 3,"sla",$54
    db 3,"sra",$55
    db 3,"srl",$56
    db 3,"bit",$60
    db 3,"res",$61
    db 3,"set",$62
    db 3,"nop",$80+0
    db 4,"rlca",$80+1
    db 4,"rrca",$80+2
    db 3,"rla",$80+3
    db 3,"rra",$80+4
    db 3,"daa",$80+5
    db 3,"cpl",$80+6
    db 3,"scf",$80+7
    db 3,"ccf",$80+8
    db 4,"halt",$80+9
    db 2,"di",$80+10
    db 2,"ei",$80+11
    db 3,"exx",$80+12
    db 4,"reti",$80+13
    db 3,"neg",$80+14
    db 3,"ldi",$80+15
    db 4,"ldir",$80+16
    db 3,"ldd",$80+17
    db 4,"lddr",$80+18
    db 3,"cpi",$80+19
    db 4,"cpir",$80+20
    db 3,"cpd",$80+21
    db 4,"cpdr",$80+22
    db 0

r17_txt_source:      dw 0
r17_txt_source_len:  dw 0
r17_txt_cur:         dw 0
r17_txt_end:         dw 0
r17_txt_line_start:  dw 0
r17_txt_line_end:    dw 0
r17_txt_p:           dw 0
r17_txt_saved_p:     dw 0
r17_txt_table_name:  dw 0
r17_txt_table_next:  dw 0
r17_txt_id:          db 0
r17_txt_saw_org:     db 0
r17_txt_char:        db 0
r17_txt_hex_count:   db 0
r17_txt_family:      db 0
r17_txt_tmp0:        db 0
r17_txt_tmp1:        db 0
r17_txt_num:         dw 0
r17_txt_num2:        dw 0
r17_txt_op_type:     db 0
r17_txt_op_v0:       db 0
r17_txt_op_v1:       db 0
r17_txt_op_w:        dw 0
r17_txt_f_type:      db 0
r17_txt_f_v0:        db 0
r17_txt_f_v1:        db 0
r17_txt_f_w:         dw 0
r17_txt_rec_len:     db 0
r17_txt_rec:         defs 5,0
    ENDM
