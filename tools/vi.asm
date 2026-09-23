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
    cp 'a'
    jp z,vi_p909_enter_append
    cp 'o'
    jp z,vi_p910_open
    cp 'O'
    jp z,vi_p910_open
    cp ':'
    jr z,vi_p905_enter_command
    ; A future multi-key normal command may stage here. ESC must cancel it.
    ld a,1
    ld (vi_normal_pending),a
    xor a
    ret

vi_p905_insert_key:
    ; P9.09 inserts the literal byte at the current insertion offset.
    ld a,b
    jp vi_p909_insert_byte

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
    cp 36
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
    jp z,vi_p906_ok
    ld hl,(vi_cursor_off)
    dec hl
    ld (vi_cursor_off),hl
    jp vi_p906_ok

vi_p906_right:
    call vi_p906_current_end
    ld de,(vi_motion_start)
    or a
    sbc hl,de
    jp z,vi_p906_ok
    dec hl
    ld de,(vi_cursor_off)
    or a
    sbc hl,de
    jp z,vi_p906_ok
    ld hl,(vi_cursor_off)
    inc hl
    ld (vi_cursor_off),hl
    jp vi_p906_ok

vi_p906_zero:
    ld hl,(vi_motion_start)
    ld (vi_cursor_off),hl
    jp vi_p906_ok

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
    jp vi_p906_ok
vi_p906_dollar_empty:
    ld hl,(vi_motion_start)
    ld (vi_cursor_off),hl
    jp vi_p906_ok

vi_p906_down:
    ld a,(vi_motion_line)
    inc a
    ld b,a
    ld a,(vi_line_count)
    cp b
    jp z,vi_p906_ok
    jp c,vi_p906_ok
    ld a,b
    jr vi_p906_vertical

vi_p906_up:
    ld a,(vi_motion_line)
    or a
    jp z,vi_p906_ok
    dec a
vi_p906_vertical:
    ld (vi_motion_target_line),a
    ld hl,(vi_cursor_off)
    ld de,(vi_motion_start)
    or a
    sbc hl,de
    ld (vi_motion_col),hl
    ld a,(vi_motion_target_line)
    call vi_p906_line_start
    ld (vi_motion_target_start),hl
    ld a,(vi_motion_target_line)
    call vi_p906_line_end_for_a
    ld (vi_motion_target_end),hl
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
    jp vi_p906_ok
vi_p906_vertical_empty:
    ld hl,(vi_motion_target_start)
    ld (vi_cursor_off),hl
    ld a,(vi_motion_target_line)
    ld (vi_motion_line),a
    ld (vi_motion_start),hl

vi_p906_ok:
    xor a
    ret

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
    ld a,b
    ld (vi_motion_line),a
    jr vi_p906_locate_loop
vi_p906_locate_done:
    ld a,(vi_motion_line)
    call vi_p906_line_start
    ld (vi_motion_start),hl
    ret

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

; P9.07 w/b/e word motions.  Classification is ASCII: [A-Za-z0-9_] is one
; class, horizontal whitespace another, and punctuation a third.  Motion is
; bounded to the current logical line and never consumes LF.
vi_p907_move:
    ld (vi_word_cmd),a
    ld hl,(vi_buffer_len)
    ld a,h
    or l
    jr nz,vi_p907_nonempty
    xor a
    ret
vi_p907_nonempty:
    call vi_p906_locate_line
    ld a,(vi_word_cmd)
    cp 'w'
    jp z,vi_p907_w
    cp 'b'
    jp z,vi_p907_b
    cp 'e'
    jp z,vi_p907_e
    ld a,E_INVAL
    scf
    ret

vi_p907_w:
    call vi_p906_current_end
    ld (vi_word_end),hl
    ld hl,(vi_cursor_off)
    inc hl
    ld de,(vi_word_end)
    push hl
    or a
    sbc hl,de
    pop hl
    jp nc,vi_p907_ok
    ; Skip the remainder of the current class when currently non-space.
    ld de,(vi_cursor_off)
    ex de,hl
    call vi_p903_get_byte
    call vi_p907_class
    ld (vi_word_class),a
    cp 0
    jr z,vi_p907_w_from_space
    ld hl,(vi_cursor_off)
    inc hl
vi_p907_w_same:
    ld de,(vi_word_end)
    push hl
    or a
    sbc hl,de
    pop hl
    jp nc,vi_p907_ok
    push hl
    call vi_p903_get_byte
    call vi_p907_class
    ld b,a
    pop hl
    ld a,(vi_word_class)
    cp b
    jr nz,vi_p907_w_space_loop
    inc hl
    jr vi_p907_w_same
vi_p907_w_from_space:
    ld hl,(vi_cursor_off)
    inc hl
vi_p907_w_space_loop:
    ld de,(vi_word_end)
    push hl
    or a
    sbc hl,de
    pop hl
    jp nc,vi_p907_ok
    push hl
    call vi_p903_get_byte
    call vi_p907_class
    ld b,a
    pop hl
    ld a,b
    or a
    jp nz,vi_p907_set
    inc hl
    jr vi_p907_w_space_loop

vi_p907_b:
    ld hl,(vi_cursor_off)
    ld de,(vi_motion_start)
    or a
    sbc hl,de
    jp z,vi_p907_ok
    ld hl,(vi_cursor_off)
    dec hl
vi_p907_b_skip_space:
    push hl
    call vi_p903_get_byte
    call vi_p907_class
    ld b,a
    pop hl
    ld a,b
    or a
    jr nz,vi_p907_b_class
    ld de,(vi_motion_start)
    push hl
    or a
    sbc hl,de
    pop hl
    jr z,vi_p907_set
    dec hl
    jr vi_p907_b_skip_space
vi_p907_b_class:
    ld a,b
    ld (vi_word_class),a
vi_p907_b_same:
    ld de,(vi_motion_start)
    push hl
    or a
    sbc hl,de
    pop hl
    jr z,vi_p907_set
    dec hl
    push hl
    call vi_p903_get_byte
    call vi_p907_class
    ld b,a
    pop hl
    ld a,(vi_word_class)
    cp b
    jr z,vi_p907_b_same
    inc hl
    jr vi_p907_set

vi_p907_e:
    call vi_p906_current_end
    ld (vi_word_end),hl
    ld hl,(vi_cursor_off)
vi_p907_e_skip_space:
    ld de,(vi_word_end)
    push hl
    or a
    sbc hl,de
    pop hl
    jp nc,vi_p907_ok
    push hl
    call vi_p903_get_byte
    call vi_p907_class
    ld b,a
    pop hl
    ld a,b
    or a
    jr nz,vi_p907_e_class
    inc hl
    jr vi_p907_e_skip_space
vi_p907_e_class:
    ld a,b
    ld (vi_word_class),a
vi_p907_e_same:
    inc hl
    ld de,(vi_word_end)
    push hl
    or a
    sbc hl,de
    pop hl
    jr nc,vi_p907_e_back
    push hl
    call vi_p903_get_byte
    call vi_p907_class
    ld b,a
    pop hl
    ld a,(vi_word_class)
    cp b
    jr z,vi_p907_e_same
vi_p907_e_back:
    dec hl

vi_p907_set:
    ld (vi_cursor_off),hl
vi_p907_ok:
    xor a
    ret

; A=byte -> A=0 whitespace, 1 [A-Za-z0-9_], 2 punctuation.
vi_p907_class:
    cp ' '
    jr z,vi_p907_class_space
    cp 9
    jr z,vi_p907_class_space
    cp '_'
    jr z,vi_p907_class_word
    cp '0'
    jr c,vi_p907_class_punct
    cp '9'+1
    jr c,vi_p907_class_word
    cp 'A'
    jr c,vi_p907_class_punct
    cp 'Z'+1
    jr c,vi_p907_class_word
    cp 'a'
    jr c,vi_p907_class_punct
    cp 'z'+1
    jr c,vi_p907_class_word
vi_p907_class_punct:
    ld a,2
    ret
vi_p907_class_word:
    ld a,1
    ret
vi_p907_class_space:
    xor a
    ret

vi_word_cmd: db 0
vi_word_class: db 0
vi_word_end: dw 0

; P9.08 case-sensitive gg / G line motions (exact candidate).
; Single 'g' only arms the pending state.  A second lowercase 'g' selects
; the first logical line.  Uppercase 'G' independently selects the last.
vi_p908_key:
    ld b,a
    ld a,(vi_normal_pending)
    cp 'g'
    jr z,vi_p908_after_g
    ld a,b
    cp 'g'
    jr z,vi_p908_arm_g
    cp 'G'
    jr z,vi_p908_last
    xor a
    ld (vi_normal_pending),a
    ld a,E_NOTSUP
    scf
    ret

vi_p908_after_g:
    xor a
    ld (vi_normal_pending),a
    ld a,b
    cp 'g'
    jr z,vi_p908_first
    ld a,E_NOTSUP
    scf
    ret

vi_p908_arm_g:
    ld a,'g'
    ld (vi_normal_pending),a
    xor a
    ret

vi_p908_first:
    ld hl,0
    ld (vi_cursor_off),hl
    xor a
    ret

vi_p908_last:
    xor a
    ld (vi_normal_pending),a
    ld a,(vi_line_count)
    or a
    jr z,vi_p908_first
    dec a
    call vi_p906_line_start
    ld (vi_cursor_off),hl
    xor a
    ret

; P9.09 i/a insertion over the allocation-safe P9.03 gap primitives (exact candidate).
vi_p909_enter_append:
    ld hl,(vi_buffer_len)
    ld a,h
    or l
    jr z,vi_p909_append_ready
    ld hl,(vi_cursor_off)
    inc hl
    ld (vi_cursor_off),hl
vi_p909_append_ready:
    jp vi_p905_enter_insert

; A=byte.  On failure P9.03 guarantees the buffer is byte-identical and the
; cursor remains unchanged.  On success the insertion offset advances by one.
vi_p909_insert_byte:
    push af
    call vi_p914_stage_state
    ld hl,(vi_cursor_off)
    ld (vi_edit_pos),hl
    pop af
    call vi_p903_insert_byte
    ret c
    ld hl,(vi_edit_pos)
    ld bc,1
    call vi_p914_commit_insert
    ld hl,(vi_cursor_off)
    inc hl
    ld (vi_cursor_off),hl
    xor a
    ret

; P9.10 case-sensitive o/O open-line commands (exact candidate).
; Entry A is 'o' (below) or 'O' (above).  The LF insertion is delegated to
; P9.03 so allocation failure is atomic.
vi_p910_open:
    ld (vi_open_cmd),a
    call vi_p906_locate_line
    ld a,(vi_open_cmd)
    cp 'O'
    jr z,vi_p910_above

    ; Below: insert a line separator immediately after the current logical
    ; line.  For the final unterminated line this is exactly buffer_len.
    call vi_p906_current_end
    ld (vi_open_pos),hl
    jr vi_p910_insert

vi_p910_above:
    ld hl,(vi_motion_start)
    ld (vi_open_pos),hl

vi_p910_insert:
    call vi_p914_stage_state
    ld a,10
    ld hl,(vi_open_pos)
    call vi_p903_insert_byte
    ret c
    ld hl,(vi_open_pos)
    ld bc,1
    call vi_p914_commit_insert
    ld hl,(vi_open_pos)
    ld a,(vi_open_cmd)
    cp 'o'
    jr nz,vi_p910_cursor_ready
    inc hl
vi_p910_cursor_ready:
    ld (vi_cursor_off),hl
    jp vi_p905_enter_insert

vi_open_cmd: db 0
vi_open_pos: dw 0

; P9.11 x/dd/D deletions with exact yank-buffer effects.
VI_YANK_CAPACITY        EQU 256

; x: yank and delete the byte under the cursor. Empty/end is a safe no-op.
vi_p911_x:
    ld hl,(vi_buffer_len)
    ld de,(vi_cursor_off)
    or a
    sbc hl,de
    jp z,vi_p911_safe
    jp c,vi_p911_safe
    call vi_p914_stage_state
    xor a
    ld (vi_yank_linewise),a
    ld hl,(vi_cursor_off)
    ld bc,1
    call vi_p911_yank_range
    ret c
    ld hl,(vi_cursor_off)
    call vi_p903_delete_byte
    ret c
    ld hl,(vi_cursor_off)
    call vi_p914_commit_delete_from_yank
    call vi_p911_clamp_cursor
    xor a
    ret

; D: delete/yank cursor through end-of-line, never consuming LF.
vi_p911_D:
    ld hl,(vi_buffer_len)
    ld de,(vi_cursor_off)
    or a
    sbc hl,de
    jp z,vi_p911_safe
    jp c,vi_p911_safe
    call vi_p906_locate_line
    call vi_p906_current_end
    ld de,(vi_cursor_off)
    or a
    sbc hl,de
    ld b,h
    ld c,l
    ld a,b
    or c
    jp z,vi_p911_safe
    call vi_p914_stage_state
    xor a
    ld (vi_yank_linewise),a
    ld hl,(vi_cursor_off)
    call vi_p911_yank_range
    ret c
    ld hl,(vi_yank_len)
vi_p911_D_loop:
    ld a,h
    or l
    jr z,vi_p911_D_done
    push hl
    ld hl,(vi_cursor_off)
    call vi_p903_delete_byte
    pop hl
    ret c
    dec hl
    jr vi_p911_D_loop
vi_p911_D_done:
    ld hl,(vi_edit_prev_cursor)
    call vi_p914_commit_delete_from_yank
    call vi_p911_clamp_cursor
    xor a
    ret

; dd: delete/yank one complete logical line. If an LF terminates the line it
; is included. For the final unterminated line only content bytes are removed.
vi_p911_dd:
    call vi_p914_stage_state
    ld hl,(vi_buffer_len)
    ld a,h
    or l
    jp z,vi_p911_safe
    call vi_p906_locate_line
    ld hl,(vi_motion_start)
    ld (vi_delete_start),hl
    ld a,(vi_motion_line)
    inc a
    ld b,a
    ld a,(vi_line_count)
    cp b
    jr z,vi_p911_dd_last
    jr c,vi_p911_dd_last
    ld a,b
    call vi_p906_line_start
    jr vi_p911_dd_have_end
vi_p911_dd_last:
    ld hl,(vi_buffer_len)
vi_p911_dd_have_end:
    ld de,(vi_delete_start)
    or a
    sbc hl,de
    ld b,h
    ld c,l
    ld a,1
    ld (vi_yank_linewise),a
    ld hl,(vi_delete_start)
    call vi_p911_yank_range
    ret c
    ld hl,(vi_yank_len)
vi_p911_dd_loop:
    ld a,h
    or l
    jr z,vi_p911_dd_done
    push hl
    ld hl,(vi_delete_start)
    call vi_p903_delete_byte
    pop hl
    ret c
    dec hl
    jr vi_p911_dd_loop
vi_p911_dd_done:
    ld hl,(vi_delete_start)
    call vi_p914_commit_delete_from_yank
    ld hl,(vi_delete_start)
    ld (vi_cursor_off),hl
    call vi_p911_clamp_cursor
    xor a
    ret

vi_p911_safe:
    xor a
    ld (vi_yank_len),a
    ld (vi_yank_len+1),a
    ret

; HL=start, BC=len. Copy logical bytes into a bounded yank buffer.
vi_p911_yank_range:
    push hl
    ld hl,VI_YANK_CAPACITY
    or a
    sbc hl,bc
    pop hl
    jr c,vi_p911_nomem
    ld (vi_yank_len),bc
    ld de,vi_yank_buf
vi_p911_yank_loop:
    ld a,b
    or c
    ret z
    push bc
    push de
    push hl
    call vi_p903_get_byte
    pop hl
    pop de
    ld (de),a
    inc de
    inc hl
    pop bc
    dec bc
    jr vi_p911_yank_loop
vi_p911_nomem:
    ld a,E_NOMEM
    scf
    ret

; Keep the normal-mode cursor in-range after destructive edits.
vi_p911_clamp_cursor:
    ld hl,(vi_buffer_len)
    ld a,h
    or l
    jr nz,vi_p911_clamp_nonempty
    ld hl,0
    ld (vi_cursor_off),hl
    ret
vi_p911_clamp_nonempty:
    dec hl
    ld de,(vi_cursor_off)
    push hl
    or a
    sbc hl,de
    pop hl
    ret nc
    ld (vi_cursor_off),hl
    ret

vi_delete_start: dw 0
vi_yank_len: dw 0
vi_yank_linewise: db 0
vi_yank_buf: defs VI_YANK_CAPACITY,0

; P9.12 yy/p/P using the single P9.11 yank buffer.
vi_p912_yy:
    ld hl,(vi_buffer_len)
    ld a,h
    or l
    jr z,vi_p912_yy_empty
    call vi_p906_locate_line
    ld hl,(vi_motion_start)
    ld (vi_put_start),hl
    ld a,(vi_motion_line)
    inc a
    ld b,a
    ld a,(vi_line_count)
    cp b
    jr z,vi_p912_yy_last
    jr c,vi_p912_yy_last
    ld a,b
    call vi_p906_line_start
    jr vi_p912_yy_have_end
vi_p912_yy_last:
    ld hl,(vi_buffer_len)
vi_p912_yy_have_end:
    ld de,(vi_put_start)
    or a
    sbc hl,de
    ld b,h
    ld c,l
    ld a,1
    ld (vi_yank_linewise),a
    ld hl,(vi_put_start)
    jp vi_p911_yank_range
vi_p912_yy_empty:
    xor a
    ld (vi_yank_len),a
    ld (vi_yank_len+1),a
    ld (vi_yank_linewise),a
    ret

; A='p' or 'P'. Puts are fully preflighted before the first byte is inserted.
vi_p912_put:
    ld (vi_put_cmd),a
    call vi_p912_preflight
    ret c
    call vi_p914_stage_state
    ld hl,(vi_yank_len)
    ld a,h
    or l
    ret z
    ld a,(vi_yank_linewise)
    or a
    jr z,vi_p912_char_position
    call vi_p906_locate_line
    ld a,(vi_put_cmd)
    cp 'P'
    jr z,vi_p912_line_above
    ; linewise p starts at the next line boundary, or EOF for final line.
    ld a,(vi_motion_line)
    inc a
    ld b,a
    ld a,(vi_line_count)
    cp b
    jr z,vi_p912_line_eof
    jr c,vi_p912_line_eof
    ld a,b
    call vi_p906_line_start
    jr vi_p912_position_ready
vi_p912_line_eof:
    ld hl,(vi_buffer_len)
    jr vi_p912_position_ready
vi_p912_line_above:
    ld hl,(vi_motion_start)
    jr vi_p912_position_ready
vi_p912_char_position:
    ld hl,(vi_cursor_off)
    ld a,(vi_put_cmd)
    cp 'P'
    jr z,vi_p912_position_ready
    ld de,(vi_buffer_len)
    push hl
    or a
    sbc hl,de
    pop hl
    jr nc,vi_p912_position_ready
    inc hl
vi_p912_position_ready:
    ld (vi_put_start),hl
    ld de,vi_yank_buf
    ld bc,(vi_yank_len)
vi_p912_put_loop:
    ld a,b
    or c
    jr z,vi_p912_put_done
    ld a,(de)
    push bc
    push de
    push hl
    call vi_p903_insert_byte
    pop hl
    pop de
    pop bc
    ret c
    inc hl
    inc de
    dec bc
    jr vi_p912_put_loop
vi_p912_put_done:
    ld hl,(vi_put_start)
    ld bc,(vi_yank_len)
    call vi_p914_commit_insert
    ld hl,(vi_put_start)
    ld (vi_cursor_off),hl
    ld a,1
    ld (vi_dirty),a
    xor a
    ret

; Prove the whole insertion can succeed before mutating the gap.
vi_p912_preflight:
    ld a,(vi_fail_gap_alloc)
    or a
    jr nz,vi_p912_nomem
    ld a,(vi_fail_index_alloc)
    or a
    jr nz,vi_p912_nomem
    ld hl,(vi_gap_end)
    ld de,(vi_gap_start)
    or a
    sbc hl,de
    ld de,(vi_yank_len)
    or a
    sbc hl,de
    jr c,vi_p912_nomem
    ; A linewise yank can contribute at most one LF/line boundary.
    ld a,(vi_yank_linewise)
    or a
    ret z
    ld a,(vi_line_count)
    cp VI_LINE_MAX
    jr nc,vi_p912_nomem
    xor a
    ret
vi_p912_nomem:
    ld a,E_NOMEM
    scf
    ret

vi_put_cmd: db 0
vi_put_start: dw 0

; P9.13 r/J replacement and join.
; r is two-stage so a missing replacement byte leaves the buffer untouched.
vi_p913_r_begin:
    ld hl,(vi_buffer_len)
    ld de,(vi_cursor_off)
    or a
    sbc hl,de
    jr z,vi_p913_r_empty
    jr c,vi_p913_r_empty
    ld a,1
    ld (vi_replace_pending),a
    xor a
    ret
vi_p913_r_empty:
    xor a
    ld (vi_replace_pending),a
    ret

; A is the replacement byte.
vi_p913_r_char:
    ld b,a
    ld a,(vi_replace_pending)
    or a
    jr z,vi_p913_r_missing
    xor a
    ld (vi_replace_pending),a
    call vi_p914_stage_state
    ld hl,(vi_cursor_off)
    push bc
    call vi_p903_get_byte
    ld (vi_replace_old),a
    pop bc
    ld hl,(vi_cursor_off)
    ld a,b
    call vi_p913_set_byte
    ret c
    ld hl,(vi_cursor_off)
    ld a,(vi_replace_old)
    call vi_p914_commit_replace
    ld a,1
    ld (vi_dirty),a
    xor a
    ret
vi_p913_r_missing:
    ld a,E_INVAL
    scf
    ret

; J replaces the current line's LF separator with one ASCII space.
; No next line is a safe no-op.
vi_p913_J:
    ld hl,(vi_buffer_len)
    ld a,h
    or l
    ret z
    call vi_p906_locate_line
    ld a,(vi_motion_line)
    inc a
    ld b,a
    ld a,(vi_line_count)
    cp b
    ret z
    ret c
    call vi_p906_current_end
    ld (vi_join_pos),hl
    call vi_p914_stage_state
    ; current_end points at the LF for every non-final logical line.
    ld a,' '
    call vi_p913_set_byte
    ret c
    ; Removing the LF line boundary requires a fresh compact index.
    call vi_p903_reindex
    ret c
    ld hl,(vi_join_pos)
    ld a,10
    call vi_p914_commit_replace
    ld a,1
    ld (vi_dirty),a
    xor a
    ret

; HL logical offset, A replacement byte. Same-size update: allocation-free.
vi_p913_set_byte:
    ld (vi_replace_byte),a
    ld de,(vi_gap_start)
    push hl
    or a
    sbc hl,de
    pop hl
    jr c,vi_p913_set_physical
    push hl
    ld hl,(vi_gap_end)
    or a
    sbc hl,de
    ld b,h
    ld c,l
    pop hl
    add hl,bc
vi_p913_set_physical:
    ld de,vi_buffer
    add hl,de
    ld a,(vi_replace_byte)
    ld (hl),a
    xor a
    ret

vi_replace_pending: db 0
vi_replace_byte: db 0
vi_replace_old: db 0
vi_join_pos: dw 0

; P9.14 exact one-level undo.  This is a bounded delta record, never a full
; duplicate file image. kind 1 deletes prior insertion, kind 2 reinserts prior
; deletion bytes, kind 3 restores one replaced byte.
VI_UNDO_INSERT          EQU 1
VI_UNDO_DELETE          EQU 2
VI_UNDO_REPLACE         EQU 3

vi_p914_stage_state:
    ld a,(vi_dirty)
    ld (vi_edit_prev_dirty),a
    ld hl,(vi_cursor_off)
    ld (vi_edit_prev_cursor),hl
    ret

; HL insertion start, BC insertion length.
vi_p914_commit_insert:
    ld (vi_undo_pos),hl
    ld (vi_undo_len),bc
    ld a,(vi_edit_prev_dirty)
    ld (vi_undo_dirty),a
    ld hl,(vi_edit_prev_cursor)
    ld (vi_undo_cursor),hl
    ld a,VI_UNDO_INSERT
    ld (vi_undo_kind),a
    ret

; HL deletion start; source bytes are the single yank buffer.
vi_p914_commit_delete_from_yank:
    ld (vi_undo_pos),hl
    ld bc,(vi_yank_len)
    ld (vi_undo_len),bc
    ld a,(vi_edit_prev_dirty)
    ld (vi_undo_dirty),a
    ld hl,(vi_edit_prev_cursor)
    ld (vi_undo_cursor),hl
    ld hl,vi_yank_buf
    ld de,vi_undo_data
    ldir
    ld a,VI_UNDO_DELETE
    ld (vi_undo_kind),a
    ret

; HL replacement offset, A prior byte.
vi_p914_commit_replace:
    ld (vi_undo_pos),hl
    ld (vi_undo_data),a
    ld hl,1
    ld (vi_undo_len),hl
    ld a,(vi_edit_prev_dirty)
    ld (vi_undo_dirty),a
    ld hl,(vi_edit_prev_cursor)
    ld (vi_undo_cursor),hl
    ld a,VI_UNDO_REPLACE
    ld (vi_undo_kind),a
    ret

vi_p914_undo:
    ld a,(vi_undo_kind)
    cp VI_UNDO_INSERT
    jp z,vi_p914_undo_insert
    cp VI_UNDO_DELETE
    jp z,vi_p914_undo_delete
    cp VI_UNDO_REPLACE
    jp z,vi_p914_undo_replace
    ld a,E_NOTSUP
    scf
    ret

vi_p914_undo_insert:
    ld hl,(vi_undo_len)
vi_p914_undo_insert_loop:
    ld a,h
    or l
    jr z,vi_p914_finish
    push hl
    ld hl,(vi_undo_pos)
    call vi_p903_delete_byte
    pop hl
    ret c
    dec hl
    jr vi_p914_undo_insert_loop

vi_p914_undo_delete:
    ; Preflight the complete inverse before changing the buffer.
    ld a,(vi_fail_gap_alloc)
    or a
    jr nz,vi_p914_nomem
    ld a,(vi_fail_index_alloc)
    or a
    jr nz,vi_p914_nomem
    ld hl,(vi_gap_end)
    ld de,(vi_gap_start)
    or a
    sbc hl,de
    ld de,(vi_undo_len)
    or a
    sbc hl,de
    jr c,vi_p914_nomem
    ld hl,(vi_undo_pos)
    ld de,vi_undo_data
    ld bc,(vi_undo_len)
vi_p914_undo_delete_loop:
    ld a,b
    or c
    jr z,vi_p914_finish
    ld a,(de)
    push bc
    push de
    push hl
    call vi_p903_insert_byte
    pop hl
    pop de
    pop bc
    ret c
    inc hl
    inc de
    dec bc
    jr vi_p914_undo_delete_loop

vi_p914_undo_replace:
    ld hl,(vi_undo_pos)
    ld a,(vi_undo_data)
    call vi_p913_set_byte
    ret c
    call vi_p903_reindex

vi_p914_finish:
    ld hl,(vi_undo_cursor)
    ld (vi_cursor_off),hl
    ld a,(vi_undo_dirty)
    ld (vi_dirty),a
    xor a
    ld (vi_undo_kind),a
    ret

vi_p914_nomem:
    ld a,E_NOMEM
    scf
    ret

vi_edit_prev_dirty: db 0
vi_edit_prev_cursor: dw 0
vi_undo_len: dw 0
vi_undo_dirty: db 0
vi_undo_cursor: dw 0
vi_undo_data: defs VI_YANK_CAPACITY,0

; P9.15 case-sensitive literal /text search with n/N repeat.
VI_SEARCH_CAPACITY      EQU 31

; Normal-mode search dispatch. '?' is deliberately unsupported in version 1.
vi_p915_normal_key:
    cp '/'
    jp z,vi_p915_begin
    cp 'n'
    jp z,vi_p915_repeat_same
    cp 'N'
    jp z,vi_p915_repeat_opposite
    cp '?'
    jp z,vi_p915_unsupported
vi_p915_unsupported:
    ld a,E_NOTSUP
    scf
    ret

; Begin interactive / entry without touching the previous committed search.
vi_p915_begin:
    xor a
    ld (vi_search_edit_len),a
    ld a,1
    ld (vi_search_entry),a
    call vi_p905_cursor_underline
    ret c
    call vi_p905_status_pos
    ret c
    ld hl,vi_search_prompt
    ld bc,1
    ld a,SYS_CON_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,VI_MODE_COMMAND
    ld (vi_editor_mode),a
    xor a
    ret

; A=input byte. EDIT supplies exactly 0x1B and cancels unfinished search.
; BREAK is not mapped here and remains a separate cancellation source.
vi_p915_input:
    cp VI_ESC
    jp z,vi_p915_cancel
    cp 10
    jp z,vi_p915_commit
    cp 13
    jp z,vi_p915_commit
    ld b,a
    ld a,(vi_search_edit_len)
    cp VI_SEARCH_CAPACITY
    jp nc,vi_p915_nomem
    ld e,a
    ld d,0
    ld hl,vi_search_edit_buf
    add hl,de
    ld a,b
    ld (hl),a
    ld a,(vi_search_edit_len)
    inc a
    ld (vi_search_edit_len),a
    xor a
    ret

vi_p915_cancel:
    xor a
    ld (vi_search_entry),a
    ; p905 escape returns to normal, clears transient command-line state and
    ; status, but does not touch the committed search state or file bytes.
    jp vi_p905_escape

vi_p915_commit:
    ld a,(vi_search_edit_len)
    or a
    jp z,vi_p915_invalid
    ld (vi_search_len),a
    ld c,a
    ld b,0
    ld hl,vi_search_edit_buf
    ld de,vi_search_pattern
    ldir
    ld a,1
    ld (vi_search_dir),a
    xor a
    ld (vi_search_entry),a
    ld a,VI_MODE_NORMAL
    ld (vi_editor_mode),a
    call vi_p905_clear_status
    ret c
    call vi_p905_cursor_block
    ret c
    jp vi_p915_search_forward

vi_p915_repeat_same:
    ld a,(vi_search_len)
    or a
    jp z,vi_p915_unsupported
    ld a,(vi_search_dir)
    or a
    jp z,vi_p915_search_backward
    jp vi_p915_search_forward

vi_p915_repeat_opposite:
    ld a,(vi_search_len)
    or a
    jp z,vi_p915_unsupported
    ld a,(vi_search_dir)
    or a
    jp z,vi_p915_search_forward
    jp vi_p915_search_backward

vi_p915_search_forward:
    call vi_p915_last_start
    ret c
    ld (vi_search_last),hl
    ld hl,(vi_cursor_off)
    inc hl
    ld (vi_search_candidate),hl
vi_p915_forward_loop:
    ld hl,(vi_search_last)
    ld de,(vi_search_candidate)
    or a
    sbc hl,de
    jp c,vi_p915_notfound
    ld hl,(vi_search_candidate)
    call vi_p915_match_at
    jp nc,vi_p915_found
    ld hl,(vi_search_candidate)
    inc hl
    ld (vi_search_candidate),hl
    jr vi_p915_forward_loop

vi_p915_search_backward:
    call vi_p915_last_start
    ret c
    ld (vi_search_last),hl
    ld hl,(vi_cursor_off)
    ld a,h
    or l
    jr z,vi_p915_notfound
    dec hl
    ld (vi_search_candidate),hl
vi_p915_backward_loop:
    ; candidates beyond the last full-pattern start cannot match.
    ld hl,(vi_search_last)
    ld de,(vi_search_candidate)
    or a
    sbc hl,de
    jr c,vi_p915_backward_next
    ld hl,(vi_search_candidate)
    call vi_p915_match_at
    jp nc,vi_p915_found
vi_p915_backward_next:
    ld hl,(vi_search_candidate)
    ld a,h
    or l
    jr z,vi_p915_notfound
    dec hl
    ld (vi_search_candidate),hl
    jr vi_p915_backward_loop

; Return HL=last legal start; carry if pattern cannot fit.
vi_p915_last_start:
    ld a,(vi_search_len)
    or a
    jp z,vi_p915_unsupported
    ld e,a
    ld d,0
    ld hl,(vi_buffer_len)
    or a
    sbc hl,de
    ret nc
    ld a,E_NOENT
    scf
    ret

; HL=candidate. Carry clear only for an exact byte-for-byte match.
vi_p915_match_at:
    ld (vi_search_match_pos),hl
    xor a
    ld (vi_search_match_index),a
vi_p915_match_loop:
    ld a,(vi_search_match_index)
    ld b,a
    ld a,(vi_search_len)
    cp b
    jr z,vi_p915_match_yes
    ld e,b
    ld d,0
    ld hl,(vi_search_match_pos)
    add hl,de
    call vi_p903_get_byte
    ld c,a
    ld a,(vi_search_match_index)
    ld e,a
    ld d,0
    ld hl,vi_search_pattern
    add hl,de
    ld a,(hl)
    cp c
    jr nz,vi_p915_match_no
    ld a,(vi_search_match_index)
    inc a
    ld (vi_search_match_index),a
    jr vi_p915_match_loop
vi_p915_match_yes:
    xor a
    ret
vi_p915_match_no:
    scf
    ret

vi_p915_found:
    ld hl,(vi_search_candidate)
    ld (vi_cursor_off),hl
    xor a
    ret
vi_p915_notfound:
    ld a,E_NOENT
    scf
    ret
vi_p915_invalid:
    ld a,E_INVAL
    scf
    ret
vi_p915_nomem:
    ld a,E_NOMEM
    scf
    ret

vi_search_entry: db 0
vi_search_edit_len: db 0
vi_search_edit_buf: defs VI_SEARCH_CAPACITY,0
vi_search_len: db 0
vi_search_dir: db 1
vi_search_pattern: defs VI_SEARCH_CAPACITY,0
vi_search_candidate: dw 0
vi_search_last: dw 0
vi_search_match_pos: dw 0
vi_search_match_index: db 0
vi_search_prompt: db '/'

; P9.16 transactional :e and :r staging.  Failed loads never touch the live
; gap buffer or current target; path lookup remains exact/case-sensitive.
VI_EX_STAGE_CAPACITY    EQU VI_LOAD_CAPACITY

; HL=path. Dirty buffers refuse :e. Successful load atomically replaces buffer
; and target after complete staging/type/line validation.
vi_p916_e:
    ld (vi_ex_path),hl
    ld a,(vi_dirty)
    or a
    jr z,vi_p916_e_clean
    ld a,E_BUSY
    scf
    ret
vi_p916_e_clean:
    call vi_p916_stage_load
    ret c
    call vi_p916_validate_stage_lines
    ret c
    ld hl,vi_ex_stage
    ld de,vi_buffer
    ld bc,(vi_ex_stage_len)
    ldir
    ld hl,(vi_ex_stage_len)
    ld (vi_buffer_len),hl
    call vi_p903_init
    ret c
    ld hl,0
    ld (vi_cursor_off),hl
    xor a
    ld (vi_undo_kind),a
    ld a,(vi_ex_stage_type)
    ld hl,(vi_ex_path)
    jp vi_p904_commit_target

; HL=path. :r inserts staged bytes after the current logical line and never
; changes the current target. Full capacity/index preflight precedes mutation.
vi_p916_r:
    ld (vi_ex_path),hl
    call vi_p916_stage_load
    ret c
    call vi_p916_validate_stage_lines
    ret c
    ld hl,(vi_ex_stage_len)
    ld a,h
    or l
    ret z
    call vi_p916_r_preflight
    ret c
    call vi_p914_stage_state
    call vi_p906_locate_line
    ld a,(vi_motion_line)
    inc a
    ld b,a
    ld a,(vi_line_count)
    cp b
    jr z,vi_p916_r_eof
    jr c,vi_p916_r_eof
    ld a,b
    call vi_p906_line_start
    jr vi_p916_r_pos_ready
vi_p916_r_eof:
    ld hl,(vi_buffer_len)
vi_p916_r_pos_ready:
    ld (vi_ex_insert_pos),hl
    ld de,vi_ex_stage
    ld bc,(vi_ex_stage_len)
vi_p916_r_loop:
    ld a,b
    or c
    jr z,vi_p916_r_done
    ld a,(de)
    push bc
    push de
    push hl
    call vi_p903_insert_byte
    pop hl
    pop de
    pop bc
    ret c
    inc hl
    inc de
    dec bc
    jr vi_p916_r_loop
vi_p916_r_done:
    ld hl,(vi_ex_insert_pos)
    ld bc,(vi_ex_stage_len)
    call vi_p914_commit_insert
    ld a,1
    ld (vi_dirty),a
    xor a
    ret

vi_p916_r_preflight:
    ld a,(vi_fail_gap_alloc)
    or a
    jp nz,vi_p916_nomem
    ld a,(vi_fail_index_alloc)
    or a
    jp nz,vi_p916_nomem
    ld hl,(vi_gap_end)
    ld de,(vi_gap_start)
    or a
    sbc hl,de
    ld de,(vi_ex_stage_len)
    or a
    sbc hl,de
    jp c,vi_p916_nomem
    ld a,(vi_ex_stage_lines)
    dec a
    ld b,a
    ld a,(vi_line_count)
    add a,b
    jp c,vi_p916_nomem
    cp VI_LINE_MAX+1
    jp nc,vi_p916_nomem
    xor a
    ret

; Stage an editable object without touching live file bytes.
vi_p916_stage_load:
    ld (vi_ex_path),hl
    xor a
    ld (vi_ex_stage_len),a
    ld (vi_ex_stage_len+1),a
    ld (vi_ex_open),a
    ld (vi_ex_stat_req),hl
    ld hl,vi_ex_stat_out
    ld (vi_ex_stat_req+2),hl
    ld hl,vi_ex_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    ret c
    ld a,(vi_ex_stat_out)
    cp OBJ_TXT
    jr z,vi_p916_type_ok
    cp OBJ_C
    jr z,vi_p916_type_ok
    cp OBJ_ASM
    jr z,vi_p916_type_ok
    cp OBJ_CFG
    jr z,vi_p916_type_ok
    ld a,E_FORMAT
    scf
    ret
vi_p916_type_ok:
    ld (vi_ex_stage_type),a
    ld hl,(vi_ex_path)
    ld c,O_READ
    ld b,0
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,vi_p916_bad_handle
    ld a,l
    ld (vi_ex_handle),a
    ld a,1
    ld (vi_ex_open),a
vi_p916_read:
    ld a,(vi_ex_handle)
    ld e,a
    ld d,0
    ld hl,vi_io_chunk
    ld bc,64
    ld a,SYS_READ
    call SYSCALL_GATEWAY
    jr c,vi_p916_stream_error
    ld a,h
    or l
    jr z,vi_p916_eof
    ld (vi_chunk_len),hl
    ex de,hl
    ld hl,(vi_ex_stage_len)
    add hl,de
    ld a,h
    cp 4
    jr c,vi_p916_room
    jr nz,vi_p916_overflow
    ld a,l
    or a
    jr nz,vi_p916_overflow
vi_p916_room:
    ld (vi_ex_new_len),hl
    ld de,vi_ex_stage
    ld hl,(vi_ex_stage_len)
    add hl,de
    ex de,hl
    ld hl,vi_io_chunk
    ld bc,(vi_chunk_len)
    ldir
    ld hl,(vi_ex_new_len)
    ld (vi_ex_stage_len),hl
    jr vi_p916_read
vi_p916_overflow:
    ld a,E_NOMEM
    jr vi_p916_stream_error
vi_p916_eof:
    call vi_p916_close
    ret c
    xor a
    ret
vi_p916_stream_error:
    ld (vi_ex_errno),a
    call vi_p916_close
    ld a,(vi_ex_errno)
    scf
    ret
vi_p916_bad_handle:
    ld a,E_FORMAT
    scf
    ret

vi_p916_close:
    ld a,(vi_ex_open)
    or a
    ret z
    xor a
    ld (vi_ex_open),a
    ld a,(vi_ex_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    jp SYSCALL_GATEWAY

; Count logical lines in staging.  This guarantees p903 reindex cannot fail.
vi_p916_validate_stage_lines:
    ld a,1
    ld (vi_ex_stage_lines),a
    ld hl,0
vi_p916_line_loop:
    ld de,(vi_ex_stage_len)
    push hl
    or a
    sbc hl,de
    pop hl
    jr z,vi_p916_lines_ok
    ld de,vi_ex_stage
    add hl,de
    ld a,(hl)
    cp 10
    jr nz,vi_p916_line_next
    ld a,(vi_ex_stage_lines)
    cp VI_LINE_MAX
    jp nc,vi_p916_nomem
    inc a
    ld (vi_ex_stage_lines),a
vi_p916_line_next:
    ld de,vi_ex_stage
    or a
    sbc hl,de
    inc hl
    jr vi_p916_line_loop
vi_p916_lines_ok:
    xor a
    ret
vi_p916_nomem:
    ld a,E_NOMEM
    scf
    ret

vi_ex_path: dw 0
vi_ex_handle: db 0
vi_ex_open: db 0
vi_ex_errno: db 0
vi_ex_stage_type: db OBJ_TXT
vi_ex_stage_lines: db 1
vi_ex_stage_len: dw 0
vi_ex_new_len: dw 0
vi_ex_insert_pos: dw 0
vi_ex_stat_req: defs 4,0
vi_ex_stat_out: defs 10,0
vi_ex_stage: defs VI_EX_STAGE_CAPACITY,0

; P9.17 transactional :w path core. The destination is never opened/truncated.
; A unique /tmp/.vi<pid>.<n> (n=0..9) is created exclusively, completely
; written and closed, then atomically renamed over the destination.
vi_p917_write_path:
    ld (vi_write_dest),hl
    xor a
    ld (vi_temp_owned),a
    ld (vi_temp_open),a
    call vi_p917_select_type
    ret c
    ld a,SYS_GETPID
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jp nz,vi_p917_format
    ld a,l
    cp 10
    jp nc,vi_p917_format
    add a,'0'
    ld (vi_temp_name+8),a
    xor a
    ld (vi_temp_n),a
vi_p917_open_retry:
    ld a,(vi_temp_n)
    add a,'0'
    ld (vi_temp_name+10),a
    ld hl,vi_temp_name
    ld c,O_WRITE|O_CREATE|O_EXCL
    ld a,(vi_write_type)
    ld b,a
    ld a,SYS_OPEN
    call SYSCALL_GATEWAY
    jr nc,vi_p917_opened
    cp E_EXIST
    ret nz
    ld a,(vi_temp_n)
    cp 9
    jp z,vi_p917_exist
    inc a
    ld (vi_temp_n),a
    jr vi_p917_open_retry

vi_p917_opened:
    ld a,h
    or a
    jp nz,vi_p917_format_created
    ld a,l
    ld (vi_temp_handle),a
    ld a,1
    ld (vi_temp_owned),a
    ld (vi_temp_open),a
    call vi_p917_write_all
    jp c,vi_p917_cleanup_error
    call vi_p917_close_temp
    jp c,vi_p917_cleanup_error
    ld hl,vi_temp_name
    ld (vi_rename_req),hl
    ld hl,(vi_write_dest)
    ld (vi_rename_req+2),hl
    ld hl,vi_rename_req
    ld a,SYS_RENAME
    call SYSCALL_GATEWAY
    jp c,vi_p917_cleanup_error
    xor a
    ld (vi_temp_owned),a
    ret

vi_p917_write_all:
    ld hl,0
    ld (vi_write_pos),hl
vi_p917_write_loop:
    ld hl,(vi_write_pos)
    ld de,(vi_buffer_len)
    push hl
    or a
    sbc hl,de
    pop hl
    ret z
    call vi_p903_get_byte
    ld (vi_write_byte),a
    ld a,(vi_temp_handle)
    ld e,a
    ld d,0
    ld hl,vi_write_byte
    ld bc,1
    ld a,SYS_WRITE
    call SYSCALL_GATEWAY
    ret c
    ld a,h
    or a
    jr nz,vi_p917_io
    ld a,l
    cp 1
    jr nz,vi_p917_io
    ld hl,(vi_write_pos)
    inc hl
    ld (vi_write_pos),hl
    jr vi_p917_write_loop

vi_p917_close_temp:
    ld a,(vi_temp_open)
    or a
    ret z
    ld a,(vi_temp_handle)
    ld l,a
    ld h,0
    ld a,SYS_CLOSE
    call SYSCALL_GATEWAY
    ret c
    xor a
    ld (vi_temp_open),a
    ret

; Preserve the first transactional errno while cleaning only an exclusively
; created temp owned by this vi process. Unknown E_EXIST collisions are untouched.
vi_p917_cleanup_error:
    ld (vi_write_errno),a
    call vi_p917_close_temp
    ld a,(vi_temp_owned)
    or a
    jr z,vi_p917_return_primary
    xor a
    ld (vi_temp_owned),a
    ld hl,vi_temp_name
    ld a,SYS_REMOVE
    call SYSCALL_GATEWAY
vi_p917_return_primary:
    ld a,(vi_write_errno)
    scf
    ret

vi_p917_format_created:
    ld a,1
    ld (vi_temp_owned),a
    ld a,E_FORMAT
    jr vi_p917_cleanup_error
vi_p917_format:
    ld a,E_FORMAT
    scf
    ret
vi_p917_exist:
    ld a,E_EXIST
    scf
    ret
vi_p917_io:
    ld a,E_IO
    scf
    ret

; Existing destination type is preserved. A new destination selects C only for
; exact lower-case .c, ASM only for exact lower-case .asm, TXT otherwise.
vi_p917_select_type:
    ld hl,(vi_write_dest)
    ld (vi_write_stat_req),hl
    ld hl,vi_write_stat_out
    ld (vi_write_stat_req+2),hl
    ld hl,vi_write_stat_req
    ld a,SYS_STAT
    call SYSCALL_GATEWAY
    jr c,vi_p917_select_missing
    ld a,(vi_write_stat_out)
    cp OBJ_TXT
    jr z,vi_p917_select_existing
    cp OBJ_C
    jr z,vi_p917_select_existing
    cp OBJ_ASM
    jr z,vi_p917_select_existing
    cp OBJ_CFG
    jr z,vi_p917_select_existing
    ld a,E_FORMAT
    scf
    ret
vi_p917_select_existing:
    ld (vi_write_type),a
    xor a
    ret
vi_p917_select_missing:
    cp E_NOENT
    ret nz
    xor a
    ld (vi_suffix_1),a
    ld (vi_suffix_2),a
    ld (vi_suffix_3),a
    ld (vi_suffix_4),a
    ld hl,(vi_write_dest)
vi_p917_suffix_loop:
    ld a,(hl)
    or a
    jr z,vi_p917_suffix_done
    ld b,a
    ld a,(vi_suffix_3)
    ld (vi_suffix_4),a
    ld a,(vi_suffix_2)
    ld (vi_suffix_3),a
    ld a,(vi_suffix_1)
    ld (vi_suffix_2),a
    ld a,b
    ld (vi_suffix_1),a
    inc hl
    jr vi_p917_suffix_loop
vi_p917_suffix_done:
    ld a,(vi_suffix_2)
    cp '.'
    jr nz,vi_p917_check_asm
    ld a,(vi_suffix_1)
    cp 'c'
    jr nz,vi_p917_check_asm
    ld a,OBJ_C
    jr vi_p917_select_new
vi_p917_check_asm:
    ld a,(vi_suffix_4)
    cp '.'
    jr nz,vi_p917_new_txt
    ld a,(vi_suffix_3)
    cp 'a'
    jr nz,vi_p917_new_txt
    ld a,(vi_suffix_2)
    cp 's'
    jr nz,vi_p917_new_txt
    ld a,(vi_suffix_1)
    cp 'm'
    jr nz,vi_p917_new_txt
    ld a,OBJ_ASM
    jr vi_p917_select_new
vi_p917_new_txt:
    ld a,OBJ_TXT
vi_p917_select_new:
    ld (vi_write_type),a
    xor a
    ret

vi_write_dest: dw 0
vi_write_type: db OBJ_TXT
vi_write_errno: db 0
vi_write_pos: dw 0
vi_write_byte: db 0
vi_temp_handle: db 0
vi_temp_open: db 0
vi_temp_owned: db 0
vi_temp_n: db 0
vi_suffix_1: db 0
vi_suffix_2: db 0
vi_suffix_3: db 0
vi_suffix_4: db 0
vi_write_stat_req: defs 4,0
vi_write_stat_out: defs 10,0
vi_rename_req: defs 4,0
vi_temp_name: db '/','t','m','p','/','.','v','i','0','.','0',0

; P9.18 exact :w, :w path and :wq state transitions.
; Successful writes clear dirty. A named-target change is published only after
; vi_p917_write_path has committed the atomic rename.
vi_p918_w_current:
    call vi_p904_require_target
    ret c
    ld hl,vi_target
    call vi_p917_write_path
    ret c
    xor a
    ld (vi_dirty),a
    ret

; HL=explicit path. Retarget only after the complete transaction commits.
vi_p918_w_path:
    ld (vi_p918_path),hl
    call vi_p917_write_path
    ret c
    ld a,(vi_write_type)
    ld hl,(vi_p918_path)
    jp vi_p904_commit_target

; :wq has no implicit name for an unnamed buffer and never exits on save error.
vi_p918_wq:
    xor a
    ld (vi_should_exit),a
    call vi_p918_w_current
    ret c
    ld a,1
    ld (vi_should_exit),a
    xor a
    ret

; Entry helper used when an editor session begins.
vi_p918_session_init:
    xor a
    ld (vi_should_exit),a
    ret

vi_should_exit: db 0
vi_p918_path: dw 0
    ENDM
