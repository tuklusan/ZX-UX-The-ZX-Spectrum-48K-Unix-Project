// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "gameapi.h"

char *fortunes[12] = {
    "A clean build is worth two clever excuses.",
    "The bug you skip today owns tomorrow morning.",
    "Small RAM encourages large opinions.",
    "If it works once, you have one data point.",
"A backup is a promise. A restore is proof it kept its word.",
    "Undefined behavior is optimism with paperwork.",
    "The shortest path often visits the debugger.",
    "A green test can still be the wrong test.",
    "Old computers punish modern assumptions quickly.",
    "Measure twice. Flash ROM once.",
    "A checksum is cheaper than archaeology.",
    "Today is an excellent day to read the log."
};
int fort_turns;

int main(void)
{
    int key;
    int pick;
    fort_turns = 0;
    while (1) {
        pick = game_rand(12);
        cls();
        print_at(0, 0, "C48 FORTUNE");
        print_at(5, 2, fortunes[pick]);
        print_at(10, 2, "Any key for another; q quits.");
        key = game_key();
        fort_turns++;
        if (key == 'q')
            return 0;
    }
}
