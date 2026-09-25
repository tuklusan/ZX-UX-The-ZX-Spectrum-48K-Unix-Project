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
; Sole production owner of raw 48K ROM routine addresses.

ROM_PRINT_A               EQU $0010
ROM_FP_CALC               EQU $0028
ROM_KEY_SCAN              EQU $028E
ROM_KEYBOARD              EQU $02BF
ROM_K_TEST                EQU $031E
ROM_KEY_DECODE            EQU $0333
ROM_BEEPER                EQU $03B5
ROM_BEEP_COMMAND          EQU $03F8
ROM_SA_BYTES              EQU $04C2
ROM_LD_BYTES              EQU $0556
ROM_PIXEL_ADD             EQU $22AA
ROM_POINT                 EQU $22CB
ROM_PLOT_SUB              EQU $22E5
ROM_DRAW_LINE             EQU $24BA
ROM_FP_TO_BC              EQU $2DA2
ROM_FP_PRINT              EQU $2DE3
ROM_CALCULATE             EQU $335B
ROM_INT                   EQU $36AF
ROM_EXP                   EQU $36C4
ROM_LN                    EQU $3713
ROM_COS                   EQU $37AA
ROM_SIN                   EQU $37B5
ROM_TAN                   EQU $37DA
ROM_ATN                   EQU $37E2
ROM_ASN                   EQU $3833
ROM_ACS                   EQU $3843
ROM_SQR                   EQU $384A
ROM_POWER                 EQU $3851
ROM_ERR_SP                EQU $5C3D
ROM_STKBOT                EQU $5C63
ROM_STKEND                EQU $5C65
ROM_BREG                  EQU $5C67
ROM_MEM                   EQU $5C68
ROM_MEMBOT                EQU $5C92
ROM_BEEP_STACK            EQU $5D00
ROM_FLAGS                 EQU $5C3B
ROM_CH_ADD                EQU $5C5D
ROM_SCANNING              EQU $24FB
ROM_DEC_TO_FP             EQU $2C9B
ROM_CALC_STACK            EQU $5D80

    MACRO EMIT_ROM_SERVICE_ROUTINES
; Every raw ROM return samples/checks the dedicated kernel stack while preserving
; the ROM routine's complete AF/BC/DE/HL result contract, then canonicalizes IY.
zx48_rom_checked_return:
    push af
zx48_rom_checked_return_af_saved:
    push bc
    push de
    push hl
    call zx48_kernel_stack_sample
    call zx48_kernel_stack_check
    pop hl
    pop de
    pop bc
    pop af
zx48_rom_restore_iy:
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_print_a:
    call ROM_PRINT_A
    jr zx48_rom_checked_return
zx48_rom_key_scan:
    call ROM_KEY_SCAN
    jr zx48_rom_checked_return
zx48_rom_k_test:
    call ROM_K_TEST
    jr zx48_rom_checked_return
zx48_rom_key_decode:
    call ROM_KEY_DECODE
    jr zx48_rom_checked_return
zx48_rom_pixel_add:
    call ROM_PIXEL_ADD
    jr zx48_rom_checked_return
zx48_rom_point:
    call ROM_POINT
    jr zx48_rom_checked_return
zx48_rom_plot_sub:
    call ROM_PLOT_SUB
    jr zx48_rom_checked_return
zx48_rom_draw_line:
    call ROM_DRAW_LINE
    jr zx48_rom_checked_return

; These ROM services drive ULA port 0xFE. Mirror only the kernel border bits
; into BORDCR before entry, then re-emit the authoritative shadow on return.
zx48_rom_beeper:
    call zx48_ula_rom_prepare
    call ROM_BEEPER
    jr zx48_rom_ula_done
zx48_rom_sa_bytes:
    call zx48_ula_rom_prepare
    call ROM_SA_BYTES
    jr zx48_rom_ula_done
zx48_rom_ld_bytes:
    call zx48_ula_rom_prepare
    call ROM_LD_BYTES
zx48_rom_ula_done:
    push af
    xor a
    ld (altreg_busy),a
    ld a,(ula_shadow)
    call zx48_ula_commit
    jr zx48_rom_checked_return_af_saved
    ENDM

; P7.09 staged ROM BEEP gateway. Kept out of the resident Phase-6 ROM macro
; until the Phase-7 integration/packing boundary owns the final kernel layout.

; P7.10 isolated numeric-expression gateway. The shell tokenizer has already
; reduced input to decimal/operator bytes plus the exact approved ROM function
; tokens. No user identifier, string token, BASIC statement, or arbitrary ROM
; address reaches SCANNING.
    MACRO EMIT_P710_ROM_CALC_ROUTINES
; Convert one already allow-listed decimal literal to the exact Spectrum
; five-byte representation without modifying the source text. HL=literal start,
; DE=writable five-byte destination. The caller has already validated the whole
; expression before this routine may enter ROM.
zx48_rom_decimal_literal:
    ld (rom_decimal_input_ptr),hl
    ld (rom_decimal_output_ptr),de
    ld a,(altreg_busy)
    or a
    jp nz,zx48_rom_calc_busy

    ld hl,0
    add hl,sp
    ld (rom_calc_saved_sp),hl
    ld hl,(ROM_ERR_SP)
    ld (rom_calc_saved_err_sp),hl
    ld hl,(ROM_STKBOT)
    ld (rom_calc_saved_stkbot),hl
    ld hl,(ROM_STKEND)
    ld (rom_calc_saved_stkend),hl
    ld hl,(ROM_MEM)
    ld (rom_calc_saved_mem),hl
    ld hl,(ROM_CH_ADD)
    ld (rom_calc_saved_chadd),hl
    ld a,(ROM_FLAGS)
    ld (rom_calc_saved_flags),a
    ld a,(ROM_IY_ANCHOR)
    ld (rom_calc_saved_errnr),a

    ld a,1
    ld (altreg_busy),a
    ld hl,ROM_CALC_STACK
    ld (ROM_STKBOT),hl
    ld (ROM_STKEND),hl
    ld hl,ROM_MEMBOT
    ld (ROM_MEM),hl
    ld hl,(rom_decimal_input_ptr)
    ld (ROM_CH_ADD),hl
    ld a,$ff
    ld (ROM_IY_ANCHOR),a

    ld hl,zx48_rom_decimal_error
    push hl
    ld hl,0
    add hl,sp
    ld (ROM_ERR_SP),hl
    ld iy,ROM_IY_ANCHOR
    ld hl,(rom_decimal_input_ptr)
    ld a,(hl)
    call ROM_DEC_TO_FP
    pop hl

    ld hl,(ROM_STKEND)
    ld bc,5
    or a
    sbc hl,bc
    ld de,(rom_decimal_output_ptr)
    ldir
    call zx48_rom_calc_cleanup
    xor a
    or a
    ret

zx48_rom_decimal_error:
    ld hl,(rom_calc_saved_sp)
    ld sp,hl
    call zx48_rom_calc_cleanup
    ld a,E_INVAL
    scf
    ret

zx48_rom_calc_expr:
    ld (rom_calc_input_ptr),hl
    ld (rom_calc_output_ptr),de
    ld a,(altreg_busy)
    or a
    jp nz,zx48_rom_calc_busy

    ld hl,0
    add hl,sp
    ld (rom_calc_saved_sp),hl
    ld hl,(ROM_ERR_SP)
    ld (rom_calc_saved_err_sp),hl
    ld hl,(ROM_STKBOT)
    ld (rom_calc_saved_stkbot),hl
    ld hl,(ROM_STKEND)
    ld (rom_calc_saved_stkend),hl
    ld hl,(ROM_MEM)
    ld (rom_calc_saved_mem),hl
    ld hl,(ROM_CH_ADD)
    ld (rom_calc_saved_chadd),hl
    ld a,(ROM_FLAGS)
    ld (rom_calc_saved_flags),a
    ld a,(ROM_IY_ANCHOR)
    ld (rom_calc_saved_errnr),a

    ld a,1
    ld (altreg_busy),a
    ld hl,ROM_CALC_STACK
    ld (ROM_STKBOT),hl
    ld (ROM_STKEND),hl
    ld hl,ROM_MEMBOT
    ld (ROM_MEM),hl
    ld hl,(rom_calc_input_ptr)
    ld (ROM_CH_ADD),hl
    ld a,(rom_calc_saved_flags)
    and $bf
    or $80
    ld (ROM_FLAGS),a
    ld a,$ff
    ld (ROM_IY_ANCHOR),a

    ld hl,zx48_rom_calc_error
    push hl
    ld hl,0
    add hl,sp
    ld (ROM_ERR_SP),hl
    ld iy,ROM_IY_ANCHOR
    call ROM_SCANNING
    pop hl

    ld a,(ROM_FLAGS)
    bit 6,a
    jr z,zx48_rom_calc_type_error
    ld hl,(ROM_STKEND)
    ld bc,5
    or a
    sbc hl,bc
    ld de,(rom_calc_output_ptr)
    ldir
    call zx48_rom_calc_cleanup
    xor a
    or a
    ret

zx48_rom_calc_type_error:
    call zx48_rom_calc_cleanup
    ld a,E_INVAL
    scf
    ret

zx48_rom_calc_error:
    ld hl,(rom_calc_saved_sp)
    ld sp,hl
    call zx48_rom_calc_cleanup
    ld a,E_INVAL
    scf
    ret

zx48_rom_calc_cleanup:
    ld hl,(rom_calc_saved_err_sp)
    ld (ROM_ERR_SP),hl
    ld hl,(rom_calc_saved_stkbot)
    ld (ROM_STKBOT),hl
    ld hl,(rom_calc_saved_stkend)
    ld (ROM_STKEND),hl
    ld hl,(rom_calc_saved_mem)
    ld (ROM_MEM),hl
    ld hl,(rom_calc_saved_chadd)
    ld (ROM_CH_ADD),hl
    ld a,(rom_calc_saved_flags)
    ld (ROM_FLAGS),a
    ld a,(rom_calc_saved_errnr)
    ld (ROM_IY_ANCHOR),a
    xor a
    ld (altreg_busy),a
    ld iy,ROM_IY_ANCHOR
    ret

zx48_rom_calc_busy:
    ld a,E_BUSY
    scf
    ret

rom_decimal_input_ptr: dw 0
rom_decimal_output_ptr: dw 0
rom_calc_input_ptr: dw 0
rom_calc_output_ptr: dw 0
rom_calc_saved_sp: dw 0
rom_calc_saved_err_sp: dw 0
rom_calc_saved_stkbot: dw 0
rom_calc_saved_stkend: dw 0
rom_calc_saved_mem: dw 0
rom_calc_saved_chadd: dw 0
rom_calc_saved_flags: db 0
rom_calc_saved_errnr: db 0
    ENDM


; P11.17 isolated SYS_FP_EXEC calculator engine. The public syscall layer owns
; FPOP1 validation; this routine owns calculator serialization, protected ROM
; state, controlled operand copies, error recovery, and exact result copying.
    MACRO EMIT_P1117_ROM_FP_EXEC_ROUTINES
P1117_ROM_ADD            EQU $0F
P1117_ROM_SUB            EQU $03
P1117_ROM_MUL            EQU $04
P1117_ROM_DIV            EQU $05
P1117_ROM_POW            EQU $06
P1117_ROM_ABS            EQU $2A
P1117_ROM_SGN            EQU $29
P1117_ROM_INT            EQU $27
P1117_ROM_EXP            EQU $26
P1117_ROM_LN             EQU $25
P1117_ROM_SIN            EQU $1F
P1117_ROM_COS            EQU $20
P1117_ROM_TAN            EQU $21
P1117_ROM_ASN            EQU $22
P1117_ROM_ACS            EQU $23
P1117_ROM_ATN            EQU $24
P1117_ROM_SQR            EQU $28

p1117_fp_op:             db 0
p1117_fp_lhs_ptr:        dw 0
p1117_fp_rhs_ptr:        dw 0
p1117_fp_out_ptr:        dw 0
p1117_fp_result:         defs 5,0
p1117_fp_saved_sp:       dw 0
p1117_fp_saved_err_sp:   dw 0
p1117_fp_saved_stkbot:   dw 0
p1117_fp_saved_stkend:   dw 0
p1117_fp_saved_mem:      dw 0
p1117_fp_saved_chadd:    dw 0
p1117_fp_saved_flags:    db 0
p1117_fp_saved_errnr:    db 0
p1117_fp_saved_breg:     db 0

p1117_fp_rom_table:
    db P1117_ROM_ADD,P1117_ROM_SUB,P1117_ROM_MUL,P1117_ROM_DIV
    db P1117_ROM_POW,P1117_ROM_ABS,P1117_ROM_SGN,P1117_ROM_INT
    db P1117_ROM_EXP,P1117_ROM_LN,P1117_ROM_SIN,P1117_ROM_COS
    db P1117_ROM_TAN,P1117_ROM_ASN,P1117_ROM_ACS,P1117_ROM_ATN
    db P1117_ROM_SQR

; A=FPOP1 op 1..17, HL=lhs five-byte pointer, DE=rhs pointer/0,
; BC=caller-owned five-byte output. Inputs have already been range-validated.
zx48_p1117_rom_fp_exec:
    ld (p1117_fp_op),a
    ld (p1117_fp_lhs_ptr),hl
    ld (p1117_fp_rhs_ptr),de
    ld (p1117_fp_out_ptr),bc
    ld a,(altreg_busy)
    or a
    jp nz,p1117_fp_rom_busy

    ld hl,0
    add hl,sp
    ld (p1117_fp_saved_sp),hl
    ld hl,(ROM_ERR_SP)
    ld (p1117_fp_saved_err_sp),hl
    ld hl,(ROM_STKBOT)
    ld (p1117_fp_saved_stkbot),hl
    ld hl,(ROM_STKEND)
    ld (p1117_fp_saved_stkend),hl
    ld hl,(ROM_MEM)
    ld (p1117_fp_saved_mem),hl
    ld hl,(ROM_CH_ADD)
    ld (p1117_fp_saved_chadd),hl
    ld a,(ROM_FLAGS)
    ld (p1117_fp_saved_flags),a
    ld a,(ROM_IY_ANCHOR)
    ld (p1117_fp_saved_errnr),a
    ld a,(ROM_BREG)
    ld (p1117_fp_saved_breg),a

    ld a,1
    ld (altreg_busy),a
    ld hl,ROM_CALC_STACK
    ld (ROM_STKBOT),hl
    ld (ROM_STKEND),hl
    ld hl,ROM_MEMBOT
    ld (ROM_MEM),hl
    ld a,$FF
    ld (ROM_IY_ANCHOR),a

    ld hl,(p1117_fp_lhs_ptr)
    ld de,ROM_CALC_STACK
    ld bc,5
    ldir
    ld hl,ROM_CALC_STACK+5
    ld (ROM_STKEND),hl

    ld a,(p1117_fp_op)
    cp FPOP_OP_ABS
    jp nc,p1117_fp_rom_operands_ready
    ld hl,(p1117_fp_rhs_ptr)
    ld de,ROM_CALC_STACK+5
    ld bc,5
    ldir
    ld hl,ROM_CALC_STACK+10
    ld (ROM_STKEND),hl

p1117_fp_rom_operands_ready:
    ld a,(p1117_fp_op)
    dec a
    ld e,a
    ld d,0
    ld hl,p1117_fp_rom_table
    add hl,de
    ld b,(hl)

    ld hl,p1117_fp_rom_error
    push hl
    ld hl,0
    add hl,sp
    ld (ROM_ERR_SP),hl
    ld iy,ROM_IY_ANCHOR
    call ROM_CALCULATE
    db $3B,$38
    pop hl

    ld hl,(ROM_STKEND)
    ld bc,5
    or a
    sbc hl,bc
    ld de,p1117_fp_result
    ldir
    call p1117_fp_rom_cleanup

    ld hl,p1117_fp_result
    ld de,(p1117_fp_out_ptr)
    ld bc,5
    ldir
    ld hl,0
    xor a
    ret

p1117_fp_rom_error:
    ld hl,(p1117_fp_saved_sp)
    ld sp,hl
    call p1117_fp_rom_cleanup
    ld a,E_INVAL
    scf
    ret

p1117_fp_rom_cleanup:
    ld hl,(p1117_fp_saved_err_sp)
    ld (ROM_ERR_SP),hl
    ld hl,(p1117_fp_saved_stkbot)
    ld (ROM_STKBOT),hl
    ld hl,(p1117_fp_saved_stkend)
    ld (ROM_STKEND),hl
    ld hl,(p1117_fp_saved_mem)
    ld (ROM_MEM),hl
    ld hl,(p1117_fp_saved_chadd)
    ld (ROM_CH_ADD),hl
    ld a,(p1117_fp_saved_flags)
    ld (ROM_FLAGS),a
    ld a,(p1117_fp_saved_breg)
    ld (ROM_BREG),a
    ld a,(p1117_fp_saved_errnr)
    ld (ROM_IY_ANCHOR),a
    xor a
    ld (altreg_busy),a
    ld iy,ROM_IY_ANCHOR
    ret

p1117_fp_rom_busy:
    ld a,E_BUSY
    scf
    ret
    ENDM

    MACRO EMIT_P709_ROM_BEEP_ROUTINES
; P7.09 isolated BASIC-compatible BEEP gateway.
; HL -> five-byte duration, DE -> five-byte pitch. The two exact values are
; copied into a private calculator stack in protected ROM-compatibility RAM.
; ERR_SP is redirected to a kernel-owned recovery item so any Sinclair report
; becomes E_INVAL rather than escaping into BASIC.
zx48_rom_beep_values:
    ld (rom_beep_duration_ptr),hl
    ld (rom_beep_pitch_ptr),de
    ld hl,(ROM_ERR_SP)
    ld (rom_beep_saved_err_sp),hl
    ld hl,(ROM_STKBOT)
    ld (rom_beep_saved_stkbot),hl
    ld hl,(ROM_STKEND)
    ld (rom_beep_saved_stkend),hl
    ld hl,(ROM_MEM)
    ld (rom_beep_saved_mem),hl
    ld hl,0
    add hl,sp
    ld (rom_beep_saved_sp),hl

    ld hl,ROM_BEEP_STACK
    ld (ROM_STKBOT),hl
    ld (ROM_STKEND),hl
    ld hl,ROM_MEMBOT
    ld (ROM_MEM),hl

    ld hl,(rom_beep_duration_ptr)
    ld de,ROM_BEEP_STACK
    ld bc,5
    ldir
    ld hl,(rom_beep_pitch_ptr)
    ld de,ROM_BEEP_STACK+5
    ld bc,5
    ldir
    ld hl,ROM_BEEP_STACK+10
    ld (ROM_STKEND),hl

    ld hl,zx48_rom_beep_error
    push hl
    ld hl,0
    add hl,sp
    ld (ROM_ERR_SP),hl
    ld iy,ROM_IY_ANCHOR
    call zx48_ula_rom_prepare
    call ROM_BEEP_COMMAND
    pop hl
    call zx48_rom_beep_cleanup
    xor a
    or a
    ret

zx48_rom_beep_error:
    ld hl,(rom_beep_saved_sp)
    ld sp,hl
    call zx48_rom_beep_cleanup
    ld a,E_INVAL
    scf
    ret

zx48_rom_beep_cleanup:
    ld hl,(rom_beep_saved_err_sp)
    ld (ROM_ERR_SP),hl
    ld hl,(rom_beep_saved_stkbot)
    ld (ROM_STKBOT),hl
    ld hl,(rom_beep_saved_stkend)
    ld (ROM_STKEND),hl
    ld hl,(rom_beep_saved_mem)
    ld (ROM_MEM),hl
    xor a
    ld (altreg_busy),a
    ld a,(ula_shadow)
    call zx48_ula_commit
    ld iy,ROM_IY_ANCHOR
    ret

rom_beep_duration_ptr: dw 0
rom_beep_pitch_ptr: dw 0
rom_beep_saved_err_sp: dw 0
rom_beep_saved_stkbot: dw 0
rom_beep_saved_stkend: dw 0
rom_beep_saved_mem: dw 0
rom_beep_saved_sp: dw 0

    ENDM

; P7.11 canonical read-only ROM service metadata.
ROMINFO_CLASS_A          EQU 1
ROMINFO_CLASS_B          EQU 2
ROMINFO_CLASS_C          EQU 3
ROMINFO_CAT_KEYBOARD     EQU 1
ROMINFO_CAT_CONSOLE      EQU 2
ROMINFO_CAT_TAPE         EQU 3
ROMINFO_CAT_GRAPHICS     EQU 4
ROMINFO_CAT_SOUND        EQU 5
ROMINFO_CAT_MATH         EQU 6
ROMINFO_FLAG_ERROR       EQU 1
ROMINFO_FLAG_ALTREG      EQU 2
ROMINFO_FLAG_DI          EQU 4
ROMINFO_FLAG_NONREENT    EQU 8
ROMINFO_RECORD_SIZE      EQU 24

    MACRO ROMINFO_REC nameText,nameLen,addressValue,classValue,categoryValue,flagsValue
    db nameText
    defs 16-nameLen,0
    dw addressValue
    db classValue,categoryValue
    dw flagsValue
    dw 0
    ENDM

    MACRO EMIT_P711_ROM_INFO_ROUTINES
; A=category 0..6, B=index, DE=writable 24-byte output. The syscall layer has
; validated the complete request and destination before this lookup executes.
zx48_rom_info_lookup:
    cp 7
    jp nc,zx48_rom_info_invalid
    ld (rom_info_query_category),a
    ld a,b
    ld (rom_info_query_index),a
    ld (rom_info_out_ptr),de
    xor a
    ld (rom_info_match_index),a
    ld hl,rom_info_table
zx48_rom_info_scan:
    ld a,(hl)
    or a
    jr z,zx48_rom_info_past_end
    ld a,(rom_info_query_category)
    or a
    jr z,zx48_rom_info_candidate
    push hl
    ld de,19
    add hl,de
    ld a,(hl)
    ld c,a
    pop hl
    ld a,(rom_info_query_category)
    cp c
    jr nz,zx48_rom_info_next
zx48_rom_info_candidate:
    ld a,(rom_info_match_index)
    ld c,a
    ld a,(rom_info_query_index)
    cp c
    jr z,zx48_rom_info_publish
    ld a,(rom_info_match_index)
    inc a
    ld (rom_info_match_index),a
zx48_rom_info_next:
    ld de,ROMINFO_RECORD_SIZE
    add hl,de
    jr zx48_rom_info_scan

zx48_rom_info_publish:
    ld de,(rom_info_out_ptr)
    ld bc,ROMINFO_RECORD_SIZE
    ldir
    ld hl,1
    xor a
    ret

zx48_rom_info_past_end:
    ld hl,0
    xor a
    ret

zx48_rom_info_invalid:
    ld a,E_INVAL
    scf
    ret

rom_info_query_category: db 0
rom_info_query_index: db 0
rom_info_match_index: db 0
rom_info_out_ptr: dw 0

; name[16], address, class, category, contract_flags, reserved=0.
; Flags: bit0 MAY_ERROR_RESTART, bit1 ALTREG_SENSITIVE,
; bit2 DISABLES_INTERRUPTS, bit3 NONREENTRANT.
rom_info_table:
    ROMINFO_REC "KEY-SCAN",8,ROM_KEY_SCAN,ROMINFO_CLASS_A,ROMINFO_CAT_KEYBOARD,0
    ROMINFO_REC "KEYBOARD",8,ROM_KEYBOARD,ROMINFO_CLASS_A,ROMINFO_CAT_KEYBOARD,ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "KEY-DECODE",10,ROM_KEY_DECODE,ROMINFO_CLASS_A,ROMINFO_CAT_KEYBOARD,ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "PRINT-A",7,ROM_PRINT_A,ROMINFO_CLASS_A,ROMINFO_CAT_CONSOLE,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "SA-BYTES",8,ROM_SA_BYTES,ROMINFO_CLASS_A,ROMINFO_CAT_TAPE,ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_DI+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "LD-BYTES",8,ROM_LD_BYTES,ROMINFO_CLASS_A,ROMINFO_CAT_TAPE,ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_DI+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "PIXEL-ADD",9,ROM_PIXEL_ADD,ROMINFO_CLASS_A,ROMINFO_CAT_GRAPHICS,ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "POINT",5,ROM_POINT,ROMINFO_CLASS_A,ROMINFO_CAT_GRAPHICS,ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "PLOT-SUB",8,ROM_PLOT_SUB,ROMINFO_CLASS_A,ROMINFO_CAT_GRAPHICS,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "DRAW-CONVERT",12,$24B7,ROMINFO_CLASS_B,ROMINFO_CAT_GRAPHICS,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "DRAW-LINE",9,ROM_DRAW_LINE,ROMINFO_CLASS_A,ROMINFO_CAT_GRAPHICS,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "BEEPER",6,ROM_BEEPER,ROMINFO_CLASS_A,ROMINFO_CAT_SOUND,ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_DI+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "BEEP-COMMAND",12,ROM_BEEP_COMMAND,ROMINFO_CLASS_B,ROMINFO_CAT_SOUND,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_DI+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "FP-CALC",7,ROM_FP_CALC,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "FP-TO-BC",8,ROM_FP_TO_BC,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "FP-PRINT",8,ROM_FP_PRINT,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "CALCULATE",9,ROM_CALCULATE,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "INT",3,ROM_INT,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "EXP",3,ROM_EXP,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "LN",2,ROM_LN,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "COS",3,ROM_COS,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "SIN",3,ROM_SIN,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "TAN",3,ROM_TAN,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "ATN",3,ROM_ATN,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "ASN",3,ROM_ASN,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "ACS",3,ROM_ACS,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "SQR",3,ROM_SQR,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ROMINFO_REC "POWER",5,ROM_POWER,ROMINFO_CLASS_B,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    ; Class-C rejection is diagnostic metadata only; SYS_ROM_INFO cannot call it.
    ROMINFO_REC "USR",3,$34BC,ROMINFO_CLASS_C,ROMINFO_CAT_MATH,ROMINFO_FLAG_ERROR+ROMINFO_FLAG_ALTREG+ROMINFO_FLAG_NONREENT
    db 0
    ENDM
