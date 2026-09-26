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
    print_at(7, 8, text);
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
    while (misses < 7) {
        cls();
        print_at(0, 0, "C48 HANGMAN");
        print_at(2, 0, "Guess letters. q quits.");
        h_mask(word, used);
        print_at(10, 0, "Misses:");
        game_num(10, 8, (unsigned int)misses);
        if (h_done(word, used)) {
            print_at(14, 0, "You solved it. Press q.");
            while (game_key() != 'q')
                h_turns++;
            return 0;
        }
        key = game_key();
        h_turns++;
        if (key == 'q')
            return 0;
        if (key < 'a' || key > 'z')
            continue;
        if (used[key - 'a'])
            continue;
        used[key - 'a'] = 1;
        hit = 0;
        i = 0;
        while (word[i] != 0) {
            if (word[i] == key)
                hit = 1;
            i++;
        }
        if (!hit)
            misses++;
    }
    cls();
    print_at(8, 0, "Hanged. The word was:");
    print_at(10, 0, word);
    print_at(12, 0, "Press q to leave.");
    while (game_key() != 'q')
        h_turns++;
    return 0;
}
