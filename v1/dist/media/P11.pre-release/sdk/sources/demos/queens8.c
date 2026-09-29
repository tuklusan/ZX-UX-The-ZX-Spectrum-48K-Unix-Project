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

#define Q_SIZE 8
#define Q_GCOL_MIN 16
#define Q_GCOL_MAX 31
#define Q_TCOL_MIN 32
#define Q_TCOL_MAX 63

int q_col[8];
int q_col_used[8];
int q_down_used[15];
int q_up_used[15];
int q_current_row;
int q_current_col;
int q_placed_count;
int q_tests;
int q_backtracks;
int q_current_depth;
int q_maximum_depth;
int q_inv_fail;
int q_guard_fail;
int q_failed;
int q_fast;

unsigned char q_udg[128] = {
130,199,111,63,31,15,7,15,
65,227,246,252,248,240,224,240,
31,63,63,127,127,255,255,127,
248,252,252,254,254,255,255,254,
130,197,104,48,16,8,4,8,
65,163,22,12,8,16,32,16,
16,32,32,64,64,128,128,127,
8,4,4,2,2,1,1,254,
130,197,104,48,24,12,6,9,
65,163,22,12,24,48,96,144,
17,34,36,72,80,160,192,255,
136,68,36,18,10,5,3,255,
0,0,0,0,0,0,0,0,
24,24,126,24,24,126,24,24,
24,60,126,219,255,126,60,24,
0,0,0,0,0,0,0,0
};

int q_abs(int v)
{
    if (v < 0)
        return -v;
    return v;
}

void q_style(int inkc, int paperc, int br)
{
    ink(inkc);
    paper(paperc);
    bright(br);
    inverse(0);
    over(0);
}

int q_text_ok(int row, int col, char *s)
{
    int n;
    n = (int)strlen(s);
    if (row < 0 || row > 23)
        return 0;
    if (col < Q_TCOL_MIN || col > Q_TCOL_MAX)
        return 0;
    if (col + n > 64)
        return 0;
    return 1;
}

void q_fail(char *reason)
{
    q_failed = 1;
    q_style(7, 0, 1);
    if (q_text_ok(19, 32, reason))
        print_at(19, 32, reason);
    print_at(23, 32, "FAIL");
}

void q_text(int row, int col, char *s)
{
    if (q_failed)
        return;
    if (!q_text_ok(row, col, s)) {
        q_inv_fail++;
        q_fail("TEXT RANGE");
        return;
    }
    q_style(7, 0, 1);
    if (print_at(row, col, s) != 0) {
        q_inv_fail++;
        q_fail("TEXT HOST");
    }
}

void q_num(int row, int col, int value, int width)
{
    char out[8];
    int i;
    int v;
    if (width < 1 || width > 6) {
        q_inv_fail++;
        q_fail("NUM WIDTH");
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
    q_text(row, col, out);
}

int q_gfx_ok(int slot, int row, int col)
{
    if (slot < 16 || slot > 31)
        return 0;
    if (row < 0 || row > 23)
        return 0;
    if (col < Q_GCOL_MIN || col > Q_GCOL_MAX)
        return 0;
    return 1;
}

void q_draw(int slot, int row, int col, int inkc, int paperc)
{
    if (q_failed)
        return;
    if (!q_gfx_ok(slot, row, col)) {
        q_inv_fail++;
        q_fail("DRAW RANGE");
        return;
    }
    q_style(inkc, paperc, 1);
    if (udg_draw(slot, row, col) != 0) {
        q_inv_fail++;
        q_fail("DRAW HOST");
    }
}

void q_draw_queen(int base, int row, int col, int inkc,
                  int paperc)
{
    if (q_failed)
        return;
    if (base != 16 && base != 20 && base != 24) {
        q_inv_fail++;
        q_fail("QUEEN UDG");
        return;
    }
    if (row < 3 || row > 17 || col < 16 || col > 30) {
        q_inv_fail++;
        q_fail("QUEEN RANGE");
        return;
    }
    q_style(inkc, paperc, 1);
    if (udg_draw_2x2(base, row, col) != 0) {
        q_inv_fail++;
        q_fail("QUEEN HOST");
    }
}

void q_define_udg(int slot)
{
    if (slot < 16 || slot > 31) {
        q_inv_fail++;
        q_fail("UDG RANGE");
        return;
    }
    if (udg_define(slot, q_udg + (slot - 16) * 8) != 0) {
        q_inv_fail++;
        q_fail("UDG HOST");
    }
}

void q_clear_half(void)
{
    int r;
    char *blank;
    blank = "                                ";
    for (r = 0; r < 24; r++)
        q_text(r, 32, blank);
}

int q_square_paper(int row, int col)
{
    if ((row + col) & 1)
        return 1;
    return 0;
}

void q_board_square(int row, int col)
{
    int gr;
    int gc;
    int p;
    if (row < 0 || row > 7 || col < 0 || col > 7) {
        q_inv_fail++;
        q_fail("BOARD RANGE");
        return;
    }
    gr = 3 + row * 2;
    gc = 16 + col * 2;
    p = q_square_paper(row, col);
    q_draw(28, gr, gc, 7, p);
    q_draw(28, gr, gc + 1, 7, p);
    q_draw(28, gr + 1, gc, 7, p);
    q_draw(28, gr + 1, gc + 1, 7, p);
}

void q_show_piece(int row, int col, int base, int inkc)
{
    int gr;
    int gc;
    int p;
    q_board_square(row, col);
    if (q_failed)
        return;
    gr = 3 + row * 2;
    gc = 16 + col * 2;
    p = q_square_paper(row, col);
    q_draw_queen(base, gr, gc, inkc, p);
}

void q_draw_board(void)
{
    int r;
    int c;
    for (r = 0; r < 8; r++) {
        for (c = 0; c < 8; c++)
            q_board_square(r, c);
    }
}

void q_pause(int ticks50)
{
    yield();
    if (!q_fast)
        sleep((unsigned int)ticks50);
}

void q_live(void)
{
    char s[2];
    q_text(1, 32, "TRY ");
    s[0] = (char)('A' + q_current_col);
    s[1] = 0;
    q_text(1, 36, s);
    q_num(1, 37, q_current_row + 1, 1);
    q_text(1, 39, " DEP ");
    q_num(1, 44, q_current_depth, 1);
    q_text(1, 45, "/8");
    q_text(19, 32, "ROW ");
    q_num(19, 36, q_current_row + 1, 1);
    q_text(19, 38, " COL ");
    q_text(19, 43, s);
    q_text(20, 32, "PLACED ");
    q_num(20, 39, q_placed_count, 1);
    q_text(20, 41, "BACK ");
    q_num(20, 46, q_backtracks, 3);
    q_text(21, 32, "FRAME GUARD OK");
    q_text(22, 32, "MAX DEP ");
    q_num(22, 40, q_maximum_depth, 1);
}

int q_validate(void)
{
    int cs[8];
    int ds[15];
    int us[15];
    int r;
    int c;
    int d;
    int u;
    int count;
    for (c = 0; c < 8; c++)
        cs[c] = 0;
    for (c = 0; c < 15; c++) {
        ds[c] = 0;
        us[c] = 0;
    }
    count = 0;
    for (r = 0; r < 8; r++) {
        c = q_col[r];
        if (c == -1)
            continue;
        if (c < 0 || c > 7)
            return 0;
        d = r - c + 7;
        u = r + c;
        if (d < 0 || d > 14 || u < 0 || u > 14)
            return 0;
        if (cs[c] || ds[d] || us[u])
            return 0;
        cs[c] = 1;
        ds[d] = 1;
        us[u] = 1;
        count++;
    }
    if (count != q_placed_count)
        return 0;
    for (c = 0; c < 8; c++) {
        if (cs[c] != q_col_used[c])
            return 0;
    }
    for (c = 0; c < 15; c++) {
        if (ds[c] != q_down_used[c])
            return 0;
        if (us[c] != q_up_used[c])
            return 0;
    }
    return 1;
}

int q_check_final(void)
{
    int expected[8];
    int r;
    int c;
    int rr;
    expected[0] = 0;
    expected[1] = 4;
    expected[2] = 7;
    expected[3] = 5;
    expected[4] = 2;
    expected[5] = 6;
    expected[6] = 1;
    expected[7] = 3;
    if (!q_validate())
        return 0;
    if (q_placed_count != 8 || q_maximum_depth != 8)
        return 0;
    if (q_tests != 876)
        return 0;
    if (q_backtracks != 105)
        return 0;
    if (q_inv_fail != 0)
        return 0;
    if (q_guard_fail != 0)
        return 0;
    for (r = 0; r < 8; r++) {
        if (q_col[r] != expected[r])
            return 0;
        for (rr = r + 1; rr < 8; rr++) {
            c = q_col[rr];
            if (c == q_col[r])
                return 0;
            if (q_abs(rr - r) == q_abs(c - q_col[r]))
                return 0;
        }
    }
    return 1;
}

int q_place(int row, int depth)
{
    int col;
    int down;
    int up;
    int guard;
    int child;
    if (q_failed)
        return 0;
    q_current_row = row;
    q_current_depth = depth;
    if (depth > q_maximum_depth)
        q_maximum_depth = depth;
    for (col = 0; col < 8; col++) {
        guard = row * 101 + depth * 17 + col * 7 + 3;
        q_current_row = row;
        q_current_col = col;
        q_current_depth = depth;
        q_live();
        q_show_piece(row, col, 20, 6);
        q_tests++;
        q_pause(1);
        down = row - col + 7;
        up = row + col;
        if (down < 0 || down > 14 || up < 0 || up > 14) {
            q_inv_fail++;
            q_fail("DIAG RANGE");
            return 0;
        }
        if (q_col_used[col] ||
            q_down_used[down] || q_up_used[up]) {
            q_board_square(row, col);
            continue;
        }
        q_col[row] = col;
        q_col_used[col] = 1;
        q_down_used[down] = 1;
        q_up_used[up] = 1;
        q_placed_count++;
        if (!q_validate()) {
            q_inv_fail++;
            q_fail("MODEL FAIL");
            return 0;
        }
        q_show_piece(row, col, 16, 7);
        q_live();
        q_pause(4);
        if (row == 7)
            return 1;
        child = q_place(row + 1, depth + 1);
        if (guard != row * 101 + depth * 17 + col * 7 + 3 ||
            q_col[row] != col) {
            q_guard_fail++;
            q_fail("FRAME FAIL");
            return 0;
        }
        q_current_row = row;
        q_current_col = col;
        q_current_depth = depth;
        if (child)
            return 1;
        q_show_piece(row, col, 24, 2);
        q_pause(4);
        q_col[row] = -1;
        q_col_used[col] = 0;
        q_down_used[down] = 0;
        q_up_used[up] = 0;
        q_placed_count--;
        q_backtracks++;
        q_board_square(row, col);
        if (!q_validate()) {
            q_inv_fail++;
            q_fail("MODEL FAIL");
            return 0;
        }
        q_live();
    }
    return 0;
}

void q_init_model(void)
{
    int i;
    for (i = 0; i < 8; i++) {
        q_col[i] = -1;
        q_col_used[i] = 0;
    }
    for (i = 0; i < 15; i++) {
        q_down_used[i] = 0;
        q_up_used[i] = 0;
    }
    q_current_row = 0;
    q_current_col = 0;
    q_placed_count = 0;
    q_tests = 0;
    q_backtracks = 0;
    q_current_depth = 0;
    q_maximum_depth = 0;
    q_inv_fail = 0;
    q_guard_fail = 0;
    q_failed = 0;
}

void q_init_screen(void)
{
    int i;
    char s[2];
    for (i = 16; i < 32; i++)
        q_define_udg(i);
    q_clear_half();
    q_text(0, 32, "8 QUEENS - RECURSIVE SEARCH");
    for (i = 0; i < 8; i++) {
        s[0] = (char)('A' + i);
        s[1] = 0;
        q_text(2, 32 + i * 4, s);
    }
    q_text(21, 32, "FRAME GUARD OK");
    q_text(23, 32, "SEARCHING");
    q_draw_board();
}

void q_show_pass(void)
{
    q_text(19, 32, "SOLUTION FOUND");
    q_text(20, 32, "8/8 QUEENS");
    q_text(21, 32, "FRAME GUARD OK");
    q_text(22, 32, "MAX DEP 8");
    q_text(23, 32, "PASS");
}

int main(int argc, char **argv)
{
    q_fast = 0;
    if (argc > 1 && strcmp(argv[1], "--verify") == 0)
        q_fast = 1;
    q_init_model();
    q_init_screen();
    if (!q_validate()) {
        q_inv_fail++;
        q_fail("INIT MODEL");
        return 1;
    }
    if (!q_place(0, 1)) {
        if (!q_failed)
            q_fail("NO SOLUTION");
        return 1;
    }
    if (!q_check_final()) {
        q_inv_fail++;
        q_fail("FINAL FAIL");
        return 1;
    }
    q_show_pass();
    if (!q_fast)
        sleep(100u);
    return 0;
}
