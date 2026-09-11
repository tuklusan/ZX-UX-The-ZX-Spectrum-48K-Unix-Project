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
; Compact address-ordered arena extent allocator. All requests are even-rounded.

    MACRO EMIT_MEMORY_ROUTINES
zx48_memory_init:
    xor a
    ld hl,memory_free_extents
    ld de,memory_free_extents+1
    ld bc,FREE_EXTENT_COUNT*4-1
    ld (hl),a
    ldir
    ld hl,ARENA_START
    ld (memory_free_extents),hl
    ld hl,ARENA_SIZE
    ld (memory_free_extents+2),hl
    ld hl,0
    ld (memory_live_allocations),hl
    ld (memory_pinned_bytes),hl
    ret

; A policy, BC requested bytes. Return HL base or carry/E_NOMEM.
zx48_alloc:
    ld (memory_policy),a
    ld a,b
    or c
    jp z,zx48_alloc_zero
    bit 0,c
    jr z,zx48_alloc_aligned
    inc bc
zx48_alloc_aligned:
    ld (memory_request),bc
    ld a,(memory_policy)
    and $7f
    cp ALLOC_FAST_REQUIRED
    jp z,zx48_alloc_fast_scan
zx48_alloc_low_restart:
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_alloc_low_loop:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    ld a,d
    or e
    jr z,zx48_alloc_low_next
    ld bc,(memory_request)
    push hl
    ld h,d
    ld l,e
    or a
    sbc hl,bc
    pop hl
    jr c,zx48_alloc_low_next
    ld a,(memory_policy)
    and $7f
    cp ALLOC_COLD_PREFERRED
    jr nz,zx48_alloc_low_take
    push hl
    add hl,bc
    ld de,FAST_START
    or a
    sbc hl,de
    pop hl
    jr nc,zx48_alloc_low_next
zx48_alloc_low_take:
    push hl
    add hl,bc
    ld (ix+0),l
    ld (ix+1),h
    ld l,(ix+2)
    ld h,(ix+3)
    or a
    sbc hl,bc
    ld (ix+2),l
    ld (ix+3),h
    pop hl
    pop bc
    jp zx48_alloc_success
zx48_alloc_low_next:
    ld de,4
    add ix,de
    pop bc
    djnz zx48_alloc_low_loop
    ld a,(memory_policy)
    and $7f
    cp ALLOC_COLD_PREFERRED
    jr nz,zx48_alloc_fail
    xor a
    ld (memory_policy),a
    jp zx48_alloc_low_restart

zx48_alloc_fast_scan:
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_alloc_fast_loop:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    ld a,d
    or e
    jr z,zx48_alloc_fast_next
    ld bc,(memory_request)
    push hl
    ld h,d
    ld l,e
    or a
    sbc hl,bc
    jr c,zx48_alloc_fast_short
    ld (memory_remainder),hl
    pop hl
    ld de,(memory_remainder)
    add hl,de
    ld de,FAST_START
    push hl
    or a
    sbc hl,de
    pop hl
    jr c,zx48_alloc_fast_next
    ld de,(memory_remainder)
    ld (ix+2),e
    ld (ix+3),d
    pop bc
    jp zx48_alloc_success
zx48_alloc_fast_short:
    pop hl
zx48_alloc_fast_next:
    ld de,4
    add ix,de
    pop bc
    djnz zx48_alloc_fast_loop
zx48_alloc_fail:
    ld a,E_NOMEM
    scf
    ret
zx48_alloc_zero:
    ld hl,0
    xor a
    ret
zx48_alloc_success:
    ld de,(memory_live_allocations)
    inc de
    ld (memory_live_allocations),de
    xor a
    ret

; HL base, BC rounded size. Insert and normalize.
zx48_free:
    ld a,b
    or c
    ret z
    bit 0,l
    jp nz,zx48_free_bad
    bit 0,c
    jp nz,zx48_free_bad
    ld a,h
    cp COLD_START/256
    jr c,zx48_free_bad
    push hl
    add hl,bc
    ld de,ARENA_END+1
    or a
    sbc hl,de
    pop hl
    jr c,zx48_free_find
    jr nz,zx48_free_bad
zx48_free_find:
    ld (memory_free_start),hl
    ld (memory_free_length),bc
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_free_find_loop:
    ld a,(ix+2)
    or (ix+3)
    jr z,zx48_free_store
    ld de,4
    add ix,de
    djnz zx48_free_find_loop
    ld a,E_NOSPC
    scf
    ret
zx48_free_store:
    ld hl,(memory_free_start)
    ld bc,(memory_free_length)
    ld (ix+0),l
    ld (ix+1),h
    ld (ix+2),c
    ld (ix+3),b
    call zx48_extent_normalize
    ld hl,(memory_live_allocations)
    ld a,h
    or l
    jr z,zx48_free_ok
    dec hl
    ld (memory_live_allocations),hl
zx48_free_ok:
    xor a
    ret
zx48_free_bad:
    ld a,E_INVAL
    scf
    ret

; Small insertion/bubble normalize. Empty extents sort last, adjacent coalesce.
zx48_extent_normalize:
    ld c,FREE_EXTENT_COUNT
zx48_sort_pass:
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT-1
zx48_sort_loop:
    ld e,(ix+6)
    ld d,(ix+7)
    ld a,d
    or e
    jr z,zx48_sort_next
    ld e,(ix+2)
    ld d,(ix+3)
    ld a,d
    or e
    jr z,zx48_sort_swap
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+4)
    ld d,(ix+5)
    or a
    sbc hl,de
    jr c,zx48_sort_next
    jr z,zx48_sort_next
zx48_sort_swap:
    ld a,(ix+0)
    ld l,(ix+4)
    ld (ix+0),l
    ld (ix+4),a
    ld a,(ix+1)
    ld l,(ix+5)
    ld (ix+1),l
    ld (ix+5),a
    ld a,(ix+2)
    ld l,(ix+6)
    ld (ix+2),l
    ld (ix+6),a
    ld a,(ix+3)
    ld l,(ix+7)
    ld (ix+3),l
    ld (ix+7),a
zx48_sort_next:
    ld de,4
    add ix,de
    djnz zx48_sort_loop
    dec c
    jr nz,zx48_sort_pass
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT-1
zx48_merge_loop:
    ld l,(ix+2)
    ld h,(ix+3)
    ld a,h
    or l
    ret z
    ld e,(ix+6)
    ld d,(ix+7)
    ld a,d
    or e
    ret z
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld e,(ix+4)
    ld d,(ix+5)
    or a
    sbc hl,de
    jr nz,zx48_merge_next
    ld l,(ix+2)
    ld h,(ix+3)
    ld e,(ix+6)
    ld d,(ix+7)
    add hl,de
    ld (ix+2),l
    ld (ix+3),h
    xor a
    ld (ix+6),a
    ld (ix+7),a
    jp zx48_extent_normalize
zx48_merge_next:
    ld de,4
    add ix,de
    djnz zx48_merge_loop
    ret

zx48_memory_pin_bytes:
    ld hl,(memory_pinned_bytes)
    add hl,bc
    ld (memory_pinned_bytes),hl
    ret

; HL points to exact 16-byte MINFO1. Process count filled by syscall caller.
zx48_mem_info:
    ld (memory_info_ptr),hl
    ld hl,0
    ld (memory_fast_total),hl
    ld (memory_fast_largest),hl
    ld (memory_cold_total),hl
    ld (memory_cold_largest),hl
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_mem_scan:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    ld a,d
    or e
    jr z,zx48_mem_next
    ld a,h
    cp FAST_START/256
    jr nc,zx48_mem_fast
    push hl
    add hl,de
    ld a,h
    cp FAST_START/256
    pop hl
    jr c,zx48_mem_cold
    jr nz,zx48_mem_split
    ld a,l
    or a
    jr z,zx48_mem_cold
zx48_mem_split:
    push de
    ld de,FAST_START
    ex de,hl
    or a
    sbc hl,de
    call zx48_mem_acc_cold
    pop de
    ld l,(ix+0)
    ld h,(ix+1)
    add hl,de
    ld de,FAST_START
    or a
    sbc hl,de
    call zx48_mem_acc_fast
    jr zx48_mem_next
zx48_mem_cold:
    ex de,hl
    call zx48_mem_acc_cold
    jr zx48_mem_next
zx48_mem_fast:
    ex de,hl
    call zx48_mem_acc_fast
zx48_mem_next:
    ld de,4
    add ix,de
    pop bc
    djnz zx48_mem_scan
    ld hl,(memory_info_ptr)
    ld de,(memory_fast_total)
    call zx48_mem_put16
    ld de,(memory_fast_largest)
    call zx48_mem_put16
    ld de,(memory_cold_total)
    call zx48_mem_put16
    ld de,(memory_cold_largest)
    call zx48_mem_put16
    push hl
    ld hl,(memory_fast_total)
    ld de,(memory_cold_total)
    add hl,de
    ex de,hl
    pop hl
    call zx48_mem_put16
    ld de,(memory_live_allocations)
    call zx48_mem_put16
    ld de,(memory_pinned_bytes)
    call zx48_mem_put16
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    ret
zx48_mem_put16:
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ret
zx48_mem_acc_cold:
    push hl
    ld de,(memory_cold_total)
    add hl,de
    ld (memory_cold_total),hl
    pop hl
    ld de,(memory_cold_largest)
    or a
    sbc hl,de
    ret c
    ret z
    add hl,de
    ld (memory_cold_largest),hl
    ret
zx48_mem_acc_fast:
    push hl
    ld de,(memory_fast_total)
    add hl,de
    ld (memory_fast_total),hl
    pop hl
    ld de,(memory_fast_largest)
    or a
    sbc hl,de
    ret c
    ret z
    add hl,de
    ld (memory_fast_largest),hl
    ret

memory_request: dw 0
memory_policy: db 0
memory_remainder: dw 0
memory_free_start: dw 0
memory_free_length: dw 0
memory_live_allocations: dw 0
memory_pinned_bytes: dw 0
memory_info_ptr: dw 0
memory_fast_total: dw 0
memory_fast_largest: dw 0
memory_cold_total: dw 0
memory_cold_largest: dw 0
memory_free_extents: defs FREE_EXTENT_COUNT*4,0
    ENDM
