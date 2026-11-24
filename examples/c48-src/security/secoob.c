// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "secapi.h"

int main(void)
{
    int a[2];
    int *p;
    cls();
    print_at(21, 0, "HISTORICAL TEST - REAL ZX-UX NOW");
    print_at(0, 0, "SECURITY TEST: ONE-PAST WRITE");
    print_at(2, 0, "ATTEMPT: write through a + 2");
    print_at(3, 0, "MITIGATION: range guard must trap write");
    p = a + 2;
    *p = 7;
    print_at(5, 0, "OLD VM-ONLY GUARD NOT PRESENT");
    return 99;
}
