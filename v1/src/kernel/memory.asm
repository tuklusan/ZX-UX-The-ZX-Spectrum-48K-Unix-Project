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
; Sixteen-entry address-ordered arena allocator. Requests are rounded even.
; ANY takes the lowest fit, FAST_REQUIRED carves a high fit, COLD_PREFERRED
; first stays wholly below 0x8000 and otherwise retries as ANY.

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
    jp z,zx48_alloc_zero
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
    dec b
    jp nz,zx48_alloc_loop
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

; HL=base, BC=rounded length. Reject overlaps/double free before mutation.
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
    jp c,zx48_free_bad
    cp KERNEL_START/256
    jp nc,zx48_free_bad
    ld (memory_free_start),hl
    ld (memory_free_length),bc
    add hl,bc
    jp c,zx48_free_bad
    ld de,ARENA_END+1
    or a
    sbc hl,de
    jr c,zx48_free_end_ok
    jp nz,zx48_free_bad
zx48_free_end_ok:
    add hl,de
    ld (memory_candidate),hl
    ld hl,0
    ld (memory_info_ptr),hl
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_free_scan:
    ld a,(ix+2)
    or (ix+3)
    jr nz,zx48_free_live
    ld hl,(memory_info_ptr)
    ld a,h
    or l
    jr nz,zx48_free_next
    push ix
    pop hl
    ld (memory_info_ptr),hl
    jr zx48_free_next
zx48_free_live:
    ; new_end compared with existing_start.
    ld hl,(memory_candidate)
    ld e,(ix+0)
    ld d,(ix+1)
    or a
    sbc hl,de
    jp z,zx48_free_prepend
    jr c,zx48_free_next
    ; existing_end compared with new_start.
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld de,(memory_free_start)
    or a
    sbc hl,de
    jp z,zx48_free_append
    jr c,zx48_free_next
    jp zx48_free_bad
zx48_free_next:
    ld de,4
    add ix,de
    djnz zx48_free_scan
    ld hl,(memory_info_ptr)
    ld a,h
    or l
    jp z,zx48_free_nospc
    push hl
    pop ix
    ld hl,(memory_free_start)
    ld bc,(memory_free_length)
    ld (ix+0),l
    ld (ix+1),h
    ld (ix+2),c
    ld (ix+3),b
    jp zx48_free_normalize
zx48_free_prepend:
    ld hl,(memory_free_start)
    ld (ix+0),l
    ld (ix+1),h
    ld hl,(memory_free_length)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld (ix+2),l
    ld (ix+3),h
    jr zx48_free_normalize
zx48_free_append:
    ld hl,(memory_free_length)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld (ix+2),l
    ld (ix+3),h
zx48_free_normalize:
    call zx48_extent_sort
zx48_extent_merge_restart:
    ld ix,memory_free_extents
    ld c,FREE_EXTENT_COUNT-1
zx48_extent_merge_loop:
    ld a,(ix+2)
    or (ix+3)
    jr z,zx48_free_commit
    ld a,(ix+6)
    or (ix+7)
    jr z,zx48_free_commit
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld e,(ix+4)
    ld d,(ix+5)
    or a
    sbc hl,de
    jr nz,zx48_extent_merge_next
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
    call zx48_extent_sort
    jr zx48_extent_merge_restart
zx48_extent_merge_next:
    ld de,4
    add ix,de
    dec c
    jr nz,zx48_extent_merge_loop
zx48_free_commit:
    ld hl,(memory_live_allocations)
    ld a,h
    or l
    jr z,zx48_free_ok
    dec hl
    ld (memory_live_allocations),hl
zx48_free_ok:
    xor a
    ret
zx48_free_nospc:
    ld a,E_NOSPC
    scf
    ret
zx48_free_bad:
    ld a,E_INVAL
    scf
    ret

; Stable bounded sort: active records by ascending start, zero-length records last.
zx48_extent_sort:
    ld b,FREE_EXTENT_COUNT-1
zx48_extent_sort_pass:
    ld ix,memory_free_extents
    ld c,FREE_EXTENT_COUNT-1
zx48_extent_sort_pair:
    ld a,(ix+2)
    or (ix+3)
    jr nz,zx48_extent_sort_current_live
    ld a,(ix+6)
    or (ix+7)
    jr z,zx48_extent_sort_next
    jr zx48_extent_swap
zx48_extent_sort_current_live:
    ld a,(ix+6)
    or (ix+7)
    jr z,zx48_extent_sort_next
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+4)
    ld d,(ix+5)
    or a
    sbc hl,de
    jr c,zx48_extent_sort_next
    jr z,zx48_extent_sort_next
zx48_extent_swap:
    ld a,(ix+0)
    ld e,(ix+4)
    ld (ix+0),e
    ld (ix+4),a
    ld a,(ix+1)
    ld e,(ix+5)
    ld (ix+1),e
    ld (ix+5),a
    ld a,(ix+2)
    ld e,(ix+6)
    ld (ix+2),e
    ld (ix+6),a
    ld a,(ix+3)
    ld e,(ix+7)
    ld (ix+3),e
    ld (ix+7),a
zx48_extent_sort_next:
    ld de,4
    add ix,de
    dec c
    jr nz,zx48_extent_sort_pair
    djnz zx48_extent_sort_pass
    ret

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
    call zx48_process_count
    ld (hl),a
    inc hl
    xor a
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
