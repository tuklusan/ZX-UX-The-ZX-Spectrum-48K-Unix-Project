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
/* Local game declarations for the C48 Host Game API profile. */
int getchar(void);
int putchar(int c);
int cls(void);
int print_at(int row, int col, char *text);
int ink(int c);
int paper(int c);
int bright(int on);
int border(int c);
int plot(int x, int y);
int draw(int x1, int y1, int x2, int y2);
unsigned int ticks(void);
int yield(void);
int sleep(unsigned int ticks);

static unsigned int game_seed = 44257u;

static int game_key(void)
{
    int c;
    c = getchar();
    if (c >= 'A' && c <= 'Z')
        c = c + 32;
    return c;
}

static void game_putc(int row, int col, int c)
{
    char text[2];
    text[0] = (char)c;
    text[1] = 0;
    print_at(row, col, text);
}

static void game_num(int row, int col, unsigned int value)
{
    char text[6];
    int pos;
    pos = 5;
    text[pos] = 0;
    do {
        pos--;
        text[pos] = (char)('0' + (value % 10u));
        value = value / 10u;
    } while (value != 0u);
    print_at(row, col, text + pos);
}

static int game_rand(int limit)
{
    unsigned int value;
    if (limit <= 1)
        return 0;
    game_seed = game_seed * 25173u + 13849u;
    game_seed = game_seed & 65535u;
    value = game_seed % (unsigned int)limit;
    return (int)value;
}

static int game_readint(void)
{
    int c;
    int sign;
    int value;
    int seen;
    sign = 1;
    value = 0;
    seen = 0;
    c = game_key();
    if (c == '-') {
        sign = -1;
        c = game_key();
    }
    while (c != 10 && c != 13) {
        if (c >= '0' && c <= '9') {
            value = value * 10 + c - '0';
            seen = 1;
        }
        c = game_key();
    }
    if (!seen)
        return 0;
    return value * sign;
}
