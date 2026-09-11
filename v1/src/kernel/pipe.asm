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
; Four 256-byte FAST_REQUIRED circular pipes. A pipe exists while at least one
; endpoint description exists; dup/inheritance share endpoint descriptions.

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

zx48_pipe_find_slot:
    ld ix,pipe_table
    ld c,0
    ld b,PIPE_COUNT
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

zx48_pipe_lookup:
    cp PIPE_COUNT
    jr nc,zx48_pipe_bad
    ld c,a
    ld ix,pipe_table
    or a
    jr z,zx48_pipe_lookup_check
    ld b,a
    ld de,PIPE_RECORD_SIZE
zx48_pipe_lookup_loop:
    add ix,de
    djnz zx48_pipe_lookup_loop
zx48_pipe_lookup_check:
    ld a,(ix+PIPE_BUFFER_PTR)
    or (ix+PIPE_BUFFER_PTR+1)
    jr z,zx48_pipe_bad
    xor a
    or a
    ret
zx48_pipe_bad:
    ld a,E_INVAL
    scf
    ret

; HL -> two writable handle bytes.
zx48_pipe_create:
    ld (pipe_result_ptr),hl
    call zx48_pipe_find_slot
    ret c
    ld (pipe_slot),a
    push ix
    ld bc,PIPE_BUFFER_SIZE
    ld a,ALLOC_FAST_REQUIRED
    call zx48_alloc
    pop ix
    ret c
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
    ld c,(ix+PIPE_READERS)       ; overwritten below with identity
    ld a,(pipe_slot)
    ld c,a
    ld a,OD_KIND_PIPE_READ
    call zx48_od_create
    jp c,zx48_pipe_create_rollback_buffer
    ld (pipe_read_od),a
    ld a,(pipe_slot)
    ld c,a
    ld b,O_WRITE
    ld a,OD_KIND_PIPE_WRITE
    call zx48_od_create
    jp c,zx48_pipe_create_rollback_read
    ld (pipe_write_od),a
    ld a,(current_pid)
    call zx48_process_lookup
    jp c,zx48_pipe_create_rollback_both
    ld a,(pipe_read_od)
    ld c,HANDLE_FREE
    call zx48_handle_install
    jp c,zx48_pipe_create_rollback_both
    ld a,l
    ld (pipe_read_handle),a
    ld a,(pipe_write_od)
    ld c,HANDLE_FREE
    call zx48_handle_install
    jp c,zx48_pipe_create_rollback_handle
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
zx48_pipe_create_rollback_handle:
    ld c,(pipe_read_handle)
    call zx48_close
zx48_pipe_create_rollback_both:
    ld a,(pipe_write_od)
    call zx48_pipe_clear_od
zx48_pipe_create_rollback_read:
    ld a,(pipe_read_od)
    call zx48_pipe_clear_od
zx48_pipe_create_rollback_buffer:
    ld a,(pipe_slot)
    call zx48_pipe_lookup
    ret c
    ld l,(ix+PIPE_BUFFER_PTR)
    ld h,(ix+PIPE_BUFFER_PTR+1)
    ld bc,PIPE_BUFFER_SIZE
    call zx48_free
    xor a
    ld (ix+PIPE_BUFFER_PTR),a
    ld (ix+PIPE_BUFFER_PTR+1),a
    scf
    ret
zx48_pipe_clear_od:
    call zx48_od_lookup
    ret c
    xor a
    ld (ix+OD_KIND),a
    ret

; A=slot, HL=dst, BC=count. Empty+writers blocks cooperatively.
zx48_pipe_read:
    ld (pipe_ptr),hl
    ld (pipe_left),bc
    ld (pipe_slot),a
zx48_pipe_read_retry:
    ld a,(pipe_slot)
    call zx48_pipe_lookup
    ret c
    ld e,(ix+PIPE_COUNT_BYTES)
    ld d,(ix+PIPE_COUNT_BYTES+1)
    ld a,d
    or e
    jr nz,zx48_pipe_read_data
    ld a,(ix+PIPE_WRITERS)
    or a
    jr z,zx48_pipe_zero
    ld a,(current_pid)
    call zx48_process_lookup
    ld (ix+PROC_STATE),PROC_WAIT_PIPE_READ
    call zx48_schedule
    jr zx48_pipe_read_retry
zx48_pipe_read_data:
    ld bc,(pipe_left)
    ld hl,0
zx48_pipe_read_loop:
    ld a,b
    or c
    jr z,zx48_pipe_read_done
    ld a,d
    or e
    jr z,zx48_pipe_read_done
    push hl
    push de
    ld l,(ix+PIPE_BUFFER_PTR)
    ld h,(ix+PIPE_BUFFER_PTR+1)
    ld a,(ix+PIPE_READ_POS)
    add a,l
    ld l,a
    jr nc,zx48_pipe_read_addr
    inc h
zx48_pipe_read_addr:
    ld a,(hl)
    ld de,(pipe_ptr)
    ld (de),a
    inc de
    ld (pipe_ptr),de
    ld a,(ix+PIPE_READ_POS)
    inc a
    ld (ix+PIPE_READ_POS),a
    pop de
    pop hl
    inc hl
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
zx48_pipe_zero:
    ld hl,0
    xor a
    or a
    ret

; A=slot, HL=src, BC=count. Completes full request or blocks; no readers E_PIPE.
zx48_pipe_write:
    ld (pipe_ptr),hl
    ld (pipe_left),bc
    ld (pipe_total),bc
    ld (pipe_slot),a
zx48_pipe_write_retry:
    ld a,(pipe_slot)
    call zx48_pipe_lookup
    ret c
    ld a,(ix+PIPE_READERS)
    or a
    jr z,zx48_pipe_broken
    ld e,(ix+PIPE_COUNT_BYTES)
    ld d,(ix+PIPE_COUNT_BYTES+1)
    ld bc,(pipe_left)
zx48_pipe_write_loop:
    ld a,b
    or c
    jr z,zx48_pipe_write_done
    ld a,d
    cp 1
    jr nz,zx48_pipe_write_space
    ld a,e
    or a
    jr z,zx48_pipe_write_block
zx48_pipe_write_space:
    push bc
    push de
    ld l,(ix+PIPE_BUFFER_PTR)
    ld h,(ix+PIPE_BUFFER_PTR+1)
    ld a,(ix+PIPE_WRITE_POS)
    add a,l
    ld l,a
    jr nc,zx48_pipe_write_addr
    inc h
zx48_pipe_write_addr:
    ld de,(pipe_ptr)
    ld a,(de)
    ld (hl),a
    inc de
    ld (pipe_ptr),de
    ld a,(ix+PIPE_WRITE_POS)
    inc a
    ld (ix+PIPE_WRITE_POS),a
    pop de
    pop bc
    inc de
    dec bc
    ld (pipe_left),bc
    jr zx48_pipe_write_loop
zx48_pipe_write_block:
    ld (ix+PIPE_COUNT_BYTES),e
    ld (ix+PIPE_COUNT_BYTES+1),d
    call zx48_pipe_wake_waiters
    ld a,(current_pid)
    call zx48_process_lookup
    ld (ix+PROC_STATE),PROC_WAIT_PIPE_WRITE
    call zx48_schedule
    jr zx48_pipe_write_retry
zx48_pipe_write_done:
    ld (ix+PIPE_COUNT_BYTES),e
    ld (ix+PIPE_COUNT_BYTES+1),d
    call zx48_pipe_wake_waiters
    ld hl,(pipe_total)
    xor a
    or a
    ret
zx48_pipe_broken:
    ld a,E_PIPE
    scf
    ret

zx48_pipe_wake_waiters:
    push ix
    ld ix,process_table+PROC_DESC_SIZE
    ld b,MAX_PROCESSES-1
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

; IX=open description about to lose final reference.
zx48_pipe_reader_final_close:
    ld a,(ix+OD_IDENTITY)
    call zx48_pipe_lookup
    ret c
    ld a,(ix+PIPE_READERS)
    or a
    jr z,zx48_pipe_close_check
    dec a
    ld (ix+PIPE_READERS),a
    jr zx48_pipe_close_check
zx48_pipe_writer_final_close:
    ld a,(ix+OD_IDENTITY)
    call zx48_pipe_lookup
    ret c
    ld a,(ix+PIPE_WRITERS)
    or a
    jr z,zx48_pipe_close_check
    dec a
    ld (ix+PIPE_WRITERS),a
zx48_pipe_close_check:
    call zx48_pipe_wake_waiters
    ld a,(ix+PIPE_READERS)
    or (ix+PIPE_WRITERS)
    ret nz
    ld l,(ix+PIPE_BUFFER_PTR)
    ld h,(ix+PIPE_BUFFER_PTR+1)
    ld bc,PIPE_BUFFER_SIZE
    push ix
    call zx48_free
    pop ix
    xor a
    ld (ix+PIPE_BUFFER_PTR),a
    ld (ix+PIPE_BUFFER_PTR+1),a
    ret

pipe_result_ptr: dw 0
pipe_ptr: dw 0
pipe_left: dw 0
pipe_total: dw 0
pipe_slot: db 0
pipe_read_od: db 0
pipe_write_od: db 0
pipe_read_handle: db 0
pipe_write_handle: db 0
pipe_table: defs PIPE_COUNT*PIPE_RECORD_SIZE,0
    ENDM
