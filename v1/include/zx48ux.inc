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
; ZX-UX version-1 canonical assembly constants.
; This file owns each public syscall number exactly once.

ZXUX_ABI_VERSION         EQU $0100

ROM_START                EQU $0000
ROM_END                  EQU $3FFF
BITMAP_START             EQU $4000
BITMAP_END               EQU $57FF
ATTR_START               EQU $5800
ATTR_END                 EQU $5AFF
ROM_COMPAT_START         EQU $5B00
ROM_COMPAT_END           EQU $5FFF
COLD_START               EQU $6000
COLD_END                 EQU $7FFF
FAST_START               EQU $8000
FAST_END                 EQU $DFFF
KERNEL_START             EQU $E000
KERNEL_END               EQU $FFFF

KERNEL_CODE_START        EQU $E000
KERNEL_CODE_END          EQU $FAFF
KERNEL_STACK_START       EQU $FB00
KERNEL_STACK_END         EQU $FCFF
FAST_RESERVE_START       EQU $FD00
FAST_RESERVE_END         EQU $FDFC
IM2_TRAMPOLINE_START     EQU $FDFD
IM2_TRAMPOLINE_END       EQU $FDFF
IM2_TABLE_START          EQU $FE00
IM2_TABLE_END            EQU $FF00
EMERGENCY_START          EQU $FF01
EMERGENCY_END            EQU $FFFF

SYSCALL_GATEWAY          EQU $E000
BOOT_GATEWAY             EQU $E003
BOOT_STACK_TOP           EQU $FD00
ROM_IY_ANCHOR            EQU $5C3A
IM2_I_VALUE              EQU $FE
IM2_VECTOR_BYTE          EQU $FD

MAX_PROCESSES            EQU $08
MAX_HANDLES_PER_PROCESS  EQU $08
OPEN_DESCRIPTION_COUNT   EQU $18
RAM_OBJECT_COUNT         EQU $20
FIXED_DIR_COUNT          EQU $07

DIR_ROOT                 EQU $00
DIR_BIN                  EQU $01
DIR_DEV                  EQU $02
DIR_ETC                  EQU $03
DIR_HOME                 EQU $04
DIR_USERHOME             EQU $05
DIR_TMP                  EQU $06
DIR_SYSTEM               EQU $07

OBJ_TXT                  EQU $01
OBJ_BIN                  EQU $02
OBJ_OBJ                  EQU $03
OBJ_ASM                  EQU $04
OBJ_C                    EQU $05
OBJ_DAT                  EQU $06
OBJ_UDG                  EQU $07
OBJ_GFX                  EQU $08
OBJ_FNT                  EQU $09
OBJ_CFG                  EQU $0A
OBJ_SYS                  EQU $0B
OBJ_DIR                  EQU $0C
OBJ_DEV                  EQU $0D
OBJ_PACKED               EQU $01

STATE_RAM                EQU $00
STATE_TAPE_BACKED        EQU $01
STATE_PINNED_SYSTEM      EQU $02
STATE_PSEUDO             EQU $03

O_READ                   EQU $01
O_WRITE                  EQU $02
O_CREATE                 EQU $04
O_TRUNC                  EQU $08
O_APPEND                 EQU $10
O_EXCL                   EQU $20

E_OK                     EQU $00
E_INVAL                  EQU $01
E_NOENT                  EQU $02
E_NOMEM                  EQU $03
E_BUSY                   EQU $04
E_IO                     EQU $05
E_EOF                    EQU $06
E_PERM                   EQU $07
E_CHILD                  EQU $08
E_PIPE                   EQU $09
E_TOOLONG                EQU $0A
E_FORMAT                 EQU $0B
E_NOSPC                  EQU $0C
E_AGAIN                  EQU $0D
E_NOTSUP                 EQU $0E
E_INTR                   EQU $0F
E_EXIST                  EQU $10

SYS_VERSION              EQU $00
SYS_EXIT                 EQU $01
SYS_YIELD                EQU $02
SYS_SLEEP                EQU $03
SYS_GETPID               EQU $04
SYS_SPAWN                EQU $05
SYS_EXEC                 EQU $06
SYS_WAIT                 EQU $07
SYS_KILL                 EQU $08

SYS_OPEN                 EQU $10
SYS_CLOSE                EQU $11
SYS_READ                 EQU $12
SYS_WRITE                EQU $13
SYS_SEEK                 EQU $14
SYS_STAT                 EQU $15
SYS_REMOVE               EQU $16
SYS_RENAME               EQU $17
SYS_LIST                 EQU $18
SYS_CHDIR                EQU $19
SYS_GETCWD               EQU $1A
SYS_PACK                 EQU $1B
SYS_UNPACK               EQU $1C

SYS_PIPE                 EQU $20
SYS_DUP                  EQU $21
SYS_IOCTL                EQU $22

SYS_CON_GETKEY           EQU $30
SYS_CON_PUTCHAR          EQU $31
SYS_CON_WRITE            EQU $32
SYS_CON_CLEAR            EQU $33
SYS_CON_GETPOS           EQU $34
SYS_CON_SETPOS           EQU $35

SYS_GFX_PLOT             EQU $40
SYS_GFX_DRAW             EQU $41
SYS_GFX_CIRCLE           EQU $42
SYS_GFX_ATTR             EQU $43
SYS_GFX_BORDER           EQU $44
SYS_GFX_POINT            EQU $45
SYS_BEEP                 EQU $46

SYS_UDG_DEFINE           EQU $48
SYS_UDG_DRAW             EQU $49
SYS_UDG_GET              EQU $4A
SYS_UDG_CLEAR            EQU $4B

SYS_TAPE_SAVE            EQU $50
SYS_TAPE_LOAD            EQU $51
SYS_TAPE_VERIFY          EQU $52
SYS_TAPE_SCAN            EQU $53

SYS_MEM_INFO             EQU $60
SYS_PROC_INFO            EQU $61
SYS_TICKS                EQU $62
SYS_TIME_GET             EQU $63
SYS_TIME_SET             EQU $64
SYS_ZXPACK_INFO          EQU $65

SYS_FP_EXEC              EQU $68
SYS_FP_TO_TEXT           EQU $69
SYS_FP_FROM_TEXT         EQU $6A
SYS_ROM_INFO             EQU $6B
SYS_INT_TO_FP            EQU $6C
SYS_FP_TO_INT            EQU $6D
SYS_FP_CMP               EQU $6E

MEX1_HEADER_SIZE         EQU $0018
OBJ1_HEADER_SIZE         EQU $0018
M48O_HEADER_SIZE         EQU $0020
F4X8_SIZE                EQU $0188
BCAT_ENTRY_COUNT         EQU $28
BCAT_SIZE                EQU $01E8
UDG_BANK_SIZE            EQU $0100
SCREEN_IMAGE_SIZE        EQU $1B00
KERNEL_IMAGE_SIZE        EQU $2000
