// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "secapi.h"

int main(void)
{
    char *p;
    cls();
    print_at(21, 0, "HISTORICAL TEST - REAL ZX-UX NOW");
    print_at(0, 0, "SECURITY TEST: INTERIOR FREE");
    print_at(2, 0, "ATTEMPT: free malloc pointer + 1");
    print_at(3, 0, "MITIGATION: exact-base guard must trap");
    p = malloc(8);
    if (p == 0) return 2;
    free(p + 1);
    print_at(5, 0, "FAILED: interior free escaped guard");
    return 99;
}
