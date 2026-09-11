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
; Phase-0 public gateway and conservative base dispatcher. Later subsystem
; phases replace E_NOTSUP entries without moving the fixed E000 entry point.

    MACRO EMIT_SYSCALL_GATEWAY
syscall_gateway:
    jp zx48_syscall
    ENDM

    MACRO EMIT_SYSCALL_BODY
zx48_syscall:
    jp zx48_syscall_impl
    ENDM

    MACRO EMIT_SYSCALL_IMPL
; in: A=syscall number and call-specific registers.
; out: documented result; unsupported calls return E_NOTSUP.
; flags: carry set on failure, clear on success.
; clobber: AF plus call-specific result registers.
zx48_syscall_impl:
    cp SYS_VERSION
    jr z,zx48_sys_version
    cp SYS_GETPID
    jr z,zx48_sys_getpid
    cp SYS_YIELD
    jr z,zx48_sys_yield
    ld a,E_NOTSUP
    scf
    ld iy,ROM_IY_ANCHOR
    ret
zx48_sys_version:
    ld hl,ZXUX_ABI_VERSION
    xor a
    ld iy,ROM_IY_ANCHOR
    ret
zx48_sys_getpid:
    ld a,(kernel_current_pid)
    ld l,a
    ld h,0
    xor a
    ld iy,ROM_IY_ANCHOR
    ret
zx48_sys_yield:
    xor a
    ld iy,ROM_IY_ANCHOR
    ret
kernel_current_pid:
    db 0
    ENDM
