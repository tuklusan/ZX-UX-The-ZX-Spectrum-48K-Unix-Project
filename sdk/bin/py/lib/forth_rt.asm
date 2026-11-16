; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; Indirect-threaded Forth: BC = thread pointer, SP = data stack,
; IX = return stack, DE/HL/A = scratch. One byte of RAM likes company.
; Each fw_* count runs to the next word field, including shared helpers
; that sit between words; no helper is billed twice.
; A thread cell points to a code field, whose first word points to code.
; Colon words use docol/exit; branch cells contain absolute addresses.
; The kernel keeps IX/IY through SYS, so we save BC around the write call.
; rfc supplies the compiled entry thread at @forth_main.
SYS	equ	6003h
	global	start
	section	text
; start: 41 bytes before the next label. Give Forth a return stack, decimal base and dictionary. Home sweet RAM.
start:
	ld	ix,rstack_top
	ld	hl,0
	add	hl,sp
	ld	(sp0),hl
	ld	hl,10
	ld	(base),hl
	ld	hl,dict_area
	ld	(dp),hl
	ld	hl,0
	ld	(state),hl
	ld	hl,(@latest0)
	ld	(latest),hl
	ld	bc,@forth_main
	jp	next
; next: 13 bytes before the next label. Fetch the next code field and jump. The tiny treadmill rolls on.
next:
	ld	a,(bc)
	ld	e,a
	inc	bc
	ld	a,(bc)
	ld	d,a
	inc	bc
	ld	a,(de)
	ld	l,a
	inc	de
	ld	a,(de)
	ld	h,a
	inc	de
	jp	(hl)
; docol: 15 bytes before the next label. Park the current thread on the return stack before a colon word.
docol:
	dec	ix
	ld	(ix+0),b
	dec	ix
	ld	(ix+0),c
	ld	b,d
	ld	c,e
	jp	next
; dovar_c: 4 bytes before the next label. Push the variable address. The contents can wait.
dovar_c:
	push	de
	jp	next
; docon_c: 8 bytes before the next label. Push the constant stored after its code field. No treasure hunt.
docon_c:
	ex	de,hl
	ld	e,(hl)
	inc	hl
	ld	d,(hl)
	push	de
	jp	next
; putc: 26 bytes before the next label. Write A to stdout and restore BC. One byte, big paperwork.
putc:
	ld	(charbuf),a
	ld	(ipsave),bc
	ld	hl,1
	ld	de,charbuf
	ld	bc,1
	ld	a,4
	call	SYS
	ld	bc,(ipsave)
	ret
; fw_exit: 15 bytes through the next word field. Return to the caller thread; IX knows who sent us.
fw_exit:
	dw	exit_c
exit_c:
	ld	c,(ix+0)
	inc	ix
	ld	b,(ix+0)
	inc	ix
	jp	next
; fw_lit: 12 bytes through the next word field. Push the next 16-bit literal from the thread. Straight from the wrapper.
fw_lit:
	dw	lit_c
lit_c:
	ld	a,(bc)
	ld	l,a
	inc	bc
	ld	a,(bc)
	ld	h,a
	inc	bc
	push	hl
	jp	next
; fw_branch: 12 bytes through the next word field. Jump to the absolute target in the thread. No sightseeing.
fw_branch:
	dw	branch_c
branch_c:
	ld	a,(bc)
	ld	l,a
	inc	bc
	ld	a,(bc)
	ld	h,a
	ld	b,h
	ld	c,l
	jp	next
; fw_zbranch: 22 bytes through the next word field. Pop a flag and jump on zero. The rest stay on the path.
fw_zbranch:
	dw	zbranch_c
zbranch_c:
	pop	hl
	ld	a,h
	or	l
	jr	z,zbranch_take
	inc	bc
	inc	bc
	jp	next
zbranch_take:
	ld	a,(bc)
	ld	l,a
	inc	bc
	ld	a,(bc)
	ld	h,a
	ld	b,h
	ld	c,l
	jp	next
; fw_pdo: 27 bytes through the next word field. Move loop limit and index to the return stack. Room for two more.
fw_pdo:
	dw	pdo_c
pdo_c:
	pop	de
	pop	hl
	dec	ix
	ld	(ix+0),h
	dec	ix
	ld	(ix+0),l
	dec	ix
	ld	(ix+0),d
	dec	ix
	ld	(ix+0),e
	jp	next
; fw_ploop: 52 bytes through the next word field. Step the loop index; leave when the limit has had enough.
fw_ploop:
	dw	ploop_c
ploop_c:
	ld	l,(ix+0)
	ld	h,(ix+1)
	inc	hl
	ld	(ix+0),l
	ld	(ix+1),h
	ld	e,(ix+2)
	ld	d,(ix+3)
	ld	a,l
	cp	e
	jr	nz,ploop_go
	ld	a,h
	cp	d
	jr	nz,ploop_go
	inc	ix
	inc	ix
	inc	ix
	inc	ix
	inc	bc
	inc	bc
	jp	next
ploop_go:
	ld	a,(bc)
	ld	l,a
	inc	bc
	ld	a,(bc)
	ld	h,a
	ld	b,h
	ld	c,l
	jp	next
; fw_i: 12 bytes through the next word field. Read the current loop index from the return stack. No queueing.
fw_i:
	dw	i_c
i_c:
	ld	l,(ix+0)
	ld	h,(ix+1)
	push	hl
	jp	next
; fw_j: 12 bytes through the next word field. Read the outer loop index. The older loop gets a say.
fw_j:
	dw	j_c
j_c:
	ld	l,(ix+4)
	ld	h,(ix+5)
	push	hl
	jp	next
; fw_dup: 8 bytes through the next word field. Copy the top stack cell. Two for the price of one.
fw_dup:
	dw	dup_c
dup_c:
	pop	hl
	push	hl
	push	hl
	jp	next
; fw_drop: 6 bytes through the next word field. Discard the top cell. Its brief career ends here.
fw_drop:
	dw	drop_c
drop_c:
	pop	hl
	jp	next
; fw_swap: 9 bytes through the next word field. Swap the top two cells. Neither gets the window seat.
fw_swap:
	dw	swap_c
swap_c:
	pop	hl
	pop	de
	push	hl
	push	de
	jp	next
; fw_over: 10 bytes through the next word field. Copy the second cell above the first. Stack gymnastics.
fw_over:
	dw	over_c
over_c:
	pop	hl
	pop	de
	push	de
	push	hl
	push	de
	jp	next
; fw_rot: 17 bytes through the next word field. Rotate the top three cells. Nobody leaves the stack.
fw_rot:
	dw	rot_c
rot_c:
	pop	hl
	ld	(rot_t),hl
	pop	hl
	pop	de
	push	hl
	ld	hl,(rot_t)
	push	hl
	push	de
	jp	next
; fw_nip: 8 bytes through the next word field. Remove the second cell and keep the top. Selective memory.
fw_nip:
	dw	nip_c
nip_c:
	pop	hl
	pop	de
	push	hl
	jp	next
; fw_plus: 9 bytes through the next word field. Add the top two 16-bit cells. Carry earns its keep.
fw_plus:
	dw	plus_c
plus_c:
	pop	hl
	pop	de
	add	hl,de
	push	hl
	jp	next
; fw_minus: 11 bytes through the next word field. Subtract the top cell from the next. Order is everything.
fw_minus:
	dw	minus_c
minus_c:
	pop	de
	pop	hl
	or	a
	sbc	hl,de
	push	hl
	jp	next
; fw_1p: 8 bytes through the next word field. Add one to the top cell. We budgeted accordingly.
fw_1p:
	dw	oneplus_c
oneplus_c:
	pop	hl
	inc	hl
	push	hl
	jp	next
; fw_1m: 8 bytes through the next word field. Subtract one from the top cell. Inflation in reverse.
fw_1m:
	dw	oneminus_c
oneminus_c:
	pop	hl
	dec	hl
	push	hl
	jp	next
; fw_neg: 14 bytes through the next word field. Two's complement negation, not just flipped bits.
fw_neg:
	dw	neg_c
neg_c:
	pop	hl
	ld	a,l
	cpl
	ld	l,a
	ld	a,h
	cpl
	ld	h,a
	inc	hl
	push	hl
	jp	next
; fw_abs: 18 bytes through the next word field. Take the signed magnitude. Negative numbers lose their attitude.
fw_abs:
	dw	abs_c
abs_c:
	pop	hl
	bit	7,h
	jr	z,abs_done
	ld	a,l
	cpl
	ld	l,a
	ld	a,h
	cpl
	ld	h,a
	inc	hl
abs_done:
	push	hl
	jp	next
; fw_2s: 8 bytes through the next word field. Double the top cell with a left shift. No multiplication fee.
fw_2s:
	dw	twostar_c
twostar_c:
	pop	hl
	add	hl,hl
	push	hl
	jp	next
; fw_2d: 11 bytes through the next word field. Shift right with the sign intact. Bad news stays negative.
fw_2d:
	dw	twoslash_c
twoslash_c:
	pop	hl
	sra	h
	rr	l
	push	hl
	jp	next
; fw_star: 36 bytes through the next word field. Multiply two cells, keeping the low 16 bits. The rest vanish.
fw_star:
	dw	star_c
star_c:
	ld	(ipsave),bc
	pop	de
	pop	bc
	ld	hl,0
star_loop:
	ld	a,d
	or	e
	jr	z,star_done
	srl	d
	rr	e
	jr	nc,star_noadd
	add	hl,bc
star_noadd:
	sla	c
	rl	b
	jr	star_loop
star_done:
	push	hl
	ld	bc,(ipsave)
	jp	next
; fw_slash: 19 bytes through the next word field. Signed division; return just the quotient. Remainders get no vote.
fw_slash:
	dw	slash_c
slash_c:
	ld	(ipsave),bc
	pop	de
	pop	hl
	call	fdivmod
	push	hl
	ld	bc,(ipsave)
	jp	next
; fw_mod: 19 bytes through the next word field. Signed division; return the remainder. Quotient goes home.
fw_mod:
	dw	mod_c
mod_c:
	ld	(ipsave),bc
	pop	de
	pop	hl
	call	fdivmod
	push	de
	ld	bc,(ipsave)
	jp	next
; fw_slmod: 20 bytes through the next word field. Return signed quotient and remainder. Two results, one bill.
fw_slmod:
	dw	slmod_c
slmod_c:
	ld	(ipsave),bc
	pop	de
	pop	hl
	call	fdivmod
	push	de
	push	hl
	ld	bc,(ipsave)
	jp	next
; fw_dplus: 36 bytes through the next word field. Add two double-width values with carry. Twice the room, same math.
fw_dplus:
	dw	dplus_c
dplus_c:
	pop	de
	ld	(dtmp_hi2),de
	pop	hl
	ld	(dtmp_lo2),hl
	pop	de
	ld	(dtmp_hi1),de
	pop	hl
	ld	de,(dtmp_lo2)
	add	hl,de
	push	hl
	ld	hl,(dtmp_hi1)
	ld	de,(dtmp_hi2)
	adc	hl,de
	push	hl
	jp	next
; fw_dminus: 38 bytes through the next word field. Subtract two double-width values, borrowing when needed.
fw_dminus:
	dw	dminus_c
dminus_c:
	pop	de
	ld	(dtmp_hi2),de
	pop	hl
	ld	(dtmp_lo2),hl
	pop	de
	ld	(dtmp_hi1),de
	pop	hl
	ld	de,(dtmp_lo2)
	or	a
	sbc	hl,de
	push	hl
	ld	hl,(dtmp_hi1)
	ld	de,(dtmp_hi2)
	sbc	hl,de
	push	hl
	jp	next
; fw_dzeq: 24 bytes through the next word field. Check whether both halves of a double cell are zero. Thorough.
fw_dzeq:
	dw	dzeq_c
dzeq_c:
	pop	de
	pop	hl
	ld	a,d
	or	e
	or	h
	or	l
	jr	nz,dzeq_false
	ld	hl,-1
	push	hl
	jp	next
dzeq_false:
	ld	hl,0
	push	hl
	jp	next
; fw_deq: 51 bytes through the next word field. Compare both halves of two double values. Every bit gets heard.
fw_deq:
	dw	deq_c
deq_c:
	pop	de
	ld	(dtmp_hi2),de
	pop	hl
	ld	(dtmp_lo2),hl
	pop	hl
	ld	(dtmp_hi1),hl
	pop	hl
	ld	de,(dtmp_lo2)
	or	a
	sbc	hl,de
	jr	nz,deq_false
	ld	hl,(dtmp_hi1)
	ld	de,(dtmp_hi2)
	or	a
	sbc	hl,de
	jr	nz,deq_false
	ld	hl,-1
	push	hl
	jp	next
deq_false:
	ld	hl,0
	push	hl
	jp	next
; fw_dult: 59 bytes through the next word field. Unsigned less-than across two double cells. No sign politics.
fw_dult:
	dw	dult_c
dult_c:
	pop	de
	ld	(dtmp_hi2),de
	pop	hl
	ld	(dtmp_lo2),hl
	pop	hl
	ld	(dtmp_hi1),hl
	pop	hl
	ld	(dtmp_lo1),hl
	ld	hl,(dtmp_hi1)
	ld	de,(dtmp_hi2)
	or	a
	sbc	hl,de
	jr	c,dult_true
	jr	nz,dult_false
	ld	hl,(dtmp_lo1)
	ld	de,(dtmp_lo2)
	or	a
	sbc	hl,de
	jr	c,dult_true
dult_false:
	ld	hl,0
	push	hl
	jp	next
dult_true:
	ld	hl,-1
	push	hl
	jp	next
; fw_and: 14 bytes through the next word field. AND the top two cells. A bit survives only if both agree.
fw_and:
	dw	and_c
and_c:
	pop	de
	pop	hl
	ld	a,l
	and	e
	ld	l,a
	ld	a,h
	and	d
	ld	h,a
	push	hl
	jp	next
; fw_or: 14 bytes through the next word field. OR the top two cells. Either vote will do.
fw_or:
	dw	or_c
or_c:
	pop	de
	pop	hl
	ld	a,l
	or	e
	ld	l,a
	ld	a,h
	or	d
	ld	h,a
	push	hl
	jp	next
; fw_xor: 14 bytes through the next word field. XOR the top two cells. Disagreement wins.
fw_xor:
	dw	xor_c
xor_c:
	pop	de
	pop	hl
	ld	a,l
	xor	e
	ld	l,a
	ld	a,h
	xor	d
	ld	h,a
	push	hl
	jp	next
; fw_inv: 13 bytes through the next word field. Invert every bit in the top cell. Instant personality change.
fw_inv:
	dw	inv_c
inv_c:
	pop	hl
	ld	a,l
	cpl
	ld	l,a
	ld	a,h
	cpl
	ld	h,a
	push	hl
	jp	next
; fw_eq: 23 bytes through the next word field. Compare two cells; return a Forth flag. Agreement or nothing.
fw_eq:
	dw	eq_c
eq_c:
	pop	de
	pop	hl
	or	a
	sbc	hl,de
	jr	z,eq_true
	ld	hl,0
	push	hl
	jp	next
eq_true:
	ld	hl,-1
	push	hl
	jp	next
; fw_zeq: 21 bytes through the next word field. Return true only for a zero cell. Modest standards.
fw_zeq:
	dw	zeq_c
zeq_c:
	pop	hl
	ld	a,h
	or	l
	jr	z,zeq_true
	ld	hl,0
	push	hl
	jp	next
zeq_true:
	ld	hl,-1
	push	hl
	jp	next
; fw_zlt: 11 bytes through the next word field. Return true for a negative cell. Zero gets no sympathy.
fw_zlt:
	dw	zlt_c
zlt_c:
	pop	hl
	ld	a,h
	rla
	sbc	hl,hl
	push	hl
	jp	next
; fw_lt: 32 bytes through the next word field. Signed less-than of two cells. Stack order matters.
fw_lt:
	dw	lt_c
lt_c:
	pop	de
	pop	hl
	or	a
	sbc	hl,de
	jp	pe,lt_ov
	jp	m,lt_true
	jr	lt_false
lt_ov:
	jp	p,lt_true
lt_false:
	ld	hl,0
	push	hl
	jp	next
lt_true:
	ld	hl,-1
	push	hl
	jp	next
; fw_gt: 33 bytes through the next word field. Signed greater-than of two cells. The other side of less-than.
fw_gt:
	dw	gt_c
gt_c:
	pop	de
	pop	hl
	ex	de,hl
	or	a
	sbc	hl,de
	jp	pe,gt_ov
	jp	m,gt_true
	jr	gt_false
gt_ov:
	jp	p,gt_true
gt_false:
	ld	hl,0
	push	hl
	jp	next
gt_true:
	ld	hl,-1
	push	hl
	jp	next
; fw_fetch: 10 bytes through the next word field. Read a word through the stack address. Follow the pointer.
fw_fetch:
	dw	fetch_c
fetch_c:
	pop	hl
	ld	e,(hl)
	inc	hl
	ld	d,(hl)
	push	de
	jp	next
; fw_store: 10 bytes through the next word field. Store a word through the stack address. Keep the receipt.
fw_store:
	dw	store_c
store_c:
	pop	hl
	pop	de
	ld	(hl),e
	inc	hl
	ld	(hl),d
	jp	next
; fw_emit: 10 bytes through the next word field. Write one character to stdout. One byte, one job.
fw_emit:
	dw	emit_c
emit_c:
	pop	hl
	ld	a,l
	call	putc
	jp	next
; fw_cr: 10 bytes through the next word field. Write a newline. Even a terminal likes a fresh row.
fw_cr:
	dw	cr_c
cr_c:
	ld	a,10
	call	putc
	jp	next
; fw_key: 34 bytes through the next word field. Read one terminal key. Patience sold separately.
fw_key:
	dw	key_c
key_c:
	ld	(ipsave),bc
	ld	hl,0
	ld	de,charbuf
	ld	bc,1
	ld	a,3
	call	SYS
	ld	bc,(ipsave)
	ld	a,(charbuf)
	ld	l,a
	ld	h,0
	push	hl
	jp	next
; fw_bye: 13 bytes through the next word field. Exit the Forth program. That is the whole farewell.
fw_bye:
	dw	bye_c
bye_c:
	ld	hl,0
	ld	a,1
	call	SYS
	jp	next
; fw_dot: 50 bytes through the next word field. Print a signed cell in the current base. Digits do the talking.
fw_dot:
	dw	dot_c
dot_c:
	pop	hl
	ld	(ipsave),bc
	xor	a
	ld	(dot_neg),a
	bit	7,h
	jr	z,dot_pos
	ld	a,1
	ld	(dot_neg),a
	ld	a,l
	cpl
	ld	l,a
	ld	a,h
	cpl
	ld	h,a
	inc	hl
dot_pos:
	call	convnum
	ld	a,(dot_neg)
	or	a
	jr	z,dot_write
	dec	de
	ld	a,'-'
	ld	(de),a
dot_write:
	call	numout
	ld	bc,(ipsave)
	jp	next
; fw_dotstr: 37 bytes. Print an inline counted string. Its length calls the shots.
fw_dotstr:
	dw	dotstr_c
dotstr_c:
	ld	a,(bc)
	inc	bc
	ld	l,a
	ld	d,b
	ld	e,c
	ld	h,0
	ld	a,c
	add	a,l
	ld	c,a
	ld	a,b
	adc	a,h
	ld	b,a
	ld	(ipsave),bc
	ld	c,l
	ld	b,0
	ld	hl,1
	ld	a,4
	call	SYS
	ld	bc,(ipsave)
	jp	next
; convnum: 42 bytes including branches. Reverse the digits in numbuf; HL and DE mark the ends.
convnum:
	ld	de,numbuf_end
	ld	(cnv_p),de
convnum_loop:
	ld	de,(base)
	call	udivmod
	ld	a,c
	cp	10
	jr	c,convnum_dig
	add	a,7
convnum_dig:
	add	a,'0'
	ld	de,(cnv_p)
	dec	de
	ld	(de),a
	ld	(cnv_p),de
	ld	a,h
	or	l
	jr	nz,convnum_loop
	ld	de,(cnv_p)
	ret
; numout: 36 bytes including its branch labels. Print the prepared digits and a trailing space. Polite exit.
numout:
	ld	hl,numbuf_end
	or	a
	sbc	hl,de
	ld	b,h
	ld	c,l
	ld	hl,1
	ld	a,4
	call	SYS
	ld	a,' '
	ld	(charbuf),a
	ld	hl,1
	ld	de,charbuf
	ld	bc,1
	ld	a,4
	call	SYS
	ret
; udivmod: 37 bytes including branches. Unsigned HL divided by DE; return quotient HL, remainder BC.
udivmod:
	ld	(udiv_dvs),de
	ld	bc,0
	ld	a,16
udivmod_loop:
	add	hl,hl
	rl	c
	rl	b
	push	hl
	ld	h,b
	ld	l,c
	ld	de,(udiv_dvs)
	or	a
	sbc	hl,de
	jr	c,udivmod_no
	ld	b,h
	ld	c,l
	pop	hl
	inc	l
	jr	udivmod_next
udivmod_no:
	pop	hl
udivmod_next:
	dec	a
	jr	nz,udivmod_loop
	ret
; fw_tor: 16 bytes through the next word field. Move a data-stack cell to the return stack. Change of address.
fw_tor:
	dw	tor_c
tor_c:
	pop	hl
	dec	ix
	ld	(ix+0),h
	dec	ix
	ld	(ix+0),l
	jp	next
; fw_fromr: 16 bytes through the next word field. Bring a cell back from the return stack. Welcome home.
fw_fromr:
	dw	fromr_c
fromr_c:
	ld	l,(ix+0)
	inc	ix
	ld	h,(ix+0)
	inc	ix
	push	hl
	jp	next
; fw_rat: 12 bytes through the next word field. Copy the return-stack top without taking it. No vacancy lost.
fw_rat:
	dw	rat_c
rat_c:
	ld	l,(ix+0)
	ld	h,(ix+1)
	push	hl
	jp	next
; fw_2dup: 11 bytes through the next word field. Duplicate the top two cells. A small population boom.
fw_2dup:
	dw	twodup_c
twodup_c:
	pop	hl
	pop	de
	push	de
	push	hl
	push	de
	push	hl
	jp	next
; fw_2drop: 7 bytes through the next word field. Discard the top two cells. Double eviction.
fw_2drop:
	dw	twodrop_c
twodrop_c:
	pop	hl
	pop	hl
	jp	next
; fw_qdup: 16 bytes through the next word field. Duplicate the top cell only if nonzero. Zero stays single.
fw_qdup:
	dw	qdup_c
qdup_c:
	pop	hl
	ld	a,h
	or	l
	jr	z,qdup_zero
	push	hl
	push	hl
	jp	next
qdup_zero:
	push	hl
	jp	next
; fw_min: 32 bytes through the next word field. Keep the smaller signed cell. A humble winner.
fw_min:
	dw	min_c
min_c:
	pop	de
	pop	hl
	ld	(rot_t),hl
	or	a
	sbc	hl,de
	jp	pe,min_ov
	jp	m,min_a
	jr	min_b
min_ov:
	jp	p,min_a
min_b:
	push	de
	jp	next
min_a:
	ld	hl,(rot_t)
	push	hl
	jp	next
; fw_max: 32 bytes through the next word field. Keep the larger signed cell. Competitive arithmetic.
fw_max:
	dw	max_c
max_c:
	pop	de
	pop	hl
	ld	(rot_t),hl
	or	a
	sbc	hl,de
	jp	pe,max_ov
	jp	m,max_b
	jr	max_a
max_ov:
	jp	p,max_b
max_a:
	ld	hl,(rot_t)
	push	hl
	jp	next
max_b:
	push	de
	jp	next
; fw_space: 10 bytes through the next word field. Write one space. Not every byte wants attention.
fw_space:
	dw	space_c
space_c:
	ld	a,' '
	call	putc
	jp	next
; fw_spaces: 31 bytes through the next word field. Write the requested number of spaces. The gaps are the point.
fw_spaces:
	dw	spaces_c
spaces_c:
	pop	hl
	bit	7,h
	jr	nz,spaces_done
	ld	(spc_n),hl
spaces_loop:
	ld	hl,(spc_n)
	ld	a,h
	or	l
	jr	z,spaces_done
	dec	hl
	ld	(spc_n),hl
	ld	a,' '
	call	putc
	jr	spaces_loop
spaces_done:
	jp	next
; fw_type: 23 bytes. Print bytes from the supplied address and length. No NUL required.
fw_type:
	dw	type_c
type_c:
	ld	(ipsave),bc
	pop	bc
	pop	de
	ld	hl,1
	ld	a,4
	call	SYS
	ld	bc,(ipsave)
	jp	next
; fdivmod: 95 bytes including branches. Floor signed HL/DE; quotient in HL, remainder DE. Signs bite.
fdivmod:
	ld	(fdiv_d),de
	ld	a,h
	xor	d
	ld	(fdiv_qs),a
	ld	a,h
	ld	(fdiv_ns),a
	bit	7,h
	jr	z,fdiv_na
	ld	a,l
	cpl
	ld	l,a
	ld	a,h
	cpl
	ld	h,a
	inc	hl
fdiv_na:
	bit	7,d
	jr	z,fdiv_dap
	ld	a,e
	cpl
	ld	e,a
	ld	a,d
	cpl
	ld	d,a
	inc	de
fdiv_dap:
	call	udivmod
	ld	a,b
	or	c
	ld	(fdiv_rz),a
	ld	a,(fdiv_qs)
	bit	7,a
	jr	z,fdiv_qp
	ld	a,l
	cpl
	ld	l,a
	ld	a,h
	cpl
	ld	h,a
	inc	hl
fdiv_qp:
	ld	d,b
	ld	e,c
	ld	a,(fdiv_ns)
	bit	7,a
	jr	z,fdiv_rp
	ld	a,e
	cpl
	ld	e,a
	ld	a,d
	cpl
	ld	d,a
	inc	de
fdiv_rp:
	ld	a,(fdiv_rz)
	or	a
	jr	z,fdiv_ok
	ld	a,(fdiv_qs)
	bit	7,a
	jr	z,fdiv_ok
	dec	hl
	push	hl
	ld	hl,(fdiv_d)
	add	hl,de
	ex	de,hl
	pop	hl
fdiv_ok:
	ret
; fw_leave: 20 bytes through the next word field. Leave the active loop. Enough laps for one day.
fw_leave:
	dw	leave_c
leave_c:
	inc	ix
	inc	ix
	inc	ix
	inc	ix
	ld	a,(bc)
	ld	l,a
	inc	bc
	ld	a,(bc)
	ld	h,a
	ld	b,h
	ld	c,l
	jp	next
; fw_pplusloop: 84 bytes through the next word field. Advance a loop by its step; mind the crossing of the limit.
fw_pplusloop:
	dw	pplusloop_c
pplusloop_c:
	ld	(ipsave),bc
	pop	de
	ld	l,(ix+0)
	ld	h,(ix+1)
	ld	(pl_idx),hl
	ld	c,(ix+2)
	ld	b,(ix+3)
	or	a
	sbc	hl,bc
	ld	a,h
	and	80h
	ld	(pl_bsign),a
	ld	hl,(pl_idx)
	add	hl,de
	ld	(ix+0),l
	ld	(ix+1),h
	or	a
	sbc	hl,bc
	ld	a,h
	and	80h
	ld	hl,pl_bsign
	xor	(hl)
	jr	nz,pplus_exit
	ld	bc,(ipsave)
	ld	a,(bc)
	ld	l,a
	inc	bc
	ld	a,(bc)
	ld	h,a
	ld	b,h
	ld	c,l
	jp	next
pplus_exit:
	inc	ix
	inc	ix
	inc	ix
	inc	ix
	ld	bc,(ipsave)
	inc	bc
	inc	bc
	jp	next
; fw_cfetch: 10 bytes through the next word field. Read one byte from the address on stack. Smaller shopping bag.
fw_cfetch:
	dw	cfetch_c
cfetch_c:
	pop	hl
	ld	l,(hl)
	ld	h,0
	push	hl
	jp	next
; fw_cstore: 8 bytes through the next word field. Store one byte to memory. The other eight bits stay home.
fw_cstore:
	dw	cstore_c
cstore_c:
	pop	hl
	pop	de
	ld	(hl),e
	jp	next
; fw_plusstore: 14 bytes through the next word field. Add a cell directly to a word in memory. In-place economy.
fw_plusstore:
	dw	plusstore_c
plusstore_c:
	pop	hl
	pop	de
	ld	a,(hl)
	add	a,e
	ld	(hl),a
	inc	hl
	ld	a,(hl)
	adc	a,d
	ld	(hl),a
	jp	next
; fw_2swap: 34 bytes through the next word field. Swap the top two pairs. Four cells, no new furniture.
fw_2swap:
	dw	twoswap_c
twoswap_c:
	pop	hl
	ld	(ts_d),hl
	pop	hl
	ld	(ts_c),hl
	pop	hl
	ld	(ts_b),hl
	pop	hl
	ld	de,(ts_c)
	push	de
	ld	de,(ts_d)
	push	de
	push	hl
	ld	de,(ts_b)
	push	de
	jp	next
; fw_2over: 40 bytes through the next word field. Copy the pair beneath the top pair. Double-decker stack.
fw_2over:
	dw	twoover_c
twoover_c:
	pop	hl
	ld	(ts_d),hl
	pop	hl
	ld	(ts_c),hl
	pop	hl
	ld	(ts_b),hl
	pop	hl
	push	hl
	ld	de,(ts_b)
	push	de
	ld	de,(ts_c)
	push	de
	ld	de,(ts_d)
	push	de
	push	hl
	ld	de,(ts_b)
	push	de
	jp	next
; fw_pick: 18 bytes through the next word field. Copy the cell at the chosen stack depth. Selective shopping.
fw_pick:
	dw	pick_c
pick_c:
	pop	hl
	add	hl,hl
	ld	e,l
	ld	d,h
	ld	hl,0
	add	hl,sp
	add	hl,de
	ld	e,(hl)
	inc	hl
	ld	d,(hl)
	push	de
	jp	next
; fw_depth: 21 bytes through the next word field. Count current data-stack cells. No guesses about height.
fw_depth:
	dw	depth_c
depth_c:
	ld	hl,0
	add	hl,sp
	ex	de,hl
	ld	hl,(sp0)
	or	a
	sbc	hl,de
	srl	h
	rr	l
	push	hl
	jp	next
; fw_ult: 23 bytes through the next word field. Unsigned less-than of two cells. Minus signs need not apply.
fw_ult:
	dw	ult_c
ult_c:
	pop	de
	pop	hl
	or	a
	sbc	hl,de
	jr	c,ult_true
	ld	hl,0
	push	hl
	jp	next
ult_true:
	ld	hl,-1
	push	hl
	jp	next
; fw_zgt: 25 bytes through the next word field. Check whether a signed cell is positive. Zero sits this one out.
fw_zgt:
	dw	zgt_c
zgt_c:
	pop	hl
	ld	a,h
	bit	7,a
	jr	nz,zgt_false
	or	l
	jr	z,zgt_false
	ld	hl,-1
	push	hl
	jp	next
zgt_false:
	ld	hl,0
	push	hl
	jp	next
; fw_udot: 20 bytes through the next word field. Print an unsigned cell using the current base. No minus sign.
fw_udot:
	dw	udot_c
udot_c:
	pop	hl
	ld	(ipsave),bc
	call	convnum
	call	numout
	ld	bc,(ipsave)
	jp	next
; fw_base: 9 bytes through the next word field. Push the number-base variable address. Decimal is only a choice.
fw_base:
	dw	base_c
base_c:
	ld	hl,base
	push	hl
	jp	next
; fw_hex: 11 bytes through the next word field. Set base to sixteen. Six new digits join the club.
fw_hex:
	dw	hex_c
hex_c:
	ld	hl,16
	ld	(base),hl
	jp	next
; fw_decimal: 11 bytes through the next word field. Set base to ten. Back to familiar arithmetic.
fw_decimal:
	dw	decimal_c
decimal_c:
	ld	hl,10
	ld	(base),hl
	jp	next
; fw_umstar: 52 bytes through the next word field. Multiply unsigned cells to a double result. Keep every bit.
fw_umstar:
	dw	umstar_c
umstar_c:
	ld	(ipsave),bc
	pop	de
	pop	hl
	ld	(umm),hl
	ld	hl,0
	ld	bc,0
	ld	a,16
umstar_loop:
	add	hl,hl
	rl	c
	rl	b
	sla	e
	rl	d
	jr	nc,umstar_noadd
	push	de
	ld	de,(umm)
	add	hl,de
	jr	nc,umstar_nc
	inc	bc
umstar_nc:
	pop	de
umstar_noadd:
	dec	a
	jr	nz,umstar_loop
	push	hl
	push	bc
	ld	bc,(ipsave)
	jp	next
; fw_umslashmod: 21 bytes plus the 26-byte udiv32 helper. Long division, tiny machine.
fw_umslashmod:
	dw	umsmod_c
umsmod_c:
	ld	(ipsave),bc
	pop	de
	pop	bc
	pop	hl
	call	udiv32
	push	bc
	push	hl
	ld	bc,(ipsave)
	jp	next
; udiv32: 26 bytes including its branch labels. Divide unsigned double by a word. Even 16 bits need help.
udiv32:
	ld	a,16
udiv32_loop:
	add	hl,hl
	rl	c
	rl	b
	push	hl
	ld	h,b
	ld	l,c
	or	a
	sbc	hl,de
	jr	c,udiv32_no
	ld	b,h
	ld	c,l
	pop	hl
	inc	l
	jr	udiv32_next
udiv32_no:
	pop	hl
udiv32_next:
	dec	a
	jr	nz,udiv32_loop
	ret
; fw_execute: 10 bytes through the next word field. Run the code field named by the execution token. Off we go.
fw_execute:
	dw	execute_c
execute_c:
	pop	de
	ld	a,(de)
	ld	l,a
	inc	de
	ld	a,(de)
	ld	h,a
	inc	de
	jp	(hl)
; fw_fill: 25 bytes through the next word field. Fill a memory range with one byte value. Same paint everywhere.
fw_fill:
	dw	fill_c
fill_c:
	ld	(ipsave),bc
	pop	de
	pop	bc
	pop	hl
fill_loop:
	ld	a,b
	or	c
	jr	z,fill_done
	ld	(hl),e
	inc	hl
	dec	bc
	jr	fill_loop
fill_done:
	ld	bc,(ipsave)
	jp	next
; fw_cmove: 22 bytes through the next word field. Copy bytes forward. Overlap is the caller’s problem.
fw_cmove:
	dw	cmove_c
cmove_c:
	ld	(ipsave),bc
	pop	bc
	pop	de
	pop	hl
	ld	a,b
	or	c
	jr	z,cmove_done
	ldir
cmove_done:
	ld	bc,(ipsave)
	jp	next
; fw_cmovep: 28 bytes through the next word field. Copy bytes backward for an overlapping range. No tail trampling.
fw_cmovep:
	dw	cmovep_c
cmovep_c:
	ld	(ipsave),bc
	pop	bc
	pop	de
	pop	hl
	ld	a,b
	or	c
	jr	z,cmovep_done
	dec	bc
	add	hl,bc
	ex	de,hl
	add	hl,bc
	ex	de,hl
	inc	bc
	lddr
cmovep_done:
	ld	bc,(ipsave)
	jp	next
; fw_count: 29 bytes through the next word field. Turn a counted string into address and length. No extra terminator.
fw_count:
	dw	count_c
count_c:
	pop	hl
	ld	e,(hl)
	ld	d,0
	inc	hl
	push	hl
	push	de
	jp	next
numout_ns:
	ld	hl,numbuf_end
	or	a
	sbc	hl,de
	ld	b,h
	ld	c,l
	ld	hl,1
	ld	a,4
	call	SYS
	ret
; fw_numstart: 11 bytes through the next word field. Start pictured-number output. The buffer has the floor.
fw_numstart:
	dw	numstart_c
numstart_c:
	ld	hl,hold_end
	ld	(hld),hl
	jp	next
; fw_hold: 17 bytes through the next word field. Prepend one character to the pictured-number buffer.
fw_hold:
	dw	hold_c
hold_c:
	pop	hl
	ld	a,l
	ld	de,(hld)
	dec	de
	ld	(de),a
	ld	(hld),de
	jp	next
; fw_sign: 22 bytes through the next word field. Add a minus sign to pictured output when needed. No freebies.
fw_sign:
	dw	sign_c
sign_c:
	pop	hl
	bit	7,h
	jr	z,sign_done
	ld	de,(hld)
	dec	de
	ld	a,'-'
	ld	(de),a
	ld	(hld),de
sign_done:
	jp	next
; fw_hashnum: 74 bytes through the next word field. Prepend one digit of the number in the current base.
fw_hashnum:
	dw	hashnum_c
hashnum_c:
	ld	(ipsave),bc
	pop	hl
	ld	(ph_hi),hl
	pop	hl
	ld	(ph_lo),hl
	ld	hl,(ph_hi)
	ld	de,(base)
	call	udivmod
	ld	(ph_hi),hl
	ld	hl,(ph_lo)
	ld	de,(base)
	call	udiv32
	ld	(ph_lo),hl
	ld	a,c
	cp	10
	jr	c,hash_dig
	add	a,7
hash_dig:
	add	a,'0'
	ld	de,(hld)
	dec	de
	ld	(de),a
	ld	(hld),de
	ld	hl,(ph_lo)
	push	hl
	ld	hl,(ph_hi)
	push	hl
	ld	bc,(ipsave)
	jp	next
; fw_numend: 19 bytes through the next word field. Finish pictured-number output and return the string. Curtain.
fw_numend:
	dw	numend_c
numend_c:
	pop	hl
	pop	hl
	ld	de,(hld)
	ld	hl,hold_end
	or	a
	sbc	hl,de
	push	de
	push	hl
	jp	next
; fw_dotr: 95 bytes through the next word field. Right-align a signed number inside its field. Space is expensive.
fw_dotr:
	dw	dotr_c
dotr_c:
	ld	(dr_ip),bc
	pop	hl
	ld	(dr_w),hl
	pop	hl
	xor	a
	ld	(dot_neg),a
	bit	7,h
	jr	z,dotr_pos
	ld	a,1
	ld	(dot_neg),a
	ld	a,l
	cpl
	ld	l,a
	ld	a,h
	cpl
	ld	h,a
	inc	hl
dotr_pos:
	call	convnum
	ld	a,(dot_neg)
	or	a
	jr	z,dotr_pad
	dec	de
	ld	a,'-'
	ld	(de),a
dotr_pad:
	ld	(dr_p),de
	ld	hl,numbuf_end
	or	a
	sbc	hl,de
	ex	de,hl
	ld	hl,(dr_w)
	or	a
	sbc	hl,de
	jr	c,dotr_write
dotr_sploop:
	ld	a,h
	or	l
	jr	z,dotr_write
	dec	hl
	ld	(dr_w),hl
	ld	a,' '
	call	putc
	ld	hl,(dr_w)
	jr	dotr_sploop
dotr_write:
	ld	de,(dr_p)
	call	numout_ns
	ld	bc,(dr_ip)
	jp	next
; fw_udotr: 65 bytes through the next word field. Right-align an unsigned number in its field. Neatly parked.
fw_udotr:
	dw	udotr_c
udotr_c:
	ld	(dr_ip),bc
	pop	hl
	ld	(dr_w),hl
	pop	hl
	call	convnum
	ld	(dr_p),de
	ld	hl,numbuf_end
	or	a
	sbc	hl,de
	ex	de,hl
	ld	hl,(dr_w)
	or	a
	sbc	hl,de
	jr	c,udotr_write
udotr_sploop:
	ld	a,h
	or	l
	jr	z,udotr_write
	dec	hl
	ld	(dr_w),hl
	ld	a,' '
	call	putc
	ld	hl,(dr_w)
	jr	udotr_sploop
udotr_write:
	ld	de,(dr_p)
	call	numout_ns
	ld	bc,(dr_ip)
	jp	next
; fw_roll: 70 bytes through the next word field. Bring one chosen stack cell to the top. Everyone else shuffles.
fw_roll:
	dw	roll_c
roll_c:
	ld	(ipsave),bc
	pop	hl
	ld	a,h
	or	l
	jr	z,roll_done
	add	hl,hl
	ld	(roll_n),hl
	ld	hl,0
	add	hl,sp
	ld	(roll_sp),hl
	ld	de,(roll_n)
	add	hl,de
	ld	e,(hl)
	inc	hl
	ld	d,(hl)
	ld	(roll_xn),de
	ld	hl,(roll_sp)
	ld	de,(roll_n)
	add	hl,de
	dec	hl
	ld	d,h
	ld	e,l
	inc	de
	inc	de
	ld	bc,(roll_n)
	lddr
	ld	hl,(roll_sp)
	ld	de,(roll_xn)
	ld	(hl),e
	inc	hl
	ld	(hl),d
roll_done:
	ld	bc,(ipsave)
	jp	next
; fw_dashtrail: 25 bytes through the next word field. Trim trailing spaces from a string. Less luggage.
fw_dashtrail:
	dw	dashtrail_c
dashtrail_c:
	pop	de
	pop	hl
dashtrail_loop:
	ld	a,d
	or	e
	jr	z,dashtrail_done
	push	hl
	add	hl,de
	dec	hl
	ld	a,(hl)
	pop	hl
	cp	32
	jr	nz,dashtrail_done
	dec	de
	jr	dashtrail_loop
dashtrail_done:
	push	hl
	push	de
	jp	next
; fw_here: 9 bytes through the next word field. Return the next free dictionary address. Mind the ceiling.
fw_here:
	dw	here_c
here_c:
	ld	hl,(dp)
	push	hl
	jp	next
; fw_comma: 16 bytes through the next word field. Store a word in the dictionary and advance the pointer.
fw_comma:
	dw	comma_c
comma_c:
	pop	de
	ld	hl,(dp)
	ld	(hl),e
	inc	hl
	ld	(hl),d
	inc	hl
	ld	(dp),hl
	jp	next
; fw_ccomma: 14 bytes through the next word field. Store one byte in the dictionary and step once.
fw_ccomma:
	dw	ccomma_c
ccomma_c:
	pop	de
	ld	hl,(dp)
	ld	(hl),e
	inc	hl
	ld	(dp),hl
	jp	next
; fw_allot: 13 bytes through the next word field. Advance the dictionary pointer by the requested byte count.
fw_allot:
	dw	allot_c
allot_c:
	pop	de
	ld	hl,(dp)
	add	hl,de
	ld	(dp),hl
	jp	next
; fw_state: 9 bytes through the next word field. Push the address of compilation state. The switch lives here.
fw_state:
	dw	state_c
state_c:
	ld	hl,state
	push	hl
	jp	next
; fw_find: 113 bytes to the next word. Find dictionary name; 1 immediate, -1 normal, 0 missing. No guesses.
fw_find:
	dw	find_c
find_c:
	ld	(ipsave),bc
	pop	hl
	ld	a,(hl)
	ld	(find_ilen),a
	inc	hl
	ld	(find_iptr),hl
	ld	hl,(latest)
find_loop:
	ld	a,h
	or	l
	jp	z,find_none
	ld	(find_cur),hl
	inc	hl
	inc	hl
	ld	a,(hl)
	ld	(find_fl),a
	and	3fh
	ld	c,a
	ld	a,(find_ilen)
	cp	c
	jr	nz,find_next
	inc	hl
	ld	de,(find_iptr)
	ld	b,c
find_cmp:
	ld	a,(de)
	cp	(hl)
	jr	nz,find_next
	inc	hl
	inc	de
	djnz	find_cmp
	ld	e,(hl)
	inc	hl
	ld	d,(hl)
	push	de
	ld	a,(find_fl)
	and	80h
	jr	z,find_norm
	ld	hl,1
	push	hl
	ld	bc,(ipsave)
	jp	next
find_norm:
	ld	hl,-1
	push	hl
	ld	bc,(ipsave)
	jp	next
find_next:
	ld	hl,(find_cur)
	ld	e,(hl)
	inc	hl
	ld	d,(hl)
	ex	de,hl
	jr	find_loop
find_none:
	ld	hl,(find_iptr)
	dec	hl
	push	hl
	ld	hl,0
	push	hl
	ld	bc,(ipsave)
	jp	next
; fw_tib: 9 bytes through the next word field. Push terminal-input buffer address. The keys landed here.
fw_tib:
	dw	tib_c
tib_c:
	ld	hl,tib
	push	hl
	jp	next
; fw_numtib: 9 bytes through the next word field. Push terminal-input length address. Count before reading.
fw_numtib:
	dw	numtib_c
numtib_c:
	ld	hl,numtib
	push	hl
	jp	next
; fw_toin: 9 bytes through the next word field. Push the input position address. The parser keeps score.
fw_toin:
	dw	toin_c
toin_c:
	ld	hl,toin
	push	hl
	jp	next
; fw_span: 9 bytes through the next word field. Push the last input-length address. A little history.
fw_span:
	dw	span_c
span_c:
	ld	hl,span
	push	hl
	jp	next
; fw_word: 164 bytes to next word. Parse TIB into counted wbuf using the supplied delimiter.
fw_word:
	dw	word_c
word_c:
	ld	(ipsave),bc
	pop	hl
	ld	a,l
	ld	(word_delim),a
	ld	hl,tib
	ld	de,(numtib)
	add	hl,de
	ld	(tibend),hl
	ld	hl,tib
	ld	de,(toin)
	add	hl,de
word_sk:
	ld	de,(tibend)
	or	a
	push	hl
	sbc	hl,de
	pop	hl
	jp	nc,word_empty
	ld	a,(hl)
	ld	b,a
	ld	a,(word_delim)
	cp	b
	jr	nz,word_cinit
	inc	hl
	jr	word_sk
word_cinit:
	ld	de,wbuf
	inc	de
	ld	(word_dp),de
	xor	a
	ld	(word_len),a
word_cl:
	ld	de,(tibend)
	or	a
	push	hl
	sbc	hl,de
	pop	hl
	jr	nc,word_cdone
	ld	a,(hl)
	ld	b,a
	ld	a,(word_delim)
	cp	b
	jr	z,word_cdone
	ld	a,b
	ld	de,(word_dp)
	ld	(de),a
	inc	de
	ld	(word_dp),de
	inc	hl
	ld	a,(word_len)
	inc	a
	ld	(word_len),a
	jr	word_cl
word_cdone:
	ld	de,(tibend)
	or	a
	push	hl
	sbc	hl,de
	pop	hl
	jr	nc,word_noeat
	inc	hl
word_noeat:
	ld	de,tib
	or	a
	sbc	hl,de
	ld	(toin),hl
	ld	a,(word_len)
	ld	(wbuf),a
	ld	hl,wbuf
	push	hl
	ld	bc,(ipsave)
	jp	next
word_empty:
	ld	hl,(numtib)
	ld	(toin),hl
	xor	a
	ld	(wbuf),a
	ld	hl,wbuf
	push	hl
	ld	bc,(ipsave)
	jp	next
; fw_number: 176 bytes to next word. Parse a counted string in the current base; return value and flag.
fw_number:
	dw	number_c
number_c:
	ld	(ipsave),bc
	pop	hl
	ld	a,(hl)
	or	a
	jp	z,num_fail
	ld	(num_len),a
	inc	hl
	ld	(num_ptr),hl
	xor	a
	ld	(num_neg),a
	ld	a,(hl)
	cp	'-'
	jr	nz,num_init
	ld	a,1
	ld	(num_neg),a
	ld	hl,(num_ptr)
	inc	hl
	ld	(num_ptr),hl
	ld	a,(num_len)
	dec	a
	ld	(num_len),a
	jp	z,num_fail
num_init:
	ld	hl,0
	ld	(num_acc),hl
num_loop:
	ld	a,(num_len)
	or	a
	jp	z,num_ok
	ld	hl,(num_ptr)
	ld	a,(hl)
	sub	'0'
	jp	c,num_fail
	cp	10
	jr	c,num_haved
	sub	7
	cp	10
	jp	c,num_fail
num_haved:
	ld	(num_dig),a
	ld	a,(base)
	ld	b,a
	ld	a,(num_dig)
	cp	b
	jr	nc,num_fail
	ld	hl,(num_acc)
	ex	de,hl
	ld	a,(base)
	ld	b,a
	ld	hl,0
num_mul:
	add	hl,de
	djnz	num_mul
	ld	a,(num_dig)
	ld	e,a
	ld	d,0
	add	hl,de
	ld	(num_acc),hl
	ld	hl,(num_ptr)
	inc	hl
	ld	(num_ptr),hl
	ld	a,(num_len)
	dec	a
	ld	(num_len),a
	jr	num_loop
num_ok:
	ld	hl,(num_acc)
	ld	a,(num_neg)
	or	a
	jr	z,num_pos
	ld	a,l
	cpl
	ld	l,a
	ld	a,h
	cpl
	ld	h,a
	inc	hl
num_pos:
	push	hl
	ld	hl,-1
	push	hl
	ld	bc,(ipsave)
	jp	next
num_fail:
	ld	hl,0
	push	hl
	push	hl
	ld	bc,(ipsave)
	jp	next
; Forth runtime BSS: 2609 bytes. Dictionary and return stack eat most of it.
	section	bss
rstack:
	ds	256
rstack_top:
ipsave:
	ds	2
udiv_dvs:
	ds	2
rot_t:
	ds	2
fdiv_d:
	ds	2
fdiv_qs:
	ds	1
fdiv_ns:
	ds	1
fdiv_rz:
	ds	1
spc_n:
	ds	2
charbuf:
	ds	1
dot_neg:
	ds	1
numbuf:
	ds	18
numbuf_end:
base:
	ds	2
cnv_p:
	ds	2
umm:
	ds	2
hold_buf:
	ds	34
hold_end:
hld:
	ds	2
ph_lo:
	ds	2
ph_hi:
	ds	2
dr_w:
	ds	2
dr_p:
	ds	2
dr_ip:
	ds	2
roll_n:
	ds	2
roll_sp:
	ds	2
roll_xn:
	ds	2
state:
	ds	2
dp:
	ds	2
dict_area:
	ds	2048
latest:
	ds	2
find_ilen:
	ds	1
find_iptr:
	ds	2
find_cur:
	ds	2
find_fl:
	ds	1
tib:
	ds	82
numtib:
	ds	2
toin:
	ds	2
span:
	ds	2
wbuf:
	ds	82
word_delim:
	ds	1
word_len:
	ds	1
word_dp:
	ds	2
tibend:
	ds	2
num_len:
	ds	1
num_ptr:
	ds	2
num_neg:
	ds	1
num_acc:
	ds	2
num_dig:
	ds	1
sp0:
	ds	2
pl_idx:
	ds	2
pl_bsign:
	ds	1
ts_b:
	ds	2
ts_c:
	ds	2
ts_d:
	ds	2
dtmp_lo1:
	ds	2
dtmp_hi1:
	ds	2
dtmp_lo2:
	ds	2
dtmp_hi2:
	ds	2
