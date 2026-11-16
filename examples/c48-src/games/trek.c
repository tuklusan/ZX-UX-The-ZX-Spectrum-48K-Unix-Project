// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "gameapi.h"

int t_quad;
int t_energy;
int t_shield;
int t_torps;
int t_enemy[3] = {1, 6, 15};
int t_alive[3] = {1, 1, 1};
int t_turns;

int t_here(void)
{
    int i;
    for (i = 0; i < 3; i++) {
        if (t_alive[i] && t_enemy[i] == t_quad)
            return i;
    }
    return -1;
}

int t_left(void)
{
    int i;
    int count;
    count = 0;
    for (i = 0; i < 3; i++) {
        if (t_alive[i])
            count++;
    }
    return count;
}

void t_token(int row, int col, char *text)
{
    print_at(row, col, text);
}

void t_sector(void)
{
    int x;
    int y;
    int enemy;
    int ex;
    int ey;
    enemy = t_here();
    ex = 3 + (t_quad & 1);
    ey = 3 + ((t_quad >> 1) & 1);
    for (y = 0; y < 8; y++) {
        print_at(4 + y, 0, "|                       |");
        for (x = 0; x < 8; x++) {
            if (x == ex && y == ey)
                t_token(4 + y, 1 + x * 3, "<*>");
            else if (enemy >= 0 && x == 6 && y == 2)
                t_token(4 + y, 1 + x * 3, "+K+");
            else if (((x * 7 + y * 11 + t_quad) % 13) == 0)
                t_token(4 + y, 1 + x * 3, " * ");
            else
                t_token(4 + y, 1 + x * 3, " . ");
        }
    }
}

void t_draw(void)
{
    int enemy;
    cls();
    print_at(0, 10, "*** C48 STAR TREK ***");
    print_at(2, 0, "SHORT RANGE SENSOR SCAN");
    print_at(2, 35, "SHIP STATUS");
    print_at(3, 0, "+-----------------------+");
    t_sector();
    print_at(12, 0, "+-----------------------+");
    print_at(4, 35, "Quadrant:");
    game_num(4, 47, (unsigned int)t_quad);
    print_at(5, 35, "Energy:");
    game_num(5, 47, (unsigned int)t_energy);
    print_at(6, 35, "Shields:");
    game_num(6, 47, (unsigned int)t_shield);
    print_at(7, 35, "Torpedoes:");
    game_num(7, 47, (unsigned int)t_torps);
    print_at(8, 35, "Klingons:");
    game_num(8, 47, (unsigned int)t_left());
    enemy = t_here();
    if (enemy >= 0)
        print_at(10, 35, "CONDITION RED");
    else
        print_at(10, 35, "CONDITION GREEN");
    print_at(14, 0,
             "w=WARP  p=PHASER  t=TORPEDO  s=SCAN  q=QUIT");
    if (enemy >= 0)
        print_at(16, 0, "KLINGON CONTACT IN THIS QUADRANT!");
    if (t_left() == 0 && t_quad == 0)
        print_at(16, 0, "Mission complete. Press q.");
    game_show_last(19);
    print_at(22, 0, "COMMAND:");
}

void t_status(void)
{
    game_show_last(19);
    game_putc(22, 9, ' ');
    print_at(23, 0, "                                ");
}

void t_attack(void)
{
    int hit;
    if (t_here() < 0)
        return;
    hit = game_rand(81) + 40;
    if (t_shield >= hit)
        t_shield = t_shield - hit;
    else {
        hit = hit - t_shield;
        t_shield = 0;
        t_energy = t_energy - hit;
    }
}

int t_warp(void)
{
    int key;
    int x;
    int y;
    int nx;
    int ny;
    print_at(23, 0, "WARP COURSE w a s d:");
    key = game_key_echo(23, 21);
    x = t_quad % 4;
    y = t_quad / 4;
    nx = x;
    ny = y;
    if (key == 'w')
        ny--;
    else if (key == 's')
        ny++;
    else if (key == 'a')
        nx--;
    else if (key == 'd')
        nx++;
    else {
        game_record2('w', key, 3);
        return 0;
    }
    if (nx < 0 || nx > 3 || ny < 0 || ny > 3) {
        game_record2('w', key, 2);
        return 0;
    }
    t_quad = ny * 4 + nx;
    t_energy = t_energy - 50;
    game_record2('w', key, 1);
    return 1;
}

int main(void)
{
    int key;
    int enemy;
    int acted;
    t_quad = 0;
    t_energy = 3000;
    t_shield = 500;
    t_torps = 5;
    t_turns = 0;
    while (1) {
        t_draw();
        if (t_energy <= 0) {
            print_at(16, 0, "Ship destroyed. Press q.");
            while (game_key() != 'q')
                t_turns++;
            return 0;
        }
        while (1) {
            key = game_key_echo(22, 9);
            t_turns++;
            if (key == 'q')
                return 0;
            if (t_left() == 0 && t_quad == 0) {
                t_status();
                continue;
            }
            enemy = t_here();
            acted = 0;
            if (key == 'w') {
                acted = t_warp();
                if (!acted) {
                    t_status();
                    continue;
                }
            }
            else if (key == 'p') {
                if (enemy < 0) {
                    game_record(key, 2);
                    t_status();
                    continue;
                }
                t_energy = t_energy - 250;
                if (game_rand(100) < 80)
                    t_alive[enemy] = 0;
                game_record(key, 1);
                acted = 1;
            }
            else if (key == 't') {
                if (enemy < 0 || t_torps <= 0) {
                    game_record(key, 2);
                    t_status();
                    continue;
                }
                t_torps--;
                if (game_rand(100) < 90)
                    t_alive[enemy] = 0;
                game_record(key, 1);
                acted = 1;
            }
            else if (key == 's') {
                t_energy = t_energy - 10;
                game_record(key, 1);
                acted = 1;
            }
            else {
                game_record(key, 3);
                t_status();
                continue;
            }
            if (acted)
                t_attack();
            break;
        }
    }
}
