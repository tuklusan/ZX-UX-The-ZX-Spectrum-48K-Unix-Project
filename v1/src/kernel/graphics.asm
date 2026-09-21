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
; P7.01 exposes these routines only through the validated public syscall ABI.
; P7.02 delegates every direct pixel address to the one canonical zx48_bitmap_address helper.

    MACRO EMIT_GRAPHICS_ROUTINES
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
    ld a,(gfx_mask)
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
    or a
    ret

; DE retains the public x/y pair from zx48_gfx_pixel_addr.
; Return HL = hardware attribute cell for that exact pixel.
zx48_gfx_attr_address_from_de:
    ld a,e
    and $f8
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    ld a,d
    srl a
    srl a
    srl a
    ld c,a
    ld b,0
    add hl,bc
    ld bc,ATTR_START
    add hl,bc
    ret

; P7.06: H=x,L=y -> H=0,L=0/1 with no visible/cursor/attribute mutation.
zx48_gfx_point:
    ld a,l
    cp 192
    jp nc,zx48_gfx_bad
    call zx48_gfx_pixel_addr
    ld a,(gfx_mask)
    and (hl)
    jr z,zx48_gfx_point_zero
    ld hl,1
    xor a
    or a
    ret
zx48_gfx_point_zero:
    ld hl,0
    xor a
    or a
    ret

; H=x,L=y -> bitmap HL, mask in gfx_mask.
zx48_gfx_pixel_addr:
    ld a,h
    ld c,a
    srl c
    srl c
    srl c
    ld b,l
    push hl
    call zx48_bitmap_address
    pop de
    ld a,d
    and 7
    ld c,a
    ld a,$80
zx48_gfx_mask_loop:
    ld b,c
    ld c,a
    ld a,b
    or a
    ld a,c
    jr z,zx48_gfx_mask_done
    srl a
    dec b
    ld c,b
    jr zx48_gfx_mask_loop
zx48_gfx_mask_done:
    ld (gfx_mask),a
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
    ; dx=abs(x2-x), sx=+/-1
    ld a,(gfx_x2)
    ld b,a
    ld a,(gfx_x)
    cp b
    jr c,zx48_gfx_dx_pos
    jr z,zx48_gfx_dx_zero
    sub b
    ld (gfx_dx),a
    ld a,$ff
    ld (gfx_sx),a
    jr zx48_gfx_dy
zx48_gfx_dx_pos:
    ld a,b
    ld c,a
    ld a,(gfx_x)
    ld b,a
    ld a,c
    sub b
    ld (gfx_dx),a
    ld a,1
    ld (gfx_sx),a
    jr zx48_gfx_dy
zx48_gfx_dx_zero:
    xor a
    ld (gfx_dx),a
    ld (gfx_sx),a
zx48_gfx_dy:
    ld a,(gfx_y2)
    ld b,a
    ld a,(gfx_y)
    cp b
    jr c,zx48_gfx_dy_pos
    jr z,zx48_gfx_dy_zero
    sub b
    ld (gfx_dy),a
    ld a,$ff
    ld (gfx_sy),a
    jr zx48_gfx_line_start
zx48_gfx_dy_pos:
    ld a,b
    ld c,a
    ld a,(gfx_y)
    ld b,a
    ld a,c
    sub b
    ld (gfx_dy),a
    ld a,1
    ld (gfx_sy),a
    jr zx48_gfx_line_start
zx48_gfx_dy_zero:
    xor a
    ld (gfx_dy),a
    ld (gfx_sy),a
    jr zx48_gfx_line_start
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
    or a
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
    or a
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
    ; Four unique axis points for y=0.
    ld a,(gfx_circle_x)
    ld b,a
    push bc
    ld a,(gfx_cx)
    add a,b
    jr c,zx48_gfx_circle_axis_xp_done
    ld h,a
    ld a,(gfx_cy)
    ld l,a
    call zx48_gfx_plot
zx48_gfx_circle_axis_xp_done:
    pop bc

    push bc
    ld a,(gfx_cx)
    sub b
    jr c,zx48_gfx_circle_axis_xm_done
    ld h,a
    ld a,(gfx_cy)
    ld l,a
    call zx48_gfx_plot
zx48_gfx_circle_axis_xm_done:
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
zx48_gfx_circle_pair:
    push bc
    ld a,(gfx_cx)
    add a,b
    jr c,zx48_gfx_circle_pp_done
    ld h,a
    ld a,(gfx_cy)
    add a,c
    jr c,zx48_gfx_circle_pp_done
    cp 192
    jr nc,zx48_gfx_circle_pp_done
    ld l,a
    call zx48_gfx_plot
zx48_gfx_circle_pp_done:
    pop bc

    push bc
    ld a,(gfx_cx)
    sub b
    jr c,zx48_gfx_circle_mp_done
    ld h,a
    ld a,(gfx_cy)
    add a,c
    jr c,zx48_gfx_circle_mp_done
    cp 192
    jr nc,zx48_gfx_circle_mp_done
    ld l,a
    call zx48_gfx_plot
zx48_gfx_circle_mp_done:
    pop bc

    push bc
    ld a,(gfx_cx)
    add a,b
    jr c,zx48_gfx_circle_pm_done
    ld h,a
    ld a,(gfx_cy)
    sub c
    jr c,zx48_gfx_circle_pm_done
    ld l,a
    call zx48_gfx_plot
zx48_gfx_circle_pm_done:
    pop bc

    ld a,(gfx_cx)
    sub b
    ret c
    ld h,a
    ld a,(gfx_cy)
    sub c
    ret c
    ld l,a
    jp zx48_gfx_plot

; P7.07 shared console/graphics state: H=selector,L=value.
; Selectors: ink,paper,bright,flash,inverse,over; values are validated before commit.
zx48_gfx_attr:
    ld a,h
    cp 6
    jp nc,zx48_gfx_bad
    ld (gfx_selector),a
    ld a,l
    ld (gfx_value),a
    ld a,(gfx_selector)
    cp 2
    jr nc,zx48_gfx_attr_bool
    ld a,(gfx_value)
    cp 8
    jp nc,zx48_gfx_bad
    jr zx48_gfx_attr_store
zx48_gfx_attr_bool:
    ld a,(gfx_value)
    cp 2
    jp nc,zx48_gfx_bad
zx48_gfx_attr_store:
    ld a,(gfx_selector)
    ld e,a
    ld d,0
    ld hl,gfx_attr_state
    add hl,de
    ld a,(gfx_value)
    ld (hl),a
    ld a,(gfx_attr_state)
    and 7
    ld b,a
    ld a,(gfx_attr_state+1)
    and 7
    rlca
    rlca
    rlca
    or b
    ld b,a
    ld a,(gfx_attr_state+2)
    or a
    jr z,zx48_gfx_attr_no_bright
    ld a,b
    or $40
    ld b,a
zx48_gfx_attr_no_bright:
    ld a,(gfx_attr_state+3)
    or a
    jr z,zx48_gfx_attr_no_flash
    ld a,b
    or $80
    ld b,a
zx48_gfx_attr_no_flash:
    ld a,b
    ld (tty_current_attr),a
    xor a
    or a
    ret

; P7.08: H=0,L=color; only the central ULA shadow may publish the border.
zx48_gfx_border:
    ld a,h
    or a
    jp nz,zx48_gfx_bad
    ld a,l
    cp 8
    jp nc,zx48_gfx_bad
    jp zx48_ula_set_border
zx48_gfx_bad:
    ld a,E_INVAL
    scf
    ret

gfx_mask: db 0
gfx_attr_state: db 7,0,0,0,0,0
gfx_selector: db 0
gfx_value: db 0
gfx_x: db 0
gfx_y: db 0
gfx_x2: db 0
gfx_y2: db 0
gfx_dx: db 0
gfx_dy: db 0
gfx_sx: db 0
gfx_sy: db 0
gfx_err: dw 0
gfx_e2: dw 0
gfx_cx: db 0
gfx_cy: db 0
gfx_r: db 0
gfx_circle_x: db 0
gfx_circle_y: db 0
gfx_circle_d: dw 0
    ENDM
