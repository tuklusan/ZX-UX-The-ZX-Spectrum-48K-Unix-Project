/* 2D MINI-MAZE, Mark Green (1996).
 * C48 port for ZX-UX, based on the original BASIC stored in 2DM.SNA.
 * Original maze layout, eight objects, eight-pixel tile sprites, and
 * player-following scroll is preserved in a 10x10 viewport. Controls are
 * polled from the physical keyboard, so games cannot consume or clear the
 * shared ZX-UX terminal input while the shell accepts background commands.
 * The rock event is checked once per input, rather than on every
 * pass through the original BASIC INKEY$ polling loop.
 * Safety fix: random rocks are accepted only if every uncollected
 * object stays reachable from the player. Original BASIC may trap you.
 *
 * ZX-UX SDK: SANYALnet Labs Non-Commercial License applies to its API.
 * Controls Q/Z up/down, I/P left/right, 0 abort. Display limited to left half.
 */
#include <c48.h>

char *original[15] = {
    "#################",
    "#               #",
    "# ## # ### # ## #",
    "# #  # # # #  # #",
    "# # ##     ## # #",
    "#   #  ###  #   #",
    "# ###  ###  ### #",
    "#               #",
    "# ###  ###  ### #",
    "#   #  ###  #   #",
    "# # ##     ## # #",
    "# #  # # # #  # #",
    "# ## # ### # ## #",
    "#               #",
    "#################"
};

char cells[285];                   /* 15 rows by 19 columns, padded. */
int px;
int py;
int collected;
unsigned int seed;
unsigned char flood_seen[285];
int flood_queue[285];
unsigned char pawn[8] = {0, 24, 24, 126, 24, 36, 36, 0};
unsigned char rock[8] = {126, 223, 123, 110, 255, 239, 253, 94};
unsigned char object_sprite[8] = {0, 60, 66, 66, 66, 66, 60, 0};

/* 10 x 10 original-size (8x8) cells, centered in the left screen half:
 * horizontal 24..103 / 256, vertical 56..135 / 192. Font is 64x24.
 * Moving the player shifts the visible world, as with the original 5x5.
 */
#define VIEW_TILES 10
#define VIEW_TOP 7
#define VIEW_LEFT 3
#define VIEW_ANCHOR 5


int getcell(int x, int y)
{
    if (x < 0 || x >= 15 || y < 0 || y >= 19)
        return '#';
    return cells[x * 19 + y];
}

void setcell(int x, int y, int ch)
{
    cells[x * 19 + y] = (char)ch;
}

int random_n(int n)
{
    seed = (seed * 25173u + 13849u) & 65535u;
    return (int)(seed % (unsigned int)n);
}

/* Verify that every outstanding object is still reachable by the
 * player. This runs only when testing a proposed new rock. A 15 x 19
 * flood fill fits comfortably inside the ZX Spectrum 48K memory budget.
 */
int obj_reachable(void)
{
    int i;
    int head;
    int tail;
    int pos;
    int x;
    int y;
    int found;
    for (i = 0; i < 285; i++)
        flood_seen[i] = 0;
    head = 0;
    tail = 1;
    pos = px * 19 + py;
    flood_seen[pos] = 1;
    flood_queue[0] = pos;
    found = 0;
    while (head < tail) {
        pos = flood_queue[head++];
        x = pos / 19;
        y = pos % 19;
        if (cells[pos] == 'O')
            found++;
        i = pos - 19;
        if (x > 0 && cells[i] != '#' && !flood_seen[i]) {
            flood_seen[i] = 1;
            flood_queue[tail++] = i;
        }
        i = pos + 19;
        if (x < 14 && cells[i] != '#' && !flood_seen[i]) {
            flood_seen[i] = 1;
            flood_queue[tail++] = i;
        }
        i = pos - 1;
        if (y > 0 && cells[i] != '#' && !flood_seen[i]) {
            flood_seen[i] = 1;
            flood_queue[tail++] = i;
        }
        i = pos + 1;
        if (y < 18 && cells[i] != '#' && !flood_seen[i]) {
            flood_seen[i] = 1;
            flood_queue[tail++] = i;
        }
    }
    return found == 8 - collected;
}

/* Reject a rock if it strands any remaining object. On success the
 * tested rock remains in the board; on failure the board is restored.
 */
int try_rock(int x, int y)
{
    if (getcell(x, y) != ' ' || (x == px && y == py))
        return 0;
    setcell(x, y, '#');
    if (obj_reachable())
        return 1;
    setcell(x, y, ' ');
    return 0;
}

void counter(void)
{
    char count[2];
    count[0] = (char)('0' + collected);
    count[1] = 0;
    print_at(3, 24, count);
}

void initialize(void)
{
    int x;
    int y;
    int placed;
    int tries;
    for (x = 0; x < 15; x++) {
        setcell(x, 0, ' ');
        for (y = 0; y < 17; y++)
            setcell(x, y + 1, original[x][y]);
        setcell(x, 18, ' ');
    }
    seed = ticks();
    if (seed == 0)
        seed = 44257u;
    placed = 0;
    tries = 0;
    while (placed < 8 && tries < 5000) {
        x = 1 + random_n(13);
        y = 1 + random_n(15);
        if (getcell(x, y) == ' ' && (x != 4 || y != 4)) {
            setcell(x, y, 'O');
            placed++;
        }
        tries++;
    }
    px = 4;
    py = 4;
    collected = 0;
}

/* Character 127 is the copyright sign already shipped in ZX-UX's
 * 64-column font (font4x8.bin). Do not manufacture a new bitmap glyph.
 */
/* Two left-aligned lines, each within the first 32 font64 columns. */
void credits(void)
{
    char copyright_char[2];
    copyright_char[0] = 127; /* existing ZX-UX font64 copyright glyph */
    copyright_char[1] = 0;
    print_at(21, 0, "Original ");
    print_at(21, 9, copyright_char);
    print_at(21, 10, "1996 Mark Green");
    print_at(22, 0, "ZX-UX port ");
    print_at(22, 11, copyright_char);
    print_at(22, 12, "2026 Supratim Sanyal");
}

/* Centred in 32-character (128 pixel) left half, rows 0 through 3. */
void game_header(void)
{
    print_at(0, 4, "SANYALnet Labs Mini Maze");
    print_at(1, 6, "ZX-UX Unix C Edition");
    print_at(2, 4, "Move: Q,Z,I,P  Abort: 0");
    print_at(3, 5, "OBJECTS COLLECTED: 0/8");
}

void viewport(void)
{
    int a;
    int b;
    int tile;
    int row;
    int col;
    for (a = 0; a < VIEW_TILES; a++) {
        row = VIEW_TOP + a;
        /* Wipe only the 80-pixel window, never the rest of the screen.
         * Console columns are 4 pixels; a UDG tile occupies 8 pixels.
         */
        print_at(row, VIEW_LEFT * 2, "                    ");
        for (b = 0; b < VIEW_TILES; b++) {
            col = VIEW_LEFT + b;
            tile = getcell(px + a - VIEW_ANCHOR,
                           py + b - VIEW_ANCHOR);
            if (tile == '#')
                udg_draw(1, row, col);
            else if (tile == 'O')
                udg_draw(2, row, col);
        }
    }
    /* Player remains at a fixed screen position while maze scrolls. */
    udg_draw(0, VIEW_TOP + VIEW_ANCHOR, VIEW_LEFT + VIEW_ANCHOR);
    counter();
}

int maze_key(int menu);

int postgame(int won)
{
    int key;
    cls();
    if (won) {
        print_at(1, 0, "You did it, but the forces of");
        print_at(2, 0, "Xzardiarl have launched a");
        print_at(3, 0, "counterattack. You must do it");
        print_at(4, 0, "all over again. Sorry.");
    } else {
        print_at(1, 0, "The forces of Xzardiarl have");
        print_at(2, 0, "defeated you. The planet of");
        print_at(3, 0, "Uitrodef is doomed to");
        print_at(4, 0, "domination, and it's all down");
        print_at(5, 0, "to you.");
    }
    print_at(19, 0, "R = replay   Q = exit");
    credits();
    while (1) {
        key = maze_key(1);
        if (key == 'r' || key == 'R')
            return 1;
        if (key == 'q' || key == 'Q')
            return 0;
    }
}

/* Poll the keyboard matrix without touching /dev/tty.  The old code
 * rewrote the kernel's shared tty tail and then called getchar(), stealing
 * characters from a simultaneous shell command (e.g. kill or cls).
 * Wait for key release so one held key generates one move, and sleep one
 * tick between scans so the shell and other jobs continue to run.
 */
int maze_key(int menu)
{
    int key;
    while (1) {
        key = 0;
        if (kbd_down('q')) key = 'q';
        else if (menu) {
            if (kbd_down('r')) key = 'r';
        } else {
            if (kbd_down('z')) key = 'z';
            else if (kbd_down('i')) key = 'i';
            else if (kbd_down('p')) key = 'p';
            else if (kbd_down('0')) key = '0';
        }
        if (key) {
            while (kbd_down(key))
                sleep(1);
            return key;
        }
        sleep(1);
    }
}

int play(void)
{
    int key;
    int nx;
    int ny;
    int q;
    int r;
    int attempts;
    initialize();
    cls();
    game_header();
    credits();
    viewport();
    while (1) {
        key = maze_key(0);
        nx = px;
        ny = py;
        if (key == 'i' || key == 'I')
            ny--;
        else if (key == 'p' || key == 'P')
            ny++;
        else if (key == 'z' || key == 'Z')
            nx++;
        else if (key == 'q' || key == 'Q')
            nx--;
        else if (key == '0')
            return 0;
        if (getcell(nx, ny) != '#') {
            px = nx;
            py = ny;
        }
        if (getcell(px, py) == 'O') {
            setcell(px, py, ' ');
            collected++;
            if (collected == 8)
                return 1;
        }
        /* BASIC's RND*10 >= 7 gives a 30% rock event. */
        if (random_n(10) >= 7) {
            attempts = 0;
            while (attempts < 10) {
                q = 1 + random_n(13);
                r = 1 + random_n(15);
                if (try_rock(q, r))
                    break;
                attempts++;
            }
        }
        viewport();
    }
}

int main(void)
{
    udg_define(0, pawn);
    udg_define(1, rock);
    udg_define(2, object_sprite);
    while (postgame(play())) {
        /* R starts another game directly. */
    }
    return 0;
}
