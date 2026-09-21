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

    INCLUDE "graphics.asm"

SYSCALL_FRAME_PC_O       EQU 10
syscall_frame_sp          EQU FAST_RESERVE_END-1

; Fixed emergency-reserve syscall scratch. This relocates mutable scratch only;
; no public ABI address is exposed.
SYSCALL_STATE_BASE        EQU EMERGENCY_START+$1F
syscall_user_sp           EQU SYSCALL_STATE_BASE+0
syscall_saved_ix          EQU SYSCALL_STATE_BASE+2
syscall_arg_hl            EQU SYSCALL_STATE_BASE+4
syscall_arg_de            EQU SYSCALL_STATE_BASE+6
syscall_arg_bc            EQU SYSCALL_STATE_BASE+8
syscall_temp              EQU SYSCALL_STATE_BASE+10
syscall_tick_lo           EQU SYSCALL_STATE_BASE+11
syscall_tick_hi           EQU SYSCALL_STATE_BASE+13
SYSCALL_STATE_END         EQU SYSCALL_STATE_BASE+15

; P2.09 exact pointer-based spawn preflight record.
PROC1_PATH_PTR             EQU 0
PROC1_ARG1_PTR             EQU 2
PROC1_ARG1_LEN             EQU 4
PROC1_ENV1_PTR             EQU 6
PROC1_ENV1_LEN             EQU 8
PROC1_STDIN_HANDLE         EQU 10
PROC1_STDOUT_HANDLE        EQU 11
PROC1_STDERR_HANDLE        EQU 12
PROC1_FLAGS                EQU 13
PROC1_RESERVED             EQU 14
PROC1_SIZE                 EQU 16
PROC1_ALLOW_TAPE           EQU $01
PROC1_PATH_MAX             EQU 31

    MACRO EMIT_SYSCALL_GATEWAY
syscall_gateway:
    jp zx48_syscall
    ENDM

    MACRO EMIT_SYSCALL_BODY
; The user CALL return word remains below a canonical 12-byte task frame.
; Kernel work then runs only on the dedicated 0xFB00-0xFCFF stack.
zx48_syscall:
    ld (syscall_user_sp),sp
    ld (syscall_saved_ix),ix
    push hl
    ld hl,zx48_syscall
    ex (sp),hl
    push af
    push bc
    push de
    push hl
    push ix
    ld (syscall_frame_sp),sp
    ld sp,BOOT_STACK_TOP
    push af
    push de
    push hl
    call zx48_kernel_stack_sample
    pop hl
    pop de
    pop af
    call zx48_syscall_impl
zx48_syscall_return:
    push af
    push hl
    call zx48_kernel_stack_sample
    call zx48_kernel_stack_check
    ld ix,(syscall_saved_ix)
    pop de
    pop af
    ld hl,(syscall_user_sp)
    ld sp,hl
    ex de,hl
    ld iy,ROM_IY_ANCHOR
    ret

; Scheduler continuation for yield/sleep: SP again points at the user CALL return.
zx48_syscall_resume_ok:
    ld (syscall_user_sp),sp
    ld (syscall_saved_ix),ix
    ld sp,BOOT_STACK_TOP
    ld hl,0
    xor a
    jr zx48_syscall_return

; Cancellation continuation for a blocked started process.
zx48_syscall_resume_intr:
    ld (syscall_user_sp),sp
    ld (syscall_saved_ix),ix
    ld sp,BOOT_STACK_TOP
    ld a,E_INTR
    scf
    jr zx48_syscall_return

    IFDEF ZX48_P2_15_WAIT_ENABLED
; Scheduler continuation for a blocked P2.15 specific-child WAIT.
zx48_syscall_resume_wait_specific:
    ld (syscall_user_sp),sp
    ld (syscall_saved_ix),ix
    ld sp,BOOT_STACK_TOP
    call zx48_process_wait_specific_resume
    jr zx48_syscall_return
    ENDIF
    ENDM

; Shared exact user-range validator. P2.09 emits this same source into its staged
; fixture rather than maintaining a second range implementation.
    MACRO EMIT_USER_RANGE_VALIDATION_ROUTINE
; Validate one complete nonzero range inside either shared display 4000..5AFF
; or the single contiguous user arena 6000..DFFF. Count zero never dereferences.
zx48_user_range_validate:
    ld a,b
    or c
    jr z,zx48_user_range_ok
    push hl
    ; ADD HL,BC plus carry is the exact 17-bit widened end_exclusive.
    ; Any carry is fail-closed here: exact 0x10000 would have end byte 0xFFFF,
    ; which cannot lie in either permitted ABI region, while all larger carries
    ; violate end_exclusive <= 0x10000. Thus no narrowing precedes the decision.
    add hl,bc
    jr c,zx48_user_range_wrap
    ; BC is nonzero and no carry occurred, so end_exclusive > start.
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
    ENDM


    MACRO EMIT_SYSCALL_IMPL
zx48_syscall_impl:
    ld (syscall_arg_hl),hl
    ld (syscall_arg_de),de
    ld (syscall_arg_bc),bc

    ; P6.26 cooperative BREAK boundary. User DE is already snapshotted, so E
    ; temporarily preserves the selector. BREAK is consumed only when the current
    ; cooperative task is the tty owner; non-owner stages leave it pending.
    ld e,a
    ld a,(break_pending)
    or a
    jr z,zx48_p626_break_restore_selector
    ld a,(tty_input_owner)
    ld b,a
    ld a,(current_pid)
    xor b
    jr nz,zx48_p626_break_restore_selector
    ld (break_pending),a
    ld a,E_INTR
    scf
    ret
zx48_p626_break_restore_selector:
    ld a,e
    cp SYS_KILL+1
    jr c,zx48_sys_dispatch_proc
    cp SYS_OPEN
    jp c,zx48_sys_notsup
    cp SYS_UNPACK+1
    jr c,zx48_sys_dispatch_handle
    cp SYS_PIPE
    jp c,zx48_sys_notsup
    cp SYS_IOCTL+1
    jr c,zx48_sys_dispatch_pipe
    cp SYS_CON_GETKEY
    jp c,zx48_sys_notsup
    cp SYS_CON_SETPOS+1
    jr c,zx48_sys_dispatch_console
    cp SYS_MEM_INFO
    jp c,zx48_sys_notsup
    cp SYS_TIME_SET+1
    jp nc,zx48_sys_notsup
    sub SYS_MEM_INFO
    ld hl,zx48_sys_info_table
    jr zx48_sys_dispatch_index

zx48_sys_dispatch_pipe:
    sub SYS_PIPE
    ld hl,zx48_sys_pipe_table
    jr zx48_sys_dispatch_index
zx48_sys_dispatch_handle:
    sub SYS_OPEN
    ld hl,zx48_sys_handle_table
    jr zx48_sys_dispatch_index
zx48_sys_dispatch_console:
    sub SYS_CON_GETKEY
    ld hl,zx48_sys_console_table
    jr zx48_sys_dispatch_index
zx48_sys_dispatch_proc:
    ld hl,zx48_sys_process_table
zx48_sys_dispatch_index:
    add a,a
    ld e,a
    ld d,0
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp (hl)

zx48_sys_version:
    ld hl,ZXUX_ABI_VERSION
    xor a
    ret
zx48_sys_exit:
    ld hl,(syscall_arg_hl)
    ld a,h
    or a
    jp nz,zx48_sys_invalid
    ld a,l
    jp zx48_process_exit
zx48_sys_yield:
    jp zx48_schedule_finish_syscall
zx48_sys_sleep:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    call zx48_sleep_current
    ret c
    jp zx48_sys_zero_result
zx48_sys_getpid:
    ld a,(current_pid)
    ld l,a
    xor a
    ld h,a
    ret
zx48_sys_spawn_stub:
zx48_sys_exec_stub:
zx48_sys_open_stub:
zx48_sys_handle_stub:
    jp zx48_sys_notsup

; WAIT1 {i16 pid,u16 status_ptr}. Current process helper uses FF for wait-any.
zx48_sys_wait:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    cp $ff
    jr z,zx48_sys_wait_any_check
    or a
    jp nz,zx48_sys_invalid
    ld a,e
    cp 2
    jp c,zx48_sys_invalid
    cp MAX_PROCESSES
    jp nc,zx48_sys_invalid
    jr zx48_sys_wait_target_ok
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
    ret c
    ld hl,(syscall_arg_hl)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(syscall_arg_hl)
    ld a,(hl)
    IFDEF ZX48_P2_15_WAIT_ENABLED
    cp $ff
    jr z,zx48_sys_wait_legacy_any
    call zx48_process_wait_specific
    ret
zx48_sys_wait_legacy_any:
    ENDIF
    call zx48_process_wait
    ret c
    xor a
    ret

zx48_sys_kill:
    ld hl,(syscall_arg_hl)
    ld a,h
    or a
    jp nz,zx48_sys_invalid
    ld a,l
    call zx48_process_kill
    ret c
    jp zx48_sys_zero_result

zx48_sys_close:
    ld hl,(syscall_arg_hl)
    ld a,h
    or a
    jp nz,zx48_sys_invalid
    ld a,l
    call zx48_handle_close
    ret c
    jp zx48_sys_zero_result

; A=required access bit. Returns C set on error, Z set for count=0,
; NZ for a validated nonzero buffer. IX remains the open description.
zx48_sys_rw_prepare:
    ld b,a
    ld de,(syscall_arg_de)
    ld a,d
    or a
    jp nz,zx48_sys_invalid
    push bc
    ld a,e
    call zx48_handle_lookup
    pop bc
    ret c
    ld a,(ix+OD_ACCESS_O)
    and b
    jp z,zx48_sys_perm
    ld bc,(syscall_arg_bc)
    ld a,b
    or c
    ret z
    ld hl,(syscall_arg_hl)
    call zx48_user_range_validate
    ret c
    inc a
    ret

; E=handle,D=0,HL=buffer,BC=count.
zx48_sys_read:
    ld a,O_READ
    call zx48_sys_rw_prepare
    ret c
    jr z,zx48_sys_zero_result
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_NULL
    jr z,zx48_sys_zero_result
    cp OD_KIND_TTY
    jr z,zx48_sys_read_tty
    cp OD_KIND_PIPE_READ
    jr z,zx48_sys_read_pipe
    jp zx48_sys_notsup
zx48_sys_read_tty:
    call zx48_keyboard_getkey
    ret c
    ld hl,(syscall_arg_hl)
    ld (hl),a
    ld hl,1
    xor a
    ret
zx48_sys_read_pipe:
    ld a,(ix+OD_ID_O)
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_pipe_read
    ret

zx48_sys_write:
    ld a,O_WRITE
    call zx48_sys_rw_prepare
    ret c
    jr z,zx48_sys_zero_result
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_NULL
    jr z,zx48_sys_write_null
    cp OD_KIND_TTY
    jr z,zx48_sys_write_tty
    cp OD_KIND_PIPE_WRITE
    jr z,zx48_sys_write_pipe
    jp zx48_sys_notsup
zx48_sys_write_null:
    ld hl,(syscall_arg_bc)
    xor a
    ret
zx48_sys_write_tty:
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_console_write
    ret c
    xor a
    ret
zx48_sys_write_pipe:
    ld a,(ix+OD_ID_O)
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_pipe_write
    ret
zx48_sys_zero_result:
    xor a
    ld h,a
    ld l,a
    ret

zx48_sys_seek:
    ld de,(syscall_arg_de)
    ld a,d
    or a
    jp nz,zx48_sys_invalid
    ld a,e
    call zx48_handle_lookup
    ret c
    jp zx48_sys_notsup

; HL -> two writable u8 handle result slots.
zx48_sys_pipe:
    ld hl,(syscall_arg_hl)
    ld bc,2
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    jp zx48_pipe_create

; HL -> DUP1 {source,destination}.
zx48_sys_dup:
    ld hl,(syscall_arg_hl)
    ld bc,2
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    ld b,(hl)
    inc hl
    ld c,(hl)
    ld a,b
    cp MAX_HANDLES_PER_PROCESS
    jp nc,zx48_sys_invalid
    ld a,c
    cp HANDLE_FREE
    jr z,zx48_sys_dup_go
    cp MAX_HANDLES_PER_PROCESS
    jp nc,zx48_sys_invalid
zx48_sys_dup_go:
    call zx48_handle_dup
    ret c
    ld l,a
    ld h,0
    xor a
    ret

; HL -> IOCTL1 {handle,request,u16 arg_ptr}.
zx48_sys_ioctl:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    ld a,(hl)
    call zx48_handle_lookup
    ret c
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_TTY
    jp nz,zx48_sys_notsup
    ld hl,(syscall_arg_hl)
    inc hl
    ld a,(hl)
    cp TTY_REQ_GET_MODE
    jp c,zx48_sys_notsup
    cp TTY_REQ_SET_OWNER+1
    jp nc,zx48_sys_notsup
    ld bc,1
    cp TTY_REQ_GET_SIZE
    jr nz,zx48_sys_ioctl_arg
    inc bc
zx48_sys_ioctl_arg:
    ld hl,(syscall_arg_hl)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    call zx48_tty_ioctl
    ret c
    jp zx48_sys_zero_result

zx48_sys_con_getkey:
    call zx48_keyboard_getkey
    ret c
    ld l,a
    ld h,0
    xor a
    ret
zx48_sys_con_putchar:
    ld hl,(syscall_arg_hl)
    ld a,h
    or a
    jp nz,zx48_sys_invalid
    ld a,l
    call zx48_console_putchar
    ret c
    ld hl,1
    xor a
    ret
zx48_sys_con_write:
    ld bc,(syscall_arg_bc)
    ld a,b
    or c
    jp z,zx48_sys_zero_result
    ld hl,(syscall_arg_hl)
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    ld bc,(syscall_arg_bc)
    call zx48_console_write
    ret c
    xor a
    ret
zx48_sys_con_clear:
    call zx48_console_clear
    jp zx48_sys_zero_result
zx48_sys_con_getpos:
    call zx48_console_getpos
    xor a
    ret
zx48_sys_con_setpos:
    ld hl,(syscall_arg_hl)
    call zx48_console_setpos
    ret c
    jp zx48_sys_zero_result

zx48_sys_mem_info:
    ld hl,(syscall_arg_hl)
    ld bc,MINFO1_SIZE
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    call zx48_mem_info
    ld hl,(syscall_arg_hl)
    xor a
    ret
zx48_sys_proc_info:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    ret c
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
    ret c
    ld hl,(syscall_arg_hl)
    inc hl
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld a,(syscall_temp)
    call zx48_process_info
    ret c
    xor a
    ret
zx48_sys_ticks:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    ret c
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
    xor a
    ret
zx48_sys_time_get:
    ld hl,(syscall_arg_hl)
    ld bc,6
    call zx48_user_range_validate
    ret c
    ld a,(wall_valid)
    or a
    jp z,zx48_sys_again
    di
    ld de,(syscall_arg_hl)
    ld hl,wall_seconds
    ld bc,6
    ldir
    ei
    ld hl,(syscall_arg_hl)
    xor a
    ret
zx48_sys_time_set:
    ld a,(current_pid)
    cp 1
    jp nz,zx48_sys_perm
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    ret c
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
    jr nz,zx48_sys_invalid
    ld hl,(syscall_tick_lo)
    ld de,$5700
    or a
    sbc hl,de
    jr nc,zx48_sys_invalid
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
    jp zx48_sys_zero_result

    EMIT_USER_RANGE_VALIDATION_ROUTINE

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

    ENDM

; P2.09/P2.10 staged production spawn entry and preflight. The resident kernel
; keeps SYS_SPAWN on its compact not-supported dispatch entry because the frozen
; ordinary-code pool has no room for the Phase-2 transaction yet. Deterministic
; Phase-2 fixtures emit this exact source and the P2.10 transaction together.
    MACRO EMIT_SPAWN_PREFLIGHT_ROUTINES
zx48_sys_spawn:
    ld hl,(syscall_arg_hl)
    call zx48_sys_spawn_preflight
    ret c
    ld hl,(syscall_arg_hl)
    jp zx48_process_spawn_transaction

zx48_sys_spawn_preflight:
    ; Capacity is authoritative and must precede even validation of PROC1 itself.
    call zx48_process_find_free_slot
    ret c

    ; Only after capacity exists may the sixteen-byte request record be touched.
    ld bc,PROC1_SIZE
    call zx48_user_range_validate
    ret c
    push hl
    pop ix

    ; Structural fields are closed before any pointed range is dereferenced.
    ld a,(ix+PROC1_STDIN_HANDLE)
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_sys_spawn_preflight_invalid
    ld a,(ix+PROC1_STDOUT_HANDLE)
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_sys_spawn_preflight_invalid
    ld a,(ix+PROC1_STDERR_HANDLE)
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_sys_spawn_preflight_invalid
    ld a,(ix+PROC1_FLAGS)
    and $FE
    jr nz,zx48_sys_spawn_preflight_invalid
    ld a,(ix+PROC1_RESERVED)
    or (ix+PROC1_RESERVED+1)
    jr nz,zx48_sys_spawn_preflight_invalid

    ; ARG1/ENV1 are range-only at P2.09. A zero length follows the frozen buffer
    ; rule: the corresponding pointer is not dereferenced and need not be valid.
    ld l,(ix+PROC1_ARG1_PTR)
    ld h,(ix+PROC1_ARG1_PTR+1)
    ld c,(ix+PROC1_ARG1_LEN)
    ld b,(ix+PROC1_ARG1_LEN+1)
    call zx48_user_range_validate
    ret c
    ld l,(ix+PROC1_ENV1_PTR)
    ld h,(ix+PROC1_ENV1_PTR+1)
    ld c,(ix+PROC1_ENV1_LEN)
    ld b,(ix+PROC1_ENV1_LEN+1)
    call zx48_user_range_validate
    ret c

    ; Path scanning is bounded to 31 bytes plus the required NUL and validates
    ; each byte before reading it so a short string at a region edge remains legal.
    ld l,(ix+PROC1_PATH_PTR)
    ld h,(ix+PROC1_PATH_PTR+1)
    ld d,PROC1_PATH_MAX+1
zx48_sys_spawn_preflight_path:
    push de
    ld bc,1
    call zx48_user_range_validate
    pop de
    ret c
    ld a,(hl)
    or a
    jr z,zx48_sys_spawn_preflight_path_done
    inc hl
    dec d
    jr nz,zx48_sys_spawn_preflight_path
    ld a,E_TOOLONG
    scf
    ret
zx48_sys_spawn_preflight_path_done:
    ld a,d
    cp PROC1_PATH_MAX+1
    jr z,zx48_sys_spawn_preflight_invalid
    xor a
    ret

zx48_sys_spawn_preflight_invalid:
    ld a,E_INVAL
    scf
    ret
    ENDM


;
; P4.32 exact SYS_GETCWD syscall surface.
;
    MACRO EMIT_P432_GETCWD_SYSCALL_ROUTINES
; HL=destination, BC=capacity. Validate the complete declared writable range
; before inspecting cwd state or publishing any output byte.
zx48_p432_sys_getcwd:
    ld (p432_sys_out),hl
    ld (p432_sys_capacity),bc
    call zx48_user_range_validate
    ret c
    ld hl,(p432_sys_out)
    ld bc,(p432_sys_capacity)
    jp zx48_p432_getcwd
p432_sys_out: dw 0
p432_sys_capacity: dw 0
    ENDM

;
; P4.31 exact SYS_CHDIR syscall surface.
;
    MACRO EMIT_P431_CHDIR_SYSCALL_ROUTINES
; HL=NUL-terminated directory path. Prove the complete user C string before
; resolution; no cwd byte is changed until zx48_p431_chdir commits.
zx48_p431_sys_chdir:
    ld (p431_chdir_path),hl
zx48_p431_chdir_validate_loop:
    push hl
    ld bc,1
    call zx48_user_range_validate
    pop hl
    ret c
    ld a,(hl)
    or a
    jr z,zx48_p431_chdir_validated
    inc hl
    jr zx48_p431_chdir_validate_loop
zx48_p431_chdir_validated:
    ld hl,(p431_chdir_path)
    jp zx48_p431_chdir
p431_chdir_path: dw 0
    ENDM

;
; P4.28 exact SYS_ZXPACK_INFO syscall surface.
;
    MACRO EMIT_P428_ZXPACK_INFO_SYSCALL_ROUTINES
; A=SYS_ZXPACK_INFO, HL=writable exact 20-byte ZPINFO1.
zx48_p428_sys_zxpack_info:
    cp SYS_ZXPACK_INFO
    jr nz,zx48_p428_sys_zxpack_info_notsup
    ld bc,20
    call zx48_user_range_validate
    ret c
    jp zx48_p428_zxpack_info
zx48_p428_sys_zxpack_info_notsup:
    ld a,E_NOTSUP
    scf
    ret
    ENDM

;
; P4.05 compact SYS_OPEN transaction. This is emitted by the exact P4.05
; qualification fixture; later Phase-4 steps add writer exclusivity/read/write.
;
    MACRO EMIT_P405_SYS_OPEN_ROUTINES
; B=OD kind,C=access flags,D=identity -> HL=lowest free process handle.
; Any failed handle install rolls back the just-created open description.
zx48_p405_open_allocate:
    call zx48_od_create
    ret c
    ld (p405_open_od),a
    ld c,a
    ld a,HANDLE_FREE
    call zx48_handle_install
    jr c,zx48_p405_open_allocate_rollback
    ld (p405_result_handle),a
    ld l,a
    ld h,0
    xor a
    or a
    ret
zx48_p405_open_allocate_rollback:
    ld (p405_open_error),a
    ld a,(p405_open_od)
    call zx48_od_release
    ld a,(p405_open_error)
    scf
    ret

; HL=NUL path,C=open flags,B=creation type when O_CREATE.
zx48_sys_open:
    ld (p405_open_path),hl
    ld a,c
    ld (p405_open_flags),a
    ld a,b
    ld (p405_open_type),a

    ; Reject unknown flag bits and illegal dependencies before path/object mutation.
    ld a,(p405_open_flags)
    and $c0
    jp nz,zx48_p405_open_invalid
    ld a,(p405_open_flags)
    and O_READ+O_WRITE
    jp z,zx48_p405_open_invalid
    ld a,(p405_open_flags)
    and O_TRUNC+O_APPEND
    jr z,zx48_p405_open_excl_check
    ld a,(p405_open_flags)
    and O_WRITE
    jp z,zx48_p405_open_invalid
zx48_p405_open_excl_check:
    ld a,(p405_open_flags)
    and O_EXCL
    jr z,zx48_p405_open_type_check
    ld a,(p405_open_flags)
    and O_CREATE
    jp z,zx48_p405_open_invalid

zx48_p405_open_type_check:
    ld a,(p405_open_flags)
    and O_CREATE
    jr nz,zx48_p405_open_create_type
    ld a,(p405_open_type)
    or a
    jp nz,zx48_p405_open_invalid
    jr zx48_p405_open_resolve
zx48_p405_open_create_type:
    ld a,(p405_open_type)
    cp OBJ_CFG+1
    jp nc,zx48_p405_open_invalid

zx48_p405_open_resolve:
    ld hl,(p405_open_path)
    call zx48_path_resolve
    ret c
    ld (p405_open_dir),a
    ld a,c
    cp PATH_KIND_DIR
    jp z,zx48_p405_open_perm

    ld a,(p405_open_dir)
    cp DIR_DEV
    jp z,zx48_p405_open_device

    ; Resident exact-name RAM objects precede BCAT-only metadata.
    ld a,(p405_open_dir)
    ld hl,path_name
    call zx48_p405_object_lookup
    jr nc,zx48_p405_open_existing

    ld a,(p405_open_dir)
    ld hl,path_name
    call zx48_p405_is_bcat
    jp z,zx48_p405_open_again

    ld a,(p405_open_flags)
    and O_CREATE
    jp z,zx48_p405_open_noent
    ld a,(p405_open_type)
    or a
    jp z,zx48_p405_open_invalid
    ld b,a
    ld a,(p405_open_dir)
    ld hl,path_name
    call zx48_p405_object_create
    ret c
    ld a,c
    ld (p405_open_slot),a
    ld a,(ix+OBJ_TYPE_ID)
    ld (p405_result_type),a

    ; Publish an open description/handle. Exhaustion rolls the empty new object back.
    ld d,c
    ld b,OD_KIND_OBJECT
    ld a,(p405_open_flags)
    ld c,a
    call zx48_p405_open_allocate
    jr c,zx48_p405_open_create_rollback
    ld a,OD_KIND_OBJECT
    ld (p405_result_kind),a
    ld a,(p405_open_slot)
    ld (p405_result_id),a
    ret

zx48_p405_open_create_rollback:
    ld (p405_open_error),a
    ld a,(p405_open_slot)
    ld c,a
    call zx48_p405_object_rollback_create
    ld a,(p405_open_error)
    scf
    ret

zx48_p405_open_existing:
    ld a,c
    ld (p405_open_slot),a
    ld a,(ix+OBJ_TYPE_ID)
    ld (p405_result_type),a
    ld a,(p405_open_flags)
    and O_EXCL
    jp nz,zx48_p405_open_exist

    ; Reserve description+handle before O_TRUNC can mutate existing object state.
    ld a,(p405_open_slot)
    ld d,a
    ld b,OD_KIND_OBJECT
    ld a,(p405_open_flags)
    ld c,a
    call zx48_p405_open_allocate
    ret c
    ld a,OD_KIND_OBJECT
    ld (p405_result_kind),a
    ld a,(p405_open_slot)
    ld (p405_result_id),a

    ld a,(p405_open_flags)
    and O_TRUNC
    ret z
    ld a,(p405_open_slot)
    call zx48_p405_object_ptr_slot
    ret c
    call zx48_p405_object_truncate
    ret

zx48_p405_open_device:
    ld a,(p405_open_type)
    or a
    jp nz,zx48_p405_open_invalid
    ld a,(p405_open_flags)
    and O_CREATE+O_TRUNC+O_APPEND+O_EXCL
    jp nz,zx48_p405_open_perm
    ld a,(p405_open_dir)
    ld hl,path_name
    call zx48_p405_device_kind
    ret c
    ld (p405_result_kind),a
    ld b,a
    ld d,0
    ld a,(p405_open_flags)
    ld c,a
    call zx48_p405_open_allocate
    ret c
    xor a
    ld (p405_result_id),a
    ld (p405_result_type),a
    ret

; /dev/tape is control-only. Byte I/O and unsupported ioctls never move tape.
zx48_p405_tape_read:
zx48_p405_tape_write:
zx48_p405_tape_ioctl:
    ld a,E_NOTSUP
    scf
    ret

zx48_p405_open_invalid:
    ld a,E_INVAL
    scf
    ret
zx48_p405_open_noent:
    ld a,E_NOENT
    scf
    ret
zx48_p405_open_perm:
    ld a,E_PERM
    scf
    ret
zx48_p405_open_again:
    ld a,E_AGAIN
    scf
    ret
zx48_p405_open_exist:
    ld a,E_EXIST
    scf
    ret

p405_open_path: dw 0
p405_open_flags: db 0
p405_open_type: db 0
p405_open_dir: db 0
p405_open_slot: db 0
p405_open_od: db 0
p405_open_error: db 0
p405_result_kind: db 0
p405_result_id: db 0
p405_result_type: db 0
p405_result_flags EQU p405_open_flags
p405_result_handle: db 0
; Diagnostic stand-in for physical tape position/state; P4.05 routines never write it.
p405_tape_motion: db $5a
    ENDM


;
; P4.11 staged SYS_STAT ABI. Validate STAT1, the complete ten-byte output range,
; and every path byte before resolving metadata. Copy only after full success.
;
    MACRO EMIT_P411_SYS_STAT_ROUTINES
; HL -> STAT1 {u16 path_ptr,u16 out_ptr}.
zx48_p411_sys_stat:
    ld (p411_stat_req_ptr),hl
    ld bc,4
    call zx48_user_range_validate
    ret c

    ld hl,(p411_stat_req_ptr)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p411_stat_path_ptr),de
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld (p411_stat_out_ptr),de

    ex de,hl
    ld bc,10
    call zx48_user_range_validate
    ret c

    ; Validate the complete NUL-terminated path one byte at a time. This keeps
    ; raw repeated separators legal while preventing reads into protected memory.
    ld hl,(p411_stat_path_ptr)
zx48_p411_stat_path_validate:
    push hl
    ld bc,1
    call zx48_user_range_validate
    pop hl
    ret c
    ld a,(hl)
    or a
    jr z,zx48_p411_stat_path_ok
    inc hl
    jr zx48_p411_stat_path_validate

zx48_p411_stat_path_ok:
    ld hl,(p411_stat_path_ptr)
    call zx48_p411_stat_resolve
    ret c

    ld hl,p411_stat_record
    ld de,(p411_stat_out_ptr)
    ld bc,10
    ldir
    ld hl,0
    xor a
    ret

p411_stat_req_ptr: dw 0
p411_stat_path_ptr: dw 0
p411_stat_out_ptr: dw 0
    ENDM

; P7.01 staged graphics syscall ABI. The resident 8 KiB kernel code pool is already
; byte-full at the Phase-6 checkpoint, so Phase-7 graphics qualification emits
; this exact syscall surface in a bounded fixture until the later Phase-7
; integration/acceptance gate owns the final resident packing decision.
    MACRO EMIT_P701_GRAPHICS_SYSCALL_ROUTINES
zx48_p701_gfx_dispatch:
    cp SYS_GFX_PLOT
    jp c,zx48_p701_gfx_notsup
    cp SYS_GFX_POINT+1
    jp nc,zx48_p701_gfx_notsup
    sub SYS_GFX_PLOT
    add a,a
    ld e,a
    ld d,0
    ld hl,zx48_p701_gfx_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp (hl)

zx48_p701_gfx_plot:
    ld hl,(syscall_arg_hl)
    jp zx48_gfx_plot
zx48_p701_gfx_draw:
    ld hl,(syscall_arg_hl)
    ld bc,4
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    jp zx48_gfx_draw
zx48_p701_gfx_circle:
    ld hl,(syscall_arg_hl)
    ld bc,3
    call zx48_user_range_validate
    ret c
    ld hl,(syscall_arg_hl)
    jp zx48_gfx_circle
zx48_p701_gfx_attr:
    ld hl,(syscall_arg_hl)
    jp zx48_gfx_attr
zx48_p701_gfx_border:
    ld hl,(syscall_arg_hl)
    jp zx48_gfx_border
zx48_p701_gfx_point:
    ld hl,(syscall_arg_hl)
    jp zx48_gfx_point

zx48_p701_gfx_table:
    dw zx48_p701_gfx_plot,zx48_p701_gfx_draw,zx48_p701_gfx_circle
    dw zx48_p701_gfx_attr,zx48_p701_gfx_border,zx48_p701_gfx_point
zx48_p701_gfx_notsup:
    ld a,E_NOTSUP
    scf
    ret
    ENDM
