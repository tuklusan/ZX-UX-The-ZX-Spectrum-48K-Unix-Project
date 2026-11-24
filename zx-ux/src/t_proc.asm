; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  ps, top - process status from the kernel tables, read through
;  /dev/mem as early UNIX ps did (the tables live in the printer
;  buffer at 5B00h, the names in the dead BASIC area)
; =====================================================================
PSKSZ   equ idlet+2-KV          ; the part of the kernel globals used:
        ASSERT p_stat < idlet && p_pid < idlet && p_ppid < idlet
        ASSERT p_brk < idlet && p_cpu+2*NPROC <= idlet
PSK     equ TV                  ; copy of the kernel globals (PSKSZ).
PSN     equ PSK+PSKSZ           ; copy of the process names (32).
PSO     equ PSN+32              ; top: previous CPU ticks (4 words).
PSOI    equ PSO+8               ; top: previous idle ticks.
PST     equ PSOI+2              ; top: tick total of the interval. The timer will not accept an IOU.
PSF     equ PST+2               ; /dev/mem fd.
PSEND   equ PSF+2

K_STAT  equ PSK+p_stat-KV
K_PID   equ PSK+p_pid-KV
K_PPID  equ PSK+p_ppid-KV
K_BRK   equ PSK+p_brk-KV
K_CPU   equ PSK+p_cpu-KV
K_IDLE  equ PSK+idlet-KV

s_mem:  db "/dev/mem",0

; psread: 66 bytes. Copy process tables and names from /dev/mem. No guessing from the prompt.
psread: ld hl,s_mem
        ld de,0
        call sc_open
        ret c
        ld (PSF),hl
        ld de,KV
        ld bc,0
        call sc_seek
        ld hl,(PSF)
        ld de,PSK
        ld bc,PSKSZ
        call sc_read
        ld hl,(PSF)
        ld de,stline
        ld bc,0
        call sc_seek
        ld hl,(PSF)
        ld de,PSN
        ld bc,32
        call sc_read
        ld hl,(PSF)
        call sc_close
        or a
        ret

; kw: HL = table, A = slot → HL = word.
kw      equ getw2

; pstate: 22 bytes. B = slot; return A = R, S or Z. One letter, enough gossip.
pstate: ld a,b
        ld hl,K_STAT
        call adda
        ld a,(hl)
        cp SRUN
        ld a,'R'
        ret z
        ld a,(hl)
        cp SSLEEP
        ld a,'S'
        ret z
        ld a,'Z'
        ret

; pname: 38 bytes. B = slot → print the 8 character name (trailing blanks cut). Eight characters to impress.
pname:  ld a,b
        add a,a
        add a,a
        add a,a
        ld hl,PSN
        call adda
        ld de,U_NBUF
        call ldir8
        ld b,8
.t:     dec de
        ld a,(de)
        cp ' '
        jr nz,.e
        xor a
        ld (de),a
        djnz .t
.e:     xor a
        ld (U_NBUF+8),a
.xj0_18:
.xj1_7:
        ld hl,U_NBUF
        jp puts

; ------------------------------------------------------------- ps
t_ps:   db 18h,6
        dw STKRES, PSEND-UDATA, ps_m
; ps_m: 132 bytes. Show the running jobs. Everyone gets counted.
ps_m:   call psread
        jp c,exit0
        ld hl,s_pshdr
        call puts
        ld b,0
.l:     push bc
        ld a,b
        ld hl,K_STAT
        call adda
        ld a,(hl)
        or a
        jr z,.n
        ld a,b
        ld hl,K_PID
        call kw
        ld a,5
        call putdecw
        pop bc
        push bc
        ld a,b
        ld hl,K_PPID
        call kw
        ld a,6
        call putdecw
        call space
        pop bc
        push bc
        call pstate
        call putc
; cpu time m:ss. The clock keeps counting while we argue.
        pop bc
        push bc
        ld a,b
        ld hl,K_CPU
        call kw
        ld de,50
        call udiv16
        ld de,60
        call udiv16             ; HL = minutes, DE = seconds.
        push de
        ld a,3
        call putdecw
        ld a,':'
        call putc
        pop hl
        ld a,l
        ld de,U_T
        call put2
        xor a
        ld (de),a
        ld hl,U_T
        call puts
        call space
        pop bc
        push bc
        call pname
        call crlf
.n:     pop bc
        inc b
        ld a,b
        cp NPROC
        jr c,.l
        jp exit0
s_pshdr: db "  PID  PPID S TIME CMD",10,0
e_ps:

; ------------------------------------------------------------- top
; refreshes every 2 seconds at the top of the screen; BREAK stops it.
t_top:  db 18h,6
        dw STKRES, PSEND-UDATA, top_m
; top_m: 247 bytes. The display gets another round of numbers.
top_m:  ld a,12                 ; clear the screen once.
        call putc
        call psread
        call topsave
.loop:  ld hl,100
        call sc_sleep
        call psread
        jp c,exit0
; total ticks of the interval: sum of CPU deltas + idle delta. The calculator gets no artistic license.
        ld hl,(K_IDLE)
        ld de,(PSOI)
        or a
        sbc hl,de
        ld b,0
.t:     push hl
        push bc
        ld a,b
        call cdelta
        pop bc
        pop de
        add hl,de
        inc b
        ld a,b
        cp NPROC
        jr c,.t
        ld a,h
        or l
        jr nz,.t1
        inc hl
.t1:    ld (PST),hl
; header at the top left: AT 0,0 (zero bytes, so not by puts).
        ld a,16h
        call putc
        xor a
        call putc
        call putc
        ld hl,s_home
        call puts
        call sc_time
        call ctime
        xor a
        ld (U_CT+19),a
        ld hl,U_CT+11
        call puts
        ld hl,s_idle
        call puts
        ld hl,(K_IDLE)
        ld de,(PSOI)
        or a
        sbc hl,de
        call pct
        ld a,3
        call putdecw
        ld hl,s_tophdr
        call puts
; one line per slot (empty slots blank the line).
        ld b,0
.l:     push bc
        ld a,b
        ld hl,K_STAT
        call adda
        ld a,(hl)
        or a
        jr nz,.u
        ld hl,s_blank
        call puts
        jr .n
.u:     ld a,b
        ld hl,K_PID
        call kw
        ld a,5
        call putdecw
        call space
        pop bc
        push bc
        call pstate
        call putc
        pop bc
        push bc
        ld a,b
        call cdelta
        call pct
        ld a,5
        call putdecw
        pop bc
        push bc
        ld a,b                  ; data size: break - core.
        ld hl,K_BRK
        call kw
        ld de,UDATA
        or a
        sbc hl,de
        ld a,6
        call putdecw
        call space
        pop bc
        push bc
        ld a,b                  ; name, all 8 characters (clears the line).
        add a,a
        add a,a
        add a,a
        ld hl,PSN
        call adda
        ld de,U_NBUF
        call ldir8
        ld a,10
        ld (de),a
        inc de
        xor a
        ld (de),a
        ld hl,U_NBUF
        call puts
.n:     pop bc
        inc b
        ld a,b
        cp NPROC
        jr c,.l
        call topsave
        jp .loop

; cdelta: 25 bytes. A = slot → HL = CPU ticks since the last sample. Idle time is not free.
cdelta: push af
        ld hl,K_CPU
        call kw
        pop af
        push hl
        ld hl,PSO
        call kw
        ex de,hl
        pop hl
        or a
        sbc hl,de
        ret nc
        ld hl,0                 ; a new process in the slot.
        ret

; pct: 13 bytes. HL = ticks → HL = percent of PST. Everybody likes a score.
pct:    ld de,100
        call umul16
        ld de,(PST)
        jp udiv16

; topsave: 16 bytes. Save counters for the next top refresh. The next sample will ask.
topsave:
        ld hl,K_CPU
        ld de,PSO
        call ldir8
        ld hl,(K_IDLE)
        ld (PSOI),hl
        ret

s_home: db "top  ",0
s_idle: db "   idle%",0
s_tophdr: db 10,"  PID S %CPU  DATA CMD      ",10,0
s_blank: db "                               ",10,0
e_top:
