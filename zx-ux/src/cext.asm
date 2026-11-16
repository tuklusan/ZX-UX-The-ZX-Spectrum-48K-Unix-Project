; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  C support calls (ZX-UX v1, for programs from the ZX-UX SDK)
;   38 ticks    HL = 50 Hz frame counter
;   39 screen   HL = 1: the caller owns the screen (no status line, no
;               cursor) -> HL = the 4x8 font; HL = 0: give it back
;  Floats and BEEP need no kernel help: a program calls the ROM's
;  calculator itself, interrupts off, with STKBOT/STKEND/MEM pointing
;  into its own memory and ERR_SP at its own error handler (the kernel
;  never uses the calculator).  See sdk/lib/float.asm.
; =====================================================================

; systicks: 9 bytes. Ask the frame clock. It never takes sick leave.
systicks:
        ld hl,(fticks)
        ld de,0
        jp sysok

; sysscreen: 33 bytes. Claim the screen (E = 0 for first owner); the console returns after the last release.
; Share the pixels, not the throne.
sysscreen:
        ld a,h
        or l
        jr z,.rel
        di
        xor a
        ld (cvis),a
        call cxoff              ; the cursor goes.
        ei
        call curbit
        ld hl,scrown
        ld e,(hl)               ; E = the owners before.
        or e
        ld (hl),a
        jr .ok
.rel:   call scrrel
.ok:    ld hl,FONT
        jp sysok

; curbit: 11 bytes. Return the bit for the running slot in A (slot 0 = 1). Four voters, no favorites.
curbit: ld a,(cur)
        ld b,a
        inc b
        xor a
        scf
.l:     rla
        djnz .l
        ret

; scrrel: 11 bytes. Release the current job's screen bit; the last owner restores the console. Shared rent.
scrrel: call curbit
        ld hl,scrown
        and (hl)
        ret z
        xor (hl)
        ld (hl),a
        ret nz

; scrfree: 44 bytes. Restore console rows and the white-on-black screen, then start on a new bottom row. No
; deposit.
scrfree:
        ld hl,ttop
        ld b,(hl)
        xor a
        ld (hl),a
        ld (scrown),a
        ld (cdrawn),a
        out (0FEh),a
        ld a,7                  ; ... and stays black (key click, beep): A stray key can still start a
                                ; riot.
        ld (SV_BORDCR),a        ; BORDCR as the ROM's BORDER 0 leaves it.
        ld a,TT_ECHO
        ld (ttymode),a
        ld hl,5800h
        call attr7
        inc b
        dec b
        ld a,TROWS-1
        ld (stdirty),a
        ret nz                  ; the console was at the bottom already.
        ld (trow),a
        jp tnl

; cstrip: 39 bytes. Z permits console output; NZ means a screen owner has it. Rows 21-22 and status 23 still
; work.
cstrip: call curbit
        ld hl,scrown
        and (hl)
        ret nz
        or (hl)
        ret z
        ld a,(ttop)
        or a
        jr nz,attr7.z
        ld a,21
        ld (ttop),a
        ld (stdirty),a
        ld hl,TROWS-1           ; row 22, column 0.
        ld (trow),hl
        call tscrl              ; clear rows 21 and 22.
        call tscrl
        ld hl,5800h+21*32       ; white on black, the status row too.
; attr7: 10 bytes. Fill attributes from HL onward with white on black; return A = 0, Z. Paint by numbers.
attr7:  ld (hl),7
        inc hl
        ld a,h
        cp 5Bh
        jr nz,attr7
.z:     xor a
        ret

