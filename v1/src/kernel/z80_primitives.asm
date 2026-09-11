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
; Canonical Z80 copy/move/search primitives. Repeated block instructions remain
; interruptible; callers may not use them as critical-section boundaries.

    MACRO EMIT_Z80_PRIMITIVES
zx48_memcpy:
    ld a,b
    or c
    ret z
    ldir
    ret

; HL=source, DE=destination, BC=count.
zx48_memmove:
    ld a,b
    or c
    ret z
    push hl
    push de
    or a
    sbc hl,de
    pop de
    pop hl
    jr nc,zx48_memmove_fwd
    push hl
    add hl,bc
    dec hl
    ex de,hl
    add hl,bc
    dec hl
    ex de,hl
    lddr
    ret
zx48_memmove_fwd:
    ldir
    ret

; HL=buffer, BC=count, A=needle; carry clear at match, carry set if absent.
zx48_memchr:
    ld d,a
zx48_memchr_loop:
    ld a,b
    or c
    jr z,zx48_memchr_miss
    ld a,(hl)
    cp d
    ret z
    inc hl
    dec bc
    jr zx48_memchr_loop
zx48_memchr_miss:
    scf
    ret

; HL=NUL string; BC=length, HL points to NUL.
zx48_strlen:
    ld bc,0
zx48_strlen_loop:
    ld a,(hl)
    or a
    ret z
    inc hl
    inc bc
    jr zx48_strlen_loop

; HL and DE are NUL strings. Z means equal.
zx48_strcmp:
    ld a,(de)
    cp (hl)
    ret nz
    or a
    ret z
    inc de
    inc hl
    jr zx48_strcmp
    ENDM
