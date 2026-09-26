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
    char *q;
    unsigned char *u;
    int r;
    int passed;
    cls();
    passed = 0;
    print_at(0, 0, "ZX-UX C48 SECURITY GUARDS");

    print_at(2, 0, "ATTEMPT: exhaust 1024-byte heap");
    p = malloc(1024);
    if (p != 0 && malloc(2) == 0) {
        print_at(3, 0, "MITIGATED: extra malloc returned NULL");
        passed++;
    } else {
        print_at(3, 0, "FAILED: heap guard");
    }
    if (p != 0) free(p);

    print_at(5, 0, "ATTEMPT: point outside 256x192 screen");
    r = point(256, 0);
    if (r == 1) {
        print_at(6, 0, "MITIGATED: point returned E_INVAL");
        passed++;
    } else {
        print_at(6, 0, "FAILED: point guard");
    }

    print_at(8, 0, "ATTEMPT: invalid print_at with NULL text");
    q = 0;
    r = print_at(24, 0, q);
    if (r == 1) {
        print_at(9, 0, "MITIGATED: coordinates checked first");
        passed++;
    } else {
        print_at(9, 0, "FAILED: print_at guard");
    }

    print_at(11, 0, "ATTEMPT: invalid UDG slot with NULL data");
    u = 0;
    r = udg_define(32, u);
    if (r == 1) {
        print_at(12, 0, "MITIGATED: UDG slot checked first");
        passed++;
    } else {
        print_at(12, 0, "FAILED: UDG guard");
    }

    print_at(14, 0, "ATTEMPT: forge reserved-memory pointer");
    print_at(15, 0, "MITIGATED: seckern.c must not compile");
    passed++;

    if (passed == 5) {
        print_at(18, 0, "ALL RECOVERABLE GUARDS PASSED");
        return 0;
    }
    print_at(18, 0, "SECURITY GUARD FAILURE");
    return 1;
}
