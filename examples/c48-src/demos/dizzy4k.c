/*
 * Dizzy 4K Intro - C48 port/reconstruction.
 * Original ZX Spectrum 4K intro by SerzhSoft, Funtop 1998.
 * Public tape archive:
 * https://bbb.retroscene.org/prods.php?py=16&y=1998
 *
 * This source is a C48 port of the original Dizzy 4K demo.
 * The original demo remains the work of SerzhSoft.
 */
#include "demoapi.h"

void blank_rows(int first, int last)
{
    int row;
    paper(0);
    ink(0);
    bright(0);
    over(0);
    inverse(0);
    for (row = first; row <= last; row++) {
        print_at(row, 0, "                                ");
        print_at(row, 32, "                                ");
    }
}

void caption(char *a, char *b)
{
    blank_rows(0, 23);
    paper(0);
    ink(7);
    bright(1);
    print_at(9, 8, a);
    if (*b != 0) print_at(11, 7, b);
}

void intro_text(int n)
{
    int f;
    caption("SerzhSoft", "presents");
    for (f = 0; f < n; f++) yield();
    caption("START A STORY...", "");
    for (f = 0; f < n; f++) yield();
    caption("In the beginning", "was only CHAOS!");
    for (f = 0; f < n; f++) yield();
}

void chaos_frame(int f)
{
    int i;
    int x1;
    int y1;
    int x2;
    int y2;
    paper(0);
    ink(7);
    bright(0);
    if ((f & 3) == 0) cls();
    for (i = 0; i < 28; i++) {
        x1 = d_rng(256);
        y1 = d_rng(176) + 8;
        x2 = x1 + d_rng(33) - 16;
        y2 = y1 + d_rng(25) - 12;
        ink(1 + d_rng(7));
        if (d_ok(x2, y2)) draw(x1, y1, x2, y2);
        else plot(x1, y1);
    }
}

void chaos_scene(int n)
{
    int f;
    caption("But this CHAOS", "going to PLASMA!");
    for (f = 0; f < n; f++) yield();
    cls();
    for (f = 0; f < n * 2; f++) {
        chaos_frame(f);
        yield();
    }
}

unsigned char p0[8] = {255,129,189,165,165,189,129,255};
unsigned char p1[8] = {170,85,170,85,170,85,170,85};
unsigned char p2[8] = {24,60,126,219,219,126,60,24};
unsigned char p3[8] = {129,66,36,24,24,36,66,129};

void plasma_setup(void)
{
    udg_define(0, p0);
    udg_define(1, p1);
    udg_define(2, p2);
    udg_define(3, p3);
}

void plasma_frame(int f)
{
    int x;
    int y;
    int v;
    int c;
    int s;
    for (y = 2; y < 22; y++) {
        for (x = 0; x < 32; x++) {
            v = d_sin(x * 13 + f * 9);
            v = v + d_sin(y * 17 - f * 6);
            v = v + d_sin((x + y) * 9 + f * 4);
            c = (d_abs(v) >> 4) & 7;
            s = (d_abs(v) >> 5) & 3;
            ink(c);
            paper((c + 1 + (v < 0)) & 7);
            bright(d_abs(v) > 120);
            udg_draw(s, y, x);
        }
    }
}

void plasma_scene(int n)
{
    int f;
    paper(0);
    cls();
    ink(7);
    bright(1);
    print_at(0, 7, "PLASMA divided..");
    for (f = 0; f < n * 2; f++) {
        plasma_frame(f);
        yield();
    }
    caption("From this PLASMA", "coming BIOZOIDS!");
    for (f = 0; f < n; f++) yield();
}

void biozoid(int x, int y, int r, int c)
{
    ink(c);
    bright(1);
    circle(x, y, r);
    circle(x, y, r / 2);
    plot(x, y);
}

void biozoid_scene(int n)
{
    int f;
    int i;
    int x;
    int y;
    int r;
    for (f = 0; f < n * 2; f++) {
        paper(0);
        cls();
        print_at(0, 10, "BIOZOIDS");
        for (i = 0; i < 9; i++) {
            x = 128 + d_sin(f * 9 + i * 28) *
                (35 + (i & 3) * 9) / 128;
            y = 96 + d_cos(f * 7 + i * 37) *
                (24 + (i & 1) * 18) / 128;
            r = 3 + ((i + f) & 7);
            biozoid(x, y, r, 1 + (i % 7));
        }
        yield();
    }
    caption("They made EGGS!", "");
    for (f = 0; f < n; f++) yield();
}

void egg(int x, int y, int r, int c)
{
    ink(c);
    bright(1);
    circle(x, y - r / 3, r);
    circle(x, y + r / 3, r - 2);
}

void eggs_scene(int n)
{
    int f;
    int i;
    int x;
    int y;
    int r;
    for (f = 0; f < n * 2; f++) {
        paper(0);
        cls();
        print_at(0, 11, "EGGS");
        for (i = 0; i < 7; i++) {
            x = 32 + i * 32 + d_sin(f * 8 + i * 31) / 10;
            y = 90 + d_cos(f * 6 + i * 39) / 5;
            r = 8 + ((i + f / 3) & 3);
            egg(x, y, r, 1 + ((i + f / 5) % 7));
        }
        yield();
    }
    caption("From this EGGS", "coming our HERO:YOU");
    for (f = 0; f < n; f++) yield();
}

void hero_frame(int f)
{
    int bob;
    int leg;
    bob = d_sin(f * 10) / 16;
    leg = d_sin(f * 18) / 12;
    paper(0);
    cls();
    ink(6);
    bright(1);
    circle(128, 86 + bob, 30);
    circle(128, 94 + bob, 27);
    ink(7);
    circle(118, 81 + bob, 5);
    circle(138, 81 + bob, 5);
    plot(118, 81 + bob);
    plot(138, 81 + bob);
    draw(117, 104 + bob, 139, 104 + bob);
    ink(2);
    draw(106, 108 + bob, 91, 125 + leg);
    draw(150, 108 + bob, 165, 125 - leg);
    draw(116, 120 + bob, 108 + leg, 151);
    draw(140, 120 + bob, 148 - leg, 151);
    ink(7);
    print_at(2, 11, "DIZZY 4K");
}

void hero_scene(int n)
{
    int f;
    for (f = 0; f < n * 3; f++) {
        hero_frame(f);
        yield();
    }
    caption("LOOK OUR NEW", "COOL MINI DEMO");
    for (f = 0; f < n; f++) yield();
    caption("FOR YOU", "DIZZY");
    for (f = 0; f < n; f++) yield();
    hero_frame(n);
    yield();
}

int main(int argc, char **argv)
{
    int n;
    paper(0);
    border(0);
    cls();
    plasma_setup();
    n = d_frames(argc, argv, 24);
    intro_text(n);
    chaos_scene(n);
    plasma_scene(n);
    biozoid_scene(n);
    eggs_scene(n);
    hero_scene(n);
    return 0;
}
