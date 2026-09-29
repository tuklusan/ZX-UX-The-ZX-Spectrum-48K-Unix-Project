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
    print_at(0, 7, "FRACTAL FOREST / RECURSIVE WIND");
}

void branch(int x, int y, int len, int ang, int dep)
{
    int nx;
    int ny;
    if (dep <= 0 || len < 3) return;
    nx = x + d_cos(ang) * len / 128;
    ny = y + d_sin(ang) * len / 128;
    if (!d_ok(nx, ny)) return;
    ink(2 + (dep & 3));
    bright(dep < 3);
    draw(x, y, nx, ny);
    if (dep == 1) {
        ink(4 + ((x + y) & 1));
        circle(nx, ny, 2);
        return;
    }
    branch(nx, ny, len * 3 / 4, ang + 18, dep - 1);
    branch(nx, ny, len * 3 / 4, ang - 22, dep - 1);
}

void scene(int f)
{
    int i;
    int x;
    int sway;
    paper(0);
    clear_demo_rows(1, 23);
    ink(2);
    bright(0);
    draw(0, 18, 255, 18);
    for (i = 0; i < 4; i++) {
        x = 38 + i * 60;
        sway = d_sin(f * 6 + i * 31) / 18;
        branch(x, 18, 32 + (i & 1) * 6,
               64 + sway, 6);
    }
    ink(6);
    bright(1);
    circle(214, 156, 11);
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
