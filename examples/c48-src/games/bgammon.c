// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "gameapi.h"

int bg_pt[24];
int bg_bar_w;
int bg_bar_b;
int bg_off_w;
int bg_off_b;
int bg_side;
int bg_d1;
int bg_d2;
int bg_turns;
int bg_skip_die;

void bg_init(void)
{
    int i;
    for (i = 0; i < 24; i++)
        bg_pt[i] = 0;
    bg_pt[23] = 2;
    bg_pt[12] = 5;
    bg_pt[7] = 3;
    bg_pt[5] = 5;
    bg_pt[0] = -2;
    bg_pt[11] = -5;
    bg_pt[16] = -3;
    bg_pt[18] = -5;
    bg_bar_w = 0;
    bg_bar_b = 0;
    bg_off_w = 0;
    bg_off_b = 0;
    bg_side = 0;
    bg_turns = 0;
    bg_skip_die = 0;
}

void bg_cell(int row, int col, int point)
{
    int v;
    game_putc(row, col, 'a' + point);
    game_putc(row, col + 1, ':');
    v = bg_pt[point];
    if (v > 0) {
        game_putc(row, col + 2, 'W');
        game_num(row, col + 3, (unsigned int)v);
    }
    if (v < 0) {
        game_putc(row, col + 2, 'B');
        game_num(row, col + 3, (unsigned int)(-v));
    }
    if (v == 0)
        game_putc(row, col + 2, '.');
}

void bg_show(void)
{
    int i;
    int row;
    int col;
    cls();
    print_at(0, 0, "C48 BACKGAMMON");
    print_at(1, 0, "a-x point, z bar, 0 quit");
    for (i = 0; i < 24; i++) {
        row = 4 + (i / 6) * 2;
        col = (i % 6) * 10;
        bg_cell(row, col, i);
    }
    print_at(13, 0, "White bar/off:");
    game_num(13, 15, (unsigned int)bg_bar_w);
    game_num(13, 20, (unsigned int)bg_off_w);
    print_at(14, 0, "Black bar/off:");
    game_num(14, 15, (unsigned int)bg_bar_b);
    game_num(14, 20, (unsigned int)bg_off_b);
    if (bg_side == 0)
        print_at(16, 0, "Turn: White");
    else
        print_at(16, 0, "Turn: Black");
    print_at(17, 0, "Dice:");
    game_num(17, 6, (unsigned int)bg_d1);
    game_num(17, 10, (unsigned int)bg_d2);
    if (bg_skip_die > 0) {
        print_at(18, 0, "No legal move for die:");
        game_num(18, 23, (unsigned int)bg_skip_die);
    }
    game_show_last(19);
}

int bg_home(int side)
{
    int i;
    if (side == 0) {
        if (bg_bar_w)
            return 0;
        for (i = 6; i < 24; i++) {
            if (bg_pt[i] > 0)
                return 0;
        }
        return 1;
    }
    if (bg_bar_b)
        return 0;
    for (i = 0; i < 18; i++) {
        if (bg_pt[i] < 0)
            return 0;
    }
    return 1;
}

int bg_over(int src, int die, int side)
{
    int i;
    if (side == 0) {
        for (i = src + 1; i < 6; i++) {
            if (bg_pt[i] > 0)
                return 0;
        }
        return die > src + 1;
    }
    for (i = 18; i < src; i++) {
        if (bg_pt[i] < 0)
            return 0;
    }
    return src + die > 23;
}

int bg_can(int src, int die, int side)
{
    int dest;
    if (die < 1 || die > 6)
        return 0;
    if (side == 0) {
        if (bg_bar_w) {
            if (src != 24)
                return 0;
            dest = 24 - die;
        }
        else {
            if (src < 0 || src > 23 || bg_pt[src] <= 0)
                return 0;
            dest = src - die;
            if (dest < 0) {
                if (!bg_home(0))
                    return 0;
                if (dest == -1 || bg_over(src, die, 0))
                    return 1;
                return 0;
            }
        }
        if (bg_pt[dest] < -1)
            return 0;
        return 1;
    }
    if (bg_bar_b) {
        if (src != 24)
            return 0;
        dest = die - 1;
    }
    else {
        if (src < 0 || src > 23 || bg_pt[src] >= 0)
            return 0;
        dest = src + die;
        if (dest > 23) {
            if (!bg_home(1))
                return 0;
            if (dest == 24 || bg_over(src, die, 1))
                return 1;
            return 0;
        }
    }
    if (bg_pt[dest] > 1)
        return 0;
    return 1;
}

int bg_any(int die, int side)
{
    int i;
    if (side == 0 && bg_bar_w)
        return bg_can(24, die, side);
    if (side == 1 && bg_bar_b)
        return bg_can(24, die, side);
    for (i = 0; i < 24; i++) {
        if (bg_can(i, die, side))
            return 1;
    }
    return 0;
}

void bg_move(int src, int die, int side)
{
    int dest;
    if (side == 0) {
        if (src == 24) {
            bg_bar_w--;
            dest = 24 - die;
        }
        else {
            bg_pt[src]--;
            dest = src - die;
        }
        if (dest < 0) {
            bg_off_w++;
            return;
        }
        if (bg_pt[dest] == -1) {
            bg_pt[dest] = 0;
            bg_bar_b++;
        }
        bg_pt[dest]++;
        return;
    }
    if (src == 24) {
        bg_bar_b--;
        dest = die - 1;
    }
    else {
        bg_pt[src]++;
        dest = src + die;
    }
    if (dest > 23) {
        bg_off_b++;
        return;
    }
    if (bg_pt[dest] == 1) {
        bg_pt[dest] = 0;
        bg_bar_w++;
    }
    bg_pt[dest]--;
}

void bg_prompt(int die)
{
    print_at(20, 0, "Move die:");
    game_num(20, 10, (unsigned int)die);
    print_at(21, 0, "Source:");
}

void bg_status(void)
{
    game_show_last(19);
    game_putc(21, 8, ' ');
}

int bg_play(int die)
{
    int key;
    int src;
    if (!bg_any(die, bg_side)) {
        bg_skip_die = die;
        return 0;
    }
    bg_skip_die = 0;
    bg_show();
    bg_prompt(die);
    while (1) {
        key = game_key_echo(21, 8);
        bg_turns++;
        if (key == '0')
            return -1;
        if (key == 'z')
            src = 24;
        else if (key >= 'a' && key <= 'x')
            src = key - 'a';
        else {
            game_record(key, 3);
            bg_status();
            continue;
        }
        if (bg_can(src, die, bg_side)) {
            game_record2(key, '0' + die, 1);
            bg_move(src, die, bg_side);
            return 0;
        }
        game_record2(key, '0' + die, 2);
        bg_status();
    }
}

int bg_order(void)
{
    int key;
    int can1;
    int can2;
    can1 = bg_any(bg_d1, bg_side);
    can2 = bg_any(bg_d2, bg_side);
    if (!can1 && !can2)
        return 1;
    if (!can1)
        return 2;
    if (!can2)
        return 1;
    bg_show();
    print_at(20, 0, "First die: 1 or 2");
    print_at(21, 0, "Order:");
    while (1) {
        key = game_key_echo(21, 7);
        bg_turns++;
        if (key == '0')
            return 0;
        if (key == '1' || key == '2') {
            game_record(key, 1);
            return key - '0';
        }
        game_record(key, 3);
        game_show_last(19);
        game_putc(21, 7, ' ');
    }
}

int main(void)
{
    int count;
    int i;
    int die;
    int rc;
    int order;
    bg_init();
    while (bg_off_w < 15 && bg_off_b < 15) {
        bg_d1 = game_rand(6) + 1;
        bg_d2 = game_rand(6) + 1;
        count = 2;
        order = 1;
        if (bg_d1 == bg_d2)
            count = 4;
        else {
            order = bg_order();
            if (order == 0)
                return 0;
        }
        for (i = 0; i < count; i++) {
            if (count == 4)
                die = bg_d1;
            else if (order == 1) {
                if (i == 0)
                    die = bg_d1;
                else
                    die = bg_d2;
            }
            else {
                if (i == 0)
                    die = bg_d2;
                else
                    die = bg_d1;
            }
            rc = bg_play(die);
            if (rc < 0)
                return 0;
        }
        if (bg_side == 0)
            bg_side = 1;
        else
            bg_side = 0;
    }
    bg_show();
    if (bg_off_w == 15)
        print_at(21, 0, "White wins. Press 0.");
    else
        print_at(21, 0, "Black wins. Press 0.");
    while (game_key() != '0')
        bg_turns++;
    return 0;
}
