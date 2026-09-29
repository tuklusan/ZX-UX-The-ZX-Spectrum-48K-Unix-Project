// ============================================================
// Copyright (c) 2026 SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK
// Governed by the SANYALnet Labs Non-Commercial License.
// See root LICENSE for full terms.
//
// Attribution required: SANYALnet Labs.
// ============================================================
#include "recapi.h"

#define H_DISCS 7
#define H_POLES 3
#define H_LEFT_GCOL_MAX 15
#define H_LEFT_TCOL_MAX 31
#define H_TRAVEL_ROW 4

int h_count[3];
int h_disc[21];
int h_move_count;
int h_current_disc;
int h_cur_src;
int h_cur_dst;
int h_current_depth;
int h_maximum_depth;
int h_inv_fail;
int h_guard_fail;
int h_failed;
int h_fast;

unsigned char h_udg[128] = {
0,0,0,0,0,0,0,0,
24,24,24,24,24,24,24,24,
0,0,0,255,255,0,0,0,
24,24,24,255,255,24,24,24,
0,1,3,3,3,3,1,0,
0,3,15,15,15,15,3,0,
0,7,31,31,31,31,7,0,
0,31,127,127,127,127,31,0,
126,255,255,255,255,255,255,126,
0,248,254,254,254,254,248,0,
0,224,248,248,248,248,224,0,
0,192,240,240,240,240,192,0,
0,128,192,192,192,192,128,0,
60,126,255,255,255,255,126,60,
0,0,0,0,0,0,0,0,
0,0,0,0,0,0,0,0
};

int h_abs(int v)
{
    if (v < 0)
        return -v;
    return v;
}

void h_style(int inkc, int paperc, int br)
{
    ink(inkc);
    paper(paperc);
    bright(br);
    inverse(0);
    over(0);
}

int h_text_ok(int row, int col, char *s)
{
    int n;
    n = (int)strlen(s);
    if (row < 0 || row > 23)
        return 0;
    if (col < 0 || col > H_LEFT_TCOL_MAX)
        return 0;
    if (col + n > 32)
        return 0;
    return 1;
}

void h_fail(char *reason)
{
    h_failed = 1;
    h_style(7, 0, 1);
    if (h_text_ok(19, 0, reason))
        print_at(19, 0, reason);
    print_at(23, 0, "FAIL");
}

void h_text(int row, int col, char *s)
{
    if (h_failed)
        return;
    if (!h_text_ok(row, col, s)) {
        h_inv_fail++;
        h_fail("TEXT RANGE");
        return;
    }
    h_style(7, 0, 1);
    if (print_at(row, col, s) != 0) {
        h_inv_fail++;
        h_fail("TEXT HOST");
    }
}

void h_num(int row, int col, int value, int width)
{
    char out[8];
    int i;
    int v;
    if (width < 1 || width > 6) {
        h_inv_fail++;
        h_fail("NUM WIDTH");
        return;
    }
    for (i = 0; i < width; i++)
        out[i] = ' ';
    out[width] = 0;
    v = value;
    i = width - 1;
    if (v == 0)
        out[i] = '0';
    while (v > 0 && i >= 0) {
        out[i] = (char)('0' + v % 10);
        v = v / 10;
        i--;
    }
    h_text(row, col, out);
}

int h_gfx_ok(int slot, int row, int col)
{
    if (slot < 0 || slot > 15)
        return 0;
    if (row < 0 || row > 23)
        return 0;
    if (col < 0 || col > H_LEFT_GCOL_MAX)
        return 0;
    return 1;
}

void h_draw(int slot, int row, int col, int inkc)
{
    if (h_failed)
        return;
    if (!h_gfx_ok(slot, row, col)) {
        h_inv_fail++;
        h_fail("DRAW RANGE");
        return;
    }
    h_style(inkc, 0, 1);
    if (udg_draw(slot, row, col) != 0) {
        h_inv_fail++;
        h_fail("DRAW HOST");
    }
}

void h_define_udg(int slot)
{
    if (slot < 0 || slot > 15) {
        h_inv_fail++;
        h_fail("UDG RANGE");
        return;
    }
    if (udg_define(slot, h_udg + slot * 8) != 0) {
        h_inv_fail++;
        h_fail("UDG HOST");
    }
}

void h_clear_half(void)
{
    int r;
    char *blank;
    blank = "                                ";
    for (r = 0; r < 24; r++)
        h_text(r, 0, blank);
}

int h_disc_color(int disc)
{
    int colors[7];
    colors[0] = 6;
    colors[1] = 3;
    colors[2] = 5;
    colors[3] = 4;
    colors[4] = 2;
    colors[5] = 7;
    colors[6] = 3;
    if (disc < 1 || disc > 7)
        return 7;
    return colors[disc - 1];
}

void h_draw_disc(int disc, int row, int col)
{
    int inkc;
    inkc = h_disc_color(disc);
    if (disc == 1) {
        h_draw(13, row, col, inkc);
        return;
    }
    if (disc == 2) {
        h_draw(4, row, col - 1, inkc);
        h_draw(8, row, col, inkc);
        h_draw(12, row, col + 1, inkc);
        return;
    }
    if (disc == 3) {
        h_draw(5, row, col - 1, inkc);
        h_draw(8, row, col, inkc);
        h_draw(11, row, col + 1, inkc);
        return;
    }
    if (disc == 4) {
        h_draw(6, row, col - 1, inkc);
        h_draw(8, row, col, inkc);
        h_draw(10, row, col + 1, inkc);
        return;
    }
    if (disc == 5) {
        h_draw(7, row, col - 1, inkc);
        h_draw(8, row, col, inkc);
        h_draw(9, row, col + 1, inkc);
        return;
    }
    if (disc == 6) {
        h_draw(4, row, col - 2, inkc);
        h_draw(8, row, col - 1, inkc);
        h_draw(8, row, col, inkc);
        h_draw(8, row, col + 1, inkc);
        h_draw(12, row, col + 2, inkc);
        return;
    }
    if (disc == 7) {
        h_draw(5, row, col - 2, inkc);
        h_draw(8, row, col - 1, inkc);
        h_draw(8, row, col, inkc);
        h_draw(8, row, col + 1, inkc);
        h_draw(11, row, col + 2, inkc);
        return;
    }
    h_inv_fail++;
    h_fail("DISC RANGE");
}

int h_pole_col(int pole)
{
    if (pole == 0)
        return 2;
    if (pole == 1)
        return 7;
    return 12;
}

void h_restore_row(int row)
{
    int c;
    int p;
    int i;
    int prow;
    for (c = 0; c < 16; c++)
        h_draw(0, row, c, 0);
    if (row >= 6 && row <= 16) {
        for (p = 0; p < 3; p++)
            h_draw(1, row, h_pole_col(p), 7);
    }
    if (row == 17) {
        for (c = 0; c < 16; c++)
            h_draw(2, row, c, 7);
        h_draw(3, row, h_pole_col(0), 7);
        h_draw(3, row, h_pole_col(1), 7);
        h_draw(3, row, h_pole_col(2), 7);
    }
    for (p = 0; p < 3; p++) {
        for (i = 0; i < h_count[p]; i++) {
            prow = 16 - i;
            if (prow == row)
                h_draw_disc(h_disc[p * 7 + i], row,
                            h_pole_col(p));
        }
    }
}

void h_repaint_stack(int pole)
{
    int row;
    if (pole < 0 || pole > 2) {
        h_inv_fail++;
        h_fail("POLE RANGE");
        return;
    }
    for (row = 6; row <= 17; row++)
        h_restore_row(row);
}

void h_pause(int ticks50)
{
    yield();
    if (!h_fast)
        sleep((unsigned int)ticks50);
}

void h_show_live(void)
{
    char s[2];
    h_text(1, 0, "MOVE ");
    h_num(1, 5, h_move_count, 3);
    h_text(1, 8, "/127 DEP ");
    h_num(1, 17, h_current_depth, 1);
    h_text(1, 18, "/7");
    h_text(2, 0, "DISC ");
    h_num(2, 5, h_current_disc, 1);
    h_text(2, 7, " ");
    s[0] = (char)('A' + h_cur_src);
    s[1] = 0;
    h_text(2, 8, s);
    h_text(2, 9, "->");
    s[0] = (char)('A' + h_cur_dst);
    h_text(2, 11, s);
    h_text(20, 0, "FRAME GUARD OK");
    h_text(22, 0, "MAX DEP ");
    h_num(22, 8, h_maximum_depth, 1);
}

int h_validate(void)
{
    int seen[8];
    int p;
    int i;
    int d;
    int total;
    for (i = 0; i < 8; i++)
        seen[i] = 0;
    total = 0;
    for (p = 0; p < 3; p++) {
        if (h_count[p] < 0 || h_count[p] > 7)
            return 0;
        for (i = 0; i < h_count[p]; i++) {
            d = h_disc[p * 7 + i];
            if (d < 1 || d > 7)
                return 0;
            if (seen[d])
                return 0;
            seen[d] = 1;
            total++;
            if (i > 0 && h_disc[p * 7 + i - 1] <= d)
                return 0;
        }
    }
    if (total != 7)
        return 0;
    for (d = 1; d <= 7; d++) {
        if (!seen[d])
            return 0;
    }
    return 1;
}

int h_check_final(void)
{
    int i;
    if (!h_validate())
        return 0;
    if (h_move_count != 127)
        return 0;
    if (h_count[0] != 0 || h_count[1] != 0)
        return 0;
    if (h_count[2] != 7)
        return 0;
    for (i = 0; i < 7; i++) {
        if (h_disc[14 + i] != 7 - i)
            return 0;
    }
    if (h_maximum_depth != 7)
        return 0;
    if (h_inv_fail != 0)
        return 0;
    if (h_guard_fail != 0)
        return 0;
    return 1;
}

int h_move(int source, int target)
{
    int disc;
    int old_count;
    int target_count;
    int row;
    int col;
    int next;
    int target_row;
    if (h_failed)
        return 0;
    if (source < 0 || source > 2 || target < 0 || target > 2) {
        h_inv_fail++;
        h_fail("MOVE POLE");
        return 0;
    }
    if (h_count[source] <= 0) {
        h_inv_fail++;
        h_fail("EMPTY SOURCE");
        return 0;
    }
    old_count = h_count[source];
    target_count = h_count[target];
    disc = h_disc[source * 7 + old_count - 1];
    if (disc < 1 || disc > 7) {
        h_inv_fail++;
        h_fail("MOVE DISC");
        return 0;
    }
    if (target_count > 0 &&
        h_disc[target * 7 + target_count - 1] < disc) {
        h_inv_fail++;
        h_fail("ILLEGAL MOVE");
        return 0;
    }
    h_current_disc = disc;
    h_cur_src = source;
    h_cur_dst = target;
    h_show_live();
    h_count[source]--;
    row = 17 - old_count;
    col = h_pole_col(source);
    h_restore_row(row);
    h_draw_disc(disc, row, col);
    while (row > H_TRAVEL_ROW) {
        h_restore_row(row);
        row--;
        h_draw_disc(disc, row, col);
        h_text(19, 0, "LIFT");
        h_pause(2);
        if (h_failed)
            return 0;
    }
    next = h_pole_col(target);
    while (col != next) {
        h_restore_row(row);
        if (col < next)
            col++;
        else
            col--;
        h_draw_disc(disc, row, col);
        h_text(19, 0, "TRAVEL");
        h_pause(2);
        if (h_failed)
            return 0;
    }
    target_row = 16 - target_count;
    while (row < target_row) {
        h_restore_row(row);
        row++;
        h_draw_disc(disc, row, col);
        h_text(19, 0, "DROP");
        h_pause(2);
        if (h_failed)
            return 0;
    }
    h_disc[target * 7 + target_count] = disc;
    h_count[target]++;
    h_move_count++;
    h_restore_row(row);
    h_repaint_stack(source);
    h_repaint_stack(target);
    if (!h_validate()) {
        h_inv_fail++;
        h_fail("MODEL FAIL");
        return 0;
    }
    h_text(19, 0, "SETTLE");
    h_show_live();
    h_pause(4);
    return !h_failed;
}

int h_solve(int n, int source, int spare, int target,
            int depth)
{
    int guard;
    if (h_failed)
        return 0;
    if (n <= 0)
        return 1;
    guard = n * 101 + source * 17 + spare * 7 +
            target * 3 + depth;
    h_current_depth = depth;
    if (depth > h_maximum_depth)
        h_maximum_depth = depth;
    if (!h_solve(n - 1, source, target, spare, depth + 1))
        return 0;
    if (guard != n * 101 + source * 17 + spare * 7 +
        target * 3 + depth) {
        h_guard_fail++;
        h_fail("FRAME FAIL");
        return 0;
    }
    h_current_depth = depth;
    if (!h_move(source, target))
        return 0;
    if (!h_solve(n - 1, spare, source, target, depth + 1))
        return 0;
    if (guard != n * 101 + source * 17 + spare * 7 +
        target * 3 + depth) {
        h_guard_fail++;
        h_fail("FRAME FAIL");
        return 0;
    }
    h_current_depth = depth;
    return 1;
}

void h_init_model(void)
{
    int p;
    int i;
    for (p = 0; p < 3; p++) {
        h_count[p] = 0;
        for (i = 0; i < 7; i++)
            h_disc[p * 7 + i] = 0;
    }
    h_count[0] = 7;
    for (i = 0; i < 7; i++)
        h_disc[i] = 7 - i;
    h_move_count = 0;
    h_current_disc = 0;
    h_cur_src = 0;
    h_cur_dst = 2;
    h_current_depth = 0;
    h_maximum_depth = 0;
    h_inv_fail = 0;
    h_guard_fail = 0;
    h_failed = 0;
}

void h_init_screen(void)
{
    int i;
    for (i = 0; i < 16; i++)
        h_define_udg(i);
    h_clear_half();
    h_text(0, 0, "TOWERS OF HANOI");
    h_text(18, 4, "A");
    h_text(18, 14, "B");
    h_text(18, 24, "C");
    h_text(20, 0, "FRAME GUARD OK");
    h_text(23, 0, "SEARCHING");
    h_repaint_stack(0);
}

void h_show_pass(void)
{
    h_text(19, 0, "SOLVED");
    h_text(20, 0, "127/127 MOVES");
    h_text(21, 0, "FRAME GUARD OK");
    h_text(22, 0, "MAX DEP 7");
    h_text(23, 0, "PASS");
}

int main(int argc, char **argv)
{
    h_fast = 0;
    if (argc > 1 && strcmp(argv[1], "--verify") == 0)
        h_fast = 1;
    h_init_model();
    h_init_screen();
    if (!h_validate()) {
        h_inv_fail++;
        h_fail("INIT MODEL");
        return 1;
    }
    if (!h_solve(7, 0, 1, 2, 1))
        return 1;
    if (!h_check_final()) {
        h_inv_fail++;
        h_fail("FINAL FAIL");
        return 1;
    }
    h_show_pass();
    if (!h_fast)
        sleep(100u);
    return 0;
}
