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

int dive(int n)
{
    return dive(n + 1);
}

int main(void)
{
    cls();
    print_at(0, 0, "SECURITY TEST: CALL RECURSION");
    print_at(2, 0, "ATTEMPT: recurse without base case");
    print_at(3, 0, "MITIGATION: VM call-depth guard must trap");
    return dive(0);
}
