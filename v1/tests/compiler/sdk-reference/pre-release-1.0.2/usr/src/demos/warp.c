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
    print_at(0, 6, "WARP DRIVE / STAR STREAKS");
}

int wx[40];
int wy[40];
int wz[40];

void init(void)
{
    int i;
    d_seed = 53921u;
    for (i = 0; i < 40; i++) {
        wx[i] = d_rng(161) - 80;
        wy[i] = d_rng(121) - 60;
        wz[i] = 20 + d_rng(160);
    }
}

void scene(int f)
{
    int i;
    int z1;
    int z2;
    int x1;
    int y1;
    int x2;
    int y2;
    int sp;
    paper(0);
    clear_demo_rows(1, 23);
    border(1 + (f % 7));
    sp = 2 + (f % 3);
    for (i = 0; i < 40; i++) {
        z1 = wz[i];
        z2 = z1 - sp;
        if (z2 < 10) {
            wx[i] = d_rng(181) - 90;
            wy[i] = d_rng(141) - 70;
            z2 = 175;
            z1 = 181;
        }
        x1 = 128 + wx[i] * 120 / z1;
        y1 = 96 + wy[i] * 120 / z1;
        x2 = 128 + wx[i] * 120 / z2;
        y2 = 96 + wy[i] * 120 / z2;
        ink(1 + ((z2 >> 4) % 7));
        bright(z2 < 70);
        if (d_ok(x1, y1) && d_ok(x2, y2) &&
            y1 >= 16 && y1 < 184 &&
            y2 >= 16 && y2 < 184) {
            draw(x1, y1, x2, y2);
        }
        wz[i] = z2;
    }
}

int main(int argc, char **argv)
{
    int f;
    int n;
    init();
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
