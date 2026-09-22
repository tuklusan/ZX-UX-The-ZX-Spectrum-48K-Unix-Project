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
; /bin/which: exact-case external PATH lookup using the frozen shell P6.14
; algorithm. Parent-shell builtin names are never reported as external.
;
    INCLUDE "../src/shell/sh.asm"

    MACRO EMIT_P816_WHICH_ROUTINES
which_entry:
    ld (which_env),de
    push hl
    pop ix
    ld a,(ix+4)
    cp 2
    jp nz,which_invalid
    ld de,8
    add ix,de
which_skip_argv0:
    ld a,(ix+0)
    inc ix
    or a
    jr nz,which_skip_argv0
    push ix
    pop hl
    ld (which_name),hl
    call which_is_builtin
    jr c,which_not_found

    call which_find_path
    ld hl,(which_name)
    ld de,which_resolved
    call sh_p614_lookup_external
    jr c,which_not_found

    ld hl,which_resolved
    ld b,0
which_count_result:
    ld a,(hl)
    or a
    jr z,which_result_end
    inc hl
    inc b
    jr which_count_result
which_result_end:
    ld (hl),10
    inc b
    ld c,b
    ld b,0
    ld hl,which_resolved
    call which_write_all
    jr c,which_error
    ld l,0
    jr which_exit

which_invalid:
    ld a,E_INVAL
    jr which_error
which_not_found:
    ld l,1
    jr which_exit
which_error:
    ld l,a
which_exit:
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

; Return carry for any exact parent-shell builtin name.
which_is_builtin:
    ld hl,(which_name)
    ld b,0
which_name_count:
    ld a,(hl)
    or a
    jr z,which_name_count_done
    inc b
    inc hl
    jr which_name_count
which_name_count_done:
    ld hl,which_builtin_table
which_builtin_next:
    ld a,(hl)
    or a
    jr z,which_not_builtin
    ld c,a
    inc hl
    ld a,b
    cp c
    jr nz,which_builtin_skip
    push hl
    push bc
    ld de,(which_name)
which_builtin_cmp:
    ld a,(de)
    cp (hl)
    jr nz,which_builtin_cmp_miss
    inc de
    inc hl
    dec c
    jr nz,which_builtin_cmp
    pop bc
    pop hl
    scf
    ret
which_builtin_cmp_miss:
    pop bc
    pop hl
which_builtin_skip:
    ld e,c
    ld d,0
    add hl,de
    jr which_builtin_next
which_not_builtin:
    or a
    ret

; Locate exact PATH= entry in canonical ENV1. IX=0 means unset/missing.
which_find_path:
    ld hl,(which_env)
    ld de,8
    add hl,de
    ld de,(which_env)
    ex de,hl
    ; DE now entries start, HL env base.
    ld bc,4
    add hl,bc
    ld a,(hl)
    ld b,a
    ex de,hl
which_env_next:
    ld a,b
    or a
    jr z,which_path_missing
    push bc
    push hl
    ld de,which_path_key
    ld c,5
which_path_cmp:
    ld a,(de)
    cp (hl)
    jr nz,which_path_miss
    inc de
    inc hl
    dec c
    jr nz,which_path_cmp
    pop de
    pop bc
    ex de,hl
    ld de,5
    add hl,de
    push hl
    pop ix
    ret
which_path_miss:
    pop hl
    pop bc
which_env_skip:
    ld a,(hl)
    inc hl
    or a
    jr nz,which_env_skip
    djnz which_env_next
which_path_missing:
    ld ix,0
    ret

which_write_all:
    ld (which_write_ptr),hl
    ld (which_write_left),bc
which_write_loop:
    ld hl,(which_write_ptr)
    ld bc,(which_write_left)
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or l
    jr z,which_write_zero
    ld (which_written),hl
    ld de,(which_write_ptr)
    add hl,de
    ld (which_write_ptr),hl
    ld hl,(which_write_left)
    ld de,(which_written)
    or a
    sbc hl,de
    jr c,which_write_zero
    ld (which_write_left),hl
    ld a,h
    or l
    jr nz,which_write_loop
    xor a
    ret
which_write_zero:
    ld a,E_IO
    scf
    ret

which_path_key: db 'P','A','T','H','='
which_builtin_table:
    db 2,'c','d'
    db 3,'p','w','d'
    db 3,'s','e','t'
    db 5,'u','n','s','e','t'
    db 4,'j','o','b','s'
    db 4,'w','a','i','t'
    db 4,'k','i','l','l'
    db 3,'m','e','m'
    db 2,'p','s'
    db 5,'c','l','e','a','r'
    db 4,'s','a','v','e'
    db 4,'l','o','a','d'
    db 6,'v','e','r','i','f','y'
    db 4,'t','a','p','e'
    db 4,'e','x','i','t'
    db 4,'c','a','l','c'
    db 4,'b','e','e','p'
    db 4,'p','l','o','t'
    db 4,'l','i','n','e'
    db 6,'c','i','r','c','l','e'
    db 5,'p','o','i','n','t'
    db 3,'i','n','k'
    db 5,'p','a','p','e','r'
    db 6,'b','r','i','g','h','t'
    db 5,'f','l','a','s','h'
    db 7,'i','n','v','e','r','s','e'
    db 4,'o','v','e','r'
    db 6,'b','o','r','d','e','r'
    db 3,'r','o','m'
    db 0

which_env: dw 0
which_name: dw 0
which_write_ptr: dw 0
which_write_left: dw 0
which_written: dw 0
which_resolved: defs 32,0

    EMIT_P614_PATH_ROUTINES
which_end:
    ENDM
