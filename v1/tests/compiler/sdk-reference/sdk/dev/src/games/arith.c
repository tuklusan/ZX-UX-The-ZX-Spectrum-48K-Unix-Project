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

int ar_turns;
int ar_right;

int main(void)
{
    int a;
    int b;
    int op;
    int answer;
    int want;
    int key;
    int digits;
    ar_turns = 0;
    ar_right = 0;
    want = 0;
    while (1) {
        a = game_rand(10) + 1;
        b = game_rand(10) + 1;
        op = game_rand(4);
        if (op == 2) {
            a = game_rand(10) + 1;
            b = game_rand(10) + 1;
        }
        if (op == 3) {
            want = game_rand(10) + 1;
            b = game_rand(9) + 1;
            a = want * b;
        }
        if (op == 0)
            want = a + b;
        if (op == 1) {
            if (b > a) {
                answer = a;
                a = b;
                b = answer;
            }
            want = a - b;
        }
        if (op == 2)
            want = a * b;
        if (op == 3)
            want = a / b;
        cls();
        print_at(0, 0, "C48 ARITHMETIC");
        print_at(3, 0, "Solve the problem or press q.");
        game_num(7, 8, (unsigned int)a);
        if (op == 0)
            game_putc(7, 12, '+');
        if (op == 1)
            game_putc(7, 12, '-');
        if (op == 2)
            game_putc(7, 12, '*');
        if (op == 3)
            game_putc(7, 12, '/');
        game_num(7, 16, (unsigned int)b);
        print_at(7, 20, "=");
        answer = 0;
        digits = 0;
        key = game_key();
        while (key != 10 && key != 13) {
            if (key == 'q' && digits == 0)
                return 0;
            if (key == 8 && digits > 0) {
                digits--;
                answer = answer / 10;
                game_putc(7, 22 + digits, ' ');
            }
            if (key >= '0' && key <= '9' && digits < 5) {
                game_putc(7, 22 + digits, key);
                answer = answer * 10 + key - '0';
                digits++;
            }
            key = game_key();
        }
        if (digits == 0)
            continue;
        ar_turns++;
        if (answer == want)
            ar_right++;
        print_at(11, 0, "Score:");
        game_num(11, 7, (unsigned int)ar_right);
        print_at(11, 13, "of");
        game_num(11, 16, (unsigned int)ar_turns);
        print_at(14, 0, "Press any key.");
        key = game_key();
        if (key == 'q')
            return 0;
    }
}
