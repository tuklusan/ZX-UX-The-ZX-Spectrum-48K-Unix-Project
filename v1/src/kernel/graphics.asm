; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Proprietary rights reserved except as expressly licensed herein.
;
; ZX-UX Sinclair ZX Spectrum Unix
; This file is governed by the SANYALnet Labs Non-Commercial License in the
; root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
; for AI/ML model training are prohibited unless separately authorized.
;
; Attribution is required: "Based on original work by Supratim Sanyal of
; SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
; patent, trademark, and governing-law provisions.
;
; Bounded native Spectrum graphics primitives. Pixel writes touch bitmap only.
; P7.19 integrated golden qualification binds screen/attribute/UDG guard behavior.
; P7.01 exposes these routines only through the validated public syscall ABI.
; P7.02 delegates every direct pixel address to the one canonical zx48_bitmap_address helper.

    MACRO EMIT_GRAPHICS_ROUTINES
; P7.21 aggregate acceptance revalidates this graphics owner at the exact candidate head.
; H=x,L=y. Exact 0..255/0..191 coordinate domain.
; P7.03 uses a native PLOT-SUB-visible replacement because the 48K ROM
; PIXEL-ADD/PLOT-SUB contract rejects y>175 and uses BASIC's 175-y origin,
; which cannot satisfy ZX-UX's P7.02-frozen full top-origin 0..191 bitmap ABI.
; The pixel modes and attribute publication below remain byte-equivalent to
; PLOT-SUB after applying the ZX-UX coordinate mapping.
zx48_gfx_plot:
    ld a,l
    cp 192
    jp nc,zx48_gfx_bad
    call zx48_cursor_hide
    call zx48_gfx_pixel_addr
    ld b,a
    ld a,(gfx_attr_state+5)       ; OVER
    or a
    jr z,zx48_gfx_plot_over0
    ld a,(gfx_attr_state+4)       ; INVERSE
    or a
    ld a,(hl)
    jr nz,zx48_gfx_plot_store     ; OVER 1 + INVERSE 1 leaves pixel unchanged.
    xor b                         ; OVER 1 + INVERSE 0 toggles the pixel.
    jr zx48_gfx_plot_store
zx48_gfx_plot_over0:
    ld a,(hl)
    ld c,a
    ld a,(gfx_attr_state+4)       ; INVERSE
    or a
    ld a,c
    jr nz,zx48_gfx_plot_clear
    or b                          ; OVER 0 + INVERSE 0 sets the pixel.
    jr zx48_gfx_plot_store
zx48_gfx_plot_clear:
    ld a,b
    cpl
    and c                         ; OVER 0 + INVERSE 1 clears the pixel.
zx48_gfx_plot_store:
    ld (hl),a
    call zx48_gfx_attr_address_from_de
    ld a,(tty_current_attr)
    ld (hl),a
    call zx48_cursor_show
    xor a
    ret

; HL is the current bitmap byte. Preserve its low byte: that is already
; ((y>>3)&7)*32 + x/8. Convert bitmap H bits 4:3 back to y/64, then add ATTR_START.
zx48_gfx_attr_address_from_de:
    ld a,h
    and $18
    rrca
    rrca
    rrca
    ld h,a
    ld bc,ATTR_START
    add hl,bc
    ret

; P7.06: H=x,L=y -> H=0,L=0/1 with no visible/cursor/attribute mutation.
zx48_gfx_point:
    ld a,l
    cp 192
    jp nc,zx48_gfx_bad
    call zx48_gfx_pixel_addr
    and (hl)
    ld hl,0
    jr z,zx48_gfx_point_done
    inc l
zx48_gfx_point_done:
    xor a
    ret

; H=x,L=y -> bitmap HL, mask in A. DE retains the public x/y pair.
zx48_gfx_pixel_addr:
    ld a,h
    ld c,a
    srl c
    srl c
    srl c
    ld b,l
    ld d,a
    call zx48_bitmap_address
    ld a,d
    and 7
    ld b,a
    ld a,$80
    ret z
zx48_gfx_mask_loop:
    rrca
    djnz zx48_gfx_mask_loop
    ret

; HL -> x1,y1,x2,y2. Bresenham with 16-bit signed error scratch.
; P7.04 keeps the verified ROM 24BA contract documented but uses the native
; replacement because that lower ROM path ultimately reaches PLOT-SUB and the
; BASIC y<=175/origin contract cannot satisfy the ZX-UX 0..191 coordinate ABI.
zx48_gfx_draw:
    ; Validate both endpoints before any graphics scratch or display mutation.
    push hl
    inc hl
    ld a,(hl)
    cp 192
    jr nc,zx48_gfx_draw_bad
    inc hl
    inc hl
    ld a,(hl)
    cp 192
    jr nc,zx48_gfx_draw_bad
    pop hl
    ld a,(hl)
    ld (gfx_x),a
    inc hl
    ld a,(hl)
    ld (gfx_y),a
    inc hl
    ld a,(hl)
    ld (gfx_x2),a
    inc hl
    ld a,(hl)
    ld (gfx_y2),a
    ; Derive both absolute deltas and signed unit steps through one compact path.
    ld a,(gfx_x)
    ld c,a
    ld a,(gfx_x2)
    call zx48_gfx_delta
    ld (gfx_dx),a
    ld a,b
    ld (gfx_sx),a
    ld a,(gfx_y)
    ld c,a
    ld a,(gfx_y2)
    call zx48_gfx_delta
    ld (gfx_dy),a
    ld a,b
    ld (gfx_sy),a
    jr zx48_gfx_line_start

; C=current coordinate, A=target. Return A=absolute delta and B=-1/0/+1.
zx48_gfx_delta:
    sub c
    jr z,zx48_gfx_delta_zero
    jr c,zx48_gfx_delta_negative
    ld b,1
    ret
zx48_gfx_delta_negative:
    neg
    ld b,$ff
    ret
zx48_gfx_delta_zero:
    ld b,a
    ret
zx48_gfx_draw_bad:
    pop hl
    jp zx48_gfx_bad
zx48_gfx_line_start:
    ; signed err = dx-dy in 16 bits.
    ld a,(gfx_dx)
    ld l,a
    ld h,0
    ld a,(gfx_dy)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (gfx_err),hl
zx48_gfx_line_loop:
    ld a,(gfx_x)
    ld h,a
    ld a,(gfx_y)
    ld l,a
    call zx48_gfx_plot
    ret c
    ld a,(gfx_x)
    ld b,a
    ld a,(gfx_x2)
    cp b
    jr nz,zx48_gfx_line_step
    ld a,(gfx_y)
    ld b,a
    ld a,(gfx_y2)
    cp b
    jr nz,zx48_gfx_line_step
    xor a
    ret
zx48_gfx_line_step:
    ld hl,(gfx_err)
    add hl,hl                    ; e2=2*err
    ld (gfx_e2),hl
    ; if e2 > -dy then err-=dy, x+=sx
    ld a,(gfx_dy)
    neg
    ld e,a
    ld d,$ff
    ld hl,(gfx_e2)
    or a
    sbc hl,de
    bit 7,h
    jr nz,zx48_gfx_line_skip_x
    ld hl,(gfx_err)
    ld a,(gfx_dy)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (gfx_err),hl
    ld a,(gfx_sx)
    ld b,a
    ld a,(gfx_x)
    add a,b
    ld (gfx_x),a
zx48_gfx_line_skip_x:
    ; if e2 < dx then err+=dx,y+=sy
    ld hl,(gfx_e2)
    ld a,(gfx_dx)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    bit 7,h
    jr z,zx48_gfx_line_loop
    ld hl,(gfx_err)
    ld a,(gfx_dx)
    ld e,a
    ld d,0
    add hl,de
    ld (gfx_err),hl
    ld a,(gfx_sy)
    ld b,a
    ld a,(gfx_y)
    add a,b
    ld (gfx_y),a
    jr zx48_gfx_line_loop

; HL -> x,y,radius. Native integer midpoint circle with exact clipping.
; P7.05 records the Class-B ROM-assisted option but uses the Section-14.9
; fallback because the ROM graphics path inherits BASIC's y<=175/origin
; semantics and cannot expose the ZX-UX 0..191 top-origin contract byte-for-byte.
zx48_gfx_circle:
    ; Validate center y before touching graphics scratch or display state.
    push hl
    inc hl
    ld a,(hl)
    cp 192
    jr nc,zx48_gfx_circle_bad
    pop hl
    ld a,(hl)
    ld (gfx_cx),a
    inc hl
    ld a,(hl)
    ld (gfx_cy),a
    inc hl
    ld a,(hl)
    ld (gfx_r),a
    or a
    jr nz,zx48_gfx_circle_init
    ld a,(gfx_cx)
    ld h,a
    ld a,(gfx_cy)
    ld l,a
    jp zx48_gfx_plot
zx48_gfx_circle_bad:
    pop hl
    jp zx48_gfx_bad

zx48_gfx_circle_init:
    ld a,(gfx_r)
    ld (gfx_circle_x),a
    xor a
    ld (gfx_circle_y),a
    ld hl,1
    ld a,(gfx_r)
    ld e,a
    ld d,0
    or a
    sbc hl,de
    ld (gfx_circle_d),hl

zx48_gfx_circle_loop:
    call zx48_gfx_circle_octants
    ld a,(gfx_circle_x)
    ld b,a
    ld a,(gfx_circle_y)
    cp b
    jr nc,zx48_gfx_circle_done

    inc a
    ld (gfx_circle_y),a
    ld hl,(gfx_circle_d)
    bit 7,h
    jr z,zx48_gfx_circle_nonnegative

    ; err < 0: err += 2*y + 1
    ld a,(gfx_circle_y)
    ld l,a
    ld h,0
    add hl,hl
    inc hl
    ld de,(gfx_circle_d)
    add hl,de
    ld (gfx_circle_d),hl
    jr zx48_gfx_circle_loop

zx48_gfx_circle_nonnegative:
    ; err >= 0: x--, err += 2*(y-x) + 1
    ld a,(gfx_circle_x)
    dec a
    ld (gfx_circle_x),a
    ld e,a
    ld d,0
    ld a,(gfx_circle_y)
    ld l,a
    ld h,0
    or a
    sbc hl,de
    add hl,hl
    inc hl
    ld de,(gfx_circle_d)
    add hl,de
    ld (gfx_circle_d),hl
    jr zx48_gfx_circle_loop

zx48_gfx_circle_done:
    xor a
    ret

; Plot each unique midpoint-circle point at most once. This matters for OVER:
; duplicate symmetric points would otherwise toggle an even number of times.
zx48_gfx_circle_octants:
    ld a,(gfx_circle_y)
    or a
    jr z,zx48_gfx_circle_axis
    ld b,a
    ld a,(gfx_circle_x)
    cp b
    jr z,zx48_gfx_circle_diag

    ; General case: (x,y) and (y,x), four signs each.
    ld b,a
    ld a,(gfx_circle_y)
    ld c,a
    call zx48_gfx_circle_pair
    ld a,(gfx_circle_y)
    ld b,a
    ld a,(gfx_circle_x)
    ld c,a
    jp zx48_gfx_circle_pair

zx48_gfx_circle_diag:
    ld a,(gfx_circle_x)
    ld b,a
    ld c,a
    jp zx48_gfx_circle_pair

zx48_gfx_circle_axis:
    ; Four unique axis points for y=0. Reuse the general clipped x pair.
    ld a,(gfx_circle_x)
    ld b,a
    push bc
    ld a,(gfx_cy)
    ld l,a
    call zx48_gfx_circle_x_pair
    pop bc

    push bc
    ld a,(gfx_cy)
    add a,b
    jr c,zx48_gfx_circle_axis_yp_done
    cp 192
    jr nc,zx48_gfx_circle_axis_yp_done
    ld l,a
    ld a,(gfx_cx)
    ld h,a
    call zx48_gfx_plot
zx48_gfx_circle_axis_yp_done:
    pop bc

    ld a,(gfx_cy)
    sub b
    ret c
    ld l,a
    ld a,(gfx_cx)
    ld h,a
    jp zx48_gfx_plot

; B=absolute x offset, C=absolute y offset; both nonzero.
; Resolve each y once, then share the clipped +/-x publication path.
zx48_gfx_circle_pair:
    push bc
    ld a,(gfx_cy)
    add a,c
    jr c,zx48_gfx_circle_pair_plus_done
    cp 192
    jr nc,zx48_gfx_circle_pair_plus_done
    ld l,a
    call zx48_gfx_circle_x_pair
zx48_gfx_circle_pair_plus_done:
    pop bc
    ld a,(gfx_cy)
    sub c
    ret c
    ld l,a
    jp zx48_gfx_circle_x_pair

; B=absolute x offset, L=validated y.
zx48_gfx_circle_x_pair:
    push bc
    push hl
    ld a,(gfx_cx)
    add a,b
    jr c,zx48_gfx_circle_xp_done
    ld h,a
    call zx48_gfx_plot
zx48_gfx_circle_xp_done:
    pop hl
    pop bc
    ld a,(gfx_cx)
    sub b
    ret c
    ld h,a
    jp zx48_gfx_plot

; P7.07 shared console/graphics state: H=selector,L=value.
; Selectors: ink,paper,bright,flash,inverse,over; values are validated before commit.
zx48_gfx_attr:
    ld a,h
    cp 6
    jp nc,zx48_gfx_bad
    ld e,a
    cp 2
    ld a,l
    jr c,zx48_gfx_attr_color
    cp 2
    jp nc,zx48_gfx_bad
    jr zx48_gfx_attr_store
zx48_gfx_attr_color:
    cp 8
    jp nc,zx48_gfx_bad
zx48_gfx_attr_store:
    ld d,0
    ld hl,gfx_attr_state
    add hl,de
    ld (hl),a

    ; Repack validated private state directly into the Spectrum attribute byte.
    ld a,(gfx_attr_state+1)
    rlca
    rlca
    rlca
    ld b,a
    ld a,(gfx_attr_state)
    or b
    ld b,a
    ld a,(gfx_attr_state+2)
    rrca
    rrca
    or b
    ld b,a
    ld a,(gfx_attr_state+3)
    rrca
    or b
    ld (tty_current_attr),a
    xor a
    ret

; P7.08: H=0,L=color; only the central ULA shadow may publish the border.
zx48_gfx_border:
    ld a,h
    or a
    jp nz,zx48_gfx_bad
    ld a,l
    cp 8
    jp nc,zx48_gfx_bad
    call zx48_ula_set_border
    xor a
    ret
zx48_gfx_bad:
    ld a,E_INVAL
    scf
    ret

; Preserve the nonzero attribute defaults in ordinary initialized data. All
; remaining zero-initialized graphics scratch lives in the fixed emergency reserve.
gfx_attr_state: db 7,0,0,0,0,0
GRAPHICS_STATE_BASE       EQU EMERGENCY_START+$67
gfx_selector              EQU GRAPHICS_STATE_BASE+0
gfx_value                 EQU GRAPHICS_STATE_BASE+1
gfx_x                     EQU GRAPHICS_STATE_BASE+2
gfx_y                     EQU GRAPHICS_STATE_BASE+3
gfx_x2                    EQU GRAPHICS_STATE_BASE+4
gfx_y2                    EQU GRAPHICS_STATE_BASE+5
gfx_dx                    EQU GRAPHICS_STATE_BASE+6
gfx_dy                    EQU GRAPHICS_STATE_BASE+7
gfx_sx                    EQU GRAPHICS_STATE_BASE+8
gfx_sy                    EQU GRAPHICS_STATE_BASE+9
gfx_err                   EQU GRAPHICS_STATE_BASE+10
gfx_e2                    EQU GRAPHICS_STATE_BASE+12
gfx_cx                    EQU GRAPHICS_STATE_BASE+14
gfx_cy                    EQU GRAPHICS_STATE_BASE+15
gfx_r                     EQU GRAPHICS_STATE_BASE+16
gfx_circle_x              EQU GRAPHICS_STATE_BASE+17
gfx_circle_y              EQU GRAPHICS_STATE_BASE+18
gfx_circle_d              EQU GRAPHICS_STATE_BASE+19
GRAPHICS_STATE_END        EQU GRAPHICS_STATE_BASE+21
    ASSERT GRAPHICS_STATE_END <= EMERGENCY_START+$7F
    ENDM
