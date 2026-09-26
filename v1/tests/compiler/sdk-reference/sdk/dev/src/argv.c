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

int main(int argc, char **argv)
{
    int i;
    cls();
    print_at(0, 0, "argv");
    for (i = 0; i < argc; i++) {
        if (i < 20) print_at(i + 2, 0, argv[i]);
    }
    return 0;
}
