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
; Shared version-1 open descriptions.  Eight-byte records are sufficient for
; kind/access/refcount/identity/shared offset and the packed-reader state pointer.

OD_KIND_O                  EQU 0
OD_ACCESS_O                EQU 1
OD_REFS_O                  EQU 2
OD_ID_O                    EQU 3
OD_OFFSET_O                EQU 4
OD_AUX_O                   EQU 6
OD_COMPACT_SIZE            EQU 8

    MACRO EMIT_HANDLE_ROUTINES
zx48_handles_init:
    xor a
    ld hl,open_description_table
    ld de,open_description_table+1
    ld bc,OPEN_DESCRIPTION_COUNT*OD_COMPACT_SIZE-1
    ld (hl),a
    ldir
    ret

; A=index -> IX record.
zx48_od_ptr:
    cp OPEN_DESCRIPTION_COUNT
    jp nc,zx48_handle_noent
    ld ix,open_description_table
    or a
    ret z
    ld b,a
    ld de,OD_COMPACT_SIZE
zx48_od_ptr_loop:
    add ix,de
    djnz zx48_od_ptr_loop
    xor a
    ret

; B=kind,C=access,D=identity -> A=index, IX record, refs=1.
zx48_od_create:
    ld a,b
    ld (handle_kind),a
    ld a,c
    ld (handle_access),a
    ld a,d
    ld (handle_identity),a
    ld ix,open_description_table
    ld e,0
zx48_od_create_scan:
    ld a,(ix+OD_KIND_O)
    or a
    jp z,zx48_od_create_found
    inc e
    ld a,e
    cp OPEN_DESCRIPTION_COUNT
    jp nc,zx48_od_create_full
    ld bc,OD_COMPACT_SIZE
    add ix,bc
    jp zx48_od_create_scan
zx48_od_create_full:
    ld a,E_NOSPC
    scf
    ret
zx48_od_create_found:
    ld a,(handle_kind)
    ld (ix+OD_KIND_O),a
    ld a,(handle_access)
    ld (ix+OD_ACCESS_O),a
    ld a,(handle_identity)
    ld (ix+OD_ID_O),a
    ld a,1
    ld (ix+OD_REFS_O),a
    xor a
    ld (ix+OD_OFFSET_O),a
    ld (ix+OD_OFFSET_O+1),a
    ld (ix+OD_AUX_O),a
    ld (ix+OD_AUX_O+1),a
    ld a,e
    or a
    ret

; A=OD index. Adds one shared reference.
zx48_od_retain:
    ld (handle_od),a
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
    ld a,(handle_od)
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
    ld a,(ix+OD_KIND_O)
    ld (handle_kind),a
    ld a,(ix+OD_ID_O)
    ld (handle_identity),a
    xor a
    ld (ix+OD_KIND_O),a
    ld (ix+OD_ACCESS_O),a
    ld (ix+OD_ID_O),a
    ld (ix+OD_OFFSET_O),a
    ld (ix+OD_OFFSET_O+1),a
    ld (ix+OD_AUX_O),a
    ld (ix+OD_AUX_O+1),a
    ld a,(handle_kind)
    cp OD_KIND_PIPE_READ
    jp z,zx48_od_release_pipe
    cp OD_KIND_PIPE_WRITE
    jp z,zx48_od_release_pipe
    xor a
    ret
zx48_od_release_pipe:
    ld a,(handle_identity)
    ld c,a
    ld a,(handle_kind)
    jp zx48_pipe_endpoint_closed

; A=handle in current process -> C=OD index, IX=OD.
zx48_handle_lookup:
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
    ld (handle_od),a
    cp OPEN_DESCRIPTION_COUNT
    jp nc,zx48_handle_noent
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld a,(handle_requested)
    cp HANDLE_FREE
    jp z,zx48_handle_install_auto
    cp MAX_HANDLES_PER_PROCESS
    jp nc,zx48_handle_nospc
    ld e,a
    ld d,0
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jp nz,zx48_handle_busy
    ld a,(handle_requested)
    jp zx48_handle_install_here
zx48_handle_install_auto:
    ld b,MAX_HANDLES_PER_PROCESS
    xor a
zx48_handle_install_scan:
    ld c,(hl)
    inc c
    jp z,zx48_handle_install_here
    inc hl
    inc a
    djnz zx48_handle_install_scan
zx48_handle_nospc:
    ld a,E_NOSPC
    scf
    ret
zx48_handle_install_here:
    ld c,a
    ld a,(handle_od)
    ld (hl),a
    ld a,c
    or a
    ret

; A=handle. Final close releases the shared description.
zx48_handle_close:
    cp MAX_HANDLES_PER_PROCESS
    jp nc,zx48_handle_noent
    ld (handle_requested),a
    ld e,a
    ld d,0
    ld a,(current_pid)
    call zx48_process_lookup
    ret c
    push ix
    pop hl
    ld bc,PROC_HANDLES
    add hl,bc
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jp z,zx48_handle_noent
    ld (handle_od),a
    ld (hl),HANDLE_FREE
    ld a,(handle_od)
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
    jp z,zx48_handle_dup_retain
    ld b,a
    ld a,(handle_dup_source)
    cp b
    jp nz,zx48_handle_dup_retain
    ld a,b
    or a
    ret
zx48_handle_dup_retain:
    ld a,c
    ld (handle_od),a
    call zx48_od_retain
    ret c
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
    xor a
    ld (handle_close_cursor),a
zx48_handles_close_all_loop:
    ld a,(handle_close_cursor)
    call zx48_handle_lookup
    jp c,zx48_handles_close_all_next
    ld a,(handle_close_cursor)
    call zx48_handle_close
zx48_handles_close_all_next:
    ld a,(handle_close_cursor)
    inc a
    ld (handle_close_cursor),a
    cp MAX_HANDLES_PER_PROCESS
    jp c,zx48_handles_close_all_loop
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

handle_requested: db 0
handle_od: db 0
handle_scan_left: db 0
handle_kind: db 0
handle_access: db 0
handle_identity: db 0
handle_dup_source: db 0
handle_dup_destination: db 0
handle_close_cursor: db 0
open_description_table: defs OPEN_DESCRIPTION_COUNT*OD_COMPACT_SIZE,0
    ENDM
