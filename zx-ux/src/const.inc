; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
; ZX-UX v1 kernel constants: Z80 memory, four jobs, UNIX-style calls.
; Old UNIX calls, new Z80 storage. Every byte pays rent.
; =====================================================================

; ---------------------------------------------------------------- memory map
; 0000-3FFF: ROM serves keyboard, BEEP and tape; screen drawing is ours.
; 4000-5AFF: Screen bitmap and attributes. Pixels have claimed prime space.
; 5B00-5BFF: The printer buffer holds kernel globals. Sorry, printer.
; 5C00-5CB5: ROM variables; MEMBOT 5C92-5CAF lends scratch space to us.
;             Its first five bytes stay clear for program BEEP. Music has rules.
; 5CB6-5CCA: Keep ROM CHANS intact. Old routines dislike surprises.
; 5CCB-5EFF: Unused BASIC/IF1 space holds file, keyboard, process, packing
;             and stack state. Old RAM gets a second career.
; 5F01-5F50: Terminal line buffer. Eighty bytes, no novels.
; 5F51-5F61: Packing variables. Every bit gets counted.
; 5F62-5FFF: Program arguments. No free luggage allowance.
; 6000 onward: Kernel and resident program code. The main event.
; ZXW: 256-byte packing model, borrowed by the one-shot boot code.
; ITAB: NINODE nodes, 32 bytes each. A tidy little roll call.
; AR0 onward: Files, directories, saved processes and loaded SSX1 programs.
;             The top may borrow WINDOW; it cannot invent more RAM.
; F000-FFB8: WINDOW holds resident program data and stack. Very snug.
; FFB9-FFF3: Running process state, UASZ bytes. No room for souvenirs.
; FFF4-FFF6: JP isr for IM 2. The vector uses FFFFh and the F3h
;             byte at address zero redirects to FFF4h. Sneaky but real.
;             I=39h avoids the display pages, where ULA snow would be rude.

KBASE   equ 06000h
TRAMP   equ 0FFF4h          ; IM 2 detour. Three bytes, no sightseeing.
UASZ    equ 59              ; 59 bytes for the current process. No penthouse suite.
CORE    equ TRAMP-UASZ      ; The active process lives here. Mind the roof.
WINDOW  equ 0F000h          ; Resident process images live here. Space is borrowed, not free.
UDATA   equ WINDOW          ; User data begins here. No warm-up lap.
CORETOP equ CORE            ; Stack and arguments stop here. No attic above it.
STKRES  equ 384             ; Up to 384 bytes of stack per program, set by header word two. No extras.

KV      equ 05B00h          ; The kernel uses the printer buffer. Sorry, printer.
KSTACK  equ 05F00h          ; Kernel stack top. It only grows toward trouble.
IM2I    equ 039h            ; The interrupt register points into ROM FFh bytes. Handy detour.
TTYBUF  equ 05F01h          ; 80 bytes for a line. No rambling allowed.
TTYBSZ  equ 80
KARGS   equ 05F62h          ; 158 bytes for command arguments. Short speeches, please.
KARGSZ  equ 158
MEMBOT  equ 05C92h          ; 30 calculator bytes on loan as scratch. Keep BEEP out of the first five.

; ---------------------------------------------------------------- file system
NINODE  equ 24              ; 24 file nodes, numbered 41 to 64. The guest list is short.
ROOTINO equ 41              ; Directory 41 is home. No need to ask for directions.
INOSZ   equ 32              ; A file node costs 32 bytes. Rent is not optional.
TXINO   equ 128             ; Resident programs start at node 128. Different neighborhood.

; arena block kinds (arena.asm); below K_IMG: movable.
K_FREE  equ 0
K_FILE  equ 1               ; File or directory blocks can move. No permanent parking.
K_SAVE  equ 2               ; A saved process image can move, too. Keep its forwarding address.
K_IMG   equ 4               ; Loaded SSX1 images stay put. Somebody nailed down the furniture.
K_TEMP  equ 5               ; The packer gets fixed workspace. No sharing the desk.

; i-node field offsets. Old names, tight new storage.
I_FLGS  equ 0
I_NLKS  equ 2
I_UID   equ 3
I_SIZE  equ 4
I_DSKP  equ 6
I_CTIM  equ 22
I_MTIM  equ 26
I_RSVD  equ 30

; i.flgs bits (v1, octal in comments). An off-by-one is still one too many.
IALLOC  equ 08000h          ; 0100000 octal: the node is claimed. Taken means taken.
IFDIR   equ 04000h          ; 040000 octal: a directory, not a regular file.
IFMOD   equ 02000h          ; 020000 octal: modified. The bytes have changed their tune.
IFLARGE equ 01000h          ; 010000 octal: large file. Large is a relative word here.
IFTEXT  equ 00800h          ; Resident Z80 text in core. This code keeps its seat.
ISUID   equ 020h            ; 040 octal: set user ID. The flag has a job.
IEXEC   equ 010h            ; 020 octal: executable. This one gets to run.
IROWN   equ 008h            ; 010 octal: owner may read. Others can ask nicely.
IWOWN   equ 004h            ; 04 octal: owner may write. Handle with care.
IROTH   equ 002h            ; 02 octal: others may read. Sharing has rules.
IWOTH   equ 001h            ; 01 octal: others may write. Sharing has consequences.

; Special files: tty, memory and tape. No imaginary drives.
DEV_TTY equ 1
DEV_MEM equ 2
DEV_TAP equ 5
NSPEC   equ 5

; ---------------------------------------------------------------- processes
NPROC   equ 4               ; Four processes maximum. Not much of a crowd.
NFILES  equ 12              ; Twelve system file slots. No standing room.
NUFILE  equ 10              ; Ten file handles per process. Keep count.
QUANT   equ 4               ; Four 50 Hz ticks per turn. The clock does not play favorites.

SFREE   equ 0
SRUN    equ 1
SSLEEP  equ 2
SZOMB   equ 3

WC_TTY  equ 1               ; Wait for terminal input. Fingers, your move.
WC_WAIT equ 2
WC_TIME equ 3

; ---------------------------------------------------------------- errors
EPERM   equ 1
ENOENT  equ 2
EIO     equ 5
EBADF   equ 9
ECHILD  equ 10
EAGAIN  equ 11
ENOMEM  equ 12
EACCES  equ 13
EBUSY   equ 16
EEXIST  equ 17
ENOTDIR equ 20
EISDIR  equ 21
EINVAL  equ 22
ENFILE  equ 23
EMFILE  equ 24
ENOEXEC equ 8
ENOSPC  equ 28
EINTR   equ 4
EFBIG   equ 27
EDOM    equ 33
ERANGE  equ 34

; ---------------------------------------------------------------- syscalls
SYS     equ KBASE+3         ; System calls enter at KBASE+3. A gets the call number.
_rele   equ 0
_exit   equ 1
_fork   equ 2
_read   equ 3
_write  equ 4
_open   equ 5
_close  equ 6
_wait   equ 7
_creat  equ 8
_link   equ 9
_unlink equ 10
_exec   equ 11
_chdir  equ 12
_time   equ 13
_mkdir  equ 14
_chmod  equ 15
_chown  equ 16
_break  equ 17
_stat   equ 18
_seek   equ 19
_tell   equ 20
_mount  equ 21
_umount equ 22
_setuid equ 23
_getuid equ 24
_stime  equ 25
_quit   equ 26
_intr   equ 27
_fstat  equ 28
_emt    equ 29
_mdate  equ 30
_stty   equ 31
_gtty   equ 32
_ilgins equ 33
_sleep  equ 34              ; System call 34 sleeps. The clock keeps its day job.
_kill   equ 35              ; System call 35 sends a signal. Break the news gently.
_getpid equ 36              ; System call 36 asks who is running. ID please.
_zxpack equ 37              ; Call 37 packs a named file; zero asks for arena status. No guessing.
_ticks  equ 38              ; Call 38 reads the 50 Hz frame count. Time still passes.
_screen equ 39              ; Call 39 claims or frees the screen. Share the pixels.
_ssxload equ 40             ; Call 40 takes length in BC, RAM in DE, args in HL. Bring all three.
NSYS    equ 41

; tty modes (stty word 3).
TT_RAW  equ 020h
TT_ECHO equ 010h
TT_FLUSH equ 080h          ; Flush old raw keys once. Yesterday can stay yesterday.

; ---------------------------------------------------------------- ROM
ROM_KEYBOARD  equ 002BFh
ROM_KEYINPUT  equ 010A8h
ROM_CHANOPEN  equ 01601h
ROM_CLS       equ 00D6Bh
ROM_BEEPER    equ 003B5h
ROM_BREAKKEY  equ 01F54h
ROM_SABYTES   equ 004C2h
ROM_LDBYTES   equ 00556h
ROM_CHARSET   equ 03D00h

; ROM system variables. Our old neighbors still own their addresses.
SV_KSTATE equ 05C00h
SV_LASTK  equ 05C08h
SV_FLAGS  equ 05C3Bh
SV_TVFLAG equ 05C3Ch
SV_ERRSP  equ 05C3Dh
SV_MODE   equ 05C41h
SV_BORDCR equ 05C48h
SV_FLAGS2 equ 05C6Ah
SV_DFSZ   equ 05C6Bh
SV_FRAMES equ 05C78h
SV_SPOSN  equ 05C88h
SV_SCRCT  equ 05C8Ch
SV_ATTRP  equ 05C8Dh
SV_ATTRT  equ 05C8Fh
SV_CHANS  equ 05C4Fh
