; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  device drivers  (u6 rtty/wtty/rmem/wmem, u7 otty/ctty, u9 getc/putc)
;   1 /dev/tty   ROM keys, our 64 x 24 text screen in a 4 x 8 font
;   2 /dev/mem   core memory
;   5 /dev/tap   cassette tape (ROM SA-BYTES / LD-BYTES)
; =====================================================================

; devread: 14 bytes. IX+30 picks tty, RAM or tape input. Three doors, one handle.
devread:
        ld a,(ix+30)
        cp DEV_TTY
        jp z,ttread
        cp DEV_MEM
        jr z,memrd
        jr taprd

; devwrite: 14 bytes. IX+30 picks tty, RAM or tape output. Same doors, other way.
devwrite:
        ld a,(ix+30)
        cp DEV_TTY
        jp z,ttwrite
        cp DEV_MEM
        jr z,memwr
        jr tapwr

; memrd: 9 bytes. Read RAM directly. The address had better be right.
memrd:  ld hl,(u_off)
        ld de,(u_base)
        jr memwr.xj0_0  
; memwr: 19 bytes. Write RAM directly. No second chance for bad pointers.
memwr:  ld de,(u_off)
        ld hl,(u_base)
.xj0_0:
        ld bc,(u_count)
        ld a,b
        or c
        ret z
        ldir
        jp ttwrite.xj1_13  

; ---------------------------------------------------------------------
; tape - one write = one block, one read = one block. A transfer of exactly 17 bytes is a standard Spectrum
; header (flag 00), any other size a data block (flag FF). Tape never offered a fast lane.
; ---------------------------------------------------------------------
; tapwr: 9 bytes. Write one tape block. The motor sets the pace.
tapwr:
        call tapset
        call rom_save_short
        scf
        jr tapend
; rom_save_short: 10 bytes. Use the verified 48K ROM SA-BYTES shortcut at 0C98h, not the 1F80h header pilot.
; The build checks the ROM fingerprint. Wrong ROM, wrong landing.
rom_save_short:
        ld hl,053Fh             ; normal SA-BYTES cleanup return. One extra byte can ruin everyone’s day.
        push hl
        ld hl,0C98h             ; shorter but standard ROM pilot. Tape remains gloriously allergic to
                                ; shortcuts.
        jp 04D0h                ; resumes the unmodified ROM SAVE routine. 1982 called; it wants its
                                ; loading time back.

; taprd: 7 bytes. Read one tape block. No fast-forward button.
taprd:
        call tapset
        scf
        call ROM_LDBYTES
; tapend: 38 bytes. NC = tape failure, including ROM errors and BREAK; restore state and time. The reel is
; picky.
tapend: ld sp,(tapsp)           ; drop the error trap (flags kept). The exit is marked for a reason.
        ld hl,kerrsp
        ld (SV_ERRSP),hl
        di
        ld a,250                ; Give this tape user five quiet seconds. Preemption can wait.
        ld (tapq),a             ; Count down the hold. The next tape block will not wait.
        ld a,(cur)              ; Remember the slot that owns the hold. No passing the baton.
        ld (tapqp),a
        ld a,0
        ld (tapbusy),a
        call c,tclk             ; the time it took onto the clock (CF kept). Even 50 Hz can feel impatient.
        ei
        jp c,ttwrite.xj0_33  
        ld a,EIO
        scf
        ret

; tapset: 41 bytes. IX = buffer, DE = count, A = block flag; prepare the ROM tape call. No fast lane.
tapset: ld a,0FFh
        ld (tapbusy),a
        ld ix,(u_base)
        ld de,(u_count)
        ld a,d
        or a
        ld a,0FFh
        jr nz,.s
        ld a,e
        cp 17
        ld a,0FFh
        jr nz,.s
        xor a
.s:     pop hl                  ; Restore the ROM entry. BREAK still needs a safe way home.
        ld (tapsp),sp           ; Save the caller stack for an orderly tape-error escape.
        ld bc,rom_error         ; Point ROM errors at our trap. Lost returns are expensive.
        push bc                 ; Put that trap on the stack before the ROM wakes interrupts.
        ld (SV_ERRSP),sp        ; ROM RST 8 will use this stack. Leave it actual room.
        jp (hl)                 ; Enter the ROM. The trap is packed and ready.

tapbusy equ MEMBOT+5
tapsp   equ MEMBOT+6

; ---------------------------------------------------------------------
; tty input - ISR side. The keyboard has no rewind switch.
; ---------------------------------------------------------------------
; ttrawin: 89 bytes. A = key code from ROM KEY-INPUT (ISR). One keystroke, one chance to behave.
ttrawin:
        cp 0Dh                  ; ENTER.
        jr z,.st
        cp 0Ch                  ; DELETE.
        jr z,.st
        cp 07h                  ; EDIT → EOT (ESC in vi).
        jr z,.st
        cp 08h                  ; cursor keys 8..11 (raw mode).
        jr c,.ign
        cp 0Ch
        jr c,.st
.ign:   cp 20h
        ret c
        cp 80h
        jr c,.st
        ld hl,toktab
        ld b,a
.t:     ld a,(hl)
        or a
        ret z
        inc hl
        cp b
        ld a,(hl)
        inc hl
        jr nz,.t
.st:    ld b,a
        ld a,(ttyhd)
        ld c,a
        inc a
        and 31
        ld hl,ttytl
        cp (hl)
        ret z                   ; ring full.
        ld (ttyhd),a
        ld hl,ttyring
        ld a,c
        call addhla
        ld (hl),b
; key click. The keyboard does not send an apology.
        ld a,(SV_BORDCR)
        rrca
        rrca
        rrca
        and 7
        or 010h
        out (0FEh),a
        ld b,40
.c:     djnz .c
        and 7
        out (0FEh),a
        ld a,WC_TTY
        jp kwakeup

; ttintr: 50 bytes. BREAK signals every live process (UNIX v1 DEL). The key does not negotiate.
ttintr:
        ld b,0
.l:     ld a,b
        ld l,a                  ; p_stat is page aligned (KV).
        ld h,p_stat >> 8
        ld a,(hl)
        or a
        jr z,.n
        cp SZOMB
        jr z,.n
        ld a,b
        ld hl,p_sig
        call addhla
        ld a,(hl)
        or a
        jr nz,.n
        ld (hl),1
.n:     call nxslot
        jr c,.l
        call ttyflush           ; discard stale keys after BREAK. The input line is not a parking lot.
        ld a,WC_TTY
        call kwakeup
        ld a,WC_WAIT
        call kwakeup
        ld a,WC_TIME
        jp kwakeup

; ttyflush: 7 bytes. Flush raw keys after a foreground child; leave background readers alone. No stale votes.
ttyflush:
        ld a,(ttyhd)
        ld (ttytl),a
        ret

; ---------------------------------------------------------------------
; tty input - process side (canonical line discipline, echo) DELETE erases, ENTER ends the line, EDIT = EOT
; (^D), BREAK = intr. BREAK is a key, not a polite suggestion.
; ---------------------------------------------------------------------
; ttgetc: 55 bytes. Pull one character from the line. No queue jumping.
ttgetc:                         ; → A = key; CF if interrupted (ignored). The keyboard insists on being
                                ; heard.
.l:     di
        call sigck
        jr c,.int
        ld a,(ttytl)
        ld hl,ttyhd
        cp (hl)
        jr nz,.have
        call curon
        ld a,WC_TTY
        call ksleep
        ei
        jr .l
.have:  ld hl,ttyring
        call addhla
        ld b,(hl)
        ld a,(ttytl)
        inc a
        and 31
        ld (ttytl),a
        ei
        call curoff
        ld a,b
        or a
        ret
.int:   ei
        call curoff
        scf
        ret

; ttread: 244 bytes. Read the terminal line. The keyboard gets a turn.
ttread:
        ld a,(ttymode)
        and TT_RAW
        jr z,.can
        call ttgetc
        jp c,.int
        ld hl,(u_base)            ; raw: keys untranslated (ENTER = 13). No key gets to jump the queue.
        ld (hl),a
        ld hl,1
        jp iadv
.can:   ld a,(ttyrdy)
        or a
        jr nz,.copy
.col:   call ttgetc
        jp c,.int
        cp 0Dh
        jr z,.nl
        cp 0Ch
        jr z,.del
        cp 07h
        jr z,.eot
        cp 0Ch
        jr c,.col               ; cursor keys: raw mode only.
        ld b,a
        ld a,(ttycnt)
        cp TTYBSZ-1
        jr nc,.col
        ld hl,TTYBUF
        call addhla
        ld (hl),b
        ld hl,ttycnt
        inc (hl)
        ld a,(ttymode)
        and TT_ECHO
        jr z,.col
        ld a,b
        jr ttread.xj0_42  
.del:   ld a,(ttycnt)
        or a
        jr z,.col
        dec a
        ld (ttycnt),a
        ld a,(ttymode)
        and TT_ECHO
        jr z,.col
        ld a,8
        call kputc
        ld a,' '
        call kputc
        ld a,8
.xj0_42:
        call kputc
        jr .col
.nl:    ld a,(ttycnt)
        ld hl,TTYBUF
        call addhla
        ld (hl),10
        ld hl,ttycnt
        inc (hl)
        ld a,10
        call kputc
        jr .done
.eot:   ld a,(ttycnt)
        or a
        ret z                   ; EOF: nread = 0.
.done:  ld a,1
        ld (ttyrdy),a
.copy:  ld a,(ttypos)
        ld b,a
        ld a,(ttycnt)
        sub b
        ld l,a
        ld h,0
        ld de,(u_count)
        call minhlde
        ld (ktmp),hl
        ld a,(ttypos)
        add a,l
        ld (ttypos),a
        ld a,b
        ld hl,TTYBUF
        call addhla
        ld de,(u_base)
        ld bc,(ktmp)
        ld a,b
        or c
        jr z,.c1
        ldir
.c1:    ld a,(ttypos)
        ld hl,ttycnt
        cp (hl)
        jr c,.c2
        xor a
        ld (ttyrdy),a
        ld (ttycnt),a
        ld (ttypos),a
.xj0_34:
.c2:    ld hl,(ktmp)
        jp iadv
.int:   xor a
        ld (ttyrdy),a
        ld (ttycnt),a
        ld (ttypos),a
        ld a,(ttymode)
        and TT_RAW
        ld a,10
        call z,kputc
        ld a,EINTR
        scf
        ret

; ---------------------------------------------------------------------
; tty output. The keys have the last word.
; ---------------------------------------------------------------------
; ttwrite: 29 bytes. Put text on screen. Pixels have a tight schedule.
ttwrite:
        ld hl,(u_base)
        ld bc,(u_count)
.l:     ld a,b
        or c
        jr z,.d
        ld a,(hl)
        push hl
        push bc
        call kputc
        pop bc
        pop hl
        inc hl
        dec bc
        jr .l
.xj0_33:
.xj1_13:
.d:     ld hl,(u_count)
        jp iadv

; kputs: 11 bytes. Print a string. The screen charges by the character.
kputs:  ld a,(hl)
        or a
        ret z
        push hl
        call kputc
        pop hl
        inc hl
        jr kputs

; ---------------------------------------------------------------------
;  64 x 24 text screen in a 4 x 8 font (rows 0-22 text, row 23 status)
;  No ROM printing: every character is drawn into the display file.
;  The ULA's interleaved layout does most of the work - the 8 pixel
;  lines of a character cell lie 256 bytes apart, so INC H steps one
;  line down - and two characters share each byte, one per nibble.
; The display will notice if we cheat.
; ---------------------------------------------------------------------
TROWS   equ 23

; kputc: 182 bytes. A = character or AT/INVERSE control; print through the 4x8 screen path. No ROM printer.
kputc:
        push hl
        push de
        push bc
        push af
        call cstrip             ; silent while this process owns the screen. The cursor has places to be.
        jr nz,.q
        ld hl,cbusy             ; the blinking cursor keeps off while. The screen has no spare row for our
                                ; feelings.
        ld (hl),1               ; the screen changes.
        call cxoff
        pop af
        ld hl,ttat
        inc (hl)
        dec (hl)
        jr nz,.prm
        cp 16h                  ; AT row,col.
        jr z,.ctl2
        cp 14h                  ; INVERSE n.
        jr z,.ctl1
        cp 10
        jr z,.nl
        cp 9
        jr z,.tab
        cp 7
        jr z,.bel
        cp 8
        jr z,.bs
        cp 12
        jr z,.ff
        cp 7Fh+1                ; 20h-7Fh printable.
        jr nc,.x
        cp 20h
        call nc,tput
.x:     xor a
        ld (cbusy),a
.xj0_56:
        pop bc
        pop de
        pop hl
        ret
.q:     pop af
        jr .xj0_56
.nl:    call tnl
        jr .x
.bs:    ld hl,tcol              ; backspace.
        ld a,(hl)
        or a
        jr z,.x
        dec (hl)
        jr .x
.tab:   ld a,' '
        call tput
        ld a,(tcol)
        and 7
        jr nz,.tab
        jr .x
.bel:   ld hl,0300h             ; ROM BEEPER: ~ 560 Hz, 0.1 s.
        ld de,056h
        push ix
        call ROM_BEEPER
        pop ix
        ei
        jr .x
.ff:    call kcls
        jr .x
.ctl2:  ld (hl),2
        jr .ctl
.ctl1:  ld (hl),1
.ctl:   ld (ttcc),a
        jr .x
.prm:   dec (hl)                ; a parameter byte.
        jr z,.pend
        ld (ttp1),a
        jr .x
.pend:  ld c,a
        ld a,(ttcc)
        cp 14h
        jr nz,.pat
        ld a,c                  ; INVERSE 0/1.
        rrca
        sbc a,a
        and 0F0h
        ld (tinv),a
        jr .x
.pat:   ld a,(ttp1)             ; AT: text rows and columns only.
        cp TROWS
        jr nc,.x
        ld b,a
        ld a,c
        cp 64
        jr nc,.x
        ld (tcol),a
        ld a,b
        ld (trow),a
        jr .x

; tput: 19 bytes. A = printable char; draw and advance, wrapping after column 63. No spare row.
tput:   ld de,(trow)            ; E = row, D = column.
        ld hl,tinv
        ld b,(hl)
        call glyph
        ld hl,tcol
        inc (hl)
        ld a,(hl)
        cp 64
        ret c
; tnl: 14 bytes. Advance the text row, scrolling when needed. Twenty-three rows are the whole deal.
tnl:    xor a
        ld (tcol),a
        ld hl,trow
        ld a,(hl)
        cp TROWS-1
        jr nc,tscrl
        inc (hl)
        ret

; tscrl: 39 bytes. Scroll text rows ttop+1..22 and clear row 22. Pixels get new seats.
tscrl:  ld a,(ttop)
.r:     push af
        inc a
        call rowadr             ; source row.
        pop af
        push af
        push hl
        call rowadr
        ex de,hl                ; destination row.
        pop hl
        ld b,8
.p:     push bc                 ; Copy 32 pixels bytes per scanline.
        push hl                 ; INC H/D moves down the ULA display.
        push de
        ld bc,32
        ldir
        pop de
        pop hl
        pop bc
        inc h
        inc d
        djnz .p
        pop af
        inc a
        cp TROWS-1
        jr c,.r
; clrrow: 18 bytes. A = row → clear its pixels. No rag required.
clrrow: call rowadr
        ld c,8
.c:     push hl
        xor a
        ld b,32
        call zfill
        pop hl
        inc h
        dec c
        jr nz,.c
        ret

; rowadr: 3 bytes. A = row → HL = its first display byte. The screen is not a flat map.
rowadr: ld e,a
        ld d,0
; scradr: 25 bytes. E = row, D = col (0-63); HL = first pixel byte, C = nibble mask. Spectrum rows misbehave.
scradr: ld a,e
        and 18h
        or 40h
        ld h,a
        ld a,e
        rrca
        rrca
        rrca
        and 0E0h
        ld l,a
        ld a,d
        srl a
        ld c,0F0h
        jr nc,.e
        ld c,0Fh
.e:     or l
        ld l,a
        ret

; glyph: 60 bytes. A = char, E/D = row/col, B = inverse mask; draw paired 4x8 font rows. Tiny art.
glyph:  push af
        call scradr
        pop af
        sub 20h
        cp 60h                  ; not printable: a space.
        jr c,.ok
        xor a
.ok:    push hl
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        ld de,FONT
        add hl,de
        ex de,hl
        pop hl
.l:     ld a,(de)               ; upper row of the pair.
        call .row
        ld a,(de)               ; lower row.
        rlca
        rlca
        rlca
        rlca
        call .row
        inc de
        ld a,e                  ; the font is 4-aligned: 4 bytes a glyph.
        and 3
        jr nz,.l
        ret
.row:   and 0F0h
        xor b
        bit 0,c
        jr z,.r1
        rrca                    ; odd column: the low nibble.
        rrca
        rrca
        rrca
.r1:    xor (hl)                ; replace just this column's nibble.
        and c
        xor (hl)
        ld (hl),a
        inc h                   ; the ULA's next pixel line.
        ret

; kcls: 24 bytes. Clear the console. Fresh slate, same tiny screen.
kcls:   ld hl,4000h
        ld bc,1800h
        call zero               ; Clear the bitmap, not the attribute bytes.
        xor a                   ; Keep the screen colors already in RAM.
        ld (trow),a
        ld (tcol),a
        ld (cdrawn),a
        inc a
.xj0_55:
.xj1_25:
.xj0_0:
        ld (stdirty),a
        ret

; ---------------------------------------------------------------------
;  cursor: a 4 x 8 block XORed into the display file at the print
;  position, blinking from the clock interrupt while a process waits
;  for the keyboard.  It is taken off before anything is drawn (cbusy
;  holds the blink off meanwhile), so it never leaves a mark.
; The key buffer is no bottomless bag.
; ---------------------------------------------------------------------
; cxor: 23 bytes. XOR the cursor block at the print position. Blinking has to come from somewhere.
cxor:   ld de,(trow)
        call scradr
        ld b,8
.l:     ld a,(hl)
        xor c
        ld (hl),a
        inc h
        djnz .l
        ld hl,cdrawn
        ld a,(hl)
        xor 1
        ld (hl),a
        ret
; cxoff: 7 bytes. Remove the cursor from the display. End of its solo.
cxoff:  ld a,(cdrawn)
        or a
        ret z
        jr cxor
; curon: 20 bytes. With interrupts off, show the cursor while waiting for input. Tiny flashing star.
curon:  call cstrip              ; this process owns the screen: no cursor.
        ret nz
        ld a,1
        ld (cvis),a
        xor a
        ld (cblink),a
        ld a,(cdrawn)
        or a
        ret nz
        jr cxor
; curoff: 12 bytes. A key arrived; remove the cursor. No encore.
curoff: push bc
        di
        xor a
        ld (cvis),a
        call cxoff
        ei
        pop bc
        ret
; cblnk: 21 bytes. On the frame interrupt, toggle the cursor every 16 frames. Time to blink.
cblnk:  ld hl,cblink
        inc (hl)
        ld a,(hl)
        and 15
        ret nz
        ld a,(cbusy)
        or a
        ret nz
        ld a,(cvis)
        or a
        jr nz,cxor
        jr cxoff

; ---------------------------------------------------------------------
; stty / gtty (u1) HL = fd, DE = 3 word buffer (speeds, mode). Every byte has to pay rent.
; ---------------------------------------------------------------------
; sysstty: 33 bytes. Set terminal rules. The keys follow orders.
sysstty:
        push de
        call getf
        pop de
        jp c,syserr
        call ckty
        jp c,syserr
        ex de,hl
        inc hl
        inc hl
        inc hl
        inc hl
        ld a,(hl)
        rla                     ; TT_FLUSH bit 7 requests raw ring drain.
        call c,ttyflush
        ld a,(hl)
        and TT_RAW+TT_ECHO
        ld (ttymode),a
        jp sysok
; sysgtty: 31 bytes. Read terminal rules. Nobody likes surprises.
sysgtty:
        push de
        call getf
        pop de
        jp c,syserr
        call ckty
        jp c,syserr
        ex de,hl
        xor a
        ld b,6
.z:     ld (hl),a
        inc hl
        djnz .z
        dec hl
        dec hl
        ld a,(ttymode)
        ld (hl),a
        jp sysok

; ckty: 10 bytes. HL = fsp entry → CF if it is not the terminal. Other devices need not apply.
ckty:   ld a,(hl)
        dec a
        inc hl
        or (hl)
        dec hl
        ret z
        ld a,ENOTTY
        scf
        ret
ENOTTY  equ 25

; low-memory scratch (the time of day, stdirty and kcon: kvars.inc; they were MEMBOT+0..4, which a
; program's BEEP uses). The clock keeps counting while we argue.
trow    equ MEMBOT+8            ; print position: row (trow, tcol adjacent).
tcol    equ MEMBOT+9            ; column 0-63.
tinv    equ MEMBOT+10           ; F0h: INVERSE 1.
cvis    equ MEMBOT+11           ; cursor wanted (waiting for a key). One keystroke, one chance to behave.
cdrawn  equ MEMBOT+12           ; cursor is on the screen.
cbusy   equ MEMBOT+13           ; screen being changed: no blinking.
cblink  equ MEMBOT+14           ; blink frame counter.
