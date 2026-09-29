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

void view_dot(int x, int y)
{
    if (d_ok(x, y) && y >= 16 && y < 184) plot(x, y);
}

void draw_labels(void)
{
    paper(0);
    ink(7);
    bright(1);
    over(0);
    inverse(0);
    print_at(0, 6, "SPIRAL GALAXY / FOUR ARMS");
    print_at(22, 0, "MATH: a=64*arm+11*(i/4)+3f");
    print_at(23, 0, "r=5+2*(i mod 24)");
}

void scene(int f)
{
    int i;
    int arm;
    int r;
    int a;
    int x;
    int y;
    int z;
    int px;
    int py;
    paper(0);
    clear_demo_rows(1, 21);
    border(1 + (f % 7));
    for (i = 0; i < 96; i++) {
        arm = i & 3;
        r = 5 + (i % 24) * 2;
        a = arm * 64 + (i >> 2) * 11 + f * 3;
        x = r * d_cos(a) / 128;
        z = r * d_sin(a) / 128;
        y = d_sin(i * 29 + f * 2) * (i % 7) / 50;
        d_rot3(x, y, z, 22, f * 2, 0, &x, &y, &z);
        x = x * 2;
        y = y * 2;
        px = d_px(x, z);
        py = d_py(y, z);
        ink(1 + (i % 7));
        bright(r < 22);
        view_dot(px, py);
        if (r < 18) view_dot(px + 1, py);
    }
    ink(7);
    bright(1);
    circle(128, 96, 5);
    circle(128, 96, 9);
}

int main(int argc, char **argv)
{
    int f;
    int n;
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
