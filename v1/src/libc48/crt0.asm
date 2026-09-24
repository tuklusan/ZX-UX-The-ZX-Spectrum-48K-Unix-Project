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
; P10.22 built-in crt0 OBJ1 member.
; _start calls main, then exit. Relocations remain ordinary OBJ1 ABS16 records
; until the native linker assigns final module bases.

    MACRO EMIT_P10_CRT0_OBJ1
p10_crt0_obj:
    db $4F,$42,$4A,$31,$01,$00,$18,$00,$07,$00,$00,$00,$03,$00,$02,$00
    db $1F,$00,$5B,$00,$51,$2E,$71,$92,$CD,$00,$00,$CD,$00,$00,$C9,$5F
    db $73,$74,$61,$72,$74,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    db $00,$01,$01,$6D,$61,$69,$6E,$00,$00,$00,$00,$00,$00,$00,$00,$00
    db $00,$00,$00,$00,$00,$00,$01,$65,$78,$69,$74,$00,$00,$00,$00,$00
    db $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$01,$01,$00,$01,$00,$01
    db $00,$04,$00,$02,$00,$01,$00
p10_crt0_obj_end:
    ENDM
