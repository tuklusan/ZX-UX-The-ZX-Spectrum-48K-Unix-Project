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
    print_at(0, 5, "TORUS REACTOR / PARAMETRIC 3D");
    print_at(22, 0, "MATH: r=36+13*cos(v)");
    print_at(23, 0, "p=(r*cos u,13*sin v,r*sin u)");
}

void tpt(int u, int v, int f, int *x, int *y, int *z)
{
    int rr;
    int a;
    int b;
    int c;
    rr = 36 + 13 * d_cos(v) / 128;
    a = rr * d_cos(u) / 128;
    b = 13 * d_sin(v) / 128;
    c = rr * d_sin(u) / 128;
    d_rot3(a, b, c, 18 + f * 3, f * 5, f * 2,
           x, y, z);
    *x = *x * 2;
    *y = *y * 2;
}

void scene(int f)
{
    int u;
    int v;
    int u2;
    int v2;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    paper(0);
    clear_demo_rows(1, 21);
    border(1 + (f % 7));
    for (v = 0; v < 8; v++) {
        ink(1 + v % 7);
        bright(v & 1);
        for (u = 0; u < 16; u++) {
            u2 = (u + 1) & 15;
            tpt(u * 16, v * 32, f, &x1, &y1, &z1);
            tpt(u2 * 16, v * 32, f, &x2, &y2, &z2);
            view_line3(x1, y1, z1, x2, y2, z2);
        }
    }
    ink(7);
    bright(1);
    for (u = 0; u < 16; u = u + 2) {
        for (v = 0; v < 8; v++) {
            v2 = (v + 1) & 7;
            tpt(u * 16, v * 32, f, &x1, &y1, &z1);
            tpt(u * 16, v2 * 32, f, &x2, &y2, &z2);
            view_line3(x1, y1, z1, x2, y2, z2);
        }
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
