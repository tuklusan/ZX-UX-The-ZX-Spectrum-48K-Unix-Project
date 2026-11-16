/* =====================================================================
 * ZX-UX 48K Sinclair ZX Spectrum Unix.
 * Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
 * Non-commercial use only under the repository LICENSE.
 * Commercial use prohibited without separate written permission.
 * ===================================================================== */
/* 32x24 full-height 8x8 text and per-program glyph interface.
 * Requires frozen <c48.h> and the generated matching .asm companion.
 * 32..127 = Acer VGA printable glyphs; 128..159 = per-game glyphs.
 * Each call writes eight screen bitmap bytes and one color attribute.
 * Supports the frozen SDK's INVERSE and OVER state; no UDG slots used.
 */
int c48_cell(int row, int col, int code);

/* 1 if any physical Spectrum key is held, else 0; never reads tty buffer. */
int c48_any_key(void);
int c48_shift_down(void); /* Physical CAPS SHIFT; never reads tty. */
