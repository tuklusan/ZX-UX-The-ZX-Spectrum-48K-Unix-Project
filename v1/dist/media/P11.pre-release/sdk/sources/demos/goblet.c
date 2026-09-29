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
    print_at(0, 2, "CRYSTAL GOBLET / 3D WIREFRAME");
    print_at(22, 0, "MATH: p=(r*cos a,y,r*sin a)");
    print_at(23, 0, "r,y come from profile table");
}

int gr[10] = {18, 28, 36, 40, 36, 16, 7, 7, 28, 32};
int gy[10] = {58, 48, 34, 16, 0, -20, -42, -58, -66, -70};

void gpt(int p, int a, int f, int *x, int *y, int *z)
{
    int u;
    int v;
    int w;
    u = gr[p] * d_cos(a) / 128;
    v = gy[p];
    w = gr[p] * d_sin(a) / 128;
    d_rot3(u, v, w, 10 + f * 2, f * 5, f, x, y, z);
    *x = *x * 2;
}

void scene(int f)
{
    int p;
    int j;
    int a1;
    int a2;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    paper(0);
    clear_demo_rows(1, 21);
    border(3 + (f & 1) * 4);
    ink(7);
    bright(1);
    for (p = 0; p < 10; p++) {
        for (j = 0; j < 12; j++) {
            a1 = j * 21;
            if (j == 11) a2 = 0;
            else a2 = (j + 1) * 21;
            gpt(p, a1, f, &x1, &y1, &z1);
            gpt(p, a2, f, &x2, &y2, &z2);
            view_line3(x1, y1, z1, x2, y2, z2);
        }
    }
    for (p = 0; p < 9; p++) {
        for (j = 0; j < 12; j++) {
            a1 = j * 21;
            gpt(p, a1, f, &x1, &y1, &z1);
            gpt(p + 1, a1, f, &x2, &y2, &z2);
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
