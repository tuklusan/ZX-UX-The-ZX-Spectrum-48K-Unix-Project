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
; Synchronous cassette transport. Physical positioning is never inferred.

    MACRO EMIT_TAPE_ROUTINES
; A=block type,DE=length,IX=source.
zx48_tape_save_block:
    call zx48_rom_sa_bytes
    ret nc
    ld a,E_IO
    scf
    ret
; A=block type,DE=length,IX=destination; carry selects load/verify.
zx48_tape_load_block:
    call zx48_rom_ld_bytes
    ret nc
    ld a,E_IO
    scf
    ret

; Public object operations are deliberately sequential. The compact resident
; layer validates RAM namespace first; host/tape format tests own M48O framing.
zx48_tape_save_path:
    call zx48_path_resolve
    ret c
    ld a,c
    cp PATH_KIND_BASE
    jr nz,zx48_tape_bad
    ld a,(path_dir)
    ld hl,path_name
    call zx48_object_lookup
    ret c
    ; Save RAW logical payload as ROM data block after a transport header emitted
    ; by the shell/host builder. PACKED RAM objects are materialized first.
    ld a,(ix+OBJ_FLAGS_BYTE)
    and OBJ_PACKED
    call nz,zx48_zxpack_materialize
    ret c
    ld l,(ix+OBJ_ALLOCATION_PTR)
    ld h,(ix+OBJ_ALLOCATION_PTR+1)
    push hl
    pop ix
    ld e,(ix+OBJ_LOGICAL_LENGTH)  ; IX is payload now; metadata unavailable.
    ld a,E_NOTSUP
    scf
    ret

zx48_tape_load_path:
    ; Loading requires the next physical M48O name to match requested path. The
    ; full sequential transaction is exposed through SYS_TAPE_SCAN + shell copy.
    ld a,E_AGAIN
    scf
    ret
zx48_tape_verify_path:
    ld a,E_AGAIN
    scf
    ret

; HL=32-byte header destination. Consumes exactly one next M48O header block.
zx48_tape_scan_next:
    push hl
    pop ix
    ld a,$ff
    ld de,M48O_HEADER_SIZE
    scf
    call zx48_tape_load_block
    ret c
    ld hl,1
    xor a
    or a
    ret
zx48_tape_bad:
    ld a,E_INVAL
    scf
    ret
    ENDM
