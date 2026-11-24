// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "gameapi.h"

char *h_words[8] = {
    "spectrum", "sinclair", "cassette", "rubber",
    "pixel", "memory", "kernel", "unix"
};
int h_turns;

int h_done(char *word, char *used)
{
    int i;
    int j;
    int found;
    i = 0;
    while (word[i] != 0) {
        found = 0;
        for (j = 0; j < 26; j++) {
            if (used[j] && word[i] == 'a' + j)
                found = 1;
        }
        if (!found)
            return 0;
        i++;
    }
    return 1;
}


void h_draw_stage(int misses)
{
    if (misses >= 1)
        game_putc(7, 18, 'O');
    if (misses >= 2)
        game_putc(8, 18, '|');
    if (misses >= 3)
        game_putc(8, 17, '/');
    if (misses >= 4)
        game_putc(8, 19, '\\');
    if (misses >= 5)
        game_putc(9, 17, '/');
    if (misses >= 6)
        game_putc(9, 19, '\\');
    if (misses >= 7) {
        game_putc(7, 18, 'X');
        game_putc(6, 18, '|');
    }
}

void h_draw_board(void)
{
    cls();
    print_at(0, 0, "C48 HANGMAN");
    print_at(1, 0, "Guess letters. q quits.");
    print_at(3, 8, "+---------+");
    print_at(4, 8, "|         |");
    print_at(5, 8, "|         |");
    print_at(6, 8, "|");
    print_at(7, 8, "|");
    print_at(8, 8, "|");
    print_at(9, 8, "|");
    print_at(10, 5, "================");
    print_at(12, 0, "Misses:");
    print_at(15, 0, "Guess:");
}

void h_mask(char *word, char *used)
{
    char text[16];
    int i;
    int j;
    int found;
    i = 0;
    while (word[i] != 0 && i < 15) {
        found = 0;
        for (j = 0; j < 26; j++) {
            if (used[j] && word[i] == 'a' + j)
                found = 1;
        }
        if (found)
            text[i] = word[i];
        else
            text[i] = '_';
        i++;
    }
    text[i] = 0;
    print_at(13, 12, text);
}

int main(void)
{
    char used[26];
    char *word;
    int i;
    int key;
    int misses;
    int hit;
    word = h_words[game_rand(8)];
    for (i = 0; i < 26; i++)
        used[i] = 0;
    misses = 0;
    h_turns = 0;
    h_draw_board();
    h_mask(word, used);
    game_num(12, 8, (unsigned int)misses);
    while (misses < 7) {
        if (h_done(word, used)) {
            print_at(19, 0, "You solved it. Press q.");
            while (game_key() != 'q')
                h_turns++;
            return 0;
        }
        key = game_key_echo(15, 7);
        h_turns++;
        if (key == 'q')
            return 0;
        if (key < 'a' || key > 'z') {
            game_record(key, 3);
            game_show_last(17);
            game_putc(15, 7, ' ');
            continue;
        }
        if (used[key - 'a']) {
            game_record(key, 8);
            game_show_last(17);
            game_putc(15, 7, ' ');
            continue;
        }
        used[key - 'a'] = 1;
        hit = 0;
        i = 0;
        while (word[i] != 0) {
            if (word[i] == key)
                hit = 1;
            i++;
        }
        if (!hit) {
            misses++;
            game_record(key, 5);
            h_draw_stage(misses);
            game_num(12, 8, (unsigned int)misses);
        }
        else {
            game_record(key, 4);
            h_mask(word, used);
        }
        game_show_last(17);
        game_putc(15, 7, ' ');
    }
    h_draw_stage(7);
    print_at(19, 0, "Hanged. The word was:");
    print_at(20, 0, word);
    print_at(22, 0, "Press q to leave.");
    while (game_key() != 'q')
        h_turns++;
    return 0;
}
