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
; P8.23 exact public stty subset.

    MACRO EMIT_P823_STTY_ROUTINES
TTY_REQ_GET_MODE         EQU 1
TTY_REQ_SET_MODE         EQU 2
TTY_REQ_SET_CURSOR       EQU 4
TTY_REQ_GET_CURSOR       EQU 5

stty_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr z,stty_show
    cp 3
    jp nz,stty_bad
    ld de,8
    add ix,de
stty_skip_argv0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,stty_skip_argv0
    push ix
    pop hl
    call stty_match_cols
    jr nc,stty_set_cols
    push ix
    pop hl
    call stty_match_cursor
    jr nc,stty_set_cursor
    jp stty_bad

stty_show:
    call stty_open
    jp c,stty_exit_error
    ld a,TTY_REQ_GET_MODE
    ld hl,stty_mode
    call stty_ioctl
    jp c,stty_close_error
    ld a,TTY_REQ_GET_CURSOR
    ld hl,stty_cursor
    call stty_ioctl
    jp c,stty_close_error
    call stty_close
    jp c,stty_exit_error
    ld hl,stty_cols_prefix
    call stty_write_z
    jp c,stty_exit_error
    ld a,(stty_mode)
    cp 64
    jr z,stty_show_64
    ld hl,stty_32
    jr stty_show_mode
stty_show_64:
    ld hl,stty_64
stty_show_mode:
    call stty_write_z
    jp c,stty_exit_error
    ld hl,stty_rows_cursor
    call stty_write_z
    jp c,stty_exit_error
    ld a,(stty_cursor)
    or a
    jr z,stty_show_off
    cp 1
    jr z,stty_show_under
    ld hl,stty_block
    jr stty_show_cursor
stty_show_under:
    ld hl,stty_underline
    jr stty_show_cursor
stty_show_off:
    ld hl,stty_off
stty_show_cursor:
    call stty_write_z
    jp c,stty_exit_error
    ld hl,stty_lf
    ld bc,1
    call stty_write_all
    jp c,stty_exit_error
    xor a
    jp stty_exit_a

stty_set_cols:
    push ix
    pop hl
    call stty_advance_word
    ld a,(hl)
    cp '6'
    jr z,stty_cols64
    cp '3'
    jr z,stty_cols32
    jp stty_bad
stty_cols64:
    inc hl
    ld a,(hl)
    cp '4'
    jp nz,stty_bad
    inc hl
    ld a,(hl)
    or a
    jp nz,stty_bad
    ld a,64
    jr stty_apply_mode
stty_cols32:
    inc hl
    ld a,(hl)
    cp '2'
    jp nz,stty_bad
    inc hl
    ld a,(hl)
    or a
    jp nz,stty_bad
    ld a,32
stty_apply_mode:
    ld (stty_mode),a
    call stty_open
    jp c,stty_exit_error
    ld a,TTY_REQ_SET_MODE
    ld hl,stty_mode
    call stty_ioctl
    jr c,stty_close_error
    call stty_close
    jp c,stty_exit_error
    xor a
    jp stty_exit_a

stty_set_cursor:
    push ix
    pop hl
    call stty_advance_word
    ld a,(hl)
    cp 'b'
    jr z,stty_cursor_block
    cp 'u'
    jr z,stty_cursor_under
    cp 'o'
    jr z,stty_cursor_off
    jp stty_bad
stty_cursor_block:
    ld de,stty_word_block
    call stty_eq_z
    jp c,stty_bad
    ld a,2
    jr stty_apply_cursor
stty_cursor_under:
    ld de,stty_word_underline
    call stty_eq_z
    jp c,stty_bad
    ld a,1
    jr stty_apply_cursor
stty_cursor_off:
    ld de,stty_word_off
    call stty_eq_z
    jp c,stty_bad
    xor a
stty_apply_cursor:
    ld (stty_cursor),a
    call stty_open
    jp c,stty_exit_error
    ld a,TTY_REQ_SET_CURSOR
    ld hl,stty_cursor
    call stty_ioctl
    jr c,stty_close_error
    call stty_close
    jp c,stty_exit_error
    xor a
    jp stty_exit_a

stty_bad:
    ld a,E_INVAL
    jr stty_exit_a
stty_close_error:
    ld (stty_errno),a
    call stty_close
    ld a,(stty_errno)
stty_exit_error:
stty_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

stty_open:
    ld hl,stty_tty
    ld c,O_READ|O_WRITE
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,stty_open_bad
    ld a,l
    ld (stty_handle),a
    xor a
    ret
stty_open_bad:
    ld a,E_FORMAT
    scf
    ret
stty_close:
    ld a,(stty_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    jp SYSCALL_GATEWAY
stty_ioctl:
    ld (stty_req+1),a
    ld (stty_req+2),hl
    ld a,(stty_handle)
    ld (stty_req),a
    ld hl,stty_req
    ld a,SYS_IOCTL
    jp SYSCALL_GATEWAY

stty_match_cols:
    ld de,stty_word_cols
    jp stty_eq_z
stty_match_cursor:
    ld de,stty_word_cursor
stty_eq_z:
    ld a,(de)
    cp (hl)
    jr nz,stty_eq_no
    or a
    ret z
    inc de
    inc hl
    jr stty_eq_z
stty_eq_no:
    scf
    ret
stty_advance_word:
    ld a,(hl)
    inc hl
    or a
    jr nz,stty_advance_word
    ret

stty_write_z:
    push hl
    ld bc,0
stty_write_z_count:
    ld a,(hl)
    or a
    jr z,stty_write_z_ready
    inc hl
    inc bc
    jr stty_write_z_count
stty_write_z_ready:
    pop hl
stty_write_all:
    ld (stty_wptr),hl
    ld (stty_wleft),bc
stty_write_loop:
    ld hl,(stty_wptr)
    ld bc,(stty_wleft)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,stty_write_zero
    ld (stty_wrote),hl
    ld de,(stty_wptr)
    add hl,de
    ld (stty_wptr),hl
    ld hl,(stty_wleft)
    ld de,(stty_wrote)
    or a
    sbc hl,de
    jr c,stty_write_zero
    ld (stty_wleft),hl
    ld a,h
    or l
    jr nz,stty_write_loop
    xor a
    ret
stty_write_zero:
    ld a,E_IO
    scf
    ret

stty_word_cols: db 'c','o','l','s',0
stty_word_cursor: db 'c','u','r','s','o','r',0
stty_word_block: db 'b','l','o','c','k',0
stty_word_underline: db 'u','n','d','e','r','l','i','n','e',0
stty_word_off: db 'o','f','f',0
stty_tty: db '/','d','e','v','/','t','t','y',0
stty_cols_prefix: db 'c','o','l','s',' ',0
stty_32: db '3','2',0
stty_64: db '6','4',0
stty_rows_cursor: db ' ','r','o','w','s',' ','2','4',' ','c','u','r','s','o','r',' ',0
stty_block: db 'b','l','o','c','k',0
stty_underline: db 'u','n','d','e','r','l','i','n','e',0
stty_off: db 'o','f','f',0
stty_lf: db 10
stty_req: db 0,0
    dw 0
stty_handle: db 0
stty_mode: db 0
stty_cursor: db 0
stty_errno: db 0
stty_wptr: dw 0
stty_wleft: dw 0
stty_wrote: dw 0
    ENDM
