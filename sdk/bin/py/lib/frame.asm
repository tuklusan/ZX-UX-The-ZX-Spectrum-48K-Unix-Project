; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48 recursive frames: call @enter, DW local bytes, then exit via @leaveK. (ZX-UX SDK)
; IX holds the frame; the final argument sits at IX-2. The stack pays for recursion.
        section text
        global @enter,@leave,@leave0,@leave1,@leave2,@leave3
; @enter: 39 bytes. Allocate locals, leave 170 bytes for kernel/IRQ, jump past DW.
@enter: pop de
        push ix
        ld ix,0
        add ix,sp
        push hl
        ex de,hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld b,h
        ld c,l
        ld hl,0
        add hl,sp
        or a
        sbc hl,de
        push hl
        ld de,@end+170          ; keep 170 bytes for the kernel and interrupts
        or a
        sbc hl,de
        pop hl
        jp c,@noret             ; stack overflow: end the program (status 1)
        ld sp,hl
        ld h,b
        ld l,c
        jp (hl)
; @leave0: 5 bytes. Restore IX and return; no stacked arguments to evict.
@leave0:
        ld sp,ix
        pop ix
        ret
; @leave1: 4 bytes plus @leave. Remove one pushed argument.
@leave1:
        ld a,1
        j @leave
; @leave2: 4 bytes plus @leave. Remove two pushed arguments.
@leave2:
        ld a,2
        j @leave
; @leave3: 2 bytes plus @leave. Remove three pushed arguments.
@leave3:
        ld a,3
; @leave: 11-byte shared tail. A = stacked argument count; unwind and return.
@leave: ld sp,ix
        pop ix
        pop de
.l:     pop bc
        dec a
        j nz,.l
        push de
        ret
