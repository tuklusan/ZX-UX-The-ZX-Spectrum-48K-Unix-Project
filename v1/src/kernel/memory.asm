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
; Single address-ordered free-extent map for 0x6000..0xdfff. Allocations are
; two-byte aligned. FAST_REQUIRED allocates from an extent's high end so it can
; never spill below FAST_START. COLD_PREFERRED consumes low addresses first.

    MACRO EMIT_MEMORY_ROUTINES
; Inputs: none.
; Outputs: one free extent covering the complete arena.
; Flags: modified.
; Clobbers: AF/BC/DE/HL.
zx48_memory_init:
    xor a
    ld (memory_live_allocations),a
    ld (memory_live_allocations+1),a
    ld (memory_pinned_bytes),a
    ld (memory_pinned_bytes+1),a
    ld hl,memory_free_extents
    ld de,memory_free_extents+1
    ld bc,FREE_EXTENT_COUNT*4-1
    ld (hl),a
    ldir
    ld hl,ARENA_START
    ld (memory_free_extents),hl
    ld hl,ARENA_SIZE
    ld (memory_free_extents+2),hl
    ret

; Inputs: BC=requested bytes, A=ALLOC_* policy (NO_COMPACT bit ignored here).
; Outputs: carry clear HL=allocation base; carry set A=E_NOMEM.
; Flags: carry reports success/failure.
; Clobbers: AF/BC/DE/HL/IX.
zx48_alloc:
    ld a,b
    or c
    jr z,zx48_alloc_zero
    bit 0,c
    jr z,zx48_alloc_rounded
    inc bc
zx48_alloc_rounded:
    ld (memory_request),bc
    ld (memory_policy),a
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
    cp ALLOC_COLD_PREFERRED
    jr z,zx48_alloc_cold
zx48_alloc_any:
    push hl
    call zx48_extent_fits
    pop hl
    jr c,zx48_alloc_next
    call zx48_extent_take_low
    jr zx48_alloc_success
zx48_alloc_cold:
    push hl
    ld bc,(memory_request)
    add hl,bc
    ld de,FAST_START
    or a
    sbc hl,de
    pop hl
    jr nc,zx48_alloc_next_cold
    call zx48_extent_fits
    jr c,zx48_alloc_next
    call zx48_extent_take_low
    jr zx48_alloc_success
zx48_alloc_next_cold:
    ; Pass one exhausts contended candidates. The fallback to ANY is done after
    ; the table scan so scarce FAST-only space is consumed only when required.
    jr zx48_alloc_next
zx48_alloc_fast:
    push hl
    ex de,hl
    pop de
    add hl,de                    ; HL=end of extent
    ld de,(memory_request)
    or a
    sbc hl,de                    ; HL=candidate high-end allocation base
    ld de,FAST_START
    push hl
    or a
    sbc hl,de
    pop hl
    jr c,zx48_alloc_next
    ; Shorten current extent by request bytes. Candidate is already in HL.
    ld de,(memory_request)
    ld c,(ix+2)
    ld b,(ix+3)
    push hl
    ld h,b
    ld l,c
    or a
    sbc hl,de
    ld (ix+2),l
    ld (ix+3),h
    pop hl
    jr zx48_alloc_success
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
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
    jr zx48_alloc_scan
zx48_alloc_success:
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

; Inputs: DE=extent length, memory_request=request.
; Outputs: carry clear if request <= length.
; Flags: carry result.
; Clobbers: BC/HL.
zx48_extent_fits:
    ld h,d
    ld l,e
    ld bc,(memory_request)
    or a
    sbc hl,bc
    ret

; Inputs: IX current extent; HL current start.
; Outputs: HL original allocation base, extent shortened/removed.
; Flags: modified.
; Clobbers: BC/DE.
zx48_extent_take_low:
    push hl
    ld bc,(memory_request)
    add hl,bc
    ld (ix+0),l
    ld (ix+1),h
    ld e,(ix+2)
    ld d,(ix+3)
    ex de,hl
    or a
    sbc hl,bc
    ld (ix+2),l
    ld (ix+3),h
    ld a,h
    or l
    jr nz,zx48_extent_take_done
    xor a
    ld (ix+0),a
    ld (ix+1),a
zx48_extent_take_done:
    pop hl
    ret

; Inputs: HL=allocation base, BC=rounded allocation byte count.
; Outputs: carry clear on insertion/coalescing; carry set A=E_INVAL/E_NOSPC.
; Flags: carry result.
; Clobbers: AF/BC/DE/HL/IX.
zx48_free:
    ld a,b
    or c
    ret z
    bit 0,c
    jr nz,zx48_free_invalid
    ld a,h
    cp COLD_START/256
    jr c,zx48_free_invalid
    push hl
    add hl,bc
    ld de,ARENA_END+1
    or a
    sbc hl,de
    pop hl
    jr c,zx48_free_insert
    jr z,zx48_free_insert
zx48_free_invalid:
    ld a,E_INVAL
    scf
    ret
zx48_free_insert:
    ld (memory_free_request_start),hl
    ld (memory_free_request_length),bc
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT
zx48_free_find_slot:
    ld a,(ix+0)
    or (ix+1)
    jr z,zx48_free_place
    ld de,4
    add ix,de
    djnz zx48_free_find_slot
    ld a,E_NOSPC
    scf
    ret
zx48_free_place:
    ld hl,(memory_free_request_start)
    ld bc,(memory_free_request_length)
    ld (ix+0),l
    ld (ix+1),h
    ld (ix+2),c
    ld (ix+3),b
    call zx48_extent_normalize
    ld hl,(memory_live_allocations)
    ld a,h
    or l
    jr z,zx48_free_done
    dec hl
    ld (memory_live_allocations),hl
zx48_free_done:
    xor a
    or a
    ret

; Compact, sort and coalesce the bounded free table. Host/static gates prove the
; same algorithm over exhaustive boundary fixtures; target path is deliberately
; bounded to sixteen records.
zx48_extent_normalize:
    ld b,FREE_EXTENT_COUNT
zx48_extent_sort_outer:
    push bc
    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT-1
zx48_extent_sort_inner:
    ld l,(ix+0)
    ld h,(ix+1)
    ld e,(ix+4)
    ld d,(ix+5)
    ld a,d
    or e
    jr z,zx48_extent_sort_continue
    ld a,h
    or l
    jr z,zx48_extent_swap
    or a
    sbc hl,de
    jr c,zx48_extent_sort_continue
    jr z,zx48_extent_sort_continue
zx48_extent_swap:
    ld a,(ix+0)
    ld c,(ix+4)
    ld (ix+0),c
    ld (ix+4),a
    ld a,(ix+1)
    ld c,(ix+5)
    ld (ix+1),c
    ld (ix+5),a
    ld a,(ix+2)
    ld c,(ix+6)
    ld (ix+2),c
    ld (ix+6),a
    ld a,(ix+3)
    ld c,(ix+7)
    ld (ix+3),c
    ld (ix+7),a
zx48_extent_sort_continue:
    ld de,4
    add ix,de
    djnz zx48_extent_sort_inner
    pop bc
    djnz zx48_extent_sort_outer

    ld ix,memory_free_extents
    ld b,FREE_EXTENT_COUNT-1
zx48_extent_coalesce:
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
    jr nz,zx48_extent_coalesce_next
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
    push bc
    call zx48_extent_normalize
    pop bc
    ret
zx48_extent_coalesce_next:
    ld de,4
    add ix,de
    djnz zx48_extent_coalesce
    ret

; Inputs: HL=writable 16-byte MINFO1.
; Outputs: MINFO1 snapshot; process_count filled by process layer later.
; Flags: modified.
; Clobbers: AF/BC/DE/HL/IX.
zx48_mem_info:
    ld (memory_info_ptr),hl
    ld de,0                      ; cold total
    ld bc,0                      ; fast total
    ld ix,memory_free_extents
    ld a,FREE_EXTENT_COUNT
zx48_mem_info_scan:
    push af
    ld l,(ix+0)
    ld h,(ix+1)
    ld a,h
    or l
    jr z,zx48_mem_info_next
    ld a,h
    cp FAST_START/256
    jr nc,zx48_mem_info_fast
    push bc
    ld c,(ix+2)
    ld b,(ix+3)
    ex de,hl
    add hl,bc
    ex de,hl
    pop bc
    jr zx48_mem_info_next
zx48_mem_info_fast:
    ld l,(ix+2)
    ld h,(ix+3)
    add hl,bc
    ld b,h
    ld c,l
zx48_mem_info_next:
    ld hl,4
    add ix,hl
    pop af
    dec a
    jr nz,zx48_mem_info_scan
    ld hl,(memory_info_ptr)
    ld (hl),c
    inc hl
    ld (hl),b
    inc hl
    xor a
    ld (hl),a                    ; fast_largest filled by compact host-visible accounting later
    inc hl
    ld (hl),a
    inc hl
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld (hl),a                    ; cold_largest
    inc hl
    ld (hl),a
    inc hl
    push hl
    ld h,b
    ld l,c
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
    ld (hl),a                    ; process count updated by SYS_MEM_INFO wrapper
    inc hl
    ld (hl),a
    ret

memory_request:
    dw 0
memory_policy:
    db 0
memory_free_request_start:
    dw 0
memory_free_request_length:
    dw 0
memory_live_allocations:
    dw 0
memory_pinned_bytes:
    dw 0
memory_info_ptr:
    dw 0
memory_free_extents:
    defs FREE_EXTENT_COUNT*4,0
    ENDM
