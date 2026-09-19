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
; Shared version-1 open descriptions. Eight-byte records hold kind/access,
; reference count, identity, shared logical offset and packed-reader state.

OD_KIND_O                  EQU 0
OD_ACCESS_O                EQU 1
OD_REFS_O                  EQU 2
OD_ID_O                    EQU 3
OD_OFFSET_O                EQU 4
OD_AUX_O                   EQU 6
OD_COMPACT_SIZE            EQU OD_RECORD_SIZE
PACKED_READER_STATE_SIZE  EQU 272

; Fixed fast-data area: runtime state does not consume the ordinary code/data pool.
HANDLE_FAST_BASE           EQU FAST_RESERVE_START
handle_requested           EQU HANDLE_FAST_BASE+0
handle_od                  EQU HANDLE_FAST_BASE+1
handle_dup_source          EQU HANDLE_FAST_BASE+2
handle_dup_destination     EQU HANDLE_FAST_BASE+3
open_description_table     EQU HANDLE_FAST_BASE+4
HANDLE_FAST_END            EQU open_description_table+OPEN_DESCRIPTION_COUNT*OD_COMPACT_SIZE

    ASSERT OPEN_DESCRIPTION_COUNT = 24
    ASSERT MAX_HANDLES_PER_PROCESS = 8
    ASSERT OD_COMPACT_SIZE <= OD_DESC_SIZE
    ASSERT OPEN_DESCRIPTION_COUNT*OD_COMPACT_SIZE <= OPEN_DESCRIPTION_BUDGET
    ASSERT HANDLE_FAST_END <= FAST_RESERVE_END+1

    MACRO EMIT_HANDLE_ROUTINES
zx48_handles_init:
    xor a
    ld hl,open_description_table
    ld de,open_description_table+1
    ld bc,OPEN_DESCRIPTION_COUNT*OD_COMPACT_SIZE-1
    ld (hl),a
    ldir
    ret

; A=index -> IX record. A is preserved on success.
zx48_od_ptr:
    cp OPEN_DESCRIPTION_COUNT
    jp nc,zx48_handle_noent
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,open_description_table
    add hl,de
    push hl
    pop ix
    or a
    ret

; B=kind,C=access,D=identity -> A=index, IX record, refs=1.
zx48_od_create:
    push bc
    push de
    ld ix,open_description_table
    ld c,0
    ld b,OPEN_DESCRIPTION_COUNT
zx48_od_create_scan:
    ld a,(ix+OD_KIND_O)
    or a
    jr z,zx48_od_create_found
    ld de,OD_COMPACT_SIZE
    add ix,de
    inc c
    djnz zx48_od_create_scan
    pop de
    pop bc
zx48_handle_nospc:
    ld a,E_NOSPC
    scf
    ret
zx48_od_create_found:
    ld a,c
    ld (handle_od),a
    pop de
    pop bc
    ld (ix+OD_KIND_O),b
    ld (ix+OD_ACCESS_O),c
    ld (ix+OD_ID_O),d
    ld a,1
    ld (ix+OD_REFS_O),a
    xor a
    ld (ix+OD_OFFSET_O),a
    ld (ix+OD_OFFSET_O+1),a
    ld (ix+OD_AUX_O),a
    ld (ix+OD_AUX_O+1),a
    ld a,(handle_od)
    or a
    ret

; A=OD index. Adds one shared reference.
zx48_od_retain:
    ld c,a
    call zx48_od_ptr
    ret c
    ld a,(ix+OD_KIND_O)
    or a
    jp z,zx48_handle_noent
    ld a,(ix+OD_REFS_O)
    cp $ff
    jp z,zx48_handle_busy
    inc a
    ld (ix+OD_REFS_O),a
    ld a,c
    or a
    ret

; A=OD index. Final release destroys the record and closes a logical pipe end.
zx48_od_release:
    call zx48_od_ptr
    ret c
    ld a,(ix+OD_KIND_O)
    or a
    jp z,zx48_handle_noent
    ld a,(ix+OD_REFS_O)
    dec a
    ld (ix+OD_REFS_O),a
    ret nz
    ld l,(ix+OD_AUX_O)
    ld h,(ix+OD_AUX_O+1)
    ld a,h
    or l
    jr z,zx48_od_release_no_decoder
    ld bc,PACKED_READER_STATE_SIZE
    push ix
    call zx48_free
    pop ix
    ld a,PANIC_SCHEDULER
    jp c,zx48_panic
zx48_od_release_no_decoder:
    ld d,(ix+OD_KIND_O)
    ld e,(ix+OD_ID_O)
    push ix
    pop hl
    ld b,OD_COMPACT_SIZE
    xor a
zx48_od_release_clear:
    ld (hl),a
    inc hl
    djnz zx48_od_release_clear
    ld a,d
    cp OD_KIND_PIPE_READ
    jr z,zx48_od_release_pipe
    cp OD_KIND_PIPE_WRITE
    jr z,zx48_od_release_pipe
    xor a
    ret
zx48_od_release_pipe:
    ld c,e
    ld a,d
    jp zx48_pipe_endpoint_closed

; A=handle -> HL=current-process slot.
zx48_handle_slot_ptr:
    cp MAX_HANDLES_PER_PROCESS
    jp nc,zx48_handle_noent
    ld e,a
    ld d,0
    push de
    ld a,(current_pid)
    call zx48_process_lookup
    pop de
    ret c
    push ix
    pop hl
    ld bc,PROC_HANDLES
    add hl,bc
    add hl,de
    xor a
    ret

; A=handle in current process -> C=OD index, IX=OD.
zx48_handle_lookup:
    call zx48_handle_slot_ptr
    ret c
    ld a,(hl)
    cp HANDLE_FREE
    jp z,zx48_handle_noent
    cp OPEN_DESCRIPTION_COUNT
    jp nc,zx48_handle_noent
    ld c,a
    call zx48_od_ptr
    ret c
    ld a,(ix+OD_KIND_O)
    or a
    jp z,zx48_handle_noent
    xor a
    ret

; A=requested handle or FF, C=OD index. Does not change OD refcount.
; Returns A=installed handle.
zx48_handle_install:
    ld (handle_requested),a
    ld a,c
    cp OPEN_DESCRIPTION_COUNT
    jp nc,zx48_handle_noent
    ld (handle_od),a
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld a,(handle_requested)
    cp HANDLE_FREE
    jr z,zx48_handle_install_auto
    cp MAX_HANDLES_PER_PROCESS
    jp nc,zx48_handle_nospc
    ld e,a
    ld d,0
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jp nz,zx48_handle_busy
    ld a,(handle_requested)
    jr zx48_handle_install_here
zx48_handle_install_auto:
    ld b,MAX_HANDLES_PER_PROCESS
    xor a
zx48_handle_install_scan:
    ld c,(hl)
    inc c
    jr z,zx48_handle_install_here
    inc hl
    inc a
    djnz zx48_handle_install_scan
    jp zx48_handle_nospc
zx48_handle_install_here:
    ld c,a
    ld a,(handle_od)
    ld (hl),a
    ld a,c
    or a
    ret

; A=handle. Final close releases the shared description.
zx48_handle_close:
    call zx48_handle_slot_ptr
    ret c
    ld a,(hl)
    cp HANDLE_FREE
    jp z,zx48_handle_noent
    ld (hl),HANDLE_FREE
    call zx48_od_release
    ret nc
    ld a,PANIC_SCHEDULER
    jp zx48_panic

; B=source handle,C=destination or FF. Returns A=destination.
zx48_handle_dup:
    ld a,c
    ld (handle_dup_destination),a
    ld a,b
    ld (handle_dup_source),a
    call zx48_handle_lookup
    ret c
    ld a,(handle_dup_destination)
    cp HANDLE_FREE
    jr z,zx48_handle_dup_retain
    ld b,a
    ld a,(handle_dup_source)
    cp b
    jr nz,zx48_handle_dup_retain
    ld a,b
    or a
    ret
zx48_handle_dup_retain:
    ld a,c
    call zx48_od_retain
    ret c
    ld (handle_od),a
    ld c,a
    ld a,(handle_dup_destination)
    call zx48_handle_install
    ret nc
    push af
    ld a,(handle_od)
    call zx48_od_release
    pop af
    scf
    ret

; Close every live handle of current process.
zx48_handles_close_all_current:
    ld b,0
zx48_handles_close_all_loop:
    push bc
    ld a,b
    call zx48_handle_close
    pop bc
    inc b
    ld a,b
    cp MAX_HANDLES_PER_PROCESS
    jr c,zx48_handles_close_all_loop
    xor a
    ret

zx48_handle_noent:
    ld a,E_NOENT
    scf
    ret
zx48_handle_busy:
    ld a,E_BUSY
    scf
    ret

    ENDM

;
; P4.06 staged object-open exclusivity. Kept separate from the resident handle
; macro until later Phase-4 integration so the frozen 8 KiB kernel budget remains
; unchanged while the exact bounded-pool semantics are independently qualified.
;
    MACRO EMIT_P406_EXCLUSIVITY_ROUTINES
; C=requested access,D=RAM-object identity. Scan the bounded OD pool only.
zx48_od_object_open_guard:
    ld a,c
    and O_WRITE
    ld e,a
    ld ix,open_description_table
    ld b,OPEN_DESCRIPTION_COUNT
zx48_od_object_open_guard_loop:
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_OBJECT
    jr nz,zx48_od_object_open_guard_next
    ld a,(ix+OD_ID_O)
    cp d
    jr nz,zx48_od_object_open_guard_next
    ld a,e
    or a
    jr nz,zx48_od_object_open_guard_busy
    ld a,(ix+OD_ACCESS_O)
    and O_WRITE
    jr nz,zx48_od_object_open_guard_busy
zx48_od_object_open_guard_next:
    push de
    ld de,OD_COMPACT_SIZE
    add ix,de
    pop de
    djnz zx48_od_object_open_guard_loop
    xor a
    or a
    ret
zx48_od_object_open_guard_busy:
    ld a,E_BUSY
    scf
    ret

; D=RAM-object identity. Any live OD blocks representation swaps/removal.
zx48_od_object_any_live:
    ld ix,open_description_table
    ld b,OPEN_DESCRIPTION_COUNT
zx48_od_object_any_live_loop:
    ld a,(ix+OD_KIND_O)
    cp OD_KIND_OBJECT
    jr nz,zx48_od_object_any_live_next
    ld a,(ix+OD_ID_O)
    cp d
    jr z,zx48_od_object_any_live_busy
zx48_od_object_any_live_next:
    push de
    ld de,OD_COMPACT_SIZE
    add ix,de
    pop de
    djnz zx48_od_object_any_live_loop
    xor a
    or a
    ret
zx48_od_object_any_live_busy:
    ld a,E_BUSY
    scf
    ret

; B=kind,C=access,D=identity -> A=index. Object opens enforce the P4.06 guard;
; non-object descriptions retain the already-admitted generic allocator path.
zx48_p406_od_create:
    ld a,b
    cp OD_KIND_OBJECT
    jp nz,zx48_od_create
    push bc
    push de
    call zx48_od_object_open_guard
    pop de
    pop bc
    ret c
    jp zx48_od_create
    ENDM


;
; P4.17 packed read-only open-description allocation. A=object flags,
; B=kind,C=open flags,D=identity. PACKED read-only object opens allocate exactly
; one 272-byte COLD_PREFERRED state and attach it to OD_AUX. dup/inheritance
; continue to use zx48_od_retain and therefore share this single state.
;
    MACRO EMIT_P417_PACKED_OD_ROUTINES
zx48_p417_od_create:
    ld (p417_object_flags),a
    ld a,b
    cp OD_KIND_OBJECT
    jp nz,zx48_od_create
    ld a,c
    and O_READ|O_WRITE
    cp O_READ
    jp nz,zx48_od_create
    ld a,(p417_object_flags)
    and OBJ_PACKED
    jp z,zx48_od_create

    call zx48_od_create
    ret c
    ld (p417_od_index),a

    ld bc,PACKED_READER_STATE_SIZE
    ld a,ALLOC_COLD_PREFERRED
    call zx48_alloc
    jr c,zx48_p417_od_alloc_fail
    ld (p417_state_ptr),hl
    call zx48_p417_state_init

    ld a,(p417_od_index)
    call zx48_od_ptr
    jp c,zx48_p417_od_internal_fail
    ld hl,(p417_state_ptr)
    ld (ix+OD_AUX_O),l
    ld (ix+OD_AUX_O+1),h
    ld a,(p417_od_index)
    or a
    ret

zx48_p417_od_alloc_fail:
    ld (p417_error),a
    ld a,(p417_od_index)
    call zx48_od_release
    ld a,(p417_error)
    scf
    ret

zx48_p417_od_internal_fail:
    ld hl,(p417_state_ptr)
    ld bc,PACKED_READER_STATE_SIZE
    call zx48_free
    ld a,(p417_od_index)
    call zx48_od_release
    ld a,PANIC_SCHEDULER
    jp zx48_panic

p417_object_flags: db 0
p417_od_index: db 0
p417_state_ptr: dw 0
p417_error: db 0
    ENDM
