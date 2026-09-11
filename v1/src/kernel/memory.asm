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
; Sixteen-extent even allocator for the 0x6000-0xDFFF shared arena. ANY carves
; low addresses, FAST_REQUIRED carves high addresses, COLD_PREFERRED first tries
; a wholly contended allocation and then falls back to ANY.

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

; A=allocation policy, BC=request. Returns even HL base.
zx48_alloc:
    ld (memory_policy),a
    ld a,b
    or c
    jr z,zx48_alloc_zero
    bit 0,c
    jr z,zx48_alloc_rounded
    inc bc
zx48_alloc_rounded:
    ld (memory_request),bc
zx48_alloc_restart:
    ld ix,memory_free_extents
    ld a,FREE_EXTENT_COUNT
    ld (memory_scan_left),a
zx48_alloc_scan:
    ld e,(ix+2)
    ld d,(ix+3)
    ld a,d
    or e
    jr z,zx48_alloc_next
    ld a,(memory_policy)
    and $7f
    cp ALLOC_FAST_REQUIRED
    jr z,zx48_alloc_fast
    ld h,d
    ld l,e
    ld bc,(memory_request)
    or a
    sbc hl,bc
    jr c,zx48_alloc_next
    ld a,(memory_policy)
    and $7f
    cp ALLOC_COLD_PREFERRED
    jr nz,zx48_alloc_low_take
    ld l,(ix+0)
    ld h,(ix+1)
    add hl,bc
    ld de,FAST_START
    or a
    sbc hl,de
    jr c,zx48_alloc_low_take
    jr z,zx48_alloc_low_take
    jr zx48_alloc_next
zx48_alloc_low_take:
    ld l,(ix+0)
    ld h,(ix+1)
    push hl
    ld bc,(memory_request)
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
    ld l,(ix+0)
    ld h,(ix+1)
    add hl,de
    ld bc,(memory_request)
    or a
    sbc hl,bc
    jr c,zx48_alloc_next
    push hl
    ld de,FAST_START
    or a
    sbc hl,de
    pop hl
    jr c,zx48_alloc_next
    ld e,(ix+0)
    ld d,(ix+1)
    push hl
    or a
    sbc hl,de
    ld (ix+2),l
    ld (ix+3),h
    pop hl
    jr zx48_alloc_ok

zx48_alloc_next:
    ld de,4
    add ix,de
    ld a,(memory_scan_left)
    dec a
    ld (memory_scan_left),a
    jr nz,zx48_alloc_scan
    ld a,(memory_policy)
    and $7f
    cp ALLOC_COLD_PREFERRED
    jr nz,zx48_alloc_fail
    xor a
    ld (memory_policy),a
    jr zx48_alloc_restart
zx48_alloc_fail:
    ld a,E_NOMEM
    scf
    ret
zx48_alloc_zero:
    ld hl,0
    xor a
    ret
zx48_alloc_ok:
    ld de,(memory_live_allocations)
    inc de
    ld (memory_live_allocations),de
    xor a
    ret

; HL=base, BC=rounded size. Insert into first empty extent then coalesce.
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
    jr c,zx48_free_store
    jr z,zx48_free_store
    jr zx48_free_bad
zx48_free_bad_pop:
    pop hl
zx48_free_bad:
    ld a,E_INVAL
    scf
    ret
zx48_free_store:
    ld ix,memory_free_extents
    ld a,FREE_EXTENT_COUNT
    ld (memory_scan_left),a
zx48_free_find:
    ld a,(ix+2)
    or (ix+3)
    jr z,zx48_free_here
    ld de,4
    add ix,de
    ld a,(memory_scan_left)
    dec a
    ld (memory_scan_left),a
    jr nz,zx48_free_find
    ld a,E_NOSPC
    scf
    ret
zx48_free_here:
    ld hl,(memory_free_start)
    ld bc,(memory_free_length)
    ld (ix+0),l
    ld (ix+1),h
    ld (ix+2),c
    ld (ix+3),b
    call zx48_extent_coalesce
    ld hl,(memory_live_allocations)
    ld a,h
    or l
    jr z,zx48_free_done
    dec hl
    ld (memory_live_allocations),hl
zx48_free_done:
    xor a
    ret

; Merge any touching pair; restart after each merge. Preserve global IY anchor.
zx48_extent_coalesce:
    push iy
    call zx48_extent_coalesce_body
    pop iy
    ret
zx48_extent_coalesce_body:
zx48_extent_coalesce_restart:
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
    ld a,b
    dec a
    ld b,a
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
    jr z,zx48_extent_merge_forward
    ld l,(iy+0)
    ld h,(iy+1)
    ld e,(iy+2)
    ld d,(iy+3)
    add hl,de
    ld e,(ix+0)
    ld d,(ix+1)
    or a
    sbc hl,de
    jr z,zx48_extent_merge_reverse
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
    ret
zx48_extent_merge_forward:
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
    jr zx48_extent_coalesce_restart
zx48_extent_merge_reverse:
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
    jr zx48_extent_coalesce_restart

zx48_memory_pin_bytes:
    ld hl,(memory_pinned_bytes)
    add hl,bc
    ld (memory_pinned_bytes),hl
    ret

; HL -> exact MINFO1. Process count/reserved are filled by syscall caller.
zx48_mem_info:
    ld (memory_info_ptr),hl
    ld hl,0
    ld (memory_fast_total),hl
    ld (memory_fast_largest),hl
    ld (memory_cold_total),hl
    ld (memory_cold_largest),hl
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_mem_info_scan:
    push bc
    ld l,(ix+0)
    ld h,(ix+1)
    ld c,(ix+2)
    ld b,(ix+3)
    ld a,b
    or c
    jr z,zx48_mem_info_next
    push hl
    add hl,bc
    ld de,FAST_START
    or a
    sbc hl,de
    pop hl
    jr c,zx48_mem_info_cold_only
    ld a,h
    cp FAST_START/256
    jr nc,zx48_mem_info_fast_only
    push bc
    ld de,FAST_START
    ex de,hl
    or a
    sbc hl,de
    call zx48_mem_acc_cold
    pop bc
    ld l,(ix+0)
    ld h,(ix+1)
    add hl,bc
    ld de,FAST_START
    or a
    sbc hl,de
    call zx48_mem_acc_fast
    jr zx48_mem_info_next
zx48_mem_info_cold_only:
    ld h,b
    ld l,c
    call zx48_mem_acc_cold
    jr zx48_mem_info_next
zx48_mem_info_fast_only:
    ld h,b
    ld l,c
    call zx48_mem_acc_fast
zx48_mem_info_next:
    ld de,4
    add ix,de
    pop bc
    djnz zx48_mem_info_scan
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
memory_scan_left: db 0
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
