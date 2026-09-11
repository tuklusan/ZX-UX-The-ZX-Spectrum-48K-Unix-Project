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
; Twenty-four shared open descriptions. Process handle slots contain only IDs.

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

zx48_od_alloc:
    ld ix,open_descriptions
    ld c,0
    ld b,OPEN_DESCRIPTION_COUNT
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
    ld a,c
    ld (handle_temp_id),a
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,OD_DESC_SIZE-1
    ldir
    ld a,(handle_temp_id)
    or a
    ret

zx48_od_lookup:
    cp OPEN_DESCRIPTION_COUNT
    jr nc,zx48_handle_invalid
    ld c,a
    ld ix,open_descriptions
    or a
    jr z,zx48_od_lookup_check
    ld b,a
    ld de,OD_DESC_SIZE
zx48_od_lookup_loop:
    add ix,de
    djnz zx48_od_lookup_loop
zx48_od_lookup_check:
    ld a,(ix+OD_KIND)
    or a
    jr z,zx48_handle_invalid
    xor a
    or a
    ret

; IX=process,C=handle -> A=OD id.
zx48_handle_lookup:
    ld a,c
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_handle_invalid
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld e,c
    ld d,0
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr z,zx48_handle_invalid
    cp OPEN_DESCRIPTION_COUNT
    jr nc,zx48_handle_invalid
    or a
    ret
zx48_handle_invalid:
    ld a,E_INVAL
    scf
    ret

; IX=process,A=OD id,C=slot or FF lowest free. Returns HL=handle.
zx48_handle_install:
    ld (handle_temp_id),a
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld a,c
    cp HANDLE_FREE
    jr z,zx48_handle_install_find
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_handle_invalid
    ld e,c
    ld d,0
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr nz,zx48_handle_busy
    jr zx48_handle_install_here
zx48_handle_install_find:
    ld c,0
    ld b,MAX_HANDLES_PER_PROCESS
zx48_handle_install_scan:
    ld a,(hl)
    cp HANDLE_FREE
    jr z,zx48_handle_install_here
    inc hl
    inc c
    djnz zx48_handle_install_scan
    ld a,E_NOSPC
    scf
    ret
zx48_handle_install_here:
    ld a,(handle_temp_id)
    ld (hl),a
    ld l,c
    ld h,0
    xor a
    or a
    ret
zx48_handle_busy:
    ld a,E_BUSY
    scf
    ret

; A=kind,B=access,C=identity -> A=id, IX record, refs=1.
zx48_od_create:
    ld (handle_temp_kind),a
    ld a,b
    ld (handle_temp_access),a
    ld a,c
    ld (handle_temp_identity),a
    call zx48_od_alloc
    ret c
    ld (handle_temp_id),a
    ld a,(handle_temp_kind)
    ld (ix+OD_KIND),a
    ld a,(handle_temp_access)
    ld (ix+OD_ACCESS),a
    ld (ix+OD_REFS),1
    ld a,(handle_temp_identity)
    ld (ix+OD_IDENTITY),a
    ld a,(handle_temp_id)
    or a
    ret

; A=id. Drop one reference; invoke endpoint/object hooks at final close.
zx48_od_release_id:
    call zx48_od_lookup
    ret c
    ld a,(ix+OD_REFS)
    or a
    jr z,zx48_handle_invalid
    dec a
    ld (ix+OD_REFS),a
    jr nz,zx48_od_release_ok
    ld a,(ix+OD_KIND)
    cp OD_KIND_OBJECT
    call z,zx48_object_description_final_close
    ld a,(ix+OD_KIND)
    cp OD_KIND_PIPE_READ
    call z,zx48_pipe_reader_final_close
    ld a,(ix+OD_KIND)
    cp OD_KIND_PIPE_WRITE
    call z,zx48_pipe_writer_final_close
    ld l,(ix+OD_DECODER)
    ld h,(ix+OD_DECODER+1)
    ld a,h
    or l
    call nz,zx48_object_final_close_decoder
    push ix
    pop hl
    xor a
    ld (hl),a
    ld d,h
    ld e,l
    inc de
    ld bc,OD_DESC_SIZE-1
    ldir
zx48_od_release_ok:
    xor a
    or a
    ret

; IX=process,C=handle.
zx48_close:
    ld a,c
    cp MAX_HANDLES_PER_PROCESS
    jr nc,zx48_handle_invalid
    push ix
    pop hl
    ld de,PROC_HANDLES
    add hl,de
    ld e,c
    ld d,0
    add hl,de
    ld a,(hl)
    cp HANDLE_FREE
    jr z,zx48_handle_invalid
    ld (handle_temp_id),a
    ld (hl),HANDLE_FREE
    ld a,(handle_temp_id)
    jp zx48_od_release_id

; IX=process, HL -> {source,destination}. Destination FF chooses lowest free.
zx48_dup:
    ld (handle_process_ptr),ix
    ld c,(hl)
    inc hl
    ld a,(hl)
    ld (handle_temp_dest),a
    call zx48_handle_lookup
    ret c
    ld (handle_temp_id),a
    ld a,(handle_temp_dest)
    ld c,a
    ld ix,(handle_process_ptr)
    ld a,(handle_temp_id)
    call zx48_handle_install
    ret c
    ld (handle_temp_result),hl
    ld a,(handle_temp_id)
    call zx48_od_lookup
    ret c
    ld a,(ix+OD_REFS)
    cp $ff
    jr z,zx48_dup_overflow
    inc a
    ld (ix+OD_REFS),a
    ld hl,(handle_temp_result)
    xor a
    or a
    ret
zx48_dup_overflow:
    ld a,E_NOSPC
    scf
    ret

handle_temp_id: db 0
handle_temp_kind: db 0
handle_temp_access: db 0
handle_temp_identity: db 0
handle_temp_dest: db 0
handle_temp_result: dw 0
handle_process_ptr: dw 0
open_descriptions: defs OPEN_DESCRIPTION_COUNT*OD_DESC_SIZE,0
    ENDM
