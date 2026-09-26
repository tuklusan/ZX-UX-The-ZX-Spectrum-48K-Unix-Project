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

int c_deck[52];
int c_hand[6];
int c_comp[6];
int c_crib[4];
int c_hscore;
int c_cscore;
int c_dealer;
int c_turns;

int c_rank(int card)
{
    return card % 13 + 1;
}

int c_suit(int card)
{
    return card / 13;
}

int c_value(int card)
{
    int rank;
    rank = c_rank(card);
    if (rank > 10)
        return 10;
    return rank;
}

int c_bits(int value)
{
    int n;
    n = 0;
    while (value) {
        if (value & 1)
            n++;
        value = value >> 1;
    }
    return n;
}

int c_get(int *cards, int starter, int pos)
{
    if (pos < 4)
        return cards[pos];
    return starter;
}

int c_run(int *cards, int starter, int mask)
{
    int used[13];
    int i;
    int card;
    int rank;
    int lo;
    int hi;
    for (i = 0; i < 13; i++)
        used[i] = 0;
    lo = 13;
    hi = 0;
    for (i = 0; i < 5; i++) {
        if (mask & (1 << i)) {
            card = c_get(cards, starter, i);
            rank = c_rank(card) - 1;
            if (used[rank])
                return 0;
            used[rank] = 1;
            if (rank < lo)
                lo = rank;
            if (rank > hi)
                hi = rank;
        }
    }
    if (hi - lo + 1 == c_bits(mask))
        return 1;
    return 0;
}

int c_score5(int *cards, int starter, int crib)
{
    int score;
    int mask;
    int i;
    int j;
    int sum;
    int runlen;
    int runs;
    int suit;
    int flush;
    score = 0;
    for (mask = 1; mask < 32; mask++) {
        sum = 0;
        for (i = 0; i < 5; i++) {
            if (mask & (1 << i))
                sum = sum + c_value(c_get(cards, starter, i));
        }
        if (sum == 15)
            score = score + 2;
    }
    for (i = 0; i < 5; i++) {
        for (j = i + 1; j < 5; j++) {
            if (c_rank(c_get(cards, starter, i)) ==
                c_rank(c_get(cards, starter, j)))
                score = score + 2;
        }
    }
    runlen = 5;
    runs = 0;
    while (runlen >= 3 && runs == 0) {
        for (mask = 1; mask < 32; mask++) {
            if (c_bits(mask) == runlen) {
                if (c_run(cards, starter, mask))
                    runs++;
            }
        }
        if (runs == 0)
            runlen--;
    }
    score = score + runs * runlen;
    suit = c_suit(cards[0]);
    flush = 1;
    for (i = 1; i < 4; i++) {
        if (c_suit(cards[i]) != suit)
            flush = 0;
    }
    if (flush) {
        if (c_suit(starter) == suit)
            score = score + 5;
        else {
            if (!crib)
                score = score + 4;
        }
    }
    for (i = 0; i < 4; i++) {
        if (c_rank(cards[i]) == 11 &&
            c_suit(cards[i]) == c_suit(starter))
            score++;
    }
    return score;
}

void c_shuffle(void)
{
    int i;
    int j;
    int t;
    for (i = 0; i < 52; i++)
        c_deck[i] = i;
    for (i = 51; i > 0; i--) {
        j = game_rand(i + 1);
        t = c_deck[i];
        c_deck[i] = c_deck[j];
        c_deck[j] = t;
    }
}

void c_card(int row, int col, int card)
{
    int rank;
    int suit;
    rank = c_rank(card);
    suit = c_suit(card);
    if (rank == 1)
        game_putc(row, col, 'A');
    if (rank >= 2 && rank <= 9)
        game_putc(row, col, '0' + rank);
    if (rank == 10)
        game_putc(row, col, 'T');
    if (rank == 11)
        game_putc(row, col, 'J');
    if (rank == 12)
        game_putc(row, col, 'Q');
    if (rank == 13)
        game_putc(row, col, 'K');
    if (suit == 0)
        game_putc(row, col + 1, 'C');
    if (suit == 1)
        game_putc(row, col + 1, 'D');
    if (suit == 2)
        game_putc(row, col + 1, 'H');
    if (suit == 3)
        game_putc(row, col + 1, 'S');
}

void c_showhand(int *hand)
{
    int i;
    for (i = 0; i < 6; i++) {
        game_num(7, i * 8, (unsigned int)(i + 1));
        c_card(8, i * 8, hand[i]);
    }
}

int c_discard(void)
{
    int key;
    int first;
    int second;
    int out[4];
    int i;
    int n;
    first = -1;
    second = -1;
    while (first < 0) {
        cls();
        print_at(0, 0, "C48 CRIBBAGE SHOW - first to 61");
        print_at(2, 0, "Choose two cards for the crib.");
        print_at(3, 0, "q quits.");
        c_showhand(c_hand);
        print_at(11, 0, "First discard 1-6:");
        key = game_key();
        c_turns++;
        if (key == 'q')
            return -1;
        if (key >= '1' && key <= '6')
            first = key - '1';
    }
    while (second < 0) {
        print_at(13, 0, "Second discard 1-6:");
        key = game_key();
        c_turns++;
        if (key == 'q')
            return -1;
        if (key >= '1' && key <= '6') {
            second = key - '1';
            if (second == first)
                second = -1;
        }
    }
    c_crib[0] = c_hand[first];
    c_crib[1] = c_hand[second];
    n = 0;
    for (i = 0; i < 6; i++) {
        if (i != first && i != second) {
            out[n] = c_hand[i];
            n++;
        }
    }
    for (i = 0; i < 4; i++)
        c_hand[i] = out[i];
    return 0;
}

void c_round(void)
{
    int i;
    int starter;
    int hs;
    int cs;
    int crs;
    c_shuffle();
    for (i = 0; i < 6; i++) {
        c_hand[i] = c_deck[i * 2];
        c_comp[i] = c_deck[i * 2 + 1];
    }
    if (c_discard() < 0) {
        c_hscore = 1000;
        return;
    }
    c_crib[2] = c_comp[4];
    c_crib[3] = c_comp[5];
    starter = c_deck[12];
    hs = c_score5(c_hand, starter, 0);
    cs = c_score5(c_comp, starter, 0);
    crs = c_score5(c_crib, starter, 1);
    if (c_dealer == 0) {
        c_hscore = c_hscore + hs + crs;
        c_cscore = c_cscore + cs;
    }
    else {
        c_hscore = c_hscore + hs;
        c_cscore = c_cscore + cs + crs;
    }
    cls();
    print_at(0, 0, "Starter:");
    c_card(0, 10, starter);
    print_at(3, 0, "Your show:");
    game_num(3, 11, (unsigned int)hs);
    print_at(4, 0, "Computer show:");
    game_num(4, 15, (unsigned int)cs);
    print_at(5, 0, "Crib:");
    game_num(5, 6, (unsigned int)crs);
    print_at(8, 0, "Score you/computer:");
    game_num(8, 20, (unsigned int)c_hscore);
    game_num(8, 25, (unsigned int)c_cscore);
    print_at(11, 0, "Any key continues; q quits.");
    if (game_key() == 'q')
        c_hscore = 1000;
    c_turns++;
    if (c_dealer == 0)
        c_dealer = 1;
    else
        c_dealer = 0;
}

int main(void)
{
    c_hscore = 0;
    c_cscore = 0;
    c_dealer = 0;
    c_turns = 0;
    while (c_hscore < 61 && c_cscore < 61)
        c_round();
    if (c_hscore == 1000)
        return 0;
    cls();
    if (c_hscore >= 61)
        print_at(8, 0, "You win the match. Press q.");
    else
        print_at(8, 0, "Computer wins. Press q.");
    while (game_key() != 'q')
        c_turns++;
    return 0;
}
