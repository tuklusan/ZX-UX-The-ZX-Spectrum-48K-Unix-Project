// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "secapi.h"

int main(void)
{
    int *p;
    char *heap;
    char *dst;
    char *src;
    void *v;
    cls();
    print_at(21, 0, "HISTORICAL TEST - REAL ZX-UX NOW");
    print_at(0, 0, "SECURITY TEST: RAW POINTER FORGERY");
    print_at(2, 0,
             "ATTEMPT: copy pointer bytes by char writes");
    print_at(3, 0,
  "MITIGATION: raw bytes cannot create a valid pointer handle");
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
    print_at(5, 0, "OLD VM-ONLY GUARD NOT PRESENT");
    return 99;
}
