// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
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

void r_cell(int y, int x, int ch)
{
    int col;
    col = 2 + x * 3;
    game_putc(y + 3, col, ch);
    game_putc(y + 3, col + 1, ch);
    game_putc(y + 3, col + 2, ch);
}

void r_board(void)
{
    int x;
    int y;
    int i;
    cls();
    print_at(0, 0, "C48 ROGUE - w a s d, q quits");
    print_at(1, 0, "Collect all gold, then reach >.");
    for (y = 0; y < 12; y++) {
        for (x = 0; x < 20; x++)
            r_cell(y, x, r_map[r_at(x, y)]);
    }
    for (i = 0; i < 3; i++) {
        if (r_alive[i])
            r_cell(r_my[i], r_mx[i], 'g');
    }
    r_cell(r_y, r_x, '@');
}

void r_status(void)
{
    print_at(16, 0, "HP:     Gold:     ");
    game_num(16, 4, (unsigned int)r_hp);
    game_num(16, 18, (unsigned int)r_gold);
    game_show_last(18);
    print_at(22, 0, "Command:");
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
            r_cell(r_my[i], r_mx[i],
                   r_map[r_at(r_mx[i], r_my[i])]);
            r_mx[i] = nx;
            r_my[i] = ny;
            r_cell(r_my[i], r_mx[i], 'g');
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
            print_at(20, 0, "The dungeon wins. Press q.");
            while (game_key() != 'q')
                r_turns++;
            return 0;
        }
        cell = r_map[r_at(r_x, r_y)];
        if (cell == '>' && r_gold == 3) {
            print_at(20, 0, "You escape rich. Press q.");
            while (game_key() != 'q')
                r_turns++;
            return 0;
        }
        key = game_key_echo(22, 9);
        r_turns++;
        if (key == 'q')
            return 0;
        nx = r_x;
        ny = r_y;
        if (key == 'w')
            ny--;
        else if (key == 's')
            ny++;
        else if (key == 'a')
            nx--;
        else if (key == 'd')
            nx++;
        else {
            game_record(key, 3);
            continue;
        }
        if (r_map[r_at(nx, ny)] == '#') {
            game_record(key, 2);
            continue;
        }
        r_cell(r_y, r_x, r_map[r_at(r_x, r_y)]);
        mon = r_mon(nx, ny);
        if (mon >= 0) {
            r_alive[mon] = 0;
            game_record(key, 4);
        }
        else
            game_record(key, 1);
        r_x = nx;
        r_y = ny;
        cell = r_at(r_x, r_y);
        if (r_map[cell] == '$') {
            r_gold++;
            r_map[cell] = '.';
        }
        r_cell(r_y, r_x, '@');
        r_mmove();
        r_cell(r_y, r_x, '@');
    }
}
