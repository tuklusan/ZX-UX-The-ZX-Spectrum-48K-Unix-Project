/* =====================================================================
 * ZX-UX 48K Sinclair ZX Spectrum Unix.
 * Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
 * Non-commercial use only under the repository LICENSE.
 * Commercial use prohibited without separate written permission.
 * ===================================================================== */
/* rcc runtime: malloc/free over the program's heap (first fit, coalescing).
 * Block: word 0 = size in words including the 2-word header, bit 15 = in
 * use; word 1 = requested bytes.  Live requested bytes are limited to the
 * C48 heap size (1024 by default), as in the SDK.  free() of anything but a
 * live block start ends the program with status 1. */
extern unsigned int __heap[];
extern unsigned int __heapw;
extern unsigned int __heapsz;
void exit(int status);

static int __hinit;
static unsigned int __hlive;

void *malloc(unsigned int n)
{
    unsigned int *p;
    unsigned int *end;
    unsigned int *q;
    unsigned int w;
    unsigned int sz;
    if (n == 0u || n > __heapsz || __hlive + n > __heapsz)
        return 0;
    if (!__hinit) {
        __heap[0] = __heapw;
        __hinit = 1;
    }
    w = (n + 1u) / 2u + 2u;
    p = __heap;
    end = __heap + __heapw;
    while (p < end) {
        sz = *p & 0x7fffu;
        if (!(*p & 0x8000u)) {
            q = p + sz;
            while (q < end && !(*q & 0x8000u)) {
                sz = sz + *q;
                q = p + sz;
            }
            *p = sz;
            if (sz >= w) {
                if (sz > w + 2u) {
                    p[w] = sz - w;
                    *p = w | 0x8000u;
                } else
                    *p = sz | 0x8000u;
                p[1] = n;
                __hlive = __hlive + n;
                return p + 2;
            }
        }
        p = p + sz;
    }
    return 0;
}

void free(void *v)
{
    unsigned int *p;
    unsigned int *q;
    if (v == 0)
        return;
    p = v;
    p = p - 2;
    q = __heap;
    while (q < p && __hinit)
        q = q + (*q & 0x7fffu);
    if (!__hinit || q != p || !(*p & 0x8000u))
        exit(1);
    __hlive = __hlive - p[1];
    *p = *p & 0x7fffu;
}
