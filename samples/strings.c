/* blcc sample 6 (§7, contract v3): copy "blcc" into char buf[16] via strlen +
   byte loop, reverse the buffer with a two-index swap loop, print it.
   gcc ground truth: stdout "cclb\n", exit 0. */
#include "print.h"

int main(void) {
    char buf[16];
    const char *src = "blcc";
    long n = strlen(src);
    for (long i = 0; i < n; i = i + 1) {
        buf[i] = src[i];
    }
    buf[n] = 0;                 /* terminate for pstr/strlen */
    long a = 0;
    long b = n - 1;
    while (a < b) {
        char t = buf[a];
        buf[a] = buf[b];
        buf[b] = t;
        a = a + 1;
        b = b - 1;
    }
    pstr(buf);
    pstr(NL);
    _sys_exit(0);
}
