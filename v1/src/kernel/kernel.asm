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
; Resident 8-KiB kernel image. Fixed subranges are asserted byte-for-byte.

    DEVICE ZXSPECTRUM48
    INCLUDE "../../include/zx48ux.inc"
    INCLUDE "errors.asm"
    INCLUDE "z80_primitives.asm"
    INCLUDE "memory.asm"
    INCLUDE "process.asm"
    INCLUDE "handles.asm"
    INCLUDE "pipe.asm"
    INCLUDE "objects.asm"
    INCLUDE "zxpack.asm"
    INCLUDE "ula_io.asm"
    INCLUDE "tty32.asm"
    INCLUDE "tty64.asm"
    INCLUDE "cursor.asm"
    INCLUDE "console.asm"
    INCLUDE "keyboard.asm"
    INCLUDE "graphics.asm"
    INCLUDE "udg.asm"
    INCLUDE "sound.asm"
    INCLUDE "tape.asm"
    INCLUDE "scheduler.asm"
    INCLUDE "interrupt.asm"
    INCLUDE "im2.asm"
    INCLUDE "rom_services.asm"
    INCLUDE "syscall.asm"
    INCLUDE "../boot/entry.asm"

    ORG KERNEL_START
kernel_image_start:
kernel_ordinary_pool_start:
    EMIT_SYSCALL_GATEWAY
    ASSERT $ = BOOT_GATEWAY
    EMIT_BOOT_GATEWAY
    ASSERT $ = BOOT_GATEWAY+3
    EMIT_SYSCALL_BODY
    EMIT_BOOT_BODY
    EMIT_ERROR_ROUTINES
    EMIT_Z80_PRIMITIVES
    EMIT_MEMORY_ROUTINES
    EMIT_PROCESS_ROUTINES
    EMIT_HANDLE_ROUTINES
    EMIT_PIPE_ROUTINES
    EMIT_OBJECT_ROUTINES
    EMIT_ZXPACK_ROUTINES
    EMIT_ULA_ROUTINES
    EMIT_TTY32_ROUTINES
    EMIT_TTY64_ROUTINES
    EMIT_CURSOR_ROUTINES
    EMIT_CONSOLE_ROUTINES
    EMIT_KEYBOARD_ROUTINES
    EMIT_GRAPHICS_ROUTINES
    EMIT_UDG_ROUTINES
    EMIT_SOUND_ROUTINES
    EMIT_TAPE_ROUTINES
    EMIT_SCHEDULER_ROUTINES
    EMIT_INTERRUPT_ROUTINE
    EMIT_IM2_ROUTINES
    EMIT_ROM_SERVICE_ROUTINES
; Temporary private-loader entry points are replaced by process.asm before the
; candidate may become a check-in. They keep size/syntax validation independent.
zx48_process_spawn:
    ld a,E_NOTSUP
    scf
    ret
zx48_process_exec:
    ld a,E_NOTSUP
    scf
    ret
    EMIT_SYSCALL_IMPL
    EMIT_BOOT_IMPL
kernel_ordinary_used_end:
    ASSERT $ <= KERNEL_CODE_END+1
    DEFS KERNEL_CODE_END+1-$,0
kernel_ordinary_pool_end:

    ASSERT $ = KERNEL_STACK_START
kernel_stack_storage:
    DEFS KERNEL_STACK_END-KERNEL_STACK_START+1,0
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
    DEFS EMERGENCY_END-EMERGENCY_START+1,0
kernel_image_end:

    ASSERT kernel_ordinary_pool_end-kernel_ordinary_pool_start = KERNEL_CODE_END-KERNEL_CODE_START+1
    ASSERT kernel_image_end-kernel_image_start = KERNEL_IMAGE_SIZE
    SAVEBIN "../../build/kernel.bin",kernel_image_start,KERNEL_IMAGE_SIZE
