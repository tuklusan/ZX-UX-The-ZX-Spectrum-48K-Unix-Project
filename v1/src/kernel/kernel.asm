; Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
; Proprietary rights reserved except as expressly licensed herein.
;
; ZX-UX Sinclair ZX Spectrum Unix
; This file is governed by the SANYALnet Labs Non-Commercial License in the
; root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
; for AI/ML model training are prohibited unless separately authorized.
;
; Attribution is required: "Based on original work by Supratim Sanyal of
; SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
; patent, trademark, and governing-law provisions.
;
; Resident ZX-UX kernel composition.

    DEVICE ZXSPECTRUM48
    INCLUDE "../../include/zx48ux.inc"
ZX48_REV02_COLD_IMAGE_INIT EQU 1
    INCLUDE "syscall.asm"
    INCLUDE "../boot/entry.asm"
    INCLUDE "interrupt.asm"
    INCLUDE "im2.asm"
    INCLUDE "rom_services.asm"
    INCLUDE "errors.asm"
    INCLUDE "memory.asm"
    INCLUDE "process.asm"
    INCLUDE "handles.asm"
    INCLUDE "pipe.asm"
    INCLUDE "scheduler.asm"
    INCLUDE "z80_primitives.asm"
    INCLUDE "ula_io.asm"
    INCLUDE "tty32.asm"
    INCLUDE "tty64.asm"
    INCLUDE "cursor.asm"
    INCLUDE "console.asm"
    INCLUDE "keyboard.asm"
    INCLUDE "udg.asm"

    ORG KERNEL_START
kernel_image_start:
kernel_ordinary_pool_start:
kernel_mod_gateways:
    EMIT_SYSCALL_GATEWAY
    ASSERT $ = BOOT_GATEWAY
    EMIT_BOOT_GATEWAY
    ASSERT $ = BOOT_GATEWAY+3
    EMIT_SYSCALL_BODY
    EMIT_BOOT_BODY
kernel_mod_syscall:
    EMIT_SYSCALL_IMPL
kernel_mod_boot:
    EMIT_BOOT_IMPL
kernel_mod_interrupt:
    EMIT_INTERRUPT_ROUTINE
kernel_mod_im2:
    EMIT_IM2_ROUTINES
kernel_mod_rom:
    EMIT_ROM_SERVICE_ROUTINES
kernel_mod_errors:
    EMIT_ERROR_ROUTINES
kernel_mod_memory:
    EMIT_REV02_MEMORY_ROUTINES
kernel_mod_process:
    EMIT_REV02_PROCESS_ROUTINES
kernel_mod_handles:
    EMIT_HANDLE_ROUTINES
kernel_mod_pipe:
    EMIT_REV02_PIPE_ROUTINES
kernel_mod_scheduler:
    EMIT_REV02_SCHEDULER_ROUTINES
kernel_mod_primitives:
    EMIT_Z80_PRIMITIVES
kernel_mod_ula:
    EMIT_ULA_ROUTINES
kernel_mod_tty32:
    EMIT_REV02_TTY32_ROUTINES
kernel_mod_tty64:
    EMIT_REV02_TTY64_ROUTINES
kernel_mod_cursor:
    EMIT_CURSOR_ROUTINES
kernel_mod_console:
    EMIT_CONSOLE_ROUTINES
kernel_mod_keyboard:
    EMIT_KEYBOARD_ROUTINES
kernel_mod_udg:
    EMIT_UDG_ROUTINES
kernel_ordinary_used_end:
    ASSERT $ <= KERNEL_CODE_END+1
    DEFS KERNEL_CODE_END+1-$,0
kernel_ordinary_pool_end:

    ASSERT $ = KERNEL_STACK_START
kernel_stack_storage:
    ; The exact image carries the release stack guard; the remainder starts 0.
    DEFS KSTACK_GUARD_SIZE,KSTACK_GUARD_BYTE
    DEFS KERNEL_STACK_END-KERNEL_STACK_START+1-KSTACK_GUARD_SIZE,0

    ASSERT $ = FAST_RESERVE_START
kernel_fast_reserve:
    DEFS FAST_RESERVE_END-FAST_RESERVE_START+1,0

    ASSERT $ = IM2_TRAMPOLINE_START
    EMIT_IM2_TRAMPOLINE
    ASSERT $ = IM2_TRAMPOLINE_END+1

    ASSERT $ = IM2_TABLE_START
kernel_im2_table:
    DEFS IM2_TABLE_END-IM2_TABLE_START+1,IM2_VECTOR_BYTE

    ASSERT $ = EMERGENCY_START
kernel_emergency_reserve:
    ; Exact cold-state bytes remove redundant boot-time stores while preserving
    ; every fixed reserve address and public behavior.
    ASSERT wall_seconds >= EMERGENCY_START
    ASSERT memory_free_extents+FREE_EXTENT_COUNT*4 <= EMERGENCY_END+1
    DEFS wall_seconds-$,0
    dw $0680,$1726
    DEFS wall_valid-$,0
    db 1
    DEFS kernel_stack_low_water-$,0
    dw BOOT_STACK_TOP
    DEFS cursor_phase-$,0
    db 1
    DEFS tty_mode-$,0
    db TTY_MODE_64
    DEFS tty_cursor_shape-$,0
    db TTY_CURSOR_UNDERLINE
    DEFS memory_free_extents-$,0
    dw ARENA_START,ARENA_SIZE
    DEFS (FREE_EXTENT_COUNT-1)*4,0
    DEFS EMERGENCY_END+1-$,0
kernel_image_end:

    ASSERT kernel_ordinary_pool_end-kernel_ordinary_pool_start = KERNEL_CODE_END-KERNEL_CODE_START+1
    ASSERT kernel_stack_storage = KERNEL_STACK_START
    ASSERT kernel_fast_reserve = FAST_RESERVE_START
    ASSERT kernel_im2_trampoline = IM2_TRAMPOLINE_START
    ASSERT kernel_im2_table = IM2_TABLE_START
    ASSERT kernel_emergency_reserve = EMERGENCY_START
    ASSERT kernel_image_end-kernel_image_start = KERNEL_IMAGE_SIZE

    SAVEBIN "../../build/kernel.bin",kernel_image_start,KERNEL_IMAGE_SIZE
