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
    print_at(0, 7, "JULIA BALLET / MOVING CONSTANT");
    print_at(22, 0, "MATH: z=z*z+c");
    print_at(23, 0, "c=(-22+sin(9f)/12,cos(7f)/9)");
}

void scene(int f)
{
    int x;
    int y;
    int i;
    int cr;
    int ci;
    int zx;
    int zy;
    int xx;
    int py;
    paper(0);
    clear_demo_rows(1, 21);
    cr = -22 + d_sin(f * 9) / 12;
    ci = d_cos(f * 7) / 9;
    for (y = 0; y < 48; y++) {
        py = 16 + y * 167 / 47;
        for (x = 0; x < 64; x++) {
            zx = (x - 32) * 3;
            zy = (y - 24) * 3;
            for (i = 0; i < 12; i++) {
                if (d_abs(zx) > 64) break;
                if (d_abs(zy) > 64) break;
                if (zx * zx + zy * zy > 4096) break;
                xx = (zx * zx - zy * zy) / 32 + cr;
                zy = 2 * zx * zy / 32 + ci;
                zx = xx;
            }
            ink((i + f) & 7);
            bright(i > 6);
            plot(x * 4, py);
            if (i > 8) plot(x * 4 + 1, py);
        }
        if ((y & 7) == 0) yield();
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
