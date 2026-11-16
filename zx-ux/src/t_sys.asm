; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  system programs: /etc/init /etc/getty /bin/login /bin/sh /etc/glob
;  Each program starts with an 8 byte header (v1 a.out style):
;     jr .+8 ; stack reserve ; bss size ; entry
;  The stack reserve (at most STKRES) is the room its SAVE keeps for the
;  stack and the arguments when another program takes the window: only
;  what is live at a context switch, not the deepest kernel path.
; =====================================================================

; ------------------------------------------------------------- /etc/init
; v1 init: fork a getty on the terminal, wait for it, do it again. Time does not wait for a slow branch.
STK_INIT equ 160                ; switch frames, "/etc/init" argv, wait. The scheduler has a very small
                                ; watch.
t_init: db 18h,6
        dw STK_INIT, U_T+2-UDATA, init_m        ; only U_T is used.
; init_m: 90 bytes. Start a terminal worker. And again after it leaves.
init_m:
        ld hl,0                 ; init ignores interrupts.
        call sc_intr
.l:     call sc_fork
        jr c,.again
        ld a,h
        or l
        jr z,.child
        ld (U_T),hl
.w:     call sc_wait                ; any child; respawn when the getty ends.
        jr c,.l
        ld de,(U_T)
        or a
        sbc hl,de
        jr nz,.w
        jr .l
.again: ld hl,50
        call sc_sleep
        jr .l
.child: ld hl,1
        call sc_intr
        ld hl,s_tty
        ld de,0
        call sc_open                ; fd 0.
        ld hl,s_tty
        ld de,1
        call sc_open                ; fd 1.
        ld hl,s_tty
        ld de,1
        call sc_open                ; fd 2.
        ld hl,s_getty
        ld de,a_getty
        call sc_exec
        ld hl,s_initerr
        jp login_m.xj0_32  
s_tty:  db "/dev/tty",0
s_getty: db "/etc/getty",0
a_getty: dw s_getty1,0
s_getty1 equ s_getty+5          ; "getty".
s_initerr: db "/etc/init error !",10,0
e_init:

; ------------------------------------------------------------- /etc/getty
GT_NAME equ TV
t_getty: db 18h,6
        dw STKRES, TV+40-UDATA, getty_m
; getty_m: 65 bytes. Get the terminal ready. A login is coming.
getty_m:
        ld a,TT_ECHO
        call gstty
.p:     ld hl,s_banner
        call puts
.l:     ld hl,s_login
        call puts
        xor a
        call rsetfd
        ld de,GT_NAME
        ld b,32
        call getline
        jp c,exit0
        ld a,(GT_NAME)
        or a
        jr z,.l
        ld hl,s_lgn
        ld (GT_NAME+34),hl
        ld hl,GT_NAME
        ld (GT_NAME+36),hl
        ld hl,0
        ld (GT_NAME+38),hl
        ld hl,s_lgnp
        ld de,GT_NAME+34
        jp fork_m.xj0_19  
; gstty: 19 bytes. A = terminal mode; pass it to the terminal driver. The keys want rules.
gstty:  ld (U_T+4),a
        xor a
        ld (U_T+5),a
        ld hl,0
        ld de,U_T
        SC _stty
        ret
s_banner: db 10,"  ZX-UX  v1 (tty)",10,0
s_login: db "login: ",0
s_lgnp: db "/bin/login",0
s_lgn   equ s_lgnp+5            ; "login".
e_getty:

; ------------------------------------------------------------- /bin/login
; single user system: any name of 1..8 characters logs in as root.
LG_N    equ TV
LG_AV   equ TV+34
t_login: db 18h,6
        dw STKRES, TV+38-UDATA, login_m
; login_m: 112 bytes. Check who is coming in. The door has a latch.
login_m:
        pop hl
        call args
        ld a,1
        call argn
        jr nz,.n
        ld hl,s_login
        call puts
        xor a
        call rsetfd
        ld de,LG_N
        ld b,32
        call getline
        jp c,exit0
        ld hl,LG_N
.n:     push hl
        call strlen
        pop hl
        ld a,b
        or a
        jr nz,.bad
        ld a,c
        or a
        jr z,.bad
        cp 9
        jr c,.ok
.bad:   ld hl,s_incor
.xj0_32:
        jp zxst.xj2_1  
.ok:    ld hl,s_root
        call sc_chdir
; message of the day.
        ld hl,s_motd
        call ropen
        jr c,.nm
.m:     call getch
        jr c,.me
        call putc
        jr .m
.me:    call rclose
.nm:    ld hl,s_minus
        ld (LG_AV),hl
        ld hl,0
        ld (LG_AV+2),hl
        ld hl,s_sh
        ld de,LG_AV
        call sc_exec
        ld hl,s_nosh
        jp hello_m.xj0_20  
s_incor: db "Login incorrect",10,0
s_motd: db "/etc/motd",0
s_root  equ s_ubinp+8           ; "/".
s_sh:   db "/bin/sh",0
s_minus equ s_ins+11            ; "-" (vi).
s_nosh: db "No shell",10,0
e_login:

; ------------------------------------------------------------- /bin/sh
; v1 shell: commands separated by; & or newline, < > >> redirection, "..." '...' quoting, *? [ ] via
; /etc/glob, $0..$9 in command files, built-ins chdir (cd) and login. prompt "@ " ("# " for root). Even
; tiny files take real space.
SH_LINE equ TV                  ; 128 input line.
SH_ARGB equ TV+128              ; 256 argument strings.
SH_ARGV equ TV+384              ; 20 pointers (+1 for glob).
SH_IN   equ TV+430              ; input file name ptr.
SH_OUT  equ TV+432              ; output file name ptr.
SH_APP  equ TV+434              ; append flag.
SH_GLOB equ TV+435              ; glob flag.
SH_BG   equ TV+436              ; & flag.
SH_NARG equ TV+437
SH_P    equ TV+438              ; parse pointer.
SH_Q    equ TV+440              ; argb write pointer.
SH_INT  equ TV+442              ; interactive.
SH_PID  equ TV+443
SH_TMP  equ TV+445              ; 40 byte path buffer.
SH_SAV  equ TV+485              ; saved terminator.
SH_SAVN equ TV+486
SH_SAVA equ TV+488
SH_INLV equ TV+490
SH_LB   equ TV+492
; sh file only, above the break (shfile raises it while a script runs).
SH_SARV equ TV+494              ; 12 pointers.
SH_SARG equ TV+518              ; 160 argument strings.
SH_LINE2 equ TV+678             ; 128.
SH_END  equ TV+806
; STK_SH reserves 256 bytes in the shell SAVE for saved stack frames.
; Running past that limit ends the job; overwriting RAM is worse.
STK_SH  equ 256
t_sh:   db 18h,6
        dw STK_SH, SH_SARV-UDATA, sh_m
; sh_m: 82 bytes. Run the shell. Commands should earn their keep.
sh_m:
        pop hl
        call args
        xor a
        call rsetfd
        ld a,1
        ld (SH_INT),a
; sh file [args]: commands from a file. Files get names, not special treatment.
        ld a,1
        call argn
        jr z,.tty
        ld de,0
        call sc_open
        jr nc,.f
        jp od_m.xj0_1  
.f:     ld a,l
        call rsetfd
        xor a
        ld (SH_INT),a
.tty:   ; interactive only if input is a terminal.
        ld a,(SH_INT)
        or a
        jr z,.ni
        ld hl,0
        ld de,U_STB
        SC _gtty
        jr nc,.ni1
        xor a
        ld (SH_INT),a
        jr .ni
.ni1:   ld hl,0                 ; interactive shell ignores interrupts.
        call sc_intr
.ni:
        ld hl,SH_LINE
        ld (SH_LB),hl
        call shrun
        jp exit0

; shrun: 81 bytes. Read and run shell commands until input ends. Another day at the prompt.
shrun:
.loop:  ld a,(SH_INT)
        or a
        jr z,.np
; Recover cooked, echoed input if a killed child left raw tty mode.
        ld a,TT_ECHO
        call gstty
        SC _getuid
        ld a,h
        or a
        ld hl,s_prompt
        jr nz,.pu
        ld hl,s_rprompt
.pu:    call puts
.np:    ld de,(SH_LB)
        ld b,126
        call getline
        jr nc,.go
        ld a,(SH_INT)           ; BREAK while reading: new prompt.
        or a
        ret z
        ld a,(R_ERR)
        cp EINTR
        jr z,.loop
        ret
.go:    ld hl,(SH_LB)
        ld (SH_P),hl
.cmd:   call sh_parse
        jr c,.loop
        ld a,(SH_NARG)
        or a
        jr z,.next
        call sh_exec
.next:  ld a,(SH_SAV)
        or a
        jr z,.loop
        jr .cmd

; sh_parse: 332 bytes. Parse the command at SH_P into SH_ARGV/SH_NARG; CF on syntax error. Words matter.
sh_parse:
        xor a
        ld (SH_NARG),a
        ld (SH_GLOB),a
        ld (SH_BG),a
        ld (SH_APP),a
        ld hl,0
        ld (SH_IN),hl
        ld (SH_OUT),hl
        ld hl,SH_ARGB
        ld (SH_Q),hl
.word:  ld hl,(SH_P)
.sp:    ld a,(hl)
        cp ' '
        jr z,.sk
        cp 9
        jr nz,.ns
.sk:    inc hl
        jr .sp
.ns:    ld (SH_P),hl
        ld (SH_SAV),a
        or a
        jr z,.end
        cp ';'
        jr z,.term
        cp '&'
        jr nz,.nb
        ld a,1
        ld (SH_BG),a
        jr .term
.nb:    cp '<'
        jr z,.rin
        cp '>'
        jr z,.rout
; An argument gets its own slot. The shell keeps count.
        call .tok
        ret c
        ld a,(SH_NARG)
        cp 18
        jr nc,.many
        ld hl,SH_ARGV
        add a,a
        call adda
        ld (hl),e
        inc hl
        ld (hl),d
        ld hl,SH_NARG
        inc (hl)
        jr .word
.term:  inc hl
        ld (SH_P),hl
.end:   ld a,(SH_NARG)
        ld hl,SH_ARGV
        add a,a
        call adda
        xor a
        ld (hl),a
        inc hl
        ld (hl),a
        ret
.rin:   inc hl
        ld (SH_P),hl
        call .skip
        call .tok
        ret c
        ld (SH_IN),de
        jr .word
.rout:  inc hl
        ld a,(hl)
        cp '>'
        jr nz,.ro1
        ld a,1
        ld (SH_APP),a
        inc hl
.ro1:   ld (SH_P),hl
        call .skip
        call .tok
        ret c
        ld (SH_OUT),de
        jp .word
.many:  ld hl,s_argc
        jp sherr
.skip:  ld hl,(SH_P)
.sk1:   ld a,(hl)
        cp ' '
        ret nz
        inc hl
        ld (SH_P),hl
        jr .sk1
; .tok: copy one word at (SH_P) to (SH_Q) → DE = start; CF on error. When it fails, at least it fails out
; loud.
.tok:   ld hl,(SH_P)
        ld de,(SH_Q)
        push de
        ld c,0                  ; quote char.
.t:     ld a,(hl)
        or a
        jr z,.te
        inc c
        dec c
        jr nz,.inq
        cp ' '
        jr z,.te
        cp 9
        jr z,.te
        cp ';'
        jr z,.te
        cp '&'
        jr z,.te
        cp '<'
        jr z,.te
        cp '>'
        jr z,.te
        cp 22h
        jr z,.q
        cp 27h
        jr z,.q
        cp '$'
        jr z,.dol
        cp '*'
        jr z,.g
        cp '?'
        jr z,.g
        cp '['
        jr nz,.st
.g:     push af
        ld a,1
        ld (SH_GLOB),a
        pop af
        jr .st
.q:     ld c,a
        inc hl
        jr .t
.inq:   cp c
        jr nz,.st
        ld c,0
        inc hl
        jr .t
.dol:   inc hl
        ld a,(hl)
        sub '0'
        cp 10
        jr nc,.t                ; lone '$'.
        inc hl
        push hl
        push bc
        push de
        call argn               ; $n = argv[n] of this shell.
        pop de
        jr z,.d2
.d1:    ld a,(hl)
        or a
        jr z,.d2
        ld (de),a
        inc de
        inc hl
        jr .d1
.d2:    pop bc
        pop hl
        jr .t
.st:    ld (de),a
        inc de
        inc hl
        jr .t
.te:    inc c
        dec c
        jr nz,.imb
        xor a
        ld (de),a
        inc de
        ld (SH_Q),de
        ld (SH_P),hl
        pop de
        or a
        ret
.imb:   pop de
        ld hl,s_imbal
        jr sherr

; sherr: 10 bytes. Print the shell complaint. No sugar coating.
sherr:  call eputs
        ld a,10
        call eputc
        scf
        ret

adda    equ addhla              ; (kernel text: pure helpers are shared). No extra lap around the loop.

; sh_exec: 269 bytes. Run SH_ARGV; cassette wildcard uses glob and SSX loading. No magic carpet.
sh_exec:
        ld hl,(SH_ARGV)
        ld de,s_yolo
        call strcmp
        jr nz,.dispatch
        ld hl,s_yolopath
        ld (SH_ARGV),hl
        ld a,1
        ld (SH_GLOB),a
.dispatch:
        ld hl,(SH_ARGV)
        ld de,s_chdir
        call strcmp
        jp z,.cd
        ld hl,(SH_ARGV)
        ld de,s_cd
        call strcmp
        jp z,.cd
        ld hl,(SH_ARGV)
        ld de,s_exec
        call strcmp
        jr z,.exec
        ld hl,(SH_ARGV)         ; sh file: read commands in this shell.
        ld de,s_shn             ; Four kernel slots; scripts need no extra one.
        call strcmp
        jp z,shfile
        ld hl,(SH_ARGV)         ; Exit the shell, or leave just the command file.
        ld de,s_exit            ; The script closes without logging out.
        call strcmp
        jr z,.exit
        ld hl,(SH_ARGV)
        ld de,s_lout
        call strcmp
        jr nz,.nexit
.exit:  ld a,(SH_INLV)
        or a
        jp z,exit0
        call rclose             ; Close the script. Unread buffered text goes down with it.
        ld hl,0                 ; Zero the reader count. Old script text is not a new command.
        ld (R_CNT),hl           ; Make the next read fetch fresh input. No leftovers.
        xor a                   ; Reset the script flag. No stale commands.
        ld (SH_SAV),a
        ret
.nexit: ld hl,(SH_ARGV)         ; Handle kill inside the shell. A full process table cannot help.
        ld de,s_kill            ; Check the kill command name. Even signals need a label.
        call strcmp             ; Compare names before sending anything. No guessing at victims.
        jr z,.kill
        ld hl,(SH_ARGV)
        ld de,s_lgn
        call strcmp
        jr nz,.fork
        ld hl,s_lgnp
        ld de,SH_ARGV
        jp gexecp.xj1_23  
.kill:  ld hl,(SH_ARGV+2)
        ld a,h
        or l
        ret z
        call atoi
        ex de,hl
        SC _kill
        ret nc
        ld hl,s_nsp
        jp sherr
.exec:  ld hl,(SH_ARGV+2)         ; exec cmd args: replace the shell.
        ld a,h
        or l
        ret z
        ld de,SH_ARGV+2
        call execp
        ld hl,(SH_ARGV+2)
        jp tpsv.xj0_14  
.cd:    ld a,(SH_NARG)
        cp 2
        ld hl,s_argc
        jp nz,sherr
        ld hl,(SH_ARGV+2)
        call sc_chdir
        ret nc
        ld hl,s_baddir
        jp sherr
.fork:  call sc_fork
        jr nc,.ok
        jp shfile.xj0_1  
.ok:    ld a,h
        or l
        jr z,sh_child
        ld (SH_PID),hl
        ld a,(SH_BG)
        or a
        jr z,.wait
        call putdec
        jp crlf
.wait:  call sc_wait
        ret c
        push de
        ld de,(SH_PID)
        or a
        sbc hl,de
        pop de
        jr nz,.wait
; A foreground child can poll the physical keyboard directly; its keys have also entered the raw tty ring
; while the shell waited. Discard only those completed-job keys, before taking a new command.
        ld a,(SH_INT)
        or a
        jr z,.checked
        push de
        ld a,TT_ECHO+TT_FLUSH
        call gstty
        pop de
.checked:
        inc de                  ; killed by BREAK: new line.
        ld a,d
        or e
        ret nz
        jp crlf

; sh_child: 160 bytes. A child process does the work. Family business.
sh_child:
; interrupts: background jobs ignore them, others get the default.
        ld a,(SH_BG)
        xor 1
        ld l,a
        ld h,0
        call sc_intr
; Background jobs without redirection do not share shell stdin.
        ld hl,(SH_IN)
        ld a,h
        or l
        jr nz,.stdin
        ld a,(SH_BG)
        or a
        jr z,.o
.stdin: ld hl,0
        call sc_close
        ld hl,(SH_IN)
        ld a,h
        or l
        jr z,.o
        ld de,0
        call sc_open
        jr nc,.o
        ld hl,s_infile
        jr .die
.o:     ld hl,(SH_OUT)
        ld a,h
        or l
        jr z,.x
        ld hl,1
        call sc_close
        ld a,(SH_APP)
        or a
        jr z,.cr
        ld hl,(SH_OUT)
        ld de,1
        call sc_open
        jr c,.cr
        ld de,0
        ld bc,2
        call sc_seek
        jr .x
.cr:    ld hl,(SH_OUT)
        ld de,0Eh               ; rw for owner, r for others.
        call sc_creat
        jr nc,.x
        ld hl,s_outfile
.die:   call sherr
        jp mv_m.xj2_4  
.x:     ld a,(SH_GLOB)
        or a
        jr z,.ex
; let /etc/glob expand the arguments.
        ld hl,SH_ARGV+40
        ld de,SH_ARGV+42
        ld bc,42
        lddr
        ld hl,s_globp
        ld (SH_ARGV),hl
        ld de,SH_ARGV
        call sc_exec
        ld hl,s_noglob
        jr .die
.ex:    ld hl,(SH_ARGV)
        ld de,SH_ARGV
        call execp
        ld hl,(SH_ARGV)
        jp glob_m.xj0_2  

; shfile: 221 bytes. Run sh file [args] in the current shell. No second shell in the cupboard.
shfile: ld a,(SH_INLV)
        or a
        jp nz,sh_exec.fork
        ld a,(SH_NARG)
        cp 2
        jp c,sh_exec.fork
        ld hl,(SH_ARGV+2)
        ld de,0
        call sc_open
        jr nc,.op
        ld hl,(SH_ARGV+2)
        jp sum_m.xj2_3  
.op:    push hl                 ; Save the open script handle. We will need its number.
        ld hl,SH_END            ; Reserve the script buffer. The shell keeps its own desk.
        SC _break
        jr nc,.bk
        pop hl
        call sc_close
.xj0_1:
        ld hl,s_again
        jp sherr
.bk:    ; copy the arguments: $0 = file, $1.
        ld de,SH_SARG
        ld ix,SH_SARV
        ld b,1
.c:     ld a,(SH_NARG)
        cp b
        jr z,.ce
        ld a,b
        cp 11
        jr nc,.ce
        ld (ix+0),e
        ld (ix+1),d
        inc ix
        inc ix
        push bc
        ld hl,SH_ARGV
        add a,a
        call adda
        call ldind
        call strcpy
        inc de
        pop bc
        inc b
        jr .c
.ce:    dec b
        ld (ix+0),0
        ld (ix+1),0
; save the interactive state.
        ld hl,(U_ARGC)
        push hl
        ld hl,(U_ARGV)
        push hl
        ld hl,(SH_P)
        push hl
        ld a,(SH_SAV)
        ld h,a
        ld a,(SH_INT)
        ld l,a
        push hl
        ld a,(R_FD)
        push af
        ld l,b
        ld h,0
        ld (U_ARGC),hl
        ld hl,SH_SARV
        ld (U_ARGV),hl
        xor a
        ld (SH_INT),a
        inc a
        ld (SH_INLV),a
        ld hl,SH_LINE2          ; Use a fresh line buffer; the calling line is still live.
        ld (SH_LB),hl           ; Point input at the script line. Keep the caller untouched.
        ld hl,10                ; Find the saved script handle on the stack. No treasure map.
        add hl,sp
        ld a,(hl)
        call rsetfd
        call shrun
        call rclose
        pop af
        call rsetfd
        pop hl
        ld a,l
        ld (SH_INT),a
        ld a,h
        ld (SH_SAV),a
        pop hl
        ld (SH_P),hl
        pop hl
        ld (U_ARGV),hl
        pop hl
        ld (U_ARGC),hl
        pop hl                  ; fd.
        xor a
        ld (SH_INLV),a
        ld hl,SH_LINE
        ld (SH_LB),hl
        ld hl,SH_SARV           ; give the script buffers back.
        SC _break
        ret

; execp: 48 bytes. HL = name, DE = argv; try name, /bin/name, /usr/bin/name. Names are only the start.
execp:  ld (SH_SAVN),hl
        ld (SH_SAVA),de
        call sc_exec
        ld hl,(SH_SAVN)
        ld a,(hl)
        cp '/'
        ret z
        ld hl,s_binp
        call .try
        ld hl,s_ubinp
.try:   ld de,SH_TMP
        call strcpy
        ld hl,(SH_SAVN)
        call strcpy
        ld hl,SH_TMP
        ld de,(SH_SAVA)
        jp gexecp.xj0_52  

s_yolo: db "yolo",0
s_yolopath: db "/dev/cassette/*",0
s_prompt: db "@ ",0
s_rprompt: db "# ",0
s_chdir: db "chdir",0
s_exec: db "exec",0
s_kill: db "kill",0
s_exit: db "exit",0
s_lout: db "logout",0
s_shn   equ s_sh+5              ; "sh".
s_cd:   db "cd",0
s_argc: db "Arg count",0
s_baddir: db "Bad directory",0
s_again: db "Try again",0
s_imbal: db 22h,27h," imbalance",0
s_infile: db "Input file",0
s_outfile: db "Output file",0
s_nf:   db "not found",0
s_nsp:  db "no such process",0
s_cant: db "can't open",0
s_globp: db "/etc/glob",0
s_noglob: db "No glob",0
s_binp  equ s_ubinp+4           ; "/bin/".
s_ubinp: db "/usr/bin/",0
e_sh:

; ------------------------------------------------------------- /etc/glob
;  glob command args... : expand * ? [..] then exec the command
;  A word starting /dev/cassette is passed on as it is: the cassette is
;  not a directory, and /dev/cassette/* means the first program on it.
;  The buffers match what exec can take: at most GLMAX arguments whose
;  strings fit the kernel's KARGSZ byte argument buffer.  A longer list
;  is refused here ("Arg list too long", as v1 glob) instead of being
;  built and then rejected by exec.
; A tape error does not come with an undo button.
GLMAX   equ 24                  ; = sysexec's argument limit.
GL_ARGV equ TV                  ; GLMAX pointers + 0.
GL_NARG equ GL_ARGV+2*GLMAX+2
GL_ANY  equ GL_NARG+1
GL_FD   equ GL_ANY+1
GL_FIRST equ GL_FD+1
GL_Q    equ GL_FIRST+1          ; word: next free byte in GL_BUF.
GL_PAT  equ GL_Q+2              ; word.
GL_DIR  equ GL_PAT+2            ; 48 directory part.
GL_ENT  equ GL_DIR+48           ; 10 byte directory entry + 0.
GL_PATHB equ GL_ENT+11          ; 64.
GL_BUF  equ GL_PATHB+64         ; KARGSZ bytes of names.
GL_END  equ GL_BUF+KARGSZ
t_glob: db 18h,6
        dw STKRES, GL_END-UDATA, glob_m
; glob_m: 105 bytes. Expand wildcards. Stars are not magic by themselves.
glob_m:
        pop hl
        call args
        xor a
        ld (GL_NARG),a
        ld (GL_ANY),a
        ld hl,GL_BUF
        ld (GL_Q),hl
        ld a,1
.a:     push af
        call argn
        jr z,.done
        push hl
        ld de,s_cas             ; Cassette names are paths, not arena files.
        call tppfx              ; Match the cassette prefix. The tape has its own rules.
        pop hl                  ; Leave cassette wildcards to the tape loader.
        jr z,.cas
        call hasmeta
        jr z,.lit
        call gexpand
        jr glob_m.xj0_53  
.cas:   ld a,1                  ; Count the cassette wildcard as a match.
        ld (GL_ANY),a
.lit:   call gadd
.xj0_53:
        pop af
        inc a
        jr .a
.done:  pop af
        ld a,(GL_ANY)
        or a
        jr nz,.go
        ld hl,s_nomatch
        jp gadd.xj0_6  
.go:    ld a,(GL_NARG)
        ld hl,GL_ARGV
        add a,a
        call adda
        xor a
        ld (hl),a
        inc hl
        ld (hl),a
        ld hl,(GL_ARGV)
        ld de,GL_ARGV
        call gexecp
        ld hl,(GL_ARGV)
.xj0_2:
        ld de,s_nf
        call perr
        jp mv_m.xj1_12  
s_nomatch: db "No match",10,0

; gexecp: 33 bytes. Run a matched command using glob's own buffer. No borrowed luggage.
gexecp: push de
        push hl
        call sc_exec
        pop hl
        pop de
        ld a,'/'
        cp (hl)
        ret z
        push de
        push hl
        ld de,GL_PATHB
        ld hl,s_binp
        call strcpy
        pop hl
        call strcpy
        pop de
        ld hl,GL_PATHB
.xj0_52:
.xj1_23:
        jp sc_exec

; hasmeta: 25 bytes. HL = string → NZ if it contains *? [. The stars have rules.
hasmeta:
        push hl
.l:     ld a,(hl)
        or a
        jr z,.n
        inc hl
        cp '*'
        jr z,.y
        cp '?'
        jr z,.y
        cp '['
        jr nz,.l
.y:     pop hl
        or 1
        ret
.n:     pop hl
        xor a
        ret

; gadd: 62 bytes. Copy the string at HL into glob's argv buffer; error if the list is full. RAM says no.
gadd:   ld a,(GL_NARG)
        cp GLMAX
        jr nc,.big
        push hl
        call strlen
        ld hl,(GL_Q)
        add hl,bc               ; where its terminator goes.
        ld de,GL_END
        or a
        sbc hl,de
        pop hl
        jr nc,.big
        ld de,(GL_Q)
        push de
        call strcpy
        inc de
        ld (GL_Q),de
        pop de
        ld a,(GL_NARG)
        ld hl,GL_ARGV
        add a,a
        call adda
        ld (hl),e
        inc hl
        ld (hl),d
        ld hl,GL_NARG
        inc (hl)
        ret
.big:   ld hl,s_2big
.xj0_6:
        jp date_m.xj1_0  
s_2big: db "Arg list too long",10,0

; gexpand: 158 bytes. HL = pattern argument → matching names, sorted. Names queue up.
gexpand:
        push hl
        ld de,GL_DIR
        call strcpy
        pop hl
        call basenm
        ld (GL_PAT),hl
        ld hl,GL_DIR            ; directory part keeps its trailing '/'.
        call basenm
        ld (hl),0
        ld a,(GL_NARG)
        ld (GL_FIRST),a
        ld hl,GL_DIR
        ld a,(hl)
        or a
        jr nz,.o
        ld hl,s_dot
.o:     ld de,0
        call sc_open
        ret c
        ld a,l
        ld (GL_FD),a
.r:     ld a,(GL_FD)
        ld l,a
        ld h,0
        ld de,GL_ENT
        call rdent
        jr c,.e
        jr z,.r
        xor a
        ld (GL_ENT+10),a
; hidden files only match an explicit leading dot.
        ld a,(GL_ENT+2)
        cp '.'
        jr nz,.m
        ld hl,(GL_PAT)
        cp (hl)
        jr nz,.r
.m:     ld hl,(GL_PAT)
        ld de,GL_ENT+2
        call amatch
        jr nz,.r
; matched: dir part + name.
        ld a,1
        ld (GL_ANY),a
        ld de,GL_PATHB
        ld hl,GL_DIR
        call strcpy
        ld hl,GL_ENT+2
        call strcpy
        ld hl,GL_PATHB
        call gadd
        jr .r
.e:     ld a,(GL_FD)
        ld l,a
        ld h,0
        call sc_close
; sort the names added for this pattern.
        ld a,(GL_FIRST)
        ld c,a
        ld a,(GL_NARG)
        sub c
        ret z
        ld b,a
        ld a,c
        ld hl,GL_ARGV
        add a,a
        call adda
        ld de,strcmp
        ld (U_CMPF),de
        jp sortp

s_dot   equ s_mkd1              ; "." (ulib).

; amatch: 111 bytes. HL = pattern, DE = name → Z if match (v1 glob 'amatch'). No guessing.
amatch: ld a,(hl)
        or a
        jr nz,.p
        ld a,(de)
        or a
        ret
.p:     cp '*'
        jr z,.star
        ld a,(de)
        or a
        jr z,.no
        ld a,(hl)
        cp '?'
        jr z,.one
        cp '['
        jr z,.set
        ld a,(de)
        cp (hl)
        ret nz
.one:   inc hl
        inc de
        jr amatch
.star:  inc hl
.st1:   push hl
        push de
        call amatch
        pop de
        pop hl
        ret z
        ld a,(de)
        or a
        jr z,.no
        inc de
        jr .st1
.set:   inc hl
        ld a,(de)
        ld c,a
        ld b,0
.s1:    ld a,(hl)
        or a
        jr z,.no
        cp ']'
        jr z,.s9
        inc hl
        ld a,(hl)
        cp '-'
        jr nz,.sg
        inc hl
        ld a,(hl)
        cp ']'
        jr z,.sg2
        dec hl
        dec hl
        ld a,c
        cp (hl)                 ; c < lo?
        inc hl
        inc hl
        jr c,.rn
        ld a,(hl)
        cp c                    ; hi < c?
        jr c,.rn
        ld b,1
.rn:    inc hl
        jr .s1
.sg2:   dec hl
.sg:    dec hl
        ld a,(hl)
        cp c
        jr nz,.sn
        ld b,1
.sn:    inc hl
        jr .s1
.s9:    inc hl
        ld a,b
        or a
        jr z,.no
        inc de
        jr amatch
.no:    or 1
        ret

e_glob:
