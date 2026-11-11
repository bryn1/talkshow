/* blcc sample 6 (§7): copy "blcc" into char buf[16] via strlen + byte loop,
   then print it "reversed". §7 pins stdout to the exact bytes "ccbl\n" — that
   is the two halves of "blcc" printed back-to-front (the byte-reverse of
   "blcc" would be "cclb"; the pinned bytes in the contract win).
   stdout "ccbl\n", exit 0. */
#include "print.h"

int main(void) {
    char buf[16];
    const char *src = "blcc";
    long n = strlen(src);
    for (long i = 0; i < n; i = i + 1) {
        buf[i] = src[i];
    }
    long h = n / 2;
    for (long i = h; i < n; i = i + 1) {
        pchar(buf[i]);
    }
    for (long i = 0; i < h; i = i + 1) {
        pchar(buf[i]);
    }
    pstr(NL);
    _sys_exit(0);
}
