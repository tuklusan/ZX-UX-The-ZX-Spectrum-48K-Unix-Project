/*
 * Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
 * Proprietary rights reserved except as expressly licensed herein.
 *
 * ZX-UX Sinclair ZX Spectrum Unix
 * This file is governed by the SANYALnet Labs Non-Commercial License in the
 * root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
 * for AI/ML model training are prohibited unless separately authorized.
 *
 * Attribution is required: Based on original work by Supratim Sanyal of
 * SANYALnet Labs. See LICENSE for full terms, warranty disclaimer, termination,
 * patent, trademark, and governing-law provisions.
 */
int main(void)
{
    int a;
    int b;
    int i;
    a = spawn("ball");
    b = spawn("stars");
    for (i = 0; i < 16; i = i + 1) {
        yield();
    }
    wait(a);
    wait(b);
    return 0;
}
