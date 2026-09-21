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
