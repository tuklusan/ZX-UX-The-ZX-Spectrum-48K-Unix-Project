# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BITMAP_SIZE=6144
ATTR_SIZE=768
SCREEN_SIZE=6912
WIDTH=256
HEIGHT=192

# Standard Spectrum palette; BRIGHT black remains black.
PALETTE_NORMAL=((0,0,0),(0,0,205),(205,0,0),(205,0,205),(0,205,0),(0,205,205),(205,205,0),(205,205,205))
PALETTE_BRIGHT=((0,0,0),(0,0,255),(255,0,0),(255,0,255),(0,255,0),(0,255,255),(255,255,0),(255,255,255))

class ScreenError(ValueError): pass


def bitmap_offset(x:int,y:int)->int:
    if not (0<=x<256 and 0<=y<192): raise ScreenError("pixel coordinate out of range")
    # Native Spectrum display-memory interleave; y=0 is top physical scanline.
    return ((y & 0xC0)<<5)|((y & 0x07)<<8)|((y & 0x38)<<2)|(x>>3)

def attr_offset(x:int,y:int)->int:
    if not (0<=x<256 and 0<=y<192): raise ScreenError("pixel coordinate out of range")
    return BITMAP_SIZE+(y>>3)*32+(x>>3)

@dataclass
class Font4x8:
    rows: tuple[tuple[int,...],...]
    @classmethod
    def load(cls,path:Path)->"Font4x8":
        d=path.read_bytes()
        if len(d)!=392 or d[:4]!=b"F4X8" or d[4:8]!=bytes((1,0x20,96,0)):
            raise ScreenError("invalid F4X8 resource")
        glyphs=[]
        p=8
        for _ in range(96):
            r=[]
            for _ in range(4):
                b=d[p];p+=1;r.extend(((b>>4)&15,b&15))
            glyphs.append(tuple(r))
        return cls(tuple(glyphs))
    def glyph(self,code:int)->tuple[int,...]:
        if not 0x20<=code<=0x7F: code=ord('?')
        return self.rows[code-0x20]

class ZXScreen:
    def __init__(self,font:Font4x8):
        self.font=font
        self.mem=bytearray(SCREEN_SIZE)
        self.ink_color=7;self.paper_color=0;self.bright_flag=0;self.flash_flag=0
        self.inverse_flag=0;self.over_flag=0;self.border_color=0
        self.row=0;self.col=0
        self.udg=[bytearray(8) for _ in range(32)]
        self.cls()
    def attr(self)->int:
        return (self.ink_color&7)|((self.paper_color&7)<<3)|((self.bright_flag&1)<<6)|((self.flash_flag&1)<<7)
    def ink(self,c:int)->int:
        if not 0<=c<=7:return 1
        self.ink_color=c;return 0
    def paper(self,c:int)->int:
        if not 0<=c<=7:return 1
        self.paper_color=c;return 0
    def bright(self,on:int)->int:
        if on not in (0,1): return 1
        self.bright_flag=on;return 0
    def flash(self,on:int)->int:
        if on not in (0,1): return 1
        self.flash_flag=on;return 0
    def inverse(self,on:int)->int:
        if on not in (0,1): return 1
        self.inverse_flag=on;return 0
    def over(self,on:int)->int:
        if on not in (0,1): return 1
        self.over_flag=on;return 0
    def border(self,c:int)->int:
        if not 0<=c<=7:return 1
        self.border_color=c;return 0
    def cls(self)->int:
        self.mem[:BITMAP_SIZE]=b'\0'*BITMAP_SIZE
        self.mem[BITMAP_SIZE:]=bytes([self.attr()])*ATTR_SIZE
        self.row=self.col=0;return 0
    @staticmethod
    def _graphics_physical_y(y:int)->int:
        # Spectrum PLOT coordinates use a bottom-left origin; bitmap storage is top-down.
        return (HEIGHT-1)-y
    def _apply_bit(self,x:int,y:int,on:bool)->None:
        py=self._graphics_physical_y(y)
        off=bitmap_offset(x,py);mask=0x80>>(x&7)
        if on:
            # Exact PLOT-class OVER/INVERSE truth table from the 48K ROM:
            # O0/I0=set, O0/I1=clear, O1/I0=toggle, O1/I1=unchanged.
            if self.over_flag:
                if not self.inverse_flag:self.mem[off]^=mask
            elif self.inverse_flag:
                self.mem[off]&=(~mask)&0xFF
            else:
                self.mem[off]|=mask
        self.mem[attr_offset(x,py)]=self.attr()
    def plot(self,x:int,y:int)->int:
        if not (0<=x<WIDTH and 0<=y<HEIGHT):return 1
        self._apply_bit(x,y,True);return 0
    def point(self,x:int,y:int)->int:
        if not (0<=x<WIDTH and 0<=y<HEIGHT):return 1
        py=self._graphics_physical_y(y)
        return 1 if self.mem[bitmap_offset(x,py)]&(0x80>>(x&7)) else 0
    def draw(self,x1:int,y1:int,x2:int,y2:int)->int:
        if not all((0<=x1<256,0<=x2<256,0<=y1<192,0<=y2<192)):return 1
        dx=abs(x2-x1);sx=1 if x1<x2 else -1;dy=-abs(y2-y1);sy=1 if y1<y2 else -1;err=dx+dy
        while True:
            self._apply_bit(x1,y1,True)
            if x1==x2 and y1==y2:break
            e2=2*err
            if e2>=dy:err+=dy;x1+=sx
            if e2<=dx:err+=dx;y1+=sy
        return 0
    def circle(self,cx:int,cy:int,r:int)->int:
        if not (0<=cx<256 and 0<=cy<192 and 0<=r<=255):return 1
        if r==0:return self.plot(cx,cy)
        x=r;y=0;err=1-r
        while x>=y:
            for px,py in ((cx+x,cy+y),(cx+y,cy+x),(cx-y,cy+x),(cx-x,cy+y),(cx-x,cy-y),(cx-y,cy-x),(cx+y,cy-x),(cx+x,cy-y)):
                if 0<=px<256 and 0<=py<192:self._apply_bit(px,py,True)
            y+=1
            if err<0:err+=2*y+1
            else:x-=1;err+=2*(y-x+1)
        return 0
    def print_at(self,row:int,col:int,data:bytes)->int:
        if not (0<=row<24 and 0<=col<64):return 1
        oldr,oldc=self.row,self.col;self.row,self.col=row,col
        for b in data:
            self.putchar(b)
        self.row,self.col=oldr,oldc;return 0
    def _glyph(self,row:int,col:int,rows:tuple[int,...])->None:
        if not (0<=row<24 and 0<=col<64):return
        x0=col*4;y0=row*8
        for ry,bits in enumerate(rows):
            off=bitmap_offset(x0,y0+ry);high=(col&1)==0
            old=self.mem[off]
            nib=(bits&15)<<(4 if high else 0);mask=0xF0 if high else 0x0F
            if self.inverse_flag:nib^=mask
            if self.over_flag:self.mem[off]=old^nib
            else:self.mem[off]=(old&(~mask&0xFF))|nib
        self.mem[BITMAP_SIZE+row*32+(col>>1)]=self.attr()
    def putchar(self,code:int)->int:
        code&=0xFF
        if code==10:
            self.col=0;self.row+=1
        elif code==13:self.col=0
        elif code==8:
            if self.col>0:self.col-=1
        elif 0x20<=code<=0x7F:
            self._glyph(self.row,self.col,self.font.glyph(code));self.col+=1
            if self.col>=64:self.col=0;self.row+=1
        if self.row>=24:self.scroll();self.row=23
        return code
    def puts(self,data:bytes)->int:
        for b in data:self.putchar(b)
        self.putchar(10);return 0
    def scroll(self)->None:
        # Move physical raster up eight scanlines using mapped offsets.
        rows=[[self.mem[bitmap_offset(x*8,y)] for x in range(32)] for y in range(192)]
        for y in range(184):
            for xb,b in enumerate(rows[y+8]):self.mem[bitmap_offset(xb*8,y)]=b
        for y in range(184,192):
            for xb in range(32):self.mem[bitmap_offset(xb*8,y)]=0
        self.mem[BITMAP_SIZE:BITMAP_SIZE+23*32]=self.mem[BITMAP_SIZE+32:BITMAP_SIZE+24*32]
        self.mem[BITMAP_SIZE+23*32:]=bytes([self.attr()])*32
    def udg_define(self,slot:int,data:bytes)->int:
        if not 0<=slot<32 or len(data)!=8:return 1
        self.udg[slot][:]=data;return 0
    def udg_get(self,slot:int)->bytes:
        if not 0<=slot<32:raise ScreenError("UDG slot out of range")
        return bytes(self.udg[slot])
    def udg_clear(self,slot:int)->int:
        if not 0<=slot<32:return 1
        self.udg[slot][:]=b'\0'*8;return 0
    def udg_draw(self,slot:int,row:int,col:int)->int:
        if not (0<=slot<32 and 0<=row<24 and 0<=col<32):return 1
        x0=col*8;y0=row*8
        for ry,b in enumerate(self.udg[slot]):
            off=bitmap_offset(x0,y0+ry)
            pattern=((~b)&0xFF) if self.inverse_flag else b
            self.mem[off]=(self.mem[off]^pattern) if self.over_flag else pattern
        self.mem[BITMAP_SIZE+row*32+col]=self.attr();return 0
    def udg_draw_2x2(self,base:int,row:int,col:int)->int:
        if not (0<=base<=28 and 0<=row<=22 and 0<=col<=30):return 1
        for ds,dr,dc in ((0,0,0),(1,0,1),(2,1,0),(3,1,1)):
            rc=self.udg_draw(base+ds,row+dr,col+dc)
            if rc:return rc
        return 0
    def bytes(self)->bytes:return bytes(self.mem)
    def render_rgb(self,flash_phase:bool=False)->bytes:
        out=bytearray(WIDTH*HEIGHT*3);p=0
        for y in range(HEIGHT):
            for x in range(WIDTH):
                a=self.mem[attr_offset(x,y)];ink=a&7;paper=(a>>3)&7;br=(a>>6)&1;fl=(a>>7)&1
                if fl and flash_phase:ink,paper=paper,ink
                bit=bool(self.mem[bitmap_offset(x,y)]&(0x80>>(x&7)))
                c=(PALETTE_BRIGHT if br else PALETTE_NORMAL)[ink if bit else paper]
                out[p:p+3]=bytes(c);p+=3
        return bytes(out)
    def save_ppm(self,path:Path,flash_phase:bool=False)->None:
        path.write_bytes(f"P6\n256 192\n255\n".encode("ascii")+self.render_rgb(flash_phase))
