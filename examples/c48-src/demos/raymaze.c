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
    print_at(0, 6, "RAYCAST LABYRINTH / DDA VIEW");
}

unsigned char wm[256] = {
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,
1,0,1,1,1,1,0,1,1,1,1,1,1,1,0,1,
1,0,0,0,0,1,0,0,0,0,0,0,0,1,0,1,
1,1,1,1,0,1,0,1,1,1,1,0,0,1,0,1,
1,0,0,0,0,1,0,1,0,0,1,0,0,1,0,1,
1,0,1,1,1,1,0,1,0,0,1,0,0,1,0,1,
1,0,0,0,0,0,0,1,0,0,1,0,0,0,0,1,
1,0,1,1,1,1,1,1,0,0,1,1,1,1,0,1,
1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,
1,0,1,1,1,1,0,1,1,1,1,1,0,1,0,1,
1,0,1,0,0,0,0,1,0,0,0,0,0,1,0,1,
1,0,1,0,1,1,1,1,0,1,1,1,1,1,0,1,
1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,
1,0,0,1,1,1,1,1,1,1,1,1,0,0,0,1,
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
};

int wall(int x, int y)
{
    if (x < 0 || x > 255) return 1;
    if (y < 0 || y > 255) return 1;
    return wm[(y >> 4) * 16 + (x >> 4)];
}

void scene(int f)
{
    int c;
    int st;
    int a;
    int px;
    int py;
    int dx;
    int dy;
    int dist;
    int h;
    int top;
    int bot;
    int x;
    paper(0);
    clear_demo_rows(1, 23);
    draw(0, 96, 255, 96);
    for (c = 0; c < 64; c++) {
        a = 20 + f * 4 + c - 32;
        dx = d_cos(a);
        dy = d_sin(a);
        dist = 126;
        for (st = 4; st < 126; st = st + 3) {
            px = 72 + dx * st / 128;
            py = 72 + dy * st / 128;
            if (wall(px, py)) {
                dist = st;
                break;
            }
        }
        h = 1100 / dist;
        if (h > 174) h = 174;
        top = 96 - h / 2;
        bot = 96 + h / 2;
        x = c * 4 + 2;
        ink(1 + ((dist >> 3) % 7));
        bright(dist < 40);
        draw(x, top, x, bot);
        draw(x + 1, top, x + 1, bot);
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
