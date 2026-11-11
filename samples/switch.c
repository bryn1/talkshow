/* blcc sample 11 (§7): switch compare chain over 0..4.
   stdout "zero\none\ntwo\nmany\nmany\n", exit 0. */
#include "print.h"

int main(void) {
    for (int i = 0; i < 5; i = i + 1) {
        switch (i) {
        case 0:
            pstr("zero\n");
            break;
        case 1:
            pstr("one\n");
            break;
        case 2:
            pstr("two\n");
            break;
        default:
            pstr("many\n");
            break;
        }
    }
    _sys_exit(0);
}
