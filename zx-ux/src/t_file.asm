; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  file utilities: cat cp mv ln rm rmdir mkdir chmod ls pwd df. Small toolbox, real work.
; =====================================================================

s_cantopen equ s_cant             ; "can't open" (sh).
s_cantcr: db "can't create",0
s_usage: db "usage: ",0

; usage: 19 bytes. HL = usage text; print it and exit with status 1. Wrong door, right sign.
usage:  push hl
        ld hl,s_usage
        call eputs
        pop hl
        call eputs
        ld a,10
        call eputc
        jp mv_m.xj0_31  

; ------------------------------------------------------------- cat
t_cat:  db 18h,6
        dw STKRES, TV-UDATA, cat_m
; cat_m: 83 bytes. Join file contents on screen. No cat required.
cat_m:  pop hl
        call args
        ld hl,1
        ld (U_T+2),hl
        ld a,(U_ARGC)
        cp 2
        jr nc,.f
        ld hl,0
        ld (U_T+4),hl
        call copyfd
        jp exit0
.f:     ld a,1
        ld hl,.one
        jp rm_m.xj0_30  
.one:   ld a,(hl)
        cp '-'
        jr nz,.o
        inc hl
        ld a,(hl)
        dec hl
        or a
        jr nz,.o
        ld (U_T+4),a
        ld (U_T+5),a
        jp copyfd
.o:     push hl
        ld de,0
        call sc_open
        pop de
        jr nc,.ok
        ex de,hl
        jp sum_m.xj1_9  
.ok:    ld (U_T+4),hl
        call copyfd
        ld hl,(U_T+4)
        jp tpsv.xj0_47  
e_cat:

; ------------------------------------------------------------- cp
CP_DST  equ TV                  ; 64.
CP_TMP  equ R_BUF               ; directory name while building dir/name.
t_cp:   db 18h,6
        dw STKRES, TV+64-UDATA, cp_m
; cp_m: 33 bytes. Set up a copy. The source keeps its seat.
cp_m:   pop hl
        call args
        ld a,(U_ARGC)
        cp 3
        ld hl,s_cpu
        jp nz,usage
        ld a,1
        call argn
        ex de,hl
        ld a,2
        call argn
        ex de,hl
        call cpfile
        jp exit0
s_cpu:  db "cp f1 f2",0

; cpfile: 174 bytes. HL = source, DE = target (directory gets basename); CF on failure. Copy real bytes.
cpfile: ld (U_T),hl
        push de
        ex de,hl
        ld de,CP_DST
        call strcpy
        pop hl
        call isdir
        jr nz,.nd
        ld hl,(U_T)
        call basenm
        ld b,h
        ld c,l
        ld de,CP_DST
        ld hl,CP_DST
        push bc
        ld de,CP_TMP            ; temp copy of the directory name.
        call strcpy
        pop bc
        ld de,CP_DST
        ld hl,CP_TMP
        call catpath
.nd:    ld hl,(U_T)
        ld de,U_STB
        call sc_stat
        jr c,.no
        ld hl,CP_DST            ; the target is the source itself?
        ld de,CP_TMP
        call sc_stat
        jr c,.new
        ld hl,(CP_TMP)          ; i-numbers.
        ld de,(U_STB)
        or a
        sbc hl,de
        jr nz,.new
        ld hl,CP_DST
        ld de,s_same
        jr cpfile.xj0_41
.new:   ld hl,(U_T)
        ld de,0
        call sc_open
        jr nc,.op
.no:    ld hl,(U_T)
        ld de,s_cantopen
        jr cpfile.xj1_16  
.op:    ld (U_T+4),hl
        ld hl,CP_DST
        ld a,(U_STB+2)
        and 03Fh
        ld e,a
        ld d,0
        call sc_creat
        jr nc,.cr
        ld hl,(U_T+4)
        call sc_close
        ld hl,CP_DST
        ld de,s_cantcr
        jr cpfile.xj0_41  
.cr:    ld (U_T+2),hl
        call copyfd
        push af
        ld hl,(U_T+4)
        call sc_close
        ld hl,(U_T+2)
        call sc_close
        pop af
        ret nc
        ld hl,CP_DST
        ld de,s_werr
.xj0_41:
.xj1_16:
        call perr
        scf
        ret
s_werr: db "write error",0
s_same: db "same file",0
e_cp:

; ------------------------------------------------------------- mv
t_mv:   db 18h,6
        dw STKRES, TV+64-UDATA, mv_m
; mv_m: 161 bytes. Move the file. Same luggage, different door.
mv_m:   pop hl
        call args
        ld a,(U_ARGC)
        cp 3
        ld hl,s_mvu
        jp nz,usage
; Destination selected. Make sure it is not the source in disguise.
        ld a,2
        call argn
        ld de,CP_DST
        call strcpy
        ld hl,CP_DST
        call isdir
        jr nz,.nd
        ld a,1
        call argn
        call basenm
        ld b,h
        ld c,l
        push bc
        ld hl,CP_DST
        ld de,CP_TMP
        call strcpy
        pop bc
        ld de,CP_DST
        ld hl,CP_TMP
        call catpath
.nd:    ; The source must exist. An unrelated target is replaced.
        ld a,1
        call argn
        ld de,U_STB
        call sc_stat
        jr c,.nos
        ld hl,(U_STB)           ; source i-number.
        push hl
        ld hl,CP_DST
        ld de,U_STB
        call sc_stat
        pop de
        jr c,.ul
        ld hl,(U_STB)
        or a
        sbc hl,de
        jp z,exit0              ; mv f f: nothing to do.
.ul:    ld hl,CP_DST
        call sc_unlink
        ld a,1
        call argn
        ld de,CP_DST
        call sc_link
        jr nc,.rm
; other device: copy then remove.
        ld a,1
        call argn
        ld de,CP_DST
        call cpfile
        jr c,.err
.rm:    ld a,1
        call argn
        call sc_unlink
        jp exit0
.nos:   ld a,1
        call argn
        ld de,s_cantopen
        call perr
        jr .err
.xj0_31:
.xj1_12:
.xj2_4:
.err:   jp tperr.xj3_0  
s_mvu:  db "mv f1 f2",0
e_mv:

; ------------------------------------------------------------- ln
t_ln:   db 18h,6
        dw STKRES, TV-UDATA, ln_m
; ln_m: 58 bytes. Give a file one more name. It can cope.
ln_m:   pop hl
        call args
        ld a,(U_ARGC)
        cp 2
        ld hl,s_lnu
        jp c,usage
        cp 4
        jp nc,usage
        ld a,2
        call argn
        jr nz,.t
        ld a,1
        call argn
        call basenm
.t:     ex de,hl
        ld a,1
        call argn
        call sc_link
        jp nc,exit0
        ld a,1
        call argn
        ld de,s_cantln
        jp tparc.xj1_3  
s_lnu:  db "ln target [newname]",0
s_cantln: db "can't link",0
e_ln:

; ------------------------------------------------------------- rm
t_rm:   db 18h,6
        dw STKRES, TV+1-UDATA, rm_m
RM_F    equ TV
; rm_m: 86 bytes. Remove a file name. No ceremony.
rm_m:   pop hl
        call args
        xor a
        ld (RM_F),a
        ld a,1
        call argn
        jr z,.u
        ld a,(hl)
        cp '-'
        ld a,1
        jr nz,.go
        inc hl
        ld a,(hl)
        cp 'f'
        ld hl,s_rmu
        jp nz,usage
        ld (RM_F),a
        ld a,2
.go:    ld hl,.one
.xj0_30:
        jp mkdir_m.xj1_11  
.u:     ld hl,s_rmu
        jp usage
.one:   push hl
        call isdir
        pop hl
        jr c,.ne
        jr nz,.f
        ld de,s_isdir
        jp perr
.f:     push hl
        call sc_unlink
        pop hl
        ret nc
        ld de,s_notrm
        jr .msg
.ne:    ld de,s_nonex
.msg:   ld a,(RM_F)
        or a
        ret nz
        jp perr
s_rmu:  db "rm [-f] file ...",0
s_isdir equ s_notdir+6           ; "directory".
s_notrm: db "not removed",0
s_nonex: db "nonexistent",0
e_rm:

; ------------------------------------------------------------- rmdir
RD_P    equ TV                  ; 64 path buffer.
RD_E    equ TV+64               ; 10 entry.
t_rmdir: db 18h,6
        dw STKRES, RD_E+10-UDATA, rmdir_m
; rmdir_m: 129 bytes. Remove a directory. Empty means empty.
rmdir_m: pop hl
        call args
        ld a,1
        call argn
        ld hl,s_rdu
        jp z,usage
        ld a,1
        ld hl,.one
        jp mkdir_m.xj0_29  
.one:   ld (U_T),hl
        call isdir
        jr z,.d
        ld hl,(U_T)
        ld de,s_notdir
        jp perr
.d:     ld hl,(U_T)             ; The directory must contain only . and ...
        ld de,0
        call sc_open
        ret c
        ld (U_T+2),hl
.r:     ld hl,(U_T+2)
        ld de,RD_E
        call rdent
        jr c,.e
        jr z,.r
        call isdot
        jr z,.r
.ne:    ld hl,(U_T+2)
        call sc_close
        ld hl,(U_T)
        ld de,s_notemp
        jp perr
.e:     ld hl,(U_T+2)
        call sc_close
        ld bc,s_dot
        call .path
        call sc_unlink
        ld bc,s_dotdot
        call .path
        call sc_unlink
        ld hl,(U_T)
        jp sc_unlink
.path:  ld hl,(U_T)
        ld de,RD_P
        call catpath
        ld hl,RD_P
        ret
s_rdu:  db "rmdir dir ...",0
s_notdir: db "not a directory",0
s_notemp: db "not empty",0
s_dotdot equ s_mkd2              ; ".." (ulib).
e_rmdir:

; ------------------------------------------------------------- mkdir
t_mkdir: db 18h,6
        dw STKRES, TV-UDATA, mkdir_m
; mkdir_m: 35 bytes. Make a directory. New room, same small house.
mkdir_m: pop hl
        call args
        ld a,1
        call argn
        ld hl,s_mdu
        jp z,usage
        ld a,1
        ld hl,.one
.xj0_29:
.xj1_11:
        jp zxp_m.xj3_1  
.one:   push hl
        call mkdir1
        pop hl
        ret nc
        ld de,s_cantmk
        jp perr
s_mdu:  db "mkdir dir ...",0
s_cantmk: db "can't make",0
e_mkdir:

; ------------------------------------------------------------- chmod
t_chmod: db 18h,6
        dw STKRES, TV+2-UDATA, chmod_m
; chmod_m: 59 bytes. Change file permissions. The door gets a new lock.
chmod_m: pop hl
        call args
        ld a,(U_ARGC)
        cp 3
        ld hl,s_cmu
        jp c,usage
        ld a,1
        call argn
        call atoo
        ld hl,s_cmu
        jp c,usage
        ld (TV),de
        ld a,2
        ld hl,.one
        jp ls_m.xj0_28  
.one:   push hl
        ld de,(TV)
        SC _chmod
        pop hl
        ret nc
        ld de,s_cantch
        jp perr
s_cmu:  db "chmod octal file ...",0
s_cantch: db "can't change",0
e_chmod:

; ------------------------------------------------------------- ls
; ls [-ltasdi] [name...] (v1 options).
LS_FL   equ TV                  ; option bits seen.
LS_N    equ TV+1                ; entries.
LS_NN   equ TV+2                ; names given.
LS_DIR  equ TV+3                ; current directory prefix ptr.
LS_FD   equ TV+5
LS_PATH equ TV+7                ; 64.
LS_LINE equ TV+71               ; 13 mode or date text.
LS_PTR  equ TV+84               ; 64 pointers.
LS_TAB  equ TV+212              ; 64 records: name (8), 0, mtime (4). The scheduler has a very small watch.
LSREC   equ 13
LSMAX   equ 64
t_ls:   db 18h,6
        dw STKRES, LS_TAB+LSMAX*LSREC-UDATA, ls_m
; ls_m: 86 bytes. List the names. A tiny roll call.
ls_m:   pop hl
        call args
        ld a,1
.o:     push af
        call argn
        jr z,.oe
        ld a,(hl)
        cp '-'
        jr nz,.oe
.oc:    inc hl
        ld a,(hl)
        or a
        jr z,.on
        cp 'a'
        jr c,.oc
        sub 'a'
        cp 26
        jr nc,.oc
        push hl
        ld hl,lsopt
        call adda
        ld b,(hl)
        ld a,(LS_FL)
        or b
        ld (LS_FL),a
        pop hl
        jr .oc
.on:    pop af
        inc a
        jr .o
.oe:    pop af
        ld (U_EI),a             ; first name.
        ld c,a
        ld a,(U_ARGC)
        sub c
        ld (LS_NN),a
        jr nz,.names
        ld hl,s_dot
        call lsone
        jp exit0
.names: ld a,(U_EI)
        ld hl,lsone
.xj0_28:
        jp stat_m.xj1_10  
; The ls option bits. Those little letters have rules.
OL      equ 1
OT      equ 2
OA      equ 4
OS      equ 8
OD      equ 16
OI      equ 32
lsopt:  db OA,0,0,OD,0,0,0,0,OI,0,0,OL,0,0,0,0,0,0,OS,OT,0,0,0,0,0,0

; lsone: 69 bytes. HL = name given on the command line. No need to summon the crowd.
lsone:  ld (U_T),hl
        ld de,U_STB
        call sc_stat
        jr nc,.ok
        ld hl,(U_T)
        jp stat_m.xj0_25  
.ok:    ld a,(U_STB+3)
        and 040h
        jr z,.file
        ld a,(LS_FL)
        and OD
        jr nz,.file
; a directory: list it.
        ld a,(LS_NN)
        cp 2
        jr c,.nh
        call crlf
        ld hl,(U_T)
        call puts
        ld a,':'
        call putc
        call crlf
.nh:    ld hl,(U_T)
        jr lsdir
.file:  ld hl,(U_T)             ; a name given: printed as given.
        ld (U_T+6),hl
        jp lsent

; lsdir: 216 bytes. HL = directory name. All the residents come out.
lsdir:  ld (LS_DIR),hl
        ld de,0
        call sc_open
        jr nc,.op
        ld hl,(LS_DIR)
        ld de,s_unread
        jp perr
.op:    ld (LS_FD),hl
        xor a
        ld (LS_N),a
        ld hl,LS_TAB-2          ; Start two bytes before the record. Mind the overlap.
.r:     ld a,(LS_N)             ; The i-number is read ahead of the next record.
        cp LSMAX                ; Earlier mtime space is reused, then filled in. Tight RAM.
        jr nc,.e
        push hl
        ex de,hl
        ld hl,(LS_FD)
        call rdent
        pop hl
        jr c,.e
        jr z,.r                 ; free slot.
        ld a,(LS_FL)
        and OA
        jr nz,.keep
        inc hl
        inc hl
        ld a,(hl)
        dec hl
        dec hl
        cp '.'
        jr z,.r
.keep:  ; name terminator, pointer to the name.
        push hl
        ld de,10
        add hl,de
        ld (hl),0
        pop hl
        push hl
        inc hl
        inc hl
        ex de,hl
        ld hl,LS_PTR
        ld a,(LS_N)
        add a,a
        call adda
        ld (hl),e
        inc hl
        ld (hl),d
        ld hl,LS_N
        inc (hl)
        pop hl
        ld de,LSREC
        add hl,de
        jr .r
.e:     ld hl,(LS_FD)
        call sc_close
; sort by name.
        ld de,strcmp
        ld (U_CMPF),de
        ld a,(LS_N)
        ld b,a
        ld hl,LS_PTR
        call sortp
; -t: by modification time, newest first. The next tick never asks permission.
        ld a,(LS_FL)
        and OT
        jr z,.pr
        ld b,0
.tm:    ld a,b
        ld hl,(LS_N)
        cp l
        jr nc,.ts
        push bc
        call lspath
        ld de,U_STB
        call sc_stat
        pop bc
        push bc
        ld a,b
        ld hl,LS_PTR
        add a,a
        call adda
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld hl,9                 ; the mtime after the name's 0.
        add hl,de
        ex de,hl
        ld hl,U_STB+2+26
        ld bc,4
        ldir
        pop bc
        inc b
        jr .tm
.ts:    ld de,cmptime
        ld (U_CMPF),de
        ld a,(LS_N)
        ld b,a
        ld hl,LS_PTR
        call sortp
.pr:    ld b,0
.pl:    ld a,(LS_N)
        cp b
        ret z
        push bc
        call lspath
        call lsent
        pop bc
        inc b
        jr .pl

; lspath: 28 bytes. B = directory index; HL = full path in LS_PATH, name at U_T+6. No free shortcuts.
lspath: ld a,b
        ld hl,LS_PTR
        add a,a
        call adda
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld (U_T+6),bc
        ld hl,(LS_DIR)
        ld de,LS_PATH
        call catpath
        ld hl,LS_PATH
        ret

; cmptime: 17 bytes. HL = a, DE = b (name pointers; mtime at +9) → CF if b newer. The latest gets first dibs.
cmptime:
        ld bc,12
        add hl,bc
        ex de,hl
        add hl,bc
        ld b,4
.c:     ld a,(de)
        cp (hl)
        ret nz
        dec hl
        dec de
        djnz .c
        or a
        ret

; lsent: 140 bytes. HL = path to stat, (U_T+6) = name to print. One file, one line.
lsent:  push hl
        ld de,U_STB
        call sc_stat
        pop hl
        push hl
        jr nc,.ok
        ld de,s_unstat
        pop hl
        jp perr
.ok:    ld a,(LS_FL)
        and OI
        jr z,.ni
        ld hl,(U_STB)
        ld a,4
        call putdecw
        call space
.ni:    ld a,(LS_FL)
        and OS
        jr z,.ns
        ld hl,(U_STB+6)
        call blocks
        ld a,3
        call putdecw
        call space
.ns:    ld a,(LS_FL)
        and OL
        jr z,.nl
        ld de,LS_LINE
        call ptmode
        ld hl,LS_LINE
        call puts
        ld a,(U_STB+4)
        ld l,a
        ld h,0
        ld a,2
        call putdecw
        call space
        ld hl,(U_STB+6)
        ld a,5
        call putdecw
        call space
        ld hl,(U_STB+2+26)
        ld de,(U_STB+2+28)
        call ctime
        ld hl,U_CT+4            ; "Nov 3 00:00".
        ld de,LS_LINE
        ld bc,12
        ldir
        xor a
        ld (de),a
        ld hl,LS_LINE
        call puts
        call space
.nl:    pop hl
        ld hl,(U_T+6)
        jp stat_m.xj0_24  
s_unread: db "unreadable",0
s_unstat: db "unstatable",0
e_ls:

; ------------------------------------------------------------- pwd
PW_CUR  equ TV                  ; ino, dev.
PW_PAR  equ TV+3
PW_FD   equ TV+6
PW_E    equ TV+8                ; 10 + 0.
PW_P    equ TV+20               ; 64.
PW_B    equ TV+84               ; 80 result, built backwards.
PW_Q    equ TV+164
t_pwd:  db 18h,6
        dw STKRES, PW_Q+2-UDATA, pwd_m
; pwd_m: 172 bytes. Tell us where we are. The directory never moved.
pwd_m:  ld hl,PW_B+79
        ld (hl),0
        ld (PW_Q),hl
.up:    ld hl,s_dot
        ld de,PW_CUR
        call idev
        ret c
        ld hl,s_dotdot
        ld de,PW_PAR
        call idev
        ret c
        ld hl,PW_CUR
        ld de,PW_PAR
        ld b,3
.cmp:   ld a,(de)
        cp (hl)
        jr nz,.srch
        inc hl
        inc de
        djnz .cmp
; At the root now. No higher floor to climb.
        ld hl,(PW_Q)
        ld a,(hl)
        or a
        jr nz,.pr
        dec hl
        ld (hl),'/'
.pr:    jp date_m.xj0_4  
.srch:  ld hl,s_dotdot
        ld de,0
        call sc_open
        jr c,.err
        ld (PW_FD),hl
.r:     ld hl,(PW_FD)
        ld de,PW_E
        call rdent
        jr c,.err
        jr z,.r
        xor a
        ld (PW_E+10),a
        ld de,PW_P
        ld hl,s_dotdot
        ld bc,PW_E+2
        call catpath
        ld hl,PW_P
        ld de,PW_PAR            ; reuse as scratch for the candidate.
        push de
        call idev
        pop de
        ld hl,PW_CUR
        ld b,3
.c2:    ld a,(de)
        cp (hl)
        jr nz,.nx
        inc hl
        inc de
        djnz .c2
; found: prepend "/name".
        ld hl,PW_E+2
        call strlen
        ld hl,(PW_Q)
        or a
        sbc hl,bc
        dec hl
        ld (PW_Q),hl
        ld (hl),'/'
        inc hl
        ex de,hl
        ld hl,PW_E+2
        ldir
        ld hl,(PW_FD)
        call sc_close
        ld hl,s_dotdot
        call sc_chdir
        jp .up
.nx:    jr .r
.err:   ld hl,s_pwderr
        jp date_m.xj0_5  
; idev: 21 bytes. HL = name, DE = 3 byte (ino, dev) result. IDs, please.
idev:   push de
        ld de,U_STB
        call sc_stat
        pop de
        ret c
        ld hl,(U_STB)
        ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (hl),0               ; One RAM filesystem, device 0. No spare drive.
        or a
        ret
s_pwderr: db "pwd: read error in ..",10,0
e_pwd:

; ------------------------------------------------------------- df
; df - free memory: the arena holds every file (and every program).
t_df:   db 18h,6
        dw STKRES, TV-UDATA, df_m
; df_m: 28 bytes. Count free space. The answer may be depressing.
df_m:   ld hl,0
        SC _zxpack              ; HL = free bytes, DE = free i-nodes.
        push de
        call putdec
        ld hl,s_dff
        call puts
        pop hl
        call putdec
        ld hl,s_dfi
        jp zxst.xj0_2  
s_dff:  db " bytes free, ",0
s_dfi:  db " i-nodes free",10,0
e_df:
