/*
 * Spectrum Invaders (Over the Spectrum, 1982), C48 translation for ZX-UX.
 * Original source: Sinclair BASIC embedded in the supplied 16K TZX.
 * C48 port preserves the 1982 screen layout, bitmap symbols, two-frame
 * animation, formations, scoring, lives, direction, and original keys.
 * ZX-UX requires the included _invkey assembler SDK service for nonblocking
 * Z/C/M keyboard scanning. It is not a stock C48 SDK entry point.
 * This source is independent of and does not execute the BASIC interpreter.
 */
#include <c48.h>
extern int invkey(void);

/* 21 8-byte glyphs, parsed from BASIC DATA lines 100-150. */
unsigned char shapes[168] = {
    0, 31, 63, 63, 123, 113, 225, 225, 0, 248, 252, 252, 222, 142, 135, 135,
    255, 127, 111, 111, 199, 192, 240, 240, 255, 254, 246, 246, 227, 3, 15, 15,
    7, 63, 127, 65, 193, 199, 255, 124, 224, 252, 254, 131, 131, 227, 254, 62,
    124, 127, 51, 48, 112, 88, 136, 248, 254, 204, 124, 26, 17, 31, 0, 0,
    31, 63, 63, 115, 113, 225, 225, 255, 248, 252, 252, 206, 142, 135, 135, 255,
    127, 111, 103, 103, 96, 48, 60, 60, 254, 246, 230, 230, 6, 12, 60, 60,
    7, 63, 127, 193, 193, 199, 127, 124, 224, 252, 254, 130, 131, 227, 255, 62,
    127, 51, 113, 88, 136, 248, 0, 0, 62, 254, 204, 12, 14, 26, 17, 31,
    24, 24, 24, 24, 60, 126, 231, 231, 7, 31, 63, 60, 112, 112, 248, 248,
    224, 248, 252, 60, 14, 14, 31, 31, 18, 26, 14, 14, 7, 3, 1, 0,
    36, 44, 56, 56, 112, 96, 192, 128
};

unsigned char cells[768];
unsigned char inks[768];
char aliens_a[385];
char aliens_b[385];
char strips[132];
char bases[128];
char cspaces[34];
int alen;
int q, f, sc, lives;
int player, bullet_row, bullet_col;
int bomb_row, bomb_col;
int last_player;
int current_pos;
unsigned int seed;

/* Native font64 is used for every on-screen text message via print_at().
   Only the arcade playfield uses the original 8x8 bitmap game sprites.
   These are separate display paths, not a substitute font. */
extern void cell(int row, int col, int ch, int pen);
extern void show(int row, int col, char *s, int len, int pen);

void clear_game(void)
{
    int row, col;
    border(7);
    paper(7);
    ink(0);
    cls();
    for (row=0; row<22; row++)
        for (col=0; col<32; col++) {
            cells[row*32+col]=' ';
            inks[row*32+col]=56;
        }
}

/* Draw every word with the kernel-provided 64-column font via C48.
   Font64 is four pixels wide and eight high; the playfield stays 8x8. */
void score(void)
{
    char buffer[8];
    int d, n, pos;
    n=sc; pos=0;
    if (n==0) buffer[pos++]='0';
    else {
        char reverse[8];
        d=0;
        while(n>0 && d<7) {reverse[d++]=(char)('0'+n%10);n=n/10;}
        while(d>0) buffer[pos++]=reverse[--d];
    }
    buffer[pos]=0;
    print_at(0,13,"        ");
    print_at(0,13,buffer);
}

void life_text(void)
{
    char life[4];
    int i;
    for(i=0;i<3;i++) { if(i<lives) life[i]='^'; else life[i]=' '; }
    life[3]=0;
    print_at(0,54,life);
}

/* Dark 64-column title and controls, before the arcade starts.
   The historical label is transcribed from the supplied 1982 TZX. */
void intro(void)
{
    border(0);
    paper(0);
    ink(7);
    cls();
    ink(6);
    print_at(2,9,"==============================================");
    ink(7);
    print_at(4,24,"ZX-UX Invaders");
    ink(6);
    print_at(6,9,"==============================================");
    ink(7);
    print_at(9,8,"BASED ON SPECTRUM INVADERS (1982)");
    print_at(11,8,"ORIGINAL: SINCLAIR ZX SPECTRUM 16K BASIC");
    print_at(12,8,"TAPE LABEL: OVER THE SPECTRUM");
    print_at(13,8,"REBUILT AS A C48 GAME FOR ZX-UX");
    ink(5);
    print_at(16,19,"Z  LEFT     C  RIGHT");
    print_at(17,19,"M  FIRE");
    ink(6);
    print_at(20,20,"PRESS M TO START");
    while(invkey()!='m') sleep(1);
    while(invkey()=='m') sleep(1);
    ink(0);
}

/* BASIC 9000,9010: make paired alternating sprite strips. */
void sprite_strip(char *top, char *bottom, int s)
{
    int i,j;
    for (i=0; i<6; i++) {
        j=i*4;
        top[j]=s; top[j+1]=s+1; top[j+2]=' '; top[j+3]=' ';
        bottom[j]=s+2;bottom[j+1]=s+3;bottom[j+2]=' ';bottom[j+3]=' ';
    }
    for(i=24;i<32;i++) top[i]=' ';
    for(i=24;i<31;i++) bottom[i]=' ';
    top[32]=0;
    bottom[31]=0;
}

void init_fleet(void)
{
    int i, j, idx, val;
    for(i=0;i<4;i++) {
        sprite_strip(strips+i*33,bases+i*32,144+i*4);
        for(j=0;j<33;j++) cspaces[j]=' ';
        cspaces[33]=0;
    }
    /* K,L,K,L with 96-byte strips; M,N,M,N has the same structure. */
    for(i=0;i<384;i++) {
        idx=(i/96)&1;
        val=idx;
        j=i%96;
        if(j<32) aliens_a[i]=strips[val*33+j];
        else if(j<63) aliens_a[i]=bases[val*32+j-32];
        else aliens_a[i]=' ';
        if(j<32) aliens_b[i]=strips[(val+2)*33+j];
        else if(j<63) aliens_b[i]=bases[(val+2)*32+j-32];
        else aliens_b[i]=' ';
    }
    alen=343;
    aliens_a[alen]=0;
    aliens_b[alen]=0;
}

/* The ship and shield use original block/UDG character codes. */
void shields(void)
{
    char top[8],mid[8],low[8];
    int i,k, row,col;
    int t[5]={132,139,131,135,136};
    int m[5]={137,137,131,134,134};
    int l[5]={135,130,32,129,139};
    for(i=0;i<8;i++) {
        if (i<5) {top[i]=t[i]; mid[i]=m[i]; low[i]=l[i];}
        else {top[i]=' ';mid[i]=' ';low[i]=' ';}
    }
    for(i=0;i<12;i++) {
        row=16+i/4;
        col=2+(i%4)*8;
        if(i<4) show(row,col,top,8,4);
        else if(i<8) show(row,col,mid,8,4);
        else show(row,col,low,8,4);
    }
}

unsigned int random16(void)
{
    seed=(seed * 25173u+13849u)&65535u;
    return seed;
}

int is_blank(int row,int col)
{
    if(row<0 || row>=22 || col<0 || col>=32) return 1;
    return cells[row*32+col]==' ';
}

int attr_at(int row,int col)
{
    if(row<0 || row>=22 || col<0 || col>=32) return 56;
    return inks[row*32+col];
}

void erase3(int n)
{
    int j;
    if(n<1) n=1;
    for(j=n-1;j<n+2;j++)
        if(j>=0 && j<alen) {aliens_a[j]=' '; aliens_b[j]=' ';}
}

void player_draw(void)
{
    int col;
    col=player;
    if (last_player>=0) {
        cell(20,last_player+1,' ',0);
        cell(21,last_player,' ',0);
        cell(21,last_player+1,' ',0);
        cell(21,last_player+2,' ',0);
    }
    cell(20,col,' ',0);
    cell(20,col+1,160,0);
    cell(20,col+2,' ',0);
    cell(21,col,161,0);
    cell(21,col+1,131,0);
    cell(21,col+2,162,0);
    last_player=col;
}

void explode(int r, int c)
{
    cell(r,c,145,6);cell(r,c+1,144,6);
    cell(r+1,c,162,6);cell(r+1,c+1,161,6);
    beep(0.05,10);
    cell(r,c,' ',0);cell(r,c+1,' ',0);
    cell(r+1,c,' ',0);cell(r+1,c+1,' ',0);
}

/* BASIC 6005 onward: shield collisions versus loss of ship. */
void bomb_hit(void)
{
    int k;
    if(bomb_row!=20) {
        cell(bomb_row-1,bomb_col,' ',0);
        cell(bomb_row-1,bomb_col+1,' ',0);
        cell(bomb_row,bomb_col,144,2);
        cell(bomb_row,bomb_col+1,145,2);
        beep(0.05,-10);
        cell(bomb_row,bomb_col,' ',0);
        cell(bomb_row,bomb_col+1,' ',0);
        if(bomb_row==bullet_row && (bullet_col==bomb_col || bullet_col==bomb_col+1)) {
            cell(bullet_row,bullet_col,' ',0);
            bullet_row=0;
        }
    } else {
        cell(19,bomb_col,' ',0);cell(19,bomb_col+1,' ',0);
        cell(20,bomb_col,144,2);cell(20,bomb_col+1,145,2);
        beep(0.05,10);
        cell(20,bomb_col,' ',0);cell(20,bomb_col+1,' ',0);
        for(k=0;k<10;k++) {
            /* BASIC PRINT OVER 1 XORs the ship on alternate beeps. */
            if((k&1)==0) {
                cell(21,player,' ',0);cell(21,player+1,' ',0);
                cell(21,player+2,' ',0);
            } else {
                cell(21,player,161,0);cell(21,player+1,131,0);
                cell(21,player+2,162,0);
            }
            beep(0.1,0);
        }
        lives--;
        life_text();
        if(lives>0 && bomb_row<=20) explode(bomb_row,bomb_col);
    }
    if (bomb_row==20) bullet_row=0;
    bomb_row=21;
}

/* BASIC 5000, 5010-5220: collision destroys three corresponding strips. */
void bullet_hit(void)
{
    int h, count, pen;
    pen=attr_at(bullet_row,bullet_col);
    if(pen==58) { bomb_hit(); return; }
    if(pen!=60) {
        h=bullet_col-current_pos+32*(bullet_row-q-1);
        if(h>=0) erase3(h);
        h=h+32;
        if(h<alen) erase3(h);
        h=h+32;
        if(h<alen) erase3(h);
        count=4-h/96;
        if(h<0 && h%96!=0) count++;
        sc=sc+100*count;
        score();
        beep(0.05,8);
    }
    explode(bullet_row,bullet_col);
    bullet_row=0;
}

void missile_step(void)
{
    if(bullet_row>=q) {
        /* The outgoing shot starts on the ship's own turret.  It must not
           collide with that glyph or erase the ship as it climbs away. */
        if(!(bullet_row==20 && bullet_col==player+1) &&
           !is_blank(bullet_row,bullet_col)) bullet_hit();
        if(bullet_row>=q) {
            cell(bullet_row,bullet_col,160,0);
            if(!(bullet_col==player+1 &&
                 (bullet_row==20 || bullet_row==19)))
                cell(bullet_row+1,bullet_col,' ',0);
        }
    }
    bullet_row--;
}

void controls(void)
{
    int key;
    key=invkey();
    if(key=='c' && player<28) player++;
    if(key=='z' && player>0) player--;
    if(key=='m' && bullet_row<=q-1) {
        bullet_row=20;
        bullet_col=player+1;
    }
}

void alien_step(int p,int anim)
{
    int i;
    current_pos=p;
    for(i=0;i<p;i++) cell(q,i,' ',0);
    if (anim) show(q,p,aliens_b,alen,0);
    else show(q,p,aliens_a,alen,0);
    player_draw();
    missile_step();
    controls();
}

void next_bomb(int p,int dir)
{
    int w, idx;
    if(bomb_row<=20) return;
    w=(int)(random16()%6u);
    idx=alen-4*w-3;
    if(idx<0 || idx>=alen) return;
    if(aliens_a[idx]!=146 && aliens_a[idx]!=150) return;
    bomb_row=q+1+alen/32;
    bomb_col=p-4*w+20+dir;
    if(bomb_col==31) bomb_col=30;
}

int end_check(void)
{
    int i,blank;
    if(alen<=55) {
        blank=1;
        for(i=22;i<alen;i++) if(aliens_a[i]!=' ') blank=0;
        if(blank) return 1;
    }
    if(alen>=96) {
        blank=1;
        for(i=alen-33;i<alen;i++) if(aliens_a[i]!=' ') blank=0;
        if(blank) {
            alen=alen-96;
            aliens_a[alen]=0;
            aliens_b[alen]=0;
        }
    }
    if(32*q+alen>609) return -1;
    return 0;
}

int battle(void)
{
    int t, r, s, p, done, dir;
    q=f;
    f++;
    if(f==11) return 2;
    init_fleet();
    shields();
    player=0;last_player=-1;
    show(20,30,cspaces,33,0);
    bullet_row=0;bullet_col=0;
    bomb_row=21;bomb_col=12;
    lives=3;life_text();
    t=1; r=0; s=10;
    for(;;) {
        p=r;
        for (;;) {
            if(t==1) beep(0.005,1);
            alien_step(p,0);
            if(lives==0) return -1;
            if(bomb_row<=20) {
                if(!is_blank(bomb_row,bomb_col) || !is_blank(bomb_row,bomb_col+1))
                    bomb_hit();
                if(bomb_row<=20) {
                    cell(bomb_row-1,bomb_col,' ',0);
                    cell(bomb_row-1,bomb_col+1,' ',0);
                    cell(bomb_row,bomb_col,163,2);
                    cell(bomb_row,bomb_col+1,164,2);
                }
            }
            sleep(1);
            if(lives==0) return -1;
            alien_step(p,1);
            if(lives==0) return -1;
            if(bomb_row>20) next_bomb(p,t);
            if(bomb_row==20) {cell(20,bomb_col,' ',0);cell(20,bomb_col+1,' ',0);}
            bomb_row++;
            if(lives==0) return -1;
            sleep(1);
            if(p==s) break;
            p=p+t;
        }
        if(t==1) {t=-1;r=9;s=0;continue;}
        done=end_check();
        if(done==1) return 1;
        if(done<0) return -1;
        r=0;s=10;t=1;
        show(q,0,cspaces,33,0);
        q++;
    }
}

int gameover(void)
{
    int c;
    border(0);
    paper(0);
    ink(7);
    cls();
    ink(6);
    print_at(5,22,"ZX-UX INVADERS");
    ink(7);
    print_at(9,14,"THE ALIENS HAVE OVERRUN YOU.");
    print_at(11,24,"ALL IS LOST.");
    ink(5);
    print_at(15,23,"PLAY AGAIN? (Y/N)");
    ink(7);
    for (;;) {
        c=invkey();
        if(c=='y') return 1;
        if(c=='n') return 0;
        sleep(1);
    }
}

int main(void)
{
    int result;
    seed=ticks();
    intro();
    if (shapes[0] != 0) seed++; /* anchor glyph data for native blitter */
    for (;;) {
        clear_game();
        print_at(0,2,"SCORE");
        print_at(0,45,"LIVES");
        f=2;sc=0;
        for(;;) {
            result=battle();
            if(result==2) return 0;
            if(result<0) break;
        }
        if(!gameover()) return 0;
    }
}
