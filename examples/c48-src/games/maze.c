// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "gameapi.h"

char *m_map[12] = {
    "####################",
    "#S...#..............#",
    "###.#.#.#############",
    "#...#.#.............#",
    "#.###.###########.#.#",
    "#.....#.........#.#.#",
    "#.#####.#######.#.#.#",
    "#.......#.....#...#.#",
    "#########.###.#####.#",
    "#.........#.........#",
    "#.#################E#",
    "####################"
};
int maze_turns;
int maze_x;
int maze_y;

void maze_cell(int y, int x, int ch)
{
    int col;
    col = 2 + x * 3;
    game_putc(y + 3, col, ch);
    game_putc(y + 3, col + 1, ch);
    game_putc(y + 3, col + 2, ch);
}

void maze_draw(void)
{
    int x;
    int y;
    cls();
    print_at(0, 0, "C48 MAZE - w a s d, q quits");
    print_at(1, 0, "Find E. Walls are solid. @ is you.");
    for (y = 0; y < 12; y++) {
        for (x = 0; x < 20; x++)
            maze_cell(y, x, m_map[y][x]);
    }
    maze_cell(maze_y, maze_x, '@');
    print_at(16, 0, "Move:");
    game_show_last(18);
    print_at(21, 0, "S=start   E=exit   ###=wall");
}

void maze_status(void)
{
    game_show_last(18);
    game_putc(16, 6, ' ');
}

int main(void)
{
    int key;
    int nx;
    int ny;
    int oldx;
    int oldy;
    maze_x = 1;
    maze_y = 1;
    maze_turns = 0;
    maze_draw();
    while (1) {
        if (m_map[maze_y][maze_x] == 'E') {
            print_at(20, 0, "You escaped. Press q.");
            while (game_key() != 'q')
                maze_turns++;
            return 0;
        }
        key = game_key_echo(16, 6);
        maze_turns++;
        if (key == 'q')
            return 0;
        nx = maze_x;
        ny = maze_y;
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
            maze_status();
            continue;
        }
        if (m_map[ny][nx] == '#') {
            game_record(key, 2);
            maze_status();
            continue;
        }
        oldx = maze_x;
        oldy = maze_y;
        maze_x = nx;
        maze_y = ny;
        game_record(key, 1);
        maze_cell(oldy, oldx, m_map[oldy][oldx]);
        maze_cell(maze_y, maze_x, '@');
        maze_status();
    }
}
