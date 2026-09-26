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

int s_x[120];
int s_y[120];
int s_len;
int s_fx;
int s_fy;
int s_dx;
int s_dy;
int s_score;
int s_turns;

int s_hit(int x, int y, int count)
{
    int i;
    for (i = 0; i < count; i++) {
        if (s_x[i] == x && s_y[i] == y)
            return 1;
    }
    return 0;
}

void s_food(void)
{
    do {
        s_fx = game_rand(18) + 1;
        s_fy = game_rand(10) + 1;
    } while (s_hit(s_fx, s_fy, s_len));
}

void s_draw(void)
{
    int x;
    int y;
    int i;
    cls();
    print_at(0, 0, "C48 SNAKE - w a s d, q quits");
    for (x = 0; x < 20; x++) {
        game_putc(3, x + 4, '#');
        game_putc(14, x + 4, '#');
    }
    for (y = 1; y < 11; y++) {
        game_putc(y + 3, 4, '#');
        game_putc(y + 3, 23, '#');
    }
    game_putc(s_fy + 3, s_fx + 4, '*');
    for (i = s_len - 1; i > 0; i--)
        game_putc(s_y[i] + 3, s_x[i] + 4, 'o');
    game_putc(s_y[0] + 3, s_x[0] + 4, '@');
    print_at(17, 0, "Score:");
    game_num(17, 7, (unsigned int)s_score);
}

int main(void)
{
    int key;
    int nx;
    int ny;
    int eat;
    int body;
    int i;
    s_len = 4;
    s_x[0] = 8;
    s_x[1] = 7;
    s_x[2] = 6;
    s_x[3] = 5;
    s_y[0] = 6;
    s_y[1] = 6;
    s_y[2] = 6;
    s_y[3] = 6;
    s_dx = 1;
    s_dy = 0;
    s_score = 0;
    s_turns = 0;
    s_food();
    while (1) {
        s_draw();
        key = game_key();
        s_turns++;
        if (key == 'q')
            return 0;
        if (key == 'w' && s_dy != 1) {
            s_dx = 0;
            s_dy = -1;
        }
        if (key == 's' && s_dy != -1) {
            s_dx = 0;
            s_dy = 1;
        }
        if (key == 'a' && s_dx != 1) {
            s_dx = -1;
            s_dy = 0;
        }
        if (key == 'd' && s_dx != -1) {
            s_dx = 1;
            s_dy = 0;
        }
        nx = s_x[0] + s_dx;
        ny = s_y[0] + s_dy;
        eat = nx == s_fx && ny == s_fy;
        body = s_len;
        if (!eat)
            body--;
        if (nx <= 0 || nx >= 19 || ny <= 0 || ny >= 11)
            break;
        if (s_hit(nx, ny, body))
            break;
        if (eat) {
            for (i = s_len; i > 0; i--) {
                s_x[i] = s_x[i - 1];
                s_y[i] = s_y[i - 1];
            }
            s_len++;
            s_score++;
        }
        else {
            for (i = s_len - 1; i > 0; i--) {
                s_x[i] = s_x[i - 1];
                s_y[i] = s_y[i - 1];
            }
        }
        s_x[0] = nx;
        s_y[0] = ny;
        if (eat)
            s_food();
        if (s_score == 20) {
            cls();
            print_at(8, 8, "Snake master. Press q.");
            while (game_key() != 'q')
                s_turns++;
            return 0;
        }
    }
    cls();
    print_at(8, 8, "Game over. Press q.");
    while (game_key() != 'q')
        s_turns++;
    return 0;
}
