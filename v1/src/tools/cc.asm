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

; HL=source-window pointer, BC=window bytes. Source windows are bounded;
; the caller may feed arbitrarily many windows without materializing the source.
cc_pipeline_feed:
    ld a,b
    or a
    jr nz,cc_p1102_nospc
    ld a,c
    cp CC_SOURCE_WINDOW_SIZE+1
    jr nc,cc_p1102_nospc
    ld hl,(cc_stream_total)
    add hl,bc
    jr c,cc_p1102_nospc
    ld (cc_stream_total),hl
    ld a,CC_STAGE_LEX
    ld (cc_pipeline_stage),a
    xor a
    ret

cc_pipeline_parse:
    ld a,(cc_pipeline_stage)
    cp CC_STAGE_LEX
    jr nz,cc_p1102_format
    ld a,CC_STAGE_PARSE
    ld (cc_pipeline_stage),a
    xor a
    ret

cc_pipeline_emit:
    ld a,(cc_pipeline_stage)
    cp CC_STAGE_PARSE
    jr nz,cc_p1102_format
    ld a,CC_STAGE_EMIT
    ld (cc_pipeline_stage),a
    xor a
    ret

cc_pipeline_obj1:
    ld a,(cc_pipeline_stage)
    cp CC_STAGE_EMIT
    jr nz,cc_p1102_format
    ld a,CC_STAGE_OBJ1
    ld (cc_pipeline_stage),a
    xor a
    ret

cc_expr_enter:
    ld a,(cc_expr_depth)
    cp CC_EXPR_CAPACITY
    jr nc,cc_p1102_nospc
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
    jr z,cc_p1102_format
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
    jr nc,cc_p1102_inval
    ld a,c
    or a
    ld a,(hl)
    jr nz,cc_ident_tail
    call cc_ident_first_char
    jr c,cc_p1102_inval
    jr cc_ident_accept
cc_ident_tail:
    call cc_ident_next_char
    jr c,cc_p1102_inval
cc_ident_accept:
    inc c
    inc hl
    djnz cc_ident_loop
    jr cc_p1102_inval
cc_ident_nul:
    ld a,c
    or a
    jr z,cc_p1102_inval
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
    jr c,cc_p1102_nospc

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
