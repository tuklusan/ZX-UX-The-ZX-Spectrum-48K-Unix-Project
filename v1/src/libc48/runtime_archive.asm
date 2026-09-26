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
; P10.22 compact built-in runtime archive.
; Member order is frozen here: crt0, write, puts, exit.
; crt0 is the mandatory default first module unless -nostart is active.
; Runtime archive scans begin after crt0. Deliberately placing write before puts
; makes puts -> write require a repeated fixed-order scan, proving the later
; P10.23 fixed-point contract without changing archive order.

P10_RUNTIME_MEMBER_COUNT EQU 4
P10_RUNTIME_FIRST_LIBRARY_MEMBER EQU 1

    MACRO EMIT_P10_RUNTIME_ARCHIVE
p10_runtime_archive:
    db 'L','A','R','1'
    db P10_RUNTIME_MEMBER_COUNT
    db 0
    dw p10_runtime_archive_table_end-p10_runtime_archive_table
p10_runtime_archive_table:
    dw p10_crt0_obj
    dw p10_crt0_obj_end-p10_crt0_obj
    dw p10_runtime_write_obj
    dw p10_runtime_write_obj_end-p10_runtime_write_obj
    dw p10_runtime_puts_obj
    dw p10_runtime_puts_obj_end-p10_runtime_puts_obj
    dw p10_runtime_exit_obj
    dw p10_runtime_exit_obj_end-p10_runtime_exit_obj
p10_runtime_archive_table_end:

p10_runtime_write_obj:
    db $4F,$42,$4A,$31,$01,$00,$18,$00,$04,$00,$00,$00,$01,$00,$00,$00
    db $1C,$00,$30,$00,$73,$0D,$23,$F3,$21,$00,$00,$C9,$77,$72,$69,$74
    db $65,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$01,$01
p10_runtime_write_obj_end:

p10_runtime_puts_obj:
    db $4F,$42,$4A,$31,$01,$00,$18,$00,$04,$00,$00,$00,$02,$00,$01,$00
    db $1C,$00,$44,$00,$B2,$33,$70,$C1,$CD,$00,$00,$C9,$70,$75,$74,$73
    db $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$01,$01
    db $77,$72,$69,$74,$65,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    db $00,$00,$00,$01,$01,$00,$01,$00,$01,$00
p10_runtime_puts_obj_end:

p10_runtime_exit_obj:
    db $4F,$42,$4A,$31,$01,$00,$18,$00,$01,$00,$00,$00,$01,$00,$00,$00
    db $19,$00,$2D,$00,$5B,$BC,$EE,$BC,$C9,$65,$78,$69,$74,$00,$00,$00
    db $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$01,$01
p10_runtime_exit_obj_end:
p10_runtime_archive_end:
    ENDM

; A=member index. Success HL=OBJ1 member pointer, BC=exact stored length.
; Invalid index returns carry with E_INVAL.
    MACRO EMIT_P10_RUNTIME_ARCHIVE_ROUTINES
ld_p1022_archive_get:
    cp P10_RUNTIME_MEMBER_COUNT
    jp nc,ld_p1022_archive_bad
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld de,p10_runtime_archive_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    xor a
    ret
ld_p1022_archive_bad:
    ld a,E_INVAL
    scf
    ret
    ENDM

; P11.23 native libc48 object/handle archive surface.
; P10 archive bytes above remain frozen. This table binds every P11.23 public
; symbol to its target-native implementation until the later OBJ1 archive
; materialization steps consume the same canonical symbol set.
P1123_LIBC48_IO_SYMBOL_COUNT EQU 15

    MACRO EMIT_P1123_LIBC48_IO_ARCHIVE
p1123_libc48_io_table:
    dw open
    dw open_typed
    dw close
    dw read
    dw write
    dw seek
    dw stat
    dw remove
    dw rename
    dw list
    dw pipe
    dw dup
    dw ioctl
    dw read_full
    dw write_full
p1123_libc48_io_table_end:
    ASSERT (p1123_libc48_io_table_end-p1123_libc48_io_table)/2 = P1123_LIBC48_IO_SYMBOL_COUNT

p1123_libc48_io_names:
    db "open",0
    db "open_typed",0
    db "close",0
    db "read",0
    db "write",0
    db "seek",0
    db "stat",0
    db "remove",0
    db "rename",0
    db "list",0
    db "pipe",0
    db "dup",0
    db "ioctl",0
    db "read_full",0
    db "write_full",0
    ENDM

