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
; /bin/cat: stream one named object, or inherited stdin, to inherited stdout.

    MACRO EMIT_P802_CAT_ROUTINES
cat_entry:
    push hl
    pop ix
    xor a
    ld (cat_opened),a
    ld a,(ix+4)
    cp 1
    jr z,cat_stdin
    cp 2
    jr z,cat_named
    ld a,E_INVAL
    jp cat_exit_error

cat_named:
    ld de,8
    add ix,de
cat_skip_argv0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,cat_skip_argv0
    push ix
    pop hl
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,cat_exit_error
    ld a,l
    ld (cat_handle),a
    ld a,1
    ld (cat_opened),a
    jr cat_read_loop

cat_stdin:
    xor a
    ld (cat_handle),a

cat_read_loop:
    ld a,(cat_handle)
    ld e,a
    ld d,0
    ld hl,cat_buffer
    ld bc,64
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,cat_stream_error
    ld a,h
    or l
    jr z,cat_success
    ld (cat_remaining),hl
    ld hl,cat_buffer
    ld (cat_ptr),hl

cat_write_loop:
    ld hl,(cat_ptr)
    ld bc,(cat_remaining)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jp c,cat_stream_error
    ld a,h
    or l
    jr z,cat_zero_write
    ld (cat_written),hl
    ld de,(cat_ptr)
    add hl,de
    ld (cat_ptr),hl
    ld hl,(cat_remaining)
    ld de,(cat_written)
    or a
    sbc hl,de
    jp c,cat_zero_write
    ld (cat_remaining),hl
    ld a,h
    or l
    jr nz,cat_write_loop
    jr cat_read_loop

cat_zero_write:
    ld a,E_IO

cat_stream_error:
    ld (cat_error),a
    ld a,(cat_opened)
    or a
    jr z,cat_stream_error_exit
    ld a,(cat_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
cat_stream_error_exit:
    ld a,(cat_error)
    jp cat_exit_error

cat_success:
    ld a,(cat_opened)
    or a
    jr z,cat_exit_ok
    ld a,(cat_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    jp c,cat_exit_error

cat_exit_ok:
    ld l,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

cat_exit_error:
    ld l,a
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

cat_handle: db 0
cat_opened: db 0
cat_error: db 0
cat_ptr: dw 0
cat_remaining: dw 0
cat_written: dw 0
cat_buffer: defs 64,0
cat_end:
    ENDM
