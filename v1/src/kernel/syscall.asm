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
; Fixed E000 syscall gateway. The process range uses a bounded indirect table;
; every table index is validated before JP (HL).

    MACRO EMIT_SYSCALL_GATEWAY
syscall_gateway:
    jp zx48_syscall
    ENDM

    MACRO EMIT_SYSCALL_BODY
zx48_syscall:
    jp zx48_syscall_impl
    ENDM

    MACRO EMIT_SYSCALL_IMPL
zx48_syscall_impl:
    ld (syscall_arg_hl),hl
    cp SYS_KILL+1
    jr c,zx48_sys_process_dispatch
    cp SYS_MEM_INFO
    jr c,zx48_sys_not_supported
    cp SYS_TICKS+1
    jr nc,zx48_sys_not_supported
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
zx48_sys_process_dispatch:
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

zx48_sys_not_supported:
    ld a,E_NOTSUP
    jr zx48_sys_error

zx48_sys_version:
    ld hl,ZXUX_ABI_VERSION
    jp zx48_sys_ok
zx48_sys_exit:
    ld hl,(syscall_arg_hl)
    ld a,l
    jp zx48_process_exit
zx48_sys_yield:
    call zx48_schedule
    jp zx48_sys_ok
zx48_sys_sleep:
    ld hl,(syscall_arg_hl)
    call zx48_sleep_current
    jr c,zx48_sys_error
    jp zx48_sys_ok
zx48_sys_getpid:
    ld a,(current_pid)
    ld l,a
    ld h,0
    jp zx48_sys_ok

zx48_sys_mem_info:
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
    ld a,(hl)
    ld (syscall_temp),a
    inc hl
    ld a,(hl)
    or a
    jr nz,zx48_sys_invalid
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,(syscall_temp)
    call zx48_process_info
    jr c,zx48_sys_error
    jp zx48_sys_ok

zx48_sys_ticks:
    ld hl,(syscall_arg_hl)
    ld de,(kernel_ticks)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(kernel_ticks+2)
    ld (hl),e
    inc hl
    ld (hl),d
    ld hl,(syscall_arg_hl)
    jp zx48_sys_ok

zx48_sys_invalid:
    ld a,E_INVAL
zx48_sys_error:
    ld iy,ROM_IY_ANCHOR
    scf
    ret
zx48_sys_ok:
    xor a
    ld iy,ROM_IY_ANCHOR
    ret

zx48_sys_process_table:
    dw zx48_sys_version,zx48_sys_exit,zx48_sys_yield,zx48_sys_sleep
    dw zx48_sys_getpid,zx48_sys_not_supported,zx48_sys_not_supported
    dw zx48_sys_not_supported,zx48_sys_not_supported
zx48_sys_info_table:
    dw zx48_sys_mem_info,zx48_sys_proc_info,zx48_sys_ticks
syscall_arg_hl: dw 0
syscall_temp: db 0
    ENDM
