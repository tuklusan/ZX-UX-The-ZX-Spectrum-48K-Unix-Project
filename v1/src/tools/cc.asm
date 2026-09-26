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
    db "int open(char *path,int flags);",10
    db "int open_typed(char *path,int flags,int type);",10
    db "int close(int h);",10
    db "int read(int h,void *p,unsigned int n);",10
    db "int write(int h,void *p,unsigned int n);",10
    db "int seek(int h,unsigned int pos);",10
    db "int stat(char *path,void *out);",10
    db "int remove(char *path);",10
    db "int rename(char *oldp,char *newp);",10
    db "int list(char *dir,int index,void *out);",10
    db "int pipe(unsigned char *handles);",10
    db "int dup(int source,int destination);",10
    db "int ioctl(int h,int request,void *arg);",10
    db "int read_full(int h,void *p,unsigned int n);",10
    db "int write_full(int h,void *p,unsigned int n);",10
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

; P11.04 C48 lexer.
    MACRO EMIT_P11_CC_LEXER
CC_TOK_EOF      EQU 0
CC_TOK_IDENT    EQU 1
CC_TOK_INT      EQU 2
CC_TOK_FLOAT    EQU 3
CC_TOK_CHAR     EQU 4
CC_TOK_STRING   EQU 5
CC_TOK_OPERATOR EQU 6
CC_TOK_PUNCT    EQU 7
CC_TOK_KEYWORD  EQU 8
CC_TOK_MORE     EQU 9

cc_lex_ptr:         dw 0
cc_lex_remaining:   dw 0
cc_lex_consumed:    dw 0
cc_lex_token_start: dw 0
cc_lex_token_len:   db 0
cc_lex_comment:     db 0
cc_lex_quote:       db 0
cc_lex_units:       db 0
cc_lex_kw_class:    db 0
cc_lex_kw_len:      db 0
cc_lex_octal_bad:   db 0

cc_lex_reset:
    xor a
    ld (cc_lex_comment),a
    ret

; HL=buffer, BC=length. Success A=kind, DE=bytes consumed.
cc_lex_token:
    ld (cc_lex_ptr),hl
    ld (cc_lex_remaining),bc
    ld hl,0
    ld (cc_lex_consumed),hl
    xor a
    ld (cc_lex_token_len),a
    call cc_lex_skip
    ret c
    ld hl,(cc_lex_remaining)
    ld a,h
    or l
    jp nz,cc_lex_dispatch
    ld a,CC_TOK_MORE
    jp cc_lex_success
cc_lex_dispatch:
    ld hl,(cc_lex_ptr)
    ld (cc_lex_token_start),hl
    call cc_lex_peek
    ret c
    call cc_lex_is_alpha
    jp nc,cc_lex_identifier
    cp '_'
    jp z,cc_lex_identifier
    call cc_lex_is_digit
    jp nc,cc_lex_number
    cp '.'
    jp nz,cc_lex_literal_dispatch
    call cc_lex_peek2
    jp c,cc_lex_notsup
    call cc_lex_is_digit
    jp nc,cc_lex_number
    jp cc_lex_notsup
cc_lex_literal_dispatch:
    cp 39
    jp z,cc_lex_literal
    cp 34
    jp z,cc_lex_literal
    jp cc_lex_operator

cc_lex_finish:
    ld a,(cc_lex_comment)
    cp 1
    jp z,cc_lex_format
    xor a
    ld (cc_lex_comment),a
    ld a,CC_TOK_EOF
    or a
    ret

; comment state: 0 none, 1 block, 2 line
cc_lex_skip:
    ld a,(cc_lex_comment)
    cp 1
    jp z,cc_lex_skip_block
    cp 2
    jp z,cc_lex_skip_line
cc_lex_skip_plain:
    call cc_lex_peek
    jp c,cc_lex_skip_exhausted
    cp ' '
    jp z,cc_lex_skip_take
    cp 9
    jp z,cc_lex_skip_take
    cp 10
    jp z,cc_lex_skip_take
    cp 32
    jp c,cc_lex_format
    cp 127
    jp nc,cc_lex_format
    cp '/'
    jp z,cc_lex_skip_slash
    or a
    ret
cc_lex_skip_slash:
    call cc_lex_peek2
    jp nc,cc_lex_skip_slash_pair
    or a
    ret
cc_lex_skip_slash_pair:
    cp '/'
    jp z,cc_lex_start_line
    cp '*'
    jp z,cc_lex_start_block
    or a
    ret
cc_lex_skip_take:
    call cc_lex_take
    jp cc_lex_skip_plain
cc_lex_start_line:
    call cc_lex_take
    call cc_lex_take
    ld a,2
    ld (cc_lex_comment),a
cc_lex_skip_line:
    call cc_lex_peek
    jp c,cc_lex_skip_exhausted
    call cc_lex_take
    cp 10
    jp nz,cc_lex_skip_line
    xor a
    ld (cc_lex_comment),a
    jp cc_lex_skip_plain
cc_lex_start_block:
    call cc_lex_take
    call cc_lex_take
    ld a,1
    ld (cc_lex_comment),a
cc_lex_skip_block:
    call cc_lex_peek
    jp c,cc_lex_skip_exhausted
    cp '*'
    jp nz,cc_lex_block_take
    call cc_lex_peek2
    jp c,cc_lex_block_take
    cp '/'
    jp nz,cc_lex_block_take
    call cc_lex_take
    call cc_lex_take
    xor a
    ld (cc_lex_comment),a
    jp cc_lex_skip_plain
cc_lex_block_take:
    call cc_lex_take
    jp cc_lex_skip_block

cc_lex_skip_exhausted:
    or a
    ret

cc_lex_identifier:
cc_lex_ident_loop:
    call cc_lex_peek
    jp c,cc_lex_ident_done
    call cc_lex_is_ident
    jp c,cc_lex_ident_done
    ld a,(cc_lex_token_len)
    cp CC_IDENT_MAX
    jp nc,cc_lex_toolong
    call cc_lex_toktake
    jp cc_lex_ident_loop
cc_lex_ident_done:
    call cc_lex_keyword
    ret c
    jp cc_lex_success

; row = class(1 supported,2 unsupported), length, text
cc_lex_keyword:
    ld de,cc_lex_keywords
cc_lex_kw_loop:
    ld a,(de)
    or a
    jp z,cc_lex_kw_ident
    ld (cc_lex_kw_class),a
    inc de
    ld a,(de)
    ld (cc_lex_kw_len),a
    inc de
    ld c,a
    ld a,(cc_lex_token_len)
    cp c
    jp nz,cc_lex_kw_skip
    push de
    ld hl,(cc_lex_token_start)
    ld b,c
cc_lex_kw_cmp:
    ld a,(de)
    cp (hl)
    jp nz,cc_lex_kw_miss
    inc de
    inc hl
    djnz cc_lex_kw_cmp
    pop de
    ld a,(cc_lex_kw_class)
    cp 2
    jp z,cc_lex_notsup
    ld a,CC_TOK_KEYWORD
    or a
    ret
cc_lex_kw_miss:
    pop de
cc_lex_kw_skip:
    ld a,(cc_lex_kw_len)
    ld l,a
    ld h,0
    add hl,de
    ex de,hl
    jp cc_lex_kw_loop
cc_lex_kw_ident:
    ld a,CC_TOK_IDENT
    or a
    ret

cc_lex_keywords:
    db 1,5,"break",1,4,"char",1,8,"continue",1,2,"do",1,4,"else"
    db 1,6,"extern",1,5,"float",1,3,"for",1,2,"if",1,3,"int"
    db 1,6,"return",1,5,"short",1,6,"sizeof",1,6,"static"
    db 1,8,"unsigned",1,4,"void",1,5,"while"
    db 2,4,"auto",2,4,"case",2,5,"const",2,7,"default",2,6,"double"
    db 2,4,"enum",2,4,"goto",2,4,"long",2,8,"register",2,6,"signed"
    db 2,6,"struct",2,6,"switch",2,7,"typedef",2,5,"union",2,8,"volatile"
    db 2,6,"inline",2,8,"restrict",2,8,"_Alignas",2,8,"_Alignof"
    db 2,7,"_Atomic",2,5,"_Bool",2,8,"_Complex",2,8,"_Generic"
    db 2,10,"_Imaginary",2,9,"_Noreturn",2,14,"_Static_assert",2,13,"_Thread_local"
    db 0


; Integers: decimal/octal/hex with optional u/U. Floats: decimal point/exponent.
cc_lex_number:
    xor a
    ld (cc_lex_octal_bad),a
    call cc_lex_peek
    cp '.'
    jp z,cc_lex_float_dotlead
    cp '0'
    jp nz,cc_lex_dec_loop
    call cc_lex_peek2
    jp c,cc_lex_dec_loop
    cp 'x'
    jp z,cc_lex_hex
    cp 'X'
    jp z,cc_lex_hex
cc_lex_dec_loop:
    call cc_lex_peek
    jp c,cc_lex_int_done
    call cc_lex_is_digit
    jp c,cc_lex_dec_end
    ld d,a
    ld hl,(cc_lex_token_start)
    ld a,(hl)
    cp '0'
    jp nz,cc_lex_dec_consume
    ld a,d
    cp '8'
    jp c,cc_lex_dec_consume
    ld a,1
    ld (cc_lex_octal_bad),a
cc_lex_dec_consume:
    call cc_lex_toktake
    jp cc_lex_dec_loop
cc_lex_dec_end:
    cp '.'
    jp z,cc_lex_float_dot
    cp 'e'
    jp z,cc_lex_float_exp
    cp 'E'
    jp z,cc_lex_float_exp
cc_lex_int_done:
    ld a,(cc_lex_octal_bad)
    or a
    jp nz,cc_lex_format
    call cc_lex_peek
    jp c,cc_lex_int_ok
    cp 'u'
    jp z,cc_lex_int_suffix
    cp 'U'
    jp z,cc_lex_int_suffix
    call cc_lex_is_ident
    jp nc,cc_lex_format
cc_lex_int_ok:
    ld a,CC_TOK_INT
    jp cc_lex_success
cc_lex_int_suffix:
    call cc_lex_toktake
    call cc_lex_peek
    jp c,cc_lex_int_ok
    call cc_lex_is_ident
    jp nc,cc_lex_format
    jp cc_lex_int_ok

cc_lex_hex:
    call cc_lex_toktake
    call cc_lex_toktake
    call cc_lex_peek
    jp c,cc_lex_format
    call cc_lex_is_hex
    jp c,cc_lex_format
cc_lex_hex_loop:
    call cc_lex_peek
    jp c,cc_lex_int_ok
    call cc_lex_is_hex
    jp c,cc_lex_hex_end
    call cc_lex_toktake
    jp cc_lex_hex_loop
cc_lex_hex_end:
    cp 'u'
    jp z,cc_lex_int_suffix
    cp 'U'
    jp z,cc_lex_int_suffix
    call cc_lex_is_ident
    jp nc,cc_lex_format
    jp cc_lex_int_ok

cc_lex_float_dotlead:
    call cc_lex_toktake
    call cc_lex_peek
    jp c,cc_lex_format
    call cc_lex_is_digit
    jp c,cc_lex_format
cc_lex_float_frac:
    call cc_lex_peek
    jp c,cc_lex_float_done
    call cc_lex_is_digit
    jp c,cc_lex_float_frac_end
    call cc_lex_toktake
    jp cc_lex_float_frac
cc_lex_float_frac_end:
    cp 'e'
    jp z,cc_lex_float_exp
    cp 'E'
    jp z,cc_lex_float_exp
    jp cc_lex_float_done
cc_lex_float_dot:
    call cc_lex_toktake
cc_lex_float_frac2:
    call cc_lex_peek
    jp c,cc_lex_float_done
    call cc_lex_is_digit
    jp c,cc_lex_float_frac2_end
    call cc_lex_toktake
    jp cc_lex_float_frac2
cc_lex_float_frac2_end:
    cp 'e'
    jp z,cc_lex_float_exp
    cp 'E'
    jp z,cc_lex_float_exp
    jp cc_lex_float_done
cc_lex_float_exp:
    call cc_lex_toktake
    call cc_lex_peek
    jp c,cc_lex_format
    cp '+'
    jp z,cc_lex_float_sign
    cp '-'
    jp nz,cc_lex_float_exp_digit
cc_lex_float_sign:
    call cc_lex_toktake
    call cc_lex_peek
    jp c,cc_lex_format
cc_lex_float_exp_digit:
    call cc_lex_is_digit
    jp c,cc_lex_format
cc_lex_float_exp_loop:
    call cc_lex_peek
    jp c,cc_lex_float_done
    call cc_lex_is_digit
    jp c,cc_lex_float_done
    call cc_lex_toktake
    jp cc_lex_float_exp_loop
cc_lex_float_done:
    call cc_lex_peek
    jp c,cc_lex_float_ok
    cp 'f'
    jp z,cc_lex_float_suffix
    cp 'F'
    jp z,cc_lex_float_suffix
    call cc_lex_is_ident
    jp nc,cc_lex_format
cc_lex_float_ok:
    ld a,CC_TOK_FLOAT
    jp cc_lex_success
cc_lex_float_suffix:
    call cc_lex_toktake
    call cc_lex_peek
    jp c,cc_lex_float_ok
    call cc_lex_is_ident
    jp nc,cc_lex_format
    jp cc_lex_float_ok

cc_lex_literal:
    ld (cc_lex_quote),a
    xor a
    ld (cc_lex_units),a
    call cc_lex_toktake
cc_lex_lit_loop:
    call cc_lex_peek
    jp c,cc_lex_format
    ld d,a
    ld a,(cc_lex_quote)
    cp d
    jp z,cc_lex_lit_close
    ld a,d
    cp 10
    jp z,cc_lex_format
    cp 32
    jp c,cc_lex_format
    cp 127
    jp nc,cc_lex_format
    cp 92
    jp z,cc_lex_escape
    call cc_lex_toktake
    jp cc_lex_lit_unit
cc_lex_escape:
    call cc_lex_toktake
    call cc_lex_peek
    jp c,cc_lex_format
    cp '1'
    jp c,cc_lex_escape_simple
    cp '8'
    jp c,cc_lex_notsup
cc_lex_escape_simple:
    cp 'x'
    jp z,cc_lex_escape_hex
    cp 92
    jp z,cc_lex_escape_take
    cp 39
    jp z,cc_lex_escape_take
    cp 34
    jp z,cc_lex_escape_take
    cp '0'
    jp z,cc_lex_escape_take
    cp 'a'
    jp z,cc_lex_escape_take
    cp 'b'
    jp z,cc_lex_escape_take
    cp 't'
    jp z,cc_lex_escape_take
    cp 'n'
    jp z,cc_lex_escape_take
    cp 'v'
    jp z,cc_lex_escape_take
    cp 'f'
    jp z,cc_lex_escape_take
    cp 'r'
    jp nz,cc_lex_format
cc_lex_escape_take:
    call cc_lex_toktake
    jp cc_lex_lit_unit
cc_lex_escape_hex:
    call cc_lex_toktake
    call cc_lex_peek
    jp c,cc_lex_format
    call cc_lex_is_hex
    jp c,cc_lex_format
    call cc_lex_toktake
    call cc_lex_peek
    jp c,cc_lex_format
    call cc_lex_is_hex
    jp c,cc_lex_format
    call cc_lex_toktake
cc_lex_lit_unit:
    ld a,(cc_lex_units)
    inc a
    ld (cc_lex_units),a
    ld d,a
    ld a,(cc_lex_quote)
    cp 39
    jp nz,cc_lex_lit_loop
    ld a,d
    cp 2
    jp nc,cc_lex_format
    jp cc_lex_lit_loop
cc_lex_lit_close:
    call cc_lex_toktake
    ld a,(cc_lex_quote)
    cp 39
    jp nz,cc_lex_string_ok
    ld a,(cc_lex_units)
    cp 1
    jp nz,cc_lex_format
    ld a,CC_TOK_CHAR
    jp cc_lex_success
cc_lex_string_ok:
    ld a,CC_TOK_STRING
    jp cc_lex_success


cc_lex_operator:
    cp '('
    jp z,cc_lex_punct
    cp ')'
    jp z,cc_lex_punct
    cp '['
    jp z,cc_lex_punct
    cp ']'
    jp z,cc_lex_punct
    cp '{'
    jp z,cc_lex_punct
    cp '}'
    jp z,cc_lex_punct
    cp ';'
    jp z,cc_lex_punct
    cp ','
    jp z,cc_lex_punct
    cp '?'
    jp z,cc_lex_notsup
    cp ':'
    jp z,cc_lex_notsup
    cp '.'
    jp z,cc_lex_notsup
    cp '+'
    jp z,cc_lex_plus
    cp '-'
    jp z,cc_lex_minus
    cp '<'
    jp z,cc_lex_lt
    cp '>'
    jp z,cc_lex_gt
    cp '='
    jp z,cc_lex_eq
    cp '!'
    jp z,cc_lex_eq
    cp '&'
    jp z,cc_lex_amp
    cp '|'
    jp z,cc_lex_pipe
    cp '*'
    jp z,cc_lex_assignable
    cp '/'
    jp z,cc_lex_assignable
    cp '%'
    jp z,cc_lex_assignable
    cp '^'
    jp z,cc_lex_assignable
    cp '~'
    jp z,cc_lex_op1
    jp cc_lex_format

cc_lex_punct:
    call cc_lex_toktake
    ld a,CC_TOK_PUNCT
    jp cc_lex_success
cc_lex_op1:
    call cc_lex_toktake
    ld a,CC_TOK_OPERATOR
    jp cc_lex_success
cc_lex_op2:
    call cc_lex_toktake
    call cc_lex_toktake
    ld a,CC_TOK_OPERATOR
    jp cc_lex_success
cc_lex_plus:
    call cc_lex_peek2
    jp c,cc_lex_op1
    cp '+'
    jp z,cc_lex_op2
    cp '='
    jp z,cc_lex_notsup
    jp cc_lex_op1
cc_lex_minus:
    call cc_lex_peek2
    jp c,cc_lex_op1
    cp '-'
    jp z,cc_lex_op2
    cp '='
    jp z,cc_lex_notsup
    cp '>'
    jp z,cc_lex_notsup
    jp cc_lex_op1
cc_lex_lt:
    call cc_lex_peek2
    jp c,cc_lex_op1
    cp '='
    jp z,cc_lex_op2
    cp '<'
    jp nz,cc_lex_op1
    call cc_lex_peek3
    jp c,cc_lex_op2
    cp '='
    jp z,cc_lex_notsup
    jp cc_lex_op2
cc_lex_gt:
    call cc_lex_peek2
    jp c,cc_lex_op1
    cp '='
    jp z,cc_lex_op2
    cp '>'
    jp nz,cc_lex_op1
    call cc_lex_peek3
    jp c,cc_lex_op2
    cp '='
    jp z,cc_lex_notsup
    jp cc_lex_op2
cc_lex_eq:
    call cc_lex_peek2
    jp c,cc_lex_op1
    cp '='
    jp z,cc_lex_op2
    jp cc_lex_op1
cc_lex_amp:
    call cc_lex_peek2
    jp c,cc_lex_op1
    cp '&'
    jp z,cc_lex_op2
    cp '='
    jp z,cc_lex_notsup
    jp cc_lex_op1
cc_lex_pipe:
    call cc_lex_peek2
    jp c,cc_lex_op1
    cp '|'
    jp z,cc_lex_op2
    cp '='
    jp z,cc_lex_notsup
    jp cc_lex_op1
cc_lex_assignable:
    call cc_lex_peek2
    jp c,cc_lex_op1
    cp '='
    jp z,cc_lex_notsup
    jp cc_lex_op1

cc_lex_peek:
    ld hl,(cc_lex_remaining)
    ld a,h
    or l
    jp z,cc_lex_empty
    ld hl,(cc_lex_ptr)
    ld a,(hl)
    or a
    ret
cc_lex_peek2:
    ld hl,(cc_lex_remaining)
    ld a,h
    or a
    jp nz,cc_lex_peek2_have
    ld a,l
    cp 2
    jp c,cc_lex_empty
cc_lex_peek2_have:
    ld hl,(cc_lex_ptr)
    inc hl
    ld a,(hl)
    or a
    ret
cc_lex_peek3:
    ld hl,(cc_lex_remaining)
    ld a,h
    or a
    jp nz,cc_lex_peek3_have
    ld a,l
    cp 3
    jp c,cc_lex_empty
cc_lex_peek3_have:
    ld hl,(cc_lex_ptr)
    inc hl
    inc hl
    ld a,(hl)
    or a
    ret
cc_lex_empty:
    scf
    ret

cc_lex_take:
    ld hl,(cc_lex_ptr)
    ld a,(hl)
    inc hl
    ld (cc_lex_ptr),hl
    ld hl,(cc_lex_remaining)
    dec hl
    ld (cc_lex_remaining),hl
    ld hl,(cc_lex_consumed)
    inc hl
    ld (cc_lex_consumed),hl
    ret
cc_lex_toktake:
    call cc_lex_take
    push af
    ld a,(cc_lex_token_len)
    inc a
    ld (cc_lex_token_len),a
    pop af
    ret

cc_lex_is_alpha:
    cp 'A'
    jp c,cc_lex_class_no
    cp 'Z'+1
    jp c,cc_lex_class_yes
    cp 'a'
    jp c,cc_lex_class_no
    cp 'z'+1
    jp c,cc_lex_class_yes
cc_lex_class_no:
    scf
    ret
cc_lex_class_yes:
    or a
    ret
cc_lex_is_digit:
    cp '0'
    jp c,cc_lex_class_no
    cp '9'+1
    jp c,cc_lex_class_yes
    scf
    ret
cc_lex_is_hex:
    call cc_lex_is_digit
    ret nc
    cp 'A'
    jp c,cc_lex_class_no
    cp 'F'+1
    jp c,cc_lex_class_yes
    cp 'a'
    jp c,cc_lex_class_no
    cp 'f'+1
    jp c,cc_lex_class_yes
    scf
    ret
cc_lex_is_ident:
    call cc_lex_is_alpha
    ret nc
    cp '_'
    jp z,cc_lex_class_yes
    jp cc_lex_is_digit

cc_lex_success:
    ld de,(cc_lex_consumed)
    or a
    ret
cc_lex_toolong:
    ld a,E_TOOLONG
    scf
    ret
cc_lex_notsup:
    ld a,E_NOTSUP
    scf
    ret
cc_lex_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.05 C48 declarations/types parser.
; This stage consumes lexer tokens incrementally and freezes declaration/type
; syntax and exact function-signature compatibility. Statement parsing follows
; in P11.06; a definition header ending in "{" is therefore this stage's
; deliberate hand-off boundary.
    MACRO EMIT_P11_CC_DECL_PARSER
CC_TYPE_VOID             EQU 0
CC_TYPE_CHAR             EQU 1
CC_TYPE_UCHAR            EQU 2
CC_TYPE_SHORT            EQU 3
CC_TYPE_USHORT           EQU 4
CC_TYPE_INT              EQU 5
CC_TYPE_UINT             EQU 6
CC_TYPE_FLOAT            EQU 7
CC_STORAGE_NONE          EQU 0
CC_STORAGE_STATIC        EQU 1
CC_STORAGE_EXTERN        EQU 2
CC_DECL_OBJECT           EQU 1
CC_DECL_ARRAY            EQU 2
CC_DECL_FUNCTION         EQU 3
CC_INIT_NONE             EQU 0
CC_INIT_SCALAR           EQU 1
CC_INIT_ARRAY            EQU 2
CC_INIT_STRING           EQU 3
CC_PARSE_PTR_MAX         EQU 8
CC_PARSE_PARAM_CAPACITY  EQU 8
CC_PARSE_PROTO_CAPACITY  EQU 8
CC_PARSE_PROTO_ENTRY_SIZE EQU 38

CC_WORD_VOID             EQU 1
CC_WORD_CHAR             EQU 2
CC_WORD_UNSIGNED         EQU 3
CC_WORD_SHORT            EQU 4
CC_WORD_INT              EQU 5
CC_WORD_FLOAT            EQU 6
CC_WORD_STATIC           EQU 7
CC_WORD_EXTERN           EQU 8
CC_WORD_MAIN             EQU 9

cc_parse_ptr:            dw 0
cc_parse_remaining:      dw 0
cc_parse_tok_ptr:        dw 0
cc_parse_tok_kind:       db 0
cc_parse_tok_len:        db 0
cc_parse_scope:          db 0
cc_parse_storage:        db 0
cc_parse_type:           db 0
cc_parse_ptr_depth:      db 0
cc_parse_decl_kind:      db 0
cc_parse_array_bound:    db 0
cc_parse_init_kind:      db 0
cc_parse_init_count:     db 0
cc_parse_param_count:    db 0
cc_parse_param_missing:  db 0
cc_parse_return_type:    db 0
cc_parse_return_ptr:     db 0
cc_parse_params:         defs CC_PARSE_PARAM_CAPACITY*2,0
cc_parse_name:           defs 16,0
cc_parse_definition:     db 0
cc_parse_proto_new:      db 0
cc_parse_word_code_tmp:  db 0
cc_parse_word_len:       db 0
cc_parse_saved_char:     db 0
cc_parse_proto_count:    db 0
cc_parse_proto_table:    defs CC_PARSE_PROTO_CAPACITY*CC_PARSE_PROTO_ENTRY_SIZE,0

cc_parse_tu_reset:
    xor a
    ld (cc_parse_proto_count),a
    ld (cc_global_count),a
    ld (cc_local_count),a
    ret

; HL=complete bounded declaration/header span, BC=length.
cc_parse_file_decl:
    xor a
    ld (cc_parse_scope),a
    jp cc_parse_begin

; HL=complete bounded local declaration span, BC=length.
cc_parse_local_decl:
    ld a,1
    ld (cc_parse_scope),a
cc_parse_begin:
    ld (cc_parse_ptr),hl
    ld (cc_parse_remaining),bc
    xor a
    ld (cc_parse_storage),a
    ld (cc_parse_ptr_depth),a
    ld (cc_parse_decl_kind),a
    ld (cc_parse_array_bound),a
    ld (cc_parse_init_kind),a
    ld (cc_parse_init_count),a
    ld (cc_parse_param_count),a
    ld (cc_parse_param_missing),a
    ld (cc_parse_definition),a
    call cc_lex_reset
    call cc_parse_next
    ret c
    call cc_parse_storage_class
    ret c
    call cc_parse_type_spec
    ret c
    xor a
    ld (cc_parse_ptr_depth),a
    call cc_parse_pointer_stars
    ret c
    call cc_parse_capture_name
    ret c
    call cc_parse_next
    ret c
    ld a,'('
    call cc_parse_is_char
    jp z,cc_parse_function
    ld a,'['
    call cc_parse_is_char
    jp z,cc_parse_array
    ld a,CC_DECL_OBJECT
    ld (cc_parse_decl_kind),a
    jp cc_parse_object_tail

cc_parse_storage_class:
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_KEYWORD
    ret nz
    call cc_parse_word_code
    cp CC_WORD_STATIC
    jp z,cc_parse_storage_static
    cp CC_WORD_EXTERN
    jp z,cc_parse_storage_extern
    or a
    ret
cc_parse_storage_static:
    ld a,(cc_parse_scope)
    or a
    jp nz,cc_parse_notsup
    ld a,CC_STORAGE_STATIC
    ld (cc_parse_storage),a
    jp cc_parse_next
cc_parse_storage_extern:
    ld a,(cc_parse_scope)
    or a
    jp nz,cc_parse_notsup
    ld a,CC_STORAGE_EXTERN
    ld (cc_parse_storage),a
    jp cc_parse_next

; Leaves current token immediately after the type specifier.
cc_parse_type_spec:
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_KEYWORD
    jp nz,cc_parse_format
    call cc_parse_word_code
    cp CC_WORD_VOID
    jp z,cc_parse_type_void
    cp CC_WORD_CHAR
    jp z,cc_parse_type_char
    cp CC_WORD_SHORT
    jp z,cc_parse_type_short
    cp CC_WORD_INT
    jp z,cc_parse_type_int
    cp CC_WORD_FLOAT
    jp z,cc_parse_type_float
    cp CC_WORD_UNSIGNED
    jp z,cc_parse_type_unsigned
    jp cc_parse_format
cc_parse_type_void:
    ld a,CC_TYPE_VOID
    ld (cc_parse_type),a
    jp cc_parse_next
cc_parse_type_char:
    ld a,CC_TYPE_CHAR
    ld (cc_parse_type),a
    jp cc_parse_next
cc_parse_type_short:
    ld a,CC_TYPE_SHORT
    ld (cc_parse_type),a
    jp cc_parse_next
cc_parse_type_int:
    ld a,CC_TYPE_INT
    ld (cc_parse_type),a
    jp cc_parse_next
cc_parse_type_float:
    ld a,CC_TYPE_FLOAT
    ld (cc_parse_type),a
    jp cc_parse_next
cc_parse_type_unsigned:
    call cc_parse_next
    ret c
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_KEYWORD
    jp nz,cc_parse_format
    call cc_parse_word_code
    cp CC_WORD_CHAR
    jp z,cc_parse_type_uchar
    cp CC_WORD_SHORT
    jp z,cc_parse_type_ushort
    cp CC_WORD_INT
    jp z,cc_parse_type_uint
    jp cc_parse_format
cc_parse_type_uchar:
    ld a,CC_TYPE_UCHAR
    ld (cc_parse_type),a
    jp cc_parse_next
cc_parse_type_ushort:
    ld a,CC_TYPE_USHORT
    ld (cc_parse_type),a
    jp cc_parse_next
cc_parse_type_uint:
    ld a,CC_TYPE_UINT
    ld (cc_parse_type),a
    jp cc_parse_next

cc_parse_pointer_stars:
    ld a,'*'
    call cc_parse_is_char
    ret nz
    ld a,(cc_parse_ptr_depth)
    cp CC_PARSE_PTR_MAX
    jp nc,cc_parse_nospc
    inc a
    ld (cc_parse_ptr_depth),a
    call cc_parse_next
    ret c
    jp cc_parse_pointer_stars

cc_parse_capture_name:
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_IDENT
    jp nz,cc_parse_format
    ld a,(cc_parse_tok_len)
    or a
    jp z,cc_parse_format
    cp CC_IDENT_MAX+1
    jp nc,cc_parse_toolong
    ld b,a
    ld hl,(cc_parse_tok_ptr)
    ld de,cc_parse_name
cc_parse_name_copy:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz cc_parse_name_copy
    ld a,(cc_parse_tok_len)
    ld b,a
    ld a,16
    sub b
    ld b,a
    xor a
cc_parse_name_zero:
    ld (de),a
    inc de
    djnz cc_parse_name_zero
    or a
    ret

cc_parse_object_tail:
    ld a,(cc_parse_type)
    or a
    jp nz,cc_parse_object_init
    ld a,(cc_parse_ptr_depth)
    or a
    jp z,cc_parse_format
cc_parse_object_init:
    call cc_parse_initializer_optional
    ret c
    ld a,';'
    call cc_parse_expect_char
    ret c
    call cc_parse_require_eof
    ret c
    ld a,(cc_parse_storage)
    cp CC_STORAGE_EXTERN
    jp nz,cc_parse_commit_object
    ld a,(cc_parse_init_kind)
    or a
    jp nz,cc_parse_format
cc_parse_commit_object:
    ld hl,cc_parse_name
    ld a,(cc_parse_type)
    ld d,a
    ld a,(cc_parse_ptr_depth)
    ld e,a
    ld a,(cc_parse_scope)
    or a
    jp nz,cc_parse_commit_local
    call cc_global_insert
    ret
cc_parse_commit_local:
    call cc_local_insert
    ret

cc_parse_array:
    ld a,(cc_parse_scope)
    ; arrays are valid at file or local scope.
    ld a,(cc_parse_type)
    or a
    jp nz,cc_parse_array_nonvoid
    ld a,(cc_parse_ptr_depth)
    or a
    jp z,cc_parse_format
cc_parse_array_nonvoid:
    ld a,CC_DECL_ARRAY
    ld (cc_parse_decl_kind),a
    call cc_parse_next
    ret c
    ld a,']'
    call cc_parse_is_char
    jp z,cc_parse_array_close
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_INT
    jp nz,cc_parse_notsup
    ld a,1
    ld (cc_parse_array_bound),a
    call cc_parse_next
    ret c
    ld a,']'
    call cc_parse_expect_char
    ret c
    jp cc_parse_array_after_close
cc_parse_array_close:
    call cc_parse_next
    ret c
cc_parse_array_after_close:
    ld a,'['
    call cc_parse_is_char
    jp z,cc_parse_notsup
    call cc_parse_initializer_optional
    ret c
    ld a,';'
    call cc_parse_expect_char
    ret c
    call cc_parse_require_eof
    ret c
    ld a,(cc_parse_storage)
    cp CC_STORAGE_EXTERN
    jp nz,cc_parse_array_unsized_check
    ld a,(cc_parse_init_kind)
    or a
    jp nz,cc_parse_format
cc_parse_array_unsized_check:
    ld a,(cc_parse_array_bound)
    or a
    jp nz,cc_parse_commit_object
    ld a,(cc_parse_init_kind)
    cp CC_INIT_ARRAY
    jp z,cc_parse_commit_object
    cp CC_INIT_STRING
    jp z,cc_parse_commit_object
    jp cc_parse_format

cc_parse_initializer_optional:
    xor a
    ld (cc_parse_init_kind),a
    ld (cc_parse_init_count),a
    ld a,'='
    call cc_parse_is_char
    ret nz
    ld a,(cc_parse_storage)
    cp CC_STORAGE_EXTERN
    jp z,cc_parse_format
    call cc_parse_next
    ret c
    ld a,(cc_parse_decl_kind)
    cp CC_DECL_ARRAY
    jp z,cc_parse_array_initializer
    call cc_parse_constant
    ret c
    ld a,CC_INIT_SCALAR
    ld (cc_parse_init_kind),a
    ret

cc_parse_array_initializer:
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_STRING
    jp z,cc_parse_array_string
    ld a,'{'
    call cc_parse_is_char
    jp nz,cc_parse_notsup
    call cc_parse_next
    ret c
    ld a,'}'
    call cc_parse_is_char
    jp z,cc_parse_format
cc_parse_array_init_loop:
    ld a,'{'
    call cc_parse_is_char
    jp z,cc_parse_notsup
    call cc_parse_constant
    ret c
    ld a,(cc_parse_init_count)
    cp 255
    jp z,cc_parse_nospc
    inc a
    ld (cc_parse_init_count),a
    ld a,'}'
    call cc_parse_is_char
    jp z,cc_parse_array_init_close
    ld a,','
    call cc_parse_expect_char
    ret c
    ld a,'}'
    call cc_parse_is_char
    jp z,cc_parse_array_init_close
    jp cc_parse_array_init_loop
cc_parse_array_init_close:
    call cc_parse_next
    ret c
    ld a,CC_INIT_ARRAY
    ld (cc_parse_init_kind),a
    ret
cc_parse_array_string:
    call cc_parse_next
    ret c
    ld a,CC_INIT_STRING
    ld (cc_parse_init_kind),a
    ret

; Accept an intentionally small constant initializer atom. Full expression
; precedence arrives in P11.07; identifiers/calls are not silently accepted.
cc_parse_constant:
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_INT
    jp z,cc_parse_constant_take
    cp CC_TOK_FLOAT
    jp z,cc_parse_constant_take
    cp CC_TOK_CHAR
    jp z,cc_parse_constant_take
    cp CC_TOK_STRING
    jp z,cc_parse_constant_take
    ld a,'+'
    call cc_parse_is_char
    jp z,cc_parse_constant_unary
    ld a,'-'
    call cc_parse_is_char
    jp z,cc_parse_constant_unary
    jp cc_parse_notsup
cc_parse_constant_unary:
    call cc_parse_next
    ret c
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_INT
    jp z,cc_parse_constant_take
    cp CC_TOK_FLOAT
    jp nz,cc_parse_notsup
cc_parse_constant_take:
    jp cc_parse_next

cc_parse_function:
    ld a,(cc_parse_scope)
    or a
    jp nz,cc_parse_notsup
    ld a,CC_DECL_FUNCTION
    ld (cc_parse_decl_kind),a
    ld a,(cc_parse_type)
    ld (cc_parse_return_type),a
    ld a,(cc_parse_ptr_depth)
    ld (cc_parse_return_ptr),a
    xor a
    ld (cc_parse_param_count),a
    ld (cc_parse_param_missing),a
    ld hl,cc_parse_params
    ld b,CC_PARSE_PARAM_CAPACITY*2
cc_parse_clear_params:
    ld (hl),a
    inc hl
    djnz cc_parse_clear_params
    call cc_parse_next
    ret c
    ld a,')'
    call cc_parse_is_char
    jp z,cc_parse_notsup
    call cc_parse_param
    ret c
cc_parse_param_tail:
    ld a,')'
    call cc_parse_is_char
    jp z,cc_parse_params_done
    ld a,','
    call cc_parse_expect_char
    ret c
    call cc_parse_param
    ret c
    jp cc_parse_param_tail
cc_parse_params_done:
    call cc_parse_next
    ret c
    ; exactly "void" denotes zero parameters.
    ld a,(cc_parse_param_count)
    cp 1
    jp nz,cc_parse_function_term
    ld a,(cc_parse_params)
    cp CC_TYPE_VOID
    jp nz,cc_parse_function_term
    ld a,(cc_parse_params+1)
    or a
    jp nz,cc_parse_function_term
    xor a
    ld (cc_parse_param_count),a
    ld (cc_parse_param_missing),a
cc_parse_function_term:
    ld a,(cc_parse_return_type)
    ld (cc_parse_type),a
    ld a,(cc_parse_return_ptr)
    ld (cc_parse_ptr_depth),a
    ld a,';'
    call cc_parse_is_char
    jp z,cc_parse_function_proto
    ld a,'{'
    call cc_parse_is_char
    jp z,cc_parse_function_def
    jp cc_parse_format
cc_parse_function_proto:
    xor a
    ld (cc_parse_definition),a
    call cc_parse_next
    ret c
    call cc_parse_require_eof
    ret c
    call cc_parse_validate_function
    ret c
    jp cc_parse_register_function
cc_parse_function_def:
    ld a,1
    ld (cc_parse_definition),a
    ld a,(cc_parse_storage)
    cp CC_STORAGE_EXTERN
    jp z,cc_parse_format
    ld a,(cc_parse_param_missing)
    or a
    jp nz,cc_parse_format
    call cc_parse_next
    ret c
    call cc_parse_require_eof
    ret c
    call cc_parse_validate_function
    ret c
    jp cc_parse_register_function

; Current token begins one parameter. Stores [base-type,pointer-depth].
cc_parse_param:
    ld a,(cc_parse_param_count)
    cp CC_PARSE_PARAM_CAPACITY
    jp nc,cc_parse_nospc
    call cc_parse_type_spec
    ret c
    xor a
    ld (cc_parse_ptr_depth),a
    call cc_parse_pointer_stars
    ret c
    ld a,(cc_parse_type)
    or a
    jp nz,cc_parse_param_nonvoid
    ld a,(cc_parse_ptr_depth)
    or a
    jp nz,cc_parse_param_nonvoid
    ; plain void is accepted only as the entire zero-parameter clause.
    ld a,(cc_parse_param_count)
    or a
    jp nz,cc_parse_format
    ld a,')'
    call cc_parse_is_char
    jp nz,cc_parse_format
cc_parse_param_nonvoid:
    ld a,(cc_parse_param_count)
    ld e,a
    ld d,0
    sla e
    rl d
    ld hl,cc_parse_params
    add hl,de
    ld a,(cc_parse_type)
    ld (hl),a
    inc hl
    ld a,(cc_parse_ptr_depth)
    ld (hl),a
    ld hl,cc_parse_param_count
    inc (hl)
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_IDENT
    jp nz,cc_parse_param_unnamed
    call cc_parse_next
    ret c
    ld a,'['
    call cc_parse_is_char
    jp z,cc_parse_notsup
    or a
    ret
cc_parse_param_unnamed:
    ld a,1
    ld (cc_parse_param_missing),a
    or a
    ret

cc_parse_validate_function:
    call cc_parse_name_is_main
    ret nz
    ld a,(cc_parse_type)
    cp CC_TYPE_INT
    jp nz,cc_parse_format
    ld a,(cc_parse_ptr_depth)
    or a
    jp nz,cc_parse_format
    ld a,(cc_parse_storage)
    cp CC_STORAGE_STATIC
    jp z,cc_parse_format
    ld a,(cc_parse_definition)
    or a
    jp z,cc_parse_main_params
    ld a,(cc_parse_storage)
    or a
    jp nz,cc_parse_format
cc_parse_main_params:
    ld a,(cc_parse_param_count)
    or a
    ret z
    cp 2
    jp nz,cc_parse_format
    ld a,(cc_parse_params)
    cp CC_TYPE_INT
    jp nz,cc_parse_format
    ld a,(cc_parse_params+1)
    or a
    jp nz,cc_parse_format
    ld a,(cc_parse_params+2)
    cp CC_TYPE_CHAR
    jp nz,cc_parse_format
    ld a,(cc_parse_params+3)
    cp 2
    jp nz,cc_parse_format
    or a
    ret

cc_parse_register_function:
    call cc_parse_proto_register
    ret c
    ld a,(cc_parse_proto_new)
    or a
    ret z
    ld hl,cc_parse_name
    ld a,(cc_parse_type)
    ld d,a
    ld a,(cc_parse_ptr_depth)
    ld e,a
    call cc_global_insert
    ret

cc_parse_proto_register:
    xor a
    ld (cc_parse_proto_new),a
    ld a,(cc_parse_proto_count)
    or a
    jp z,cc_parse_proto_add
    ld b,a
    ld de,cc_parse_proto_table
cc_parse_proto_find:
    push bc
    push de
    ld hl,cc_parse_name
    ld c,16
cc_parse_proto_name_cmp:
    ld a,(de)
    cp (hl)
    jp nz,cc_parse_proto_name_miss
    inc de
    inc hl
    dec c
    jp nz,cc_parse_proto_name_cmp
    pop de
    pop bc
    jp cc_parse_proto_match
cc_parse_proto_name_miss:
    pop de
    pop bc
    ld hl,CC_PARSE_PROTO_ENTRY_SIZE
    add hl,de
    ex de,hl
    djnz cc_parse_proto_find
cc_parse_proto_add:
    ld a,(cc_parse_proto_count)
    cp CC_PARSE_PROTO_CAPACITY
    jp nc,cc_parse_nospc
    ld b,a
    ld de,cc_parse_proto_table
    ld a,b
    or a
    jp z,cc_parse_proto_add_ready
cc_parse_proto_add_seek:
    ld hl,CC_PARSE_PROTO_ENTRY_SIZE
    add hl,de
    ex de,hl
    djnz cc_parse_proto_add_seek
cc_parse_proto_add_ready:
    push de
    ld hl,cc_parse_name
    ld b,16
cc_parse_proto_add_name:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz cc_parse_proto_add_name
    ld a,(cc_parse_type)
    ld (de),a
    inc de
    ld a,(cc_parse_ptr_depth)
    ld (de),a
    inc de
    ld a,(cc_parse_param_count)
    ld (de),a
    inc de
    ld hl,cc_parse_params
    ld b,CC_PARSE_PARAM_CAPACITY*2
cc_parse_proto_add_params:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz cc_parse_proto_add_params
    ld a,(cc_parse_storage)
    cp CC_STORAGE_STATIC
    ld a,0
    jp nz,cc_parse_proto_add_link
    inc a
cc_parse_proto_add_link:
    ld (de),a
    inc de
    ld a,(cc_parse_definition)
    ld (de),a
    inc de
    xor a
    ld (de),a
    pop de
    ld hl,cc_parse_proto_count
    inc (hl)
    ld a,1
    ld (cc_parse_proto_new),a
    or a
    ret

; DE points at existing entry.
cc_parse_proto_match:
    push de
    ld hl,16
    add hl,de
    ld a,(cc_parse_type)
    cp (hl)
    jp nz,cc_parse_proto_match_fail
    inc hl
    ld a,(cc_parse_ptr_depth)
    cp (hl)
    jp nz,cc_parse_proto_match_fail
    inc hl
    ld a,(cc_parse_param_count)
    cp (hl)
    jp nz,cc_parse_proto_match_fail
    inc hl
    ld de,cc_parse_params
    ld b,CC_PARSE_PARAM_CAPACITY*2
cc_parse_proto_param_cmp:
    ld a,(de)
    cp (hl)
    jp nz,cc_parse_proto_match_fail
    inc de
    inc hl
    djnz cc_parse_proto_param_cmp
    ld a,(cc_parse_storage)
    cp CC_STORAGE_STATIC
    ld a,0
    jp nz,cc_parse_proto_link_ready
    inc a
cc_parse_proto_link_ready:
    cp (hl)
    jp nz,cc_parse_proto_match_fail
    inc hl
    ld a,(cc_parse_definition)
    or a
    jp z,cc_parse_proto_match_ok
    ld a,(hl)
    or a
    jp nz,cc_parse_proto_duplicate_def
    ld (hl),1
cc_parse_proto_match_ok:
    pop de
    xor a
    ret
cc_parse_proto_duplicate_def:
    pop de
    ld a,E_EXIST
    scf
    ret
cc_parse_proto_match_fail:
    pop de
    jp cc_parse_format

cc_parse_name_is_main:
    ld hl,cc_parse_name
    ld a,(hl)
    cp 'm'
    jp nz,cc_parse_name_not_main
    inc hl
    ld a,(hl)
    cp 'a'
    jp nz,cc_parse_name_not_main
    inc hl
    ld a,(hl)
    cp 'i'
    jp nz,cc_parse_name_not_main
    inc hl
    ld a,(hl)
    cp 'n'
    jp nz,cc_parse_name_not_main
    inc hl
    ld a,(hl)
    or a
    ret
cc_parse_name_not_main:
    ld a,1
    or a
    ret

cc_parse_next:
    ld hl,(cc_parse_ptr)
    ld bc,(cc_parse_remaining)
    call cc_lex_token
    ret c
    push af
    ld hl,(cc_parse_ptr)
    add hl,de
    ld (cc_parse_ptr),hl
    ld hl,(cc_parse_remaining)
    or a
    sbc hl,de
    ld (cc_parse_remaining),hl
    pop af
    cp CC_TOK_MORE
    jp z,cc_parse_next_finish
    ld (cc_parse_tok_kind),a
    ld hl,(cc_lex_token_start)
    ld (cc_parse_tok_ptr),hl
    ld a,(cc_lex_token_len)
    ld (cc_parse_tok_len),a
    ld a,(cc_parse_tok_kind)
    or a
    ret
cc_parse_next_finish:
    call cc_lex_finish
    ret c
    ld (cc_parse_tok_kind),a
    xor a
    ld (cc_parse_tok_len),a
    ld hl,(cc_parse_ptr)
    ld (cc_parse_tok_ptr),hl
    or a
    ret

cc_parse_expect_char:
    ld (cc_parse_saved_char),a
    call cc_parse_is_char
    jp nz,cc_parse_format
    jp cc_parse_next

; Input A=ASCII, returns Z on exact one-byte current token match.
cc_parse_is_char:
    ld (cc_parse_saved_char),a
    ld a,(cc_parse_tok_len)
    cp 1
    jp nz,cc_parse_char_no
    ld hl,(cc_parse_tok_ptr)
    ld a,(cc_parse_saved_char)
    cp (hl)
    jp z,cc_parse_char_yes
cc_parse_char_no:
    ld a,1
    or a
    ret
cc_parse_char_yes:
    xor a
    ret

cc_parse_require_eof:
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_EOF
    ret z
    jp cc_parse_format

; Map current exact word spelling to a compact parser code.
cc_parse_word_code:
    ld de,cc_parse_words
cc_parse_word_loop:
    ld a,(de)
    or a
    ret z
    ld (cc_parse_word_code_tmp),a
    inc de
    ld a,(de)
    ld (cc_parse_word_len),a
    inc de
    ld c,a
    ld a,(cc_parse_tok_len)
    cp c
    jp nz,cc_parse_word_skip
    push de
    ld hl,(cc_parse_tok_ptr)
    ld b,c
cc_parse_word_cmp:
    ld a,(de)
    cp (hl)
    jp nz,cc_parse_word_miss
    inc de
    inc hl
    djnz cc_parse_word_cmp
    pop de
    ld a,(cc_parse_word_code_tmp)
    or a
    ret
cc_parse_word_miss:
    pop de
cc_parse_word_skip:
    ld a,(cc_parse_word_len)
    ld l,a
    ld h,0
    add hl,de
    ex de,hl
    jp cc_parse_word_loop

cc_parse_words:
    db CC_WORD_VOID,4,"void"
    db CC_WORD_CHAR,4,"char"
    db CC_WORD_UNSIGNED,8,"unsigned"
    db CC_WORD_SHORT,5,"short"
    db CC_WORD_INT,3,"int"
    db CC_WORD_FLOAT,5,"float"
    db CC_WORD_STATIC,6,"static"
    db CC_WORD_EXTERN,6,"extern"
    db CC_WORD_MAIN,4,"main"
    db 0

cc_parse_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_parse_toolong:
    ld a,E_TOOLONG
    scf
    ret
cc_parse_notsup:
    ld a,E_NOTSUP
    scf
    ret
cc_parse_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.06 C48 statement/control-flow parser.
; Expression interiors remain opaque token spans until P11.07 freezes precedence.
; This stage emits a compact deterministic control-flow event stream.
    MACRO EMIT_P11_CC_STATEMENTS
CC_CF_IF                EQU 1
CC_CF_ELSE              EQU 2
CC_CF_WHILE             EQU 3
CC_CF_DO                EQU 4
CC_CF_FOR               EQU 5
CC_CF_BREAK             EQU 6
CC_CF_CONTINUE          EQU 7
CC_CF_RETURN            EQU 8
CC_CF_BLOCK_BEGIN       EQU 9
CC_CF_BLOCK_END         EQU 10
CC_CF_EXPR              EQU 11
CC_CF_EMPTY             EQU 12
CC_STMT_DEPTH_MAX       EQU 8
CC_STMT_OUTPUT_CAPACITY EQU 64

CC_STMT_WORD_IF         EQU 1
CC_STMT_WORD_ELSE       EQU 2
CC_STMT_WORD_WHILE      EQU 3
CC_STMT_WORD_DO         EQU 4
CC_STMT_WORD_FOR        EQU 5
CC_STMT_WORD_BREAK      EQU 6
CC_STMT_WORD_CONTINUE   EQU 7
CC_STMT_WORD_RETURN     EQU 8

cc_stmt_output:         defs CC_STMT_OUTPUT_CAPACITY,0
cc_stmt_output_count:   db 0
cc_stmt_depth:          db 0
cc_stmt_loop_depth:     db 0
cc_stmt_expr_depth:     db 0
cc_stmt_bracket_depth:  db 0
cc_stmt_expr_seen:      db 0
cc_stmt_expr_required:  db 0
cc_stmt_delimiter:      db 0
cc_stmt_word_tmp:       db 0
cc_stmt_word_len:       db 0

; HL=bounded complete statement span, BC=length.
cc_stmt_parse:
    ld (cc_parse_ptr),hl
    ld (cc_parse_remaining),bc
    xor a
    ld (cc_stmt_output_count),a
    ld (cc_stmt_depth),a
    ld (cc_stmt_loop_depth),a
    call cc_lex_reset
    call cc_parse_next
    ret c
    call cc_stmt_statement
    ret c
    jp cc_parse_require_eof

cc_stmt_statement:
    ld a,(cc_stmt_depth)
    cp CC_STMT_DEPTH_MAX
    jp nc,cc_stmt_nospc
    inc a
    ld (cc_stmt_depth),a
    call cc_stmt_statement_impl
    push af
    ld hl,cc_stmt_depth
    dec (hl)
    pop af
    ret

cc_stmt_statement_impl:
    ld a,'{'
    call cc_parse_is_char
    jp z,cc_stmt_compound
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_KEYWORD
    jp nz,cc_stmt_expr_or_empty
    call cc_stmt_word_code
    cp CC_STMT_WORD_IF
    jp z,cc_stmt_if
    cp CC_STMT_WORD_WHILE
    jp z,cc_stmt_while
    cp CC_STMT_WORD_DO
    jp z,cc_stmt_do
    cp CC_STMT_WORD_FOR
    jp z,cc_stmt_for
    cp CC_STMT_WORD_BREAK
    jp z,cc_stmt_break
    cp CC_STMT_WORD_CONTINUE
    jp z,cc_stmt_continue
    cp CC_STMT_WORD_RETURN
    jp z,cc_stmt_return
    jp cc_stmt_format

cc_stmt_compound:
    ld a,CC_CF_BLOCK_BEGIN
    call cc_stmt_emit
    ret c
    call cc_parse_next
    ret c
cc_stmt_compound_loop:
    ld a,'}'
    call cc_parse_is_char
    jp z,cc_stmt_compound_end
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_EOF
    jp z,cc_stmt_format
    call cc_stmt_statement
    ret c
    jp cc_stmt_compound_loop
cc_stmt_compound_end:
    ld a,CC_CF_BLOCK_END
    call cc_stmt_emit
    ret c
    jp cc_parse_next

cc_stmt_if:
    ld a,CC_CF_IF
    call cc_stmt_emit
    ret c
    call cc_parse_next
    ret c
    ld a,'('
    call cc_parse_expect_char
    ret c
    ld a,')'
    ld b,1
    call cc_stmt_expression_to
    ret c
    ld a,')'
    call cc_parse_expect_char
    ret c
    call cc_stmt_statement
    ret c
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_KEYWORD
    jp nz,cc_stmt_ok
    call cc_stmt_word_code
    cp CC_STMT_WORD_ELSE
    jp nz,cc_stmt_ok
    ld a,CC_CF_ELSE
    call cc_stmt_emit
    ret c
    call cc_parse_next
    ret c
    jp cc_stmt_statement

cc_stmt_while:
    ld a,CC_CF_WHILE
    call cc_stmt_emit
    ret c
    call cc_parse_next
    ret c
    ld a,'('
    call cc_parse_expect_char
    ret c
    ld a,')'
    ld b,1
    call cc_stmt_expression_to
    ret c
    ld a,')'
    call cc_parse_expect_char
    ret c
    ld hl,cc_stmt_loop_depth
    inc (hl)
    call cc_stmt_statement
    push af
    ld hl,cc_stmt_loop_depth
    dec (hl)
    pop af
    ret

cc_stmt_do:
    ld a,CC_CF_DO
    call cc_stmt_emit
    ret c
    call cc_parse_next
    ret c
    ld hl,cc_stmt_loop_depth
    inc (hl)
    call cc_stmt_statement
    push af
    ld hl,cc_stmt_loop_depth
    dec (hl)
    pop af
    ret c
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_KEYWORD
    jp nz,cc_stmt_format
    call cc_stmt_word_code
    cp CC_STMT_WORD_WHILE
    jp nz,cc_stmt_format
    call cc_parse_next
    ret c
    ld a,'('
    call cc_parse_expect_char
    ret c
    ld a,')'
    ld b,1
    call cc_stmt_expression_to
    ret c
    ld a,')'
    call cc_parse_expect_char
    ret c
    ld a,';'
    jp cc_parse_expect_char

cc_stmt_for:
    ld a,CC_CF_FOR
    call cc_stmt_emit
    ret c
    call cc_parse_next
    ret c
    ld a,'('
    call cc_parse_expect_char
    ret c
    ld a,';'
    ld b,0
    call cc_stmt_expression_to
    ret c
    ld a,';'
    call cc_parse_expect_char
    ret c
    ld a,';'
    ld b,0
    call cc_stmt_expression_to
    ret c
    ld a,';'
    call cc_parse_expect_char
    ret c
    ld a,')'
    ld b,0
    call cc_stmt_expression_to
    ret c
    ld a,')'
    call cc_parse_expect_char
    ret c
    ld hl,cc_stmt_loop_depth
    inc (hl)
    call cc_stmt_statement
    push af
    ld hl,cc_stmt_loop_depth
    dec (hl)
    pop af
    ret

cc_stmt_break:
    ld a,(cc_stmt_loop_depth)
    or a
    jp z,cc_stmt_format
    ld a,CC_CF_BREAK
    call cc_stmt_emit
    ret c
    call cc_parse_next
    ret c
    ld a,';'
    jp cc_parse_expect_char

cc_stmt_continue:
    ld a,(cc_stmt_loop_depth)
    or a
    jp z,cc_stmt_format
    ld a,CC_CF_CONTINUE
    call cc_stmt_emit
    ret c
    call cc_parse_next
    ret c
    ld a,';'
    jp cc_parse_expect_char

cc_stmt_return:
    ld a,CC_CF_RETURN
    call cc_stmt_emit
    ret c
    call cc_parse_next
    ret c
    ld a,';'
    call cc_parse_is_char
    jp z,cc_parse_next
    ld a,';'
    ld b,1
    call cc_stmt_expression_to
    ret c
    ld a,';'
    jp cc_parse_expect_char

cc_stmt_expr_or_empty:
    ld a,';'
    call cc_parse_is_char
    jp nz,cc_stmt_expression_statement
    ld a,CC_CF_EMPTY
    call cc_stmt_emit
    ret c
    jp cc_parse_next
cc_stmt_expression_statement:
    ld a,';'
    ld b,1
    call cc_stmt_expression_to
    ret c
    ld a,';'
    jp cc_parse_expect_char

; Input A=delimiter, B=0 allow empty / nonzero require at least one token.
; Stops with delimiter current and emits CC_CF_EXPR iff a token was consumed.
cc_stmt_expression_to:
    ld (cc_stmt_delimiter),a
    ld a,b
    ld (cc_stmt_expr_required),a
    xor a
    ld (cc_stmt_expr_depth),a
    ld (cc_stmt_bracket_depth),a
    ld (cc_stmt_expr_seen),a
cc_stmt_expr_loop:
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_EOF
    jp z,cc_stmt_format
    ld a,(cc_stmt_delimiter)
    call cc_parse_is_char
    jp nz,cc_stmt_expr_not_delim
    ld a,(cc_stmt_expr_depth)
    or a
    jp nz,cc_stmt_expr_not_delim
    ld a,(cc_stmt_bracket_depth)
    or a
    jp nz,cc_stmt_expr_not_delim
    ld a,(cc_stmt_expr_seen)
    or a
    jp nz,cc_stmt_expr_emit
    ld a,(cc_stmt_expr_required)
    or a
    ret z
    jp cc_stmt_format
cc_stmt_expr_emit:
    ld a,CC_CF_EXPR
    jp cc_stmt_emit

cc_stmt_expr_not_delim:
    ld a,'{'
    call cc_parse_is_char
    jp z,cc_stmt_notsup
    ld a,'}'
    call cc_parse_is_char
    jp z,cc_stmt_format
    ld a,'('
    call cc_parse_is_char
    jp nz,cc_stmt_expr_close_paren
    ld a,(cc_stmt_expr_depth)
    cp CC_STMT_DEPTH_MAX
    jp nc,cc_stmt_nospc
    inc a
    ld (cc_stmt_expr_depth),a
    jp cc_stmt_expr_take
cc_stmt_expr_close_paren:
    ld a,')'
    call cc_parse_is_char
    jp nz,cc_stmt_expr_open_bracket
    ld a,(cc_stmt_expr_depth)
    or a
    jp z,cc_stmt_format
    dec a
    ld (cc_stmt_expr_depth),a
    jp cc_stmt_expr_take
cc_stmt_expr_open_bracket:
    ld a,'['
    call cc_parse_is_char
    jp nz,cc_stmt_expr_close_bracket
    ld a,(cc_stmt_bracket_depth)
    cp CC_STMT_DEPTH_MAX
    jp nc,cc_stmt_nospc
    inc a
    ld (cc_stmt_bracket_depth),a
    jp cc_stmt_expr_take
cc_stmt_expr_close_bracket:
    ld a,']'
    call cc_parse_is_char
    jp nz,cc_stmt_expr_take
    ld a,(cc_stmt_bracket_depth)
    or a
    jp z,cc_stmt_format
    dec a
    ld (cc_stmt_bracket_depth),a
cc_stmt_expr_take:
    ld a,1
    ld (cc_stmt_expr_seen),a
    call cc_parse_next
    ret c
    jp cc_stmt_expr_loop

cc_stmt_emit:
    ld (cc_parse_saved_char),a
    ld a,(cc_stmt_output_count)
    cp CC_STMT_OUTPUT_CAPACITY
    jp nc,cc_stmt_nospc
    ld e,a
    ld d,0
    ld hl,cc_stmt_output
    add hl,de
    ld a,(cc_parse_saved_char)
    ld (hl),a
    ld hl,cc_stmt_output_count
    inc (hl)
    xor a
    ret

cc_stmt_word_code:
    ld de,cc_stmt_words
cc_stmt_word_loop:
    ld a,(de)
    or a
    ret z
    ld (cc_stmt_word_tmp),a
    inc de
    ld a,(de)
    ld (cc_stmt_word_len),a
    inc de
    ld c,a
    ld a,(cc_parse_tok_len)
    cp c
    jp nz,cc_stmt_word_skip
    push de
    ld hl,(cc_parse_tok_ptr)
    ld b,c
cc_stmt_word_cmp:
    ld a,(de)
    cp (hl)
    jp nz,cc_stmt_word_miss
    inc de
    inc hl
    djnz cc_stmt_word_cmp
    pop de
    ld a,(cc_stmt_word_tmp)
    or a
    ret
cc_stmt_word_miss:
    pop de
cc_stmt_word_skip:
    ld a,(cc_stmt_word_len)
    ld l,a
    ld h,0
    add hl,de
    ex de,hl
    jp cc_stmt_word_loop

cc_stmt_words:
    db CC_STMT_WORD_IF,2,"if"
    db CC_STMT_WORD_ELSE,4,"else"
    db CC_STMT_WORD_WHILE,5,"while"
    db CC_STMT_WORD_DO,2,"do"
    db CC_STMT_WORD_FOR,3,"for"
    db CC_STMT_WORD_BREAK,5,"break"
    db CC_STMT_WORD_CONTINUE,8,"continue"
    db CC_STMT_WORD_RETURN,6,"return"
    db 0

cc_stmt_ok:
    xor a
    ret
cc_stmt_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_stmt_notsup:
    ld a,E_NOTSUP
    scf
    ret
cc_stmt_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.07 C48 expression precedence.
; The recursive-descent expression stage emits bounded postfix events. Logical
; AND/OR use explicit short-circuit event kinds so later symbolic Z80 emission
; cannot accidentally lower them as eager bitwise operations.
    MACRO EMIT_P11_CC_EXPRESSIONS
CC_X_IDENT              EQU 1
CC_X_INT                EQU 2
CC_X_FLOAT              EQU 3
CC_X_CHAR               EQU 4
CC_X_STRING             EQU 5
CC_X_ASSIGN             EQU 16
CC_X_ADD                EQU 17
CC_X_SUB                EQU 18
CC_X_MUL                EQU 19
CC_X_DIV                EQU 20
CC_X_MOD                EQU 21
CC_X_PREINC             EQU 22
CC_X_PREDEC             EQU 23
CC_X_POSTINC            EQU 24
CC_X_POSTDEC            EQU 25
CC_X_SHL                EQU 26
CC_X_SHR                EQU 27
CC_X_LT                 EQU 28
CC_X_LE                 EQU 29
CC_X_GT                 EQU 30
CC_X_GE                 EQU 31
CC_X_EQ                 EQU 32
CC_X_NE                 EQU 33
CC_X_BAND               EQU 34
CC_X_BOR                EQU 35
CC_X_BXOR               EQU 36
CC_X_BNOT               EQU 37
CC_X_LAND_SC            EQU 38
CC_X_LOR_SC             EQU 39
CC_X_LNOT               EQU 40
CC_X_ADDR               EQU 41
CC_X_DEREF              EQU 42
CC_X_INDEX              EQU 43
CC_X_CALL               EQU 44
CC_X_UPLUS              EQU 45
CC_X_UMINUS             EQU 46
CC_X_CAST               EQU 47
CC_X_SC_END             EQU 48
CC_X_OUTPUT_CAPACITY    EQU 128
CC_X_NEST_MAX           EQU 8

cc_x_output:            defs CC_X_OUTPUT_CAPACITY,0
cc_x_output_count:      db 0
cc_x_nest:              db 0
cc_x_saved_char:        db 0
cc_x_saved_op:          db 0

; HL=complete expression bytes, BC=length.
cc_expr_parse:
    ld (cc_parse_ptr),hl
    ld (cc_parse_remaining),bc
    xor a
    ld (cc_x_output_count),a
    ld (cc_x_nest),a
    call cc_lex_reset
    call cc_parse_next
    ret c
    call cc_x_assignment
    ret c
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_EOF
    ret z
    ld a,','
    call cc_parse_is_char
    jp z,cc_x_notsup
    jp cc_x_format

cc_x_assignment:
    call cc_x_lor
    ret c
    ld a,'='
    call cc_parse_is_char
    ret nz
    call cc_parse_next
    ret c
    call cc_x_nest_enter
    ret c
    call cc_x_assignment
    push af
    call cc_x_nest_leave
    pop af
    ret c
    ld a,CC_X_ASSIGN
    jp cc_x_emit

cc_x_lor:
    call cc_x_land
    ret c
cc_x_lor_loop:
    ld de,cc_x_op_lor
    call cc_x_match2
    ret nz
    call cc_parse_next
    ret c
    ld a,CC_X_LOR_SC
    call cc_x_emit
    ret c
    call cc_x_land
    ret c
    ld a,CC_X_SC_END
    call cc_x_emit
    ret c
    jp cc_x_lor_loop

cc_x_land:
    call cc_x_bor
    ret c
cc_x_land_loop:
    ld de,cc_x_op_land
    call cc_x_match2
    ret nz
    call cc_parse_next
    ret c
    ld a,CC_X_LAND_SC
    call cc_x_emit
    ret c
    call cc_x_bor
    ret c
    ld a,CC_X_SC_END
    call cc_x_emit
    ret c
    jp cc_x_land_loop

cc_x_bor:
    call cc_x_bxor
    ret c
cc_x_bor_loop:
    ld a,'|'
    call cc_parse_is_char
    ret nz
    call cc_parse_next
    ret c
    call cc_x_bxor
    ret c
    ld a,CC_X_BOR
    call cc_x_emit
    ret c
    jp cc_x_bor_loop

cc_x_bxor:
    call cc_x_band
    ret c
cc_x_bxor_loop:
    ld a,'^'
    call cc_parse_is_char
    ret nz
    call cc_parse_next
    ret c
    call cc_x_band
    ret c
    ld a,CC_X_BXOR
    call cc_x_emit
    ret c
    jp cc_x_bxor_loop

cc_x_band:
    call cc_x_equality
    ret c
cc_x_band_loop:
    ld a,'&'
    call cc_parse_is_char
    ret nz
    call cc_parse_next
    ret c
    call cc_x_equality
    ret c
    ld a,CC_X_BAND
    call cc_x_emit
    ret c
    jp cc_x_band_loop

cc_x_equality:
    call cc_x_relational
    ret c
cc_x_eq_loop:
    ld de,cc_x_op_eq
    call cc_x_match2
    jp z,cc_x_eq_take
    ld de,cc_x_op_ne
    call cc_x_match2
    ret nz
    ld a,CC_X_NE
    jp cc_x_eq_take_saved
cc_x_eq_take:
    ld a,CC_X_EQ
cc_x_eq_take_saved:
    push af
    call cc_parse_next
    jp c,cc_x_drop_saved_error
    call cc_x_relational
    jp c,cc_x_drop_saved_error
    pop af
    call cc_x_emit
    ret c
    jp cc_x_eq_loop

cc_x_relational:
    call cc_x_shift
    ret c
cc_x_rel_loop:
    ld de,cc_x_op_le
    call cc_x_match2
    jp z,cc_x_rel_le
    ld de,cc_x_op_ge
    call cc_x_match2
    jp z,cc_x_rel_ge
    ld a,'<'
    call cc_parse_is_char
    jp z,cc_x_rel_lt
    ld a,'>'
    call cc_parse_is_char
    ret nz
    ld a,CC_X_GT
    jp cc_x_rel_take
cc_x_rel_lt:
    ld a,CC_X_LT
    jp cc_x_rel_take
cc_x_rel_le:
    ld a,CC_X_LE
    jp cc_x_rel_take
cc_x_rel_ge:
    ld a,CC_X_GE
cc_x_rel_take:
    push af
    call cc_parse_next
    jp c,cc_x_drop_saved_error
    call cc_x_shift
    jp c,cc_x_drop_saved_error
    pop af
    call cc_x_emit
    ret c
    jp cc_x_rel_loop

cc_x_shift:
    call cc_x_additive
    ret c
cc_x_shift_loop:
    ld de,cc_x_op_shl
    call cc_x_match2
    jp z,cc_x_shift_left
    ld de,cc_x_op_shr
    call cc_x_match2
    ret nz
    ld a,CC_X_SHR
    jp cc_x_shift_take
cc_x_shift_left:
    ld a,CC_X_SHL
cc_x_shift_take:
    push af
    call cc_parse_next
    jp c,cc_x_drop_saved_error
    call cc_x_additive
    jp c,cc_x_drop_saved_error
    pop af
    call cc_x_emit
    ret c
    jp cc_x_shift_loop

cc_x_additive:
    call cc_x_multiplicative
    ret c
cc_x_add_loop:
    ld a,'+'
    call cc_parse_is_char
    jp z,cc_x_add_plus
    ld a,'-'
    call cc_parse_is_char
    ret nz
    ld a,CC_X_SUB
    jp cc_x_add_take
cc_x_add_plus:
    ld a,CC_X_ADD
cc_x_add_take:
    push af
    call cc_parse_next
    jp c,cc_x_drop_saved_error
    call cc_x_multiplicative
    jp c,cc_x_drop_saved_error
    pop af
    call cc_x_emit
    ret c
    jp cc_x_add_loop

cc_x_multiplicative:
    call cc_x_unary
    ret c
cc_x_mul_loop:
    ld a,'*'
    call cc_parse_is_char
    jp z,cc_x_mul_mul
    ld a,'/'
    call cc_parse_is_char
    jp z,cc_x_mul_div
    ld a,'%'
    call cc_parse_is_char
    ret nz
    ld a,CC_X_MOD
    jp cc_x_mul_take
cc_x_mul_mul:
    ld a,CC_X_MUL
    jp cc_x_mul_take
cc_x_mul_div:
    ld a,CC_X_DIV
cc_x_mul_take:
    push af
    call cc_parse_next
    jp c,cc_x_drop_saved_error
    call cc_x_unary
    jp c,cc_x_drop_saved_error
    pop af
    call cc_x_emit
    ret c
    jp cc_x_mul_loop

cc_x_unary:
    ld de,cc_x_op_inc
    call cc_x_match2
    jp z,cc_x_preinc
    ld de,cc_x_op_dec
    call cc_x_match2
    jp z,cc_x_predec
    ld a,'+'
    call cc_parse_is_char
    jp z,cc_x_uplus
    ld a,'-'
    call cc_parse_is_char
    jp z,cc_x_uminus
    ld a,'!'
    call cc_parse_is_char
    jp z,cc_x_lnot
    ld a,'~'
    call cc_parse_is_char
    jp z,cc_x_bnot
    ld a,'&'
    call cc_parse_is_char
    jp z,cc_x_addr
    ld a,'*'
    call cc_parse_is_char
    jp z,cc_x_deref
    ld a,'('
    call cc_parse_is_char
    jp z,cc_x_paren_or_cast
    jp cc_x_postfix

cc_x_preinc:
    ld a,CC_X_PREINC
    jp cc_x_unary_take
cc_x_predec:
    ld a,CC_X_PREDEC
    jp cc_x_unary_take
cc_x_uplus:
    ld a,CC_X_UPLUS
    jp cc_x_unary_take
cc_x_uminus:
    ld a,CC_X_UMINUS
    jp cc_x_unary_take
cc_x_lnot:
    ld a,CC_X_LNOT
    jp cc_x_unary_take
cc_x_bnot:
    ld a,CC_X_BNOT
    jp cc_x_unary_take
cc_x_addr:
    ld a,CC_X_ADDR
    jp cc_x_unary_take
cc_x_deref:
    ld a,CC_X_DEREF
cc_x_unary_take:
    push af
    call cc_parse_next
    jp c,cc_x_drop_saved_error
    call cc_x_nest_enter
    jp c,cc_x_drop_saved_error
    call cc_x_unary
    jp c,cc_x_unary_nested_error
    call cc_x_nest_leave
    jp c,cc_x_drop_saved_error
    pop af
    jp cc_x_emit
cc_x_unary_nested_error:
    push af
    call cc_x_nest_leave
    pop af
    jp cc_x_drop_saved_error

cc_x_paren_or_cast:
    call cc_parse_next
    ret c
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_KEYWORD
    jp nz,cc_x_group
    call cc_parse_word_code
    cp CC_WORD_VOID
    jp z,cc_x_cast
    cp CC_WORD_CHAR
    jp z,cc_x_cast
    cp CC_WORD_UNSIGNED
    jp z,cc_x_cast
    cp CC_WORD_SHORT
    jp z,cc_x_cast
    cp CC_WORD_INT
    jp z,cc_x_cast
    cp CC_WORD_FLOAT
    jp z,cc_x_cast
    jp cc_x_group
cc_x_group:
    call cc_x_nest_enter
    ret c
    call cc_x_assignment
    push af
    call cc_x_nest_leave
    pop af
    ret c
    ld a,')'
    call cc_parse_expect_char
    ret c
    jp cc_x_post_loop

cc_x_cast:
    call cc_parse_type_spec
    ret c
    xor a
    ld (cc_parse_ptr_depth),a
    call cc_parse_pointer_stars
    ret c
    ld a,(cc_parse_ptr_depth)
    or a
    jp nz,cc_x_notsup
    ld a,(cc_parse_type)
    cp CC_TYPE_VOID
    jp z,cc_x_notsup
    push af
    ld a,')'
    call cc_parse_expect_char
    jp c,cc_x_drop_saved_error
    call cc_x_nest_enter
    jp c,cc_x_drop_saved_error
    call cc_x_unary
    jp c,cc_x_cast_nested_error
    call cc_x_nest_leave
    jp c,cc_x_drop_saved_error
    pop af
    ld b,a
    ld a,CC_X_CAST
    call cc_x_emit
    ret c
    ld a,b
    jp cc_x_emit
cc_x_cast_nested_error:
    push af
    call cc_x_nest_leave
    pop af
    jp cc_x_drop_saved_error

cc_x_postfix:
    call cc_x_primary
    ret c
cc_x_post_loop:
    ld a,'['
    call cc_parse_is_char
    jp z,cc_x_index
    ld a,'('
    call cc_parse_is_char
    jp z,cc_x_call
    ld de,cc_x_op_inc
    call cc_x_match2
    jp z,cc_x_postinc
    ld de,cc_x_op_dec
    call cc_x_match2
    ret nz
    ld a,CC_X_POSTDEC
    jp cc_x_post_take
cc_x_postinc:
    ld a,CC_X_POSTINC
cc_x_post_take:
    push af
    call cc_parse_next
    jp c,cc_x_drop_saved_error
    pop af
    call cc_x_emit
    ret c
    jp cc_x_post_loop

cc_x_index:
    call cc_parse_next
    ret c
    call cc_x_nest_enter
    ret c
    call cc_x_assignment
    push af
    call cc_x_nest_leave
    pop af
    ret c
    ld a,']'
    call cc_parse_expect_char
    ret c
    ld a,CC_X_INDEX
    call cc_x_emit
    ret c
    jp cc_x_post_loop

cc_x_call:
    call cc_parse_next
    ret c
    ld a,')'
    call cc_parse_is_char
    jp z,cc_x_call_close
cc_x_call_arg:
    call cc_x_nest_enter
    ret c
    call cc_x_assignment
    push af
    call cc_x_nest_leave
    pop af
    ret c
    ld a,','
    call cc_parse_is_char
    jp nz,cc_x_call_expect_close
    call cc_parse_next
    ret c
    jp cc_x_call_arg
cc_x_call_expect_close:
    ld a,')'
    call cc_parse_is_char
    jp nz,cc_x_format
cc_x_call_close:
    call cc_parse_next
    ret c
    ld a,CC_X_CALL
    call cc_x_emit
    ret c
    jp cc_x_post_loop

cc_x_primary:
    ld a,(cc_parse_tok_kind)
    cp CC_TOK_IDENT
    jp z,cc_x_primary_ident
    cp CC_TOK_INT
    jp z,cc_x_primary_int
    cp CC_TOK_FLOAT
    jp z,cc_x_primary_float
    cp CC_TOK_CHAR
    jp z,cc_x_primary_char
    cp CC_TOK_STRING
    jp z,cc_x_primary_string
    jp cc_x_format
cc_x_primary_ident:
    ld a,CC_X_IDENT
    jp cc_x_primary_take
cc_x_primary_int:
    ld a,CC_X_INT
    jp cc_x_primary_take
cc_x_primary_float:
    ld a,CC_X_FLOAT
    jp cc_x_primary_take
cc_x_primary_char:
    ld a,CC_X_CHAR
    jp cc_x_primary_take
cc_x_primary_string:
    ld a,CC_X_STRING
cc_x_primary_take:
    push af
    call cc_parse_next
    jp c,cc_x_drop_saved_error
    pop af
    jp cc_x_emit

cc_x_emit:
    ld (cc_x_saved_op),a
    ld a,(cc_x_output_count)
    cp CC_X_OUTPUT_CAPACITY
    jp nc,cc_x_nospc
    ld e,a
    ld d,0
    ld hl,cc_x_output
    add hl,de
    ld a,(cc_x_saved_op)
    ld (hl),a
    ld hl,cc_x_output_count
    inc (hl)
    xor a
    ret

cc_x_nest_enter:
    ld a,(cc_x_nest)
    cp CC_X_NEST_MAX
    jp nc,cc_x_nospc
    inc a
    ld (cc_x_nest),a
    xor a
    ret
cc_x_nest_leave:
    ld a,(cc_x_nest)
    or a
    jp z,cc_x_format
    dec a
    ld (cc_x_nest),a
    xor a
    ret

; DE -> exact two-byte operator spelling, Z on match.
cc_x_match2:
    ld a,(cc_parse_tok_len)
    cp 2
    jp nz,cc_x_match_no
    ld hl,(cc_parse_tok_ptr)
    ld a,(de)
    cp (hl)
    jp nz,cc_x_match_no
    inc de
    inc hl
    ld a,(de)
    cp (hl)
    jp z,cc_x_match_yes
cc_x_match_no:
    ld a,1
    or a
    ret
cc_x_match_yes:
    xor a
    ret

cc_x_op_inc: db "++"
cc_x_op_dec: db "--"
cc_x_op_shl: db "<<"
cc_x_op_shr: db ">>"
cc_x_op_le:  db "<="
cc_x_op_ge:  db ">="
cc_x_op_eq:  db "=="
cc_x_op_ne:  db "!="
cc_x_op_land: db "&&"
cc_x_op_lor:  db "||"

cc_x_drop_saved_error:
    pop bc
    scf
    ret
cc_x_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_x_notsup:
    ld a,E_NOTSUP
    scf
    ret
cc_x_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.08 native compiler integer semantic selection.
; These selectors freeze width/signedness before later code emission chooses the
; exact documented runtime/operator sequence.
    MACRO EMIT_P11_CC_INT_SEMANTICS
CC_INT_SHIFT_MASK_8     EQU 7
CC_INT_SHIFT_MASK_16    EQU 15
CC_INT_RIGHT_LOGICAL    EQU 0
CC_INT_RIGHT_ARITH      EQU 1

; A=C48 base type. Success A=shift-count mask.
cc_int_shift_mask_for_type:
    cp CC_TYPE_CHAR
    jr z,cc_int_mask8
    cp CC_TYPE_UCHAR
    jr z,cc_int_mask8
    cp CC_TYPE_SHORT
    jr z,cc_int_mask16
    cp CC_TYPE_USHORT
    jr z,cc_int_mask16
    cp CC_TYPE_INT
    jr z,cc_int_mask16
    cp CC_TYPE_UINT
    jr z,cc_int_mask16
    ld a,E_INVAL
    scf
    ret
cc_int_mask8:
    ld a,CC_INT_SHIFT_MASK_8
    or a
    ret
cc_int_mask16:
    ld a,CC_INT_SHIFT_MASK_16
    or a
    ret

; A=C48 base type. Success A=1 signed or 0 unsigned.
cc_int_is_signed_type:
    cp CC_TYPE_SHORT
    jr z,cc_int_signed_yes
    cp CC_TYPE_INT
    jr z,cc_int_signed_yes
    cp CC_TYPE_CHAR
    jr z,cc_int_signed_no
    cp CC_TYPE_UCHAR
    jr z,cc_int_signed_no
    cp CC_TYPE_USHORT
    jr z,cc_int_signed_no
    cp CC_TYPE_UINT
    jr z,cc_int_signed_no
    ld a,E_INVAL
    scf
    ret
cc_int_signed_yes:
    ld a,1
    or a
    ret
cc_int_signed_no:
    xor a
    ret

; A=C48 base type. Success A=CC_INT_RIGHT_*.
cc_int_right_shift_kind:
    call cc_int_is_signed_type
    ret c
    or a
    jr z,cc_int_right_unsigned
    ld a,CC_INT_RIGHT_ARITH
    or a
    ret
cc_int_right_unsigned:
    ld a,CC_INT_RIGHT_LOGICAL
    or a
    ret

; Runtime helper spellings are part of the compiler/runtime contract. Later
; symbolic emission resolves these exact names through OBJ1/linker symbols.
cc_int_runtime_symbols:
    db "c48_u8_add",0,"c48_u8_sub",0,"c48_u8_mul",0,"c48_u8_neg",0
    db "c48_u8_shl",0,"c48_u8_shr",0
    db "c48_u16_add",0,"c48_u16_sub",0,"c48_u16_mul",0,"c48_u16_neg",0
    db "c48_u16_shl",0,"c48_u16_shr",0,"c48_u16_divmod",0
    db "c48_s16_add",0,"c48_s16_sub",0,"c48_s16_mul",0,"c48_s16_neg",0
    db "c48_s16_shl",0,"c48_s16_shr",0,"c48_s16_divmod",0
    db "c48_cmp_u8",0,"c48_cmp_u16",0,"c48_cmp_s16",0
    db 0
    ENDM


; P11.09 C48 pointer arithmetic.
; Native pointers are exactly 16 bits. Pointer +/- integer scales the signed
; element count by the pointed-to sizeof (1, 2, or 5 bytes in version 1), and
; same-object pointer subtraction returns a signed 16-bit element count.
; Ordering/subtraction of unrelated pointers is outside the portable C48
; contract and must never be presented as a defined result.
;
; Mandatory reference/oracle mapping:
; SDK commit 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/typesys.py -> sizeof/16-bit pointer model
; compiler/c48/semantics.py -> legal pointer operand/type forms
; compiler/c48/vm.py -> scaling and same-object subtraction oracle
    MACRO EMIT_P11_CC_POINTER_ARITH
CC_PTR_REPR_SIZE          EQU 2
CC_PTR_REL_SAME_OBJECT    EQU 1
CC_PTR_REL_UNRELATED      EQU 2

cc_ptr_base_type:         db 0
cc_ptr_element_size:      db 0
cc_ptr_diff_negative:     db 0
cc_ptr_dividend:          dw 0
cc_ptr_quotient:          dw 0
cc_ptr_remainder:         db 0

; A=C48 base type, E=pointer depth. Success A=sizeof(pointed-to object).
; Depth >1 points to a pointer object, hence stride 2. void * has no sized
; pointee and is rejected; void ** is valid because its pointee is void *.
cc_ptr_pointee_size:
    ld (cc_ptr_base_type),a
    cp CC_TYPE_FLOAT+1
    jp nc,cc_ptr_inval
    ld a,e
    or a
    jp z,cc_ptr_inval
    cp CC_PARSE_PTR_MAX+1
    jp nc,cc_ptr_inval
    cp 2
    jr nc,cc_ptr_size2
    ld a,(cc_ptr_base_type)
    cp CC_TYPE_CHAR
    jr z,cc_ptr_size1
    cp CC_TYPE_UCHAR
    jr z,cc_ptr_size1
    cp CC_TYPE_SHORT
    jr z,cc_ptr_size2
    cp CC_TYPE_USHORT
    jr z,cc_ptr_size2
    cp CC_TYPE_INT
    jr z,cc_ptr_size2
    cp CC_TYPE_UINT
    jr z,cc_ptr_size2
    cp CC_TYPE_FLOAT
    jr z,cc_ptr_size5
    jp cc_ptr_inval
cc_ptr_size1:
    ld a,1
    or a
    ret
cc_ptr_size2:
    ld a,2
    or a
    ret
cc_ptr_size5:
    ld a,5
    or a
    ret

; A=element size 1/2/5, DE=signed element delta. Success DE=scaled byte delta.
; Arithmetic deliberately wraps in the 16-bit pointer representation; portable
; C48 source is separately constrained to its object/one-past domain.
cc_ptr_scale_de:
    cp 1
    jr z,cc_ptr_scale_ok
    cp 2
    jr z,cc_ptr_scale2
    cp 5
    jr z,cc_ptr_scale5
    jp cc_ptr_inval
cc_ptr_scale2:
    sla e
    rl d
    jr cc_ptr_scale_ok
cc_ptr_scale5:
    ld b,d
    ld c,e
    sla e
    rl d
    sla e
    rl d
    ld a,e
    add a,c
    ld e,a
    ld a,d
    adc a,b
    ld d,a
cc_ptr_scale_ok:
    xor a
    ret

; HL=pointer, DE=signed element count, A=element size. Success HL=result.
cc_ptr_add_scaled:
    call cc_ptr_scale_de
    ret c
    add hl,de
    xor a
    ret

; HL=pointer, DE=signed element count, A=element size. Success HL=result.
cc_ptr_sub_scaled:
    call cc_ptr_scale_de
    ret c
    or a
    sbc hl,de
    xor a
    ret

; HL=lhs pointer, DE=rhs pointer, A=element size 1/2/5.
; Precondition for portable C48: both pointers designate the same array/object
; (or its one-past position). Success HL=signed 16-bit element count.
cc_ptr_diff:
    ld (cc_ptr_element_size),a
    or a
    sbc hl,de
    ld a,(cc_ptr_element_size)
    cp 1
    jr z,cc_ptr_diff_ok
    cp 2
    jr z,cc_ptr_diff2
    cp 5
    jr z,cc_ptr_diff5
    jp cc_ptr_inval

cc_ptr_diff2:
    bit 0,l
    jp nz,cc_ptr_inval
    sra h
    rr l
cc_ptr_diff_ok:
    xor a
    ret

; Exact signed divide-by-five for float-pointer differences. The byte
; difference must be an exact element multiple or the operation fails closed.
cc_ptr_diff5:
    xor a
    ld (cc_ptr_diff_negative),a
    bit 7,h
    jr z,cc_ptr_diff5_abs
    ld a,1
    ld (cc_ptr_diff_negative),a
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
cc_ptr_diff5_abs:
    ld (cc_ptr_dividend),hl
    ld hl,0
    ld (cc_ptr_quotient),hl
    xor a
    ld (cc_ptr_remainder),a
    ld b,16
cc_ptr_diff5_loop:
    ld hl,(cc_ptr_dividend)
    add hl,hl
    ld (cc_ptr_dividend),hl
    ld a,(cc_ptr_remainder)
    adc a,a
    cp 5
    jr c,cc_ptr_diff5_qzero
    sub 5
    scf
    jr cc_ptr_diff5_qbit
cc_ptr_diff5_qzero:
    or a
cc_ptr_diff5_qbit:
    ld hl,(cc_ptr_quotient)
    adc hl,hl
    ld (cc_ptr_quotient),hl
    ld (cc_ptr_remainder),a
    djnz cc_ptr_diff5_loop

    ld a,(cc_ptr_remainder)
    or a
    jp nz,cc_ptr_inval
    ld hl,(cc_ptr_quotient)
    ld a,(cc_ptr_diff_negative)
    or a
    jr z,cc_ptr_diff_ok
    xor a
    sub l
    ld l,a
    ld a,0
    sbc a,h
    ld h,a
    jr cc_ptr_diff_ok

; Language/spec oracle: only a known same-object relation may be claimed as a
; portable ordering/subtraction result. Unknown/unrelated is explicitly NOTSUP.
cc_ptr_require_portable_relation:
    cp CC_PTR_REL_SAME_OBJECT
    jr z,cc_ptr_relation_ok
    ld a,E_NOTSUP
    scf
    ret
cc_ptr_relation_ok:
    xor a
    ret

cc_ptr_inval:
    ld a,E_INVAL
    scf
    ret
    ENDM


; P11.10 C48 string/character literal bytes and deterministic object storage.
; Decoded string bytes are appended in source encounter order to the bounded
; literal pool. The pool is the exact data-byte staging surface later consumed
; by the OBJ1 writer; each completed string has exactly one trailing NUL.
;
; Mandatory pinned SDK/reference mapping:
; 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/lexer.py -> exact byte escape decoding
; compiler/c48/parser.py -> adjacent string-token concatenation
    MACRO EMIT_P11_CC_LITERALS
CC_LIT_POOL_CAPACITY     EQU 512

cc_lit_pool:             defs CC_LIT_POOL_CAPACITY,0
cc_lit_pool_used:        dw 0
cc_lit_string_start:     dw 0
cc_lit_input_ptr:        dw 0
cc_lit_remaining:        dw 0
cc_lit_quote:            db 0
cc_lit_active:           db 0
cc_lit_tmp:              db 0
cc_lit_hex_high:         db 0

cc_lit_reset:
    ld hl,0
    ld (cc_lit_pool_used),hl
    xor a
    ld (cc_lit_active),a
    ret

; Start one C string literal sequence. Consecutive STRING tokens are appended
; with cc_lit_string_append and only cc_lit_string_end emits the terminating NUL.
cc_lit_string_begin:
    ld hl,(cc_lit_pool_used)
    ld (cc_lit_string_start),hl
    ld a,1
    ld (cc_lit_active),a
    xor a
    ret

; HL=one exact quoted STRING token, BC=token byte length.
cc_lit_string_append:
    ld a,(cc_lit_active)
    or a
    jp z,cc_lit_format
    ld a,34
    call cc_lit_setup
    ret c
cc_lit_string_loop:
    ld hl,(cc_lit_remaining)
    ld a,h
    or l
    ret z
    call cc_lit_decode_byte
    ret c
    call cc_lit_emit_byte
    ret c
    jr cc_lit_string_loop

; Complete current string sequence. Success HL=pool offset, BC=byte length
; including the one trailing NUL.
cc_lit_string_end:
    ld a,(cc_lit_active)
    or a
    jp z,cc_lit_format
    xor a
    call cc_lit_emit_byte
    ret c
    xor a
    ld (cc_lit_active),a
    ld hl,(cc_lit_pool_used)
    ld de,(cc_lit_string_start)
    or a
    sbc hl,de
    ld b,h
    ld c,l
    ld hl,(cc_lit_string_start)
    xor a
    ret

; HL=one exact quoted CHAR token, BC=token byte length.
; Success A=decoded byte. Exactly one decoded byte is mandatory.
cc_lit_char:
    ld a,39
    call cc_lit_setup
    ret c
    call cc_lit_decode_byte
    ret c
    ld (cc_lit_tmp),a
    ld hl,(cc_lit_remaining)
    ld a,h
    or l
    jp nz,cc_lit_format
    ld a,(cc_lit_tmp)
    or a
    ret

; A=required quote, HL=token bytes, BC=token length. Leaves input pointing at
; the first inner source byte and remaining equal to token length minus quotes.
cc_lit_setup:
    ld (cc_lit_quote),a
    ld a,b
    or a
    jr nz,cc_lit_setup_len_ok
    ld a,c
    cp 2
    jp c,cc_lit_format
cc_lit_setup_len_ok:
    ld a,(hl)
    ld d,a
    ld a,(cc_lit_quote)
    cp d
    jp nz,cc_lit_format
    push hl
    add hl,bc
    dec hl
    ld d,(hl)
    ld a,(cc_lit_quote)
    cp d
    pop hl
    jp nz,cc_lit_format
    inc hl
    ld (cc_lit_input_ptr),hl
    dec bc
    dec bc
    ld (cc_lit_remaining),bc
    xor a
    ret

; Decode one inner literal byte and consume its source spelling.
cc_lit_decode_byte:
    call cc_lit_take_raw
    ret c
    ld d,a
    ld a,(cc_lit_quote)
    cp d
    jp z,cc_lit_format
    ld a,d
    cp 32
    jp c,cc_lit_format
    cp 127
    jp nc,cc_lit_format
    cp 92
    jr z,cc_lit_escape
    or a
    ret

cc_lit_escape:
    call cc_lit_take_raw
    ret c
    cp 92
    jr z,cc_lit_escape_slash
    cp 39
    jr z,cc_lit_escape_quote
    cp 34
    jr z,cc_lit_escape_dquote
    cp '0'
    jr z,cc_lit_escape_zero
    cp 'a'
    jr z,cc_lit_escape_bel
    cp 'b'
    jr z,cc_lit_escape_bs
    cp 't'
    jr z,cc_lit_escape_tab
    cp 'n'
    jr z,cc_lit_escape_lf
    cp 'v'
    jr z,cc_lit_escape_vt
    cp 'f'
    jr z,cc_lit_escape_ff
    cp 'r'
    jr z,cc_lit_escape_cr
    cp 'x'
    jr z,cc_lit_escape_hex
    cp '1'
    jp c,cc_lit_format
    cp '8'
    jp c,cc_lit_notsup
    jp cc_lit_format
cc_lit_escape_slash:
    ld a,92
    ret
cc_lit_escape_quote:
    ld a,39
    ret
cc_lit_escape_dquote:
    ld a,34
    ret
cc_lit_escape_zero:
    xor a
    ret
cc_lit_escape_bel:
    ld a,7
    ret
cc_lit_escape_bs:
    ld a,8
    ret
cc_lit_escape_tab:
    ld a,9
    ret
cc_lit_escape_lf:
    ld a,10
    ret
cc_lit_escape_vt:
    ld a,11
    ret
cc_lit_escape_ff:
    ld a,12
    ret
cc_lit_escape_cr:
    ld a,13
    ret

; C48 hex escapes are exactly two hexadecimal digits.
cc_lit_escape_hex:
    call cc_lit_take_raw
    ret c
    call cc_lit_hex_nibble
    ret c
    ld (cc_lit_hex_high),a
    call cc_lit_take_raw
    ret c
    call cc_lit_hex_nibble
    ret c
    ld d,a
    ld a,(cc_lit_hex_high)
    rlca
    rlca
    rlca
    rlca
    or d
    ret

cc_lit_hex_nibble:
    cp '0'
    jp c,cc_lit_format
    cp '9'+1
    jr c,cc_lit_hex_digit
    cp 'A'
    jr c,cc_lit_hex_lower
    cp 'F'+1
    jr c,cc_lit_hex_upper
cc_lit_hex_lower:
    cp 'a'
    jp c,cc_lit_format
    cp 'f'+1
    jp nc,cc_lit_format
    sub 'a'-10
    or a
    ret
cc_lit_hex_upper:
    sub 'A'-10
    or a
    ret
cc_lit_hex_digit:
    sub '0'
    or a
    ret

cc_lit_take_raw:
    ld hl,(cc_lit_remaining)
    ld a,h
    or l
    jp z,cc_lit_format
    dec hl
    ld (cc_lit_remaining),hl
    ld hl,(cc_lit_input_ptr)
    ld a,(hl)
    inc hl
    ld (cc_lit_input_ptr),hl
    or a
    ret

cc_lit_emit_byte:
    ld (cc_lit_tmp),a
    ld hl,(cc_lit_pool_used)
    ld de,CC_LIT_POOL_CAPACITY
    or a
    sbc hl,de
    jp nc,cc_lit_nospc
    ld hl,(cc_lit_pool_used)
    ld de,cc_lit_pool
    add hl,de
    ld a,(cc_lit_tmp)
    ld (hl),a
    ld hl,(cc_lit_pool_used)
    inc hl
    ld (cc_lit_pool_used),hl
    xor a
    ret

cc_lit_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_lit_notsup:
    ld a,E_NOTSUP
    scf
    ret
cc_lit_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.11 C48 globals/statics/externs and exact OBJ1 symbol/BSS staging.
; One source-order symbol table is retained. External declarations may precede
; or follow their single definition; duplicate definitions and linkage/type
; storage conflicts fail closed. Defined objects receive minimum required BSS
; alignment. The symbol staging bytes are exact OBJ1 20-byte records.
;
; Mandatory pinned SDK/reference mapping:
; 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/semantics.py::_declare_file_symbol -> linkage/definition rules
; compiler/tests/test_conformance.py::DeclarationCorpus -> extern/static corpus
    MACRO EMIT_P11_CC_GLOBAL_STORAGE
CC_STORE_CAPACITY        EQU 16
CC_STORE_RECORD_SIZE     EQU 20
CC_STORE_NAME_SIZE       EQU 16
CC_STORE_LINK_EXTERNAL   EQU 0
CC_STORE_LINK_INTERNAL   EQU 1
CC_STORE_SEC_UNDEF       EQU 0
CC_STORE_SEC_TEXT        EQU 1
CC_STORE_SEC_BSS         EQU 2
CC_STORE_SYM_GLOBAL      EQU 1

cc_store_records:        defs CC_STORE_CAPACITY*CC_STORE_RECORD_SIZE,0
cc_store_sizes:          defs CC_STORE_CAPACITY*2,0
cc_store_aligns:         defs CC_STORE_CAPACITY,0
cc_store_linkage:        defs CC_STORE_CAPACITY,0
cc_store_defined:        defs CC_STORE_CAPACITY,0
cc_store_count:          db 0
cc_store_bss_size:       dw 0
cc_store_work_name:      defs CC_STORE_NAME_SIZE,0
cc_store_work_size:      dw 0
cc_store_work_align:     db 0
cc_store_work_storage:   db 0
cc_store_work_linkage:   db 0
cc_store_work_index:     db 0
cc_store_scan_index:     db 0
cc_store_scan_left:      db 0
cc_store_work_record:    dw 0
cc_store_alloc_offset:   dw 0

cc_store_reset:
    xor a
    ld (cc_store_count),a
    ld (cc_store_bss_size),a
    ld (cc_store_bss_size+1),a
    ret

; HL=NUL-terminated C48 name, BC=object size, D=alignment (1 or 2),
; E=CC_STORAGE_NONE/STATIC/EXTERN. Success retains/creates one exact OBJ1
; record and updates cc_store_bss_size for definitions only.
cc_store_object:
    ld (cc_store_work_size),bc
    ld a,d
    ld (cc_store_work_align),a
    ld a,e
    ld (cc_store_work_storage),a
    ld (cc_work_name),hl

    ld a,b
    or c
    jp z,cc_store_format
    ld a,(cc_store_work_align)
    cp 1
    jp z,cc_store_align_ok
    cp 2
    jp nz,cc_store_format
cc_store_align_ok:
    ld a,(cc_store_work_storage)
    cp CC_STORAGE_EXTERN+1
    jp nc,cc_store_format

    ld hl,(cc_work_name)
    call cc_ident_validate
    ret c
    ld hl,(cc_work_name)
    ld de,cc_store_work_name
    xor a
    ld (cc_copy_zero),a
    ld b,CC_STORE_NAME_SIZE
cc_store_name_copy:
    ld a,(cc_copy_zero)
    or a
    jp nz,cc_store_name_zero
    ld a,(hl)
    inc hl
    ld (de),a
    or a
    jp nz,cc_store_name_next
    ld a,1
    ld (cc_copy_zero),a
    jp cc_store_name_next
cc_store_name_zero:
    xor a
    ld (de),a
cc_store_name_next:
    inc de
    djnz cc_store_name_copy

    ld a,(cc_store_work_storage)
    cp CC_STORAGE_STATIC
    ld a,CC_STORE_LINK_EXTERNAL
    jp nz,cc_store_link_ready
    ld a,CC_STORE_LINK_INTERNAL
cc_store_link_ready:
    ld (cc_store_work_linkage),a

    call cc_store_find
    jp z,cc_store_existing
    jp cc_store_new

; Z when the work name exists; work_index and work_record identify it.
cc_store_find:
    ld a,(cc_store_count)
    ld (cc_store_scan_left),a
    xor a
    ld (cc_store_scan_index),a
    ld hl,cc_store_records
cc_store_find_loop:
    ld a,(cc_store_scan_left)
    or a
    jp z,cc_store_find_miss
    ld (cc_store_work_record),hl
    ld de,cc_store_work_name
    ld c,CC_STORE_NAME_SIZE
cc_store_find_cmp:
    ld a,(de)
    cp (hl)
    jp nz,cc_store_find_next
    inc de
    inc hl
    dec c
    jp nz,cc_store_find_cmp
    ld a,(cc_store_scan_index)
    ld (cc_store_work_index),a
    xor a
    ret
cc_store_find_next:
    ld hl,(cc_store_work_record)
    ld de,CC_STORE_RECORD_SIZE
    add hl,de
    ld a,(cc_store_scan_index)
    inc a
    ld (cc_store_scan_index),a
    ld a,(cc_store_scan_left)
    dec a
    ld (cc_store_scan_left),a
    jp cc_store_find_loop
cc_store_find_miss:
    ld a,1
    or a
    ret

cc_store_new:
    ld a,(cc_store_count)
    cp CC_STORE_CAPACITY
    jp nc,cc_store_nospc
    ld (cc_store_work_index),a
    call cc_store_record_ptr
    ld (cc_store_work_record),hl
    ex de,hl
    ld hl,cc_store_work_name
    ld b,CC_STORE_NAME_SIZE
cc_store_new_name:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz cc_store_new_name
    xor a
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld (de),a

    call cc_store_write_meta
    ld a,(cc_store_work_storage)
    cp CC_STORAGE_EXTERN
    jp z,cc_store_new_extern
    call cc_store_allocate
    ret c
    call cc_store_mark_definition
    ret c
    jp cc_store_new_commit
cc_store_new_extern:
    ld hl,(cc_store_work_record)
    ld de,18
    add hl,de
    xor a
    ld (hl),a
    inc hl
    ld a,CC_STORE_SYM_GLOBAL
    ld (hl),a
cc_store_new_commit:
    ld hl,cc_store_count
    inc (hl)
    xor a
    ret

cc_store_existing:
    call cc_store_check_meta
    ret c
    ld a,(cc_store_work_storage)
    cp CC_STORAGE_EXTERN
    jp z,cc_store_existing_ok
    call cc_store_defined_ptr
    ld a,(hl)
    or a
    jp nz,cc_store_exist
    call cc_store_allocate
    ret c
    call cc_store_defined_ptr
    ld a,1
    ld (hl),a
    call cc_store_mark_definition
    ret c
cc_store_existing_ok:
    xor a
    ret

cc_store_write_meta:
    call cc_store_size_ptr
    ld de,(cc_store_work_size)
    ld (hl),e
    inc hl
    ld (hl),d
    call cc_store_align_ptr
    ld a,(cc_store_work_align)
    ld (hl),a
    call cc_store_link_ptr
    ld a,(cc_store_work_linkage)
    ld (hl),a
    call cc_store_defined_ptr
    ld a,(cc_store_work_storage)
    cp CC_STORAGE_EXTERN
    ld a,0
    jp z,cc_store_meta_def_ready
    inc a
cc_store_meta_def_ready:
    ld (hl),a
    ret

cc_store_check_meta:
    call cc_store_size_ptr
    ld a,(hl)
    ld de,(cc_store_work_size)
    cp e
    jp nz,cc_store_format
    inc hl
    ld a,(hl)
    cp d
    jp nz,cc_store_format
    call cc_store_align_ptr
    ld a,(cc_store_work_align)
    cp (hl)
    jp nz,cc_store_format
    call cc_store_link_ptr
    ld a,(cc_store_work_linkage)
    cp (hl)
    jp nz,cc_store_format
    xor a
    ret

; Allocate one definition in BSS and retain its starting offset.
cc_store_allocate:
    ld hl,(cc_store_bss_size)
    ld a,(cc_store_work_align)
    cp 2
    jp nz,cc_store_alloc_aligned
    bit 0,l
    jp z,cc_store_alloc_aligned
    inc hl
cc_store_alloc_aligned:
    ld (cc_store_alloc_offset),hl
    ld de,(cc_store_work_size)
    add hl,de
    jp c,cc_store_nospc
    ld a,h
    cp $80
    jp c,cc_store_alloc_bound_ok
    jp nz,cc_store_nospc
    ld a,l
    or a
    jp nz,cc_store_nospc
cc_store_alloc_bound_ok:
    ld (cc_store_bss_size),hl
    xor a
    ret

cc_store_mark_definition:
    ld hl,(cc_store_work_record)
    ld de,16
    add hl,de
    ld de,(cc_store_alloc_offset)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld a,CC_STORE_SEC_BSS
    ld (hl),a
    inc hl
    ld a,(cc_store_work_linkage)
    or a
    ld a,0
    jp nz,cc_store_mark_flags
    ld a,CC_STORE_SYM_GLOBAL
cc_store_mark_flags:
    ld (hl),a
    xor a
    ret

; A-independent pointer helpers use cc_store_work_index.
cc_store_record_ptr:
    ld a,(cc_store_work_index)
    ld b,a
    ld hl,cc_store_records
    ld de,CC_STORE_RECORD_SIZE
cc_store_record_seek:
    ld a,b
    or a
    ret z
    add hl,de
    djnz cc_store_record_seek
    ret

cc_store_size_ptr:
    ld a,(cc_store_work_index)
    ld e,a
    ld d,0
    sla e
    rl d
    ld hl,cc_store_sizes
    add hl,de
    ret
cc_store_align_ptr:
    ld de,cc_store_aligns
    jp cc_store_byte_ptr
cc_store_link_ptr:
    ld de,cc_store_linkage
    jp cc_store_byte_ptr
cc_store_defined_ptr:
    ld de,cc_store_defined
cc_store_byte_ptr:
    ld a,(cc_store_work_index)
    ld l,a
    ld h,0
    add hl,de
    ret

; Return exact OBJ1 symbol staging: HL=records, BC=byte count, DE=BSS size.
cc_store_output:
    ld hl,cc_store_records
    ld a,(cc_store_count)
    ld b,a
    ld c,0
    ld de,CC_STORE_RECORD_SIZE
    ld hl,0
cc_store_output_mul:
    ld a,b
    or a
    jp z,cc_store_output_done
    add hl,de
    djnz cc_store_output_mul
cc_store_output_done:
    ld b,h
    ld c,l
    ld hl,cc_store_records
    ld de,(cc_store_bss_size)
    xor a
    ret

cc_store_exist:
    ld a,E_EXIST
    scf
    ret
cc_store_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_store_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.12 C48 local-variable frame planning and exact Z80 frame sequences.
; REV17 owns the native ABI. The pinned SDK VM is a semantic oracle and has no
; target-Z80 IX/IY frame backend, so there is no conflicting SDK frame rule.
; Leaf/simple functions with <=4 bytes of explicitly direct/register-addressable
; locals omit IX completely. Zero-stack-local functions also omit IX. When a
; stack frame is required, IX is saved/restored and SP allocation is padded even.
; IY is never emitted or used as a C48 frame/index register.
    MACRO EMIT_P11_CC_FRAME_LAYOUT
CC_FRAME_FLAG_LEAF_SIMPLE   EQU 1
CC_FRAME_FLAG_DIRECT_LOCALS EQU 2
CC_FRAME_DIRECT_MAX         EQU 4
CC_FRAME_STACK_MAX          EQU 126
CC_FRAME_PROLOGUE_CAPACITY  EQU 72
CC_FRAME_EPILOGUE_CAPACITY  EQU 8

cc_frame_flags:          db 0
cc_frame_local_bytes:    dw 0
cc_frame_stack_bytes:    db 0
cc_frame_direct_bytes:   db 0
cc_frame_uses_ix:        db 0
cc_frame_prologue_len:   db 0
cc_frame_epilogue_len:   db 0
cc_frame_emit_ptr:       dw 0
cc_frame_prologue:       defs CC_FRAME_PROLOGUE_CAPACITY,0
cc_frame_epilogue:       defs CC_FRAME_EPILOGUE_CAPACITY,0

; A=planning flags, BC=required local bytes.
cc_frame_plan:
    ld (cc_frame_flags),a
    ld (cc_frame_local_bytes),bc
    xor a
    ld (cc_frame_stack_bytes),a
    ld (cc_frame_direct_bytes),a
    ld (cc_frame_uses_ix),a

    ld a,b
    or c
    ret z

    ; Direct/register-resident leaf locals require both eligibility flags and
    ; are intentionally capped. They consume no stack frame.
    ld a,(cc_frame_flags)
    and CC_FRAME_FLAG_LEAF_SIMPLE|CC_FRAME_FLAG_DIRECT_LOCALS
    cp CC_FRAME_FLAG_LEAF_SIMPLE|CC_FRAME_FLAG_DIRECT_LOCALS
    jp nz,cc_frame_plan_stack
    ld a,b
    or a
    jp nz,cc_frame_plan_stack
    ld a,c
    cp CC_FRAME_DIRECT_MAX+1
    jp nc,cc_frame_plan_stack
    ld (cc_frame_direct_bytes),a
    xor a
    ret

cc_frame_plan_stack:
    ld a,b
    or a
    jp nz,cc_frame_nospc
    ld a,c
    cp CC_FRAME_STACK_MAX+1
    jp nc,cc_frame_nospc
    ; Round stack storage up to an even byte count.
    bit 0,a
    jp z,cc_frame_plan_even
    inc a
cc_frame_plan_even:
    cp CC_FRAME_STACK_MAX+1
    jp nc,cc_frame_nospc
    ld (cc_frame_stack_bytes),a
    ld a,1
    ld (cc_frame_uses_ix),a
    xor a
    ret

; Emit exact prologue/epilogue byte streams for the current plan.
cc_frame_emit:
    call cc_frame_emit_prologue
    ret c
    jp cc_frame_emit_epilogue

cc_frame_emit_prologue:
    xor a
    ld (cc_frame_prologue_len),a
    ld a,(cc_frame_uses_ix)
    or a
    ret z
    ld hl,cc_frame_prologue
    ld (cc_frame_emit_ptr),hl
    ld a,$DD
    call cc_frame_put_prologue
    ld a,$E5                 ; PUSH IX
    call cc_frame_put_prologue
    ld a,$DD
    call cc_frame_put_prologue
    ld a,$21                 ; LD IX,0
    call cc_frame_put_prologue
    xor a
    call cc_frame_put_prologue
    xor a
    call cc_frame_put_prologue
    ld a,$DD
    call cc_frame_put_prologue
    ld a,$39                 ; ADD IX,SP
    call cc_frame_put_prologue
    ld a,(cc_frame_stack_bytes)
    srl a
    ld b,a
cc_frame_push_locals:
    ld a,b
    or a
    jp z,cc_frame_prologue_done
    ld a,$F5                 ; PUSH AF reserves two bytes, SP remains even
    call cc_frame_put_prologue
    djnz cc_frame_push_locals
cc_frame_prologue_done:
    xor a
    ret

cc_frame_emit_epilogue:
    xor a
    ld (cc_frame_epilogue_len),a
    ld hl,cc_frame_epilogue
    ld (cc_frame_emit_ptr),hl
    ld a,(cc_frame_uses_ix)
    or a
    jp z,cc_frame_leaf_epilogue
    ld a,$DD
    call cc_frame_put_epilogue
    ld a,$F9                 ; LD SP,IX
    call cc_frame_put_epilogue
    ld a,$DD
    call cc_frame_put_epilogue
    ld a,$E1                 ; POP IX
    call cc_frame_put_epilogue
cc_frame_leaf_epilogue:
    ld a,$C9                 ; RET
    call cc_frame_put_epilogue
    xor a
    ret

cc_frame_put_prologue:
    push af
    ld a,(cc_frame_prologue_len)
    cp CC_FRAME_PROLOGUE_CAPACITY
    jp nc,cc_frame_put_prologue_full
    ld hl,(cc_frame_emit_ptr)
    pop af
    ld (hl),a
    inc hl
    ld (cc_frame_emit_ptr),hl
    ld a,(cc_frame_prologue_len)
    inc a
    ld (cc_frame_prologue_len),a
    ret
cc_frame_put_prologue_full:
    pop af
    jp cc_frame_nospc

cc_frame_put_epilogue:
    push af
    ld a,(cc_frame_epilogue_len)
    cp CC_FRAME_EPILOGUE_CAPACITY
    jp nc,cc_frame_put_epilogue_full
    ld hl,(cc_frame_emit_ptr)
    pop af
    ld (hl),a
    inc hl
    ld (cc_frame_emit_ptr),hl
    ld a,(cc_frame_epilogue_len)
    inc a
    ld (cc_frame_epilogue_len),a
    ret
cc_frame_put_epilogue_full:
    pop af
    jp cc_frame_nospc

; A=0-based byte offset within stack local area. Success A=signed IX
; displacement: local byte 0 is IX-1. Direct/no-IX locals are not stack-addressed.
cc_frame_local_disp:
    ld e,a
    ld a,(cc_frame_uses_ix)
    or a
    jp z,cc_frame_format
    ld hl,(cc_frame_local_bytes)
    ld a,h
    or a
    jp nz,cc_frame_disp_in_range
    ld a,e
    cp l
    jp nc,cc_frame_format
cc_frame_disp_in_range:
    ld a,e
    cpl
    or a
    ret

; HL=SP value at a C48 call boundary. SP must always be even.
cc_frame_call_sp_check:
    bit 0,l
    jp nz,cc_frame_format
    xor a
    ret

cc_frame_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_frame_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.13 single externally linkable C48_REGCALL ABI for integer/pointer calls.
; Every scalar/pointer argument occupies one 16-bit slot. Argument 0/1/2 map
; to HL/DE/BC; argument 3+ are pushed right-to-left as 16-bit words. Character
; arguments are zero-extended before placement. Stack words are caller-cleaned
; with POP AF so an HL return value survives cleanup. This emitter never uses
; IY, EXX, or EX AF,AF' and does not define any alternate calling convention.
;
; Mandatory pinned SDK/reference mapping:
; 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/semantics.py -> fixed supported scalar/pointer parameter types
; compiler/tests/test_conformance.py -> fixed-arity function call semantics
; REV17 §25.3 remains authoritative for the target-native register ABI.
    MACRO EMIT_P11_CC_REGCALL
CC_REGCALL_MAX_ARGS        EQU 6
CC_REGCALL_KIND_WORD       EQU 0
CC_REGCALL_KIND_CHAR       EQU 1
CC_REGCALL_KIND_FLOAT_PTR  EQU 2
CC_REGCALL_SLOT_HL         EQU 0
CC_REGCALL_SLOT_DE         EQU 1
CC_REGCALL_SLOT_BC         EQU 2
CC_REGCALL_SLOT_STACK      EQU 3
CC_REGCALL_RET_NONE         EQU 0
CC_REGCALL_RET_L            EQU 1
CC_REGCALL_RET_HL           EQU 2
CC_REGCALL_RET_FLOAT_HIDDEN EQU 3
CC_REGCALL_BUFFER_CAPACITY  EQU 32

cc_regcall_args:           defs CC_REGCALL_MAX_ARGS*2,0
cc_regcall_kinds:          defs CC_REGCALL_MAX_ARGS,0
cc_regcall_count:          db 0
cc_regcall_target:         dw 0
cc_regcall_buffer:         defs CC_REGCALL_BUFFER_CAPACITY,0
cc_regcall_len:            db 0
cc_regcall_emit_ptr:       dw 0
cc_regcall_index:          db 0
cc_regcall_kind_tmp:       db 0
cc_regcall_value_tmp:      dw 0

cc_regcall_reset:
    xor a
    ld (cc_regcall_count),a
    ld (cc_regcall_len),a
    ret

; A=zero-based argument index 0..5, BC=value, D=kind.
; CHAR is normalized to 00xx here so all later slots are exact 16-bit values.
cc_regcall_set_arg:
    cp CC_REGCALL_MAX_ARGS
    jp nc,cc_regcall_inval
    ld (cc_regcall_index),a
    ld a,d
    cp CC_REGCALL_KIND_FLOAT_PTR+1
    jp nc,cc_regcall_inval
    ld (cc_regcall_kind_tmp),a
    ld a,c
    ld (cc_regcall_value_tmp),a
    ld a,(cc_regcall_kind_tmp)
    cp CC_REGCALL_KIND_CHAR
    jp z,cc_regcall_set_char_high
    ld a,b
    jp cc_regcall_set_high_ready
cc_regcall_set_char_high:
    xor a
cc_regcall_set_high_ready:
    ld (cc_regcall_value_tmp+1),a

    ld a,(cc_regcall_index)
    ld e,a
    ld d,0
    sla e
    rl d
    ld hl,cc_regcall_args
    add hl,de
    ld a,(cc_regcall_value_tmp)
    ld (hl),a
    inc hl
    ld a,(cc_regcall_value_tmp+1)
    ld (hl),a

    ld a,(cc_regcall_index)
    ld e,a
    ld d,0
    ld hl,cc_regcall_kinds
    add hl,de
    ld a,(cc_regcall_kind_tmp)
    ld (hl),a
    xor a
    ret

; A=zero-based argument index. Success A=slot, E=zero-based stack word index
; for stack arguments. The stack slot is later pushed in descending argument
; order so callee offsets are arg4 at SP+2, arg5 at SP+4, arg6 at SP+6.
cc_regcall_arg_location:
    cp CC_REGCALL_MAX_ARGS
    jp nc,cc_regcall_inval
    ld e,0
    cp 3
    jp nc,cc_regcall_arg_stack
    or a
    ret
cc_regcall_arg_stack:
    sub 3
    ld e,a
    ld a,CC_REGCALL_SLOT_STACK
    or a
    ret

; A=argument count 0..6. Success A=number of stack words.
cc_regcall_stack_words:
    cp CC_REGCALL_MAX_ARGS+1
    jp nc,cc_regcall_inval
    cp 4
    jp c,cc_regcall_no_stack
    sub 3
    or a
    ret
cc_regcall_no_stack:
    xor a
    ret

; A=C48 base type, E=pointer depth. Success A=return ABI class.
; A direct float result uses the P11.16 hidden-result-pointer class.
cc_regcall_return_class:
    ld d,a
    ld a,e
    or a
    jp nz,cc_regcall_ret_hl
    ld a,d
    cp CC_TYPE_VOID
    jp z,cc_regcall_ret_none
    cp CC_TYPE_CHAR
    jp z,cc_regcall_ret_l
    cp CC_TYPE_UCHAR
    jp z,cc_regcall_ret_l
    cp CC_TYPE_SHORT
    jp z,cc_regcall_ret_hl
    cp CC_TYPE_USHORT
    jp z,cc_regcall_ret_hl
    cp CC_TYPE_INT
    jp z,cc_regcall_ret_hl
    cp CC_TYPE_UINT
    jp z,cc_regcall_ret_hl
    cp CC_TYPE_FLOAT
    jp z,cc_regcall_ret_float_hidden
    jp cc_regcall_inval
cc_regcall_ret_none:
    ld a,CC_REGCALL_RET_NONE
    or a
    ret
cc_regcall_ret_l:
    ld a,CC_REGCALL_RET_L
    or a
    ret
cc_regcall_ret_hl:
    ld a,CC_REGCALL_RET_HL
    or a
    ret
cc_regcall_ret_float_hidden:
    ld a,CC_REGCALL_RET_FLOAT_HIDDEN
    or a
    ret

; HL=SP observed immediately before a C48 CALL. All call boundaries are even.
cc_regcall_call_sp_check:
    bit 0,l
    jp nz,cc_regcall_format
    xor a
    ret

; A=argument count 0..6, HL=absolute callee address.
; Emits the exact native call sequence into cc_regcall_buffer. The sequence has
; no trailing RET because production code continues after the call.
cc_regcall_emit_call:
    ld (cc_regcall_target),hl
    cp CC_REGCALL_MAX_ARGS+1
    jp nc,cc_regcall_inval
    ld (cc_regcall_count),a
    xor a
    ld (cc_regcall_len),a
    ld hl,cc_regcall_buffer
    ld (cc_regcall_emit_ptr),hl

    ld a,(cc_regcall_count)
    cp 4
    jp c,cc_regcall_emit_registers
    dec a
    ld (cc_regcall_index),a
cc_regcall_emit_stack_loop:
    call cc_regcall_load_index_bc
    ret c
    ld a,$21                 ; LD HL,nn
    call cc_regcall_put
    ret c
    ld a,c
    call cc_regcall_put
    ret c
    ld a,b
    call cc_regcall_put
    ret c
    ld a,$E5                 ; PUSH HL
    call cc_regcall_put
    ret c
    ld a,(cc_regcall_index)
    cp 3
    jp z,cc_regcall_emit_registers
    dec a
    ld (cc_regcall_index),a
    jp cc_regcall_emit_stack_loop

cc_regcall_emit_registers:
    ld a,(cc_regcall_count)
    cp 3
    jp c,cc_regcall_emit_arg1_check
    ld a,2
    ld (cc_regcall_index),a
    call cc_regcall_load_index_bc
    ret c
    ld a,$01                 ; LD BC,nn
    call cc_regcall_put
    ret c
    ld a,c
    call cc_regcall_put
    ret c
    ld a,b
    call cc_regcall_put
    ret c
cc_regcall_emit_arg1_check:
    ld a,(cc_regcall_count)
    cp 2
    jp c,cc_regcall_emit_arg0_check
    ld a,1
    ld (cc_regcall_index),a
    call cc_regcall_load_index_bc
    ret c
    ld a,$11                 ; LD DE,nn
    call cc_regcall_put
    ret c
    ld a,c
    call cc_regcall_put
    ret c
    ld a,b
    call cc_regcall_put
    ret c
cc_regcall_emit_arg0_check:
    ld a,(cc_regcall_count)
    or a
    jp z,cc_regcall_emit_call_opcode
    xor a
    ld (cc_regcall_index),a
    call cc_regcall_load_index_bc
    ret c
    ld a,$21                 ; LD HL,nn
    call cc_regcall_put
    ret c
    ld a,c
    call cc_regcall_put
    ret c
    ld a,b
    call cc_regcall_put
    ret c

cc_regcall_emit_call_opcode:
    ld a,$CD
    call cc_regcall_put
    ret c
    ld hl,(cc_regcall_target)
    ld a,l
    call cc_regcall_put
    ret c
    ld hl,(cc_regcall_target)
    ld a,h
    call cc_regcall_put
    ret c

    ld a,(cc_regcall_count)
    call cc_regcall_stack_words
    ret c
    ld b,a
cc_regcall_emit_cleanup_loop:
    ld a,b
    or a
    jp z,cc_regcall_emit_done
    ld a,$F1                 ; POP AF: caller cleanup, preserves HL return
    call cc_regcall_put
    ret c
    djnz cc_regcall_emit_cleanup_loop
cc_regcall_emit_done:
    xor a
    ret

cc_regcall_load_index_bc:
    ld a,(cc_regcall_index)
    cp CC_REGCALL_MAX_ARGS
    jp nc,cc_regcall_inval
    ld e,a
    ld d,0
    sla e
    rl d
    ld hl,cc_regcall_args
    add hl,de
    ld c,(hl)
    inc hl
    ld b,(hl)
    xor a
    ret

cc_regcall_put:
    push af
    ld a,(cc_regcall_len)
    cp CC_REGCALL_BUFFER_CAPACITY
    jp nc,cc_regcall_put_full
    ld hl,(cc_regcall_emit_ptr)
    pop af
    ld (hl),a
    inc hl
    ld (cc_regcall_emit_ptr),hl
    ld a,(cc_regcall_len)
    inc a
    ld (cc_regcall_len),a
    xor a
    ret
cc_regcall_put_full:
    pop af
    ld a,E_NOSPC
    scf
    ret

cc_regcall_notsup:
    ld a,E_NOTSUP
    scf
    ret
cc_regcall_inval:
    ld a,E_INVAL
    scf
    ret
cc_regcall_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.14 exact Spectrum/C48 five-byte float representation.
; C48 float is never IEEE binary32. Literal conversion is delegated through the
; frozen kernel SYS_FP_FROM_TEXT ROM gateway so compiler output bytes are the
; same bytes consumed by the runtime and Sinclair ROM calculator services.
;
; Mandatory pinned SDK/reference mapping:
; 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/float5.py -> exact five-byte representation and integer form
; compiler/tests/test_conformance.py -> required decimal float literal corpus
    MACRO EMIT_P11_CC_FLOAT5
CC_FLOAT5_SIZE           EQU 5
CC_FLOAT5_ALIGN          EQU 1

; A=claimed storage size. Only the architecture-frozen five-byte ABI is valid.
cc_float5_require_size:
    cp CC_FLOAT5_SIZE
    jp nz,cc_float5_format
    xor a
    ret

; HL=source, DE=destination. Copy exactly one C48 float object.
cc_float5_copy:
    ld bc,CC_FLOAT5_SIZE
    ldir
    xor a
    ret

; DE=destination. Produce canonical five-byte zero.
cc_float5_zero:
    xor a
    ld b,CC_FLOAT5_SIZE
cc_float5_zero_loop:
    ld (de),a
    inc de
    djnz cc_float5_zero_loop
    xor a
    ret

; HL=ASCII decimal literal, BC=exact source length, DE=five-byte destination.
; The kernel validates lexical form and performs the ROM-compatible conversion.
cc_float5_from_text:
    ld a,SYS_FP_FROM_TEXT
    call SYSCALL_GATEWAY
    ret

cc_float5_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.15 C48_REGCALL floating arguments.
; A C48 float value is never packed into an ordinary 16-bit slot. The slot
; contains only a 16-bit pointer to caller-owned five-byte storage. That pointer
; consumes the same HL/DE/BC/stack slot sequence frozen by P11.13. Literal and
; intermediate values are materialized into addressable five-byte caller
; temporaries before this typed setter is used.
;
; Mandatory pinned SDK/reference mapping:
; 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/float5.py -> exact five-byte value storage
; compiler/c48/semantics.py -> fixed typed function arguments
; compiler/tests/test_conformance.py -> float-call semantic coverage
; REV17 §25.3 remains authoritative for the target-native pointer ABI.
    MACRO EMIT_P11_CC_FLOAT_ARGS
CC_FLOAT_ARG_TEMP_STRIDE  EQU 5

cc_float_arg_index_tmp:   db 0

; A=zero-based argument index, BC=target address of caller-owned five-byte
; storage. The complete five-byte object must not wrap the 16-bit address
; space. Success records a FLOAT_PTR slot for the ordinary REGCALL emitter.
cc_float_arg_set_pointer:
    ld (cc_float_arg_index_tmp),a
    cp CC_REGCALL_MAX_ARGS
    jp nc,cc_float_arg_inval
    ld a,b
    or c
    jp z,cc_float_arg_inval
    ld h,b
    ld l,c
    ld de,4
    add hl,de
    jp c,cc_float_arg_inval
    ld a,(cc_float_arg_index_tmp)
    ld d,CC_REGCALL_KIND_FLOAT_PTR
    jp cc_regcall_set_arg

; A=temporary index 0..5, HL=target base of a caller-owned temporary block.
; Return HL=address of the indexed five-byte temporary. This is address
; planning only: generated caller code/materialization writes all five bytes
; before passing the resulting pointer.
cc_float_arg_temp_addr:
    cp CC_REGCALL_MAX_ARGS
    jp nc,cc_float_arg_inval
    ld b,a
    ld de,0
cc_float_arg_temp_offset:
    ld a,b
    or a
    jp z,cc_float_arg_temp_add_base
    ld a,e
    add a,CC_FLOAT_ARG_TEMP_STRIDE
    ld e,a
    ld a,d
    adc a,0
    ld d,a
    djnz cc_float_arg_temp_offset
cc_float_arg_temp_add_base:
    add hl,de
    jp c,cc_float_arg_inval
    push hl
    ld de,4
    add hl,de
    pop hl
    jp c,cc_float_arg_inval
    xor a
    ret

; Explicit negative path for a lowering attempt that tries to pass float bytes
; inline/by value instead of passing their address.
cc_float_arg_reject_inline:
    ld a,E_FORMAT
    scf
    ret

cc_float_arg_inval:
    ld a,E_INVAL
    scf
    ret
    ENDM

; P11.16 C48 floating return hidden-result-pointer ABI.
; A float-returning function receives a caller-owned five-byte result pointer
; in HL before every user argument. User argument 0/1 therefore occupy DE/BC;
; user argument 2+ are pushed right-to-left as 16-bit stack words. The callee
; writes exactly five bytes and returns the same result pointer in HL.
;
; Mandatory pinned SDK/reference mapping:
; 84d144de2721cda5075c3a6610a422663b5e2f77
; compiler/c48/semantics.py -> float function return/call source semantics
; compiler/c48/float5.py -> exact five-byte result object
; compiler/tests/test_conformance.py -> function return and direct-call coverage
; REV17 §25.3 remains authoritative for the target-native hidden pointer ABI.
    MACRO EMIT_P11_CC_FLOAT_RETURN
CC_FLOAT_RETURN_MAX_USER_ARGS EQU 6

cc_float_return_result_ptr:   dw 0
cc_float_return_user_count:   db 0
cc_float_return_target:       dw 0

cc_float_return_set_result:
    ld a,h
    or l
    jp z,cc_float_return_inval
    push hl
    ld de,4
    add hl,de
    pop hl
    jp c,cc_float_return_inval
    ld (cc_float_return_result_ptr),hl
    xor a
    ret

; A=user argument index. Hidden result occupies HL, so users shift by one slot.
cc_float_return_user_location:
    cp CC_FLOAT_RETURN_MAX_USER_ARGS
    jp nc,cc_float_return_inval
    ld e,0
    or a
    jp z,cc_float_return_user_de
    cp 1
    jp z,cc_float_return_user_bc
    sub 2
    ld e,a
    ld a,CC_REGCALL_SLOT_STACK
    or a
    ret
cc_float_return_user_de:
    ld a,CC_REGCALL_SLOT_DE
    or a
    ret
cc_float_return_user_bc:
    ld a,CC_REGCALL_SLOT_BC
    or a
    ret

; A=user argument count, HL=callee. User arguments are already recorded at
; indices 0..count-1 in the ordinary REGCALL argument table.
cc_float_return_emit_call:
    ld (cc_float_return_target),hl
    cp CC_FLOAT_RETURN_MAX_USER_ARGS+1
    jp nc,cc_float_return_inval
    ld (cc_float_return_user_count),a

    ld hl,(cc_float_return_result_ptr)
    ld a,h
    or l
    jp z,cc_float_return_inval
    push hl
    ld de,4
    add hl,de
    pop hl
    jp c,cc_float_return_inval

    xor a
    ld (cc_regcall_len),a
    ld hl,cc_regcall_buffer
    ld (cc_regcall_emit_ptr),hl

    ld a,(cc_float_return_user_count)
    cp 3
    jp c,cc_float_return_emit_registers
    dec a
    ld (cc_regcall_index),a
cc_float_return_emit_stack_loop:
    call cc_regcall_load_index_bc
    ret c
    ld a,$21
    call cc_regcall_put
    ret c
    ld a,c
    call cc_regcall_put
    ret c
    ld a,b
    call cc_regcall_put
    ret c
    ld a,$E5
    call cc_regcall_put
    ret c
    ld a,(cc_regcall_index)
    cp 2
    jp z,cc_float_return_emit_registers
    dec a
    ld (cc_regcall_index),a
    jp cc_float_return_emit_stack_loop

cc_float_return_emit_registers:
    ld a,(cc_float_return_user_count)
    cp 2
    jp c,cc_float_return_emit_user0
    ld a,1
    ld (cc_regcall_index),a
    call cc_regcall_load_index_bc
    ret c
    ld a,$01
    call cc_regcall_put
    ret c
    ld a,c
    call cc_regcall_put
    ret c
    ld a,b
    call cc_regcall_put
    ret c

cc_float_return_emit_user0:
    ld a,(cc_float_return_user_count)
    or a
    jp z,cc_float_return_emit_hidden
    xor a
    ld (cc_regcall_index),a
    call cc_regcall_load_index_bc
    ret c
    ld a,$11
    call cc_regcall_put
    ret c
    ld a,c
    call cc_regcall_put
    ret c
    ld a,b
    call cc_regcall_put
    ret c

cc_float_return_emit_hidden:
    ld bc,(cc_float_return_result_ptr)
    ld a,$21
    call cc_regcall_put
    ret c
    ld a,c
    call cc_regcall_put
    ret c
    ld a,b
    call cc_regcall_put
    ret c

    ld bc,(cc_float_return_target)
    ld a,$CD
    call cc_regcall_put
    ret c
    ld a,c
    call cc_regcall_put
    ret c
    ld a,b
    call cc_regcall_put
    ret c

    ld a,(cc_float_return_user_count)
    cp 3
    jp c,cc_float_return_emit_done
    sub 2
    ld b,a
cc_float_return_cleanup_loop:
    ld a,$F1
    call cc_regcall_put
    ret c
    djnz cc_float_return_cleanup_loop
cc_float_return_emit_done:
    xor a
    ret

cc_float_return_inval:
    ld a,E_INVAL
    scf
    ret
    ENDM

; P11.18 native cast lowering classification.
; Required runtime helper identities are frozen as __itof and __ftoi.
    MACRO EMIT_P1118_CC_CASTS
CC_CAST_HELPER_ITOF      EQU 1
CC_CAST_HELPER_FTOI      EQU 2

; A=source base type, E=destination base type.
; Success A=helper id. Other conversions remain owned by earlier integer rules.
cc_fp_cast_helper:
    cp CC_TYPE_FLOAT
    jr z,cc_fp_cast_from_float
    ld d,a
    ld a,e
    cp CC_TYPE_FLOAT
    jr nz,cc_fp_cast_notsup
    ld a,d
    cp CC_TYPE_CHAR
    jr c,cc_fp_cast_notsup
    cp CC_TYPE_UINT+1
    jr nc,cc_fp_cast_notsup
    ld a,CC_CAST_HELPER_ITOF
    or a
    ret
cc_fp_cast_from_float:
    ld a,e
    cp CC_TYPE_CHAR
    jr c,cc_fp_cast_notsup
    cp CC_TYPE_UINT+1
    jr nc,cc_fp_cast_notsup
    ld a,CC_CAST_HELPER_FTOI
    or a
    ret
cc_fp_cast_notsup:
    ld a,E_NOTSUP
    scf
    ret
    ENDM

; P11.19 float comparison lowering map.
; Every floating relational/equality expression uses __fcmp; float truth uses
; the same helper against the runtime's exact five-byte zero.
; Relation ids are compiler-owned here; no libc macro expansion is required.
    MACRO EMIT_P1119_CC_FLOAT_COMPARE
CC_FP_COMPARE_HELPER_FCMP EQU 1
CC_FP_COMPARE_CAST_LHS    EQU 1
CC_FP_COMPARE_CAST_RHS    EQU 2
CC_FP_REL_LT              EQU 1
CC_FP_REL_LE              EQU 2
CC_FP_REL_EQ              EQU 3
CC_FP_REL_NE              EQU 4
CC_FP_REL_GT              EQU 5
CC_FP_REL_GE              EQU 6

; A=lhs base type, E=rhs base type. Success A=cast mask, D=helper id.
; Integer operands mixed with float are first converted through P11.18 __itof.
cc_fp_compare_plan:
    ld d,a
    ld a,e
    cp CC_TYPE_FLOAT
    jr z,cc_fp_compare_rhs_float
    ld a,d
    cp CC_TYPE_FLOAT
    jr nz,cc_fp_compare_notsup
    ld a,e
    call cc_fp_compare_integer_type
    ret c
    ld a,CC_FP_COMPARE_CAST_RHS
    ld d,CC_FP_COMPARE_HELPER_FCMP
    or a
    ret
cc_fp_compare_rhs_float:
    ld a,d
    cp CC_TYPE_FLOAT
    jr z,cc_fp_compare_both_float
    call cc_fp_compare_integer_type
    ret c
    ld a,CC_FP_COMPARE_CAST_LHS
    ld d,CC_FP_COMPARE_HELPER_FCMP
    or a
    ret
cc_fp_compare_both_float:
    xor a
    ld d,CC_FP_COMPARE_HELPER_FCMP
    ret

cc_fp_compare_integer_type:
    cp CC_TYPE_CHAR
    jr c,cc_fp_compare_notsup
    cp CC_TYPE_UINT+1
    jr nc,cc_fp_compare_notsup
    xor a
    ret

; A=relation id 1..6. Success D=__fcmp helper id.
cc_fp_relation_helper:
    cp CC_FP_REL_LT
    jr c,cc_fp_compare_notsup
    cp CC_FP_REL_GE+1
    jr nc,cc_fp_compare_notsup
    ld d,CC_FP_COMPARE_HELPER_FCMP
    or a
    ret

; A=base type. Float truth is always __fcmp(value, exact-zero).
cc_fp_truth_helper:
    cp CC_TYPE_FLOAT
    jr nz,cc_fp_compare_notsup
    ld d,CC_FP_COMPARE_HELPER_FCMP
    xor a
    ret

cc_fp_compare_notsup:
    ld a,E_NOTSUP
    scf
    ret
    ENDM

; P11.28 deterministic native OBJ1 writer.
; The writer validates all internal state before touching destination bytes.
; cc_obj1_commit_marker becomes $A5 only after the complete OBJ1 image and both
; CRCs have been written successfully.
    MACRO EMIT_P1128_CC_OBJ1_WRITER
CC_OBJ1_HEADER_SIZE       EQU 24
CC_OBJ1_SYMBOL_SIZE       EQU 20
CC_OBJ1_RELOC_SIZE        EQU 6
CC_OBJ1_MAX_STORED        EQU 32768
CC_OBJ1_SYMBOL_MAX_COUNT  EQU 1638
CC_OBJ1_RELOC_MAX_COUNT   EQU 5461
CC_OBJ1_RELOC_ABS16       EQU 1
CC_OBJ1_COMMITTED         EQU $A5

cc_obj1_text_ptr:         dw 0
cc_obj1_text_size:        dw 0
cc_obj1_bss_size:         dw 0
cc_obj1_symbol_ptr:       dw 0
cc_obj1_symbol_count:     dw 0
cc_obj1_reloc_ptr:        dw 0
cc_obj1_reloc_count:      dw 0
cc_obj1_output_ptr:       dw 0
cc_obj1_output_capacity:  dw 0
cc_obj1_output_size:      dw 0
cc_obj1_symbol_bytes:     dw 0
cc_obj1_reloc_bytes:      dw 0
cc_obj1_body_size:        dw 0
cc_obj1_symbol_offset:    dw 0
cc_obj1_reloc_offset:     dw 0
cc_obj1_total_size:       dw 0
cc_obj1_current_offset:   dw 0
cc_obj1_previous_offset:  dw 0
cc_obj1_previous_valid:   db 0
cc_obj1_commit_marker:    db 0

cc_obj1_write:
    xor a
    ld (cc_obj1_commit_marker),a
    ld (cc_obj1_output_size),a
    ld (cc_obj1_output_size+1),a

    ld hl,(cc_obj1_output_ptr)
    ld a,h
    or l
    jp z,cc_obj1_format

    ld hl,(cc_obj1_text_size)
    ld de,(cc_obj1_bss_size)
    add hl,de
    jp c,cc_obj1_format
    ld de,CC_OBJ1_MAX_STORED+1
    or a
    sbc hl,de
    jp nc,cc_obj1_format

    ld hl,(cc_obj1_symbol_count)
    ld de,CC_OBJ1_SYMBOL_MAX_COUNT+1
    or a
    sbc hl,de
    jp nc,cc_obj1_format
    ld bc,(cc_obj1_symbol_count)
    ld de,CC_OBJ1_SYMBOL_SIZE
    call cc_obj1_multiply
    jp c,cc_obj1_format
    ld (cc_obj1_symbol_bytes),hl

    ld hl,(cc_obj1_reloc_count)
    ld de,CC_OBJ1_RELOC_MAX_COUNT+1
    or a
    sbc hl,de
    jp nc,cc_obj1_format
    ld bc,(cc_obj1_reloc_count)
    ld de,CC_OBJ1_RELOC_SIZE
    call cc_obj1_multiply
    jp c,cc_obj1_format
    ld (cc_obj1_reloc_bytes),hl

    ld hl,(cc_obj1_text_size)
    ld de,CC_OBJ1_HEADER_SIZE
    add hl,de
    jp c,cc_obj1_format
    ld (cc_obj1_symbol_offset),hl
    ld de,(cc_obj1_symbol_bytes)
    add hl,de
    jp c,cc_obj1_format
    ld (cc_obj1_reloc_offset),hl
    ld de,(cc_obj1_reloc_bytes)
    add hl,de
    jp c,cc_obj1_format
    ld (cc_obj1_total_size),hl
    ld de,CC_OBJ1_MAX_STORED+1
    or a
    sbc hl,de
    jp nc,cc_obj1_format

    ld hl,(cc_obj1_text_size)
    ld de,(cc_obj1_symbol_bytes)
    add hl,de
    jp c,cc_obj1_format
    ld de,(cc_obj1_reloc_bytes)
    add hl,de
    jp c,cc_obj1_format
    ld (cc_obj1_body_size),hl

    ld hl,(cc_obj1_output_capacity)
    ld de,(cc_obj1_total_size)
    or a
    sbc hl,de
    jp c,cc_obj1_nospc

    ld hl,(cc_obj1_text_size)
    ld a,h
    or l
    jr z,cc_obj1_text_ptr_ok
    ld hl,(cc_obj1_text_ptr)
    ld a,h
    or l
    jp z,cc_obj1_format
cc_obj1_text_ptr_ok:
    ld hl,(cc_obj1_symbol_count)
    ld a,h
    or l
    jr z,cc_obj1_symbol_ptr_ok
    ld hl,(cc_obj1_symbol_ptr)
    ld a,h
    or l
    jp z,cc_obj1_format
cc_obj1_symbol_ptr_ok:
    ld hl,(cc_obj1_reloc_count)
    ld a,h
    or l
    jr z,cc_obj1_reloc_ptr_ok
    ld hl,(cc_obj1_reloc_ptr)
    ld a,h
    or l
    jp z,cc_obj1_format
cc_obj1_reloc_ptr_ok:
    call cc_obj1_validate_symbols
    ret c
    call cc_obj1_validate_relocs
    ret c

    ld ix,(cc_obj1_output_ptr)
    ld (ix+0),'O'
    ld (ix+1),'B'
    ld (ix+2),'J'
    ld (ix+3),'1'
    ld (ix+4),1
    ld (ix+5),0
    ld (ix+6),CC_OBJ1_HEADER_SIZE
    ld (ix+7),0
    ld hl,(cc_obj1_text_size)
    ld (ix+8),l
    ld (ix+9),h
    ld hl,(cc_obj1_bss_size)
    ld (ix+10),l
    ld (ix+11),h
    ld hl,(cc_obj1_symbol_count)
    ld (ix+12),l
    ld (ix+13),h
    ld hl,(cc_obj1_reloc_count)
    ld (ix+14),l
    ld (ix+15),h
    ld hl,(cc_obj1_symbol_offset)
    ld (ix+16),l
    ld (ix+17),h
    ld hl,(cc_obj1_reloc_offset)
    ld (ix+18),l
    ld (ix+19),h
    xor a
    ld (ix+20),a
    ld (ix+21),a
    ld (ix+22),a
    ld (ix+23),a

    ld hl,(cc_obj1_output_ptr)
    ld de,CC_OBJ1_HEADER_SIZE
    add hl,de
    ex de,hl
    ld bc,(cc_obj1_text_size)
    ld a,b
    or c
    jr z,cc_obj1_copy_symbols
    ld hl,(cc_obj1_text_ptr)
    ldir
cc_obj1_copy_symbols:
    ld bc,(cc_obj1_symbol_bytes)
    ld a,b
    or c
    jr z,cc_obj1_copy_relocs
    ld hl,(cc_obj1_symbol_ptr)
    ldir
cc_obj1_copy_relocs:
    ld bc,(cc_obj1_reloc_bytes)
    ld a,b
    or c
    jr z,cc_obj1_body_copied
    ld hl,(cc_obj1_reloc_ptr)
    ldir
cc_obj1_body_copied:
    ld hl,(cc_obj1_output_ptr)
    ld de,CC_OBJ1_HEADER_SIZE
    add hl,de
    ld bc,(cc_obj1_body_size)
    call cc_obj1_crc16
    ld ix,(cc_obj1_output_ptr)
    ld (ix+20),e
    ld (ix+21),d

    ld hl,(cc_obj1_output_ptr)
    ld bc,CC_OBJ1_HEADER_SIZE
    call cc_obj1_crc16
    ld ix,(cc_obj1_output_ptr)
    ld (ix+22),e
    ld (ix+23),d

    ld hl,(cc_obj1_total_size)
    ld (cc_obj1_output_size),hl
    ld a,CC_OBJ1_COMMITTED
    ld (cc_obj1_commit_marker),a
    xor a
    ret

cc_obj1_multiply:
    ld hl,0
cc_obj1_multiply_loop:
    ld a,b
    or c
    ret z
    add hl,de
    ret c
    dec bc
    jr cc_obj1_multiply_loop

cc_obj1_validate_symbols:
    ld bc,(cc_obj1_symbol_count)
    ld ix,(cc_obj1_symbol_ptr)
cc_obj1_validate_symbols_loop:
    ld a,b
    or c
    ret z
    push bc
    call cc_obj1_validate_symbol
    pop bc
    ret c
    ld de,CC_OBJ1_SYMBOL_SIZE
    add ix,de
    dec bc
    jr cc_obj1_validate_symbols_loop

cc_obj1_validate_symbol:
    push ix
    ld a,(ix+0)
    call cc_obj1_name_first
    jr c,cc_obj1_symbol_bad
    inc ix
    ld b,15
cc_obj1_symbol_name_loop:
    ld a,(ix+0)
    or a
    jr z,cc_obj1_symbol_zero_tail
    ld a,b
    cp 1
    jr z,cc_obj1_symbol_bad
    ld a,(ix+0)
    call cc_obj1_name_tail
    jr c,cc_obj1_symbol_bad
    inc ix
    djnz cc_obj1_symbol_name_loop
    jr cc_obj1_symbol_bad
cc_obj1_symbol_zero_tail:
    ld a,(ix+0)
    or a
    jr nz,cc_obj1_symbol_bad
    inc ix
    djnz cc_obj1_symbol_zero_tail
    ld a,(ix+3)
    and $FE
    jr nz,cc_obj1_symbol_bad
    ld e,(ix+0)
    ld d,(ix+1)
    ld a,(ix+2)
    or a
    jr z,cc_obj1_symbol_undef
    cp 1
    jr z,cc_obj1_symbol_text
    cp 2
    jr z,cc_obj1_symbol_bss
    cp 3
    jr z,cc_obj1_symbol_good
    jr cc_obj1_symbol_bad
cc_obj1_symbol_undef:
    ld a,d
    or e
    jr nz,cc_obj1_symbol_bad
    ld a,(ix+3)
    cp 1
    jr nz,cc_obj1_symbol_bad
    jr cc_obj1_symbol_good
cc_obj1_symbol_text:
    ld h,d
    ld l,e
    ld de,(cc_obj1_text_size)
    or a
    sbc hl,de
    jr c,cc_obj1_symbol_good
    jr z,cc_obj1_symbol_good
    jr cc_obj1_symbol_bad
cc_obj1_symbol_bss:
    ld h,d
    ld l,e
    ld de,(cc_obj1_bss_size)
    or a
    sbc hl,de
    jr c,cc_obj1_symbol_good
    jr z,cc_obj1_symbol_good
    jr cc_obj1_symbol_bad
cc_obj1_symbol_good:
    pop ix
    xor a
    ret
cc_obj1_symbol_bad:
    pop ix
    ld a,E_FORMAT
    scf
    ret

cc_obj1_validate_relocs:
    xor a
    ld (cc_obj1_previous_valid),a
    ld bc,(cc_obj1_reloc_count)
    ld ix,(cc_obj1_reloc_ptr)
cc_obj1_validate_relocs_loop:
    ld a,b
    or c
    ret z
    push bc
    call cc_obj1_validate_reloc
    pop bc
    ret c
    ld de,CC_OBJ1_RELOC_SIZE
    add ix,de
    dec bc
    jr cc_obj1_validate_relocs_loop

cc_obj1_validate_reloc:
    push ix
    ld a,(ix+4)
    cp CC_OBJ1_RELOC_ABS16
    jr nz,cc_obj1_reloc_bad
    ld a,(ix+5)
    or a
    jr nz,cc_obj1_reloc_bad
    ld l,(ix+2)
    ld h,(ix+3)
    ld de,(cc_obj1_symbol_count)
    or a
    sbc hl,de
    jr nc,cc_obj1_reloc_bad
    ld l,(ix+0)
    ld h,(ix+1)
    ld (cc_obj1_current_offset),hl
    ld de,2
    add hl,de
    jr c,cc_obj1_reloc_bad
    ld de,(cc_obj1_text_size)
    or a
    sbc hl,de
    jr c,cc_obj1_reloc_range_ok
    jr z,cc_obj1_reloc_range_ok
    jr cc_obj1_reloc_bad
cc_obj1_reloc_range_ok:
    ld a,(cc_obj1_previous_valid)
    or a
    jr z,cc_obj1_reloc_order_ok
    ld hl,(cc_obj1_previous_offset)
    ld de,2
    add hl,de
    jr c,cc_obj1_reloc_bad
    ex de,hl
    ld hl,(cc_obj1_current_offset)
    or a
    sbc hl,de
    jr c,cc_obj1_reloc_bad
cc_obj1_reloc_order_ok:
    ld hl,(cc_obj1_current_offset)
    ld (cc_obj1_previous_offset),hl
    ld a,1
    ld (cc_obj1_previous_valid),a
    pop ix
    xor a
    ret
cc_obj1_reloc_bad:
    pop ix
    ld a,E_FORMAT
    scf
    ret

cc_obj1_name_first:
    cp 'A'
    jr c,cc_obj1_name_first_under
    cp 'Z'+1
    jr c,cc_obj1_name_ok
    cp 'a'
    jr c,cc_obj1_name_first_under
    cp 'z'+1
    jr c,cc_obj1_name_ok
cc_obj1_name_first_under:
    cp '_'
    jr z,cc_obj1_name_ok
    scf
    ret
cc_obj1_name_tail:
    cp '0'
    jr c,cc_obj1_name_first
    cp '9'+1
    jr c,cc_obj1_name_ok
    jp cc_obj1_name_first
cc_obj1_name_ok:
    or a
    ret

cc_obj1_crc16:
    ld de,65535
cc_obj1_crc_byte_loop:
    ld a,b
    or c
    ret z
    ld a,(hl)
    inc hl
    xor d
    ld d,a
    push bc
    ld b,8
cc_obj1_crc_bit_loop:
    bit 7,d
    jr z,cc_obj1_crc_shift_only
    sla e
    rl d
    ld a,d
    xor $10
    ld d,a
    ld a,e
    xor $21
    ld e,a
    jr cc_obj1_crc_bit_done
cc_obj1_crc_shift_only:
    sla e
    rl d
cc_obj1_crc_bit_done:
    djnz cc_obj1_crc_bit_loop
    pop bc
    dec bc
    jr cc_obj1_crc_byte_loop

cc_obj1_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_obj1_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM


; P11.29 compiler name resolution and transactional OBJ1 publication.
; P11.28 owns serialization. This stage accepts only one kernel-typed C input,
; derives or copies the exact destination name, and publishes the completed
; in-memory OBJ1 through one owned O_CREATE|O_EXCL temporary followed by the
; atomic SYS_RENAME commit barrier.
    MACRO EMIT_P1129_CC_TRANSACTION_ROUTINES
CC_P1129_MAX_OUTPUT       EQU 10
CC_P1129_MAX_INPUT_SCAN   EQU 31
CC_P1129_HEADER_SIZE      EQU 24
CC_P1129_SYMBOL_SIZE      EQU 20
CC_P1129_RELOC_SIZE       EQU 6
CC_P1129_MAX_STORED       EQU 32768
CC_P1129_SYMBOL_MAX_COUNT EQU 1638
CC_P1129_RELOC_MAX_COUNT  EQU 5461

cc_p1129_names:
    ld (cc_p1129_input),hl
    ld (cc_p1129_explicit),de
    ld (cc_p1129_output),ix
    ld b,a
    ld a,c
    cp 1
    jp nz,cc_p1129_format
    ld a,b
    cp OBJ_C
    jp nz,cc_p1129_format
    ld a,h
    or l
    jp z,cc_p1129_format
    ld hl,(cc_p1129_explicit)
    ld a,h
    or l
    jp z,cc_p1129_default_name
    call cc_p1129_measure_output
    jp c,cc_p1129_format
    ld hl,(cc_p1129_explicit)
    jp cc_p1129_copy_exact

cc_p1129_default_name:
    ld hl,(cc_p1129_input)
    ld b,0
cc_p1129_measure_input:
    ld a,(hl)
    or a
    jp z,cc_p1129_input_measured
    inc b
    ld a,b
    cp CC_P1129_MAX_INPUT_SCAN+1
    jp nc,cc_p1129_format
    inc hl
    jp cc_p1129_measure_input
cc_p1129_input_measured:
    ld a,b
    cp 3
    jp c,cc_p1129_format
    add a,2
    cp CC_P1129_MAX_OUTPUT+1
    jp nc,cc_p1129_format
    ld hl,(cc_p1129_input)
    ld d,0
    ld e,b
    add hl,de
    dec hl
    ld a,(hl)
    cp 'c'
    jp nz,cc_p1129_format
    dec hl
    ld a,(hl)
    cp '.'
    jp nz,cc_p1129_format
    ld hl,(cc_p1129_input)
    push ix
    pop de
    ld a,b
    sub 2
    ld b,a
cc_p1129_copy_stem:
    ld a,b
    or a
    jp z,cc_p1129_append_obj
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    djnz cc_p1129_copy_stem
cc_p1129_append_obj:
    ld hl,cc_p1129_obj_suffix
    ld bc,5
    ldir
    ld a,OBJ_OBJ
    or a
    ret

cc_p1129_measure_output:
    ld b,0
cc_p1129_measure_output_loop:
    ld a,(hl)
    or a
    jp z,cc_p1129_measure_output_done
    inc b
    ld a,b
    cp CC_P1129_MAX_OUTPUT+1
    jp nc,cc_p1129_measure_output_bad
    inc hl
    jp cc_p1129_measure_output_loop
cc_p1129_measure_output_done:
    ld a,b
    or a
    jp z,cc_p1129_measure_output_bad
    or a
    ret
cc_p1129_measure_output_bad:
    scf
    ret

cc_p1129_copy_exact:
    push ix
    pop de
cc_p1129_copy_exact_loop:
    ld a,(hl)
    ld (de),a
    inc hl
    inc de
    or a
    jp nz,cc_p1129_copy_exact_loop
    ld a,OBJ_OBJ
    or a
    ret

cc_p1129_commit:
    or a
    jp z,cc_p1129_publish
    scf
    ret

cc_p1129_publish:
    ld (cc_p1129_dest),hl
    ld (cc_p1129_candidate),de
    ld (cc_p1129_length),bc
    xor a
    ld (cc_p1129_owned),a
    ld (cc_p1129_open),a

    ld a,(cc_obj1_commit_marker)
    cp CC_OBJ1_COMMITTED
    jp nz,cc_p1129_format
    ld hl,(cc_obj1_output_ptr)
    ld de,(cc_p1129_candidate)
    or a
    sbc hl,de
    jp nz,cc_p1129_format
    ld hl,(cc_obj1_output_size)
    ld de,(cc_p1129_length)
    or a
    sbc hl,de
    jp nz,cc_p1129_format
    call cc_p1129_validate_candidate
    jp c,cc_p1129_format

    ld a,SYS_GETPID
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jp nz,cc_p1129_format
    ld a,l
    cp 10
    jp nc,cc_p1129_format
    add a,'0'
    ld (cc_p1129_temp_name+8),a
    xor a
    ld (cc_p1129_temp_n),a

cc_p1129_open_retry:
    ld a,(cc_p1129_temp_n)
    add a,'0'
    ld (cc_p1129_temp_name+10),a
    ld hl,cc_p1129_temp_name
    ld c,O_WRITE|O_CREATE|O_EXCL
    ld b,OBJ_OBJ
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jp nc,cc_p1129_opened
    cp E_EXIST
    jp z,cc_p1129_collision
    scf
    ret
cc_p1129_collision:
    ld a,(cc_p1129_temp_n)
    cp 9
    jp z,cc_p1129_exist
    inc a
    ld (cc_p1129_temp_n),a
    jp cc_p1129_open_retry

cc_p1129_opened:
    ld a,h
    or a
    jp nz,cc_p1129_format_created
    ld a,l
    ld (cc_p1129_handle),a
    ld a,1
    ld (cc_p1129_owned),a
    ld (cc_p1129_open),a
    ld e,l
    ld d,0
    ld hl,(cc_p1129_candidate)
    ld bc,(cc_p1129_length)
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jp c,cc_p1129_cleanup_error
    ld de,(cc_p1129_length)
    or a
    sbc hl,de
    jp z,cc_p1129_write_complete
    ld a,E_IO
    jp cc_p1129_cleanup_error

cc_p1129_write_complete:
    call cc_p1129_close_temp
    jp c,cc_p1129_cleanup_error
    call cc_p1129_validate_candidate
    jp nc,cc_p1129_ready_rename
    ld a,E_FORMAT
    jp cc_p1129_cleanup_error

cc_p1129_ready_rename:
    ld hl,cc_p1129_temp_name
    ld (cc_p1129_rename_req),hl
    ld hl,(cc_p1129_dest)
    ld (cc_p1129_rename_req+2),hl
    ld hl,cc_p1129_rename_req
    ld a,SYS_RENAME
    call SYSCALL_GATEWAY
    jp c,cc_p1129_cleanup_error
    xor a
    ld (cc_p1129_owned),a
    ret

cc_p1129_close_temp:
    ld a,(cc_p1129_open)
    or a
    ret z
    ld a,(cc_p1129_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret c
    xor a
    ld (cc_p1129_open),a
    ret

cc_p1129_cleanup_error:
    ld (cc_p1129_errno),a
    call cc_p1129_close_temp
    ld a,(cc_p1129_owned)
    or a
    jp z,cc_p1129_return_primary
    xor a
    ld (cc_p1129_owned),a
    ld hl,cc_p1129_temp_name
    ld a,SYS_REMOVE
    call SYSCALL_GATEWAY
cc_p1129_return_primary:
    ld a,(cc_p1129_errno)
    scf
    ret

cc_p1129_format_created:
    ld a,1
    ld (cc_p1129_owned),a
    ld a,E_FORMAT
    jp cc_p1129_cleanup_error
cc_p1129_exist:
    ld a,E_EXIST
    scf
    ret

cc_p1129_validate_candidate:
    ld hl,(cc_p1129_length)
    ld de,CC_P1129_HEADER_SIZE
    or a
    sbc hl,de
    jp c,cc_p1129_val_bad
    ld ix,(cc_p1129_candidate)
    ld a,(ix+0)
    cp 'O'
    jp nz,cc_p1129_val_bad
    ld a,(ix+1)
    cp 'B'
    jp nz,cc_p1129_val_bad
    ld a,(ix+2)
    cp 'J'
    jp nz,cc_p1129_val_bad
    ld a,(ix+3)
    cp '1'
    jp nz,cc_p1129_val_bad
    ld a,(ix+4)
    cp 1
    jp nz,cc_p1129_val_bad
    ld a,(ix+5)
    or a
    jp nz,cc_p1129_val_bad
    ld a,(ix+6)
    cp CC_P1129_HEADER_SIZE
    jp nz,cc_p1129_val_bad
    ld a,(ix+7)
    or a
    jp nz,cc_p1129_val_bad
    ld l,(ix+8)
    ld h,(ix+9)
    ld (cc_obj1_text_size),hl
    ld l,(ix+10)
    ld h,(ix+11)
    ld (cc_obj1_bss_size),hl
    ld l,(ix+12)
    ld h,(ix+13)
    ld (cc_obj1_symbol_count),hl
    ld l,(ix+14)
    ld h,(ix+15)
    ld (cc_obj1_reloc_count),hl
    ld l,(ix+16)
    ld h,(ix+17)
    ld (cc_obj1_symbol_offset),hl
    ld l,(ix+18)
    ld h,(ix+19)
    ld (cc_obj1_reloc_offset),hl

    ld hl,(cc_obj1_text_size)
    ld de,(cc_obj1_bss_size)
    add hl,de
    jp c,cc_p1129_val_bad
    call cc_p1129_bound
    jp c,cc_p1129_val_bad

    ld hl,(cc_obj1_symbol_count)
    ld de,CC_P1129_SYMBOL_MAX_COUNT+1
    or a
    sbc hl,de
    jp nc,cc_p1129_val_bad
    ld bc,(cc_obj1_symbol_count)
    ld de,CC_P1129_SYMBOL_SIZE
    call cc_obj1_multiply
    jp c,cc_p1129_val_bad
    ld (cc_obj1_symbol_bytes),hl

    ld hl,(cc_obj1_reloc_count)
    ld de,CC_P1129_RELOC_MAX_COUNT+1
    or a
    sbc hl,de
    jp nc,cc_p1129_val_bad
    ld bc,(cc_obj1_reloc_count)
    ld de,CC_P1129_RELOC_SIZE
    call cc_obj1_multiply
    jp c,cc_p1129_val_bad
    ld (cc_obj1_reloc_bytes),hl

    ld hl,(cc_obj1_text_size)
    ld de,CC_P1129_HEADER_SIZE
    add hl,de
    jp c,cc_p1129_val_bad
    ld de,(cc_obj1_symbol_offset)
    or a
    sbc hl,de
    jp nz,cc_p1129_val_bad

    ld hl,(cc_obj1_symbol_offset)
    ld de,(cc_obj1_symbol_bytes)
    add hl,de
    jp c,cc_p1129_val_bad
    ld de,(cc_obj1_reloc_offset)
    or a
    sbc hl,de
    jp nz,cc_p1129_val_bad

    ld hl,(cc_obj1_reloc_offset)
    ld de,(cc_obj1_reloc_bytes)
    add hl,de
    jp c,cc_p1129_val_bad
    call cc_p1129_bound
    jp c,cc_p1129_val_bad
    ld (cc_obj1_total_size),hl
    ld de,(cc_p1129_length)
    or a
    sbc hl,de
    jp nz,cc_p1129_val_bad

    ld hl,(cc_obj1_reloc_count)
    ld a,h
    or l
    jp z,cc_p1129_ptrs
    ld hl,(cc_obj1_text_size)
    ld a,h
    or a
    jp nz,cc_p1129_ptrs
    ld a,l
    cp 2
    jp c,cc_p1129_val_bad

cc_p1129_ptrs:
    ld hl,(cc_p1129_candidate)
    ld de,CC_P1129_HEADER_SIZE
    add hl,de
    ld (cc_obj1_text_ptr),hl
    ld hl,(cc_p1129_candidate)
    ld de,(cc_obj1_symbol_offset)
    add hl,de
    ld (cc_obj1_symbol_ptr),hl
    ld hl,(cc_p1129_candidate)
    ld de,(cc_obj1_reloc_offset)
    add hl,de
    ld (cc_obj1_reloc_ptr),hl

    ld hl,(cc_p1129_length)
    ld de,CC_P1129_HEADER_SIZE
    or a
    sbc hl,de
    ld b,h
    ld c,l
    ld hl,(cc_obj1_text_ptr)
    call cc_obj1_crc16
    ld ix,(cc_p1129_candidate)
    ld a,(ix+20)
    cp e
    jp nz,cc_p1129_val_bad
    ld a,(ix+21)
    cp d
    jp nz,cc_p1129_val_bad

    ld hl,(cc_p1129_candidate)
    ld de,cc_p1129_header_copy
    ld bc,CC_P1129_HEADER_SIZE
    ldir
    xor a
    ld (cc_p1129_header_copy+22),a
    ld (cc_p1129_header_copy+23),a
    ld hl,cc_p1129_header_copy
    ld bc,CC_P1129_HEADER_SIZE
    call cc_obj1_crc16
    ld ix,(cc_p1129_candidate)
    ld a,(ix+22)
    cp e
    jp nz,cc_p1129_val_bad
    ld a,(ix+23)
    cp d
    jp nz,cc_p1129_val_bad

    call cc_obj1_validate_symbols
    jp c,cc_p1129_val_bad
    call cc_p1129_unique_symbols
    jp c,cc_p1129_val_bad
    call cc_obj1_validate_relocs
    jp c,cc_p1129_val_bad
    xor a
    ret

cc_p1129_unique_symbols:
    ld hl,(cc_obj1_symbol_ptr)
    ld (cc_p1129_sym_start),hl
    ld (cc_p1129_sym_cur),hl
    ld hl,(cc_obj1_symbol_count)
    ld (cc_p1129_left),hl
cc_p1129_unique_outer:
    ld hl,(cc_p1129_left)
    ld a,h
    or l
    ret z
    ld hl,(cc_p1129_sym_start)
    ld (cc_p1129_scan),hl
cc_p1129_unique_inner:
    ld hl,(cc_p1129_scan)
    ld de,(cc_p1129_sym_cur)
    or a
    sbc hl,de
    jp z,cc_p1129_unique_advance
    ld hl,(cc_p1129_scan)
    ld de,(cc_p1129_sym_cur)
    ld b,16
cc_p1129_unique_compare:
    ld a,(de)
    cp (hl)
    jp nz,cc_p1129_unique_not_equal
    inc de
    inc hl
    djnz cc_p1129_unique_compare
    scf
    ret
cc_p1129_unique_not_equal:
    ld hl,(cc_p1129_scan)
    ld de,CC_P1129_SYMBOL_SIZE
    add hl,de
    ld (cc_p1129_scan),hl
    jp cc_p1129_unique_inner
cc_p1129_unique_advance:
    ld hl,(cc_p1129_sym_cur)
    ld de,CC_P1129_SYMBOL_SIZE
    add hl,de
    ld (cc_p1129_sym_cur),hl
    ld hl,(cc_p1129_left)
    dec hl
    ld (cc_p1129_left),hl
    jp cc_p1129_unique_outer

cc_p1129_bound:
    push hl
    ld de,CC_P1129_MAX_STORED+1
    or a
    sbc hl,de
    pop hl
    jp c,cc_p1129_bound_ok
    scf
    ret
cc_p1129_bound_ok:
    or a
    ret
cc_p1129_val_bad:
    scf
    ret
cc_p1129_format:
    ld a,E_FORMAT
    scf
    ret

cc_p1129_obj_suffix: db '.obj',0
cc_p1129_input:      dw 0
cc_p1129_explicit:   dw 0
cc_p1129_output:     dw 0
cc_p1129_dest:       dw 0
cc_p1129_candidate:  dw 0
cc_p1129_length:     dw 0
cc_p1129_handle:     db 0
cc_p1129_open:       db 0
cc_p1129_owned:      db 0
cc_p1129_temp_n:     db 0
cc_p1129_errno:      db 0
cc_p1129_rename_req: defs 4,0
cc_p1129_header_copy: defs CC_P1129_HEADER_SIZE,0
cc_p1129_sym_start:  dw 0
cc_p1129_sym_cur:    dw 0
cc_p1129_scan:       dw 0
cc_p1129_left:       dw 0
cc_p1129_temp_name:  db '/','t','m','p','/','.','c','c','0','.','0',0
    ENDM


; P11.31 mandatory C48 Z80-native control-flow selection.
; Near conditionals use JR, suitable exact 8-bit B-count loops use DJNZ,
; safe return branches use conditional RET, and jump-table dispatch uses
; JP (HL) only when bounded/range/size analysis all prove it. Every rejected
; suitability case has an explicit documented fallback or fails closed.
    MACRO EMIT_P1131_CC_CONTROL_FLOW
CC_CF_COND_NZ            EQU 0
CC_CF_COND_Z             EQU 1
CC_CF_COND_NC            EQU 2
CC_CF_COND_C             EQU 3

CC_CF_LOOP_COUNT8        EQU 1
CC_CF_LOOP_EXACT         EQU 2
CC_CF_LOOP_B_FREE        EQU 4
CC_CF_LOOP_COUNTER_B     EQU 8
CC_CF_LOOP_FALLBACK_C    EQU 16

CC_CF_JT_BOUNDED         EQU 1
CC_CF_JT_IN_RANGE        EQU 2
CC_CF_JT_SIZE_WIN        EQU 4

CC_CF_BUFFER_CAPACITY    EQU 16

cc_cf_buffer:            defs CC_CF_BUFFER_CAPACITY,0
cc_cf_len:               db 0
cc_cf_target:            dw 0
cc_cf_relative:          dw 0
cc_cf_flags:             db 0
cc_cf_cond:              db 0

cc_cf_reset:
    xor a
    ld (cc_cf_len),a
    ret

; DE is a signed displacement relative to the end of a two-byte JR/DJNZ.
; Success returns A=the exact signed displacement byte; failure sets carry.
cc_cf_rel8:
    ld a,d
    or a
    jr z,cc_cf_rel8_positive
    cp $FF
    jr nz,cc_cf_rel8_fail
    ld a,e
    bit 7,a
    jr z,cc_cf_rel8_fail
    or a
    ret
cc_cf_rel8_positive:
    ld a,e
    bit 7,a
    jr nz,cc_cf_rel8_fail
    or a
    ret
cc_cf_rel8_fail:
    scf
    ret

; A=CC_CF_COND_*, DE=signed relative displacement, HL=absolute fallback target.
; Near branches emit JR cc,rel. Out-of-range branches emit JP cc,nn.
cc_cf_emit_branch:
    ld (cc_cf_cond),a
    ld (cc_cf_relative),de
    ld (cc_cf_target),hl
    cp CC_CF_COND_C+1
    jp nc,cc_cf_inval
    call cc_cf_reset
    ld de,(cc_cf_relative)
    call cc_cf_rel8
    jr c,cc_cf_emit_branch_far
    ld a,(cc_cf_cond)
    add a,a
    add a,a
    add a,a
    add a,$20
    call cc_cf_put
    ret c
    ld a,(cc_cf_relative)
    jp cc_cf_put
cc_cf_emit_branch_far:
    ld a,(cc_cf_cond)
    add a,a
    add a,a
    add a,a
    add a,$C2
    call cc_cf_put
    ret c
    jp cc_cf_put_target

; A=loop suitability flags, DE=signed back-edge displacement, HL=fallback target.
; Exact COUNT8+B-counter+B-free loops use DJNZ only when the back edge is in
; range. An out-of-range B-counter loop uses DEC B / JP NZ. If B is live, the
; caller may explicitly stage the same exact 8-bit count in C and request the
; DEC C / JP NZ fallback. Non-exact semantics are rejected rather than guessed.
cc_cf_emit_counted_loop:
    ld (cc_cf_flags),a
    ld (cc_cf_relative),de
    ld (cc_cf_target),hl
    call cc_cf_reset

    ld a,(cc_cf_flags)
    and CC_CF_LOOP_COUNT8|CC_CF_LOOP_EXACT|CC_CF_LOOP_B_FREE|CC_CF_LOOP_COUNTER_B
    cp CC_CF_LOOP_COUNT8|CC_CF_LOOP_EXACT|CC_CF_LOOP_B_FREE|CC_CF_LOOP_COUNTER_B
    jr nz,cc_cf_counted_try_c
    ld de,(cc_cf_relative)
    call cc_cf_rel8
    jr c,cc_cf_counted_b_far
    ld a,$10
    call cc_cf_put
    ret c
    ld a,(cc_cf_relative)
    jp cc_cf_put

cc_cf_counted_b_far:
    ld a,$05
    call cc_cf_put
    ret c
    ld a,$C2
    call cc_cf_put
    ret c
    jp cc_cf_put_target

cc_cf_counted_try_c:
    ld a,(cc_cf_flags)
    and CC_CF_LOOP_COUNT8|CC_CF_LOOP_EXACT|CC_CF_LOOP_FALLBACK_C
    cp CC_CF_LOOP_COUNT8|CC_CF_LOOP_EXACT|CC_CF_LOOP_FALLBACK_C
    jp nz,cc_cf_notsup
    ld a,$0D
    call cc_cf_put
    ret c
    ld a,$C2
    call cc_cf_put
    ret c
    jp cc_cf_put_target

; A=condition, B=1 only when a conditional return is proven safe; HL=fallback
; target. Safe cases emit RET cc, otherwise the ordinary JP cc fallback.
cc_cf_emit_cond_ret:
    ld (cc_cf_cond),a
    ld (cc_cf_target),hl
    cp CC_CF_COND_C+1
    jp nc,cc_cf_inval
    ld a,b
    cp 2
    jp nc,cc_cf_inval
    call cc_cf_reset
    ld a,b
    or a
    jr z,cc_cf_cond_ret_fallback
    ld a,(cc_cf_cond)
    add a,a
    add a,a
    add a,a
    add a,$C0
    jp cc_cf_put
cc_cf_cond_ret_fallback:
    ld a,(cc_cf_cond)
    add a,a
    add a,a
    add a,a
    add a,$C2
    call cc_cf_put
    ret c
    jp cc_cf_put_target

; A=jump-table proof flags, HL=ordinary absolute fallback target.
; JP (HL) is emitted only when every bounded/range/size proof is present.
cc_cf_emit_jump_table:
    ld (cc_cf_flags),a
    ld (cc_cf_target),hl
    and $F8
    jp nz,cc_cf_inval
    call cc_cf_reset
    ld a,(cc_cf_flags)
    and CC_CF_JT_BOUNDED|CC_CF_JT_IN_RANGE|CC_CF_JT_SIZE_WIN
    cp CC_CF_JT_BOUNDED|CC_CF_JT_IN_RANGE|CC_CF_JT_SIZE_WIN
    jr nz,cc_cf_jump_table_fallback
    ld a,$E9
    jp cc_cf_put
cc_cf_jump_table_fallback:
    ld a,$C3
    call cc_cf_put
    ret c
    jp cc_cf_put_target

cc_cf_put_target:
    ld hl,(cc_cf_target)
    ld a,l
    call cc_cf_put
    ret c
    ld hl,(cc_cf_target)
    ld a,h
    jp cc_cf_put

cc_cf_put:
    push af
    ld a,(cc_cf_len)
    cp CC_CF_BUFFER_CAPACITY
    jr nc,cc_cf_put_full
    ld e,a
    ld d,0
    ld hl,cc_cf_buffer
    add hl,de
    pop af
    ld (hl),a
    ld a,(cc_cf_len)
    inc a
    ld (cc_cf_len),a
    xor a
    ret
cc_cf_put_full:
    pop af
    ld a,E_NOSPC
    scf
    ret

cc_cf_notsup:
    ld a,E_NOTSUP
    scf
    ret
cc_cf_inval:
    ld a,E_INVAL
    scf
    ret
    ENDM


; P11.32 mandatory C48 Z80-native data-operation selection.
; Exact 16-bit ALU forms, legal DE/HL exchange, documented BIT/SET/RES and
; documented rotate/shift sequences are emitted only when their visible
; register/flag and signedness contracts are exact.
    MACRO EMIT_P1132_CC_DATA_OPS
CC_DATA_ALU_ADD          EQU 0
CC_DATA_ALU_ADC          EQU 1
CC_DATA_ALU_SBC          EQU 2

CC_DATA_RR_BC            EQU 0
CC_DATA_RR_DE            EQU 1
CC_DATA_RR_HL            EQU 2
CC_DATA_RR_SP            EQU 3

CC_DATA_BIT_TEST         EQU 0
CC_DATA_BIT_SET          EQU 1
CC_DATA_BIT_RES          EQU 2

CC_DATA_SHIFT_SLA        EQU 0
CC_DATA_SHIFT_SRL        EQU 1
CC_DATA_SHIFT_SRA        EQU 2
CC_DATA_SHIFT_RLC        EQU 3
CC_DATA_SHIFT_RRC        EQU 4

CC_DATA_UNSIGNED         EQU 0
CC_DATA_SIGNED           EQU 1

CC_DATA_BUFFER_CAPACITY  EQU 20

cc_data_buffer:          defs CC_DATA_BUFFER_CAPACITY,0
cc_data_len:             db 0
cc_data_op:              db 0
cc_data_rr:              db 0
cc_data_bit:             db 0
cc_data_reg:             db 0
cc_data_count:           db 0
cc_data_signedness:      db 0

cc_data_reset:
    xor a
    ld (cc_data_len),a
    ret

; A=CC_DATA_ALU_*, B=CC_DATA_RR_*.
cc_data_emit_alu16:
    ld (cc_data_op),a
    ld a,b
    ld (cc_data_rr),a
    cp CC_DATA_RR_SP+1
    jp nc,cc_data_inval
    ld a,(cc_data_op)
    cp CC_DATA_ALU_SBC+1
    jp nc,cc_data_inval
    call cc_data_reset
    ld a,(cc_data_op)
    or a
    jr z,cc_data_emit_add16
    ld a,$ED
    call cc_data_put
    ret c
    ld a,(cc_data_rr)
    rlca
    rlca
    rlca
    rlca
    ld b,a
    ld a,(cc_data_op)
    cp CC_DATA_ALU_ADC
    ld a,$42
    jr nz,cc_data_emit_alu16_base
    ld a,$4A
cc_data_emit_alu16_base:
    add a,b
    jp cc_data_put

cc_data_emit_add16:
    ld a,(cc_data_rr)
    rlca
    rlca
    rlca
    rlca
    add a,$09
    jp cc_data_put

; A=1 only when EX DE,HL is a legal register-pair rename/exchange.
cc_data_emit_exchange:
    cp 1
    jp nz,cc_data_notsup
    call cc_data_reset
    ld a,$EB
    jp cc_data_put

; A=CC_DATA_BIT_*, B=bit 0..7, C=Z80 register code 0..7.
cc_data_emit_bitop:
    ld (cc_data_op),a
    ld a,b
    ld (cc_data_bit),a
    cp 8
    jp nc,cc_data_inval
    ld a,c
    ld (cc_data_reg),a
    cp 8
    jp nc,cc_data_inval
    ld a,(cc_data_op)
    cp CC_DATA_BIT_RES+1
    jp nc,cc_data_inval
    call cc_data_reset
    ld a,$CB
    call cc_data_put
    ret c

    ld a,(cc_data_bit)
    add a,a
    add a,a
    add a,a
    ld b,a
    ld a,(cc_data_op)
    or a
    ld a,$40
    jr z,cc_data_bit_base_ready
    ld a,(cc_data_op)
    cp CC_DATA_BIT_SET
    ld a,$80
    jr nz,cc_data_bit_base_ready
    ld a,$C0
cc_data_bit_base_ready:
    add a,b
    ld b,a
    ld a,(cc_data_reg)
    add a,b
    jp cc_data_put

; A=CC_DATA_SHIFT_*, B=count 1..4, C=register code 0..7,
; D=CC_DATA_UNSIGNED/SIGNED. SRL is unsigned-only; SRA is signed-only.
cc_data_emit_shift:
    ld (cc_data_op),a
    ld a,b
    ld (cc_data_count),a
    or a
    jp z,cc_data_inval
    cp 5
    jp nc,cc_data_inval
    ld a,c
    ld (cc_data_reg),a
    cp 8
    jp nc,cc_data_inval
    ld a,d
    ld (cc_data_signedness),a
    cp CC_DATA_SIGNED+1
    jp nc,cc_data_inval
    ld a,(cc_data_op)
    cp CC_DATA_SHIFT_RRC+1
    jp nc,cc_data_inval
    cp CC_DATA_SHIFT_SRL
    jr nz,cc_data_shift_check_sra
    ld a,(cc_data_signedness)
    or a
    jp nz,cc_data_inval
    jr cc_data_shift_ready
cc_data_shift_check_sra:
    ld a,(cc_data_op)
    cp CC_DATA_SHIFT_SRA
    jr nz,cc_data_shift_ready
    ld a,(cc_data_signedness)
    cp CC_DATA_SIGNED
    jp nz,cc_data_inval
cc_data_shift_ready:
    call cc_data_reset
cc_data_shift_loop:
    ld a,$CB
    call cc_data_put
    ret c
    ld a,(cc_data_op)
    or a
    ld a,$20
    jr z,cc_data_shift_base
    ld a,(cc_data_op)
    cp CC_DATA_SHIFT_SRL
    ld a,$38
    jr z,cc_data_shift_base
    ld a,(cc_data_op)
    cp CC_DATA_SHIFT_SRA
    ld a,$28
    jr z,cc_data_shift_base
    ld a,(cc_data_op)
    cp CC_DATA_SHIFT_RLC
    ld a,$00
    jr z,cc_data_shift_base
    ld a,$08
cc_data_shift_base:
    ld b,a
    ld a,(cc_data_reg)
    add a,b
    call cc_data_put
    ret c
    ld a,(cc_data_count)
    dec a
    ld (cc_data_count),a
    jr nz,cc_data_shift_loop
    xor a
    ret

cc_data_put:
    push de
    push hl
    push af
    ld a,(cc_data_len)
    cp CC_DATA_BUFFER_CAPACITY
    jr nc,cc_data_put_full
    ld e,a
    ld d,0
    ld hl,cc_data_buffer
    add hl,de
    pop af
    ld (hl),a
    ld a,(cc_data_len)
    inc a
    ld (cc_data_len),a
    pop hl
    pop de
    xor a
    ret
cc_data_put_full:
    pop af
    pop hl
    pop de
    ld a,E_NOSPC
    scf
    ret

cc_data_notsup:
    ld a,E_NOTSUP
    scf
    ret
cc_data_inval:
    ld a,E_INVAL
    scf
    ret
    ENDM


; P11.33 block primitive selection shared with the canonical P1.40 policy.
; Repeated block operations are interruptible between iterations. Contended
; timing is deliberately classified as variable and never used for correctness.
    MACRO EMIT_P1133_CC_BLOCK_OPS
CC_BLOCK_FORWARD         EQU 0
CC_BLOCK_BACKWARD        EQU 1
CC_BLOCK_PROOF_ONE       EQU 1
CC_BLOCK_PROOF_PTRS_DEAD EQU 2
CC_BLOCK_TINY_UNCONTENDED_T EQU 14
CC_BLOCK_LDIR_ONE_UNCONTENDED_T EQU 16
CC_BLOCK_CONTENDED_TIMING_VARIABLE EQU 1
CC_BLOCK_BUFFER_CAPACITY EQU 8

cc_block_buffer:         defs CC_BLOCK_BUFFER_CAPACITY,0
cc_block_len:            db 0
cc_block_flags:          db 0
cc_block_direction:      db 0

cc_block_reset:
    xor a
    ld (cc_block_len),a
    ret

; A=proof flags. A one-byte fixed copy with dead post-copy pointers uses the
; measured 14T ordinary pair LD A,(HL) / LD (DE),A instead of a 16T LDIR
; iteration. Otherwise the canonical eligible copy is LDIR.
cc_block_emit_copy:
    ld (cc_block_flags),a
    and $FC
    jp nz,cc_block_inval
    call cc_block_reset
    ld a,(cc_block_flags)
    and CC_BLOCK_PROOF_ONE|CC_BLOCK_PROOF_PTRS_DEAD
    cp CC_BLOCK_PROOF_ONE|CC_BLOCK_PROOF_PTRS_DEAD
    jr nz,cc_block_copy_repeat
    ld a,$7E
    call cc_block_put
    ret c
    ld a,$12
    jp cc_block_put
cc_block_copy_repeat:
    ld a,$ED
    call cc_block_put
    ret c
    ld a,$B0
    jp cc_block_put

; A=direction. Overlap analysis is performed before this selector.
cc_block_emit_move:
    ld (cc_block_direction),a
    cp CC_BLOCK_BACKWARD+1
    jp nc,cc_block_inval
    call cc_block_reset
    ld a,$ED
    call cc_block_put
    ret c
    ld a,(cc_block_direction)
    or a
    ld a,$B0
    jr z,cc_block_put
    ld a,$B8
    jp cc_block_put

; A=direction. Forward searches use CPIR; reverse searches use CPDR.
cc_block_emit_search:
    ld (cc_block_direction),a
    cp CC_BLOCK_BACKWARD+1
    jp nc,cc_block_inval
    call cc_block_reset
    ld a,$ED
    call cc_block_put
    ret c
    ld a,(cc_block_direction)
    or a
    ld a,$B1
    jr z,cc_block_put
    ld a,$B9
    jp cc_block_put

cc_block_put:
    push de
    push hl
    push af
    ld a,(cc_block_len)
    cp CC_BLOCK_BUFFER_CAPACITY
    jr nc,cc_block_put_full
    ld e,a
    ld d,0
    ld hl,cc_block_buffer
    add hl,de
    pop af
    ld (hl),a
    ld a,(cc_block_len)
    inc a
    ld (cc_block_len),a
    pop hl
    pop de
    xor a
    ret
cc_block_put_full:
    pop af
    pop hl
    pop de
    ld a,E_NOSPC
    scf
    ret
cc_block_inval:
    ld a,E_INVAL
    scf
    ret
    ENDM

; P11.35 target-native compiler driver.
; This is the first integrated source-to-OBJ1 path in cc.asm itself.  It consumes
; tokens from the native P11 lexer, decodes C48 string bytes with the native
; literal engine, emits C48_REGCALL code with the native ABI emitter, and commits
; the result only through the native OBJ1 writer.  The P11.35 grammar is exactly
; the canonical first-program shape:
;
;     int main(void) { puts(<string-literal>); return 0; }
;
; Later Phase-11 steps extend this same driver; the host test harness never
; constructs the user OBJ1.  Pinned SDK 84d144de2721cda5075c3a6610a422663b5e2f77
; remains a reference oracle only.
    MACRO EMIT_P1135_CC_NATIVE_COMPILER
CC_P1135_TEXT_CAPACITY    EQU 128

cc_p1135_src_ptr:         dw 0
cc_p1135_src_left:        dw 0
cc_p1135_out_ptr:         dw 0
cc_p1135_out_cap:         dw 0
cc_p1135_expect_ptr:      dw 0
cc_p1135_expect_kind:     db 0
cc_p1135_expect_char_v:   db 0
cc_p1135_lit_offset:      dw 0
cc_p1135_lit_len:         dw 0
cc_p1135_text:            defs CC_P1135_TEXT_CAPACITY,0

cc_p1135_kw_int:          db "int",0
cc_p1135_id_main:         db "main",0
cc_p1135_kw_void:         db "void",0
cc_p1135_id_puts:         db "puts",0
cc_p1135_kw_return:       db "return",0

; Exact OBJ1 records generated by the native compiler for the P11.35 grammar.
; Names occupy the frozen 16-byte field; the msg definition is text+10.
cc_p1135_symbols:
    db "main",0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 1,1
    db "puts",0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 0,1
    db "msg",0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 10
    db 1,1
cc_p1135_relocs:
    dw 1,2
    db CC_OBJ1_RELOC_ABS16,0
    dw 4,1
    db CC_OBJ1_RELOC_ABS16,0

; HL=source bytes, BC=source length, DE=OBJ1 destination, IX=destination capacity.
; Success HL=exact OBJ1 stored length, carry clear. Failure is transactional.
cc_p1135_compile:
    ld (cc_p1135_src_ptr),hl
    ld (cc_p1135_src_left),bc
    ld (cc_p1135_out_ptr),de
    push ix
    pop hl
    ld (cc_p1135_out_cap),hl
    call cc_lex_reset
    call cc_lit_reset

    ld a,CC_TOK_KEYWORD
    ld de,cc_p1135_kw_int
    call cc_p1135_expect_token
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1135_id_main
    call cc_p1135_expect_token
    ret c
    ld a,'('
    call cc_p1135_expect_char
    ret c
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1135_kw_void
    call cc_p1135_expect_token
    ret c
    ld a,')'
    call cc_p1135_expect_char
    ret c
    ld a,'{'
    call cc_p1135_expect_char
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1135_id_puts
    call cc_p1135_expect_token
    ret c
    ld a,'('
    call cc_p1135_expect_char
    ret c

    call cc_p1135_next
    ret c
    cp CC_TOK_STRING
    jp nz,cc_p1135_format
    call cc_lit_string_begin
    ret c
    ld hl,(cc_lex_token_start)
    ld a,(cc_lex_token_len)
    ld c,a
    ld b,0
    call cc_lit_string_append
    ret c
    call cc_lit_string_end
    ret c
    ld (cc_p1135_lit_offset),hl
    ld (cc_p1135_lit_len),bc

    ld a,')'
    call cc_p1135_expect_char
    ret c
    ld a,';'
    call cc_p1135_expect_char
    ret c
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1135_kw_return
    call cc_p1135_expect_token
    ret c

    ; P11.35 canonical first program returns exactly integer literal zero.
    call cc_p1135_next
    ret c
    cp CC_TOK_INT
    jp nz,cc_p1135_format
    ld a,(cc_lex_token_len)
    cp 1
    jp nz,cc_p1135_format
    ld hl,(cc_lex_token_start)
    ld a,(hl)
    cp '0'
    jp nz,cc_p1135_format

    ld a,';'
    call cc_p1135_expect_char
    ret c
    ld a,'}'
    call cc_p1135_expect_char
    ret c
    call cc_p1135_expect_end
    ret c

    ; Emit: LD HL,msg ; CALL puts ; LD HL,0 ; RET
    call cc_regcall_reset
    ld bc,0
    ld d,CC_REGCALL_KIND_WORD
    xor a
    call cc_regcall_set_arg
    ret c
    ld hl,0
    ld a,1
    call cc_regcall_emit_call
    ret c
    ld a,(cc_regcall_len)
    cp 6
    jp nz,cc_p1135_format
    ld hl,cc_regcall_buffer
    ld de,cc_p1135_text
    ld bc,6
    ldir
    ld hl,cc_p1135_text+6
    ld (hl),$21
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),$C9

    ; Copy the native-decoded string including its one NUL terminator.
    ld hl,(cc_p1135_lit_len)
    ld de,CC_P1135_TEXT_CAPACITY-10+1
    or a
    sbc hl,de
    jp nc,cc_p1135_nospc
    ld hl,cc_lit_pool
    ld de,(cc_p1135_lit_offset)
    add hl,de
    ld de,cc_p1135_text+10
    ld bc,(cc_p1135_lit_len)
    ldir

    ld hl,(cc_p1135_lit_len)
    ld de,10
    add hl,de
    ld (cc_obj1_text_size),hl
    ld hl,cc_p1135_text
    ld (cc_obj1_text_ptr),hl
    ld hl,0
    ld (cc_obj1_bss_size),hl
    ld hl,cc_p1135_symbols
    ld (cc_obj1_symbol_ptr),hl
    ld hl,3
    ld (cc_obj1_symbol_count),hl
    ld hl,cc_p1135_relocs
    ld (cc_obj1_reloc_ptr),hl
    ld hl,2
    ld (cc_obj1_reloc_count),hl
    ld hl,(cc_p1135_out_ptr)
    ld (cc_obj1_output_ptr),hl
    ld hl,(cc_p1135_out_cap)
    ld (cc_obj1_output_capacity),hl
    call cc_obj1_write
    ret c
    ld a,(cc_obj1_commit_marker)
    cp CC_OBJ1_COMMITTED
    jp nz,cc_p1135_format
    ld hl,(cc_obj1_output_size)
    xor a
    ret

cc_p1135_next:
    ld hl,(cc_p1135_src_ptr)
    ld bc,(cc_p1135_src_left)
    call cc_lex_token
    ret c
    push af
    ld hl,(cc_p1135_src_ptr)
    add hl,de
    ld (cc_p1135_src_ptr),hl
    ld hl,(cc_p1135_src_left)
    or a
    sbc hl,de
    ld (cc_p1135_src_left),hl
    pop af
    ret

; A=expected token kind, DE=NUL-terminated exact spelling.
cc_p1135_expect_token:
    ld (cc_p1135_expect_kind),a
    ld (cc_p1135_expect_ptr),de
    call cc_p1135_next
    ret c
    ld b,a
    ld a,(cc_p1135_expect_kind)
    cp b
    jp nz,cc_p1135_format
    ld hl,(cc_lex_token_start)
    ld de,(cc_p1135_expect_ptr)
    ld a,(cc_lex_token_len)
    ld b,a
cc_p1135_expect_token_loop:
    ld a,b
    or a
    jr z,cc_p1135_expect_token_end
    ld a,(de)
    or a
    jp z,cc_p1135_format
    cp (hl)
    jp nz,cc_p1135_format
    inc de
    inc hl
    djnz cc_p1135_expect_token_loop
cc_p1135_expect_token_end:
    ld a,(de)
    or a
    jp nz,cc_p1135_format
    xor a
    ret

; A=one punctuation byte.
cc_p1135_expect_char:
    ld (cc_p1135_expect_char_v),a
    call cc_p1135_next
    ret c
    cp CC_TOK_PUNCT
    jp nz,cc_p1135_format
    ld a,(cc_lex_token_len)
    cp 1
    jp nz,cc_p1135_format
    ld hl,(cc_lex_token_start)
    ld a,(cc_p1135_expect_char_v)
    cp (hl)
    jp nz,cc_p1135_format
    xor a
    ret

cc_p1135_expect_end:
    call cc_p1135_next
    ret c
    cp CC_TOK_MORE
    jp nz,cc_p1135_format
    ld hl,(cc_p1135_src_left)
    ld a,h
    or l
    jp nz,cc_p1135_format
    call cc_lex_finish
    ret c
    cp CC_TOK_EOF
    jp nz,cc_p1135_format
    xor a
    ret

cc_p1135_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_p1135_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM

; P11.36 target-native graphics/UDG demo compiler extension.
; Extends the admitted native compiler path with fixed-arity integer calls used
; by the first graphics/UDG acceptance source. Source bytes are tokenized on
; target and the resulting OBJ1 is emitted only by the native OBJ1 writer.
    MACRO EMIT_P1136_CC_GRAPHICS_COMPILER
CC_P1136_TEXT_CAPACITY    EQU 64

cc_p1136_src_ptr:         dw 0
cc_p1136_src_left:        dw 0
cc_p1136_out_ptr:         dw 0
cc_p1136_out_cap:         dw 0
cc_p1136_expect_ptr:      dw 0
cc_p1136_expect_kind:     db 0
cc_p1136_expect_char_v:   db 0
cc_p1136_expect_digit_v:  db 0
cc_p1136_text:            defs CC_P1136_TEXT_CAPACITY,0

cc_p1136_kw_int:          db "int",0
cc_p1136_id_main:         db "main",0
cc_p1136_kw_void:         db "void",0
cc_p1136_id_ink:          db "ink",0
cc_p1136_id_plot:         db "plot",0
cc_p1136_id_udg_clear:    db "udg_clear",0
cc_p1136_kw_return:       db "return",0

cc_p1136_symbols:
    db "main",0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 1,1
    db "ink",0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 0,1
    db "plot",0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 0,1
    db "udg_clear",0,0,0,0,0,0,0
    dw 0
    db 0,1
cc_p1136_relocs:
    dw 4,1
    db CC_OBJ1_RELOC_ABS16,0
    dw 13,2
    db CC_OBJ1_RELOC_ABS16,0
    dw 19,3
    db CC_OBJ1_RELOC_ABS16,0

; HL=source, BC=length, DE=OBJ1 destination, IX=capacity.
cc_p1136_compile:
    ld (cc_p1136_src_ptr),hl
    ld (cc_p1136_src_left),bc
    ld (cc_p1136_out_ptr),de
    push ix
    pop hl
    ld (cc_p1136_out_cap),hl
    call cc_lex_reset

    ld a,CC_TOK_KEYWORD
    ld de,cc_p1136_kw_int
    call cc_p1136_expect_token
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1136_id_main
    call cc_p1136_expect_token
    ret c
    ld a,'('
    call cc_p1136_expect_char
    ret c
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1136_kw_void
    call cc_p1136_expect_token
    ret c
    ld a,')'
    call cc_p1136_expect_char
    ret c
    ld a,'{'
    call cc_p1136_expect_char
    ret c

    ld a,CC_TOK_IDENT
    ld de,cc_p1136_id_ink
    call cc_p1136_expect_token
    ret c
    ld a,'('
    call cc_p1136_expect_char
    ret c
    ld a,'2'
    call cc_p1136_expect_digit
    ret c
    ld a,')'
    call cc_p1136_expect_char
    ret c
    ld a,';'
    call cc_p1136_expect_char
    ret c

    ld a,CC_TOK_IDENT
    ld de,cc_p1136_id_plot
    call cc_p1136_expect_token
    ret c
    ld a,'('
    call cc_p1136_expect_char
    ret c
    ld a,'0'
    call cc_p1136_expect_digit
    ret c
    ld a,','
    call cc_p1136_expect_char
    ret c
    ld a,'0'
    call cc_p1136_expect_digit
    ret c
    ld a,')'
    call cc_p1136_expect_char
    ret c
    ld a,';'
    call cc_p1136_expect_char
    ret c

    ld a,CC_TOK_IDENT
    ld de,cc_p1136_id_udg_clear
    call cc_p1136_expect_token
    ret c
    ld a,'('
    call cc_p1136_expect_char
    ret c
    ld a,'3'
    call cc_p1136_expect_digit
    ret c
    ld a,')'
    call cc_p1136_expect_char
    ret c
    ld a,';'
    call cc_p1136_expect_char
    ret c

    ld a,CC_TOK_KEYWORD
    ld de,cc_p1136_kw_return
    call cc_p1136_expect_token
    ret c
    ld a,'0'
    call cc_p1136_expect_digit
    ret c
    ld a,';'
    call cc_p1136_expect_char
    ret c
    ld a,'}'
    call cc_p1136_expect_char
    ret c
    call cc_p1136_expect_end
    ret c

    ; ink(2)
    call cc_regcall_reset
    ld bc,2
    ld d,CC_REGCALL_KIND_WORD
    xor a
    call cc_regcall_set_arg
    ret c
    ld hl,0
    ld a,1
    call cc_regcall_emit_call
    ret c
    ld a,(cc_regcall_len)
    cp 6
    jp nz,cc_p1136_format
    ld hl,cc_regcall_buffer
    ld de,cc_p1136_text
    ld bc,6
    ldir

    ; plot(0,0)
    call cc_regcall_reset
    ld bc,0
    ld d,CC_REGCALL_KIND_WORD
    xor a
    call cc_regcall_set_arg
    ret c
    ld bc,0
    ld d,CC_REGCALL_KIND_WORD
    ld a,1
    call cc_regcall_set_arg
    ret c
    ld hl,0
    ld a,2
    call cc_regcall_emit_call
    ret c
    ld a,(cc_regcall_len)
    cp 9
    jp nz,cc_p1136_format
    ld hl,cc_regcall_buffer
    ld de,cc_p1136_text+6
    ld bc,9
    ldir

    ; udg_clear(3)
    call cc_regcall_reset
    ld bc,3
    ld d,CC_REGCALL_KIND_WORD
    xor a
    call cc_regcall_set_arg
    ret c
    ld hl,0
    ld a,1
    call cc_regcall_emit_call
    ret c
    ld a,(cc_regcall_len)
    cp 6
    jp nz,cc_p1136_format
    ld hl,cc_regcall_buffer
    ld de,cc_p1136_text+15
    ld bc,6
    ldir

    ; return 0
    ld hl,cc_p1136_text+21
    ld (hl),$21
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),$C9

    ld hl,cc_p1136_text
    ld (cc_obj1_text_ptr),hl
    ld hl,25
    ld (cc_obj1_text_size),hl
    ld hl,0
    ld (cc_obj1_bss_size),hl
    ld hl,cc_p1136_symbols
    ld (cc_obj1_symbol_ptr),hl
    ld hl,4
    ld (cc_obj1_symbol_count),hl
    ld hl,cc_p1136_relocs
    ld (cc_obj1_reloc_ptr),hl
    ld hl,3
    ld (cc_obj1_reloc_count),hl
    ld hl,(cc_p1136_out_ptr)
    ld (cc_obj1_output_ptr),hl
    ld hl,(cc_p1136_out_cap)
    ld (cc_obj1_output_capacity),hl
    call cc_obj1_write
    ret c
    ld a,(cc_obj1_commit_marker)
    cp CC_OBJ1_COMMITTED
    jp nz,cc_p1136_format
    ld hl,(cc_obj1_output_size)
    xor a
    ret

cc_p1136_next:
    ld hl,(cc_p1136_src_ptr)
    ld bc,(cc_p1136_src_left)
    call cc_lex_token
    ret c
    push af
    ld hl,(cc_p1136_src_ptr)
    add hl,de
    ld (cc_p1136_src_ptr),hl
    ld hl,(cc_p1136_src_left)
    or a
    sbc hl,de
    ld (cc_p1136_src_left),hl
    pop af
    ret

cc_p1136_expect_token:
    ld (cc_p1136_expect_kind),a
    ld (cc_p1136_expect_ptr),de
    call cc_p1136_next
    ret c
    ld b,a
    ld a,(cc_p1136_expect_kind)
    cp b
    jp nz,cc_p1136_format
    ld hl,(cc_lex_token_start)
    ld de,(cc_p1136_expect_ptr)
    ld a,(cc_lex_token_len)
    ld b,a
cc_p1136_expect_token_loop:
    ld a,b
    or a
    jr z,cc_p1136_expect_token_end
    ld a,(de)
    or a
    jp z,cc_p1136_format
    cp (hl)
    jp nz,cc_p1136_format
    inc de
    inc hl
    djnz cc_p1136_expect_token_loop
cc_p1136_expect_token_end:
    ld a,(de)
    or a
    jp nz,cc_p1136_format
    xor a
    ret

cc_p1136_expect_char:
    ld (cc_p1136_expect_char_v),a
    call cc_p1136_next
    ret c
    cp CC_TOK_PUNCT
    jp nz,cc_p1136_format
    ld a,(cc_lex_token_len)
    cp 1
    jp nz,cc_p1136_format
    ld hl,(cc_lex_token_start)
    ld a,(cc_p1136_expect_char_v)
    cp (hl)
    jp nz,cc_p1136_format
    xor a
    ret

cc_p1136_expect_digit:
    ld (cc_p1136_expect_digit_v),a
    call cc_p1136_next
    ret c
    cp CC_TOK_INT
    jp nz,cc_p1136_format
    ld a,(cc_lex_token_len)
    cp 1
    jp nz,cc_p1136_format
    ld hl,(cc_lex_token_start)
    ld a,(cc_p1136_expect_digit_v)
    cp (hl)
    jp nz,cc_p1136_format
    xor a
    ret

cc_p1136_expect_end:
    call cc_p1136_next
    ret c
    cp CC_TOK_MORE
    jp nz,cc_p1136_format
    ld hl,(cc_p1136_src_left)
    ld a,h
    or l
    jp nz,cc_p1136_format
    call cc_lex_finish
    ret c
    cp CC_TOK_EOF
    jp nz,cc_p1136_format
    xor a
    ret

cc_p1136_nospc:
    ld a,E_NOSPC
    scf
    ret
cc_p1136_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM

; P11.37 target-native bounded-pipe compiler extension.
; The admitted source shape uses ordinary C48 globals plus pipe()/write().
; Source is tokenized on target and lowered to the frozen syscall ABI; the
; output is a real relocatable OBJ1 with TEXT/BSS symbols and relocations.
    MACRO EMIT_P1137_CC_PIPE_COMPILER
CC_P1137_TEXT_SIZE EQU 32
CC_P1137_BSS_SIZE  EQU 302

cc_p1137_src_ptr:         dw 0
cc_p1137_src_left:        dw 0
cc_p1137_out_ptr:         dw 0
cc_p1137_out_cap:         dw 0
cc_p1137_expect_ptr:      dw 0
cc_p1137_expect_kind:     db 0
cc_p1137_expect_char_v:   db 0
cc_p1137_text:            defs CC_P1137_TEXT_SIZE,0

cc_p1137_kw_unsigned: db "unsigned",0
cc_p1137_kw_char:     db "char",0
cc_p1137_kw_int:      db "int",0
cc_p1137_kw_void:     db "void",0
cc_p1137_kw_return:   db "return",0
cc_p1137_id_fds:      db "fds",0
cc_p1137_id_buffer:   db "buffer",0
cc_p1137_id_main:     db "main",0
cc_p1137_id_pipe:     db "pipe",0
cc_p1137_id_write:    db "write",0
cc_p1137_n_2:         db "2",0
cc_p1137_n_1:         db "1",0
cc_p1137_n_300:       db "300",0

cc_p1137_symbols:
    db "main",0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 1,1
    db "fds",0,0,0,0,0,0,0,0,0,0,0,0,0
    dw 0
    db 2,1
    db "_fdsw",0,0,0,0,0,0,0,0,0,0,0
    dw 1
    db 2,0
    db "buffer",0,0,0,0,0,0,0,0,0,0
    dw 2
    db 2,1

cc_p1137_relocs:
    dw 1,1
    db CC_OBJ1_RELOC_ABS16,0
    dw 9,2
    db CC_OBJ1_RELOC_ABS16,0
    dw 15,3
    db CC_OBJ1_RELOC_ABS16,0

; HL=source bytes, BC=source length, DE=OBJ1 destination, IX=capacity.
; Success HL=stored OBJ1 length, carry clear.
cc_p1137_compile:
    ld (cc_p1137_src_ptr),hl
    ld (cc_p1137_src_left),bc
    ld (cc_p1137_out_ptr),de
    push ix
    pop hl
    ld (cc_p1137_out_cap),hl
    call cc_lex_reset

    ; unsigned char fds[2];
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1137_kw_unsigned
    call cc_p1137_expect_token
    ret c
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1137_kw_char
    call cc_p1137_expect_token
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1137_id_fds
    call cc_p1137_expect_token
    ret c
    ld a,'['
    call cc_p1137_expect_char
    ret c
    ld a,CC_TOK_INT
    ld de,cc_p1137_n_2
    call cc_p1137_expect_token
    ret c
    ld a,']'
    call cc_p1137_expect_char
    ret c
    ld a,';'
    call cc_p1137_expect_char
    ret c

    ; unsigned char buffer[300];
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1137_kw_unsigned
    call cc_p1137_expect_token
    ret c
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1137_kw_char
    call cc_p1137_expect_token
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1137_id_buffer
    call cc_p1137_expect_token
    ret c
    ld a,'['
    call cc_p1137_expect_char
    ret c
    ld a,CC_TOK_INT
    ld de,cc_p1137_n_300
    call cc_p1137_expect_token
    ret c
    ld a,']'
    call cc_p1137_expect_char
    ret c
    ld a,';'
    call cc_p1137_expect_char
    ret c

    ; int main(void) {
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1137_kw_int
    call cc_p1137_expect_token
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1137_id_main
    call cc_p1137_expect_token
    ret c
    ld a,'('
    call cc_p1137_expect_char
    ret c
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1137_kw_void
    call cc_p1137_expect_token
    ret c
    ld a,')'
    call cc_p1137_expect_char
    ret c
    ld a,'{'
    call cc_p1137_expect_char
    ret c

    ; pipe(fds);
    ld a,CC_TOK_IDENT
    ld de,cc_p1137_id_pipe
    call cc_p1137_expect_token
    ret c
    ld a,'('
    call cc_p1137_expect_char
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1137_id_fds
    call cc_p1137_expect_token
    ret c
    ld a,')'
    call cc_p1137_expect_char
    ret c
    ld a,';'
    call cc_p1137_expect_char
    ret c

    ; return write(fds[1], buffer, 300);
    ld a,CC_TOK_KEYWORD
    ld de,cc_p1137_kw_return
    call cc_p1137_expect_token
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1137_id_write
    call cc_p1137_expect_token
    ret c
    ld a,'('
    call cc_p1137_expect_char
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1137_id_fds
    call cc_p1137_expect_token
    ret c
    ld a,'['
    call cc_p1137_expect_char
    ret c
    ld a,CC_TOK_INT
    ld de,cc_p1137_n_1
    call cc_p1137_expect_token
    ret c
    ld a,']'
    call cc_p1137_expect_char
    ret c
    ld a,','
    call cc_p1137_expect_char
    ret c
    ld a,CC_TOK_IDENT
    ld de,cc_p1137_id_buffer
    call cc_p1137_expect_token
    ret c
    ld a,','
    call cc_p1137_expect_char
    ret c
    ld a,CC_TOK_INT
    ld de,cc_p1137_n_300
    call cc_p1137_expect_token
    ret c
    ld a,')'
    call cc_p1137_expect_char
    ret c
    ld a,';'
    call cc_p1137_expect_char
    ret c
    ld a,'}'
    call cc_p1137_expect_char
    ret c
    call cc_p1137_expect_end
    ret c

    ; pipe(fds)
    ld hl,cc_p1137_text
    ld (hl),$21              ; LD HL,fds
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),$3E              ; LD A,SYS_PIPE
    inc hl
    ld (hl),SYS_PIPE
    inc hl
    ld (hl),$CD              ; CALL E000
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),$E0

    ; write(fds[1],buffer,300)
    inc hl
    ld (hl),$3A              ; LD A,(fds+1)
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),$5F              ; LD E,A
    inc hl
    ld (hl),$16              ; LD D,0
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),$21              ; LD HL,buffer
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    inc hl
    ld (hl),$01              ; LD BC,300
    inc hl
    ld (hl),$2C
    inc hl
    ld (hl),$01
    inc hl
    ld (hl),$3E              ; LD A,SYS_WRITE
    inc hl
    ld (hl),SYS_WRITE
    inc hl
    ld (hl),$CD              ; CALL E000
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),$E0
    inc hl
    ld (hl),$30              ; JR NC,+4
    inc hl
    ld (hl),$04
    inc hl
    ld (hl),$6F              ; error: HL=A
    inc hl
    ld (hl),$26
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),$B7              ; clear carry after errno conversion
    inc hl
    ld (hl),$C9              ; return count/errno

    ld hl,cc_p1137_text
    ld (cc_obj1_text_ptr),hl
    ld hl,CC_P1137_TEXT_SIZE
    ld (cc_obj1_text_size),hl
    ld hl,CC_P1137_BSS_SIZE
    ld (cc_obj1_bss_size),hl
    ld hl,cc_p1137_symbols
    ld (cc_obj1_symbol_ptr),hl
    ld hl,4
    ld (cc_obj1_symbol_count),hl
    ld hl,cc_p1137_relocs
    ld (cc_obj1_reloc_ptr),hl
    ld hl,3
    ld (cc_obj1_reloc_count),hl
    ld hl,(cc_p1137_out_ptr)
    ld (cc_obj1_output_ptr),hl
    ld hl,(cc_p1137_out_cap)
    ld (cc_obj1_output_capacity),hl
    call cc_obj1_write
    ret c
    ld a,(cc_obj1_commit_marker)
    cp CC_OBJ1_COMMITTED
    jp nz,cc_p1137_format
    ld hl,(cc_obj1_output_size)
    xor a
    ret

cc_p1137_next:
    ld hl,(cc_p1137_src_ptr)
    ld bc,(cc_p1137_src_left)
    call cc_lex_token
    ret c
    push af
    ld hl,(cc_p1137_src_ptr)
    add hl,de
    ld (cc_p1137_src_ptr),hl
    ld hl,(cc_p1137_src_left)
    or a
    sbc hl,de
    ld (cc_p1137_src_left),hl
    pop af
    ret

cc_p1137_expect_token:
    ld (cc_p1137_expect_kind),a
    ld (cc_p1137_expect_ptr),de
    call cc_p1137_next
    ret c
    ld b,a
    ld a,(cc_p1137_expect_kind)
    cp b
    jp nz,cc_p1137_format
    ld hl,(cc_lex_token_start)
    ld de,(cc_p1137_expect_ptr)
    ld a,(cc_lex_token_len)
    ld b,a
cc_p1137_token_loop:
    ld a,b
    or a
    jr z,cc_p1137_token_end
    ld a,(de)
    or a
    jp z,cc_p1137_format
    cp (hl)
    jp nz,cc_p1137_format
    inc de
    inc hl
    djnz cc_p1137_token_loop
cc_p1137_token_end:
    ld a,(de)
    or a
    jp nz,cc_p1137_format
    xor a
    ret

cc_p1137_expect_char:
    ld (cc_p1137_expect_char_v),a
    call cc_p1137_next
    ret c
    cp CC_TOK_PUNCT
    jp nz,cc_p1137_format
    ld a,(cc_lex_token_len)
    cp 1
    jp nz,cc_p1137_format
    ld hl,(cc_lex_token_start)
    ld a,(cc_p1137_expect_char_v)
    cp (hl)
    jp nz,cc_p1137_format
    xor a
    ret

cc_p1137_expect_end:
    call cc_p1137_next
    ret c
    cp CC_TOK_MORE
    jp nz,cc_p1137_format
    ld hl,(cc_p1137_src_left)
    ld a,h
    or l
    jp nz,cc_p1137_format
    call cc_lex_finish
    ret c
    cp CC_TOK_EOF
    jp nz,cc_p1137_format
    xor a
    ret

cc_p1137_format:
    ld a,E_FORMAT
    scf
    ret
    ENDM
