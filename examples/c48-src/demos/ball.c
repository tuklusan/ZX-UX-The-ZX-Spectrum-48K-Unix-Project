/* SPECTRUM BALL - ZX-UX C48 full-arena-bounce companion edition.
 * Reference: original 1986 Spectrum BASIC program and exact emulator frames.
 * Vertical stripe background removed; sampled checkerboard sphere retained.
 * The 8 original 128x127 bitmap frames are reduced 4:1 by nearest-neighbor
 * pixel sampling, with no hand-drawn replacement.  All graphics writes stay
 * within pixel columns 128..255, screen rows 32..159, except that ZX-UX's
 * C runtime can clear the whole screen when this is the first screen owner.
 * This program does not call cls(), border(), print(), or terminal reads.
 * Background work shares the screen with other cooperative C48 programs.
 * 6 slows, 7 speeds, SPACE exits (hardware matrix reads, no queue stealing).
 */
#include <c48.h>
int ballkeys(void);
unsigned char *screenbytes(void);
/* Original 60-step vertical profile, scaled into the full 96px travel. */
unsigned char bounce[60]={96,90,84,78,72,67,61,56,52,47,43,38,35,30,27,24,21,18,15,12,11,9,6,5,5,3,2,2,0,0,0,0,0,2,2,3,5,5,6,9,11,12,15,18,21,24,27,30,35,38,43,47,52,56,61,67,72,78,84,90};
unsigned char frames[1024]={
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,63,252,0,
 0,185,255,0,1,97,223,192,3,13,207,192,7,30,55,240,6,30,57,240,22,62,29,120,
 3,204,28,252,35,195,252,252,39,131,227,252,71,131,227,188,27,131,195,188,24,127,195,188,
 24,120,59,188,24,120,60,124,120,248,60,188,39,248,60,252,7,134,120,248,23,135,141,240,
 19,143,142,240,5,143,13,240,6,119,27,192,1,112,223,192,1,243,175,0,0,31,188,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,31,188,0,0,41,255,0,1,113,159,192,3,31,201,224,6,60,61,240,
 6,60,57,240,2,124,57,248,7,140,60,252,7,135,252,188,39,135,195,252,79,7,195,188,
 49,7,195,188,48,255,131,188,16,240,123,188,16,240,120,124,48,240,120,252,7,240,120,188,
 7,15,248,252,7,15,12,248,23,15,14,240,5,143,28,240,6,118,59,192,1,115,207,192,
 0,243,47,0,0,31,252,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,31,188,0,0,49,255,0,1,227,155,192,
 2,63,137,224,6,52,124,240,12,120,121,240,6,120,121,252,3,12,120,188,7,15,152,252,
 15,15,135,124,15,15,135,60,49,143,135,60,49,247,135,30,49,224,127,60,49,224,248,252,
 49,224,240,252,6,224,241,188,14,31,241,252,23,30,21,248,7,30,24,240,5,158,60,240,
 6,226,49,224,1,99,139,192,0,231,63,0,0,31,252,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,188,0,
 0,51,191,0,1,227,159,192,2,63,155,240,6,120,125,240,4,112,241,120,7,240,241,252,
 7,12,241,188,14,15,24,252,14,31,15,124,30,31,15,30,35,159,15,30,35,231,15,62,
 19,225,127,62,19,225,240,254,19,225,241,252,12,193,225,188,6,63,225,188,6,60,31,252,
 6,60,60,120,5,188,56,240,2,226,115,224,1,103,159,192,0,103,39,128,0,31,188,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,15,252,0,0,51,55,128,1,199,31,192,0,127,27,240,4,240,237,240,
 0,240,227,120,7,224,241,188,6,29,241,188,14,30,25,188,12,62,14,126,28,62,14,62,
 3,190,30,62,3,194,30,63,3,195,238,62,3,195,225,254,19,195,225,222,12,195,225,188,
 12,125,195,188,6,60,63,252,6,56,120,248,5,184,121,240,2,199,243,240,1,103,31,192,
 0,102,103,128,0,31,158,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,15,222,0,0,51,55,128,1,199,55,192,
 0,114,58,240,0,225,237,240,1,225,227,124,7,193,227,60,6,63,227,188,12,60,25,158,
 28,60,30,62,28,124,30,63,7,244,30,63,7,131,62,63,7,135,206,63,7,135,195,223,
 23,135,195,158,12,71,195,158,12,121,131,188,4,120,127,60,4,120,120,252,5,248,241,120,
 0,199,227,240,1,207,63,192,0,110,103,192,0,15,252,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,222,0,
 0,103,63,192,0,142,53,224,0,98,59,240,0,227,205,248,0,195,199,124,5,67,195,124,
 12,127,195,158,12,120,59,190,24,120,60,127,24,248,60,127,7,248,60,127,7,7,60,111,
 7,15,204,127,7,15,131,159,23,15,135,159,24,207,135,190,8,241,134,60,4,240,243,60,
 4,112,241,252,1,240,99,120,0,143,226,240,0,78,61,224,0,124,111,192,0,15,255,0,
 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,15,223,0,0,38,127,192,0,142,117,224,0,227,51,240,1,195,205,248,
 1,199,135,124,1,135,135,60,4,127,135,30,8,248,127,191,24,240,124,127,16,240,120,111,
 7,240,120,111,7,15,120,111,7,15,4,111,6,15,7,159,30,15,7,31,9,255,15,63,
 0,225,143,30,4,225,242,60,4,225,225,188,1,225,227,124,0,143,198,240,0,78,55,224,
 0,124,171,192,0,7,254,0,0,0,0,0,0,0,0,0
};
unsigned char ball_x,ball_y,ball_phase;
/* The union of the old and new sprite footprints, in panel-local pixels. */
unsigned char clip_x,clip_y,clip_dx,clip_dy,clip_width,clip_height;
void fastsprite(void);
unsigned char *scr,*fbase;
int xphase,forward,phase,period,prior_keys,prevx,prevy;
unsigned int last_tick;
/* ZX display file bytes: bitplane rows are interleaved. */
unsigned int screen_offset(int y)
{
  return (unsigned int)(((y&192)<<5)|((y&7)<<8)|((y&56)<<2));
}
void panel_bg(void);
void panel_clear(void);
void poll_controls(void)
{
  int keys,press;
  keys=ballkeys();
  press=keys & (~prior_keys);
  prior_keys=keys;
  if(press&1){if(period<12)period++;}
  if(press&2){if(period>1)period--;}
  if(press&4)xphase=-1;
}
int main(void)
{
  int xpos,ypos;
  scr=screenbytes();
  fbase=frames;
  panel_bg();
  xphase=0;forward=1;phase=0;period=2;
  prevx=-1;prevy=-1;
  prior_keys=ballkeys();
  last_tick=ticks();
  while(xphase>=0){
    poll_controls();
    if(xphase<0)break;
    if((unsigned int)(ticks()-last_tick)<(unsigned int)period){yield();continue;}
    last_tick=ticks();
    xpos=xphase;
    ypos=(int)bounce[phase];
    /* Draw only the union of the previous and current sprite, using an
       8-byte-wide RAM window. This avoids full-arena clearing/flicker. */
    {
      int xlo,xhi,ylo,yhi;
      xlo=xpos; xhi=xpos; ylo=ypos; yhi=ypos;
      if(prevx>=0){
        if(prevx<xlo)xlo=prevx;
        if(prevx>xhi)xhi=prevx;
        if(prevy<ylo)ylo=prevy;
        if(prevy>yhi)yhi=prevy;
      }
      clip_x=xlo>>3;
      clip_y=ylo;
      clip_dx=(xpos>>3)-(int)clip_x;
      clip_dy=ypos-ylo;
      clip_width=((xhi+31)>>3)-(int)clip_x+1;
      clip_height=yhi-ylo+32;
    }
    ball_x=xpos;ball_y=ypos;ball_phase=xphase&7;
    fastsprite();
    prevx=xpos;prevy=ypos;
    phase++;
    if(phase==60)phase=0;
    if(forward)xphase++;else xphase--;
    if(xphase==96)forward=0;
    if(xphase==0)forward=1;
    yield();
  }
  panel_clear();
  return 0;
}
