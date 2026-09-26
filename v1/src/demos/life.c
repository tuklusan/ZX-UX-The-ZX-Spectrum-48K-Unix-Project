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
unsigned char cells[768];

int main(void)
{
    int i;
    udg_clear(1);
    for (i = 0; i < 768; i = i + 1) {
        cells[i] = 0;
    }
    cells[12 * 32 + 15] = 1;
    cells[12 * 32 + 16] = 1;
    cells[12 * 32 + 17] = 1;
    yield();
    return 0;
}
