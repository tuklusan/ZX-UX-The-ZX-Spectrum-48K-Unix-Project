; Fast right-panel blitter. ZX-UX screen is shared, left half is untouched.
        section text
        global _ballkeys,_screenbytes,_fastsprite,_panel_bg,_panel_clear
_ballkeys:
        ld d,0
        ld bc,0EFFEh
        in a,(c)
        bit 0,a
        jr nz,.not6
        set 0,d
.not6:  bit 1,a
        jr nz,.not7
        set 1,d
.not7:  ld bc,07FFEh
        in a,(c)
        bit 0,a
        jr nz,.notspace
        set 2,d
.notspace:
        ld l,d
        ld h,0
        ret
_screenbytes:
        ld hl,04000h
        ret
_panel_bg:
        xor a
        ld (fillval),a
        ld a,56
        ld (fillattr),a
        jr panel_fill
_panel_clear:
        xor a
        ld (fillval),a
        ld a,7
        ld (fillattr),a
panel_fill:
        ld a,32
        ld (bgrow),a
.bgrow:
        ld a,(bgrow)
        ld l,a
        ld h,0
        add hl,hl
        ld de,rowtable
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld a,16
        add a,e
        ld e,a
        ld b,16
        ld a,(fillval)
.fillpix:
        ld (de),a
        inc de
        djnz .fillpix
        ld a,(bgrow)
        inc a
        ld (bgrow),a
        cp 160
        jr nz,.bgrow
        ld hl,05890h      ; attribute row 4, column 16
        ld b,16
.attrrow:
        push bc
        ld b,16
        ld a,(fillattr)
.attrpix:
        ld (hl),a
        inc hl
        djnz .attrpix
        ld de,16
        add hl,de
        pop bc
        djnz .attrrow
        ld hl,0
        ret
_fastsprite:
        ; Build a clean 8-byte-stride working window for the union of
        ; the current and prior 32x32 sprites, then compare changed bytes.
        ld hl,newbuf
        ld (hl),0
        ld de,newbuf+1
        ld bc,511
        ldir
        ; Each source frame is 32x32, 4 bytes/row (128 bytes).
        ld a,(_ball_phase)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,(_fbase)
        add hl,de
        ld (fsource),hl
        ld a,(_ball_x)
        and 7
        ld (fbits),a
        ; Source window starts at the leftmost of old/new bounding boxes.
        ld a,(_clip_dx)
        ld e,a
        ld d,0
        ld a,(_clip_dy)
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,de
        ld de,newbuf
        add hl,de
        ld (frowdest),hl
        ld a,32
        ld (fcount),a
.sourcerow:
        ld hl,(fsource)
        ld de,fbuf
        ld bc,4
        ldir
        ld (fsource),hl
        xor a
        ld (de),a
        ld a,(fbits)
        or a
        jr z,.unshifted
        ld b,a
.shifts:
        ld hl,fbuf
        ld c,5
        or a
.shiftbyte:
        rr (hl)
        inc hl
        dec c
        jr nz,.shiftbyte
        djnz .shifts
.unshifted:
        ld hl,fbuf
        ld de,(frowdest)
        ld bc,5
        ldir
        ld hl,(frowdest)
        ld de,8
        add hl,de
        ld (frowdest),hl
        ld a,(fcount)
        dec a
        ld (fcount),a
        jr nz,.sourcerow
        ; Compare directly with the visible screen.  Keep HL as the
        ; destination, DE as the new image; no second memory buffer and
        ; no separate clearing pass.  A changed byte is written once.
        ld hl,newbuf
        ld (newp),hl
        ld a,(_clip_height)
        ld (rowleft),a
        ld a,(_clip_y)
        add a,32
        ld (rowindex),a
.screenrow:
        ld a,(rowindex)
        ld l,a
        ld h,0
        add hl,hl
        ld de,rowtable
        add hl,de
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        ld a,(_clip_x)
        add a,16
        ld e,a
        ld d,0
        add hl,de
        ld de,(newp)
        ld a,(_clip_width)
        ld b,a
.screenbyte:
        ld a,(de)
        cp (hl)
        jr z,.same
        ld (hl),a
.same:
        inc hl
        inc de
        djnz .screenbyte
        ld hl,(newp)
        ld de,8
        add hl,de
        ld (newp),hl
        ld a,(rowindex)
        inc a
        ld (rowindex),a
        ld a,(rowleft)
        dec a
        ld (rowleft),a
        jr nz,.screenrow
        ld hl,0
        ret
        section data
rowtable:
        dw 04000h,04100h,04200h,04300h,04400h,04500h,04600h,04700h
        dw 04020h,04120h,04220h,04320h,04420h,04520h,04620h,04720h
        dw 04040h,04140h,04240h,04340h,04440h,04540h,04640h,04740h
        dw 04060h,04160h,04260h,04360h,04460h,04560h,04660h,04760h
        dw 04080h,04180h,04280h,04380h,04480h,04580h,04680h,04780h
        dw 040A0h,041A0h,042A0h,043A0h,044A0h,045A0h,046A0h,047A0h
        dw 040C0h,041C0h,042C0h,043C0h,044C0h,045C0h,046C0h,047C0h
        dw 040E0h,041E0h,042E0h,043E0h,044E0h,045E0h,046E0h,047E0h
        dw 04800h,04900h,04A00h,04B00h,04C00h,04D00h,04E00h,04F00h
        dw 04820h,04920h,04A20h,04B20h,04C20h,04D20h,04E20h,04F20h
        dw 04840h,04940h,04A40h,04B40h,04C40h,04D40h,04E40h,04F40h
        dw 04860h,04960h,04A60h,04B60h,04C60h,04D60h,04E60h,04F60h
        dw 04880h,04980h,04A80h,04B80h,04C80h,04D80h,04E80h,04F80h
        dw 048A0h,049A0h,04AA0h,04BA0h,04CA0h,04DA0h,04EA0h,04FA0h
        dw 048C0h,049C0h,04AC0h,04BC0h,04CC0h,04DC0h,04EC0h,04FC0h
        dw 048E0h,049E0h,04AE0h,04BE0h,04CE0h,04DE0h,04EE0h,04FE0h
        dw 05000h,05100h,05200h,05300h,05400h,05500h,05600h,05700h
        dw 05020h,05120h,05220h,05320h,05420h,05520h,05620h,05720h
        dw 05040h,05140h,05240h,05340h,05440h,05540h,05640h,05740h
        dw 05060h,05160h,05260h,05360h,05460h,05560h,05660h,05760h
        dw 05080h,05180h,05280h,05380h,05480h,05580h,05680h,05780h
        dw 050A0h,051A0h,052A0h,053A0h,054A0h,055A0h,056A0h,057A0h
        dw 050C0h,051C0h,052C0h,053C0h,054C0h,055C0h,056C0h,057C0h
        dw 050E0h,051E0h,052E0h,053E0h,054E0h,055E0h,056E0h,057E0h
        section bss
fsource: ds 2
frowdest: ds 2
fcount: ds 1
fbits: ds 1
fbuf: ds 5
newp: ds 2
rowindex: ds 1
rowleft: ds 1
newbuf: ds 512
fillval: ds 1
fillattr: ds 1
bgrow: ds 1
