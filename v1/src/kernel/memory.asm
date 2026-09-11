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
; Compact sixteen-extent arena allocator. Requests are rounded even. ANY takes
; the lowest fit, FAST_REQUIRED carves a high fit, COLD_PREFERRED first stays
; wholly below 0x8000 and otherwise retries as ANY.

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

; A=policy, BC=request -> HL=base.
zx48_alloc:
    ld (memory_policy),a
    ld a,b
    or c
    jr z,zx48_alloc_zero
    bit 0,c
    jr z,zx48_alloc_even
    inc bc
zx48_alloc_even:
    ld (memory_request),bc
zx48_alloc_retry:
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_alloc_loop:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    ld a,d
    or e
    jr z,zx48_alloc_next
    ld bc,(memory_request)
    push hl
    ld h,d
    ld l,e
    or a
    sbc hl,bc
    pop hl
    jr c,zx48_alloc_next
    ld a,(memory_policy)
    and $7f
    cp ALLOC_FAST_REQUIRED
    jr z,zx48_alloc_take_high
    cp ALLOC_COLD_PREFERRED
    jr nz,zx48_alloc_take_low
    push hl
    add hl,bc
    ld de,FAST_START
    or a
    sbc hl,de
    pop hl
    jr c,zx48_alloc_take_low
    jr z,zx48_alloc_take_low
    jr zx48_alloc_next
zx48_alloc_take_low:
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
    jp zx48_alloc_done
zx48_alloc_take_high:
    push hl
    add hl,de
    or a
    sbc hl,bc
    ld (memory_candidate),hl
    ld de,FAST_START
    or a
    sbc hl,de
    pop hl
    jr c,zx48_alloc_next
    ld de,(memory_candidate)
    push de
    ex de,hl
    or a
    sbc hl,de
    ld (ix+2),l
    ld (ix+3),h
    pop hl
    pop bc
    jp zx48_alloc_done
zx48_alloc_next:
    ld de,4
    add ix,de
    pop bc
    djnz zx48_alloc_loop
    ld a,(memory_policy)
    and $7f
    cp ALLOC_COLD_PREFERRED
    jr nz,zx48_alloc_fail
    xor a
    ld (memory_policy),a
    jp zx48_alloc_retry
zx48_alloc_fail:
    ld a,E_NOMEM
    scf
    ret
zx48_alloc_zero:
    ld hl,0
    xor a
    ret
zx48_alloc_done:
    ld de,(memory_live_allocations)
    inc de
    ld (memory_live_allocations),de
    xor a
    ret

; HL=base, BC=rounded length.
zx48_free:
    ld a,b
    or c
    ret z
    bit 0,l
    jr nz,zx48_free_bad
    bit 0,c
    jr nz,zx48_free_bad
    ld a,h
    cp COLD_START/256
    jr c,zx48_free_bad
    cp KERNEL_START/256
    jr nc,zx48_free_bad
    ld (memory_free_start),hl
    ld (memory_free_length),bc
    push hl
    add hl,bc
    jr c,zx48_free_bad_pop
    ld de,ARENA_END+1
    or a
    sbc hl,de
    pop hl
    jr c,zx48_free_find
    jr z,zx48_free_find
    jr zx48_free_bad
zx48_free_bad_pop:
    pop hl
zx48_free_bad:
    ld a,E_INVAL
    scf
    ret
zx48_free_find:
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_free_scan:
    ld a,(ix+2)
    or (ix+3)
    jr z,zx48_free_store
    ld de,4
    add ix,de
    djnz zx48_free_scan
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
    call zx48_extent_merge
    ld hl,(memory_live_allocations)
    ld a,h
    or l
    jr z,zx48_free_ok
    dec hl
    ld (memory_live_allocations),hl
zx48_free_ok:
    xor a
    ret

; Pairwise adjacent coalescing. IY is restored before return.
zx48_extent_merge:
    push iy
zx48_extent_again:
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_extent_outer:
    ld a,(ix+2)
    or (ix+3)
    jr z,zx48_extent_outer_next
    push bc
    push ix
    pop iy
    ld de,4
    add iy,de
    dec b
    jr z,zx48_extent_outer_pop
zx48_extent_inner:
    ld a,(iy+2)
    or (iy+3)
    jr z,zx48_extent_inner_next
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld e,(iy+0)
    ld d,(iy+1)
    or a
    sbc hl,de
    jr z,zx48_extent_join_xy
    ld l,(iy+0)
    ld h,(iy+1)
    ld e,(iy+2)
    ld d,(iy+3)
    add hl,de
    ld e,(ix+0)
    ld d,(ix+1)
    or a
    sbc hl,de
    jr z,zx48_extent_join_yx
zx48_extent_inner_next:
    ld de,4
    add iy,de
    djnz zx48_extent_inner
zx48_extent_outer_pop:
    pop bc
zx48_extent_outer_next:
    ld de,4
    add ix,de
    djnz zx48_extent_outer
    pop iy
    ret
zx48_extent_join_xy:
    ld l,(ix+2)
    ld h,(ix+3)
    ld e,(iy+2)
    ld d,(iy+3)
    add hl,de
    ld (ix+2),l
    ld (ix+3),h
    xor a
    ld (iy+2),a
    ld (iy+3),a
    pop bc
    jp zx48_extent_again
zx48_extent_join_yx:
    ld l,(iy+2)
    ld h,(iy+3)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld (iy+2),l
    ld (iy+3),h
    xor a
    ld (ix+2),a
    ld (ix+3),a
    pop bc
    jp zx48_extent_again

zx48_memory_pin_bytes:
    ld hl,(memory_pinned_bytes)
    add hl,bc
    ld (memory_pinned_bytes),hl
    ret

; HL -> MINFO1. Computes exact totals/largest by clipping each free extent.
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
    ld c,(ix+2)
    ld b,(ix+3)
    ld a,b
    or c
    jr z,zx48_mem_next
    ld a,h
    cp FAST_START/256
    jr nc,zx48_mem_fast_whole
    push hl
    add hl,bc
    ld de,FAST_START
    or a
    sbc hl,de
    pop hl
    jr c,zx48_mem_cold_whole
    jr z,zx48_mem_cold_whole
    ; crossing extent: cold=8000-start, fast=end-8000.
    push bc
    ld de,FAST_START
    ex de,hl
    or a
    sbc hl,de
    call zx48_mem_add_cold
    pop bc
    ld l,(ix+0)
    ld h,(ix+1)
    add hl,bc
    ld de,FAST_START
    or a
    sbc hl,de
    call zx48_mem_add_fast
    jr zx48_mem_next
zx48_mem_cold_whole:
    ld h,b
    ld l,c
    call zx48_mem_add_cold
    jr zx48_mem_next
zx48_mem_fast_whole:
    ld h,b
    ld l,c
    call zx48_mem_add_fast
zx48_mem_next:
    ld de,4
    add ix,de
    pop bc
    djnz zx48_mem_scan
    ld hl,(memory_info_ptr)
    ld de,(memory_fast_total)
    call zx48_mem_put
    ld de,(memory_fast_largest)
    call zx48_mem_put
    ld de,(memory_cold_total)
    call zx48_mem_put
    ld de,(memory_cold_largest)
    call zx48_mem_put
    push hl
    ld hl,(memory_fast_total)
    ld de,(memory_cold_total)
    add hl,de
    ex de,hl
    pop hl
    call zx48_mem_put
    ld de,(memory_live_allocations)
    call zx48_mem_put
    ld de,(memory_pinned_bytes)
    call zx48_mem_put
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
    ret
zx48_mem_put:
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ret
zx48_mem_add_cold:
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
zx48_mem_add_fast:
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
memory_candidate: dw 0
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
