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
/* Shared helpers for the graphics demonstrations. */
int cls(void);
int plot(int x, int y);
int draw(int x1, int y1, int x2, int y2);
int circle(int x, int y, int r);
int ink(int c);
int paper(int c);
int bright(int on);
int over(int on);
int inverse(int on);
int border(int c);
int print_at(int row, int col, char *text);
int udg_define(int slot, unsigned char *data);
int udg_draw(int slot, int row, int col);
int udg_draw_2x2(int base, int row, int col);
int yield(void);
int sleep(unsigned int ticks);
int beep(float duration, float pitch);

int d_tab[65] = {
    0, 3, 6, 9, 13, 16, 19, 22, 25, 28, 31, 34, 37,
    40, 43, 46, 49, 52, 55, 58, 60, 63, 66, 68, 71,
    74, 76, 79, 81, 84, 86, 88, 91, 93, 95, 97, 99,
    101, 103, 105, 106, 108, 110, 111, 113, 114, 116,
    117, 118, 119, 121, 122, 122, 123, 124, 125, 126,
    126, 127, 127, 127, 128, 128, 128, 128
};

unsigned int d_seed = 44257u;

int d_sin(int a)
{
    int q;
    int n;
    a = a & 255;
    q = a >> 6;
    n = a & 63;
    if (q == 0) return d_tab[n];
    if (q == 1) return d_tab[64 - n];
    if (q == 2) return -d_tab[n];
    return -d_tab[64 - n];
}

int d_cos(int a)
{
    return d_sin(a + 64);
}

int d_abs(int x)
{
    if (x < 0) return -x;
    return x;
}

int d_rng(int lim)
{
    unsigned int v;
    if (lim <= 1) return 0;
    d_seed = d_seed * 25173u + 13849u;
    d_seed = d_seed & 65535u;
    v = d_seed % (unsigned int)lim;
    return (int)v;
}

int d_num(char *s)
{
    int n;
    int c;
    n = 0;
    while (*s != 0) {
        c = *s;
        if (c < '0' || c > '9') return 0;
        n = n * 10 + c - '0';
        s++;
    }
    return n;
}

int d_frames(int argc, char **argv, int defv)
{
    int n;
    if (argc < 2) return defv;
    n = d_num(argv[1]);
    if (n < 1) n = 1;
    if (n > 240) n = 240;
    return n;
}

void d_scene_break(void)
{
    int rc;
    rc = beep(0.25, 0.0);
    if (rc != 0) return;
    rc = beep(0.25, 4.0);
    if (rc != 0) return;
    rc = beep(0.25, 7.0);
    if (rc != 0) return;
    rc = beep(0.25, 12.0);
    if (rc != 0) return;
    rc = beep(0.25, 9.0);
    if (rc != 0) return;
    rc = beep(0.25, 7.0);
    if (rc != 0) return;
    rc = beep(0.25, 4.0);
    if (rc != 0) return;
    beep(0.25, 0.0);
}

int d_muldiv(int value, int scale, int div)
{
    int p;
    int whole;
    int rem;
    int n;
    int q;
    int acc;
    int mask;
    int out;
    if (div <= 0 || scale != 220) return 0;
    if (value >= -2978 && value <= 2978 &&
        div <= 1638) {
        p = value * 11;
        whole = p / div;
        rem = p % div;
        if (whole >= -1637 && whole <= 1637)
            return whole * 20 + rem * 20 / div;
    }
    whole = value / div;
    rem = value % div;
    if (whole > 148 || whole < -148) return 0;
    if (rem < 0) n = -rem;
    else n = rem;
    q = 0;
    acc = 0;
    mask = 128;
    while (mask != 0) {
        q = q * 2;
        if (acc >= div - acc) {
            acc = acc - (div - acc);
            q = q + 1;
        }
        else
            acc = acc + acc;
        if ((scale & mask) != 0) {
            if (acc >= div - n) {
                acc = acc - (div - n);
                q = q + 1;
            }
            else
                acc = acc + n;
        }
        mask = mask >> 1;
    }
    if (rem < 0) q = -q;
    out = whole * scale;
    if (out > 0 && q > 32767 - out) return 0;
    if (out < 0 && q < -32767 - 1 - out) return 0;
    return out + q;
}

int d_px(int x, int z)
{
    int q;
    q = z + 176;
    if (q < 32) q = 32;
    return 128 + d_muldiv(x, 220, q);
}

int d_py(int y, int z)
{
    int q;
    q = z + 176;
    if (q < 32) q = 32;
    return 96 + d_muldiv(y, 220, q);
}

int d_ok(int x, int y)
{
    return x >= 0 && x < 256 && y >= 0 && y < 192;
}

void d_line3(int x1, int y1, int z1,
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
    if (d_ok(a, b) && d_ok(c, d)) draw(a, b, c, d);
}

void d_rot3(int x, int y, int z,
            int ax, int ay, int az,
            int *ox, int *oy, int *oz)
{
    int sx;
    int cx;
    int sy;
    int cy;
    int sz;
    int cz;
    int u;
    int v;
    int w;
    int t;
    sx = d_sin(ax);
    cx = d_cos(ax);
    sy = d_sin(ay);
    cy = d_cos(ay);
    sz = d_sin(az);
    cz = d_cos(az);
    u = (x * cy + z * sy) / 128;
    w = (z * cy - x * sy) / 128;
    v = (y * cx - w * sx) / 128;
    t = (y * sx + w * cx) / 128;
    x = (u * cz - v * sz) / 128;
    y = (u * sz + v * cz) / 128;
    *ox = x;
    *oy = y;
    *oz = t;
}

void d_dot(int x, int y)
{
    if (d_ok(x, y)) plot(x, y);
}
