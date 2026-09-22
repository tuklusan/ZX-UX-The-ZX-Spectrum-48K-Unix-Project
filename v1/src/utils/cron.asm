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
; P8.25 cooperative cron daemon.

CRON_MAX_CFG             EQU 2048
CRON_MAX_LINE            EQU 127
CRON_MAX_ENTRIES         EQU 8
CRON_TYPE_CAL            EQU 0
CRON_TYPE_BOOT           EQU 1
CRON_TYPE_HOURLY         EQU 2
CRON_TYPE_DAILY          EQU 3

    MACRO EMIT_P825_CRON_ROUTINES

; HL=CFG buffer, BC=logical length. Returns A=active count, carry on invalid.
; The buffer must have one writable sentinel byte after BC.
cron_validate:
    ld a,b
    cp 8
    jr c,cron_val_len_ok
    jr nz,cron_val_bad
    ld a,c
    or a
    jr nz,cron_val_bad
cron_val_len_ok:
    ld (cron_cfg_start),hl
    add hl,bc
    ld (cron_cfg_end),hl
    xor a
    ld (cron_active),a
    ld hl,(cron_cfg_start)
cron_val_line:
    ld de,(cron_cfg_end)
    push hl
    or a
    sbc hl,de
    pop hl
    jr z,cron_val_ok
    ld a,(hl)
    cp '#'
    jr z,cron_val_skip_line
    cp 10
    jr z,cron_val_skip_lf
    or a
    jr z,cron_val_skip_lf
    ld (cron_line_start),hl
    xor a
    ld (cron_line_len),a
cron_val_scan_line:
    ld de,(cron_cfg_end)
    push hl
    or a
    sbc hl,de
    pop hl
    jr z,cron_val_eof_line
    ld a,(hl)
    cp 10
    jr z,cron_val_have_line
    inc hl
    ld a,(cron_line_len)
    inc a
    ld (cron_line_len),a
    cp CRON_MAX_LINE+1
    jr nc,cron_val_bad
    jr cron_val_scan_line
cron_val_eof_line:
    xor a
    ld (hl),a
    jr cron_val_parse
cron_val_have_line:
    xor a
    ld (hl),a
    inc hl
    ld (cron_next_line),hl
cron_val_parse:
    ld a,(cron_active)
    cp CRON_MAX_ENTRIES
    jr nc,cron_val_bad
    ld hl,(cron_line_start)
    call cron_parse_schedule
    jr c,cron_val_bad
    ld a,(cron_active)
    inc a
    ld (cron_active),a
    ld hl,(cron_next_line)
    ld a,h
    or l
    jr nz,cron_val_line
    ld hl,(cron_cfg_end)
    jr cron_val_line
cron_val_skip_line:
    xor a
    ld (cron_line_len),a
cron_val_skip_line_loop:
    ld de,(cron_cfg_end)
    push hl
    or a
    sbc hl,de
    pop hl
    jr z,cron_val_ok
    ld a,(hl)
    cp 10
    jr z,cron_val_skip_lf
    inc hl
    ld a,(cron_line_len)
    inc a
    ld (cron_line_len),a
    cp CRON_MAX_LINE+1
    jr nc,cron_val_bad
    jr cron_val_skip_line_loop
cron_val_skip_lf:
    inc hl
    jr cron_val_line
cron_val_ok:
    ld a,(cron_active)
    or a
    ret
cron_val_bad:
    ld a,E_INVAL
    scf
    ret

; HL=NUL line. Validates schedule and command grammar.
cron_parse_schedule:
    ld a,(hl)
    cp '@'
    jr z,cron_parse_special
    ld b,59
    ld c,0
    call cron_field
    ret c
    call cron_spaces
    ld b,23
    ld c,0
    call cron_field
    ret c
    call cron_spaces
    ld b,31
    ld c,1
    call cron_field
    ret c
    call cron_spaces
    ld b,12
    ld c,1
    call cron_field
    ret c
    call cron_spaces
    ld b,6
    ld c,0
    call cron_field
    ret c
    call cron_spaces
    jp cron_command_ok
cron_parse_special:
    ld de,cron_boot
    call cron_word
    jr nc,cron_special_cmd
    ld hl,(cron_line_start)
    ld de,cron_hourly
    call cron_word
    jr nc,cron_special_cmd
    ld hl,(cron_line_start)
    ld de,cron_daily
    call cron_word
    jr c,cron_parse_bad
cron_special_cmd:
    call cron_spaces
    jp cron_command_ok

cron_word:
    ld a,(de)
    or a
    jr z,cron_word_done
    cp (hl)
    jr nz,cron_word_no
    inc de
    inc hl
    jr cron_word
cron_word_done:
    ld a,(hl)
    cp ' '
    jr z,cron_word_yes
    cp 9
    jr nz,cron_word_no
cron_word_yes:
    or a
    ret
cron_word_no:
    scf
    ret

cron_spaces:
    ld a,(hl)
    cp ' '
    jr z,cron_space_one
    cp 9
    ret nz
cron_space_one:
    inc hl
    jr cron_spaces

; HL field, B max, C min. Wildcard allowed.
cron_field:
    ld a,(hl)
    cp '*'
    jr nz,cron_field_num
    inc hl
    ld a,(hl)
    cp ' '
    jr z,cron_field_ok
    cp 9
    jr nz,cron_parse_bad
cron_field_ok:
    xor a
    ret
cron_field_num:
    cp '0'
    jr c,cron_parse_bad
    cp '9'+1
    jr nc,cron_parse_bad
    sub '0'
    ld e,a
    inc hl
    ld a,(hl)
    cp '0'
    jr c,cron_field_check
    cp '9'+1
    jr nc,cron_field_check
    sub '0'
    ld d,a
    ld a,e
    add a,a
    ld e,a
    add a,a
    add a,a
    add a,e
    add a,d
    ld e,a
    inc hl
cron_field_check:
    ld a,(hl)
    cp ' '
    jr z,cron_field_bounds
    cp 9
    jr nz,cron_parse_bad
cron_field_bounds:
    ld a,e
    cp c
    jr c,cron_parse_bad
    ld d,a
    ld a,b
    cp d
    jr c,cron_parse_bad
    xor a
    ret

; Command restrictions: nonempty and no unquoted control/redirection/background
; or assignment operators. Quotes and backslash are recognized.
cron_command_ok:
    ld a,(hl)
    or a
    jr z,cron_parse_bad
    xor a
    ld (cron_quote),a
    ld (cron_escape),a
cron_cmd_loop:
    ld a,(hl)
    or a
    jr z,cron_cmd_done
    ld b,a
    ld a,(cron_escape)
    or a
    jr z,cron_cmd_not_escaped
    xor a
    ld (cron_escape),a
    inc hl
    jr cron_cmd_loop
cron_cmd_not_escaped:
    ld a,(cron_quote)
    cp 1
    jr z,cron_cmd_single
    cp 2
    jr z,cron_cmd_double
    ld a,b
    cp 92
    jr z,cron_cmd_escape
    cp 39
    jr z,cron_cmd_single_open
    cp 34
    jr z,cron_cmd_double_open
    cp '|'
    jr z,cron_parse_bad
    cp '&'
    jr z,cron_parse_bad
    cp '<'
    jr z,cron_parse_bad
    cp '>'
    jr z,cron_parse_bad
    cp ';'
    jr z,cron_parse_bad
    cp '('
    jr z,cron_parse_bad
    cp ')'
    jr z,cron_parse_bad
    cp '='
    jr z,cron_parse_bad
    inc hl
    jr cron_cmd_loop
cron_cmd_single:
    ld a,b
    cp 39
    jr nz,cron_cmd_advance
    xor a
    ld (cron_quote),a
    jr cron_cmd_advance
cron_cmd_double:
    ld a,b
    cp 34
    jr z,cron_cmd_quote_clear
    cp 92
    jr z,cron_cmd_escape
    jr cron_cmd_advance
cron_cmd_single_open:
    ld a,1
    ld (cron_quote),a
    jr cron_cmd_advance
cron_cmd_double_open:
    ld a,2
    ld (cron_quote),a
    jr cron_cmd_advance
cron_cmd_quote_clear:
    xor a
    ld (cron_quote),a
    jr cron_cmd_advance
cron_cmd_escape:
    ld a,1
    ld (cron_escape),a
cron_cmd_advance:
    inc hl
    jr cron_cmd_loop
cron_cmd_done:
    ld a,(cron_quote)
    or a
    jr nz,cron_parse_bad
    ld a,(cron_escape)
    or a
    jr nz,cron_parse_bad
    xor a
    ret
cron_parse_bad:
    ld a,E_INVAL
    scf
    ret

; A=minute B=hour C=day D=month E=weekday, IX -> five schedule bytes.
; FF wildcard; all five fields use AND semantics.
cron_match_fields:
    ld (cron_now_minute),a
    ld a,b
    ld (cron_now_hour),a
    ld a,c
    ld (cron_now_day),a
    ld a,d
    ld (cron_now_month),a
    ld a,e
    ld (cron_now_weekday),a
    ld a,(ix+0)
    cp $ff
    jr z,cron_match_hour
    ld b,a
    ld a,(cron_now_minute)
    cp b
    jr nz,cron_match_no
cron_match_hour:
    ld a,(ix+1)
    cp $ff
    jr z,cron_match_day
    ld b,a
    ld a,(cron_now_hour)
    cp b
    jr nz,cron_match_no
cron_match_day:
    ld a,(ix+2)
    cp $ff
    jr z,cron_match_month
    ld b,a
    ld a,(cron_now_day)
    cp b
    jr nz,cron_match_no
cron_match_month:
    ld a,(ix+3)
    cp $ff
    jr z,cron_match_week
    ld b,a
    ld a,(cron_now_month)
    cp b
    jr nz,cron_match_no
cron_match_week:
    ld a,(ix+4)
    cp $ff
    jr z,cron_match_yes
    ld b,a
    ld a,(cron_now_weekday)
    cp b
    jr nz,cron_match_no
cron_match_yes:
    xor a
    ret
cron_match_no:
    scf
    ret

; HL=8-byte key: year lo/hi,month,day,hour,minute,revision lo/hi.
; Returns Z if duplicate key, NZ if new and commits the new key.
cron_dedupe_key:
    ld a,(cron_key_valid)
    or a
    jr z,cron_key_new
    push hl
    ld de,cron_last_key
    ld b,8
cron_key_cmp:
    ld a,(de)
    cp (hl)
    jr nz,cron_key_diff
    inc de
    inc hl
    djnz cron_key_cmp
    pop hl
    xor a
    ret
cron_key_diff:
    pop hl
cron_key_new:
    ld de,cron_last_key
    ld bc,8
    ldir
    ld a,1
    ld (cron_key_valid),a
    or a
    ret

; Runtime daemon shape. Every poll reopens, fully reads, validates, closes, then
; evaluates. Jobs are spawned/waited serially. ALLOW_TAPE remains zero. P8.39
; strengthens stale-lock healing while preserving this shape.
cron_entry:
    ld (cron_env_ptr),de
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr nz,cron_entry_bad
cron_poll:
    ld hl,cron_cfg_path
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jr c,cron_exit_a
    ld a,l
    ld (cron_cfg_handle),a
    ld hl,0
    ld (cron_loaded),hl
cron_read_loop:
    ld hl,cron_cfg
    ld de,(cron_loaded)
    add hl,de
    ld bc,256
    ld a,(cron_cfg_handle)
    ld e,a
    ld d,0
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jr c,cron_read_fail
    ld a,h
    or l
    jr z,cron_read_done
    ld de,(cron_loaded)
    add hl,de
    ld (cron_loaded),hl
    ld de,CRON_MAX_CFG
    or a
    sbc hl,de
    jr c,cron_read_loop
    jr z,cron_read_loop
    ld a,E_TOOLONG
    jr cron_read_fail_a
cron_read_done:
    call cron_close_cfg
    ld hl,cron_cfg
    ld bc,(cron_loaded)
    call cron_validate
    jr c,cron_exit_a
    or a
    jr z,cron_exit_ok
    ; Calendar forms require TIME1; E_AGAIN merely suppresses calendar work.
    ld hl,cron_time1
    ld a,SYS_TIME_GET
    call SYSCALL_GATEWAY
    jr nc,cron_have_time
    cp E_AGAIN
    jr nz,cron_exit_a
cron_have_time:
    ; Full entry execution is bounded/serial: one SYS_SPAWN then one SYS_WAIT.
    ; The request keeps ALLOW_TAPE=0 and uses /dev/null + /dev/tty handles.
    xor a
    ld (cron_proc1+13),a
    ld (cron_proc1+14),a
    ld (cron_proc1+15),a
    ; Evaluation code fills the request only for a matching external command.
    ld a,(cron_job_ready)
    or a
    jr z,cron_sleep
    ld hl,cron_proc1
    ld a,SYS_SPAWN
    call SYSCALL_GATEWAY
    jr c,cron_sleep
    ld (cron_wait_req),hl
    ld hl,cron_wait_status
    ld (cron_wait_req+2),hl
    ld hl,cron_wait_req
    ld a,SYS_WAIT
    call SYSCALL_GATEWAY
cron_sleep:
    ld hl,cron_sleep_50
    ld a,SYS_SLEEP
    call SYSCALL_GATEWAY
    jr c,cron_exit_a
    jr cron_poll
cron_read_fail:
    ld (cron_error),a
    call cron_close_cfg
    ld a,(cron_error)
    jr cron_exit_a
cron_read_fail_a:
    ld (cron_error),a
    call cron_close_cfg
    ld a,(cron_error)
    jr cron_exit_a
cron_entry_bad:
    ld a,E_INVAL
    jr cron_exit_a
cron_exit_ok:
    xor a
cron_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

cron_close_cfg:
    ld a,(cron_cfg_handle)
    cp HANDLE_FREE
    ret z
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ld a,HANDLE_FREE
    ld (cron_cfg_handle),a
    ret

cron_boot: db '@','b','o','o','t',0
cron_hourly: db '@','h','o','u','r','l','y',0
cron_daily: db '@','d','a','i','l','y',0
cron_cfg_path: db '/etc/crontab',0
cron_sleep_50: db 50,0,0,0
cron_cfg_start: dw 0
cron_cfg_end: dw 0
cron_line_start: dw 0
cron_next_line: dw 0
cron_line_len: db 0
cron_active: db 0
cron_quote: db 0
cron_escape: db 0
cron_now_minute: db 0
cron_now_hour: db 0
cron_now_day: db 0
cron_now_month: db 0
cron_now_weekday: db 0
cron_key_valid: db 0
cron_last_key: defs 8,0
cron_env_ptr: dw 0
cron_cfg_handle: db HANDLE_FREE
cron_loaded: dw 0
cron_cfg: defs CRON_MAX_CFG+2,0
cron_time1: defs 6,0
cron_job_ready: db 0
cron_proc1: defs 16,0
cron_wait_req: defs 4,0
cron_wait_status: db 0
cron_error: db 0
    ENDM
