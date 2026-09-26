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
    int a[2];
    int *p;
    cls();
    print_at(0, 0, "SECURITY TEST: ONE-PAST WRITE");
    print_at(2, 0, "ATTEMPT: write through a + 2");
    print_at(3, 0, "MITIGATION: range guard must trap write");
    p = a + 2;
    *p = 7;
    print_at(5, 0, "FAILED: write escaped guard");
    return 99;
}
