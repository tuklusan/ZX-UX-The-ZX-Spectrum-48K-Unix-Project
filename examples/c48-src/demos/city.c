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
    print_at(0, 3, "VECTOR METROPOLIS / NIGHT FLIGHT");
}

void bldg(int x, int z, int w, int h)
{
    int y0;
    int y1;
    int z2;
    y0 = -68;
    y1 = y0 + h;
    z2 = z + 22;
    d_line3(x, y0, z, x + w, y0, z);
    d_line3(x, y1, z, x + w, y1, z);
    d_line3(x, y0, z, x, y1, z);
    d_line3(x + w, y0, z, x + w, y1, z);
    d_line3(x, y0, z2, x + w, y0, z2);
    d_line3(x, y1, z2, x + w, y1, z2);
    d_line3(x, y0, z2, x, y1, z2);
    d_line3(x + w, y0, z2, x + w, y1, z2);
    d_line3(x, y0, z, x, y0, z2);
    d_line3(x + w, y0, z, x + w, y0, z2);
    d_line3(x, y1, z, x, y1, z2);
    d_line3(x + w, y1, z, x + w, y1, z2);
}

void scene(int f)
{
    int i;
    int z;
    int sh;
    int h;
    paper(0);
    clear_demo_rows(1, 23);
    border(1);
    sh = (f * 6) % 24;
    ink(4);
    bright(1);
    d_line3(-28, -68, 8, -28, -68, 210);
    d_line3(28, -68, 8, 28, -68, 210);
    d_line3(-104, -68, 8, 0, -68, 210);
    d_line3(104, -68, 8, 0, -68, 210);
    for (i = 0; i < 8; i++) {
        z = 24 + i * 24 - sh;
        if (z < 20) z = z + 192;
        h = 32 + ((i * 13 + f * 3) % 52);
        ink(1 + (i % 6));
        bright(i < 4);
        bldg(-106, z, 38, h);
        bldg(68, z + 8, 38, 28 + ((h * 3) % 54));
    }
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
