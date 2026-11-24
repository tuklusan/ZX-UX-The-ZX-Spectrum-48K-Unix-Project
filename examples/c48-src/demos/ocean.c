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
    paper(1);
    ink(7);
    bright(1);
    over(0);
    inverse(0);
    print_at(0, 4, "OCEAN GRID / THREE WAVE FIELD");
    print_at(22, 0, "MATH: y=(sin(3x+7f)+");
    print_at(23, 0, "sin(2z-5f)+sin(x+z+3f))/18");
}

int wave(int x, int z, int f)
{
    int a;
    int b;
    int c;
    a = d_sin(x * 3 + f * 7);
    b = d_sin(z * 2 - f * 5);
    c = d_sin(x + z + f * 3);
    return (a + b + c) / 18;
}

void scene(int f)
{
    int r;
    int c;
    int x1;
    int x2;
    int z1;
    int z2;
    int y1;
    int y2;
    paper(1);
    clear_demo_rows(1, 21);
    border(1 + (f & 1) * 4);
    for (r = 0; r < 10; r++) {
        z1 = 18 + r * 18;
        ink(5 + (r & 1));
        bright(r < 6);
        for (c = 0; c < 10; c++) {
            x1 = -110 + c * 22;
            x2 = x1 + 22;
            y1 = wave(x1, z1, f);
            y2 = wave(x2, z1, f);
            view_line3(x1, y1, z1, x2, y2, z1);
        }
    }
    ink(5);
    for (c = 0; c < 11; c++) {
        x1 = -110 + c * 22;
        for (r = 0; r < 9; r++) {
            z1 = 18 + r * 18;
            z2 = z1 + 18;
            y1 = wave(x1, z1, f);
            y2 = wave(x1, z2, f);
            view_line3(x1, y1, z1, x1, y2, z2);
        }
    }
    ink(7);
    bright(1);
    circle(54, 148, 10);
}

int main(int argc, char **argv)
{
    int f;
    int n;
    paper(1);
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
