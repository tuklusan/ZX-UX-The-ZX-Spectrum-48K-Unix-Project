/* 3D Painter (CDS Microsystems, 1983): ZX-UX C48 keyboard reconstruction.
 * Gameplay reference: original CDS TZX and executed original-Z80 audit.
 * Q up, Z down, I left, P right. X opens the score screen.
 * Distinct deliberate changes: no Kempston; bounded enemy fallback;
 * ZX-UX terminal/UDG rendering and time-based scheduling.
 * Full original printer and electrical sound/timing are not reproduced.
 */
#include <c48.h>
int kbdpoll(void);
int kbdmatrix(void);
void flush_keys(void);
void intro_screen(void);
unsigned char glyphs[768]={
 0, 0, 0, 0, 0, 0, 0, 0, 24, 60, 24, 126, 90, 24, 36, 36,
 0, 0, 0, 0, 60, 0, 0, 0, 255, 255, 255, 255, 255, 255, 255, 255,
 255, 254, 252, 248, 240, 224, 192, 128, 254, 253, 251, 247, 239, 223, 191, 127,
 1, 3, 7, 15, 31, 63, 127, 255, 124, 68, 0, 0, 0, 0, 0, 0,
 255, 255, 195, 195, 195, 195, 255, 255, 16, 16, 16, 16, 16, 0, 16, 0,
 0, 0, 20, 8, 62, 8, 20, 0, 0, 0, 8, 8, 62, 8, 8, 0,
 0, 0, 0, 0, 0, 8, 8, 16, 0, 0, 0, 0, 62, 0, 0, 0,
 0, 0, 0, 0, 0, 24, 24, 0, 0, 0, 2, 4, 8, 16, 32, 0,
 124, 68, 68, 68, 68, 68, 124, 0, 16, 16, 16, 16, 16, 16, 16, 0,
 124, 4, 4, 124, 64, 64, 124, 0, 124, 4, 4, 124, 4, 4, 124, 0,
 68, 68, 68, 124, 4, 4, 4, 0, 124, 64, 64, 124, 4, 4, 124, 0,
 124, 64, 64, 124, 68, 68, 124, 0, 124, 4, 4, 4, 4, 4, 4, 0,
 124, 68, 68, 124, 68, 68, 124, 0, 124, 68, 68, 124, 4, 4, 124, 0,
 0, 0, 0, 16, 0, 0, 16, 0, 0, 0, 16, 0, 0, 16, 16, 32,
 0, 0, 4, 8, 16, 8, 4, 0, 0, 0, 0, 62, 0, 62, 0, 0,
 0, 0, 16, 8, 4, 8, 16, 0, 0, 60, 66, 4, 8, 0, 8, 0,
 255, 255, 255, 255, 255, 255, 255, 255, 124, 68, 68, 124, 68, 68, 68, 0,
 120, 68, 68, 124, 68, 68, 120, 0, 124, 64, 64, 64, 64, 64, 124, 0,
 120, 68, 68, 68, 68, 68, 120, 0, 124, 64, 64, 120, 64, 64, 124, 0,
 124, 64, 64, 120, 64, 64, 64, 0, 124, 64, 64, 76, 68, 68, 124, 0,
 68, 68, 68, 124, 68, 68, 68, 0, 124, 16, 16, 16, 16, 16, 124, 0,
 4, 4, 4, 4, 4, 68, 124, 0, 68, 72, 80, 96, 80, 72, 68, 0,
 64, 64, 64, 64, 64, 64, 124, 0, 68, 108, 84, 68, 68, 68, 68, 0,
 68, 68, 100, 84, 76, 68, 68, 0, 124, 68, 68, 68, 68, 68, 124, 0,
 124, 68, 68, 124, 64, 64, 64, 0, 124, 68, 68, 68, 84, 76, 124, 0,
 124, 68, 68, 124, 80, 72, 68, 0, 124, 64, 64, 124, 4, 4, 124, 0,
 124, 16, 16, 16, 16, 16, 16, 0, 68, 68, 68, 68, 68, 68, 124, 0,
 68, 68, 68, 68, 68, 40, 16, 0, 68, 68, 68, 68, 84, 108, 68, 0,
 68, 68, 40, 16, 40, 68, 68, 0, 68, 68, 40, 16, 16, 16, 16, 0,
 124, 4, 8, 16, 32, 64, 124, 0, 0, 0, 0, 0, 24, 24, 0, 0,
 0, 0, 64, 32, 16, 8, 4, 0, 0, 112, 16, 16, 16, 16, 112, 0,
 0, 16, 56, 84, 16, 16, 16, 0, 0, 0, 0, 0, 0, 0, 0, 255,
 0, 28, 34, 120, 32, 32, 126, 0, 24, 36, 24, 189, 126, 189, 24, 126,
 24, 36, 24, 126, 189, 24, 36, 36, 60, 36, 24, 255, 189, 189, 36, 102,
 0, 4, 4, 60, 68, 68, 60, 0, 0, 0, 56, 68, 120, 64, 60, 0,
 0, 12, 16, 24, 16, 16, 16, 0, 0, 0, 60, 68, 68, 60, 4, 56,
 0, 64, 64, 120, 68, 68, 68, 0, 0, 16, 0, 48, 16, 16, 56, 0,
 0, 4, 0, 4, 4, 4, 36, 24, 0, 32, 40, 48, 48, 40, 36, 0,
 0, 16, 16, 16, 16, 16, 12, 0, 0, 0, 104, 84, 84, 84, 84, 0,
 0, 0, 120, 68, 68, 68, 68, 0, 0, 0, 56, 68, 68, 68, 56, 0,
 0, 0, 120, 68, 68, 120, 64, 64, 0, 0, 60, 68, 68, 60, 4, 6,
 0, 0, 28, 32, 32, 32, 32, 0, 0, 0, 56, 64, 56, 4, 120, 0,
 0, 16, 56, 16, 16, 16, 12, 0, 0, 0, 68, 68, 68, 68, 56, 0,
 0, 0, 68, 68, 40, 40, 16, 0, 0, 0, 68, 84, 84, 84, 40, 0,
 0, 0, 68, 40, 16, 40, 68, 0, 0, 0, 68, 68, 68, 60, 4, 56,
 0, 0, 124, 8, 16, 32, 124, 0, 0, 14, 8, 48, 8, 8, 14, 0,
 0, 8, 8, 8, 8, 8, 8, 0, 0, 112, 16, 12, 16, 16, 112, 0,
 189, 20, 40, 0, 0, 0, 0, 0, 60, 66, 189, 141, 141, 189, 66, 60,
};
char *map_lines[88]={
"    &@@@@@@@@%       &@@@@@@@@% ",
"   &@@@@@@@@%@      &@@@@@@@@%@ ",
"   #########@@      #########@@ ",
"   #@@     #@@      #@@     #@@ ",
"   #@%@@@@@#@@      #@%@@@@@#@@ ",
"   #%@@@@@@#@@      #%@@@@@@#@$ ",
"   #########@@      #########$  ",
"      #@@  #@%@@@@@@#@@  #@@    ",
"      #@@  #%@@@@@@@#@@  #@@    ",
"      #@@  ##########@@  #@@    ",
"      #@@  #@@      #@@  #@@    ",
"      #@@  #@@      #@@  #@@    ",
"      #@@  #@%@@@@@@#@@  #@@    ",
"      #@@  #%@@@@@@@#@@  #@@    ",
"      #@@  ##########@@  #@@    ",
"    &@#@%@@#@@      #@%@@#@%@@% ",
"   &@@#%@@@#@@      #%@@@#%@@%@ ",
"   #########@@      #########@@ ",
"   #@@     #@@      #@@     #@@ ",
"   #@%@@@@@#@@      #@%@@@@@#@@ ",
"   #%@@@@@@#@$      #%@@@@@@#@$ ",
"   #########$       #########$  ",
"      &@@@@@@%      &@@@@@@%    ",
"     &@@@@@@%@     &@@@@@@%@    ",
"     #######@%@%  &#######@@    ",
"     #@@ &@#%@%@ &@#%@%@ #@@    ",
"  &@@#@@ #####@%@#####@@ #@%@@@%",
" &@@@#@@ #@@ #%@@#@@ #@@ #%@@@%@",
" #####@@ #@%@#####@%@#@@ #####@@",
" #@@ #@@ #%@@#@$ #%@@#@$ #@@ #@@",
" #@@ #@%@#####$  #####%@@#@@ #@@",
" #@@ #%@@@@#@$     #%@@@@#@$ #@@",
" #@@ #######%%     #######%% #@@",
" #@@ &@@@@@@%@     &@@@@@@%@ #@@",
" #@@ #######@%@%  &#######@@ #@@",
" #@@ #@@ &@#%@%@ &@#%@%@ #@@ #@@",
" #@%@#@@ #####@%@#####@@ #@%@#@@",
" #%@@#@@ #@@ #%@@#@@ #@@ #%@@#@$",
" #####@@ #@%@#####@%@#@@ #####$ ",
"     #@@ #%@@#@$ #%@@#@$ #@@    ",
"     #@%@#####$  #####%@@#@@    ",
"     #%@@@@#@$     #%@@@@#@$    ",
"     #######$      #######$     ",
"                                ",
"     &@@@@@@@%        &@@@@@@@% ",
"    &@@@@@@@%@       &@@@@@@@%@ ",
"    ########@%@@@@@@@########@@ ",
"    #@@    #%@@@@@@@@#@@    #@@ ",
"    #@@    ###########@@    #@@ ",
"    #@%@@@@#@@  #@@  #@%@@@@#@@ ",
"    #%@@@@@#@$ &#@%@%#%@@@@@#@$ ",
"    ########$ &@#%@%@########$  ",
"        #@%@@@#####@%@@@#@@     ",
"        #%@@@@#@@ #%@@@@#@@     ",
"        #######@%@#######@@     ",
"     &@@#@%@@%#%@@#@$ &@#@%@@@% ",
"    &@@@#%@@%@#####$ &@@#%@@@%@ ",
"    ########@@  #@@  ########@@ ",
"    #@@    #@%@@#@%@@#@@    #@@ ",
"    #@@    #%@@@#%@@@#@@    #@@ ",
"    #@@    ###########@@    #@@ ",
"    #@%@@@@#@@       #@%@@@@#@@ ",
"    #%@@@@@#@$       #%@@@@@#@$ ",
"    ########$        ########$  ",
"                                ",
"                                ",
"  &@@@@@@@@%                    ",
" &@@@@@@@@%@  &@@@@@@@@@@@@@%   ",
" #########@@ &@@@@@@@@@@@@@%@   ",
" #@@     #@@ ##############@@   ",
" #@%@@@@@#@@ #@%@@@@% &@@@#@@   ",
" #%@@@@@@#@$ #%@@@@%@&@@@@#@$   ",
" #########$  ######@@######$    ",
" #@@  &@@@%&%&@@@%#@@#@%@@%&@@@%",
" #@@ &@@@%%%%@@@%@#@@#%@@%%@@@%$",
" #@@ ####@#@####@@#@@####$####$ ",
" #@@ #@%#@#@#@@#@@#@@#@%@%#@@   ",
" #@@ #%@#@#@#@@#@@#@@#%@%$#@@   ",
" #@@ ####@#@#@@#@@#@@###$ #@@   ",
" #@@ #@@#@#@#@@#@@#@@#@%@@#@@   ",
" #@@ #@$#%#%#@@#@$#@@#%@@@#@@   ",
" #@%@#%@#####@@#$ #@@######@%@@%",
" #%@@@@@#%@@#@$   #@@  &@@#%@@%@",
" ############%@@@@#@%@@#######@@",
"        #%@@@@@@@@#%@@@#@@   #@@",
"        ################@%@@@#@@",
"                       #%@@@@#@$",
"                       #######$ ",
};


/* Original coordinates are (row,column), not (column,row). */
unsigned char startrow[4]={15,17,17,20}, startcol[4]={15,15,16,15};
unsigned char erow[4]={10,7,5,6}, ecol[4]={15,15,16,1};
unsigned char playerpaper[4]={3,4,3,6};
/* Mirror original screen attributes: 1=wall, 3=painted, 5=new. */
unsigned char world[768];
unsigned int seed;
unsigned int tlast;
unsigned int clock_left;
int level, roundno, py, px, ey, ex, done, direction;
int turnh, turnv;
int first_enemy, stages_cleared, raw_seen, lives;
char cfg[6], original_cfg[6];
/* ASCII decimal digits retain original six-place modulo-1000000 score. */
char score_digits[7]="000000";
char high_digits[7]="000000";
char table_digits[35];
char leaders[30];

int ix(int row,int col) { return row*32+col; }
void type_char(int row,int col,int ch,int slot,int inkcolor,int papercolor)
{
  int index;
  if(ch<32 || ch>127)ch=32;
  index=(ch-32)*8;
  udg_define(slot,glyphs+index);
  bright(0);paper(papercolor);ink(inkcolor);
  udg_draw(slot,row,col);
}
void font_text(int row,int col,char *str)
{
  while(*str && col<32) {
    type_char(row,col,*str,9,7,0);
    col++;str++;
  }
}
void draw_digits(int row,int col,char *str)
{
  int j;
  for(j=0;j<6;j++)type_char(row,col+j,str[j],9,7,0);
}
void center_text(int row,char *str)
{
  int len;
  len=0;
  while(str[len])len++;
  if(len>32)len=32;
  font_text(row,(32-len)/2,str);
}
void box_line(int row,int c1,int c2)
{
  int col;
  for(col=c1;col<=c2;col++)type_char(row,col,'-',9,6,0);
}
void intro_screen(void)
{
  int k;
  cls();paper(0);ink(7);
  center_text(1,"3D PAINTER");
  center_text(2,"ZX-UX C48 EDITION");
  box_line(3,4,27);
  font_text(5,2,"CONTROLS");
  font_text(7,3,"Q UP");
  font_text(8,3,"Z DOWN");
  font_text(9,3,"I LEFT");
  font_text(10,3,"P RIGHT");
  font_text(11,3,"X SCORES");
  font_text(5,18,"GAMEPLAY");
  font_text(7,15,"PAINT THE CYAN");
  font_text(8,15,"FLOOR TILES");
  font_text(10,15,"PAINTED TILES");
  font_text(11,15,"TURN BRIGHT BLUE");
  font_text(13,15,"YOU MAY WALK ON");
  font_text(14,15,"PAINTED TILES");
  font_text(16,15,"AVOID THE ENEMY");
  font_text(17,15,"AND CLEAR THE");
  font_text(18,15,"MAZE IN TIME");
  center_text(21,"PRESS ANY KEY TO START");
  flush_keys();
  for(;;){
    k=kbdmatrix();
    if(k)break;
    k=kbdpoll();
    if(k)break;
    yield();
  }
  flush_keys();
}
/* Change decimal ASCII digits without overflowing C48's 16-bit int. */
void score_add(unsigned int amount)
{
  int j;
  unsigned int carry;
  carry=amount;
  for(j=5;j>=0;j--) {
    carry=carry+(unsigned int)(score_digits[j]-'0');
    score_digits[j]='0'+carry%10u;
    carry=carry/10u;
  }
}
int score_cmp(char *a,char *b)
{
  int j;
  for(j=0;j<6;j++) {
    if(a[j]>b[j])return 1;
    if(a[j]<b[j])return -1;
  }
  return 0;
}
void copy_score(char *dest,char *src)
{
  int j;
  for(j=0;j<6;j++)dest[j]=src[j];
  dest[6]=0;
}
void clock_display(void)
{
  char b[4];
  unsigned int v;
  int j;
  v=clock_left;
  for(j=3;j>=0;j--){b[j]='0'+v%10u;v=v/10u;}
  type_char(0,13,'(',9,4,0);
  for(j=0;j<4;j++)type_char(0,14+j,b[j],9,6,0);
  type_char(0,18,'(',9,4,0);
}
void hud(void)
{
  font_text(0,0,"SCORE ");
  draw_digits(0,6,score_digits);
  font_text(0,21,"HIGH ");
  draw_digits(0,26,high_digits);
  clock_display();
}
void lives_display(void)
{
  font_text(23,1,"LIVES ");
  type_char(23,7,'0'+lives,9,6,0);
}
void show_floor(int row,int col)
{
  int tile, index;
  if(row<1 || row>22 || col<0 || col>31)return;
  tile=map_lines[level*22+row-1][col];
  if(tile=='#')index=1;
  else if(tile=='@')index=2;
  else if(tile=='%')index=3;
  else if(tile=='&')index=4;
  else if(tile=='$')index=5;
  else index=0;
  paper(0);
  if(world[ix(row,col)]==3){
    /* C48 ink() accepts 0..7 only. Bright blue is ink(1) + bright(1). */
    bright(1);ink(1);
  }else{
    bright(0);
    if(world[ix(row,col)]==5)ink(5);
    else ink(1);
  }
  udg_draw(index,row,col);
  bright(0); /* Keep later characters and screens at normal brightness. */
}
int isfloor(int row,int col)
{
  if(row<1 || row>22 || col<0 || col>31)return 0;
  /* A painted cell (3) IS walkable in the original game. */
  return world[ix(row,col)]==3 || world[ix(row,col)]==5;
}
void show_player(void){type_char(py,px,'!',7,0,playerpaper[level]);}
void show_enemy(void){type_char(ey,ex,'c',8,0,5);}
int randn(int m)
{
  unsigned int n;
  seed=((seed+1u)*75u-1u)&65535u;
  n=seed>>8;
  return (int)((n*(unsigned int)(m+1))>>8);
}
void init_level(void)
{
  int row,col,j;
  char *text;
  cls();paper(0);
  for(j=0;j<6;j++)udg_define(j,glyphs+(" #@%&$"[j]-32)*8);
  py=startrow[level];px=startcol[level];
  ey=erow[level];ex=ecol[level];
  for(row=1;row<=22;row++){
    text=map_lines[level*22+row-1];
    for(col=0;col<32;col++){
      if(text[col]=='#')world[ix(row,col)]=5;
      else world[ix(row,col)]=1;
      show_floor(row,col);
    }
  }
  clock_left=1300;
  hud();lives_display();show_player();show_enemy();
  tlast=ticks();
  direction=0;turnh=0;turnv=0;first_enemy=1;
}
void move_player(int dy,int dx)
{
  int ny,nx,was_new;
  ny=py+dy;nx=px+dx;
  if(!isfloor(ny,nx))return;
  was_new=(world[ix(ny,nx)]==5);
  world[ix(py,px)]=3;
  show_floor(py,px);
  py=ny;px=nx;
  if(was_new)score_add(5);
  show_player();hud();
  if(py==ey && px==ex)done=2;
}
int enemy_try(int d)
{
  int nr,nc;
  nr=ey;nc=ex;
  if(d==0)nr--;
  else if(d==1)nr++;
  else if(d==2)nc--;
  else nc++;
  if(!isfloor(nr,nc))return 0;
  if(d==0)turnv=1;
  if(d==1)turnv=0;
  if(d==2)turnh=1;
  if(d>=3)turnh=0; /* Original random result 4 also means right. */
  ey=nr;ex=nc;
  if(d<2)direction=1;else direction=0;
  return 1;
}
void move_enemy(void)
{
  int n,d,ok,j;
  show_floor(ey,ex);
  ok=0;
  /* Preserve original initial direction choices and PRNG consumption. */
  if(direction){
    n=randn(2);
    if(n!=0)ok=enemy_try(2);else ok=enemy_try(3);
    if(!ok){if(turnv)ok=enemy_try(0);else ok=enemy_try(1);}
  }else{
    n=randn(2);
    if(n==2)ok=enemy_try(1);else ok=enemy_try(0);
    if(!ok){if(turnh)ok=enemy_try(2);else ok=enemy_try(3);}
  }
  /* Original can retry forever for rare seeds. Limit it, then examine
     all four directions so an available move cannot be missed. */
  for(j=0;j<8 && !ok;j++){
    d=randn(4);
    ok=enemy_try(d);
  }
  for(j=0;j<4 && !ok;j++)ok=enemy_try(j);
  if(ey==py && ex==px)done=2;
  show_enemy();
}
int paths_left(void)
{
  int i;
  /* Original attribute scan: 0x5860..0x5ADE, inclusive (639 bytes). */
  for(i=96;i<=734;i++){
    if(i!=ix(py,px) && i!=ix(ey,ex) && world[i]==5)return 1;
  }
  return 0;
}
void stage_bonus(void)
{
  /* Original: remaining clock's decimal numeric value, not digit weights. */
  score_add(clock_left);
  if(score_cmp(score_digits,high_digits)>0)
    copy_score(high_digits,score_digits);
}
void rank_init(void)
{
  int i,j;
  for(i=0;i<5;i++){
    for(j=0;j<6;j++)table_digits[i*7+j]='0';
    table_digits[i*7+6]=0;
    for(j=0;j<5;j++)leaders[i*6+j]="-CDS-"[j];
    leaders[i*6+5]=0;
  }
}
int rank_insert(void)
{
  int i,j,r;
  r=5;
  for(i=0;i<5;i++){
    if(score_cmp(score_digits,table_digits+i*7)>0){r=i;break;}
  }
  if(r==5)return -1;
  for(i=4;i>r;i--){
    for(j=0;j<7;j++)table_digits[i*7+j]=table_digits[(i-1)*7+j];
    for(j=0;j<6;j++)leaders[i*6+j]=leaders[(i-1)*6+j];
  }
  copy_score(table_digits+r*7,score_digits);
  /* The original editor begins with '[' in every position. */
  for(j=0;j<5;j++)leaders[r*6+j]='[';
  leaders[r*6+5]=0;
  if(score_cmp(score_digits,high_digits)>0)
    copy_score(high_digits,score_digits);
  return r;
}
void rank_screen(void)
{
  int i;
  cls();
  font_text(1,9,"3D-PAINTER");
  font_text(3,5,"TODAYS HIGH SCORES");
  for(i=0;i<5;i++){
    type_char(6+i*2,4,'1'+i,9,7,0);
    draw_digits(6+i*2,11,table_digits+i*7);
    font_text(6+i*2,22,leaders+i*6);
  }
  if(lives==0)center_text(18,"GAME OVER");
  font_text(21,1,"R RESTART            X EXIT");
}
/* On real 48K hardware, read the original keyboard matrix so
   held keys repeat and simultaneous directions reject. The queued
   key-event adapter remains the fallback for ZX-UX RVM. */
int game_key(void)
{
  int k;
  k=kbdmatrix();
  if(k==-1){raw_seen=1;return 0;}
  if(k){raw_seen=1;return k;}
  if(raw_seen)return 0;
  return kbdpoll();
}
void flush_keys(void)
{
  int n;
  for(n=0;n<32;n++)if(!kbdpoll())break;
}
/* Drain both the ZX-UX event queue and live Q/Z/I/P/X keys.
 * The visible period is time-based, not shortened by buffered input.
 */
void pause_and_drain(unsigned int duration)
{
  unsigned int start;
  start=ticks();
  while((unsigned int)(ticks()-start)<duration){
    flush_keys();
    yield();
  }
  flush_keys();
}
void waitfresh(void)
{
  unsigned int quiet;
  quiet=ticks();
  /* Require 15 ticks with no queued event or held gameplay key.
   * This also debounces the held X used to reach the score screen. */
  while((unsigned int)(ticks()-quiet)<15u){
    if(kbdpoll() || kbdmatrix())quiet=ticks();
    yield();
  }
  flush_keys();
}
void life_message(void)
{
  cls();
  center_text(8,"LIFE LOST");
  center_text(11,"THE ENEMY CAUGHT YOU");
  font_text(13,9,"LIVES LEFT ");
  type_char(13,20,'0'+lives,9,6,0);
  center_text(19,"GET READY");
  pause_and_drain(90u);
  waitfresh();
}
void gameovermsg(void)
{
  cls();
  center_text(8,"GAME OVER");
  center_text(11,"FINAL SCORE");
  draw_digits(13,13,score_digits);
  center_text(19,"HIGH SCORES NEXT");
  pause_and_drain(180u);
  waitfresh();
}
void enter_name(int rank)
{
  int i,k,c,base;
  base=rank*6;i=0;
  flush_keys();
  rank_screen();
  font_text(18,1,"HIGH SCORE: Q/Z LETTER");
  font_text(19,1,"I/P MOVE  P ON END = DONE");
  font_text(6+rank*2,22,leaders+base);
  type_char(6+rank*2,22,leaders[base],9,0,6);
  while(i<5){
    k=kbdpoll();
    if(k=='q' || k=='Q'){
      c=leaders[base+i];
      if(c<'A'||c>'Z')c='A';else if(c=='Z')c='A';else c++;
      leaders[base+i]=c;
    }else if(k=='z'||k=='Z'){
      c=leaders[base+i];
      if(c<'A'||c>'Z')c='Z';else if(c=='A')c='Z';else c--;
      leaders[base+i]=c;
    }else if(k=='i'||k=='I'){
      if(i>0)i--;
    }else if(k=='p'||k=='P')i++;
    else if(k=='x'||k=='X')i=5; /* ZX-UX escape convenience. */
    if(k && i<5){
      font_text(6+rank*2,22,leaders+base);
      type_char(6+rank*2,22+i,leaders[base+i],9,0,6);
    }
    yield();
  }
  rank_screen();
  pause_and_drain(45u);
  waitfresh();
}
int main(void)
{
  int key,i,rank;
  unsigned int now,delay;
  level=0;roundno=0;stages_cleared=0;raw_seen=0;done=0;lives=3;
  for(i=0;i<6;i++){score_digits[i]='0';high_digits[i]='0';}
  score_digits[6]=0;high_digits[6]=0;
  rank_init();seed=ticks();
  gtty(0,original_cfg);
  for(i=0;i<6;i++)cfg[i]=original_cfg[i];
  cfg[4]=32;stty(0,cfg);
  intro_screen();
  for(;;){
    init_level();
    while(done==0){
      now=ticks();
      /* The original takes one input sample, one clock step, and
         (after the first sample of a stage) one opponent turn per
         gameplay update. Never let input outrun the opponent. */
      delay=4;
      if(stages_cleared>=1)delay=3;
      if(stages_cleared>=2)delay=2;
      if(stages_cleared>=3)delay=1;
      if((unsigned int)(now-tlast)>=delay){
        tlast=now;
        key=game_key();
        if(key=='q'||key=='Q')move_player(-1,0);
        else if(key=='z'||key=='Z')move_player(1,0);
        else if(key=='i'||key=='I')move_player(0,-1);
        else if(key=='p'||key=='P')move_player(0,1);
        else if(key=='x'||key=='X')done=3;
        if(done)break;
        if(first_enemy)first_enemy=0;
        else move_enemy();
        if(done)break;
        if(clock_left>0)clock_left--;
        clock_display();
        if(!paths_left()){
          stage_bonus();
          /* ZX-UX addition: one extra life on every cleared level.
           * Keep the one-digit lives display valid (maximum nine). */
          if(lives<9)lives++;
          level++;stages_cleared++;
          if(level==4){level=0;roundno++;}
          /* Original Z80 consumes one random step during stage setup. */
          randn(2);
          init_level();
        }
      }
      yield();
    }
    if(done==2){
      lives--;
      if(lives>0){
        life_message();
        done=0;
        continue; /* Retry this level without erasing the score. */
      }
      gameovermsg();
    }else if(done==3){
      /* X goes straight to the scores, not to the shell. */
      pause_and_drain(45u);
      waitfresh();
    }
    if(done==2 || done==3){
      rank=rank_insert();
      rank_screen();
      if(rank>=0)enter_name(rank);
      else{
        pause_and_drain(50u);
        waitfresh();
      }
      for(;;){
        key=kbdpoll();
        if(key=='r'||key=='R'||key==' '){
          for(i=0;i<6;i++)score_digits[i]='0';
          level=0;roundno=0;stages_cleared=0;done=0;lives=3;
          break;
        }
        if(key=='x'||key=='X'||key==27)break;
        yield();
      }
      if(done==0)continue;
    }
    break;
  }
  stty(0,original_cfg);
  return 0;
}
