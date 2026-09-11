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
; Fixed E000 syscall gateway. Table dispatch keeps deliberate number gaps cheap.

    MACRO EMIT_SYSCALL_GATEWAY
syscall_gateway:
    jp zx48_syscall_dispatch
    ENDM

    MACRO EMIT_SYSCALL_BODY
zx48_syscall_dispatch:
    jp zx48_syscall_dispatch_impl
    ENDM

    MACRO EMIT_SYSCALL_IMPL
zx48_syscall_dispatch_impl:
    push ix
    ld b,a
    ld hl,zx48_syscall_table
zx48_syscall_find:
    ld a,(hl)
    cp $ff
    jr z,zx48_sc_notsup
    cp b
    jr z,zx48_syscall_found
    inc hl
    inc hl
    inc hl
    jr zx48_syscall_find
zx48_syscall_found:
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp (hl)

; BC=count,HL=base. Zero count succeeds. Valid ranges: shared display or arena.
zx48_validate_user_range:
    ld a,b
    or c
    ret z
    ld (sc_ptr),hl
    add hl,bc
    jr c,zx48_validate_bad
    ld (sc_end),hl
    ld hl,(sc_ptr)
    ld a,h
    cp $40
    jr c,zx48_validate_bad
    cp $5b
    jr c,zx48_validate_display
    cp $60
    jr c,zx48_validate_bad
    cp $e0
    jr nc,zx48_validate_bad
    ld hl,(sc_end)
    ld a,h
    cp $e0
    jr c,zx48_validate_ok
    jr nz,zx48_validate_bad
    ld a,l
    or a
    jr z,zx48_validate_ok
    jr zx48_validate_bad
zx48_validate_display:
    ld hl,(sc_end)
    ld a,h
    cp $5b
    jr c,zx48_validate_ok
    jr nz,zx48_validate_bad
    ld a,l
    or a
    jr z,zx48_validate_ok
zx48_validate_bad:
    ld a,E_INVAL
    scf
    ret
zx48_validate_ok:
    xor a
    or a
    ret

zx48_sc_version:
    ld hl,ZXUX_ABI_VERSION
    xor a
    or a
    jr zx48_sc_return
zx48_sc_exit:
    ld a,l
    call zx48_process_exit
    jr zx48_sc_return
zx48_sc_yield:
    call zx48_schedule
    xor a
    or a
    jr zx48_sc_return
zx48_sc_sleep:
    ld bc,4
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_sleep_current
    jr zx48_sc_return
zx48_sc_getpid:
    ld a,(current_pid)
    ld l,a
    ld h,0
    xor a
    or a
    jr zx48_sc_return
zx48_sc_spawn:
    call zx48_process_spawn
    jr zx48_sc_return
zx48_sc_exec:
    call zx48_process_exec
    jr zx48_sc_return
zx48_sc_wait:
    ld bc,4
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld a,d
    cp $ff
    jr z,zx48_sc_wait_any
    or a
    jr nz,zx48_sc_bad
    ld a,e
    jr zx48_sc_wait_target
zx48_sc_wait_any:
    ld a,e
    cp $ff
    jr nz,zx48_sc_bad
zx48_sc_wait_target:
    ld (sc_pid),a
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld bc,1
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ex de,hl
    ld a,(sc_pid)
    call zx48_process_wait
    jr zx48_sc_return
zx48_sc_kill:
    ld a,h
    or a
    jr nz,zx48_sc_bad
    ld a,l
    call zx48_process_kill
    jr zx48_sc_return

zx48_sc_open:
    call zx48_object_open
    jr zx48_sc_return
zx48_sc_close:
    ld a,h
    or a
    jr nz,zx48_sc_bad
    ld c,l
    ld a,(current_pid)
    call zx48_process_lookup
    jr c,zx48_sc_return
    call zx48_close
    jr zx48_sc_return
zx48_sc_read:
    ld (sc_ptr),hl
    ld (sc_count),bc
    ld a,d
    or a
    jr nz,zx48_sc_bad
    ld a,e
    ld (sc_handle),a
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_sc_lookup_od
    jr c,zx48_sc_return
    ld a,(ix+OD_KIND)
    cp OD_KIND_NULL
    jr z,zx48_sc_zero
    cp OD_KIND_OBJECT
    jr z,zx48_sc_read_object
    cp OD_KIND_PIPE_READ
    jr z,zx48_sc_read_pipe
    cp OD_KIND_TTY
    jr z,zx48_sc_read_tty
    jr zx48_sc_notsup
zx48_sc_read_object:
    ld hl,(sc_ptr)
    ld bc,(sc_count)
    call zx48_object_read_od
    jr zx48_sc_return
zx48_sc_read_pipe:
    ld a,(ix+OD_IDENTITY)
    ld hl,(sc_ptr)
    ld bc,(sc_count)
    call zx48_pipe_read
    jr zx48_sc_return
zx48_sc_read_tty:
    ld bc,(sc_count)
    ld a,b
    or c
    jr z,zx48_sc_zero
    call zx48_keyboard_getkey
    jr c,zx48_sc_return
    ld hl,(sc_ptr)
    ld (hl),a
    ld hl,1
    xor a
    or a
    jr zx48_sc_return
zx48_sc_zero:
    ld hl,0
    xor a
    or a
    jr zx48_sc_return

zx48_sc_write:
    ld (sc_ptr),hl
    ld (sc_count),bc
    ld a,d
    or a
    jr nz,zx48_sc_bad
    ld a,e
    ld (sc_handle),a
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_sc_lookup_od
    jr c,zx48_sc_return
    ld a,(ix+OD_KIND)
    cp OD_KIND_NULL
    jr z,zx48_sc_write_null
    cp OD_KIND_OBJECT
    jr z,zx48_sc_write_object
    cp OD_KIND_PIPE_WRITE
    jr z,zx48_sc_write_pipe
    cp OD_KIND_TTY
    jr z,zx48_sc_write_tty
    jr zx48_sc_notsup
zx48_sc_write_null:
    ld hl,(sc_count)
    xor a
    or a
    jr zx48_sc_return
zx48_sc_write_object:
    ld hl,(sc_ptr)
    ld bc,(sc_count)
    call zx48_object_write_od
    jr zx48_sc_return
zx48_sc_write_pipe:
    ld a,(ix+OD_IDENTITY)
    ld hl,(sc_ptr)
    ld bc,(sc_count)
    call zx48_pipe_write
    jr zx48_sc_return
zx48_sc_write_tty:
    ld hl,(sc_ptr)
    ld bc,(sc_count)
    call zx48_console_write
    jr zx48_sc_return

zx48_sc_seek:
    ld (sc_ptr),hl
    ld a,d
    or a
    jr nz,zx48_sc_bad
    ld a,e
    ld (sc_handle),a
    call zx48_sc_lookup_od
    jr c,zx48_sc_return
    ld a,(ix+OD_KIND)
    cp OD_KIND_OBJECT
    jr nz,zx48_sc_notsup
    ld hl,(sc_ptr)
    ld (object_od_ptr),ix
    call zx48_object_seek_od
    jr zx48_sc_return
zx48_sc_stat:
    ld bc,4
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    ld d,b
    ld e,c
    call zx48_object_stat
    jr zx48_sc_return
zx48_sc_remove:
    call zx48_object_remove
    jr zx48_sc_return
zx48_sc_rename:
    call zx48_object_rename
    jr zx48_sc_return
zx48_sc_list:
    ld bc,6
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld a,(hl)
    or a
    jr nz,zx48_sc_bad
    inc hl
    ld a,(hl)
    inc hl
    ld h,(hl)
    ld l,a
    push hl
    ex de,hl
    pop de
    call zx48_object_list
    jr zx48_sc_return
zx48_sc_chdir:
    call zx48_object_chdir
    jr zx48_sc_return
zx48_sc_getcwd:
    call zx48_object_getcwd
    jr zx48_sc_return
zx48_sc_pack:
    call zx48_object_pack
    jr zx48_sc_return
zx48_sc_unpack:
    call zx48_object_unpack
    jr zx48_sc_return

zx48_sc_pipe:
    ld bc,2
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_pipe_create
    jr zx48_sc_return
zx48_sc_dup:
    ld bc,2
    call zx48_validate_user_range
    jr c,zx48_sc_return
    push hl
    ld a,(current_pid)
    call zx48_process_lookup
    pop hl
    jr c,zx48_sc_return
    call zx48_dup
    jr zx48_sc_return
zx48_sc_ioctl:
    ld bc,4
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld a,(hl)
    ld (sc_handle),a
    push hl
    call zx48_sc_lookup_od
    pop hl
    jr c,zx48_sc_return
    ld a,(ix+OD_KIND)
    cp OD_KIND_TTY
    jr nz,zx48_sc_notsup
    call zx48_tty_ioctl
    jr zx48_sc_return

zx48_sc_getkey:
    call zx48_keyboard_getkey
    jr c,zx48_sc_return
    ld l,a
    ld h,0
    xor a
    or a
    jr zx48_sc_return
zx48_sc_putchar:
    ld a,h
    or a
    jr nz,zx48_sc_bad
    ld a,l
    call zx48_console_putchar
    jr zx48_sc_return
zx48_sc_conwrite:
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_console_write
    jr zx48_sc_return
zx48_sc_clear:
    call zx48_console_clear
    xor a
    or a
    jr zx48_sc_return
zx48_sc_getpos:
    call zx48_console_getpos
    jr zx48_sc_return
zx48_sc_setpos:
    call zx48_console_setpos
    jr zx48_sc_return

zx48_sc_plot:
    call zx48_gfx_plot
    jr zx48_sc_return
zx48_sc_draw:
    ld bc,4
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_gfx_draw
    jr zx48_sc_return
zx48_sc_circle:
    ld bc,3
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_gfx_circle
    jr zx48_sc_return
zx48_sc_attr:
    call zx48_gfx_attr
    jr zx48_sc_return
zx48_sc_border:
    call zx48_gfx_border
    jr zx48_sc_return
zx48_sc_point:
    call zx48_gfx_point
    jr zx48_sc_return
zx48_sc_beep:
    ld (sc_ptr),hl
    ld (sc_ptr2),de
    ld bc,5
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld hl,(sc_ptr2)
    ld bc,5
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld hl,(sc_ptr)
    ld de,(sc_ptr2)
    call zx48_sound_beep
    jr zx48_sc_return

zx48_sc_udg_define:
    ld (sc_ptr),hl
    ld a,c
    ld (sc_slot),a
    ld a,b
    ld (sc_zero),a
    ld bc,8
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld hl,(sc_ptr)
    ld a,(sc_slot)
    ld c,a
    ld a,(sc_zero)
    ld b,a
    call zx48_udg_define
    jr zx48_sc_return
zx48_sc_udg_draw:
    ld bc,3
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_udg_draw
    jr zx48_sc_return
zx48_sc_udg_get:
    ld (sc_ptr),hl
    ld a,c
    ld (sc_slot),a
    ld a,b
    ld (sc_zero),a
    ld bc,8
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld hl,(sc_ptr)
    ld a,(sc_slot)
    ld c,a
    ld a,(sc_zero)
    ld b,a
    call zx48_udg_get
    jr zx48_sc_return
zx48_sc_udg_clear:
    call zx48_udg_clear
    jr zx48_sc_return

zx48_sc_tape_save:
    call zx48_tape_save_path
    jr zx48_sc_return
zx48_sc_tape_load:
    call zx48_tape_load_path
    jr zx48_sc_return
zx48_sc_tape_verify:
    call zx48_tape_verify_path
    jr zx48_sc_return
zx48_sc_tape_scan:
    ld bc,M48O_HEADER_SIZE
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_tape_scan_next
    jr zx48_sc_return

zx48_sc_meminfo:
    ld bc,MINFO1_SIZE
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld (sc_ptr),hl
    call zx48_mem_info
    call zx48_process_count
    ld hl,(sc_ptr)
    ld de,14
    add hl,de
    ld (hl),a
    xor a
    or a
    jr zx48_sc_return
zx48_sc_procinfo:
    ld bc,4
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld a,(hl)
    ld (sc_pid),a
    inc hl
    ld a,(hl)
    or a
    jr nz,zx48_sc_bad
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld bc,16
    call zx48_validate_user_range
    jr c,zx48_sc_return
    ld a,(sc_pid)
    call zx48_process_info
    jr zx48_sc_return
zx48_sc_ticks:
    ld bc,4
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_ticks_snapshot
    jr zx48_sc_return
zx48_sc_timeget:
    ld bc,6
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_time_get
    jr zx48_sc_return
zx48_sc_timeset:
    ld bc,4
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_time_set
    jr zx48_sc_return
zx48_sc_zxpackinfo:
    ld bc,ZPINFO1_SIZE
    call zx48_validate_user_range
    jr c,zx48_sc_return
    call zx48_zxpack_info
    jr zx48_sc_return

; Calculator/ROM services are centralized in rom_services.asm.
zx48_sc_fp_exec:
    call zx48_fp_exec
    jr zx48_sc_return
zx48_sc_fp_to_text:
    call zx48_fp_to_text
    jr zx48_sc_return
zx48_sc_fp_from_text:
    call zx48_fp_from_text
    jr zx48_sc_return
zx48_sc_rom_info:
    call zx48_rom_info
    jr zx48_sc_return
zx48_sc_int_to_fp:
    call zx48_int_to_fp
    jr zx48_sc_return
zx48_sc_fp_to_int:
    call zx48_fp_to_int
    jr zx48_sc_return
zx48_sc_fp_cmp:
    call zx48_fp_cmp
    jr zx48_sc_return

zx48_sc_lookup_od:
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    ld a,(sc_handle)
    ld c,a
    call zx48_handle_lookup
    ret c
    jp zx48_od_lookup
zx48_sc_bad:
    ld a,E_INVAL
    scf
    jr zx48_sc_return
zx48_sc_notsup:
    ld a,E_NOTSUP
    scf
zx48_sc_return:
    ld iy,ROM_IY_ANCHOR
    pop ix
    ret

zx48_syscall_table:
    db SYS_VERSION
    dw zx48_sc_version
    db SYS_EXIT
    dw zx48_sc_exit
    db SYS_YIELD
    dw zx48_sc_yield
    db SYS_SLEEP
    dw zx48_sc_sleep
    db SYS_GETPID
    dw zx48_sc_getpid
    db SYS_SPAWN
    dw zx48_sc_spawn
    db SYS_EXEC
    dw zx48_sc_exec
    db SYS_WAIT
    dw zx48_sc_wait
    db SYS_KILL
    dw zx48_sc_kill
    db SYS_OPEN
    dw zx48_sc_open
    db SYS_CLOSE
    dw zx48_sc_close
    db SYS_READ
    dw zx48_sc_read
    db SYS_WRITE
    dw zx48_sc_write
    db SYS_SEEK
    dw zx48_sc_seek
    db SYS_STAT
    dw zx48_sc_stat
    db SYS_REMOVE
    dw zx48_sc_remove
    db SYS_RENAME
    dw zx48_sc_rename
    db SYS_LIST
    dw zx48_sc_list
    db SYS_CHDIR
    dw zx48_sc_chdir
    db SYS_GETCWD
    dw zx48_sc_getcwd
    db SYS_PACK
    dw zx48_sc_pack
    db SYS_UNPACK
    dw zx48_sc_unpack
    db SYS_PIPE
    dw zx48_sc_pipe
    db SYS_DUP
    dw zx48_sc_dup
    db SYS_IOCTL
    dw zx48_sc_ioctl
    db SYS_CON_GETKEY
    dw zx48_sc_getkey
    db SYS_CON_PUTCHAR
    dw zx48_sc_putchar
    db SYS_CON_WRITE
    dw zx48_sc_conwrite
    db SYS_CON_CLEAR
    dw zx48_sc_clear
    db SYS_CON_GETPOS
    dw zx48_sc_getpos
    db SYS_CON_SETPOS
    dw zx48_sc_setpos
    db SYS_GFX_PLOT
    dw zx48_sc_plot
    db SYS_GFX_DRAW
    dw zx48_sc_draw
    db SYS_GFX_CIRCLE
    dw zx48_sc_circle
    db SYS_GFX_ATTR
    dw zx48_sc_attr
    db SYS_GFX_BORDER
    dw zx48_sc_border
    db SYS_GFX_POINT
    dw zx48_sc_point
    db SYS_BEEP
    dw zx48_sc_beep
    db SYS_UDG_DEFINE
    dw zx48_sc_udg_define
    db SYS_UDG_DRAW
    dw zx48_sc_udg_draw
    db SYS_UDG_GET
    dw zx48_sc_udg_get
    db SYS_UDG_CLEAR
    dw zx48_sc_udg_clear
    db SYS_TAPE_SAVE
    dw zx48_sc_tape_save
    db SYS_TAPE_LOAD
    dw zx48_sc_tape_load
    db SYS_TAPE_VERIFY
    dw zx48_sc_tape_verify
    db SYS_TAPE_SCAN
    dw zx48_sc_tape_scan
    db SYS_MEM_INFO
    dw zx48_sc_meminfo
    db SYS_PROC_INFO
    dw zx48_sc_procinfo
    db SYS_TICKS
    dw zx48_sc_ticks
    db SYS_TIME_GET
    dw zx48_sc_timeget
    db SYS_TIME_SET
    dw zx48_sc_timeset
    db SYS_ZXPACK_INFO
    dw zx48_sc_zxpackinfo
    db SYS_FP_EXEC
    dw zx48_sc_fp_exec
    db SYS_FP_TO_TEXT
    dw zx48_sc_fp_to_text
    db SYS_FP_FROM_TEXT
    dw zx48_sc_fp_from_text
    db SYS_ROM_INFO
    dw zx48_sc_rom_info
    db SYS_INT_TO_FP
    dw zx48_sc_int_to_fp
    db SYS_FP_TO_INT
    dw zx48_sc_fp_to_int
    db SYS_FP_CMP
    dw zx48_sc_fp_cmp
    db $ff

sc_ptr: dw 0
sc_ptr2: dw 0
sc_end: dw 0
sc_count: dw 0
sc_handle: db 0
sc_pid: db 0
sc_slot: db 0
sc_zero: db 0
    ENDM
