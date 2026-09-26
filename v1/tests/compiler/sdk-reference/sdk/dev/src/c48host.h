// ============================================================
// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and AI/ML
// model training prohibited unless separately authorized.
//
// Attribution required: Based on original work by Supratim
// Sanyal of SANYALnet Labs. See root LICENSE for full terms.
// ============================================================
/* C48 Host Game API profile 0.1.
 * DEVELOPMENT-ONLY PROTOTYPES. These are not the final
 * ZX-UX P11.41 <c48.h> ABI.
 * The source language remains strict C48 Rev 0.11.
 */
int getchar(void);
int putchar(int c);
int puts(char *s);
unsigned int strlen(char *s);
int strcmp(char *a, char *b);
char *strcpy(char *d, char *s);
char *strncpy(char *d, char *s, unsigned int n);
void *memcpy(void *d, void *s, unsigned int n);
void *memmove(void *d, void *s, unsigned int n);
void *memchr(void *p, int c, unsigned int n);
void *memset(void *p, int c, unsigned int n);
void *malloc(unsigned int n);
void free(void *p);
int cls(void);
int plot(int x, int y);
int point(int x, int y);
int draw(int x1, int y1, int x2, int y2);
int circle(int x, int y, int r);
int ink(int c);
int paper(int c);
int bright(int on);
int flash(int on);
int inverse(int on);
int over(int on);
int border(int c);
int print_at(int row, int col, char *text);
int udg_define(int slot, unsigned char *bytes);
int udg_get(int slot, unsigned char *bytes);
int udg_draw(int slot, int row, int col);
int udg_clear(int slot);
int udg_draw_2x2(int base, int row, int col);
unsigned int ticks(void);
int yield(void);
int sleep(unsigned int ticks);
void exit(int status);
float sin(float x);
float cos(float x);
float tan(float x);
float asin(float x);
float acos(float x);
float atan(float x);
float sqrt(float x);
float exp(float x);
float log(float x);
float pow(float x, float y);
float fabs(float x);
