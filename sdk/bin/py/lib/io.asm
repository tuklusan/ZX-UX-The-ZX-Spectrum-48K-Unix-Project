; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48 file calls. Errors return FFFFh and set errno. The kernel keeps the receipts. (ZX-UX SDK)
SYS     equ 6003h
        section text
        global _open,_close,_read,_seek
; _open: 9 bytes. Open path with mode 0/1/2; HL gets the handle. Tickets, please.
_open:  pop bc
        pop de
        push bc
        ex de,hl                ; HL = path, DE = mode
        ld a,5
        jp @sys
; _close: 5 bytes. Close handle HL; return 0 or -1. Door shut.
_close: ld a,6
        jp @sys0                ; (the kernel leaves HL as it was)
; _read: 10 bytes. Read (handle, buffer, count); HL = bytes or -1. Short reads happen.
_read:  ld b,h                  ; BC = count
        ld c,l
        pop hl
        pop de                  ; DE = buffer
        ex (sp),hl              ; HL = handle
        ld a,3
        jp @sys
; _seek: 12 bytes. Seek from start: (handle, position) -> HL offset or -1. No teleporting.
_seek:  ex de,hl                ; DE = position
        pop bc
        pop hl                  ; HL = handle
        push bc
        ld bc,0
        ld a,19
        jp @sys
