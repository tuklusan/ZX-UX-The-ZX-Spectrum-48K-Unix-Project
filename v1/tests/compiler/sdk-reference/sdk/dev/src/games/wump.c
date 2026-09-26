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

int cave[36] = {
    1, 4, 7, 0, 2, 9, 1, 3, 11,
    2, 4, 6, 0, 3, 5, 4, 6, 8,
    3, 5, 7, 0, 6, 8, 5, 7, 9,
    1, 8, 10, 9, 11, 6, 2, 10, 7
};
int w_room;
int p_room;
int b_room;
int player_room;
int arrows;
int w_turns;

int near_room(int room, int target)
{
    int i;
    for (i = 0; i < 3; i++) {
        if (cave[room * 3 + i] == target)
            return 1;
    }
    return 0;
}

void w_draw(void)
{
    cls();
    print_at(0, 0, "HUNT THE WUMPUS");
    print_at(2, 0, "a b c = tunnels, s = shoot, q = quit");
    print_at(5, 0, "Room:");
    game_num(5, 7, (unsigned int)(player_room + 1));
    print_at(6, 0, "Tunnels lead to:");
    game_num(6, 17,
        (unsigned int)(cave[player_room * 3] + 1));
    game_num(6, 21,
        (unsigned int)(cave[player_room * 3 + 1] + 1));
    game_num(6, 25,
        (unsigned int)(cave[player_room * 3 + 2] + 1));
    print_at(8, 0, "Arrows:");
    game_num(8, 8, (unsigned int)arrows);
    if (near_room(player_room, w_room))
        print_at(11, 0, "You smell a Wumpus.");
    if (near_room(player_room, p_room))
        print_at(12, 0, "You feel a cold draft.");
    if (near_room(player_room, b_room))
        print_at(13, 0, "You hear giant bats.");
    print_at(16, 0, "Command:");
}

int w_pick(int key)
{
    if (key == 'a')
        return cave[player_room * 3];
    if (key == 'b')
        return cave[player_room * 3 + 1];
    if (key == 'c')
        return cave[player_room * 3 + 2];
    return -1;
}

int main(void)
{
    int key;
    int dest;
    w_room = 10;
    p_room = 5;
    b_room = 8;
    player_room = 0;
    arrows = 5;
    w_turns = 0;
    while (1) {
        w_draw();
        key = game_key();
        w_turns++;
        if (key == 'q')
            return 0;
        if (key == 's') {
            print_at(18, 0, "Shoot down tunnel a, b, or c?");
            key = game_key();
            dest = w_pick(key);
            if (dest == w_room) {
                cls();
                print_at(8, 10, "You slew the Wumpus!");
                print_at(10, 10, "Press q to leave.");
                while (game_key() != 'q')
                    w_turns++;
                return 0;
            }
            if (dest >= 0)
                arrows--;
            if (arrows == 0) {
                cls();
                print_at(8, 10, "No arrows. The Wumpus wins.");
                print_at(10, 10, "Press q to leave.");
                while (game_key() != 'q')
                    w_turns++;
                return 0;
            }
            continue;
        }
        dest = w_pick(key);
        if (dest < 0)
            continue;
        player_room = dest;
        if (player_room == p_room) {
            cls();
            print_at(8, 10, "You fell into a bottomless pit.");
            print_at(10, 10, "Press q to leave.");
            while (game_key() != 'q')
                w_turns++;
            return 0;
        }
        if (player_room == w_room) {
            cls();
            print_at(8, 10, "The Wumpus got you.");
            print_at(10, 10, "Press q to leave.");
            while (game_key() != 'q')
                w_turns++;
            return 0;
        }
        if (player_room == b_room) {
            player_room = game_rand(12);
            if (player_room == p_room)
                player_room = 0;
            if (player_room == w_room)
                player_room = 0;
        }
    }
}
