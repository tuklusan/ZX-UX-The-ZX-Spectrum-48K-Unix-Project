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
    print_at(0, 4, "POLYHEDRON MORPH / CUBE TO STAR");
    print_at(22, 0, "MATH: p=((64-ph)cube+ph*star)/64");
    print_at(23, 0, "then rotate3");
}

int vx[8] = {-28, 28, 28, -28, -28, 28, 28, -28};
int vy[8] = {-28, -28, 28, 28, -28, -28, 28, 28};
int vz[8] = {-28, -28, -28, -28, 28, 28, 28, 28};
int tx[8] = {-8, 40, 8, -40, -8, 40, 8, -40};
int ty[8] = {-40, -8, 40, 8, -40, -8, 40, 8};
int tz[8] = {-8, -40, -8, 40, 8, 40, 8, -40};
int ea[12] = {0,1,2,3,4,5,6,7,0,1,2,3};
int eb[12] = {1,2,3,0,5,6,7,4,4,5,6,7};

void shp(int sc, int ph, int f)
{
    int i;
    int a;
    int b;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    int p;
    int q;
    for (i = 0; i < 12; i++) {
        a = ea[i];
        b = eb[i];
        p = vx[a] * (64 - ph) + tx[a] * ph;
        q = vy[a] * (64 - ph) + ty[a] * ph;
        x1 = p / 64 * sc / 3;
        y1 = q / 64 * sc / 3;
        z1 = (vz[a] * (64 - ph) + tz[a] * ph) / 64;
        z1 = z1 * sc / 3;
        p = vx[b] * (64 - ph) + tx[b] * ph;
        q = vy[b] * (64 - ph) + ty[b] * ph;
        x2 = p / 64 * sc / 3;
        y2 = q / 64 * sc / 3;
        z2 = (vz[b] * (64 - ph) + tz[b] * ph) / 64;
        z2 = z2 * sc / 3;
        d_rot3(x1, y1, z1, f * 3, f * 5, f,
               &x1, &y1, &z1);
        d_rot3(x2, y2, z2, f * 3, f * 5, f,
               &x2, &y2, &z2);
        view_line3(x1, y1, z1, x2, y2, z2);
    }
}

void scene(int f)
{
    int ph;
    ph = (f * 8) & 127;
    if (ph > 64) ph = 128 - ph;
    paper(0);
    clear_demo_rows(1, 21);
    ink(5);
    bright(0);
    shp(3, ph, f);
    ink(6);
    bright(1);
    shp(4, ph, f);
    ink(7);
    shp(5, ph, f);
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
