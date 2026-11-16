/* Orc Attack (1984): playable C48 game reconstruction.
 * The Z80 tape stays untouched; there is no loading picture or Z80 payload.
 * The game rules are rebuilt here. Exact original timing and later foes remain.
 */
#include <c48.h>
#include "orcattack-original-sprites.h"
extern void orc_tile(int x, int y, unsigned char *shape, int attr);

#define ENEMIES 15
#define ENEMY_CYCLE 20
#define POSE_FRAMES 10
#define OIL_READY_TICKS 700
#define ORC_WALK 1
#define ORC_BUILD 2
#define ORC_CLIMB 3
#define ORC_ROOF 4
#define STAGE_ORCS 0
#define STAGE_SORCERER 1
#define STAGE_ORCS_HARD 2
#define STAGE_TROLLS 3
#define STAGE_WARTS 4
#define WALL_TOP 8
#define LADDER_LIP 7
#define FIRST_LANE 15
#define MID_LANE 20
#define LAST_LANE 24
#define WALL_END 20
#define GROUND 21
#define LADDER_FOOT 23
#define PLAYER_ROW 5

/* Eight scan lines for each tile: empty, parapet, wall, ground, guard,
 * orc, ladder, rock, arrow, sword, oil, fire, raider, skull. */
unsigned char art[224] = {
    0,0,0,0,0,0,0,0,
    255,129,129,255,255,165,165,255,
    255,129,189,165,165,189,129,255,
    0,0,102,255,153,255,102,0,
    15,60,80,80,80,80,80,80,
    60,126,219,255,126,126,90,165,
    255,0,0,0,255,0,0,0,
    24,60,126,255,255,126,60,24,
    8,28,62,127,62,28,8,0,
    16,56,56,254,16,16,16,56,
    24,60,60,126,126,255,126,60,
    24,60,126,255,255,189,102,0,
    60,126,255,195,255,126,102,195,
    60,126,219,219,255,102,60,102,
    /* Original 1984 Spectrum screen: guard helmet and legs, column 16. */
    3,7,15,19,16,28,28,28,
    112,80,112,32,63,55,20,20,
    /* Original orc idle frame, column 5, three screen rows. */
    60,126,255,255,60,66,60,60,
    126,231,219,219,231,255,255,126,
    126,102,102,102,102,102,231,231,
    /* Original orc walking frame, column 26, three screen rows. */
    60,126,14,247,216,14,28,28,
    54,51,51,115,243,243,255,62,
    30,60,60,60,60,60,124,252,
    /* Later opponents use independent shapes, not a fake orc head. */
    24,60,126,90,126,36,90,129,
    60,126,255,219,255,126,36,66,
    126,255,219,255,126,60,126,231,
    /* Same little menace, now facing right. */
    60,126,112,239,27,112,56,56,
    108,204,204,206,207,207,207,124,
    120,56,56,56,56,56,62,63
};
/* The tape keeps the lowest rung visible between an orc's boots. */
unsigned char climb_foot[8] = {255,102,102,102,255,102,102,231};
int players, current, game_over;
int px, carries, rock_x, rock_y;
int arrow_x, arrow_y, arrow_active;
int ex[ENEMIES], ey[ENEMIES], alive[ENEMIES], etype[ENEMIES];
int ladder[ENEMIES], ladder_top[ENEMIES], ladder_x[ENEMIES];
int gait[ENEMIES], walk_phase[ENEMIES];
int orc_mode[ENEMIES], heading[ENEMIES], ai_wait[ENEMIES];
int spawn_wait[ENEMIES], target_lane[ENEMIES], lane_hold[ENEMIES];
int kills, score, wounds, lives, round_no, frame;
int parapet_hp[32];
int roof_danger(void);
void terrain(int x,int y);
void restore(int x,int y);
int last_direction, repeat_wait, last_fire, seed, oil_fall, ai_slot;
int oil_x, flame_radius, flame_finished, wave_age;
int battle_stage;
int spell_x, spell_y, spell_active, spells_sent, spells_resolved;
int spell_wait, caster_x;
int major_x, major_y, major_hp, major_count, major_wait;
unsigned int wave_clock;
int oil_announced;


/* Eight-pixel tiles map onto the Spectrum's interleaved bitmap. */
void tile(int x, int y, int shape, int attr)
{
    if(x<0 || x>31 || y<0 || y>23) return;
    orc_tile(x,y,art+shape*8,attr);
}

/* The original guard is two characters wide and three characters high. */
void raw_tile(int x,int y,unsigned char *image,int attr)
{
    if(x<0 || x>31 || y<0 || y>23) return;
    orc_tile(x,y,image,attr);
}

void hud_digit(int x,int y,int value,int attr)
{
    if(value<0 || value>9) return;
    raw_tile(x,y,sprite_digits+value*8,attr);
}

/* Sprite shapes and palette bytes come from the unmodified tape. */
void draw_guard(void)
{
    tile(px,PLAYER_ROW-1,14,0x29);
    raw_tile(px+1,PLAYER_ROW-1,sprite_guard_r,0x29);
    tile(px,PLAYER_ROW,4,0x28);
    raw_tile(px+1,PLAYER_ROW,sprite_guard_r+8,0x28);
    tile(px,PLAYER_ROW+1,15,0x29);
    /* The original brick hides the guard's lower right side. */
    if(px+1<32 && parapet_hp[px+1]<=0)
        raw_tile(px+1,PLAYER_ROW+1,sprite_guard_br,0x29);
}

void clear_guard(void)
{
    terrain(px,PLAYER_ROW-1);
    terrain(px,PLAYER_ROW);
    terrain(px,PLAYER_ROW+1);
    terrain(px+1,PLAYER_ROW-1);
    terrain(px+1,PLAYER_ROW);
    terrain(px+1,PLAYER_ROW+1);
}

/* Ground animation and facing come from the four original Z80 sprite pairs.
 * The one-column climbing pose remains the original C14B/C163 bitmap. */
int enemy_columns(int i)
{
    if(orc_mode[i]==ORC_ROOF) return 2;
    if(orc_mode[i]==ORC_BUILD || orc_mode[i]==ORC_CLIMB) return 1;
    if(gait[i]<0) return 2;
    return 1;
}

void draw_enemy(int i)
{
    int base, top_attr, middle_attr, bottom_attr;
    unsigned char *left,*right;
    if(!alive[i]) return;
    /* Moving sprites keep cyan paper when they enter the open sky. */
    top_attr=0x1E; middle_attr=0x1F; bottom_attr=0x18;
    if(ey[i]<6) top_attr=0x28;
    if(ey[i]+1<6) middle_attr=0x28;
    if(ey[i]+2<6) bottom_attr=0x28;
    if(enemy_columns(i)==2) {
        if(heading[i]>=0) {
            if(gait[i]==-2) { left=sprite_walk_l; right=sprite_walk_r; }
            else { left=walk_e0_l; right=walk_e0_r; }
        } else {
            if(gait[i]!=-2) { left=walk_w1_l; right=walk_w1_r; }
            else { left=walk_w0_l; right=walk_w0_r; }
        }
        raw_tile(ex[i],ey[i],left,top_attr);
        raw_tile(ex[i]+1,ey[i],right,top_attr);
        raw_tile(ex[i],ey[i]+1,left+8,middle_attr);
        raw_tile(ex[i]+1,ey[i]+1,right+8,middle_attr);
        raw_tile(ex[i],ey[i]+2,left+16,bottom_attr);
        raw_tile(ex[i]+1,ey[i]+2,right+16,bottom_attr);
        return;
    }
    base=16;
    if(orc_mode[i]==ORC_WALK) {
        base=19;
        if(heading[i]>0) base=25;
    }
    tile(ex[i],ey[i],base,top_attr);
    tile(ex[i],ey[i]+1,base+1,middle_attr);
    tile(ex[i],ey[i]+2,base+2,bottom_attr);
    if(ey[i]==GROUND &&
       (orc_mode[i]==ORC_CLIMB || orc_mode[i]==ORC_BUILD)) {
        int j;
        for(j=0;j<ENEMIES;j++) {
            if(ladder[j] && ladder_x[j]==ex[i]) {
                raw_tile(ex[i],ey[i]+2,climb_foot,bottom_attr);
                break;
            }
        }
    }
}

void clear_enemy(int i)
{
    int j,k,right,jright;
    right=ex[i]+enemy_columns(i)-1;
    for(k=0;k<3;k++) {
        restore(ex[i],ey[i]+k);
        if(enemy_columns(i)==2) restore(ex[i]+1,ey[i]+k);
    }
    /* The original two-column walkers also overlap at the right edge. */
    for(j=0;j<ENEMIES;j++) {
        jright=ex[j]+enemy_columns(j)-1;
        if(j!=i && alive[j] && ex[j]<=right && jright>=ex[i] &&
           ey[j]<=ey[i]+2 && ey[j]+2>=ey[i]) draw_enemy(j);
    }
}

void terrain(int x, int y)
{
    if(x<0 || x>31 || y<0 || y>23) return;
    /* Original screen 0180: 0x29 blue/cyan sky in row four. */
    if(y<6) {
        /* Sky tiles carry the neutral sky code; the blitter applies
         * original row-four attribute 0x29 to its empty pixels. */
        tile(x,y,0,0x28);
    } else if(y==6) {
        /* Exact two-cell magenta crenellations and cyan gaps. */
        if(x<3 || x>28) tile(x,y,0,0x28);
        else if(parapet_hp[x]>0) raw_tile(x,y,sprite_brick,0x2B);
        else tile(x,y,0,0x18);
    } else if(y<20) tile(x,y,0,0x18);
    else tile(x,y,0,0);
}

void ladder_rung(int center,int y)
{
    /* The ladder ends under the roof; no rung may repaint the sky. */
    if(y<LADDER_LIP || y>LADDER_FOOT) return;
    raw_tile(center-1,y,sprite_ladder,0x18);
    tile(center,y,6,0x18);
    raw_tile(center+1,y,sprite_ladder+16,0x18);
}

void draw_ladder(int i)
{
    int y;
    if(!ladder[i]) return;
    for(y=ladder_top[i];y<=LADDER_FOOT;y++) ladder_rung(ladder_x[i],y);
}

/* Restore the original three-column ladder below moving sprites. */
void restore(int x,int y)
{
    int j,part;
    terrain(x,y);
    for(j=0;j<ENEMIES;j++) {
        if(ladder[j] && y>=LADDER_LIP &&
           y>=ladder_top[j] && y<=LADDER_FOOT) {
            part=x-ladder_x[j]+1;
            if(part>=0 && part<3) {
                if(part==1) tile(x,y,6,0x18);
                else raw_tile(x,y,sprite_ladder+part*8,0x18);
                break;
            }
        }
    }
}

void clear_lane(int x)
{
    int y,j,k;
    for(y=6;y<=23;y++)
        for(k=-1;k<=1;k++) restore(x+k,y);
    for(j=0;j<ENEMIES;j++)
        if(alive[j] && ex[j]+enemy_columns(j)-1>=x-2 && ex[j]<=x+2) draw_enemy(j);
}

void digits(int row,int col,int val)
{
    char num[7],rev[7];
    int p, q;
    p=0;
    if (val==0) rev[p++]='0';
    while (val>0 && p<6) {
        rev[p++]=(char)('0'+val%10);
        val=val/10;
    }
    q=0;
    while (p>0) num[q++]=rev[--p];
    num[q]=0;
    print_at(row,col,num);
}

void hud(void)
{
    int n,k;
    /* Original Sinclair font, original red/white and black/white attributes. */
    hud_digit(8,0,current,0x3A);
    n=score;
    for(k=6;k>=1;k--) {
        hud_digit(k,1,n%10,0x38);
        n=n/10;
    }
    if(round_no>=10) hud_digit(17,1,(round_no/10)%10,0x38);
    else tile(17,1,0,0x38);
    hud_digit(18,1,round_no%10,0x38);
    if(lives>=10) hud_digit(29,1,(lives/10)%10,0x38);
    else tile(29,1,0,0x38);
    hud_digit(30,1,lives%10,0x38);
}

int next_random(void)
{
    seed=(seed*109+89)&32767;
    return seed;
}

void background(void)
{
    int x,y;
    cls();
    /* Paint all 24 screen rows. Zero attr is the floor tile's
     * magenta paper code in this game's private screen blitter. */
    for(y=2;y<24;y++)
        for(x=0;x<32;x++) terrain(x,y);
    for(x=0;x<32;x++)
        raw_tile(x,0,sprite_hud+x*8,0x3A);
    for(x=0;x<32;x++) tile(x,1,0,0x38);
    hud();
}

void show_items(void)
{
    int item;
    item=7;
    if(roof_danger()) item=9;
    if(px!=1) {
        if(item==7) raw_tile(1,3,sprite_rock,0x28);
        else tile(1,3,item,0x28);
        tile(1,PLAYER_ROW,0,0x28);
    }
    item=10;
    if(roof_danger()) item=9;
    if(!roof_danger() && (battle_stage!=STAGE_ORCS &&
        battle_stage!=STAGE_ORCS_HARD || wave_age<OIL_READY_TICKS)) item=7;
    if(px!=30) {
        if(item==7) raw_tile(30,3,sprite_rock,0x28);
        else tile(30,3,item,0x28);
        tile(30,PLAYER_ROW,0,0x28);
    }
}

void spawn(int i)
{
    int candidate, j;
    /* The original tape shows arrivals entering at the two screen edges. */
    candidate=0;
    if(i==0 || (i&1)) candidate=30;
    if(i==4 && round_no==1 && battle_stage==STAGE_ORCS) candidate=31;
    for(j=0;j<ENEMIES;j++) {
        if(j!=i && alive[j] && ey[j]==GROUND &&
           ex[j]<=candidate+1 && ex[j]+enemy_columns(j)>candidate) {
            spawn_wait[i]=3;
            return;
        }
    }
    ex[i]=candidate;
    ey[i]=GROUND;
    etype[i]=0;gait[i]=-1;walk_phase[i]=0;
    if(round_no>2 && next_random()%4==0) etype[i]=1;
    alive[i]=1;
    ladder[i]=0;
    ladder_x[i]=ex[i];
    ladder_top[i]=GROUND;
    orc_mode[i]=ORC_WALK;
    heading[i]=1;
    if(candidate>=30) heading[i]=-1;
    ai_wait[i]=7+next_random()%15;
    /* The tape's first wave grows three shafts, not fifteen. */
    target_lane[i]=FIRST_LANE;
    if(i%3==1) target_lane[i]=MID_LANE;
    if(i%3==2) target_lane[i]=LAST_LANE;
    lane_hold[i]=0;
    if(round_no==1 && battle_stage==STAGE_ORCS) {
        if(i==0) lane_hold[i]=3;
        if(i==1) lane_hold[i]=1;
        if(i==2) lane_hold[i]=4;
    }
    spawn_wait[i]=0;
    draw_enemy(i);
}

void reset_wave(void)
{
    int i;
    px=16;carries=0;
    rock_y=-1;arrow_active=0;
    oil_fall=0;flame_radius=0;flame_finished=0;wave_age=0;kills=0;
    wave_clock=ticks();oil_announced=0;ai_slot=0;
    for(i=0;i<32;i++) {
        if(i>=3 && i<=28 && (i-3)%4>=2) parapet_hp[i]=2;
        else parapet_hp[i]=0;
    }
    background();
    /* Enemies enter one by one. The five-ladder parade is cancelled. */
    for(i=0;i<ENEMIES;i++) {
        alive[i]=0;
        ex[i]=0;
        ey[i]=GROUND;
        etype[i]=0;gait[i]=-1;walk_phase[i]=0;
        heading[i]=0;
        ai_wait[i]=0;
        ladder[i]=0;
        ladder_x[i]=0;
        ladder_top[i]=GROUND;
        orc_mode[i]=0;
        target_lane[i]=0;lane_hold[i]=0;
        if(battle_stage==STAGE_ORCS || battle_stage==STAGE_ORCS_HARD) {
            if(i<5) {
                spawn_wait[i]=2+i*4+next_random()%3;
                if(i==2 || i==3) spawn_wait[i]--;
            }
            else spawn_wait[i]=90+(i-5)*4;
            if(i==4 && round_no==1 && battle_stage==STAGE_ORCS) spawn_wait[i]=spawn_wait[i]-3;
        } else spawn_wait[i]=-1;
    }
    spell_x=0;spell_y=GROUND;spell_active=0;spells_sent=0;
    spells_resolved=0;spell_wait=10;caster_x=16;
    major_hp=0;major_count=0;major_wait=0;
    if(battle_stage==STAGE_SORCERER) {
        print_at(2,20,"SORCERER  SKULL SPELLS");
        tile(caster_x,GROUND,22,70);
    }
    if(battle_stage==STAGE_TROLLS) print_at(2,20,"GIANT TROLLS");
    if(battle_stage==STAGE_WARTS) print_at(2,20,"STONE WARTS");
    show_items();
    draw_guard();
    if(carries==1) tile(px,PLAYER_ROW-1,7,71);
    if(carries==2) tile(px,PLAYER_ROW-1,9,71);
    if(carries==3) tile(px,PLAYER_ROW-1,10,71);
}

int roof_danger(void)
{
    int i;
    for(i=0;i<ENEMIES;i++)
        if (alive[i] && ey[i]<=PLAYER_ROW) return 1;
    return 0;
}

void kill_orc(int i)
{
    if(!alive[i]) return;
    clear_enemy(i);
    alive[i]=0;
    spawn_wait[i]=-1;
    /* A fallen orc does not take its ladder to the grave. */
    score=score+10;
    kills++;
    show_items();
    hud();
}

void damage(void)
{
    /* The Spectrum version begins with nine lives; a hit loses one. */
    lives--;
    carries=0;
    if(lives<=0) game_over=1;
    else {
        if(players==2) current=3-current;
        reset_wave();
    }
    hud();
}

void end_round(void)
{
    int i;
    for(i=0;i<ENEMIES;i++)
        if(alive[i]) kill_orc(i);
    score=score+50;
    round_no++;
    battle_stage++;
    if(battle_stage>STAGE_WARTS) battle_stage=STAGE_ORCS;
    if(players==2) current=3-current;
    reset_wave();
}

void advance_special(void)
{
    score=score+50;
    round_no++;
    battle_stage++;
    if(battle_stage>STAGE_WARTS) battle_stage=STAGE_ORCS;
    if(players==2) current=3-current;
    reset_wave();
}

void spawn_major(void)
{
    major_x=3+next_random()%26;
    major_y=11+next_random()%5;
    if(battle_stage==STAGE_TROLLS) major_hp=3;
    else major_hp=1;
    major_wait=7;
    if(battle_stage==STAGE_TROLLS) tile(major_x,major_y,24,93);
    else tile(major_x,major_y,22,78);
}

void hit_major(void)
{
    score=score+30;
    major_hp--;
    if(major_hp<=0) {
        restore(major_x,major_y);
        major_count++;
        if((battle_stage==STAGE_TROLLS && major_count>=3) ||
           (battle_stage==STAGE_WARTS && major_count>=5)) advance_special();
        else spawn_major();
    }
    hud();
}

/* Spells and heavy attackers are their own waves after the oil attack. */
void move_special(void)
{
    int dx;
    if(battle_stage==STAGE_SORCERER) {
        if(!spell_active && spells_sent<7) {
            if(--spell_wait<=0) {
                spell_x=3+next_random()%26;
                spell_y=GROUND;
                spell_active=1;
                spells_sent++;
                spell_wait=25;
            }
        }
        if(spell_active) {
            if(spell_y<GROUND) restore(spell_x,spell_y);
            spell_y--;
            if(rock_y>=6 && rock_x==spell_x &&
               rock_y>=spell_y-1 && rock_y<=spell_y+1) {
                spell_active=0;spells_resolved++;
                restore(spell_x,spell_y);
                restore(rock_x,rock_y);
                rock_y=-1;
                score=score+20;
                hud();
            } else if(spell_y<=PLAYER_ROW) {
                spell_active=0;spells_resolved++;
                if(spell_x==px) damage();
                else {
                    if(parapet_hp[spell_x]>0) parapet_hp[spell_x]--;
                    terrain(spell_x,6);
                }
            } else tile(spell_x,spell_y,23,71);
        }
        if(spells_resolved>=7 && !spell_active) advance_special();
        return;
    }
    if(battle_stage==STAGE_TROLLS || battle_stage==STAGE_WARTS) {
        if(major_hp<=0) {
            if((battle_stage==STAGE_TROLLS && major_count>=3) ||
               (battle_stage==STAGE_WARTS && major_count>=5)) advance_special();
            else spawn_major();
            return;
        }
        if(--major_wait<=0) {
            restore(major_x,major_y);
            dx=1;
            if(major_x>px) dx=-1;
            if(next_random()%3==0) dx=-dx;
            major_x=major_x+dx;
            if(major_x<2) major_x=2;
            if(major_x>29) major_x=29;
            if(battle_stage==STAGE_TROLLS) tile(major_x,major_y,24,93);
            else tile(major_x,major_y,22,78);
            major_wait=4+next_random()%5;
            if(!arrow_active && next_random()%5==0) {
                arrow_x=major_x;arrow_y=major_y-1;arrow_active=1;
                tile(arrow_x,arrow_y,8,71);
            }
        }
    }
}

/* One update advances each orc independently, if it has arrived yet. */
void move_one_orc(int i)
{
    int j,candidate,blocked;
        if(battle_stage!=STAGE_ORCS && battle_stage!=STAGE_ORCS_HARD) return;
        if(!alive[i]) {
            if(spawn_wait[i]>0) {
                spawn_wait[i]--;
                if(spawn_wait[i]==0) spawn(i);
            }
            return;
        }
        if(orc_mode[i]==ORC_WALK) {
            clear_enemy(i);
            ai_wait[i]--;
            /* Walk to a shaft before starting the climb. */
            if(target_lane[i] && ex[i]!=target_lane[i] &&
               ai_wait[i]<=0) ai_wait[i]=1;
            if(target_lane[i] && ex[i]==target_lane[i]) {
                if(lane_hold[i]>0) {
                    lane_hold[i]--;
                    ai_wait[i]=1;
                    draw_enemy(i);
                    return;
                }
                ai_wait[i]=0;
            }
            if(ai_wait[i]<=0) {
                /* Pick a ladder site after wandering, not at birth. */
                blocked=0;candidate=-1;
                for(j=0;j<ENEMIES;j++) {
                    if(j!=i && ladder[j] &&
                       ex[i]>=ladder_x[j]-2 && ex[i]<=ladder_x[j]+2) {
                        blocked=1;
                        /* Follow a finished ladder. Orcs queue, not duplicate. */
                        if(ex[i]==ladder_x[j] &&
                           ladder_top[j]<=GROUND-3 && !etype[i])
                            candidate=j;
                    }
                }
                if(candidate>=0) {
                    orc_mode[i]=ORC_CLIMB;
                    gait[i]=-1;
                } else if(!blocked && ex[i]>=2 && ex[i]<=29) {
                    if(etype[i]) {
                        /* Later ninja orcs do not need ladders. */
                        orc_mode[i]=ORC_CLIMB;
                    } else {
                        ladder[i]=1;
                        ladder_x[i]=ex[i];
                        ladder_top[i]=GROUND-1;
                        if(round_no==1 && battle_stage==STAGE_ORCS)
                            ladder_top[i]=GROUND;
                        parapet_hp[ex[i]]=0;
                        orc_mode[i]=ORC_BUILD;
                        ai_wait[i]=2;
                        if(round_no==1 && battle_stage==STAGE_ORCS && i==0) ai_wait[i]=1;
                        draw_ladder(i);
                    }
                } else ai_wait[i]=3+next_random()%8;
            } else {
                /* A little indecision keeps the horde from marching in step. */
                if(target_lane[i]) {
                    if(ex[i]<target_lane[i]) heading[i]=1;
                    if(ex[i]>target_lane[i]) heading[i]=-1;
                } else if(next_random()%7==0) heading[i]=-heading[i];
                candidate=ex[i]+heading[i];
                if(candidate<0 || candidate>30) {
                    heading[i]=-heading[i];
                    candidate=ex[i]+heading[i];
                }
                blocked=0;
                /* Walkers cross on the way to their separate shafts. */
                if(!target_lane[i])
                    for(j=0;j<ENEMIES;j++)
                        if(j!=i && alive[j] && ey[j]==GROUND &&
                           ex[j]<=candidate+1 &&
                           ex[j]+enemy_columns(j)>candidate)
                            blocked=1;
                if(!blocked) {
                    ex[i]=candidate;
                    if(walk_phase[i]) gait[i]=-1;
                    else gait[i]=-2;
                    walk_phase[i]=1-walk_phase[i];
                } else heading[i]=-heading[i];
            }
        } else if(orc_mode[i]==ORC_BUILD) {
            if(--ai_wait[i]<=0) {
                if(ladder_top[i]>LADDER_LIP) {
                    ladder_top[i]--;
                    ladder_rung(ladder_x[i],ladder_top[i]);
                }
                ai_wait[i]=1+next_random()%2;
                if(round_no==1 && battle_stage==STAGE_ORCS && i<3) {
                    ai_wait[i]=2;
                    if(i==0) ai_wait[i]=1;
                }
                if(ladder_top[i]<=GROUND-3) orc_mode[i]=ORC_CLIMB;
            }
        } else if(orc_mode[i]==ORC_CLIMB) {
            clear_enemy(i);
            candidate=i;
            if(!ladder[i] && !etype[i]) {
                candidate=-1;
                for(j=0;j<ENEMIES;j++)
                    if(j!=i && ladder[j] && ladder_x[j]==ex[i]) {
                        candidate=j;
                        break;
                    }
                if(candidate<0) {
                    /* A missing ladder means a long walk back down. */
                    ey[i]=GROUND;
                    orc_mode[i]=ORC_WALK;
                    gait[i]=0;
                    ai_wait[i]=5;
                }
            }
            blocked=0;
            for(j=0;j<ENEMIES;j++)
                if(j!=i && alive[j] && ex[j]==ex[i] &&
                   ey[j]<ey[i] && ey[j]+3>=ey[i]) blocked=1;
            if(ladder[i] && ladder_top[i]>LADDER_LIP) {
                ladder_top[i]--;
                ladder_rung(ladder_x[i],ladder_top[i]);
            }
            if(!blocked && orc_mode[i]==ORC_CLIMB && ey[i]>PLAYER_ROW) {
                if(candidate==i) {
                    if(etype[i] || ey[i]>ladder_top[i] ||
                       ladder_top[i]==LADDER_LIP) ey[i]--;
                } else if(candidate>=0 &&
                          (ey[i]>ladder_top[candidate] ||
                           ladder_top[candidate]==LADDER_LIP)) ey[i]--;
            }
            if(ey[i]<=PLAYER_ROW) orc_mode[i]=ORC_ROOF;
        } else if(orc_mode[i]==ORC_ROOF) {
            clear_enemy(i);
            if(ex[i]<px) { ex[i]++;gait[i]=(gait[i]+1)&1; }
            else if(ex[i]>px) { ex[i]--;gait[i]=(gait[i]+1)&1; }
            if(ex[i]==px) {
                draw_enemy(i);
                damage();
                return;
            }
        }
        draw_enemy(i);
    
}

/* The tape spends ten frames wide, then ten frames skinny. */
void pause_walker(int i)
{
    if(!alive[i] || orc_mode[i]!=ORC_WALK || gait[i]>=0) return;
    clear_enemy(i);
    gait[i]=0;
    draw_enemy(i);
}

/* Eastward ground walkers change shape halfway through each step. */
void widen_walker(int i)
{
    if(!alive[i] || orc_mode[i]!=ORC_WALK || heading[i]<=0 || gait[i]<0) return;
    clear_enemy(i);
    gait[i]=-2;
    draw_enemy(i);
}

void stride_east(int i)
{
    if(!alive[i] || orc_mode[i]!=ORC_WALK || heading[i]<=0) return;
    move_one_orc(i);
    pause_walker(i);
}

/* The original eastward steps have four visible beats per twenty frames. */
void enemy_frame(void)
{
    int slot,pauser,actor;
    slot=ai_slot;
    if(slot<ENEMIES) {
        if(alive[slot] && orc_mode[slot]==ORC_WALK && heading[slot]>0)
            widen_walker(slot);
        else move_one_orc(slot);
    }
    actor=slot+15;
    if(actor>=ENEMY_CYCLE) actor=actor-ENEMY_CYCLE;
    if(actor<ENEMIES) stride_east(actor);
    pauser=slot+POSE_FRAMES;
    if(pauser>=ENEMY_CYCLE) pauser=pauser-ENEMY_CYCLE;
    if(pauser<ENEMIES) {
        if(alive[pauser] && orc_mode[pauser]==ORC_WALK && heading[pauser]>0)
            widen_walker(pauser);
        else pause_walker(pauser);
    }
    actor=slot+5;
    if(actor>=ENEMY_CYCLE) actor=actor-ENEMY_CYCLE;
    if(actor<ENEMIES) stride_east(actor);
    ai_slot++;
    if(ai_slot>=ENEMY_CYCLE) ai_slot=0;
}

/* Tests can still advance a complete enemy tick. Gameplay spreads the work. */
void move_orcs(void)
{
    int i;
    for(i=0;i<ENEMIES;i++) move_one_orc(i);
    show_items();
}

void move_shots(void)
{
    int i,hit;
    if(rock_y>=0) {
        /* The thrown rock starts above the battlement, not on the guard. */
        if(rock_y>=6) restore(rock_x,rock_y);
        rock_y++;
        hit=0;
        for(i=0;i<ENEMIES;i++) {
            if(alive[i] && rock_x>=ex[i] && rock_x<ex[i]+enemy_columns(i) && rock_y>=ey[i] &&
               rock_y<=ey[i]+2) {
                kill_orc(i);hit=1;break;
            }
        }
        if(!hit && battle_stage==STAGE_SORCERER &&
           spell_active && rock_x==spell_x &&
           rock_y>=spell_y-1 && rock_y<=spell_y+1) {
            restore(spell_x,spell_y);
            spell_active=0;spells_resolved++;
            score=score+20;hud();hit=1;
        }
        if(!hit && (battle_stage==STAGE_TROLLS || battle_stage==STAGE_WARTS) &&
           major_hp>0 && rock_x==major_x && rock_y==major_y) {
            hit_major();hit=1;
        }
        if(!hit && rock_y>=WALL_TOP && rock_y<=GROUND) {
            for(i=0;i<ENEMIES;i++) {
                if(ladder[i] && ladder_x[i]==rock_x && rock_y>=ladder_top[i]) {
                    ladder[i]=0;
                    clear_lane(rock_x);
                    if(alive[i] && orc_mode[i]==ORC_CLIMB) kill_orc(i);
                    hit=1;
                    break;
                }
            }
        }
        if(!hit && battle_stage==STAGE_SORCERER && rock_y==GROUND &&
           rock_x==caster_x) {
            score=score+100;
            restore(caster_x,GROUND);
            caster_x=3+next_random()%26;
            tile(caster_x,GROUND,22,70);
            hit=1;hud();
        }
        if(hit || rock_y>GROUND) rock_y=-1;
        else if(rock_y==6 && parapet_hp[rock_x]>0) {
            parapet_hp[rock_x]--;
            terrain(rock_x,6);
            rock_y=-1;
        } else tile(rock_x,rock_y,7,70);
    }
    if(arrow_active) {
        restore(arrow_x,arrow_y);
        arrow_y--;
        if(arrow_y<PLAYER_ROW) arrow_active=0;
        else if(arrow_y==PLAYER_ROW && arrow_x==px) {
            arrow_active=0;
            damage();
            return;
        } else if(arrow_y==6 && parapet_hp[arrow_x]>0) arrow_active=0;
        else tile(arrow_x,arrow_y,8,71);
    }
    if(oil_fall) {
        if(oil_fall>6) restore(oil_x,oil_fall-1);
        if(oil_fall<=GROUND) {
            tile(oil_x,oil_fall,11,70);
            oil_fall++;
        } else {
            oil_fall=0;
            flame_radius=1;
        }
    }
    if(flame_radius) {
        /* A dropped oil flask burns out the attackers and their ladders. */
        for(i=0;i<ENEMIES;i++) {
            if(alive[i] && ex[i]+enemy_columns(i)-1>=oil_x-flame_radius &&
               ex[i]<=oil_x+flame_radius) kill_orc(i);
            if(ladder[i] && ladder_x[i]>=oil_x-flame_radius &&
               ladder_x[i]<=oil_x+flame_radius) {
                ladder[i]=0;
                clear_lane(ladder_x[i]);
            }
        }
        if(oil_x-flame_radius>=0) tile(oil_x-flame_radius,GROUND,11,70);
        if(oil_x+flame_radius<=31) tile(oil_x+flame_radius,GROUND,11,70);
        flame_radius=flame_radius+2;
        if(flame_radius>31) {
            flame_radius=0;
            flame_finished=1;
        }
    }
}

void command(void)
{
    int left,right,fire,direction,i,redraw,old_carries;
    old_carries=carries;redraw=0;
    if(carries==2 && !roof_danger()) carries=0;
    left=kbd_down('6') || kbd_down('a');
    right=kbd_down('7') || kbd_down('d');
    fire=kbd_down('0') || kbd_down(' ');
    direction=0;
    if(left && !right) direction=-1;
    if(right && !left) direction=1;
    /* No queued moves: a released key clears the repeat timer. */
    if(!direction) repeat_wait=0;
    else {
        if(direction!=last_direction) repeat_wait=0;
        if(repeat_wait<=1) {
            if(px+direction>=1 && px+direction<=30) {
                clear_guard();
                px=px+direction;
                redraw=1;
            }
            if(direction!=last_direction) repeat_wait=8;
            else repeat_wait=4;
        } else repeat_wait--;
    }
    last_direction=direction;
    if((px==1 || px==30) && !carries) {
        if(roof_danger()) carries=2;
        else if(px==30 && wave_age>=OIL_READY_TICKS &&
                (battle_stage==STAGE_ORCS || battle_stage==STAGE_ORCS_HARD)) carries=3;
        else carries=1;
    }
    /* Fire once per press, even if a round ends with the key held. */
    if(fire && !last_fire) {
        if(carries==2) {
            for(i=0;i<ENEMIES;i++)
                if(alive[i] && ey[i]<=PLAYER_ROW &&
                   (ex[i]==px || ex[i]==px-1 || ex[i]==px+1)) kill_orc(i);
        } else if(carries==3 && !oil_fall && !flame_radius && rock_y<0) {
            oil_fall=6;oil_x=px;carries=0;
        } else if(carries==1 && rock_y<0) {
            rock_x=px;rock_y=5;carries=0;
        }
    }
    last_fire=fire;
    if(!redraw && old_carries==carries) return;
    show_items();
    draw_guard();
    if(carries==1) tile(px,PLAYER_ROW-1,7,71);
    if(carries==2) tile(px,PLAYER_ROW-1,9,71);
    if(carries==3) tile(px,PLAYER_ROW-1,10,71);
}

void intro(void)
{
    int k;
    paper(0);ink(7);border(0);cls();
    print_at(4,22,"ORC ATTACK");
    print_at(7,11,"DEFEND THE CASTLE AGAINST THE ORCS");
    print_at(10,10,"6 / A  LEFT       7 / D  RIGHT");
    print_at(12,10,"0 / SPACE  FIRE OR DROP ROCK");
    print_at(14,10,"ROCKS BOTH SIDES; OIL APPEARS LATER");
    print_at(16,10,"USE SWORD WHEN ORCS REACH TOP");
    print_at(18,10,"POUR OIL ON CLIMBING ORCS");
    print_at(21,10,"P TO PLAY   1 TO SWITCH PLAYERS");
    k=0;
    while(k!='p' && k!='q') {
        if(kbd_down('1')) {
            players=3-players;
            if(players==1) print_at(20,12,"ONE PLAYER ");
            else print_at(20,12,"TWO PLAYERS");
            while(kbd_down('1')) sleep(1);
        }
        if(kbd_down('p')) k='p';
        if(kbd_down('q')) k='q';
        sleep(1);
    }
    if(k=='q') game_over=2;
    while(kbd_down('p')) sleep(1);
}

int main(void)
{
    int i;
    screen(1);
    seed=ticks()&32767;
    players=1;current=1;game_over=0;
    intro();
    if(game_over==2) return 0;
    score=0;round_no=1;lives=9;wounds=0;frame=0;
    battle_stage=STAGE_ORCS;
    last_direction=0;repeat_wait=0;ai_slot=0;last_fire=kbd_down('0') || kbd_down(' ');
    reset_wave();
    while(!game_over) {
        if(kbd_down('q')) break;
        frame++;
        if(frame>=1500) frame=0;
        /* Use real frame ticks; drawing three-tile sprites takes longer than a loop. */
        if(wave_age<OIL_READY_TICKS+1) {
            unsigned int elapsed;
            elapsed=ticks()-wave_clock;
            if(elapsed>OIL_READY_TICKS) wave_age=OIL_READY_TICKS+1;
            else wave_age=(int)elapsed;
        }
        if(!oil_announced && wave_age>=OIL_READY_TICKS &&
           (battle_stage==STAGE_ORCS || battle_stage==STAGE_ORCS_HARD)) {
            oil_announced=1;
            print_at(2,30,"OIL READY");
            show_items();
        }
        command();
        if(frame%4==0) {
            move_shots();
            if(battle_stage==STAGE_SORCERER ||
               battle_stage==STAGE_TROLLS || battle_stage==STAGE_WARTS)
                move_special();
        }
        if((battle_stage==STAGE_ORCS || battle_stage==STAGE_ORCS_HARD) &&
           (flame_finished || (kills>=ENEMIES && !oil_fall && !flame_radius))) {
            end_round();continue;
        }
        /* One visit per fighter; the other half is for moving pixels. */
        enemy_frame();
        if(frame%8==0) show_items();
        if(frame%90==0 && !arrow_active &&
           (battle_stage==STAGE_ORCS || battle_stage==STAGE_ORCS_HARD)) {
            i=next_random()%ENEMIES;
            if(alive[i] && ey[i]>7) {
                arrow_x=ex[i];arrow_y=ey[i]-1;arrow_active=1;
                tile(arrow_x,arrow_y,8,71);
            }
        }
        sleep(1);
    }
    cls();
    print_at(7,21,"GAME OVER");
    print_at(10,17,"SCORE:");digits(10,32,score);
    print_at(15,9,"PRESS Q OR SPACE TO RETURN");
    while(!kbd_down('q') && !kbd_down(' ')) sleep(1);
    return 0;
}
