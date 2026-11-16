/* =====================================================================
 * ZX-UX 48K Sinclair ZX Spectrum Unix.
 * Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
 * Non-commercial use only under the repository LICENSE.
 * Commercial use prohibited without separate written permission.
 * ===================================================================== */
/* C48 library entry points. Include <c48.h> or use these exact prototypes.
 * Kernel call numbers appear beside the extra syscall wrappers below.
 * Missing functions do not appear by wishful thinking. */
#define NULL 0
int getchar(void);
int kbd_down(int key); /* 1 while held, 0 when released; no blocking */
int putchar(int c);
int puts(char *s);
int cls(void);
int print_at(int row, int col, char *text);
int cursor_at(int row, int col); /* move 64-column print cursor without writing */
int ink(int c);
int paper(int c);
int bright(int on);
int flash(int on);
int inverse(int on);
int over(int on);
int border(int c);
int plot(int x, int y);
int point(int x, int y);
int draw(int x1, int y1, int x2, int y2);
int circle(int x, int y, int r);
int udg_define(int slot, unsigned char *bytes);
int udg_get(int slot, unsigned char *bytes);
int udg_draw(int slot, int row, int col);
int udg_clear(int slot);
int udg_draw_2x2(int base, int row, int col);
unsigned int ticks(void);
int yield(void);
int sleep(unsigned int ticks);
int beep(float duration, float pitch);
void exit(int status);
int getpid(void);
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
float sin(float x);
float cos(float x);
float tan(float x);
float asin(float x);
float acos(float x);
float atan(float x);
float sqrt(float x);
float exp(float x);
float log(float x);
float fabs(float x);
float pow(float x, float y);
int open(char *path, int mode);
int close(int h);
int read(int h, void *p, unsigned int n);
int seek(int h, unsigned int pos);

/* The other ZX-UX system calls.  -1 on an error, with errno set to the
 * kernel's error number (also for open, close, read and seek above). */
extern int errno;
int fork(void);                                     /*  2 SSX1: -1 EAGAIN */
int write(int h, void *p, unsigned int n);          /*  4 */
int wait(int *status);                              /*  7 */
int creat(char *path, int mode);                    /*  8 */
int link(char *old, char *new);                     /*  9 */
int unlink(char *path);                             /* 10 */
int exec(char *path, char **argv);                  /* 11 */
int chdir(char *path);                              /* 12 */
int time(unsigned int *t);                          /* 13 t[0] low, t[1] high */
int mkdir(char *path, int mode);                    /* 14 */
int chmod(char *path, int mode);                    /* 15 */
int chown(char *path, int owner);                   /* 16 */
int brk(void *addr);                                /* 17 */
int stat(char *path, void *buf);                    /* 18 34-byte buffer */
int lseek(int h, int offset, int whence);           /* 19 */
int tell(int h);                                    /* 20 */
int setuid(int uid);                                /* 23 */
int getuid(void);                                   /* 24 */
int stime(unsigned int *t);                         /* 25 */
int quit(int on);                                   /* 26 */
int intr(int on);                                   /* 27 */
int fstat(int h, void *buf);                        /* 28 34-byte buffer */
int cemt(void *p);                                  /* 29 */
int mdate(char *path, unsigned int *t);             /* 30 */
int stty(int h, void *buf);                         /* 31 6-byte buffer */
int gtty(int h, void *buf);                         /* 32 6-byte buffer */
int ilgins(void *p);                                /* 33 */
int kill(int pid);                                  /* 35 */
unsigned int zxpack(char *path);                    /* 37 */
int zxinfo(unsigned int *info);                     /* 37 path NULL */
unsigned char *screen(int claim);                   /* 39 */
int ssxload(char **argv, unsigned int memory, unsigned int length); /* 40 */
