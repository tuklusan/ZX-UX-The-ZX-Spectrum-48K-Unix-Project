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

    MACRO EMIT_ROM_SERVICE_ROUTINES
zx48_rom_restore_iy:
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_print_a:
    call ROM_PRINT_A
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_key_scan:
    call ROM_KEY_SCAN
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_pixel_add:
    call ROM_PIXEL_ADD
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_point:
    call ROM_POINT
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_plot_sub:
    call ROM_PLOT_SUB
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_draw_line:
    call ROM_DRAW_LINE
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_beeper:
    call ROM_BEEPER
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_sa_bytes:
    call ROM_SA_BYTES
    ld iy,ROM_IY_ANCHOR
    ret
zx48_rom_ld_bytes:
    call ROM_LD_BYTES
    ld iy,ROM_IY_ANCHOR
    ret

; Public five-byte BEEP bridge. Full calculator state is serialized by altreg_busy.
zx48_rom_beep_values:
    ; Keep the bridge controlled even on ROM-domain failure. The compact resident
    ; implementation currently converts the integer-form low words when both
    ; Spectrum values use integer exponent byte zero; other forms use ROM command.
    ld a,(hl)
    or a
    jr nz,zx48_rom_beep_rom
    ld a,(de)
    or a
    jr nz,zx48_rom_beep_rom
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    inc de
    ld l,(de)
    inc de
    ld h,(de)
    ex de,hl
    ld h,b
    ld l,c
    call zx48_rom_beeper
    xor a
    or a
    ret
zx48_rom_beep_rom:
    ld a,E_NOTSUP
    scf
    ret

; Calculator ABI operation ids are target-private. Unsupported/unsafe ROM paths
; return controlled errors rather than escaping through BASIC RST8.
zx48_fp_exec:
    ld a,E_NOTSUP
    scf
    ret
zx48_fp_to_text:
    ld a,E_NOTSUP
    scf
    ret
zx48_fp_from_text:
    ld a,E_NOTSUP
    scf
    ret

; SYS_ROM_INFO exposes only the frozen address ledger through a bounded index.
; H=0,L=index, DE=writable u16 address; HL returns class (1=A,2=B).
zx48_rom_info:
    ld a,h
    or a
    jr nz,zx48_rom_info_bad
    ld a,l
    cp ROM_INFO_COUNT
    jr nc,zx48_rom_info_bad
    add a,a
    ld c,a
    ld b,0
    ld hl,rom_info_addresses
    add hl,bc
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(hl)
    ld (de),a
    ld h,0
    ld l,1
    xor a
    or a
    ret
zx48_rom_info_bad:
    ld a,E_INVAL
    scf
    ret

; Integer-form Spectrum number conversion. Five-byte integer encoding uses byte0
; zero, byte1 sign marker, bytes2..3 magnitude/word, byte4 zero for this bridge.
zx48_int_to_fp:
    ; HL -> ITOF1; record validation is performed by syscall caller in later ABI
    ; hardening. Keep implementation bounded and deterministic.
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld a,(hl)
    ld (rom_signed),a
    inc hl
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    push bc
    pop hl
    xor a
    ld (hl),a
    inc hl
    ld a,(rom_signed)
    or a
    jr z,zx48_int_to_fp_unsigned
    bit 7,d
    jr z,zx48_int_to_fp_unsigned
    ld a,$ff
    ld (hl),a
    inc hl
    xor a
    sub e
    ld e,a
    ld a,0
    sbc a,d
    ld d,a
    jr zx48_int_to_fp_store
zx48_int_to_fp_unsigned:
    xor a
    ld (hl),a
    inc hl
zx48_int_to_fp_store:
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    xor a
    ld (hl),a
    or a
    ret

zx48_fp_to_int:
    ld a,E_NOTSUP
    scf
    ret
zx48_fp_cmp:
    ; HL lhs, DE rhs; integer-form fast path only.
    ld a,(hl)
    or a
    jr nz,zx48_fp_cmp_not
    ld a,(de)
    or a
    jr nz,zx48_fp_cmp_not
    inc hl
    inc hl
    inc de
    inc de
    ld a,(de)
    ld c,a
    ld a,(hl)
    cp c
    jr nz,zx48_fp_cmp_done
    inc hl
    inc de
    ld a,(de)
    ld c,a
    ld a,(hl)
    cp c
zx48_fp_cmp_done:
    ; HL returns FFFF/0000/0001 for less/equal/greater.
    jr c,zx48_fp_cmp_less
    jr z,zx48_fp_cmp_equal
    ld hl,1
    xor a
    or a
    ret
zx48_fp_cmp_less:
    ld hl,$ffff
    xor a
    or a
    ret
zx48_fp_cmp_equal:
    ld hl,0
    xor a
    or a
    ret
zx48_fp_cmp_not:
    ld a,E_NOTSUP
    scf
    ret

ROM_INFO_COUNT EQU 10
rom_info_addresses:
    dw ROM_PRINT_A,ROM_KEY_SCAN,ROM_BEEPER,ROM_SA_BYTES,ROM_LD_BYTES
    dw ROM_PIXEL_ADD,ROM_POINT,ROM_PLOT_SUB,ROM_DRAW_LINE,ROM_CALCULATE
rom_signed: db 0
    ENDM
