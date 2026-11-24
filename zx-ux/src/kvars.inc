; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================

; =====================================================================
;  kernel globals - live in the ZX printer buffer (5B00-5BFF)
; =====================================================================
p_stat  equ KV+0        ; Four slots. Each gets exactly one state.
        ASSERT (p_stat & 0FFh) == 0 && NPROC <= 256
p_wchan equ KV+4        ; Four places to wait. No line-cutting.
p_sig   equ KV+8        ; Four pending signals. BREAK can be pushy.
p_pid   equ KV+12       ; Four process IDs. Everyone gets a number.
p_ppid  equ KV+20       ; Four parent IDs. Family ties come in pairs.
p_sp    equ KV+28       ; Four saved stacks. All their own baggage.
p_brk   equ KV+36       ; Four break points. Memory has its limits.
p_xst   equ KV+44       ; Four exit scores. Nobody gets an encore.
p_tick  equ KV+52       ; Four sleep counters. Even naps are tracked.
p_save  equ KV+60       ; Four saved images. The swap bill comes due.
p_img   equ KV+68       ; Four image slots. No hidden fifth seat.
p_cpu   equ KV+76       ; Four CPU clocks. Fairness needs numbers.
idlet   equ KV+84       ; Idle time counts, too. No paid holiday.
runrun  equ KV+86       ; A request to swap jobs. No union break.
quant   equ KV+87       ; The remaining time slice. Clock is ticking.
ticks   equ KV+88       ; A 1/50-second tick. The clock has a tiny ruler.
brkst   equ KV+89       ; BREAK edge state. No repeat customers.
mpid    equ KV+90       ; Last process ID. Someone keeps the score.
systime equ KV+92       ; Four seconds bytes. Time gets a ledger.
tmpsp   equ KV+96       ; Temporary stack pointer. Do not leave it behind.
wown    equ KV+98       ; Window owner. Only one renter at a time.
scrown  equ KV+99       ; Screen owners. The pixels run a shared flat.
fticks  equ KV+100      ; Frame counter. Fifty ticks, no refunds.
a_dst   equ KV+102      ; Next compaction spot. No parking sideways.
ttyhd   equ KV+104      ; ISR writes the raw-key head. Queue starts here.
ttytl   equ KV+105      ; Raw-key tail. The queue ends here.
ttymode equ KV+106      ; Terminal settings. Keys follow house rules.
ttycnt  equ KV+107      ; Characters in a line. No overflow seating.
ttypos  equ KV+108      ; Next line character. The queue moves along.
ttyrdy  equ KV+109      ; Complete line waiting. Service, please.
a_kind  equ KV+110      ; Block kind. Memory checks the guest list.
; KV+111: zxpack (zx.asm).
spino   equ KV+112      ; 32 bytes: synthesized special-file i-node.
xhdr    equ KV+144      ; 8 bytes exec header.
fsp     equ KV+152      ; NFILES * 6: inum.w off.w cnt.b flg.b.
FSPSZ   equ 6
a_top   equ KV+224      ; Arena ceiling. No adding another floor.
wlend   equ KV+226      ; Window loan holder. Borrowed RAM still counts.
ttop    equ KV+228      ; Console start row. Everybody gets their lane.
tod_h   equ KV+229      ; Hour of day. BEEP used to own this desk.
tod_m   equ KV+230      ; Minute of day. The clock does not take breaks.
tod_s   equ KV+231      ; Second of day. Another tenant in old MEMBOT space.
stdirty equ KV+232      ; Status line needs paint. Again.
a_try   equ KV+233      ; Remaining allocation tries. Not infinite.
a_new   equ KV+234      ; New address. Do not trust the old one.
; KV+236..238: zxpack (zx.asm).
kerrsp  equ KV+239      ; word → rom_error (ERR_SP points here). The Z80 has delivered its complaint.
ktmp    equ KV+241      ; word scratch.
; KV+243..246: zxpack (zx.asm).
xargc   equ KV+247      ; exec: argc.
xtop    equ KV+248      ; word exec: end of packed args.
cur     equ KV+250      ; Running slot. One driver at the wheel.
inkern  equ KV+251      ; Kernel is busy. Mind the door.
idling  equ KV+252      ; Idle means waiting, not disappearing.
ttat    equ KV+253      ; TTY parameter count. We expect exact change.
ttcc    equ KV+254      ; TTY control awaiting its arguments. Patiently.
ttp1    equ KV+255      ; First TTY argument. The second can wait.

; Spare low RAM belongs to zxpack. Keep model state out of the arena.
; ROM routines and other kernel paths must not borrow these bytes.
ZLO1    equ 05CCBh      ; 32 dead BASIC area below KV2: txino.
ZLO2    equ MEMBOT+15   ; 15 calculator memory past the kernel's (the ROM calculator is never used).
ZLO3    equ TTYBUF+TTYBSZ ; 17 between the tty line and KARGS.

; second kernel data area in the dead BASIC / IF1 area. Ticks are not a savings account.
KV2     equ 05CEBh
ttyring equ KV2+0       ; 32 keys of waiting room. Please form a line.
stline  equ KV2+32      ; Four names, eight bytes apiece. No long introductions.
chslot  equ KV2+64      ; Child process seat. No family discounts.
sw_lo   equ KV2+65      ; Saved data address. Remember where it went.
sw_hi   equ KV2+67      ; Saved stack address. Do not lose the ladder.
sw_n    equ KV2+69      ; Saved-image size. Every byte counts twice.
a_need  equ KV2+71      ; Requested arena size. Wishful thinking is not RAM.
a_old   equ KV2+73      ; Previous address. Only good for looking back.
kcon    equ KV2+75      ; Kernel chatter switch. Even it needs a mute.
ZLO4    equ KV2+76      ; 97 bytes of compression state. Packed tight.
KV2END  equ ZLO4+97
LOWK    equ KV2END      ; The kernel and stack share this low spot. Cozy.
; Idle packing and an interrupt can both need stack. Give them room.

; Open-file flags. Even a one-bit choice can cause trouble.
F_READ  equ 1
F_WRITE equ 2
F_DEL   equ 080h

; =====================================================================
;  per-process 'u' area (swapped with the process) - at CORE, the top
;  of the window
;  Only what the kernel reads: single user (no uids), no quit key (the
;  quit flag was never consulted), no errno word (results go back in A),
;  no mount table (files share RAM), and status names live in stline.
; =====================================================================
u_sp    equ CORE+0      ; Saved entry stack. Keep the return ticket.
u_cdir  equ CORE+2      ; Current directory number. No wandering blind.
u_fp    equ CORE+4      ; Ten open-file seats. Standing room is gone.
u_intr  equ CORE+14     ; Interrupt preference. BREAK gets a vote.
u_dirbuf equ CORE+15    ; Ten bytes for a directory entry. Compact company.
u_off   equ CORE+25     ; File position. The read starts somewhere.
u_base  equ CORE+27     ; I/O address. No treasure hunt required.
u_count equ CORE+29     ; Requested byte count. Ask, do not guess.
u_nread equ CORE+31     ; Delivered byte count. Receipts matter.
u_pdir  equ CORE+33     ; Parent directory. Follow the breadcrumb.
u_dirp  equ CORE+35     ; Directory slot. Everything has its place.
u_name  equ CORE+37     ; Last path name. Eight bytes, no extras.
u_ino   equ CORE+45     ; A spare word. It still has a job.
u_tmp   equ CORE+47     ; Scratch word. Borrowed room is still room.
u_tmp2  equ CORE+49     ; Another scratch word. Two pockets, no luxury.
u_fdi   equ CORE+51     ; Scratch byte. No bulk storage here.
u_nmp   equ CORE+52     ; Path pointer. Do not lose the trail.
u_nmi   equ CORE+54     ; Directory number. Names need a home.
u_nlast equ CORE+56     ; Last path piece. The journey ends here.
u_nfree equ CORE+57     ; First empty directory slot. If we are lucky.
u_end   equ CORE+59
        ASSERT u_end - CORE == UASZ
