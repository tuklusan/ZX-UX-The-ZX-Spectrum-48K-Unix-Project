; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  vi - a small visual editor for the 64 x 23 text screen
;
;  command mode   h j k l / cursor keys   0 $   [n]G   x  dd  p  r c
;                 J (join)   i a A o O (insert)   /text   ZZ
;                 :w [file]  :q  :q!  :wq  :n (go to line n)
;  insert mode    type text, ENTER splits the line, DELETE erases,
;                 EDIT (CAPS SHIFT+1) is ESC
;  Rows 0-21 show text, row 22 is the status / command line.  The
;  screen is addressed with the Spectrum's AT control code.
; =====================================================================
VI_N    equ TV                  ; number of lines.
VI_L    equ TV+2                ; current line (1..N).
VI_C    equ TV+4                ; current column.
VI_TOP  equ TV+5                ; first line on the screen.
VI_LEFT equ TV+7                ; first column on the screen.
VI_END  equ TV+8                ; end of text.
VI_MOD  equ TV+10               ; modified.
VI_CNT  equ TV+11               ; count prefix.
VI_INS  equ TV+13               ; insert mode.
VI_RD   equ TV+14               ; full redraw needed.
VI_MSG  equ TV+15               ; message for the status line.
VI_FD   equ TV+17
VI_YL   equ TV+19               ; yanked line length (0 = none).
VI_FN   equ TV+20               ; 32 file name.
VI_ROW  equ TV+52               ; 68 output row.
VI_CMD  equ TV+120              ; 64 command line text.
VI_YANK equ R_BUF               ; 128 yanked line (vi reads no files through the buffered reader). Every
                                ; open file has a tab running.
VI_BUF  equ TV+184              ; text.
VI_LIM  equ CORETOP-750         ; keep 750 bytes for stack and arguments. This is not an all-you-can-push
                                ; buffet.
VROWS   equ 22

t_vi:   db 18h,6
        dw STKRES, VI_BUF-UDATA, vi_m
; vi_m: 56 bytes. Start the editor. One screen, lots of ambition.
vi_m:   pop hl
        call args
        ld hl,0                 ; BREAK does not kill the editor. The keys have the last word.
        call sc_intr
        ld a,TT_RAW
        call gstty
        ld hl,VI_BUF
        ld (VI_END),hl
        ld hl,1
        ld (VI_L),hl
        ld (VI_TOP),hl
        ld a,12
        call putc
        ld a,1
        call argn
        jr z,.lp
        ld de,VI_FN
        call strcpy
        call vload
.lp:    ld a,1
        ld (VI_RD),a
; vloop: 72 bytes. The editor keeps asking for another key.
vloop:  call vfix
        call vshow
        call vkey
        ld hl,vloop
        push hl
; count prefix. The low byte still matters.
        cp '1'
        jr c,.nd
        cp '9'+1
        jr c,.dig
.nd:    cp '0'
        jr nz,.nz
        ld hl,(VI_CNT)
        ld a,h
        or l
        ld a,'0'
        jr nz,.dig
.nz:    push af
        ld hl,(VI_CNT)
        ld (U_T),hl             ; count for this command.
        ld hl,0
        ld (VI_CNT),hl
        pop af
        ld hl,vitab
        jp tabjp
.dig:   sub '0'
        ld hl,(VI_CNT)
        ld d,h
        ld e,l
        add hl,hl
        add hl,hl
        add hl,de
        add hl,hl
        ld e,a
        ld d,0
        add hl,de
        ld (VI_CNT),hl
; vnop: 1 byte. Do nothing. One byte of pure restraint.
vnop:   ret

vitab:  db 'h'
        dw vleft
        db 8
        dw vleft
        db 'l'
        dw vright
        db 9
        dw vright
        db 'j'
        dw vdown
        db 10
        dw vdown
        db 13
        dw vdown
        db 'k'
        dw vup
        db 11
        dw vup
        db '0'
        dw vbol
        db '$'
        dw veol
        db 'G'
        dw vgoto
        db 'x'
        dw vdelc
        db 'd'
        dw vdd
        db 'p'
        dw vput
        db 'r'
        dw vrepl
        db 'J'
        dw vjoin
        db 'i'
        dw vins
        db 'a'
        dw vappend
        db 'A'
        dw vappe
        db 'o'
        dw vopen
        db 'O'
        dw vopenu
        db ':'
        dw vcolon
        db '/'
        dw vsearch
        db 'Z'
        dw vzz
        db 0                    ; unknown key: nothing.
        dw vnop

; ---- motions
; vleft: 8 bytes. One step left. The cursor can be stubborn.
vleft:  ld hl,VI_C
        ld a,(hl)
        or a
        ret z
        dec (hl)
        ret
; vright: 5 bytes. One step right. No teleportation included.
vright: ld hl,VI_C
        inc (hl)
        ret
; vdown: 14 bytes. Move down a line. The cursor likes a map.
vdown:  ld hl,(VI_L)
        ld de,(VI_N)
        call cphl
        ret nc
        inc hl
        jr vup.xj0_51  
; vup: 10 bytes. Move up a line. Gravity gets no say.
vup:    ld hl,(VI_L)
        dec hl
        ld a,h
        or l
        ret z
.xj0_51:
        jp vsearch.xj1_21  
; vbol: 4 bytes. Back to the line start. Fresh start, same line.
vbol:   xor a
        jp vfixc.xj1_22  
; veol: 5 bytes. Find the line end. No further seats.
veol:   ld a,255
        jp vfixc.xj0_50  
; vgoto: 13 bytes. Jump to a line. That count had better fit.
vgoto:  ld hl,(U_T)
        ld a,h
        or l
        jr nz,.g
        ld hl,(VI_N)
.g:     jp vsearch.xj0_49  

; ---- editing in command mode
; vdelc: 13 bytes. Delete a character. The buffer gets one bite smaller.
vdelc:  call vcadr                 ; x.
        ld a,(hl)
        cp 10
        ret z
        call vdel1
        jp vline
; vrepl: 24 bytes. Replace a character. One out, one in.
vrepl:  call vkey                  ; r c.
        cp ' '
        ret c
        push af
        call vcadr
        pop bc
        ld a,(hl)
        cp 10
        ret z
        ld (hl),b
        ld a,1
        ld (VI_MOD),a
        jp vline
; vdd: 63 bytes. Delete a whole line. The cursor gets serious.
vdd:    call vkey                  ; dd.
        cp 'd'
        ret nz
        ld hl,(VI_N)
        ld a,h
        or l
        ret z
        ld hl,(VI_L)
        call vladr
        push hl
        ld de,VI_YANK               ; yank the line.
        ld b,0
.y:     ld a,(hl)
        ld (de),a
        inc hl
        inc de
        inc b
        cp 10
        jr z,.ye
        ld a,b
        cp 127
        jr c,.y
        ld a,10
        ld (de),a
        inc b
.ye:    ld a,b
        ld (VI_YL),a
        ld hl,(VI_L)
        inc hl
        call vladr                  ; HL = next line.
        pop de                      ; DE = line start.
        call vcut
        ld hl,(VI_N)
        dec hl
        jr vput.xj0_17  
; vput: 60 bytes. Put the saved line back. No magic clipboard.
vput:   ld a,(VI_YL)               ; p: the yanked line below.
        or a
        ret z
        ld hl,(VI_N)
        ld a,h
        or l
        ld hl,(VI_L)
        jr z,.e
        inc hl
.e:     ld (U_T+2),hl
        call vladr
        ld a,(VI_YL)
        ld c,a
        ld b,0
        call vgap
        ret c
        ex de,hl
        ld hl,VI_YANK
        ld a,(VI_YL)
        ld c,a
        ld b,0
        ldir
        ld hl,(U_T+2)
        ld (VI_L),hl
        ld hl,(VI_N)
        inc hl
.xj0_17:
        ld (VI_N),hl
        jp vredr
; vjoin: 38 bytes. Join two lines. Make room for the handshake.
vjoin:  ld hl,(VI_L)               ; J: join with the next line.
        ld de,(VI_N)
        call cphl
        ret nc
        call vladr
.f:     ld a,(hl)
        inc hl
        cp 10
        jr nz,.f
        dec hl
        ld (hl),' '
        ld hl,(VI_N)
        dec hl
        ld (VI_N),hl
        ld a,1
        ld (VI_MOD),a
        jp vredr
; vzz: 9 bytes. Save and quit. The editor knows the exit.
vzz:    call vkey                  ; ZZ =:wq.
        cp 'Z'
        ret nz
        jp vcolon.xj0_9  

; ---- insert mode
; vappe: 8 bytes. Append text. The buffer has the final word.
vappe:  ld a,255                   ; A.
        ld (VI_C),a
        call vfixc
; vappend: 12 bytes. Append after the cursor. One small shift.
vappend:
        call vlen                   ; a: after the cursor.
        or a
        jr z,vins
        ld hl,VI_C
        inc (hl)
        jr vins
; vopen: 14 bytes. Open a new line. No expansion pack required.
vopen:  ld hl,(VI_N)               ; o.
        ld a,h
        or l
        ld hl,(VI_L)
        jr z,vopenu
        inc hl
        ld (VI_L),hl
; vopenu: 11 bytes. Open a line above. Gravity again gets no say.
vopenu: ld hl,(VI_L)               ; O.
        call vnewl
        ret c
        xor a
        ld (VI_C),a
; vins: 141 bytes. Insert text. The gap must be real, not wished for.
vins:   ld hl,(VI_N)               ; an empty buffer gets one line.
        ld a,h
        or l
        jr nz,.go
        ld hl,1
        ld (VI_L),hl
        call vnewl
        ret c
.go:    ld a,1
        ld (VI_INS),a
        ld hl,s_ins
        ld (VI_MSG),hl
.l:     call vfix
        call vshow
        call vkey
        cp 7                        ; EDIT = ESC.
        jr z,.esc
        cp 13
        jr z,.nl
        cp 12
        jr z,.del
        cp ' '
        jr c,.l
        push af
        call vcadr
        ld bc,1
        call vgap
        pop bc
        jr c,.l
        ld (hl),b
        ld hl,VI_C
        inc (hl)
        jr vins.xj0_40  
.del:   ld hl,VI_C
        ld a,(hl)
        or a
        jr z,.l
        dec (hl)
        call vcadr
        call vdel1
.xj0_40:
        call vline
        jr .l
.nl:    call vcadr                  ; split the line.
        ld bc,1
        call vgap
        jr c,.l
        ld (hl),10
        ld hl,(VI_N)
        inc hl
        ld (VI_N),hl
        ld hl,(VI_L)
        inc hl
        ld (VI_L),hl
        xor a
        ld (VI_C),a
        call vredr
        jr .l
.esc:   xor a
        ld (VI_INS),a
        ld hl,s_vnull
        ld (VI_MSG),hl
        jp vleft

; vnewl: 24 bytes. HL = line number - insert an empty line in front of it. Two halves, same text.
vnewl:  call vladr
        ld bc,1
        call vgap
        ret c
        ld (hl),10
        ld hl,(VI_N)
        inc hl
        ld (VI_N),hl
        call vredr
        or a
        ret

; ---- buffer primitives
; vladr: 29 bytes. HL = line number 1..N+1; return its buffer address. No treasure map included.
vladr:  ex de,hl
        ld hl,VI_BUF
.l:     dec de
        ld a,d
        or e
        ret z
        bit 7,d
        ret nz
.s:     push de
        ld de,(VI_END)
        call cphl
        pop de
        ret nc
        ld a,(hl)
        inc hl
        cp 10
        jr nz,.s
        jr .l

; vcadr: 12 bytes. Return HL pointing at the cursor character. The screen never moves itself.
vcadr:  ld hl,(VI_L)
        call vladr
        ld a,(VI_C)
        jp adda

; vlen: 25 bytes. A = length of the current line (without the newline). Newline does not get a vote.
vlen:   ld hl,(VI_N)
        ld a,h
        or l
        ret z
        ld hl,(VI_L)
        call vladr
        ld b,0
.l:     ld a,(hl)
        cp 10
        jr z,.e
        inc hl
        inc b
        jr .l
.e:     ld a,b
        ret

; vgap: 87 bytes. Open BC bytes at HL or return CF if full. There is no extra 48K in the drawer.
vgap:   ld (U_T+4),hl
        ld (U_T+6),bc
        ld hl,(VI_END)
        add hl,bc
        ld de,VI_LIM
        call cphl
        jr nc,.full
        ld de,128                   ; grow the break first (v1 'sbrk'). Someone has to tidy up those
                                    ; keypresses.
        add hl,de
        SC _break
        jr c,.full
        ld de,(U_T+4)
        ld hl,(VI_END)
        or a
        sbc hl,de                   ; tail length.
        ld a,h
        or l
        jr z,.nt
        ld b,h
        ld c,l
        ld hl,(VI_END)
        dec hl
        push hl
        ld de,(U_T+6)
        add hl,de
        ex de,hl
        pop hl
        lddr
.nt:    ld hl,(VI_END)
        ld de,(U_T+6)
        add hl,de
        ld (VI_END),hl
        ld hl,(U_T+4)
        ld a,1
        ld (VI_MOD),a
        or a
        ret
.full:  ld hl,s_full
        jp vsave.xj0_37  

; vdel1: 3 bytes. Delete the byte at HL. One less tenant in 48K.
vdel1:  ld d,h
        ld e,l
        inc hl
; vcut: 26 bytes. Delete bytes from DE through HL-1. Mind both ends.
vcut:   push de
        ld b,h
        ld c,l
        ld hl,(VI_END)
        or a
        sbc hl,bc
        push hl
        ld h,b
        ld l,c
        pop bc
        call ldirz
        ld (VI_END),de
        pop de
        ld a,1
        jp vsave.xj1_19  

; ---- screen
; vfix: 107 bytes. Keep the cursor and view inside the text buffer. No trips off the map.
vfix:   ld hl,(VI_N)
        ld de,(VI_L)
        ex de,hl
        call cphl                   ; L > N?
        jr c,.l1
        jr z,.l1
        ld (VI_L),de
.l1:    ld hl,(VI_L)
        ld a,h
        or l
        jr nz,.l2
        inc hl
        ld (VI_L),hl
.l2:    call vfixc
; Vertical motion. The cursor needs a line to land on.
        ld hl,(VI_L)
        ld de,(VI_TOP)
        call cphl
        jr nc,.v1
        ld (VI_TOP),hl
        jr .vr
.v1:    ld de,(VI_TOP)
        ld hl,VROWS-1
        add hl,de
        ld de,(VI_L)
        ex de,hl
        call cphl                   ; L > TOP+21?
        jr c,.h
        jr z,.h
        ld de,-(VROWS-1)
        add hl,de
        ld (VI_TOP),hl
.vr:    call vredr
.h:     ; horizontal.
        ld a,(VI_LEFT)
        ld b,a
        ld a,(VI_C)
        cp b
        jr nc,.h1
        ld (VI_LEFT),a
        jr vredr
.h1:    sub b
        cp 64
        ret c
        ld a,(VI_C)
        sub 63
        ld (VI_LEFT),a
; vredr: 6 bytes. Redraw the text. Pixels love attention.
vredr:  ld a,1
        ld (VI_RD),a
        ret
; vfixc: 25 bytes. Clamp the cursor column to the line (or its end in insert mode). Borders are real.
vfixc:  call vlen
        ld b,a
        ld a,(VI_INS)
        or a
        jr nz,.i
        ld a,b
        or a
        jr z,.i
        dec b
.i:     ld a,(VI_C)
        cp b
        ret c
        ld a,b
.xj0_50:
.xj1_22:
        ld (VI_C),a
        ret

; vshow: 61 bytes. Redraw if needed, then update status and cursor. There are no spare columns.
vshow:  ld a,(VI_RD)
        or a
        jr z,.s
        xor a
        ld (VI_RD),a
        ld b,0
.r:     push bc
        call vrow
        pop bc
        inc b
        ld a,b
        cp VROWS
        jr c,.r
.s:     call vstat
; cursor: AT L-TOP, C-LEFT. The display will notice if we cheat.
        ld hl,VI_ROW
        ld (hl),16h
        inc hl
        push hl
        ld hl,(VI_L)
        ld de,(VI_TOP)
        or a
        sbc hl,de
        ld a,l
        pop hl
        ld (hl),a
        inc hl
        ld a,(VI_LEFT)
        ld b,a
        ld a,(VI_C)
        sub b
        ld (hl),a
        ld bc,3
        jr vwrite

; vline: 11 bytes. Redraw the current line only. The pixels know their place.
vline:  ld hl,(VI_L)
        ld de,(VI_TOP)
        or a
        sbc hl,de
        ld b,l
; vrow: 86 bytes. B = display row; draw its text. The Spectrum bitmap takes the scenic route.
vrow:   ld hl,VI_ROW
        ld (hl),16h
        inc hl
        ld (hl),b
        inc hl
        ld (hl),0
        ld hl,(VI_TOP)
        ld a,b
        call adda
        ex de,hl
        ld hl,(VI_N)
        call cphl                   ; N >= line?
        ex de,hl
        ld de,VI_ROW+3
        ld c,64
        jr c,.tilde
        push de
        call vladr
        pop de
        ld a,(VI_LEFT)              ; skip LEFT characters.
        or a
        jr z,.cp
        ld b,a
.sk:    ld a,(hl)
        cp 10
        jr z,.pad
        inc hl
        djnz .sk
.cp:    ld a,(hl)
        cp 10
        jr z,.pad
        cp ' '
        jr nc,.ok
        ld a,'?'
.ok:    ld (de),a
        inc hl
        inc de
        dec c
        jr nz,.cp
        jr .w
.tilde: ld a,'~'
        ld (de),a
        inc de
        dec c
.pad:   ld a,' '
.p:     ld (de),a
        inc de
        dec c
        jr nz,.p
.w:     ld bc,67
; vwrite: 9 bytes. Write a row. No room for extras.
vwrite: ld hl,1
        ld de,VI_ROW
        jp tpadopt.xj0_45  

; vstat: 77 bytes. Fill row 22 with status text, or file name and position. Small screen, big gossip.
vstat:  ld de,VI_CMD
        ld hl,(VI_MSG)
        ld a,h
        or l
        jr nz,.m
        ld hl,VI_FN
        ld a,(hl)
        or a
        jr nz,.f
        ld hl,s_noname
.f:     call strcpy
        ld a,(VI_MOD)
        or a
        jr z,.nm
        ld hl,s_vmod
        call strcpy
.nm:    ld a,' '
        ld (de),a
        inc de
        ld hl,(VI_L)
        call fmtdec
        ld a,'/'
        ld (de),a
        inc de
        ld hl,(VI_N)
        call fmtdec
        xor a
        ld (de),a
        jr .out
.m:     call strcpy
        ld a,(VI_INS)               ; keep "-- INSERT --" while inserting.
        or a
        jr nz,.out
        ld hl,0
        ld (VI_MSG),hl
.out:   ld hl,VI_CMD
; vline21: 40 bytes. HL = text; pad status output to 63 chars. Even blanks occupy pixels.
vline21:
        ld de,VI_ROW
        ld a,16h
        ld (de),a
        inc de
        ld a,VROWS
        ld (de),a
        inc de
        xor a
        ld (de),a
        inc de
        ld c,63
.c:     ld a,(hl)
        or a
        jr z,.p
        ld (de),a
        inc hl
        inc de
        dec c
        jr nz,.c
        jr .w
.p:     ld a,' '
.q:     ld (de),a
        inc de
        dec c
        jr nz,.q
.w:     ld bc,66
        jr vwrite

; vkey: 19 bytes. Return next raw key in A; BREAK returns zero. No polite requests.
vkey:   ld hl,0
        ld de,U_CH
        ld bc,1
        call sc_read
        ld a,0
        ret c
        ld a,(U_CH)
        ret

; ---- command line (: and /)
; vreadl: 70 bytes. A = prompt; read a command into VI_CMD, CF on cancel. Colons have ambitions.
vreadl: ld (VI_CMD),a
        ld hl,VI_CMD+1
        ld (U_T+2),hl
.l:     ld hl,(U_T+2)
        ld (hl),0
        ld hl,VI_CMD
        call vline21
        call vkey
        cp 13
        ret z
        cp 7
        scf
        ret z
        cp 12
        jr z,.del
        cp ' '
        jr c,.l
        ld hl,(U_T+2)
        ld (hl),a
        ld de,VI_CMD+62
        call cphl
        jr nc,.l
        inc hl
        jr vreadl.xj0_39  
.del:   ld hl,(U_T+2)
        ld de,VI_CMD+1
        call cphl
        jr z,.l
        dec hl
.xj0_39:
        ld (U_T+2),hl
        jr .l

; vcolon: 76 bytes. Run an ex-style command. A colon gets power.
vcolon: ld a,':'
        call vreadl
        ret c
        ld hl,VI_CMD+1
        ld a,(hl)
        cp '0'
        jr c,.nn
        cp '9'+1
        jr nc,.nn
        call atoi                   ; :n go to line n.
        ld (VI_L),de
        ret
.nn:    cp 'w'
        jr z,.w
        cp 'x'
        jr z,.wq
        cp 'q'
        ret nz
        inc hl
        ld a,(hl)
        cp '!'
        jp z,vquit
        ld a,(VI_MOD)
        or a
        jp z,vquit
        ld hl,s_nowr
        jp vload.xj1_20  
.w:     inc hl
        ld a,(hl)
        cp 'q'
        jr z,.wq
        call vname
        jp vsave
.xj0_9:
.wq:    call vsave
        ret c
        jp vquit

; vname: 16 bytes. Read an optional command file name. Empty means no new destination.
vname:
.s:     ld a,(hl)
        cp ' '
        jr nz,.n
        inc hl
        jr .s
.n:     or a
        ret z
        ld de,VI_FN
        jp strcpy

; vsearch: 91 bytes. Search the text. The pattern gets a say.
vsearch:
        ld a,'/'
        call vreadl
        ret c
        ld hl,(VI_L)
        ld bc,(VI_N)
.l:     ld a,b
        or c
        jr z,.no
        dec bc
        inc hl
        ld de,(VI_N)
        call cphl
        jr c,.t
        jr z,.t
        ld hl,1
.t:     push hl
        push bc
        call vladr
        push hl
        pop ix                      ; line start.
.c:     ld a,(hl)
        cp 10
        jr z,.nx
        push hl
        ld de,VI_CMD+1
.m:     ld a,(de)
        or a
        jr z,.yes
        cp (hl)
        jr nz,.mn
        inc hl
        inc de
        jr .m
.mn:    pop hl
        inc hl
        jr .c
.nx:    pop bc
        pop hl
        jr .l
.yes:   pop hl                      ; match: column = HL - line start. The pixels have enough trouble
                                    ; staying put.
        push ix
        pop de
        or a
        sbc hl,de
        ld a,l
        ld (VI_C),a
        pop bc
        pop hl
.xj0_49:
.xj1_21:
        ld (VI_L),hl
        ret
.no:    ld hl,s_nfnd
        jr vload.xj0_48  

; ---- files
; vload: 149 bytes. Load text. Hope it fits in the buffer.
vload:  ld hl,VI_FN
        ld de,0
        call sc_open
        jr nc,.o
        ld hl,s_new
.xj0_48:
.xj1_20:
        ld (VI_MSG),hl
        ret
.o:     ld (VI_FD),hl
.r:     ld hl,(VI_END)
        ld bc,128
        add hl,bc
        ld de,VI_LIM
        call cphl
        jr nc,.full
        ld de,128
        add hl,de
        SC _break
        jr c,.full
        ld hl,(VI_FD)
        ld de,(VI_END)
        ld bc,128
        call sc_read
        jr c,.e
        ld a,h
        or l
        jr z,.e
        ld de,(VI_END)
        add hl,de
        ld (VI_END),hl
        jr .r
.full:  ld hl,s_full
        ld (VI_MSG),hl
        xor a                       ; only part of it: the name goes, so.
        ld (VI_FN),a                ; :w cannot cut the file short.
.e:     ld hl,(VI_FD)
        call sc_close
; the text must end with a newline.
        ld hl,(VI_END)
        ld de,VI_BUF
        or a
        sbc hl,de
        jr z,.cnt
        ld hl,(VI_END)
        dec hl
        ld a,(hl)
        cp 10
        jr z,.cnt
        inc hl
        ld (hl),10
        inc hl
        ld (VI_END),hl
.cnt:   ld hl,VI_BUF                ; count the lines.
        ld bc,0
.k:     ld de,(VI_END)
        call cphl
        jr nc,.kd
        ld a,(hl)
        inc hl
        cp 10
        jr nz,.k
        inc bc
        jr .k
.kd:    ld (VI_N),bc
        jr vsave.xj0_38  

; vsave: 85 bytes. Write the buffer, CF on error. Hope does not count as a saved file.
vsave:  ld hl,VI_FN
        ld a,(hl)
        or a
        jr z,.err
        ld de,0Eh
        call sc_creat
        jr c,.err
        ld (VI_FD),hl
        ld hl,(VI_END)
        ld de,VI_BUF
        or a
        sbc hl,de
        ld b,h
        ld c,l
        push bc
        ld hl,(VI_FD)
        call sc_write
        pop de
        push de
        jr c,.wr
        or a
        sbc hl,de                   ; CF: written short (no space).
.wr:    push af
        ld hl,(VI_FD)
        call sc_close
        pop af
        pop hl                      ; "<n> chars written".
        jr c,.err                   ; still modified::wq stays in vi.
        ld de,VI_CMD+1
        call fmtdec
        ld hl,s_written
        call strcpy
        ld hl,VI_CMD+1
        ld (VI_MSG),hl
.xj0_38:
        xor a
.xj1_19:
        ld (VI_MOD),a
        ret
.err:   ld hl,s_cantw
.xj0_37:
        ld (VI_MSG),hl
        scf
        ret

; vquit: 13 bytes. Quit the editor. The buffer has its last word.
vquit:  ld a,TT_ECHO
        call gstty
.xj0_8:
        ld a,12
.xj1_6:
        call putc
        jp exit0

s_ins:  db "-- INSERT --",0
s_vnull equ s_null             ; "".
s_full: db "buffer full",0
s_noname: db "[no name]",0
s_vmod:  db " [+]",0
s_nowr: db "no write since change (:q!)",0
s_nfnd  equ s_nf                ; "not found" (sh).
s_new:  db "new file",0
s_written: db " chars written",0
s_cantw: db "can't write",0
e_vi:
