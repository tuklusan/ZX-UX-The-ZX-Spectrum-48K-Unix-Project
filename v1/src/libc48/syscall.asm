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
; P11.22 C48 process/environment runtime API.
; All kernel calls use symbolic syscall numbers from zx48ux.inc.

    MACRO EMIT_P1122_C48_SYSCALL_RUNTIME
c48_env1_ptr:       dw 0
c48_env1_len:       dw 0
c48_getenv_query:   dw 0
c48_getenv_scan:    dw 0
c48_getenv_count:   db 0
c48_sleep_ticks:    defs 4,0

; Entry bootstrap helper. crt0 supplies the validated process ENV1 DE/BC pair.
c48_runtime_capture_env1:
    ld (c48_env1_ptr),de
    ld (c48_env1_len),bc
    xor a
    ret

c48_sys_errno:
    ld l,a
    ld h,0
    or a
    ret

c48_sys_zero:
    ld hl,0
    xor a
    ret

exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    jr c,c48_sys_errno
    ; Success is non-returning. A returning gateway is a controlled failure.
    ld hl,E_FORMAT
    ret

yield:
    ld a,SYS_YIELD
    call SYSCALL_GATEWAY
    jr c,c48_sys_errno
    jr c48_sys_zero

; C48 sleep(unsigned ticks) widens the 16-bit API value to the kernel u32 frame record.
sleep:
    ld (c48_sleep_ticks),hl
    xor a
    ld (c48_sleep_ticks+2),a
    ld (c48_sleep_ticks+3),a
    ld hl,c48_sleep_ticks
    ld a,SYS_SLEEP
    call SYSCALL_GATEWAY
    jr c,c48_sys_errno
    jr c48_sys_zero

getpid:
    ld a,SYS_GETPID
    call SYSCALL_GATEWAY
    jr c,c48_sys_errno
    or a
    ret

; spawn(HL=PROC1 pointer) -> child PID or errno.
spawn:
    ld a,SYS_SPAWN
    call SYSCALL_GATEWAY
    jr c,c48_sys_errno
    or a
    ret

; wait(HL=WAIT1 pointer) -> zero or errno; status is written through WAIT1.
wait:
    ld a,SYS_WAIT
    call SYSCALL_GATEWAY
    jr c,c48_sys_errno
    jr c48_sys_zero

; kill(HL=PID) -> zero or errno.
kill:
    ld a,SYS_KILL
    call SYSCALL_GATEWAY
    jr c,c48_sys_errno
    jr c48_sys_zero

; chdir(HL=NUL path) -> zero or errno.
chdir:
    ld a,SYS_CHDIR
    call SYSCALL_GATEWAY
    jr c,c48_sys_errno
    jr c48_sys_zero

; getcwd(HL=destination, DE=capacity) -> bytes excluding NUL or errno.
getcwd:
    ld b,d
    ld c,e
    ld a,SYS_GETCWD
    call SYSCALL_GATEWAY
    jr c,c48_sys_errno
    or a
    ret

; getenv(HL=NUL name) -> pointer to immutable ENV1 value bytes, or NULL.
; ENV1 itself was fully validated by the loader before process READY state.
getenv:
    ld (c48_getenv_query),hl
    ld hl,(c48_env1_ptr)
    ld a,h
    or l
    jr z,c48_getenv_null
    ld de,(c48_env1_len)
    ld a,d
    or a
    jr nz,c48_getenv_len_ok
    ld a,e
    cp 8
    jr c,c48_getenv_null
c48_getenv_len_ok:
    ld a,(hl)
    cp 'E'
    jr nz,c48_getenv_null
    inc hl
    ld a,(hl)
    cp 'N'
    jr nz,c48_getenv_null
    inc hl
    ld a,(hl)
    cp 'V'
    jr nz,c48_getenv_null
    inc hl
    ld a,(hl)
    cp '1'
    jr nz,c48_getenv_null
    inc hl
    ld a,(hl)
    cp 9
    jr nc,c48_getenv_null
    ld (c48_getenv_count),a
    inc hl
    ld a,(hl)
    or a
    jr nz,c48_getenv_null
    inc hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    push hl
    ld hl,(c48_env1_len)
    or a
    sbc hl,de
    pop hl
    jr nz,c48_getenv_null
    ld (c48_getenv_scan),hl

c48_getenv_entry:
    ld a,(c48_getenv_count)
    or a
    jr z,c48_getenv_null
    ld hl,(c48_getenv_scan)
    ld de,(c48_getenv_query)
    ld b,80
c48_getenv_compare:
    ld a,(hl)
    or a
    jr z,c48_getenv_next
    cp '='
    jr z,c48_getenv_equal
    ld c,a
    ld a,(de)
    cp c
    jr nz,c48_getenv_skip
    inc hl
    inc de
    djnz c48_getenv_compare
    jr c48_getenv_null

c48_getenv_equal:
    ld a,(de)
    or a
    jr nz,c48_getenv_skip
    inc hl
    xor a
    ret

c48_getenv_skip:
    ld b,80
c48_getenv_skip_loop:
    ld a,(hl)
    or a
    jr z,c48_getenv_advance
    inc hl
    djnz c48_getenv_skip_loop
    jr c48_getenv_null

c48_getenv_next:
c48_getenv_advance:
    inc hl
    ld (c48_getenv_scan),hl
    ld a,(c48_getenv_count)
    dec a
    ld (c48_getenv_count),a
    jr c48_getenv_entry

c48_getenv_null:
    ld hl,0
    xor a
    ret
    ENDM
