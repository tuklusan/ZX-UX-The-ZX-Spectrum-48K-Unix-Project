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
; Reviewed fast-loader source promoted from the preserved portable package.
        org 0x5E4F

TEXT_BUFFER     equ 0xBEEF     ; build.py patches this to the BASIC-resident 768-byte array
CHARS_SYSVAR    equ 23606
CHAN_OPEN       equ 0x1601
BORDCR          equ 23624

; The original loader begins with CALL ROM_CLS. build.py redirects that
; call here. BASIC has already done its initial CLS/PRINT setup; from this
; point the turbo loader owns the screen, including clearing the bitmap,
; establishing attributes, and reopening channel 2 for ROM error messages.
screen_init:
        ; The ROM treats the bottom display area specially.  Initialize the
        ; complete 32x24 attribute map directly so rows 23/24 cannot retain
        ; the lower-screen attributes.  Keep this entry exactly six bytes so
        ; DISPLAY_HOOK_ADDR remains HOOK_ADDR+6.
        call init_screen
        ret
        nop
        nop

hook:
        ; Replace original POP HL / POP DE / LD A,H sequence while
        ; preserving the CALL return address beneath those two words.
        pop bc
        pop hl
        pop de
        push bc
        push hl
        push de

        ld a,(lines_left)
        or a
        jr z,restore

        ld a,32
        ld (chars_left),a

        ; DE = first bitmap byte of the current 8-pixel character row.
        ld a,(line_index)
        add a,a
        ld e,a
        ld d,0
        ld hl,screen_rows
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)

        ld hl,(text_ptr)

char_loop:
        ld a,(hl)
        inc hl
        push hl

        ; Default Spectrum CHARS points 256 bytes before the 8-byte
        ; character glyphs, so CHARS + 8*code addresses the glyph.
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld bc,(CHARS_SYSVAR)
        add hl,bc

        push de
        ld b,8
glyph_loop:
        ld a,(hl)
        ld (de),a
        inc hl
        inc d
        djnz glyph_loop
        pop de
        inc e

        pop hl
        ld a,(chars_left)
        dec a
        ld (chars_left),a
        jr nz,char_loop

        ld (text_ptr),hl
        ld a,(line_index)
        inc a
        ld (line_index),a
        ld a,(lines_left)
        dec a
        ld (lines_left),a
        jr nz,restore

        ; Last row: tape payload is complete. The product TZX deliberately
        ; uses the loader's ordinary 0x0100 continuation for its final block
        ; so this 24th callback runs. Tail-dispatch through final_hold: render
        ; is already complete, then beep exactly once and hand off to 0xE003.
        jp final_hold

restore:
        pop de
        pop hl
        ld a,h
        ret

final_hold:
        ; Keep this block exactly 14 bytes so init_screen remains at 0x5EC2.
        ; The beep follows the data tables and may move when init_screen grows.
        ; The kernel entry is permanent and resets SP, so no loader return is
        ; required after the final callback.
        call startup_beep
        jp 0xE003
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        nop

init_screen:
        ; This replaces the final BASIC CLS. Clear the complete 6144-byte
        ; bitmap so the turbo loader owns a clean screen from this point on.
        ld hl,0x4000
        ld de,0x4001
        ld bc,6143
        xor a
        ld (hl),a
        ldir

        ; White INK (7), black PAPER (0), no BRIGHT/FLASH across all 768 cells.
        ld hl,0x5800
        ld de,0x5801
        ld bc,767
        ld (hl),0x07
        ldir

        ; Spectrum colors at BASIC row 21, columns 28-31. The text in these
        ; cells is spaces, so the PAPER colors remain visible during loading.
        ld hl,0x5ABC
        ld (hl),0x17       ; PAPER 2 red, INK 7
        inc hl
        ld (hl),0x37       ; PAPER 6 yellow, INK 7
        inc hl
        ld (hl),0x27       ; PAPER 4 green, INK 7
        inc hl
        ld (hl),0x2F       ; PAPER 5 cyan, INK 7

        ; BORDCR is also the ROM's attribute source for the lower two
        ; screen rows. Force white INK / black PAPER there as well.
        ld a,0x07
        ld (BORDCR),a

        ld a,2
        call CHAN_OPEN
        ret

text_ptr:
        dw TEXT_BUFFER
lines_left:
        db 24
line_index:
        db 0
chars_left:
        db 0

screen_rows:
        dw 0x4000,0x4020,0x4040,0x4060,0x4080,0x40A0,0x40C0,0x40E0
        dw 0x4800,0x4820,0x4840,0x4860,0x4880,0x48A0,0x48C0,0x48E0
        dw 0x5000,0x5020,0x5040,0x5060,0x5080,0x50A0,0x50C0,0x50E0

startup_beep:
        ; One audible startup beep. Spectrum ROM BEEPER uses DE as the
        ; cycle count and HL as the integer period parameter. DE=224 and
        ; HL=458 target 896 Hz for 250 ms on the nominal 3.5 MHz machine.
        ; Preserve IX because ROM BEEPER uses it internally.
        push ix
        ld de,224
        ld hl,458
        call 0x03B5
        di
        pop ix
        ret
