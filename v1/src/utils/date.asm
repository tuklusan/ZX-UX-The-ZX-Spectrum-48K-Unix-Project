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
; P8.24 external date utility.

    MACRO EMIT_P824_DATE_ROUTINES
date_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr z,date_show
    cp 3
    jp nz,date_bad
    ld de,8
    add ix,de
date_skip0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,date_skip0
    ld a,(ix+0)
    cp '-'
    jp nz,date_bad
    ld a,(ix+1)
    cp 's'
    jp nz,date_bad
    ld a,(ix+2)
    or a
    jp nz,date_bad
    push ix
    pop hl
    call date_advance_z
    call date_parse_set
    jr c,date_exit_a
    ld hl,date_time
    ld a,SYS_TIME_SET
    call SYSCALL_GATEWAY
    jr c,date_exit_a
    xor a
    jr date_exit_a

date_show:
    ld hl,date_time
    ld a,SYS_TIME_GET
    call SYSCALL_GATEWAY
    jr nc,date_show_valid
    cp E_AGAIN
    jr nz,date_exit_a
    ld hl,date_not_set
    call date_write_z
    jr c,date_exit_a
    ld a,E_AGAIN
    jr date_exit_a
date_show_valid:
    call date_seconds_to_fields
    call date_format
    ld hl,date_out
    ld bc,20
    call date_write_all
    jr c,date_exit_a
    xor a
    jr date_exit_a

date_bad:
    ld a,E_INVAL
date_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

date_advance_z:
    ld a,(hl)
    inc hl
    or a
    jr nz,date_advance_z
    ret

; Parse exact YYYY-MM-DD hh:mm:ss at HL and build date_time seconds.
date_parse_set:
    ld de,date_parse_buf
    ld b,19
date_parse_copy:
    ld a,(hl)
    or a
    jp z,date_parse_bad
    ld (de),a
    inc hl
    inc de
    djnz date_parse_copy
    ld a,(hl)
    or a
    jp nz,date_parse_bad

    ld hl,date_parse_buf
    call date_parse_4
    jp c,date_parse_bad
    ld (date_year),de
    ld a,(date_parse_buf+4)
    cp '-'
    jp nz,date_parse_bad
    ld hl,date_parse_buf+5
    call date_parse_2
    jp c,date_parse_bad
    ld (date_month),a
    ld a,(date_parse_buf+7)
    cp '-'
    jp nz,date_parse_bad
    ld hl,date_parse_buf+8
    call date_parse_2
    jp c,date_parse_bad
    ld (date_day),a
    ld a,(date_parse_buf+10)
    cp ' '
    jp nz,date_parse_bad
    ld hl,date_parse_buf+11
    call date_parse_2
    jp c,date_parse_bad
    ld (date_hour),a
    ld a,(date_parse_buf+13)
    cp ':'
    jp nz,date_parse_bad
    ld hl,date_parse_buf+14
    call date_parse_2
    jp c,date_parse_bad
    ld (date_minute),a
    ld a,(date_parse_buf+16)
    cp ':'
    jp nz,date_parse_bad
    ld hl,date_parse_buf+17
    call date_parse_2
    jp c,date_parse_bad
    ld (date_second),a

    ld hl,(date_year)
    ld de,1970
    or a
    sbc hl,de
    jp c,date_parse_bad
    ld hl,(date_year)
    ld de,2100
    or a
    sbc hl,de
    jp nc,date_parse_bad
    ld a,(date_month)
    or a
    jp z,date_parse_bad
    cp 13
    jp nc,date_parse_bad
    ld a,(date_hour)
    cp 24
    jp nc,date_parse_bad
    ld a,(date_minute)
    cp 60
    jp nc,date_parse_bad
    ld a,(date_second)
    cp 60
    jp nc,date_parse_bad

    call date_month_length_current
    ld b,a
    ld a,(date_day)
    or a
    jp z,date_parse_bad
    cp b
    jr c,date_parse_valid_day
    jr z,date_parse_valid_day
    jp date_parse_bad
date_parse_valid_day:
    call date_fields_to_seconds
    or a
    ret
date_parse_bad:
    ld a,E_INVAL
    scf
    ret

; HL points at 4 digits, DE=result.
date_parse_4:
    ld de,0
    ld b,4
date_parse_4_loop:
    ld a,(hl)
    cp '0'
    jr c,date_parse_digit_bad
    cp '9'+1
    jr nc,date_parse_digit_bad
    sub '0'
    ld c,a
    push hl
    ex de,hl
    add hl,hl
    push hl
    add hl,hl
    add hl,hl
    pop de
    add hl,de
    ld e,c
    ld d,0
    add hl,de
    ex de,hl
    pop hl
    inc hl
    djnz date_parse_4_loop
    or a
    ret

; HL points at 2 digits, A=result.
date_parse_2:
    ld a,(hl)
    cp '0'
    jr c,date_parse_digit_bad
    cp '9'+1
    jr nc,date_parse_digit_bad
    sub '0'
    ld b,a
    inc hl
    ld a,(hl)
    cp '0'
    jr c,date_parse_digit_bad
    cp '9'+1
    jr nc,date_parse_digit_bad
    sub '0'
    ld c,a
    ld a,b
    add a,a
    ld b,a
    add a,a
    add a,a
    add a,b
    add a,c
    or a
    ret
date_parse_digit_bad:
    ld a,E_INVAL
    scf
    ret

; Convert TIME1 seconds to year/month/day/hour/min/sec.
date_seconds_to_fields:
    ld hl,(date_time)
    ld (date_work),hl
    ld hl,(date_time+2)
    ld (date_work+2),hl
    ld hl,0
    ld (date_days),hl
date_day_div_loop:
    ld hl,(date_work+2)
    ld a,h
    or a
    jr nz,date_day_sub
    ld a,l
    cp 1
    jr c,date_day_div_done
    jr nz,date_day_sub
    ld hl,(date_work)
    ld de,$5180
    or a
    sbc hl,de
    jr c,date_day_div_done
date_day_sub:
    ld hl,(date_work)
    ld de,$5180
    or a
    sbc hl,de
    ld (date_work),hl
    ld hl,(date_work+2)
    ld de,1
    sbc hl,de
    ld (date_work+2),hl
    ld hl,(date_days)
    inc hl
    ld (date_days),hl
    jr date_day_div_loop
date_day_div_done:
    xor a
    ld (date_hour),a
date_hour_loop:
    ld hl,(date_work+2)
    ld a,h
    or l
    jr nz,date_hour_sub
    ld hl,(date_work)
    ld de,3600
    or a
    sbc hl,de
    jr c,date_hour_done
date_hour_sub:
    ld hl,(date_work)
    ld de,3600
    or a
    sbc hl,de
    ld (date_work),hl
    ld hl,(date_work+2)
    ld de,0
    sbc hl,de
    ld (date_work+2),hl
    ld a,(date_hour)
    inc a
    ld (date_hour),a
    jr date_hour_loop
date_hour_done:
    xor a
    ld (date_minute),a
date_min_loop:
    ld hl,(date_work)
    ld de,60
    or a
    sbc hl,de
    jr c,date_min_done
    ld (date_work),hl
    ld a,(date_minute)
    inc a
    ld (date_minute),a
    jr date_min_loop
date_min_done:
    ld hl,(date_work)
    ld a,l
    ld (date_second),a

    ld hl,1970
    ld (date_year),hl
date_year_loop:
    call date_year_length
    ld b,h
    ld c,l
    ld hl,(date_days)
    or a
    sbc hl,bc
    jr c,date_year_done
    ld (date_days),hl
    ld hl,(date_year)
    inc hl
    ld (date_year),hl
    jr date_year_loop
date_year_done:
    ld a,1
    ld (date_month),a
date_month_loop:
    call date_month_length_current
    ld c,a
    ld b,0
    ld hl,(date_days)
    or a
    sbc hl,bc
    jr c,date_month_done
    ld (date_days),hl
    ld a,(date_month)
    inc a
    ld (date_month),a
    jr date_month_loop
date_month_done:
    ld hl,(date_days)
    inc hl
    ld a,l
    ld (date_day),a
    ret

; HL = 365/366 for current date_year.
date_year_length:
    ld hl,(date_year)
    ld a,l
    and 3
    ld hl,365
    ret nz
    inc hl
    ret

; A = month length for date_month/current date_year.
date_month_length_current:
    ld a,(date_month)
    dec a
    ld e,a
    ld d,0
    ld hl,date_month_lengths
    add hl,de
    ld a,(hl)
    ld b,a
    ld a,(date_month)
    cp 2
    jr nz,date_month_len_done
    ld hl,(date_year)
    ld a,l
    and 3
    jr nz,date_month_len_done
    inc b
date_month_len_done:
    ld a,b
    ret

; Convert validated fields into little-endian u32 seconds in date_time.
date_fields_to_seconds:
    ld hl,0
    ld (date_days),hl
    ld hl,1970
    ld (date_iter_year),hl
date_f2s_year_loop:
    ld hl,(date_iter_year)
    ld de,(date_year)
    or a
    sbc hl,de
    jr z,date_f2s_months
    ld hl,(date_iter_year)
    ld a,l
    and 3
    ld de,365
    jr nz,date_f2s_add_year
    inc de
date_f2s_add_year:
    ld hl,(date_days)
    add hl,de
    ld (date_days),hl
    ld hl,(date_iter_year)
    inc hl
    ld (date_iter_year),hl
    jr date_f2s_year_loop

date_f2s_months:
    ld a,1
    ld (date_iter_month),a
date_f2s_month_loop:
    ld a,(date_iter_month)
    ld b,a
    ld a,(date_month)
    cp b
    jr z,date_f2s_add_day
    ld a,b
    ld (date_month_save),a
    ld a,(date_month)
    push af
    ld a,b
    ld (date_month),a
    call date_month_length_current
    ld e,a
    ld d,0
    ld hl,(date_days)
    add hl,de
    ld (date_days),hl
    pop af
    ld (date_month),a
    ld a,(date_iter_month)
    inc a
    ld (date_iter_month),a
    jr date_f2s_month_loop

date_f2s_add_day:
    ld a,(date_day)
    dec a
    ld e,a
    ld d,0
    ld hl,(date_days)
    add hl,de
    ld (date_days),hl

    xor a
    ld (date_time),a
    ld (date_time+1),a
    ld (date_time+2),a
    ld (date_time+3),a
    ld hl,(date_days)
date_f2s_day_seconds:
    ld a,h
    or l
    jr z,date_f2s_hours
    ld de,$5180
    push hl
    ld hl,(date_time)
    add hl,de
    ld (date_time),hl
    ld hl,(date_time+2)
    ld de,1
    adc hl,de
    ld (date_time+2),hl
    pop hl
    dec hl
    jr date_f2s_day_seconds

date_f2s_hours:
    ld a,(date_hour)
    ld b,a
date_f2s_hour_loop:
    ld a,b
    or a
    jr z,date_f2s_minutes
    ld hl,(date_time)
    ld de,3600
    add hl,de
    ld (date_time),hl
    ld hl,(date_time+2)
    ld de,0
    adc hl,de
    ld (date_time+2),hl
    djnz date_f2s_hour_loop

date_f2s_minutes:
    ld a,(date_minute)
    ld b,a
date_f2s_min_loop:
    ld a,b
    or a
    jr z,date_f2s_seconds
    ld hl,(date_time)
    ld de,60
    add hl,de
    ld (date_time),hl
    ld hl,(date_time+2)
    ld de,0
    adc hl,de
    ld (date_time+2),hl
    djnz date_f2s_min_loop
date_f2s_seconds:
    ld a,(date_second)
    ld e,a
    ld d,0
    ld hl,(date_time)
    add hl,de
    ld (date_time),hl
    ld hl,(date_time+2)
    ld de,0
    adc hl,de
    ld (date_time+2),hl
    ret

date_format:
    ld hl,(date_year)
    ld de,date_out
    call date_put4
    ld a,'-'
    ld (date_out+4),a
    ld a,(date_month)
    ld de,date_out+5
    call date_put2
    ld a,'-'
    ld (date_out+7),a
    ld a,(date_day)
    ld de,date_out+8
    call date_put2
    ld a,' '
    ld (date_out+10),a
    ld a,(date_hour)
    ld de,date_out+11
    call date_put2
    ld a,':'
    ld (date_out+13),a
    ld a,(date_minute)
    ld de,date_out+14
    call date_put2
    ld a,':'
    ld (date_out+16),a
    ld a,(date_second)
    ld de,date_out+17
    call date_put2
    ld a,10
    ld (date_out+19),a
    ret

; HL u16 <=9999, DE output 4 chars.
date_put4:
    ld bc,1000
    call date_digit_div
    ld (de),a
    inc de
    ld bc,100
    call date_digit_div
    ld (de),a
    inc de
    ld bc,10
    call date_digit_div
    ld (de),a
    inc de
    ld a,l
    add a,'0'
    ld (de),a
    ret
date_digit_div:
    ld a,'0'
date_digit_div_loop:
    or a
    sbc hl,bc
    jr c,date_digit_div_done
    inc a
    jr date_digit_div_loop
date_digit_div_done:
    add hl,bc
    ret

; A 0..99, DE output 2 chars.
date_put2:
    ld b,'0'
date_put2_loop:
    cp 10
    jr c,date_put2_done
    sub 10
    inc b
    jr date_put2_loop
date_put2_done:
    ld c,a
    ld a,b
    ld (de),a
    inc de
    ld a,c
    add a,'0'
    ld (de),a
    ret

date_write_z:
    push hl
    ld bc,0
date_write_z_count:
    ld a,(hl)
    or a
    jr z,date_write_z_ready
    inc hl
    inc bc
    jr date_write_z_count
date_write_z_ready:
    pop hl
date_write_all:
    ld (date_wptr),hl
    ld (date_wleft),bc
date_write_loop:
    ld hl,(date_wptr)
    ld bc,(date_wleft)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,date_write_zero
    ld (date_wrote),hl
    ld de,(date_wptr)
    add hl,de
    ld (date_wptr),hl
    ld hl,(date_wleft)
    ld de,(date_wrote)
    or a
    sbc hl,de
    jr c,date_write_zero
    ld (date_wleft),hl
    ld a,h
    or l
    jr nz,date_write_loop
    xor a
    ret
date_write_zero:
    ld a,E_IO
    scf
    ret

date_month_lengths: db 31,28,31,30,31,30,31,31,30,31,30,31
date_not_set: db 'd','a','t','e',':',' ','n','o','t',' ','s','e','t',10,0
date_time: defs 6,0
date_work: defs 4,0
date_days: dw 0
date_year: dw 0
date_iter_year: dw 0
date_month: db 0
date_month_save: db 0
date_iter_month: db 0
date_day: db 0
date_hour: db 0
date_minute: db 0
date_second: db 0
date_parse_buf: defs 19,0
date_out: defs 20,0
date_wptr: dw 0
date_wleft: dw 0
date_wrote: dw 0
    ENDM
