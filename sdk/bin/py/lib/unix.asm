; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48's remaining kernel calls. The wrapper count is not a personality test.
; A = call number; HL, DE, BC = arguments; CF and A report a kernel error.
; Failure returns FFFFh and sets errno. Success leaves errno alone and
; returns the result in HL, or zero when the call has no result.
; sys.asm and io.asm already handle the common calls. No duplicate tickets.
; rcc passes the last C argument in HL and earlier ones on the stack;
; the callee removes them. IX survives because the kernel preserves IX/IY.
SYS     equ 6003h
        section text
        global @sys,@sys0,_fork,_write,_wait,_creat,_link,_unlink,_exec,_chdir
        global _time,_mkdir,_chmod,_chown,_brk,_stat,_lseek,_tell,_setuid
        global _getuid,_stime,_quit,_intr,_fstat,_cemt,_mdate,_stty,_gtty
        global _ilgins,_kill,_zxpack,_zxinfo,_screen,_ssxload,@a2,@a3,_errno

; @sys: 16 bytes. Call the kernel; on error return FFFFh and set errno.
@sys:   call SYS
        ret nc
        ld (_errno),a
        xor a
        ld (_errno+1),a
        ld hl,-1
        scf
        ret

; @sys0: 8 bytes. Use @sys but return zero on success. The caller likes zero.
@sys0:  call @sys
        ret c
        ld hl,0
        ret

; @a2: 6 bytes. Move two C arguments into HL and DE for a system call.
@a2:    ex de,hl                ; DE = a2
        pop bc                  ; (@a2's own return)
        pop hl                  ; the wrapper's return
        ex (sp),hl              ; HL = a1, the wrapper's return on top
        push bc
        ret

; @a3: 15 bytes. Move three C arguments into HL, DE and BC. Full house.
@a3:    ld b,h
        ld c,l                  ; BC = a3
        pop hl                  ; (@a3's own return)
        ld (@t),hl
        pop hl                  ; the wrapper's return
        pop de                  ; DE = a2
        ex (sp),hl              ; Bring a1 into HL; the wrapper still gets its return.
        push hl
        ld hl,(@t)
        ex (sp),hl
        ret

; _fork: 5 bytes. Fork the process; SSX1 programs get EAGAIN instead.
_fork:  ld a,2
        jp @sys

; _write: 8 bytes. Write a buffer and return the byte count, or -1 on error.
_write: call @a3
        ld a,4
        jp @sys

; _wait: 17 bytes. Wait for a child; store its exit status when the pointer is nonzero.
_wait:  push hl
        ld a,7
        call @sys
        pop bc
        ret c
        ld a,b
        or c
        ret z
        ld a,e
        ld (bc),a
        inc bc
        ld a,d
        ld (bc),a
        ret

; _creat: 8 bytes. Create or empty a file, then open it for writing.
_creat: call @a2
        ld a,8
        jp @sys

; _link: 8 bytes. Link an old path to a new one. Same file, another door.
_link:  call @a2
        ld a,9
        jp @sys0

; _unlink: 5 bytes. Remove a pathname. Mind the directory.
_unlink:
        ld a,10
        jp @sys0

; _exec: 43 bytes. Give up the tty and screen, then replace the image; restore them on failure.
_exec:  push hl                 ; argv
        ld a,(@israw)
        or a
        ld a,10h                ; keyboard: cooked, echo again
        call nz,@stty
        xor a
        ld (@israw),a           ; (the next getchar makes it raw again)
        ld hl,0
        ld a,39                 ; give the screen back
        call SYS
        pop de                  ; DE = argv
        pop bc
        pop hl                  ; HL = path
        push bc
        ld a,11
        call @sys               ; returns only on an error
        push hl
        ld hl,1
        ld a,39                 ; take the screen again
        call SYS
        pop hl
        scf
        ret

; _chdir: 5 bytes. Change the working directory. No suitcase needed.
_chdir: ld a,12
        jp @sys0

; _time: 19 bytes. Read the kernel clock into two 16-bit words, low first.
_time:  push hl
        ld a,13
        call @sys
        ex (sp),hl              ; HL = t, low word on the stack
        pop bc
        ld (hl),c
        inc hl
        ld (hl),b
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        ld hl,0
        ret

; _stime: 18 bytes. Set the clock from two words, low first. Time travel, limited.
_stime: ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        push de
        ld e,(hl)
        inc hl
        ld d,(hl)               ; DE = high
        pop hl                  ; HL = low
        ld a,25
        call @sys
        ld hl,0
        ret

; _mkdir: 8 bytes. Create a directory with the requested mode.
_mkdir: call @a2
        ld a,14
        jp @sys0

; _chmod: 8 bytes. Change the path mode. The kernel decides.
_chmod: call @a2
        ld a,15
        jp @sys0

; _chown: 8 bytes. Accept an owner change in this single-user system.
_chown: call @a2
        ld a,16
        jp @sys0

; _brk: 5 bytes. Move the program break below its stack, or return ENOMEM.
_brk:   ld a,17
        jp @sys

; _stat: 8 bytes. Ask the kernel for the inode record at a pathname.
_stat:  call @a2
        ld a,18
        jp @sys0

; _lseek: 8 bytes. Seek by offset from start, current position, or end.
_lseek: call @a3
        ld a,19
        jp @sys

; _tell: 5 bytes. Read the current file position. No guesswork.
_tell:  ld a,20
        jp @sys

; _setuid: 5 bytes. Accept a user ID; there is only one user aboard.
_setuid:
        ld a,23
        jp @sys0

; _getuid: 5 bytes. Return user ID zero. Everybody gets root.
_getuid:
        ld a,24
        jp @sys

; _quit: 5 bytes. Accept the quit-key switch; there is no quit key.
_quit:  ld a,26
        jp @sys0

; _intr: 5 bytes. Control BREAK handling for the current process.
_intr:  ld a,27
        jp @sys0

; _fstat: 8 bytes. Get inode details for an open handle instead of a path.
_fstat: call @a2
        ld a,28
        jp @sys0

; _cemt: 5 bytes. Accept the old emulator-trap request; do nothing.
_cemt:  ld a,29
        jp @sys0

; _mdate: 14 bytes. Set file modification time from two 16-bit words.
_mdate: ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)               ; BC = high, DE = low
        pop hl                  ; return
        ex (sp),hl              ; HL = path
        ld a,30
        jp @sys0

; _stty: 8 bytes. Write the six-byte terminal mode block.
_stty:  call @a2
        ld a,31
        jp @sys0
; _gtty: 8 bytes. Read the six-byte terminal mode block.
_gtty:  call @a2
        ld a,32
        jp @sys0

; _ilgins: 5 bytes. Accept the old illegal-instruction-trap call; do nothing.
_ilgins:
        ld a,33
        jp @sys0

; _kill: 5 bytes. End the selected process. It gets no veto.
_kill:  ld a,35
        jp @sys0

; _zxpack: 5 bytes. Pack a file if needed; return the packed stream length.
_zxpack:
        ld a,37
        jp @sys

; _zxinfo: 22 bytes. Copy the kernel free-space and free-inode counts to the buffer.
_zxinfo:
        push hl
        ld hl,0
        ld a,37
        call @sys
        ex (sp),hl
        pop bc
        ld (hl),c
        inc hl
        ld (hl),b
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        ld hl,0
        ret

; _screen: 5 bytes. Claim or release the screen; the kernel returns its address.
_screen:
        ld a,39
        jp @sys

; _ssxload: 8 bytes. Request SSX1 tape loading; only the resident loader is allowed.
_ssxload:
        call @a3
        ld a,40
        jp @sys

        section bss
; @t: 2 BSS bytes. Two bytes for the high word while reading time.
@t:     ds 2
; _errno: 2 BSS bytes. Last kernel error; left alone after a successful call.
_errno: ds 2                    ; Low byte from A; high byte forced to zero.
