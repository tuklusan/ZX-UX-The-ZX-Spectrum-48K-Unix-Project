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
; P11.24 C48 byte-preserving stdio/string runtime and compact integer formatter.
; Public C48_REGCALL entry points are getchar, putchar, puts, strlen, strcmp,
; strcpy and strncpy. No routine touches IY or the alternate register bank.

    MACRO EMIT_P1124_C48_STRING_RUNTIME
c48_stdio_byte:       db 0
c48_puts_ptr:         dw 0
c48_puts_left:        dw 0
c48_puts_step:        dw 0

c48_fmt_dest:         dw 0
c48_fmt_cap:          dw 0
c48_fmt_value:        dw 0
c48_fmt_out:          dw 0
c48_fmt_sign:         db 0
c48_fmt_digits:       db 0
c48_fmt_count:        db 0
c48_fmt_reverse:      defs 5,0

c48_text_errno:
    ld l,a
    ld h,0
    or a
    ret

; getchar(void): exact byte from process stdin, EOF=-1, syscall error=errno.
; In particular, tty EDIT arrives unchanged as 0x1B and BREAK remains E_INTR.
getchar:
    ld hl,c48_stdio_byte
    ld de,0
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,c48_text_errno
    ld a,h
    or l
    jr z,c48_getchar_eof
    ld a,(c48_stdio_byte)
    ld l,a
    ld h,0
    xor a
    ret
c48_getchar_eof:
    ld hl,0
    dec hl
    xor a
    ret

; putchar(int): write one low byte to process stdout and return that byte.
putchar:
    ld a,l
    ld (c48_stdio_byte),a
    push af
    ld hl,c48_stdio_byte
    ld de,1
    ld bc,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jr c,c48_putchar_error
    pop af
    ld l,a
    ld h,0
    xor a
    ret
c48_putchar_error:
    pop bc
    jp c48_text_errno

; puts(char *): write the complete string and one newline to process stdout.
; Short writes are completed; zero-progress writes fail with E_IO.
puts:
    ld (c48_puts_ptr),hl
    call strlen
    ld (c48_puts_left),hl
c48_puts_loop:
    ld bc,(c48_puts_left)
    ld a,b
    or c
    jr z,c48_puts_newline
    ld hl,(c48_puts_ptr)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jp c,c48_text_errno
    ld a,h
    or l
    jr z,c48_puts_io
    ld (c48_puts_step),hl

    ld de,(c48_puts_left)
    or a
    sbc hl,de
    ld hl,(c48_puts_step)
    jr c,c48_puts_advance
    jr z,c48_puts_advance
    ld a,E_FORMAT
    jp c48_text_errno
c48_puts_advance:
    ld de,(c48_puts_ptr)
    add hl,de
    ld (c48_puts_ptr),hl
    ld hl,(c48_puts_left)
    ld de,(c48_puts_step)
    or a
    sbc hl,de
    ld (c48_puts_left),hl
    jr c48_puts_loop

c48_puts_newline:
    ld a,10
    ld (c48_stdio_byte),a
    ld hl,c48_stdio_byte
    ld de,1
    ld bc,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jp c,c48_text_errno
    ld a,h
    or l
    jr z,c48_puts_io
    ld hl,0
    xor a
    ret
c48_puts_io:
    ld a,E_IO
    jp c48_text_errno

; strlen(char *): unsigned byte count excluding NUL.
strlen:
    ld de,0
c48_strlen_loop:
    ld a,(hl)
    or a
    jr z,c48_strlen_done
    inc hl
    inc de
    jr c48_strlen_loop
c48_strlen_done:
    ex de,hl
    xor a
    ret

; strcmp(char *,char *): return -1, 0 or +1 using unsigned target bytes.
strcmp:
c48_strcmp_loop:
    ld a,(hl)
    ld c,a
    ld a,(de)
    ld b,a
    ld a,c
    cp b
    jr c,c48_strcmp_less
    jr nz,c48_strcmp_greater
    or a
    jr z,c48_strcmp_equal
    inc hl
    inc de
    jr c48_strcmp_loop
c48_strcmp_less:
    ld hl,0
    dec hl
    xor a
    ret
c48_strcmp_greater:
    ld hl,1
    xor a
    ret
c48_strcmp_equal:
    ld hl,0
    xor a
    ret

; strcpy(dest,src): copy through NUL and return dest.
strcpy:
    push hl
c48_strcpy_loop:
    ld a,(de)
    ld (hl),a
    inc de
    inc hl
    or a
    jr nz,c48_strcpy_loop
    pop hl
    xor a
    ret

; strncpy(dest,src,n): copy at most n bytes and zero-pad after source NUL.
strncpy:
    push hl
    ld a,b
    or c
    jr z,c48_strncpy_done
c48_strncpy_copy:
    ld a,(de)
    ld (hl),a
    inc hl
    inc de
    dec bc
    or a
    jr z,c48_strncpy_pad_check
    ld a,b
    or c
    jr nz,c48_strncpy_copy
    jr c48_strncpy_done
c48_strncpy_pad_check:
    ld a,b
    or c
    jr z,c48_strncpy_done
    xor a
c48_strncpy_pad:
    ld (hl),a
    inc hl
    dec bc
    ld a,b
    or c
    jr nz,c48_strncpy_pad
c48_strncpy_done:
    pop hl
    xor a
    ret

; Compact signed integer formatter retained from the REV16 runtime requirement.
; HL=signed value, DE=destination, BC=capacity including NUL.
; Success HL=bytes excluding NUL. Insufficient capacity returns E_NOSPC and
; leaves the destination untouched. Uses the admitted P11.08 integer runtime.
c48_format_int:
    ld (c48_fmt_dest),de
    ld (c48_fmt_cap),bc
    xor a
    ld (c48_fmt_sign),a
    bit 7,h
    jr z,c48_fmt_magnitude
    ld a,1
    ld (c48_fmt_sign),a
    call c48_s16_neg
c48_fmt_magnitude:
    ld (c48_fmt_value),hl
    xor a
    ld (c48_fmt_digits),a

c48_fmt_digit_loop:
    ld hl,(c48_fmt_value)
    ld de,10
    call c48_u16_divmod
    ret c
    ld (c48_fmt_value),hl
    ld a,e
    add a,'0'
    ld c,a
    ld a,(c48_fmt_digits)
    ld e,a
    ld d,0
    ld hl,c48_fmt_reverse
    add hl,de
    ld (hl),c
    inc a
    ld (c48_fmt_digits),a
    ld hl,(c48_fmt_value)
    ld a,h
    or l
    jr nz,c48_fmt_digit_loop

    ld a,(c48_fmt_digits)
    ld e,a
    ld a,(c48_fmt_sign)
    add a,e
    ld (c48_fmt_count),a
    inc a
    ld e,a
    ld d,0
    ld hl,(c48_fmt_cap)
    or a
    sbc hl,de
    jr c,c48_fmt_nospc

    ld hl,(c48_fmt_dest)
    ld a,(c48_fmt_sign)
    or a
    jr z,c48_fmt_copy_digits
    ld (hl),'-'
    inc hl
c48_fmt_copy_digits:
    ld (c48_fmt_out),hl
    ld a,(c48_fmt_digits)
    dec a
    ld e,a
    ld d,0
    ld hl,c48_fmt_reverse
    add hl,de
    ex de,hl
    ld hl,(c48_fmt_out)
    ld a,(c48_fmt_digits)
    ld b,a
c48_fmt_copy_loop:
    ld a,(de)
    ld (hl),a
    inc hl
    dec de
    djnz c48_fmt_copy_loop
    xor a
    ld (hl),a
    ld a,(c48_fmt_count)
    ld l,a
    ld h,0
    xor a
    ret
c48_fmt_nospc:
    ld hl,E_NOSPC
    xor a
    ret
    ENDM
