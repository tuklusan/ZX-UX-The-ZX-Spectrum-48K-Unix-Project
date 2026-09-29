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
    print_at(0, 7, "FIREWORK NIGHT / PARTICLES");
}

void burst(int cx, int cy, int t, int col)
{
    int i;
    int a;
    int sp;
    int x1;
    int y1;
    int x2;
    int y2;
    if (t < 1 || t > 27) return;
    ink(col);
    bright(t < 15);
    for (i = 0; i < 24; i++) {
        a = i * 11;
        sp = 2 + (i & 3);
        x2 = cx + d_cos(a) * sp * t / 128;
        y2 = cy + d_sin(a) * sp * t / 128;
        y2 = y2 - t * t / 18;
        x1 = cx + d_cos(a) * sp * (t - 2) / 128;
        y1 = cy + d_sin(a) * sp * (t - 2) / 128;
        y1 = y1 - (t - 2) * (t - 2) / 18;
        if (d_ok(x1, y1) && d_ok(x2, y2) &&
            y1 >= 16 && y1 < 184 &&
            y2 >= 16 && y2 < 184) {
            draw(x1, y1, x2, y2);
        }
    }
}

void sky(void)
{
    int x;
    ink(1);
    bright(0);
    for (x = 0; x < 256; x = x + 16) {
        draw(x, 16, x, 18 + ((x * 7) % 30));
        draw(x, 18 + ((x * 7) % 30),
             x + 14, 18 + ((x * 7) % 30));
    }
}

void scene(int f)
{
    int t1;
    int t2;
    int t3;
    paper(0);
    clear_demo_rows(1, 23);
    sky();
    t1 = f % 32;
    t2 = (f + 21) % 32;
    t3 = (f + 11) % 32;
    burst(70, 118, t1, 2);
    burst(132, 142, t2, 6);
    burst(196, 110, t3, 5);
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
