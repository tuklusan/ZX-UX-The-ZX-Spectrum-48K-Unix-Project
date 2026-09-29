// ============================================================
// Copyright (c) 2026 SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and model
// training prohibited unless separately authorized.
//
// Attribution required: SANYALnet Labs.
// See root LICENSE for full terms.
// ============================================================
#include "exapi.h"

char *c_names[8] = {
    "BLACK", "BLUE", "RED", "MAGENTA",
    "GREEN", "CYAN", "YELLOW", "WHITE"
};

void c_cell(int row, int col, int color, int is_bright)
{
    paper(color);
    bright(is_bright);
    if (color == 0)
        ink(7);
    else
        ink(0);
    print_at(row, col, " @#*+                    ");
    print_at(row, col + 7, c_names[color]);
}

int main(void)
{
    int c;
    paper(0);
    ink(7);
    bright(1);
    cls();
    print_at(0, 8, "ZX SPECTRUM ATTRIBUTE TEST CARD");
    bright(0);
    print_at(2, 6, "NORMAL");
    bright(1);
    print_at(2, 38, "BRIGHT");
    for (c = 0; c < 8; c++) {
        c_cell(4 + c, 1, c, 0);
        c_cell(4 + c, 33, c, 1);
    }
    paper(0);
    ink(7);
    bright(1);
    print_at(14, 4, "INK / PAPER / BRIGHT / BORDER");
    print_at(16, 4, "@ # * +  0123456789  ABC  xyz");
    for (c = 0; c < 8; c++) {
        border(c);
        yield();
    }
    border(1);
    return 0;
}
