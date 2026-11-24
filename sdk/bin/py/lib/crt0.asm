; =====================================================================
; ZX-UX 48K Sinclair ZX Spectrum Unix.
; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Non-commercial use only under the repository LICENSE.
; Commercial use prohibited without separate written permission.
; =====================================================================
; C48 startup: kernel stack holds argc, argv and strings. No mystery guests. (ZX-UX SDK)
; ENV1 is an empty process-owned BSS byte, separate from ARG1/KARGS. exec resets it.
; __c48_env1 aliases ENV1 for tests, not a getenv API. Nice try.
SYS     equ 6003h
        section text
        global start,@noret,@divz,@env1
; start: 25 bytes. Read argc/argv off SP, clear ENV1 and call @main. Exit through _exit.
start:  xor a
        ld (@env1),a            ; ENV1: empty
        ld hl,0
        add hl,sp
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        push hl
        push de
        call @scrinit
        pop de
        pop hl
        call @main
        jp _exit
; @divz/@noret: 6 bytes. Exit with status 1 on division failure or stack trouble.
@divz:
@noret: ld hl,1
        jp _exit
        section bss
        global __c48_env1
; @env1/__c48_env1: 1 BSS byte shared by both names. Same room, two signs.
@env1:
__c48_env1: ds 1
