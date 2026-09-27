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
int touched;

int touch(void)
{
    touched = touched + 1;
    return 1;
}

int recur(int n)
{
    if (n <= 1)
        return 1;
    return n * recur(n - 1);
}

int main(void)
{
    int i;
    int s;

    i = 0;
    s = 0;
    while (i < 6) {
        i++;
        if (i == 2)
            continue;
        s = s + i;
        if (i == 5)
            break;
    }

    do {
        s = s + 1;
    } while (s < 14);

    for (i = 0; i < 3; i++) {
        s = s + 2;
    }

    if (0 && touch())
        return 2;
    if ((recur(5) == 120 && s == 20) || touch())
        return touched;
    return 3;
}
