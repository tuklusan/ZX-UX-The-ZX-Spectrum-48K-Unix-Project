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
#include "exapi.h"

char *a_sample[15] = {
    "SANYALnet Labs ZX-UX: It is 1982 again but you are ",
    "running Unix on a ZX Spectrum! ",
    "https://supratim-sanyal.blogspot.com/ ",
    "The quick brown fox jumps over the lazy dog. ",
    "Sphinx of black quartz, judge my vow! ",
    "The five boxing wizards jump quickly. ",
    "Pack my box with five dozen liquor jugs. Lorem Ipsum. ",
    "Hamburgefontsiv. Waltz, bad nymph, for quick jigs vex. ",
    "Mr. Jock, TV quiz PhD, bags few lynx. ",
    "How vexingly quick daft zebras jump! ",
    "Two driven jocks help fax my big quiz. ",
    "My girl wove six dozen plaid jackets before she quit. ",
    "Sixty zippers were quickly picked from the woven ",
    "jute bag. A wizard's job is to vex chumps quickly ",
    "in fog. "
};

void a_style(int side)
{
    bright(1);
    if (side == 0) {
        paper(0);
        ink(7);
    }
    else {
        paper(7);
        ink(0);
    }
}

void a_put(int side, int row, int col, int ch)
{
    char s[2];
    s[0] = (char)ch;
    s[1] = 0;
    a_style(side);
    print_at(row, side * 32 + col, s);
}

void a_line(int side, int row, char *text)
{
    int col;
    col = 0;
    while (*text != 0 && col < 32) {
        a_put(side, row, col, *text);
        col++;
        text++;
    }
}

void a_background(int side)
{
    int row;
    a_style(side);
    for (row = 0; row < 24; row++)
        print_at(row, side * 32,
                 "                                ");
}

int a_argline(char *dst, char *arg)
{
    int n;
    n = 0;
    dst[n++] = 'a';
    dst[n++] = 'r';
    dst[n++] = 'g';
    dst[n++] = 'v';
    dst[n++] = '=';
    dst[n++] = '"';
    while (*arg != 0 && n < 62)
        dst[n++] = *arg++;
    dst[n++] = '"';
    dst[n] = 0;
    return n;
}

void a_charset(int side)
{
    char text[25];
    int line;
    int i;
    for (line = 0; line < 4; line++) {
        for (i = 0; i < 24; i++)
            text[i] = (char)(32 + line * 24 + i);
        text[24] = 0;
        a_line(side, 3 + line, text);
    }
}

void a_body(int side)
{
    int row;
    int col;
    int part;
    int pos;
    int ch;
    row = 7;
    col = 0;
    part = 0;
    pos = 0;
    while (row < 24) {
        ch = a_sample[part][pos];
        if (ch == 0) {
            part++;
            pos = 0;
            if (part == 15)
                part = 0;
            continue;
        }
        a_put(side, row, col, ch);
        pos++;
        col++;
        if (col == 32) {
            col = 0;
            row++;
        }
    }
}

void a_half(int side, char *arg, char *path)
{
    char line[64];
    int n;
    a_background(side);
    n = a_argline(line, arg);
    a_line(side, 0, line);
    if (n > 32) {
        a_line(side, 1, line + 32);
        a_line(side, 2, path);
    }
    else
        a_line(side, 1, path);
    a_charset(side);
    a_body(side);
}

int main(int argc, char **argv)
{
    char *arg;
    arg = "(none)";
    if (argc > 1)
        arg = argv[1];
    paper(0);
    ink(7);
    bright(1);
    cls();
    border(1);
    a_half(0, arg, argv[0]);
    a_half(1, arg, argv[0]);
    return 0;
}
