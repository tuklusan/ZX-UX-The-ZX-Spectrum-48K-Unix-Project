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

; P11.35 target-native lifecycle archive.
; P10 bytes above remain frozen.  This overlay keeps the same member IDs/order
; while replacing only the C48 puts member with a real target-native stdout
; implementation for native cc -> OBJ1 -> ld -> executable lifecycle proof.
P1135_RUNTIME_MEMBER_COUNT EQU 4

    MACRO EMIT_P1135_C48_RUNTIME_ARCHIVE
p1135_runtime_archive:
    db 'L','A','R','1'
    db P1135_RUNTIME_MEMBER_COUNT
    db 0
    dw p1135_runtime_archive_table_end-p1135_runtime_archive_table
p1135_runtime_archive_table:
    dw p10_crt0_obj
    dw p10_crt0_obj_end-p10_crt0_obj
    dw p10_runtime_write_obj
    dw p10_runtime_write_obj_end-p10_runtime_write_obj
    dw p1135_runtime_puts_obj
    dw p1135_runtime_puts_obj_end-p1135_runtime_puts_obj
    dw p10_runtime_exit_obj
    dw p10_runtime_exit_obj_end-p10_runtime_exit_obj
p1135_runtime_archive_table_end:

; OBJ1 puts(char *).  The code is position independent except for the frozen
; syscall gateway at E000.  It writes the whole NUL-terminated byte string and
; then one LF.  No host service participates.
p1135_runtime_puts_obj:
    db $4F,$42,$4A,$31,$01,$00,$18,$00,$36,$00,$00,$00,$01,$00,$00,$00
    db $4E,$00,$62,$00,$DD,$AB,$52,$2E
    db $E5,$01,$00,$00,$7E,$B7,$28,$04,$23,$03,$18,$F8,$E1,$11,$01,$00
    db $3E,$13,$CD,$00,$E0,$38,$1A,$21,$0A,$00,$E5,$21,$00,$00,$39,$11
    db $01,$00,$01,$01,$00,$3E,$13,$CD,$00,$E0,$C1,$38,$04,$21,$00,$00
    db $C9,$6F,$26,$00,$B7,$C9
    db "puts",0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 1,1
p1135_runtime_puts_obj_end:
    ENDM

; A=member ID 0..3. Success HL=OBJ1 pointer, BC=stored length.
    MACRO EMIT_P1135_C48_RUNTIME_ARCHIVE_ROUTINES
ld_p1135_archive_get:
    cp P1135_RUNTIME_MEMBER_COUNT
    jr nc,ld_p1135_archive_bad
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld de,p1135_runtime_archive_table
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
ld_p1135_archive_bad:
    ld a,E_INVAL
    scf
    ret
    ENDM

; P11.36 native graphics/UDG archive members used by target-native cc/ld proof.
; Each member is valid OBJ1 and calls only the frozen syscall gateway.
P1136_GRAPHICS_MEMBER_COUNT EQU 3

    MACRO EMIT_P1136_GRAPHICS_ARCHIVE
p1136_graphics_archive:
    db 'L','A','R','1'
    db P1136_GRAPHICS_MEMBER_COUNT
    db 0
    dw p1136_graphics_archive_table_end-p1136_graphics_archive_table
p1136_graphics_archive_table:
    dw p1136_ink_obj
    dw p1136_ink_obj_end-p1136_ink_obj
    dw p1136_plot_obj
    dw p1136_plot_obj_end-p1136_plot_obj
    dw p1136_udg_clear_obj
    dw p1136_udg_clear_obj_end-p1136_udg_clear_obj
p1136_graphics_archive_table_end:

p1136_ink_obj:
    db $4F,$42,$4A,$31,$01,$00,$18,$00,$1D,$00,$00,$00,$01,$00,$00,$00
    db $35,$00,$49,$00,$FA,$0B,$78,$DA,$7C,$B7,$20,$0F,$16,$00,$62,$3E
    db $43,$CD,$00,$E0,$38,$0A,$21,$00,$00,$AF,$C9,$21,$01,$00,$AF,$C9
    db $6F,$26,$00,$B7,$C9,$69,$6E,$6B,$00,$00,$00,$00,$00,$00,$00,$00
    db $00,$00,$00,$00,$00,$00,$00,$01,$01
p1136_ink_obj_end:

p1136_plot_obj:
    db $4F,$42,$4A,$31,$01,$00,$18,$00,$1C,$00,$00,$00,$01,$00,$00,$00
    db $34,$00,$48,$00,$58,$E6,$51,$95,$7C,$B2,$20,$0E,$65,$6B,$3E,$40
    db $CD,$00,$E0,$38,$0A,$21,$00,$00,$AF,$C9,$21,$01,$00,$AF,$C9,$6F
    db $26,$00,$B7,$C9,$70,$6C,$6F,$74,$00,$00,$00,$00,$00,$00,$00,$00
    db $00,$00,$00,$00,$00,$00,$01,$01
p1136_plot_obj_end:

p1136_udg_clear_obj:
    db $4F,$42,$4A,$31,$01,$00,$18,$00,$1A,$00,$00,$00,$01,$00,$00,$00
    db $32,$00,$46,$00,$AA,$82,$0C,$60,$7C,$B7,$20,$0C,$3E,$4B,$CD,$00
    db $E0,$38,$0A,$21,$00,$00,$AF,$C9,$21,$01,$00,$AF,$C9,$6F,$26,$00
    db $B7,$C9,$75,$64,$67,$5F,$63,$6C,$65,$61,$72,$00,$00,$00,$00,$00
    db $00,$00,$00,$00,$01,$01
p1136_udg_clear_obj_end:
    ENDM

    MACRO EMIT_P1136_GRAPHICS_ARCHIVE_ROUTINES
ld_p1136_archive_get:
    cp P1136_GRAPHICS_MEMBER_COUNT
    jr nc,ld_p1136_archive_bad
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld de,p1136_graphics_archive_table
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
ld_p1136_archive_bad:
    ld a,E_INVAL
    scf
    ret
    ENDM
