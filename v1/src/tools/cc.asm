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
; Native C48 compiler. Phase 11 grows this file monotonically.
; P11.02 freezes the bounded streaming architecture.
;
; Pinned SDK reference decomposition:
; compiler/c48/preprocessor.py -> bounded source-window front end
; compiler/c48/lexer.py        -> streaming lexical stage
; compiler/c48/parser.py       -> recursive-descent parser
; compiler/c48/typesys.py      -> compact target type descriptors
; compiler/c48/semantics.py    -> incremental semantic checks
; compiler/c48/limits.py       -> deterministic resource failures
; compiler/c48/errors.py       -> deterministic diagnostics
; compiler/c48/float5.py       -> numeric behavior oracle
; compiler/c48/memory.py       -> host model only, not copied as target storage
; compiler/c48/vm.py           -> host runtime oracle only
;
; The Z80 target deliberately does not copy the host Python object graph.
; Source is consumed in <=64-byte windows, statements are emitted incrementally,
; expression state is bounded and released, and no whole-source/whole-program AST
; allocation exists.

    MACRO EMIT_P11_CC_STREAMING_CORE
CC_IDENT_MAX             EQU 15
CC_NAME_FIELD            EQU 16
CC_SYMBOL_ENTRY_SIZE     EQU 18
CC_GLOBAL_CAPACITY       EQU 32
CC_LOCAL_CAPACITY        EQU 32
CC_LABEL_CAPACITY        EQU 32
CC_EXPR_NODE_SIZE        EQU 4
CC_EXPR_CAPACITY         EQU 8
CC_SOURCE_WINDOW_SIZE    EQU 64
CC_WORKSPACE_LIMIT       EQU 2048

CC_STAGE_RESET           EQU 0
CC_STAGE_LEX             EQU 1
CC_STAGE_PARSE           EQU 2
CC_STAGE_EMIT            EQU 3
CC_STAGE_OBJ1            EQU 4

cc_workspace_guard_pre:  db $A5
cc_workspace_begin:
cc_source_window:        defs CC_SOURCE_WINDOW_SIZE,0
cc_global_table:         defs CC_GLOBAL_CAPACITY*CC_SYMBOL_ENTRY_SIZE,0
cc_local_table:          defs CC_LOCAL_CAPACITY*CC_SYMBOL_ENTRY_SIZE,0
cc_label_table:          defs CC_LABEL_CAPACITY*CC_SYMBOL_ENTRY_SIZE,0
cc_expr_nodes:           defs CC_EXPR_CAPACITY*CC_EXPR_NODE_SIZE,0
cc_global_count:         db 0
cc_local_count:          db 0
cc_label_count:          db 0
cc_expr_depth:           db 0
cc_expr_highwater:       db 0
cc_pipeline_stage:       db 0
cc_stream_total:         dw 0
cc_output_commit_marker: db 0
cc_name_length:          db 0
cc_work_capacity:        db 0
cc_copy_zero:            db 0
cc_work_name:            dw 0
cc_work_value:           dw 0
cc_work_table:           dw 0
cc_work_count:           dw 0
cc_workspace_end:
cc_workspace_guard_post: db $5A

    ASSERT cc_workspace_end-cc_workspace_begin <= CC_WORKSPACE_LIMIT

cc_p1102_reset:
    xor a
    ld (cc_global_count),a
    ld (cc_local_count),a
    ld (cc_label_count),a
    ld (cc_expr_depth),a
    ld (cc_expr_highwater),a
    ld (cc_pipeline_stage),a
    ld (cc_stream_total),a
    ld (cc_stream_total+1),a
    ld (cc_output_commit_marker),a
    ret

; HL=source-window pointer, BC=window bytes. P11.03 and later consume the bytes;
; P11.02 freezes the bounded streaming window and stage contract.
cc_pipeline_feed:
    ld a,b
    or a
    jp nz,cc_p1102_nospc
    ld a,c
    cp CC_SOURCE_WINDOW_SIZE+1
    jp nc,cc_p1102_nospc
    ld hl,(cc_stream_total)
    add hl,bc
    jp c,cc_p1102_nospc
    ld (cc_stream_total),hl
    ld a,CC_STAGE_LEX
    ld (cc_pipeline_stage),a
    xor a
    ret

cc_pipeline_parse:
    ld a,(cc_pipeline_stage)
    cp CC_STAGE_LEX
    jp nz,cc_p1102_format
    ld a,CC_STAGE_PARSE
    ld (cc_pipeline_stage),a
    xor a
    ret

cc_pipeline_emit:
    ld a,(cc_pipeline_stage)
    cp CC_STAGE_PARSE
    jp nz,cc_p1102_format
    ld a,CC_STAGE_EMIT
    ld (cc_pipeline_stage),a
    xor a
    ret

cc_pipeline_obj1:
    ld a,(cc_pipeline_stage)
    cp CC_STAGE_EMIT
    jp nz,cc_p1102_format
    ld a,CC_STAGE_OBJ1
    ld (cc_pipeline_stage),a
    xor a
    ret

cc_expr_enter:
    ld a,(cc_expr_depth)
    cp CC_EXPR_CAPACITY
    jp nc,cc_p1102_nospc
    inc a
    ld (cc_expr_depth),a
    ld b,a
    ld a,(cc_expr_highwater)
    cp b
    jr nc,cc_expr_enter_ok
    ld a,b
    ld (cc_expr_highwater),a
cc_expr_enter_ok:
    xor a
    ret

cc_expr_leave:
    ld a,(cc_expr_depth)
    or a
    jp z,cc_p1102_format
    dec a
    ld (cc_expr_depth),a
    xor a
    ret

; Statement completion releases every bounded expression node immediately.
cc_statement_release:
    xor a
    ld (cc_expr_depth),a
    ret

; HL -> NUL-terminated C48 identifier.
cc_ident_validate:
    ld b,CC_NAME_FIELD
    ld c,0
cc_ident_loop:
    ld a,(hl)
    or a
    jr z,cc_ident_nul
    ld a,c
    cp CC_IDENT_MAX
    jp nc,cc_p1102_inval
    ld a,c
    or a
    ld a,(hl)
    jr nz,cc_ident_tail
    call cc_ident_first_char
    jp c,cc_p1102_inval
    jp cc_ident_accept
cc_ident_tail:
    call cc_ident_next_char
    jp c,cc_p1102_inval
cc_ident_accept:
    inc c
    inc hl
    djnz cc_ident_loop
    jp cc_p1102_inval
cc_ident_nul:
    ld a,c
    or a
    jp z,cc_p1102_inval
    ld a,c
    ld (cc_name_length),a
    xor a
    ret

cc_ident_first_char:
    cp 'A'
    jr c,cc_ident_first_under
    cp 'Z'+1
    jr c,cc_ident_char_ok
    cp 'a'
    jr c,cc_ident_first_under
    cp 'z'+1
    jr c,cc_ident_char_ok
cc_ident_first_under:
    cp '_'
    jr z,cc_ident_char_ok
    scf
    ret
cc_ident_next_char:
    cp '0'
    jr c,cc_ident_first_char
    cp '9'+1
    jr c,cc_ident_char_ok
    jp cc_ident_first_char
cc_ident_char_ok:
    or a
    ret

; HL=name, DE=value. Separate tables are deliberately fixed-capacity.
cc_global_insert:
    ld (cc_work_name),hl
    ld (cc_work_value),de
    ld hl,cc_global_table
    ld (cc_work_table),hl
    ld hl,cc_global_count
    ld (cc_work_count),hl
    ld a,CC_GLOBAL_CAPACITY
    ld (cc_work_capacity),a
    jp cc_table_insert

cc_local_insert:
    ld (cc_work_name),hl
    ld (cc_work_value),de
    ld hl,cc_local_table
    ld (cc_work_table),hl
    ld hl,cc_local_count
    ld (cc_work_count),hl
    ld a,CC_LOCAL_CAPACITY
    ld (cc_work_capacity),a
    jp cc_table_insert

cc_label_insert:
    ld (cc_work_name),hl
    ld (cc_work_value),de
    ld hl,cc_label_table
    ld (cc_work_table),hl
    ld hl,cc_label_count
    ld (cc_work_count),hl
    ld a,CC_LABEL_CAPACITY
    ld (cc_work_capacity),a
    jp cc_table_insert

cc_table_insert:
    ld hl,(cc_work_name)
    call cc_ident_validate
    ret c

    ld hl,(cc_work_count)
    ld a,(hl)
    ld b,a
    ld a,(cc_work_capacity)
    cp b
    jr z,cc_p1102_nospc
    jp c,cc_p1102_nospc

    ld hl,(cc_work_table)
    ld a,b
    or a
    jr z,cc_table_dest_ready
    ld b,a
    ld de,CC_SYMBOL_ENTRY_SIZE
cc_table_dest_loop:
    add hl,de
    djnz cc_table_dest_loop
cc_table_dest_ready:
    ex de,hl
    ld hl,(cc_work_name)
    xor a
    ld (cc_copy_zero),a
    ld b,CC_NAME_FIELD
cc_table_copy_loop:
    ld a,(cc_copy_zero)
    or a
    jr nz,cc_table_copy_zero
    ld a,(hl)
    inc hl
    ld (de),a
    or a
    jr nz,cc_table_copy_next
    ld a,1
    ld (cc_copy_zero),a
    jr cc_table_copy_next
cc_table_copy_zero:
    xor a
    ld (de),a
cc_table_copy_next:
    inc de
    djnz cc_table_copy_loop

    ld hl,(cc_work_value)
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a

    ld hl,(cc_work_count)
    inc (hl)
    xor a
    ret

cc_p1102_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_p1102_inval:
    ld a,E_INVAL
    scf
    ret
cc_p1102_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.03 Version-1 C48 preprocessor.
; Runs before lexical parsing. Local includes use cwd-relative ordinary reads;
; <c48.h> is compiler-resident and never loaded from tape/object storage.
    MACRO EMIT_P11_CC_PREPROCESSOR
CC_PP_MACRO_CAPACITY     EQU 16
CC_PP_REPLACEMENT_MAX   EQU 32
CC_PP_MACRO_ENTRY_SIZE  EQU 49
CC_PP_LOCAL_NAME_MAX    EQU 10
CC_PP_INCLUDE_CHUNK     EQU 64
CC_PP_FEATURE_FUNCTION  EQU 1
CC_PP_FEATURE_CONDITION EQU 2
CC_PP_FEATURE_PASTE     EQU 3
CC_PP_FEATURE_STRINGIFY EQU 4
CC_PP_FEATURE_RECURSIVE EQU 5

cc_pp_macro_table:      defs CC_PP_MACRO_CAPACITY*CC_PP_MACRO_ENTRY_SIZE,0
cc_pp_macro_count:      db 0
cc_pp_include_depth:    db 0
cc_pp_builtin_seen:     db 0
cc_pp_open:             db 0
cc_pp_handle:           db 0
cc_pp_errno:            db 0
cc_pp_work_flags:       db 0
cc_pp_work_len:         db 0
cc_pp_work_capacity:    db 0
cc_pp_local_len:        db 0
cc_pp_work_name:        dw 0
cc_pp_work_repl:        dw 0
cc_pp_work_dest:        dw 0
cc_pp_stat_req:         defs 4,0
cc_pp_stat_out:         defs 10,0
cc_pp_local_name:       defs CC_PP_LOCAL_NAME_MAX+1,0
cc_pp_lookup_name:      defs 16,0

; P11.41 freezes the complete public declarations. P11.03 freezes delivery.
cc_pp_builtin_header:
    db "int getpid(void);",10
    db "int getchar(void);",10
cc_pp_builtin_header_end:
CC_PP_BUILTIN_HEADER_SIZE EQU cc_pp_builtin_header_end-cc_pp_builtin_header
    ASSERT CC_PP_BUILTIN_HEADER_SIZE <= CC_SOURCE_WINDOW_SIZE
cc_pp_builtin_operand:   db "<c48.h>",0

cc_pp_reset:
    xor a
    ld (cc_pp_macro_count),a
    ld (cc_pp_include_depth),a
    ld (cc_pp_builtin_seen),a
    ld (cc_pp_open),a
    ret

; A=0 object-like; nonzero means a deferred preprocessing form.
; HL=name, DE=replacement bytes, C=length.
cc_pp_define_object:
    ld (cc_pp_work_flags),a
    ld (cc_pp_work_name),hl
    ld (cc_pp_work_repl),de
    ld a,c
    ld (cc_pp_work_len),a
    ld a,(cc_pp_work_flags)
    or a
    jp nz,cc_pp_notsup
    ld a,(cc_pp_work_len)
    or a
    jp z,cc_pp_format
    cp CC_PP_REPLACEMENT_MAX+1
    jp nc,cc_pp_toolong
    ld hl,(cc_pp_work_name)
    call cc_ident_validate
    ret c
    ld a,(cc_pp_macro_count)
    cp CC_PP_MACRO_CAPACITY
    jp nc,cc_pp_nospc
    ld b,a
    ld de,cc_pp_macro_table
    ld a,b
    or a
    jr z,cc_pp_define_dest_ready
cc_pp_define_dest_loop:
    ld hl,CC_PP_MACRO_ENTRY_SIZE
    add hl,de
    ex de,hl
    djnz cc_pp_define_dest_loop
cc_pp_define_dest_ready:
    push de
    ld hl,(cc_pp_work_name)
    call cc_pp_copy_name16
    pop de
    ld hl,16
    add hl,de
    ex de,hl
    ld a,(cc_pp_work_len)
    ld (de),a
    inc de
    ld hl,(cc_pp_work_repl)
    ld a,(cc_pp_work_len)
    ld b,a
cc_pp_define_repl_loop:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz cc_pp_define_repl_loop
    ld hl,cc_pp_macro_count
    inc (hl)
    xor a
    ret

; HL=name, DE=destination, C=capacity; success A=expanded byte count.
cc_pp_expand_ident:
    ld (cc_pp_work_name),hl
    ld (cc_pp_work_dest),de
    ld a,c
    ld (cc_pp_work_capacity),a
    call cc_ident_validate
    ret c
    ld hl,(cc_pp_work_name)
    ld de,cc_pp_lookup_name
    call cc_pp_copy_name16
    ld a,(cc_pp_macro_count)
    or a
    jp z,cc_pp_noent
    ld b,a
    ld de,cc_pp_macro_table
cc_pp_find_loop:
    push bc
    push de
    ld hl,cc_pp_lookup_name
    ld c,16
cc_pp_find_cmp:
    ld a,(de)
    cp (hl)
    jr nz,cc_pp_find_miss
    inc de
    inc hl
    dec c
    jr nz,cc_pp_find_cmp
    pop de
    pop bc
    ld hl,16
    add hl,de
    ld a,(hl)
    ld c,a
    ld a,(cc_pp_work_capacity)
    cp c
    jp c,cc_pp_nospc
    inc hl
    ld de,(cc_pp_work_dest)
    ld a,c
    or a
    jr z,cc_pp_expand_done
    ld b,a
cc_pp_expand_copy:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz cc_pp_expand_copy
cc_pp_expand_done:
    ld a,c
    or a
    ret
cc_pp_find_miss:
    pop de
    pop bc
    ld hl,CC_PP_MACRO_ENTRY_SIZE
    add hl,de
    ex de,hl
    djnz cc_pp_find_loop
    jp cc_pp_noent

cc_pp_copy_name16:
    xor a
    ld (cc_copy_zero),a
    ld b,16
cc_pp_copy_name_loop:
    ld a,(cc_copy_zero)
    or a
    jr nz,cc_pp_copy_name_zero
    ld a,(hl)
    inc hl
    ld (de),a
    or a
    jr nz,cc_pp_copy_name_next
    ld a,1
    ld (cc_copy_zero),a
    jr cc_pp_copy_name_next
cc_pp_copy_name_zero:
    xor a
    ld (de),a
cc_pp_copy_name_next:
    inc de
    djnz cc_pp_copy_name_loop
    ret

; HL -> exact operand: <c48.h> or "portable-basename".
cc_pp_include_operand:
    ld a,(hl)
    cp '<'
    jr z,cc_pp_include_angle
    cp '"'
    jp nz,cc_pp_format
    inc hl
    ld de,cc_pp_local_name
    xor a
    ld (cc_pp_local_len),a
cc_pp_quote_loop:
    ld a,(hl)
    or a
    jp z,cc_pp_format
    cp '"'
    jr z,cc_pp_quote_done
    call cc_pp_portable_char
    jp c,cc_pp_inval
    ld a,(cc_pp_local_len)
    cp CC_PP_LOCAL_NAME_MAX
    jp nc,cc_pp_toolong
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    ld a,(cc_pp_local_len)
    inc a
    ld (cc_pp_local_len),a
    jr cc_pp_quote_loop
cc_pp_quote_done:
    inc hl
    ld a,(hl)
    or a
    jp nz,cc_pp_format
    xor a
    ld (de),a
    ld a,(cc_pp_local_len)
    or a
    jp z,cc_pp_inval
    cp 1
    jr nz,cc_pp_quote_check_dotdot
    ld a,(cc_pp_local_name)
    cp '.'
    jp z,cc_pp_inval
    jr cc_pp_quote_ready
cc_pp_quote_check_dotdot:
    cp 2
    jr nz,cc_pp_quote_ready
    ld a,(cc_pp_local_name)
    cp '.'
    jr nz,cc_pp_quote_ready
    ld a,(cc_pp_local_name+1)
    cp '.'
    jp z,cc_pp_inval
cc_pp_quote_ready:
    ld hl,cc_pp_local_name
    jp cc_pp_include_local

cc_pp_include_angle:
    ld de,cc_pp_builtin_operand
    call cc_pp_streq
    jp nz,cc_pp_notsup
    jp cc_pp_include_builtin

cc_pp_include_builtin:
    ld a,(cc_pp_builtin_seen)
    or a
    ret nz
    ld a,1
    ld (cc_pp_builtin_seen),a
    ld hl,cc_pp_builtin_header
    ld bc,CC_PP_BUILTIN_HEADER_SIZE
    call cc_pipeline_feed
    ret

; Local C/TXT include: current cwd basename, streamed in <=64-byte reads.
; No whole include object is materialized.
cc_pp_include_local:
    ld a,(cc_pp_include_depth)
    or a
    jp nz,cc_pp_notsup
    ld (cc_pp_stat_req),hl
    ld de,cc_pp_stat_out
    ld (cc_pp_stat_req+2),de
    ld hl,cc_pp_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    ret c
    ld a,(cc_pp_stat_out)
    cp OBJ_C
    jr z,cc_pp_local_type_ok
    cp OBJ_TXT
    jp nz,cc_pp_format
cc_pp_local_type_ok:
    ld a,1
    ld (cc_pp_include_depth),a
    ld hl,(cc_pp_stat_req)
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp c,cc_pp_local_open_fail
    ld a,h
    or a
    jp nz,cc_pp_local_bad_handle
    ld a,l
    ld (cc_pp_handle),a
    ld a,1
    ld (cc_pp_open),a
cc_pp_local_read:
    ld a,(cc_pp_handle)
    ld e,a
    ld d,0
    ld hl,cc_source_window
    ld bc,CC_PP_INCLUDE_CHUNK
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jp c,cc_pp_stream_error
    ld a,h
    or l
    jr z,cc_pp_local_eof
    ld b,h
    ld c,l
    ld hl,cc_source_window
    call cc_pipeline_feed
    jp c,cc_pp_stream_error
    jr cc_pp_local_read
cc_pp_local_eof:
    call cc_pp_close
    jp c,cc_pp_local_close_fail
    xor a
    ld (cc_pp_include_depth),a
    ret
cc_pp_local_open_fail:
    ld (cc_pp_errno),a
    xor a
    ld (cc_pp_include_depth),a
    ld a,(cc_pp_errno)
    scf
    ret
cc_pp_local_bad_handle:
    ld a,E_FORMAT
    jp cc_pp_stream_error
cc_pp_stream_error:
    ld (cc_pp_errno),a
    call cc_pp_close
    xor a
    ld (cc_pp_include_depth),a
    ld a,(cc_pp_errno)
    scf
    ret
cc_pp_local_close_fail:
    ld (cc_pp_errno),a
    xor a
    ld (cc_pp_include_depth),a
    ld a,(cc_pp_errno)
    scf
    ret
cc_pp_close:
    ld a,(cc_pp_open)
    or a
    ret z
    ld a,(cc_pp_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret c
    xor a
    ld (cc_pp_open),a
    ret

cc_pp_reject_feature:
    cp CC_PP_FEATURE_FUNCTION
    jr z,cc_pp_notsup
    cp CC_PP_FEATURE_CONDITION
    jr z,cc_pp_notsup
    cp CC_PP_FEATURE_PASTE
    jr z,cc_pp_notsup
    cp CC_PP_FEATURE_STRINGIFY
    jr z,cc_pp_notsup
    cp CC_PP_FEATURE_RECURSIVE
    jr z,cc_pp_notsup
    jp cc_pp_format

cc_pp_portable_char:
    cp '0'
    jr c,cc_pp_portable_alpha
    cp '9'+1
    jr c,cc_pp_char_ok
cc_pp_portable_alpha:
    cp 'A'
    jr c,cc_pp_portable_misc
    cp 'Z'+1
    jr c,cc_pp_char_ok
    cp 'a'
    jr c,cc_pp_portable_misc
    cp 'z'+1
    jr c,cc_pp_char_ok
cc_pp_portable_misc:
    cp '.'
    jr z,cc_pp_char_ok
    cp '_'
    jr z,cc_pp_char_ok
    cp '-'
    jr z,cc_pp_char_ok
    scf
    ret
cc_pp_char_ok:
    or a
    ret

cc_pp_streq:
    ld a,(de)
    cp (hl)
    ret nz
    or a
    ret z
    inc de
    inc hl
    jr cc_pp_streq

cc_pp_noent:
    ld a,E_NOENT
    scf
    ret
cc_pp_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_pp_toolong:
    ld a,E_TOOLONG
    scf
    ret
cc_pp_notsup:
    ld a,E_NOTSUP
    scf
    ret
cc_pp_inval:
    ld a,E_INVAL
    scf
    ret
cc_pp_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM
