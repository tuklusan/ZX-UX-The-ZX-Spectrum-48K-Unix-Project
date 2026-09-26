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
#include "gameapi.h"

char ch_board[65] =
    "rnbqkbnr"
    "pppppppp"
    "........"
    "........"
    "........"
    "........"
    "PPPPPPPP"
    "RNBQKBNR";
int ch_side;
int ch_ep;
int ch_wk;
int ch_wq;
int ch_bk;
int ch_bq;
int ch_turns;

int ch_white(int p)
{
    return p >= 'A' && p <= 'Z';
}

int ch_black(int p)
{
    return p >= 'a' && p <= 'z';
}

int ch_same(int p, int side)
{
    if (side == 0)
        return ch_white(p);
    return ch_black(p);
}

int ch_abs(int value)
{
    if (value < 0)
        return -value;
    return value;
}

int ch_path(int from, int to, int dx, int dy)
{
    int x;
    int y;
    int tx;
    int ty;
    x = from % 8 + dx;
    y = from / 8 + dy;
    tx = to % 8;
    ty = to / 8;
    while (x != tx || y != ty) {
        if (ch_board[y * 8 + x] != '.')
            return 0;
        x = x + dx;
        y = y + dy;
    }
    return 1;
}

int ch_attackp(int from, int to, int side)
{
    int p;
    int fx;
    int fy;
    int tx;
    int ty;
    int dx;
    int dy;
    int ax;
    int ay;
    p = ch_board[from];
    if (!ch_same(p, side))
        return 0;
    fx = from % 8;
    fy = from / 8;
    tx = to % 8;
    ty = to / 8;
    dx = tx - fx;
    dy = ty - fy;
    ax = ch_abs(dx);
    ay = ch_abs(dy);
    if (p == 'P')
        return dy == -1 && ax == 1;
    if (p == 'p')
        return dy == 1 && ax == 1;
    if (p == 'N' || p == 'n')
        return (ax == 1 && ay == 2) ||
            (ax == 2 && ay == 1);
    if (p == 'B' || p == 'b') {
        if (ax != ay || ax == 0)
            return 0;
        return ch_path(from, to, dx / ax, dy / ay);
    }
    if (p == 'R' || p == 'r') {
        if (dx != 0 && dy != 0)
            return 0;
        if (dx == 0 && dy == 0)
            return 0;
        if (dx == 0)
            return ch_path(from, to, 0, dy / ay);
        return ch_path(from, to, dx / ax, 0);
    }
    if (p == 'Q' || p == 'q') {
        if (ax == ay && ax != 0)
            return ch_path(from, to, dx / ax, dy / ay);
        if (dx == 0 && dy != 0)
            return ch_path(from, to, 0, dy / ay);
        if (dy == 0 && dx != 0)
            return ch_path(from, to, dx / ax, 0);
        return 0;
    }
    if (p == 'K' || p == 'k')
        return ax <= 1 && ay <= 1 && ax + ay > 0;
    return 0;
}

int ch_attacked(int square, int side)
{
    int i;
    for (i = 0; i < 64; i++) {
        if (ch_attackp(i, square, side))
            return 1;
    }
    return 0;
}

int ch_check(int side)
{
    int i;
    int king;
    king = -1;
    for (i = 0; i < 64; i++) {
        if (side == 0 && ch_board[i] == 'K')
            king = i;
        if (side == 1 && ch_board[i] == 'k')
            king = i;
    }
    if (king < 0)
        return 1;
    return ch_attacked(king, 1 - side);
}

int ch_castle(int from, int to, int side)
{
    if (side == 0 && from == 60 && to == 62 && ch_wk) {
        if (ch_board[61] != '.' || ch_board[62] != '.')
            return 0;
        if (ch_attacked(60, 1) || ch_attacked(61, 1))
            return 0;
        if (ch_attacked(62, 1))
            return 0;
        return ch_board[63] == 'R';
    }
    if (side == 0 && from == 60 && to == 58 && ch_wq) {
        if (ch_board[59] != '.' || ch_board[58] != '.')
            return 0;
        if (ch_board[57] != '.')
            return 0;
        if (ch_attacked(60, 1) || ch_attacked(59, 1))
            return 0;
        if (ch_attacked(58, 1))
            return 0;
        return ch_board[56] == 'R';
    }
    if (side == 1 && from == 4 && to == 6 && ch_bk) {
        if (ch_board[5] != '.' || ch_board[6] != '.')
            return 0;
        if (ch_attacked(4, 0) || ch_attacked(5, 0))
            return 0;
        if (ch_attacked(6, 0))
            return 0;
        return ch_board[7] == 'r';
    }
    if (side == 1 && from == 4 && to == 2 && ch_bq) {
        if (ch_board[3] != '.' || ch_board[2] != '.')
            return 0;
        if (ch_board[1] != '.')
            return 0;
        if (ch_attacked(4, 0) || ch_attacked(3, 0))
            return 0;
        if (ch_attacked(2, 0))
            return 0;
        return ch_board[0] == 'r';
    }
    return 0;
}

int ch_pseudo(int from, int to, int side)
{
    int p;
    int t;
    int fx;
    int fy;
    int tx;
    int ty;
    int dx;
    int dy;
    int ax;
    int ay;
    if (from < 0 || from > 63 || to < 0 || to > 63)
        return 0;
    if (from == to)
        return 0;
    p = ch_board[from];
    t = ch_board[to];
    if (!ch_same(p, side) || ch_same(t, side))
        return 0;
    fx = from % 8;
    fy = from / 8;
    tx = to % 8;
    ty = to / 8;
    dx = tx - fx;
    dy = ty - fy;
    ax = ch_abs(dx);
    ay = ch_abs(dy);
    if (p == 'P') {
        if (dx == 0 && dy == -1 && t == '.')
            return 1;
        if (dx == 0 && dy == -2 && fy == 6 && t == '.') {
            if (ch_board[from - 8] == '.')
                return 1;
        }
        if (dy == -1 && ax == 1) {
            if (ch_black(t) || to == ch_ep)
                return 1;
        }
        return 0;
    }
    if (p == 'p') {
        if (dx == 0 && dy == 1 && t == '.')
            return 1;
        if (dx == 0 && dy == 2 && fy == 1 && t == '.') {
            if (ch_board[from + 8] == '.')
                return 1;
        }
        if (dy == 1 && ax == 1) {
            if (ch_white(t) || to == ch_ep)
                return 1;
        }
        return 0;
    }
    if (p == 'K' || p == 'k') {
        if (ax <= 1 && ay <= 1)
            return 1;
        if (ay == 0 && ax == 2)
            return ch_castle(from, to, side);
        return 0;
    }
    return ch_attackp(from, to, side);
}

int ch_promote(int p, int side)
{
    if (p != 'q' && p != 'r' && p != 'b' && p != 'n')
        p = 'q';
    if (side == 0)
        p = p - 32;
    return p;
}

int ch_legal(int from, int to, int prom, int apply)
{
    int side;
    int epcap;
    int rookfrom;
    int rookto;
    int bad;
    int oldep;
    int oldwk;
    int oldwq;
    int oldbk;
    int oldbq;
    char moving;
    char target;
    char epold;
    char rook;
    char rookold;
    side = ch_side;
    if (!ch_pseudo(from, to, side))
        return 0;
    moving = ch_board[from];
    target = ch_board[to];
    epcap = -1;
    rookfrom = -1;
    rookto = -1;
    epold = '.';
    rook = '.';
    rookold = '.';
    oldep = ch_ep;
    oldwk = ch_wk;
    oldwq = ch_wq;
    oldbk = ch_bk;
    oldbq = ch_bq;
    if ((moving == 'P' || moving == 'p') &&
        target == '.' && to == ch_ep) {
        if (side == 0)
            epcap = to + 8;
        else
            epcap = to - 8;
        epold = ch_board[epcap];
        ch_board[epcap] = '.';
    }
    ch_board[from] = '.';
    ch_board[to] = moving;
    if ((moving == 'K' || moving == 'k') &&
        ch_abs(to - from) == 2) {
        if (to == 62) {
            rookfrom = 63;
            rookto = 61;
        }
        if (to == 58) {
            rookfrom = 56;
            rookto = 59;
        }
        if (to == 6) {
            rookfrom = 7;
            rookto = 5;
        }
        if (to == 2) {
            rookfrom = 0;
            rookto = 3;
        }
        rook = ch_board[rookfrom];
        rookold = ch_board[rookto];
        ch_board[rookfrom] = '.';
        ch_board[rookto] = rook;
    }
    if (moving == 'P' && to / 8 == 0)
        ch_board[to] = (char)ch_promote(prom, side);
    if (moving == 'p' && to / 8 == 7)
        ch_board[to] = (char)ch_promote(prom, side);
    bad = ch_check(side);
    if (bad || !apply) {
        ch_board[from] = moving;
        ch_board[to] = target;
        if (epcap >= 0)
            ch_board[epcap] = epold;
        if (rookfrom >= 0) {
            ch_board[rookfrom] = rook;
            ch_board[rookto] = rookold;
        }
        ch_ep = oldep;
        ch_wk = oldwk;
        ch_wq = oldwq;
        ch_bk = oldbk;
        ch_bq = oldbq;
        if (bad)
            return 0;
        return 1;
    }
    if (moving == 'K') {
        ch_wk = 0;
        ch_wq = 0;
    }
    if (moving == 'k') {
        ch_bk = 0;
        ch_bq = 0;
    }
    if (from == 63 || to == 63)
        ch_wk = 0;
    if (from == 56 || to == 56)
        ch_wq = 0;
    if (from == 7 || to == 7)
        ch_bk = 0;
    if (from == 0 || to == 0)
        ch_bq = 0;
    ch_ep = -1;
    if ((moving == 'P' || moving == 'p') &&
        ch_abs(to - from) == 16)
        ch_ep = (from + to) / 2;
    return 1;
}

int ch_try(int from, int x, int y)
{
    int to;
    if (x < 0 || x > 7 || y < 0 || y > 7)
        return 0;
    to = y * 8 + x;
    return ch_legal(from, to, 'q', 0);
}

int ch_ray(int from, int dx, int dy)
{
    int x;
    int y;
    int to;
    x = from % 8 + dx;
    y = from / 8 + dy;
    while (x >= 0 && x < 8 && y >= 0 && y < 8) {
        to = y * 8 + x;
        if (ch_legal(from, to, 'q', 0))
            return 1;
        if (ch_board[to] != '.')
            return 0;
        x = x + dx;
        y = y + dy;
    }
    return 0;
}

int ch_pieceany(int from)
{
    int p;
    int x;
    int y;
    p = ch_board[from];
    x = from % 8;
    y = from / 8;
    if (p == 'P') {
        if (ch_try(from, x, y - 1))
            return 1;
        if (ch_try(from, x, y - 2))
            return 1;
        if (ch_try(from, x - 1, y - 1))
            return 1;
        return ch_try(from, x + 1, y - 1);
    }
    if (p == 'p') {
        if (ch_try(from, x, y + 1))
            return 1;
        if (ch_try(from, x, y + 2))
            return 1;
        if (ch_try(from, x - 1, y + 1))
            return 1;
        return ch_try(from, x + 1, y + 1);
    }
    if (p == 'N' || p == 'n') {
        if (ch_try(from, x - 2, y - 1))
            return 1;
        if (ch_try(from, x - 2, y + 1))
            return 1;
        if (ch_try(from, x + 2, y - 1))
            return 1;
        if (ch_try(from, x + 2, y + 1))
            return 1;
        if (ch_try(from, x - 1, y - 2))
            return 1;
        if (ch_try(from, x - 1, y + 2))
            return 1;
        if (ch_try(from, x + 1, y - 2))
            return 1;
        return ch_try(from, x + 1, y + 2);
    }
    if (p == 'K' || p == 'k') {
        if (ch_try(from, x - 1, y - 1))
            return 1;
        if (ch_try(from, x, y - 1))
            return 1;
        if (ch_try(from, x + 1, y - 1))
            return 1;
        if (ch_try(from, x - 1, y))
            return 1;
        if (ch_try(from, x + 1, y))
            return 1;
        if (ch_try(from, x - 1, y + 1))
            return 1;
        if (ch_try(from, x, y + 1))
            return 1;
        if (ch_try(from, x + 1, y + 1))
            return 1;
        if (ch_try(from, x - 2, y))
            return 1;
        return ch_try(from, x + 2, y);
    }
    if (p == 'B' || p == 'b' ||
        p == 'Q' || p == 'q') {
        if (ch_ray(from, -1, -1))
            return 1;
        if (ch_ray(from, 1, -1))
            return 1;
        if (ch_ray(from, -1, 1))
            return 1;
        if (ch_ray(from, 1, 1))
            return 1;
    }
    if (p == 'R' || p == 'r' ||
        p == 'Q' || p == 'q') {
        if (ch_ray(from, -1, 0))
            return 1;
        if (ch_ray(from, 1, 0))
            return 1;
        if (ch_ray(from, 0, -1))
            return 1;
        if (ch_ray(from, 0, 1))
            return 1;
    }
    return 0;
}

int ch_any(int side)
{
    int from;
    int save;
    save = ch_side;
    ch_side = side;
    for (from = 0; from < 64; from++) {
        if (ch_same(ch_board[from], side)) {
            if (ch_pieceany(from)) {
                ch_side = save;
                return 1;
            }
        }
    }
    ch_side = save;
    return 0;
}

int ch_coord(int file, int rank)
{
    if (file < 'a' || file > 'h')
        return -1;
    if (rank < '1' || rank > '8')
        return -1;
    return (8 - (rank - '0')) * 8 + file - 'a';
}

void ch_draw(void)
{
    char text[9];
    int row;
    int col;
    cls();
    print_at(0, 0, "C48 CHESS - move like e2e4");
    print_at(1, 0, "q quits");
    for (row = 0; row < 8; row++) {
        for (col = 0; col < 8; col++)
            text[col] = ch_board[row * 8 + col];
        text[8] = 0;
        game_putc(row + 3, 0, '8' - row);
        print_at(row + 3, 3, text);
    }
    print_at(12, 3, "abcdefgh");
    if (ch_side == 0)
        print_at(15, 0, "White to move:");
    else
        print_at(15, 0, "Black to move:");
    if (ch_check(ch_side))
        print_at(17, 0, "CHECK");
}

int main(void)
{
    int a;
    int b;
    int c;
    int d;
    int from;
    int to;
    int prom;
    int piece;
    ch_side = 0;
    ch_ep = -1;
    ch_wk = 1;
    ch_wq = 1;
    ch_bk = 1;
    ch_bq = 1;
    ch_turns = 0;
    while (1) {
        ch_draw();
        if (!ch_any(ch_side)) {
            if (ch_check(ch_side))
                print_at(19, 0, "CHECKMATE. Press q.");
            else
                print_at(19, 0, "STALEMATE. Press q.");
            while (game_key() != 'q')
                ch_turns++;
            return 0;
        }
        a = game_key();
        if (a == 'q')
            return 0;
        b = game_key();
        c = game_key();
        d = game_key();
        ch_turns++;
        from = ch_coord(a, b);
        to = ch_coord(c, d);
        if (from < 0 || to < 0)
            continue;
        prom = 'q';
        piece = ch_board[from];
        if ((piece == 'P' && to / 8 == 0) ||
            (piece == 'p' && to / 8 == 7)) {
            print_at(19, 0, "Promote q r b n:");
            prom = game_key();
        }
        if (ch_legal(from, to, prom, 1))
            ch_side = 1 - ch_side;
        else {
            print_at(19, 0, "Illegal move.");
        }
    }
}
