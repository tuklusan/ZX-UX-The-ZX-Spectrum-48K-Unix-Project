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
; Phase P0.03 syscall gateway scaffold.

    MACRO EMIT_SYSCALL_GATEWAY
syscall_gateway:
    jp zx48_syscall_dispatch
    ENDM

    MACRO EMIT_SYSCALL_BODY
; Inputs: A syscall number; HL/DE/BC arguments.
; Outputs: implementation-dependent syscall result.
; Flags: implementation-dependent.
; Clobbers: AF/BC/DE/HL; IX preserved by public ABI.
zx48_syscall_dispatch:
    jp zx48_syscall_dispatch_impl
    ENDM

    MACRO EMIT_SYSCALL_IMPL
zx48_syscall_dispatch_impl:
    ret
    ENDM
