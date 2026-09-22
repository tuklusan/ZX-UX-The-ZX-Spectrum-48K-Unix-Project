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

; P8.29 exact qualification source.
    MACRO EMIT_P829_UPTIME_ROUTINES
uptime_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr nz,uptime_bad
    ld hl,uptime_ticks
    ld a,SYS_TICKS
    call SYSCALL_GATEWAY
    jr c,uptime_exit_a
    call uptime_format_u32
    ld hl,uptime_out
    ld bc,(uptime_len)
    call uptime_write_all
    jr c,uptime_exit_a
    xor a
    jr uptime_exit_a
uptime_bad:
    ld a,E_INVAL
uptime_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

; Format exact unsigned 32-bit tick value modulo 2^32 in decimal plus LF.
uptime_format_u32:
    ld hl,uptime_digits+10
    ld a,10
    ld (hl),a
    ld b,10
uptime_digit_loop:
    dec hl
    push hl
    call uptime_div10
    pop hl
    add a,'0'
    ld (hl),a
    djnz uptime_digit_loop
    ld hl,uptime_digits
uptime_trim:
    ld a,(hl)
    cp '0'
    jr nz,uptime_trim_done
    inc hl
    ld de,uptime_digits+9
    push hl
    or a
    sbc hl,de
    pop hl
    jr c,uptime_trim
uptime_trim_done:
    ld de,uptime_out
    ld bc,0
uptime_copy:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    inc bc
    cp 10
    jr nz,uptime_copy
    ld (uptime_len),bc
    ret

; Divide uptime_ticks by 10 in place. A=remainder.
uptime_div10:
    ld hl,uptime_ticks+3
    ld b,4
    xor a
uptime_div10_byte:
    ld c,(hl)
    ld e,8
    ld d,0
uptime_div10_bit:
    sla c
    rla
    cp 10
    jr c,uptime_div10_no_sub
    sub 10
    scf
    jr uptime_div10_store_bit
uptime_div10_no_sub:
    or a
uptime_div10_store_bit:
    rl d
    dec e
    jr nz,uptime_div10_bit
    ld (hl),d
    dec hl
    djnz uptime_div10_byte
    ret

uptime_write_all:
    ld (uptime_wptr),hl
    ld (uptime_wleft),bc
uptime_write_loop:
    ld hl,(uptime_wptr)
    ld bc,(uptime_wleft)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,uptime_io
    ld (uptime_wrote),hl
    ld de,(uptime_wptr)
    add hl,de
    ld (uptime_wptr),hl
    ld hl,(uptime_wleft)
    ld de,(uptime_wrote)
    or a
    sbc hl,de
    jr c,uptime_io
    ld (uptime_wleft),hl
    ld a,h
    or l
    jr nz,uptime_write_loop
    xor a
    ret
uptime_io:
    ld a,E_IO
    scf
    ret

uptime_ticks: defs 4,0
uptime_digits: defs 11,0
uptime_out: defs 11,0
uptime_len: dw 0
uptime_wptr: dw 0
uptime_wleft: dw 0
uptime_wrote: dw 0
    ENDM
