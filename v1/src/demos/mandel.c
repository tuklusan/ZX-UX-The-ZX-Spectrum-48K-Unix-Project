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
    int i;
    float x;
    float y;
    float z;
    x = -2.0;
    y = -1.0;
    z = 0.0;
    for (i = 0; i < 24; i = i + 1) {
        z = z * z + x * y;
        plot(i * 8, 88 + (int)z);
        yield();
    }
    return 0;
}
