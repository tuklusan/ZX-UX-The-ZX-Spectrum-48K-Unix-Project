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
; P8.26 crontab transaction utility.

    INCLUDE "cron.asm"

    MACRO EMIT_P826_CRONTAB_ROUTINES
    EMIT_P825_CRON_ROUTINES

crontab_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 2
    jp nz,crontab_bad
    ld de,8
    add ix,de
crontab_skip0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,crontab_skip0
    ld a,(ix+0)
    cp '-'
    jp nz,crontab_bad
    ld a,(ix+1)
    cp 'l'
    jr z,crontab_list_check
    cp 'e'
    jp z,crontab_edit_check
    jp crontab_bad
crontab_list_check:
    ld a,(ix+2)
    or a
    jp nz,crontab_bad
    jp crontab_list
crontab_edit_check:
    ld a,(ix+2)
    or a
    jp nz,crontab_bad
    jp crontab_edit

crontab_list:
    ld hl,crontab_live
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,crontab_exit_a
    ld a,l
    ld (crontab_live_h),a
crontab_list_loop:
    ld a,(crontab_live_h)
    ld e,a
    ld d,0
    ld hl,crontab_buf
    ld bc,64
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,crontab_list_fail
    ld a,h
    or l
    jr z,crontab_list_done
    ld b,h
    ld c,l
    ld hl,crontab_buf
    call crontab_write_all
    jp c,crontab_list_fail
    jr crontab_list_loop
crontab_list_done:
    call crontab_close_live
    xor a
    jp crontab_exit_a
crontab_list_fail:
    ld (crontab_error),a
    call crontab_close_live
    ld a,(crontab_error)
    jp crontab_exit_a

crontab_edit:
    xor a
    ld (crontab_tmp_created),a
    ld (crontab_live_h),a
    ld (crontab_tmp_h),a
    ld (crontab_try),a
    ld a,SYS_GETPID
    call SYSCALL_GATEWAY
    jp c,crontab_exit_a
    ld (crontab_pid),hl

    ld hl,crontab_live
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,crontab_exit_a
    ld a,l
    ld (crontab_live_h),a

crontab_temp_try:
    call crontab_build_temp
    ld hl,crontab_temp
    ld c,O_WRITE|O_CREATE|O_EXCL
    ld b,OBJ_CFG
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jr nc,crontab_temp_open
    cp E_EXIST
    jp nz,crontab_cleanup_error
    ld a,(crontab_try)
    inc a
    ld (crontab_try),a
    cp 10
    jr c,crontab_temp_try
    ld a,E_EXIST
    jp crontab_cleanup_error
crontab_temp_open:
    ld a,l
    ld (crontab_tmp_h),a
    ld a,1
    ld (crontab_tmp_created),a

crontab_copy_loop:
    ld a,(crontab_live_h)
    ld e,a
    ld d,0
    ld hl,crontab_buf
    ld bc,64
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,crontab_cleanup_error
    ld a,h
    or l
    jr z,crontab_copy_done
    ld (crontab_count),hl
    ld b,h
    ld c,l
    ld a,(crontab_tmp_h)
    ld e,a
    ld d,0
    ld hl,crontab_buf
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jp c,crontab_cleanup_error
    ld de,(crontab_count)
    or a
    sbc hl,de
    jr z,crontab_copy_loop
    ld a,E_IO
    jp crontab_cleanup_error
crontab_copy_done:
    call crontab_close_live
    jp c,crontab_cleanup_error
    call crontab_close_tmp
    jp c,crontab_cleanup_error

    call crontab_spawn_vi
    jp c,crontab_cleanup_error
    ld a,(crontab_child_status)
    or a
    jr z,crontab_validate_edit
    ld a,(crontab_child_status)
    jp crontab_cleanup_error

crontab_validate_edit:
    ld hl,crontab_temp
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,crontab_cleanup_error
    ld a,l
    ld (crontab_tmp_h),a
    ld hl,0
    ld (crontab_loaded),hl
crontab_validate_read:
    ld hl,(crontab_loaded)
    ld de,2049
    ex de,hl
    or a
    sbc hl,de
    ex de,hl
    ld a,d
    or e
    jr z,crontab_too_long
    ld hl,crontab_cfg
    ld bc,(crontab_loaded)
    add hl,bc
    ld b,d
    ld c,e
    ld a,(crontab_tmp_h)
    ld e,a
    ld d,0
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,crontab_cleanup_error
    ld a,h
    or l
    jr z,crontab_validate_done_read
    ld de,(crontab_loaded)
    add hl,de
    ld (crontab_loaded),hl
    jp crontab_validate_read
crontab_too_long:
    ld a,E_TOOLONG
    jp crontab_cleanup_error
crontab_validate_done_read:
    call crontab_close_tmp
    jp c,crontab_cleanup_error
    ld hl,crontab_cfg
    ld bc,(crontab_loaded)
    call cron_validate
    jp c,crontab_cleanup_error
    ld (crontab_active),a

    ld hl,crontab_temp
    ld (crontab_ren1),hl
    ld hl,crontab_live
    ld (crontab_ren1+2),hl
    ld hl,crontab_ren1
    ld a,SYS_RENAME
    call SYSCALL_GATEWAY
    jp c,crontab_cleanup_error
    xor a
    ld (crontab_tmp_created),a

    ld a,(crontab_active)
    or a
    jr z,crontab_success
    call crontab_start_cron
    ; E_BUSY means an existing daemon already owns the lock and is success here.
    jr nc,crontab_success
    cp E_BUSY
    jr z,crontab_success
    jp crontab_exit_a

crontab_success:
    xor a
    jp crontab_exit_a

crontab_spawn_vi:
    ld hl,crontab_vi_path
    ld (crontab_proc1),hl
    call crontab_make_arg1
    ld hl,crontab_arg1
    ld (crontab_proc1+2),hl
    ld hl,(crontab_arg1_len)
    ld (crontab_proc1+4),hl
    xor a
    ld (crontab_proc1+6),a
    ld (crontab_proc1+7),a
    ld (crontab_proc1+8),a
    ld (crontab_proc1+9),a
    ld a,0
    ld (crontab_proc1+10),a
    ld a,1
    ld (crontab_proc1+11),a
    ld a,2
    ld (crontab_proc1+12),a
    xor a
    ld (crontab_proc1+13),a
    ld (crontab_proc1+14),a
    ld (crontab_proc1+15),a
    call crontab_authorize_vi_tape
    ret c
    ld hl,crontab_proc1
    ld a,SYS_SPAWN
    call SYSCALL_GATEWAY
    ret c
    ld (crontab_wait),hl
    ld hl,crontab_child_status
    ld (crontab_wait+2),hl
    ld hl,crontab_wait
    ld a,SYS_WAIT
    jp SYSCALL_GATEWAY

crontab_authorize_vi_tape:
    ; Resolve /bin/vi first.  A tape-backed editor is authorized only after
    ; explicit foreground consent; declining returns E_AGAIN before SYS_SPAWN.
    ld hl,crontab_vi_path
    ld (crontab_vi_stat_req),hl
    ld hl,crontab_vi_stat_out
    ld (crontab_vi_stat_req+2),hl
    ld hl,crontab_vi_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    ret c
    xor a
    ld (crontab_proc1+13),a
    ld a,(crontab_vi_stat_out+7)
    cp STATE_TAPE_BACKED
    ret nz
    ld hl,crontab_tape_prompt
    ld bc,52
    ld a,SYS_CON_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld de,0
    ld hl,crontab_tape_reply
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,crontab_tape_decline
    ld a,l
    cp 1
    jr nz,crontab_tape_decline
    ld a,(crontab_tape_reply)
    cp 'y'
    jr z,crontab_tape_accept
    cp 'Y'
    jr nz,crontab_tape_decline
crontab_tape_accept:
    ld a,1
    ld (crontab_proc1+13),a
    xor a
    ret
crontab_tape_decline:
    ld a,E_AGAIN
    scf
    ret

crontab_start_cron:
    ld hl,crontab_cron_path
    ld (crontab_proc1),hl
    ld hl,crontab_cron_arg1
    ld (crontab_proc1+2),hl
    ld hl,13
    ld (crontab_proc1+4),hl
    xor a
    ld (crontab_proc1+6),a
    ld (crontab_proc1+7),a
    ld (crontab_proc1+8),a
    ld (crontab_proc1+9),a
    ld a,0
    ld (crontab_proc1+10),a
    ld a,1
    ld (crontab_proc1+11),a
    ld a,2
    ld (crontab_proc1+12),a
    xor a
    ld (crontab_proc1+13),a
    ld (crontab_proc1+14),a
    ld (crontab_proc1+15),a
    ld hl,crontab_proc1
    ld a,SYS_SPAWN
    jp SYSCALL_GATEWAY

crontab_make_arg1:
    ld hl,crontab_arg1_template
    ld de,crontab_arg1
    ld bc,12
    ldir
    ld hl,crontab_temp
    ld de,crontab_arg1+12
    ld bc,0
crontab_arg_copy:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    inc bc
    or a
    jr nz,crontab_arg_copy
    ld hl,12
    add hl,bc
    ld (crontab_arg1_len),hl
    ret

crontab_build_temp:
    ld hl,crontab_temp_prefix
    ld de,crontab_temp
    ld bc,8
    ldir
    push de
    pop ix
    ld hl,(crontab_pid)
    xor a
    ld (crontab_dec_started),a
    ld de,10000
    call crontab_dec_place
    ld de,1000
    call crontab_dec_place
    ld de,100
    call crontab_dec_place
    ld de,10
    call crontab_dec_place
    ld a,l
    add a,'0'
    ld (ix+0),a
    inc ix
    ld a,'.'
    ld (ix+0),a
    inc ix
    ld a,(crontab_try)
    add a,'0'
    ld (ix+0),a
    inc ix
    xor a
    ld (ix+0),a
    ret

crontab_dec_place:
    ld c,0
crontab_dec_sub:
    or a
    sbc hl,de
    jr c,crontab_dec_done
    inc c
    jr crontab_dec_sub
crontab_dec_done:
    add hl,de
    ld a,(crontab_dec_started)
    or c
    ret z
    ld a,1
    ld (crontab_dec_started),a
    ld a,c
    add a,'0'
    ld (ix+0),a
    inc ix
    ret

crontab_close_live:
    ld a,(crontab_live_h)
    or a
    ret z
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    xor a
    ld (crontab_live_h),a
    ret
crontab_close_tmp:
    ld a,(crontab_tmp_h)
    or a
    ret z
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    xor a
    ld (crontab_tmp_h),a
    ret

crontab_cleanup_error:
    ld (crontab_error),a
    call crontab_close_live
    call crontab_close_tmp
    ld a,(crontab_tmp_created)
    or a
    jr z,crontab_cleanup_done
    ld hl,crontab_temp
    ld a,SYS_REMOVE
    call SYSCALL_GATEWAY
crontab_cleanup_done:
    ld a,(crontab_error)
    jp crontab_exit_a

crontab_write_all:
    ld (crontab_wptr),hl
    ld (crontab_wleft),bc
crontab_write_loop:
    ld hl,(crontab_wptr)
    ld bc,(crontab_wleft)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,crontab_write_zero
    ld (crontab_wrote),hl
    ld de,(crontab_wptr)
    add hl,de
    ld (crontab_wptr),hl
    ld hl,(crontab_wleft)
    ld de,(crontab_wrote)
    or a
    sbc hl,de
    jr c,crontab_write_zero
    ld (crontab_wleft),hl
    ld a,h
    or l
    jr nz,crontab_write_loop
    xor a
    ret
crontab_write_zero:
    ld a,E_IO
    scf
    ret

crontab_bad:
    ld a,E_INVAL
crontab_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

crontab_live: db '/etc/crontab',0
crontab_vi_path: db '/bin/vi',0
crontab_vi_stat_req: defs 4,0
crontab_vi_stat_out: defs 10,0
crontab_tape_prompt:
    db 'c','a','s','s','e','t','t','e',' ','r','e','q','u','i','r','e','d',';',' '
    db 'p','o','s','i','t','i','o','n',' ','t','a','p','e','/','P','L','A','Y'
    db ',',' ','t','h','e','n',' ','p','r','e','s','s',' ','y',':',' '
crontab_tape_reply: db 0
crontab_cron_path: db '/bin/cron',0
crontab_temp_prefix: db '/tmp/.ct'
crontab_temp: defs 24,0
crontab_arg1_template: db 'A','R','G','1',2,0,0,0,'v','i',0,0
crontab_cron_arg1: db 'A','R','G','1',1,0,13,0,'c','r','o','n',0
crontab_arg1: defs 64,0
crontab_arg1_len: dw 0
crontab_proc1: defs 16,0
crontab_wait: defs 4,0
crontab_child_status: db 0
crontab_live_h: db 0
crontab_tmp_h: db 0
crontab_tmp_created: db 0
crontab_try: db 0
crontab_pid: dw 0
crontab_count: dw 0
crontab_loaded: dw 0
crontab_active: db 0
crontab_error: db 0
crontab_dec_started: db 0
crontab_ren1: defs 4,0
crontab_buf: defs 64,0
crontab_cfg: defs 2050,0
crontab_wptr: dw 0
crontab_wleft: dw 0
crontab_wrote: dw 0
    ENDM
