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
#include "demoapi.h"

void clear_demo_rows(int first, int last)
{
    int row;
    ink(0);
    bright(0);
    over(0);
    inverse(0);
    for (row = first; row <= last; row++) {
        print_at(row, 0, "                                ");
        print_at(row, 32, "                                ");
    }
}

void draw_labels(void)
{
    paper(0);
    ink(7);
    bright(1);
    over(0);
    inverse(0);
    print_at(0, 7, "SPECTRUM PLASMA / ATTRIBUTES");
    print_at(22, 0, "MATH: v=sin(13x+9f)+");
    print_at(23, 0, "sin(17y-6f)+sin(9(x+y)+4f)");
}

unsigned char p0[8] = {
    255,255,255,255,255,255,255,255
};
unsigned char p1[8] = {
    170,85,170,85,170,85,170,85
};
unsigned char p2[8] = {
    240,15,240,15,240,15,240,15
};
unsigned char p3[8] = {
    129,66,36,24,24,36,66,129
};

void setup(void)
{
    udg_define(0, p0);
    udg_define(1, p1);
    udg_define(2, p2);
    udg_define(3, p3);
}

void scene(int f)
{
    int x;
    int y;
    int v;
    int c;
    int s;
    paper(0);
    clear_demo_rows(2, 21);
    for (y = 2; y < 22; y++) {
        for (x = 0; x < 32; x++) {
            v = d_sin(x * 13 + f * 9);
            v = v + d_sin(y * 17 - f * 6);
            v = v + d_sin((x + y) * 9 + f * 4);
            c = (d_abs(v) >> 4) & 7;
            s = (d_abs(v) >> 5) & 3;
            ink(c);
            paper((c + 1 + (v < 0)) & 7);
            bright(d_abs(v) > 120);
            udg_draw(s, y, x);
        }
    }
}

int main(int argc, char **argv)
{
    int f;
    int n;
    setup();
    paper(0);
    cls();
    draw_labels();
    n = d_frames(argc, argv, 240);
    for (f = 0; f < n; f++) {
        scene(f);
        yield();
    }
    return 0;
}
