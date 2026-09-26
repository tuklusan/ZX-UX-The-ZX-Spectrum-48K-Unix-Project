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

int room;
int have_key;
int have_crown;
int adv_turns;

void adv_draw(void)
{
    cls();
    print_at(0, 0, "C48 ADVENTURE");
    print_at(2, 0, "n s e w move, t take, q quit");
    if (room == 0) {
        print_at(5, 0, "You are in a quiet stone cabin.");
        print_at(7, 0, "A path leads east into the wood.");
    }
    if (room == 1) {
        print_at(5, 0, "You are in a dark pine forest.");
        print_at(7, 0, "Cabin west, cave north, river east.");
    }
    if (room == 2) {
        print_at(5, 0, "A cold cave echoes around you.");
        if (!have_key)
            print_at(7, 0, "A brass key glints on the floor.");
    }
    if (room == 3) {
        print_at(5, 0, "A fast river blocks the old road.");
        print_at(7, 0, "A locked tower gate stands north.");
    }
    if (room == 4) {
        print_at(5, 0, "You stand inside the ruined tower.");
        if (!have_crown)
            print_at(7, 0, "The lost crown rests on a plinth.");
    }
    print_at(11, 0, "Inventory:");
    if (have_key)
        print_at(11, 12, "key");
    if (have_crown)
        print_at(12, 12, "crown");
    print_at(15, 0, "Command:");
}

int adv_move(int key)
{
    if (room == 0 && key == 'e') {
        room = 1;
        return 1;
    }
    if (room == 1 && key == 'w') {
        room = 0;
        return 1;
    }
    if (room == 1 && key == 'n') {
        room = 2;
        return 1;
    }
    if (room == 2 && key == 's') {
        room = 1;
        return 1;
    }
    if (room == 1 && key == 'e') {
        room = 3;
        return 1;
    }
    if (room == 3 && key == 'w') {
        room = 1;
        return 1;
    }
    if (room == 3 && key == 'n' && have_key) {
        room = 4;
        return 1;
    }
    if (room == 4 && key == 's') {
        room = 3;
        return 1;
    }
    return 0;
}

int main(void)
{
    int key;
    room = 0;
    have_key = 0;
    have_crown = 0;
    adv_turns = 0;
    while (1) {
        adv_draw();
        if (room == 0 && have_crown) {
            print_at(18, 0, "You return the crown. Victory!");
            print_at(20, 0, "Press q to leave.");
            while (game_key() != 'q')
                adv_turns++;
            return 0;
        }
        key = game_key();
        adv_turns++;
        if (key == 'q')
            return 0;
        if (key == 't' && room == 2 && !have_key) {
            have_key = 1;
            continue;
        }
        if (key == 't' && room == 4 && !have_crown) {
            have_crown = 1;
            continue;
        }
        if (!adv_move(key)) {
            if (room == 3 && key == 'n' && !have_key) {
                print_at(18, 0, "The tower gate is locked.");
                game_key();
            }
        }
    }
}
