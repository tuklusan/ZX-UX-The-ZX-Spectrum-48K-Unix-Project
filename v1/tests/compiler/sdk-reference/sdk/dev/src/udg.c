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
    unsigned char a[8] = {24, 60, 126, 219, 255, 36, 90, 165};
    unsigned char b[8] = {129, 66, 36, 24, 24, 36, 66, 129};
    cls();
    udg_define(0, a);
    udg_define(1, b);
    udg_draw(0, 10, 12);
    udg_draw(1, 10, 14);
    print_at(14, 16, "udg sprites");
    return 0;
}
