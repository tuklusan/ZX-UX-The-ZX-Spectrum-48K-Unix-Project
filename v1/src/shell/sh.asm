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
; P6.01 shell image entry. The MEX1 container is emitted by deterministic host
; tooling; this image has no relocations and uses only the fixed syscall gateway.

    MACRO EMIT_P601_SH_IMAGE
sh_entry:
    ; The loader entry contract is HL=ARG1, BC=ARG1 length, DE=ENV1, A=0.
    ; P6.01 deliberately performs no login/output work; later Phase-6 steps
    ; extend this entry after the already-established cold-boot contract.
sh_idle:
    ld a,SYS_YIELD
    call SYSCALL_GATEWAY
    jr sh_idle
sh_image_end:
    ENDM

; P6.02 exact issue/login presentation. HL/BC supply the canonical /etc/issue
; bytes and IX points at the exact seven-byte login prompt.
P602_ISSUE_LENGTH        EQU 144
P602_LOGIN_LENGTH        EQU 7

    MACRO EMIT_P602_ISSUE_ROUTINES
sh_p602_display_issue:
    ld a,b
    or a
    jr nz,sh_p602_issue_format
    ld a,c
    cp P602_ISSUE_LENGTH
    jr nz,sh_p602_issue_format
    ld a,SYS_CON_WRITE
    call SYSCALL_GATEWAY
    ret c
    push ix
    pop hl
    ld bc,P602_LOGIN_LENGTH
    ld a,SYS_CON_WRITE
    jp SYSCALL_GATEWAY
sh_p602_issue_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM

; P6.03 exact session username validator and invalid-input reprompt.
    MACRO EMIT_P603_LOGIN_ROUTINES
; HL=input bytes, BC=length. Accept exactly [a-z][a-z0-9_-]{0,7}.
sh_p603_validate_username:
    ld a,b
    or a
    jr nz,sh_p603_invalid
    ld a,c
    or a
    jr z,sh_p603_invalid
    cp 9
    jr nc,sh_p603_invalid
    ld a,(hl)
    cp 'a'
    jr c,sh_p603_invalid
    cp 'z'+1
    jr nc,sh_p603_invalid
    inc hl
    dec c
sh_p603_tail:
    ld a,c
    or a
    jr z,sh_p603_valid
    ld a,(hl)
    cp 'a'
    jr c,sh_p603_tail_digit
    cp 'z'+1
    jr c,sh_p603_tail_next
sh_p603_tail_digit:
    cp '0'
    jr c,sh_p603_tail_punct
    cp '9'+1
    jr c,sh_p603_tail_next
sh_p603_tail_punct:
    cp '_'
    jr z,sh_p603_tail_next
    cp '-'
    jr nz,sh_p603_invalid
sh_p603_tail_next:
    inc hl
    dec c
    jr sh_p603_tail
sh_p603_valid:
    xor a
    ret
sh_p603_invalid:
    ld a,E_INVAL
    scf
    ret

; IX points at exact "login: " prompt. Invalid usernames are visibly reprompted.
sh_p603_validate_or_reprompt:
    call sh_p603_validate_username
    ret nc
    push ix
    pop hl
    ld bc,P602_LOGIN_LENGTH
    ld a,SYS_CON_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,E_INVAL
    scf
    ret
    ENDM

; P6.04 fixed session-home construction and cwd initialization.
    MACRO EMIT_P604_HOME_ROUTINES
; HL=username, BC=length, DE=writable >=15-byte path buffer.
; Revalidate username, construct only /home/<user>, and chdir there.
sh_p604_session_home:
    ld a,b
    or a
    jr nz,sh_p604_invalid
    ld a,c
    or a
    jr z,sh_p604_invalid
    cp 9
    jr nc,sh_p604_invalid
    push hl
    push bc
    ld a,(hl)
    cp 'a'
    jr c,sh_p604_invalid_restore
    cp 'z'+1
    jr nc,sh_p604_invalid_restore
    inc hl
    dec c
sh_p604_validate_tail:
    ld a,c
    or a
    jr z,sh_p604_build
    ld a,(hl)
    cp 'a'
    jr c,sh_p604_validate_digit
    cp 'z'+1
    jr c,sh_p604_validate_next
sh_p604_validate_digit:
    cp '0'
    jr c,sh_p604_validate_punct
    cp '9'+1
    jr c,sh_p604_validate_next
sh_p604_validate_punct:
    cp '_'
    jr z,sh_p604_validate_next
    cp '-'
    jr nz,sh_p604_invalid_restore
sh_p604_validate_next:
    inc hl
    dec c
    jr sh_p604_validate_tail

sh_p604_build:
    pop bc
    pop hl
    push de
    ex de,hl
    ld (hl),'/'
    inc hl
    ld (hl),'h'
    inc hl
    ld (hl),'o'
    inc hl
    ld (hl),'m'
    inc hl
    ld (hl),'e'
    inc hl
    ld (hl),'/'
    inc hl
sh_p604_copy_user:
    ld a,b
    or c
    jr z,sh_p604_terminate
    ld a,(de)
    ld (hl),a
    inc de
    inc hl
    dec bc
    jr sh_p604_copy_user
sh_p604_terminate:
    xor a
    ld (hl),a
    pop hl
    ld a,SYS_CHDIR
    jp SYSCALL_GATEWAY

sh_p604_invalid_restore:
    pop bc
    pop hl
sh_p604_invalid:
    ld a,E_INVAL
    scf
    ret

; HL=writable buffer, BC=capacity. pwd uses the kernel descriptor cwd.
sh_p604_getcwd:
    ld a,SYS_GETCWD
    jp SYSCALL_GATEWAY
    ENDM

; P6.05 initial mutable environment. The shell table uses canonical ENV1 bytes.
    MACRO EMIT_P605_ENV_ROUTINES
; HL=username, BC=length (accepted P6.03 identity), DE=writable ENV1 buffer.
; Emits exact sorted HOME,PATH,SHELL,USER entries. $? is not in this table.
sh_p605_init_env:
    ld a,b
    or a
    jp nz,sh_p605_invalid
    ld a,c
    or a
    jp z,sh_p605_invalid
    cp 9
    jp nc,sh_p605_invalid
    push hl
    pop ix
    ld a,c
    add a,a
    add a,52
    ld h,a
    push bc

    ld a,'E'
    ld (de),a
    inc de
    ld a,'N'
    ld (de),a
    inc de
    ld a,'V'
    ld (de),a
    inc de
    ld a,'1'
    ld (de),a
    inc de
    ld a,4
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de

    ; HOME=/home/<user>
    ld a,'H'
    ld (de),a
    inc de
    ld a,'O'
    ld (de),a
    inc de
    ld a,'M'
    ld (de),a
    inc de
    ld a,'E'
    ld (de),a
    inc de
    ld a,'='
    ld (de),a
    inc de
    ld a,'/'
    ld (de),a
    inc de
    ld a,'h'
    ld (de),a
    inc de
    ld a,'o'
    ld (de),a
    inc de
    ld a,'m'
    ld (de),a
    inc de
    ld a,'e'
    ld (de),a
    inc de
    ld a,'/'
    ld (de),a
    inc de
    pop bc
    push bc
    push ix
    pop hl
sh_p605_home_user:
    ld a,b
    or c
    jr z,sh_p605_home_done
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    dec bc
    jr sh_p605_home_user
sh_p605_home_done:
    xor a
    ld (de),a
    inc de

    ; PATH=/bin:.
    ld a,'P'
    ld (de),a
    inc de
    ld a,'A'
    ld (de),a
    inc de
    ld a,'T'
    ld (de),a
    inc de
    ld a,'H'
    ld (de),a
    inc de
    ld a,'='
    ld (de),a
    inc de
    ld a,'/'
    ld (de),a
    inc de
    ld a,'b'
    ld (de),a
    inc de
    ld a,'i'
    ld (de),a
    inc de
    ld a,'n'
    ld (de),a
    inc de
    ld a,':'
    ld (de),a
    inc de
    ld a,'.'
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de

    ; SHELL=/bin/sh
    ld a,'S'
    ld (de),a
    inc de
    ld a,'H'
    ld (de),a
    inc de
    ld a,'E'
    ld (de),a
    inc de
    ld a,'L'
    ld (de),a
    inc de
    ld a,'L'
    ld (de),a
    inc de
    ld a,'='
    ld (de),a
    inc de
    ld a,'/'
    ld (de),a
    inc de
    ld a,'b'
    ld (de),a
    inc de
    ld a,'i'
    ld (de),a
    inc de
    ld a,'n'
    ld (de),a
    inc de
    ld a,'/'
    ld (de),a
    inc de
    ld a,'s'
    ld (de),a
    inc de
    ld a,'h'
    ld (de),a
    inc de
    xor a
    ld (de),a
    inc de

    ; USER=<user>
    ld a,'U'
    ld (de),a
    inc de
    ld a,'S'
    ld (de),a
    inc de
    ld a,'E'
    ld (de),a
    inc de
    ld a,'R'
    ld (de),a
    inc de
    ld a,'='
    ld (de),a
    inc de
    pop bc
    push ix
    pop hl
sh_p605_user_copy:
    ld a,b
    or c
    jr z,sh_p605_user_done
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    dec bc
    jr sh_p605_user_copy
sh_p605_user_done:
    xor a
    ld (de),a
    ret

sh_p605_invalid:
    ld a,E_INVAL
    scf
    ret

; HL points at the separate one-byte shell status used by $? expansion.
sh_p605_status_init:
    xor a
    ld (hl),a
    ret
    ENDM

; P6.06 transactional set/unset over the shell's canonical ENV1 table.
    MACRO EMIT_P606_SET_UNSET_ROUTINES
; IX=ENV1 buffer, HL=NUL NAME=VALUE. Existing table must be canonical/sorted.
; On success the exact ENV1 is replaced atomically from a private 256-byte
; scratch image. On any lexical/capacity failure the original bytes are untouched.
sh_p606_set:
    ld (p606_env_ptr),ix
    ld (p606_new_ptr),hl
    call sh_p606_parse_set_arg
    ret c
    call sh_p606_prepare_env
    ret c
    call sh_p606_find_name
    ret c
    ld a,(p606_found)
    or a
    jr nz,sh_p606_set_replace_count
    ld a,(p606_old_count)
    cp 8
    jp nc,sh_p606_nospc
    inc a
    jr sh_p606_set_count_ready
sh_p606_set_replace_count:
    ld a,(p606_old_count)
sh_p606_set_count_ready:
    ld (p606_new_count),a

    ld hl,(p606_old_total)
    ld a,(p606_found)
    or a
    jr z,sh_p606_set_add_new
    ld a,(p606_found_len)
    ld e,a
    ld d,0
    or a
    sbc hl,de
sh_p606_set_add_new:
    ld a,(p606_new_len)
    ld e,a
    ld d,0
    add hl,de
    ld a,h
    or a
    jp nz,sh_p606_nospc
    ld a,l
    or a
    jp z,sh_p606_nospc
    ld (p606_new_total),hl

    call sh_p606_scratch_header
    ld hl,(p606_env_ptr)
    ld de,8
    add hl,de
    ld (p606_old_ptr),hl
    xor a
    ld (p606_inserted),a
    ld a,(p606_old_count)
    ld (p606_remaining),a

sh_p606_set_rebuild_loop:
    ld a,(p606_remaining)
    or a
    jr z,sh_p606_set_rebuild_done
    ld hl,(p606_old_ptr)
    ld de,(p606_new_ptr)
    call sh_p606_compare_names
    jr z,sh_p606_set_skip_replaced
    jr c,sh_p606_set_old_before
    ld a,(p606_inserted)
    or a
    jr nz,sh_p606_set_old_before
    call sh_p606_copy_new
    ld a,1
    ld (p606_inserted),a
sh_p606_set_old_before:
    call sh_p606_copy_old
    jr sh_p606_set_rebuild_next
sh_p606_set_skip_replaced:
    ld a,(p606_inserted)
    or a
    call z,sh_p606_copy_new
    ld a,1
    ld (p606_inserted),a
    call sh_p606_skip_old
sh_p606_set_rebuild_next:
    ld a,(p606_remaining)
    dec a
    ld (p606_remaining),a
    jr sh_p606_set_rebuild_loop

sh_p606_set_rebuild_done:
    ld a,(p606_inserted)
    or a
    call z,sh_p606_copy_new
    jp sh_p606_commit_scratch

; IX=ENV1 buffer, HL=NUL NAME. Missing names are a successful no-op.
sh_p606_unset:
    ld (p606_env_ptr),ix
    ld (p606_new_ptr),hl
    call sh_p606_parse_name_only
    ret c
    call sh_p606_prepare_env
    ret c
    call sh_p606_find_name
    ret c
    ld a,(p606_found)
    or a
    jp z,sh_p606_ok

    ld a,(p606_old_count)
    dec a
    ld (p606_new_count),a
    ld hl,(p606_old_total)
    ld a,(p606_found_len)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (p606_new_total),hl
    call sh_p606_scratch_header

    ld hl,(p606_env_ptr)
    ld de,8
    add hl,de
    ld (p606_old_ptr),hl
    ld a,(p606_old_count)
    ld (p606_remaining),a
sh_p606_unset_loop:
    ld a,(p606_remaining)
    or a
    jp z,sh_p606_commit_scratch
    ld hl,(p606_old_ptr)
    ld de,(p606_new_ptr)
    call sh_p606_compare_names
    jr z,sh_p606_unset_skip
    call sh_p606_copy_old
    jr sh_p606_unset_next
sh_p606_unset_skip:
    call sh_p606_skip_old
sh_p606_unset_next:
    ld a,(p606_remaining)
    dec a
    ld (p606_remaining),a
    jr sh_p606_unset_loop

; Validate set operand. First '=' terminates NAME, later '=' bytes are VALUE data.
; ENV1 lexical limits are enforced before any table byte changes.
sh_p606_parse_set_arg:
    ld hl,(p606_new_ptr)
    ld b,0
    ld a,(hl)
    call sh_p606_name_first
    ret c
sh_p606_parse_set_name:
    ld a,(hl)
    cp '='
    jr z,sh_p606_parse_set_value
    or a
    jp z,sh_p606_invalid
    ld a,b
    cp 15
    jp nc,sh_p606_invalid
    ld a,(hl)
    call sh_p606_name_tail
    ret c
    inc b
    inc hl
    jr sh_p606_parse_set_name

sh_p606_parse_set_value:
    ld a,b
    or a
    jp z,sh_p606_invalid
    inc hl
    ld c,0
sh_p606_parse_set_value_loop:
    ld a,(hl)
    or a
    jr z,sh_p606_parse_set_done
    cp $20
    jp c,sh_p606_invalid
    cp $7f
    jp nc,sh_p606_invalid
    ld a,c
    cp 63
    jp nc,sh_p606_invalid
    inc c
    inc hl
    jr sh_p606_parse_set_value_loop
sh_p606_parse_set_done:
    ld a,b
    add a,c
    add a,2
    ld (p606_new_len),a
    xor a
    ret

; Validate unset operand NAME with no '='.
sh_p606_parse_name_only:
    ld hl,(p606_new_ptr)
    ld b,0
    ld a,(hl)
    call sh_p606_name_first
    ret c
sh_p606_parse_unset_loop:
    ld a,(hl)
    or a
    jr z,sh_p606_parse_unset_done
    cp '='
    jp z,sh_p606_invalid
    ld a,b
    cp 15
    jp nc,sh_p606_invalid
    ld a,(hl)
    call sh_p606_name_tail
    ret c
    inc b
    inc hl
    jr sh_p606_parse_unset_loop
sh_p606_parse_unset_done:
    ld a,b
    or a
    jp z,sh_p606_invalid
    inc a
    ld (p606_new_len),a
    xor a
    ret

; A=first NAME byte.
sh_p606_name_first:
    cp 'A'
    jr c,sh_p606_name_first_lower
    cp 'Z'+1
    jr c,sh_p606_char_ok
sh_p606_name_first_lower:
    cp 'a'
    jr c,sh_p606_name_first_us
    cp 'z'+1
    jr c,sh_p606_char_ok
sh_p606_name_first_us:
    cp '_'
    jr z,sh_p606_char_ok
    jp sh_p606_invalid
; A=subsequent NAME byte.
sh_p606_name_tail:
    cp 'A'
    jr c,sh_p606_name_tail_lower
    cp 'Z'+1
    jr c,sh_p606_char_ok
sh_p606_name_tail_lower:
    cp 'a'
    jr c,sh_p606_name_tail_digit
    cp 'z'+1
    jr c,sh_p606_char_ok
sh_p606_name_tail_digit:
    cp '0'
    jr c,sh_p606_name_tail_us
    cp '9'+1
    jr c,sh_p606_char_ok
sh_p606_name_tail_us:
    cp '_'
    jr z,sh_p606_char_ok
    jp sh_p606_invalid
sh_p606_char_ok:
    xor a
    ret

; Prove the source ENV1 before transaction work.
sh_p606_prepare_env:
    ld ix,(p606_env_ptr)
    ld l,(ix+6)
    ld h,(ix+7)
    ld (p606_old_total),hl
    ld b,h
    ld c,l
    call zx48_env1_validate
    ret c
    ld ix,(p606_env_ptr)
    ld a,(ix+4)
    ld (p606_old_count),a
    xor a
    ret

; Search exact NAME. p606_found=1 and found_len includes terminating NUL.
sh_p606_find_name:
    xor a
    ld (p606_found),a
    ld (p606_found_len),a
    ld hl,(p606_env_ptr)
    ld de,8
    add hl,de
    ld (p606_old_ptr),hl
    ld a,(p606_old_count)
    ld (p606_remaining),a
sh_p606_find_loop:
    ld a,(p606_remaining)
    or a
    ret z
    ld hl,(p606_old_ptr)
    ld de,(p606_new_ptr)
    call sh_p606_compare_names
    jr z,sh_p606_find_hit
    call sh_p606_skip_old
    ld a,(p606_remaining)
    dec a
    ld (p606_remaining),a
    jr sh_p606_find_loop
sh_p606_find_hit:
    ld a,1
    ld (p606_found),a
    ld hl,(p606_old_ptr)
    ld b,0
sh_p606_find_len:
    inc b
    ld a,(hl)
    inc hl
    or a
    jr nz,sh_p606_find_len
    ld a,b
    ld (p606_found_len),a
    xor a
    ret

; Compare old ENV name at HL with operand NAME at DE.
; Z => equal. C => old < new. NC/non-Z => old > new.
sh_p606_compare_names:
    ld a,(hl)
    cp '='
    jr z,sh_p606_cmp_old_end
    ld a,(de)
    or a
    jr z,sh_p606_cmp_old_greater
    cp '='
    jr z,sh_p606_cmp_old_greater
    ld a,(hl)
    ld b,a
    ld a,(de)
    cp b
    jr c,sh_p606_cmp_old_greater
    jr nz,sh_p606_cmp_old_less
    inc hl
    inc de
    jr sh_p606_compare_names
sh_p606_cmp_old_end:
    ld a,(de)
    or a
    jr z,sh_p606_cmp_equal
    cp '='
    jr z,sh_p606_cmp_equal
sh_p606_cmp_old_less:
    ld a,1
    or a
    scf
    ret
sh_p606_cmp_old_greater:
    ld a,1
    or a
    ret
sh_p606_cmp_equal:
    xor a
    ret

sh_p606_scratch_header:
    ld hl,p606_scratch
    ld (p606_dst_ptr),hl
    ld (hl),'E'
    inc hl
    ld (hl),'N'
    inc hl
    ld (hl),'V'
    inc hl
    ld (hl),'1'
    inc hl
    ld a,(p606_new_count)
    ld (hl),a
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld de,(p606_new_total)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld (p606_dst_ptr),hl
    ret

sh_p606_copy_new:
    ld hl,(p606_new_ptr)
    ld de,(p606_dst_ptr)
sh_p606_copy_new_loop:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jr nz,sh_p606_copy_new_loop
    ld (p606_dst_ptr),de
    ret

sh_p606_copy_old:
    ld hl,(p606_old_ptr)
    ld de,(p606_dst_ptr)
sh_p606_copy_old_loop:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jr nz,sh_p606_copy_old_loop
    ld (p606_old_ptr),hl
    ld (p606_dst_ptr),de
    ret

sh_p606_skip_old:
    ld hl,(p606_old_ptr)
sh_p606_skip_old_loop:
    ld a,(hl)
    inc hl
    or a
    jr nz,sh_p606_skip_old_loop
    ld (p606_old_ptr),hl
    ret

; Validate the finished scratch ENV1 and only then publish all bytes.
sh_p606_commit_scratch:
    ld ix,p606_scratch
    ld bc,(p606_new_total)
    call zx48_env1_validate
    ret c
    ld hl,p606_scratch
    ld de,(p606_env_ptr)
    ld bc,(p606_new_total)
    ldir
sh_p606_ok:
    xor a
    ret
sh_p606_nospc:
    ld a,E_NOSPC
    scf
    ret
sh_p606_invalid:
    ld a,E_INVAL
    scf
    ret

p606_env_ptr: dw 0
p606_new_ptr: dw 0
p606_old_ptr: dw 0
p606_dst_ptr: dw 0
p606_old_total: dw 0
p606_new_total: dw 0
p606_old_count: db 0
p606_new_count: db 0
p606_new_len: db 0
p606_found_len: db 0
p606_found: db 0
p606_inserted: db 0
p606_remaining: db 0
p606_scratch: defs 256,0
    ENDM

; P6.07 bounded interactive line input. All input is obtained through SYS_READ
; handle 0, so the kernel tty ownership contract remains the sole input owner.
    MACRO EMIT_P607_LINE_ROUTINES
P607_LINE_MAX            EQU 247

; IX=writable destination >=248 bytes. On success copy the edited line plus NUL.
; On E_TOOLONG/E_INVAL/read failure the caller destination remains untouched.
sh_p607_read_line:
    ld (p607_dest),ix
    xor a
    ld (p607_len),a

sh_p607_read_next:
    ld de,0
    ld hl,p607_key
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jp nz,sh_p607_read_fault
    ld a,l
    cp 1
    jp nz,sh_p607_read_fault

    ld a,(p607_key)
    cp $0d
    jp z,sh_p607_commit
    cp $0a
    jp z,sh_p607_commit
    cp $08
    jp z,sh_p607_backspace
    cp $7f
    jp z,sh_p607_backspace
    cp $09
    jp z,sh_p607_store
    cp $20
    jp c,sh_p607_invalid
    cp $7f
    jp nc,sh_p607_invalid

sh_p607_store:
    ld a,(p607_len)
    cp P607_LINE_MAX
    jp nc,sh_p607_toolong
    ld e,a
    ld d,0
    ld hl,p607_scratch
    add hl,de
    ld a,(p607_key)
    ld (hl),a
    ld a,(p607_len)
    inc a
    ld (p607_len),a
    jp sh_p607_read_next

sh_p607_backspace:
    ld a,(p607_len)
    or a
    jp z,sh_p607_read_next
    dec a
    ld (p607_len),a
    jp sh_p607_read_next

sh_p607_commit:
    ld hl,p607_scratch
    ld de,(p607_dest)
    ld a,(p607_len)
    ld c,a
    ld b,0
    push bc
    ldir
    xor a
    ld (de),a
    pop bc
    ld h,b
    ld l,c
    xor a
    ret

sh_p607_read_fault:
    ld a,E_IO
    scf
    ret
sh_p607_toolong:
    ld a,E_TOOLONG
    scf
    ret
sh_p607_invalid:
    ld a,E_INVAL
    scf
    ret

p607_dest: dw 0
p607_len: db 0
p607_key: db 0
p607_scratch: defs P607_LINE_MAX,0
    ENDM
