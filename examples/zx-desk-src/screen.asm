; Original ZXDesk screen-addressing routines from src/zxdesk.asm.
; Damian Cooper, MIT; see zxdesk/NOTICE.txt.
; ZX-UX holds screen ownership. No private ROM/IM2 or fixed code origin.
        section text
        global CalcScr
        global RowAddr
        global ScrDown
        global AddrAt
        global DrawEdges
        extern PxRow
        global FillRowSolid

SCRROWS equ 192
SCRCOLS equ 32

; in: A = pixel row, out: DE = screen address of column 0
CalcScr:
                ld      d,a
                and     $07
                ld      e,a
                ld      a,d
                and     $38
                rlca
                rlca
                ld      c,a
                ld      a,d
                and     $c0
                rrca
                rrca
                rrca
                or      e
                or      $40
                ld      d,a
                ld      e,c
                ret

; in: A = pixel row, out: HL = screen address of column 0
RowAddr:
                push    af
                push    bc
                call    CalcScr
                ex      de,hl
                pop     bc
                pop     af
                ret

; Step HL down one pixel row. Touches only A and HL.
ScrDown:
                inc     h
                ld      a,h
                and     7
                ret     nz
                ld      a,l
                add     a,SCRCOLS
                ld      l,a
                ret     c
                ld      a,h
                sub     8
                ld      h,a
                ret

; in: A = pixel row, C = byte column, out: HL = screen address
AddrAt:
                call    RowAddr
                ld      e,c
                ld      d,0
                add     hl,de
                ret

; Original ZXDesk screen row surface primitives.
; in: A = pixel row
FillRowSolid:
                call    RowAddr
                ld      b,SCRCOLS
FrsLoop:
                ld      (hl),$FF
                inc     l
                djnz    FrsLoop
                ret

; in: A = pixel row

; Border sides of a box. PxRow = first pixel row, B = rows, C = left screen byte,
; E = width - 1: set the left pixel (bit 7 of byte C) and the right pixel (bit 0
; of byte C+E) on each of the rows.
DrawEdges:
                push    bc
                push    de
                ld      a,(PxRow)
                call    AddrAt
                pop     de
                ld      a,(hl)
                or      $80
                ld      (hl),a
                ld      d,0
                add     hl,de
                ld      a,(hl)
                or      $01
                ld      (hl),a
                ld      hl,PxRow
                inc     (hl)
                pop     bc
                djnz    DrawEdges
                ret
