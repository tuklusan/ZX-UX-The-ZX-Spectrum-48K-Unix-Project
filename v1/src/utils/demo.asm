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
; /bin/demo: exact-case demo discovery/runner. Missing pair members are loaded
; explicitly; resident expected-type members are preserved and never overwritten.

; P8.36 exact qualification source; resident pair members are preserved.
; P8.36 qualification retry anchor.
    MACRO EMIT_P836_DEMO_ROUTINES
DEMO_STAT_TYPE      EQU 0
DEMO_PROC_PATH      EQU 0
DEMO_PROC_ARG       EQU 2
DEMO_PROC_ARGLEN    EQU 4
DEMO_PROC_ENV       EQU 6
DEMO_PROC_ENVLEN    EQU 8
DEMO_PROC_STDIN     EQU 10
DEMO_PROC_STDOUT    EQU 11
DEMO_PROC_STDERR    EQU 12
DEMO_PROC_FLAGS     EQU 13
DEMO_PROC_RESERVED  EQU 14
DEMO_PROC_SIZE      EQU 16

demo_entry:
    ld (demo_env),de
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jp z,demo_list
    cp 2
    jp nz,demo_bad

    ld de,8
    add ix,de
demo_skip0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,demo_skip0
    push ix
    pop hl
    ld (demo_arg),hl

    xor a
    ld (demo_index),a
demo_find:
    ld a,(demo_index)
    cp DEMO_COUNT
    jp z,demo_noent
    add a,a
    ld e,a
    ld d,0
    ld hl,demo_exec_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld de,(demo_arg)
    call demo_streq
    jr z,demo_found
    ld a,(demo_index)
    inc a
    ld (demo_index),a
    jr demo_find

demo_found:
    ld a,(demo_index)
    add a,a
    ld e,a
    ld d,0
    ld hl,demo_exec_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld de,demo_exec_name
    call demo_copy_z

    ld a,(demo_index)
    add a,a
    ld e,a
    ld d,0
    ld hl,demo_source_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ld de,demo_source_name
    call demo_copy_z

    ld hl,demo_source_name
    ld b,OBJ_C
    call demo_ensure
    jp c,demo_exit_a
    ld hl,demo_exec_name
    ld b,OBJ_BIN
    call demo_ensure
    jp c,demo_exit_a

    call demo_print_hint
    jp c,demo_exit_a
    call demo_spawn_wait
    jp c,demo_exit_a
    ld a,(demo_child_status)
    jp demo_exit_a

demo_list:
    ld hl,demo_list_text
    ld bc,demo_list_end-demo_list_text
    call demo_write_all
    jp c,demo_exit_a
    xor a
    jp demo_exit_a

demo_bad:
    ld a,E_INVAL
    jp demo_exit_a
demo_noent:
    ld a,E_NOENT
demo_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

; HL=path, B=required type. Carry/error on wrong type or failed explicit load.
demo_ensure:
    ld a,b
    ld (demo_req_type),a
    ld (demo_path),hl
    call demo_stat
    jr nc,demo_ensure_have
    cp E_NOENT
    ret nz
    ld hl,(demo_path)
    ld a,SYS_TAPE_LOAD
    call SYSCALL_GATEWAY
    ret c
    ld hl,(demo_path)
    call demo_stat
    ret c
demo_ensure_have:
    ld a,(demo_statout+DEMO_STAT_TYPE)
    ld b,a
    ld a,(demo_req_type)
    cp b
    jr z,demo_ensure_ok
    ld hl,demo_wrong_type
    ld bc,demo_wrong_type_end-demo_wrong_type
    call demo_write_all
    ld a,E_FORMAT
    scf
    ret
demo_ensure_ok:
    xor a
    ret

demo_stat:
    ld (demo_stat_req+0),hl
    ld de,demo_statout
    ld (demo_stat_req+2),de
    ld hl,demo_stat_req
    ld a,SYS_STAT
    jp SYSCALL_GATEWAY

demo_spawn_wait:
    ld hl,demo_exec_name
    ld (demo_proc+DEMO_PROC_PATH),hl

    ld hl,demo_child_arg
    ld (demo_proc+DEMO_PROC_ARG),hl
    ld a,(demo_exec_name)
    ld hl,demo_child_arg+8
    ld de,demo_exec_name
    ld b,0
demo_arg_copy:
    ld a,(de)
    ld (hl),a
    inc de
    inc hl
    inc b
    or a
    jr nz,demo_arg_copy
    ld a,b
    add a,8
    ld l,a
    ld h,0
    ld (demo_child_arg+6),hl
    ld (demo_proc+DEMO_PROC_ARGLEN),hl

    ld hl,(demo_env)
    ld (demo_proc+DEMO_PROC_ENV),hl
    push hl
    ld de,6
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    pop hl
    ld (demo_proc+DEMO_PROC_ENVLEN),de

    xor a
    ld (demo_proc+DEMO_PROC_STDIN),a
    inc a
    ld (demo_proc+DEMO_PROC_STDOUT),a
    inc a
    ld (demo_proc+DEMO_PROC_STDERR),a
    xor a
    ld (demo_proc+DEMO_PROC_FLAGS),a
    ld (demo_proc+DEMO_PROC_RESERVED),a
    ld (demo_proc+DEMO_PROC_RESERVED+1),a

    ld hl,demo_proc
    ld a,SYS_SPAWN
    call SYSCALL_GATEWAY
    ret c
    ld a,l
    ld (demo_wait_req),a
    xor a
    ld (demo_wait_req+1),a
    ld hl,demo_child_status
    ld (demo_wait_req+2),hl
    ld hl,demo_wait_req
    ld a,SYS_WAIT
    jp SYSCALL_GATEWAY

demo_print_hint:
    ld hl,demo_hint1
    ld bc,demo_hint1_end-demo_hint1
    call demo_write_all
    ret c
    ld hl,demo_source_name
    call demo_write_z
    ret c
    ld hl,demo_hint2
    ld bc,demo_hint2_end-demo_hint2
    call demo_write_all
    ret c
    ld hl,demo_exec_name
    call demo_write_z
    ret c
    ld hl,demo_hint3
    ld bc,demo_hint3_end-demo_hint3
    jp demo_write_all

demo_streq:
    ld a,(de)
    cp (hl)
    ret nz
    or a
    ret z
    inc de
    inc hl
    jr demo_streq

demo_copy_z:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jr nz,demo_copy_z
    ret

demo_write_z:
    push hl
    ld bc,0
demo_wz_count:
    ld a,(hl)
    or a
    jr z,demo_wz_ready
    inc hl
    inc bc
    jr demo_wz_count
demo_wz_ready:
    pop hl
demo_write_all:
    ld (demo_wptr),hl
    ld (demo_wleft),bc
demo_write_loop:
    ld hl,(demo_wptr)
    ld bc,(demo_wleft)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,demo_io
    ld (demo_wrote),hl
    ld de,(demo_wptr)
    add hl,de
    ld (demo_wptr),hl
    ld hl,(demo_wleft)
    ld de,(demo_wrote)
    or a
    sbc hl,de
    jr c,demo_io
    ld (demo_wleft),hl
    ld a,h
    or l
    jr nz,demo_write_loop
    xor a
    ret
demo_io:
    ld a,E_IO
    scf
    ret

DEMO_COUNT EQU 13
demo_exec_table:
    dw demo_n0,demo_n1,demo_n2,demo_n3,demo_n4,demo_n5,demo_n6
    dw demo_n7,demo_n8,demo_n9,demo_n10,demo_n11,demo_n12
demo_source_table:
    dw demo_s0,demo_s1,demo_s2,demo_s3,demo_s4,demo_s5,demo_s6
    dw demo_s7,demo_s8,demo_s9,demo_s10,demo_s11,demo_s12
demo_n0: db 'h','e','l','l','o',0
demo_s0: db 'h','e','l','l','o','.','c',0
demo_n1: db 'c','o','l','o','r','s',0
demo_s1: db 'c','o','l','o','r','s','.','c',0
demo_n2: db 'l','i','n','e','s',0
demo_s2: db 'l','i','n','e','s','.','c',0
demo_n3: db 's','h','i','p',0
demo_s3: db 's','h','i','p','.','c',0
demo_n4: db 'b','a','l','l',0
demo_s4: db 'b','a','l','l','.','c',0
demo_n5: db 's','t','a','r','s',0
demo_s5: db 's','t','a','r','s','.','c',0
demo_n6: db 'l','i','f','e',0
demo_s6: db 'l','i','f','e','.','c',0
demo_n7: db 'm','a','z','e',0
demo_s7: db 'm','a','z','e','.','c',0
demo_n8: db 's','i','n','e',0
demo_s8: db 's','i','n','e','.','c',0
demo_n9: db 'm','a','n','d','e','l',0
demo_s9: db 'm','a','n','d','e','l','.','c',0
demo_n10: db 't','u','n','e',0
demo_s10: db 't','u','n','e','.','c',0
demo_n11: db 'p','i','p','e',0
demo_s11: db 'p','i','p','e','.','c',0
demo_n12: db 'm','u','l','t','i',0
demo_s12: db 'm','u','l','t','i','.','c',0

demo_list_text:
    db 'h','e','l','l','o',' ','h','e','l','l','o','.','c',10
    db 'c','o','l','o','r','s',' ','c','o','l','o','r','s','.','c',10
    db 'l','i','n','e','s',' ','l','i','n','e','s','.','c',10
    db 's','h','i','p',' ','s','h','i','p','.','c',10
    db 'b','a','l','l',' ','b','a','l','l','.','c',10
    db 's','t','a','r','s',' ','s','t','a','r','s','.','c',10
    db 'l','i','f','e',' ','l','i','f','e','.','c',10
    db 'm','a','z','e',' ','m','a','z','e','.','c',10
    db 's','i','n','e',' ','s','i','n','e','.','c',10
    db 'm','a','n','d','e','l',' ','m','a','n','d','e','l','.','c',10
    db 't','u','n','e',' ','t','u','n','e','.','c',10
    db 'p','i','p','e',' ','p','i','p','e','.','c',10
    db 'm','u','l','t','i',' ','m','u','l','t','i','.','c',10
demo_list_end:

demo_hint1: db 'E','d','i','t','/','r','e','b','u','i','l','d',':',' ','v','i',' '
demo_hint1_end:
demo_hint2: db ' ',';',' ','r','u','n',' '
demo_hint2_end:
demo_hint3: db 10
demo_hint3_end:
demo_wrong_type: db 'd','e','m','o',':',' ','w','r','o','n','g',' ','t','y','p','e',10
demo_wrong_type_end:

demo_env: dw 0
demo_arg: dw 0
demo_path: dw 0
demo_req_type: db 0
demo_index: db 0
demo_exec_name: defs 16,0
demo_source_name: defs 16,0
demo_stat_req: defs 4,0
demo_statout: defs 10,0
demo_proc: defs DEMO_PROC_SIZE,0
demo_wait_req: defs 4,0
demo_child_status: db 0
demo_child_arg: db 'A','R','G','1',1,0,0,0
                defs 16,0
demo_wptr: dw 0
demo_wleft: dw 0
demo_wrote: dw 0
    ENDM
