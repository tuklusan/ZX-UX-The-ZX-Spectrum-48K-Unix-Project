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
; P7.16 UDG1 RAM persistence. Save stages a complete UDG object in /tmp and
; commits with SYS_RENAME. Load fully reads and validates UDG1 before touching
; the live UDG bank. Neither path invokes a cassette syscall.

    MACRO EMIT_P716_UDG_UTILITY_ROUTINES
udg_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 3
    jr nz,udg_entry_bad
    ld de,8
    add ix,de
udg_entry_skip_argv0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,udg_entry_skip_argv0

    ld a,(ix+0)
    cp 's'
    jr nz,udg_entry_try_load
    ld a,(ix+1)
    cp 'a'
    jr nz,udg_entry_bad
    ld a,(ix+2)
    cp 'v'
    jr nz,udg_entry_bad
    ld a,(ix+3)
    cp 'e'
    jr nz,udg_entry_bad
    ld a,(ix+4)
    or a
    jr nz,udg_entry_bad
    ld de,5
    add ix,de
    ld a,(ix+0)
    or a
    jr z,udg_entry_bad
    push ix
    pop hl
    call udg_save_path
    jr udg_entry_exit

udg_entry_try_load:
    ld a,(ix+0)
    cp 'l'
    jr nz,udg_entry_bad
    ld a,(ix+1)
    cp 'o'
    jr nz,udg_entry_bad
    ld a,(ix+2)
    cp 'a'
    jr nz,udg_entry_bad
    ld a,(ix+3)
    cp 'd'
    jr nz,udg_entry_bad
    ld a,(ix+4)
    or a
    jr nz,udg_entry_bad
    ld de,5
    add ix,de
    ld a,(ix+0)
    or a
    jr z,udg_entry_bad
    push ix
    pop hl
    call udg_load_path
    jr udg_entry_exit

udg_entry_bad:
    ld a,E_INVAL
    scf
udg_entry_exit:
    jr nc,udg_entry_exit_ok
    ld l,a
    jr udg_entry_exit_call
udg_entry_exit_ok:
    ld l,0
udg_entry_exit_call:
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

; HL = exact destination path. Save all 32 live slots as one UDG1 object.
udg_save_path:
    ld (udg_target_ptr),hl
    ld a,SYS_GETPID
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,udg_save_invalid
    ld a,l
    cp 1
    jr c,udg_save_invalid
    cp 8
    jr nc,udg_save_invalid
    add a,'0'
    ld (udg_temp_pid),a
    ld a,'0'
udg_save_open_retry:
    ld (udg_temp_n),a
    ld hl,udg_temp_path
    ld c,O_WRITE|O_CREATE|O_EXCL
    ld b,OBJ_UDG
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jr nc,udg_save_opened
    cp E_EXIST
    ret nz
    ld a,(udg_temp_n)
    cp '9'
    jr z,udg_save_exists
    inc a
    jr udg_save_open_retry

udg_save_exists:
    ld a,E_EXIST
    scf
    ret
udg_save_invalid:
    ld a,E_INVAL
    scf
    ret

udg_save_opened:
    ld a,h
    or a
    jr nz,udg_save_bad_handle
    ld a,l
    ld (udg_handle),a

    ld hl,udg_payload
    ld (hl),'U'
    inc hl
    ld (hl),'D'
    inc hl
    ld (hl),'G'
    inc hl
    ld (hl),'1'
    inc hl
    ld (hl),UDG1_VERSION
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld a,UDG1_MAX_GLYPHS
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (udg_payload_ptr),hl
    xor a
    ld (udg_slot),a

udg_save_get_loop:
    ld a,(udg_slot)
    ld c,a
    ld b,0
    ld hl,(udg_payload_ptr)
    ld a,SYS_UDG_GET
    call SYSCALL_GATEWAY
    jr c,udg_save_cleanup
    ld hl,(udg_payload_ptr)
    ld de,8
    add hl,de
    ld (udg_payload_ptr),hl
    ld a,(udg_slot)
    inc a
    ld (udg_slot),a
    cp UDG1_MAX_GLYPHS
    jr nz,udg_save_get_loop

    ld hl,udg_payload
    ld bc,UDG1_FULL_SIZE
    ld d,0
    ld a,(udg_handle)
    ld e,a
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jr c,udg_save_cleanup
    ld de,UDG1_FULL_SIZE
    or a
    sbc hl,de
    jr z,udg_save_close
    ld a,E_IO
    jr udg_save_cleanup

udg_save_close:
    ld a,(udg_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    jr c,udg_save_cleanup_closed

    ld hl,udg_temp_path
    ld (udg_ren1),hl
    ld hl,(udg_target_ptr)
    ld (udg_ren1+2),hl
    ld hl,udg_ren1
    ld a,SYS_RENAME
    call SYSCALL_GATEWAY
    jr c,udg_save_cleanup_closed
    xor a
    ret

udg_save_bad_handle:
    ld a,E_FORMAT
    scf
    ret

udg_save_cleanup:
    ld (udg_errno),a
    ld a,(udg_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ld a,(udg_errno)
udg_save_cleanup_closed:
    ld (udg_errno),a
    ld hl,udg_temp_path
    ld a,SYS_REMOVE
    call SYSCALL_GATEWAY
    ld a,(udg_errno)
    scf
    ret

; HL = exact RAM UDG-object path. RAW/PACKED are both read logically by SYS_READ.
udg_load_path:
    ld (udg_target_ptr),hl
    ld (udg_stat1),hl
    ld hl,udg_statout
    ld (udg_stat1+2),hl
    ld hl,udg_stat1
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    ret c

    ld a,(udg_statout+0)
    cp OBJ_UDG
    jp nz,udg_load_format
    ld a,(udg_statout+1)
    and $fe
    jp nz,udg_load_format
    ld a,(udg_statout+7)
    cp STATE_RAM
    jp nz,udg_load_format
    ld hl,(udg_statout+2)
    ld (udg_load_len),hl
    ld de,UDG1_HEADER_SIZE+UDG1_GLYPH_BYTES
    or a
    sbc hl,de
    jp c,udg_load_format
    ld hl,(udg_load_len)
    ld de,UDG1_FULL_SIZE
    or a
    sbc hl,de
    jr c,udg_load_len_ok
    jr z,udg_load_len_ok
    jp udg_load_format

udg_load_len_ok:
    ld hl,(udg_target_ptr)
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,udg_load_bad_handle
    ld a,l
    ld (udg_handle),a

    ld hl,udg_payload
    ld bc,(udg_load_len)
    ld d,0
    ld a,(udg_handle)
    ld e,a
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jr c,udg_load_close_error
    ld de,(udg_load_len)
    or a
    sbc hl,de
    jr z,udg_load_close
    ld a,E_FORMAT
    jr udg_load_close_error

udg_load_close:
    ld a,(udg_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret c
    jr udg_load_validate

udg_load_close_error:
    ld (udg_errno),a
    ld a,(udg_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ld a,(udg_errno)
    scf
    ret

udg_load_bad_handle:
    ld a,E_FORMAT
    scf
    ret

; Full UDG1 validation precedes the first SYS_UDG_DEFINE.
udg_load_validate:
    ld a,(udg_payload+0)
    cp 'U'
    jp nz,udg_load_format
    ld a,(udg_payload+1)
    cp 'D'
    jp nz,udg_load_format
    ld a,(udg_payload+2)
    cp 'G'
    jp nz,udg_load_format
    ld a,(udg_payload+3)
    cp '1'
    jp nz,udg_load_format
    ld a,(udg_payload+4)
    cp UDG1_VERSION
    jp nz,udg_load_format
    ld a,(udg_payload+7)
    or a
    jp nz,udg_load_format
    ld a,(udg_payload+5)
    cp UDG1_MAX_GLYPHS
    jp nc,udg_load_format
    ld (udg_slot),a
    ld d,a
    ld a,(udg_payload+6)
    or a
    jp z,udg_load_format
    cp UDG1_MAX_GLYPHS+1
    jp nc,udg_load_format
    ld (udg_count),a
    add a,d
    jp c,udg_load_format
    cp UDG1_MAX_GLYPHS+1
    jp nc,udg_load_format

    ld a,(udg_count)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,UDG1_HEADER_SIZE
    add hl,de
    ld de,(udg_load_len)
    or a
    sbc hl,de
    jp nz,udg_load_format

    ld hl,udg_payload+UDG1_HEADER_SIZE
    ld (udg_payload_ptr),hl
udg_load_apply_loop:
    ld a,(udg_slot)
    ld c,a
    ld b,0
    ld hl,(udg_payload_ptr)
    ld a,SYS_UDG_DEFINE
    call SYSCALL_GATEWAY
    ret c
    ld hl,(udg_payload_ptr)
    ld de,UDG1_GLYPH_BYTES
    add hl,de
    ld (udg_payload_ptr),hl
    ld a,(udg_slot)
    inc a
    ld (udg_slot),a
    ld a,(udg_count)
    dec a
    ld (udg_count),a
    jr nz,udg_load_apply_loop
    xor a
    ret

udg_load_format:
    ld a,E_FORMAT
    scf
    ret

udg_temp_path:
    db '/','t','m','p','/','.','u','d','g'
udg_temp_pid: db '0'
    db '.'
udg_temp_n: db '0',0
udg_target_ptr: dw 0
udg_payload_ptr: dw 0
udg_load_len: dw 0
udg_handle: db 0
udg_slot: db 0
udg_count: db 0
udg_errno: db 0
udg_ren1: defs 4,0
udg_stat1: defs 4,0
udg_statout: defs 10,0
udg_payload:
    defs UDG1_FULL_SIZE,0
    ENDM
