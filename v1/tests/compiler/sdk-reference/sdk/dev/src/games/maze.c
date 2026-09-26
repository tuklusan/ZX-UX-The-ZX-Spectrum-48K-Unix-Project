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

void maze_draw(void)
{
    int y;
    cls();
    print_at(0, 0, "C48 MAZE - w a s d, q quits");
    for (y = 0; y < 12; y++)
        print_at(y + 3, 4, m_map[y]);
    game_putc(maze_y + 3, maze_x + 4, '@');
}

int main(void)
{
    int key;
    int nx;
    int ny;
    maze_x = 1;
    maze_y = 1;
    maze_turns = 0;
    while (1) {
        maze_draw();
        if (m_map[maze_y][maze_x] == 'E') {
            print_at(18, 4, "You escaped. Press q.");
            while (game_key() != 'q')
                maze_turns++;
            return 0;
        }
        key = game_key();
        maze_turns++;
        if (key == 'q')
            return 0;
        nx = maze_x;
        ny = maze_y;
        if (key == 'w')
            ny--;
        if (key == 's')
            ny++;
        if (key == 'a')
            nx--;
        if (key == 'd')
            nx++;
        if (m_map[ny][nx] != '#') {
            maze_x = nx;
            maze_y = ny;
        }
    }
}
