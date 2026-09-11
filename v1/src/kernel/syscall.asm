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
    jr c,zx48_sys_dispatch_proc
    cp SYS_CON_GETKEY
    jp c,zx48_sys_notsup
    cp SYS_CON_SETPOS+1
    jr c,zx48_sys_dispatch_console
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
    jp zx48_sys_ok
zx48_sys_sleep:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    call zx48_sleep_current
    jp c,zx48_sys_error
    jp zx48_sys_ok
zx48_sys_getpid:
    ld a,(current_pid)
    ld l,a
    ld h,0
    jp zx48_sys_ok
zx48_sys_spawn_stub:
zx48_sys_exec_stub:
zx48_sys_wait_stub:
zx48_sys_kill_stub:
    jp zx48_sys_notsup

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
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_user_range_validate
    jp c,zx48_sys_error
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_console_write
    jp c,zx48_sys_error
    jp zx48_sys_ok
zx48_sys_con_clear:
    call zx48_console_clear
    jp zx48_sys_ok
zx48_sys_con_getpos:
    call zx48_console_getpos
    jp zx48_sys_ok
zx48_sys_con_setpos:
    ld hl,(syscall_arg_hl)
    call zx48_console_setpos
    jp c,zx48_sys_error
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
    jr z,zx48_sys_again
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
    jr c,zx48_sys_time_valid
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
    jp zx48_sys_ok

; Generic nonzero user range: wholly display 4000-5AFF or arena 6000-DFFF.
; Zero count never dereferences and accepts any pointer.
zx48_user_range_validate:
    ld a,b
    or c
    jr z,zx48_user_range_ok
    push hl
    add hl,bc
    jr c,zx48_user_range_wrap
    dec hl
    ex de,hl
    pop hl
    ld a,h
    cp $40
    jr c,zx48_user_range_bad
    cp $5B
    jr c,zx48_user_range_display
    cp $60
    jr c,zx48_user_range_bad
    cp $E0
    jr nc,zx48_user_range_bad
    ld a,d
    cp $60
    jr c,zx48_user_range_bad
    cp $E0
    jr nc,zx48_user_range_bad
zx48_user_range_ok:
    xor a
    ret
zx48_user_range_display:
    ld a,d
    cp $5B
    jr nc,zx48_user_range_bad
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
    jr zx48_sys_error
zx48_sys_perm:
    ld a,E_PERM
    jr zx48_sys_error
zx48_sys_invalid:
    ld a,E_INVAL
    jr zx48_sys_error
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
    dw zx48_sys_getpid,zx48_sys_spawn_stub,zx48_sys_exec_stub,zx48_sys_wait_stub
    dw zx48_sys_kill_stub
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
