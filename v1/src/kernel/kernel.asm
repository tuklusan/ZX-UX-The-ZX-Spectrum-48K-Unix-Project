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
; Phase P0.02: fixed 8 KiB resident-kernel image scaffold.
;
; This file owns only fixed image layout. Functional modules progressively
; replace zero-filled bytes inside KERNEL_CODE_START..KERNEL_CODE_END.

    DEVICE ZXSPECTRUM48
    INCLUDE "../../include/zx48ux.inc"

    ORG KERNEL_START
kernel_image_start:
kernel_ordinary_pool_start:
    DEFS KERNEL_CODE_END-KERNEL_CODE_START+1,0
kernel_ordinary_pool_end:

    ASSERT $ = KERNEL_STACK_START
kernel_stack_storage:
    DEFS KERNEL_STACK_END-KERNEL_STACK_START+1,0

    ASSERT $ = FAST_RESERVE_START
kernel_fast_reserve:
    DEFS FAST_RESERVE_END-FAST_RESERVE_START+1,0

    ASSERT $ = IM2_TRAMPOLINE_START
kernel_im2_trampoline:
    DEFS IM2_TRAMPOLINE_END-IM2_TRAMPOLINE_START+1,0

    ASSERT $ = IM2_TABLE_START
kernel_im2_table:
    DEFS IM2_TABLE_END-IM2_TABLE_START+1,IM2_VECTOR_BYTE

    ASSERT $ = EMERGENCY_START
kernel_emergency_reserve:
    DEFS EMERGENCY_END-EMERGENCY_START+1,0
kernel_image_end:

    ASSERT kernel_ordinary_pool_end-kernel_ordinary_pool_start = $1B00
    ASSERT kernel_stack_storage = $FB00
    ASSERT kernel_fast_reserve = $FD00
    ASSERT kernel_im2_trampoline = $FDFD
    ASSERT kernel_im2_table = $FE00
    ASSERT kernel_emergency_reserve = $FF01
    ASSERT kernel_image_end-kernel_image_start = KERNEL_IMAGE_SIZE

    SAVEBIN "../../build/kernel.bin",kernel_image_start,KERNEL_IMAGE_SIZE
