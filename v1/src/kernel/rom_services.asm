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
ROM_INT_STORE             EQU $2D8E
ROM_FP_TO_BC              EQU $2DA2
ROM_FP_PRINT              EQU $2DE3
ROM_TRUNCATE              EQU $3214
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
ROM_CURCHL                EQU $5C51
ROM_SCANNING              EQU $24FB
ROM_DEC_TO_FP             EQU $2C9B
ROM_CALC_STACK            EQU $5D80

; Shared bounded ROM-compatibility workspace for transient calculator/text
; transactions. The ROM disassembly contains no fixed 0x5E00/0x5F00 accesses;
; approved math/text paths reach these bytes only through the protected
; STKBOT/STKEND/MEM/CH_ADD contracts. Keep a full 128-byte calculator-stack
; window above ROM_CALC_STACK, then overlay mutually exclusive operation scratch.
P11_ROM_OP_BASE           EQU ROM_CALC_STACK+$80
P11_ROM_OP_MAX_END        EQU P11_ROM_OP_BASE+298
P11_ROM_TXN_BASE          EQU $5F40
P11_ROM_TXN_SNAPSHOT_END  EQU $5CB0
P11_ROM_TXN_SNAPSHOT_SIZE EQU P11_ROM_TXN_SNAPSHOT_END-ROM_IY_ANCHOR
P11_ROM_TXN_END           EQU P11_ROM_TXN_BASE+P11_ROM_TXN_SNAPSHOT_SIZE+2
    ASSERT P11_ROM_OP_MAX_END <= P11_ROM_TXN_BASE
    ASSERT P11_ROM_TXN_END <= ROM_COMPAT_END+1

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

; REV02 production ROM wrapper set. Historical qualification retains the full
; EMIT_ROM_SERVICE_ROUTINES surface above; the resident product keeps only
; wrappers reachable from ordinary keyboard/tape paths. Graphics is native and
; BEEP/FP use their dedicated validated ROM gateways below.
    MACRO EMIT_REV02_ROM_SERVICE_ROUTINES
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
zx48_rom_key_scan:
    call ROM_KEY_SCAN
    jr zx48_rom_checked_return
zx48_rom_k_test:
    call ROM_K_TEST
    jr zx48_rom_checked_return
zx48_rom_key_decode:
    call ROM_KEY_DECODE
    jr zx48_rom_checked_return

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
    ld (ROM_ERR_SP),sp
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
    ld (ROM_ERR_SP),sp
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


; P11 calculator/text gateways serialize the same ROM workspace. Emit one shared
; save/restore transaction even when several public gateway macros are packed together.
; Each gateway remains independently assemblable for its historical qualification fixture.
    MACRO EMIT_P11_ROM_CALC_TXN_ROUTINES
    IFNDEF ZX48_P11_ROM_CALC_TXN_EMITTED
    DEFINE ZX48_P11_ROM_CALC_TXN_EMITTED
; Snapshot the exact contiguous ROM system-variable range touched by the
; calculator/text gateways. The previous field-by-field save/restore covered
; only members of this same range; copying the full range is equivalent and
; also preserves intervening ROM workspace bytes.
p11_rom_snapshot           EQU P11_ROM_TXN_BASE
p11_rom_saved_sp           EQU P11_ROM_TXN_BASE+P11_ROM_TXN_SNAPSHOT_SIZE

; HL=caller SP before CALL. Carry set/E_BUSY if another serialized ROM gateway owns
; the compatibility workspace; otherwise preserve ROM state and prepare the stack.
zx48_p11_rom_txn_begin:
    ld a,(altreg_busy)
    or a
    jr nz,zx48_p11_rom_txn_busy
    ld (p11_rom_saved_sp),hl
    ld hl,ROM_IY_ANCHOR
    ld de,p11_rom_snapshot
    ld bc,P11_ROM_TXN_SNAPSHOT_SIZE
    ldir
    ld a,1
    ld (altreg_busy),a
    ld hl,ROM_CALC_STACK
    ld (ROM_STKBOT),hl
    ld (ROM_STKEND),hl
    ld hl,ROM_MEMBOT
    ld (ROM_MEM),hl
    ld a,$FF
    ld (ROM_IY_ANCHOR),a
    xor a
    ret

zx48_p11_rom_txn_busy:
    ld a,E_BUSY
    scf
    ret

zx48_p11_rom_txn_cleanup:
    ld hl,p11_rom_snapshot
    ld de,ROM_IY_ANCHOR
    ld bc,P11_ROM_TXN_SNAPSHOT_SIZE
    ldir
    xor a
    ld (altreg_busy),a
    ld iy,ROM_IY_ANCHOR
    ret

; Common ROM error restart for calculator gateways that need only transaction
; restoration before returning E_INVAL.
zx48_p11_rom_invalid_error:
    ld hl,(p11_rom_saved_sp)
    ld sp,hl
    call zx48_p11_rom_txn_cleanup
    ld a,E_INVAL
    scf
    ret
    ENDIF
    ENDM

; P11.17 isolated SYS_FP_EXEC calculator engine. The public syscall layer owns
; FPOP1 validation; this routine owns calculator serialization, protected ROM
; state, controlled operand copies, error recovery, and exact result copying.
    MACRO EMIT_P1117_ROM_FP_EXEC_ROUTINES
    EMIT_P11_ROM_CALC_TXN_ROUTINES
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


p1117_fp_rom_table:
    db P1117_ROM_ADD,P1117_ROM_SUB,P1117_ROM_MUL,P1117_ROM_DIV
    db P1117_ROM_POW,P1117_ROM_ABS,P1117_ROM_SGN,P1117_ROM_INT
    db P1117_ROM_EXP,P1117_ROM_LN,P1117_ROM_SIN,P1117_ROM_COS
    db P1117_ROM_TAN,P1117_ROM_ASN,P1117_ROM_ACS,P1117_ROM_ATN
    db P1117_ROM_SQR

; A=FPOP1 op 1..17, HL=lhs five-byte pointer, DE=rhs pointer/0,
; BC=caller-owned five-byte output. Inputs have already been range-validated.
; Historical qualification anchors retained as comments after equivalent compaction:
; p1117_fp_rom_busy:
; p1117_fp_result:
; ld de,p1117_fp_result
zx48_p1117_rom_fp_exec:
    ; Preserve the four gateway arguments in OS-private alternate registers
    ; while the common transaction snapshots ROM state and records caller SP.
    ex af,af'
    exx
    ld hl,0
    add hl,sp
    call zx48_p11_rom_txn_begin
    ret c
    exx
    ex af,af'

    ; Keep output/rhs/op on the kernel stack while the lhs is copied.
    push bc
    push de
    push af
    ld de,ROM_CALC_STACK
    ld bc,5
    ldir
    ld hl,ROM_CALC_STACK+5
    ld (ROM_STKEND),hl

    pop af
    cp FPOP_OP_ABS
    jr nc,p1117_fp_rom_unary
    pop hl
    ld de,ROM_CALC_STACK+5
    ld bc,5
    ldir
    ld hl,ROM_CALC_STACK+10
    ld (ROM_STKEND),hl
    jr p1117_fp_rom_operands_ready

p1117_fp_rom_unary:
    pop hl

p1117_fp_rom_operands_ready:
    pop de
    push de
    dec a
    ld e,a
    ld d,0
    ld hl,p1117_fp_rom_table
    add hl,de
    ld b,(hl)

    ld hl,zx48_p11_rom_invalid_error
    push hl
    ld (ROM_ERR_SP),sp
    ld iy,ROM_IY_ANCHOR
    call ROM_CALCULATE
    db $3B,$38
    pop hl
    pop de

    ld hl,(ROM_STKEND)
    ld bc,5
    or a
    sbc hl,bc
    ldir
    call zx48_p11_rom_txn_cleanup
    xor a
    ld h,a
    ld l,a
    ret


    ENDM

    MACRO EMIT_P709_ROM_BEEP_ROUTINES
    EMIT_P11_ROM_CALC_TXN_ROUTINES
; P7.09 isolated BASIC-compatible BEEP gateway.
; HL -> five-byte duration, DE -> five-byte pitch.
zx48_rom_beep_values:
    push de
    push hl
    ld hl,4
    add hl,sp
    call zx48_p11_rom_txn_begin
    jr nc,zx48_rom_beep_txn_ready
    pop hl
    pop de
    ret
zx48_rom_beep_txn_ready:
    pop hl
    pop de
    push de
    ld de,ROM_BEEP_STACK
    ld bc,5
    ldir
    pop hl
    ld de,ROM_BEEP_STACK+5
    ld bc,5
    ldir
    ld hl,ROM_BEEP_STACK+10
    ld (ROM_STKEND),hl
    ld hl,zx48_rom_beep_error
    push hl
    ld (ROM_ERR_SP),sp
    ld iy,ROM_IY_ANCHOR
    call zx48_ula_rom_prepare
    call ROM_BEEP_COMMAND
    pop hl
    call zx48_rom_beep_cleanup
    xor a
    ret
zx48_rom_beep_error:
    ld hl,(p11_rom_saved_sp)
    ld sp,hl
    call zx48_rom_beep_cleanup
    ld a,E_INVAL
    scf
    ret
zx48_rom_beep_cleanup:
    call zx48_p11_rom_txn_cleanup
    ld a,(ula_shadow)
    jp zx48_ula_commit
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
    ; Historical public ROMOUT1 expansion used: defs 16-nameLen,0
    ; Compact private descriptor: packed category/class, low flag byte, address,
    ; then the NUL-terminated public name. ROMOUT1 is expanded on lookup.
    db categoryValue*4+classValue,flagsValue
    dw addressValue
    db nameText,0
    ENDM

    MACRO EMIT_P711_ROM_INFO_ROUTINES
; A=category 0..6, B=index, DE=writable 24-byte output. The syscall layer has
; validated the complete request and destination before this lookup executes.
; Resident metadata is packed privately and expanded to exact ROMOUT1 bytes.
zx48_rom_info_lookup:
    cp 7
    jr nc,zx48_rom_info_invalid
    ld c,a
    push de
    pop ix
    ld hl,rom_info_table
zx48_rom_info_scan:
    ld a,(hl)
    or a
    jr z,zx48_rom_info_past_end
    ld d,a
    ld a,c
    or a
    jr z,zx48_rom_info_candidate
    ld a,d
    srl a
    srl a
    cp c
    jr nz,zx48_rom_info_next
zx48_rom_info_candidate:
    ld a,b
    or a
    jr z,zx48_rom_info_publish
    dec b
zx48_rom_info_next:
    ld de,4
    add hl,de
zx48_rom_info_skip_name:
    ld a,(hl)
    inc hl
    or a
    jr nz,zx48_rom_info_skip_name
    jr zx48_rom_info_scan

zx48_rom_info_publish:
    ; Clear the exact public result first; all unspecified bytes remain zero.
    push hl
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,ROMINFO_RECORD_SIZE-1
    ldir
    pop hl

    ; Decode one compact descriptor and publish its NUL-terminated name.
    ld a,(hl)
    ld c,a
    inc hl
    ld a,(hl)
    ld b,a
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    push bc
    push de
    push ix
    pop de
zx48_rom_info_copy_name:
    ld a,(hl)
    or a
    jr z,zx48_rom_info_publish_meta
    ld (de),a
    inc hl
    inc de
    jr zx48_rom_info_copy_name

zx48_rom_info_publish_meta:
    pop de
    ld (ix+16),e
    ld (ix+17),d
    pop bc
    ld a,c
    and 3
    ld (ix+18),a
    ld a,c
    srl a
    srl a
    ld (ix+19),a
    ld (ix+20),b
    ld hl,1
    xor a
    ret

zx48_rom_info_past_end:
    xor a
    ld h,a
    ld l,a
    ret

zx48_rom_info_invalid:
    ld a,E_INVAL
    scf
    ret

; Private compact descriptors expand to exact public ROMOUT1:
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

; P11.18 approved ROM integer/floating conversion gateway.
; Inputs are copied to private bytes before any caller destination is written,
; so the documented request/input/output aliasing contract is atomic.
    MACRO EMIT_P1118_ROM_FP_CAST_ROUTINES
p1118_rom_float          EQU P11_ROM_OP_BASE+0
; HL=u16 source, A=0 unsigned/1 signed, DE=writable five-byte destination.
zx48_p1118_rom_int_to_fp:
    push de
    ex de,hl
    ld c,0
    or a
    jr z,p1118_rom_itof_store
    bit 7,d
    jr z,p1118_rom_itof_store
    ld c,$FF
    ld a,e
    cpl
    ld e,a
    ld a,d
    cpl
    ld d,a
    inc de
p1118_rom_itof_store:
    ld hl,p1118_rom_float
    call ROM_INT_STORE
    pop de
    ld hl,p1118_rom_float
    ld bc,5
    ldir
    xor a
    ld h,a
    ld l,a
    ret
; HL=five-byte source, A=0 unsigned/1 signed, DE=writable u16 destination.
zx48_p1118_rom_fp_to_int:
    push af
    push de
    ld de,p1118_rom_float
    ld bc,5
    ldir
    ld hl,p1118_rom_float
    call ROM_TRUNCATE
    pop de
    pop bc
    ld a,(p1118_rom_float)
    or a
    jr nz,p1118_rom_cast_invalid
    ld a,(p1118_rom_float+4)
    or a
    jr nz,p1118_rom_cast_invalid
    ld a,(p1118_rom_float+1)
    or a
    jr z,p1118_rom_ftoi_positive
    cp $FF
    jr nz,p1118_rom_cast_invalid
    ld a,b
    or a
    jr z,p1118_rom_cast_invalid
    ld a,(p1118_rom_float+3)
    bit 7,a
    jr z,p1118_rom_cast_invalid
    jr p1118_rom_ftoi_publish
p1118_rom_ftoi_positive:
    ld a,b
    or a
    jr z,p1118_rom_ftoi_publish
    ld a,(p1118_rom_float+3)
    bit 7,a
    jr nz,p1118_rom_cast_invalid
p1118_rom_ftoi_publish:
    ld hl,p1118_rom_float+2
    ld bc,2
    ldir
    xor a
    ld h,a
    ld l,a
    ret
p1118_rom_cast_invalid:
    ld a,E_INVAL
    scf
    ret
    ENDM

; P11.19 serialized ROM floating comparison gateway.
; The two caller operands are copied into protected calculator workspace before
; the one-byte caller result is touched, preserving documented alias safety.
    MACRO EMIT_P1119_ROM_FP_CMP_ROUTINES
    EMIT_P11_ROM_CALC_TXN_ROUTINES
P1119_ROM_LT             EQU $0D
P1119_ROM_EQ             EQU $0E
p1119_rom_operands       EQU P11_ROM_OP_BASE+0
; HL=lhs five-byte pointer, DE=rhs five-byte pointer, BC=writable i8 result.
zx48_p1119_rom_fp_cmp:
    exx
    ld hl,0
    add hl,sp
    call zx48_p11_rom_txn_begin
    ret c
    exx
    push bc
    push de
    ld de,p1119_rom_operands
    ld bc,5
    ldir
    pop hl
    ld de,p1119_rom_operands+5
    ld bc,5
    ldir
    ld hl,zx48_p11_rom_invalid_error
    push hl
    ld (ROM_ERR_SP),sp
    ld iy,ROM_IY_ANCHOR
    call p1119_rom_load_operands
    ld b,P1119_ROM_EQ
    call ROM_CALCULATE
    db $3B,$38
    call p1119_rom_bool
    or a
    jr z,p1119_rom_not_equal
    xor a
    jr p1119_rom_success
p1119_rom_not_equal:
    call p1119_rom_load_operands
    ld b,P1119_ROM_LT
    call ROM_CALCULATE
    db $3B,$38
    call p1119_rom_bool
    or a
    ld a,$FF
    jr nz,p1119_rom_success
    ld a,1
p1119_rom_success:
    pop hl
    push af
    call zx48_p11_rom_txn_cleanup
    pop af
    pop hl
    ld (hl),a
    xor a
    ld h,a
    ld l,a
    ret
p1119_rom_load_operands:
    ld hl,p1119_rom_operands
    ld de,ROM_CALC_STACK
    ld bc,10
    ldir
    ld hl,ROM_CALC_STACK+10
    ld (ROM_STKEND),hl
    ret
p1119_rom_bool:
    ld hl,(ROM_STKEND)
    ld de,$FFFB
    add hl,de
    ld b,5
    xor a
p1119_rom_bool_loop:
    or (hl)
    inc hl
    djnz p1119_rom_bool_loop
    ret z
    ld a,1
    ret
    ENDM

; P11.46 isolated ROM-backed floating text formatter. The caller owns all
; user-range validation. This gateway copies the five-byte value into protected
; calculator workspace, redirects RST 10 through a private capture channel, and
; commits caller bytes only after ROM success and a complete capacity check.
    MACRO EMIT_P1146_ROM_FP_TO_TEXT_ROUTINES
    EMIT_P11_ROM_CALC_TXN_ROUTINES
P1146_TEXT_MAX            EQU 14
P1146_TEXT_SCRATCH        EQU 16
P1146_MEM35               EQU $5CA1
P1146_MEM35_SIZE          EQU 15

p1146_text_scratch       EQU P11_ROM_OP_BASE+8
p1146_text_count         EQU P11_ROM_OP_BASE+39
p1146_text_overflow      EQU P11_ROM_OP_BASE+40

p1146_text_channel:
    dw p1146_text_capture
    dw p1146_text_input_stub
    db 'R'

p1146_text_input_stub:
    xor a
    ret

; Called by ROM PRINT-A while its alternate BC/DE/HL bank is live. Preserve that
; bank so PRINT-FP can continue using it between emitted characters.
p1146_text_capture:
    push af
    push bc
    ld c,a
    push de
    push hl
    ld a,(p1146_text_count)
    cp P1146_TEXT_SCRATCH
    jr nc,p1146_text_capture_overflow
    ld e,a
    ld d,0
    ld hl,p1146_text_scratch
    add hl,de
    ld a,c
    ld (hl),a
    ld hl,p1146_text_count
    inc (hl)
    jr p1146_text_capture_done
p1146_text_capture_overflow:
    ld a,1
    ld (p1146_text_overflow),a
p1146_text_capture_done:
    pop hl
    pop de
    pop bc
    pop af
    ret

; HL=five-byte source, DE=destination, BC=capacity. Source and destination
; ranges have already been validated by the syscall surface.
zx48_p1146_rom_fp_to_text:
    push bc
    push de
    push hl
    ld hl,6
    add hl,sp
    call zx48_p11_rom_txn_begin
    jr nc,p1146_text_txn_ready
    pop hl
    pop de
    pop bc
    ret
p1146_text_txn_ready:
    pop hl
    pop de
    pop bc
    push bc
    push de
    xor a
    ld (p1146_text_count),a
    ld (p1146_text_overflow),a
    ld hl,p1146_text_channel
    ld (ROM_CURCHL),hl

    ld de,ROM_CALC_STACK
    ld bc,5
    ldir
    ld hl,ROM_CALC_STACK+5
    ld (ROM_STKEND),hl

    ld hl,p1146_text_error
    push hl
    ld (ROM_ERR_SP),sp
    ld iy,ROM_IY_ANCHOR
    call ROM_FP_PRINT
    pop hl

    ld a,(p1146_text_overflow)
    or a
    jr nz,p1146_text_internal_overflow
    call p1146_text_cleanup
    pop ix
    pop bc

    ld a,(p1146_text_count)
    ld e,a
    ld d,0
    inc de
    ld h,b
    ld l,c
    or a
    sbc hl,de
    jr c,p1146_text_nospc

    ld a,(p1146_text_count)
    ld c,a
    ld b,0
    ld hl,p1146_text_scratch
    push ix
    pop de
    ldir
    xor a
    ld (de),a
    ld a,(p1146_text_count)
    ld l,a
    ld h,0
    xor a
    ret

p1146_text_internal_overflow:
    call p1146_text_cleanup
    pop de
    pop bc
    ld a,E_FORMAT
    scf
    ret

p1146_text_nospc:
    ld a,E_NOSPC
    scf
    ret

p1146_text_error:
    ld hl,(p11_rom_saved_sp)
    ld sp,hl
    call p1146_text_cleanup
    ld a,E_INVAL
    scf
    ret

p1146_text_cleanup:
    jp zx48_p11_rom_txn_cleanup

    ENDM

; P11.47 exact bounded decimal-text to Spectrum five-byte floating gateway.
; The public syscall validates the complete grammar and all user ranges first.
; Only the unsigned decimal token is copied into private kernel storage; the ROM
; decimal parser never sees BASIC statements, tokens, or caller memory beyond BC.
    MACRO EMIT_P1147_ROM_FP_FROM_TEXT_ROUTINES
    EMIT_P11_ROM_CALC_TXN_ROUTINES
P1147_TEXT_MAX            EQU 255
P1147_TEXT_SCRATCH        EQU 256
P1147_MEM_WORK_SIZE       EQU 30

p1147_text_sign          EQU P11_ROM_OP_BASE+6
p1147_text_calc_mem      EQU P11_ROM_OP_BASE+7
p1147_text_scratch       EQU P11_ROM_OP_BASE+37

; A=0 positive / 1 negative, HL=unsigned decimal token, BC=exact token length,
; DE=writable five-byte destination. Grammar/ranges are already validated.
zx48_p1147_rom_fp_from_text:
    push af
    push bc
    push de
    push hl
    ld hl,8
    add hl,sp
    call zx48_p11_rom_txn_begin
    jr nc,p1147_text_txn_ready
    pop hl
    pop de
    pop bc
    pop af
    ret
p1147_text_txn_ready:
    pop hl
    pop de
    pop bc
    pop af
    ld (p1147_text_sign),a
    push de

    ; Freeze caller bytes before any ROM entry so output may alias input safely.
    ld de,p1147_text_scratch
    ldir
    ; GET-CHAR skips control bytes, including NUL. Use a printable punctuation
    ; sentinel that DEC-TO-FP returns on without interpreting as numeric syntax.
    ld a,':'
    ld (de),a

    ld hl,p1147_text_calc_mem
    ld (ROM_MEM),hl
    ld hl,p1147_text_scratch
    ld (ROM_CH_ADD),hl

    ld hl,zx48_p11_rom_invalid_error
    push hl
    ld (ROM_ERR_SP),sp
    ld iy,ROM_IY_ANCHOR
    ld hl,p1147_text_scratch
    ld a,(hl)
    call ROM_DEC_TO_FP
    ld a,(p1147_text_sign)
    or a
    jr z,p1147_text_sign_done
    call ROM_CALCULATE
    db $1B,$38
p1147_text_sign_done:
    pop hl

    pop de
    ld hl,(ROM_STKEND)
    ld bc,5
    or a
    sbc hl,bc
    ldir
    call zx48_p11_rom_txn_cleanup
    xor a
    ld h,a
    ld l,a
    ret


    ENDM
