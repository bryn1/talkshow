/* blcc sample 3 (§7): sum 1..10. stdout "55\n", exit 55. */
#include "print.h"

int main(void) {
    long sum = 0;
    for (int i = 1; i <= 10; i = i + 1) {
        sum = sum + i;
    }
    pint(sum);
    pstr(NL);
    _sys_exit(sum);
}
