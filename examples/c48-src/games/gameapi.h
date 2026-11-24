// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
/* Local game declarations for the C48 Host Game API profile. */
int getchar(void);
int kbd_down(int key);
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
static int game_seeded = 0;

static int game_key(void)
{
    int c;
    c = getchar();
    if (c == -1) {
        /* Background tty stdin is closed by the shell. Scan physical keys
         * without taking any characters from the shell keyboard queue. */
        char *keys;
        int i;
        keys = "abcdefghijklmnopqrstuvwxyz0123456789 \r";
        for (;;) {
            i = 0;
            while (keys[i] != 0) {
                if (kbd_down(keys[i])) {
                    c = keys[i];
                    do {
                        yield();
                    } while (kbd_down(c));
                    return c;
                }
                i++;
            }
            yield();
        }
    }
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

static int game_key_echo(int row, int col)
{
    int key;
    key = game_key();
    if (key >= 32 && key <= 126)
        game_putc(row, col, key);
    return key;
}

static int game_last_key;
static int game_last_arg;
static int game_last_state;

static void game_record(int key, int state)
{
    game_last_key = key;
    game_last_arg = 0;
    game_last_state = state;
}

static void game_record2(int key, int arg, int state)
{
    game_last_key = key;
    game_last_arg = arg;
    game_last_state = state;
}

static void game_show_last(int row)
{
    if (game_last_state == 0)
        return;
    print_at(row, 0, "Last:");
    if (game_last_key >= 32 && game_last_key <= 126)
        game_putc(row, 6, game_last_key);
    else
        game_putc(row, 6, '?');
    if (game_last_arg >= 32 && game_last_arg <= 126)
        game_putc(row, 8, game_last_arg);
    else
        game_putc(row, 8, ' ');
    if (game_last_state == 1)
        print_at(row, 11, "accepted");
    if (game_last_state == 2)
        print_at(row, 11, "blocked ");
    if (game_last_state == 3)
        print_at(row, 11, "ignored ");
    if (game_last_state == 4)
        print_at(row, 11, "hit     ");
    if (game_last_state == 5)
        print_at(row, 11, "miss    ");
    if (game_last_state == 6)
        print_at(row, 11, "correct ");
    if (game_last_state == 7)
        print_at(row, 11, "wrong   ");
    if (game_last_state == 8)
        print_at(row, 11, "repeated");
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

static void game_seed_set(unsigned int seed)
{
    game_seed = seed;
    game_seeded = 1;
}

static void game_seed_init(void)
{
    game_seed_set(ticks());
}

static int game_rand(int limit)
{
    unsigned int value;
    if (limit <= 1)
        return 0;
    if (!game_seeded)
        game_seed_init();
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
