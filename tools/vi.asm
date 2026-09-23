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
; P9.01 vi transient MEX1 skeleton: exact tty mode/cursor save and restore.

    MACRO EMIT_P901_VI_ROUTINES
VI_TTY_GET_MODE         EQU 1
VI_TTY_SET_MODE         EQU 2
VI_TTY_SET_CURSOR       EQU 4
VI_TTY_GET_CURSOR       EQU 5
VI_MODE_64              EQU 64
VI_CURSOR_BLOCK         EQU 2

vi_entry:
    xor a
    ld (vi_have_mode),a
    ld (vi_have_cursor),a
    ld (vi_primary_errno),a
    call vi_open_tty
    jp c,vi_exit_error
    ld a,VI_TTY_GET_MODE
    ld hl,vi_saved_mode
    call vi_ioctl
    jp c,vi_close_error
    ld a,1
    ld (vi_have_mode),a
    ld a,VI_TTY_GET_CURSOR
    ld hl,vi_saved_cursor
    call vi_ioctl
    jp c,vi_unwind_error
    ld a,1
    ld (vi_have_cursor),a
    ld a,VI_MODE_64
    ld (vi_work),a
    ld a,VI_TTY_SET_MODE
    ld hl,vi_work
    call vi_ioctl
    jp c,vi_unwind_error
    ld a,VI_CURSOR_BLOCK
    ld (vi_work),a
    ld a,VI_TTY_SET_CURSOR
    ld hl,vi_work
    call vi_ioctl
    jp c,vi_unwind_error

; Shared unwind path is deliberately retained for all later editor exits.
vi_normal_exit:
    xor a
    ld (vi_primary_errno),a
    call vi_restore_terminal
    jr c,vi_exit_error
    call vi_close_tty
    jr c,vi_exit_error
    xor a
    jr vi_exit_a

vi_unwind_error:
    ld (vi_primary_errno),a
    call vi_restore_terminal
    call vi_close_tty
    ld a,(vi_primary_errno)
    jr vi_exit_a

vi_close_error:
    ld (vi_primary_errno),a
    call vi_close_tty
    ld a,(vi_primary_errno)
    jr vi_exit_a

vi_restore_terminal:
    xor a
    ld (vi_restore_errno),a
    ld a,(vi_have_mode)
    or a
    jr z,vi_restore_cursor
    ld a,VI_TTY_SET_MODE
    ld hl,vi_saved_mode
    call vi_ioctl
    jr nc,vi_restore_cursor
    ld (vi_restore_errno),a
vi_restore_cursor:
    ld a,(vi_have_cursor)
    or a
    jr z,vi_restore_done
    ld a,VI_TTY_SET_CURSOR
    ld hl,vi_saved_cursor
    call vi_ioctl
    jr nc,vi_restore_done
    ld b,a
    ld a,(vi_restore_errno)
    or a
    jr nz,vi_restore_done
    ld a,b
    ld (vi_restore_errno),a
vi_restore_done:
    ld a,(vi_restore_errno)
    or a
    ret z
    scf
    ret

vi_exit_error:
vi_exit_a:
    ld l,a
    ld h,0
    ld a,SYS_EXIT
    call SYSCALL_GATEWAY
    ret

vi_open_tty:
    ld hl,vi_tty
    ld c,O_READ|O_WRITE
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,vi_open_bad
    ld a,l
    ld (vi_handle),a
    xor a
    ret
vi_open_bad:
    ld a,E_FORMAT
    scf
    ret

vi_close_tty:
    ld a,(vi_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    jp SYSCALL_GATEWAY

vi_ioctl:
    ld (vi_req+1),a
    ld (vi_req+2),hl
    ld a,(vi_handle)
    ld (vi_req),a
    ld hl,vi_req
    ld a,SYS_IOCTL
    jp SYSCALL_GATEWAY

vi_tty: db '/','d','e','v','/','t','t','y',0
vi_req: db 0,0
    dw 0
vi_handle: db 0
vi_saved_mode: db 0
vi_saved_cursor: db 0
vi_have_mode: db 0
vi_have_cursor: db 0
vi_primary_errno: db 0
vi_restore_errno: db 0
vi_work: db 0

; P9.02 named-buffer loader.  The source handle is transient: a completed
; load has no live source handle before any editor command can be accepted.
VI_LOAD_CAPACITY        EQU 1024

vi_p902_load:
    ld (vi_load_path),hl
    xor a
    ld (vi_source_open),a
    ld (vi_buffer_ready),a
    ld (vi_buffer_len),a
    ld (vi_buffer_len+1),a

    ld (vi_stat_req),hl
    ld hl,vi_stat_out
    ld (vi_stat_req+2),hl
    ld hl,vi_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    ret c

    ld a,(vi_stat_out)
    cp OBJ_TXT
    jr z,vi_load_type_ok
    cp OBJ_ASM
    jr z,vi_load_type_ok
    cp OBJ_C
    jr z,vi_load_type_ok
    cp OBJ_CFG
    jr z,vi_load_type_ok
    ld a,E_FORMAT
    scf
    ret

vi_load_type_ok:
    ld hl,(vi_load_path)
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,vi_load_bad_handle
    ld a,l
    ld (vi_source_handle),a
    ld a,1
    ld (vi_source_open),a

vi_load_read:
    ld a,(vi_source_handle)
    ld e,a
    ld d,0
    ld hl,vi_io_chunk
    ld bc,64
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jr c,vi_load_stream_error
    ld a,h
    or l
    jr z,vi_load_eof
    ld (vi_chunk_len),hl
    ex de,hl
    ld hl,(vi_buffer_len)
    add hl,de
    ld a,h
    cp 4
    jr c,vi_load_room
    jr nz,vi_load_overflow
    ld a,l
    or a
    jr nz,vi_load_overflow
vi_load_room:
    ld (vi_new_len),hl
    ld de,vi_buffer
    ld hl,(vi_buffer_len)
    add hl,de
    ex de,hl
    ld hl,vi_io_chunk
    ld bc,(vi_chunk_len)
    ldir
    ld hl,(vi_new_len)
    ld (vi_buffer_len),hl
    jr vi_load_read

vi_load_overflow:
    ld a,E_NOMEM
    jr vi_load_stream_error

vi_load_eof:
    call vi_close_source
    ret c
    ld a,1
    ld (vi_buffer_ready),a
    xor a
    ret

vi_load_stream_error:
    ld (vi_load_errno),a
    call vi_close_source
    ld a,(vi_load_errno)
    scf
    ret

vi_load_bad_handle:
    ld a,E_FORMAT
    scf
    ret

vi_close_source:
    ld a,(vi_source_open)
    or a
    ret z
    xor a
    ld (vi_source_open),a
    ld a,(vi_source_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret

vi_load_path: dw 0
vi_source_handle: db 0
vi_source_open: db 0
vi_buffer_ready: db 0
vi_load_errno: db 0
vi_chunk_len: dw 0
vi_new_len: dw 0
vi_buffer_len: dw 0
vi_stat_req: defs 4,0
vi_stat_out: defs 10,0
vi_io_chunk: defs 64,0
vi_buffer: defs VI_LOAD_CAPACITY,0

; P9.03 gap buffer plus compact line-offset index.  The file bytes live only
; once in vi_buffer; the gap is [vi_gap_start,vi_gap_end).  The index contains
; 16-bit logical starts and therefore never duplicates the text.
VI_LINE_MAX             EQU 128

vi_p903_init:
    ld hl,(vi_buffer_len)
    ld (vi_gap_start),hl
    ld hl,VI_LOAD_CAPACITY
    ld (vi_gap_end),hl
    xor a
    ld (vi_undo_kind),a
    ld (vi_dirty),a
    ld (vi_fail_gap_alloc),a
    ld (vi_fail_index_alloc),a
    jp vi_p903_reindex

; Insert A at logical offset HL.  All failure decisions precede gap motion, so
; allocation/index failure leaves text, index, dirty state and gap byte-identical.
vi_p903_insert_byte:
    ld (vi_edit_pos),hl
    ld (vi_edit_byte),a
    ld a,(vi_fail_gap_alloc)
    or a
    jp nz,vi_p903_nomem
    ld a,(vi_fail_index_alloc)
    or a
    jp nz,vi_p903_nomem
    ld de,(vi_buffer_len)
    push hl
    or a
    sbc hl,de
    pop hl
    jr c,vi_p903_insert_pos_ok
    jr z,vi_p903_insert_pos_ok
    ld a,E_INVAL
    scf
    ret
vi_p903_insert_pos_ok:
    ld de,(vi_gap_end)
    ld bc,(vi_gap_start)
    push hl
    ex de,hl
    or a
    sbc hl,bc
    pop hl
    jp z,vi_p903_nomem
    ld a,(vi_edit_byte)
    cp 10
    jr nz,vi_p903_insert_ready
    ld a,(vi_line_count)
    cp VI_LINE_MAX
    jp nc,vi_p903_nomem
vi_p903_insert_ready:
    ld hl,(vi_edit_pos)
    call vi_p903_move_gap
    ld hl,(vi_gap_start)
    ld de,vi_buffer
    add hl,de
    ld a,(vi_edit_byte)
    ld (hl),a
    ld hl,(vi_gap_start)
    inc hl
    ld (vi_gap_start),hl
    ld hl,(vi_buffer_len)
    inc hl
    ld (vi_buffer_len),hl
    ld a,1
    ld (vi_dirty),a
    ld (vi_undo_kind),a
    ld hl,(vi_edit_pos)
    ld (vi_undo_pos),hl
    ld a,(vi_edit_byte)
    ld (vi_undo_byte),a
    jp vi_p903_reindex

; Delete one byte at logical offset HL.
vi_p903_delete_byte:
    ld (vi_edit_pos),hl
    ld a,(vi_fail_index_alloc)
    or a
    jp nz,vi_p903_nomem
    ld de,(vi_buffer_len)
    push hl
    or a
    sbc hl,de
    pop hl
    jr nc,vi_p903_badpos
    call vi_p903_move_gap
    ld hl,(vi_gap_end)
    ld de,vi_buffer
    add hl,de
    ld a,(hl)
    ld (vi_undo_byte),a
    ld hl,(vi_gap_end)
    inc hl
    ld (vi_gap_end),hl
    ld hl,(vi_buffer_len)
    dec hl
    ld (vi_buffer_len),hl
    ld a,1
    ld (vi_dirty),a
    ld a,2
    ld (vi_undo_kind),a
    ld hl,(vi_edit_pos)
    ld (vi_undo_pos),hl
    jp vi_p903_reindex
vi_p903_badpos:
    ld a,E_INVAL
    scf
    ret
vi_p903_nomem:
    ld a,E_NOMEM
    scf
    ret

; Move the physical gap to logical offset HL without changing logical bytes.
vi_p903_move_gap:
    ld (vi_gap_target),hl
vi_p903_move_again:
    ld hl,(vi_gap_start)
    ld de,(vi_gap_target)
    or a
    sbc hl,de
    ret z
    jr c,vi_p903_move_right
    ld hl,(vi_gap_start)
    dec hl
    ld (vi_gap_start),hl
    push hl
    ld de,vi_buffer
    add hl,de
    ld a,(hl)
    ld (vi_move_byte),a
    pop hl
    ld hl,(vi_gap_end)
    dec hl
    ld (vi_gap_end),hl
    ld de,vi_buffer
    add hl,de
    ld a,(vi_move_byte)
    ld (hl),a
    jr vi_p903_move_again
vi_p903_move_right:
    ld hl,(vi_gap_end)
    ld de,vi_buffer
    add hl,de
    ld a,(hl)
    ld (vi_move_byte),a
    ld hl,(vi_gap_start)
    ld de,vi_buffer
    add hl,de
    ld a,(vi_move_byte)
    ld (hl),a
    ld hl,(vi_gap_start)
    inc hl
    ld (vi_gap_start),hl
    ld hl,(vi_gap_end)
    inc hl
    ld (vi_gap_end),hl
    jr vi_p903_move_again

; Return logical byte HL in A.
vi_p903_get_byte:
    push hl
    ld de,(vi_gap_start)
    or a
    sbc hl,de
    pop hl
    jr c,vi_p903_get_physical
    push hl
    ld hl,(vi_gap_end)
    or a
    sbc hl,de
    ld b,h
    ld c,l
    pop hl
    add hl,bc
vi_p903_get_physical:
    ld de,vi_buffer
    add hl,de
    ld a,(hl)
    ret

; Build into a compact staging index and publish only after complete success.
vi_p903_reindex:
    ld a,(vi_fail_index_alloc)
    or a
    jp nz,vi_p903_nomem
    xor a
    ld (vi_line_stage),a
    ld (vi_line_stage+1),a
    ld a,1
    ld (vi_stage_line_count),a
    ld hl,0
    ld (vi_scan_pos),hl
vi_p903_reindex_loop:
    ld hl,(vi_scan_pos)
    ld de,(vi_buffer_len)
    push hl
    or a
    sbc hl,de
    pop hl
    jr z,vi_p903_reindex_commit
    call vi_p903_get_byte
    cp 10
    jr nz,vi_p903_reindex_next
    ld a,(vi_stage_line_count)
    cp VI_LINE_MAX
    jp nc,vi_p903_nomem
    ld e,a
    ld d,0
    sla e
    rl d
    push hl
    ld hl,vi_line_stage
    add hl,de
    ex de,hl
    pop hl
    inc hl
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    ld a,(vi_stage_line_count)
    inc a
    ld (vi_stage_line_count),a
    dec hl
vi_p903_reindex_next:
    ld hl,(vi_scan_pos)
    inc hl
    ld (vi_scan_pos),hl
    jr vi_p903_reindex_loop
vi_p903_reindex_commit:
    ld a,(vi_stage_line_count)
    ld (vi_line_count),a
    add a,a
    ld c,a
    ld b,0
    ld hl,vi_line_stage
    ld de,vi_line_index
    ldir
    xor a
    ret

vi_gap_start: dw 0
vi_gap_end: dw 0
vi_line_count: db 0
vi_stage_line_count: db 0
vi_fail_gap_alloc: db 0
vi_fail_index_alloc: db 0
vi_dirty: db 0
vi_undo_kind: db 0
vi_undo_pos: dw 0
vi_undo_byte: db 0
vi_edit_pos: dw 0
vi_edit_byte: db 0
vi_gap_target: dw 0
vi_move_byte: db 0
vi_scan_pos: dw 0
vi_line_stage: defs VI_LINE_MAX*2,0
vi_line_index: defs VI_LINE_MAX*2,0
    ENDM
