// ============================================================
// Copyright (c) 2026 SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and restricted
// model training prohibited unless separately authorized.
//
// Attribution required: SANYALnet Labs.
// See root LICENSE for full terms.
// ============================================================
#include "appapi.h"

/* 1982 constructor figures used by the startup dashboard. */
/* Wins: official 16-race season results. */
/* Podiums/poles: season constructor statistics. */

int gp_wins[4];
int gp_podiums[4];
int gp_poles[4];

int gp_vx[16];
int gp_vy[16];
int gp_owner[16];
int gp_edited;
char gp_filebuf[16];

void gp_rebuild_pie(void);

void gp_new(void)
{
    int i;
    if (!app_confirm_new()) {
        app_notice_set("NEW CANCELLED");
        return;
    }
    for (i = 0; i < 4; i++) {
        gp_wins[i] = 0;
        gp_podiums[i] = 0;
        gp_poles[i] = 0;
    }
    gp_edited = 1;
    gp_rebuild_pie();
    app_notice_set("NEW BLANK STATISTICS");
}

void gp_seed(void)
{
    gp_wins[0] = 3;
    gp_wins[1] = 4;
    gp_wins[2] = 4;
    gp_wins[3] = 1;

    gp_podiums[0] = 11;
    gp_podiums[1] = 8;
    gp_podiums[2] = 8;
    gp_podiums[3] = 7;

    gp_poles[0] = 3;
    gp_poles[1] = 0;
    gp_poles[2] = 10;
    gp_poles[3] = 1;

    gp_vx[0] = 0;
    gp_vy[0] = 500;
    gp_vx[1] = 191;
    gp_vy[1] = 462;
    gp_vx[2] = 354;
    gp_vy[2] = 354;
    gp_vx[3] = 462;
    gp_vy[3] = 191;
    gp_vx[4] = 500;
    gp_vy[4] = 0;
    gp_vx[5] = 462;
    gp_vy[5] = -191;
    gp_vx[6] = 354;
    gp_vy[6] = -354;
    gp_vx[7] = 191;
    gp_vy[7] = -462;
    gp_vx[8] = 0;
    gp_vy[8] = -500;
    gp_vx[9] = -191;
    gp_vy[9] = -462;
    gp_vx[10] = -354;
    gp_vy[10] = -354;
    gp_vx[11] = -462;
    gp_vy[11] = -191;
    gp_vx[12] = -500;
    gp_vy[12] = 0;
    gp_vx[13] = -462;
    gp_vy[13] = 191;
    gp_vx[14] = -354;
    gp_vy[14] = 354;
    gp_vx[15] = -191;
    gp_vy[15] = 462;

    gp_owner[0] = 0;
    gp_owner[1] = 0;
    gp_owner[2] = 0;
    gp_owner[3] = 0;
    gp_owner[4] = 1;
    gp_owner[5] = 1;
    gp_owner[6] = 1;
    gp_owner[7] = 1;
    gp_owner[8] = 2;
    gp_owner[9] = 2;
    gp_owner[10] = 2;
    gp_owner[11] = 3;
    gp_owner[12] = 3;
    gp_owner[13] = 4;
    gp_owner[14] = 5;
    gp_owner[15] = 6;
}

/* Pie shares reflect the edited win totals; remaining wins are other teams. */
void gp_rebuild_pie(void)
{
    int k;
    int g;
    int left;
    k = 0;
    for (g = 0; g < 4; g++) {
        left = gp_wins[g];
        while (left > 0 && k < 16) {
            gp_owner[k] = g;
            k++;
            left--;
        }
    }
    while (k < 16) {
        gp_owner[k] = 4;
        k++;
    }
}

void gp_save(void)
{
    int i;
    if (!app_choose_file("SAVE>"))
        return;
    gp_filebuf[0] = 'G';
    gp_filebuf[1] = 'P';
    gp_filebuf[2] = '8';
    gp_filebuf[3] = '2';
    for (i = 0; i < 4; i++) {
        gp_filebuf[4 + i * 3] = (char)gp_wins[i];
        gp_filebuf[5 + i * 3] = (char)gp_podiums[i];
        gp_filebuf[6 + i * 3] = (char)gp_poles[i];
    }
    if (app_save_file(gp_filebuf, 16u))
        app_notice_set("SAVED TO RAM FILE");
    else
        app_notice_set("SAVE FAILED");
}

void gp_load(void)
{
    int n;
    int i;
    int wins;
    if (!app_choose_file("LOAD>"))
        return;
    n = app_load_file(gp_filebuf, 16u);
    if (n != 16 || gp_filebuf[0] != 'G' ||
        gp_filebuf[1] != 'P' || gp_filebuf[2] != '8' ||
        gp_filebuf[3] != '2') {
        app_notice_set("LOAD FAILED OR INVALID FILE");
        return;
    }
    wins = 0;
    for (i = 0; i < 4; i++) {
        if ((unsigned char)gp_filebuf[4 + i * 3] > 16 ||
            (unsigned char)gp_filebuf[5 + i * 3] > 16 ||
            (unsigned char)gp_filebuf[6 + i * 3] > 16) {
            app_notice_set("INVALID RACE STATISTICS");
            return;
        }
        wins = wins + (unsigned char)gp_filebuf[4 + i * 3];
    }
    if (wins > 16) {
        app_notice_set("WIN TOTAL EXCEEDS 16");
        return;
    }
    for (i = 0; i < 4; i++) {
        gp_wins[i] = (unsigned char)gp_filebuf[4 + i * 3];
        gp_podiums[i] = (unsigned char)gp_filebuf[5 + i * 3];
        gp_poles[i] = (unsigned char)gp_filebuf[6 + i * 3];
    }
    gp_edited = 1;
    gp_rebuild_pie();
    app_notice_set("LOADED FROM RAM FILE");
}

void gp_edit(void)
{
    char buf[6];
    int team;
    int stat;
    int value;
    int i;
    int wins;
    app_clear_row(23);
    print_at(23, 0, "TEAM (1 FER 2 MCL 3 REN 4 WIL)> ");
    if (!app_readline(23, 34, buf, 6))
        return;
    team = app_decimal(buf, 4) - 1;
    if (team < 0 || team > 3) {
        app_notice_set("INVALID TEAM");
        return;
    }
    app_clear_row(23);
    print_at(23, 0, "STAT W WINS P PODIUMS L POLES> ");
    stat = app_key();
    if (stat != 'w' && stat != 'p' && stat != 'l') {
        app_notice_set("INVALID STAT");
        return;
    }
    app_clear_row(23);
    print_at(23, 0, "NEW VALUE 0-16> ");
    if (!app_readline(23, 17, buf, 6))
        return;
    value = app_decimal(buf, 16);
    if (value < 0) {
        app_notice_set("INVALID VALUE");
        return;
    }
    if (stat == 'w') {
        wins = value;
        for (i = 0; i < 4; i++) {
            if (i != team)
                wins = wins + gp_wins[i];
        }
        if (wins > 16) {
            app_notice_set("WIN TOTAL EXCEEDS 16");
            return;
        }
        gp_wins[team] = value;
    }
    if (stat == 'p')
        gp_podiums[team] = value;
    if (stat == 'l')
        gp_poles[team] = value;
    gp_edited = 1;
    gp_rebuild_pie();
    app_notice_set("STAT UPDATED; SAVE TO KEEP");
}

/* Draw tall solid bars as lines, hatched bars as sparse pixels. */
void gp_box(int x, int y, int w, int h, int style)
{
    int px;
    int py;
    for (px = 0; px < w; px++) {
        if (style == 0) {
            draw(x + px, y, x + px, y + h - 1);
        } else {
            for (py = 0; py < h; py++) {
                if (px == 0 || px == w - 1 ||
                    py == 0 || py == h - 1 ||
                    (style == 1 && ((px + py) & 1) == 0) ||
                    (style == 2 && (px & 1) == 0))
                    plot(x + px, y + py);
            }
        }
    }
}

void gp_bars(void)
{
    int g;
    int x;
    draw(6, 34, 126, 34);
    draw(6, 34, 6, 132);
    draw(4, 74, 8, 74);
    draw(4, 114, 8, 114);
    for (g = 0; g < 4; g++) {
        x = 15 + g * 28;
        gp_box(x, 35, 5, gp_wins[g] * 8, 0);
        gp_box(x + 7, 35, 5, gp_podiums[g] * 8, 1);
        if (gp_poles[g] > 0)
            gp_box(x + 14, 35, 5, gp_poles[g] * 8, 2);
    }
}

int gp_sector(int dx, int dy)
{
    int best;
    int bestdot;
    int dot;
    int k;
    best = 0;
    bestdot = -32767;
    for (k = 0; k < 16; k++) {
        dot = dx * gp_vx[k] + dy * gp_vy[k];
        if (dot > bestdot) {
            bestdot = dot;
            best = k;
        }
    }
    return best;
}

int gp_pattern(int owner, int x, int y)
{
    if (owner == 0)
        return 1;
    if (owner == 1)
        return ((x + y) & 1) == 0;
    if (owner == 2)
        return (x & 1) == 0;
    if (owner == 3)
        return (y & 1) == 0;
    if (owner == 4)
        return ((x + y) & 3) == 0;
    if (owner == 5)
        return ((x - y) & 3) == 0;
    return ((x + y) & 2) == 0;
}

/* Plot the 16 sectors with radial strokes, not per-pixel dot products. */
void gp_pie(void)
{
    int cx;
    int cy;
    int r;
    int k;
    int k2;
    int t;
    int x1;
    int y1;
    int x2;
    int y2;
    int x;
    int y;
    cx = 190;
    cy = 94;
    r = 42;
    for (k = 0; k < 16; k++) {
        k2 = (k + 1) & 15;
        x1 = cx + gp_vx[k] * r / 500;
        y1 = cy + gp_vy[k] * r / 500;
        x2 = cx + gp_vx[k2] * r / 500;
        y2 = cy + gp_vy[k2] * r / 500;
        draw(x1, y1, x2, y2);
        for (t = 0; t < 5; t++) {
            x = x1 + (x2 - x1) * t / 5;
            y = y1 + (y2 - y1) * t / 5;
            if (gp_pattern(gp_owner[k], x, y) || t == 0)
                draw(cx, cy, x, y);
        }
    }
}

/* Keep the editable figures visible, not just their bar heights. */
void gp_team_stats(int row, int col, char *name, int idx)
{
    char digits[6];
    print_at(row, col, name);
    print_at(row, col + 4, "W");
    app_uint_text(digits, (unsigned int)gp_wins[idx]);
    print_at(row, col + 5, digits);
    print_at(row, col + 9, "P");
    app_uint_text(digits, (unsigned int)gp_podiums[idx]);
    print_at(row, col + 10, digits);
    print_at(row, col + 14, "L");
    app_uint_text(digits, (unsigned int)gp_poles[idx]);
    print_at(row, col + 15, digits);
}

void gp_render(void)
{
    cls();
    paper(0);
    ink(7);
    bright(1);
    print_at(0, 10, "GP82 - GRAND PRIX 1982");
    bright(0);
    print_at(2, 1, "TOP FOUR: WINS / PODIUMS / POLES");
    print_at(2, 35, "RACE WINS - 16 TOTAL");
    gp_bars();
    gp_pie();
    print_at(17, 1, "FER   MCL   REN   WIL");
    print_at(19, 1, "SOLID W  CHECK P  STRIPE POLE");
    if (gp_edited) {
        print_at(17, 35, "EDITED COUNTS; PIE = WINS");
        print_at(18, 35, "OTHER TEAMS: REMAINING");
    } else {
        print_at(17, 35, "MCL4 REN4 FER3 BRB2");
        print_at(18, 35, "LOT1 WIL1 TYR1");
        print_at(20, 35, "FERRARI CHAMPION: 74 PTS");
    }
    gp_team_stats(20, 1, "FER", 0);
    gp_team_stats(20, 33, "MCL", 1);
    gp_team_stats(21, 1, "REN", 2);
    gp_team_stats(21, 33, "WIL", 3);
    print_at(22, 1, "W WINS  P PODIUMS  L POLES");
    print_at(23, 1, "E EDIT N NEW S SAVE L LOAD Q QUIT R REDRAW");
    if (app_notice[0] != 0)
        print_at(19, 35, app_notice);
    yield();
}

int main(int argc, char **argv)
{
    int key;
    gp_seed();
    gp_edited = 0;
    app_setfile("/tmp/gp82.gp82");
    gp_render();
    if (argc > 1 && strcmp(argv[1], "verify") == 0)
        return 0;
    while (1) {
        key = app_key();
        if (key == 'q')
            return 0;
        if (key == 'r')
            gp_render();
        if (key == 'e') {
            gp_edit();
            gp_render();
        }
        if (key == 'n') {
            gp_new();
            gp_render();
        }
        if (key == 's') {
            gp_save();
            gp_render();
        }
        if (key == 'l') {
            gp_load();
            gp_render();
        }
    }
}
