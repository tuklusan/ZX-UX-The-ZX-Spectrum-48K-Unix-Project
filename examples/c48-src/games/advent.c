// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
#include "gameapi.h"

int room;
int have_key;
int have_crown;
int adv_turns;
int adv_notice;

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
    game_show_last(14);
    print_at(16, 0, "Command:");
}

void adv_status(void)
{
    print_at(18, 0, "                                ");
    if (adv_notice == 1)
        print_at(18, 0, "The tower gate is locked.");
    if (adv_notice == 2)
        print_at(18, 0, "There is no path that way.");
    if (adv_notice == 3)
        print_at(18, 0, "There is nothing to take.");
    game_show_last(14);
    game_putc(16, 9, ' ');
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
    adv_notice = 0;
    adv_draw();
    while (1) {
        if (room == 0 && have_crown) {
            print_at(18, 0, "You return the crown. Victory!");
            print_at(20, 0, "Press q to leave.");
            while (game_key() != 'q')
                adv_turns++;
            return 0;
        }
        key = game_key_echo(16, 9);
        adv_turns++;
        adv_notice = 0;
        if (key == 'q')
            return 0;
        if (key == 't' && room == 2 && !have_key) {
            have_key = 1;
            game_record(key, 1);
            adv_draw();
            continue;
        }
        if (key == 't' && room == 4 && !have_crown) {
            have_crown = 1;
            game_record(key, 1);
            adv_draw();
            continue;
        }
        if (key == 't') {
            adv_notice = 3;
            game_record(key, 2);
            adv_status();
            continue;
        }
        if (adv_move(key)) {
            game_record(key, 1);
            adv_draw();
            continue;
        }
        if (room == 3 && key == 'n' && !have_key) {
            adv_notice = 1;
            game_record(key, 2);
            adv_status();
            continue;
        }
        if (key == 'n' || key == 's' ||
            key == 'e' || key == 'w') {
            adv_notice = 2;
            game_record(key, 2);
            adv_status();
            continue;
        }
        game_record(key, 3);
        adv_status();
    }
}
