/* blcc sample 7 (§7): global struct point {3,4}, p->y + pt.x = 7.
   stdout "7\n", exit 0. */
#include "print.h"

struct point { int x; int y; };

struct point pt = {3, 4};

int main(void) {
    struct point *p = &pt;
    long v = p->y + pt.x;
    pint(v);
    pstr(NL);
    _sys_exit(0);
}
