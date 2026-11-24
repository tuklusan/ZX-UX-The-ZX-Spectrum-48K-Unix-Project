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

void view_plot(int x, int y)
{
    if (d_ok(x, y) && y >= 16 && y < 184) plot(x, y);
}

void view_circle(int cx, int cy, int r)
{
    int x;
    int y;
    int err;
    x = r;
    y = 0;
    err = 1 - r;
    while (x >= y) {
        view_plot(cx + x, cy + y);
        view_plot(cx + y, cy + x);
        view_plot(cx - y, cy + x);
        view_plot(cx - x, cy + y);
        view_plot(cx - x, cy - y);
        view_plot(cx - y, cy - x);
        view_plot(cx + y, cy - x);
        view_plot(cx + x, cy - y);
        y++;
        if (err < 0) err = err + 2 * y + 1;
        else {
            x--;
            err = err + 2 * (y - x + 1);
        }
    }
}

void draw_labels(void)
{
    paper(0);
    ink(7);
    bright(1);
    over(0);
    inverse(0);
    print_at(0, 7, "MOIRE ENGINE / XOR INTERFERENCE");
    print_at(22, 0, "MATH: XOR circles C1(r),C2(r)");
    print_at(23, 0, "centers move with sin/cos");
}

void scene(int f)
{
    int r;
    int x1;
    int y1;
    int x2;
    int y2;
    paper(0);
    clear_demo_rows(1, 21);
    over(1);
    x1 = 96 + d_sin(f * 7) / 5;
    y1 = 96 + d_cos(f * 5) / 8;
    x2 = 160 + d_cos(f * 6) / 5;
    y2 = 96 + d_sin(f * 4) / 8;
    for (r = 8; r <= 80; r = r + 6) {
        ink(1 + ((r >> 2) % 7));
        bright(r & 8);
        view_circle(x1, y1, r);
        ink(1 + (((r >> 2) + 3) % 7));
        view_circle(x2, y2, r);
    }
    over(0);
    ink(7);
    bright(1);
    draw(x1, y1, x2, y2);
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
