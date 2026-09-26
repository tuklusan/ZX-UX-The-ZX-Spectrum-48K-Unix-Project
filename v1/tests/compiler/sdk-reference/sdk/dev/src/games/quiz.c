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

char *q_text[10] = {
    "ZX Spectrum CPU? a Z80 b 6502 c 68000",
    "48K Spectrum year? a 1982 b 1988 c 1992",
    "Screen width? a 256 b 320 c 640",
    "Pixels high? a 192 b 200 c 480",
    "BASIC maker? a Sinclair b Commodore c IBM",
    "Tape input jack? a EAR b AUX c BUS",
    "Tape output jack? a MIC b MIDI c NET",
    "Main RAM size? a 48K b 64K c 128K",
    "Z80 data bus? a 8-bit b 16-bit c 32-bit",
    "ZX-UX target? a Spectrum b VAX c PDP-11"
};
char q_ans[10] = {
    'a', 'a', 'a', 'a', 'a',
    'a', 'a', 'a', 'a', 'a'
};
int q_turns;
int q_score;

int main(void)
{
    int i;
    int key;
    q_turns = 0;
    q_score = 0;
    for (i = 0; i < 10; i++) {
        cls();
        print_at(0, 0, "C48 QUIZ");
        print_at(2, 0, "Question:");
        game_num(2, 10, (unsigned int)(i + 1));
        print_at(6, 0, q_text[i]);
        print_at(10, 0, "Answer a, b, c or q:");
        key = game_key();
        q_turns++;
        if (key == 'q')
            return 0;
        if (key == q_ans[i])
            q_score++;
    }
    cls();
    print_at(6, 0, "Quiz complete. Score:");
    game_num(6, 22, (unsigned int)q_score);
    print_at(9, 0, "Press q to leave.");
    while (game_key() != 'q')
        q_turns++;
    return 0;
}
