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
; P9.01 vi transient MEX1 skeleton: exact tty mode/cursor save and restore.

    MACRO EMIT_P901_VI_ROUTINES
VI_TTY_GET_MODE         EQU 1
VI_TTY_SET_MODE         EQU 2
VI_TTY_SET_CURSOR       EQU 4
VI_TTY_GET_CURSOR       EQU 5
VI_MODE_64              EQU 64
VI_CURSOR_BLOCK         EQU 2

vi_entry:
    xor a
    ld (vi_have_mode),a
    ld (vi_have_cursor),a
    ld (vi_primary_errno),a
    call vi_open_tty
    jp c,vi_exit_error
    ld a,VI_TTY_GET_MODE
    ld hl,vi_saved_mode
    call vi_ioctl
    jp c,vi_close_error
    ld a,1
    ld (vi_have_mode),a
    ld a,VI_TTY_GET_CURSOR
    ld hl,vi_saved_cursor
    call vi_ioctl
    jp c,vi_unwind_error
    ld a,1
    ld (vi_have_cursor),a
    ld a,VI_MODE_64
    ld (vi_work),a
    ld a,VI_TTY_SET_MODE
    ld hl,vi_work
    call vi_ioctl
    jp c,vi_unwind_error
    ld a,VI_CURSOR_BLOCK
    ld (vi_work),a
    ld a,VI_TTY_SET_CURSOR
    ld hl,vi_work
    call vi_ioctl
    jp c,vi_unwind_error

; Shared unwind path is deliberately retained for all later editor exits.
vi_normal_exit:
    xor a
    ld (vi_primary_errno),a
    call vi_restore_terminal
    jr c,vi_exit_error
    call vi_close_tty
    jr c,vi_exit_error
    xor a
    jr vi_exit_a

vi_unwind_error:
    ld (vi_primary_errno),a
    call vi_restore_terminal
    call vi_close_tty
    ld a,(vi_primary_errno)
    jr vi_exit_a

vi_close_error:
    ld (vi_primary_errno),a
    call vi_close_tty
    ld a,(vi_primary_errno)
    jr vi_exit_a

vi_restore_terminal:
    xor a
    ld (vi_restore_errno),a
    ld a,(vi_have_mode)
    or a
    jr z,vi_restore_cursor
    ld a,VI_TTY_SET_MODE
    ld hl,vi_saved_mode
    call vi_ioctl
    jr nc,vi_restore_cursor
    ld (vi_restore_errno),a
vi_restore_cursor:
    ld a,(vi_have_cursor)
    or a
    jr z,vi_restore_done
    ld a,VI_TTY_SET_CURSOR
    ld hl,vi_saved_cursor
    call vi_ioctl
    jr nc,vi_restore_done
    ld b,a
    ld a,(vi_restore_errno)
    or a
    jr nz,vi_restore_done
    ld a,b
    ld (vi_restore_errno),a
vi_restore_done:
    ld a,(vi_restore_errno)
    or a
    ret z
    scf
    ret

vi_exit_error:
vi_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

vi_open_tty:
    ld hl,vi_tty
    ld c,O_READ|O_WRITE
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,vi_open_bad
    ld a,l
    ld (vi_handle),a
    xor a
    ret
vi_open_bad:
    ld a,E_FORMAT
    scf
    ret

vi_close_tty:
    ld a,(vi_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    jp SYSCALL_GATEWAY

vi_ioctl:
    ld (vi_req+1),a
    ld (vi_req+2),hl
    ld a,(vi_handle)
    ld (vi_req),a
    ld hl,vi_req
    ld a,SYS_IOCTL
    jp SYSCALL_GATEWAY

vi_tty: db '/','d','e','v','/','t','t','y',0
vi_req: db 0,0
    dw 0
vi_handle: db 0
vi_saved_mode: db 0
vi_saved_cursor: db 0
vi_have_mode: db 0
vi_have_cursor: db 0
vi_primary_errno: db 0
vi_restore_errno: db 0
vi_work: db 0
    ENDM
