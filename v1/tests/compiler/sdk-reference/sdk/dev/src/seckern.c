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
