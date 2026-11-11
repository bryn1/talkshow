/* blcc sample 12 (§7): global g bumped twice in bump(), 19 + g = 21.
   stdout "21\n", exit 21. */
#include "print.h"

int g = 0;

void bump(void) {
    g = g + 1;
}

int main(void) {
    bump();
    bump();
    long v = 19 + g;
    pint(v);
    pstr(NL);
    _sys_exit(v);
}
