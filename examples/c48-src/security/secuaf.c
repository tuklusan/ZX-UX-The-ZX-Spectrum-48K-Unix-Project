// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "secapi.h"

int main(void)
{
    int *p;
    cls();
    print_at(21, 0, "HISTORICAL TEST - REAL ZX-UX NOW");
    print_at(0, 0, "SECURITY TEST: USE AFTER FREE");
    print_at(2, 0, "ATTEMPT: dereference freed pointer");
    print_at(3, 0, "MITIGATION: liveness guard must trap read");
    p = malloc(2);
    if (p == 0) return 2;
    *p = 42;
    free(p);
    return *p;
}
