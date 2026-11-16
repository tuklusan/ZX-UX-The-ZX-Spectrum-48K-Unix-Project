; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  more v1 utilities: date stat wc od cmp sum echo sleep cls
;  -  and UNIX-inspired demos
; =====================================================================

; ------------------------------------------------------------- date
; Date input is mmddhhmm with optional year. No crystal ball.
DT_T    equ TV                  ; 4 byte accumulator.
t_date: db 18h,6
        dw STKRES, TV+10-UDATA, date_m
; date_m: 37 bytes. Show or set the clock. It keeps moving either way.
date_m: pop hl
        call args
        ld a,1
        call argn
        jr z,.show
        call dset
        jr nc,.show
        ld hl,s_badconv
.xj0_5:
.xj1_0:
        call eputs
        jp tperr.xj2_0  
.show:  call sc_time
        call ctime
.xj0_4:
        call puts
        jp echo_m.xj1_8  
s_badconv: db "bad conversion",10,0

DT_MIN  equ TV+4
DT_HR   equ TV+5
DT_MON  equ TV+6
DT_DAY  equ TV+7
DT_YR   equ TV+8
; dset: 200 bytes. HL = mmddhhmm[yy]; set the clock or return CF. Calendars have sharp edges.
dset:   push hl
        call strlen
        ld a,c
        pop hl
        cp 8
        jr z,.ny
        cp 10
        scf
        ret nz
.ny:    call d2
        ret c
        dec a
        cp 12
        ccf
        ret c
        ld (DT_MON),a
        call d2
        ret c
        ld (DT_DAY),a
        call d2
        ret c
        cp 24
        ccf
        ret c
        ld (DT_HR),a
        call d2
        ret c
        cp 60
        ccf
        ret c
        ld (DT_MIN),a
        ld a,(hl)
        or a
        jr z,.cy
        call d2
        ret c
        ld e,a
        ld d,0
        ld hl,1900
        add hl,de
        cp 70
        jr nc,.y
        ld de,100
        add hl,de
        jr .y
.cy:    call sc_time                ; keep the current year.
        call ctime
        ld hl,(U_T+4)
.y:     ld (DT_YR),hl
        ld de,0                 ; days since 1970.
        ld bc,1970
.yl:    ld hl,(DT_YR)
        or a
        sbc hl,bc
        jr z,.ye
        ld hl,365
        ld a,c
        and 3
        jr nz,.yn
        inc hl
.yn:    add hl,de
        ex de,hl
        inc bc
        jr .yl
.ye:    ld a,(DT_MON)
        ld b,a
        ld hl,mdays
        or a
        jr z,.md
.ml:    ld a,(hl)
        inc hl
        add a,e
        ld e,a
        jr nc,.m1
        inc d
.m1:    djnz .ml
        ld a,(DT_MON)           ; leap day.
        cp 2
        jr c,.md
        ld a,(DT_YR)
        and 3
        jr nz,.md
        inc de
.md:    ld a,(DT_DAY)
        dec a
        add a,e
        ld e,a
        jr nc,.m2
        inc d
.m2:    ex de,hl                ; seconds = ((days*24+h)*60+m)*60.
        ld de,0
        ld a,24
        call mul32
        ld a,(DT_HR)
        call add32
        ld a,60
        call mul32
        ld a,(DT_MIN)
        call add32
        ld a,60
        call mul32
        SC _stime
        ret
; d2: 24 bytes. Read two decimal digits at HL; return A. Not a guessing game.
d2:     ld a,(hl)
        sub '0'
        cp 10
        ccf
        ret c
        ld b,a
        add a,a
        add a,a
        add a,b
        add a,a
        ld b,a
        inc hl
        ld a,(hl)
        sub '0'
        cp 10
        ccf
        ret c
        inc hl
        add a,b
        ret
; mul32: 34 bytes. Multiply DE:HL by A. The Z80 has no big pockets.
mul32:  push bc
        ld (DT_T),hl
        ld (DT_T+2),de
        ld b,a
        ld hl,0
        ld de,0
.l:     push bc
        ld bc,(DT_T)
        add hl,bc
        ex de,hl
        ld bc,(DT_T+2)
        adc hl,bc
        ex de,hl
        pop bc
        djnz .l
        pop bc
        ret
; add32: 7 bytes. Add A to DE:HL. Four bytes get the job.
add32:  add a,l
        ld l,a
        ret nc
        inc h
        ret nz
        inc de
        ret
e_date:





; ------------------------------------------------------------- stat
ST_L    equ TV
t_stat: db 18h,6
        dw STKRES, TV+7-UDATA, stat_m
; stat_m: 135 bytes. Ask a file for its details. Names are not enough.
stat_m: pop hl
        call args
        ld a,1
        ld hl,.one
.xj0_26:
.xj1_10:
        jp zxp_m.xj2_2  
.one:   push hl
        ld de,U_STB
        call sc_stat
        pop hl
        jr nc,.ok
.xj0_25:
        ld de,s_nonex
        jp perr
.ok:    call puts
        ld hl,s_colon
        call puts
        ld hl,s_inum
        call puts
        ld hl,(U_STB)
        call putdec
        ld hl,s_nl1
        call puts
        ld de,ST_L
        call ptmode
        ld hl,ST_L
        call puts
        call space
        ld a,(U_STB+4)
        ld l,a
        ld h,0
        call putdec
        call space
        ld hl,(U_STB+6)
        call putdec
        ld hl,s_byte
        call puts
        ld hl,s_mod
        call puts
        ld hl,(U_STB+2+26)
        ld de,(U_STB+2+28)
        call ctime
        call puts
        call crlf
        ld hl,s_cre
        call puts
        ld hl,(U_STB+2+22)
        ld de,(U_STB+2+24)
        call ctime
.xj0_24:
        jp tpls.xj1_1  
s_colon: db ":",10,0
s_inum: db " i-number ",0
s_nl1:  db 10," ",0
s_byte: db " bytes",10,0
s_mod:  db " mod ",0
s_cre:  db " cre ",0
e_stat:

; ------------------------------------------------------------- wc
WC_L    equ TV
WC_W    equ TV+2
WC_C    equ TV+4
WC_IN   equ TV+6
t_wc:   db 18h,6
        dw STKRES, TV+8-UDATA, wc_m
; wc_m: 32 bytes. Count text. The words do not count themselves.
wc_m:   pop hl
        call args
        ld a,1
        call argn
        jr nz,.f
        xor a
        call rsetfd
        ld hl,s_null
        call wcone.cnt
        jp exit0
.f:     ld a,1
        ld hl,wcone
        jp sum_m.xj0_23  
; wcone: 117 bytes. Count one file. Even newlines get a vote.
wcone:  push hl
        call ropen
        pop hl
        jr nc,.cnt
        jp sum_m.xj0_22  
.cnt:   push hl
        ld hl,0
        ld (WC_L),hl
        ld (WC_W),hl
        ld (WC_C),hl
        xor a
        ld (WC_IN),a
.l:     call getch
        jr c,.e
        ld hl,(WC_C)
        inc hl
        ld (WC_C),hl
        cp 10
        jr nz,.nl
        ld hl,(WC_L)
        inc hl
        ld (WC_L),hl
.nl:    cp ' '+1
        jr c,.sp
        ld a,(WC_IN)
        or a
        jr nz,.l
        inc a
        ld (WC_IN),a
        ld hl,(WC_W)
        inc hl
        ld (WC_W),hl
        jr .l
.sp:    xor a
        ld (WC_IN),a
        jr .l
.e:     ld a,(R_FD)
        or a
        call nz,rclose
        ld hl,(WC_L)
        ld a,5
        call putdecw
        ld hl,(WC_W)
        ld a,6
        call putdecw
        ld hl,(WC_C)
        ld a,6
        call putdecw
        call space
        pop hl
        jp tpls.xj0_12  
s_null  equ m_colon+2           ; "".
e_wc:

; ------------------------------------------------------------- od
; od [file]: offset and eight octal words per line. Sixteen bytes, no spare change.
OD_B    equ TV
OD_O    equ TV+18
t_od:   db 18h,6
        dw STKRES, TV+20-UDATA, od_m
; od_m: 127 bytes. Show bytes in octal. Retro to the bone.
od_m:   pop hl
        call args
        ld a,1
        call argn
        ld a,0
        jr z,.s
        call ropen
        jr nc,.r
.xj0_1:
        ld a,1
        call argn
        ld de,s_cantopen
        call perr
        jp exit0
.s:     call rsetfd
.r:     ld hl,0
        ld (OD_O),hl
.l:     ld hl,OD_B
        ld b,16                 ; 8 words a line, as in v1.
        ld c,0
.g:     call getch
        jr c,.eof
        ld (hl),a
        inc hl
        inc c
        djnz .g
.eof:   ld a,c
        or a
        jr z,.end
        push bc
        ld (hl),0
        ld hl,(OD_O)
        call putoct
        pop bc
        push bc
        inc c
        srl c
        ld b,c
        ld hl,OD_B
.w:     push bc
        push hl
        call space
        pop hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        push hl
        ex de,hl
        call putoct
        pop hl
        pop bc
        djnz .w
        call crlf
        pop bc
        ld a,c
        ld hl,(OD_O)
        call adda
        ld (OD_O),hl
        ld a,c
        cp 16
        jr z,.l
.end:   ld hl,(OD_O)
        call putoct
        jp echo_m.xj0_21  
e_od:

; ------------------------------------------------------------- cmp
; cmp file1 file2.
CM_FD   equ TV
CM_C    equ TV+2                ; char count.
CM_L    equ TV+4                ; line count.
CM_B    equ TV+6                ; 128 second buffer.
CM_N    equ TV+134
CM_P    equ TV+136
t_cmp:  db 18h,6
        dw STKRES, CM_P+2-UDATA, cmp_m
; cmp_m: 186 bytes. Compare files. One mismatch ends the romance.
cmp_m:  pop hl
        call args
        ld a,(U_ARGC)
        cp 3
        ld hl,s_cmpu
        jp nz,usage
        ld a,2
        call argn
        ld de,0
        call sc_open
        ld a,2
        jr c,.ce
        ld (CM_FD),hl
        ld a,1
        call argn
        call ropen
        jr nc,.go
        ld a,1
.ce:    call argn
        ld de,s_cantopen
        call perr
        ld hl,2
        jp exitc
.go:    ld hl,1
        ld (CM_C),hl
        ld (CM_L),hl
        ld hl,0
        ld (CM_N),hl
.l:     call getch
        push af
        call cmget
        ld b,a
        jr c,.e2
        pop af
        jr c,.eof1
        cp b
        jr nz,.diff
        cp 10
        jr nz,.n
        ld hl,(CM_L)
        inc hl
        ld (CM_L),hl
.n:     ld hl,(CM_C)
        inc hl
        ld (CM_C),hl
        jr .l
.e2:    pop af
        jp c,exit0              ; both ended: identical.
        ld a,2
        jr .eof
.eof1:  ld a,1
.eof:   push af
        ld hl,s_eof
        call puts
        pop af
        call argn
        call puts
        jr cmp_m.xj0_3  
.diff:  ld a,1
        call argn
        call puts
        call space
        ld a,2
        call argn
        call puts
        ld hl,s_differ
        call puts
        ld hl,(CM_C)
        call putdec
        ld hl,s_line
        call puts
        ld hl,(CM_L)
        call putdec
.xj0_3:
        call crlf
        jp tperr.xj1_2  
; cmget: 50 bytes. Read for comparison. Same bytes, same judgement.
cmget:  ld hl,(CM_N)
        ld a,h
        or l
        jr nz,.h
        ld hl,(CM_FD)
        ld de,CM_B
        ld bc,128
        call sc_read
        ret c
        ld a,h
        or l
        scf
        ret z
        ld (CM_N),hl
        ld hl,CM_B
        ld (CM_P),hl
.h:     ld hl,(CM_N)
        dec hl
        ld (CM_N),hl
        ld hl,(CM_P)
        ld a,(hl)
        inc hl
        ld (CM_P),hl
        or a
        ret
s_cmpu: db "cmp file1 file2",0
s_eof:  db "EOF on ",0
s_differ: db " differ: char ",0
s_line: db ", line ",0
e_cmp:

; ------------------------------------------------------------- sum
t_sum:  db 18h,6
        dw STKRES, TV+4-UDATA, sum_m
; sum_m: 90 bytes. Add up the checksum. Trust still needs a number.
sum_m:  pop hl
        call args
        ld a,1
        call argn
        ld hl,s_sumu
        jp z,usage
        ld a,1
        ld hl,.one
.xj0_23:
        jp zxp_m.xj1_5  
.one:   push hl
        call ropen
        pop hl
        jr nc,.o
.xj0_22:
.xj1_9:
.xj2_3:
        jp mfile.xj0_0  
.o:     ld hl,0
        ld (TV),hl
        ld (TV+2),hl
.l:     call getch
        jr c,.e
        ld hl,(TV)
        call adda
        ld (TV),hl
        ld hl,(TV+2)
        inc hl
        ld (TV+2),hl
        jr .l
.e:     call rclose
        ld hl,(TV)
        ld a,5
        call putdecw
        ld hl,(TV+2)
        call blocks
        ld a,4
        call putdecw
        jp crlf
s_sumu: db "sum file ...",0
e_sum:

; ------------------------------------------------------------- echo
t_echo: db 18h,6
        dw STKRES, TV-UDATA, echo_m
; echo_m: 33 bytes. Say it back. No commentary required.
echo_m: pop hl
        call args
        ld a,1
.l:     push af
        call argn
        jr z,.e
        pop af
        push af
        cp 1
        call nz,space
        call puts
        pop af
        inc a
        jr .l
.e:     pop af
.xj0_21:
.xj1_8:
        call crlf
        jp exit0
e_echo:


; ------------------------------------------------------------- sleep
t_sleep: db 18h,6
        dw STKRES, TV-UDATA, sleep_m
; sleep_m: 40 bytes. Wait the requested time. The clock calls the shots.
sleep_m: pop hl
        call args
        ld a,1
        call argn
        ld hl,s_slu
        jp z,usage
        ld a,1
        call argn
        call atoi
        ex de,hl
.l:     ld a,h
        or l
        jp z,exit0
        push hl
        ld hl,50
        call sc_sleep
        pop hl
        dec hl
        jr .l
s_slu:  db "sleep seconds",0
e_sleep:

; ------------------------------------------------------------- cls
t_cls:  db 18h,6
        dw STKRES, TV-UDATA, cls_m
; cls_m: 3 bytes. Clear the screen. An empty view is still useful.
cls_m:  jp vquit.xj0_8  
e_cls:

; ------------------------------------------------------------- demos
t_hello: db 18h,6
        dw STKRES, TV-UDATA, hello_m
; hello_m: 6 bytes. Say hello. We can spare the bytes.
hello_m: ld hl,s_hello
.xj0_20:
        jp zxst.xj1_4  
s_hello: db "Hello World!",10,0
e_hello:

t_beep: db 18h,6
        dw STKRES, TV-UDATA, beep_m
; beep_m: 5 bytes. Make a noise. The ROM already knows the tune.
beep_m: ld a,7
        jp vquit.xj1_6  
e_beep:

; clock: show the time every second (BREAK to stop).
t_clock: db 18h,6
        dw STKRES, TV-UDATA, clock_m
; clock_m: 33 bytes. Show the clock. Time does not ask permission.
clock_m: call sc_time
        call ctime
        xor a
        ld (U_CT+19),a
        ld hl,U_CT+11
        call puts
        ld b,8
.b:     ld a,8
        call putc
        djnz .b
        ld hl,50
        call sc_sleep
        jr clock_m
e_clock:

; forktest: parent and child print in turn - preemptive scheduling.
FK_C    equ TV
t_fork: db 18h,6
        dw STKRES, TV+1-UDATA, fork_m
; fork_m: 82 bytes. Try a second process. Four seats in this machine.
fork_m: call sc_fork
        jr c,.p
        ld a,h
        or l
        ld a,'c'
        jr z,.go
        ld a,'P'
.go:    ld (FK_C),a
        ld c,24
.l:     ld a,(FK_C)
        call putc
        ld hl,16384
.d:     dec hl                  ; busy loop: only the clock interrupt.
        ld a,h                  ; can switch to the other process.
        or l
        jr nz,.d
        dec c
        jr nz,.l
        ld a,(FK_C)
        cp 'P'
        jp nz,exit0
        call sc_wait
        call crlf
        SC _getpid              ; If this is PID 1, start the shell again.
        dec hl                  ; No stray init process left behind.
        ld a,h
        or l
        jp nz,exit0
        ld hl,s_sh
        ld de,.av
.xj0_19:
        call sc_exec
        jp exit0
.av:    dw s_minus,0
.p:     ld hl,s_ferr
        jp zxst.xj0_15  
s_ferr: db "fork failed: no free process slot",10,0
e_fork:

; ------------------------------------------------------------- more
; more [file...] (or more < file) Shows a page, then --More--: SPACE the next page, ENTER one more line, q,
; EDIT or BREAK quit. Keys come from /dev/tty, so input may be a file.
MO_TTY  equ TV                  ; key fd.
MO_ROW  equ TV+2                ; rows shown on this page.
MO_COL  equ TV+3                ; print column.
MO_K    equ TV+4                ; key read.
MO_NF   equ TV+5                ; several files: name headers.
MOPAGE  equ 22                  ; text rows a page, the prompt below.
t_more: db 18h,6
        dw STKRES, TV+6-UDATA, more_m
; more_m: 96 bytes. Show text a page at a time. Eyes need a break.
more_m: pop hl
        call args
        ld a,1
        call argn
        jr nz,.go
        ld hl,0                 ; no file: input must not be the terminal.
        ld de,U_STB
        SC _gtty
        ld hl,s_mou
        jp nc,usage
.go:    ld hl,0                 ; Handle BREAK at the pager prompt.
        call sc_intr            ; Ignore interrupt signals while the pager reads keys.
        ld hl,s_tty
        ld de,0
        call sc_open
        jp c,exit0
        ld (MO_TTY),hl
        ld a,TT_RAW
        call mstty
        ld a,(U_ARGC)
        cp 3
        sbc a,a
        cpl
        ld (MO_NF),a
        ld a,1
        call argn
        jr nz,.f
        xor a
        call rsetfd             ; standard input.
        call mpage
        jr .x
.f:     ld a,1
        ld hl,mfile
        call each
.x:     ld a,TT_ECHO
        call mstty
        jp exit0
s_mou:  db "more [file ...]",0

; mstty: 19 bytes. A = tty mode → the key fd. The keys need rules.
mstty:  ld (U_T+4),a
        xor a
        ld (U_T+5),a
        ld hl,(MO_TTY)
        ld de,U_T
        SC _stty
        ret

; mfile: 41 bytes. HL = name → page it. Slow and steady.
mfile:  push hl
        call ropen
        pop hl
        jr nc,.o
.xj0_0:
        ld de,s_cantopen
        jp perr
.o:     ld a,(MO_NF)
        or a
        jr z,.p
        push hl
        ld hl,s_mohd
        call mputs
        pop hl
        call mputs
        ld a,10
        call mputc
.p:     call mpage
        jp rclose

; mpage: 9 bytes. Read the next page from the active input. Forty-eight K does not scroll forever.
mpage:  call getch
        ret c
        call mputc
        jr mpage

; mputs: 9 bytes. HL = string. No wall of text.
mputs:  ld a,(hl)
        or a
        ret z
        call mputc
        inc hl
        jr mputs

; mputc: 128 bytes. A = byte; print and track rows, columns and TAB; keep HL/DE/BC. Screen space is finite.
mputc:  cp 10
        jr z,.nl0
        cp 9
        jr z,.tab
        cp ' '
        ret c
        call putc               ; keeps A.
        cp 7Fh+1
        ret nc                  ; not drawn by the console.
        ld a,(MO_COL)
        inc a
        jr .c
.tab:   call putc
        ld a,(MO_COL)
        or 7
        inc a
.c:     ld (MO_COL),a
        cp 64
        ret c
        jr .nl
.nl0:   call putc
.nl:    xor a
        ld (MO_COL),a
        ld a,(MO_ROW)
        inc a
        ld (MO_ROW),a
        cp MOPAGE
        ret c
        push hl                 ; a full page: the prompt.
        push de
        push bc
        ld hl,s_more
        call puts
.k:     ld hl,(MO_TTY)
        ld de,MO_K
        ld bc,1
        call sc_read
        jr c,.q                 ; BREAK.
        ld a,(MO_K)
        ld b,0                  ; SPACE: a whole page.
        cp ' '
        jr z,.go
        ld b,MOPAGE-1           ; ENTER: one line.
        cp 13
        jr z,.go
        cp 7                    ; EDIT.
        jr z,.q
        or 20h
        cp 'q'
        jr nz,.k                ; other keys: still waiting.
.q:     ld hl,s_moer
        call puts
        jp more_m.x             ; (the stack is left: more exits). The return address would like to
                                ; survive.
.go:    ld a,b
        ld (MO_ROW),a
        ld hl,s_moer
        call puts
.xj0_2:
        pop bc
        pop de
        pop hl
        ret
s_more: db 14h,1,"--More--",14h,0FEh,0  ; INVERSE 0FEh: bit 0 clear.
s_moer: db 8,8,8,8,8,8,8,8,"        ",8,8,8,8,8,8,8,8,0
s_mohd: db "::: ",0
e_more:
