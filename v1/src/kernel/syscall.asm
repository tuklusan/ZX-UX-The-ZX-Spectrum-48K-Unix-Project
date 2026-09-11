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
; Bounded version-1 syscall dispatcher. IX is preserved and IY is canonicalized.

    MACRO EMIT_SYSCALL_GATEWAY
syscall_gateway:
    jp zx48_syscall
    ENDM

    MACRO EMIT_SYSCALL_BODY
zx48_syscall:
    push ix
    call zx48_syscall_impl
    pop ix
    ld iy,ROM_IY_ANCHOR
    ret
    ENDM

    MACRO EMIT_SYSCALL_IMPL
zx48_syscall_impl:
    ld (syscall_arg_hl),hl
    ld (syscall_arg_de),de
    ld (syscall_arg_bc),bc
    cp SYS_KILL+1
    jp c,zx48_sys_dispatch_proc
    cp SYS_OPEN
    jp c,zx48_sys_notsup
    cp SYS_UNPACK+1
    jp c,zx48_sys_dispatch_handle
    cp SYS_PIPE
    jp c,zx48_sys_notsup
    cp SYS_IOCTL+1
    jp c,zx48_sys_dispatch_pipe
    cp SYS_CON_GETKEY
    jp c,zx48_sys_notsup
    cp SYS_CON_SETPOS+1
    jp c,zx48_sys_dispatch_console
    cp SYS_MEM_INFO
    jp c,zx48_sys_notsup
    cp SYS_TIME_SET+1
    jp nc,zx48_sys_notsup
    sub SYS_MEM_INFO
    add a,a
    ld e,a
    ld d,0
    ld hl,zx48_sys_info_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp (hl)

zx48_sys_dispatch_pipe:
    sub SYS_PIPE
    add a,a
    ld e,a
    ld d,0
    ld hl,zx48_sys_pipe_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp (hl)
zx48_sys_dispatch_handle:
    sub SYS_OPEN
    add a,a
    ld e,a
    ld d,0
    ld hl,zx48_sys_handle_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp (hl)
zx48_sys_dispatch_console:
    sub SYS_CON_GETKEY
    add a,a
    ld e,a
    ld d,0
    ld hl,zx48_sys_console_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp (hl)
zx48_sys_dispatch_proc:
    add a,a
    ld e,a
    ld d,0
    ld hl,zx48_sys_process_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp (hl)

zx48_sys_version:
    ld hl,ZXUX_ABI_VERSION
    jp zx48_sys_ok
zx48_sys_exit:
    ld hl,(syscall_arg_hl)
    ld a,h
    or a
    jp nz,zx48_sys_invalid
    ld a,l
    jp zx48_process_exit
zx48_sys_yield:
    call zx48_schedule
    ld hl,0
    jp zx48_sys_ok
zx48_sys_sleep:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    call zx48_sleep_current
    jp c,zx48_sys_error
    ld hl,0
    jp zx48_sys_ok
zx48_sys_getpid:
    ld a,(current_pid)
    ld l,a
    ld h,0
    jp zx48_sys_ok
zx48_sys_spawn_stub:
zx48_sys_exec_stub:
    jp zx48_sys_notsup

; WAIT1 {i16 pid,u16 status_ptr}. Current process helper uses FF for wait-any.
zx48_sys_wait:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    cp $ff
    jp z,zx48_sys_wait_any_check
    or a
    jp nz,zx48_sys_invalid
    ld a,e
    cp 2
    jp c,zx48_sys_invalid
    cp MAX_PROCESSES
    jp nc,zx48_sys_invalid
    jp zx48_sys_wait_target_ok
zx48_sys_wait_any_check:
    ld a,e
    cp $ff
    jp nz,zx48_sys_invalid
zx48_sys_wait_target_ok:
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    push de
    ld h,b
    ld l,c
    ld bc,1
    call zx48_user_range_validate
    pop de
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(syscall_arg_hl)
    ld a,(hl)
    call zx48_process_wait
    jp c,zx48_sys_error
    jp zx48_sys_ok

zx48_sys_kill:
    ld hl,(syscall_arg_hl)
    ld a,h
    or a
    jp nz,zx48_sys_invalid
    ld a,l
    call zx48_process_kill
    jp c,zx48_sys_error
    ld hl,0
    jp zx48_sys_ok

zx48_sys_open_stub:
    jp zx48_sys_notsup

zx48_sys_close:
    ld hl,(syscall_arg_hl)
    ld a,h
    or a
    jp nz,zx48_sys_invalid
    ld a,l
    call zx48_handle_close
    jp c,zx48_sys_error
    ld hl,0
    jp zx48_sys_ok

; E=handle,D=0,HL=buffer,BC=count.
zx48_sys_read:
    ld de,(syscall_arg_de)
    ld a,d
    or a
    jp nz,zx48_sys_invalid
    ld a,e
    ld (syscall_temp),a
    call zx48_handle_lookup
    jp c,zx48_sys_error
    ld a,(ix+OD_ACCESS_O)
    and O_READ
    jp z,zx48_sys_perm
    ld bc,(syscall_arg_bc)
    ld a,b
    or c
    jp z,zx48_sys_zero_result
    ld hl,(syscall_arg_hl)
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_NULL
    jp z,zx48_sys_zero_result
    cp OD_KIND_TTY
    jp z,zx48_sys_read_tty
    cp OD_KIND_PIPE_READ
    jp z,zx48_sys_read_pipe
    jp zx48_sys_notsup
zx48_sys_read_tty:
    call zx48_keyboard_getkey
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    ld (hl),a
    ld hl,1
    jp zx48_sys_ok
zx48_sys_read_pipe:
    ld a,(ix+OD_ID_O)
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_pipe_read
    jp c,zx48_sys_error
    jp zx48_sys_ok

zx48_sys_write:
    ld de,(syscall_arg_de)
    ld a,d
    or a
    jp nz,zx48_sys_invalid
    ld a,e
    ld (syscall_temp),a
    call zx48_handle_lookup
    jp c,zx48_sys_error
    ld a,(ix+OD_ACCESS_O)
    and O_WRITE
    jp z,zx48_sys_perm
    ld bc,(syscall_arg_bc)
    ld a,b
    or c
    jp z,zx48_sys_zero_result
    ld hl,(syscall_arg_hl)
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_NULL
    jp z,zx48_sys_write_null
    cp OD_KIND_TTY
    jp z,zx48_sys_write_tty
    cp OD_KIND_PIPE_WRITE
    jp z,zx48_sys_write_pipe
    jp zx48_sys_notsup
zx48_sys_write_null:
    ld hl,(syscall_arg_bc)
    jp zx48_sys_ok
zx48_sys_write_tty:
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_console_write
    jp c,zx48_sys_error
    jp zx48_sys_ok
zx48_sys_write_pipe:
    ld a,(ix+OD_ID_O)
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_pipe_write
    jp c,zx48_sys_error
    jp zx48_sys_ok
zx48_sys_zero_result:
    ld hl,0
    jp zx48_sys_ok

zx48_sys_seek:
    ld de,(syscall_arg_de)
    ld a,d
    or a
    jp nz,zx48_sys_invalid
    ld a,e
    call zx48_handle_lookup
    jp c,zx48_sys_error
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_OBJECT
    jp nz,zx48_sys_notsup
    jp zx48_sys_notsup

zx48_sys_handle_stub:
    jp zx48_sys_notsup

; HL -> two writable u8 handle result slots.
zx48_sys_pipe:
    ld hl,(syscall_arg_hl)
    ld bc,2
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    call zx48_pipe_create
    jp c,zx48_sys_error
    ld hl,0
    jp zx48_sys_ok

; HL -> DUP1 {source,destination}.
zx48_sys_dup:
    ld hl,(syscall_arg_hl)
    ld bc,2
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    ld b,(hl)
    inc hl
    ld c,(hl)
    ld a,b
    cp MAX_HANDLES_PER_PROCESS
    jp nc,zx48_sys_invalid
    ld a,c
    cp HANDLE_FREE
    jp z,zx48_sys_dup_go
    cp MAX_HANDLES_PER_PROCESS
    jp nc,zx48_sys_invalid
zx48_sys_dup_go:
    call zx48_handle_dup
    jp c,zx48_sys_error
    ld l,a
    ld h,0
    jp zx48_sys_ok

; HL -> IOCTL1 {handle,request,u16 arg_ptr}.
zx48_sys_ioctl:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    ld a,(hl)
    call zx48_handle_lookup
    jp c,zx48_sys_error
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_TTY
    jp nz,zx48_sys_notsup
    ld hl,(syscall_arg_hl)
    inc hl
    ld a,(hl)
    ld (syscall_temp),a
    cp TTY_REQ_GET_MODE
    jp z,zx48_sys_ioctl_one
    cp TTY_REQ_SET_MODE
    jp z,zx48_sys_ioctl_one
    cp TTY_REQ_GET_SIZE
    jp z,zx48_sys_ioctl_two
    cp TTY_REQ_SET_CURSOR
    jp z,zx48_sys_ioctl_one
    cp TTY_REQ_GET_CURSOR
    jp z,zx48_sys_ioctl_one
    cp TTY_REQ_GET_OWNER
    jp z,zx48_sys_ioctl_one
    cp TTY_REQ_SET_OWNER
    jp z,zx48_sys_ioctl_one
    jp zx48_sys_notsup
zx48_sys_ioctl_two:
    ld bc,2
    jp zx48_sys_ioctl_arg
zx48_sys_ioctl_one:
    ld bc,1
zx48_sys_ioctl_arg:
    ld hl,(syscall_arg_hl)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    call zx48_tty_ioctl
    jp c,zx48_sys_error
    ld hl,0
    jp zx48_sys_ok

zx48_sys_con_getkey:
    call zx48_keyboard_getkey
    jp c,zx48_sys_error
    ld l,a
    ld h,0
    jp zx48_sys_ok
zx48_sys_con_putchar:
    ld hl,(syscall_arg_hl)
    ld a,h
    or a
    jp nz,zx48_sys_invalid
    ld a,l
    call zx48_console_putchar
    jp c,zx48_sys_error
    ld hl,1
    jp zx48_sys_ok
zx48_sys_con_write:
    ld bc,(syscall_arg_bc)
    ld a,b
    or c
    jp z,zx48_sys_zero_result
    ld hl,(syscall_arg_hl)
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_console_write
    jp c,zx48_sys_error
    jp zx48_sys_ok
zx48_sys_con_clear:
    call zx48_console_clear
    ld hl,0
    jp zx48_sys_ok
zx48_sys_con_getpos:
    call zx48_console_getpos
    jp zx48_sys_ok
zx48_sys_con_setpos:
    ld hl,(syscall_arg_hl)
    call zx48_console_setpos
    jp c,zx48_sys_error
    ld hl,0
    jp zx48_sys_ok

zx48_sys_mem_info:
    ld hl,(syscall_arg_hl)
    ld bc,MINFO1_SIZE
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    call zx48_mem_info
    ld hl,(syscall_arg_hl)
    ld de,14
    add hl,de
    call zx48_process_count
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    ld hl,(syscall_arg_hl)
    jp zx48_sys_ok
zx48_sys_proc_info:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    ld a,(hl)
    ld (syscall_temp),a
    inc hl
    ld a,(hl)
    or a
    jp nz,zx48_sys_invalid
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld bc,16
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,(syscall_temp)
    call zx48_process_info
    jp c,zx48_sys_error
    jp zx48_sys_ok
zx48_sys_ticks:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    jp c,zx48_sys_error
    di
    ld de,(kernel_ticks)
    ld (syscall_tick_lo),de
    ld de,(kernel_ticks+2)
    ld (syscall_tick_hi),de
    ei
    ld hl,(syscall_arg_hl)
    ld de,(syscall_tick_lo)
    call zx48_sys_put16
    ld de,(syscall_tick_hi)
    call zx48_sys_put16
    ld hl,(syscall_arg_hl)
    jp zx48_sys_ok
zx48_sys_time_get:
    ld hl,(syscall_arg_hl)
    ld bc,6
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld a,(wall_valid)
    or a
    jp z,zx48_sys_again
    di
    ld de,(wall_seconds)
    ld (syscall_tick_lo),de
    ld de,(wall_seconds+2)
    ld (syscall_tick_hi),de
    ld de,(wall_revision)
    ld (syscall_time_revision),de
    ei
    ld hl,(syscall_arg_hl)
    ld de,(syscall_tick_lo)
    call zx48_sys_put16
    ld de,(syscall_tick_hi)
    call zx48_sys_put16
    ld de,(syscall_time_revision)
    call zx48_sys_put16
    ld hl,(syscall_arg_hl)
    jp zx48_sys_ok
zx48_sys_time_set:
    ld a,(current_pid)
    cp 1
    jp nz,zx48_sys_perm
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (syscall_tick_lo),de
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (syscall_tick_hi),de
    ld hl,(syscall_tick_hi)
    ld de,$F486
    or a
    sbc hl,de
    jp c,zx48_sys_time_valid
    jp nz,zx48_sys_invalid
    ld hl,(syscall_tick_lo)
    ld de,$5700
    or a
    sbc hl,de
    jp nc,zx48_sys_invalid
zx48_sys_time_valid:
    di
    ld de,(syscall_tick_lo)
    ld (wall_seconds),de
    ld de,(syscall_tick_hi)
    ld (wall_seconds+2),de
    ld hl,(wall_revision)
    inc hl
    ld (wall_revision),hl
    xor a
    ld (wall_subsecond),a
    inc a
    ld (wall_valid),a
    ei
    ld hl,0
    jp zx48_sys_ok

; Validate one complete nonzero range inside either shared display 4000..5AFF
; or the single contiguous user arena 6000..DFFF. Count zero never dereferences.
zx48_user_range_validate:
    ld a,b
    or c
    jp z,zx48_user_range_ok
    push hl
    add hl,bc
    jp c,zx48_user_range_wrap
    dec hl
    ex de,hl
    pop hl
    ld a,h
    cp $40
    jp c,zx48_user_range_bad
    cp $5B
    jp c,zx48_user_range_display
    cp $60
    jp c,zx48_user_range_bad
    cp $E0
    jp nc,zx48_user_range_bad
    ld a,d
    cp $60
    jp c,zx48_user_range_bad
    cp $E0
    jp nc,zx48_user_range_bad
zx48_user_range_ok:
    xor a
    ret
zx48_user_range_display:
    ld a,d
    cp $5B
    jp nc,zx48_user_range_bad
    xor a
    ret
zx48_user_range_wrap:
    pop hl
zx48_user_range_bad:
    ld a,E_INVAL
    scf
    ret

zx48_sys_put16:
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ret
zx48_sys_again:
    ld a,E_AGAIN
    jp zx48_sys_error
zx48_sys_perm:
    ld a,E_PERM
    jp zx48_sys_error
zx48_sys_invalid:
    ld a,E_INVAL
    jp zx48_sys_error
zx48_sys_notsup:
    ld a,E_NOTSUP
zx48_sys_error:
    scf
    ret
zx48_sys_ok:
    xor a
    ret

zx48_sys_process_table:
    dw zx48_sys_version,zx48_sys_exit,zx48_sys_yield,zx48_sys_sleep
    dw zx48_sys_getpid,zx48_sys_spawn_stub,zx48_sys_exec_stub,zx48_sys_wait
    dw zx48_sys_kill
zx48_sys_handle_table:
    dw zx48_sys_open_stub,zx48_sys_close,zx48_sys_read,zx48_sys_write
    dw zx48_sys_seek,zx48_sys_handle_stub,zx48_sys_handle_stub,zx48_sys_handle_stub
    dw zx48_sys_handle_stub,zx48_sys_handle_stub,zx48_sys_handle_stub,zx48_sys_handle_stub
    dw zx48_sys_handle_stub
zx48_sys_pipe_table:
    dw zx48_sys_pipe,zx48_sys_dup,zx48_sys_ioctl
zx48_sys_console_table:
    dw zx48_sys_con_getkey,zx48_sys_con_putchar,zx48_sys_con_write
    dw zx48_sys_con_clear,zx48_sys_con_getpos,zx48_sys_con_setpos
zx48_sys_info_table:
    dw zx48_sys_mem_info,zx48_sys_proc_info,zx48_sys_ticks,zx48_sys_time_get,zx48_sys_time_set

syscall_arg_hl: dw 0
syscall_arg_de: dw 0
syscall_arg_bc: dw 0
syscall_temp: db 0
syscall_tick_lo: dw 0
syscall_tick_hi: dw 0
syscall_time_revision: dw 0
    ENDM
