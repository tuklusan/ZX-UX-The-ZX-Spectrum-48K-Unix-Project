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
; /bin/cp: atomic logical RAM-object copy via an exclusive /tmp transaction.
; The destination becomes visible only through the final SYS_RENAME commit.

    MACRO EMIT_P803_CP_ROUTINES
cp_entry:
    push hl
    pop ix
    xor a
    ld (cp_src_open),a
    ld (cp_tmp_open),a
    ld (cp_tmp_created),a
    ld a,(ix+4)
    cp 3
    jp nz,cp_invalid
    ld de,8
    add ix,de
    call cp_next_arg
    push ix
    pop hl
    ld (cp_src_path),hl
    call cp_next_arg
    push ix
    pop hl
    ld (cp_dst_path),hl

; Exact same pathname is the common same-object no-op case. All other pathname
; validation and exact case semantics remain kernel-resolver authoritative.
    ld hl,(cp_src_path)
    ld de,(cp_dst_path)
cp_same_loop:
    ld a,(de)
    cp (hl)
    jr nz,cp_stat_source
    or a
    jp z,cp_success
    inc hl
    inc de
    jr cp_same_loop

cp_stat_source:
    ld hl,(cp_src_path)
    ld (cp_stat_req),hl
    ld hl,cp_stat_out
    ld (cp_stat_req+2),hl
    ld hl,cp_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    jp c,cp_exit_error
    ld a,(cp_stat_out+7)
    cp STATE_RAM
    jr z,cp_type_check
    ld a,E_PERM
    jp cp_exit_error
cp_type_check:
    ld a,(cp_stat_out+0)
    or a
    jp z,cp_invalid
    cp 11
    jr c,cp_type_ok
    ld a,E_PERM
    jp cp_exit_error
cp_type_ok:
    ld (cp_src_type),a

    ld hl,(cp_src_path)
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,cp_exit_error
    ld a,l
    ld (cp_src_handle),a
    ld a,1
    ld (cp_src_open),a

    ld a,SYS_GETPID
    call SYSCALL_GATEWAY
    jp c,cp_cleanup_error
    ld (cp_pid),hl
    xor a
    ld (cp_try_n),a

cp_temp_try:
    call cp_build_temp
    ld hl,cp_temp_path
    ld c,O_WRITE|O_CREATE|O_EXCL
    ld a,(cp_src_type)
    ld b,a
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jr nc,cp_temp_opened
    cp E_EXIST
    jp nz,cp_cleanup_error
    ld a,(cp_try_n)
    inc a
    ld (cp_try_n),a
    cp 10
    jr c,cp_temp_try
    ld a,E_EXIST
    jp cp_cleanup_error

cp_temp_opened:
    ld a,l
    ld (cp_tmp_handle),a
    ld a,1
    ld (cp_tmp_open),a
    ld (cp_tmp_created),a

cp_read_loop:
    ld a,(cp_src_handle)
    ld e,a
    ld d,0
    ld hl,cp_buffer
    ld bc,64
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,cp_cleanup_error
    ld a,h
    or l
    jr z,cp_finish_stream
    ld (cp_count),hl
    ld b,h
    ld c,l
    ld a,(cp_tmp_handle)
    ld e,a
    ld d,0
    ld hl,cp_buffer
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jp c,cp_cleanup_error
    ld de,(cp_count)
    or a
    sbc hl,de
    jr z,cp_read_loop
    ld a,E_IO
    jp cp_cleanup_error

cp_finish_stream:
    call cp_close_source
    jp c,cp_cleanup_error
    call cp_close_temp
    jp c,cp_cleanup_error
    ld hl,cp_temp_path
    ld (cp_ren1),hl
    ld hl,(cp_dst_path)
    ld (cp_ren1+2),hl
    ld hl,cp_ren1
    ld a,SYS_RENAME
    call SYSCALL_GATEWAY
    jr nc,cp_committed
    ld (cp_error),a
    call cp_remove_temp
    ld a,(cp_error)
    jp cp_exit_error
cp_committed:
    xor a
    ld (cp_tmp_created),a
    jp cp_success

cp_cleanup_error:
    ld (cp_error),a
    call cp_close_source
    call cp_close_temp
    call cp_remove_temp
    ld a,(cp_error)
    jp cp_exit_error

cp_close_source:
    ld a,(cp_src_open)
    or a
    jr z,cp_close_ok
    xor a
    ld (cp_src_open),a
    ld a,(cp_src_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret
cp_close_temp:
    ld a,(cp_tmp_open)
    or a
    jr z,cp_close_ok
    xor a
    ld (cp_tmp_open),a
    ld a,(cp_tmp_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret
cp_close_ok:
    or a
    ret

cp_remove_temp:
    ld a,(cp_tmp_created)
    or a
    ret z
    xor a
    ld (cp_tmp_created),a
    ld hl,cp_temp_path
    ld a,SYS_REMOVE
    call SYSCALL_GATEWAY
    ret

cp_build_temp:
    ld hl,cp_temp_prefix
    ld de,cp_temp_path
    ld bc,8
    ldir
    push de
    pop ix
    ld hl,(cp_pid)
    xor a
    ld (cp_dec_started),a
    ld de,10000
    call cp_dec_place
    ld de,1000
    call cp_dec_place
    ld de,100
    call cp_dec_place
    ld de,10
    call cp_dec_place
    ld a,l
    add a,'0'
    ld (ix+0),a
    inc ix
    ld a,'.'
    ld (ix+0),a
    inc ix
    ld a,(cp_try_n)
    add a,'0'
    ld (ix+0),a
    inc ix
    xor a
    ld (ix+0),a
    ret

cp_dec_place:
    ld c,0
cp_dec_sub:
    or a
    sbc hl,de
    jr c,cp_dec_done
    inc c
    jr cp_dec_sub
cp_dec_done:
    add hl,de
    ld a,(cp_dec_started)
    or c
    ret z
    ld a,1
    ld (cp_dec_started),a
    ld a,c
    add a,'0'
    ld (ix+0),a
    inc ix
    ret

cp_next_arg:
cp_next_arg_loop:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,cp_next_arg_loop
    ret

cp_invalid:
    ld a,E_INVAL
cp_exit_error:
    ld l,a
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
cp_success:
    ld l,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

cp_src_path: dw 0
cp_dst_path: dw 0
cp_src_handle: db 0
cp_tmp_handle: db 0
cp_src_open: db 0
cp_tmp_open: db 0
cp_tmp_created: db 0
cp_src_type: db 0
cp_try_n: db 0
cp_error: db 0
cp_dec_started: db 0
cp_pid: dw 0
cp_count: dw 0
cp_stat_req: defs 4,0
cp_stat_out: defs 10,0
cp_ren1: defs 4,0
cp_temp_prefix: db '/tmp/.cp'
cp_temp_path: defs 24,0
cp_buffer: defs 64,0
cp_end:
    ENDM
