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
; Compact shared open-description layer. Eight-byte records remain below the
; twelve-byte architecture ceiling and share offsets across dup/inheritance.

OD_KIND_O                 EQU 0
OD_ACCESS_O               EQU 1
OD_REFS_O                 EQU 2
OD_ID_O                   EQU 3
OD_OFFSET_O               EQU 4
OD_AUX_O                  EQU 6
OD_COMPACT_SIZE           EQU 8

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
    ret

; B=kind,C=access,D=identity -> A=index, IX record, refs=1.
zx48_od_create:
    ld ix,open_description_table
    ld e,0
    ld a,OPEN_DESCRIPTION_COUNT
    ld (handle_scan_left),a
zx48_od_create_scan:
    ld a,(ix+OD_KIND_O)
    or a
    jr z,zx48_od_create_found
    inc e
    ld bc,OD_COMPACT_SIZE
    add ix,bc
    ld a,(handle_scan_left)
    dec a
    ld (handle_scan_left),a
    jr nz,zx48_od_create_scan
    ld a,E_NOSPC
    scf
    ret
zx48_od_create_found:
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
    ld a,e
    or a
    ret

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
    jr nc,zx48_handle_nospc
    ld e,a
    ld d,0
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr nz,zx48_handle_busy
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
zx48_handle_nospc:
    ld a,E_NOSPC
    scf
    ret
zx48_handle_busy:
    ld a,E_BUSY
    scf
    ret
zx48_handle_install_here:
    ld c,a
    ld a,(handle_od)
    ld (hl),a
    ld a,c
    or a
    ret

; A=handle. Final close clears the OD.
zx48_handle_close:
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_handle_noent
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
    jr z,zx48_handle_noent
    ld c,a
    ld (hl),HANDLE_FREE
    ld a,c
    call zx48_od_ptr
    ret c
    ld a,(ix+OD_REFS_O)
    dec a
    ld (ix+OD_REFS_O),a
    ret nz
    xor a
    ld (ix+OD_KIND_O),a
    ld (ix+OD_ACCESS_O),a
    ld (ix+OD_ID_O),a
    ret

; B=source handle,C=destination or FF. Returns A=destination.
zx48_handle_dup:
    ld a,b
    call zx48_handle_lookup
    ret c
    ld a,(ix+OD_REFS_O)
    cp $ff
    jr z,zx48_handle_busy
    inc a
    ld (ix+OD_REFS_O),a
    ld a,c
    call zx48_handle_install
    ret nc
    ld a,(ix+OD_REFS_O)
    dec a
    ld (ix+OD_REFS_O),a
    scf
    ret

zx48_handle_noent:
    ld a,E_NOENT
    scf
    ret

handle_requested: db 0
handle_od: db 0
handle_scan_left: db 0
open_description_table: defs OPEN_DESCRIPTION_COUNT*OD_COMPACT_SIZE,0
    ENDM
