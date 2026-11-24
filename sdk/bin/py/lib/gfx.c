/* =====================================================================
 * ZX-UX 48K Sinclair ZX Spectrum Unix.
 * Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
 * Non-commercial use only under the repository LICENSE.
 * Commercial use prohibited without separate written permission.
 * ===================================================================== */
/* rcc runtime: DRAW and CIRCLE in C48 (C48 SDK reference semantics).
 * __pixel(x, y) sets one on-screen pixel with OVER/INVERSE and colour. */
int __pixel(int x, int y);

int draw(int x1, int y1, int x2, int y2)
{
    int dx;
    int dy;
    int sx;
    int sy;
    int err;
    int e2;
    if (x1 < 0 || x1 > 255 || x2 < 0 || x2 > 255 || y1 < 0 || y1 > 191 || y2 < 0 || y2 > 191)
        return 1;
    dx = x2 - x1;
    sx = 1;
    if (dx < 0) {
        dx = -dx;
        sx = -1;
    }
    dy = y2 - y1;
    sy = 1;
    if (dy < 0) {
        dy = -dy;
        sy = -1;
    }
    dy = -dy;
    err = dx + dy;
    while (1) {
        __pixel(x1, y1);
        if (x1 == x2 && y1 == y2)
            break;
        e2 = err + err;
        if (e2 >= dy) {
            err = err + dy;
            x1 = x1 + sx;
        }
        if (e2 <= dx) {
            err = err + dx;
            y1 = y1 + sy;
        }
    }
    return 0;
}

static void __c8(int cx, int cy, int x, int y)
{
    int px;
    int py;
    px = cx + x;
    py = cy + y;
    if (px >= 0 && px < 256 && py >= 0 && py < 192)
        __pixel(px, py);
}

int circle(int cx, int cy, int r)
{
    int x;
    int y;
    int err;
    if (cx < 0 || cx > 255 || cy < 0 || cy > 191 || r < 0 || r > 255)
        return 1;
    if (r == 0) {
        __pixel(cx, cy);
        return 0;
    }
    x = r;
    y = 0;
    err = 1 - r;
    while (x >= y) {
        __c8(cx, cy, x, y);
        __c8(cx, cy, y, x);
        __c8(cx, cy, -y, x);
        __c8(cx, cy, -x, y);
        __c8(cx, cy, -x, -y);
        __c8(cx, cy, -y, -x);
        __c8(cx, cy, y, -x);
        __c8(cx, cy, x, -y);
        y++;
        if (err < 0)
            err = err + 2 * y + 1;
        else {
            x--;
            err = err + 2 * (y - x + 1);
        }
    }
    return 0;
}
