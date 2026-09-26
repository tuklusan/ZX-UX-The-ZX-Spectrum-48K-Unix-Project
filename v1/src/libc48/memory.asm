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
; P11.21 fixed-BSS C48 malloc/free allocator.
; Only the linker-reserved [__heap_start,__heap_end) interval is managed.

    MACRO EMIT_P1121_C48_MEMORY
C48_HEAP_HEADER_SIZE EQU 4
C48_HEAP_FREE EQU 0
C48_HEAP_USED EQU 1

c48_heap_start_ptr: dw 0
c48_heap_end_ptr:   dw 0
c48_heap_ready:     db 0
c48_heap_scan:      dw 0
c48_heap_request:   dw 0
c48_heap_prev:      dw 0

c48_heap_init_linker:
    ld de,__heap_start
    ld bc,__heap_end
    jp c48_heap_init_bounds

; DE=start, BC=end. Bounds are even and ordered. Zero bytes are valid.
c48_heap_init_bounds:
    ld a,e
    or c
    and 1
    jp nz,c48_heap_bad_bounds
    push bc
    push de
    ld h,b
    ld l,c
    or a
    sbc hl,de
    jp c,c48_heap_bad_bounds_pop
    pop de
    pop bc
    ld (c48_heap_start_ptr),de
    ld (c48_heap_end_ptr),bc
    ld a,1
    ld (c48_heap_ready),a

    ld h,b
    ld l,c
    or a
    sbc hl,de
    ret z
    ld a,h
    or a
    jr nz,c48_heap_init_large
    ld a,l
    cp C48_HEAP_HEADER_SIZE+2
    jr c,c48_heap_init_tiny
c48_heap_init_large:
    ex de,hl
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld (hl),C48_HEAP_FREE
    inc hl
    ld (hl),0
c48_heap_init_tiny:
    xor a
    ret

c48_heap_bad_bounds_pop:
    pop de
    pop bc
c48_heap_bad_bounds:
    xor a
    ld (c48_heap_ready),a
    ld hl,0
    ld (c48_heap_start_ptr),hl
    ld (c48_heap_end_ptr),hl
    ret

; HL=request bytes. Returns aligned payload pointer in HL or NULL.
malloc:
    ld a,h
    or l
    jp z,c48_malloc_null
    bit 0,l
    jr z,c48_malloc_even
    inc hl
c48_malloc_even:
    ld de,C48_HEAP_HEADER_SIZE
    add hl,de
    jp c,c48_malloc_null
    ld (c48_heap_request),hl

    ld a,(c48_heap_ready)
    or a
    call z,c48_heap_init_linker

    ld hl,(c48_heap_start_ptr)
    ld (c48_heap_scan),hl
c48_malloc_scan:
    ld hl,(c48_heap_scan)
    ld de,(c48_heap_end_ptr)
    or a
    sbc hl,de
    jp nc,c48_malloc_null

    ld hl,(c48_heap_scan)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or e
    jr z,c48_malloc_null
    inc hl
    ld a,(hl)
    cp C48_HEAP_FREE
    jr nz,c48_malloc_next

    push de
    ld hl,(c48_heap_request)
    ex de,hl
    or a
    sbc hl,de
    jr c,c48_malloc_too_small
    pop bc
    ; HL=remainder, DE=requested total.
    ld a,h
    or a
    jr nz,c48_malloc_split
    ld a,l
    cp C48_HEAP_HEADER_SIZE+2
    jr c,c48_malloc_whole

c48_malloc_split:
    push hl
    ld hl,(c48_heap_scan)
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld (hl),C48_HEAP_USED
    inc hl
    ld (hl),0

    ld hl,(c48_heap_scan)
    add hl,de
    pop de
    ld (hl),e
    inc hl
    ld (hl),d
    inc hl
    ld (hl),C48_HEAP_FREE
    inc hl
    ld (hl),0
    jr c48_malloc_return

c48_malloc_whole:
    ld hl,(c48_heap_scan)
    inc hl
    inc hl
    ld (hl),C48_HEAP_USED
    jr c48_malloc_return

c48_malloc_too_small:
    pop de
c48_malloc_next:
    ld hl,(c48_heap_scan)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(c48_heap_scan)
    add hl,de
    ld (c48_heap_scan),hl
    jr c48_malloc_scan

c48_malloc_return:
    ld hl,(c48_heap_scan)
    ld de,C48_HEAP_HEADER_SIZE
    add hl,de
    xor a
    ret

c48_malloc_null:
    ld hl,0
    xor a
    ret

; free(NULL) is a no-op. Only exact live block payload pointers are accepted.
free:
    ld a,h
    or l
    ret z
    ld a,(c48_heap_ready)
    or a
    jr nz,c48_free_ready
    push hl
    call c48_heap_init_linker
    pop hl
c48_free_ready:
    ld de,C48_HEAP_HEADER_SIZE
    or a
    sbc hl,de
    ret c
    ld (c48_heap_scan),hl
    ld de,(c48_heap_start_ptr)
    or a
    sbc hl,de
    ret c
    ld hl,(c48_heap_scan)
    ld de,(c48_heap_end_ptr)
    or a
    sbc hl,de
    ret nc

    ld hl,(c48_heap_start_ptr)
    ld (c48_heap_prev),hl
c48_free_find:
    ld de,(c48_heap_end_ptr)
    or a
    sbc hl,de
    ret nc
    ld hl,(c48_heap_prev)
    ld de,(c48_heap_scan)
    or a
    sbc hl,de
    jr z,c48_free_found
    ld hl,(c48_heap_prev)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld a,d
    or e
    ret z
    ld hl,(c48_heap_prev)
    add hl,de
    ld (c48_heap_prev),hl
    jr c48_free_find

c48_free_found:
    ld hl,(c48_heap_scan)
    inc hl
    inc hl
    ld a,(hl)
    cp C48_HEAP_USED
    ret nz
    ld (hl),C48_HEAP_FREE

c48_free_merge_next:
    ld hl,(c48_heap_scan)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(c48_heap_scan)
    add hl,de
    ld bc,(c48_heap_end_ptr)
    push hl
    or a
    sbc hl,bc
    pop hl
    jr nc,c48_free_merge_prev
    inc hl
    inc hl
    ld a,(hl)
    cp C48_HEAP_FREE
    jr nz,c48_free_merge_prev
    dec hl
    dec hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    ld hl,(c48_heap_scan)
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl
    add hl,bc
    ex de,hl
    ld hl,(c48_heap_scan)
    ld (hl),e
    inc hl
    ld (hl),d
    jr c48_free_merge_next

c48_free_merge_prev:
    ld hl,(c48_heap_start_ptr)
    ld de,(c48_heap_scan)
    or a
    sbc hl,de
    ret z
    ld hl,(c48_heap_start_ptr)
c48_free_prev_loop:
    ld (c48_heap_prev),hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(c48_heap_prev)
    add hl,de
    ld bc,(c48_heap_scan)
    push hl
    or a
    sbc hl,bc
    pop hl
    jr z,c48_free_prev_found
    jr c,c48_free_prev_loop
    ret

c48_free_prev_found:
    ld hl,(c48_heap_prev)
    inc hl
    inc hl
    ld a,(hl)
    cp C48_HEAP_FREE
    ret nz
    dec hl
    dec hl
    ld e,(hl)
    inc hl
    ld d,(hl)
    ld hl,(c48_heap_scan)
    ld c,(hl)
    inc hl
    ld b,(hl)
    ex de,hl
    add hl,bc
    ex de,hl
    ld hl,(c48_heap_prev)
    ld (hl),e
    inc hl
    ld (hl),d
    ret
    ENDM
