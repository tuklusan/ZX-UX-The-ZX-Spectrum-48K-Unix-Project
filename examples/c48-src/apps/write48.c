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
#include "appapi.h"
int lseek(int fd, int offset, int whence);

char wr_doc[641];
char wr_line[61];
int wr_pmode;
int wr_fast_drawn;
int wr_dirty_row;
int wr_drawview;
int wr_oldcursor;
/* Visible-row tracking avoids duplicate 1140-byte screen buffers. */
int wr_ncursor;
int wr_rowlen[19];
int wr_rowpos[19];
int wr_after;
int wr_len;
int wr_cur;
int wr_view;
int wr_insert;
int wr_stat;

void wr_seed(void)
{
    memmove(wr_doc, "SIR CLIVE SINCLAIR\nCambridge, England - CV, 1992\n\nPROFILE\nInventor dedicated to affordable home computing.\n\nEXPERIENCE\nSINCLAIR RESEARCH | Founder, 1979-\nCreated the ZX80 (1980), ZX81 (1981), ZX Spectrum (1982), and Sinclair QL (1984).\n\nSINCLAIR RADIONICS | Founder, 1961-79\nDeveloped compact radios, calculators and pocket TVs.\n\nMILESTONES\n1982  ZX Spectrum introduced.\n1983  Knighted for services to industry.\n1985  Sinclair C5 electric vehicle unveiled.\n1986  Computer business sold to Amstrad.\n\nINTERESTS\nMiniaturisation, electric transport, technology for all.\n", 567u);
    wr_len = 566;
}

/* Plain ASCII text, compatible with vi and cat on ZX-UX. */
void wr_save(void)
{
    if (!app_choose_file("SAVE>")) {
        wr_stat = -1;
        return;
    }
    if (app_save_file(wr_doc, (unsigned int)wr_len))
        app_notice_set("SAVED TO RAM");
    else
        app_notice_set("SAVE FAILED");
    wr_stat = -1;
}

/* ZX-UX RAM is exceptionally small. Validate the complete file first,
   then rewind the same open handle and load directly into the document.
   Invalid/missing/oversize files cannot replace the user's current text.
   The two passes are against the same RAM inode; close only at the end. */
void wr_load(void)
{
    int fd;
    int n;
    int got;
    int i;
    int done;
    char sample[64];
    if (!app_choose_file("LOAD>")) {
        wr_stat = -1;
        return;
    }
    fd = open(app_filename, 0);
    if (fd < 0) {
        app_notice_set("LOAD FAILED");
        wr_stat = -1;
        return;
    }
    n = 0;
    while (1) {
        got = read(fd, sample, 64u);
        if (got < 0) {
            app_notice_set("LOAD FAILED");
            close(fd);
            wr_stat = -1;
            return;
        }
        if (got == 0)
            break;
        if (n + got > 640) {
            app_notice_set("LOAD FAILED OR TOO LARGE");
            close(fd);
            wr_stat = -1;
            return;
        }
        for (i = 0; i < got; i++) {
            if ((sample[i] < 32 || sample[i] > 126) &&
                sample[i] != 10) {
                app_notice_set("BAD TEXT FILE");
                close(fd);
                wr_stat = -1;
                return;
            }
        }
        n = n + got;
    }
    if (lseek(fd, 0, 0) < 0) {
        app_notice_set("LOAD FAILED");
        close(fd);
        wr_stat = -1;
        return;
    }
    done = 0;
    while (done < n) {
        got = read(fd, wr_doc + done, (unsigned int)(n - done));
        if (got <= 0) {
            app_notice_set("LOAD FAILED");
            close(fd);
            wr_stat = -1;
            return;
        }
        done = done + got;
    }
    if (close(fd) < 0) {
        app_notice_set("LOAD FAILED");
        wr_stat = -1;
        return;
    }
    wr_doc[n] = 0;
    wr_len = n;
    wr_cur = 0;
    wr_view = 0;
    wr_insert = 0;
    wr_stat = -1;
    app_notice_set("LOADED FROM RAM");
}

void wr_new(void)
{
    if (!app_confirm_new()) {
        app_notice_set("NEW CANCELLED");
        wr_stat = -1;
        return;
    }
    wr_doc[0] = 0;
    wr_len = 0;
    wr_cur = 0;
    wr_view = 0;
    wr_insert = 0;
    wr_ncursor = -1;
    wr_oldcursor = -1;
    wr_drawview = -1;
    wr_stat = -1;
    app_notice_set("NEW BLANK DOCUMENT");
}

void wr_insert_char(int c)
{
    int n;
    if (wr_len >= 640)
        return;
    n = wr_len - wr_cur;
    if (n > 0)
        memmove(wr_doc + wr_cur + 1,
                wr_doc + wr_cur, (unsigned int)n);
    wr_doc[wr_cur] = (char)c;
    wr_len++;
    wr_cur++;
    wr_doc[wr_len] = 0;
}

void wr_delete_at(int pos)
{
    int n;
    if (pos < 0 || pos >= wr_len)
        return;
    n = wr_len - pos;
    memmove(wr_doc + pos, wr_doc + pos + 1, (unsigned int)n);
    wr_len--;
    if (wr_cur > wr_len)
        wr_cur = wr_len;
}

int wr_word_len(int pos)
{
    int n;
    n = 0;
    while (pos + n < wr_len && wr_doc[pos + n] != ' ' &&
           wr_doc[pos + n] != '\n' && n < 60)
        n++;
    return n;
}

void wr_blank(void)
{
    int i;
    wr_ncursor = -1;
    wr_after = wr_view;
    for (i = 0; i < 19; i++) {
        wr_rowlen[i] = 0;
        wr_rowpos[i] = -1;
    }
}

void wr_emptyline(void)
{
    memset(wr_line, ' ', 60u);
    wr_line[60] = 0;
}

void wr_paint(int row, int display)
{
    int cc;
    int k;
    if (!display)
        return;
    if (wr_pmode && wr_view == wr_drawview &&
        (wr_oldcursor < 0 || wr_oldcursor / 60 != row) &&
        (wr_ncursor < 0 || wr_ncursor / 60 != row))
        return;
    inverse(0);
    print_at(row + 2, 2, wr_line);
    if (wr_ncursor >= row * 60 && wr_ncursor < row * 60 + 60) {
        k = wr_ncursor - row * 60;
        cc = wr_line[k];
        if (cc == ' ')
            cc = '_';
        inverse(1);
        app_putc(row + 2, k + 2, cc);
        inverse(0);
    }
}

void wr_layout(int first, int pos, int display)
{
    int row;
    int col;
    int n;
    int c;
    row = first;
    col = 0;
    wr_emptyline();
    if (row < 19)
        wr_rowpos[row] = pos;
    while (row < 19 && pos <= wr_len) {
        if (pos == wr_len) {
            wr_rowlen[row] = col;
            if (pos == wr_cur)
                wr_ncursor = row * 60 + col;
            wr_paint(row, display);
            row++;
            break;
        }
        c = wr_doc[pos];
        if (c == '\n') {
            wr_rowlen[row] = col;
            if (pos == wr_cur)
                wr_ncursor = row * 60 + col;
            wr_paint(row, display);
            row++;
            col = 0;
            pos++;
            wr_emptyline();
            if (row < 19)
                wr_rowpos[row] = pos;
        } else {
            if (c != ' ' && col > 0 &&
                (pos == 0 || wr_doc[pos - 1] == ' ' ||
                 wr_doc[pos - 1] == '\n')) {
                n = wr_word_len(pos);
                if (col + n > 60) {
                    wr_paint(row, display);
                    row++;
                    col = 0;
                    wr_emptyline();
                    if (row >= 19)
                        break;
                    wr_rowpos[row] = pos;
                }
            }
            wr_line[col] = (char)c;
            if (pos == wr_cur)
                wr_ncursor = row * 60 + col;
            col++;
            pos++;
            wr_rowlen[row] = col;
            if (col >= 60) {
                wr_paint(row, display);
                row++;
                col = 0;
                wr_emptyline();
                if (row < 19)
                    wr_rowpos[row] = pos;
            }
        }
    }
    wr_after = pos;
    if (display) {
        wr_emptyline();
        while (row < 19) {
            wr_paint(row, 1);
            row++;
        }
    }
}

void wr_build(int display)
{
    wr_blank();
    wr_layout(0, wr_view, display);
}





void wr_status(void)
{
    if (wr_stat == wr_insert)
        return;
    app_clear_row(21);
    app_clear_row(22);
    app_clear_row(23);
    if (wr_insert) {
        print_at(21, 1, "INSERT: CAPS+1 CMD BS DEL ENTER NL");
    } else {
        print_at(21, 1, "CMD: I INS 5/8 MOVE 7/6 PG X DEL");
        print_at(22, 1, "F FIND G TOP N NEW S SAVE L LOAD Q QUIT");
    }
    if (app_notice[0] != 0)
        print_at(23, 1, app_notice);
    else
        print_at(23, 1, "640 CHAR MAX - EDIT IN RAM");
    wr_stat = wr_insert;
}



int wr_down_view(void)
{
    int next;
    next = wr_rowpos[1];
    if (next < 0 || next <= wr_view)
        next = wr_view + wr_rowlen[0];
    if (next < wr_len && wr_doc[next] == '\n')
        next++;
    if (next <= wr_view && wr_view < wr_len)
        next = wr_view + 1;
    if (next > wr_len)
        next = wr_len;
    if (next <= wr_view)
        return 0;
    wr_view = next;
    return 1;
}

void wr_render(void)
{
    int n;
    wr_build(0);
    n = 0;
    while (wr_ncursor < 0 && wr_cur > wr_view && n < 19) {
        if (!wr_down_view())
            break;
        wr_build(0);
        n++;
    }
    if (wr_ncursor < 0 && wr_cur < wr_view) {
        wr_view = wr_cur - 120;
        if (wr_view < 0)
            wr_view = 0;
        wr_build(0);
    }
    if (wr_ncursor < 0) {
        wr_view = wr_cur;
        wr_build(0);
    }
    wr_build(1);
    wr_drawview = wr_view;
    wr_oldcursor = wr_ncursor;
    wr_status();
}

void wr_start(void)
{
    cls();
    paper(0);
    ink(7);
    bright(1);
    print_at(0, 14, "WRITE48 - 1992 RESUME");
    bright(0);
    wr_ncursor = -1;
    wr_oldcursor = -1;
    wr_drawview = -1;
    wr_stat = -1;
}

void wr_ensure(void)
{
    if (wr_cur < wr_view) {
        wr_view = wr_cur - 120;
        if (wr_view < 0)
            wr_view = 0;
    }
    if (wr_cur > wr_view + 850) {
        wr_view = wr_cur - 400;
        if (wr_view < 0)
            wr_view = 0;
    }
}

int wr_nextrow(int pos)
{
    int col;
    int n;
    int c;
    col = 0;
    while (pos < wr_len) {
        c = wr_doc[pos];
        if (c == '\n')
            return pos + 1;
        if (c != ' ' && col > 0 &&
            (pos == 0 || wr_doc[pos - 1] == ' ' ||
             wr_doc[pos - 1] == '\n')) {
            n = wr_word_len(pos);
            if (col + n > 60)
                return pos;
        }
        col++;
        pos++;
        if (col >= 60)
            return pos;
    }
    return pos;
}

int wr_prevrow(int pos)
{
    int p;
    int prev;
    int next;
    if (pos <= 0)
        return 0;
    p = 0;
    prev = 0;
    while (p < pos && p < wr_len) {
        next = wr_nextrow(p);
        if (next <= p)
            break;
        if (next >= pos)
            return p;
        prev = p;
        p = next;
    }
    return prev;
}

void wr_page(int down)
{
    int p;
    int rows;
    int goal;
    if (down) {
        if (wr_after < wr_len) {
            wr_view = wr_after;
            wr_cur = wr_view;
        } else {
            wr_cur = wr_len;
        }
        return;
    }
    if (wr_view <= 0) {
        wr_view = 0;
        wr_cur = 0;
        return;
    }
    p = 0;
    rows = 0;
    while (p < wr_view && p < wr_len) {
        p = wr_nextrow(p);
        rows++;
    }
    goal = rows - 19;
    if (goal < 0)
        goal = 0;
    p = 0;
    while (goal > 0 && p < wr_len) {
        p = wr_nextrow(p);
        goal--;
    }
    wr_view = p;
    wr_cur = p;
}

int wr_match(int pos, char *q)
{
    int i;
    i = 0;
    while (q[i] != 0) {
        if (pos + i >= wr_len)
            return 0;
        if (wr_doc[pos + i] != q[i])
            return 0;
        i++;
    }
    return i > 0;
}

void wr_find(void)
{
    char q[24];
    int p;
    app_clear_row(23);
    print_at(23, 1, "FIND CAPS+1 CANCEL> ");
    if (!app_readline(23, 21, q, 24)) {
        wr_stat = -1;
        return;
    }
    p = wr_cur + 1;
    while (p < wr_len && !wr_match(p, q))
        p++;
    if (p >= wr_len) {
        p = 0;
        while (p <= wr_cur && p < wr_len &&
               !wr_match(p, q))
            p++;
        if (p > wr_cur)
            p = wr_len;
    }
    if (p < wr_len)
        wr_cur = p;
    wr_stat = -1;
}









/* Safe partial painting: an edited hard-ended line has no soft-wrap
   neighbours to reflow, and still has spare columns. */
int wr_local_edit(void)
{
    int row;
    int pos;
    if (wr_ncursor < 0)
        return 0;
    row = wr_ncursor / 60;
    if (row >= 19 || wr_rowlen[row] >= 58)
        return 0;
    pos = wr_rowpos[row];
    if (pos > 0 && wr_doc[pos - 1] != '\n')
        return 0;
    pos = pos + wr_rowlen[row];
    return pos >= wr_len || wr_doc[pos] == '\n';
}

/* Fast path for edits on short, hard-ended lines.  The 19-row layout
   cache remains valid, so ordinary typing needs no document reflow.
   Wrapped or nearly-full lines still use the complete renderer. */
int wr_quick_row(void)
{
    int row;
    int begin;
    int end;
    if (wr_ncursor < 0)
        return -1;
    row = wr_ncursor / 60;
    if (row >= 19 || wr_rowlen[row] >= 57)
        return -1;
    begin = wr_rowpos[row];
    if (begin < 0)
        return -1;
    end = begin + wr_rowlen[row];
    /* On a soft wrap, leave the boundary untouched even after a
       one-character deletion (the more difficult direction). */
    if (end < wr_len && wr_doc[end] != '\n' &&
        wr_rowlen[row] - 1 + wr_word_len(end) <= 60)
        return -1;
    if (row > 0 && begin > 0 && wr_doc[begin - 1] != '\n' &&
        wr_rowlen[row - 1] + wr_word_len(begin) - 1 <= 60)
        return -1;
    if (wr_cur < begin || wr_cur > end)
        return -1;
    return row;
}

void wr_quick_paint(int row)
{
    int i;
    int begin;
    wr_emptyline();
    begin = wr_rowpos[row];
    for (i = 0; i < wr_rowlen[row]; i++)
        wr_line[i] = wr_doc[begin + i];
    wr_pmode = 0;
    wr_paint(row, 1);
}

void wr_quick_shift(int row, int step)
{
    int i;
    for (i = row + 1; i < 19; i++) {
        if (wr_rowpos[i] >= 0)
            wr_rowpos[i] = wr_rowpos[i] + step;
    }
    wr_after = wr_after + step;
}

int wr_quick_insert(int c)
{
    int row;
    int col;
    int oldlen;
    row = wr_quick_row();
    if (row < 0 || wr_len >= 640)
        return 0;
    col = wr_ncursor % 60;
    oldlen = wr_rowlen[row];
    wr_insert_char(c);
    wr_rowlen[row] = oldlen + 1;
    wr_quick_shift(row, 1);
    wr_ncursor++;
    wr_oldcursor = wr_ncursor;
    if (col == oldlen) {
        inverse(0);
        app_putc(row + 2, col + 2, c);
        inverse(1);
        app_putc(row + 2, col + 3, '_');
        inverse(0);
    } else {
        wr_quick_paint(row);
    }
    wr_fast_drawn = 1;
    return 1;
}

int wr_quick_delete(void)
{
    int row;
    row = wr_quick_row();
    if (row < 0 || wr_cur <= wr_rowpos[row])
        return 0;
    wr_cur--;
    wr_delete_at(wr_cur);
    wr_rowlen[row]--;
    wr_quick_shift(row, -1);
    wr_ncursor--;
    wr_oldcursor = wr_ncursor;
    wr_quick_paint(row);
    wr_fast_drawn = 1;
    return 1;
}

int wr_quick_move(int step)
{
    int row;
    int col;
    int oldchar;
    int newchar;
    if (wr_ncursor < 0)
        return 0;
    row = wr_ncursor / 60;
    col = wr_ncursor % 60;
    if (row >= 19 || (step < 0 && col <= 0) ||
        (step > 0 && col >= wr_rowlen[row]))
        return 0;
    oldchar = wr_doc[wr_cur];
    if (oldchar == '\n' || oldchar == 0)
        oldchar = ' ';
    inverse(0);
    app_putc(row + 2, col + 2, oldchar);
    wr_cur = wr_cur + step;
    wr_ncursor = wr_ncursor + step;
    wr_oldcursor = wr_ncursor;
    newchar = wr_doc[wr_cur];
    if (newchar == '\n' || newchar == ' ' || newchar == 0)
        newchar = '_';
    inverse(1);
    app_putc(row + 2, col + 2 + step, newchar);
    inverse(0);
    wr_fast_drawn = 1;
    return 1;
}

int wr_insert_key(void)
{
    int c;
    c = getchar();
    if (c == 7) {
        wr_insert = 0;
        wr_pmode = 1;
        return 1;
    }
    if (c == 8 || c == 12) {
        if (wr_cur <= 0)
            return 0;
        if (wr_local_edit() && wr_ncursor % 60 > 0)
            wr_pmode = 1;
        if (wr_quick_delete())
            return 1;
        wr_dirty_row = wr_ncursor / 60;
        if (wr_ncursor % 60 == 0 && wr_dirty_row > 0)
            wr_dirty_row--;
        wr_cur--;
        wr_delete_at(wr_cur);
        return 1;
    }
    if (c == 10 || c == 13) {
        if (wr_len >= 640)
            return 0;
        wr_insert_char('\n');
        return 1;
    }
    if (c >= 32 && c <= 126) {
        if (wr_len >= 640)
            return 0;
        if (wr_local_edit())
            wr_pmode = 1;
        if (wr_quick_insert(c))
            return 1;
        wr_dirty_row = wr_ncursor / 60;
        wr_insert_char(c);
        return 1;
    }
    return 0;
}

int wr_command(int key)
{
    int old_cur;
    int old_view;
    if (key == 'q')
        return -1;
    if (key == '8' && wr_cur < wr_len) {
        if (wr_quick_move(1))
            return 1;
        wr_cur++;
        wr_pmode = 1;
        return 1;
    }
    if ((key == '5' || key == 'h') && wr_cur > 0) {
        if (wr_quick_move(-1))
            return 1;
        wr_cur--;
        wr_pmode = 1;
        if (wr_cur < wr_view)
            wr_view = wr_prevrow(wr_view);
        return 1;
    }
    if (key == '6' || key == '7') {
        old_cur = wr_cur;
        old_view = wr_view;
        wr_page(key == '6');
        return wr_cur != old_cur || wr_view != old_view;
    }
    if (key == 'i') {
        wr_insert = 1;
        wr_pmode = 1;
        wr_fast_drawn = 1;
        return 1;
    }
    if (key == 'x' && wr_cur < wr_len) {
        if (wr_local_edit())
            wr_pmode = 1;
        wr_delete_at(wr_cur);
        return 1;
    }
    if (key == 'n') {
        wr_new();
        return 1;
    }
    if (key == 's') {
        wr_save();
        return 1;
    }
    if (key == 'l') {
        wr_load();
        return 1;
    }
    if (key == 'f') {
        wr_find();
        return 1;
    }
    if (key == 'g' && (wr_cur != 0 || wr_view != 0)) {
        wr_cur = 0;
        wr_view = 0;
        return 1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    int key;
    int changed;
    wr_seed();
    app_setfile("/tmp/write48.txt");
    wr_cur = 0;
    wr_view = 0;
    wr_insert = 0;
    wr_start();
    wr_render();
    if (argc > 1 && strcmp(argv[1], "verify") == 0)
        return 0;
    while (1) {
        wr_fast_drawn = 0;
        wr_dirty_row = -1;
        wr_pmode = 0;
        if (wr_insert) {
            changed = wr_insert_key();
        } else {
            key = app_key();
            changed = wr_command(key);
            if (changed < 0)
                return 0;
        }
        if (!changed)
            continue;
        if (app_notice[0] != 0 &&
            (wr_insert || (key != 's' && key != 'l' && key != 'n'))) {
            app_notice[0] = 0;
            wr_stat = -1;
        }
        if (wr_fast_drawn) {
            wr_status();
        } else {
            wr_ensure();
            wr_render();
        }
    }
}
