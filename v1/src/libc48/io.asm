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
; P11.23 C48 object/handle runtime API.

    MACRO EMIT_P1123_C48_IO_RUNTIME
c48_io_stat1:       defs 4,0
c48_io_ren1:        defs 4,0
c48_io_list1:       defs 6,0
c48_io_dup1:        defs 2,0
c48_io_ioctl1:      defs 4,0
c48_io_full_handle: dw 0
c48_io_full_ptr:    dw 0
c48_io_full_left:   dw 0
c48_io_full_total:  dw 0
c48_io_full_step:   dw 0

c48_io_errno:
    ld l,a
    ld h,0
    or a
    ret

open:
    ld c,e
    ld b,0
    ld a,c
    and O_CREATE
    jr z,c48_io_open_call
    ld b,OBJ_DAT
c48_io_open_call:
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    or a
    ret

open_typed:
    ld a,c
    ld b,a
    ld c,e
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    or a
    ret

close:
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    ld hl,0
    xor a
    ret

; HL=handle, DE=buffer, BC=count. Kernel carry/A are retained internally.
c48_io_read_raw:
    ld a,l
    ex de,hl
    ld e,a
    ld d,0
    ld a,SYS_READ
    jp SYSCALL_GATEWAY

c48_io_write_raw:
    ld a,l
    ex de,hl
    ld e,a
    ld d,0
    ld a,SYS_WRITE
    jp SYSCALL_GATEWAY

read:
    call c48_io_read_raw
    jp c,c48_io_errno
    or a
    ret

write:
    call c48_io_write_raw
    jp c,c48_io_errno
    or a
    ret

seek:
    ld a,l
    ex de,hl
    ld e,a
    ld d,0
    ld a,SYS_SEEK
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    or a
    ret

stat:
    ld (c48_io_stat1),hl
    ld (c48_io_stat1+2),de
    ld hl,c48_io_stat1
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    ld hl,0
    xor a
    ret

remove:
    ld a,SYS_REMOVE
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    ld hl,0
    xor a
    ret

rename:
    ld (c48_io_ren1),hl
    ld (c48_io_ren1+2),de
    ld hl,c48_io_ren1
    ld a,SYS_RENAME
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    ld hl,0
    xor a
    ret

list:
    ld (c48_io_list1),hl
    ld a,e
    ld (c48_io_list1+2),a
    xor a
    ld (c48_io_list1+3),a
    ld (c48_io_list1+4),bc
    ld hl,c48_io_list1
    ld a,SYS_LIST
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    or a
    ret

pipe:
    ld a,SYS_PIPE
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    ld hl,0
    xor a
    ret

dup:
    ld a,l
    ld (c48_io_dup1),a
    ld a,e
    ld (c48_io_dup1+1),a
    ld hl,c48_io_dup1
    ld a,SYS_DUP
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    or a
    ret

ioctl:
    ld a,l
    ld (c48_io_ioctl1),a
    ld a,e
    ld (c48_io_ioctl1+1),a
    ld (c48_io_ioctl1+2),bc
    ld hl,c48_io_ioctl1
    ld a,SYS_IOCTL
    call SYSCALL_GATEWAY
    jp c,c48_io_errno
    or a
    ret

; HL=handle, DE=buffer, BC=count.
read_full:
    call c48_io_full_init
c48_io_read_full_loop:
    ld bc,(c48_io_full_left)
    ld a,b
    or c
    jr z,c48_io_full_done
    ld hl,(c48_io_full_handle)
    ld de,(c48_io_full_ptr)
    call c48_io_read_raw
    jp c,c48_io_errno
    ld a,h
    or l
    jr z,c48_io_full_done
    call c48_io_full_advance
    jr c48_io_read_full_loop

write_full:
    call c48_io_full_init
c48_io_write_full_loop:
    ld bc,(c48_io_full_left)
    ld a,b
    or c
    jr z,c48_io_full_done
    ld hl,(c48_io_full_handle)
    ld de,(c48_io_full_ptr)
    call c48_io_write_raw
    jp c,c48_io_errno
    ld a,h
    or l
    jr nz,c48_io_write_progress
    ld a,E_IO
    jp c48_io_errno
c48_io_write_progress:
    call c48_io_full_advance
    jr c48_io_write_full_loop

c48_io_full_init:
    ld (c48_io_full_handle),hl
    ld (c48_io_full_ptr),de
    ld (c48_io_full_left),bc
    ld hl,0
    ld (c48_io_full_total),hl
    ret

; HL=positive transfer count.
c48_io_full_advance:
    ld (c48_io_full_step),hl
    ld de,(c48_io_full_left)
    or a
    sbc hl,de
    ld hl,(c48_io_full_step)
    jr c,c48_io_full_advance_ok
    jr z,c48_io_full_advance_ok
    ld a,E_FORMAT
    jp c48_io_errno
c48_io_full_advance_ok:
    ld de,(c48_io_full_ptr)
    add hl,de
    ld (c48_io_full_ptr),hl
    ld hl,(c48_io_full_left)
    ld de,(c48_io_full_step)
    or a
    sbc hl,de
    ld (c48_io_full_left),hl
    ld hl,(c48_io_full_total)
    add hl,de
    ld (c48_io_full_total),hl
    xor a
    ret

c48_io_full_done:
    ld hl,(c48_io_full_total)
    xor a
    ret
    ENDM
