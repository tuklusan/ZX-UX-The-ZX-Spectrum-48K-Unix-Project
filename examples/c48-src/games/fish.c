// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "gameapi.h"

int f_deck[13];
int f_human[13];
int f_comp[13];
int f_hbooks;
int f_cbooks;
int f_turns;
int f_comp_rank;
int f_comp_hit;

int f_left(void)
{
    int i;
    int count;
    count = 0;
    for (i = 0; i < 13; i++)
        count = count + f_deck[i];
    return count;
}

int f_drawone(int *hand)
{
    int start;
    int i;
    int rank;
    if (f_left() == 0)
        return -1;
    start = game_rand(13);
    for (i = 0; i < 13; i++) {
        rank = (start + i) % 13;
        if (f_deck[rank] > 0) {
            f_deck[rank]--;
            hand[rank]++;
            return rank;
        }
    }
    return -1;
}

void f_books(int *hand, int *books)
{
    int i;
    for (i = 0; i < 13; i++) {
        if (hand[i] == 4) {
            hand[i] = 0;
            (*books)++;
        }
    }
}

int f_rank(int key)
{
    if (key >= '1' && key <= '9')
        return key - '1';
    if (key == 't')
        return 9;
    if (key == 'j')
        return 10;
    if (key == 'q')
        return 11;
    if (key == 'k')
        return 12;
    return -1;
}

int f_rankkey(int rank)
{
    if (rank >= 0 && rank < 9)
        return '1' + rank;
    if (rank == 9)
        return 't';
    if (rank == 10)
        return 'j';
    if (rank == 11)
        return 'q';
    if (rank == 12)
        return 'k';
    return '?';
}

int f_cpick(void)
{
    int start;
    int i;
    int rank;
    start = game_rand(13);
    for (i = 0; i < 13; i++) {
        rank = (start + i) % 13;
        if (f_comp[rank] > 0)
            return rank;
    }
    return -1;
}

void f_show(void)
{
    int i;
    cls();
    print_at(0, 0, "C48 GO FISH - x quits");
    print_at(2, 0, "Ask: 1-9, t, j, q, k");
    print_at(4, 0, "Your hand counts:");
    for (i = 0; i < 13; i++) {
        if (i < 9)
            game_putc(6, i * 4, '1' + i);
        if (i == 9)
            game_putc(6, i * 4, 'T');
        if (i == 10)
            game_putc(6, i * 4, 'J');
        if (i == 11)
            game_putc(6, i * 4, 'Q');
        if (i == 12)
            game_putc(6, i * 4, 'K');
        game_num(7, i * 4, (unsigned int)f_human[i]);
    }
    print_at(10, 0, "Your books:");
    game_num(10, 12, (unsigned int)f_hbooks);
    print_at(11, 0, "Computer books:");
    game_num(11, 16, (unsigned int)f_cbooks);
    print_at(12, 0, "Deck:");
    game_num(12, 6, (unsigned int)f_left());
    game_show_last(14);
    if (f_comp_rank >= 0) {
        print_at(15, 0, "Computer asked:");
        game_putc(15, 16, f_rankkey(f_comp_rank));
        if (f_comp_hit)
            print_at(15, 19, "hit");
        else
            print_at(15, 19, "go fish");
    }
}

void f_status(void)
{
    game_show_last(14);
    game_putc(17, 10, ' ');
}

int main(void)
{
    int i;
    int key;
    int rank;
    int draw;
    int turn;
    for (i = 0; i < 13; i++) {
        f_deck[i] = 4;
        f_human[i] = 0;
        f_comp[i] = 0;
    }
    f_hbooks = 0;
    f_cbooks = 0;
    f_turns = 0;
    f_comp_rank = -1;
    f_comp_hit = 0;
    for (i = 0; i < 7; i++) {
        f_drawone(f_human);
        f_drawone(f_comp);
    }
    f_books(f_human, &f_hbooks);
    f_books(f_comp, &f_cbooks);
    turn = 0;
    while (f_hbooks + f_cbooks < 13) {
        f_show();
        if (turn == 0) {
            print_at(17, 0, "Your ask:");
            while (1) {
                key = game_key_echo(17, 10);
                f_turns++;
                if (key == 'x')
                    return 0;
                rank = f_rank(key);
                if (rank < 0) {
                    game_record(key, 3);
                    f_status();
                    continue;
                }
                if (f_human[rank] == 0) {
                    game_record(key, 2);
                    f_status();
                    continue;
                }
                break;
            }
            f_comp_rank = -1;
            if (f_comp[rank] > 0) {
                f_human[rank] = f_human[rank] + f_comp[rank];
                f_comp[rank] = 0;
                game_record(key, 4);
            }
            else {
                draw = f_drawone(f_human);
                if (draw == rank)
                    game_record(key, 4);
                else {
                    game_record(key, 5);
                    turn = 1;
                }
            }
            f_books(f_human, &f_hbooks);
        }
        else {
            rank = f_cpick();
            if (rank < 0) {
                f_drawone(f_comp);
                turn = 0;
                continue;
            }
            f_comp_rank = rank;
            if (f_human[rank] > 0) {
                f_comp[rank] = f_comp[rank] + f_human[rank];
                f_human[rank] = 0;
                f_comp_hit = 1;
            }
            else {
                f_comp_hit = 0;
                draw = f_drawone(f_comp);
                if (draw != rank)
                    turn = 0;
            }
            f_books(f_comp, &f_cbooks);
        }
        if (f_left() == 0) {
            if (f_cpick() < 0 && turn == 1)
                turn = 0;
            rank = f_cpick();
            if (rank < 0 && turn == 0) {
                for (i = 0; i < 13; i++) {
                    if (f_human[i] > 0)
                        rank = i;
                }
                if (rank < 0)
                    break;
            }
        }
    }
    f_show();
    if (f_hbooks > f_cbooks)
        print_at(16, 0, "You win. Press x.");
    else
        print_at(16, 0, "Computer wins. Press x.");
    while (game_key() != 'x')
        f_turns++;
    return 0;
}
