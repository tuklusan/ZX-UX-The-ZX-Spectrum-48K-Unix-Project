// ============================================================
// Copyright (c) 2026 SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and model
// training prohibited unless separately authorized.
//
// Attribution required: SANYALnet Labs.
// See root LICENSE for full terms.
// ============================================================
#include "appapi.h"

char sh_cells[640];
char sh_loadbuf[644];
int sh_row;
int sh_col;

char *sh_cell(int row, int col)
{
    return sh_cells + (row * 4 + col) * 20;
}

void sh_set(int row, int col, char *text)
{
    char *p;
    int i;
    p = sh_cell(row, col);
    i = 0;
    while (text[i] != 0 && i < 19) {
        p[i] = text[i];
        i++;
    }
    p[i] = 0;
    i++;
    while (i < 20) {
        p[i] = 0;
        i++;
    }
}

unsigned int sh_uint(char *s)
{
    unsigned int v;
    int i;
    v = 0u;
    i = 0;
    while (s[i] >= '0' && s[i] <= '9') {
        v = v * 10u + (unsigned int)(s[i] - '0');
        i++;
    }
    return v;
}

int sh_colno(int c)
{
    if (c >= 'A' && c <= 'D')
        return c - 'A';
    if (c >= 'a' && c <= 'd')
        return c - 'a';
    return -1;
}

unsigned int sh_value(int row, int col, int depth);

unsigned int sh_ref(char *s, int *used, int depth)
{
    int col;
    int row;
    col = sh_colno(s[0]);
    if (col < 0 || s[1] < '1' || s[1] > '8') {
        *used = 0;
        return 0u;
    }
    if (s[2] >= '0' && s[2] <= '9') {
        *used = 0;
        return 0u;
    }
    row = s[1] - '1';
    *used = 2;
    return sh_value(row, col, depth + 1);
}

unsigned int sh_formula(char *s, int depth)
{
    unsigned int a;
    unsigned int b;
    unsigned int total;
    int used;
    int used2;
    int r1;
    int r2;
    int c;
    int c2;
    int i;
    if (depth > 6)
        return 0u;
    if (s[1] == 'S' && s[2] == 'U' && s[3] == 'M' &&
        s[4] == '(') {
        c = sh_colno(s[5]);
        c2 = sh_colno(s[8]);
        if (c < 0 || c2 != c || s[6] < '1' || s[6] > '8')
            return 0u;
        if (s[7] != ':' || s[9] < '1' || s[9] > '8')
            return 0u;
        if (s[10] != ')' || s[11] != 0)
            return 0u;
        r1 = s[6] - '0';
        r2 = s[9] - '0';
        if (r1 > r2)
            return 0u;
        total = 0u;
        for (i = r1; i <= r2; i++)
            total = total + sh_value(i - 1, c, depth + 1);
        return total;
    }
    a = sh_ref(s + 1, &used, depth);
    if (used == 0)
        return 0u;
    i = 1 + used;
    if (s[i] != '+' && s[i] != '-' &&
        s[i] != '*' && s[i] != '/')
        return 0u;
    b = sh_ref(s + i + 1, &used2, depth);
    if (used2 == 0 || s[i + 1 + used2] != 0)
        return 0u;
    if (s[i] == '+')
        return a + b;
    if (s[i] == '-')
        return a - b;
    if (s[i] == '*')
        return a * b;
    if (b != 0u)
        return a / b;
    return 0u;
}

unsigned int sh_value(int row, int col, int depth)
{
    char *p;
    if (row < 0 || row > 7 || col < 0 || col > 3)
        return 0u;
    p = sh_cell(row, col);
    if (p[0] == '=')
        return sh_formula(p, depth);
    return sh_uint(p);
}

void sh_new(void)
{
    if (!app_confirm_new()) {
        app_notice_set("NEW CANCELLED");
        return;
    }
    memset(sh_cells, 0, 640u);
    sh_row = 0;
    sh_col = 0;
    app_notice_set("NEW BLANK SHEET");
}

void sh_seed(void)
{
    sh_set(0, 0, "IBM");
    sh_set(0, 1, "9000");
    sh_set(0, 2, "18");
    sh_set(0, 3, "BLUE CHIP");
    sh_set(1, 0, "GE");
    sh_set(1, 1, "8000");
    sh_set(1, 2, "16");
    sh_set(1, 3, "INDUSTRIAL");
    sh_set(2, 0, "KO");
    sh_set(2, 1, "7000");
    sh_set(2, 2, "14");
    sh_set(2, 3, "CONSUMER");
    sh_set(3, 0, "XON");
    sh_set(3, 1, "8000");
    sh_set(3, 2, "16");
    sh_set(3, 3, "ENERGY");
    sh_set(4, 0, "MSFT");
    sh_set(4, 1, "9000");
    sh_set(4, 2, "18");
    sh_set(4, 3, "SOFTWARE");
    sh_set(5, 0, "WMT");
    sh_set(5, 1, "6000");
    sh_set(5, 2, "12");
    sh_set(5, 3, "RETAIL");
    sh_set(6, 0, "CASH");
    sh_set(6, 1, "3000");
    sh_set(6, 2, "6");
    sh_set(6, 3, "RESERVE");
    sh_set(7, 0, "TOTAL");
    sh_set(7, 1, "=SUM(B1:B7)");
    sh_set(7, 2, "100");
    sh_set(7, 3, "1992 SAMPLE");
}

/* A fixed-width local file: SH48 header and 32 x 20-byte cells. */
void sh_save(void)
{
    int i;
    if (!app_choose_file("SAVE>"))
        return;
    sh_loadbuf[0] = 'S';
    sh_loadbuf[1] = 'H';
    sh_loadbuf[2] = '4';
    sh_loadbuf[3] = '8';
    for (i = 0; i < 640; i++)
        sh_loadbuf[i + 4] = sh_cells[i];
    if (app_save_file(sh_loadbuf, 644u))
        app_notice_set("SAVED TO RAM FILE");
    else
        app_notice_set("SAVE FAILED");
}

void sh_load(void)
{
    int n;
    int i;
    int j;
    int ended;
    if (!app_choose_file("LOAD>"))
        return;
    n = app_load_file(sh_loadbuf, 644u);
    if (n != 644 || sh_loadbuf[0] != 'S' ||
        sh_loadbuf[1] != 'H' || sh_loadbuf[2] != '4' ||
        sh_loadbuf[3] != '8') {
        app_notice_set("LOAD FAILED OR INVALID FILE");
        return;
    }
    for (i = 0; i < 32; i++) {
        ended = 0;
        for (j = 0; j < 20; j++) {
            n = (unsigned char)sh_loadbuf[4 + i * 20 + j];
            if (n == 0)
                ended = 1;
            else if (n < 32 || n > 126 || ended) {
                app_notice_set("INVALID SHEET FILE");
                return;
            }
        }
        if (!ended) {
            app_notice_set("INVALID SHEET FILE");
            return;
        }
    }
    for (i = 0; i < 640; i++)
        sh_cells[i] = sh_loadbuf[i + 4];
    app_notice_set("LOADED FROM RAM FILE");
}

void sh_field(int row, int col, int width,
              int sr, int sc)
{
    char buf[20];
    char *p;
    unsigned int v;
    int selected;
    p = sh_cell(sr, sc);
    selected = sh_row == sr && sh_col == sc;
    if (sc == 1) {
        v = sh_value(sr, sc, 0);
        app_money_text(buf, v);
        app_field(row, col, buf, width, selected);
    } else if (sc == 2) {
        app_uint_text(buf, sh_uint(p));
        app_putc(row, col + width - 1, '%');
        app_field(row, col, buf, width - 1, selected);
    } else {
        app_field(row, col, p, width, selected);
    }
}

void sh_formula_bar(void)
{
    char label[5];
    char *p;
    app_clear_row(23);
    label[0] = (char)('A' + sh_col);
    label[1] = (char)('1' + sh_row);
    label[2] = ':';
    label[3] = ' ';
    label[4] = 0;
    print_at(23, 0, label);
    p = sh_cell(sh_row, sh_col);
    print_at(23, 4, p);
}

void sh_render(void)
{
    int r;
    cls();
    paper(0);
    ink(7);
    bright(1);
    print_at(0, 8, "SHEET48 - 1992 HOME BROKERAGE");
    bright(0);
    print_at(1, 3, "SAMPLE ALLOCATION - DEMO DOLLARS");
    print_at(3, 4, "A TICKER");
    print_at(3, 16, "B VALUE");
    print_at(3, 29, "C TARGET");
    print_at(3, 40, "D NOTE");
    for (r = 0; r < 8; r++) {
        app_putc(r + 4, 1, '1' + r);
        sh_field(r + 4, 4, 10, r, 0);
        sh_field(r + 4, 15, 12, r, 1);
        sh_field(r + 4, 28, 9, r, 2);
        sh_field(r + 4, 38, 20, r, 3);
    }
    print_at(15, 3, "1992 PERIOD TICKERS: XON WAS EXXON");
    print_at(21, 1, "5/8 LR 7/6 UD E EDIT N NEW S SAVE L LOAD Q QUIT");
    print_at(22, 1, "FORMULAS: =A1+B1 OR =SUM(B1:B7)");
    sh_formula_bar();
    if (app_notice[0] != 0)
        print_at(20, 1, app_notice);
    yield();
}

void sh_edit(void)
{
    char temp[20];
    char label[8];
    int ok;
    app_clear_row(23);
    label[0] = 'E';
    label[1] = 'D';
    label[2] = 'I';
    label[3] = 'T';
    label[4] = ' ';
    label[5] = (char)('A' + sh_col);
    label[6] = (char)('1' + sh_row);
    label[7] = 0;
    print_at(23, 0, label);
    print_at(23, 8, "> ");
    ok = app_readline(23, 10, temp, 20);
    if (ok)
        sh_set(sh_row, sh_col, temp);
}

int main(int argc, char **argv)
{
    int key;
    sh_row = 0;
    sh_col = 0;
    sh_seed();
    app_setfile("/tmp/sheet48.sh48");
    sh_render();
    if (argc > 1 && strcmp(argv[1], "verify") == 0)
        return 0;
    while (1) {
        key = app_key();
        if (key == 'q')
            return 0;
        if (key == '5' && sh_col > 0)
            sh_col--;
        if (key == '8' && sh_col < 3)
            sh_col++;
        if (key == '7' && sh_row > 0)
            sh_row--;
        if (key == '6' && sh_row < 7)
            sh_row++;
        if (key == 'e')
            sh_edit();
        if (key == 'n')
            sh_new();
        if (key == 's')
            sh_save();
        if (key == 'l')
            sh_load();
        sh_render();
    }
}
