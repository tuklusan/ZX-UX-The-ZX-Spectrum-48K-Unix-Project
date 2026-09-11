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
; Exactly 24 system-wide open descriptions, 12 bytes each. Process handle slots
; store only description IDs or 0xff. Independent opens own independent offsets;
; dup/spawn references share one description and therefore one offset/decoder.

OD_KIND                  EQU 0
OD_ACCESS                EQU 1
OD_REFS                  EQU 2
OD_IDENTITY              EQU 3
OD_OFFSET                EQU 4
OD_DECODER               EQU 6
OD_AUX                   EQU 8
OD_FLAGS                 EQU 10
OD_RESERVED              EQU 11

    MACRO EMIT_HANDLE_ROUTINES
zx48_handles_init:
    xor a
    ld hl,open_descriptions
    ld de,open_descriptions+1
    ld bc,OPEN_DESCRIPTION_COUNT*OD_DESC_SIZE-1
    ld (hl),a
    ldir
    ret

; Inputs: none.
; Outputs: carry clear A=description ID, IX=zeroed record; carry set A=E_NOSPC.
zx48_od_alloc:
    ld ix,open_descriptions
    ld b,OPEN_DESCRIPTION_COUNT
    ld c,0
zx48_od_alloc_loop:
    ld a,(ix+OD_KIND)
    or a
    jr z,zx48_od_alloc_found
    ld de,OD_DESC_SIZE
    add ix,de
    inc c
    djnz zx48_od_alloc_loop
    ld a,E_NOSPC
    scf
    ret
zx48_od_alloc_found:
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,OD_DESC_SIZE-1
    ldir
    ld a,c
    or a
    ret

; Inputs: A=description ID.
; Outputs: carry clear IX=record; carry set A=E_INVAL.
zx48_od_lookup:
    cp OPEN_DESCRIPTION_COUNT
    jr nc,zx48_od_lookup_fail
    ld c,a
    ld b,0
    ld hl,open_descriptions
    ld de,OD_DESC_SIZE
    ld a,c
    or a
    jr z,zx48_od_lookup_done
zx48_od_lookup_loop:
    add hl,de
    dec c
    jr nz,zx48_od_lookup_loop
zx48_od_lookup_done:
    push hl
    pop ix
    ld a,(ix+OD_KIND)
    or a
    jr z,zx48_od_lookup_fail
    xor a
    or a
    ret
zx48_od_lookup_fail:
    ld a,E_INVAL
    scf
    ret

; Inputs: IX=current process descriptor, C=handle.
; Outputs: carry clear A=description ID; carry set errno.
zx48_handle_lookup:
    ld a,c
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_handle_lookup_fail
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld e,c
    ld d,0
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr z,zx48_handle_lookup_fail
    cp OPEN_DESCRIPTION_COUNT
    jr nc,zx48_handle_lookup_fail
    or a
    ret
zx48_handle_lookup_fail:
    ld a,E_INVAL
    scf
    ret

; Inputs: IX=process, A=description ID, C=requested handle or ff lowest free.
; Outputs: carry clear L=installed handle; carry set errno. No reference changed.
zx48_handle_install:
    ld (handle_temp_description),a
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld a,c
    cp HANDLE_FREE
    jr z,zx48_handle_find_free
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_handle_install_invalid
    ld e,c
    ld d,0
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr nz,zx48_handle_install_busy
    ld a,(handle_temp_description)
    ld (hl),a
    ld l,c
    xor a
    or a
    ret
zx48_handle_find_free:
    ld c,0
    ld b,MAX_HANDLES_PER_PROCESS
zx48_handle_find_loop:
    ld a,(hl)
    cp HANDLE_FREE
    jr z,zx48_handle_found_free
    inc hl
    inc c
    djnz zx48_handle_find_loop
    ld a,E_NOSPC
    scf
    ret
zx48_handle_found_free:
    ld a,(handle_temp_description)
    ld (hl),a
    ld l,c
    xor a
    or a
    ret
zx48_handle_install_busy:
    ld a,E_BUSY
    scf
    ret
zx48_handle_install_invalid:
    ld a,E_INVAL
    scf
    ret

; Inputs: IX=process; HL -> DUP1 {source,destination}.
; Outputs: carry clear HL=result handle; carry set errno.
zx48_dup:
    ld c,(hl)
    inc hl
    ld e,(hl)
    push de
    call zx48_handle_lookup
    jr c,zx48_dup_fail_pop
    ld (handle_temp_description),a
    pop de
    ld c,e
    cp HANDLE_FREE
    jr z,zx48_dup_install
    ; Explicit same slot is the only occupied-destination no-op.
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld e,c
    ld d,0
    add hl,de
    ld a,(hl)
    ld d,a
    ld a,(handle_temp_description)
    cp d
    jr z,zx48_dup_same
zx48_dup_install:
    ld a,(handle_temp_description)
    call zx48_handle_install
    ret c
    ld c,l
    ld a,(handle_temp_description)
    call zx48_od_lookup
    jr c,zx48_dup_rollback
    ld a,(ix+OD_REFS)
    cp $ff
    jr z,zx48_dup_ref_overflow
    inc a
    ld (ix+OD_REFS),a
    ld h,0
    ld l,c
    xor a
    or a
    ret
zx48_dup_same:
    ld h,0
    ld l,c
    xor a
    or a
    ret
zx48_dup_ref_overflow:
    ld a,E_NOSPC
zx48_dup_rollback:
    push af
    ld a,(current_pid)
    call zx48_process_descriptor_from_pid
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld e,c
    ld d,0
    add hl,de
    ld (hl),HANDLE_FREE
    pop af
    scf
    ret
zx48_dup_fail_pop:
    pop de
    scf
    ret

; Inputs: IX=process, C=handle.
; Outputs: carry clear; final description destroyed at refcount zero.
zx48_close:
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld a,c
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_close_invalid
    ld e,c
    ld d,0
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr z,zx48_close_invalid
    ld (hl),HANDLE_FREE
    call zx48_od_lookup
    jr c,zx48_close_invalid
    ld a,(ix+OD_REFS)
    or a
    jr z,zx48_close_invalid
    dec a
    ld (ix+OD_REFS),a
    jr nz,zx48_close_ok
    ld a,(ix+OD_DECODER)
    or (ix+OD_DECODER+1)
    ; Decoder storage, if any, is allocator-owned by object layer and released
    ; through the bounded final-close hook before the record is cleared.
    call nz,zx48_object_final_close_decoder
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
zx48_close_ok:
    xor a
    or a
    ret
zx48_close_invalid:
    ld a,E_INVAL
    scf
    ret

; Inputs: A=description kind, B=access, C=identity.
; Outputs: carry clear A=id, IX=record initialized refs=1 offset0.
zx48_od_create:
    ld (handle_temp_kind),a
    ld a,b
    ld (handle_temp_access),a
    ld a,c
    ld (handle_temp_identity),a
    call zx48_od_alloc
    ret c
    ld (handle_temp_description),a
    ld a,(handle_temp_kind)
    ld (ix+OD_KIND),a
    ld a,(handle_temp_access)
    ld (ix+OD_ACCESS),a
    ld (ix+OD_REFS),1
    ld a,(handle_temp_identity)
    ld (ix+OD_IDENTITY),a
    xor a
    ld (ix+OD_OFFSET),a
    ld (ix+OD_OFFSET+1),a
    ld (ix+OD_DECODER),a
    ld (ix+OD_DECODER+1),a
    ld a,(handle_temp_description)
    or a
    ret

handle_temp_description:
    db 0
handle_temp_kind:
    db 0
handle_temp_access:
    db 0
handle_temp_identity:
    db 0
open_descriptions:
    defs OPEN_DESCRIPTION_COUNT*OD_DESC_SIZE,0
    ENDM
