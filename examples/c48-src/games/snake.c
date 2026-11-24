// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
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

void s_cell(int y, int x, int ch)
{
    int col;
    col = 2 + x * 3;
    game_putc(y + 3, col, ch);
    game_putc(y + 3, col + 1, ch);
    game_putc(y + 3, col + 2, ch);
}

void s_draw_board(void)
{
    int x;
    int y;
    int i;
    cls();
    print_at(0, 0, "C48 SNAKE - w a s d, q quits");
    for (x = 0; x < 20; x++) {
        s_cell(0, x, '#');
        s_cell(11, x, '#');
    }
    for (y = 1; y < 11; y++) {
        s_cell(y, 0, '#');
        s_cell(y, 19, '#');
    }
    s_cell(s_fy, s_fx, '*');
    for (i = s_len - 1; i > 0; i--)
        s_cell(s_y[i], s_x[i], 'o');
    s_cell(s_y[0], s_x[0], '@');
    print_at(17, 0, "Score:");
    game_num(17, 7, (unsigned int)s_score);
    game_show_last(19);
    print_at(22, 0, "Move:");
}

int main(void)
{
    int key;
    int nx;
    int ny;
    int eat;
    int body;
    int tail_x;
    int tail_y;
    int old_head_x;
    int old_head_y;
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
    s_draw_board();
    while (1) {
        key = game_key_echo(22, 6);
        s_turns++;
        if (key == 'q')
            return 0;
        if (key == 'w') {
            if (s_dy == 1) {
                game_record(key, 2);
                game_show_last(19);
                game_putc(22, 6, ' ');
                continue;
            }
            s_dx = 0;
            s_dy = -1;
        }
        else if (key == 's') {
            if (s_dy == -1) {
                game_record(key, 2);
                game_show_last(19);
                game_putc(22, 6, ' ');
                continue;
            }
            s_dx = 0;
            s_dy = 1;
        }
        else if (key == 'a') {
            if (s_dx == 1) {
                game_record(key, 2);
                game_show_last(19);
                game_putc(22, 6, ' ');
                continue;
            }
            s_dx = -1;
            s_dy = 0;
        }
        else if (key == 'd') {
            if (s_dx == -1) {
                game_record(key, 2);
                game_show_last(19);
                game_putc(22, 6, ' ');
                continue;
            }
            s_dx = 1;
            s_dy = 0;
        }
        else {
            game_record(key, 3);
            game_show_last(19);
            game_putc(22, 6, ' ');
            continue;
        }
        game_record(key, 1);
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
        tail_x = s_x[s_len - 1];
        tail_y = s_y[s_len - 1];
        old_head_x = s_x[0];
        old_head_y = s_y[0];
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
        if (!eat)
            s_cell(tail_y, tail_x, ' ');
        s_cell(old_head_y, old_head_x, 'o');
        s_cell(s_y[0], s_x[0], '@');
        if (eat) {
            s_food();
            s_cell(s_fy, s_fx, '*');
            game_num(17, 7, (unsigned int)s_score);
        }
        game_show_last(19);
        game_putc(22, 6, ' ');
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
