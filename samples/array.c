/* blcc sample 5 (§7): a[i]=i*i, pointer walk *(p+i) sums to 140.
   stdout "140\n", exit 0. */
#include "print.h"

int main(void) {
    int a[8];
    for (int i = 0; i < 8; i = i + 1) {
        a[i] = i * i;
    }
    int *p = a;
    long s = 0;
    for (int i = 0; i < 8; i = i + 1) {
        s = s + *(p + i);
    }
    pint(s);
    pstr(NL);
    _sys_exit(0);
}
