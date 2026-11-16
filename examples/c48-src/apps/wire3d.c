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
#include "appapi.h"

int w_tab[65] = {
    0, 3, 6, 9, 13, 16, 19, 22, 25, 28, 31, 34, 37,
    40, 43, 46, 49, 52, 55, 58, 60, 63, 66, 68, 71,
    74, 76, 79, 81, 84, 86, 88, 91, 93, 95, 97, 99,
    101, 103, 105, 106, 108, 110, 111, 113, 114, 116,
    117, 118, 119, 121, 122, 122, 123, 124, 125, 126,
    126, 127, 127, 127, 128, 128, 128, 128
};

int w_z[7];
int w_w[7];
int w_h[7];
int w_sel;
int w_yaw;
int w_pitch;
int w_zoom;
char w_filebuf[54];

int w_sin(int a)
{
    int q;
    int n;
    a = a & 255;
    q = a >> 6;
    n = a & 63;
    if (q == 0) return w_tab[n];
    if (q == 1) return w_tab[64 - n];
    if (q == 2) return -w_tab[n];
    return -w_tab[64 - n];
}

int w_cos(int a)
{
    return w_sin(a + 64);
}

int w_muldiv(int value, int scale, int div)
{
    int neg;
    int n;
    int chunk;
    int rem;
    int out;
    int prod;
    if (div <= 0 || scale < 0)
        return 0;
    neg = 0;
    if (value < 0) {
        neg = 1;
        n = -value;
    } else {
        n = value;
    }
    rem = 0;
    out = 0;
    while (n > 0) {
        chunk = n;
        if (chunk > 16)
            chunk = 16;
        prod = chunk * scale + rem;
        out = out + prod / div;
        rem = prod % div;
        n = n - chunk;
    }
    if (neg)
        return -out;
    return out;
}

void w_reset(void)
{
    w_z[0] = -88;
    w_z[1] = -68;
    w_z[2] = -42;
    w_z[3] = -10;
    w_z[4] = 24;
    w_z[5] = 56;
    w_z[6] = 84;
    w_w[0] = 2;
    w_w[1] = 24;
    w_w[2] = 48;
    w_w[3] = 70;
    w_w[4] = 62;
    w_w[5] = 38;
    w_w[6] = 8;
    w_h[0] = 2;
    w_h[1] = 6;
    w_h[2] = 10;
    w_h[3] = 14;
    w_h[4] = 12;
    w_h[5] = 8;
    w_h[6] = 3;
    w_sel = 3;
    w_yaw = 8;
    w_pitch = 7;
    w_zoom = 270;
}

/* An empty model retains the editable seven-plane positions and
   uses zero width/height for unused planes. Zero dimensions persist
   through the existing 54-byte file format. */
void w_new(void)
{
    int i;
    if (!app_confirm_new()) {
        app_notice_set("NEW CANCELLED");
        return;
    }
    w_reset();
    for (i = 0; i < 7; i++) {
        w_w[i] = 0;
        w_h[i] = 0;
    }
    app_notice_set("NEW EMPTY MODEL");
}

int w_has_shape(void)
{
    int i;
    for (i = 0; i < 7; i++)
        if (w_w[i] > 0 && w_h[i] > 0)
            return 1;
    return 0;
}

/* Versioned 54-byte local model: 4-byte tag and 25 signed 16-bit words. */
void w_store16(int pos, int value)
{
    w_filebuf[pos] = (char)(value & 255);
    w_filebuf[pos + 1] = (char)((value >> 8) & 255);
}

int w_load16(int pos)
{
    unsigned int value;
    value = (unsigned int)(unsigned char)w_filebuf[pos];
    value = value | ((unsigned int)(unsigned char)w_filebuf[pos + 1] << 8);
    return (int)value;
}

void w_save(void)
{
    int i;
    if (!app_choose_file("SAVE>"))
        return;
    w_filebuf[0] = 'W';
    w_filebuf[1] = '3';
    w_filebuf[2] = 'D';
    w_filebuf[3] = '1';
    for (i = 0; i < 7; i++) {
        w_store16(4 + i * 6, w_z[i]);
        w_store16(6 + i * 6, w_w[i]);
        w_store16(8 + i * 6, w_h[i]);
    }
    w_store16(46, w_sel);
    w_store16(48, w_yaw);
    w_store16(50, w_pitch);
    w_store16(52, w_zoom);
    if (app_save_file(w_filebuf, 54u))
        app_notice_set("SAVED TO RAM FILE");
    else
        app_notice_set("SAVE FAILED");
}

void w_load(void)
{
    int n;
    int i;
    if (!app_choose_file("LOAD>"))
        return;
    n = app_load_file(w_filebuf, 54u);
    if (n != 54 || w_filebuf[0] != 'W' ||
        w_filebuf[1] != '3' || w_filebuf[2] != 'D' ||
        w_filebuf[3] != '1') {
        app_notice_set("LOAD FAILED OR INVALID FILE");
        return;
    }
    for (i = 0; i < 7; i++) {
        if (w_load16(4 + i * 6) < -110 ||
            w_load16(4 + i * 6) > 110 ||
            w_load16(6 + i * 6) < 0 ||
            w_load16(6 + i * 6) > 78 ||
            w_load16(8 + i * 6) < 0 ||
            w_load16(8 + i * 6) > 30) {
            app_notice_set("INVALID MODEL VALUES");
            return;
        }
    }
    if (w_load16(46) < 0 || w_load16(46) > 6 ||
        w_load16(52) < 150 || w_load16(52) > 360) {
        app_notice_set("INVALID MODEL VALUES");
        return;
    }
    for (i = 0; i < 7; i++) {
        w_z[i] = w_load16(4 + i * 6);
        w_w[i] = w_load16(6 + i * 6);
        w_h[i] = w_load16(8 + i * 6);
    }
    w_sel = w_load16(46);
    w_yaw = w_load16(48);
    w_pitch = w_load16(50);
    w_zoom = w_load16(52);
    app_notice_set("LOADED FROM RAM FILE");
}

void w_rot(int x, int y, int z,
           int *ox, int *oy, int *oz)
{
    int sy;
    int cy;
    int sx;
    int cx;
    int u;
    int v;
    int w;
    sy = w_sin(w_yaw);
    cy = w_cos(w_yaw);
    sx = w_sin(w_pitch);
    cx = w_cos(w_pitch);
    u = (x * cy + z * sy) / 128;
    w = (z * cy - x * sy) / 128;
    v = (y * cx - w * sx) / 128;
    w = (y * sx + w * cx) / 128;
    *ox = u;
    *oy = v;
    *oz = w;
}

int w_project(int x, int y, int z, int *sx, int *sy)
{
    int q;
    w_rot(x, y, z, &x, &y, &z);
    q = z + 190;
    if (q < 30)
        return 0;
    *sx = 128 + w_muldiv(x, w_zoom, q);
    *sy = 100 + w_muldiv(y, w_zoom, q);
    if (*sx < 0 || *sx > 255)
        return 0;
    if (*sy < 32 || *sy > 176)
        return 0;
    return 1;
}

void w_line(int x1, int y1, int z1,
            int x2, int y2, int z2)
{
    int a;
    int b;
    int c;
    int d;
    if (!w_project(x1, y1, z1, &a, &b))
        return;
    if (!w_project(x2, y2, z2, &c, &d))
        return;
    draw(a, b, c, d);
}

int w_gproj(int x, int y, int z, int *sx, int *sy)
{
    if (z < 1)
        return 0;
    *sx = 128 + x * 100 / z;
    *sy = 105 + y * 100 / z;
    if (*sx < 0 || *sx > 255)
        return 0;
    if (*sy < 0 || *sy > 159)
        return 0;
    return 1;
}

void w_gline(int x1, int y1, int z1,
             int x2, int y2, int z2)
{
    int a;
    int b;
    int c;
    int d;
    if (!w_gproj(x1, y1, z1, &a, &b))
        return;
    if (!w_gproj(x2, y2, z2, &c, &d))
        return;
    draw(a, b, c, d);
}

void w_grid(void)
{
    int x;
    int z;
    ink(5);
    bright(0);
    for (x = -60; x <= 60; x = x + 12)
        w_gline(x, -45, 60, x, -45, 240);
    for (z = 60; z <= 240; z = z + 18)
        w_gline(-70, -45, z, 70, -45, z);
}

void w_plane_point(int p, int n,
                   int *x, int *y, int *z)
{
    *z = w_z[p];
    if (n == 0) {
        *x = 0;
        *y = w_h[p];
    }
    if (n == 1) {
        *x = w_w[p];
        *y = 0;
    }
    if (n == 2) {
        *x = 0;
        *y = -w_h[p];
    }
    if (n == 3) {
        *x = -w_w[p];
        *y = 0;
    }
}

void w_draw_plane(int p)
{
    int n;
    int m;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    if (w_w[p] == 0 || w_h[p] == 0)
        return;
    for (n = 0; n < 4; n++) {
        m = (n + 1) & 3;
        w_plane_point(p, n, &x1, &y1, &z1);
        w_plane_point(p, m, &x2, &y2, &z2);
        w_line(x1, y1, z1, x2, y2, z2);
    }
}

void w_draw_hull(void)
{
    int p;
    int n;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    ink(6);
    bright(1);
    for (p = 0; p < 7; p++)
        w_draw_plane(p);
    for (p = 0; p < 6; p++) {
        if (w_w[p] == 0 || w_h[p] == 0 ||
            w_w[p + 1] == 0 || w_h[p + 1] == 0)
            continue;
        for (n = 0; n < 4; n++) {
            w_plane_point(p, n, &x1, &y1, &z1);
            w_plane_point(p + 1, n, &x2, &y2, &z2);
            w_line(x1, y1, z1, x2, y2, z2);
        }
    }
}

void w_draw_tower(void)
{
    ink(7);
    bright(1);
    w_line(-12, 14, -8, 12, 14, -8);
    w_line(12, 14, -8, 12, 14, 28);
    w_line(12, 14, 28, -12, 14, 28);
    w_line(-12, 14, 28, -12, 14, -8);
    w_line(-8, 29, 2, 8, 29, 2);
    w_line(8, 29, 2, 8, 29, 22);
    w_line(8, 29, 22, -8, 29, 22);
    w_line(-8, 29, 22, -8, 29, 2);
    w_line(-12, 14, -8, -8, 29, 2);
    w_line(12, 14, -8, 8, 29, 2);
    w_line(12, 14, 28, 8, 29, 22);
    w_line(-12, 14, 28, -8, 29, 22);
}

void w_status(void)
{
    char num[8];
    app_clear_row(20);
    app_clear_row(21);
    app_clear_row(22);
    app_clear_row(23);
    print_at(20, 1, "PLANE ");
    app_uint_text(num, (unsigned int)(w_sel + 1));
    print_at(20, 7, num);
    print_at(20, 12, "Z=");
    app_int_text(num, w_z[w_sel]);
    print_at(20, 14, num);
    print_at(20, 24, "W=");
    app_uint_text(num, (unsigned int)w_w[w_sel]);
    print_at(20, 26, num);
    print_at(20, 34, "H=");
    app_uint_text(num, (unsigned int)w_h[w_sel]);
    print_at(20, 36, num);
    print_at(21, 1, "B/P PLANE  A/D WIDTH  E/W HT  Z/X DEPTH");
    print_at(22, 1, "5/8 YAW 7/6 PITCH +/- ZOOM N NEW R RESET S SAVE L LOAD Q Quit");
    if (app_notice[0] != 0)
        print_at(23, 1, app_notice);
    else
        print_at(23, 1, "MODEL: IMPERIAL BATTLESHIP AURELIAN");
}

void w_render(void)
{
    cls();
    paper(0);
    ink(7);
    bright(1);
    print_at(0, 8, "WIRE3D - IMPERIAL CRUISER");
    w_grid();
    if (w_has_shape())
        w_draw_hull();
    if (w_has_shape())
        w_draw_tower();
    ink(2);
    bright(1);
    w_draw_plane(w_sel);
    w_status();
    yield();
}

void w_edit(int key)
{
    if (key == 'b' && w_sel < 6)
        w_sel++;
    if (key == 'p' && w_sel > 0)
        w_sel--;
    if (key == 'a' && w_w[w_sel] > 2) {
        w_w[w_sel] = w_w[w_sel] - 2;
        if (w_w[w_sel] < 2)
            w_w[w_sel] = 2;
    }
    if (key == 'd' && w_w[w_sel] < 78) {
        w_w[w_sel] = w_w[w_sel] + 2;
        if (w_w[w_sel] > 78)
            w_w[w_sel] = 78;
    }
    if (key == 'e' && w_h[w_sel] > 2) {
        w_h[w_sel] = w_h[w_sel] - 2;
        if (w_h[w_sel] < 2)
            w_h[w_sel] = 2;
    }
    if (key == 'w' && w_h[w_sel] < 30) {
        w_h[w_sel] = w_h[w_sel] + 2;
        if (w_h[w_sel] > 30)
            w_h[w_sel] = 30;
    }
    if (key == 'z' && w_z[w_sel] > -110) {
        w_z[w_sel] = w_z[w_sel] - 3;
        if (w_z[w_sel] < -110)
            w_z[w_sel] = -110;
    }
    if (key == 'x' && w_z[w_sel] < 110) {
        w_z[w_sel] = w_z[w_sel] + 3;
        if (w_z[w_sel] > 110)
            w_z[w_sel] = 110;
    }
    if (key == '5')
        w_yaw = w_yaw - 6;
    if (key == '8')
        w_yaw = w_yaw + 6;
    if (key == '7')
        w_pitch = w_pitch - 5;
    if (key == '6')
        w_pitch = w_pitch + 5;
    if (key == '+' && w_zoom < 360) {
        w_zoom = w_zoom + 12;
        if (w_zoom > 360)
            w_zoom = 360;
    }
    if (key == '-' && w_zoom > 150) {
        w_zoom = w_zoom - 12;
        if (w_zoom < 150)
            w_zoom = 150;
    }
    if (key == 'n')
        w_new();
    if (key == 'r')
        w_reset();
    if (key == 's')
        w_save();
    if (key == 'l')
        w_load();
}

int main(int argc, char **argv)
{
    int key;
    w_reset();
    app_setfile("/tmp/wire3d.w3d");
    w_render();
    if (argc > 1 && strcmp(argv[1], "verify") == 0)
        return 0;
    while (1) {
        key = app_key();
        if (key == 'q')
            return 0;
        w_edit(key);
        w_render();
    }
}
