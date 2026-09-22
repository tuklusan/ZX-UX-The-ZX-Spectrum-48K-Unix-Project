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
; /bin/ls. Exact case-sensitive SYS_LIST consumer. Default path is ".".
; Normal format: NAME TAB TYPE LF.
; Long format: NAME TAB TYPE TAB logical TAB state [TAB physical TAB savings] LF.
; Physical/savings fields are present only for PACKED RAM objects and are obtained
; from SYS_STAT so LISTOUT1 remains the canonical enumeration ABI.

    MACRO EMIT_P801_LS_ROUTINES
ls_entry:
    push hl
    pop ix
    ld a,(ix+4)
    cp 1
    jr z,ls_default
    cp 2
    jr z,ls_two
    cp 3
    jr z,ls_three
    jp ls_invalid

ls_default:
    xor a
    ld (ls_long),a
    ld hl,ls_dot
    ld (ls_path),hl
    jp ls_begin

ls_two:
    call ls_argv1
    ld de,ls_long_opt
    call ls_streq
    jr z,ls_two_long
    xor a
    ld (ls_long),a
    ld (ls_path),hl
    jp ls_begin
ls_two_long:
    ld a,1
    ld (ls_long),a
    ld hl,ls_dot
    ld (ls_path),hl
    jp ls_begin

ls_three:
    call ls_argv1
    ld de,ls_long_opt
    call ls_streq
    jp nz,ls_invalid
    call ls_next_arg
    ld (ls_path),hl
    ld a,1
    ld (ls_long),a

ls_begin:
    xor a
    ld (ls_index),a
ls_loop:
    ld hl,(ls_path)
    ld (ls_list_req),hl
    ld a,(ls_index)
    ld (ls_list_req+2),a
    xor a
    ld (ls_list_req+3),a
    ld hl,ls_list_out
    ld (ls_list_req+4),hl
    ld hl,ls_list_req
    ld a,SYS_LIST
    call SYSCALL_GATEWAY
    jp c,ls_fail
    ld a,h
    or l
    jr z,ls_ok
    call ls_print_entry
    jp c,ls_fail
    ld a,(ls_index)
    inc a
    jr z,ls_ok
    ld (ls_index),a
    jr ls_loop

ls_print_entry:
    ld hl,ls_list_out
    ld bc,0
ls_name_count:
    ld a,c
    cp 10
    jr z,ls_name_ready
    ld a,(hl)
    or a
    jr z,ls_name_ready
    inc hl
    inc c
    jr ls_name_count
ls_name_ready:
    ld hl,ls_list_out
    call ls_write
    ret c
    ld hl,ls_tab
    ld bc,1
    call ls_write
    ret c
    ld a,(ls_list_out+10)
    call ls_type_text
    ret c
    ld a,(ls_long)
    or a
    jr z,ls_emit_lf

    ld hl,ls_tab
    ld bc,1
    call ls_write
    ret c
    ld hl,(ls_list_out+12)
    call ls_write_u16
    ret c
    ld hl,ls_tab
    ld bc,1
    call ls_write
    ret c
    ld a,(ls_list_out+14)
    call ls_state_text
    ret c

    ld a,(ls_list_out+14)
    cp STATE_RAM
    jr nz,ls_emit_lf
    ld a,(ls_list_out+11)
    and OBJ_PACKED
    jr z,ls_emit_lf

    ; Long packed details are fetched from STATOUT1, not inferred from LISTOUT1.
    call ls_build_stat_path
    ld hl,ls_stat_path
    ld (ls_stat_req),hl
    ld hl,ls_stat_out
    ld (ls_stat_req+2),hl
    ld hl,ls_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    ret c
    ld hl,ls_tab
    ld bc,1
    call ls_write
    ret c
    ld hl,(ls_stat_out+4)
    call ls_write_u16
    ret c
    ld hl,ls_tab
    ld bc,1
    call ls_write
    ret c
    ld hl,(ls_stat_out+2)
    ld de,(ls_stat_out+4)
    or a
    sbc hl,de
    call ls_write_u16
    ret c

ls_emit_lf:
    ld hl,ls_lf
    ld bc,1
    jp ls_write

ls_build_stat_path:
    ld hl,(ls_path)
    ld a,(hl)
    cp '.'
    jr nz,ls_copy_dir
    inc hl
    ld a,(hl)
    or a
    jr nz,ls_copy_dir
    ld hl,ls_list_out
    ld de,ls_stat_path
    jr ls_copy_name

ls_copy_dir:
    ld de,ls_stat_path
ls_copy_dir_loop:
    ld a,(hl)
    or a
    jr z,ls_copy_dir_done
    ld (de),a
    inc hl
    inc de
    jr ls_copy_dir_loop
ls_copy_dir_done:
    ld a,(ls_stat_path)
    cp '/'
    jr nz,ls_add_slash
    ld hl,(ls_path)
ls_find_dir_end:
    ld a,(hl)
    or a
    jr z,ls_dir_end_found
    inc hl
    jr ls_find_dir_end
ls_dir_end_found:
    dec hl
    ld a,(hl)
    cp '/'
    jr z,ls_after_slash
ls_add_slash:
    ld a,'/'
    ld (de),a
    inc de
ls_after_slash:
    ld hl,ls_list_out
ls_copy_name:
    ld b,10
ls_copy_name_loop:
    ld a,(hl)
    or a
    jr z,ls_copy_name_done
    ld (de),a
    inc hl
    inc de
    djnz ls_copy_name_loop
ls_copy_name_done:
    xor a
    ld (de),a
    ret

ls_type_text:
    dec a
    cp 13
    jr nc,ls_invalid_ret
    add a,a
    ld e,a
    ld d,0
    ld hl,ls_type_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp ls_write_z

ls_state_text:
    cp 4
    jr nc,ls_invalid_ret
    add a,a
    ld e,a
    ld d,0
    ld hl,ls_state_table
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    jp ls_write_z

ls_write_z:
    push hl
    ld bc,0
ls_write_z_count:
    ld a,(hl)
    or a
    jr z,ls_write_z_go
    inc hl
    inc bc
    jr ls_write_z_count
ls_write_z_go:
    pop hl
ls_write:
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret

; HL unsigned 16-bit -> decimal on stdout, no leading zeroes.
ls_write_u16:
    push hl
    ld de,ls_num_buf+5
    xor a
    ld (de),a
    pop hl
    ld b,0
ls_u16_loop:
    ld a,h
    or l
    jr z,ls_u16_done
    ld bc,10
    call ls_div16_10
    add a,'0'
    dec de
    ld (de),a
    inc b
    jr ls_u16_loop
ls_u16_done:
    ld a,b
    or a
    jr nz,ls_u16_emit
    dec de
    ld a,'0'
    ld (de),a
    ld b,1
ls_u16_emit:
    push de
    pop hl
    ld c,b
    ld b,0
    jp ls_write

; HL / 10 -> HL quotient, A remainder.
ls_div16_10:
    ld de,0
    ld b,16
ls_div16_loop:
    add hl,hl
    rl e
    rl d
    ld a,e
    sub 10
    jr c,ls_div16_no_sub
    ld e,a
    inc l
ls_div16_no_sub:
    djnz ls_div16_loop
    ld a,e
    ret

ls_argv1:
    push ix
    pop hl
    ld de,8
    add hl,de
    call ls_next_arg
    ret

; HL -> current NUL string; return HL -> next string.
ls_next_arg:
    ld a,(hl)
    inc hl
    or a
    jr nz,ls_next_arg
    ret

; HL,DE -> NUL strings. Z equal, NZ unequal. HL restored to first string.
ls_streq:
    push hl
ls_streq_loop:
    ld a,(de)
    cp (hl)
    jr nz,ls_streq_ne
    or a
    jr z,ls_streq_eq
    inc hl
    inc de
    jr ls_streq_loop
ls_streq_ne:
    pop hl
    ld a,1
    or a
    ret
ls_streq_eq:
    pop hl
    xor a
    ret

ls_invalid_ret:
    ld a,E_INVAL
    scf
    ret
ls_invalid:
    ld a,E_INVAL
ls_fail:
    ld l,a
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret
ls_ok:
    ld l,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

ls_dot: db '.',0
ls_long_opt: db '-','l',0
ls_tab: db 9
ls_lf: db 10
ls_type_txt: db 'T','X','T',0
ls_type_bin: db 'B','I','N',0
ls_type_obj: db 'O','B','J',0
ls_type_asm: db 'A','S','M',0
ls_type_c: db 'C',0
ls_type_dat: db 'D','A','T',0
ls_type_udg: db 'U','D','G',0
ls_type_gfx: db 'G','F','X',0
ls_type_fnt: db 'F','N','T',0
ls_type_cfg: db 'C','F','G',0
ls_type_sys: db 'S','Y','S',0
ls_type_dir: db 'D','I','R',0
ls_type_dev: db 'D','E','V',0
ls_type_table:
    dw ls_type_txt,ls_type_bin,ls_type_obj,ls_type_asm,ls_type_c,ls_type_dat,ls_type_udg
    dw ls_type_gfx,ls_type_fnt,ls_type_cfg,ls_type_sys,ls_type_dir,ls_type_dev
ls_state_ram: db 'R','A','M',0
ls_state_tape: db 'T','A','P','E','_','B','A','C','K','E','D',0
ls_state_pinned: db 'P','I','N','N','E','D','_','S','Y','S','T','E','M',0
ls_state_pseudo: db 'P','S','E','U','D','O',0
ls_state_table: dw ls_state_ram,ls_state_tape,ls_state_pinned,ls_state_pseudo

ls_long: db 0
ls_index: db 0
ls_path: dw 0
ls_list_req: defs 6,0
ls_list_out: defs 16,0
ls_stat_req: defs 4,0
ls_stat_out: defs 10,0
ls_stat_path: defs 32,0
ls_num_buf: defs 6,0
    ENDM
