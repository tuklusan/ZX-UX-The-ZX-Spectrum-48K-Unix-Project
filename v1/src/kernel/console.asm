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
; OS-owned 32/64-column console state. No BASIC line editor is entered.

TTY_MODE_32              EQU 32
TTY_MODE_64              EQU 64
TTY_REQ_GET_MODE         EQU 1
TTY_REQ_SET_MODE         EQU 2
TTY_REQ_GET_SIZE         EQU 3
TTY_REQ_SET_CURSOR       EQU 4
TTY_REQ_GET_CURSOR       EQU 5
TTY_REQ_GET_OWNER        EQU 6
TTY_REQ_SET_OWNER        EQU 7

CONSOLE_STATE_BASE       EQU CURSOR_STATE_END
console_count            EQU CONSOLE_STATE_BASE+0
tty_mode                 EQU CONSOLE_STATE_BASE+2
tty_row                  EQU CONSOLE_STATE_BASE+3
tty_col                  EQU CONSOLE_STATE_BASE+4
tty_cursor_shape         EQU CONSOLE_STATE_BASE+5
tty_cursor_visible       EQU CONSOLE_STATE_BASE+6
tty_cursor_due           EQU CONSOLE_STATE_BASE+7
CONSOLE_STATE_END        EQU CONSOLE_STATE_BASE+8

    MACRO EMIT_CONSOLE_ROUTINES
zx48_console_init:
    ld a,TTY_MODE_64
    ld (tty_mode),a
    ld a,TTY_CURSOR_UNDERLINE
    ld (tty_cursor_shape),a
    xor a
    ld (tty_row),a
    ld (tty_col),a
    ld (tty_cursor_visible),a
    ld (tty_cursor_due),a
    ret

zx48_console_clear:
    call zx48_cursor_hide
    xor a
    ld hl,BITMAP_START
    ld de,BITMAP_START+1
    ld bc,SCREEN_IMAGE_SIZE-1
    ld (hl),a
    ldir
    ld a,7
    ld hl,ATTR_START
    ld de,ATTR_START+1
    ld bc,ATTR_END-ATTR_START
    ld (hl),a
    ldir
    xor a
    ld (tty_row),a
    ld (tty_col),a
    jp zx48_cursor_show

; H=row,L=column.
zx48_console_setpos:
    ld a,h
    cp 24
    jr nc,zx48_console_bad
    ld a,(tty_mode)
    cp TTY_MODE_64
    jr z,zx48_console_set64
    ld a,l
    cp 32
    jr nc,zx48_console_bad
    jr zx48_console_set_commit
zx48_console_set64:
    ld a,l
    cp 64
    jr nc,zx48_console_bad
zx48_console_set_commit:
    call zx48_cursor_hide
    ld a,h
    ld (tty_row),a
    ld a,l
    ld (tty_col),a
    call zx48_cursor_show
    xor a
    ret
zx48_console_bad:
    ld a,E_INVAL
    scf
    ret

zx48_console_getpos:
    ld a,(tty_row)
    ld h,a
    ld a,(tty_col)
    ld l,a
    xor a
    ret

; A=byte.
zx48_console_putchar:
    cp $20
    jr nc,zx48_console_print
    cp $0a
    jr z,zx48_console_lf
    cp $0d
    jr z,zx48_console_cr
    cp $08
    jr z,zx48_console_bs
    cp $09
    jr z,zx48_console_tab
    cp $0c
    jp z,zx48_console_clear
    xor a
    ret
zx48_console_print:
    call zx48_cursor_hide
    push af
    ld a,(tty_mode)
    cp TTY_MODE_64
    jr z,zx48_console_print64
    pop af
    call zx48_tty32_draw_char
    jr zx48_console_advance
zx48_console_print64:
    pop af
    call zx48_tty64_draw_char
zx48_console_advance:
    ld a,(tty_col)
    inc a
    ld b,a
    ld a,(tty_mode)
    cp TTY_MODE_64
    ld a,b
    jr z,zx48_console_adv64
    cp 32
    jr c,zx48_console_store_col
    jr zx48_console_next_row
zx48_console_adv64:
    cp 64
    jr c,zx48_console_store_col
zx48_console_next_row:
    xor a
    ld (tty_col),a
    ld a,(tty_row)
    inc a
    cp 24
    jr c,zx48_console_store_row
    call zx48_console_scroll
    ld a,23
zx48_console_store_row:
    ld (tty_row),a
    jp zx48_cursor_show
zx48_console_store_col:
    ld (tty_col),a
    jp zx48_cursor_show
zx48_console_lf:
    call zx48_cursor_hide
    xor a
    ld (tty_col),a
    jr zx48_console_next_row
zx48_console_cr:
    call zx48_cursor_hide
    xor a
    ld (tty_col),a
    jp zx48_cursor_show
zx48_console_bs:
    ld a,(tty_col)
    or a
    ret z
    call zx48_cursor_hide
    ld a,(tty_col)
    dec a
    ld (tty_col),a
    jp zx48_cursor_show
zx48_console_tab:
    ld a,(tty_col)
    and $f8
    add a,8
    ld b,a
    ld a,(tty_mode)
    cp TTY_MODE_64
    ld a,b
    jr z,zx48_console_tab64
    cp 32
    jr nc,zx48_console_next_row
    jr zx48_console_store_col
zx48_console_tab64:
    cp 64
    jr nc,zx48_console_next_row
    jr zx48_console_store_col

; HL=buffer,BC=count; returns HL=bytes written.
zx48_console_write:
    ld (console_count),bc
zx48_console_write_loop:
    ld a,b
    or c
    jr z,zx48_console_write_done
    ld a,(hl)
    push hl
    push bc
    call zx48_console_putchar
    pop bc
    pop hl
    ret c
    inc hl
    dec bc
    jr zx48_console_write_loop
zx48_console_write_done:
    ld hl,(console_count)
    xor a
    ret

zx48_console_scroll:
    call zx48_tty_scroll_bitmap
    ld hl,ATTR_START+32
    ld de,ATTR_START
    ld bc,23*32
    ldir
    ld hl,ATTR_START+23*32
    ld b,32
    ld a,7
zx48_console_clear_attr_row:
    ld (hl),a
    inc hl
    djnz zx48_console_clear_attr_row
    ret

; HL -> {handle,request,arg_ptr}; caller verified tty handle.
zx48_tty_ioctl:
    inc hl
    ld a,(hl)
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    cp TTY_REQ_GET_MODE
    jr z,zx48_tty_get_mode
    cp TTY_REQ_SET_MODE
    jr z,zx48_tty_set_mode
    cp TTY_REQ_GET_SIZE
    jr z,zx48_tty_get_size
    cp TTY_REQ_SET_CURSOR
    jr z,zx48_tty_set_cursor
    cp TTY_REQ_GET_CURSOR
    jr z,zx48_tty_get_cursor
    cp TTY_REQ_GET_OWNER
    jr z,zx48_tty_get_owner
    cp TTY_REQ_SET_OWNER
    jr z,zx48_tty_set_owner
    ld a,E_NOTSUP
    scf
    ret
zx48_tty_get_mode:
    ld a,(tty_mode)
    ld (de),a
    jr zx48_tty_ok
zx48_tty_set_mode:
    ld a,(de)
    cp TTY_MODE_32
    jr z,zx48_tty_mode_ok
    cp TTY_MODE_64
    jr nz,zx48_tty_bad
zx48_tty_mode_ok:
    ld b,a
    call zx48_cursor_hide
    ld a,b
    ld (tty_mode),a
    call zx48_console_clear
    jr zx48_tty_ok
zx48_tty_get_size:
    ld a,(tty_mode)
    ld (de),a
    inc de
    ld a,24
    ld (de),a
    jr zx48_tty_ok
zx48_tty_set_cursor:
    ld a,(de)
    cp 3
    jr nc,zx48_tty_bad
    ld b,a
    call zx48_cursor_hide
    ld a,b
    ld (tty_cursor_shape),a
    call zx48_cursor_show
    jr zx48_tty_ok
zx48_tty_get_cursor:
    ld a,(tty_cursor_shape)
    ld (de),a
    jr zx48_tty_ok
zx48_tty_get_owner:
    ld a,(tty_input_owner)
    ld (de),a
    jr zx48_tty_ok
zx48_tty_set_owner:
    ld a,(current_pid)
    cp 1
    jr nz,zx48_tty_perm
    ld a,(de)
    cp MAX_PROCESSES
    jr nc,zx48_tty_bad
    or a
    jr z,zx48_tty_set_owner_commit
    push de
    call zx48_process_live_lookup
    pop de
    ret c
    ld a,(de)
zx48_tty_set_owner_commit:
    ld (tty_input_owner),a
zx48_tty_ok:
    xor a
    ret
zx48_tty_bad:
    ld a,E_INVAL
    scf
    ret
zx48_tty_perm:
    ld a,E_PERM
    scf
    ret
    ENDM
