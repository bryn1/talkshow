/* planted-RED witness (M58 d-leg negative control): plain-name mem* calls the
 * -Os fold classes vs the call class. memcmp VAR is the class gcc -Os CALLS
 * (jmp memcmp@PLT, measured 2.17 table) -> U memcmp -> -z,defs link FAILS on a
 * no-mem* image: the exact link-hole shape mut-memfold plants for blcc. */
extern int memcmp(const void *, const void *, unsigned long);
extern void *memcpy(void *, const void *, unsigned long);
int cmp_hole(const void *a, const void *b, unsigned long n) { return memcmp(a, b, n); }
void cp_folded(void *d, const void *s, unsigned long n) { memcpy(d, s, n); } /* VAR: rep movsb, no U */
