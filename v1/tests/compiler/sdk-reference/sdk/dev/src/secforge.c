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
    int *p;
    char *heap;
    char *dst;
    char *src;
    void *v;
    cls();
    print_at(0, 0, "SECURITY TEST: RAW POINTER FORGERY");
    print_at(2, 0,
             "ATTEMPT: copy pointer bytes by char writes");
    print_at(3, 0, "MITIGATION: raw bytes have no provenance");
    heap = malloc(2);
    if (heap == 0) return 2;
    p = 0;
    v = &p;
    dst = v;
    v = &heap;
    src = v;
    dst[0] = src[0];
    dst[1] = src[1];
    *p = 7;
    print_at(5, 0, "FAILED: forged pointer escaped guard");
    return 99;
}
