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
    char *p;
    cls();
    print_at(0, 0, "SECURITY TEST: DOUBLE FREE");
    print_at(2, 0, "ATTEMPT: free same allocation twice");
    print_at(3, 0, "MITIGATION: stale allocation must trap");
    p = malloc(8);
    if (p == 0) return 2;
    free(p);
    free(p);
    print_at(5, 0, "FAILED: double free escaped guard");
    return 99;
}
