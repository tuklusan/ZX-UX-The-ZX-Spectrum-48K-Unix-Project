// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "secapi.h"

int dive(int n)
{
    return dive(n + 1);
}

int main(void)
{
    cls();
    print_at(21, 0, "HISTORICAL TEST - REAL ZX-UX NOW");
    print_at(0, 0, "SECURITY TEST: CALL RECURSION");
    print_at(2, 0, "ATTEMPT: recurse without base case");
    print_at(3, 0, "MITIGATION: VM call-depth guard must trap");
    return dive(0);
}
