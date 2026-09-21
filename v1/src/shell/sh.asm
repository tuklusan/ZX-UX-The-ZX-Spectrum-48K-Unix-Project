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

; P6.08 byte tokenizer. Quotes are removed here; '$' bytes remain data for P6.09.
    MACRO EMIT_P608_TOKENIZER_ROUTINES
P608_Q_NONE              EQU 0
P608_Q_SINGLE            EQU 1
P608_Q_DOUBLE            EQU 2
P608_TOKEN_MAX           EQU 248

; HL=NUL command line, IX=writable token buffer >=248 bytes.
; Success: B=token count, output is NUL-separated dequoted token bytes.
; Empty quoted strings produce empty tokens. C is the current output length.
sh_p608_tokenize:
    ld (p608_src),hl
    ld (p608_dst),ix
    xor a
    ld (p608_quote),a
    ld (p608_in_token),a
    ld (p608_count),a
    ld (p608_length),a

sh_p608_loop:
    ld hl,(p608_src)
    ld a,(hl)
    or a
    jp z,sh_p608_eol
    ld d,a
    ld a,(p608_quote)
    cp P608_Q_SINGLE
    jp z,sh_p608_single
    cp P608_Q_DOUBLE
    jp z,sh_p608_double

    ld a,d
    cp ' '
    jp z,sh_p608_separator
    cp $09
    jp z,sh_p608_separator
    cp $5c
    jp z,sh_p608_escape_plain
    cp $27
    jp z,sh_p608_open_single
    cp $22
    jp z,sh_p608_open_double
    call sh_p608_begin_token
    ld a,d
    call sh_p608_emit
    jp c,sh_p608_return
    call sh_p608_advance
    jp sh_p608_loop

sh_p608_escape_plain:
    call sh_p608_begin_token
    call sh_p608_advance
    ld hl,(p608_src)
    ld a,(hl)
    or a
    jp z,sh_p608_invalid
    call sh_p608_emit
    jp c,sh_p608_return
    call sh_p608_advance
    jp sh_p608_loop

sh_p608_open_single:
    call sh_p608_begin_token
    ld a,P608_Q_SINGLE
    ld (p608_quote),a
    call sh_p608_advance
    jp sh_p608_loop

sh_p608_single:
    ld a,d
    cp $27
    jp z,sh_p608_close_quote
    call sh_p608_emit
    jp c,sh_p608_return
    call sh_p608_advance
    jp sh_p608_loop

sh_p608_open_double:
    call sh_p608_begin_token
    ld a,P608_Q_DOUBLE
    ld (p608_quote),a
    call sh_p608_advance
    jp sh_p608_loop

sh_p608_double:
    ld a,d
    cp $22
    jp z,sh_p608_close_quote
    cp $5c
    jp nz,sh_p608_double_plain
    call sh_p608_advance
    ld hl,(p608_src)
    ld a,(hl)
    or a
    jp z,sh_p608_invalid
    cp $22
    jp z,sh_p608_double_escaped
    cp $5c
    jp z,sh_p608_double_escaped
    cp '$'
    jp z,sh_p608_double_escaped
    ld a,$5c
    call sh_p608_emit
    jp c,sh_p608_return
    jp sh_p608_loop
sh_p608_double_escaped:
    call sh_p608_emit
    jp c,sh_p608_return
    call sh_p608_advance
    jp sh_p608_loop
sh_p608_double_plain:
    ld a,d
    call sh_p608_emit
    jp c,sh_p608_return
    call sh_p608_advance
    jp sh_p608_loop

sh_p608_close_quote:
    xor a
    ld (p608_quote),a
    call sh_p608_advance
    jp sh_p608_loop

sh_p608_separator:
    ld a,(p608_in_token)
    or a
    call nz,sh_p608_end_token
    jp c,sh_p608_return
    call sh_p608_advance
    jp sh_p608_loop

sh_p608_eol:
    ld a,(p608_quote)
    or a
    jp nz,sh_p608_invalid
    ld a,(p608_in_token)
    or a
    call nz,sh_p608_end_token
    jp c,sh_p608_return
    ld a,(p608_count)
    ld b,a
    ld a,(p608_length)
    ld c,a
    xor a
    ret

sh_p608_begin_token:
    ld a,(p608_in_token)
    or a
    ret nz
    ld a,1
    ld (p608_in_token),a
    ret

sh_p608_end_token:
    xor a
    call sh_p608_emit
    ret c
    xor a
    ld (p608_in_token),a
    ld a,(p608_count)
    inc a
    ld (p608_count),a
    xor a
    ret

sh_p608_emit:
    push af
    ld a,(p608_length)
    cp P608_TOKEN_MAX
    jp nc,sh_p608_emit_overflow
    ld e,a
    ld d,0
    ld hl,(p608_dst)
    add hl,de
    pop af
    ld (hl),a
    ld a,(p608_length)
    inc a
    ld (p608_length),a
    xor a
    ret
sh_p608_emit_overflow:
    pop af
    ld a,E_TOOLONG
    scf
    ret

sh_p608_advance:
    ld hl,(p608_src)
    inc hl
    ld (p608_src),hl
    ret

sh_p608_invalid:
    ld a,E_INVAL
    scf
sh_p608_return:
    ret

p608_src: dw 0
p608_dst: dw 0
p608_quote: db 0
p608_in_token: db 0
p608_count: db 0
p608_length: db 0
    ENDM

; P6.09 variable expansion contract. This scanner is consumed by the later
; integrated parser: only $NAME, ${NAME}, and $? are expansion forms.
    MACRO EMIT_P609_EXPANSION_ROUTINES
P609_NAME_MAX            EQU 15
P609_VALUE_MAX           EQU 63
P609_EXPAND_UNQUOTED     EQU 0
P609_EXPAND_SINGLE       EQU 1
P609_EXPAND_DOUBLE       EQU 2

; A=first candidate byte. Carry set means no valid NAME may start here.
sh_p609_name_first:
    cp 'A'
    jr c,sh_p609_name_first_lower
    cp 'Z'+1
    jr c,sh_p609_name_ok
sh_p609_name_first_lower:
    cp 'a'
    jr c,sh_p609_name_first_us
    cp 'z'+1
    jr c,sh_p609_name_ok
sh_p609_name_first_us:
    cp '_'
    jr z,sh_p609_name_ok
    scf
    ret

; A=subsequent NAME byte.
sh_p609_name_tail:
    cp 'A'
    jr c,sh_p609_name_tail_lower
    cp 'Z'+1
    jr c,sh_p609_name_ok
sh_p609_name_tail_lower:
    cp 'a'
    jr c,sh_p609_name_tail_digit
    cp 'z'+1
    jr c,sh_p609_name_ok
sh_p609_name_tail_digit:
    cp '0'
    jr c,sh_p609_name_tail_us
    cp '9'+1
    jr c,sh_p609_name_ok
sh_p609_name_tail_us:
    cp '_'
    jr z,sh_p609_name_ok
    scf
    ret
sh_p609_name_ok:
    or a
    ret

; HL points at '$', A is quote mode. Return:
; carry => malformed braced expansion; otherwise DE points one byte after the
; consumed expansion reference and B=name length. C=form:
; 0 literal '$', 1 NAME, 2 braced NAME, 3 status.
sh_p609_scan_reference:
    cp P609_EXPAND_SINGLE
    jr z,sh_p609_ref_literal
    inc hl
    ld a,(hl)
    cp '?'
    jr z,sh_p609_ref_status
    cp '{'
    jr z,sh_p609_ref_braced
    call sh_p609_name_first
    jr c,sh_p609_ref_literal_after
    ld b,1
    inc hl
sh_p609_ref_name_loop:
    ld a,b
    cp P609_NAME_MAX
    jr nc,sh_p609_ref_name_done
    ld a,(hl)
    call sh_p609_name_tail
    jr c,sh_p609_ref_name_done
    inc b
    inc hl
    jr sh_p609_ref_name_loop
sh_p609_ref_name_done:
    ex de,hl
    ld c,1
    xor a
    ret

sh_p609_ref_braced:
    inc hl
    ld a,(hl)
    call sh_p609_name_first
    jr c,sh_p609_ref_invalid
    ld b,1
    inc hl
sh_p609_ref_braced_loop:
    ld a,(hl)
    cp '}'
    jr z,sh_p609_ref_braced_done
    ld a,b
    cp P609_NAME_MAX
    jr nc,sh_p609_ref_invalid
    ld a,(hl)
    call sh_p609_name_tail
    jr c,sh_p609_ref_invalid
    inc b
    inc hl
    jr sh_p609_ref_braced_loop
sh_p609_ref_braced_done:
    inc hl
    ex de,hl
    ld c,2
    xor a
    ret

sh_p609_ref_status:
    inc hl
    ex de,hl
    ld b,0
    ld c,3
    xor a
    ret

sh_p609_ref_literal_after:
    dec hl
sh_p609_ref_literal:
    inc hl
    ex de,hl
    ld b,0
    ld c,0
    xor a
    ret

sh_p609_ref_invalid:
    ld a,E_INVAL
    scf
    ret

; IX=canonical ENV1, HL=name bytes, B=name length.
; Success: carry clear, DE=value bytes, C=value length. Missing => C=0 and DE=0.
sh_p609_env_lookup:
    ld a,b
    or a
    jr z,sh_p609_env_missing
    ld (p609_name_ptr),hl
    ld a,b
    ld (p609_name_len),a
    ld a,(ix+4)
    ld (p609_env_left),a
    push ix
    pop hl
    ld de,8
    add hl,de
sh_p609_env_entry:
    ld a,(p609_env_left)
    or a
    jr z,sh_p609_env_missing
    ld (p609_entry_ptr),hl
    ld de,(p609_name_ptr)
    ld a,(p609_name_len)
    ld b,a
sh_p609_env_compare:
    ld a,b
    or a
    jr z,sh_p609_env_name_end
    ld a,(de)
    cp (hl)
    jr nz,sh_p609_env_next
    inc de
    inc hl
    dec b
    jr sh_p609_env_compare
sh_p609_env_name_end:
    ld a,(hl)
    cp '='
    jr nz,sh_p609_env_next
    inc hl
    ex de,hl
    ld c,0
sh_p609_env_value_len:
    ld a,(de)
    or a
    jr z,sh_p609_env_found
    inc de
    inc c
    jr sh_p609_env_value_len
sh_p609_env_found:
    ld hl,(p609_entry_ptr)
sh_p609_env_seek_eq:
    ld a,(hl)
    inc hl
    cp '='
    jr nz,sh_p609_env_seek_eq
    ex de,hl
    xor a
    ret
sh_p609_env_next:
    ld hl,(p609_entry_ptr)
sh_p609_env_skip:
    ld a,(hl)
    inc hl
    or a
    jr nz,sh_p609_env_skip
    ld a,(p609_env_left)
    dec a
    ld (p609_env_left),a
    jr sh_p609_env_entry
sh_p609_env_missing:
    ld de,0
    ld c,0
    xor a
    ret

; A=shell status, DE=destination >=4 bytes. Returns C=ASCII byte count.
sh_p609_status_decimal:
    ld c,0
    cp 100
    jr c,sh_p609_status_tens
    ld b,0
sh_p609_status_hundreds_loop:
    cp 100
    jr c,sh_p609_status_hundreds_done
    sub 100
    inc b
    jr sh_p609_status_hundreds_loop
sh_p609_status_hundreds_done:
    push af
    ld a,b
    add a,'0'
    ld (de),a
    inc de
    inc c
    pop af
    ld b,1
    jr sh_p609_status_tens_forced
sh_p609_status_tens:
    ld b,0
sh_p609_status_tens_forced:
    cp 10
    jr c,sh_p609_status_ones
    ld h,0
sh_p609_status_tens_loop:
    cp 10
    jr c,sh_p609_status_tens_done
    sub 10
    inc h
    jr sh_p609_status_tens_loop
sh_p609_status_tens_done:
    push af
    ld a,h
    add a,'0'
    ld (de),a
    inc de
    inc c
    pop af
    ld b,1
sh_p609_status_ones:
    push af
    ld a,b
    or a
    jr nz,sh_p609_status_emit_one
    pop af
    push af
sh_p609_status_emit_one:
    pop af
    add a,'0'
    ld (de),a
    inc c
    xor a
    ret

p609_name_ptr: dw 0
p609_entry_ptr: dw 0
p609_name_len: db 0
p609_env_left: db 0
    ENDM

; P6.10 operator lexer over raw command bytes. Operator recognition is permitted
; only when the byte is unquoted and unescaped.
    MACRO EMIT_P610_OPERATOR_ROUTINES
P610_OP_NONE             EQU 0
P610_OP_SEMI             EQU 1
P610_OP_AND              EQU 2
P610_OP_OR               EQU 3
P610_OP_OUT              EQU 4
P610_OP_APPEND           EQU 5
P610_OP_IN               EQU 6
P610_OP_PIPE             EQU 7
P610_OP_BG               EQU 8

; HL=current raw byte, A=quote mode (0 unquoted), B=1 when current byte escaped.
; Success C=operator token or NONE, B=consumed width 1/2.
; '(' and ')' are explicitly unsupported grouping syntax and return E_INVAL.
sh_p610_lex_operator:
    ld c,P610_OP_NONE
    or a
    jr nz,sh_p610_literal
    ld a,b
    or a
    jr nz,sh_p610_literal
    ld a,(hl)
    cp '('
    jr z,sh_p610_grouping
    cp ')'
    jr z,sh_p610_grouping
    cp ';'
    jr z,sh_p610_semi
    cp '&'
    jr z,sh_p610_amp
    cp '|'
    jr z,sh_p610_bar
    cp '>'
    jr z,sh_p610_gt
    cp '<'
    jr z,sh_p610_in
sh_p610_literal:
    ld b,1
    xor a
    ret

sh_p610_semi:
    ld c,P610_OP_SEMI
    ld b,1
    xor a
    ret
sh_p610_amp:
    inc hl
    ld a,(hl)
    cp '&'
    jr z,sh_p610_and
    ld c,P610_OP_BG
    ld b,1
    xor a
    ret
sh_p610_and:
    ld c,P610_OP_AND
    ld b,2
    xor a
    ret
sh_p610_bar:
    inc hl
    ld a,(hl)
    cp '|'
    jr z,sh_p610_or
    ld c,P610_OP_PIPE
    ld b,1
    xor a
    ret
sh_p610_or:
    ld c,P610_OP_OR
    ld b,2
    xor a
    ret
sh_p610_gt:
    inc hl
    ld a,(hl)
    cp '>'
    jr z,sh_p610_append
    ld c,P610_OP_OUT
    ld b,1
    xor a
    ret
sh_p610_append:
    ld c,P610_OP_APPEND
    ld b,2
    xor a
    ret
sh_p610_in:
    ld c,P610_OP_IN
    ld b,1
    xor a
    ret
sh_p610_grouping:
    ld a,E_INVAL
    scf
    ret
    ENDM

; P6.11 precedence/binding helpers for the integrated parser.
    MACRO EMIT_P611_BINDING_ROUTINES
P611_PREC_BG            EQU 0
P611_PREC_SEMI          EQU 1
P611_PREC_LOGIC         EQU 2
P611_PREC_PIPE          EQU 3
P611_PREC_REDIR         EQU 4

; A=P610 operator token. Carry set means not a parser operator.
; C=precedence where larger binds more tightly.
sh_p611_precedence:
    cp P610_OP_OUT
    jr z,sh_p611_redir
    cp P610_OP_APPEND
    jr z,sh_p611_redir
    cp P610_OP_IN
    jr z,sh_p611_redir
    cp P610_OP_PIPE
    jr z,sh_p611_pipe
    cp P610_OP_AND
    jr z,sh_p611_logic
    cp P610_OP_OR
    jr z,sh_p611_logic
    cp P610_OP_SEMI
    jr z,sh_p611_semi
    cp P610_OP_BG
    jr z,sh_p611_bg
    ld a,E_INVAL
    scf
    ret
sh_p611_redir:
    ld c,P611_PREC_REDIR
    xor a
    ret
sh_p611_pipe:
    ld c,P611_PREC_PIPE
    xor a
    ret
sh_p611_logic:
    ld c,P611_PREC_LOGIC
    xor a
    ret
sh_p611_semi:
    ld c,P611_PREC_SEMI
    xor a
    ret
sh_p611_bg:
    ld c,P611_PREC_BG
    xor a
    ret

; A=nonzero if ';', '&&', or '||' already occurred on this command line.
; B=nonzero iff '&' is the final token. Version-1 backgrounding is valid only
; for one final complete pipeline and cannot coexist with those controls.
sh_p611_validate_background:
    or a
    jr nz,sh_p611_invalid
    ld a,b
    or a
    jr z,sh_p611_invalid
    xor a
    ret
sh_p611_invalid:
    ld a,E_INVAL
    scf
    ret

; Parenthesized grouping/subshells do not exist in version 1.
sh_p611_reject_grouping:
    ld a,E_INVAL
    scf
    ret
    ENDM

; P6.12 parser execution bounds. Call after expansion and before any spawn/redirection.
    MACRO EMIT_P612_BOUND_ROUTINES
P612_ARG_MAX             EQU 16
P612_PIPE_MAX            EQU 6

; A=argc including argv[0], B=pipeline stage count.
; Carry set E_TOOLONG on either bound violation. No side effect occurs here.
sh_p612_validate_bounds:
    or a
    jr z,sh_p612_invalid
    cp P612_ARG_MAX+1
    jr nc,sh_p612_toolong
    ld a,b
    or a
    jr z,sh_p612_invalid
    cp P612_PIPE_MAX+1
    jr nc,sh_p612_toolong
    xor a
    ret
sh_p612_toolong:
    ld a,E_TOOLONG
    scf
    ret
sh_p612_invalid:
    ld a,E_INVAL
    scf
    ret
    ENDM

; P6.13 exact lower-case core/stateful builtin lookup. Phase-7 ROM-assisted
; names have explicit zero dispatch-hook slots but are not resolvable here.
    MACRO EMIT_P613_BUILTIN_ROUTINES
P613_BUILTIN_CD          EQU 1
P613_BUILTIN_PWD         EQU 2
P613_BUILTIN_SET         EQU 3
P613_BUILTIN_UNSET       EQU 4
P613_BUILTIN_JOBS        EQU 5
P613_BUILTIN_WAIT        EQU 6
P613_BUILTIN_KILL        EQU 7
P613_BUILTIN_MEM         EQU 8
P613_BUILTIN_PS          EQU 9
P613_BUILTIN_CLEAR       EQU 10
P613_BUILTIN_SAVE        EQU 11
P613_BUILTIN_LOAD        EQU 12
P613_BUILTIN_VERIFY      EQU 13
P613_BUILTIN_TAPE        EQU 14
P613_BUILTIN_EXIT        EQU 15

; HL=name bytes, B=exact byte length. Success A=stable core builtin ID.
; Mixed case, aliases, ROM hooks and unknown names return E_NOENT.
sh_p613_lookup_builtin:
    ld (p613_query_ptr),hl
    ld a,b
    ld (p613_query_len),a
    ld hl,p613_core_table
sh_p613_lookup_next:
    ld a,(hl)
    or a
    jr z,sh_p613_lookup_miss
    ld c,a
    inc hl
    ld a,(p613_query_len)
    cp c
    jr nz,sh_p613_lookup_skip
    push hl
    ld de,(p613_query_ptr)
    ld b,c
sh_p613_lookup_cmp:
    ld a,(de)
    cp (hl)
    jr nz,sh_p613_lookup_cmp_fail
    inc de
    inc hl
    djnz sh_p613_lookup_cmp
    ld a,(hl)
    pop de
    or a
    ret
sh_p613_lookup_cmp_fail:
    pop hl
sh_p613_lookup_skip:
    ld e,c
    ld d,0
    add hl,de
    inc hl
    jr sh_p613_lookup_next
sh_p613_lookup_miss:
    ld a,E_NOENT
    scf
    ret

p613_core_table:
    db 2,'c','d',P613_BUILTIN_CD
    db 3,'p','w','d',P613_BUILTIN_PWD
    db 3,'s','e','t',P613_BUILTIN_SET
    db 5,'u','n','s','e','t',P613_BUILTIN_UNSET
    db 4,'j','o','b','s',P613_BUILTIN_JOBS
    db 4,'w','a','i','t',P613_BUILTIN_WAIT
    db 4,'k','i','l','l',P613_BUILTIN_KILL
    db 3,'m','e','m',P613_BUILTIN_MEM
    db 2,'p','s',P613_BUILTIN_PS
    db 5,'c','l','e','a','r',P613_BUILTIN_CLEAR
    db 4,'s','a','v','e',P613_BUILTIN_SAVE
    db 4,'l','o','a','d',P613_BUILTIN_LOAD
    db 6,'v','e','r','i','f','y',P613_BUILTIN_VERIFY
    db 4,'t','a','p','e',P613_BUILTIN_TAPE
    db 4,'e','x','i','t',P613_BUILTIN_EXIT
    db 0

; Explicit Phase-7 dispatch hooks. Each trailing word is zero until the owning
; Phase-7 step installs a handler; P6.13 lookup deliberately ignores this table.
p613_rom_hook_table:
    db 4,'c','a','l','c'
    dw 0
    db 4,'b','e','e','p'
    dw 0
    db 4,'p','l','o','t'
    dw 0
    db 4,'l','i','n','e'
    dw 0
    db 6,'c','i','r','c','l','e'
    dw 0
    db 5,'p','o','i','n','t'
    dw 0
    db 3,'i','n','k'
    dw 0
    db 5,'p','a','p','e','r'
    dw 0
    db 6,'b','r','i','g','h','t'
    dw 0
    db 5,'f','l','a','s','h'
    dw 0
    db 7,'i','n','v','e','r','s','e'
    dw 0
    db 4,'o','v','e','r'
    dw 0
    db 6,'b','o','r','d','e','r'
    dw 0
    db 3,'r','o','m'
    dw 0
    db 0

p613_query_ptr: dw 0
p613_query_len: db 0
    ENDM

; P6.14 exact external PATH lookup. PATH search skips unusable components and
; wrong-type candidates; direct slash paths bypass builtin/PATH policy.
    MACRO EMIT_P614_PATH_ROUTINES
P614_PATH_MAX            EQU 31
P614_STAT_TYPE           EQU 0
P614_STAT_STATE          EQU 7

; HL=NUL command token, IX=NUL PATH value (IX=0 means unset), DE=output >=32.
; Success writes resolved candidate to DE and returns C=namespace state.
sh_p614_lookup_external:
    ld (p614_cmd_ptr),hl
    ld (p614_path_ptr),ix
    ld (p614_out_ptr),de
    xor a
    ld (p614_cmd_len),a
    ld (p614_has_slash),a

    ld hl,(p614_cmd_ptr)
sh_p614_count_cmd:
    ld a,(hl)
    or a
    jr z,sh_p614_cmd_count_done
    cp '/'
    jr nz,sh_p614_cmd_no_slash
    ld a,1
    ld (p614_has_slash),a
sh_p614_cmd_no_slash:
    ld a,(p614_cmd_len)
    cp P614_PATH_MAX
    jp nc,sh_p614_cmd_too_long
    inc a
    ld (p614_cmd_len),a
    inc hl
    jr sh_p614_count_cmd

sh_p614_cmd_count_done:
    ld a,(p614_cmd_len)
    or a
    jp z,sh_p614_noent
    ld a,(p614_has_slash)
    or a
    jp nz,sh_p614_direct

    ld hl,(p614_path_ptr)
    ld a,h
    or l
    jp z,sh_p614_noent
    ld a,(hl)
    or a
    jp z,sh_p614_noent

sh_p614_component_start:
    ld hl,(p614_path_ptr)
    xor a
    ld (p614_comp_len),a
    ld (p614_comp_over),a
    ld de,p614_component

sh_p614_component_scan:
    ld a,(hl)
    cp ':'
    jr z,sh_p614_component_end_colon
    or a
    jr z,sh_p614_component_end_nul
    ld b,a
    ld a,(p614_comp_len)
    cp P614_PATH_MAX
    jr nc,sh_p614_component_mark_over
    ld a,b
    ld (de),a
    inc de
    ld a,(p614_comp_len)
    inc a
    ld (p614_comp_len),a
    jr sh_p614_component_advance
sh_p614_component_mark_over:
    ld a,1
    ld (p614_comp_over),a
sh_p614_component_advance:
    inc hl
    jr sh_p614_component_scan

sh_p614_component_end_colon:
    ld a,1
    ld (p614_more),a
    inc hl
    ld (p614_next_path),hl
    jr sh_p614_component_finish
sh_p614_component_end_nul:
    xor a
    ld (p614_more),a
    ld (p614_next_path),hl

sh_p614_component_finish:
    xor a
    ld (de),a
    ld a,(p614_comp_over)
    or a
    jr nz,sh_p614_component_skip

    ld a,(p614_comp_len)
    or a
    jr nz,sh_p614_component_nonempty
    ld hl,p614_component
    ld (hl),'.'
    inc hl
    xor a
    ld (hl),a
    ld a,1
    ld (p614_comp_len),a
sh_p614_component_nonempty:
    ; Combined raw candidate must fit the 31-byte resolved-path limit.
    ld a,(p614_comp_len)
    ld b,a
    ld a,(p614_cmd_len)
    add a,b
    inc a
    cp P614_PATH_MAX+1
    jr nc,sh_p614_component_skip

    ld hl,p614_component
    call sh_p614_stat
    jr c,sh_p614_component_skip
    ld a,(p614_statout+P614_STAT_TYPE)
    cp OBJ_DIR
    jr nz,sh_p614_component_skip

    call sh_p614_build_candidate
    ld hl,p614_candidate
    call sh_p614_stat
    jr c,sh_p614_component_skip
    ld a,(p614_statout+P614_STAT_TYPE)
    cp OBJ_BIN
    jr nz,sh_p614_component_skip
    ld a,(p614_statout+P614_STAT_STATE)
    ld c,a
    ld hl,p614_candidate
    jp sh_p614_commit_path

sh_p614_component_skip:
    ld a,(p614_more)
    or a
    jp z,sh_p614_noent
    ld hl,(p614_next_path)
    ld (p614_path_ptr),hl
    jp sh_p614_component_start

; Direct slash path: validate existence/normalized-length through SYS_STAT, but
; deliberately do not reject non-BIN here; SYS_SPAWN owns the E_FORMAT result.
sh_p614_direct:
    ld hl,(p614_cmd_ptr)
    ld de,p614_candidate
    ld b,0
sh_p614_direct_copy:
    ld a,(hl)
    ld (de),a
    inc de
    inc hl
    or a
    jr z,sh_p614_direct_stat
    inc b
    ld a,b
    cp P614_PATH_MAX+1
    jp nc,sh_p614_toolong
    jr sh_p614_direct_copy
sh_p614_direct_stat:
    ld hl,p614_candidate
    call sh_p614_stat
    ret c
    ld a,(p614_statout+P614_STAT_STATE)
    ld c,a
    ld hl,p614_candidate
    jp sh_p614_commit_path

sh_p614_build_candidate:
    ld hl,p614_component
    ld de,p614_candidate
sh_p614_build_component:
    ld a,(hl)
    or a
    jr z,sh_p614_build_slash
    ld (de),a
    inc hl
    inc de
    jr sh_p614_build_component
sh_p614_build_slash:
    ld a,'/'
    ld (de),a
    inc de
    ld hl,(p614_cmd_ptr)
sh_p614_build_cmd:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jr nz,sh_p614_build_cmd
    ret

sh_p614_stat:
    ld (p614_stat_req+0),hl
    ld de,p614_statout
    ld (p614_stat_req+2),de
    ld hl,p614_stat_req
    ld a,SYS_STAT
    jp SYSCALL_GATEWAY

sh_p614_commit_path:
    ld de,(p614_out_ptr)
sh_p614_commit_loop:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jr nz,sh_p614_commit_loop
    xor a
    ret

sh_p614_cmd_too_long:
    ld a,(p614_has_slash)
    or a
    jr nz,sh_p614_toolong
    ; No slash: every PATH candidate is necessarily overlong, so search fails.
    jr sh_p614_noent
sh_p614_toolong:
    ld a,E_TOOLONG
    scf
    ret
sh_p614_noent:
    ld a,E_NOENT
    scf
    ret

p614_cmd_ptr: dw 0
p614_path_ptr: dw 0
p614_next_path: dw 0
p614_out_ptr: dw 0
p614_cmd_len: db 0
p614_comp_len: db 0
p614_has_slash: db 0
p614_comp_over: db 0
p614_more: db 0
p614_component: defs 32,0
p614_candidate: defs 32,0
p614_stat_req: defs 4,0
p614_statout: defs 10,0
    ENDM

; P6.15 explicit consent gate for catalog-only tape-backed executables.
    MACRO EMIT_P615_TAPE_DISCOVERY_ROUTINES
P615_ALLOW_TAPE          EQU 1
P615_PROC1_FLAGS         EQU 13
P615_PROMPT_LEN          EQU 52

; C=STATOUT1 state, HL=PROC1 request. Resident commands leave ALLOW_TAPE clear.
; Tape-backed commands prompt before any authorization. Only y/Y sets the bit.
sh_p615_authorize_tape:
    push hl
    pop ix
    ld a,(ix+P615_PROC1_FLAGS)
    and $fe
    ld (ix+P615_PROC1_FLAGS),a
    ld a,c
    cp STATE_TAPE_BACKED
    jr z,sh_p615_need_tape
    xor a
    ret

sh_p615_need_tape:
    ld hl,p615_prompt
    ld bc,P615_PROMPT_LEN
    ld a,SYS_CON_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld de,0
    ld hl,p615_reply
    ld bc,1
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,sh_p615_decline
    ld a,l
    cp 1
    jr nz,sh_p615_decline
    ld a,(p615_reply)
    cp 'y'
    jr z,sh_p615_accept
    cp 'Y'
    jr nz,sh_p615_decline
sh_p615_accept:
    ld a,(ix+P615_PROC1_FLAGS)
    or P615_ALLOW_TAPE
    ld (ix+P615_PROC1_FLAGS),a
    xor a
    ret
sh_p615_decline:
    ld a,E_AGAIN
    scf
    ret

p615_prompt:
    db 'c','a','s','s','e','t','t','e',' ','r','e','q','u','i','r','e','d',';',' '
    db 'p','o','s','i','t','i','o','n',' ','t','a','p','e','/','P','L','A','Y'
    db ',',' ','t','h','e','n',' ','p','r','e','s','s',' ','y',':',' '
p615_reply: db 0
    ENDM
