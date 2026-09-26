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

char *fortunes[12] = {
    "A clean build is worth two clever excuses.",
    "The bug you skip today owns tomorrow morning.",
    "Small RAM encourages large opinions.",
    "If it works once, you have one data point.",
    "A backup is a promise. A restore is evidence.",
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
