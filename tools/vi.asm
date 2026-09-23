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
    ld hl,vi_line_stage
    add hl,de
    ex de,hl
    ld hl,(vi_scan_pos)
    inc hl
    ld a,l
    ld (de),a
    inc de
    ld a,h
    ld (de),a
    ld a,(vi_stage_line_count)
    inc a
    ld (vi_stage_line_count),a
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

; P9.04 exact invocation and unnamed/named target state.
VI_TARGET_MAX           EQU 31

; HL points at canonical ARG1.  argc includes argv0.
vi_p904_invocation:
    ld a,(hl)
    cp 'A'
    jp nz,vi_p904_invalid
    inc hl
    ld a,(hl)
    cp 'R'
    jp nz,vi_p904_invalid
    inc hl
    ld a,(hl)
    cp 'G'
    jp nz,vi_p904_invalid
    inc hl
    ld a,(hl)
    cp '1'
    jp nz,vi_p904_invalid
    inc hl
    ld a,(hl)
    cp 1
    jr z,vi_p904_new
    cp 2
    jp nz,vi_p904_invalid
    inc hl
    inc hl
    inc hl
    inc hl
vi_p904_skip_argv0:
    ld a,(hl)
    inc hl
    or a
    jr nz,vi_p904_skip_argv0
    push hl
    call vi_p902_load
    pop hl
    ret c
    push hl
    call vi_p903_init
    pop hl
    ret c
    ld a,(vi_stat_out)
    jp vi_p904_commit_target

vi_p904_new:
    xor a
    ld (vi_buffer_len),a
    ld (vi_buffer_len+1),a
    ld (vi_named),a
    ld (vi_dirty),a
    ld a,OBJ_TXT
    ld (vi_target_type),a
    ld a,1
    ld (vi_buffer_ready),a
    call vi_p903_init
    ret c
    xor a
    ret

vi_p904_invalid:
    ld a,E_INVAL
    scf
    ret

; Commit a successful :w path target. HL=path, A=preserved/requested type.
; The target is published only after the caller's write transaction succeeds.
vi_p904_commit_target:
    ld (vi_target_type),a
    ld de,vi_target
    ld b,VI_TARGET_MAX
vi_p904_copy_target:
    ld a,(hl)
    ld (de),a
    inc de
    inc hl
    or a
    jr z,vi_p904_target_done
    djnz vi_p904_copy_target
    xor a
    ld (de),a
vi_p904_target_done:
    ld a,1
    ld (vi_named),a
    xor a
    ld (vi_dirty),a
    ret

; Failed :w path never retargets and never clears dirty. A is the primary errno.
vi_p904_failed_write:
    scf
    ret

; Bare :w/:wq on an unnamed buffer: exact diagnostic plus E_NOENT.
vi_p904_require_target:
    ld a,(vi_named)
    or a
    ret nz
    ld hl,vi_no_name_msg
    ld bc,17
    ld de,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    jr c,vi_p904_require_target_error
    ld a,E_NOENT
    scf
    ret
vi_p904_require_target_error:
    scf
    ret

vi_named: db 0
vi_target_type: db OBJ_TXT
vi_target: defs VI_TARGET_MAX+1,0
vi_no_name_msg: db 'v','i',':',' ','n','o',' ','f','i','l','e',' ','n','a','m','e',10

; P9.05 exact three-mode state machine.
; The state byte is the sole authoritative editor mode.
VI_MODE_NORMAL          EQU 0
VI_MODE_INSERT          EQU 1
VI_MODE_COMMAND         EQU 2
VI_CURSOR_UNDERLINE     EQU 1
VI_ESC                  EQU $1B

vi_p905_init_mode:
    xor a
    ld (vi_editor_mode),a
    ld (vi_normal_pending),a
    ld (vi_command_len),a
    call vi_p905_clear_status
    ret c
    jp vi_p905_cursor_block

; A is one decoded target input byte. BREAK is never delivered here as VI_ESC.
vi_p905_key:
    cp VI_ESC
    jp z,vi_p905_escape
    ld b,a
    ld a,(vi_editor_mode)
    cp VI_MODE_NORMAL
    jr z,vi_p905_normal_key
    cp VI_MODE_INSERT
    jr z,vi_p905_insert_key
    cp VI_MODE_COMMAND
    jr z,vi_p905_command_key
    ld a,E_FORMAT
    scf
    ret

vi_p905_normal_key:
    ld a,b
    cp 'i'
    jr z,vi_p905_enter_insert
    cp ':'
    jr z,vi_p905_enter_command
    ; A future multi-key normal command may stage here. ESC must cancel it.
    ld a,1
    ld (vi_normal_pending),a
    xor a
    ret

vi_p905_insert_key:
    ; Text insertion is introduced by the later canonical editing steps.
    ; P9.05 proves that non-ESC input does not masquerade as editor escape.
    xor a
    ret

vi_p905_command_key:
    ld a,(vi_command_len)
    cp 31
    jr nc,vi_p905_command_full
    ld e,a
    ld d,0
    ld hl,vi_command_buf
    add hl,de
    ld a,b
    ld (hl),a
    ld a,(vi_command_len)
    inc a
    ld (vi_command_len),a
    xor a
    ret
vi_p905_command_full:
    ld a,E_NOMEM
    scf
    ret

vi_p905_enter_insert:
    call vi_p905_cursor_underline
    ret c
    call vi_p905_status_insert
    ret c
    ld a,VI_MODE_INSERT
    ld (vi_editor_mode),a
    xor a
    ld (vi_normal_pending),a
    ret

vi_p905_enter_command:
    call vi_p905_cursor_underline
    ret c
    call vi_p905_status_command
    ret c
    ld a,VI_MODE_COMMAND
    ld (vi_editor_mode),a
    xor a
    ld (vi_command_len),a
    ld (vi_normal_pending),a
    ret

; Canonical EDIT/0x1B escape. It never writes text and never executes a command.
vi_p905_escape:
    xor a
    ld (vi_normal_pending),a
    ld (vi_command_len),a
    call vi_p905_clear_status
    ret c
    call vi_p905_cursor_block
    ret c
    xor a
    ld (vi_editor_mode),a
    ret

vi_p905_cursor_block:
    ld a,VI_CURSOR_BLOCK
    jr vi_p905_cursor_set
vi_p905_cursor_underline:
    ld a,VI_CURSOR_UNDERLINE
vi_p905_cursor_set:
    ld (vi_work),a
    ld a,VI_TTY_SET_CURSOR
    ld hl,vi_work
    jp vi_ioctl

vi_p905_status_pos:
    ld hl,$1700
    ld a,SYS_CON_SETPOS
    jp SYSCALL_GATEWAY

vi_p905_status_insert:
    call vi_p905_status_pos
    ret c
    ld hl,vi_insert_msg
    ld bc,12
    ld a,SYS_CON_WRITE
    jp SYSCALL_GATEWAY

vi_p905_status_command:
    call vi_p905_status_pos
    ret c
    ld hl,vi_command_prompt
    ld bc,1
    ld a,SYS_CON_WRITE
    jp SYSCALL_GATEWAY

vi_p905_clear_status:
    call vi_p905_status_pos
    ret c
    ld hl,vi_status_blank
    ld bc,12
    ld a,SYS_CON_WRITE
    jp SYSCALL_GATEWAY

vi_editor_mode: db VI_MODE_NORMAL
vi_normal_pending: db 0
vi_command_len: db 0
vi_command_buf: defs 31,0
vi_insert_msg: db '-','-',' ','I','N','S','E','R','T',' ','-','-'
vi_command_prompt: db ':'
vi_status_blank: defs 12,' '

; P9.06 h/j/k/l/0/$ movement over logical LF-delimited lines.
vi_p906_move:
    ld (vi_motion_cmd),a
    ld hl,(vi_buffer_len)
    ld a,h
    or l
    jr nz,vi_p906_nonempty
    ld hl,0
    ld (vi_cursor_off),hl
    xor a
    ret
vi_p906_nonempty:
    call vi_p906_locate_line
    ld a,(vi_motion_cmd)
    cp 'h'
    jr z,vi_p906_left
    cp 'l'
    jr z,vi_p906_right
    cp '0'
    jr z,vi_p906_zero
    cp '
    jr z,vi_p906_dollar
    cp 'j'
    jr z,vi_p906_down
    cp 'k'
    jr z,vi_p906_up
    ld a,E_INVAL
    scf
    ret

vi_p906_left:
    ld hl,(vi_cursor_off)
    ld de,(vi_motion_start)
    or a
    sbc hl,de
    jr z,vi_p906_ok
    ld hl,(vi_cursor_off)
    dec hl
    ld (vi_cursor_off),hl
    jr vi_p906_ok

vi_p906_right:
    call vi_p906_current_end
    ld de,(vi_motion_start)
    or a
    sbc hl,de
    jr z,vi_p906_ok
    dec hl
    ld de,(vi_cursor_off)
    or a
    sbc hl,de
    jr z,vi_p906_ok
    ld hl,(vi_cursor_off)
    inc hl
    ld (vi_cursor_off),hl
    jr vi_p906_ok

vi_p906_zero:
    ld hl,(vi_motion_start)
    ld (vi_cursor_off),hl
    jr vi_p906_ok

vi_p906_dollar:
    call vi_p906_current_end
    ld de,(vi_motion_start)
    push hl
    or a
    sbc hl,de
    pop hl
    jr z,vi_p906_dollar_empty
    dec hl
    ld (vi_cursor_off),hl
    jr vi_p906_ok
vi_p906_dollar_empty:
    ld hl,(vi_motion_start)
    ld (vi_cursor_off),hl
    jr vi_p906_ok

vi_p906_down:
    ld a,(vi_motion_line)
    inc a
    ld b,a
    ld a,(vi_line_count)
    cp b
    jr z,vi_p906_ok
    jr c,vi_p906_ok
    ld a,b
    jr vi_p906_vertical

vi_p906_up:
    ld a,(vi_motion_line)
    or a
    jr z,vi_p906_ok
    dec a
vi_p906_vertical:
    ld (vi_motion_target_line),a
    ; desired column = cursor - current line start
    ld hl,(vi_cursor_off)
    ld de,(vi_motion_start)
    or a
    sbc hl,de
    ld (vi_motion_col),hl
    ld a,(vi_motion_target_line)
    call vi_p906_line_start
    ld (vi_motion_target_start),hl
    call vi_p906_line_end_for_a
    ld (vi_motion_target_end),hl
    ; content length = end - start
    ld de,(vi_motion_target_start)
    or a
    sbc hl,de
    ld a,h
    or l
    jr z,vi_p906_vertical_empty
    dec hl
    ld (vi_motion_maxcol),hl
    ld de,(vi_motion_col)
    or a
    sbc hl,de
    jr c,vi_p906_vertical_use_max
    ld hl,(vi_motion_col)
    jr vi_p906_vertical_apply
vi_p906_vertical_use_max:
    ld hl,(vi_motion_maxcol)
vi_p906_vertical_apply:
    ld de,(vi_motion_target_start)
    add hl,de
    ld (vi_cursor_off),hl
    ld a,(vi_motion_target_line)
    ld (vi_motion_line),a
    ld hl,(vi_motion_target_start)
    ld (vi_motion_start),hl
    jr vi_p906_ok
vi_p906_vertical_empty:
    ld hl,(vi_motion_target_start)
    ld (vi_cursor_off),hl
    ld a,(vi_motion_target_line)
    ld (vi_motion_line),a
    ld (vi_motion_start),hl

vi_p906_ok:
    xor a
    ret

; Find the indexed line containing vi_cursor_off.
vi_p906_locate_line:
    xor a
    ld (vi_motion_line),a
vi_p906_locate_loop:
    ld a,(vi_motion_line)
    inc a
    ld b,a
    ld a,(vi_line_count)
    cp b
    jr z,vi_p906_locate_done
    jr c,vi_p906_locate_done
    ld a,b
    call vi_p906_line_start
    ld de,(vi_cursor_off)
    ex de,hl
    or a
    sbc hl,de
    jr c,vi_p906_locate_done
    jr z,vi_p906_locate_advance
    jr vi_p906_locate_done
vi_p906_locate_advance:
    ld a,b
    ld (vi_motion_line),a
    jr vi_p906_locate_loop
vi_p906_locate_done:
    ld a,(vi_motion_line)
    call vi_p906_line_start
    ld (vi_motion_start),hl
    ret

; A=line number -> HL logical start offset.
vi_p906_line_start:
    add a,a
    ld e,a
    ld d,0
    ld hl,vi_line_index
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    ret

; A=line number -> HL content end-exclusive (LF itself is excluded).
vi_p906_line_end_for_a:
    ld b,a
    inc a
    ld c,a
    ld a,(vi_line_count)
    cp c
    jr z,vi_p906_last_end
    jr c,vi_p906_last_end
    ld a,c
    call vi_p906_line_start
    dec hl
    ret
vi_p906_last_end:
    ld hl,(vi_buffer_len)
    ret

vi_p906_current_end:
    ld a,(vi_motion_line)
    jp vi_p906_line_end_for_a

vi_cursor_off: dw 0
vi_motion_cmd: db 0
vi_motion_line: db 0
vi_motion_target_line: db 0
vi_motion_start: dw 0
vi_motion_col: dw 0
vi_motion_target_start: dw 0
vi_motion_target_end: dw 0
vi_motion_maxcol: dw 0
    ENDM
