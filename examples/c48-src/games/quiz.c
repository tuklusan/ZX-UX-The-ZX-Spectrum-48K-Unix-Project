// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "gameapi.h"

char *q_text[10] = {
    "ZX Spectrum CPU? a Z80 b 6502 c 68000",
    "48K Spectrum year? a 1988 b 1982 c 1992",
    "Screen width? a 320 b 640 c 256",
    "Pixels high? a 192 b 200 c 480",
    "BASIC maker? a Commodore b Sinclair c IBM",
    "Tape input jack? a AUX b BUS c EAR",
    "Tape output jack? a MIDI b MIC c NET",
    "Main RAM size? a 48K b 64K c 128K",
    "Z80 data bus? a 16-bit b 32-bit c 8-bit",
    "ZX-UX target? a VAX b Spectrum c PDP-11"
};
char q_ans[10] = {
    'a', 'b', 'c', 'a', 'b',
    'c', 'b', 'a', 'c', 'b'
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
        game_show_last(12);
        while (1) {
            key = game_key_echo(10, 21);
            q_turns++;
            if (key == 'q')
                return 0;
            if (key < 'a' || key > 'c') {
                game_record(key, 3);
                game_show_last(12);
                continue;
            }
            if (key == q_ans[i]) {
                q_score++;
                game_record(key, 6);
            }
            else
                game_record(key, 7);
            break;
        }
    }
    cls();
    print_at(6, 0, "Quiz complete. Score:");
    game_num(6, 22, (unsigned int)q_score);
    print_at(9, 0, "Press q to leave.");
    while (game_key() != 'q')
        q_turns++;
    return 0;
}
