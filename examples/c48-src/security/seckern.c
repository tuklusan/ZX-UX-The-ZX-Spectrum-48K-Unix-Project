// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
/* Compile-negative security fixture.
 * ATTEMPT: forge a pointer into reserved address 0x5B00.
 * MITIGATION: C48 rejects arbitrary integer-to-pointer casts.
 */
int main(void)
{
    int *p;
    p = (int *)0x5b00u;
    *p = 7;
    return 0;
}
