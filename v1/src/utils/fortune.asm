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

    MACRO EMIT_P832_FORTUNE_ROUTINES
fortune_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr nz,fortune_bad
    ld hl,fortune_ticks
    ld a,SYS_TICKS
    call SYSCALL_GATEWAY
    jr c,fortune_exit_a
    ld a,(fortune_ticks)
    and 3
    add a,a
    ld e,a
    ld d,0
    ld hl,fortune_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    call fortune_write_z
    jr c,fortune_exit_a
    xor a
    jr fortune_exit_a
fortune_bad:
    ld a,E_INVAL
fortune_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

fortune_write_z:
    push hl
    ld bc,0
fortune_count:
    ld a,(hl)
    or a
    jr z,fortune_count_done
    inc hl
    inc bc
    jr fortune_count
fortune_count_done:
    pop hl
fortune_write_all:
    ld (fortune_ptr),hl
    ld (fortune_left),bc
fortune_write_loop:
    ld hl,(fortune_ptr)
    ld bc,(fortune_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,fortune_io
    ld (fortune_wrote),hl
    ld de,(fortune_ptr)
    add hl,de
    ld (fortune_ptr),hl
    ld hl,(fortune_left)
    ld de,(fortune_wrote)
    or a
    sbc hl,de
    jr c,fortune_io
    ld (fortune_left),hl
    ld a,h
    or l
    jr nz,fortune_write_loop
    xor a
    ret
fortune_io:
    ld a,E_IO
    scf
    ret

fortune_table:
    dw fortune0,fortune1,fortune2,fortune3
fortune0: db 'T','h','e',' ','Z','8','0',' ','h','a','s',' ','n','o',' ','t','i','m','e',' ','f','o','r',' ','b','l','o','a','t','.',10,0
fortune1: db 'T','a','p','e',' ','i','s',' ','s','l','o','w',';',' ','p','a','t','i','e','n','c','e',' ','i','s',' ','f','a','s','t','.',10,0
fortune2: db 'F','o','r','t','y','-','e','i','g','h','t',' ','K',' ','i','s',' ','a',' ','d','e','s','i','g','n',' ','r','e','v','i','e','w','.',10,0
fortune3: db 'U','n','i','x',' ','i','d','e','a','s',',',' ','S','p','e','c','t','r','u','m',' ','h','a','r','d','w','a','r','e','.',10,0
fortune_ticks: defs 4,0
fortune_ptr: dw 0
fortune_left: dw 0
fortune_wrote: dw 0
    ENDM
