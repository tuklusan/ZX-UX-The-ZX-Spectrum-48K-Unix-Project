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
unsigned char star_x[8] = {4, 36, 68, 100, 132, 164, 196, 228};

int main(void)
{
    int i;
    for (i = 0; i < 8; i = i + 1) {
        plot(star_x[i], 40 + i * 12);
        yield();
    }
    return 0;
}
