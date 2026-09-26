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

char r_map[241] =
    "####################"
    "#....#.............#"
    "#....#..$..........#"
    "#....#######.......#"
    "#..................#"
    "#..$....######.....#"
    "#........#.........#"
    "#.######.#.######..#"
    "#........#.....$...#"
    "#........#####.....#"
    "#................>.#"
    "####################";
int r_mx[3] = {12, 16, 5};
int r_my[3] = {1, 4, 9};
int r_alive[3] = {1, 1, 1};
int r_x;
int r_y;
int r_hp;
int r_gold;
int r_turns;

int r_at(int x, int y)
{
    return y * 20 + x;
}

int r_mon(int x, int y)
{
    int i;
    for (i = 0; i < 3; i++) {
        if (r_alive[i] && r_mx[i] == x && r_my[i] == y)
            return i;
    }
    return -1;
}

void r_board(void)
{
    int x;
    int y;
    int i;
    cls();
    print_at(0, 0, "C48 ROGUE - w a s d, q quits");
    for (y = 0; y < 12; y++) {
        for (x = 0; x < 20; x++)
            game_putc(y + 3, x + 4, r_map[r_at(x, y)]);
    }
    for (i = 0; i < 3; i++) {
        if (r_alive[i])
            game_putc(r_my[i] + 3, r_mx[i] + 4, 'g');
    }
    game_putc(r_y + 3, r_x + 4, '@');
    print_at(19, 0, "Collect 3 gold, then reach >.");
}

void r_status(void)
{
    print_at(17, 0, "HP:     Gold:     ");
    game_num(17, 4, (unsigned int)r_hp);
    game_num(17, 18, (unsigned int)r_gold);
}

void r_mmove(void)
{
    int i;
    int d;
    int nx;
    int ny;
    int j;
    for (i = 0; i < 3; i++) {
        if (!r_alive[i])
            continue;
        d = game_rand(4);
        nx = r_mx[i];
        ny = r_my[i];
        if (d == 0)
            nx++;
        if (d == 1)
            nx--;
        if (d == 2)
            ny++;
        if (d == 3)
            ny--;
        if (r_map[r_at(nx, ny)] != '.')
            continue;
        if (nx == r_x && ny == r_y) {
            r_hp--;
            continue;
        }
        j = r_mon(nx, ny);
        if (j < 0) {
            game_putc(r_my[i] + 3, r_mx[i] + 4,
                r_map[r_at(r_mx[i], r_my[i])]);
            r_mx[i] = nx;
            r_my[i] = ny;
            game_putc(r_my[i] + 3, r_mx[i] + 4, 'g');
        }
    }
}

int main(void)
{
    int key;
    int nx;
    int ny;
    int mon;
    int cell;
    r_x = 1;
    r_y = 1;
    r_hp = 12;
    r_gold = 0;
    r_turns = 0;
    r_board();
    while (1) {
        r_status();
        if (r_hp <= 0) {
            print_at(21, 0, "The dungeon wins. Press q.");
            while (game_key() != 'q')
                r_turns++;
            return 0;
        }
        cell = r_map[r_at(r_x, r_y)];
        if (cell == '>' && r_gold == 3) {
            print_at(21, 0, "You escape rich. Press q.");
            while (game_key() != 'q')
                r_turns++;
            return 0;
        }
        key = game_key();
        r_turns++;
        if (key == 'q')
            return 0;
        nx = r_x;
        ny = r_y;
        if (key == 'w')
            ny--;
        if (key == 's')
            ny++;
        if (key == 'a')
            nx--;
        if (key == 'd')
            nx++;
        if (r_map[r_at(nx, ny)] == '#')
            continue;
        game_putc(r_y + 3, r_x + 4,
            r_map[r_at(r_x, r_y)]);
        mon = r_mon(nx, ny);
        if (mon >= 0)
            r_alive[mon] = 0;
        r_x = nx;
        r_y = ny;
        cell = r_at(r_x, r_y);
        if (r_map[cell] == '$') {
            r_gold++;
            r_map[cell] = '.';
        }
        game_putc(r_y + 3, r_x + 4, '@');
        r_mmove();
        game_putc(r_y + 3, r_x + 4, '@');
    }
}
