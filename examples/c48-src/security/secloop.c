// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "secapi.h"

int main(void)
{
    cls();
    print_at(21, 0, "HISTORICAL TEST - REAL ZX-UX NOW");
    print_at(0, 0, "SECURITY TEST: INFINITE LOOP");
    print_at(2, 0, "ATTEMPT: run forever");
    print_at(3, 0, "HEADLESS RVM: --frames LIMIT");
    print_at(4, 0, "GUI: USE BREAK TO STOP");
    for (;;) {
        ;
    }
    return 99;
}
