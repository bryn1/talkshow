/* blcc sample 1 (§7): exact stdout "Hello, Linux from blcc\n", exit 0. */
#include "print.h"

int main(void) {
    pstr("Hello, Linux from blcc");
    pstr(NL);
    _sys_exit(0);
}
