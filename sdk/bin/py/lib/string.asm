; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48 string and memory calls. NUL is still the bouncer. (ZX-UX SDK)
        section text
        global _strlen,_strcmp,_strcpy,_strncpy,_memcpy,_memmove,_memchr,_memset
; _strlen: 12 bytes. HL -> NUL string; return length in HL. Zero has the last word.
_strlen:
        xor a
        ld b,a
        ld c,a
        ld d,h
        ld e,l
        cpir
        or a
        sbc hl,de
        dec hl
        ret
; _strcmp: 26 bytes. Compare two strings, return -1/0/1. Alphabetical squabble.
_strcmp:
        pop bc
        pop de                  ; a
        push bc
.l:     ld a,(de)
        cp (hl)
        j nz,.d
        or a
        j z,.eq
        inc de
        inc hl
        j .l
.eq:    ld hl,0
        ret
.d:     ld hl,1
        ret nc
        ld hl,-1
        ret
; _strcpy: 13 bytes. Copy through NUL; return destination pointer. No luggage left.
_strcpy:
        pop bc
        pop de
        push bc
        push de
.l:     ld a,(hl)
        ld (de),a
        inc hl
        inc de
        or a
        j nz,.l
        pop hl
        ret
; _strncpy: 33 bytes. Copy at most n bytes and NUL-pad; full input may lack NUL. Buyer beware.
_strncpy:
        ld b,h
        ld c,l                  ; BC = n
        pop hl
        pop de                  ; s
        ex (sp),hl              ; HL = d, ret on stack
        push hl
        ex de,hl                ; HL = s, DE = d
.l:     ld a,b
        or c
        j z,.x
        ld a,(hl)
        ld (de),a
        inc de
        dec bc
        or a
        j z,.z
        inc hl
        j .l
.z:     ld a,b                  ; pad with NULs
        or c
        j z,.x
        xor a
        ld (de),a
        inc de
        dec bc
        j .z
.x:     pop hl
        ret
; _memcpy/_memmove: 32 bytes, same entry. Overlap-safe copy; return destination. No self-collision.
_memcpy:
_memmove:
        ld b,h
        ld c,l
        pop hl
        pop de                  ; s
        ex (sp),hl              ; HL = d
        push hl
        ld a,b
        or c
        j z,.x
        ex de,hl                ; HL = s, DE = d
        push hl
        or a
        sbc hl,de
        pop hl
        j c,.back              ; s < d: copy from the end
        ldir
        j .x
.back:  add hl,bc
        dec hl
        ex de,hl
        add hl,bc
        dec hl
        ex de,hl
        lddr
.x:     pop hl
        ret
; _memchr: 20 bytes. Scan n bytes for c; return its address or NULL. Wanted poster included.
_memchr:
        ld b,h
        ld c,l
        pop hl
        pop de                  ; c
        ex (sp),hl              ; HL = p
        ld a,b
        or c
        j z,.no
        ld a,e
        cpir
        j nz,.no
        dec hl
        ret
.no:    ld hl,0
        ret
; _memset: 18 bytes. Fill n bytes with c; return p. Leave no gaps.
_memset:
        ld b,h
        ld c,l
        pop hl
        pop de                  ; c
        ex (sp),hl              ; HL = p
        ld a,b
        or c
        ret z
        push hl
.l:     ld (hl),e
        inc hl
        dec bc
        ld a,b
        or c
        j nz,.l
        pop hl
        ret
