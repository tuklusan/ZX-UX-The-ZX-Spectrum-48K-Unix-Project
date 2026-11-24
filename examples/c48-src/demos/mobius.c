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

void view_line3(int x1, int y1, int z1,
                int x2, int y2, int z2)
{
    int a;
    int b;
    int c;
    int d;
    a = d_px(x1, z1);
    b = d_py(y1, z1);
    c = d_px(x2, z2);
    d = d_py(y2, z2);
    if (d_ok(a, b) && d_ok(c, d) &&
        b >= 16 && b < 184 && d >= 16 && d < 184)
        draw(a, b, c, d);
}

void draw_labels(void)
{
    paper(0);
    ink(7);
    bright(1);
    over(0);
    inverse(0);
    print_at(0, 3, "MOBIUS R=48 W=24 / ONE-SIDED");
    print_at(22, 0, "MATH: r=48+12s*cos(u/2)");
    print_at(23, 0, "half-twist, then rotate3");
}

void mpt(int u, int side, int f,
         int *x, int *y, int *z)
{
    int rr;
    int a;
    int b;
    int c;
    rr = 48 + side * 12 * d_cos(u / 2) / 128;
    a = rr * d_cos(u) / 128;
    c = rr * d_sin(u) / 128;
    b = side * 10 * d_sin(u / 2) / 128;
    d_rot3(a, b, c, 20 + f * 2, f * 4, f,
           x, y, z);
    *x = *x * 3 / 2;
    *y = *y * 3 / 2;
}

void edge(int u1, int u2, int side, int f)
{
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    mpt(u1, side, f, &x1, &y1, &z1);
    mpt(u2, side, f, &x2, &y2, &z2);
    view_line3(x1, y1, z1, x2, y2, z2);
}

void scene(int f)
{
    int i;
    int u1;
    int u2;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    paper(0);
    clear_demo_rows(1, 21);
    border(2 + (f % 6));
    for (i = 0; i < 20; i++) {
        u1 = i * 256 / 20;
        u2 = (i + 1) * 256 / 20;
        ink(2 + (i % 6));
        bright(i & 1);
        edge(u1, u2, -1, f);
        edge(u1, u2, 1, f);
        mpt(u1, -1, f, &x1, &y1, &z1);
        mpt(u1, 1, f, &x2, &y2, &z2);
        view_line3(x1, y1, z1, x2, y2, z2);
    }
}

int main(int argc, char **argv)
{
    int f;
    int n;
    paper(0);
    cls();
    draw_labels();
    n = d_frames(argc, argv, 48);
    for (f = 0; f < n; f++) {
        scene(f);
        if (f + 1 < n) d_scene_break();
        yield();
    }
    return 0;
}
