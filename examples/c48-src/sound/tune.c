// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include <c48.h>

/* A real Spectrum ROM-beeper melody, without host audio libraries. */
int main(void)
{
    int errors;
    cls();
    border(1);
    paper(0);
    ink(7);
    bright(1);
    print_at(8, 10, "SPECTRUM BEEPER TUNE");
    print_at(10, 7, "A SHORT TUNE ON THE REAL ROM");
    errors = 0;
    errors = errors + beep(0.35, 0.0);
    errors = errors + beep(0.35, 4.0);
    errors = errors + beep(0.35, 7.0);
    errors = errors + beep(0.35, 12.0);
    errors = errors + beep(0.35, 9.0);
    errors = errors + beep(0.35, 7.0);
    errors = errors + beep(0.35, 5.0);
    errors = errors + beep(0.35, 4.0);
    errors = errors + beep(0.35, 2.0);
    errors = errors + beep(0.35, 7.0);
    errors = errors + beep(0.35, 9.0);
    errors = errors + beep(0.35, 12.0);
    errors = errors + beep(0.45, 7.0);
    errors = errors + beep(0.45, 0.0);
    if (errors != 0) {
        print_at(14, 10, "ROM BEEP REPORTED ERROR");
        sleep(250u);
        return 1;
    }
    print_at(14, 12, "MELODY COMPLETE");
    return 0;
}
