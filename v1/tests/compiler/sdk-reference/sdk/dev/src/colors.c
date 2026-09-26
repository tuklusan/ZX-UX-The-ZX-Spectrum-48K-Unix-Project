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
#include "c48host.h"

int main(void)
{
    cls();
    ink(7);
    paper(0);
    print_at(1, 2, "spectrum attribute palette");
    ink(1); print_at(4, 4, "blue");
    ink(2); print_at(6, 4, "red");
    ink(3); print_at(8, 4, "magenta");
    ink(4); print_at(10, 4, "green");
    ink(5); print_at(12, 4, "cyan");
    ink(6); print_at(14, 4, "yellow");
    ink(7); print_at(16, 4, "white");
    bright(1);
    print_at(19, 4, "bright");
    bright(0);
    return 0;
}
