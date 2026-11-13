/* M58(c) FIXTURE-BOOT (§4.3): arch/x86/boot/string.h #define trio + the
 * CONST call shape of boot/main.c:39, plus an EMITTED function with a
 * variable-size memcpy (the vdso/gnu_inline wrapper class has no body in
 * the .i; boot's does). legs: nm -u blcc .o => ZERO mem* U;
 * gcc -nostdlib -Wl,-z defs fixture.o support_nomm.o => LINK SUCCEEDS;
 * gcc -std=gnu89 -Os twin => the same two legs pass. */
#define memcpy(d, s, l)  __builtin_memcpy(d, s, l)
#define memcmp(a, b, l)  __builtin_memcmp(a, b, l)
#define memset(d, c, l)  __builtin_memset(d, c, l)
typedef unsigned long size_t;
static char buf[64];
static const char msg[] = "hello boot world!!";
static int shape(void *dst, const void *src, unsigned long n)
{
    memcpy(buf, msg, 16);           /* CONST — boot/main.c:39 class  */
    memset(buf, 0, 8);              /* CONST zero-fill               */
    memcpy(dst, src, n);            /* VAR in an EMITTED function    */
    return memcmp(buf, msg, 4);     /* CONST memcmp                  */
}
static unsigned long gnn;
int main(void)
{
    char a[32], b[32];
    int i, s = 0;
    gnn = 10;
    for (i = 0; i < 32; i++) { a[i] = 0; b[i] = (char)(i + 1); }
    s += shape(a, b, gnn);          /* VAR size via GLOBAL (no fold) */
    (void)s;
    s = 0;
    for (i = 0; i < 10; i++) s += (unsigned char)a[i];
    if (s != 55) return 1;          /* 1+2+...+10 through the VAR fold */
    return 0;
}
