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
; Four bounded pipes with one shared read description and one shared write
; description per pipe. Duplicate/inherited handles add OD references only.

PIPE_PTR_O                 EQU 0
PIPE_RPOS_O                EQU 2
PIPE_WPOS_O                EQU 3
PIPE_COUNT_O               EQU 4
PIPE_CAPACITY_O            EQU 6
PIPE_READERS_O             EQU 8
PIPE_WRITERS_O             EQU 9
PIPE_RECORD_SIZE           EQU 10
PIPE_FALLBACK_SIZE         EQU 128

    MACRO EMIT_PIPE_ROUTINES
zx48_pipe_init:
    xor a
    ld hl,pipe_table
    ld de,pipe_table+1
    ld bc,PIPE_COUNT*PIPE_RECORD_SIZE-1
    ld (hl),a
    ldir
    ret

; A=slot -> IX record.
zx48_pipe_ptr:
    cp PIPE_COUNT
    jp nc,zx48_pipe_noent
    ld ix,pipe_table
    or a
    ret z
    ld b,a
    ld de,PIPE_RECORD_SIZE
zx48_pipe_ptr_loop:
    add ix,de
    djnz zx48_pipe_ptr_loop
    xor a
    ret

; Preflight two free process handles, two free OD records, and one pipe slot.
; Returns C=pipe slot.
zx48_pipe_preflight:
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld b,MAX_HANDLES_PER_PROCESS
    ld c,0
zx48_pipe_free_handle_scan:
    ld a,(hl)
    cp HANDLE_FREE
    jp nz,zx48_pipe_free_handle_next
    inc c
zx48_pipe_free_handle_next:
    inc hl
    djnz zx48_pipe_free_handle_scan
    ld a,c
    cp 2
    jp c,zx48_pipe_nospc

    ld ix,open_description_table
    ld b,OPEN_DESCRIPTION_COUNT
    ld c,0
zx48_pipe_free_od_scan:
    ld a,(ix+OD_KIND_O)
    or a
    jp nz,zx48_pipe_free_od_next
    inc c
zx48_pipe_free_od_next:
    ld de,OD_COMPACT_SIZE
    add ix,de
    djnz zx48_pipe_free_od_scan
    ld a,c
    cp 2
    jp c,zx48_pipe_nospc

    ld ix,pipe_table
    ld b,PIPE_COUNT
    ld c,0
zx48_pipe_slot_scan:
    ld a,(ix+PIPE_READERS_O)
    or (ix+PIPE_WRITERS_O)
    jp nz,zx48_pipe_slot_next
    ld a,(ix+PIPE_PTR_O)
    or (ix+PIPE_PTR_O+1)
    jp z,zx48_pipe_preflight_ok
zx48_pipe_slot_next:
    ld de,PIPE_RECORD_SIZE
    add ix,de
    inc c
    djnz zx48_pipe_slot_scan
zx48_pipe_nospc:
    ld a,E_NOSPC
    scf
    ret
zx48_pipe_preflight_ok:
    xor a
    ret

; HL points to two result bytes. Caller validated writable range.
zx48_pipe_create:
    ld (pipe_result_ptr),hl
    call zx48_pipe_preflight
    ret c
    ld a,c
    ld (pipe_active_slot),a
    ld bc,PIPE_BUFFER_SIZE
    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    jp nc,zx48_pipe_allocated
    ld bc,PIPE_FALLBACK_SIZE
    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    ret c
zx48_pipe_allocated:
    ld (pipe_buffer_ptr),hl
    ld (pipe_capacity_temp),bc
    ld a,(pipe_active_slot)
    call zx48_pipe_ptr
    ld hl,(pipe_buffer_ptr)
    ld (ix+PIPE_PTR_O),l
    ld (ix+PIPE_PTR_O+1),h
    xor a
    ld (ix+PIPE_RPOS_O),a
    ld (ix+PIPE_WPOS_O),a
    ld (ix+PIPE_COUNT_O),a
    ld (ix+PIPE_COUNT_O+1),a
    ld hl,(pipe_capacity_temp)
    ld (ix+PIPE_CAPACITY_O),l
    ld (ix+PIPE_CAPACITY_O+1),h
    ld a,1
    ld (ix+PIPE_READERS_O),a
    ld (ix+PIPE_WRITERS_O),a

    ld b,OD_KIND_PIPE_READ
    ld c,O_READ
    ld a,(pipe_active_slot)
    ld d,a
    call zx48_od_create
    jp c,zx48_pipe_rollback_buffer
    ld (pipe_read_od),a

    ld b,OD_KIND_PIPE_WRITE
    ld c,O_WRITE
    ld a,(pipe_active_slot)
    ld d,a
    call zx48_od_create
    jp c,zx48_pipe_rollback_read_od
    ld (pipe_write_od),a

    ld a,(pipe_read_od)
    ld c,a
    ld a,HANDLE_FREE
    call zx48_handle_install
    jp c,zx48_pipe_rollback_write_od
    ld (pipe_read_handle),a

    ld a,(pipe_write_od)
    ld c,a
    ld a,HANDLE_FREE
    call zx48_handle_install
    jp c,zx48_pipe_rollback_read_handle
    ld (pipe_write_handle),a

    ld hl,(pipe_result_ptr)
    ld a,(pipe_read_handle)
    ld (hl),a
    inc hl
    ld a,(pipe_write_handle)
    ld (hl),a
    ld hl,0
    xor a
    ret

zx48_pipe_rollback_read_handle:
    ld a,(pipe_read_handle)
    call zx48_handle_close
    ld a,(pipe_write_od)
    call zx48_od_release
    jp zx48_pipe_rollback_buffer
zx48_pipe_rollback_write_od:
    ld a,(pipe_write_od)
    call zx48_od_release
zx48_pipe_rollback_read_od:
    ld a,(pipe_read_od)
    call zx48_od_release
zx48_pipe_rollback_buffer:
    ld a,(pipe_active_slot)
    call zx48_pipe_ptr
    ld l,(ix+PIPE_PTR_O)
    ld h,(ix+PIPE_PTR_O+1)
    ld c,(ix+PIPE_CAPACITY_O)
    ld b,(ix+PIPE_CAPACITY_O+1)
    ld a,h
    or l
    jp z,zx48_pipe_rollback_clear
    call zx48_free
zx48_pipe_rollback_clear:
    xor a
    ld (ix+PIPE_PTR_O),a
    ld (ix+PIPE_PTR_O+1),a
    ld (ix+PIPE_READERS_O),a
    ld (ix+PIPE_WRITERS_O),a
    ld a,E_NOSPC
    scf
    ret

; A=pipe slot, HL=destination, BC=request. Returns HL=bytes read.
zx48_pipe_read:
    ld (pipe_active_slot),a
    ld (pipe_io_ptr),hl
    ld (pipe_io_request),bc
    ld hl,0
    ld (pipe_io_done),hl
    ld a,b
    or c
    jp z,zx48_pipe_io_success
zx48_pipe_read_retry:
    ld a,(pipe_active_slot)
    call zx48_pipe_ptr
    ret c
    ld a,(ix+PIPE_COUNT_O)
    or (ix+PIPE_COUNT_O+1)
    jp nz,zx48_pipe_read_copy
    ld a,(ix+PIPE_WRITERS_O)
    or a
    jp z,zx48_pipe_io_success
    ld a,(pipe_active_slot)
    ld c,a
    call zx48_pipe_block_read
    ret c
    jp zx48_pipe_read_retry
zx48_pipe_read_copy:
    ld hl,(pipe_io_request)
    ld a,h
    or l
    jp z,zx48_pipe_read_done
zx48_pipe_read_copy_loop:
    ld a,(ix+PIPE_COUNT_O)
    or (ix+PIPE_COUNT_O+1)
    jp z,zx48_pipe_read_done

    ld l,(ix+PIPE_PTR_O)
    ld h,(ix+PIPE_PTR_O+1)
    ld e,(ix+PIPE_RPOS_O)
    ld d,0
    add hl,de
    ld a,(hl)
    ld de,(pipe_io_ptr)
    ld (de),a
    inc de
    ld (pipe_io_ptr),de

    ld a,(ix+PIPE_RPOS_O)
    inc a
    ld c,a
    ld a,(ix+PIPE_CAPACITY_O+1)
    or a
    ld a,c
    jp nz,zx48_pipe_read_rpos_ok
    and $7f
zx48_pipe_read_rpos_ok:
    ld (ix+PIPE_RPOS_O),a

    ld l,(ix+PIPE_COUNT_O)
    ld h,(ix+PIPE_COUNT_O+1)
    dec hl
    ld (ix+PIPE_COUNT_O),l
    ld (ix+PIPE_COUNT_O+1),h

    ld hl,(pipe_io_request)
    dec hl
    ld (pipe_io_request),hl
    ld hl,(pipe_io_done)
    inc hl
    ld (pipe_io_done),hl
    ld hl,(pipe_io_request)
    ld a,h
    or l
    jp z,zx48_pipe_read_done
    jp zx48_pipe_read_copy_loop
zx48_pipe_read_done:
    ld a,(pipe_active_slot)
    ld c,a
    call zx48_pipe_wake_writers
zx48_pipe_io_success:
    ld hl,(pipe_io_done)
    xor a
    ret

; A=pipe slot, HL=source, BC=request. Returns HL=bytes written.
zx48_pipe_write:
    ld (pipe_active_slot),a
    ld (pipe_io_ptr),hl
    ld (pipe_io_request),bc
    ld hl,0
    ld (pipe_io_done),hl
    ld a,b
    or c
    jp z,zx48_pipe_io_success
zx48_pipe_write_retry:
    ld a,(pipe_active_slot)
    call zx48_pipe_ptr
    ret c
    ld a,(ix+PIPE_READERS_O)
    or a
    jp z,zx48_pipe_broken
    ld l,(ix+PIPE_COUNT_O)
    ld h,(ix+PIPE_COUNT_O+1)
    ld e,(ix+PIPE_CAPACITY_O)
    ld d,(ix+PIPE_CAPACITY_O+1)
    or a
    sbc hl,de
    jp nz,zx48_pipe_write_copy
    ld hl,(pipe_io_done)
    ld a,h
    or l
    jp nz,zx48_pipe_io_success
    ld a,(pipe_active_slot)
    ld c,a
    call zx48_pipe_block_write
    ret c
    jp zx48_pipe_write_retry
zx48_pipe_write_copy:
    ld hl,(pipe_io_request)
    ld a,h
    or l
    jp z,zx48_pipe_write_done
zx48_pipe_write_copy_loop:
    ld l,(ix+PIPE_COUNT_O)
    ld h,(ix+PIPE_COUNT_O+1)
    ld e,(ix+PIPE_CAPACITY_O)
    ld d,(ix+PIPE_CAPACITY_O+1)
    or a
    sbc hl,de
    jp z,zx48_pipe_write_done

    ld hl,(pipe_io_ptr)
    ld a,(hl)
    inc hl
    ld (pipe_io_ptr),hl
    ld l,(ix+PIPE_PTR_O)
    ld h,(ix+PIPE_PTR_O+1)
    ld e,(ix+PIPE_WPOS_O)
    ld d,0
    add hl,de
    ld (hl),a

    ld a,(ix+PIPE_WPOS_O)
    inc a
    ld c,a
    ld a,(ix+PIPE_CAPACITY_O+1)
    or a
    ld a,c
    jp nz,zx48_pipe_write_wpos_ok
    and $7f
zx48_pipe_write_wpos_ok:
    ld (ix+PIPE_WPOS_O),a

    ld l,(ix+PIPE_COUNT_O)
    ld h,(ix+PIPE_COUNT_O+1)
    inc hl
    ld (ix+PIPE_COUNT_O),l
    ld (ix+PIPE_COUNT_O+1),h

    ld hl,(pipe_io_request)
    dec hl
    ld (pipe_io_request),hl
    ld hl,(pipe_io_done)
    inc hl
    ld (pipe_io_done),hl
    ld hl,(pipe_io_request)
    ld a,h
    or l
    jp z,zx48_pipe_write_done
    jp zx48_pipe_write_copy_loop
zx48_pipe_write_done:
    ld a,(pipe_active_slot)
    ld c,a
    call zx48_pipe_wake_readers
    jp zx48_pipe_io_success

zx48_pipe_broken:
    ld a,E_PIPE
    scf
    ret

; C=pipe slot. Mark current process blocked, then resume at this kernel boundary.
zx48_pipe_block_read:
    ld a,PROC_WAIT_PIPE_READ
    jp zx48_pipe_block
zx48_pipe_block_write:
    ld a,PROC_WAIT_PIPE_WRITE
zx48_pipe_block:
    ld (pipe_wait_state),a
    ld a,(current_pid)
    or a
    jp z,zx48_pipe_noent
    ld ix,process_table
    ld (ix+PROC_STATE),PROC_READY
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    ld a,(pipe_active_slot)
    inc a
    ld (ix+PROC_WAIT_OBJECT),a
    ld a,(pipe_wait_state)
    ld (ix+PROC_STATE),a
    call zx48_schedule
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    xor a
    ld (ix+PROC_WAIT_OBJECT),a
    ld a,(ix+PROC_FLAGS)
    and PROC_FLAG_CANCEL
    jp nz,zx48_pipe_interrupted
    ld a,(pipe_active_slot)
    call zx48_pipe_try_free
    xor a
    ret
zx48_pipe_interrupted:
    ld a,(pipe_active_slot)
    call zx48_pipe_try_free
    ld a,E_INTR
    scf
    ret

; C=slot. Wake only waiters attached to this pipe and matching direction.
zx48_pipe_wake_readers:
    ld a,PROC_WAIT_PIPE_READ
    jp zx48_pipe_wake
zx48_pipe_wake_writers:
    ld a,PROC_WAIT_PIPE_WRITE
zx48_pipe_wake:
    ld (pipe_wait_state),a
    inc c
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_PROCESSES-1
zx48_pipe_wake_loop:
    ld a,(ix+PROC_WAIT_OBJECT)
    cp c
    jp nz,zx48_pipe_wake_next
    ld a,(ix+PROC_STATE)
    ld d,a
    ld a,(pipe_wait_state)
    cp d
    jp nz,zx48_pipe_wake_next
    ld (ix+PROC_STATE),PROC_READY
zx48_pipe_wake_next:
    ld de,PROC_DESC_SIZE
    add ix,de
    djnz zx48_pipe_wake_loop
    ret

; A=kind,C=pipe slot. Called only on final OD reference release.
zx48_pipe_endpoint_closed:
    ld (pipe_endpoint_kind),a
    ld a,c
    ld (pipe_active_slot),a
    call zx48_pipe_ptr
    ret c
    ld a,(pipe_endpoint_kind)
    cp OD_KIND_PIPE_READ
    jp z,zx48_pipe_close_reader
    cp OD_KIND_PIPE_WRITE
    jp nz,zx48_pipe_noent
    xor a
    ld (ix+PIPE_WRITERS_O),a
    ld a,(pipe_active_slot)
    ld c,a
    call zx48_pipe_wake_readers
    jp zx48_pipe_close_try
zx48_pipe_close_reader:
    xor a
    ld (ix+PIPE_READERS_O),a
    ld a,(pipe_active_slot)
    ld c,a
    call zx48_pipe_wake_writers
zx48_pipe_close_try:
    ld a,(pipe_active_slot)
    call zx48_pipe_try_free
    xor a
    ret

; A=slot. Free only after both logical ends are closed and no waiter references slot.
zx48_pipe_try_free:
    ld (pipe_active_slot),a
    call zx48_pipe_ptr
    ret c
    ld a,(ix+PIPE_READERS_O)
    or (ix+PIPE_WRITERS_O)
    ret nz
    ld a,(pipe_active_slot)
    inc a
    ld c,a
    push ix
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_PROCESSES-1
zx48_pipe_waiter_scan:
    ld a,(ix+PROC_WAIT_OBJECT)
    cp c
    jp z,zx48_pipe_waiter_exists
    ld de,PROC_DESC_SIZE
    add ix,de
    djnz zx48_pipe_waiter_scan
    pop ix
    ld l,(ix+PIPE_PTR_O)
    ld h,(ix+PIPE_PTR_O+1)
    ld c,(ix+PIPE_CAPACITY_O)
    ld b,(ix+PIPE_CAPACITY_O+1)
    ld a,h
    or l
    call nz,zx48_free
    xor a
    ld (ix+PIPE_PTR_O),a
    ld (ix+PIPE_PTR_O+1),a
    ld (ix+PIPE_RPOS_O),a
    ld (ix+PIPE_WPOS_O),a
    ld (ix+PIPE_COUNT_O),a
    ld (ix+PIPE_COUNT_O+1),a
    ld (ix+PIPE_CAPACITY_O),a
    ld (ix+PIPE_CAPACITY_O+1),a
    ret
zx48_pipe_waiter_exists:
    pop ix
    ret

zx48_pipe_noent:
    ld a,E_NOENT
    scf
    ret

pipe_result_ptr: dw 0
pipe_buffer_ptr: dw 0
pipe_capacity_temp: dw 0
pipe_io_ptr: dw 0
pipe_io_request: dw 0
pipe_io_done: dw 0
pipe_active_slot: db 0
pipe_read_od: db 0
pipe_write_od: db 0
pipe_read_handle: db 0
pipe_write_handle: db 0
pipe_wait_state: db 0
pipe_endpoint_kind: db 0
pipe_table: defs PIPE_COUNT*PIPE_RECORD_SIZE,0
    ENDM
