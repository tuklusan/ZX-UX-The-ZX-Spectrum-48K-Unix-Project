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
    print_at(0, 0, "SECURITY TEST: INFINITE LOOP");
    print_at(2, 0, "ATTEMPT: run forever");
    print_at(3, 0, "MITIGATION: --max-steps must stop VM");
    for (;;) {
        ;
    }
    return 99;
}
