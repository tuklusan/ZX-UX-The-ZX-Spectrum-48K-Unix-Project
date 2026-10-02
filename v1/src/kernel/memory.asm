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

; HL=base, BC=rounded length. Free extents stay address ordered; reject
; overlaps/double free before any mutation.
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
    ld (memory_info_ptr),hl       ; exact previous-adjacent extent, or zero
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT

zx48_free_scan:
    ld a,(ix+2)
    or (ix+3)
    jr z,zx48_free_at_empty

    ; If new_end <= current_start, ordering proves there can be no later overlap.
    ld hl,(memory_candidate)
    ld e,(ix+0)
    ld d,(ix+1)
    or a
    sbc hl,de
    jr c,zx48_free_before_current
    jp z,zx48_free_next_adjacent

    ; current_start < new_end: current_end must be <= new_start.
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld de,(memory_free_start)
    or a
    sbc hl,de
    jp nc,zx48_free_current_ge_start

zx48_free_advance:
    ld de,4
    add ix,de
    djnz zx48_free_scan
    ; Full table. Only an exact append to the final live extent can succeed.
    ld hl,(memory_info_ptr)
    ld a,h
    or l
    jp z,zx48_free_nospc
    jp zx48_free_extend_prev

zx48_free_current_ge_start:
    jr z,zx48_free_note_prev
    jp zx48_free_bad              ; current_end > new_start: overlap/double free
zx48_free_note_prev:
    push ix                       ; current_end == new_start: remember append target
    pop hl
    ld (memory_info_ptr),hl
    jr zx48_free_advance

zx48_free_at_empty:
    ld hl,(memory_info_ptr)
    ld a,h
    or l
    jp nz,zx48_free_extend_prev
    ld hl,(memory_free_start)
    ld bc,(memory_free_length)
    ld (ix+0),l
    ld (ix+1),h
    ld (ix+2),c
    ld (ix+3),b
    jp zx48_free_commit

zx48_free_before_current:
    ld hl,(memory_info_ptr)
    ld a,h
    or l
    jp nz,zx48_free_extend_prev
    ; Insert before IX. Find the first empty record and shift the sorted tail
    ; right by one record. If none exists, fail without mutation.
    push ix
    pop hl
    ld (memory_request),hl
    ld c,b
zx48_free_find_empty:
    ld a,(ix+2)
    or (ix+3)
    jr z,zx48_free_insert_found
    ld de,4
    add ix,de
    dec c
    jr nz,zx48_free_find_empty
    jp zx48_free_nospc
zx48_free_insert_found:
    push ix
    pop hl
    ld de,(memory_request)
    or a
    sbc hl,de
    ld b,h
    ld c,l
    push ix
    pop hl
    dec hl
    push ix
    pop de
    inc de
    inc de
    inc de
    lddr
    ld hl,(memory_request)
    push hl
    pop ix
    ld hl,(memory_free_start)
    ld bc,(memory_free_length)
    ld (ix+0),l
    ld (ix+1),h
    ld (ix+2),c
    ld (ix+3),b
    jp zx48_free_commit

zx48_free_next_adjacent:
    ld hl,(memory_info_ptr)
    ld a,h
    or l
    jr nz,zx48_free_merge_both
    ; Prepend into current extent.
    ld hl,(memory_free_start)
    ld (ix+0),l
    ld (ix+1),h
    ld hl,(memory_free_length)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld (ix+2),l
    ld (ix+3),h
    jp zx48_free_commit

zx48_free_extend_prev:
    push hl
    pop ix
    ld hl,(memory_free_length)
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld (ix+2),l
    ld (ix+3),h
    jp zx48_free_commit

zx48_extent_merge_restart:
zx48_free_merge_both:
    ; Previous extent touches new_start and IX touches new_end. Grow previous
    ; over both and remove IX while keeping all live records packed/sorted.
    push ix
    pop hl
    ld (memory_request),hl
    ld hl,(memory_info_ptr)
    push hl
    pop ix
    ld l,(ix+2)
    ld h,(ix+3)
    ld de,(memory_free_length)
    add hl,de
    ld de,(memory_request)
    push de
    pop ix
    ld e,(ix+2)
    ld d,(ix+3)
    add hl,de
    ld de,(memory_info_ptr)
    push de
    pop ix
    ld (ix+2),l
    ld (ix+3),h
    ld hl,(memory_request)
    push hl
    pop ix

    ; Delete current record by shifting the remaining table left, then zero the
    ; final slot. B still counts current plus all records after it.
    ld a,b
    dec a
    jr z,zx48_free_delete_zero
    add a,a
    add a,a
    ld c,a
    ld b,0
    push ix
    pop hl
    push hl
    pop de
    inc de
    inc de
    inc de
    inc de
    ex de,hl                      ; HL=source current+4, DE=destination current
    ldir
    jr zx48_free_delete_clear
zx48_free_delete_zero:
    push ix
    pop de
zx48_free_delete_clear:
    xor a
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld (de),a
    inc de
    ld (de),a

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

; Allocator runtime state lives in the fixed emergency-data reserve rather than
; consuming the frozen ordinary kernel code/data pool.
MEMORY_STATE_BASE        EQU SYSCALL_STATE_END
memory_request           EQU MEMORY_STATE_BASE+0
memory_policy            EQU MEMORY_STATE_BASE+2
memory_candidate         EQU MEMORY_STATE_BASE+3
memory_free_start        EQU MEMORY_STATE_BASE+5
memory_free_length       EQU MEMORY_STATE_BASE+7
memory_live_allocations  EQU MEMORY_STATE_BASE+9
memory_pinned_bytes      EQU MEMORY_STATE_BASE+11
memory_info_ptr          EQU MEMORY_STATE_BASE+13
memory_fast_total        EQU MEMORY_STATE_BASE+15
memory_fast_largest      EQU MEMORY_STATE_BASE+17
memory_cold_total        EQU MEMORY_STATE_BASE+19
memory_cold_largest      EQU MEMORY_STATE_BASE+21
MEMORY_STATE_END         EQU MEMORY_STATE_BASE+23
; Keep the historical unowned emergency canary at $FF80 untouched. The bounded
; extent table occupies the following fixed emergency-reserve slice.
memory_free_extents      EQU EMERGENCY_START+$80
MEMORY_EXTENT_END        EQU memory_free_extents+FREE_EXTENT_COUNT*4
    ASSERT MEMORY_STATE_END <= EMERGENCY_START+$7F
    ASSERT MEMORY_EXTENT_END <= EMERGENCY_END+1
    ENDM

;
; P4.26 bounded allocation-pressure compaction. This wrapper leaves the frozen
; base allocator unchanged: one ordinary ANY/COLD failure may trigger exactly
; one zxpack victim attempt, then exactly one guarded retry.
;
    MACRO EMIT_P426_COMPACT_ALLOC_ROUTINES
; A=allocation policy, BC=request -> HL=base.
zx48_p426_alloc:
    ld (p426_request_policy),a
    ld (p426_request_size),bc
    call zx48_alloc
    ret nc
    cp E_NOMEM
    ret nz

    ; FAST_REQUIRED and explicitly guarded allocations never compact.
    ld a,(p426_request_policy)
    bit 7,a
    jr nz,zx48_p426_nomem
    and $7f
    cp ALLOC_FAST_REQUIRED
    jr z,zx48_p426_nomem

    ; Compression is non-recursive even if a future internal caller reaches
    ; this wrapper without the public NO_COMPACT bit.
    ld a,(p426_compact_depth)
    or a
    jr nz,zx48_p426_nomem
    inc a
    ld (p426_compact_depth),a
    call zx48_p426_try_one_victim
    xor a
    ld (p426_compact_depth),a

    ; One retry only. Mark it guarded so the retry can never recurse.
    ld a,(p426_request_policy)
    or ALLOC_NO_COMPACT
    ld bc,(p426_request_size)
    jp zx48_alloc

zx48_p426_nomem:
    ld a,E_NOMEM
    scf
    ret

p426_request_policy: db 0
p426_request_size: dw 0
p426_compact_depth: db 0
    ENDM
