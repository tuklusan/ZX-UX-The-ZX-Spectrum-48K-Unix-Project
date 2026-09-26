// ============================================================
// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and AI/ML
// model training prohibited unless separately authorized.
//
// Attribution required: Based on original work by Supratim
// Sanyal of SANYALnet Labs. See root LICENSE for full terms.
// ============================================================
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

void t_draw(void)
{
    int enemy;
    cls();
    print_at(0, 0, "C48 TREK");
    print_at(2, 0, "w warp, p phaser, t torpedo");
    print_at(3, 0, "s scan, q quit");
    print_at(5, 0, "Quadrant:");
    game_num(5, 10, (unsigned int)t_quad);
    print_at(6, 0, "Energy:");
    game_num(6, 10, (unsigned int)t_energy);
    print_at(7, 0, "Shields:");
    game_num(7, 10, (unsigned int)t_shield);
    print_at(8, 0, "Torpedoes:");
    game_num(8, 11, (unsigned int)t_torps);
    print_at(9, 0, "Enemies:");
    game_num(9, 10, (unsigned int)t_left());
    enemy = t_here();
    if (enemy >= 0)
        print_at(12, 0, "KLINGON CONTACT!");
    if (t_left() == 0 && t_quad == 0)
        print_at(14, 0, "Mission complete. Press q.");
    print_at(17, 0, "Command:");
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

void t_warp(void)
{
    int key;
    int x;
    int y;
    print_at(19, 0, "Direction w a s d:");
    key = game_key();
    x = t_quad % 4;
    y = t_quad / 4;
    if (key == 'w' && y > 0)
        y--;
    if (key == 's' && y < 3)
        y++;
    if (key == 'a' && x > 0)
        x--;
    if (key == 'd' && x < 3)
        x++;
    t_quad = y * 4 + x;
    t_energy = t_energy - 50;
}

int main(void)
{
    int key;
    int enemy;
    t_quad = 0;
    t_energy = 3000;
    t_shield = 500;
    t_torps = 5;
    t_turns = 0;
    while (1) {
        t_draw();
        if (t_energy <= 0) {
            print_at(20, 0, "Ship destroyed. Press q.");
            while (game_key() != 'q')
                t_turns++;
            return 0;
        }
        key = game_key();
        t_turns++;
        if (key == 'q')
            return 0;
        if (t_left() == 0 && t_quad == 0) {
            if (key == 'q')
                return 0;
            continue;
        }
        enemy = t_here();
        if (key == 'w')
            t_warp();
        if (key == 'p' && enemy >= 0) {
            t_energy = t_energy - 250;
            if (game_rand(100) < 80)
                t_alive[enemy] = 0;
        }
        if (key == 't' && enemy >= 0 && t_torps > 0) {
            t_torps--;
            if (game_rand(100) < 90)
                t_alive[enemy] = 0;
        }
        if (key == 's')
            t_energy = t_energy - 10;
        t_attack();
    }
}
