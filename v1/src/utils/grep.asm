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
; /bin/grep: case-sensitive literal substring match over stdin or one named object.
; Matching output preserves the exact input bytes and original LF presence.

    MACRO EMIT_P808_GREP_ROUTINES
grep_entry:
    push hl
    pop ix
    xor a
    ld (grep_opened),a
    ld (grep_any),a
    ld (grep_line_len),a
    ld a,(ix+4)
    cp 2
    jr z,grep_stdin_args
    cp 3
    jp nz,grep_invalid

    ld de,8
    add ix,de
    call grep_next_arg
    push ix
    pop hl
    ld (grep_pattern),hl
    call grep_pattern_len
    jp c,grep_invalid
    call grep_next_arg
    push ix
    pop hl
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,grep_exit_error
    ld a,l
    ld (grep_handle),a
    ld a,1
    ld (grep_opened),a
    jr grep_read_loop

grep_stdin_args:
    ld de,8
    add ix,de
    call grep_next_arg
    push ix
    pop hl
    ld (grep_pattern),hl
    call grep_pattern_len
    jp c,grep_invalid
    xor a
    ld (grep_handle),a

grep_read_loop:
    ld a,(grep_handle)
    ld e,a
    ld d,0
    ld hl,grep_byte
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,grep_stream_error
    ld a,h
    or l
    jr z,grep_eof
    ld a,(grep_byte)
    cp 10
    jr z,grep_finish_line
    ld a,(grep_line_len)
    cp 255
    jr z,grep_line_overflow
    ld e,a
    ld d,0
    ld hl,grep_line
    add hl,de
    ld a,(grep_byte)
    ld (hl),a
    ld a,(grep_line_len)
    inc a
    ld (grep_line_len),a
    jr grep_read_loop

grep_finish_line:
    ld a,1
    ld (grep_had_lf),a
    call grep_process_line
    jp c,grep_stream_error
    xor a
    ld (grep_line_len),a
    jr grep_read_loop

grep_eof:
    ld a,(grep_line_len)
    or a
    jr z,grep_finish
    xor a
    ld (grep_had_lf),a
    call grep_process_line
    jp c,grep_stream_error

grep_finish:
    call grep_close
    jp c,grep_exit_error
    ld a,(grep_any)
    or a
    jr nz,grep_success
    ld a,1
    jp grep_exit_error
grep_success:
    ld l,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

grep_line_overflow:
    ld a,E_NOSPC
grep_stream_error:
    ld (grep_error),a
    call grep_close_best
    ld a,(grep_error)
grep_exit_error:
    ld l,a
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
grep_invalid:
    ld a,E_INVAL
    jp grep_exit_error

grep_pattern_len:
    ld de,(grep_pattern)
    ld b,0
grep_pat_len_loop:
    ld a,(de)
    or a
    jr z,grep_pat_len_done
    inc b
    inc de
    jr nz,grep_pat_len_loop
grep_pat_len_done:
    ld a,b
    or a
    jr z,grep_pat_len_bad
    ld (grep_pat_len),a
    or a
    ret
grep_pat_len_bad:
    scf
    ret

grep_process_line:
    ; Empty lines cannot contain the required nonempty pattern.
    ld a,(grep_line_len)
    ld c,a
    ld a,(grep_pat_len)
    cp c
    jr z,grep_try_at_zero
    jr nc,grep_process_nomatch
grep_try_at_zero:
    ld a,(grep_line_len)
    ld c,a
    ld a,(grep_pat_len)
    ld b,a
    ld a,c
    sub b
    ld (grep_last_start),a
    xor a
    ld (grep_start),a

grep_match_outer:
    ld a,(grep_start)
    ld e,a
    ld d,0
    ld hl,grep_line
    add hl,de
    ex de,hl
    ld hl,(grep_pattern)
    ld a,(grep_pat_len)
    ld b,a
grep_match_inner:
    ld a,(de)
    cp (hl)
    jr nz,grep_match_next
    inc de
    inc hl
    djnz grep_match_inner
    jr grep_process_match
grep_match_next:
    ld a,(grep_start)
    ld c,a
    ld a,(grep_last_start)
    cp c
    jr z,grep_process_nomatch
    ld a,c
    inc a
    ld (grep_start),a
    jr grep_match_outer

grep_process_match:
    ld a,1
    ld (grep_any),a
    ld a,(grep_line_len)
    or a
    jr z,grep_match_lf
    ld c,a
    ld b,0
    ld hl,grep_line
    call grep_write_all
    ret c
grep_match_lf:
    ld a,(grep_had_lf)
    or a
    jr z,grep_process_ok
    ld hl,grep_lf
    ld bc,1
    call grep_write_all
    ret c
grep_process_ok:
    or a
    ret
grep_process_nomatch:
    or a
    ret

grep_write_all:
    ld (grep_write_ptr),hl
    ld (grep_write_left),bc
grep_write_loop:
    ld hl,(grep_write_ptr)
    ld bc,(grep_write_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,grep_write_zero
    ld (grep_written),hl
    ld de,(grep_write_ptr)
    add hl,de
    ld (grep_write_ptr),hl
    ld hl,(grep_write_left)
    ld de,(grep_written)
    or a
    sbc hl,de
    jr c,grep_write_zero
    ld (grep_write_left),hl
    ld a,h
    or l
    jr nz,grep_write_loop
    xor a
    ret
grep_write_zero:
    ld a,E_IO
    scf
    ret

grep_close:
    ld a,(grep_opened)
    or a
    ret z
    xor a
    ld (grep_opened),a
    ld a,(grep_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret
grep_close_best:
    ld a,(grep_opened)
    or a
    ret z
    xor a
    ld (grep_opened),a
    ld a,(grep_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    or a
    ret

grep_next_arg:
grep_next_loop:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,grep_next_loop
    ret

grep_pattern: dw 0
grep_handle: db 0
grep_opened: db 0
grep_any: db 0
grep_line_len: db 0
grep_pat_len: db 0
grep_had_lf: db 0
grep_last_start: db 0
grep_start: db 0
grep_error: db 0
grep_byte: db 0
grep_write_ptr: dw 0
grep_write_left: dw 0
grep_written: dw 0
grep_lf: db 10
grep_line: defs 255,0
grep_end:
    ENDM
