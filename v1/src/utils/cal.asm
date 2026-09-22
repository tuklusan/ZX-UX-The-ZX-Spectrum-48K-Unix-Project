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

    MACRO EMIT_P828_CAL_ROUTINES
cal_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr z,cal_current
    cp 2
    jr z,cal_one
    cp 3
    jp nz,cal_bad
    ld de,8
    add ix,de
cal_skip0_three:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,cal_skip0_three
    push ix
    pop hl
    call cal_parse_month
    jp c,cal_bad
    ld (cal_month),a
    call cal_advance
    call cal_parse_year
    jp c,cal_bad
    ld (cal_year),de
    jp cal_render

cal_one:
    ld de,8
    add ix,de
cal_skip0_one:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,cal_skip0_one
    push ix
    pop hl
    call cal_parse_month
    jp c,cal_bad
    ld (cal_month),a
    call cal_get_current_year
    jp c,cal_time_error
    jp cal_render

cal_current:
    call cal_get_current_month_year
    jp c,cal_time_error
    jp cal_render

cal_time_error:
    cp E_AGAIN
    jr nz,cal_exit_a
    ld hl,cal_not_set
    call cal_write_z
    jr c,cal_exit_a
    ld a,E_AGAIN
    jr cal_exit_a

cal_bad:
    ld a,E_INVAL
cal_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

cal_get_current_year:
    ld hl,cal_time
    ld a,SYS_TIME_GET
    call SYSCALL_GATEWAY
    ret c
    call cal_decode_date
    xor a
    ret

cal_get_current_month_year:
    call cal_get_current_year
    ret

cal_parse_month:
    call cal_parse_u16
    ret c
    ld a,d
    or a
    jr nz,cal_parse_bad
    ld a,e
    or a
    jr z,cal_parse_bad
    cp 13
    jr nc,cal_parse_bad
    or a
    ret
cal_parse_year:
    call cal_parse_u16
    ret c
    push hl
    ex de,hl
    ld de,1970
    or a
    sbc hl,de
    pop hl
    jr c,cal_parse_bad
    push hl
    ex de,hl
    ld bc,2100
    or a
    sbc hl,bc
    ex de,hl
    pop hl
    jr nc,cal_parse_bad
    or a
    ret
cal_parse_bad:
    ld a,E_INVAL
    scf
    ret

; HL=NUL decimal, DE=value, exact digits only.
cal_parse_u16:
    ld de,0
    ld b,0
cal_parse_loop:
    ld a,(hl)
    or a
    jr z,cal_parse_done
    cp '0'
    jr c,cal_parse_bad
    cp '9'+1
    jr nc,cal_parse_bad
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
    inc b
    jr cal_parse_loop
cal_parse_done:
    ld a,b
    or a
    jr z,cal_parse_bad
    or a
    ret

cal_advance:
    ld a,(hl)
    inc hl
    or a
    jr nz,cal_advance
    ret

; Decode TIME1 u32 seconds to cal_year/cal_month.
cal_decode_date:
    ld hl,(cal_time)
    ld (cal_work),hl
    ld hl,(cal_time+2)
    ld (cal_work+2),hl
    ld hl,0
    ld (cal_days),hl
cal_decode_day_loop:
    ld hl,(cal_work+2)
    ld a,h
    or a
    jr nz,cal_decode_day_sub
    ld a,l
    cp 1
    jr c,cal_decode_day_done
    jr nz,cal_decode_day_sub
    ld hl,(cal_work)
    ld de,$5180
    or a
    sbc hl,de
    jr c,cal_decode_day_done
cal_decode_day_sub:
    ld hl,(cal_work)
    ld de,$5180
    or a
    sbc hl,de
    ld (cal_work),hl
    ld hl,(cal_work+2)
    ld de,1
    sbc hl,de
    ld (cal_work+2),hl
    ld hl,(cal_days)
    inc hl
    ld (cal_days),hl
    jr cal_decode_day_loop
cal_decode_day_done:
    ld hl,1970
    ld (cal_year),hl
cal_decode_year_loop:
    ld hl,(cal_year)
    ld a,l
    and 3
    ld de,365
    jr nz,cal_decode_year_len
    inc de
cal_decode_year_len:
    ld hl,(cal_days)
    or a
    sbc hl,de
    jr c,cal_decode_year_done
    ld (cal_days),hl
    ld hl,(cal_year)
    inc hl
    ld (cal_year),hl
    jr cal_decode_year_loop
cal_decode_year_done:
    ld a,1
    ld (cal_month),a
cal_decode_month_loop:
    call cal_month_len
    ld e,a
    ld d,0
    ld hl,(cal_days)
    or a
    sbc hl,de
    jr c,cal_decode_month_done
    ld (cal_days),hl
    ld a,(cal_month)
    inc a
    ld (cal_month),a
    jr cal_decode_month_loop
cal_decode_month_done:
    ret

cal_month_len:
    ld a,(cal_month)
    dec a
    ld e,a
    ld d,0
    ld hl,cal_month_lengths
    add hl,de
    ld b,(hl)
    ld a,(cal_month)
    cp 2
    jr nz,cal_month_len_done
    ld hl,(cal_year)
    ld a,l
    and 3
    jr nz,cal_month_len_done
    inc b
cal_month_len_done:
    ld a,b
    ret

; weekday of first day. 1970-01-01 = Thursday = 4, Sunday=0.
cal_first_weekday:
    ld hl,0
    ld (cal_total_days),hl
    ld hl,1970
    ld (cal_iter_year),hl
cal_fw_year:
    ld hl,(cal_iter_year)
    ld de,(cal_year)
    or a
    sbc hl,de
    jr z,cal_fw_months
    ld hl,(cal_iter_year)
    ld a,l
    and 3
    ld de,365
    jr nz,cal_fw_add_year
    inc de
cal_fw_add_year:
    ld hl,(cal_total_days)
    add hl,de
    ld (cal_total_days),hl
    ld hl,(cal_iter_year)
    inc hl
    ld (cal_iter_year),hl
    jr cal_fw_year
cal_fw_months:
    ld a,1
    ld (cal_iter_month),a
cal_fw_month:
    ld a,(cal_iter_month)
    ld b,a
    ld a,(cal_month)
    cp b
    jr z,cal_fw_reduce
    ld a,(cal_month)
    push af
    ld a,b
    ld (cal_month),a
    call cal_month_len
    ld e,a
    ld d,0
    ld hl,(cal_total_days)
    add hl,de
    ld (cal_total_days),hl
    pop af
    ld (cal_month),a
    ld a,(cal_iter_month)
    inc a
    ld (cal_iter_month),a
    jr cal_fw_month
cal_fw_reduce:
    ld hl,(cal_total_days)
    ld a,l
    add a,4
cal_fw_mod:
    cp 7
    jr c,cal_fw_done
    sub 7
    jr cal_fw_mod
cal_fw_done:
    ret

; Output:
; YYYY-MM LF
; Su Mo Tu We Th Fr Sa LF
; then rows with two-digit days or "--".
cal_render:
    ld hl,cal_out
    ld (cal_outptr),hl
    ld hl,(cal_year)
    call cal_emit4
    ld a,'-'
    call cal_emit
    ld a,(cal_month)
    call cal_emit2
    ld a,10
    call cal_emit
    ld hl,cal_week_header
    call cal_emit_z
    call cal_first_weekday
    ld (cal_weekday),a
    ld a,1
    ld (cal_day),a
    call cal_month_len
    ld (cal_days_in_month),a
    xor a
    ld (cal_cell),a
cal_render_cell:
    ld a,(cal_cell)
    cp 42
    jr z,cal_render_done
    ld b,a
    ld a,(cal_weekday)
    cp b
    jr nz,cal_render_maybe_day
    ld a,(cal_day)
    or a
cal_render_maybe_day:
    ld a,(cal_cell)
    ld b,a
    ld a,(cal_weekday)
    cp b
    jr c,cal_render_day
    jr z,cal_render_day
    ld a,'-'
    call cal_emit
    ld a,'-'
    call cal_emit
    jr cal_render_sep
cal_render_day:
    ld a,(cal_day)
    ld b,a
    ld a,(cal_days_in_month)
    cp b
    jr c,cal_render_blank
    ld a,b
    call cal_emit2
    inc a
    ld a,(cal_day)
    inc a
    ld (cal_day),a
    jr cal_render_sep
cal_render_blank:
    ld a,'-'
    call cal_emit
    ld a,'-'
    call cal_emit
cal_render_sep:
    ld a,(cal_cell)
    inc a
    ld (cal_cell),a
    ld b,a
    ld a,b
cal_render_mod7:
    cp 7
    jr c,cal_render_moddone
    sub 7
    jr cal_render_mod7
cal_render_moddone:
    or a
    jr z,cal_render_lf
    ld a,' '
    call cal_emit
    jr cal_render_cell
cal_render_lf:
    ld a,10
    call cal_emit
    ld a,(cal_cell)
    cp 42
    jr nz,cal_render_cell
cal_render_done:
    ld hl,cal_out
    ld de,(cal_outptr)
    ex de,hl
    or a
    sbc hl,de
    ld b,h
    ld c,l
    ld hl,cal_out
    call cal_write_all
    jr c,cal_exit_a
    xor a
    jr cal_exit_a

cal_emit:
    push hl
    ld hl,(cal_outptr)
    ld (hl),a
    inc hl
    ld (cal_outptr),hl
    pop hl
    ret
cal_emit2:
    ld b,'0'
cal_emit2_loop:
    cp 10
    jr c,cal_emit2_done
    sub 10
    inc b
    jr cal_emit2_loop
cal_emit2_done:
    ld c,a
    ld a,b
    call cal_emit
    ld a,c
    add a,'0'
    jp cal_emit
cal_emit4:
    ld de,1000
    call cal_emit_place
    ld de,100
    call cal_emit_place
    ld de,10
    call cal_emit_place
    ld a,l
    add a,'0'
    jp cal_emit
cal_emit_place:
    ld b,'0'
cal_emit_place_loop:
    or a
    sbc hl,de
    jr c,cal_emit_place_done
    inc b
    jr cal_emit_place_loop
cal_emit_place_done:
    add hl,de
    ld a,b
    jp cal_emit
cal_emit_z:
    ld a,(hl)
    or a
    ret z
    call cal_emit
    inc hl
    jr cal_emit_z

cal_write_z:
    push hl
    ld bc,0
cal_wz_count:
    ld a,(hl)
    or a
    jr z,cal_wz_ready
    inc hl
    inc bc
    jr cal_wz_count
cal_wz_ready:
    pop hl
cal_write_all:
    ld (cal_wptr),hl
    ld (cal_wleft),bc
cal_write_loop:
    ld hl,(cal_wptr)
    ld bc,(cal_wleft)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,cal_write_io
    ld (cal_wrote),hl
    ld de,(cal_wptr)
    add hl,de
    ld (cal_wptr),hl
    ld hl,(cal_wleft)
    ld de,(cal_wrote)
    or a
    sbc hl,de
    jr c,cal_write_io
    ld (cal_wleft),hl
    ld a,h
    or l
    jr nz,cal_write_loop
    xor a
    ret
cal_write_io:
    ld a,E_IO
    scf
    ret

cal_month_lengths: db 31,28,31,30,31,30,31,31,30,31,30,31
cal_week_header: db 'S','u',' ','M','o',' ','T','u',' ','W','e',' ','T','h',' ','F','r',' ','S','a',10,0
cal_not_set: db 'c','a','l',':',' ','d','a','t','e',' ','n','o','t',' ','s','e','t',10,0
cal_time: defs 6,0
cal_work: defs 4,0
cal_days: dw 0
cal_year: dw 0
cal_month: db 0
cal_iter_year: dw 0
cal_iter_month: db 0
cal_total_days: dw 0
cal_weekday: db 0
cal_day: db 0
cal_days_in_month: db 0
cal_cell: db 0
cal_out: defs 192,0
cal_outptr: dw 0
cal_wptr: dw 0
cal_wleft: dw 0
cal_wrote: dw 0
    ENDM
