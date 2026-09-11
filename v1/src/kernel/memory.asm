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
; Address-ordered 16-record arena extent allocator. ANY and COLD allocate low;
; FAST_REQUIRED allocates high and can never spill below 8000h.

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

; BC=request; A=allocation policy. Returns HL=base or carry/E_NOMEM.
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
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_alloc_scan:
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    ld a,h
    or l
    jr z,zx48_alloc_next
    ld a,(memory_policy)
    and $7f
    cp ALLOC_FAST_REQUIRED
    jr z,zx48_alloc_fast
    push hl
    ld bc,(memory_request)
    add hl,bc
    ex de,hl
    pop hl
    ld a,(memory_policy)
    and $7f
    cp ALLOC_COLD_PREFERRED
    jr nz,zx48_alloc_low_check
    ld a,d
    cp FAST_START/256
    jr nc,zx48_alloc_next
zx48_alloc_low_check:
    ld e,(ix+2)
    ld d,(ix+3)
    ld a,d
    cp b
    ; compare extent length DE with request from memory, without relying on B.
    ld bc,(memory_request)
    push hl
    ld h,d
    ld l,e
    or a
    sbc hl,bc
    pop hl
    jr c,zx48_alloc_next
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
    jr zx48_alloc_ok
zx48_alloc_fast:
    ; candidate=end-request; reject when below FAST_START or request>length.
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
    jr c,zx48_alloc_next
    ld de,(memory_remainder)
    ld (ix+2),e
    ld (ix+3),d
    jr zx48_alloc_ok
zx48_alloc_fast_short:
    pop hl
zx48_alloc_next:
    ld de,4
    add ix,de
    djnz zx48_alloc_scan
    ld a,(memory_policy)
    and $7f
    cp ALLOC_COLD_PREFERRED
    jr nz,zx48_alloc_fail
    ld a,ALLOC_ANY
    ld (memory_policy),a
    jp zx48_alloc_even
zx48_alloc_ok:
    ld de,(memory_live_allocations)
    inc de
    ld (memory_live_allocations),de
    xor a
    or a
    ret
zx48_alloc_zero:
    ld hl,0
    xor a
    or a
    ret
zx48_alloc_fail:
    ld a,E_NOMEM
    scf
    ret

; HL=base, BC=rounded length. Inserts then coalesces address-adjacent records.
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
    push hl
    add hl,bc
    ld de,ARENA_END+1
    or a
    sbc hl,de
    pop hl
    jr c,zx48_free_insert
    jr z,zx48_free_insert
zx48_free_bad:
    ld a,E_INVAL
    scf
    ret
zx48_free_insert:
    ld (memory_free_start),hl
    ld (memory_free_length),bc
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_free_find:
    ld a,(ix+0)
    or (ix+1)
    jr z,zx48_free_store
    ld de,4
    add ix,de
    djnz zx48_free_find
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
    or a
    ret

; Bubble sort by start, empty records last; merge exactly adjacent extents.
zx48_extent_normalize:
    ld c,FREE_EXTENT_COUNT
zx48_sort_pass:
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT-1
zx48_sort_pair:
    ld e,(ix+4)
    ld d,(ix+5)
    ld a,d
    or e
    jr z,zx48_sort_next
    ld l,(ix+0)
    ld h,(ix+1)
    ld a,h
    or l
    jr z,zx48_sort_swap
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
    djnz zx48_sort_pair
    dec c
    jr nz,zx48_sort_pass
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT-1
zx48_merge_loop:
    ld l,(ix+0)
    ld h,(ix+1)
    ld a,h
    or l
    ret z
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
    ld (ix+4),a
    ld (ix+5),a
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

; HL -> MINFO1. Largest fields are computed by scan; process byte filled by caller.
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
    ld a,h
    or l
    jr z,zx48_mem_next
    ld e,(ix+2)
    ld d,(ix+3)
    ld a,h
    cp FAST_START/256
    jr nc,zx48_mem_add_fast
    push hl
    add hl,de
    ld a,h
    cp FAST_START/256
    pop hl
    jr c,zx48_mem_add_cold
    jr nz,zx48_mem_split
    ld a,l
    or a
    jr z,zx48_mem_add_cold
zx48_mem_split:
    push de
    ld de,FAST_START
    ex de,hl
    or a
    sbc hl,de
    call zx48_mem_acc_cold
    pop de
    ld hl,(ix+0)
    add hl,de
    ld de,FAST_START
    or a
    sbc hl,de
    call zx48_mem_acc_fast
    jr zx48_mem_next
zx48_mem_add_cold:
    ex de,hl
    call zx48_mem_acc_cold
    jr zx48_mem_next
zx48_mem_add_fast:
    ex de,hl
    call zx48_mem_acc_fast
zx48_mem_next:
    ld de,4
    add ix,de
    pop bc
    djnz zx48_mem_scan
    ld hl,(memory_info_ptr)
    ld de,(memory_fast_total)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(memory_fast_largest)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(memory_cold_total)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(memory_cold_largest)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    push hl
    ld hl,(memory_fast_total)
    ld de,(memory_cold_total)
    add hl,de
    ex de,hl
    pop hl
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(memory_live_allocations)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld de,(memory_pinned_bytes)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    xor a
    ld (hl),a
    inc hl
    ld (hl),a
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
