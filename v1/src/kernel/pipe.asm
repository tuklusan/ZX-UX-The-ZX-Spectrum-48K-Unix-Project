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
; Four bounded 256-byte FAST_REQUIRED circular pipes. Endpoint lifetime is owned
; by shared open descriptions, not by process handles.

PIPE_BUFFER_PTR           EQU 0
PIPE_READ_POS             EQU 2
PIPE_WRITE_POS            EQU 3
PIPE_COUNT_BYTES          EQU 4
PIPE_READERS              EQU 6
PIPE_WRITERS              EQU 7
PIPE_RECORD_SIZE          EQU 8

    MACRO EMIT_PIPE_ROUTINES
zx48_pipe_init:
    xor a
    ld hl,pipe_table
    ld de,pipe_table+1
    ld bc,PIPE_COUNT*PIPE_RECORD_SIZE-1
    ld (hl),a
    ldir
    ret

; Inputs: HL -> two writable u8 process handle slots.
; Outputs: carry clear HL=0; carry set errno with complete rollback.
zx48_pipe_create:
    ld (pipe_result_ptr),hl
    call zx48_pipe_find_slot
    ret c
    ld (pipe_slot_id),a
    push ix
    ld bc,PIPE_BUFFER_SIZE
    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    pop ix
    jr c,zx48_pipe_create_fail
    ld (ix+PIPE_BUFFER_PTR),l
    ld (ix+PIPE_BUFFER_PTR+1),h
    xor a
    ld (ix+PIPE_READ_POS),a
    ld (ix+PIPE_WRITE_POS),a
    ld (ix+PIPE_COUNT_BYTES),a
    ld (ix+PIPE_COUNT_BYTES+1),a
    ld (ix+PIPE_READERS),1
    ld (ix+PIPE_WRITERS),1

    ld a,OD_KIND_PIPE_READ
    ld b,O_READ
    ld c,(pipe_slot_id)
    call zx48_od_create
    jr c,zx48_pipe_rollback_buffer
    ld (pipe_read_od),a
    ld a,OD_KIND_PIPE_WRITE
    ld b,O_WRITE
    ld c,(pipe_slot_id)
    call zx48_od_create
    jr c,zx48_pipe_rollback_read_od
    ld (pipe_write_od),a

    ld a,(current_pid)
    call zx48_process_descriptor_from_pid
    ld a,(pipe_read_od)
    ld c,HANDLE_FREE
    call zx48_handle_install
    jr c,zx48_pipe_rollback_both_od
    ld a,l
    ld (pipe_read_handle),a
    ld a,(pipe_write_od)
    ld c,HANDLE_FREE
    call zx48_handle_install
    jr c,zx48_pipe_rollback_read_handle
    ld a,l
    ld (pipe_write_handle),a

    ld hl,(pipe_result_ptr)
    ld a,(pipe_read_handle)
    ld (hl),a
    inc hl
    ld a,(pipe_write_handle)
    ld (hl),a
    ld hl,0
    xor a
    or a
    ret
zx48_pipe_rollback_read_handle:
    ld c,(pipe_read_handle)
    call zx48_close
zx48_pipe_rollback_both_od:
    ld a,(pipe_write_od)
    call zx48_pipe_clear_od
zx48_pipe_rollback_read_od:
    ld a,(pipe_read_od)
    call zx48_pipe_clear_od
zx48_pipe_rollback_buffer:
    ld l,(ix+PIPE_BUFFER_PTR)
    ld h,(ix+PIPE_BUFFER_PTR+1)
    ld bc,PIPE_BUFFER_SIZE
    call zx48_free
    xor a
    ld (ix+PIPE_BUFFER_PTR),a
    ld (ix+PIPE_BUFFER_PTR+1),a
zx48_pipe_create_fail:
    scf
    ret

zx48_pipe_clear_od:
    call zx48_od_lookup
    ret c
    push ix
    pop hl
    xor a
    ld (hl),a
    ld de,1
    add hl,de
    ex de,hl
    push ix
    pop hl
    ld bc,OD_DESC_SIZE-1
    ldir
    ret

; Outputs: carry clear A=slot, IX=record; carry set E_NOSPC.
zx48_pipe_find_slot:
    ld ix,pipe_table
    ld b,PIPE_COUNT
    ld c,0
zx48_pipe_find_loop:
    ld a,(ix+PIPE_BUFFER_PTR)
    or (ix+PIPE_BUFFER_PTR+1)
    jr z,zx48_pipe_find_ok
    ld de,PIPE_RECORD_SIZE
    add ix,de
    inc c
    djnz zx48_pipe_find_loop
    ld a,E_NOSPC
    scf
    ret
zx48_pipe_find_ok:
    ld a,c
    or a
    ret

; Inputs: A=slot.
; Outputs: IX=record or carry set E_INVAL.
zx48_pipe_lookup:
    cp PIPE_COUNT
    jr nc,zx48_pipe_lookup_fail
    ld c,a
    ld ix,pipe_table
    ld de,PIPE_RECORD_SIZE
    or a
    jr z,zx48_pipe_lookup_done
zx48_pipe_lookup_loop:
    add ix,de
    dec c
    jr nz,zx48_pipe_lookup_loop
zx48_pipe_lookup_done:
    ld a,(ix+PIPE_BUFFER_PTR)
    or (ix+PIPE_BUFFER_PTR+1)
    jr z,zx48_pipe_lookup_fail
    xor a
    or a
    ret
zx48_pipe_lookup_fail:
    ld a,E_INVAL
    scf
    ret

; Inputs: A=pipe slot, HL=destination, BC=request count.
; Outputs: carry clear HL=bytes read; empty/no writers => HL=0. Empty/live
; writers cooperatively blocks current process and retries after wake.
zx48_pipe_read:
    ld (pipe_io_ptr),hl
    ld (pipe_io_remaining),bc
    ld (pipe_slot_id),a
zx48_pipe_read_retry:
    ld a,(pipe_slot_id)
    call zx48_pipe_lookup
    ret c
    ld e,(ix+PIPE_COUNT_BYTES)
    ld d,(ix+PIPE_COUNT_BYTES+1)
    ld a,d
    or e
    jr nz,zx48_pipe_read_have_data
    ld a,(ix+PIPE_WRITERS)
    or a
    jr z,zx48_pipe_read_eof
    ld a,(current_pid)
    call zx48_process_descriptor_from_pid
    ld (ix+PROC_STATE),PROC_WAIT_PIPE_READ
    call zx48_schedule
    jr zx48_pipe_read_retry
zx48_pipe_read_have_data:
    ld bc,(pipe_io_remaining)
    ld a,b
    or c
    jr z,zx48_pipe_read_eof
    ld hl,0
zx48_pipe_read_loop:
    ld a,d
    or e
    jr z,zx48_pipe_read_done
    ld a,b
    or c
    jr z,zx48_pipe_read_done
    push hl
    ld l,(ix+PIPE_BUFFER_PTR)
    ld h,(ix+PIPE_BUFFER_PTR+1)
    ld a,(ix+PIPE_READ_POS)
    add a,l
    ld l,a
    jr nc,zx48_pipe_read_addr_ok
    inc h
zx48_pipe_read_addr_ok:
    ld a,(hl)
    ld hl,(pipe_io_ptr)
    ld (hl),a
    inc hl
    ld (pipe_io_ptr),hl
    pop hl
    inc hl
    ld a,(ix+PIPE_READ_POS)
    inc a
    ld (ix+PIPE_READ_POS),a
    dec de
    dec bc
    jr zx48_pipe_read_loop
zx48_pipe_read_done:
    ld (ix+PIPE_COUNT_BYTES),e
    ld (ix+PIPE_COUNT_BYTES+1),d
    call zx48_pipe_wake_waiters
    xor a
    or a
    ret
zx48_pipe_read_eof:
    ld hl,0
    xor a
    or a
    ret

; Inputs: A=slot, HL=source, BC=count.
; Outputs: carry clear HL=count when complete. No readers => E_PIPE. Full/live
; readers cooperatively blocks and continues from the same request.
zx48_pipe_write:
    ld (pipe_io_ptr),hl
    ld (pipe_io_remaining),bc
    ld (pipe_io_total),bc
    ld (pipe_slot_id),a
zx48_pipe_write_retry:
    ld a,(pipe_slot_id)
    call zx48_pipe_lookup
    ret c
    ld a,(ix+PIPE_READERS)
    or a
    jr z,zx48_pipe_write_broken
    ld e,(ix+PIPE_COUNT_BYTES)
    ld d,(ix+PIPE_COUNT_BYTES+1)
    ld bc,(pipe_io_remaining)
zx48_pipe_write_loop:
    ld a,b
    or c
    jr z,zx48_pipe_write_done
    ld a,d
    or a
    jr nz,zx48_pipe_write_full
    ld a,e
    or a
    jr z,zx48_pipe_write_space
    ; count low wraps at 256, represented as DE=0100 only at full.
zx48_pipe_write_space:
    push bc
    push de
    ld l,(ix+PIPE_BUFFER_PTR)
    ld h,(ix+PIPE_BUFFER_PTR+1)
    ld a,(ix+PIPE_WRITE_POS)
    add a,l
    ld l,a
    jr nc,zx48_pipe_write_addr_ok
    inc h
zx48_pipe_write_addr_ok:
    ld de,(pipe_io_ptr)
    ld a,(de)
    ld (hl),a
    inc de
    ld (pipe_io_ptr),de
    pop de
    pop bc
    ld a,(ix+PIPE_WRITE_POS)
    inc a
    ld (ix+PIPE_WRITE_POS),a
    inc de
    dec bc
    ld (pipe_io_remaining),bc
    ld a,d
    cp 1
    jr nz,zx48_pipe_write_loop
    ld a,e
    or a
    jr nz,zx48_pipe_write_loop
zx48_pipe_write_full:
    ld (ix+PIPE_COUNT_BYTES),e
    ld (ix+PIPE_COUNT_BYTES+1),d
    call zx48_pipe_wake_waiters
    ld a,b
    or c
    jr z,zx48_pipe_write_done
    ld a,(current_pid)
    call zx48_process_descriptor_from_pid
    ld (ix+PROC_STATE),PROC_WAIT_PIPE_WRITE
    call zx48_schedule
    jr zx48_pipe_write_retry
zx48_pipe_write_done:
    ld (ix+PIPE_COUNT_BYTES),e
    ld (ix+PIPE_COUNT_BYTES+1),d
    call zx48_pipe_wake_waiters
    ld hl,(pipe_io_total)
    xor a
    or a
    ret
zx48_pipe_write_broken:
    ld a,E_PIPE
    scf
    ret

; Wake all pipe readers/writers; bounded table makes the coarse wake policy
; deterministic and deadlock-free. Each task revalidates endpoint state on resume.
zx48_pipe_wake_waiters:
    push ix
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_USER_PID
zx48_pipe_wake_loop:
    ld a,(ix+PROC_STATE)
    cp PROC_WAIT_PIPE_READ
    jr z,zx48_pipe_wake_one
    cp PROC_WAIT_PIPE_WRITE
    jr nz,zx48_pipe_wake_next
zx48_pipe_wake_one:
    ld (ix+PROC_STATE),PROC_READY
zx48_pipe_wake_next:
    ld de,PROC_DESC_SIZE
    add ix,de
    djnz zx48_pipe_wake_loop
    pop ix
    ret

pipe_result_ptr:
    dw 0
pipe_io_ptr:
    dw 0
pipe_io_remaining:
    dw 0
pipe_io_total:
    dw 0
pipe_slot_id:
    db 0
pipe_read_od:
    db 0
pipe_write_od:
    db 0
pipe_read_handle:
    db 0
pipe_write_handle:
    db 0
pipe_table:
    defs PIPE_COUNT*PIPE_RECORD_SIZE,0
    ENDM
