// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "gameapi.h"
int udg_define(int slot, unsigned char *data);
int udg_draw(int slot, int row, int col);
#define CH_EMPTY 0
#define CH_PAWN 1
#define CH_KNIGHT 2
#define CH_BISHOP 3
#define CH_ROOK 4
#define CH_QUEEN 5
#define CH_KING 6
#define CH_BLACK 128
#define CH_OFF 255
#define CH_NOMOVE -1
#define CH_MAXMOVES 256
#define CH_INF 30000
#define CH_MATE 29000
unsigned char ch_board[120];
int ch_side;
int ch_ep;
int ch_wk;
int ch_wq;
int ch_bk;
int ch_bq;
int ch_halfmove;
int ch_fullmove;
int ch_turns;
int ch_level;
int ch_computer;
int ch_pending;
char ch_last[5];
int ch_last_state;
unsigned char ch_mfrom[768];
unsigned char ch_mto[768];
unsigned char ch_mpromo[768];
unsigned char ch_mscore[768];
int ch_mcount[4];
int ch_ufrom[5];
int ch_uto[5];
int ch_uepcap[5];
int ch_urookfrom[5];
int ch_urookto[5];
int ch_uolde[5];
int ch_uowk[5];
int ch_uowq[5];
int ch_uobk[5];
int ch_uobq[5];
int ch_uohalf[5];
int ch_uofull[5];
unsigned char ch_umoving[5];
unsigned char ch_utarget[5];
unsigned char ch_uepold[5];
unsigned char ch_urook[5];
unsigned char ch_urookold[5];
int ch_best_from;
int ch_best_to;
int ch_best_promo;
int ch_best_score;
int ch_nodes;
unsigned char ch_kfrom[4];
unsigned char ch_kto[4];
int ch_value[7] = {
    0, 100, 320, 330, 500, 900, 20000
};
unsigned char ch_pst[192] = {
50,50,50,50,55,60,60,30,55,45,40,50,50,50,
50,70,55,55,60,75,60,60,70,80,100,100,100,
100,50,50,50,50,0,10,20,20,10,30,50,55,20,
55,60,65,20,50,65,70,20,55,65,70,20,50,60,
65,10,30,50,50,0,10,20,20,30,40,40,40,40,
55,50,50,40,60,60,60,40,50,60,60,40,55,55,
60,40,50,55,60,40,50,50,50,30,40,40,40,50,
50,50,55,45,50,50,50,45,50,50,50,45,50,50,
50,45,50,50,50,45,50,50,50,55,60,60,60,50,
50,50,50,30,40,40,45,40,50,55,50,40,55,55,
55,50,50,55,55,45,50,55,55,40,50,55,55,40,
50,50,50,30,40,40,45,70,80,60,50,70,70,50,
50,40,30,30,30,30,20,20,10,20,10,10,0,20,
10,10,0,20,10,10,0,20,10,10,0
};
int ch_knight_step[8] = {
    -21, -19, -12, -8, 8, 12, 19, 21
};
int ch_king_step[8] = {
    -11, -10, -9, -1, 1, 9, 10, 11
};
int ch_bishop_step[4] = {-11, -9, 9, 11};
int ch_rook_step[4] = {-10, -1, 1, 10};
unsigned char ch_udg[160] = {
    0,0,0,25,25,31,15,7,
    0,0,0,152,152,248,240,224,
    3,3,3,7,7,15,31,0,
    192,192,192,224,224,240,248,0,
    0,1,3,7,15,31,15,7,
    0,128,192,128,48,248,240,224,
    1,1,7,7,1,1,31,15,
    128,128,224,224,128,128,248,240,
    15,15,15,15,15,63,127,0,
    240,240,240,240,240,252,254,0,
    0,1,1,1,5,14,31,28,
    0,32,192,192,240,240,240,240,
    0,1,3,3,3,7,15,0,
    240,240,224,224,224,240,248,0,
    1,35,33,63,63,7,15,7,
    128,196,132,252,252,224,240,224,
    7,7,7,7,31,63,63,0,
    224,224,224,224,248,252,252,0,
    0,0,0,1,3,1,0,1,
    0,0,128,192,224,192,128,192
};
unsigned char ch_blank[8] = {0,0,0,0,0,0,0,0};
unsigned char ch_piece_tab[28] = {
    128,128,128,128,
    162,163,147,146,
    154,155,157,156,
    148,149,147,146,
    144,145,147,146,
    158,159,161,160,
    150,151,161,160
};
int ch_abs(int value)
{
    if (value < 0)
        return -value;
    return value;
}
int ch_type(int p)
{
    return p & 7;
}
int ch_color(int p)
{
    return p & CH_BLACK;
}
int ch_piece(int p)
{
    return p != CH_EMPTY && p != CH_OFF;
}
int ch_own(int p, int side)
{
    if (!ch_piece(p))
        return 0;
    return ch_color(p) == side;
}
int ch_enemy(int p, int side)
{
    if (!ch_piece(p))
        return 0;
    return ch_color(p) != side;
}
int ch_coord(int file, int rank)
{
    int row;
    int col;
    if (file < 'a' || file > 'h')
        return -1;
    if (rank < '1' || rank > '8')
        return -1;
    row = rank - '0' + 1;
    col = file - 'a' + 1;
    return row * 10 + col;
}
void ch_square_text(int sq, char *text)
{
    int row;
    int col;
    row = sq / 10;
    col = sq % 10;
    text[0] = (char)('a' + col - 1);
    text[1] = (char)('0' + row - 1);
    text[2] = 0;
}
int ch_promo_code(int key)
{
    if (key == 'q')
        return CH_QUEEN;
    if (key == 'r')
        return CH_ROOK;
    if (key == 'b')
        return CH_BISHOP;
    if (key == 'n')
        return CH_KNIGHT;
    return 0;
}
void ch_init_board(void)
{
    int i;
    int r;
    int c;
    int back[8];
    back[0] = CH_ROOK;
    back[1] = CH_KNIGHT;
    back[2] = CH_BISHOP;
    back[3] = CH_QUEEN;
    back[4] = CH_KING;
    back[5] = CH_BISHOP;
    back[6] = CH_KNIGHT;
    back[7] = CH_ROOK;
    for (i = 0; i < 120; i++)
        ch_board[i] = CH_OFF;
    for (r = 2; r <= 9; r++) {
        for (c = 1; c <= 8; c++)
            ch_board[r * 10 + c] = CH_EMPTY;
    }
    for (c = 1; c <= 8; c++) {
        ch_board[20 + c] = (unsigned char)back[c - 1];
        ch_board[30 + c] = CH_PAWN;
        ch_board[80 + c] = CH_PAWN | CH_BLACK;
        ch_board[90 + c] =
            (unsigned char)(back[c - 1] | CH_BLACK);
    }
    ch_side = 0;
    ch_ep = CH_NOMOVE;
    ch_wk = 1;
    ch_wq = 1;
    ch_bk = 1;
    ch_bq = 1;
    ch_halfmove = 0;
    ch_fullmove = 1;
    ch_turns = 0;
    ch_level = 2;
    ch_computer = CH_NOMOVE;
    ch_pending = CH_NOMOVE;
    ch_last[0] = 0;
    ch_last_state = 0;
    ch_nodes = 0;
    ch_best_from = CH_NOMOVE;
    ch_best_to = CH_NOMOVE;
    ch_best_promo = CH_QUEEN;
    ch_best_score = 0;
}
int ch_ray_attack(int from, int to, int step)
{
    int sq;
    sq = from + step;
    while (ch_board[sq] != CH_OFF) {
        if (sq == to)
            return 1;
        if (ch_board[sq] != CH_EMPTY)
            return 0;
        sq = sq + step;
    }
    return 0;
}
int ch_attack_piece(int from, int to, int side)
{
    int p;
    int type;
    int i;
    int step;
    p = ch_board[from];
    if (!ch_own(p, side))
        return 0;
    type = ch_type(p);
    if (type == CH_PAWN) {
        if (side == 0)
            return to == from + 9 || to == from + 11;
        return to == from - 11 || to == from - 9;
    }
    if (type == CH_KNIGHT) {
        for (i = 0; i < 8; i++) {
            if (from + ch_knight_step[i] == to)
                return 1;
        }
        return 0;
    }
    if (type == CH_KING) {
        for (i = 0; i < 8; i++) {
            if (from + ch_king_step[i] == to)
                return 1;
        }
        return 0;
    }
    if (type == CH_BISHOP || type == CH_QUEEN) {
        for (i = 0; i < 4; i++) {
            step = ch_bishop_step[i];
            if (ch_ray_attack(from, to, step))
                return 1;
        }
    }
    if (type == CH_ROOK || type == CH_QUEEN) {
        for (i = 0; i < 4; i++) {
            step = ch_rook_step[i];
            if (ch_ray_attack(from, to, step))
                return 1;
        }
    }
    return 0;
}
int ch_attacked(int square, int side)
{
    int r;
    int c;
    int sq;
    for (r = 2; r <= 9; r++) {
        for (c = 1; c <= 8; c++) {
            sq = r * 10 + c;
            if (ch_attack_piece(sq, square, side))
                return 1;
        }
    }
    return 0;
}
int ch_king_square(int side)
{
    int r;
    int c;
    int sq;
    int p;
    for (r = 2; r <= 9; r++) {
        for (c = 1; c <= 8; c++) {
            sq = r * 10 + c;
            p = ch_board[sq];
            if (ch_own(p, side) &&
                ch_type(p) == CH_KING)
                return sq;
        }
    }
    return CH_NOMOVE;
}
int ch_check(int side)
{
    int king;
    king = ch_king_square(side);
    if (king < 0)
        return 1;
    return ch_attacked(king, side ^ CH_BLACK);
}
int ch_path_clear(int from, int to, int step)
{
    int sq;
    sq = from + step;
    while (sq != to) {
        if (ch_board[sq] != CH_EMPTY)
            return 0;
        sq = sq + step;
    }
    return 1;
}
int ch_castle(int from, int to, int side)
{
    if (side == 0 && from == 25 && to == 27 && ch_wk) {
        if (ch_board[26] || ch_board[27])
            return 0;
        if (ch_board[28] != CH_ROOK)
            return 0;
        if (ch_attacked(25, CH_BLACK))
            return 0;
        if (ch_attacked(26, CH_BLACK))
            return 0;
        return !ch_attacked(27, CH_BLACK);
    }
    if (side == 0 && from == 25 && to == 23 && ch_wq) {
        if (ch_board[24] || ch_board[23] || ch_board[22])
            return 0;
        if (ch_board[21] != CH_ROOK)
            return 0;
        if (ch_attacked(25, CH_BLACK))
            return 0;
        if (ch_attacked(24, CH_BLACK))
            return 0;
        return !ch_attacked(23, CH_BLACK);
    }
    if (side == CH_BLACK && from == 95 &&
        to == 97 && ch_bk) {
        if (ch_board[96] || ch_board[97])
            return 0;
        if (ch_board[98] != (CH_ROOK | CH_BLACK))
            return 0;
        if (ch_attacked(95, 0))
            return 0;
        if (ch_attacked(96, 0))
            return 0;
        return !ch_attacked(97, 0);
    }
    if (side == CH_BLACK && from == 95 &&
        to == 93 && ch_bq) {
        if (ch_board[94] || ch_board[93] || ch_board[92])
            return 0;
        if (ch_board[91] != (CH_ROOK | CH_BLACK))
            return 0;
        if (ch_attacked(95, 0))
            return 0;
        if (ch_attacked(94, 0))
            return 0;
        return !ch_attacked(93, 0);
    }
    return 0;
}
int ch_pseudo(int from, int to, int side)
{
    int p;
    int t;
    int type;
    int d;
    int step;
    int i;
    if (from < 0 || from >= 120)
        return 0;
    if (to < 0 || to >= 120)
        return 0;
    if (from == to || ch_board[to] == CH_OFF)
        return 0;
    p = ch_board[from];
    t = ch_board[to];
    if (!ch_own(p, side) || ch_own(t, side))
        return 0;
    if (ch_piece(t) && ch_type(t) == CH_KING)
        return 0;
    type = ch_type(p);
    d = to - from;
    if (type == CH_PAWN) {
        if (side == 0) {
            if (d == 10 && t == CH_EMPTY)
                return 1;
            if (d == 20 && from / 10 == 3 &&
                t == CH_EMPTY &&
                ch_board[from + 10] == CH_EMPTY)
                return 1;
            if ((d == 9 || d == 11) &&
                (ch_enemy(t, side) ||
                (to == ch_ep && ch_board[to - 10] ==
                 (CH_PAWN | CH_BLACK))))
                return 1;
        }
        else {
            if (d == -10 && t == CH_EMPTY)
                return 1;
            if (d == -20 && from / 10 == 8 &&
                t == CH_EMPTY &&
                ch_board[from - 10] == CH_EMPTY)
                return 1;
            if ((d == -11 || d == -9) &&
                (ch_enemy(t, side) ||
                (to == ch_ep && ch_board[to + 10] ==
                 CH_PAWN)))
                return 1;
        }
        return 0;
    }
    if (type == CH_KNIGHT) {
        for (i = 0; i < 8; i++) {
            if (d == ch_knight_step[i])
                return 1;
        }
        return 0;
    }
    if (type == CH_KING) {
        for (i = 0; i < 8; i++) {
            if (d == ch_king_step[i])
                return 1;
        }
        if (d == -2 || d == 2)
            return ch_castle(from, to, side);
        return 0;
    }
    if (type == CH_BISHOP || type == CH_QUEEN) {
        for (i = 0; i < 4; i++) {
            step = ch_bishop_step[i];
            if (ch_ray_attack(from, to, step))
                return ch_path_clear(from, to, step);
        }
    }
    if (type == CH_ROOK || type == CH_QUEEN) {
        for (i = 0; i < 4; i++) {
            step = ch_rook_step[i];
            if (ch_ray_attack(from, to, step))
                return ch_path_clear(from, to, step);
        }
    }
    return 0;
}
int ch_valid_promo(int promo)
{
    return promo == CH_QUEEN || promo == CH_ROOK ||
        promo == CH_BISHOP || promo == CH_KNIGHT;
}
void ch_save_undo(int ply, int from, int to)
{
    ch_ufrom[ply] = from;
    ch_uto[ply] = to;
    ch_umoving[ply] = ch_board[from];
    ch_utarget[ply] = ch_board[to];
    ch_uepcap[ply] = CH_NOMOVE;
    ch_urookfrom[ply] = CH_NOMOVE;
    ch_urookto[ply] = CH_NOMOVE;
    ch_uepold[ply] = 0;
    ch_urook[ply] = 0;
    ch_urookold[ply] = 0;
    ch_uolde[ply] = ch_ep;
    ch_uowk[ply] = ch_wk;
    ch_uowq[ply] = ch_wq;
    ch_uobk[ply] = ch_bk;
    ch_uobq[ply] = ch_bq;
    ch_uohalf[ply] = ch_halfmove;
    ch_uofull[ply] = ch_fullmove;
}
void ch_make(int from, int to, int promo,
             int side, int ply)
{
    int epcap;
    int rookfrom;
    int rookto;
    int type;
    unsigned char moving;
    unsigned char target;
    ch_save_undo(ply, from, to);
    moving = ch_board[from];
    target = ch_board[to];
    type = ch_type(moving);
    epcap = CH_NOMOVE;
    if (type == CH_PAWN && target == CH_EMPTY &&
        to == ch_ep) {
        if (side == 0)
            epcap = to - 10;
        else
            epcap = to + 10;
        ch_uepcap[ply] = epcap;
        ch_uepold[ply] = ch_board[epcap];
        ch_board[epcap] = CH_EMPTY;
    }
    ch_board[from] = CH_EMPTY;
    ch_board[to] = moving;
    if (type == CH_KING && ch_abs(to - from) == 2) {
        rookfrom = CH_NOMOVE;
        rookto = CH_NOMOVE;
        if (to == 27) {
            rookfrom = 28;
            rookto = 26;
        }
        if (to == 23) {
            rookfrom = 21;
            rookto = 24;
        }
        if (to == 97) {
            rookfrom = 98;
            rookto = 96;
        }
        if (to == 93) {
            rookfrom = 91;
            rookto = 94;
        }
        ch_urookfrom[ply] = rookfrom;
        ch_urookto[ply] = rookto;
        ch_urook[ply] = ch_board[rookfrom];
        ch_urookold[ply] = ch_board[rookto];
        ch_board[rookto] = ch_board[rookfrom];
        ch_board[rookfrom] = CH_EMPTY;
    }
    if (type == CH_PAWN) {
        if (to / 10 == 2 || to / 10 == 9) {
            if (!ch_valid_promo(promo))
                promo = CH_QUEEN;
            ch_board[to] = (unsigned char)(promo | side);
        }
    }
    if (type == CH_KING) {
        if (side == 0) {
            ch_wk = 0;
            ch_wq = 0;
        }
        else {
            ch_bk = 0;
            ch_bq = 0;
        }
    }
    if (from == 28 || to == 28)
        ch_wk = 0;
    if (from == 21 || to == 21)
        ch_wq = 0;
    if (from == 98 || to == 98)
        ch_bk = 0;
    if (from == 91 || to == 91)
        ch_bq = 0;
    ch_ep = CH_NOMOVE;
    if (type == CH_PAWN && ch_abs(to - from) == 20)
        ch_ep = (from + to) / 2;
    if (type == CH_PAWN || target != CH_EMPTY)
        ch_halfmove = 0;
    else
        ch_halfmove++;
    if (side == CH_BLACK)
        ch_fullmove++;
}
void ch_unmake(int ply)
{
    int from;
    int to;
    from = ch_ufrom[ply];
    to = ch_uto[ply];
    ch_board[from] = ch_umoving[ply];
    ch_board[to] = ch_utarget[ply];
    if (ch_uepcap[ply] >= 0)
        ch_board[ch_uepcap[ply]] = ch_uepold[ply];
    if (ch_urookfrom[ply] >= 0) {
        ch_board[ch_urookfrom[ply]] = ch_urook[ply];
        ch_board[ch_urookto[ply]] = ch_urookold[ply];
    }
    ch_ep = ch_uolde[ply];
    ch_wk = ch_uowk[ply];
    ch_wq = ch_uowq[ply];
    ch_bk = ch_uobk[ply];
    ch_bq = ch_uobq[ply];
    ch_halfmove = ch_uohalf[ply];
    ch_fullmove = ch_uofull[ply];
}
int ch_legal_prom(int from, int to, int promo,
                  int side, int apply)
{
    int bad;
    if (!ch_pseudo(from, to, side))
        return 0;
    ch_make(from, to, promo, side, 0);
    bad = ch_check(side);
    if (bad || !apply)
        ch_unmake(0);
    if (bad)
        return 0;
    return 1;
}
int ch_legal(int from, int to, int side, int apply)
{
    return ch_legal_prom(from, to, CH_QUEEN, side, apply);
}
int ch_cap_score(int from, int to, int promo, int ply)
{
    int target;
    int score;
    int attacker;
    target = ch_board[to];
    attacker = ch_type(ch_board[from]);
    score = 0;
    if (ch_piece(target))
        score = ch_type(target) * 16 + 7 - attacker;
    if (attacker == CH_PAWN && target == CH_EMPTY &&
        to == ch_ep)
        score = CH_PAWN * 16 + 6;
    if (ch_valid_promo(promo))
        score = score + promo;
    if (score == 0 && promo == 0 &&
        from == ch_kfrom[ply] && to == ch_kto[ply])
        score = 12;
    return score;
}
void ch_store_move(int from, int to, int promo,
                   int side, int ply)
{
    int count;
    int base;
    if (!ch_pseudo(from, to, side))
        return;
    ch_make(from, to, promo, side, ply);
    if (ch_check(side)) {
        ch_unmake(ply);
        return;
    }
    ch_unmake(ply);
    count = ch_mcount[ply];
    if (count >= CH_MAXMOVES)
        return;
    base = ply * CH_MAXMOVES + count;
    ch_mfrom[base] = (unsigned char)from;
    ch_mto[base] = (unsigned char)to;
    ch_mpromo[base] = (unsigned char)promo;
    ch_mscore[base] =
        (unsigned char)ch_cap_score(from, to, promo, ply);
    ch_mcount[ply] = count + 1;
}
void ch_store_pawn(int from, int to, int side, int ply)
{
    int row;
    row = to / 10;
    if ((side == 0 && row == 9) ||
        (side == CH_BLACK && row == 2)) {
        ch_store_move(from, to, CH_QUEEN, side, ply);
        ch_store_move(from, to, CH_ROOK, side, ply);
        ch_store_move(from, to, CH_BISHOP, side, ply);
        ch_store_move(from, to, CH_KNIGHT, side, ply);
    }
    else
        ch_store_move(from, to, 0, side, ply);
}
void ch_gen_slider(int from, int side, int ply,
                   int *steps, int nsteps)
{
    int i;
    int sq;
    int step;
    for (i = 0; i < nsteps; i++) {
        step = steps[i];
        sq = from + step;
        while (ch_board[sq] != CH_OFF) {
            ch_store_move(from, sq, 0, side, ply);
            if (ch_board[sq] != CH_EMPTY)
                break;
            sq = sq + step;
        }
    }
}
void ch_swap_move(int a, int b)
{
    unsigned char v;
    v = ch_mfrom[a];
    ch_mfrom[a] = ch_mfrom[b];
    ch_mfrom[b] = v;
    v = ch_mto[a];
    ch_mto[a] = ch_mto[b];
    ch_mto[b] = v;
    v = ch_mpromo[a];
    ch_mpromo[a] = ch_mpromo[b];
    ch_mpromo[b] = v;
    v = ch_mscore[a];
    ch_mscore[a] = ch_mscore[b];
    ch_mscore[b] = v;
}
void ch_sort_moves(int ply)
{
    int base;
    int i;
    int j;
    base = ply * CH_MAXMOVES;
    for (i = 1; i < ch_mcount[ply]; i++) {
        j = i;
        while (j > 0 &&
               ch_mscore[base + j] >
               ch_mscore[base + j - 1]) {
            ch_swap_move(base + j, base + j - 1);
            j--;
        }
    }
}
int ch_gen(int side, int ply)
{
    int r;
    int c;
    int from;
    int type;
    int i;
    int dir;
    ch_mcount[ply] = 0;
    for (r = 2; r <= 9; r++) {
        for (c = 1; c <= 8; c++) {
            from = r * 10 + c;
            if (!ch_own(ch_board[from], side))
                continue;
            type = ch_type(ch_board[from]);
            if (type == CH_PAWN) {
                if (side == 0)
                    dir = 10;
                else
                    dir = -10;
                ch_store_pawn(from, from + dir,
                              side, ply);
                ch_store_pawn(from, from + dir + dir,
                              side, ply);
                ch_store_pawn(from, from + dir - 1,
                              side, ply);
                ch_store_pawn(from, from + dir + 1,
                              side, ply);
            }
            if (type == CH_KNIGHT) {
                for (i = 0; i < 8; i++) {
                    ch_store_move(from,
                                  from + ch_knight_step[i],
                                  0, side, ply);
                }
            }
            if (type == CH_BISHOP)
                ch_gen_slider(from, side, ply,
                              ch_bishop_step, 4);
            if (type == CH_ROOK)
                ch_gen_slider(from, side, ply,
                              ch_rook_step, 4);
            if (type == CH_QUEEN) {
                ch_gen_slider(from, side, ply,
                              ch_bishop_step, 4);
                ch_gen_slider(from, side, ply,
                              ch_rook_step, 4);
            }
            if (type == CH_KING) {
                for (i = 0; i < 8; i++) {
                    ch_store_move(from,
                                  from + ch_king_step[i],
                                  0, side, ply);
                }
                ch_store_move(from, from - 2,
                              0, side, ply);
                ch_store_move(from, from + 2,
                              0, side, ply);
            }
        }
    }
    ch_sort_moves(ply);
    return ch_mcount[ply];
}
int ch_pst_value(int type, int r, int c, int side)
{
    int rr;
    int cc;
    rr = r - 2;
    if (side == CH_BLACK)
        rr = 7 - rr;
    cc = c - 1;
    if (cc > 3)
        cc = 7 - cc;
    return (int)ch_pst[(type - 1) * 32 + rr * 4 + cc] - 50;
}
int ch_eval(int side)
{
    int r;
    int c;
    int sq;
    int p;
    int type;
    int value;
    int score;
    score = 0;
    for (r = 2; r <= 9; r++) {
        for (c = 1; c <= 8; c++) {
            sq = r * 10 + c;
            p = ch_board[sq];
            if (!ch_piece(p))
                continue;
            type = ch_type(p);
            value = ch_value[type];
            value = value +
                ch_pst_value(type, r, c, ch_color(p));
            if (ch_color(p) == side)
                score = score + value;
            else
                score = score - value;
        }
    }
    return score;
}
int ch_search(int side, int depth,
              int alpha, int beta, int ply)
{
    int count;
    int i;
    int base;
    int from;
    int to;
    int promo;
    int score;
    ch_nodes++;
    if (ch_halfmove >= 100)
        return 0;
    if (depth <= 0)
        return ch_eval(side);
    count = ch_gen(side, ply);
    if (count == 0) {
        if (ch_check(side))
            return -CH_MATE + ply;
        return 0;
    }
    base = ply * CH_MAXMOVES;
    for (i = 0; i < count; i++) {
        from = ch_mfrom[base + i];
        to = ch_mto[base + i];
        promo = ch_mpromo[base + i];
        ch_make(from, to, promo, side, ply);
        score = -ch_search(side ^ CH_BLACK,
                           depth - 1,
                           -beta, -alpha, ply + 1);
        ch_unmake(ply);
        if (score > alpha)
            alpha = score;
        if (alpha >= beta) {
            if (ch_board[to] == CH_EMPTY && promo == 0 &&
                to != ch_ep) {
                ch_kfrom[ply] = (unsigned char)from;
                ch_kto[ply] = (unsigned char)to;
            }
            return alpha;
        }
    }
    return alpha;
}
void ch_prioritize(int ply, int from, int to, int promo)
{
    int base;
    int i;
    base = ply * CH_MAXMOVES;
    for (i = 0; i < ch_mcount[ply]; i++) {
        if (ch_mfrom[base + i] == from &&
            ch_mto[base + i] == to &&
            ch_mpromo[base + i] == promo) {
            if (i != 0)
                ch_swap_move(base, base + i);
            return;
        }
    }
}
int ch_find_best(int side)
{
    int depth;
    int count;
    int i;
    int from;
    int to;
    int promo;
    int score;
    int alpha;
    int this_from;
    int this_to;
    int this_promo;
    int this_score;
    ch_best_from = CH_NOMOVE;
    ch_best_to = CH_NOMOVE;
    ch_best_promo = CH_QUEEN;
    ch_best_score = -CH_INF;
    ch_nodes = 0;
    for (depth = 1; depth <= ch_level; depth++) {
        count = ch_gen(side, 0);
        if (count == 0)
            return 0;
        if (ch_best_from >= 0)
            ch_prioritize(0, ch_best_from,
                          ch_best_to, ch_best_promo);
        alpha = -CH_INF;
        this_from = CH_NOMOVE;
        this_to = CH_NOMOVE;
        this_promo = CH_QUEEN;
        this_score = -CH_INF;
        for (i = 0; i < count; i++) {
            from = ch_mfrom[i];
            to = ch_mto[i];
            promo = ch_mpromo[i];
            ch_make(from, to, promo, side, 0);
            score = -ch_search(side ^ CH_BLACK,
                               depth - 1,
                               -CH_INF, -alpha, 1);
            ch_unmake(0);
            if (this_from < 0 || score > this_score) {
                this_score = score;
                this_from = from;
                this_to = to;
                this_promo = promo;
            }
            if (score > alpha)
                alpha = score;
        }
        ch_best_from = this_from;
        ch_best_to = this_to;
        ch_best_promo = this_promo;
        ch_best_score = this_score;
        if (ch_abs(ch_best_score) > CH_MATE - 100)
            break;
    }
    return ch_best_from >= 0;
}
void ch_define_udg(void)
{
    int i;
    for (i = 0; i < 20; i++)
        udg_define(i, ch_udg + i * 8);
    udg_define(20, ch_blank);
}
void ch_draw_piece(int br, int bc, int p)
{
    int type;
    int paper_color;
    int ink_color;
    int pos;
    int code;
    if (((br / 2) + (bc / 2)) & 1)
        paper_color = 2;
    else
        paper_color = 4;
    if (ch_piece(p) && ch_color(p) == 0)
        ink_color = 7;
    else
        ink_color = 0;
    paper(paper_color);
    ink(ink_color);
    bright(0);
    if (!ch_piece(p)) {
        udg_draw(20, br, bc);
        udg_draw(20, br, bc + 1);
        udg_draw(20, br + 1, bc);
        udg_draw(20, br + 1, bc + 1);
        return;
    }
    type = ch_type(p);
    pos = type * 4;
    code = ch_piece_tab[pos];
    udg_draw(code - 144, br, bc);
    code = ch_piece_tab[pos + 1];
    udg_draw(code - 144, br, bc + 1);
    code = ch_piece_tab[pos + 3];
    udg_draw(code - 144, br + 1, bc);
    code = ch_piece_tab[pos + 2];
    udg_draw(code - 144, br + 1, bc + 1);
}
void ch_clear_text(void)
{
    paper(0);
    ink(7);
    bright(0);
}
void ch_num(int row, int col, unsigned int value)
{
    char text[6];
    int pos;
    pos = 5;
    text[pos] = 0;
    do {
        pos--;
        text[pos] = (char)('0' + value % 10u);
        value = value / 10u;
    } while (value != 0u);
    print_at(row, col, text + pos);
}
void ch_score_text(int row, int col, int value)
{
    if (value < 0) {
        game_putc(row, col, '-');
        ch_num(row, col + 1,
               (unsigned int)(-value));
    }
    else {
        game_putc(row, col, '+');
        ch_num(row, col + 1,
               (unsigned int)value);
    }
}
void ch_draw(void)
{
    int r;
    int c;
    int sq;
    int board_r;
    char side_text[2];
    cls();
    border(0);
    for (r = 0; r < 8; r++) {
        board_r = 9 - r;
        for (c = 0; c < 8; c++) {
            sq = board_r * 10 + c + 1;
            ch_draw_piece(r * 2, c * 2, ch_board[sq]);
        }
    }
    ch_clear_text();
    print_at(16, 0, " a   b   c   d   e   f   g   h");
    for (r = 0; r < 8; r++)
        game_putc(r * 2, 32, '8' - r);
    print_at(0, 34, "ZX-UX Chess");
    if (ch_computer == CH_NOMOVE)
        print_at(2, 34, "Mode: select side");
    else {
        print_at(2, 34, "Computer:");
        if (ch_computer == CH_BLACK)
            side_text[0] = 'B';
        else
            side_text[0] = 'W';
        side_text[1] = 0;
        print_at(2, 44, side_text);
        print_at(3, 34, "Look ahead:");
        game_putc(3, 46, '0' + ch_level);
    }
    print_at(5, 34, "Move:");
    if (ch_last[0] != 0)
        print_at(5, 40, ch_last);
    print_at(7, 34, "Nodes:");
    ch_num(7, 41, (unsigned int)ch_nodes);
    print_at(9, 34, "Score:");
    ch_score_text(9, 41, ch_best_score);
    if (ch_check(ch_side))
        print_at(11, 34, "CHECK");
    print_at(13, 34, "q quits");
    if (ch_side == 0)
        print_at(18, 0, "White to move:");
    else
        print_at(18, 0, "Black to move:");
    if (ch_last[0] != 0) {
        print_at(20, 0, "Last move:");
        print_at(20, 11, ch_last);
        if (ch_last_state == 1)
            print_at(20, 17, "accepted");
        else
            print_at(20, 17, "illegal ");
    }
}
int ch_readmove(char *move)
{
    int key;
    int len;
    len = 0;
    move[0] = 0;
    while (1) {
        if (ch_pending >= 0) {
            key = ch_pending;
            ch_pending = CH_NOMOVE;
        }
        else
            key = game_key();
        if (key == 'q' && len == 0)
            return -1;
        if (key == 8) {
            if (len > 0) {
                len--;
                move[len] = 0;
                game_putc(18, 15 + len, ' ');
            }
            continue;
        }
        if (key == 10 || key == 13) {
            if (len == 4 || len == 5)
                return 1;
            print_at(22, 0, "Enter a move like e2e4.");
            continue;
        }
        if (key >= 32 && key <= 126 && len < 5) {
            move[len] = (char)key;
            game_putc(18, 15 + len, key);
            len++;
            move[len] = 0;
            continue;
        }
        print_at(22, 0, "Use e2e4; DELETE edits.");
    }
}
void ch_save_last(char *move, int state)
{
    int i;
    for (i = 0; i < 4; i++)
        ch_last[i] = move[i];
    ch_last[4] = 0;
    ch_last_state = state;
}
void ch_save_squares(int from, int to, int state)
{
    char a[3];
    char b[3];
    ch_square_text(from, a);
    ch_square_text(to, b);
    ch_last[0] = a[0];
    ch_last[1] = a[1];
    ch_last[2] = b[0];
    ch_last[3] = b[1];
    ch_last[4] = 0;
    ch_last_state = state;
}
int ch_select_game(void)
{
    int key;
    ch_clear_text();
    print_at(22, 0, "PLAY WHITE OR BLACK? (W/B)");
    while (1) {
        key = game_key();
        if (key == 'q')
            return -1;
        if (key == 'w') {
            ch_computer = CH_BLACK;
            break;
        }
        if (key == 'b') {
            ch_computer = 0;
            break;
        }
        if (key >= 'a' && key <= 'h') {
            ch_computer = CH_NOMOVE;
            ch_pending = key;
            return 0;
        }
        print_at(23, 0, "Choose w, b, or enter a move.");
    }
    print_at(23, 0, "SELECT LOOK AHEAD (1-3):");
    while (1) {
        key = game_key();
        if (key >= '1' && key <= '3') {
            ch_level = key - '0';
            return 0;
        }
    }
}
int ch_game_over(void)
{
    if (ch_halfmove >= 100) {
        ch_draw();
        print_at(22, 0, "DRAW: 50-move rule. Press q.");
        while (game_key() != 'q')
            ch_turns++;
        return 1;
    }
    if (ch_gen(ch_side, 0) != 0)
        return 0;
    ch_draw();
    if (ch_check(ch_side))
        print_at(22, 0, "CHECKMATE. Press q.");
    else
        print_at(22, 0, "STALEMATE. Press q.");
    while (game_key() != 'q')
        ch_turns++;
    return 1;
}
void ch_cpu_move(void)
{
    ch_clear_text();
    print_at(22, 0, "Thinking...");
    if (!ch_find_best(ch_side))
        return;
    ch_make(ch_best_from, ch_best_to,
            ch_best_promo, ch_side, 0);
    ch_save_squares(ch_best_from, ch_best_to, 1);
    ch_side = ch_side ^ CH_BLACK;
    ch_turns++;
}
int main(void)
{
    int rc;
    int from;
    int to;
    int prom;
    int p;
    char move[6];
    ch_define_udg();
    ch_init_board();
    ch_draw();
    if (ch_select_game() < 0)
        return 0;
    while (1) {
        ch_draw();
        if (ch_game_over())
            return 0;
        if (ch_computer == ch_side) {
            ch_cpu_move();
            continue;
        }
        rc = ch_readmove(move);
        if (rc < 0)
            return 0;
        ch_turns++;
        from = ch_coord(move[0], move[1]);
        to = ch_coord(move[2], move[3]);
        if (from < 0 || to < 0) {
            ch_save_last(move, 0);
            continue;
        }
        prom = CH_QUEEN;
        if (move[4] != 0) {
            prom = ch_promo_code(move[4]);
            if (prom == 0) {
                ch_save_last(move, 0);
                continue;
            }
        }
        p = ch_board[from];
        if (ch_piece(p) && ch_type(p) == CH_PAWN &&
            (to / 10 == 2 || to / 10 == 9) &&
            move[4] == 0) {
            ch_clear_text();
            print_at(22, 0, "Promote q r b n:");
            while (prom == CH_QUEEN) {
                rc = game_key();
                prom = ch_promo_code(rc);
                if (prom == 0)
                    prom = CH_QUEEN;
                else
                    break;
            }
        }
        if (ch_legal_prom(from, to, prom,
                          ch_side, 1)) {
            ch_save_last(move, 1);
            ch_side = ch_side ^ CH_BLACK;
        }
        else {
            ch_save_last(move, 0);
            ch_draw();
            print_at(22, 0, "Illegal move.");
        }
    }
}
