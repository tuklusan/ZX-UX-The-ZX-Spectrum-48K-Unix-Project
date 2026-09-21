<!-- Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs. -->
<!-- Proprietary rights reserved except as expressly licensed herein. -->
<!-- -->
<!-- ZX-UX Sinclair ZX Spectrum Unix -->
<!-- This file is governed by the SANYALnet Labs Non-Commercial License in the -->
<!-- root LICENSE file. Non-Commercial use is permitted; Commercial Use and use -->
<!-- for AI/ML model training are prohibited unless separately authorized. -->
<!-- -->
<!-- Attribution is required: "Based on original work by Supratim Sanyal of -->
<!-- SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination, -->
<!-- patent, trademark, and governing-law provisions. -->

# ZX-UX Version-1 Shell

The Version-1 shell parser is byte-oriented. It does not delegate tokenization to
Sinclair BASIC, a ROM line editor, a host shell, or any hidden parser.

## Interactive input

An interactive command line is limited to 247 bytes excluding its terminating NUL.
Input is obtained through handle 0 with `SYS_READ`, so kernel TTY ownership remains
authoritative. Backspace editing occurs before tokenization. An attempted 248th byte
returns `E_TOOLONG` before the caller's destination line is published.

## Tokenization and quoting

Outside quotes, ASCII space and TAB separate words. A backslash quotes exactly the next
byte; a trailing backslash is `E_INVAL`. Single quotes preserve every enclosed byte
literally until the next single quote. The quote bytes themselves are removed.

Double quotes also remove their quote bytes. Inside double quotes, backslash removes
special meaning only from `"`, `\`, and `$`. Before every other byte, the backslash
itself is preserved. An unmatched single or double quote is `E_INVAL`.

Empty quoted strings are real empty tokens. Adjacent quoted and unquoted fragments belong
to the same token. Dollar bytes are retained by this tokenizer so the P6.09 expansion
pass can apply the exact unquoted/double-quoted expansion rules without field splitting.

Operators are not classified by P6.08. Quoted and escaped operator bytes therefore remain
literal token data until the dedicated operator lexer is admitted.
