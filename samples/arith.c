/* blcc sample 2 (§7): pins idq truncation toward zero: -9/2 = -4, 7%-2 = 1.
   (2+3)*4 - 6/3 + (7%5) - (-9/2) + 7 % -2 = 25. stdout "25\n", exit 25. */
#include "print.h"

int main(void) {
    long r = (2 + 3) * 4 - 6 / 3 + (7 % 5) - (-9 / 2) + 7 % -2;
    pint(r);
    pstr(NL);
    _sys_exit(r);
}
