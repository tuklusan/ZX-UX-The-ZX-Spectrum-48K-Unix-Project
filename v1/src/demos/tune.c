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
float pitch[4] = {0, 4.5, 7, 12.25};
float duration[4] = {.25, .25, .25, .5};

int main(void)
{
    int i;
    for (i = 0; i < 4; i = i + 1) {
        beep(duration[i], pitch[i]);
        yield();
    }
    return 0;
}
