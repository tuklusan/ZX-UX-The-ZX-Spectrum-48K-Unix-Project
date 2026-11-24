// ============================================================
// Copyright (c) 2026 SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and model
// training prohibited unless separately authorized.
//
// Attribution required: SANYALnet Labs.
// See root LICENSE for full terms.
// ============================================================
/* Shared helpers for interactive C48 applications. */
/* C48 has no include guards: include this once per app. */
/* Runtime declarations are intentional. Normal SDK builds */
/* do not inject declarations through <c48.h>. */
/* ZX-UX local RAM filesystem; no cassette access in applications. */
int open(char *path, int mode);
int creat(char *path, int mode);
int close(int h);
int read(int h, void *p, unsigned int n);
int write(int h, void *p, unsigned int n);
int getchar(void);
int cls(void);
int print_at(int row, int col, char *text);
int ink(int c);
int paper(int c);
int bright(int on);
int inverse(int on);
int plot(int x, int y);
int draw(int x1, int y1, int x2, int y2);
int sleep(unsigned int ticks);
int yield(void);
int strcmp(char *a, char *b);
unsigned int strlen(char *s);
void *memmove(void *d, void *s, unsigned int n);
void *memset(void *d, int c, unsigned int n);

static int app_key(void)
{
    int c;
    c = getchar();
    if (c >= 'A' && c <= 'Z')
        c = c + 32;
    return c;
}

static void app_clear_row(int row);
/* Destructive New requires an affirmative Y. All other keys cancel. */
static int app_confirm_new(void)
{
    app_clear_row(23);
    print_at(23, 1, "NEW: CLEAR DOCUMENT? Y YES / OTHER NO");
    return app_key() == 'y';
}

static void app_putc(int row, int col, int c)
{
    char s[2];
    s[0] = (char)c;
    s[1] = 0;
    print_at(row, col, s);
}

static void app_clear_row(int row)
{
    char blank[33];
    int i;
    for (i = 0; i < 32; i++)
        blank[i] = ' ';
    blank[32] = 0;
    print_at(row, 0, blank);
    print_at(row, 32, blank);
}

static void app_uint_text(char *out, unsigned int value)
{
    char rev[6];
    int n;
    int i;
    n = 0;
    do {
        rev[n] = (char)('0' + value % 10u);
        value = value / 10u;
        n++;
    } while (value != 0u && n < 5);
    for (i = 0; i < n; i++)
        out[i] = rev[n - 1 - i];
    out[n] = 0;
}

static void app_int_text(char *out, int value)
{
    if (value < 0) {
        out[0] = '-';
        app_uint_text(out + 1, (unsigned int)(-value));
    } else {
        app_uint_text(out, (unsigned int)value);
    }
}

static void app_money_text(char *out, unsigned int value)
{
    char num[6];
    int i;
    app_uint_text(num, value);
    out[0] = '$';
    i = 0;
    while (num[i] != 0) {
        out[i + 1] = num[i];
        i++;
    }
    out[i + 1] = 0;
}

static void app_field(int row, int col, char *text,
                      int width, int selected)
{
    char buf[33];
    int i;
    if (width < 0)
        width = 0;
    if (width > 32)
        width = 32;
    i = 0;
    while (i < width && text[i] != 0) {
        buf[i] = text[i];
        i++;
    }
    while (i < width) {
        buf[i] = ' ';
        i++;
    }
    buf[i] = 0;
    if (selected)
        inverse(1);
    print_at(row, col, buf);
    if (selected)
        inverse(0);
}

static int app_readline(int row, int col,
                        char *out, int max)
{
    int c;
    int n;
    n = 0;
    out[0] = 0;
    while (1) {
        c = getchar();
        if (c == 7)
            return 0;
        if (c == 10 || c == 13) {
            out[n] = 0;
            return 1;
        }
        if (c == 8 || c == 12) {
            if (n > 0) {
                n--;
                out[n] = 0;
                app_putc(row, col + n, ' ');
            }
        } else if (c >= 32 && c <= 126 && n < max - 1) {
            out[n] = (char)c;
            n++;
            out[n] = 0;
            app_putc(row, col + n - 1, c);
        }
    }
}

/* Shared filename state and status for all four independent programs. */
char app_filename[48];
char app_notice[48];

static void app_setfile(char *path)
{
    int i;
    i = 0;
    while (path[i] != 0 && i < 47) {
        app_filename[i] = path[i];
        i++;
    }
    app_filename[i] = 0;
    app_notice[0] = 0;
}

static void app_notice_set(char *message)
{
    int i;
    i = 0;
    while (message[i] != 0 && i < 47) {
        app_notice[i] = message[i];
        i++;
    }
    app_notice[i] = 0;
}

/* Type a new path or press ENTER for the shown file; EDIT cancels. */
static int app_choose_file(char *verb)
{
    char buf[48];
    int i;
    app_clear_row(21);
    app_clear_row(22);
    app_clear_row(23);
    print_at(21, 0, "TYPE PATH OR ENTER=SHOWN; CAPS+1=CANCEL");
    print_at(22, 0, "FILE: ");
    print_at(22, 6, app_filename);
    print_at(23, 0, verb);
    if (!app_readline(23, 9, buf, 48))
        return 0;
    if (buf[0] != 0) {
        i = 0;
        while (buf[i] != 0) {
            app_filename[i] = buf[i];
            i++;
        }
        app_filename[i] = 0;
    }
    return 1;
}

static int app_save_file(char *data, unsigned int size)
{
    int fd;
    int n;
    unsigned int done;
    int ok;
    fd = creat(app_filename, 15);
    if (fd < 0)
        return 0;
    done = 0u;
    ok = 1;
    while (done < size) {
        n = write(fd, data + done, size - done);
        if (n <= 0) {
            ok = 0;
            break;
        }
        done = done + (unsigned int)n;
    }
    if (close(fd) < 0)
        ok = 0;
    return ok;
}

/* -1: I/O error; -2: file exceeds capacity; >=0: byte count. */
static int app_load_file(char *data, unsigned int cap)
{
    int fd;
    int n;
    int extra;
    char tail;
    unsigned int done;
    fd = open(app_filename, 0);
    if (fd < 0)
        return -1;
    done = 0u;
    while (done < cap) {
        n = read(fd, data + done, cap - done);
        if (n < 0) {
            close(fd);
            return -1;
        }
        if (n == 0)
            break;
        done = done + (unsigned int)n;
    }
    extra = read(fd, &tail, 1u);
    if (close(fd) < 0 || extra < 0)
        return -1;
    if (extra != 0)
        return -2;
    return (int)done;
}

static int app_decimal(char *text, int max)
{
    int n;
    int i;
    n = 0;
    i = 0;
    if (text[0] == 0)
        return -1;
    while (text[i] != 0) {
        if (text[i] < '0' || text[i] > '9')
            return -1;
        n = n * 10 + text[i] - '0';
        if (n > max)
            return -1;
        i++;
    }
    return n;
}
