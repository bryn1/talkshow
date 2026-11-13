/* M58(d) v4 FIXTURE-VDSO-SYNTH (DA-m2-c3-1): stands in for the real
 * arch/x86/entry/vdso/vdso32/vclock_gettime.c, which has NO blcc object at M2
 * (-m32 flag class + 78 in-function __asm__ = M3 wall + driver.py unknown-flag
 * hard-exit). Proves the §2.17 fold emits ZERO mem* references on a synthetic
 * TU carrying the measured vdso census shapes. blcc flags:
 *   blcc fixture_vdso_synth.c -o fixture_vdso_synth.o
 * legs: (1) nm -u fixture.o: ZERO undefined memcpy/memset/memcmp/memmove
 *          (mut-memfold plants a call here => RED);
 *       (2) gcc -nostdlib -Wl,-z,defs fixture_vdso_synth.o support_nomm.o:
 *           LINK SUCCEEDS (a named-call lowering fails here);
 *       (3) gcc twin compiled identically below passes (1)+(2) too.
 * support_nomm.o = any object containing NO mem* symbols (e.g. `long s(void){return 1;}`). */
typedef unsigned long __kernel_size_t;
extern int __builtin_memcmp(const void *, const void *, __kernel_size_t); /* decl row (vdso .i:4509 shape): refs NOTHING */
typedef struct { unsigned char b[16]; } guid_t;
typedef struct { unsigned char b[16]; } uuid_t;
static inline __attribute__((__gnu_inline__)) __attribute__((__unused__)) void
memcpy_flushcache(void *d, const void *s, unsigned long n) { __builtin_memcpy(d, s, n); }
static inline __attribute__((__gnu_inline__)) __attribute__((__unused__)) void
memzero_explicit(void *p, unsigned long n) { __builtin_memset(p, 0, n); }
static inline __attribute__((__gnu_inline__)) __attribute__((__unused__)) int
bitmap_eq_shaped(const unsigned long *a, const unsigned long *b, unsigned int n)
{ return __builtin_memcmp(a, b, n / 8); }              /* VAR memcmp: blcc folds (byte loop) */
void vdso_shape(void *d, const void *s, unsigned long n, guid_t *g, const guid_t *gs)
{
    __builtin_memcpy(d, gs, sizeof(guid_t));            /* CONST 16  */
    __builtin_memset(d, 0, sizeof(uuid_t));             /* CONST 16  */
    __builtin_memcpy(d, s, 12);                         /* CONST literal 12 */
    __builtin_memset(d, 0, 1UL << 12);                  /* CONST 4096 clear_page class */
    __builtin_memcpy(d, s, n);                          /* VAR: rep movsb class */
    __builtin_memset(d, 0, n);                          /* VAR: rep stosb class */
    memcpy_flushcache(d, s, n);                         /* wrapper emitted by blcc (NO DCE) + folded */
    memzero_explicit(d, n);
    (void)g;                                        /* unused static-inline
                                                    wrapper body: blcc has
                                                    NO DCE — emitted + folded
                                                    without a (loud) fn-as-
                                                    value reference (§5) */
}

/* main() ADAPTS this spec fixture to blcc's shipped §8 rule (a TU without
 * main is rejected) — the nm/-z-defs legs are unchanged (verdict row). */
int main(void) { char d[64]; guid_t g; vdso_shape(d, d, 8, &g, &g); return 0; }
