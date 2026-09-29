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
    print_at(0, 8, "24X21 / 3X3 UDG WALKER");
    print_at(22, 10, "THREE ORIGINAL ANIMATION FRAMES");
}

unsigned char robot_tiles[216] = {
    0,0,0,0,0,0,0,3,28,8,255,128,
    162,128,255,255,0,0,128,128,128,128,128,224,
    2,6,10,18,18,35,32,0,0,127,0,73,
    0,255,127,65,32,48,40,36,36,226,2,0,
    0,0,0,0,3,0,0,0,65,65,65,193,
    0,0,0,0,0,0,0,128,96,0,0,0,
    0,0,0,0,0,0,0,3,28,8,255,128,
    162,128,255,255,0,0,128,128,128,128,128,224,
    2,6,10,18,18,35,32,0,0,127,0,73,
    0,255,127,65,32,48,40,36,36,226,2,0,
    0,0,1,3,12,0,0,0,129,128,0,0,
    0,0,0,0,0,128,128,192,48,0,0,0,
    0,0,0,0,0,0,0,3,28,8,255,128,
    162,128,255,255,0,0,128,128,128,128,128,224,
    2,6,10,18,18,35,32,0,0,127,0,73,
    0,255,127,65,32,48,40,36,36,226,2,0,
    0,0,0,1,6,0,0,0,64,128,128,128,
    0,0,0,0,128,128,64,96,24,0,0,0
};

void robot_setup(void)
{
    int i;
    for (i = 0; i < 27; i++)
        udg_define(i, robot_tiles + i * 8);
}

void robot_draw(int frame, int row, int col)
{
    int r;
    int c;
    int base;
    base = frame * 9;
    for (r = 0; r < 3; r++) {
        for (c = 0; c < 3; c++)
            udg_draw(base + r * 3 + c, row + r, col + c);
    }
}

void robot_scene(int f)
{
    int i;
    int col;
    paper(0);
    clear_demo_rows(1, 21);
    bright(0);
    ink(1);
    for (i = 0; i < 28; i++)
        plot((i * 37 + f * 5) & 255, 18 + (i * 53) % 146);
    col = 2 + (f % 24);
    ink(6);
    bright(1);
    robot_draw(f % 3, 9, col);
}

int main(int argc, char **argv)
{
    int f;
    int n;
    robot_setup();
    paper(0);
    cls();
    draw_labels();
    n = d_frames(argc, argv, 36);
    for (f = 0; f < n; f++) {
        robot_scene(f);
        yield();
        sleep(3u);
    }
    return 0;
}
